# It's giving...

Pull a face at your webcam. It's Giving tracks your face and expressions, then
drops a matching meme over your head. Point Zoom at its virtual camera and the
whole call sees it.

## Windows test build

The CI workflow builds a Windows installer from \`its_giving_v2.py\`, checks
Python syntax and dependency consistency, packages the app, runs the installer
silently, and verifies the installed files. The test artifact is named
\`ItsGiving-Test-v0.1.0-Windows\` and is retained for 7 days. Open **Actions**,
select **Windows app CI and private test build**, open a successful run, and
download that artifact. Extract it and run \`ItsGiving-Setup.exe\`.

**Privacy note:** GitHub Actions artifacts in a public repository are not
private to the repository owner. Do not treat this artifact as owner-only unless
the repository itself is private. This test workflow does not publish a GitHub
Release or upload a public Vercel Blob. Webcam and virtual-camera behavior still
needs testing on your actual Windows machine.

The first launch downloads MediaPipe model files and therefore needs an internet
connection. Allow camera access when Windows prompts you. Virtual-camera output
may require a separately installed backend such as OBS.

## Setup

\`\`\`bash
python3.12 -m venv venv
source venv/bin/activate           # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
\`\`\`

Python 3.11 or 3.12. Three MediaPipe models download themselves on first run.
