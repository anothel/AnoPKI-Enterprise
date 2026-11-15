# PostgreSQL Primary Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish measured, reproducible PostgreSQL 16 infrastructure failover evidence.
**Architecture:** Disposable Docker physical replication, process fencing, manual promotion, retained pgx pools.
**Tech Stack:** Go, PostgreSQL 16.16, Docker, Python evidence runner, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-11-15-postgres-primary-design.md

## Global Constraints

Disposable infrastructure only. No external DSN. Preserve pins and all gates.
No merge, tag, release, publication or deployment.

## Review Focus

- Promotion must follow confirmed fencing; errors must fail closed.
- Synchronous acknowledgement and async loss boundaries must be observed.
- Existing client pools must reconnect; stale transactions must fail.
- Evidence must bind exact clean source and reject skipped/missing scenarios.
- Cleanup must target only unique owned resources; no sensitive diagnostics exported.

### Task 1: Infrastructure and application regressions

- [ ] Add Phase 3 lifecycle tests with a missing topology helper; confirm compile failure.
- [ ] Add minimal Docker topology helper and implement kill/promote/reconnect.
- [ ] Run all scenarios live with race; inspect measurements and cleanup.

### Task 2: Evidence and CI

- [ ] Add evidence parser rejection tests first; confirm failure without implementation.
- [ ] Implement allowlisted measurements, clean commit attribution, fail-closed reports.
- [ ] Add a separate CI job, preserving existing jobs and checks.
- [ ] Run runner regressions, Go suite/vet and baseline/docs checks.

### Task 3: Review and draft handoff

- [ ] Commit implementation; rerun qualification on exact clean commit.
- [ ] Independent security/correctness review; fix material findings and rerun.
- [ ] Record verified results and explicit untested cases; open draft PR.
