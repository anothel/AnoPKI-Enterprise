#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


ADAPTER = Path("src/backends/anocrypto_c")
FORBIDDEN_DEPENDENCIES = (
    "libcrypto",
    "libssl",
    "libeay32",
    "ssleay32",
)
OPENSSL_CALL = re.compile(r"\b(?:ASN1|BIO|BN|EC_KEY|EVP|OCSP|OPENSSL|PEM|RSA|X509)_[A-Za-z0-9_]+\s*\(")
OPENSSL_SYMBOL = re.compile(r"(?<![A-Za-z0-9_])(?:ASN1|BIO|EC_KEY|EVP|OCSP|OPENSSL|PEM|SSL|X509)_[A-Za-z0-9_]+")
GENERIC_SHA1 = re.compile(r"\bano_crypto_(?:hash|signature)_[A-Za-z0-9_]*sha1", re.IGNORECASE)
REQUIRED_TOKENS = (
    "ano_crypto_module_init",
    "ano_crypto_module_shutdown",
    "ano_crypto_rsa_key_import",
    "ano_crypto_ec_p256_key_import",
    "ano_crypto_key_destroy",
    "ano_crypto_signature_sign",
    "ano_crypto_signature_verify",
    "ano_crypto_ocsp_certid_sha1_digest",
    "fallback_used\\\":false",
    "provider.key_binding_mismatch",
    "provider.exportability_violation",
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def source_files(root: Path) -> list[Path]:
    directory = root / ADAPTER
    if not directory.is_dir():
        fail(f"missing AnoCrypto adapter directory: {ADAPTER.as_posix()}")
    files = sorted(path for path in directory.rglob("*") if path.suffix in {".cpp", ".hpp", ".h"})
    if not files:
        fail("AnoCrypto adapter has no source files")
    return files


def validate_sources(root: Path) -> None:
    combined = ""
    for path in source_files(root):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()
        combined += text
        if re.search(r"#\s*include\s*[<\"]openssl/", text, re.IGNORECASE):
            fail(f"OpenSSL include below AnoCrypto adapter: {relative}")
        if OPENSSL_CALL.search(text):
            fail(f"OpenSSL API below AnoCrypto adapter: {relative}")
        if "anopki::crypto::openssl" in text or "openssl_adapter" in text:
            fail(f"OpenSSL adapter reference below AnoCrypto adapter: {relative}")
        if GENERIC_SHA1.search(text):
            fail(f"generic SHA-1 use below AnoCrypto adapter: {relative}")

    missing = [token for token in REQUIRED_TOKENS if token not in combined]
    if missing:
        fail("AnoCrypto boundary tokens missing:\n" + "\n".join(missing))


def reject_forbidden(text: str, context: str) -> None:
    lowered = text.lower()
    hits = sorted({token for token in FORBIDDEN_DEPENDENCIES if token in lowered})
    if hits:
        fail(f"forbidden OpenSSL dependency in {context}: {', '.join(hits)}")
    symbol = OPENSSL_SYMBOL.search(text)
    if symbol:
        fail(f"forbidden OpenSSL symbol in {context}: {symbol.group(0)}")


def dependency_command(tool: Path, artifact: Path) -> list[str]:
    name = tool.name.lower()
    if name in {"link", "link.exe", "dumpbin", "dumpbin.exe"}:
        return [str(tool), "/dump", "/dependents", str(artifact)]
    if "llvm-readobj" in name:
        return [str(tool), "--coff-imports", str(artifact)]
    if re.search(r"(?:^|-)readelf(?:-[0-9]+)?(?:\.exe)?$", name):
        return [str(tool), "-d", str(artifact)]
    if re.search(r"(?:^|-)objdump(?:-[0-9]+)?(?:\.exe)?$", name):
        return [str(tool), "-p", str(artifact)]
    fail(f"unsupported dependency reader: {tool}")


def inspect_artifact(label: str, artifact: Path, tool: Path) -> None:
    if not artifact.is_file():
        fail(f"missing dependency-purity artifact {label}: {artifact}")
    reject_forbidden(artifact.read_bytes().decode("latin-1", errors="ignore"), f"artifact {label}")
    command = dependency_command(tool, artifact)
    try:
        completed = subprocess.run(command, capture_output=True, text=True, errors="replace", check=False,
                                   env={**os.environ, "LC_ALL": "C"})
    except OSError as error:
        fail(f"could not execute dependency reader {tool}: {error}")
    output = completed.stdout + completed.stderr
    if completed.returncode != 0:
        fail(f"dependency inspection failed for {label}: {' '.join(command)}\n{output.strip()}")
    if command[1] == "-d" and (completed.stderr.strip() or not re.search(
        r"^\s*(?:Dynamic section at offset |There is no dynamic section in this file\.)",
        completed.stdout, re.MULTILINE
    )):
        fail(f"invalid ELF dependency reader output for {label}: {output.strip()}")
    reject_forbidden(output, f"dependency table {label}")
    dependencies = [
        line.strip()
        for line in output.splitlines()
        if re.fullmatch(r"[^\s]+\.(?:dll|so|dylib)", line.strip(), re.IGNORECASE)
    ]
    print(f"{label}: {artifact}")
    print("  dependencies: " + (", ".join(dependencies) if dependencies else "none (static/import scan clean)"))


def parse_artifact(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("artifact must be LABEL=PATH")
    label, path = value.split("=", 1)
    if not label or not path:
        raise argparse.ArgumentTypeError("artifact must be LABEL=PATH")
    return label, Path(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AnoCrypto no-OpenSSL source and artifact boundaries")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dependency-tool", type=Path)
    parser.add_argument("--artifact", action="append", type=parse_artifact, default=[])
    args = parser.parse_args()
    try:
        validate_sources(args.root.resolve())
        if args.artifact and args.dependency_tool is None:
            fail("--dependency-tool is required with --artifact")
        for label, artifact in args.artifact:
            inspect_artifact(label, artifact, args.dependency_tool)
    except RuntimeError as error:
        print(f"AnoCrypto boundary validation failed: {error}", file=sys.stderr)
        return 1
    print("AnoCrypto boundary validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
