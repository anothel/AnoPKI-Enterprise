#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-checks for offline dependency license evidence validation."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate-third-party-notices.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_third_party_notices", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expect_failure(function, expected: str) -> None:
    try:
        function()
    except SystemExit as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError("third-party notice validation unexpectedly passed")


def main() -> None:
    validator = load_validator()
    inventory = json.loads((ROOT / "packaging/dependency-license-inventory.json").read_text(encoding="utf-8"))
    validator.validate(ROOT)

    bad_hash = copy.deepcopy(inventory)
    first = bad_hash["dependencies"][0]
    first["license_file_sha256"][first["license_files"][0]] = "0" * 64
    expect_failure(lambda: validator.validate_inventory(ROOT, bad_hash), "SHA-256 mismatch")

    bad_version = copy.deepcopy(inventory)
    next(item for item in bad_version["dependencies"] if item["type"] == "go-module")["version"] = "v0.0.0"
    expect_failure(lambda: validator.validate_inventory(ROOT, bad_version), "selected graph/inventory mismatch")

    inferred = copy.deepcopy(inventory)
    next(item for item in inferred["dependencies"] if item["type"] == "go-module")["license_expression"] = "MIT"
    expect_failure(lambda: validator.validate_inventory(ROOT, inferred), "license expression/evidence mismatch")

    unmapped = copy.deepcopy(inventory)
    next(item for item in unmapped["dependencies"] if item["module_or_package"] == "gopkg.in/yaml.v3")[
        "license_components"
    ] = []
    expect_failure(lambda: validator.validate_inventory(ROOT, unmapped), "license component mapping mismatch")

    missing = copy.deepcopy(inventory)
    missing["dependencies"] = [item for item in missing["dependencies"] if item["module_or_package"] != "github.com/google/uuid"]
    expect_failure(lambda: validator.validate_inventory(ROOT, missing), "selected graph/inventory mismatch")

    local = json.dumps(inventory).replace("service/go.mod", "C:/Users/example/go.mod", 1)
    assert validator.LOCAL_PATH_RE.search(local)

    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, ".gitattributes").write_text("LICENSES/** whitespace=-trailing-space\n", encoding="utf-8")
        expect_failure(lambda: validator.validate_attributes(Path(tmp)), "exact pinned evidence exception")
    print("third-party notice validator tests ok")


if __name__ == "__main__":
    main()
