// SPDX-License-Identifier: MPL-2.0
// Adapted from frozen Community 49142ff50f5b37ba142d18cf61b60d8b287bdb49.
// Scope: application-node lease recovery, not PostgreSQL-primary failover.
package lifecycle

import (
	"context"
	"database/sql"
	"errors"
	"os"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anothel/anopki/service/internal/corecli"
	"github.com/anothel/anopki/service/internal/domain"
	"github.com/anothel/anopki/service/internal/store"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/stdlib"
)

func openPostgresFailoverRepositories(t *testing.T) (store.Repository, store.Repository) {
	t.Helper()
	dsn := strings.TrimSpace(os.Getenv("ANOPKI_POSTGRES_FAILOVER_DSN"))
	if dsn == "" {
		t.Skip("set ANOPKI_POSTGRES_FAILOVER_DSN to run PostgreSQL multi-node failover integration tests")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	config, err := pgx.ParseConfig(dsn)
	if err != nil {
		t.Fatal("invalid PostgreSQL failover configuration (details omitted)")
	}
	bootstrap := sql.OpenDB(stdlib.GetConnector(*config.Copy()))
	schema := "anopki_phase2_" + strings.ReplaceAll(UUIDGenerator{}.NewID(), "-", "")
	identifier := pgx.Identifier{schema}.Sanitize()
	if _, err := bootstrap.ExecContext(ctx, "CREATE SCHEMA "+identifier); err != nil {
		bootstrap.Close()
		t.Fatal("create isolated PostgreSQL schema failed (details omitted)")
	}
	// Registered before node cleanup: both pools close before the owned schema drops.
	t.Cleanup(func() {
		defer bootstrap.Close()
		cleanupCtx, cleanupCancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cleanupCancel()
		if _, err := bootstrap.ExecContext(cleanupCtx, "DROP SCHEMA "+identifier+" CASCADE"); err != nil {
			t.Error("drop owned PostgreSQL schema failed (details omitted)")
		}
	})
	open := func() *sql.DB {
		nodeConfig := config.Copy()
		nodeConfig.RuntimeParams["search_path"] = schema
		db := sql.OpenDB(stdlib.GetConnector(*nodeConfig))
		db.SetMaxOpenConns(4)
		db.SetMaxIdleConns(4)
		t.Cleanup(func() { db.Close() })
		if err := db.PingContext(ctx); err != nil {
			t.Fatal("connect PostgreSQL node failed (details omitted)")
		}
		var actualSchema string
		var version int
		if err := db.QueryRowContext(ctx, "SELECT current_schema(), current_setting('server_version_num')::int").Scan(&actualSchema, &version); err != nil {
			t.Fatal("query PostgreSQL node identity failed (details omitted)")
		}
		if actualSchema != schema || version/10000 != 16 {
			t.Fatal("isolated schema and PostgreSQL 16 are required")
		}
		return db
	}
	firstDB, secondDB := open(), open()
	var firstPID, secondPID int
	if err := firstDB.QueryRowContext(ctx, "SELECT pg_backend_pid()").Scan(&firstPID); err != nil {
		t.Fatal("query first node connection failed (details omitted)")
	}
	if err := secondDB.QueryRowContext(ctx, "SELECT pg_backend_pid()").Scan(&secondPID); err != nil {
		t.Fatal("query second node connection failed (details omitted)")
	}
	if firstPID == secondPID {
		t.Fatal("nodes must use independent PostgreSQL connections")
	}
	if err := store.ApplyInitialMigration(ctx, firstDB, "pgx"); err != nil {
		t.Fatal("apply isolated PostgreSQL migration failed (details omitted)")
	}
	if err := store.CheckInitialMigration(ctx, secondDB, "pgx"); err != nil {
		t.Fatal("check migration from second node failed (details omitted)")
	}

	return store.NewSQLStore(firstDB), store.NewSQLStore(secondDB)
}

func TestPostgresMultiNodeIssuanceFailoverIntegration(t *testing.T) {
	ctx := context.Background()
	firstRepo, secondRepo := openPostgresFailoverRepositories(t)
	base := time.Date(2026, time.January, 2, 3, 4, 5, 0, time.UTC)

	firstIssuer := &fakeIssuer{}
	firstService := New(firstRepo, firstIssuer, fixedClock{now: base}, UUIDGenerator{})
	enrollment := createPendingEnrollment(t, ctx, firstService)
	if _, err := firstService.ApproveEnrollment(ctx, "approver", enrollment.ID); err != nil {
		t.Fatalf("ApproveEnrollment: %v", err)
	}

	firstClaim, shouldSign, err := firstService.claimIssuanceAttempt(ctx, enrollment.ID, base)
	if err != nil || !shouldSign {
		t.Fatalf("first claim = (%#v, %t, %v), want signing claim", firstClaim, shouldSign, err)
	}

	activeNode := New(secondRepo, &fakeIssuer{}, fixedClock{now: base.Add(time.Minute)}, UUIDGenerator{})
	if _, _, err := activeNode.claimIssuanceAttempt(ctx, enrollment.ID, base.Add(time.Minute)); !errors.Is(err, domain.ErrInvalidTransition) {
		t.Fatalf("active-lease second claim error = %v, want %v", err, domain.ErrInvalidTransition)
	}

	failoverTime := base.Add(defaultIssuanceSigningLease + time.Minute)
	failoverIssuer := &fakeIssuer{}
	failoverNode := New(secondRepo, failoverIssuer, fixedClock{now: failoverTime}, UUIDGenerator{})
	secondClaim, shouldSign, err := failoverNode.claimIssuanceAttempt(ctx, enrollment.ID, failoverTime)
	if err != nil || !shouldSign {
		t.Fatalf("expired-lease takeover = (%#v, %t, %v), want takeover", secondClaim, shouldSign, err)
	}
	if !secondClaim.LeaseExpiresAt.After(firstClaim.LeaseExpiresAt) {
		t.Fatalf("takeover lease = %s, first lease = %s", secondClaim.LeaseExpiresAt, firstClaim.LeaseExpiresAt)
	}

	result := corecli.IssueResult{
		CertificatePEM:  "issued:postgres-failover",
		SerialNumber:    "serial-postgres-failover",
		Subject:         "CN=postgres-failover",
		NotBefore:       failoverTime,
		NotAfter:        failoverTime.Add(24 * time.Hour),
		SigningEvidence: testSigningEvidence("certificate_issue", "sha256"),
	}
	if _, err := firstService.persistSignedIssuanceAttempt(ctx, firstClaim, result, failoverTime); !errors.Is(err, domain.ErrInvalidTransition) {
		t.Fatalf("stale node persistence error = %v, want %v", err, domain.ErrInvalidTransition)
	}

	signed, err := failoverNode.persistSignedIssuanceAttempt(ctx, secondClaim, result, failoverTime)
	if err != nil {
		t.Fatalf("persist failover signed attempt: %v", err)
	}
	certificate, err := failoverNode.finalizeSignedIssuanceAttempt(ctx, enrollment.ID, signed, failoverTime)
	if err != nil {
		t.Fatalf("finalize failover attempt: %v", err)
	}
	if err := failoverNode.ensureCertificateIssuedAuditEvent(ctx, "failover-node", certificate, failoverTime); err != nil {
		t.Fatalf("ensure issuance audit: %v", err)
	}

	retryIssuer := &fakeIssuer{}
	retryNode := New(firstRepo, retryIssuer, fixedClock{now: failoverTime.Add(time.Minute)}, UUIDGenerator{})
	retried, err := retryNode.IssueCertificate(ctx, "retry-node", enrollment.ID)
	if err != nil {
		t.Fatalf("retry finalized issuance: %v", err)
	}
	if retried.ID != certificate.ID || retried.SerialNumber != certificate.SerialNumber {
		t.Fatalf("retry certificate = %#v, want %#v", retried, certificate)
	}
	if len(retryIssuer.requests) != 0 {
		t.Fatalf("retry signer requests = %d, want 0", len(retryIssuer.requests))
	}

	storedAttempt, err := secondRepo.GetIssuanceAttempt(ctx, enrollment.ID)
	if err != nil {
		t.Fatalf("GetIssuanceAttempt: %v", err)
	}
	if storedAttempt.Status != domain.IssuanceAttemptFinalized || storedAttempt.CertificateID != certificate.ID {
		t.Fatalf("stored attempt = %#v", storedAttempt)
	}
}

func TestPostgresMultiNodeCRLFailoverIntegration(t *testing.T) {
	ctx := context.Background()
	firstRepo, secondRepo := openPostgresFailoverRepositories(t)
	base := time.Date(2026, time.January, 2, 3, 4, 5, 0, time.UTC)
	issuer := domain.Issuer{
		ID:             "issuer-postgres-failover",
		Name:           "postgres-failover",
		Kind:           domain.IssuerIntermediateCA,
		Status:         domain.IssuerActive,
		CertificatePEM: "issuer-cert",
		KeyRef:         "file:local-dev-only",
		CreatedAt:      base,
		UpdatedAt:      base,
	}
	if err := firstRepo.CreateIssuer(ctx, issuer); err != nil {
		t.Fatalf("CreateIssuer: %v", err)
	}

	firstNode := New(firstRepo, &fakeIssuer{}, fixedClock{now: base}, UUIDGenerator{})
	secondNodeActive := New(secondRepo, &fakeIssuer{}, fixedClock{now: base.Add(time.Minute)}, UUIDGenerator{})
	distributionPoint := "https://pki.example.test/failover.crl"
	firstClaim, err := firstNode.claimCRLGeneration(ctx, issuer.ID, distributionPoint, base)
	if err != nil {
		t.Fatalf("first CRL claim: %v", err)
	}
	if firstClaim.CRLNumber != 1 {
		t.Fatalf("first CRL number = %d, want 1", firstClaim.CRLNumber)
	}
	if _, err := secondNodeActive.claimCRLGeneration(ctx, issuer.ID, distributionPoint, base.Add(time.Minute)); !errors.Is(err, domain.ErrInvalidTransition) {
		t.Fatalf("active CRL lease error = %v, want %v", err, domain.ErrInvalidTransition)
	}

	failoverTime := base.Add(defaultCRLGenerationLease + time.Minute)
	secondNode := New(secondRepo, &fakeIssuer{}, fixedClock{now: failoverTime}, UUIDGenerator{})
	secondClaim, err := secondNode.claimCRLGeneration(ctx, issuer.ID, distributionPoint, failoverTime)
	if err != nil {
		t.Fatalf("CRL lease takeover: %v", err)
	}
	if secondClaim.CRLNumber != 1 || !secondClaim.LeaseExpiresAt.After(firstClaim.LeaseExpiresAt) {
		t.Fatalf("takeover claim = %#v, first = %#v", secondClaim, firstClaim)
	}

	if err := firstRepo.DeleteCRLGenerationClaimIfCurrent(ctx, firstClaim); !errors.Is(err, domain.ErrInvalidTransition) {
		t.Fatalf("stale CRL completion error = %v, want %v", err, domain.ErrInvalidTransition)
	}

	publication := domain.CRLPublication{
		ID:                "crl-postgres-failover-1",
		IssuerID:          issuer.ID,
		DistributionPoint: distributionPoint,
		CRLNumber:         secondClaim.CRLNumber,
		ThisUpdate:        failoverTime,
		NextUpdate:        failoverTime.Add(24 * time.Hour),
		Status:            domain.CRLPublicationPublished,
		CRLPEM:            "crl-pem",
		CreatedAt:         failoverTime,
		UpdatedAt:         failoverTime,
	}
	if err := secondRepo.WithinTx(ctx, func(repo store.Repository) error {
		if err := repo.CreateCRLPublication(ctx, publication); err != nil {
			return err
		}
		return repo.DeleteCRLGenerationClaimIfCurrent(ctx, secondClaim)
	}); err != nil {
		t.Fatalf("commit failover CRL: %v", err)
	}

	nextTime := failoverTime.Add(time.Minute)
	nextClaim, err := firstNode.claimCRLGeneration(ctx, issuer.ID, distributionPoint, nextTime)
	if err != nil {
		t.Fatalf("next CRL claim: %v", err)
	}
	if nextClaim.CRLNumber != 2 {
		t.Fatalf("next CRL number = %d, want 2", nextClaim.CRLNumber)
	}
}

func TestPostgresMultiNodeOutboxTrafficShiftIntegration(t *testing.T) {
	ctx := context.Background()
	firstRepo, secondRepo := openPostgresFailoverRepositories(t)
	base := time.Date(2026, time.January, 2, 3, 4, 5, 0, time.UTC)
	message := domain.OutboxMessage{
		ID:          "outbox-postgres-failover",
		Type:        "certificate.expiring",
		PayloadJSON: `{"certificate_id":"cert-1"}`,
		Status:      domain.OutboxPending,
		AvailableAt: base.Add(-time.Minute),
		MaxAttempts: 4,
		CreatedAt:   base.Add(-time.Minute),
		UpdatedAt:   base.Add(-time.Minute),
	}
	if err := firstRepo.CreateOutboxMessage(ctx, message); err != nil {
		t.Fatalf("CreateOutboxMessage: %v", err)
	}

	firstDispatcher := NewOutboxDispatcher(firstRepo, OutboxHandlerFunc(func(context.Context, domain.OutboxMessage) error {
		t.Fatal("first node handler must not run in claim-only crash simulation")
		return nil
	}), fixedClock{now: base}, UUIDGenerator{})
	due, err := firstRepo.ListDueOutboxMessages(ctx, base, 10)
	if err != nil || len(due) != 1 {
		t.Fatalf("initial due = %#v, %v", due, err)
	}
	firstClaim, claimed, err := firstDispatcher.claim(ctx, due[0])
	if err != nil || !claimed {
		t.Fatalf("first outbox claim = (%#v, %t, %v)", firstClaim, claimed, err)
	}

	var handled atomic.Int32
	activeDispatcher := NewOutboxDispatcher(secondRepo, OutboxHandlerFunc(func(context.Context, domain.OutboxMessage) error {
		handled.Add(1)
		return nil
	}), fixedClock{now: base.Add(time.Minute)}, UUIDGenerator{})
	processed, err := activeDispatcher.RunOnce(ctx, 10)
	if err != nil || processed != 0 {
		t.Fatalf("active-lease traffic shift = (%d, %v), want (0, nil)", processed, err)
	}
	if handled.Load() != 0 {
		t.Fatalf("active-lease handled = %d, want 0", handled.Load())
	}

	failoverTime := base.Add(defaultOutboxProcessingLease + time.Minute)
	failoverDispatcher := NewOutboxDispatcher(secondRepo, OutboxHandlerFunc(func(context.Context, domain.OutboxMessage) error {
		handled.Add(1)
		return nil
	}), fixedClock{now: failoverTime}, UUIDGenerator{})
	processed, err = failoverDispatcher.RunOnce(ctx, 10)
	if err != nil || processed != 1 {
		t.Fatalf("expired-lease traffic shift = (%d, %v), want (1, nil)", processed, err)
	}
	if handled.Load() != 1 {
		t.Fatalf("failover handled = %d, want 1", handled.Load())
	}

	staleAttempt := domain.JobAttempt{
		ID:              "job-stale-node",
		OutboxMessageID: message.ID,
		Status:          domain.JobAttemptSucceeded,
		StartedAt:       base,
		FinishedAt:      failoverTime.Add(time.Minute),
		CreatedAt:       failoverTime.Add(time.Minute),
	}
	if err := firstDispatcher.finish(ctx, firstClaim, domain.OutboxCompleted, staleAttempt); !errors.Is(err, domain.ErrInvalidTransition) {
		t.Fatalf("stale outbox completion error = %v, want %v", err, domain.ErrInvalidTransition)
	}

	stored, err := firstRepo.GetOutboxMessage(ctx, message.ID)
	if err != nil {
		t.Fatalf("GetOutboxMessage: %v", err)
	}
	if stored.Status != domain.OutboxCompleted || !stored.ProcessingDeadlineAt.IsZero() {
		t.Fatalf("stored outbox = %#v", stored)
	}
	attempts, err := firstRepo.ListJobAttemptsByOutboxMessage(ctx, message.ID)
	if err != nil {
		t.Fatalf("ListJobAttemptsByOutboxMessage: %v", err)
	}
	if len(attempts) != 1 || attempts[0].Status != domain.JobAttemptSucceeded {
		t.Fatalf("job attempts = %#v, want one success", attempts)
	}
}
