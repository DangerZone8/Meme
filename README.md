# It's Giving

It's Giving tracks webcam expressions and overlays a matching meme reaction. The Python engine opens a live preview window and can publish processed frames to OBS Virtual Camera for use in meeting apps.

## Windows portable build

The Windows workflow builds a portable Electron desktop executable with the Python camera engine bundled inside. The distributable is a single `.exe`; users do not need to extract a ZIP or run an installer.

On successful builds to `main`, GitHub Actions publishes the `.exe` itself as a GitHub Release asset using the automatically provided `GITHUB_TOKEN`. No manually configured secrets, Vercel Blob store, or Vercel environment variables are required.

The ScreenFilter website's `/download` endpoint redirects directly to the latest `.exe` asset:

`https://github.com/DangerZone8/Meme/releases/latest/download/ItsGiving-Desktop-0.3.0-Windows.exe`

The Release exists as the binary-hosting mechanism, but users clicking the website's Download button are sent directly to the executable rather than to the Release page. GitHub Actions artifacts remain available separately for CI diagnostics.

## OBS Virtual Camera

1. Install OBS Studio once so its Virtual Camera device/driver is registered.
2. Close OBS before starting It's Giving. The Python engine writes frames directly to the OBS Virtual Camera device through `pyvirtualcam`.
3. Start the meme camera from the desktop controller.
4. In Zoom, Google Meet, Teams, or Discord, select **OBS Virtual Camera** as the camera.
5. Do not also click **Start Virtual Camera** inside OBS while It's Giving is publishing to that same device.

The synthetic OBS CI test verifies that the backend opens and accepts frames. It does not prove that a physical webcam works, that a meeting app receives the stream, or that face tracking behaves correctly on a person's live camera. Those still require a real Windows webcam test.

## Local Python setup

Use Python 3.11 or 3.12:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r engine/requirements.txt
python its_giving_v2.py --calibrate
python its_giving_v2.py
```

The Windows CI build bundles the MediaPipe model files into the executable. For a local source run, the engine downloads missing model files on first launch.

## Camera performance benchmark

Run a 30-second benchmark with the same camera resolution you normally use:

```bash
python its_giving_v2.py --no-vcam --size 1280x720 --benchmark-seconds 30 --perf-stats
```

Then repeat without `--no-vcam` to include OBS Virtual Camera output. The final `BENCHMARK` line reports average loop FPS, capture-read time, MediaPipe inference time, render time, output time, read-to-preview processing time, and p95 frame time. The five-second `PERF` lines show rolling values. Try `--size 640x480` as a comparison, without changing gesture thresholds. The read-to-preview value is a software processing estimate, not sensor-to-screen latency; true camera latency needs an external high-speed-camera measurement.

The engine now makes its image-quality decision from a small 160-pixel-wide probe while applying any correction to the full-resolution frame. This avoids running a full-resolution 64-bit Laplacian on every frame.

## Desktop shell

See [desktop/README.md](desktop/README.md) for Electron development and packaging details.
