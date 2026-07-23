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


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove a missing AnoCrypto runtime cannot fall back")
    parser.add_argument("--executable", required=True, type=Path)
    args = parser.parse_args()
    if not args.executable.is_file():
        raise SystemExit("missing test executable")
    with tempfile.TemporaryDirectory() as dirname:
        directory = Path(dirname)
        target = directory / args.executable.name
        shutil.copy2(args.executable, target)
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
