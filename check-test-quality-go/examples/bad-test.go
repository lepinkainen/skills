package example

import (
	"database/sql"
	"net/http"
	"os"
	"testing"
	"time"

	_ "github.com/lib/pq"
)

// TestLoginHandler demonstrates MULTIPLE quality issues
func TestLoginHandler(t *testing.T) {
	// ISSUE: Real database connection (External Dependency - Critical)
	db, err := sql.Open("postgres", "postgres://localhost:5432/testdb")
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	// ISSUE: Real HTTP call (External Dependency - Critical)
	resp, err := http.Get("https://api.example.com/auth/token")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()

	// ISSUE: time.Sleep for synchronization (Flaky Pattern - Critical)
	go func() {
		processLogin(db)
	}()
	time.Sleep(500 * time.Millisecond) // Hope it finishes in time

	// ISSUE: Missing assertion message (Anti-Pattern - Medium)
	if resp.StatusCode != 200 {
		t.Fatal("wrong status")
	}

	// ISSUE: Global state modification without cleanup (Anti-Pattern - Medium)
	os.Setenv("AUTH_TOKEN", "test-token")

	// Test continues for many more lines...
	// ISSUE: Test is >100 lines (Complexity - High)
}

// TestX demonstrates poor naming (Complexity - High)
func TestX(t *testing.T) {
	// Generic name provides no documentation value
	result := process(10)
	if result != 10 {
		t.Fatal("failed")
	}
}

func process(n int) int {
	return n
}

func processLogin(db *sql.DB) {
	// Stub implementation
}
