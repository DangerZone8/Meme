#!/usr/bin/env python3
"""Verify the integrity and launchability of the ItsGiving portable Windows executable."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path


def inspect_pe(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"Executable not found: {path}")
    size = path.stat().st_size
    if size < 50_000_000:
        raise ValueError(f"Executable is suspiciously small ({size:,} bytes)")
    with path.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise ValueError("Missing DOS MZ header")
        stream.seek(0x3C)
        raw_offset = stream.read(4)
        if len(raw_offset) != 4:
            raise ValueError("Truncated DOS header")
        pe_offset = struct.unpack("<I", raw_offset)[0]
        if pe_offset < 64 or pe_offset > min(size - 6, 16 * 1024 * 1024):
            raise ValueError(f"Invalid PE header offset: {pe_offset}")
        stream.seek(pe_offset)
        if stream.read(4) != b"PE\0\0":
            raise ValueError("Missing PE signature")
        machine_raw = stream.read(2)
        if len(machine_raw) != 2:
            raise ValueError("Truncated PE file header")
        machine = struct.unpack("<H", machine_raw)[0]
    if machine != 0x8664:
        raise ValueError(f"Expected x64 Windows executable (0x8664), got 0x{machine:04x}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": str(path),
        "size_bytes": size,
        "architecture": "x64",
        "format": "PE",
        "sha256": digest.hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--smoke-test", action="store_true",
                        help="launch the executable with --help and require exit code 0")
    args = parser.parse_args()
    try:
        result = inspect_pe(args.executable.resolve())
        result["smoke_test"] = "not_requested"
        if args.smoke_test:
            env = os.environ.copy()
            completed = subprocess.run(
                [str(args.executable.resolve()), "--help"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=90,
                check=False,
                env=env,
            )
            result["smoke_test"] = {
                "exit_code": completed.returncode,
                "passed": completed.returncode == 0,
                "output_excerpt": completed.stdout.decode("utf-8", errors="replace")[-1500:],
            }
            if completed.returncode != 0:
                raise ValueError(f"Executable smoke test failed (exit {completed.returncode})")
        print(json.dumps({"status": "PASS", **result}, indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
