#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "tree-sitter>=0.23.0",
#   "tree-sitter-go>=0.23.0",
# ]
# ///
"""
Check for test complexity issues in Go tests.

Detects: long tests, excessive mocks, complex logic, poor test names.

This script uses tree-sitter for accurate AST parsing, providing exact line
counts and eliminating false positives from counting patterns in comments.
"""
import sys
import re
from pathlib import Path
from tree_sitter import Query

# Import shared utilities (local module)
sys.path.insert(0, str(Path(__file__).parent))
from test_quality_common import (
    Issue, TestFunction, parse_go_file, find_test_functions, find_test_files,
    count_control_flow_statements, build_json_output, relative_path, GO_LANGUAGE
)


def check_long_functions(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect test functions >100 lines (HIGH).

    Uses exact AST boundaries instead of approximations.
    """
    issues = []

    line_count = test_func.end_line - test_func.start_line

    if line_count > 100:
        # Count additional metrics
        mock_count = count_mock_objects(test_func.body_node, test_func.source_bytes)
        control_flow_count = count_control_flow_statements(
            test_func.body_node,
            test_func.source_bytes
        )

        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=test_func.start_line,
            test_name=test_func.name,
            issue=f"Test function is {line_count} lines (exceeds 100-line guideline)",
            category="Test Complexity",
            severity="High",
            pattern="complexity",
            code_snippet=f"func {test_func.name}(...) {{ ... }}",
            suggestion="Split into multiple focused tests, extract setup to helpers, or use table-driven tests to reduce duplication",
            metrics={
                "total_lines": line_count,
                "mock_count": mock_count,
                "control_flow_statements": control_flow_count
            }
        ))

    return issues


def count_mock_objects(body_node, source_bytes: bytes) -> int:
    """
    Count mock object creations in test body.

    Patterns:
    - new(MockXxx)
    - mock := &MockXxx{}
    - NewMockXxx()
    - &MockXxx{}
    """
    # Query for composite literals with "Mock" in type name
    composite_query = Query(GO_LANGUAGE, """
    (composite_literal
      type: [
        (type_identifier) @type
        (pointer_type
          (type_identifier) @type
        )
      ]
      (#match? @type "^Mock")
    ) @composite
    """)

    # Query for function calls with "Mock" in name
    call_query = Query(GO_LANGUAGE, """
    [
      (call_expression
        function: (identifier) @func
        (#match? @func "^(new|New)Mock")
      ) @call
      (call_expression
        function: (selector_expression
          field: (field_identifier) @method
        )
        (#match? @method "^NewMock")
      ) @call
    ]
    """)

    composite_count = len(composite_query.captures(body_node))
    call_count = len(call_query.captures(body_node))

    return composite_count + call_count


def check_excessive_mocks(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect >4 mock objects per test (HIGH).

    Uses AST parsing for accurate mock counting.
    """
    issues = []

    mock_count = count_mock_objects(test_func.body_node, test_func.source_bytes)

    if mock_count > 4:
        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=test_func.start_line,
            test_name=test_func.name,
            issue=f"Test has {mock_count} mock objects (>4 suggests over-mocking)",
            category="Test Complexity",
            severity="High",
            pattern="complexity",
            code_snippet="Multiple mock objects created",
            suggestion="Consider using real objects when they're simple, or inject fewer dependencies. Too many mocks couples tests to implementation details",
            metrics={"mock_count": mock_count}
        ))

    return issues


def check_complex_logic(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect multiple control flow statements (>3) (MEDIUM).

    Excludes 'if err != nil' patterns which are idiomatic error handling.
    """
    issues = []

    control_flow_count = count_control_flow_statements(
        test_func.body_node,
        test_func.source_bytes
    )

    if control_flow_count > 3:
        issues.append(Issue(
            file=relative_path(test_func.filepath, project_root),
            line=test_func.start_line,
            test_name=test_func.name,
            issue=f"Test has {control_flow_count} control flow statements (>3 indicates complex logic)",
            category="Test Complexity",
            severity="Medium",
            pattern="complexity",
            code_snippet="Multiple for/if/switch statements",
            suggestion="Tests should be simple and linear. Consider using table-driven tests or splitting into multiple focused tests",
            metrics={"control_flow_statements": control_flow_count}
        ))

    return issues


def check_test_names(test_func: TestFunction, project_root: Path) -> list[Issue]:
    """
    Detect generic test names (MEDIUM).

    Poor patterns: TestFoo, TestX, Test1, TestCase1, TestFunc
    """
    issues = []

    poor_patterns = [
        r'^Test[A-Z]?$',          # TestX, Test
        r'^Test[0-9]+$',          # Test1, Test2
        r'^TestCase[0-9]*$',      # TestCase, TestCase1
        r'^TestFunc[0-9]*$',      # TestFunc, TestFunc1
        r'^Test(Foo|Bar)$',       # TestFoo, TestBar
    ]

    for pattern in poor_patterns:
        if re.match(pattern, test_func.name):
            issues.append(Issue(
                file=relative_path(test_func.filepath, project_root),
                line=test_func.start_line,
                test_name=test_func.name,
                issue=f"Test name '{test_func.name}' is too generic and doesn't describe behavior",
                category="Test Complexity",
                severity="Medium",
                pattern="complexity",
                code_snippet=test_func.name,
                suggestion="Use descriptive names that explain what's being tested, e.g., TestUserCreationWithInvalidEmail, TestHandlerReturns404ForMissingResource"
            ))
            break  # Only report once per test

    return issues


def analyze_file(filepath: Path, project_root: Path) -> list[Issue]:
    """Analyze a single test file for complexity issues."""
    tree = parse_go_file(filepath)
    if tree is None:
        return []

    with open(filepath, 'rb') as f:
        source_bytes = f.read()

    test_functions = find_test_functions(tree, filepath, source_bytes)

    all_issues = []
    for test_func in test_functions:
        all_issues.extend(check_long_functions(test_func, project_root))
        all_issues.extend(check_excessive_mocks(test_func, project_root))
        all_issues.extend(check_complex_logic(test_func, project_root))
        all_issues.extend(check_test_names(test_func, project_root))

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
        print(build_json_output("check-complexity", []))
        return

    # Analyze all test files
    all_issues = []
    for test_file in test_files:
        all_issues.extend(analyze_file(test_file, project_root))

    # Sort issues by file and line number
    all_issues.sort(key=lambda i: (i.file, i.line))

    # Output JSON
    print(build_json_output("check-complexity", all_issues))


if __name__ == "__main__":
    main()
