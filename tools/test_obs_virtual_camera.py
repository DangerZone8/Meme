#!/usr/bin/env python3
"""Exercise the OBS Virtual Camera backend without requiring a physical webcam."""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np
import pyvirtualcam


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--frames", type=int, default=90)
    args = parser.parse_args()
    if args.width < 80 or args.height < 80 or args.fps <= 0 or args.frames < 1:
        parser.error("width and height must be >= 80, fps must be > 0, and frames must be >= 1")

    started = time.monotonic()
    camera = None
    try:
        camera = pyvirtualcam.Camera(
            width=args.width,
            height=args.height,
            fps=args.fps,
            fmt=pyvirtualcam.PixelFormat.BGR,
            device="OBS Virtual Camera",
            backend="obs",
        )
        if camera.device != "OBS Virtual Camera" or camera.backend != "obs":
            raise RuntimeError(
                f"Wrong virtual camera selected: device={camera.device!r}, "
                f"backend={camera.backend!r}"
            )

        frame = np.zeros((args.height, args.width, 3), dtype=np.uint8)
        start_count = camera.frames_sent
        for index in range(args.frames):
            frame[:] = (24, 24, 24)
            x = int((index / max(args.frames - 1, 1)) * (args.width - 80))
            frame[40:args.height - 40, x:x + 80] = (40, 210, 255)
            camera.send(frame)
            camera.sleep_until_next_frame()

        sent = camera.frames_sent - start_count
        if sent != args.frames:
            raise RuntimeError(f"Expected {args.frames} frames sent, got {sent}")
        print(json.dumps({
            "status": "PASS",
            "device": camera.device,
            "backend": camera.backend,
            "width": args.width,
            "height": args.height,
            "fps_target": args.fps,
            "frames_sent": sent,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "backend": "obs",
            "device": "OBS Virtual Camera",
            "error": f"{type(exc).__name__}: {exc}",
        }, indent=2), file=sys.stderr)
        return 1
    finally:
        if camera is not None:
            camera.close()


if __name__ == "__main__":
    raise SystemExit(main())
