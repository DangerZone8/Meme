#!/usr/bin/env python3
"""Verify the Windows release bundle before it is uploaded or published.

This is a packaging verifier, not a substitute for testing webcam capture on a
physical Windows machine. It never opens the webcam or downloads MediaPipe models.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-dir", type=Path, required=True,
                        help="PyInstaller output directory containing ItsGiving.exe")
    parser.add_argument("--installer", type=Path, required=True,
                        help="Path to the compiled Inno Setup installer")
    args = parser.parse_args()

    app_dir = args.app_dir.resolve()
    exe = app_dir / "ItsGiving.exe"
    installer = args.installer.resolve()
    checks: list[dict[str, str]] = []

    if not exe.is_file():
        fail(f"packaged executable missing: {exe}")
    if exe.stat().st_size < 100_000:
        fail(f"packaged executable unexpectedly small ({exe.stat().st_size} bytes)")
    checks.append({"check": "packaged_executable_exists", "result": "PASS"})

    # --help exits before camera access and model downloads, making this a
    # deterministic smoke test suitable for a headless CI runner.
    try:
        proc = subprocess.run(
            [str(exe), "--help"],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except subprocess.TimeoutExpired:
        fail("packaged executable --help timed out after 45 seconds")
    if proc.returncode != 0:
        fail(
            f"packaged executable --help exited {proc.returncode}; "
            f"stdout={proc.stdout[-1000:]!r}; stderr={proc.stderr[-1000:]!r}"
        )
    help_text = (proc.stdout or "") + (proc.stderr or "")
    for expected in ("--camera", "--no-vcam", "--calibrate"):
        if expected not in help_text:
            fail(f"packaged executable help is missing expected option {expected}")
    checks.append({"check": "packaged_executable_cli_smoke_test", "result": "PASS"})

    if not installer.is_file():
        fail(f"installer missing: {installer}")
    size = installer.stat().st_size
    if size < 1_000_000:
        fail(f"installer unexpectedly small ({size} bytes); expected bundled runtime")
    with installer.open("rb") as handle:
        signature = handle.read(2)
    if signature != b"MZ":
        fail("installer does not have a Windows PE/DOS MZ signature")
    checks.append({"check": "windows_installer_exists_and_has_pe_signature", "result": "PASS"})

    report = {
        "status": "PASS",
        "scope": "packaging and CLI smoke test; physical webcam/virtual-camera test not performed",
        "app_executable": str(exe),
        "app_executable_bytes": exe.stat().st_size,
        "installer": str(installer),
        "installer_bytes": size,
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
