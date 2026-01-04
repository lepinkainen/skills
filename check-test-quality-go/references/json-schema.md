# JSON Output Schema Reference

All analysis scripts output JSON in a consistent, machine-readable format.

## Standard Output Format

```json
{
  "script": "script-name",
  "issues": [
    {
      "file": "relative/path/to/file_test.go",
      "line": 42,
      "test_name": "TestFunctionName",
      "issue": "Human-readable description of the issue",
      "category": "External Dependency | Test Complexity | Flaky Tests | Anti-Patterns",
      "severity": "Critical | High | Medium",
      "pattern": "The regex pattern or code pattern that was matched",
      "code_snippet": "The actual line of code that triggered the issue",
      "suggestion": "Actionable advice on how to fix this issue",
      "metrics": {
        "optional_key": "value"
      }
    }
  ],
  "summary": {
    "total_issues": 0,
    "critical_count": 0,
    "high_count": 0,
    "medium_count": 0,
    "files_with_issues": 0
  }
}
```

## Field Descriptions

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `script` | string | Name of the script that generated this output (e.g., "check-external-deps") |
| `issues` | array | List of issue objects detected by the script |
| `summary` | object | Aggregate statistics about the issues found |

### Issue Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | string | Yes | Relative path from project root to the test file (e.g., "internal/handler_test.go") |
| `line` | integer | Yes | Line number where the issue occurs |
| `test_name` | string | Yes | Name of the test function (e.g., "TestUserLogin") |
| `issue` | string | Yes | Clear, concise description of what's wrong |
| `category` | string | Yes | One of: "External Dependency", "Test Complexity", "Flaky Tests", "Anti-Patterns" |
| `severity` | string | Yes | One of: "Critical" (must fix), "High" (should fix), "Medium" (consider fixing) |
| `pattern` | string | Yes | The code pattern detected (useful for filtering/debugging) |
| `code_snippet` | string | Yes | Actual code from the file providing context |
| `suggestion` | string | Yes | How to fix the issue (ideally with code examples) |
| `metrics` | object | No | Optional quantitative data (line count, mock count, complexity score, etc.) |

### Summary Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_issues` | integer | Total number of issues found by this script |
| `critical_count` | integer | Number of Critical severity issues |
| `high_count` | integer | Number of High severity issues |
| `medium_count` | integer | Number of Medium severity issues |
| `files_with_issues` | integer | Number of distinct files with at least one issue |

## Severity Levels

### Critical
Issues that make tests unreliable, slow, or non-functional:
- External database/network dependencies
- `time.Sleep` calls (timing-based synchronization)
- Race conditions
- Goroutines without synchronization

**Action:** Must fix before shipping.

### High
Issues that significantly impact maintainability or reliability:
- Complex tests (>100 lines)
- Excessive setup code
- Too many mocks
- Missing synchronization in concurrent code
- Hardcoded timeouts

**Action:** Should fix soon, blocks code quality improvements.

### Medium
Anti-patterns that reduce test value or create maintenance burden:
- Reflection accessing unexported fields
- Over-verification of mocks
- Missing assertion messages
- Too many assertions per test
- Global state modifications
- Missing cleanup

**Action:** Consider fixing, especially if pattern is widespread.

## Script-Specific Schemas

### check-external-deps.py

**Categories:** External Dependency
**Severities:** Critical

Example metrics object:
```json
"metrics": {
  "dependency_type": "database" | "http" | "file" | "time"
}
```

### check-complexity.py

**Categories:** Test Complexity
**Severities:** High

Example metrics object:
```json
"metrics": {
  "total_lines": 145,
  "setup_lines": 30,
  "mock_count": 6,
  "control_flow_count": 8
}
```

### check-flaky-patterns.py

**Categories:** Flaky Tests
**Severities:** Critical, High

Example metrics object:
```json
"metrics": {
  "pattern_type": "sleep" | "goroutine" | "timeout" | "random" | "time" | "parallel"
}
```

### check-anti-patterns.py

**Categories:** Anti-Patterns
**Severities:** Medium

Example metrics object:
```json
"metrics": {
  "anti_pattern_type": "reflection" | "over_mock" | "missing_message" | "too_many_asserts" | "global_state" | "missing_cleanup",
  "count": 5  // e.g., number of assertions
}
```

## Parsing Examples

### Extract All Issues

```bash
# Combine issues from all scripts
jq -s '[.[].issues[]]' /tmp/*.json > /tmp/all-issues.json
```

### Count by Severity

```bash
# Count critical issues
jq '[.[] | select(.severity == "Critical")] | length' /tmp/all-issues.json

# Count by severity
jq 'group_by(.severity) | map({severity: .[0].severity, count: length})' /tmp/all-issues.json
```

### Filter by File

```bash
# Get all issues in specific file
jq '[.[] | select(.file == "handler_test.go")]' /tmp/all-issues.json
```

### Group by Category

```bash
# Group issues by category
jq 'group_by(.category) | map({category: .[0].category, issues: length})' /tmp/all-issues.json
```

### Deduplicate Issues

```bash
# Remove duplicates (same file + line)
jq 'unique_by([.file, .line])' /tmp/all-issues.json
```

### Get Files with Most Issues

```bash
# Sort files by issue count
jq 'group_by(.file) | map({file: .[0].file, count: length}) | sort_by(-.count)' /tmp/all-issues.json
```

## Empty Results

When no issues are found, scripts output:

```json
{
  "script": "check-external-deps",
  "issues": [],
  "summary": {
    "total_issues": 0,
    "critical_count": 0,
    "high_count": 0,
    "medium_count": 0,
    "files_with_issues": 0
  }
}
```

## Error Handling

If a script encounters errors, it outputs:

```json
{
  "error": "Error category",
  "message": "Detailed error message",
  "script": "script-name"
}
```

Common error categories:
- `"Not a Go project"` - No go.mod file found
- `"No tests found"` - No *_test.go files in project
- `"Missing dependency"` - Required tool not installed (e.g., uv)
- `"Parse error"` - Failed to parse Go source file

## Implementation Notes

- All scripts use tree-sitter for accurate Go AST parsing
- Output is deterministic (sorted by file path, then line number)
- Paths are relative to project root
- Scripts are stateless and can run in parallel
- Dependencies are automatically installed by `uv`
