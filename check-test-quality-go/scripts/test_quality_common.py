"""
Shared utilities for Go test quality analysis using tree-sitter.

This module provides common functionality for analyzing Go test files with
accurate AST parsing instead of regex-based heuristics.
"""
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import json
import sys
import re

# Tree-sitter imports
from tree_sitter import Language, Parser, Query, Tree, Node, QueryCursor
import tree_sitter_go


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Issue:
    """Represents a single test quality issue."""
    file: str
    line: int
    test_name: str
    issue: str
    category: str
    severity: str
    pattern: str
    code_snippet: str
    suggestion: str
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestFunction:
    """Represents a parsed test function."""
    name: str
    start_line: int
    end_line: int
    body_node: Node
    filepath: Path
    source_bytes: bytes


# ============================================================================
# Tree-sitter Setup
# ============================================================================

# Initialize Go language
GO_LANGUAGE = Language(tree_sitter_go.language())

# Common tree-sitter queries
TEST_FUNCTIONS_QUERY = """
(function_declaration
  name: (identifier) @test.name
  parameters: (parameter_list) @test.params
  body: (block) @test.body
) (#match? @test.name "^Test")
"""

QUALIFIED_CALL_QUERY = """
(call_expression
  function: (selector_expression
    operand: (identifier) @package
    field: (field_identifier) @method
  )
  arguments: (argument_list)? @args
) @call
"""

GOROUTINE_QUERY = """
(go_statement
  (call_expression) @go.call
) @goroutine
"""

DEFER_QUERY = """
(defer_statement
  (call_expression) @defer.call
) @defer
"""

CONTROL_FLOW_QUERY = """
[
  (for_statement) @for
  (if_statement) @if
  (switch_statement) @switch
  (select_statement) @select
] @control_flow
"""


# ============================================================================
# Core Parsing Functions
# ============================================================================

def parse_go_file(filepath: Path) -> Optional[Tree]:
    """
    Parse a Go source file into tree-sitter AST.

    Args:
        filepath: Path to Go source file

    Returns:
        Parsed tree or None if parsing fails
    """
    try:
        with open(filepath, 'rb') as f:
            source_code = f.read()
        parser = Parser(GO_LANGUAGE)
        return parser.parse(source_code)
    except Exception as e:
        print(f"Warning: Failed to parse {filepath}: {e}", file=sys.stderr)
        return None


def find_test_functions(tree: Tree, filepath: Path, source_bytes: bytes) -> List[TestFunction]:
    """
    Extract all test functions from a parsed Go file.

    Args:
        tree: Parsed tree-sitter AST
        filepath: Path to the source file
        source_bytes: Raw source code bytes

    Returns:
        List of TestFunction objects
    """
    query = Query(GO_LANGUAGE, TEST_FUNCTIONS_QUERY)
    cursor = QueryCursor(query)
    captures_dict = cursor.captures(tree.root_node)

    test_functions = []

    # Match test names with their bodies
    test_names = captures_dict.get("test.name", [])
    test_bodies = captures_dict.get("test.body", [])

    # Assuming names and bodies are in matching order
    for i, (name_node, body_node) in enumerate(zip(test_names, test_bodies)):
        test_functions.append(TestFunction(
            name=get_node_text(name_node, source_bytes),
            start_line=body_node.start_point[0] + 1,
            end_line=body_node.end_point[0] + 1,
            body_node=body_node,
            filepath=filepath,
            source_bytes=source_bytes
        ))

    return test_functions


def get_node_text(node: Node, source_bytes: bytes) -> str:
    """Extract text content from an AST node."""
    return source_bytes[node.start_byte:node.end_byte].decode('utf-8')


def get_code_snippet(node: Node, source_bytes: bytes, max_length: int = 100) -> str:
    """
    Extract code snippet from AST node.

    Args:
        node: AST node
        source_bytes: Raw source code bytes
        max_length: Maximum snippet length

    Returns:
        Formatted code snippet
    """
    snippet = get_node_text(node, source_bytes)

    # Collapse to single line if multiline
    if '\n' in snippet:
        snippet = snippet.split('\n')[0] + '...'

    # Truncate if too long
    if len(snippet) > max_length:
        snippet = snippet[:max_length] + '...'

    return snippet.strip()


# ============================================================================
# Query Helper Functions
# ============================================================================

def find_function_calls(
    body_node: Node,
    source_bytes: bytes,
    package_pattern: str,
    method_pattern: Optional[str] = None
) -> List[Tuple[Node, str, str]]:
    """
    Find all function calls matching package.method pattern.

    Args:
        body_node: AST node to search within
        source_bytes: Raw source code bytes
        package_pattern: Package name or regex pattern
        method_pattern: Method name or regex pattern (None = match all)

    Returns:
        List of (call_node, package_name, method_name) tuples
    """
    query = Query(GO_LANGUAGE, QUALIFIED_CALL_QUERY)
    cursor = QueryCursor(query)
    captures_dict = cursor.captures(body_node)

    results = []

    # Get all captured nodes
    call_nodes = captures_dict.get("call", [])
    package_nodes = captures_dict.get("package", [])
    method_nodes = captures_dict.get("method", [])

    # Match them up (assuming they're in corresponding order)
    for call_node, package_node, method_node in zip(call_nodes, package_nodes, method_nodes):
        package = get_node_text(package_node, source_bytes)
        method = get_node_text(method_node, source_bytes)

        # Match package pattern
        if re.match(f"^{package_pattern}$", package):
            # Match method pattern if specified
            if method_pattern is None or re.match(f"^{method_pattern}$", method):
                results.append((call_node, package, method))

    return results


def has_pattern_in_scope(
    body_node: Node,
    source_bytes: bytes,
    package_pattern: str,
    method_pattern: Optional[str] = None
) -> bool:
    """
    Check if a function call pattern exists in scope.

    Args:
        body_node: AST node to search within
        source_bytes: Raw source code bytes
        package_pattern: Package name pattern
        method_pattern: Method name pattern (None = match all)

    Returns:
        True if pattern found in scope
    """
    return len(find_function_calls(body_node, source_bytes, package_pattern, method_pattern)) > 0


def find_goroutines(body_node: Node) -> List[Node]:
    """Find all goroutine launches in scope."""
    query = Query(GO_LANGUAGE, GOROUTINE_QUERY)
    cursor = QueryCursor(query)
    captures_dict = cursor.captures(body_node)
    return captures_dict.get("goroutine", [])


def find_defer_statements(body_node: Node) -> List[Node]:
    """Find all defer statements in scope."""
    query = Query(GO_LANGUAGE, DEFER_QUERY)
    cursor = QueryCursor(query)
    captures_dict = cursor.captures(body_node)
    return captures_dict.get("defer", [])


def count_control_flow_statements(body_node: Node, source_bytes: bytes) -> int:
    """
    Count control flow statements (for, if, switch, select).

    Excludes 'if err != nil' patterns which are idiomatic error handling.

    Args:
        body_node: AST node to analyze
        source_bytes: Raw source code bytes

    Returns:
        Count of non-error-handling control flow statements
    """
    query = Query(GO_LANGUAGE, CONTROL_FLOW_QUERY)
    cursor = QueryCursor(query)
    captures_dict = cursor.captures(body_node)

    count = 0

    # Count all control flow statements, excluding error checks
    for capture_name, nodes in captures_dict.items():
        for node in nodes:
            # Skip if statements that are error checks
            if capture_name == "if":
                node_text = get_node_text(node, source_bytes)
                if re.search(r'\berr\s*!=\s*nil\b', node_text):
                    continue
            count += 1

    return count


# ============================================================================
# File Discovery
# ============================================================================

def find_test_files(project_root: Path) -> List[Path]:
    """
    Find all Go test files in project.

    Args:
        project_root: Root directory to search

    Returns:
        List of paths to *_test.go files
    """
    return sorted([
        p for p in project_root.rglob("*_test.go")
        if p.is_file()
    ])


# ============================================================================
# JSON Output
# ============================================================================

def build_json_output(script_name: str, issues: List[Issue]) -> str:
    """
    Build JSON output matching original bash script format.

    Args:
        script_name: Name of the script (e.g., "check-external-deps")
        issues: List of Issue objects

    Returns:
        Formatted JSON string
    """
    # Count severities
    critical = sum(1 for i in issues if i.severity == "Critical")
    high = sum(1 for i in issues if i.severity == "High")
    medium = sum(1 for i in issues if i.severity == "Medium")

    # Count unique files
    unique_files = len(set(i.file for i in issues))

    # Build output structure
    output = {
        "script": script_name,
        "issues": [asdict(i) for i in issues],
        "summary": {
            "total_issues": len(issues),
            "critical_count": critical,
            "high_count": high,
            "medium_count": medium,
            "files_with_issues": unique_files
        }
    }

    return json.dumps(output, indent=2)


# ============================================================================
# Helper Functions
# ============================================================================

def relative_path(filepath: Path, project_root: Path) -> str:
    """Get relative path from project root."""
    try:
        return str(filepath.relative_to(project_root))
    except ValueError:
        return str(filepath)
