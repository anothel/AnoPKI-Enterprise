#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Tests for Enterprise release evidence validation."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_WORKFLOW = ROOT / ".github/workflows/release.yml"
SCRIPT = ROOT / "scripts" / "validate-release-evidence.py"


def require_release_workflow() -> None:
    if not RELEASE_WORKFLOW.is_file():
        raise SystemExit("missing release workflow: .github/workflows/release.yml")
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    required = [
        "on:",
        "workflow_dispatch:",
        "tags:",
        "contents: read",
        "contents: write",
        "id-token: write",
        'go-version: "1.25.12"',
        "python scripts/verify-go-release.py",
        "--profile full",
        "anopki-enterprise-go-verification.tar.gz",
        "anopki-recovery-verification.tar.gz",
        "anopki-status-outage-verification.tar.gz",
        "anopki-audit-replay-verification.tar.gz",
        "cmake --build build-release --config Release",
        'VERSION="$(cat VERSION)"',
        "go build -ldflags",
        "anopki-service-v${VERSION}-linux-amd64.tar.gz",
        "anopki-core-v${VERSION}-linux-amd64.tar.gz",
        "python scripts/generate-package-manifest.py",
        '--package-class "$PACKAGE_CLASS"',
        "package-manifest.json",
        "python scripts/validate-package-boundary.py",
        "--manifest dist/package-manifest.json",
        "python scripts/validate-release-artifacts.py dist",
        "syft scan dir:dist",
        "cosign sign-blob",
        "actions/upload-artifact",
        "actions/download-artifact",
        "SIGNING-STATUS.txt",
        "Signing skipped: manual dry-run",
        "publish-tagged-release:",
        "if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')",
        "environment: release",
        "Require a signed annotated tag",
        "GH_TOKEN: ${{ github.token }}",
        "gh release create",
        "gh release upload",
    ]
    missing = [value for value in required if value not in text]
    if missing:
        raise SystemExit(".github/workflows/release.yml missing:\n" + "\n".join(missing))


def copy_release_evidence_inputs(dst: Path) -> None:
    files = [
        "docs/reference/release-evidence.md",
        "docs/enterprise/private-alpha-evidence.md",
        ".edition/edition.json",
        "scripts/verify-local.ps1",
        "scripts/verify-go-release.py",
        "scripts/verify-recovery-drill.py",
        "scripts/verify-status-outage-drill.py",
        "scripts/verify-audit-replay-drill.py",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
    ]
    for name in files:
        target = dst / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def mutate(path: Path, old: str, new: str = "") -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"missing fixture text: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")




def test_missing_compatibility_matrix_row_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    evidence = tmp_path / "docs" / "reference" / "release-evidence.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace("| certbot |", "| certbot-drift |", 1),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "release evidence compatibility matrix missing" in result.stderr


def test_compatibility_matrix_row_detail_drift_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    evidence = tmp_path / "docs" / "reference" / "release-evidence.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace(
            "The maintained floor is Go 1.25.11",
            "The maintained floor is Go 1.25",
            1,
        ),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "release evidence compatibility matrix row detail drift" in result.stderr


def test_certbot_wsl_evidence_link_drift_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    evidence = tmp_path / "docs" / "reference" / "release-evidence.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace("WSL certbot evidence", "certbot evidence", 1),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "release evidence compatibility matrix row detail drift" in result.stderr


def test_missing_ci_version_metadata_validation_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    ci = tmp_path / ".github" / "workflows" / "ci.yml"
    ci.write_text(
        ci.read_text(encoding="utf-8").replace("python scripts/validate-version-metadata.py", "", 1),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "validate-version-metadata.py" in result.stderr


def test_missing_go_runner_staticcheck_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    runner = tmp_path / "scripts" / "verify-go-release.py"
    runner.write_text(
        runner.read_text(encoding="utf-8").replace('STATICCHECK_VERSION = "2026.1"', "", 1),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "STATICCHECK_VERSION" in result.stderr


def test_missing_go_runner_gosec_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    runner = tmp_path / "scripts" / "verify-go-release.py"
    runner.write_text(
        runner.read_text(encoding="utf-8").replace('GOSEC_VERSION = "v2.25.0"', "", 1),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "GOSEC_VERSION" in result.stderr


def test_missing_ci_go_evidence_upload_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    ci = tmp_path / ".github" / "workflows" / "ci.yml"
    ci.write_text(
        ci.read_text(encoding="utf-8").replace("anopki-enterprise-go-analysis-1.26.5", "", 1),
        encoding="utf-8",
    )
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "anopki-enterprise-go-analysis-1.26.5" in result.stderr


def test_missing_ci_fuzz_smoke_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    ci = tmp_path / ".github" / "workflows" / "ci.yml"
    ci.write_text(
        ci.read_text(encoding="utf-8").replace("ANOPKI_ENABLE_FUZZING=ON", "", 1),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "ANOPKI_ENABLE_FUZZING=ON" in result.stderr


def test_missing_release_signing_evidence_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    release = tmp_path / ".github" / "workflows" / "release.yml"
    release.write_text(
        release.read_text(encoding="utf-8").replace("cosign sign-blob", "", 1),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "cosign sign-blob" in result.stderr


def test_missing_release_go_evidence_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    release = tmp_path / ".github" / "workflows" / "release.yml"
    release.write_text(
        release.read_text(encoding="utf-8").replace("anopki-enterprise-go-verification.tar.gz", "", 1),
        encoding="utf-8",
    )
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "anopki-enterprise-go-verification.tar.gz" in result.stderr


def test_missing_release_dry_run_gate_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    release = tmp_path / ".github" / "workflows" / "release.yml"
    release.write_text(
        release.read_text(encoding="utf-8").replace(
            "if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')",
            "if: always()",
            1,
        ),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "github.event_name == 'push'" in result.stderr


def test_release_evidence_placeholder_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    evidence = tmp_path / "docs" / "reference" / "release-evidence.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8") + "\nTODO\n",
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "contains placeholder text" in result.stderr


def test_missing_local_verification_evidence_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    evidence = tmp_path / "docs" / "reference" / "release-evidence.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace("- `python scripts/validate-docs.py`", "", 1),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "release evidence missing local verification commands" in result.stderr


def test_missing_compatibility_evidence_template_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    evidence = tmp_path / "docs" / "reference" / "release-evidence.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace(
            "## Release Candidate Compatibility Evidence Template",
            "## Release Candidate Compatibility Drift",
            1,
        ),
        encoding="utf-8",
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "release evidence compatibility template missing" in result.stderr


def test_hosted_execution_contradictions_fail(tmp_path: Path) -> None:
    cases = [
        ("hosted_ci", {"remote_validation": "passed"}, "runner_assigned=false"),
        ("hosted_ci", {"runner_assigned": True, "classification": "CI_SUCCESS"}, "zero hosted CI steps"),
        ("hosted_ci", {"release_artifact_evidence": True}, "release artifact evidence"),
        ("trusted_anocrypto_sdk_lane", {"status": "completed"}, "trusted SDK not_run"),
        ("trusted_anocrypto_sdk_lane", {"kcmvp_status": "validated"}, "KCMVP validated claim"),
        ("hosted_ci", {"blocker": "code_failure"}, "billing blocker"),
    ]
    for section, changes, expected in cases:
        copy_release_evidence_inputs(tmp_path)
        edition_path = tmp_path / ".edition" / "edition.json"
        edition = json.loads(edition_path.read_text(encoding="utf-8"))
        edition[section].update(changes)
        edition_path.write_text(json.dumps(edition), encoding="utf-8")

        result = run_validator(tmp_path)

        assert result.returncode == 1
        assert expected in result.stderr


def test_missing_recovery_runner_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    mutate(tmp_path / "scripts/verify-recovery-drill.py", "private-key-exclusion")
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "private-key-exclusion" in result.stderr


def test_missing_release_recovery_evidence_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    mutate(tmp_path / ".github/workflows/release.yml", "anopki-recovery-verification.tar.gz")
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "anopki-recovery-verification.tar.gz" in result.stderr


def test_missing_status_outage_runner_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    mutate(tmp_path / "scripts/verify-status-outage-drill.py", "sensitive-evidence-exclusion")
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "sensitive-evidence-exclusion" in result.stderr


def test_missing_release_status_outage_evidence_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    mutate(tmp_path / ".github/workflows/release.yml", "anopki-status-outage-verification.tar.gz")
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "anopki-status-outage-verification.tar.gz" in result.stderr



def test_audit_replay_minimum_go_version_format_drift_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    mutate(
        tmp_path / "scripts/verify-audit-replay-drill.py",
        "MINIMUM_GO_VERSION = (1, 25, 11)",
        "MINIMUM_GO_VERSION=(1,25,11)",
    )
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "MINIMUM_GO_VERSION = (1, 25, 11)" in result.stderr


def test_missing_audit_replay_runner_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    mutate(tmp_path / "scripts/verify-audit-replay-drill.py", "dead-letter-attempt-history-preserved")
    result = run_validator(tmp_path)
    assert result.returncode == 1


def test_missing_release_audit_replay_evidence_fails(tmp_path: Path) -> None:
    copy_release_evidence_inputs(tmp_path)
    mutate(tmp_path / ".github/workflows/release.yml", "anopki-audit-replay-verification.tar.gz")
    result = run_validator(tmp_path)
    assert result.returncode == 1



def main() -> None:
    result = run_validator(ROOT)
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        raise SystemExit(result.returncode)
    if "release evidence ok" not in result.stdout:
        raise SystemExit(f"unexpected validator output: {result.stdout!r}")
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_compatibility_matrix_row_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_compatibility_matrix_row_detail_drift_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_certbot_wsl_evidence_link_drift_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_ci_version_metadata_validation_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_go_runner_staticcheck_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_go_runner_gosec_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_ci_go_evidence_upload_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_ci_fuzz_smoke_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_release_signing_evidence_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_release_go_evidence_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_release_dry_run_gate_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_release_evidence_placeholder_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_local_verification_evidence_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_compatibility_evidence_template_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_recovery_runner_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_release_recovery_evidence_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_status_outage_runner_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_release_status_outage_evidence_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_audit_replay_minimum_go_version_format_drift_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_audit_replay_runner_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_missing_release_audit_replay_evidence_fails(Path(dirname))
    with tempfile.TemporaryDirectory() as dirname:
        test_hosted_execution_contradictions_fail(Path(dirname))
    require_release_workflow()
    print("release evidence validator tests ok")


if __name__ == "__main__":
    main()
