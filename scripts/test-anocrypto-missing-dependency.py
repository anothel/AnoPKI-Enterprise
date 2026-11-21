#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def check_linux_probe(target: Path, sdk: Path, soname: str) -> None:
    if not sdk.is_file() or not soname:
        raise SystemExit("missing positive-control SDK or SDK SONAME")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("LD_")}
    environment["LC_ALL"] = "C"
    present = subprocess.run(
        [str(target)], cwd=target.parent,
        env={**environment, "LD_LIBRARY_PATH": str(sdk.parent)},
        capture_output=True, text=True, check=False,
    )
    loaded = Path(present.stdout.strip())
    if present.returncode != 0 or not loaded.is_file() or not loaded.samefile(sdk):
        raise SystemExit(f"SDK-present control did not initialize the selected SDK: {present.stderr.strip()}")
    print(f"SDK-present control loaded the selected {soname}")

    absent = subprocess.run(
        [str(target)], cwd=target.parent, env=environment, capture_output=True, text=True, check=False,
    )
    expected = f"error while loading shared libraries: {soname}: cannot open shared object file"
    if absent.returncode != 127 or expected not in absent.stderr or absent.stdout.strip():
        raise SystemExit(
            f"SDK-absent control did not report missing {soname}: exit {absent.returncode}, {absent.stderr.strip()}"
        )
    print(f"SDK-absent control confirmed loader failure for {soname}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove a missing AnoCrypto runtime cannot fall back")
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--sdk-library", type=Path)
    parser.add_argument("--sdk-soname")
    args = parser.parse_args()
    if (args.sdk_library is None) != (args.sdk_soname is None):
        parser.error("--sdk-library and --sdk-soname must be supplied together")
    if not args.executable.is_file():
        raise SystemExit("missing test executable")
    with tempfile.TemporaryDirectory() as dirname:
        directory = Path(dirname)
        target = directory / args.executable.name
        shutil.copy2(args.executable, target)
        if args.sdk_library is not None:
            check_linux_probe(target, args.sdk_library.resolve(), args.sdk_soname)
            if any(directory.glob("*.json")):
                raise SystemExit("missing dependency produced success evidence")
            return 0

        environment = os.environ.copy()
        environment["PATH"] = os.pathsep.join(
            entry for entry in environment.get("PATH", "").split(os.pathsep)
            if "anocrypto-c-p3-10" not in entry.lower()
        )
        if os.name == "nt":
            ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)
        completed = subprocess.run([str(target)], cwd=directory, env=environment, capture_output=True, check=False)
        if completed.returncode == 0:
            raise SystemExit("executable succeeded without the AnoCrypto runtime dependency")
        if any(directory.glob("*.json")):
            raise SystemExit("missing dependency produced success evidence")
    print("AnoCrypto missing-dependency no-fallback test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
