# Test Quality Report Examples

This document shows example reports generated from test quality analysis.

## Full Analysis Report Example

```
## Test Quality Analysis Report

**Summary:**
- Total issues found: 23
- Critical: 8
- High: 10
- Medium: 5
- Files with issues: 12 / 45 (27%)

---

## Critical Issues

### handler_test.go:45 - TestLoginHandler [External Dependency]

**Issue:** Real HTTP call to external API makes test slow and flaky

**Code:**
```go
resp, err := http.Get("https://api.example.com/auth")
```

**Impact:** Test will fail if API is down or slow. Cannot run offline.

**Suggested fix:**
```go
server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"token": "test-token"}`))
}))
defer server.Close()

resp, err := http.Get(server.URL + "/auth")
```

---

### service_test.go:78 - TestProcessing [Flaky Test]

**Issue:** time.Sleep(500ms) makes test slow and timing-dependent

**Code:**
```go
time.Sleep(500 * time.Millisecond)
```

**Impact:** Test is slow (500ms per run) and may fail on slower machines if processing takes >500ms.

**Suggested fix:**
```go
// Use channels for deterministic synchronization
done := make(chan bool)
go func() {
    service.Process()
    done <- true
}()

select {
case <-done:
    // Success
case <-time.After(5 * time.Second):
    t.Fatal("timeout waiting for processing")
}

// Or use testify/require.Eventually
require.Eventually(t, func() bool {
    return service.IsComplete()
}, 5*time.Second, 100*time.Millisecond, "processing should complete")
```

---

### database_test.go:112 - TestUserRepository [External Dependency]

**Issue:** Real database connection makes test slow and environment-dependent

**Code:**
```go
db, err := sql.Open("postgres", "postgres://localhost:5432/testdb")
```

**Impact:** Test requires PostgreSQL running, fails in CI without database, cannot run in parallel.

**Suggested fix:**
```go
// Option 1: Use sqlmock for unit tests
db, mock, err := sqlmock.New()
defer db.Close()

mock.ExpectQuery("SELECT (.+) FROM users").
    WillReturnRows(sqlmock.NewRows([]string{"id", "name"}).
        AddRow(1, "John"))

// Option 2: Use testcontainers for integration tests
ctx := context.Background()
container, err := postgres.RunContainer(ctx,
    testcontainers.WithImage("postgres:15-alpine"),
)
defer container.Terminate(ctx)

connStr, err := container.ConnectionString(ctx)
db, err := sql.Open("postgres", connStr)
```

---

### async_test.go:234 - TestConcurrentProcessing [Flaky Test]

**Issue:** Goroutines without proper synchronization cause race conditions

**Code:**
```go
go func() {
    processItems(items)
}()

// No synchronization, test may end before goroutine completes
assert.Equal(t, expected, results)
```

**Impact:** Race detector fires, test results non-deterministic, goroutine may leak.

**Suggested fix:**
```go
var wg sync.WaitGroup
wg.Add(1)

go func() {
    defer wg.Done()
    processItems(items)
}()

wg.Wait() // Ensure goroutine completes
assert.Equal(t, expected, results)
```

---

## High Issues

### validator_test.go:120 - TestValidateUser [Test Complexity]

**Issue:** Test function is 145 lines with 6 mocks and complex setup

**Metrics:**
- Total lines: 145
- Setup lines: 30
- Mock count: 6
- Control flow statements: 8

**Impact:** Hard to understand what's being tested. Difficult to maintain. Failures are ambiguous.

**Suggested fix:**
- Extract setup into table-driven test helper
- Consider if all 6 mocks are necessary (use real objects when simple)
- Split into multiple focused tests (one per validation scenario)

**Example refactoring:**
```go
// Before: One giant test
func TestValidateUser(t *testing.T) {
    // 30 lines of setup...
    // 6 mocks...
    // 8 if/for statements...
    // Multiple assertions...
}

// After: Table-driven with focused tests
func TestValidateUser(t *testing.T) {
    tests := []struct {
        name    string
        user    *User
        wantErr bool
    }{
        {"valid user", &User{Email: "test@example.com", Age: 25}, false},
        {"invalid email", &User{Email: "invalid", Age: 25}, true},
        {"underage", &User{Email: "test@example.com", Age: 15}, true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := ValidateUser(tt.user)
            if (err != nil) != tt.wantErr {
                t.Errorf("wanted error: %v, got: %v", tt.wantErr, err)
            }
        })
    }
}
```

---

### processor_test.go:89 - TestProcessData [Test Complexity]

**Issue:** Test has poor naming and excessive control flow

**Metrics:**
- Test name: "TestProcessData" (generic, uninformative)
- Control flow: 5 if statements, 2 for loops
- Lines: 87

**Impact:** When test fails, name doesn't explain what broke. Complex logic makes debugging hard.

**Suggested fix:**
```go
// Replace with descriptive, focused tests
func TestProcessData_WithEmptyInput_ReturnsEmptySlice(t *testing.T) { ... }
func TestProcessData_WithDuplicates_RemovesDuplicates(t *testing.T) { ... }
func TestProcessData_WithInvalidItems_FiltersThemOut(t *testing.T) { ... }
```

---

## Medium Issues

### auth_test.go:34 - TestAuthenticate [Anti-Pattern]

**Issue:** Using reflection to access unexported field

**Code:**
```go
reflect.ValueOf(auth).Elem().FieldByName("secret").SetString("test")
```

**Impact:** Test is coupled to internal implementation. Will break if field is renamed or removed.

**Suggested fix:** Test the public API only. If you need to inject a test secret, add a constructor option:
```go
auth := NewAuthenticator(WithSecret("test-secret"))
```

---

### service_test.go:156 - TestServiceCall [Anti-Pattern]

**Issue:** Over-verification of mock behavior (8 EXPECT calls)

**Code:**
```go
mock.EXPECT().Connect().Times(1)
mock.EXPECT().BeginTx().Times(1)
mock.EXPECT().Query("SELECT ...").Times(1)
mock.EXPECT().Query("UPDATE ...").Times(1)
mock.EXPECT().Query("DELETE ...").Times(1)
mock.EXPECT().Commit().Times(1)
mock.EXPECT().Close().Times(1)
mock.EXPECT().Cleanup().Times(1)
```

**Impact:** Test is brittle (breaks on implementation order changes), tests mock behavior not actual outcomes.

**Suggested fix:** Verify the outcome, not the implementation steps:
```go
// Just verify the important behavior
mock.EXPECT().SaveUser(gomock.Any()).Return(nil)
mock.EXPECT().DeleteSession(gomock.Any()).Return(nil)

err := service.ProcessUser(userID)
assert.NoError(t, err)

// Verify final state rather than intermediate mock calls
```

---

### calculator_test.go:67 - TestCalculations [Anti-Pattern]

**Issue:** Missing assertion messages make failures hard to diagnose

**Code:**
```go
assert.Equal(t, expected, actual)
require.NoError(t, err)
assert.True(t, isValid)
```

**Impact:** When assertion fails, no context about what was being tested.

**Suggested fix:** Add descriptive messages:
```go
assert.Equal(t, expected, actual, "calculation result should match expected value for input %v", input)
require.NoError(t, err, "failed to parse mathematical expression")
assert.True(t, isValid, "result should be within valid range [0, 100]")
```

---

### config_test.go:23 - TestLoadConfig [Anti-Pattern]

**Issue:** Modifying global state without cleanup

**Code:**
```go
func TestLoadConfig(t *testing.T) {
    os.Setenv("CONFIG_PATH", "/tmp/test-config")
    // ... test logic ...
    // Missing cleanup!
}
```

**Impact:** Environment variable leaks to other tests, causing ordering dependencies.

**Suggested fix:**
```go
func TestLoadConfig(t *testing.T) {
    t.Setenv("CONFIG_PATH", "/tmp/test-config") // Auto cleanup
    // ... test logic ...
}

// Or for Go < 1.17
func TestLoadConfig(t *testing.T) {
    original := os.Getenv("CONFIG_PATH")
    t.Cleanup(func() {
        if original == "" {
            os.Unsetenv("CONFIG_PATH")
        } else {
            os.Setenv("CONFIG_PATH", original)
        }
    })

    os.Setenv("CONFIG_PATH", "/tmp/test-config")
    // ... test logic ...
}
```

---

## Recommendations

### Priority 1 (Critical): Fix External Dependencies and Flaky Patterns
**Files affected:** 5 files
**Issues:** 8 critical

Actions:
1. Replace `http.Get/Post` with `httptest.Server` (2 instances in handler_test.go)
2. Replace `sql.Open` with sqlmock or testcontainers (1 instance in database_test.go)
3. Remove all `time.Sleep` calls, use channels or `require.Eventually` (3 instances)
4. Add synchronization to goroutines (2 instances in async_test.go)

**Impact:** Tests will be faster (no sleep delays), more reliable (no external dependencies), and deterministic.

---

### Priority 2 (High): Refactor Complex Tests
**Files affected:** 7 files
**Issues:** 10 high severity

Actions:
1. Split validator_test.go:TestValidateUser (145 lines) into focused table-driven tests
2. Simplify processor_test.go:TestProcessData by reducing control flow
3. Extract common setup code into test helpers
4. Improve test names to be descriptive (5 tests with generic names)
5. Reduce mock count in 3 tests (>4 mocks each)

**Impact:** Tests become easier to understand, maintain, and debug. Clear test names serve as documentation.

---

### Priority 3 (Medium): Address Anti-Patterns
**Files affected:** 4 files
**Issues:** 5 medium severity

Actions:
1. Remove reflection from auth_test.go (add constructor option instead)
2. Reduce mock verification in service_test.go (verify outcomes not steps)
3. Add assertion messages to 2 tests
4. Fix global state cleanup in config_test.go

**Impact:** Tests become less brittle, easier to understand when they fail, and more maintainable.

---

## Summary Statistics

| Category | Critical | High | Medium | Total |
|----------|----------|------|--------|-------|
| External Dependencies | 4 | 0 | 0 | 4 |
| Flaky Tests | 4 | 2 | 0 | 6 |
| Test Complexity | 0 | 8 | 0 | 8 |
| Anti-Patterns | 0 | 0 | 5 | 5 |
| **Total** | **8** | **10** | **5** | **23** |

**Files analyzed:** 45 test files
**Files with issues:** 12 (27%)
**Clean files:** 33 (73%)

**Overall assessment:** Test suite has good coverage but needs attention to reliability (external dependencies, flaky patterns) and maintainability (complex tests). Addressing critical issues will significantly improve test suite stability.
```

## Focused Report Examples

### Example: Only Flaky Tests

When user asks: "Find flaky tests that might be failing intermittently"

```
## Flaky Test Analysis

**Summary:**
- Total flaky patterns found: 6
- Critical: 4 (time.Sleep, unsynchronized goroutines)
- High: 2 (hardcoded timeouts)

---

### service_test.go:78 - TestProcessing
**Pattern:** time.Sleep(500ms)
**Why flaky:** Timing-based synchronization is unreliable
**Fix:** Use channels or require.Eventually

### async_test.go:234 - TestConcurrentProcessing
**Pattern:** go func() without WaitGroup
**Why flaky:** Race condition, goroutine may not complete
**Fix:** Add sync.WaitGroup synchronization

### api_test.go:156 - TestTimeout
**Pattern:** context.WithTimeout(100ms)
**Why flaky:** Hardcoded timeout may be too short in CI
**Fix:** Use generous or configurable timeouts

[... additional issues ...]
```

### Example: Only Critical Issues

```
## Critical Issues Requiring Immediate Attention

Found 8 critical issues across 5 test files.

### External Dependencies (4 issues)
- handler_test.go:45 - HTTP call to real API
- database_test.go:112 - PostgreSQL connection
- cache_test.go:67 - Redis connection
- storage_test.go:89 - File system operations

### Flaky Timing Patterns (4 issues)
- service_test.go:78 - time.Sleep(500ms)
- processor_test.go:123 - time.Sleep(1s)
- worker_test.go:234 - time.Sleep(200ms)
- async_test.go:156 - Unsynchronized goroutines

**Recommended action:** Address these issues before next release.
```

### Example: Clean Test Suite

When no issues are found:

```
## Test Quality Analysis Report

**Summary:**
- Total issues found: 0
- Files analyzed: 45 test files
- All tests passed quality checks! 🎉

**Excellent practices observed:**
- ✅ No external dependencies (using mocks and httptest)
- ✅ No time.Sleep patterns (proper synchronization)
- ✅ Well-structured tests (appropriate length and complexity)
- ✅ Good test names (descriptive and focused)
- ✅ Proper cleanup (using t.Cleanup and t.Setenv)

Your test suite follows Go testing best practices!
```
