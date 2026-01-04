# Test Quality Patterns - Detailed Reference

This document provides comprehensive details about the patterns detected by each analysis script.

## 1. External Dependencies (Critical Severity)

**Script:** `check-external-deps.py`

Detects tests with real external dependencies that make tests slow, flaky, or environment-dependent.

### Patterns Detected

#### Database Connections
- **Patterns**: `sql.Open`, `gorm.DB`, `postgres://`, `mysql://`
- **Why critical**: Database tests are slow (requires setup), flaky (connection timeouts), and environment-dependent (database must be running)
- **Impact**: Tests cannot run in parallel, fail in CI without database, slow down test suite significantly

**Example issue:**
```go
db, err := sql.Open("postgres", "postgres://localhost/testdb")
```

**Suggested fix:**
```go
// Use sqlmock for unit tests
db, mock, err := sqlmock.New()
defer db.Close()

// Or use test containers for integration tests
container := testcontainers.Postgres(ctx, "postgres:15")
defer container.Terminate(ctx)
```

---

#### HTTP Calls to Real Servers
- **Patterns**: `http.Get`, `http.Post`, `http.Client{}` (excludes `httptest.Server`)
- **Why critical**: Tests fail if external API is down, slow (network latency), and unreliable (timeouts, rate limits)
- **Impact**: Cannot test offline, flaky failures, depends on external service availability

**Example issue:**
```go
resp, err := http.Get("https://api.example.com/users")
```

**Suggested fix:**
```go
// Use httptest.Server for mocking HTTP servers
server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"users": []}`))
}))
defer server.Close()

resp, err := http.Get(server.URL + "/users")
```

---

#### Web Servers on Network Ports
- **Patterns**: `ListenAndServe`, `http.Server{}`
- **Why critical**: Port conflicts in parallel tests, requires network stack, slow startup/shutdown
- **Impact**: Tests cannot run in parallel safely, port conflicts cause failures

**Example issue:**
```go
server := &http.Server{Addr: ":8080"}
go server.ListenAndServe()
```

**Suggested fix:**
```go
// Use httptest.Server which allocates random ports
server := httptest.NewServer(handler)
defer server.Close()

// Test against server.URL (which has the dynamic port)
```

---

#### File I/O Outside Temp Directories
- **Patterns**: `os.Create`, `os.Open`, `ioutil.ReadFile` (when not using `t.TempDir()`)
- **Why critical**: File conflicts in parallel tests, left-over files between runs, permission issues in CI
- **Impact**: Flaky failures from file conflicts, cleanup problems, non-hermetic tests

**Example issue:**
```go
err := os.WriteFile("/tmp/config.json", data, 0644)
```

**Suggested fix:**
```go
// Use t.TempDir() for isolated test directories
tmpDir := t.TempDir() // Automatically cleaned up
configPath := filepath.Join(tmpDir, "config.json")
err := os.WriteFile(configPath, data, 0644)
```

---

#### Time Dependencies (time.Sleep)
- **Patterns**: `time.Sleep`
- **Why CRITICAL**: Indicates timing-based synchronization which is unreliable, slow, and flaky
- **Impact**: Tests are slow (sleep duration added to every run), fail on slower CI machines if timing assumptions break

**Example issue:**
```go
go processData()
time.Sleep(500 * time.Millisecond) // Hope it's done by now
assert.True(t, isComplete)
```

**Suggested fix:**
```go
// Use channels for deterministic synchronization
done := make(chan bool)
go func() {
    processData()
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
    return isComplete()
}, 5*time.Second, 100*time.Millisecond, "processing should complete")
```

---

## 2. Test Complexity (High Severity)

**Script:** `check-complexity.py`

Analyzes test function length, setup complexity, mock count, and logic complexity.

### Patterns Detected

#### Long Test Functions
- **Threshold**: >100 lines per test function
- **Why it matters**: Long tests are hard to understand, maintain, and debug
- **Impact**: When test fails, hard to identify which part broke; difficult for new developers to understand

**Suggested fix:**
- Extract setup logic into helper functions
- Use table-driven tests to reduce duplication
- Split into multiple focused tests (one per behavior)

---

#### Excessive Setup Code
- **Threshold**: >20 lines before first assertion
- **Why it matters**: Indicates overly complex test setup, possibly testing too much at once
- **Impact**: Hard to understand what's being tested, setup failures obscure actual test logic

**Suggested fix:**
```go
// Before: 30 lines of setup in every test
func TestUserValidation(t *testing.T) {
    db := setupDB()
    cache := setupCache()
    logger := setupLogger()
    // ... 20 more lines ...
    user := &User{...}

    err := ValidateUser(user, db, cache, logger)
    assert.NoError(t, err)
}

// After: Extract to helper
func setupTestEnv(t *testing.T) (*DB, *Cache, *Logger) {
    t.Helper()
    db := setupDB()
    cache := setupCache()
    logger := setupLogger()
    return db, cache, logger
}

func TestUserValidation(t *testing.T) {
    db, cache, logger := setupTestEnv(t)
    user := &User{Email: "test@example.com"}

    err := ValidateUser(user, db, cache, logger)
    assert.NoError(t, err)
}
```

---

#### Too Many Mocks
- **Threshold**: >4 mock objects per test
- **Why it matters**: Excessive mocking indicates tight coupling to implementation details
- **Impact**: Tests become brittle (break when implementation changes), hard to maintain, test the mocks not the behavior

**Suggested fix:**
- Use real objects for simple dependencies (e.g., use real struct instead of mocking it)
- Consider if you're testing at the right level (integration vs unit)
- Use test doubles/fakes instead of full mocks when possible

---

#### Complex Logic in Tests
- **Patterns**: Multiple `for`, `if`, `switch` statements in test functions
- **Why it matters**: Tests should be simple and declarative; complex logic suggests poor test design
- **Impact**: Bugs in test logic, hard to verify test correctness, defeats purpose of testing

**Suggested fix:**
```go
// Before: Complex logic in test
func TestProcessing(t *testing.T) {
    for i := 0; i < 10; i++ {
        if i%2 == 0 {
            // test even case
        } else {
            // test odd case
        }
    }
}

// After: Table-driven test
func TestProcessing(t *testing.T) {
    tests := []struct {
        name  string
        input int
        want  string
    }{
        {"even", 2, "even"},
        {"odd", 3, "odd"},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Process(tt.input)
            assert.Equal(t, tt.want, got)
        })
    }
}
```

---

#### Poor Test Names
- **Patterns**: Generic names like "TestFoo", "TestX", "Test1", "TestBasic"
- **Why it matters**: Test names should document behavior; generic names provide no value
- **Impact**: When test fails, name doesn't explain what broke; hard to understand test suite coverage

**Suggested fix:**
```go
// Bad
func TestUser(t *testing.T) { ... }
func Test1(t *testing.T) { ... }

// Good
func TestUserCreationWithInvalidEmailReturnsError(t *testing.T) { ... }
func TestLoginWithExpiredTokenReturnsUnauthorized(t *testing.T) { ... }
```

---

## 3. Flaky Patterns (Critical/High Severity)

**Script:** `check-flaky-patterns.py`

Detects patterns that cause non-deterministic test failures (flaky tests).

### Patterns Detected

#### time.Sleep() Calls
- **Severity**: CRITICAL
- **Why critical**: Timing-based synchronization is inherently unreliable and slow
- **Impact**: Tests fail intermittently on slower machines, add unnecessary delay to test suite

**See External Dependencies section above for details and fixes.**

---

#### Goroutines Without Synchronization
- **Patterns**: `go func()` without `sync.WaitGroup`, channels, or `t.Cleanup`
- **Why critical**: Race conditions, goroutine leaks, non-deterministic test completion
- **Impact**: Tests sometimes pass, sometimes fail; race detector fires; goroutines run after test ends

**Example issue:**
```go
func TestAsync(t *testing.T) {
    go func() {
        processData() // No way to know when this completes
    }()

    // Test ends, goroutine may still be running
    assert.True(t, someCondition)
}
```

**Suggested fix:**
```go
func TestAsync(t *testing.T) {
    var wg sync.WaitGroup
    wg.Add(1)

    go func() {
        defer wg.Done()
        processData()
    }()

    wg.Wait() // Wait for goroutine to complete
    assert.True(t, someCondition)
}
```

---

#### Hardcoded Timeouts
- **Patterns**: `time.Duration` literals in contexts, `context.WithTimeout` with fixed values
- **Why it matters**: Timeouts that work locally may fail in slower CI environments
- **Impact**: Flaky failures in CI, tests that pass locally but fail in pipelines

**Example issue:**
```go
ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
defer cancel()
```

**Suggested fix:**
```go
// Make timeouts configurable or generous
testTimeout := 5 * time.Second
if deadline, ok := t.Deadline(); ok {
    testTimeout = time.Until(deadline) * 0.9 // Use 90% of test deadline
}

ctx, cancel := context.WithTimeout(context.Background(), testTimeout)
defer cancel()
```

---

#### Non-Deterministic Randomness
- **Patterns**: `rand.` without `rand.Seed` or `rand.NewSource`
- **Why it matters**: Tests should be reproducible; random data makes failures impossible to debug
- **Impact**: Cannot reproduce failures, debugging is impossible, undermines test value

**Example issue:**
```go
func TestSorting(t *testing.T) {
    data := generateRandomData(100) // Different every time
    sorted := Sort(data)
    assert.True(t, isSorted(sorted))
}
```

**Suggested fix:**
```go
func TestSorting(t *testing.T) {
    // Use seeded random for deterministic data
    rng := rand.New(rand.NewSource(12345))
    data := generateRandomData(rng, 100)

    sorted := Sort(data)
    assert.True(t, isSorted(sorted))
}
```

---

#### Time-Dependent Assertions
- **Patterns**: `time.Now()` in assertions without mocking
- **Why it matters**: Time-based comparisons are fragile and timing-dependent
- **Impact**: Tests fail depending on when they run, timezone issues, flaky timestamp comparisons

**Example issue:**
```go
func TestUserCreation(t *testing.T) {
    user := CreateUser("john")
    assert.Equal(t, time.Now(), user.CreatedAt) // Will always fail (not equal)
}
```

**Suggested fix:**
```go
// Option 1: Use time ranges
func TestUserCreation(t *testing.T) {
    before := time.Now()
    user := CreateUser("john")
    after := time.Now()

    assert.True(t, user.CreatedAt.After(before) || user.CreatedAt.Equal(before))
    assert.True(t, user.CreatedAt.Before(after) || user.CreatedAt.Equal(after))
}

// Option 2: Mock time (inject clock)
type Clock interface {
    Now() time.Time
}

func TestUserCreation(t *testing.T) {
    fixedTime := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
    clock := &MockClock{CurrentTime: fixedTime}

    user := CreateUser("john", clock)
    assert.Equal(t, fixedTime, user.CreatedAt)
}
```

---

#### Missing Parallelization
- **Patterns**: Tests that could run with `t.Parallel()` but don't
- **Why it matters**: Sequential tests waste CI time, could run 10x faster
- **Impact**: Slow test suite, inefficient resource usage

**Suggested fix:**
```go
func TestIndependentBehavior(t *testing.T) {
    t.Parallel() // Add this if test doesn't use shared state

    // Test logic...
}
```

**When NOT to use `t.Parallel()`:**
- Test modifies global state
- Test uses external resources (database, files)
- Test changes environment variables
- Test has timing requirements

---

## 4. Anti-Patterns (Medium Severity)

**Script:** `check-anti-patterns.py`

Detects Go testing anti-patterns that reduce test value or create maintenance burdens.

### Patterns Detected

#### Reflection Accessing Unexported Fields
- **Patterns**: `reflect.`, `Elem()`, `FieldByName`, `unsafe.Pointer`
- **Why it matters**: Tests should test public API only; testing internals couples tests to implementation
- **Impact**: Tests break when internal implementation changes, defeats encapsulation, brittle tests

**Example issue:**
```go
func TestAuth(t *testing.T) {
    auth := NewAuth()

    // Using reflection to access private field
    v := reflect.ValueOf(auth).Elem()
    field := v.FieldByName("secret")
    field.SetString("test-secret") // Brittle!
}
```

**Suggested fix:**
```go
// Add constructor option for testing
func NewAuth(opts ...AuthOption) *Auth {
    a := &Auth{secret: generateSecret()}
    for _, opt := range opts {
        opt(a)
    }
    return a
}

func WithSecret(secret string) AuthOption {
    return func(a *Auth) {
        a.secret = secret
    }
}

func TestAuth(t *testing.T) {
    auth := NewAuth(WithSecret("test-secret")) // Clean API
}
```

---

#### Over-Verification of Mocks
- **Patterns**: >5 `EXPECT`/`ASSERT` calls per test
- **Why it matters**: Over-verifying mocks tests the mock behavior, not the actual system behavior
- **Impact**: Tests become coupled to implementation order, brittle, hard to refactor

**Example issue:**
```go
func TestService(t *testing.T) {
    mock := NewMockDB(t)

    // Over-verification
    mock.EXPECT().Connect().Times(1)
    mock.EXPECT().BeginTx().Times(1)
    mock.EXPECT().Query("SELECT ...").Times(1)
    mock.EXPECT().Query("UPDATE ...").Times(1)
    mock.EXPECT().Commit().Times(1)
    mock.EXPECT().Close().Times(1)

    service.ProcessUser(mock) // Testing mock sequence, not behavior
}
```

**Suggested fix:**
```go
func TestService(t *testing.T) {
    mock := NewMockDB(t)

    // Verify outcome, not implementation
    mock.EXPECT().SaveUser(gomock.Any()).Return(nil)

    err := service.ProcessUser(mock)
    assert.NoError(t, err)

    // Verify final state, not intermediate steps
}
```

---

#### Missing Assertion Messages
- **Patterns**: `assert.Equal`, `require.NoError` without descriptive messages
- **Why it matters**: When test fails, message should explain what broke
- **Impact**: Debugging failures takes longer, unclear what assertion meant

**Example issue:**
```go
assert.Equal(t, expected, actual) // No context when fails
require.NoError(t, err)           // No context what operation failed
```

**Suggested fix:**
```go
assert.Equal(t, expected, actual, "user email should match input")
require.NoError(t, err, "failed to connect to database")
```

---

#### Too Many Assertions
- **Threshold**: >5 assertions per test
- **Why it matters**: Multiple assertions suggest testing multiple behaviors in one test
- **Impact**: When test fails, unclear which assertion/behavior broke

**Suggested fix:**
```go
// Before: Testing multiple behaviors
func TestUser(t *testing.T) {
    user := CreateUser("john", "john@example.com")
    assert.Equal(t, "john", user.Name)
    assert.Equal(t, "john@example.com", user.Email)
    assert.NotNil(t, user.CreatedAt)
    assert.False(t, user.IsAdmin)
    assert.Nil(t, user.LastLogin)
    assert.Equal(t, "active", user.Status)
}

// After: Split into focused tests
func TestUserCreation_SetsNameAndEmail(t *testing.T) {
    user := CreateUser("john", "john@example.com")
    assert.Equal(t, "john", user.Name)
    assert.Equal(t, "john@example.com", user.Email)
}

func TestUserCreation_DefaultsToNonAdmin(t *testing.T) {
    user := CreateUser("john", "john@example.com")
    assert.False(t, user.IsAdmin)
}

func TestUserCreation_SetsActiveStatus(t *testing.T) {
    user := CreateUser("john", "john@example.com")
    assert.Equal(t, "active", user.Status)
}
```

---

#### Global State
- **Patterns**: Package-level variables modified in tests
- **Why it matters**: Global state causes test interdependencies and ordering issues
- **Impact**: Tests fail when run in parallel, pass/fail depending on execution order, flaky

**Example issue:**
```go
var globalConfig = &Config{Timeout: 30}

func TestWithShortTimeout(t *testing.T) {
    globalConfig.Timeout = 5 // Modifies global state
    // Test logic
}

func TestWithDefaultTimeout(t *testing.T) {
    // Expects globalConfig.Timeout == 30, but might be 5 if previous test ran
}
```

**Suggested fix:**
```go
// Option 1: No global state, pass config explicitly
func TestWithShortTimeout(t *testing.T) {
    config := &Config{Timeout: 5}
    service := NewService(config)
    // Test logic
}

// Option 2: Reset in cleanup
func TestWithShortTimeout(t *testing.T) {
    original := globalConfig.Timeout
    t.Cleanup(func() {
        globalConfig.Timeout = original
    })

    globalConfig.Timeout = 5
    // Test logic
}
```

---

#### Missing Cleanup
- **Patterns**: `os.Setenv` without defer or `t.Setenv`
- **Why it matters**: Environment variables leak between tests
- **Impact**: Tests affect each other, ordering dependencies, flaky failures

**Example issue:**
```go
func TestWithEnv(t *testing.T) {
    os.Setenv("API_KEY", "test-key") // Leaks to other tests
    // Test logic
}
```

**Suggested fix:**
```go
func TestWithEnv(t *testing.T) {
    t.Setenv("API_KEY", "test-key") // Automatically cleaned up
    // Test logic
}

// Or for older Go versions
func TestWithEnv(t *testing.T) {
    originalValue := os.Getenv("API_KEY")
    t.Cleanup(func() {
        if originalValue == "" {
            os.Unsetenv("API_KEY")
        } else {
            os.Setenv("API_KEY", originalValue)
        }
    })

    os.Setenv("API_KEY", "test-key")
    // Test logic
}
```
