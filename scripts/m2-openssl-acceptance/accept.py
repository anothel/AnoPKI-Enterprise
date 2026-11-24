#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Preflight or run the isolated Enterprise/OpenSSL acceptance harness."""

import argparse
import hashlib
import http.client
import json
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

from lifecycle import CASES, CheckFailed, exercise, require

ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES = {
    "csr_inspect", "certificate_issue", "crl_generate", "crl_inspect",
    "ocsp_request_inspect", "ocsp_issuer_inspect", "ocsp_response_generate",
    "ocsp_responder_validate",
}
BACKEND = {
    "product_profile": "enterprise-openssl",
    "edition": "enterprise",
    "selected_backend": "openssl",
    "backend_id": "openssl",
    "backend_dependency": "OpenSSL",
    "backend_readiness": "ready",
    "backend_abi_version": 1,
}


def verify_backend(info):
    require(all(info.get(k) == v for k, v in BACKEND.items()), "unexpected core backend identity")
    require(info.get("fallback_enabled") is False, "core fallback is enabled or unspecified")
    capabilities = info.get("backend_capabilities", [])
    require(len(capabilities) == len(CAPABILITIES) and set(capabilities) == CAPABILITIES,
            "unexpected core capabilities")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", info.get("backend_build_fingerprint", "")),
            "invalid core build fingerprint")
    require(re.fullmatch(r"OpenSSL [0-9][a-zA-Z0-9 .-]*", info.get("backend_version", "")),
            "invalid OpenSSL runtime version")
    return {key: info[key] for key in (*BACKEND, "fallback_enabled", "backend_capabilities",
                                       "backend_build_fingerprint", "backend_version")}


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True, help="exact clean checkout SHA")
    parser.add_argument("--approval", help="owner approval reference for this isolated live run")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        parser.error("--commit must be a lowercase 40-character SHA")
    if args.approval is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", args.approval):
        parser.error("--approval must be a nonsecret reference, such as an approved ticket ID")

    os.umask(0o077)
    evidence = {
        "schema_version": 1,
        "commit": args.commit,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "profile": "enterprise-openssl",
        "mode": "live" if args.approval else "preflight",
        "runner": platform.platform(),
        "python": platform.python_version(),
        "preflight": "NOT_RUN",
        "live": "NOT_RUN",
        "cases": dict.fromkeys(CASES, "NOT_RUN"),
        "commands": [],
        "cleanup": "NOT_RUN",
    }
    if args.approval:
        evidence.update(approval_reference=args.approval, database="sqlite", auth="api_key",
                        key_provider="file", transport="loopback")

    def interrupt(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    scratch = None
    stage = "checkout"
    try:
        require(platform.system() == "Linux", "Linux runner required")
        scratch = tempfile.TemporaryDirectory(prefix="anopki-m2-")
        work = Path(scratch.name)
        # Fresh build and explicit toolchain. Build commands use the prewarmed Go caches.
        env = {"PATH": os.environ["PATH"], "LC_ALL": "C", "HOME": str(work), "TMPDIR": str(work),
               "GOTOOLCHAIN": "local", "GOENV": "off", "GOWORK": "off", "GOPROXY": "off",
               "GOSUMDB": "off", "GOCACHE": os.environ.get("GOCACHE", str(work / "gocache")),
               "GOMODCACHE": os.environ.get("GOMODCACHE", str(Path.home() / "go/pkg/mod"))}

        def run(*argv, cwd=ROOT, extra_env=None, timeout=120, expected=0):
            cmd = [str(arg) for arg in argv]
            record = {
                "argv": [part.replace(str(work), "<scratch>").replace(str(ROOT), "<repo>") for part in cmd],
                "cwd": str(cwd).replace(str(work), "<scratch>").replace(str(ROOT), "<repo>"),
            }
            evidence["commands"].append(record)
            try:
                result = subprocess.run(cmd, cwd=cwd, env=env | (extra_env or {}),
                                        capture_output=True, text=True, timeout=timeout)
            except (OSError, subprocess.TimeoutExpired):
                raise CheckFailed(f"{Path(cmd[0]).name} unavailable or timed out") from None
            record["exit"] = result.returncode
            require(result.returncode == expected, f"{Path(cmd[0]).name} returned unexpected exit status")
            return result.stdout, result.stderr

        require(run("git", "rev-parse", "HEAD")[0].strip() == args.commit, "checkout SHA mismatch")
        require(not run("git", "status", "--porcelain", "--untracked-files=all")[0].strip(),
                "checkout must be clean")
        stage = "preflight"
        build = work / "build"
        core = build / "anopki-core"
        evidence["toolchain"] = {
            "cmake": run("cmake", "--version")[0].splitlines()[0],
            "openssl_cli": run("openssl", "version")[0].strip(),
        }
        run("cmake", "-S", ROOT, "-B", build, "-DANOPKI_ENTERPRISE_EDITION=ON",
            "-DANOPKI_PRODUCT_PROFILE=enterprise-openssl", "-DCMAKE_BUILD_TYPE=Debug",
            "-DBUILD_SHARED_LIBS=OFF", "-DBUILD_TESTING=ON")
        compiler = next(build.glob("CMakeFiles/*/CMakeCXXCompiler.cmake")).read_text()
        evidence["toolchain"]["compiler"] = {
            name.lower(): re.search(rf'set\(CMAKE_CXX_COMPILER_{name} "([^"]+)"', compiler)[1]
            for name in ("ID", "VERSION")
        }
        run("cmake", "--build", build, "--parallel", "4", timeout=600)
        evidence["backend"] = verify_backend(json.loads(run(core, "backend", "info")[0]))
        evidence["core_binary"] = {"location": "<scratch>/build/anopki-core", "sha256": sha256(core)}
        linked = run("ldd", core)[0]
        libraries = re.findall(r"^\s*(libcrypto\.\S+)\s+=>\s+(/\S+)", linked, re.M)
        require(len(libraries) == 1 and "anocrypto" not in linked.lower(), "unexpected core linkage")
        lib_name, lib_path = libraries[0]
        evidence["libcrypto"] = {"soname": lib_name, "sha256": sha256(Path(lib_path))}
        results = run("ctest", "--test-dir", build, "--no-tests=error", "--output-on-failure")[0]
        require("100% tests passed" in results and "Not Run" not in results, "native fixture tests did not pass")
        evidence["ctest"] = [line.strip() for line in results.splitlines()
                             if "Passed" in line or "tests passed" in line]
        evidence["preflight"] = "PASS"

        if args.approval:
            stage = "live_prepare"
            service_dir = ROOT / "service"
            go_version = run("go", "version", cwd=service_dir)[0].strip()
            version = re.fullmatch(r"go version go(\d+)\.(\d+)\.(\d+) linux/\w+", go_version)
            require(version and tuple(map(int, version.groups())) >= (1, 26, 11), "Go 1.26.11+ required")
            evidence["toolchain"]["go"] = go_version
            service = work / "anopki-service"
            run("go", "build", "-mod=readonly", "-trimpath", f"-ldflags=-X main.serviceCommit={args.commit}",
                "-o", service, "./cmd/anopki-service", cwd=service_dir, timeout=600)
            evidence["service_binary_sha256"] = sha256(service)
            stage = "live"
            exercise(work, core, service, evidence, run, verify_backend)
            require(sha256(core) == evidence["core_binary"]["sha256"], "core binary changed during run")
            evidence["live"] = "PASS"
    except (CheckFailed, KeyboardInterrupt, OSError, ValueError, KeyError, TypeError, StopIteration, http.client.HTTPException) as exc:
        evidence["failure_stage"] = stage
        # Never serialize subprocess output, request bodies, arbitrary API fields or exceptions.
        evidence["failure"] = str(exc) if isinstance(exc, CheckFailed) else type(exc).__name__
        if stage == "preflight":
            evidence["preflight"] = "FAIL"
        if stage == "live":
            evidence["live"] = "FAIL"
    finally:
        if scratch is not None:
            try:
                scratch.cleanup()
                evidence["cleanup"] = "PASS" if not Path(scratch.name).exists() else "FAIL"
            except OSError:
                evidence["cleanup"] = "FAIL"
        evidence["completed_at"] = datetime.now(timezone.utc).isoformat()
        print(json.dumps(evidence, indent=2))
    return int("failure" in evidence or evidence["cleanup"] == "FAIL")


if __name__ == "__main__":
    sys.exit(main())
