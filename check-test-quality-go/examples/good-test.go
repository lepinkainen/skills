package example

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"sync"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestLoginHandler_WithValidCredentials_ReturnsToken demonstrates GOOD test quality
func TestLoginHandler_WithValidCredentials_ReturnsToken(t *testing.T) {
	t.Parallel() // Enable parallel execution

	// GOOD: Use httptest.Server instead of real HTTP calls
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"token": "test-token"}`))
	}))
	defer server.Close()

	// GOOD: Use sqlmock instead of real database
	db, mock, err := sqlmock.New()
	require.NoError(t, err, "failed to create sqlmock")
	defer db.Close()

	mock.ExpectQuery("SELECT (.+) FROM users").
		WillReturnRows(sqlmock.NewRows([]string{"id", "username"}).
			AddRow(1, "testuser"))

	// GOOD: Use t.Setenv for automatic cleanup
	t.Setenv("AUTH_TOKEN", "test-token")

	// GOOD: Use channels for synchronization instead of time.Sleep
	done := make(chan bool)
	go func() {
		defer func() { done <- true }()
		processLogin(db)
	}()

	// Wait for goroutine with timeout
	select {
	case <-done:
		// Success
	case <-time.After(5 * time.Second):
		t.Fatal("timeout waiting for login processing")
	}

	// GOOD: Assertion messages provide context
	resp, err := http.Get(server.URL + "/auth/token")
	require.NoError(t, err, "failed to make auth request")
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode, "should return 200 OK for valid credentials")
}

// TestUserValidation uses table-driven tests (GOOD practice)
func TestUserValidation(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		email   string
		age     int
		wantErr bool
		errMsg  string
	}{
		{
			name:    "valid user",
			email:   "test@example.com",
			age:     25,
			wantErr: false,
		},
		{
			name:    "invalid email format",
			email:   "not-an-email",
			age:     25,
			wantErr: true,
			errMsg:  "invalid email",
		},
		{
			name:    "user too young",
			email:   "test@example.com",
			age:     15,
			wantErr: true,
			errMsg:  "must be 18 or older",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel() // Each sub-test runs in parallel

			user := &User{Email: tt.email, Age: tt.age}
			err := ValidateUser(user)

			if tt.wantErr {
				require.Error(t, err, "expected validation error")
				assert.Contains(t, err.Error(), tt.errMsg, "error message should be descriptive")
			} else {
				require.NoError(t, err, "expected no validation error")
			}
		})
	}
}

// TestConcurrentProcessing demonstrates proper goroutine synchronization
func TestConcurrentProcessing(t *testing.T) {
	t.Parallel()

	// GOOD: Use WaitGroup for synchronizing multiple goroutines
	var wg sync.WaitGroup
	results := make([]int, 0, 10)
	mu := sync.Mutex{}

	for i := 0; i < 10; i++ {
		wg.Add(1)
		i := i // Capture loop variable
		go func() {
			defer wg.Done()
			result := process(i)

			mu.Lock()
			results = append(results, result)
			mu.Unlock()
		}()
	}

	wg.Wait()
	assert.Equal(t, 10, len(results), "should process all items")
}

// TestWithContext demonstrates proper context usage with generous timeout
func TestWithContext(t *testing.T) {
	t.Parallel()

	// GOOD: Use context with reasonable timeout
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	err := performOperation(ctx)
	require.NoError(t, err, "operation should complete within timeout")
}

// TestFileOperations demonstrates using t.TempDir()
func TestFileOperations(t *testing.T) {
	t.Parallel()

	// GOOD: Use t.TempDir() for isolated test directories
	tmpDir := t.TempDir() // Automatically cleaned up

	testFile := tmpDir + "/test.txt"
	err := os.WriteFile(testFile, []byte("test data"), 0644)
	require.NoError(t, err, "failed to write test file")

	// Test file operations...
	data, err := os.ReadFile(testFile)
	require.NoError(t, err, "failed to read test file")
	assert.Equal(t, "test data", string(data), "file content should match")
}

// Helper types and functions

type User struct {
	Email string
	Age   int
}

func ValidateUser(u *User) error {
	// Stub implementation
	return nil
}

func processLogin(db interface{}) {
	// Stub implementation
}

func process(n int) int {
	return n
}

func performOperation(ctx context.Context) error {
	// Stub implementation
	return nil
}
