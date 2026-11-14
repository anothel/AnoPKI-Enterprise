// SPDX-License-Identifier: MPL-2.0
package store

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"errors"
	"io"
	"strings"
	"testing"
)

func TestAuditBackfillPreservesCloseErrorAfterReadFailure(t *testing.T) {
	for _, stage := range []string{"scan", "parse"} {
		t.Run(stage, func(t *testing.T) {
			closeErr := errors.New("audit rows close failed")
			rows := &backfillFailureRows{stage: stage, closeErr: closeErr}
			db := sql.OpenDB(backfillFailureConnector{rows})
			t.Cleanup(func() { db.Close() })
			err := backfillAuditHashChain(context.Background(), db)
			if err == nil || !strings.Contains(err.Error(), stage+" legacy audit event") {
				t.Fatalf("primary %s error lost: %v", stage, err)
			}
			if !rows.closed || !errors.Is(err, closeErr) {
				t.Fatalf("row close error lost: closed=%t, error=%v", rows.closed, err)
			}
		})
	}
}

// Inject only the database driver's row read/close failures. database/sql and
// backfillAuditHashChain remain real, including Scan and timestamp parsing.
type backfillFailureConnector struct{ rows *backfillFailureRows }

func (c backfillFailureConnector) Connect(context.Context) (driver.Conn, error) {
	return backfillFailureConn(c), nil
}
func (c backfillFailureConnector) Driver() driver.Driver { return backfillFailureDriver{} }

type backfillFailureDriver struct{}

func (backfillFailureDriver) Open(string) (driver.Conn, error) {
	return nil, errors.New("use connector")
}

type backfillFailureConn struct{ rows *backfillFailureRows }

func (backfillFailureConn) Prepare(string) (driver.Stmt, error) {
	return nil, errors.New("unexpected prepare")
}
func (backfillFailureConn) Begin() (driver.Tx, error) {
	return nil, errors.New("unexpected transaction")
}
func (backfillFailureConn) Close() error { return nil }
func (c backfillFailureConn) QueryContext(context.Context, string, []driver.NamedValue) (driver.Rows, error) {
	return c.rows, nil
}

type backfillFailureRows struct {
	stage    string
	closeErr error
	read     bool
	closed   bool
}

func (*backfillFailureRows) Columns() []string {
	return []string{"id", "actor", "action", "resource_type", "resource_id", "metadata_json", "created_at"}
}
func (r *backfillFailureRows) Close() error {
	r.closed = true
	return r.closeErr
}
func (r *backfillFailureRows) Next(values []driver.Value) error {
	if r.read {
		return io.EOF
	}
	r.read = true
	copy(values, []driver.Value{"event-1", "operator", "audit.test", "audit", "1", "{}", "invalid-time"})
	if r.stage == "scan" {
		values[0] = nil // Scan cannot put a SQL NULL in the string ID.
	}
	return nil
}
