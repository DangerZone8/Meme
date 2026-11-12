# ScreenFilter desktop shell

Electron provides the desktop controller. The Python/MediaPipe engine captures the webcam, applies the reactions, and publishes processed frames to the virtual camera.

## Windows build

The Windows workflow builds the Python engine, copies it into `desktop/resources/ItsGiving.exe`, and packages the Electron app. The setup helper `scripts/setup_virtual_camera.ps1` is bundled as `VirtualCameraSetup.ps1` so first-run setup works in the portable executable.

## Automatic virtual camera setup

The **Set up virtual camera** button runs the bundled PowerShell setup helper. It checks for OBS Studio and installs it silently with Windows Package Manager if needed, then registers the OBS Virtual Camera driver when the package provides its registration script. Windows displays an administrator approval prompt because installing a camera driver requires elevation. Users do not need to open OBS or configure scenes/sources.

After setup, restart ScreenFilter and the meeting app, start the ScreenFilter camera, and choose **OBS Virtual Camera** in the meeting app's camera settings. Do not start OBS's own Virtual Camera output while ScreenFilter is using the device.

## Meeting app instructions

- **Zoom:** Settings → Video & effects → Camera → OBS Virtual Camera.
- **Google Meet:** More options → Settings → Video → Camera → OBS Virtual Camera. Restart the browser if it was already open during driver installation.
- **Microsoft Teams:** Settings → Devices → Camera → OBS Virtual Camera; it is also available in pre-join device settings.

Menu names may differ slightly by version. The CI smoke test sends synthetic frames through the OBS backend. It does not verify a physical webcam or prove that frames arrive in a live Zoom/Meet/Teams call; those require an end-to-end Windows test.

## Local build

```powershell
pyinstaller --noconfirm --clean --onefile --windowed --name ItsGiving --collect-all mediapipe --collect-all cv2 --collect-all numpy --collect-all PIL --hidden-import pyvirtualcam --add-data "assets;assets" --add-data "models;models" its_giving_v2.py
New-Item -ItemType Directory -Force desktop/resources | Out-Null
Copy-Item dist/ItsGiving.exe desktop/resources/ItsGiving.exe -Force
Set-Location desktop
npm install
npm run dist:win
```
