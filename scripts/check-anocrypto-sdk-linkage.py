#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Check the Linux Enterprise/AnoCrypto-C CLI's runtime linkage."""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


OPENSSL_PREFIXES = ("OPENSSL_", "EVP_", "X509_", "OCSP_", "ASN1_", "BIO_", "EC_KEY_", "PEM_", "SSL_")
OPENSSL_LIBRARIES = ("libssl", "libcrypto", "libeay32", "ssleay32")
LDD_LINE = re.compile(r"(?:(?P<name>[^\s/]+)\s+=>\s+)?(?P<target>.+?)\s+\(0x[0-9a-fA-F]+\)")
SDK_NAME = re.compile(r"libanocrypto_c\.so(?:\.\d+)*")
SYMBOL_LINE = re.compile(r"(?P<symbol>[A-Za-z_.$][A-Za-z0-9_.$]*(?:@{1,2}[A-Za-z0-9_.$-]+)?)\s+[Uwv]")


def inspect(tool, *args):
    try:
        result = subprocess.run(
            [tool, *args], env={**os.environ, "LC_ALL": "C"}, capture_output=True,
            encoding="utf-8", check=False, timeout=30,
        )
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"{tool} inspection failed: {error}") from error
    if result.returncode != 0 or result.stderr.strip() or not result.stdout.strip():
        raise ValueError(f"{tool} inspection failed or produced unusable output")
    return result.stdout


def check_dependencies(output):
    sdk_mapped = False
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith("=> not found"):
            raise ValueError(f"unresolved runtime dependency: {line}")
        match = LDD_LINE.fullmatch(line)
        if not match:
            raise ValueError(f"malformed ldd output: {line}")
        name, target = match.group("name", "target")
        if not Path(target).is_absolute():
            if name is None and re.fullmatch(r"linux-(?:vdso|gate)\.so\.\d+", target):
                continue
            raise ValueError(f"malformed ldd dependency path: {line}")
        if any(token in candidate.casefold()
               for candidate in (name or "", Path(target).name)
               for token in OPENSSL_LIBRARIES):
            raise ValueError(f"forbidden OpenSSL dependency: {name or target}")
        if SDK_NAME.fullmatch(name or "") and SDK_NAME.fullmatch(Path(target).name):
            sdk_mapped = True
    if not sdk_mapped:
        raise ValueError("ldd did not resolve the AnoCrypto-C SDK")


def check_symbols(output):
    found = False
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        match = SYMBOL_LINE.fullmatch(line)
        if not match:
            raise ValueError(f"malformed nm output: {line}")
        found = True
        symbol = match["symbol"].split("@", 1)[0]
        if symbol.startswith(OPENSSL_PREFIXES):
            raise ValueError(f"forbidden OpenSSL import: {match['symbol']}")
    if not found:
        raise ValueError("nm returned no undefined symbol records")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    try:
        if not args.artifact.is_file():
            raise ValueError("missing Enterprise CLI")
        artifact = str(args.artifact.resolve())
        check_dependencies(inspect("ldd", artifact))
        check_symbols(inspect("nm", "-u", "--format=posix", artifact))
    except ValueError as error:
        print(f"AnoCrypto SDK linkage check failed: {error}", file=sys.stderr)
        return 1
    print("AnoCrypto SDK linkage check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
