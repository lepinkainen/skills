#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "tree-sitter>=0.23.0",
#   "tree-sitter-go>=0.23.0",
# ]
# ///
"""
Check for external dependencies in Go tests.

Detects: database connections, HTTP calls, file I/O, time dependencies.

This script uses tree-sitter for accurate AST parsing instead of regex-based
pattern matching, eliminating false positives from comments and strings.
"""
import sys
from pathlib import Path

# Import shared utilities (local module)
sys.path.insert(0, str(Path(__file__).parent))
from test_quality_common import (
    Issue, TestFunction, parse_go_file, find_test_functions, find_test_files,
    find_function_calls, has_pattern_in_scope, get_code_snippet,
    build_json_output, relative_path
)


def check_time_sleep(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect time.Sleep calls (CRITICAL).

    time.Sleep makes tests slow and timing-dependent (flaky).
    """
    issues = []
    calls = find_function_calls(
        test_func.body_node,
        test_func.source_bytes,
        package_pattern="time",
        method_pattern="Sleep"
    )

    for call_node, package, method in calls:
        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=call_node.start_point[0] + 1,
            test_name=test_func.name,
            issue="time.Sleep makes test slow and timing-dependent (flaky)",
            category="External Dependency",
            severity="Critical",
            pattern="time.Sleep",
            code_snippet=get_code_snippet(call_node, test_func.source_bytes),
            suggestion="Use channels, sync.WaitGroup, or require.Eventually for deterministic synchronization instead of sleeping"
        ))

    return issues


def check_database_connections(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect database connections (CRITICAL).

    Patterns: sql.Open, gorm.*, postgres://, mysql://
    """
    issues = []

    # Check for sql.Open
    sql_calls = find_function_calls(
        test_func.body_node,
        test_func.source_bytes,
        package_pattern="sql",
        method_pattern="Open"
    )

    for call_node, package, method in sql_calls:
        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=call_node.start_point[0] + 1,
            test_name=test_func.name,
            issue="Real database connection in test makes it slow and environment-dependent",
            category="External Dependency",
            severity="Critical",
            pattern="sql.Open",
            code_snippet=get_code_snippet(call_node, test_func.source_bytes),
            suggestion="Use a mock database, sqlmock, or test containers for integration tests. Unit tests should mock the database layer"
        ))

    # Check for gorm.*
    gorm_calls = find_function_calls(
        test_func.body_node,
        test_func.source_bytes,
        package_pattern="gorm"
    )

    for call_node, package, method in gorm_calls:
        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=call_node.start_point[0] + 1,
            test_name=test_func.name,
            issue="Real database connection in test makes it slow and environment-dependent",
            category="External Dependency",
            severity="Critical",
            pattern=f"gorm.{method}",
            code_snippet=get_code_snippet(call_node, test_func.source_bytes),
            suggestion="Use a mock database, sqlmock, or test containers for integration tests. Unit tests should mock the database layer"
        ))

    # Check for connection strings in literals (postgres://, mysql://)
    import re
    from tree_sitter import Query
    from test_quality_common import GO_LANGUAGE

    string_query = Query(GO_LANGUAGE, """
    [
      (interpreted_string_literal) @string
      (raw_string_literal) @string
    ]
    """)

    string_captures = string_query.captures(test_func.body_node)
    for node, _ in string_captures:
        text = node.text.decode('utf-8') if isinstance(node.text, bytes) else str(node.text)
        if re.search(r'(postgres|mysql)://', text):
            issues.append(Issue(
                file=relative_path(test_func.filepath, project_root),
                line=node.start_point[0] + 1,
                test_name=test_func.name,
                issue="Real database connection in test makes it slow and environment-dependent",
                category="External Dependency",
                severity="Critical",
                pattern="postgres://|mysql://",
                code_snippet=get_code_snippet(node, test_func.source_bytes),
                suggestion="Use a mock database, sqlmock, or test containers for integration tests. Unit tests should mock the database layer"
            ))

    return issues


def check_http_calls(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect HTTP calls to real servers (CRITICAL).

    Patterns: http.Get, http.Post, http.Client (excluding httptest usage)
    """
    issues = []

    # Check if test uses httptest (which is acceptable)
    uses_httptest = has_pattern_in_scope(
        test_func.body_node,
        test_func.source_bytes,
        package_pattern="httptest"
    )

    if uses_httptest:
        return issues  # httptest usage is acceptable

    # Check for http.Get, http.Post, http.Put, http.Delete, http.Do
    http_methods = ["Get", "Post", "Put", "Delete", "Do", "Head", "NewRequest"]

    for method in http_methods:
        calls = find_function_calls(
            test_func.body_node,
            test_func.source_bytes,
            package_pattern="http",
            method_pattern=method
        )

        for call_node, package, method_name in calls:
            issues.append(Issue(
                file=relative_path(test_func.filepath, project_root),
                line=call_node.start_point[0] + 1,
                test_name=test_func.name,
                issue="Real HTTP call to external server makes test slow, flaky, and network-dependent",
                category="External Dependency",
                severity="Critical",
                pattern=f"http.{method_name}",
                code_snippet=get_code_snippet(call_node, test_func.source_bytes),
                suggestion="Use httptest.Server to create a test HTTP server, or inject a mock HTTP client"
            ))

    # Check for http.Client{} composite literals
    from tree_sitter import Query
    from test_quality_common import GO_LANGUAGE

    client_query = Query(GO_LANGUAGE, """
    (composite_literal
      type: (selector_expression
        operand: (identifier) @pkg
        field: (field_identifier) @type
      )
      (#eq? @pkg "http")
      (#eq? @type "Client")
    ) @client
    """)

    client_captures = client_query.captures(test_func.body_node)
    for node, _ in client_captures:
        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=node.start_point[0] + 1,
            test_name=test_func.name,
            issue="Real HTTP call to external server makes test slow, flaky, and network-dependent",
            category="External Dependency",
            severity="Critical",
            pattern="http.Client",
            code_snippet=get_code_snippet(node, test_func.source_bytes),
            suggestion="Use httptest.Server to create a test HTTP server, or inject a mock HTTP client"
        ))

    return issues


def check_web_servers(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect web servers on network ports (CRITICAL).

    Patterns: ListenAndServe, http.Server
    """
    issues = []

    # Check for ListenAndServe
    calls = find_function_calls(
        test_func.body_node,
        test_func.source_bytes,
        package_pattern=".*",  # Can be http.ListenAndServe or just ListenAndServe
        method_pattern="ListenAndServe"
    )

    for call_node, package, method in calls:
        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=call_node.start_point[0] + 1,
            test_name=test_func.name,
            issue="Starting real web server in test creates port conflicts and slow tests",
            category="External Dependency",
            severity="Critical",
            pattern="ListenAndServe",
            code_snippet=get_code_snippet(call_node, test_func.source_bytes),
            suggestion="Use httptest.Server which automatically picks an available port and shuts down cleanly"
        ))

    # Check for http.Server{} composite literals
    from tree_sitter import Query
    from test_quality_common import GO_LANGUAGE

    server_query = Query(GO_LANGUAGE, """
    (composite_literal
      type: (selector_expression
        operand: (identifier) @pkg
        field: (field_identifier) @type
      )
      (#eq? @pkg "http")
      (#eq? @type "Server")
    ) @server
    """)

    server_captures = server_query.captures(test_func.body_node)
    for node, _ in server_captures:
        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=node.start_point[0] + 1,
            test_name=test_func.name,
            issue="Starting real web server in test creates port conflicts and slow tests",
            category="External Dependency",
            severity="Critical",
            pattern="http.Server",
            code_snippet=get_code_snippet(node, test_func.source_bytes),
            suggestion="Use httptest.Server which automatically picks an available port and shuts down cleanly"
        ))

    return issues


def check_file_io(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect file I/O operations without t.TempDir() (HIGH).

    Patterns: os.Create, os.Open, ioutil.ReadFile, os.ReadFile
    """
    issues = []

    # Check if test uses t.TempDir() (which is acceptable)
    uses_tempdir = has_pattern_in_scope(
        test_func.body_node,
        test_func.source_bytes,
        package_pattern="t",
        method_pattern="TempDir"
    )

    # File I/O patterns to detect
    io_patterns = [
        ("os", "Create"),
        ("os", "Open"),
        ("os", "ReadFile"),
        ("ioutil", "ReadFile"),
        ("os", "WriteFile"),
        ("ioutil", "WriteFile"),
    ]

    for package, method in io_patterns:
        calls = find_function_calls(
            test_func.body_node,
            test_func.source_bytes,
            package_pattern=package,
            method_pattern=method
        )

        for call_node, pkg, meth in calls:
            # If t.TempDir is used, this is less critical but still worth mentioning
            severity = "High" if not uses_tempdir else "Medium"
            suggestion = (
                "Use t.TempDir() to create temporary directories that are automatically cleaned up after the test"
                if not uses_tempdir
                else "Consider using t.TempDir() for better isolation in parallel tests"
            )

            if not uses_tempdir:  # Only report if t.TempDir not used
                issues.append(Issue(
                    file=relative_path(test_func.filepath, project_root),
                    line=call_node.start_point[0] + 1,
                    test_name=test_func.name,
                    issue="File I/O in test may cause issues with parallel execution and cleanup",
                    category="External Dependency",
                    severity=severity,
                    pattern=f"{pkg}.{meth}",
                    code_snippet=get_code_snippet(call_node, test_func.source_bytes),
                    suggestion=suggestion
                ))

    return issues


def analyze_file(filepath: Path, project_root: Path) -> list[Issue]:
    """Analyze a single test file for external dependencies."""
    tree = parse_go_file(filepath)
    if tree is None:
        return []

    with open(filepath, 'rb') as f:
        source_bytes = f.read()

    test_functions = find_test_functions(tree, filepath, source_bytes)

    all_issues = []
    for test_func in test_functions:
        all_issues.extend(check_time_sleep(test_func, project_root))
        all_issues.extend(check_database_connections(test_func, project_root))
        all_issues.extend(check_http_calls(test_func, project_root))
        all_issues.extend(check_web_servers(test_func, project_root))
        all_issues.extend(check_file_io(test_func, project_root))

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
        print(build_json_output("check-external-deps", []))
        return

    # Analyze all test files
    all_issues = []
    for test_file in test_files:
        all_issues.extend(analyze_file(test_file, project_root))

    # Sort issues by file and line number
    all_issues.sort(key=lambda i: (i.file, i.line))

    # Output JSON
    print(build_json_output("check-external-deps", all_issues))


if __name__ == "__main__":
    main()
