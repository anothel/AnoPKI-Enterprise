// SPDX-License-Identifier: MPL-2.0
package lifecycle

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"

	"github.com/anothel/anopki/service/internal/store"
	_ "github.com/jackc/pgx/v5/stdlib"
)

// Immutable upstream image, PostgreSQL 16.16. No caller-supplied DSNs or resources.
const primaryImage = "postgres:16.16@sha256:dd2bf3ce2dc83a81674cf7f217fcfd8a5009a4b325dda5b843bfee82a06cff6f"

type primaryTopology struct {
	primary, standby, network, schema, dsn string
	db                                     *sql.DB
	sync                                   bool
}

func dockerPrimary(t *testing.T, args ...string) string {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	out, err := exec.CommandContext(ctx, "docker", args...).CombinedOutput()
	if err != nil {
		t.Fatalf("disposable Docker operation %s failed (diagnostics omitted)", args[0])
	}
	return strings.TrimSpace(string(out))
}

func waitPrimary(t *testing.T, check func() bool) {
	t.Helper()
	deadline := time.Now().Add(30 * time.Second)
	for time.Now().Before(deadline) {
		if check() {
			return
		}
		time.Sleep(50 * time.Millisecond)
	}
	t.Fatal("disposable topology condition timed out")
}

func newPrimaryTopology(t *testing.T, synchronous bool) *primaryTopology {
	t.Helper()
	if os.Getenv("ANOPKI_POSTGRES_PRIMARY_DISPOSABLE") != "1" {
		t.Skip("set ANOPKI_POSTGRES_PRIMARY_DISPOSABLE=1 to create disposable Docker topology")
	}
	id := "anopki-p3-" + strings.ReplaceAll(UUIDGenerator{}.NewID(), "-", "")
	h := &primaryTopology{primary: id + "-p", standby: id + "-s", network: id, schema: "phase3", sync: synchronous}
	label := "com.anopki.phase3.run=" + os.Getenv("ANOPKI_POSTGRES_PRIMARY_RUN_ID")
	if os.Getenv("ANOPKI_POSTGRES_PRIMARY_RUN_ID") == "" {
		label = "com.anopki.phase3.run=" + id
	}
	dockerPrimary(t, "network", "create", "--label", label, h.network)
	t.Cleanup(func() { dockerPrimary(t, "network", "rm", h.network) })
	run := func(name string, extra ...string) {
		args := []string{"run", "-d", "--label", label, "--name", name, "--network", h.network, "--publish", "127.0.0.1::5432", "--tmpfs", "/var/lib/postgresql/data:rw,mode=0700,uid=999,gid=999", "-e", "POSTGRES_HOST_AUTH_METHOD=trust"}
		args = append(args, extra...)
		dockerPrimary(t, args...)
	}
	// Register removal before creation so partial startup is cleaned too.
	cleanup := func(name string) { t.Cleanup(func() { dockerPrimary(t, "rm", "-f", "-v", name) }) }
	cleanup(h.primary)
	run(h.primary, primaryImage, "postgres", "-c", "wal_level=replica", "-c", "max_wal_senders=4")
	waitPrimary(t, func() bool {
		ctx, cancel := context.WithTimeout(context.Background(), time.Second)
		defer cancel()
		return exec.CommandContext(ctx, "docker", "exec", h.primary, "pg_isready", "-h", "127.0.0.1", "-U", "postgres").Run() == nil
	})
	h.psql(t, h.primary, "CREATE ROLE replicator REPLICATION LOGIN")
	// The bridge is unique; published client endpoints bind loopback only.
	dockerPrimary(t, "exec", h.primary, "sh", "-c", "printf '\nhost replication replicator all trust\n' >> /var/lib/postgresql/data/pg_hba.conf")
	h.psql(t, h.primary, "SELECT pg_reload_conf()")
	cleanup(h.standby)
	run(h.standby, "--user", "postgres", "--entrypoint", "sh", primaryImage, "-c", "pg_basebackup -h "+h.primary+" -U replicator -D /var/lib/postgresql/data -R -X stream && exec postgres -D /var/lib/postgresql/data")
	waitPrimary(t, func() bool {
		ctx, cancel := context.WithTimeout(context.Background(), time.Second)
		defer cancel()
		return exec.CommandContext(ctx, "docker", "exec", h.standby, "pg_isready", "-h", "127.0.0.1", "-U", "postgres").Run() == nil
	})
	if h.psql(t, h.primary, "SELECT current_setting('server_version_num')::int/10000") != "16" || h.psql(t, h.standby, "SELECT current_setting('server_version_num')::int/10000") != "16" {
		t.Fatal("PostgreSQL 16 required")
	}
	if h.psql(t, h.standby, "SELECT pg_is_in_recovery()") != "t" {
		t.Fatal("standby must be in recovery")
	}
	port := func(name string) string {
		out := dockerPrimary(t, "port", name, "5432/tcp")
		if !strings.HasPrefix(out, "127.0.0.1:") || strings.Contains(out, "\n") {
			t.Fatal("client endpoint must be loopback only")
		}
		return strings.TrimPrefix(out, "127.0.0.1:")
	}
	h.dsn = fmt.Sprintf("host=127.0.0.1,127.0.0.1 port=%s,%s user=postgres dbname=postgres sslmode=disable connect_timeout=2 target_session_attrs=read-write", port(h.primary), port(h.standby))
	var err error
	h.db, err = sql.Open("pgx", h.dsn)
	if err != nil {
		t.Fatal("open disposable pool")
	}
	h.db.SetMaxOpenConns(2)
	t.Cleanup(func() { h.db.Close() })
	if synchronous {
		h.psql(t, h.primary, "ALTER SYSTEM SET synchronous_standby_names = '*'")
		h.psql(t, h.primary, "ALTER SYSTEM SET synchronous_commit = 'remote_apply'")
		h.psql(t, h.primary, "SELECT pg_reload_conf()")
		waitPrimary(t, func() bool {
			return h.psql(t, h.primary, "SELECT count(*) FROM pg_stat_replication WHERE sync_state='sync'") == "1"
		})
	}
	h.psql(t, h.primary, "CREATE TABLE public.phase3_probe(id integer PRIMARY KEY); INSERT INTO public.phase3_probe VALUES (1)")
	lsn := h.psql(t, h.primary, "SELECT pg_current_wal_lsn()")
	waitPrimary(t, func() bool {
		return h.psql(t, h.standby, "SELECT pg_last_wal_replay_lsn() >= '"+lsn+"'::pg_lsn") == "t"
	})
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := h.db.PingContext(ctx); err != nil {
		t.Fatal("prime retained infrastructure client pool")
	}
	t.Log("PHASE3_IMAGE " + primaryImage)
	return h
}

func (h *primaryTopology) psql(t *testing.T, node, query string) string {
	t.Helper()
	return dockerPrimary(t, "exec", node, "psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-c", query)
}

func (h *primaryTopology) repositories(t *testing.T) (store.Repository, store.Repository) {
	t.Helper()
	h.psql(t, h.primary, "CREATE SCHEMA "+h.schema)
	open := func() *sql.DB {
		db, err := sql.Open("pgx", h.dsn+" search_path="+h.schema)
		if err != nil {
			t.Fatal("open repository")
		}
		t.Cleanup(func() { db.Close() })
		return db
	}
	a, b := open(), open()
	for _, db := range []*sql.DB{a, b} {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		err := db.PingContext(ctx)
		cancel()
		if err != nil {
			t.Fatal("prime retained application pool")
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := store.ApplyInitialMigration(ctx, a, "pgx"); err != nil {
		t.Fatal("migrate disposable repository")
	}
	for _, db := range []*sql.DB{a, b} {
		var mode string
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		err := db.QueryRowContext(ctx, "SHOW synchronous_commit").Scan(&mode)
		cancel()
		if err != nil || mode != "remote_apply" {
			t.Fatal("application sessions require remote_apply")
		}
	}
	first, second := store.NewSQLStore(a), store.NewSQLStore(b)
	t.Cleanup(func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		report, err := first.VerifyAuditChain(ctx)
		if err != nil || !report.Valid {
			t.Error("audit chain invalid after primary recovery")
		}
	})
	return first, second
}

func (h *primaryTopology) snapshot(t *testing.T, node string) string {
	t.Helper()
	tables := h.psql(t, node, "SELECT tablename FROM pg_tables WHERE schemaname='phase3' ORDER BY tablename")
	var all strings.Builder
	for _, table := range strings.Fields(tables) {
		// Names come only from the fixed application migrations, quote defensively.
		quoted := `"` + strings.ReplaceAll(table, `"`, `""`) + `"`
		all.WriteString(table + ":" + h.psql(t, node, "SELECT coalesce(string_agg(r::text, E'\\n' ORDER BY r::text),'') FROM (SELECT row_to_json(t) AS r FROM phase3."+quoted+" t) s") + "\n")
	}
	return fmt.Sprintf("%x", sha256.Sum256([]byte(all.String())))
}

func (h *primaryTopology) failover(t *testing.T) {
	t.Helper()
	before := h.snapshot(t, h.primary)
	// Keep a connection and uncommitted transaction on the old primary.
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()
	tx, err := h.db.BeginTx(ctx, nil)
	if err != nil {
		t.Fatal("open old-primary transaction")
	}
	defer tx.Rollback()
	if _, err = tx.ExecContext(ctx, "INSERT INTO public.phase3_probe VALUES(2)"); err != nil {
		t.Fatal("old-primary transaction write")
	}
	// Recovery nodes must reject writes before promotion.
	cmd := exec.CommandContext(ctx, "docker", "exec", h.standby, "psql", "-X", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-c", "INSERT INTO public.phase3_probe VALUES(9)")
	if cmd.Run() == nil {
		t.Fatal("standby accepted write")
	}
	started := time.Now()
	dockerPrimary(t, "kill", "--signal=KILL", h.primary)
	if dockerPrimary(t, "inspect", "-f", "{{.State.Running}}", h.primary) != "false" {
		t.Fatal("primary fencing not confirmed")
	}
	fenced := time.Since(started).Seconds()
	if _, err = tx.ExecContext(ctx, "INSERT INTO public.phase3_probe VALUES(4)"); err == nil {
		t.Fatal("fenced writer accepted write")
	}
	if err = tx.Commit(); err == nil {
		t.Fatal("old transaction committed")
	}
	h.psql(t, h.standby, "SELECT pg_promote(true, 30)")
	if h.psql(t, h.standby, "SELECT pg_is_in_recovery()") != "f" {
		t.Fatal("promotion not complete")
	}
	h.psql(t, h.standby, "ALTER SYSTEM SET synchronous_standby_names = ''")
	h.psql(t, h.standby, "SELECT pg_reload_conf()")
	promoted := time.Since(started).Seconds()
	waitPrimary(t, func() bool {
		c, stop := context.WithTimeout(context.Background(), 3*time.Second)
		defer stop()
		_, e := h.db.ExecContext(c, "INSERT INTO public.phase3_probe VALUES(5) ON CONFLICT DO NOTHING")
		return e == nil
	})
	recovered := time.Since(started).Seconds()
	if h.snapshot(t, h.standby) != before {
		t.Fatal("application state changed across promotion")
	}
	if h.psql(t, h.standby, "SELECT string_agg(id::text, ',' ORDER BY id) FROM public.phase3_probe") != "1,5" {
		t.Fatal("acknowledged or uncommitted transaction boundary violated")
	}
	metrics, _ := json.Marshal(map[string]any{"scenario": t.Name(), "fence_seconds": fenced, "promotion_seconds": promoted, "reconnect_seconds": recovered, "acknowledged_lost": 0, "state_digest": before})
	t.Log("PHASE3_METRIC " + string(metrics))
}

func TestPostgresPrimaryAsyncLossIntegration(t *testing.T) {
	h := newPrimaryTopology(t, false)
	// Stop WAL receipt and replay after the baseline is observed. This models an
	// isolated lagging standby, not random timing of asynchronous WAL delivery.
	h.psql(t, h.standby, "ALTER SYSTEM SET primary_conninfo = 'host=127.0.0.1 port=1 connect_timeout=1'")
	h.psql(t, h.standby, "SELECT pg_reload_conf()")
	waitPrimary(t, func() bool { return h.psql(t, h.standby, "SELECT count(*) FROM pg_stat_wal_receiver") == "0" })
	h.psql(t, h.standby, "SELECT pg_wal_replay_pause()")
	h.psql(t, h.primary, "INSERT INTO public.phase3_probe VALUES(3)")
	if h.psql(t, h.primary, "SELECT count(*) FROM public.phase3_probe WHERE id=3") != "1" {
		t.Fatal("async marker not committed")
	}
	started := time.Now()
	dockerPrimary(t, "kill", "--signal=KILL", h.primary)
	if dockerPrimary(t, "inspect", "-f", "{{.State.Running}}", h.primary) != "false" {
		t.Fatal("fencing failed")
	}
	fenced := time.Since(started).Seconds()
	h.psql(t, h.standby, "SELECT pg_promote(true, 30)")
	if h.psql(t, h.standby, "SELECT pg_is_in_recovery()") != "f" {
		t.Fatal("async promotion incomplete")
	}
	promoted := time.Since(started).Seconds()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if _, err := h.db.ExecContext(ctx, "INSERT INTO public.phase3_probe VALUES(5)"); err != nil {
		t.Fatal("async reconnect failed")
	}
	if h.psql(t, h.standby, "SELECT string_agg(id::text, ',' ORDER BY id) FROM public.phase3_probe") != "1,5" {
		t.Fatal("expected one acknowledged async marker lost")
	}
	metrics, _ := json.Marshal(map[string]any{"scenario": t.Name(), "fence_seconds": fenced, "promotion_seconds": promoted, "reconnect_seconds": time.Since(started).Seconds(), "acknowledged_lost": 1, "state_digest": "not-applicable"})
	t.Log("PHASE3_METRIC " + string(metrics))
}
