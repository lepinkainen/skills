# Test Quality Examples

This directory contains example Go test files demonstrating good and bad testing practices.

## Files

### bad-test.go

Demonstrates **common test quality issues**:

1. **External Dependencies (Critical)**
   - Real database connection with `sql.Open`
   - Real HTTP call to external API
   - File system operations without `t.TempDir()`

2. **Flaky Patterns (Critical)**
   - `time.Sleep()` for synchronization
   - Goroutines without proper synchronization

3. **Anti-Patterns (Medium)**
   - Missing assertion messages
   - Global state modification without cleanup (`os.Setenv`)
   - Poor test naming (`TestX`)

4. **Test Complexity (High)**
   - Long test function (would be >100 lines in real code)
   - Generic test names

**Use this file as a reference for what NOT to do.**

---

### good-test.go

Demonstrates **best practices and solutions**:

1. **No External Dependencies**
   - Uses `httptest.Server` instead of real HTTP calls
   - Uses `sqlmock` instead of real database
   - Uses `t.TempDir()` for file operations

2. **Reliable Patterns**
   - Channels for goroutine synchronization
   - `sync.WaitGroup` for multiple goroutines
   - Generous context timeouts
   - Proper error handling with `require`

3. **Good Test Design**
   - Descriptive test names (e.g., `TestLoginHandler_WithValidCredentials_ReturnsToken`)
   - Table-driven tests for multiple scenarios
   - `t.Parallel()` for independent tests
   - Assertion messages providing context

4. **Proper Cleanup**
   - `t.Setenv()` for automatic environment variable cleanup
   - `defer` statements for resource cleanup
   - `t.TempDir()` for automatic directory cleanup

**Use this file as a reference for high-quality test patterns.**

---

## Comparing the Examples

| Aspect | bad-test.go | good-test.go |
|--------|-------------|--------------|
| **HTTP calls** | Real API call | `httptest.Server` |
| **Database** | Real PostgreSQL | `sqlmock` |
| **Synchronization** | `time.Sleep` | Channels, WaitGroup |
| **Test names** | Generic (TestX) | Descriptive (Test...When...Should...) |
| **Assertions** | No messages | Clear messages |
| **Cleanup** | Manual `os.Setenv` | `t.Setenv()` |
| **Parallelization** | None | `t.Parallel()` |
| **Structure** | Single long test | Table-driven, focused tests |

## Running These Examples

These files are for reference only and won't compile without additional dependencies. They demonstrate patterns to look for and apply in your own tests.

To see how the analysis scripts would flag issues:

```bash
# From the skill root directory
uv run scripts/check-external-deps.py examples/
uv run scripts/check-flaky-patterns.py examples/
uv run scripts/check-anti-patterns.py examples/
uv run scripts/check-complexity.py examples/
```

The scripts should identify multiple issues in `bad-test.go` and zero issues in `good-test.go`.
