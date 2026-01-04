---
name: check-test-quality-go
description: Analyze Go test files (*_test.go) for quality issues, anti-patterns, and code smells. This is a Go-specific tool that checks for external dependencies, complexity, flaky patterns, and testing anti-patterns. Use when users ask to check Go test quality, analyze Go tests for issues, find test anti-patterns in Go code, find flaky Go tests, or improve Go test reliability.
version: 0.1.0
---

# Check Go Test Quality

## Purpose

Analyze Go test files to identify quality issues, anti-patterns, and code smells that make tests flaky, slow, complex, or unmaintainable. Provide actionable refactoring suggestions to improve test reliability and clarity.

**Test quality** encompasses:
- **Reliability**: Tests produce consistent results (not flaky)
- **Speed**: Tests run quickly without external dependencies
- **Clarity**: Tests are readable and maintainable
- **Correctness**: Tests verify behavior, not implementation details

## When to Use This Skill

Use this skill when users ask to:
- Check test quality or analyze tests for issues
- Find flaky or unreliable tests
- Identify test anti-patterns or code smells
- Improve test maintainability
- Detect tests with external dependencies
- Find overly complex tests

## Analysis Categories

This skill provides four Python scripts that analyze Go test files and output structured JSON. Each script focuses on a specific category of test quality issues.

### 1. External Dependencies (Critical)

**Script:** `check-external-deps.py`

Look for patterns indicating real external dependencies:
- Database connections (`sql.Open`, `gorm.DB`, connection strings)
- HTTP calls to real servers (`http.Get`, `http.Post`, `http.Client{}`)
- Web servers on network ports (`ListenAndServe`, `http.Server{}`)
- File I/O outside temp directories (`os.Create`, `os.Open` without `t.TempDir()`)
- Time dependencies (`time.Sleep` - indicates flaky timing-based tests)

**Why critical:** External dependencies make tests slow, flaky, and environment-dependent. Tests fail in CI, cannot run offline, and cannot run in parallel safely.

**Common fixes:** Use mocks/fakes, `httptest.Server` for HTTP testing, test containers for integration tests, `t.TempDir()` for file operations, and replace `time.Sleep` with channels, WaitGroups, or `require.Eventually`.

*See `references/pattern-details.md` for detailed pattern descriptions and fix examples.*

### 2. Test Complexity (High)

**Script:** `check-complexity.py`

Analyze test structure for complexity indicators:
- Long test functions (>100 lines)
- Excessive setup code (>20 lines before first assertion)
- Too many mocks (>4 mock objects per test)
- Complex logic (multiple `for`, `if`, `switch` statements in tests)
- Poor test names (generic names like "TestFoo", "TestX")

**Why it matters:** Complex tests are hard to understand, maintain, and debug. Excessive mocking indicates coupling to implementation. Generic names provide no documentation value.

**Common fixes:** Extract setup to table-driven test helpers, reduce mocking by using real objects when simple, split complex tests into focused tests, use descriptive test names.

*See `references/pattern-details.md` for detailed guidance and refactoring examples.*

### 3. Flaky Patterns (Critical/High)

**Script:** `check-flaky-patterns.py`

Detect patterns causing non-deterministic test failures:
- `time.Sleep()` calls (timing-based synchronization)
- Goroutines without synchronization (`go func()` without WaitGroup/channels)
- Hardcoded timeouts (`context.WithTimeout` with fixed durations)
- Non-deterministic randomness (`rand.` without seeded source)
- Time-dependent assertions (`time.Now()` without mocking)
- Missing parallelization (tests that could use `t.Parallel()` but don't)

**Why critical:** Flaky tests fail intermittently, undermining trust in the test suite. Timing-based synchronization breaks on slower CI machines. Race conditions cause unpredictable failures.

**Common fixes:** Use channels/WaitGroups for async operations, mock time with fixed values, use seeded random generators, add synchronization primitives, enable `t.Parallel()` for independent tests.

*See `references/pattern-details.md` for comprehensive flaky pattern examples.*

### 4. Anti-Patterns (Medium)

**Script:** `check-anti-patterns.py`

Identify testing anti-patterns:
- Reflection accessing unexported fields (`reflect.`, `FieldByName`, `unsafe.Pointer`)
- Over-verification of mocks (>5 `EXPECT`/`ASSERT` calls per test)
- Missing assertion messages (`assert.Equal` without descriptive messages)
- Too many assertions (>5 assertions per test)
- Global state modifications (package-level variables modified in tests)
- Missing cleanup (`os.Setenv` without defer or `t.Setenv`)

**Why it matters:** Testing unexported internals couples tests to implementation. Over-verifying mocks tests mock behavior, not actual behavior. Missing messages make failures hard to diagnose.

**Common fixes:** Test public API only, verify behavior/outcomes not mock sequences, add descriptive assertion messages, split tests with multiple assertions, use `t.Setenv` and `t.Cleanup`.

*See `references/pattern-details.md` for anti-pattern details and solutions.*

## Workflow Instructions

Follow these steps when analyzing Go test quality:

### Step 1: Verify Go Project

Confirm this is a Go project with test files:

```bash
# Check for go.mod
if [ ! -f "go.mod" ]; then
  echo "Error: Not a Go project (no go.mod found)"
  exit 1
fi

# Find test files
test_files=$(fd -e go -g '*_test.go' . 2>/dev/null || find . -name '*_test.go' 2>/dev/null)

if [ -z "$test_files" ]; then
  echo "No Go test files (*_test.go) found in this project"
  exit 0
fi

test_count=$(echo "$test_files" | wc -l)
echo "Found $test_count test files to analyze"
```

### Step 2: Run Analysis Scripts

Execute all four scripts to gather comprehensive quality data. Run in parallel for speed:

```bash
# Parallel execution
uv run ${CLAUDE_SKILL_ROOT}/scripts/check-external-deps.py . > /tmp/external-deps.json &
PID1=$!

uv run ${CLAUDE_SKILL_ROOT}/scripts/check-complexity.py . > /tmp/complexity.json &
PID2=$!

uv run ${CLAUDE_SKILL_ROOT}/scripts/check-flaky-patterns.py . > /tmp/flaky.json &
PID3=$!

uv run ${CLAUDE_SKILL_ROOT}/scripts/check-anti-patterns.py . > /tmp/anti-patterns.json &
PID4=$!

# Wait for all to complete
wait $PID1 $PID2 $PID3 $PID4
```

Alternatively, run sequentially:

```bash
uv run ${CLAUDE_SKILL_ROOT}/scripts/check-external-deps.py .
uv run ${CLAUDE_SKILL_ROOT}/scripts/check-complexity.py .
uv run ${CLAUDE_SKILL_ROOT}/scripts/check-flaky-patterns.py .
uv run ${CLAUDE_SKILL_ROOT}/scripts/check-anti-patterns.py .
```

### Step 3: Parse JSON Output

Each script outputs JSON in a consistent format. Collect and parse results:

```bash
# Extract all issues from all scripts
jq -s '[.[].issues[]]' /tmp/*.json > /tmp/all-issues.json

# Count by severity
jq '[.[] | select(.severity == "Critical")] | length' /tmp/all-issues.json
```

*See `references/json-schema.md` for complete JSON schema documentation and parsing examples.*

### Step 4: Synthesize Findings

Combine results from all scripts and organize for presentation:

1. **Deduplicate issues**: Same file/line may appear in multiple scripts (e.g., `time.Sleep` detected by both external-deps and flaky-patterns)
2. **Group by severity**: Critical → High → Medium
3. **Sort by file and line**: Organize issues by location
4. **Aggregate statistics**: Total issues, files affected, severity breakdown

**Deduplication logic:**
```bash
# Remove duplicates (same file + line, keep highest severity)
jq 'unique_by([.file, .line])' /tmp/all-issues.json
```

**Severity prioritization:**
1. **Critical**: External dependencies, `time.Sleep`, race conditions
2. **High**: Complex tests (>100 lines), missing synchronization
3. **Medium**: Anti-patterns (reflection, over-mocking, global state)

### Step 5: Generate Formatted Report

Present findings in a clear, actionable format organized by severity. Include:

- Summary statistics (total issues, breakdown by severity, files affected)
- Critical issues first (external dependencies, flaky patterns)
- High issues second (complexity)
- Medium issues third (anti-patterns)
- Code snippets showing the problem
- Impact explanation (why it matters)
- Suggested fixes with code examples
- Prioritized recommendations

*See `references/report-examples.md` for complete report templates and examples.*

**Report structure:**
```
## Test Quality Analysis Report

**Summary:**
- Total issues: [count]
- Critical: [count]
- High: [count]
- Medium: [count]
- Files with issues: [count] / [total] ([percentage]%)

---

## Critical Issues

### [file]:[line] - [test_name] [category]
**Issue:** [description]
**Code:** [snippet]
**Impact:** [why it matters]
**Suggested fix:** [solution with code]

---

## Recommendations

1. **Priority 1 (Critical):** [action items]
2. **Priority 2 (High):** [action items]
3. **Priority 3 (Medium):** [action items]
```

## Example Usage

**User query:**
> "Check my Go tests for quality issues"

**Expected workflow:**
1. Verify this is a Go project with test files
2. Run all 4 scripts in parallel
3. Collect and parse JSON outputs
4. Deduplicate issues (same file+line)
5. Group by severity (Critical, High, Medium)
6. Present formatted report with code context and suggestions

**User query:**
> "Find flaky tests that might be failing intermittently"

**Expected workflow:**
1. Focus on `check-flaky-patterns.py` script
2. Highlight `time.Sleep`, goroutines without sync, and non-deterministic patterns
3. Explain why each pattern causes flakiness
4. Provide specific fixes (channels, WaitGroups, `require.Eventually`)

## Error Handling

Handle these error cases gracefully:

### Not a Go Project
```bash
if [ ! -f "go.mod" ]; then
  echo '{"error": "Not a Go project", "message": "No go.mod file found"}' | jq .
  exit 0  # Not an error, just not applicable
fi
```

### No Test Files Found
```bash
test_files=$(fd -g '*_test.go' . 2>/dev/null)
if [ -z "$test_files" ]; then
  echo '{"error": "No tests found", "message": "No *_test.go files in project"}' | jq .
  exit 0
fi
```

### Script Execution Failure
```bash
# Dependencies are automatically installed by uv
# If uv is not available, install it first:
if ! command -v uv &> /dev/null; then
  echo '{"error": "Missing dependency", "message": "uv not installed. Install from https://docs.astral.sh/uv/"}' | jq .
  exit 1
fi
```

### Empty Results
If all scripts return zero issues, congratulate the user on having high-quality tests! Present a positive message highlighting good practices observed.

## Additional Resources

- **Pattern Details**: `references/pattern-details.md` - Comprehensive documentation of all detected patterns with examples and fixes
- **JSON Schema**: `references/json-schema.md` - Complete JSON output format, field descriptions, and parsing examples
- **Report Examples**: `references/report-examples.md` - Full example reports showing different scenarios and output formats

## Notes

- Scripts are stateless and can run in parallel
- Output is deterministic (sorted by file/line)
- Scripts use tree-sitter for accurate Go AST parsing
- Dependencies (tree-sitter, tree-sitter-go) are automatically installed by `uv`
- All paths are relative to project root
- Scripts work with any Go project structure
