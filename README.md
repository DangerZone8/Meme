# It's Giving

It's Giving tracks webcam expressions and overlays a matching meme reaction. The Python engine opens a live preview window and can publish processed frames to OBS Virtual Camera for use in meeting apps.

## Windows portable build

The GitHub Actions workflow builds two artifacts on Windows:

- `ItsGiving-Engine-Windows-v0.3.0` — standalone Python engine.
- `ItsGiving-Electron-Portable-Windows-v0.3.0` — desktop controller with the engine bundled.

Open the **Windows portable app CI** workflow, select a successful run, and download the Electron portable artifact. Extract the ZIP and run `ItsGiving-Desktop-0.3.0-Windows.exe`. There is no setup wizard or installer.

This repository is public, so its Actions artifacts are downloadable by anyone with access to the repository. They are not private test downloads. Artifacts are retained for 14 days. The workflow does not publish a GitHub Release.

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

## Desktop shell

See [desktop/README.md](desktop/README.md) for Electron development and packaging details.
