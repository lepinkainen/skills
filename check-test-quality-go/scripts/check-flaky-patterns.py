#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "tree-sitter>=0.23.0",
#   "tree-sitter-go>=0.23.0",
# ]
# ///
"""
Check for flaky test patterns in Go tests.

Detects: goroutines without sync, hardcoded timeouts, non-deterministic
randomness, time dependencies.

This script uses tree-sitter for scope-aware analysis, checking if
synchronization primitives exist in the same test function.
"""
import sys
import re
from pathlib import Path
from tree_sitter import Query

# Import shared utilities (local module)
sys.path.insert(0, str(Path(__file__).parent))
from test_quality_common import (
    Issue, TestFunction, parse_go_file, find_test_functions, find_test_files,
    find_function_calls, has_pattern_in_scope, find_goroutines,
    get_code_snippet, build_json_output, relative_path, GO_LANGUAGE, get_node_text
)


def has_sync_waitgroup(body_node, source_bytes: bytes) -> bool:
    """Check if test uses sync.WaitGroup."""
    # Check for sync.WaitGroup type or .Wait()/.Add()/.Done() calls
    has_waitgroup_type = has_pattern_in_scope(
        body_node, source_bytes, package_pattern="sync", method_pattern="WaitGroup"
    )

    has_wait_calls = has_pattern_in_scope(
        body_node, source_bytes, package_pattern=".*", method_pattern="(Wait|Add|Done)"
    )

    return has_waitgroup_type or has_wait_calls


def has_channel_usage(body_node) -> bool:
    """Check if test uses channels for synchronization."""
    # Query for make(chan ...), send/receive operations
    channel_query = Query(GO_LANGUAGE, """
    [
      (call_expression
        function: (identifier) @make
        arguments: (argument_list
          (channel_type)
        )
        (#eq? @make "make")
      ) @make_chan
      (send_statement) @send
      (receive_statement) @receive
    ]
    """)

    return len(channel_query.captures(body_node)) > 0


def check_unsynchronized_goroutines(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect goroutines without synchronization (CRITICAL).

    Checks if WaitGroup or channels exist in same test scope.
    """
    issues = []

    goroutines = find_goroutines(test_func.body_node)

    if not goroutines:
        return issues

    # Check if test has synchronization
    has_waitgroup = has_sync_waitgroup(test_func.body_node, test_func.source_bytes)
    has_channels = has_channel_usage(test_func.body_node)

    if not (has_waitgroup or has_channels):
        for goroutine_node in goroutines:
            issues.append(Issue(
                file=relative_path(test_func.filepath, project_root),
                line=goroutine_node.start_point[0] + 1,
                test_name=test_func.name,
                issue="Goroutine spawned without synchronization (WaitGroup/channels)",
                category="Flaky Tests",
                severity="Critical",
                pattern="go func(",
                code_snippet=get_code_snippet(goroutine_node, test_func.source_bytes),
                suggestion="Use sync.WaitGroup to wait for goroutine completion, or use channels to receive results. Without synchronization, the test may finish before the goroutine completes"
            ))

    return issues


def has_rand_seed(body_node, source_bytes: bytes) -> bool:
    """Check if test has rand.Seed or rand.NewSource."""
    return (
        has_pattern_in_scope(body_node, source_bytes, "rand", "Seed") or
        has_pattern_in_scope(body_node, source_bytes, "rand", "NewSource") or
        has_pattern_in_scope(body_node, source_bytes, "rand", "New")
    )


def check_unseeded_random(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect rand usage without deterministic seed (HIGH).

    Checks for rand.Int, rand.Float, rand.Intn without seed in same test.
    """
    issues = []

    # Find rand.Int, rand.Float, rand.Intn calls
    rand_methods = ["Int", "Float", "Intn", "Float32", "Float64", "Int31", "Int63"]

    all_rand_calls = []
    for method in rand_methods:
        calls = find_function_calls(
            test_func.body_node,
            test_func.source_bytes,
            package_pattern="rand",
            method_pattern=method
        )
        all_rand_calls.extend(calls)

    if not all_rand_calls:
        return issues

    # Check if test has rand.Seed or rand.NewSource
    has_seed = has_rand_seed(test_func.body_node, test_func.source_bytes)

    if not has_seed:
        for call_node, package, method in all_rand_calls:
            issues.append(Issue(
                file=relative_path(test_func.filepath, project_root),
                line=call_node.start_point[0] + 1,
                test_name=test_func.name,
                issue="Using rand without deterministic seed causes non-reproducible test failures",
                category="Flaky Tests",
                severity="High",
                pattern=f"rand.{method}",
                code_snippet=get_code_snippet(call_node, test_func.source_bytes),
                suggestion="Use rand.New(rand.NewSource(1)) with a fixed seed for reproducible random data in tests"
            ))

    return issues


def check_time_dependencies(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect time.Now() usage without mocking (HIGH).

    Limited to 20 issues per run to avoid spam.
    """
    issues = []

    # Find time.Now() calls
    calls = find_function_calls(
        test_func.body_node,
        test_func.source_bytes,
        package_pattern="time",
        method_pattern="Now"
    )

    for call_node, package, method in calls:
        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=call_node.start_point[0] + 1,
            test_name=test_func.name,
            issue="Using time.Now() without mocking makes test time-dependent",
            category="Flaky Tests",
            severity="High",
            pattern="time.Now",
            code_snippet=get_code_snippet(call_node, test_func.source_bytes),
            suggestion="Inject a clock interface or use a fixed time in tests. Consider using a library like github.com/benbjohnson/clock for testable time"
        ))

    return issues


def is_eventually_assertion(call_node, source_bytes: bytes) -> bool:
    """Check if this is a require.Eventually or assert.Eventually call."""
    text = get_node_text(call_node, source_bytes)
    return bool(re.search(r'(require|assert)\.Eventually', text))


def has_numeric_timeout(call_node, source_bytes: bytes) -> bool:
    """Check if call has numeric timeout duration."""
    text = get_node_text(call_node, source_bytes)
    # Look for patterns like "100 * time.Millisecond" or "5 * time.Second"
    return bool(re.search(r'\d+\s*\*\s*time\.(Millisecond|Second|Minute)', text))


def check_hardcoded_timeouts(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect hardcoded timeout durations (HIGH).

    Patterns: context.WithTimeout, time.After with numeric literals.
    Excludes require.Eventually and assert.Eventually.
    Limited to 15 issues per run.
    """
    issues = []

    # Find context.WithTimeout and time.After calls
    timeout_patterns = [
        ("context", "WithTimeout"),
        ("time", "After"),
    ]

    for package, method in timeout_patterns:
        calls = find_function_calls(
            test_func.body_node,
            test_func.source_bytes,
            package_pattern=package,
            method_pattern=method
        )

        for call_node, pkg, meth in calls:
            # Skip if using require.Eventually or assert.Eventually (acceptable)
            if is_eventually_assertion(call_node, test_func.source_bytes):
                continue

            # Check if it has numeric duration
            if has_numeric_timeout(call_node, test_func.source_bytes):
                issues.append(Issue(
                    file=relative_path(test_func.filepath, project_root),
                    line=call_node.start_point[0] + 1,
                    test_name=test_func.name,
                    issue="Hardcoded timeout duration may be too short on slow CI machines",
                    category="Flaky Tests",
                    severity="High",
                    pattern=f"{pkg}.{meth}",
                    code_snippet=get_code_snippet(call_node, test_func.source_bytes),
                    suggestion="Use generous timeouts (5-10 seconds) or environment-configurable timeouts. Tests should fail on logic errors, not slow machines"
                ))

    return issues


def analyze_file(filepath: Path, project_root: Path) -> list[Issue]:
    """Analyze a single test file for flaky patterns."""
    tree = parse_go_file(filepath)
    if tree is None:
        return []

    with open(filepath, 'rb') as f:
        source_bytes = f.read()

    test_functions = find_test_functions(tree, filepath, source_bytes)

    all_issues = []
    for test_func in test_functions:
        all_issues.extend(check_unsynchronized_goroutines(test_func, project_root))
        all_issues.extend(check_unseeded_random(test_func, project_root))
        all_issues.extend(check_time_dependencies(test_func, project_root))
        all_issues.extend(check_hardcoded_timeouts(test_func, project_root))

    return all_issues


def main():
    """Main entry point."""
    project_root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")

    # Validate project root
    if not project_root.exists():
        print(f'{{"error": "Invalid path", "message": "Project root does not exist: {project_root}"}}')
        sys.exit(1)

    # Find test files
    test_files = find_test_files(project_root)

    if not test_files:
        # No test files found - output empty result
        print(build_json_output("check-flaky-patterns", []))
        return

    # Analyze all test files
    all_issues = []
    for test_file in test_files:
        all_issues.extend(analyze_file(test_file, project_root))

    # Sort issues by file and line number
    all_issues.sort(key=lambda i: (i.file, i.line))

    # Limit time.Now issues to 20 (matching bash behavior)
    time_now_issues = [i for i in all_issues if i.pattern == "time.Now"]
    other_issues = [i for i in all_issues if i.pattern != "time.Now"]
    all_issues = other_issues + time_now_issues[:20]

    # Limit timeout issues to 15 (matching bash behavior)
    timeout_issues = [i for i in all_issues if "WithTimeout" in i.pattern or "After" in i.pattern]
    other_issues = [i for i in all_issues if i not in timeout_issues]
    all_issues = other_issues + timeout_issues[:15]

    # Sort again after limiting
    all_issues.sort(key=lambda i: (i.file, i.line))

    # Output JSON
    print(build_json_output("check-flaky-patterns", all_issues))


if __name__ == "__main__":
    main()
