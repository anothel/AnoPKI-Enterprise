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

- [x] Add Phase 3 lifecycle tests with a missing topology helper; confirm compile failure.
- [x] Add minimal Docker topology helper and implement kill/promote/reconnect.
- [x] Run all scenarios live with race; inspect measurements and cleanup.

### Task 2: Evidence and CI

- [x] Add evidence parser rejection tests first; confirm failure without implementation.
- [x] Implement allowlisted measurements, clean commit attribution, fail-closed reports.
- [x] Add a separate CI job, preserving existing jobs and checks.
- [x] Run runner regressions, Go suite/vet and baseline/docs checks.

### Task 3: Review and draft handoff

- [x] Commit implementation; rerun qualification on exact clean commit.
- [x] Independent security/correctness review; fix material findings and rerun.
- [x] Record verified results and explicit untested cases; open draft PR.

Execution record: clean implementation 5a78265 passed all four live scenarios.
Independent source review findings were fixed; timeout mutation rejected.
Ruling: Docker internal bridges suppress host ports on this daemon; use a unique
bridge and loopback publication. Cost: the disposable Docker host is a trusted boundary.
