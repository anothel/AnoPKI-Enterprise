#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-checks for deterministic third-party notice generation."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate-third-party-notices.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_third_party_notices", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    generator = load_generator()
    first = generator.build_outputs(ROOT)
    second = generator.build_outputs(ROOT)
    assert first == second
    inventory = json.loads(first[Path("THIRD_PARTY_NOTICES.json")])
    assert inventory["dependencies"] == sorted(inventory["dependencies"], key=generator.dependency_key)
    yaml = next(item for item in inventory["dependencies"] if item["module_or_package"] == "gopkg.in/yaml.v3")
    assert [item["license_expression"] for item in yaml["license_components"]] == ["MIT", "Apache-2.0"]
    assert "License component mapping" in first[Path("THIRD_PARTY_NOTICES.md")]
    assert not generator.LOCAL_PATH_RE.search("".join(first.values()))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr or result.stdout
    print("third-party notice generator tests ok")


if __name__ == "__main__":
    main()
