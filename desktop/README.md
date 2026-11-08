# It's Giving desktop shell

Electron provides the desktop controller. The Python/MediaPipe engine remains responsible for webcam capture, expression tracking, meme overlays, and virtual-camera frames.

## Build on Windows

1. Build the engine first with the repository's Windows workflow, producing `dist/ItsGiving.exe`.
2. Copy that file to `desktop/resources/ItsGiving.exe`.
3. From this directory run `npm ci` (after committing the generated lockfile) and `npm run dist:win`.
4. The portable Electron build is emitted under `release/`.

The desktop shell launches the engine as a child process and terminates it when the app closes. The webcam preview remains the engine's OpenCV window.

## Meeting apps and OBS

The engine uses `pyvirtualcam` to publish processed frames when a compatible virtual-camera backend is installed. In Zoom, Google Meet, Teams, or Discord, choose the virtual camera exposed by the engine. If it is not listed, install OBS Studio and start OBS Virtual Camera; choose **OBS Virtual Camera** in the meeting app. OBS Virtual Camera is a camera endpoint, not a filter that automatically receives the engine frames: if the engine's own virtual camera is unavailable, a dedicated OBS scene/source bridge is still needed.

Camera use is opt-in: users press Start, can stop the engine, and should tell meeting participants when using effects.
