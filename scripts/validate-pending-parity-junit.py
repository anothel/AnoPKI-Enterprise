#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Require the AnoCrypto pending parity CTest to remain explicitly skipped."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


TEST_NAME = "anopki.crypto_backend_parity.anocrypto_pending"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("junit", type=Path)
    args = parser.parse_args()
    cases = [case for case in ET.parse(args.junit).getroot().iter("testcase") if case.get("name") == TEST_NAME]
    if len(cases) != 1:
        raise SystemExit(f"expected exactly one pending parity result, found {len(cases)}")
    if cases[0].find("skipped") is None:
        raise SystemExit("AnoCrypto pending parity unexpectedly reported normal success")
    print("AnoCrypto pending parity remains explicitly skipped")


if __name__ == "__main__":
    main()
