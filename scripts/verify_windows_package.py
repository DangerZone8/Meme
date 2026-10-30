#!/usr/bin/env python3
"""Verify the Windows release bundle and, optionally, a silent installation.

This checks packaging and CLI startup without opening a webcam or downloading
MediaPipe models. Physical webcam and virtual-camera behavior needs hardware testing.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def smoke_test(exe: Path, label: str) -> dict[str, str]:
    if not exe.is_file():
        fail(f"{label} executable missing: {exe}")
    if exe.stat().st_size < 100_000:
        fail(f"{label} executable unexpectedly small ({exe.stat().st_size} bytes)")
    try:
        proc = subprocess.run(
            [str(exe), "--help"], capture_output=True, text=True,
            timeout=45, check=False,
        )
    except subprocess.TimeoutExpired:
        fail(f"{label} executable --help timed out after 45 seconds")
    if proc.returncode != 0:
        fail(
            f"{label} executable --help exited {proc.returncode}; "
            f"stdout={proc.stdout[-1000:]!r}; stderr={proc.stderr[-1000:]!r}"
        )
    help_text = (proc.stdout or "") + (proc.stderr or "")
    for expected in ("--camera", "--no-vcam", "--calibrate"):
        if expected not in help_text:
            fail(f"{label} executable help is missing expected option {expected}")
    return {
        "check": f"{label.lower().replace(' ', '_')}_cli_smoke_test",
        "result": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-dir", type=Path, required=True,
                        help="PyInstaller output directory containing ItsGiving.exe")
    parser.add_argument("--installer", type=Path, required=True,
                        help="Path to the compiled Inno Setup installer")
    parser.add_argument("--installed-dir", type=Path,
                        help="Optional directory where the installer was installed")
    args = parser.parse_args()

    app_dir = args.app_dir.resolve()
    installer = args.installer.resolve()
    checks = [smoke_test(app_dir / "ItsGiving.exe", "Packaged app")]

    if not installer.is_file():
        fail(f"installer missing: {installer}")
    size = installer.stat().st_size
    if size < 1_000_000:
        fail(f"installer unexpectedly small ({size} bytes); expected bundled runtime")
    with installer.open("rb") as handle:
        signature = handle.read(2)
    if signature != b"MZ":
        fail("installer does not have a Windows PE/DOS MZ signature")
    checks.append({
        "check": "windows_installer_exists_and_has_pe_signature",
        "result": "PASS",
    })

    installed_exe = None
    if args.installed_dir is not None:
        installed_exe = args.installed_dir.resolve() / "ItsGiving.exe"
        checks.append(smoke_test(installed_exe, "Installed app"))

    report = {
        "status": "PASS",
        "scope": "bundle/installer and CLI startup; no physical webcam test performed",
        "app_executable": str(app_dir / "ItsGiving.exe"),
        "app_executable_bytes": (app_dir / "ItsGiving.exe").stat().st_size,
        "installer": str(installer),
        "installer_bytes": size,
        "installed_executable": str(installed_exe) if installed_exe else None,
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
