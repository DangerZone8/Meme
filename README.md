# It's Giving

It's Giving tracks webcam expressions and overlays a matching meme reaction. The Python engine opens a live preview window and can publish processed frames to OBS Virtual Camera for use in meeting apps.

## Windows portable build

The GitHub Actions workflow builds two artifacts on Windows:

- `ItsGiving-Engine-Windows-v0.3.0` — standalone Python engine.
- `ItsGiving-Electron-Portable-Windows-v0.3.0` — desktop controller with the engine bundled.

Open the **Windows portable app CI** workflow, select a successful run, and download the Electron portable artifact. Extract the ZIP and run `ItsGiving-Desktop-0.3.0-Windows.exe`. There is no setup wizard or installer.

## Website download — no Vercel secrets required

The website's `/download` route redirects to `/downloads/ItsGiving.exe`, a static executable served by Vercel. The site does not need `WINDOWS_APP_URL`, Vercel Blob, or any Vercel API credentials at runtime.

To publish an updated Windows app:

1. Run **Actions → Windows portable app CI → Run workflow** on `main`.
2. The workflow builds and verifies the portable Electron app, then opens a PR containing the executable under `public/downloads/ItsGiving.exe`.
3. Review and merge that PR. The existing Vercel Git integration deploys the static file with the website.

The publishing workflow uses GitHub's automatically provided `GITHUB_TOKEN`; it does not require `BLOB_READ_WRITE_TOKEN`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, or `VERCEL_PROJECT_ID`. The generated executable must remain below GitHub's 100 MB per-file limit. If it exceeds the configured safety limit, publication stops with a clear error instead of creating a broken PR.

The website itself remains deployable from `main` through the existing Vercel Git integration. If that integration is disconnected, reconnect the GitHub repository in Vercel; no deployment secrets need to be added to this repository.

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
