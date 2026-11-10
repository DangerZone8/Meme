# It's Giving

It's Giving tracks webcam expressions and overlays a matching meme reaction. The Python engine opens a live preview window and can publish processed frames to OBS Virtual Camera for use in meeting apps.

## Windows portable build

The GitHub Actions workflow builds two artifacts on Windows:

- `ItsGiving-Engine-Windows-v0.3.0` — standalone Python engine.
- `ItsGiving-Electron-Portable-Windows-v0.3.0` — desktop controller with the engine bundled.

Open the **Windows portable app CI** workflow, select a successful run, and download the Electron portable artifact. Extract the ZIP and run `ItsGiving-Desktop-0.3.0-Windows.exe`. There is no setup wizard or installer.

## Website download — no secrets required

The website's `/download` route redirects to a public [nightly.link](https://nightly.link/) artifact URL for the latest successful Windows CI build on `main`. Visitors do not need to sign in to GitHub. The artifact is a ZIP; extract it and run `ItsGiving-Desktop-0.3.0-Windows.exe`. The website requires no Vercel environment variables, Vercel Blob, deployment token, or GitHub secret. nightly.link is an external service that brokers anonymous downloads of public GitHub Actions artifacts.

Every successful Windows CI run on `main` uploads a fresh artifact retained for 90 days. The download link automatically follows the newest successful build; no binary needs to be committed to the repository and no GitHub Release is created. If no unexpired successful artifact exists, the external download service reports that the artifact is unavailable.

The website itself continues to deploy from `main` through the existing Vercel Git integration. That integration is configured in the Vercel dashboard and does not require repository secrets.


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
