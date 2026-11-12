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

## Optional Memento-54K video-understanding evaluation

Memento-54K is an optional offline evaluation dataset for timestamped, long-video question/answer understanding. It is **not** part of ScreenFilter's live webcam, expression, gesture, or meme-selection pipeline. Nothing is downloaded or bundled with the app unless a developer explicitly runs the evaluation tools.

Install the separate optional dependency and download only the annotation JSONL:

```bash
python -m pip install -r requirements-memento-eval.txt
python tools/memento_eval.py download --split test --cache-dir .cache/memento-54k
```

The training split can be downloaded explicitly with `--split train`. Dataset files are cached outside the application. The downloader retrieves annotations only; it does **not** fetch Ego4D videos or visual features. Any video access must be obtained independently through Ego4D and comply with its terms.

The evaluation harness accepts a JSONL file of model predictions. Each prediction row must contain `video_uid`, `sample_index` (zero-based row position in the downloaded test JSONL), `turn_index` (zero-based assistant-turn index within that sample), and `predicted_text`. `predicted_time` (seconds from video start) is optional:

```json
{"video_uid":"<test-video-uid>","sample_index":0,"turn_index":0,"predicted_text":"A person enters the room.","predicted_time":12.5}
```

Run the separate test-split evaluator:

```bash
python tools/memento_eval.py evaluate --annotations path/to/test.jsonl --predictions path/to/predictions.jsonl --timing-tolerance 2.0
```

It reports coverage, normalized exact match, token F1, temporal accuracy within the selected tolerance, and mean absolute timestamp error. These lexical metrics are diagnostics, not semantic-quality judgments. The test split is reserved for evaluation; do not train on it or deduplicate its samples by video UID. Pin a Hugging Face revision with `download --revision <commit>` for reproducible runs.

**Attribution and terms:** Memento annotation text and dataset organization are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribute *Memento: Toward an All-Day Proactive Assistant for Ultra-Long Streaming Video* ([paper](https://openreview.net/forum?id=FtdbdoGbk3)) and the [Memento-54K dataset](https://huggingface.co/datasets/liarzone/Memento-54K). Ego4D source videos are not included and remain subject to their own access and use terms; CC BY 4.0 for annotations does not grant rights to the videos, people, or third-party content depicted in them. See the [Ego4D access documentation](https://ego4d-data.org/docs/start-here/).

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
