#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate that the Enterprise tree contains the expected private overlay boundary."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "ENTERPRISE-LICENSE-NOTICE.md",
    "enterprise/anocrypto/include/anocrypto/anocrypto.h",
    "enterprise/anocrypto/src/anocrypto.c",
    "src/core/crypto/anocrypto_backend.cpp",
    "include/anopki/enterprise/edition.hpp",
    "service/internal/enterprise/edition.go",
    "docs/enterprise/anocrypto-integration-plan.md",
    "docs/enterprise/kcmvp-preparation.md",
]

def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)

def main() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        fail("Enterprise tree missing required overlay files:\n" + "\n".join(missing))

    cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    for token in ["ANOPKI_ENTERPRISE_EDITION", "ANOPKI_ENTERPRISE_ANOCRYPTO_STUB", "anocrypto_c99"]:
        if token not in cmake:
            fail(f"Enterprise CMake missing {token}")

    docs = (ROOT / "docs/enterprise/anocrypto-integration-plan.md").read_text(encoding="utf-8")
    if "not KCMVP validated" not in docs or "skeleton" not in docs:
        fail("Enterprise AnoCrypto docs must clearly mark current implementation as skeleton/not validated")

    print("enterprise boundary ok")

if __name__ == "__main__":
    main()
