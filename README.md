# ScreenFilter

ScreenFilter tracks webcam expressions and overlays matching meme reactions. Its Windows desktop app can publish the processed frames as a virtual camera for Zoom, Google Meet, Microsoft Teams, and other meeting apps.

## Windows portable build

The Windows workflow builds a portable Electron desktop executable with the Python camera engine bundled inside. The distributable is a single `.exe`; users do not need to extract a ZIP or run an installer.

On successful builds to `main`, GitHub Actions publishes the `.exe` itself as a GitHub Release asset using the automatically provided `GITHUB_TOKEN`. The website's `/download` endpoint redirects directly to the latest executable:
`https://github.com/DangerZone8/Meme/releases/latest/download/ItsGiving-Desktop-0.3.0-Windows.exe`

## One-click virtual camera setup

1. Launch ScreenFilter and click **Set up virtual camera** once.
2. Approve the Windows administrator prompt. ScreenFilter installs OBS Studio's virtual-camera components and registers the device automatically; users do not need to open or configure OBS.
3. Restart ScreenFilter and the meeting app if either was already open.
4. Start ScreenFilter's camera. In the meeting app, select **OBS Virtual Camera** as the camera source.

The setup requires an internet connection, Windows Package Manager (`winget`), and administrator approval. The virtual-camera driver is a Windows system component, so it cannot be registered silently without elevated permission. ScreenFilter does not start OBS itself.

### Zoom

Open **Settings → Video & effects → Camera** and choose **OBS Virtual Camera**. In a meeting, use the arrow beside the Video button to select the same camera.

### Google Meet

Before or during a meeting, open **More options → Settings → Video → Camera** and choose **OBS Virtual Camera**. If it does not appear, restart the browser after completing setup.

### Microsoft Teams

Open **Settings → Devices → Camera** and choose **OBS Virtual Camera**. You can also select it in the pre-join device settings.

The exact menu labels may vary slightly by app version. The CI virtual-camera smoke test verifies that the OBS backend opens and accepts synthetic frames; it does not prove reception in a real meeting call. A live Windows webcam and meeting-app test is still required for end-to-end confirmation.

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

The Windows CI build bundles MediaPipe model files into the executable. For a local source run, the engine downloads missing model files on first launch.

## Desktop shell

See [desktop/README.md](desktop/README.md) for Electron development and packaging details.
