# It's Giving desktop shell

Electron provides the desktop controller. The Python/MediaPipe engine remains responsible for webcam capture, expression tracking, meme overlays, and virtual-camera frames.

## Windows build

The repository's **Windows portable app CI** workflow builds the Python engine first, copies it into `desktop/resources/ItsGiving.exe`, and packages the Electron app with electron-builder. The portable executable is emitted under `desktop/dist/` and uploaded as the `ItsGiving-Electron-Portable-Windows-v0.3.0` Actions artifact.

For a local build, first create the engine executable at the repository root:

```powershell
pyinstaller --noconfirm --clean --onefile --windowed --name ItsGiving --collect-all mediapipe --collect-all cv2 --collect-all numpy --collect-all PIL --hidden-import pyvirtualcam --add-data "assets;assets" --add-data "models;models" its_giving_v2.py
New-Item -ItemType Directory -Force desktop/resources | Out-Null
Copy-Item dist/ItsGiving.exe desktop/resources/ItsGiving.exe -Force
Set-Location desktop
npm install
npm run dist:win
```

The desktop shell launches the engine as a child process and terminates it when the app closes. The webcam preview remains the engine's OpenCV window.

## OBS Virtual Camera

The engine connects directly to `OBS Virtual Camera` using the OBS backend in `pyvirtualcam`. Install OBS Studio once to register that device, then **close OBS before starting It's Giving**. Select **OBS Virtual Camera** in Zoom, Google Meet, Teams, or Discord. Do not also start OBS's own Virtual Camera output while the engine is using the device; both would compete for the same endpoint.

The CI smoke test opens that backend and sends synthetic frames. It does not test a physical webcam or verify reception inside a meeting app. Those require a live Windows test.

Camera use is opt-in: users press Start, can stop the engine, and should tell meeting participants when using effects.
