#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "tree-sitter>=0.23.0",
#   "tree-sitter-go>=0.23.0",
# ]
# ///
"""
Check for testing anti-patterns in Go tests.

Detects: reflection, over-mocking, missing assertions, global state.

This script uses tree-sitter for accurate scope-aware analysis, ensuring
assertions are counted only in test code, not in comments or strings.
"""
import sys
import re
from pathlib import Path
from tree_sitter import Query

# Import shared utilities (local module)
sys.path.insert(0, str(Path(__file__).parent))
from test_quality_common import (
    Issue, TestFunction, parse_go_file, find_test_functions, find_test_files,
    find_function_calls, has_pattern_in_scope, find_defer_statements,
    get_code_snippet, get_node_text, build_json_output, relative_path, GO_LANGUAGE
)


def check_reflection_usage(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect reflection accessing unexported fields (HIGH).

    Patterns: reflect.ValueOf, reflect.TypeOf, .Elem(), .FieldByName, unsafe.Pointer
    """
    issues = []

    # Check for reflect.ValueOf and reflect.TypeOf
    reflection_patterns = [
        ("reflect", "ValueOf"),
        ("reflect", "TypeOf"),
        ("unsafe", "Pointer"),
    ]

    for package, method in reflection_patterns:
        calls = find_function_calls(
            test_func.body_node,
            test_func.source_bytes,
            package_pattern=package,
            method_pattern=method
        )

        for call_node, pkg, meth in calls:
            issues.append(Issue(
                file=relative_path(test_func.filepath, project_root),
                line=call_node.start_point[0] + 1,
                test_name=test_func.name,
                issue="Using reflection to access unexported fields couples test to implementation",
                category="Anti-Patterns",
                severity="High",
                pattern=f"{pkg}.{meth}",
                code_snippet=get_code_snippet(call_node, test_func.source_bytes),
                suggestion="Test the public API only. If internal behavior needs testing, consider extracting it to a separate exported function or using test-only accessors"
            ))

    # Check for .Elem() and .FieldByName() method calls (on any object)
    elem_fieldbyname_patterns = ["Elem", "FieldByName", "SetString", "Set"]

    for method in elem_fieldbyname_patterns:
        # Find all method calls matching this pattern
        calls = find_function_calls(
            test_func.body_node,
            test_func.source_bytes,
            package_pattern=".*",
            method_pattern=method
        )

        for call_node, pkg, meth in calls:
            # Only report if it's likely reflection (not a common method name)
            if method in ["Elem", "FieldByName"]:
                issues.append(Issue(
                    file=relative_path(test_func.filepath, project_root),
                    line=call_node.start_point[0] + 1,
                    test_name=test_func.name,
                    issue="Using reflection to access unexported fields couples test to implementation",
                    category="Anti-Patterns",
                    severity="High",
                    pattern=f".{meth}",
                    code_snippet=get_code_snippet(call_node, test_func.source_bytes),
                    suggestion="Test the public API only. If internal behavior needs testing, consider extracting it to a separate exported function or using test-only accessors"
                ))

    return issues


def count_assertions(body_node, source_bytes: bytes) -> int:
    """
    Count assert.* and require.* calls in test scope.

    Uses AST parsing to count only actual calls, not comments or strings.
    """
    assertion_query = Query(GO_LANGUAGE, """
    (call_expression
      function: (selector_expression
        operand: (identifier) @obj
        field: (field_identifier)
      )
      (#match? @obj "^(assert|require)$")
    ) @assertion
    """)

    # Also count t.Error, t.Fatal, t.Errorf, t.Fatalf
    t_assertion_query = Query(GO_LANGUAGE, """
    (call_expression
      function: (selector_expression
        operand: (identifier) @obj
        field: (field_identifier) @method
      )
      (#eq? @obj "t")
      (#match? @method "^(Error|Fatal|Errorf|Fatalf)$")
    ) @t_assertion
    """)

    assertion_count = len(assertion_query.captures(body_node))
    t_assertion_count = len(t_assertion_query.captures(body_node))

    return assertion_count + t_assertion_count


def check_assertion_count(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect >5 assertions per test (MEDIUM).

    Uses AST for accurate counting, excluding comments.
    """
    issues = []

    assertion_count = count_assertions(test_func.body_node, test_func.source_bytes)

    if assertion_count > 5:
        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=test_func.start_line,
            test_name=test_func.name,
            issue=f"Test has {assertion_count} assertions (>5 suggests testing multiple behaviors)",
            category="Anti-Patterns",
            severity="Medium",
            pattern="assert.|require.",
            code_snippet="Multiple assertions in single test",
            suggestion="Split into multiple focused tests with one assertion each, or group related assertions by behavior. Multiple assertions make failures harder to diagnose",
            metrics={"assertion_count": assertion_count}
        ))

    return issues


def check_missing_cleanup(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect os.Setenv without cleanup (MEDIUM).

    Checks for defer cleanup or t.Setenv within test scope.
    """
    issues = []

    # Find os.Setenv calls
    setenv_calls = find_function_calls(
        test_func.body_node,
        test_func.source_bytes,
        package_pattern="os",
        method_pattern="Setenv"
    )

    # Check for t.Setenv (new Go 1.17+ API, which is OK)
    t_setenv_calls = find_function_calls(
        test_func.body_node,
        test_func.source_bytes,
        package_pattern="t",
        method_pattern="Setenv"
    )

    # If using t.Setenv, no issues
    if t_setenv_calls:
        return issues

    # Check if defer cleanup exists
    defer_nodes = find_defer_statements(test_func.body_node)
    has_cleanup = False

    for defer_node in defer_nodes:
        defer_text = get_node_text(defer_node, test_func.source_bytes)
        if re.search(r'(Unsetenv|Setenv|Cleanup)', defer_text):
            has_cleanup = True
            break

    if not has_cleanup:
        for call_node, pkg, meth in setenv_calls:
            issues.append(Issue(
                file=relative_path(test_func.filepath, project_root),
                line=call_node.start_point[0] + 1,
                test_name=test_func.name,
                issue="os.Setenv without cleanup can pollute test environment",
                category="Anti-Patterns",
                severity="Medium",
                pattern="os.Setenv",
                code_snippet=get_code_snippet(call_node, test_func.source_bytes),
                suggestion='Use t.Setenv() (Go 1.17+) which automatically cleans up, or add: defer os.Unsetenv("VAR_NAME")'
            ))

    return issues


def check_global_state(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect global/package-level variable modifications (MEDIUM).

    This is heuristic-based even with AST, as it's hard to definitively
    determine if a variable is package-level.
    """
    issues = []

    # Query for assignment statements
    assignment_query = Query(GO_LANGUAGE, """
    (assignment_statement
      left: (expression_list
        (identifier) @var
      )
    ) @assignment
    """)

    assignments = assignment_query.captures(test_func.body_node)

    for node, capture_name in assignments[:20]:  # Limit to 20 like bash version
        if capture_name == "var":
            var_name = get_node_text(node, test_func.source_bytes)

            # Check if variable looks global (all caps or common global patterns)
            if re.match(r'^[A-Z][A-Z_]+$', var_name):
                parent = node.parent
                if parent:
                    issues.append(Issue(
                        file=relative_path(test_func.filepath, project_root),
                        line=parent.start_point[0] + 1,
                        test_name=test_func.name,
                        issue="Modifying package-level variable can cause test interdependencies",
                        category="Anti-Patterns",
                        severity="Medium",
                        pattern="global state",
                        code_snippet=get_code_snippet(parent, test_func.source_bytes),
                        suggestion="Use test-scoped variables or pass state through function parameters. If global state is necessary, ensure proper cleanup with defer or t.Cleanup()"
                    ))
                    break  # Only report once per test

    return issues


def check_missing_assertions(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect tests with no assertions (MEDIUM).

    Excludes benchmarks and tests with t.Skip.
    """
    issues = []

    # Skip benchmarks
    if test_func.name.startswith("Benchmark"):
        return issues

    # Check for assertions
    assertion_count = count_assertions(test_func.body_node, test_func.source_bytes)

    if assertion_count == 0:
        # Check for t.Skip
        has_skip = has_pattern_in_scope(
            test_func.body_node,
            test_func.source_bytes,
            package_pattern="t",
            method_pattern="Skip.*"
        )

        if not has_skip:
            issues.append(Issue(
                file=relative_path(test_func.filepath, project_root),
                line=test_func.start_line,
                test_name=test_func.name,
                issue="Test function has no assertions (may be incomplete or not actually testing)",
                category="Anti-Patterns",
                severity="Medium",
                pattern="no assertions",
                code_snippet=f"func {test_func.name}",
                suggestion="Add assertions to verify expected behavior, or add t.Skip() if the test is intentionally incomplete"
            ))

    return issues


def analyze_file(filepath: Path, project_root: Path) -> list[Issue]:
    """Analyze a single test file for anti-patterns."""
    tree = parse_go_file(filepath)
    if tree is None:
        return []

    with open(filepath, 'rb') as f:
        source_bytes = f.read()

    test_functions = find_test_functions(tree, filepath, source_bytes)

    all_issues = []
    for test_func in test_functions:
        all_issues.extend(check_reflection_usage(test_func, project_root))
        all_issues.extend(check_assertion_count(test_func, project_root))
        all_issues.extend(check_missing_cleanup(test_func, project_root))
        all_issues.extend(check_global_state(test_func, project_root))
        all_issues.extend(check_missing_assertions(test_func, project_root))

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
        print(build_json_output("check-anti-patterns", []))
        return

    # Analyze all test files
    all_issues = []
    for test_file in test_files:
        all_issues.extend(analyze_file(test_file, project_root))

    # Sort issues by file and line number
    all_issues.sort(key=lambda i: (i.file, i.line))

    # Limit global state issues to 20 (matching bash behavior)
    global_state_issues = [i for i in all_issues if i.pattern == "global state"]
    other_issues = [i for i in all_issues if i.pattern != "global state"]
    all_issues = other_issues + global_state_issues[:20]

    # Limit no-assertions issues to 30 (matching bash behavior)
    no_assertion_issues = [i for i in all_issues if i.pattern == "no assertions"]
    other_issues = [i for i in all_issues if i.pattern != "no assertions"]
    all_issues = other_issues + no_assertion_issues[:30]

    # Sort again after limiting
    all_issues.sort(key=lambda i: (i.file, i.line))

    # Output JSON
    print(build_json_output("check-anti-patterns", all_issues))


if __name__ == "__main__":
    main()
