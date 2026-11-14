// SPDX-License-Identifier: MPL-2.0
package store

import (
	"context"
	"database/sql"
	"errors"
	"testing"
	"time"

	"github.com/anothel/anopki/service/internal/domain"
)

func TestPostgresIntegrationOutboxCompareAndSwap(t *testing.T) {
	testOutboxCompareAndSwap(t, newPostgresTestRepository(t))
}

func TestSQLiteOutboxCompareAndSwap(t *testing.T) {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	if err := ApplyInitialMigration(context.Background(), db, "sqlite"); err != nil {
		t.Fatal(err)
	}
	testOutboxCompareAndSwap(t, NewSQLStore(db))
}

// Exercise NULL and non-NULL deadlines and stale-node writes through the real
// SQL repository; ordinary status updates do not exercise the dispatcher's CAS.
func testOutboxCompareAndSwap(t *testing.T, repo Repository) {
	t.Helper()
	ctx := context.Background()
	now := time.Date(2026, time.January, 2, 3, 4, 5, 0, time.UTC)
	pending := domain.OutboxMessage{
		ID: "outbox-cas", Type: "certificate.expiring", PayloadJSON: `{}`,
		Status: domain.OutboxPending, AvailableAt: now, MaxAttempts: 4,
		CreatedAt: now, UpdatedAt: now,
	}
	if err := repo.CreateOutboxMessage(ctx, pending); err != nil {
		t.Fatal(err)
	}
	claimed := pending
	claimed.Status = domain.OutboxProcessing
	claimed.ProcessingDeadlineAt = now.Add(time.Minute)
	claimed.UpdatedAt = now.Add(time.Second)
	if err := repo.UpdateOutboxMessageIfCurrent(ctx, claimed, pending); err != nil {
		t.Fatalf("claim NULL deadline: %v", err)
	}
	if err := repo.UpdateOutboxMessageIfCurrent(ctx, claimed, pending); !errors.Is(err, domain.ErrInvalidTransition) {
		t.Fatalf("stale pending claim = %v, want invalid transition", err)
	}
	completed := claimed
	completed.Status = domain.OutboxCompleted
	completed.ProcessingDeadlineAt = time.Time{}
	completed.UpdatedAt = now.Add(2 * time.Second)
	wrongDeadline := claimed
	wrongDeadline.ProcessingDeadlineAt = now.Add(2 * time.Minute)
	if err := repo.UpdateOutboxMessageIfCurrent(ctx, completed, wrongDeadline); !errors.Is(err, domain.ErrInvalidTransition) {
		t.Fatalf("mismatched lease = %v, want invalid transition", err)
	}
	if err := repo.UpdateOutboxMessageIfCurrent(ctx, completed, claimed); err != nil {
		t.Fatalf("complete non-NULL deadline: %v", err)
	}
	if err := repo.UpdateOutboxMessageIfCurrent(ctx, completed, claimed); !errors.Is(err, domain.ErrInvalidTransition) {
		t.Fatalf("stale completion = %v, want invalid transition", err)
	}
	stored, err := repo.GetOutboxMessage(ctx, pending.ID)
	if err != nil || stored.Status != domain.OutboxCompleted || !stored.ProcessingDeadlineAt.IsZero() {
		t.Fatalf("stored completion = %#v, %v", stored, err)
	}
}
