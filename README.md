# It's Giving

It's Giving tracks webcam expressions and overlays a matching meme reaction. The Python engine opens a live preview window and can publish processed frames to OBS Virtual Camera for use in meeting apps.

## Windows portable build

The Windows workflow builds a portable Electron desktop executable with the Python camera engine bundled inside. The distributable is a single `.exe`; users do not need to extract a ZIP or run an installer.

The workflow keeps a zipped GitHub Actions artifact for CI diagnostics and uploads the actual `.exe` to a public Vercel Blob store using multipart upload. The website's `/download` endpoint redirects directly to the public `.exe` URL.

### Required publishing configuration

1. In the Vercel project connected to `screenfilter.vercel.app`, create a **public Vercel Blob** store.
2. Copy its read/write token and add it to GitHub repository **Settings → Secrets and variables → Actions** as `BLOB_READ_WRITE_TOKEN`.
3. Run the Windows workflow on `main`. It uploads `its-giving/ItsGiving-Desktop-0.3.0-Windows.exe` and prints the resulting direct download URL.
4. Add that URL to the Vercel project's **Production** environment variables as `WINDOWS_APP_URL`, then redeploy the website.

The Blob object uses a stable pathname and is overwritten by each successful main build. The Vercel website never proxies the large executable through a serverless function; it redirects the browser to the public Blob download URL.

`nightly.link` is not used for the direct EXE because it downloads GitHub Actions artifacts as ZIP archives. The public Blob URL serves the `.exe` itself.

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
