#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Exercise the existing runtime-evidence CLI using a local installed SDK."""

import json
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


CAPABILITIES = {
    "csr_inspect", "certificate_issue", "crl_generate", "crl_inspect",
    "ocsp_request_inspect", "ocsp_issuer_inspect", "ocsp_response_generate", "ocsp_responder_validate",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    executable = Path(sys.argv[1]).resolve()

    def run(*args, limit_write=False):
        command = [str(executable), *map(str, args)]
        if limit_write:
            # Ignore the signal so the actual write/close reports EFBIG to the probe.
            command = [
                sys.executable, "-c",
                "import os, resource, signal, sys; "
                "signal.signal(signal.SIGXFSZ, signal.SIG_IGN); "
                "resource.setrlimit(resource.RLIMIT_FSIZE, (1, 1)); "
                "os.execv(sys.argv[1], sys.argv[1:])",
                *command,
            ]
        return subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        valid = root / "valid.json"
        completed = run(valid)
        require(completed.returncode == 0, completed.stderr)
        info = json.loads(valid.read_text(encoding="utf-8"))
        require(set(info) == {
            "backend_id", "dependency", "runtime_version", "build_identity_abi",
            "build_fingerprint", "readiness", "capabilities",
        }, "runtime evidence schema mismatch")
        require(info["backend_id"] == "anocrypto-c" and info["dependency"] == "AnoCrypto-C",
                "runtime backend identity mismatch")
        require(info["runtime_version"] and info["build_identity_abi"] == 1 and info["readiness"] == "ready",
                "runtime version, ABI or readiness mismatch")
        require(re.fullmatch(r"sha256:[0-9a-f]{64}", info["build_fingerprint"]), "fingerprint mismatch")
        require(len(info["capabilities"]) == len(CAPABILITIES) and set(info["capabilities"]) == CAPABILITIES,
                "capability set mismatch")

        if sys.platform == "linux":
            rewritten = run(valid)
            require(rewritten.returncode == 0, rewritten.stderr)
            require(valid.is_file() and not valid.is_symlink(), "rewritten evidence is not a regular file")
            require(json.loads(valid.read_text(encoding="utf-8")) == info, "rewritten evidence changed")
            staging = root / "valid.json.tmp"
            require(not staging.exists() and not staging.is_symlink(), "rewrite left a staging entry")

        extra = root / "extra.json"
        require(run(extra, "unexpected").returncode != 0 and not extra.exists(), "invalid arguments published evidence")
        require(run("").returncode != 0, "empty output argument was accepted")
        missing = root / "absent" / "cannot-open.json"
        require(run(missing).returncode != 0 and not missing.exists(), "unwritable path published evidence")
        require(run(root).returncode != 0 and root.is_dir(), "directory output was accepted")
        existing = root / "occupied.json"
        reserved = root / "occupied.json.tmp"
        reserved.write_text("existing staging entry", encoding="utf-8")
        require(run(existing).returncode != 0 and not existing.exists(), "staging collision published evidence")
        require(reserved.read_text(encoding="utf-8") == "existing staging entry", "staging collision lost data")

        if sys.platform == "linux":
            unwritable = root / "failed-write.json"
            result = run(unwritable, limit_write=True)
            require(result.returncode != 0 and "could not write runtime evidence" in result.stderr, result.stderr)
            require(not unwritable.exists() and not (root / "failed-write.json.tmp").exists(),
                    "failed write left evidence or staging files")
            saved = valid.read_bytes()
            result = run(valid, limit_write=True)
            require(result.returncode != 0 and valid.read_bytes() == saved, "failed write replaced valid evidence")
            print("Runtime evidence controls passed: actual write failure and atomic publication")
        else:
            print("Linux RLIMIT_FSIZE write-failure control: NOT_RUN")
    print("Runtime evidence controls passed: valid schema, invalid arguments and unwritable destinations")


if __name__ == "__main__":
    main()
