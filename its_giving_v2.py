#!/usr/bin/env python3
"""
its_giving_v2.py — meme reactions on top of your face, live in Zoom / Meet.

Same as its_giving.py, but expression thresholds are measured in standard
deviations above your own resting face rather than against fixed constants.
Seven seconds of calibration; see README.md.

  python its_giving_v2.py --calibrate
  python its_giving_v2.py [--camera 1] [--no-vcam] [--size 640x480] [--no-flip]

Keys:  q quit   d toggle HUD   c recalibrate   1-9 0 - = [ ] force-show a pose
"""
import argparse
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

POSES = ["time_out", "heart", "cover_nose", "crashing_out", "dance", "nose_closed", "flirty", "hand_up",
         "tongue_out", "open_mouth", "disgusted", "talking_to_wall", "suspicious", "spin",
         "shocked", "laughing", "crying", "confused", "facepalm", "clapping", "head_nod",
         "head_shake", "shrug", "arms_up", "angry", "wink"]
TEST_KEYS = "1234567890-=[]"

FACE_SCALE = 2.0
HOLD_FRAMES = 8
# Trigger on the first confident frame. Assets are preloaded at startup, so
# reaction changes never wait for disk access.
ARM = {pose: 1 for pose in POSES}
ARM["spin"] = 3

Z = dict(
    jaw_open=3.8,
    scream_jaw=2.8,
    tongue_jaw=2.8,
    sneer=3.0,
    disgust=9.0,
    squint=2.8,
)
Z_CAP = 8.0
FLOOR = dict(
    jaw_open=0.30,
    scream_jaw=0.18,
    tongue_jaw=0.18,
    sneer=0.06,
    squint=0.18,
)
T = dict(
    tongue=0.32,
    head_turn=0.11,
    gesture=0.022,
)

CALIB_FILE = "calibration.json"
CALIB_SECONDS = 7.0
CALIB_WARMUP = 1.5
CALIB_MIN_SAMPLES = 30
SIGMA_FLOOR = 0.015
SIGMA_CEIL = 0.080
CALIB_VERSION = 1

GENERIC_SIGMA = 0.035
GENERIC_MEAN = {
    "jawOpen": 0.08, "eyeSquintLeft": 0.10, "eyeSquintRight": 0.10,
    "eyeBlinkLeft": 0.10, "eyeBlinkRight": 0.10, "noseSneerLeft": 0.03, "noseSneerRight": 0.03,
    "browDownLeft": 0.06, "browDownRight": 0.06, "mouthFrownLeft": 0.05, "mouthFrownRight": 0.05,
    "mouthUpperUpLeft": 0.05, "mouthUpperUpRight": 0.05,
}

INNER_LIPS = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]

MODELS = {
    "face_landmarker.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "face_detector.tflite": "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
    "hand_landmarker.task": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
    "pose_landmarker_lite.task": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
}
# PyInstaller extracts bundled read-only resources into _MEIPASS in one-file mode.
RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
HERE = RESOURCE_DIR
if getattr(sys, "frozen", False):
    USER_DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ItsGiving")
else:
    USER_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(USER_DATA_DIR, exist_ok=True)


def ensure_models():
    mdir = os.path.join(HERE, "models")
    os.makedirs(mdir, exist_ok=True)
    paths = {}
    for name, url in MODELS.items():
        path = os.path.join(mdir, name)
        if not os.path.exists(path):
            print(f"Downloading {name} ...")
            urllib.request.urlretrieve(url, path)
        paths[name] = path
    return paths


def preflight(model_path):
    """Preflight native MediaPipe startup when running from a real Python interpreter.

    In a PyInstaller-frozen Windows app, sys.executable points to ItsGiving.exe,
    not python.exe. Spawning it with ``-c`` would relaunch this app with invalid
    arguments and make startup fail before the webcam preview appears. The
    packaged app initializes its real detectors immediately afterward, so skip
    only this interpreter-specific subprocess probe when frozen.
    """
    if getattr(sys, "frozen", False):
        return
    code = (
        "import sys\n"
        "from mediapipe.tasks import python as t\n"
        "from mediapipe.tasks.python import vision\n"
        "vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(\n"
        "    base_options=t.BaseOptions(model_asset_path=sys.argv[1]),\n"
        "    running_mode=vision.RunningMode.VIDEO, num_faces=8,\n"
        "    output_face_blendshapes=True)).close()\n"
    )
    proc = subprocess.run([sys.executable, "-c", code, model_path], capture_output=True, text=True)
    if proc.returncode == 0:
        return
    err = (proc.stderr or "") + (proc.stdout or "")
    print(f"\nMediaPipe cannot start a detector here (python {platform.python_version()}, "
          f"mediapipe {getattr(mp, '__version__', '?')}, exit {proc.returncode}).\n")
    if "Service is unavailable" in err or "MetalHelper" in err or proc.returncode == -6:
        print("Cause: mediapipe 0.10.30+ ships macOS wheels that abort on startup.\n"
              "Fix (Python 3.11 or 3.12) — install the pinned set:\n"
              "  pip install -r requirements.txt\n"
              "If you already installed something newer by hand, force it back:\n"
              '  pip install "mediapipe==0.10.21" "numpy<2" "opencv-python<5" "opencv-contrib-python<5"\n')
    else:
        print(err[-1500:])
    sys.exit(1)


def build_detectors(model_paths):
    face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=model_paths["face_landmarker.task"]),
        running_mode=vision.RunningMode.VIDEO, num_faces=8, output_face_blendshapes=True))
    # FaceLandmarker does not expose its internal detector score. Run the lightweight
    # FaceDetector alongside it so the HUD can show a real detector confidence.
    score_face = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=model_paths["face_detector.tflite"]),
        running_mode=vision.RunningMode.VIDEO, min_detection_confidence=0.0))
    hand = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=model_paths["hand_landmarker.task"]),
        running_mode=vision.RunningMode.VIDEO, num_hands=8))
    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=model_paths["pose_landmarker_lite.task"]),
        running_mode=vision.RunningMode.VIDEO, num_poses=8))
    return face, score_face, hand, pose


class Clock:
    """Strictly increasing timestamps for the life of a detector, recalibrations included."""

    def __init__(self):
        self.t0, self.last = time.monotonic(), -1

    def next(self):
        self.last = max(int((time.monotonic() - self.t0) * 1000), self.last + 1)
        return self.last


class Baseline:
    """Your resting face: a mean and a wobble for every channel."""

    def __init__(self, mean=None, sigma=None, samples=0, made=None):
        self.mean = mean or {}
        self.sigma = sigma or {}
        self.samples = samples
        self.made = made
        self.generic = not self.mean

    def z(self, name, value):
        """How far above your neutral this channel is, in standard deviations."""
        if self.generic:
            return (value - GENERIC_MEAN.get(name, 0.02)) / GENERIC_SIGMA
        m = self.mean.get(name)
        if m is None:
            return (value - GENERIC_MEAN.get(name, 0.02)) / GENERIC_SIGMA
        return (value - m) / self.sigma.get(name, SIGMA_CEIL)

    @property
    def neutral_turn(self):
        return self.mean.get("turn_signed", 0.0) if not self.generic else 0.0

    def save(self, path):
        with open(path, "w") as fh:
            json.dump({"version": CALIB_VERSION, "made": self.made, "samples": self.samples,
                       "mean": self.mean, "sigma": self.sigma}, fh, indent=1, sort_keys=True)

    @staticmethod
    def load(path):
        try:
            with open(path) as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return Baseline()
        if data.get("version") != CALIB_VERSION or not data.get("mean"):
            return Baseline()
        return Baseline(data["mean"], data.get("sigma", {}), data.get("samples", 0), data.get("made"))


class Collector:
    """Running mean and standard deviation per channel, over the calibration window."""

    def __init__(self):
        self.n, self.s, self.ss = 0, {}, {}

    def add(self, face):
        self.n += 1
        for name, v in list(face.bs.items()) + [("turn_signed", face.turn_signed)]:
            self.s[name] = self.s.get(name, 0.0) + v
            self.ss[name] = self.ss.get(name, 0.0) + v * v

    def finish(self):
        mean, sigma = {}, {}
        for name, total in self.s.items():
            m = total / self.n
            var = max(self.ss[name] / self.n - m * m, 0.0)
            mean[name] = round(m, 5)
            sigma[name] = round(min(max(var ** 0.5, SIGMA_FLOOR), SIGMA_CEIL), 5)
        sigma["turn_signed"] = min(max(sigma.get("turn_signed", 0.02), 0.01), 0.10)
        return Baseline(mean, sigma, self.n, time.strftime("%Y-%m-%d %H:%M"))


def calibration_warnings(base):
    """Catch the two ways a calibration goes wrong: mid-expression, or fidgeting."""
    out = []
    if base.mean.get("jawOpen", 0) > 0.30:
        out.append("your mouth looks like it was open — don't talk during calibration")
    if max(base.mean.get("noseSneerLeft", 0), base.mean.get("noseSneerRight", 0)) > 0.15:
        out.append("your nose was scrunched — hold a bored face, not a reaction")
    if max(base.mean.get("browInnerUp", 0), base.mean.get("browOuterUpLeft", 0)) > 0.35:
        out.append("your eyebrows were up — relax them")
    pinned = sum(1 for k, v in base.sigma.items() if v >= SIGMA_CEIL)
    if pinned > 12:
        out.append("you moved a lot — sit still and try again for a tighter baseline")
    return out


def run_calibration(cap, face_det, clock, args, W, H, window):
    """Watch a bored face for CALIB_SECONDS and learn what its channels rest at."""
    print(f"\nCalibrating for {CALIB_SECONDS:.0f}s. Sit how you normally sit, look at the "
          "camera, hold a bored face.\nBlinking is fine. Don't talk, smile or raise your eyebrows.")
    col, start, seen_face = Collector(), time.monotonic(), 0
    while True:
        elapsed = time.monotonic() - start
        if elapsed > CALIB_SECONDS:
            break
        ok, frame = cap.read()
        if not ok:
            break
        if frame.shape[0] != H or frame.shape[1] != W:
            frame = cv2.resize(frame, (W, H))
        if not args.no_flip:
            frame = cv2.flip(frame, 1)
        frame = enhance_camera_frame(frame)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        fr = face_det.detect_for_video(mp_img, clock.next())
        face = Face(fr.face_landmarks[0], fr.face_blendshapes[0] if fr.face_blendshapes else None, W, H) \
            if fr.face_landmarks else None
        if face is not None:
            seen_face += 1
            if elapsed > CALIB_WARMUP and face.bs:
                col.add(face)
        draw_calibration(frame, elapsed, col.n, face)
        cv2.imshow(window, frame)
        if (cv2.waitKey(1) & 0xFF) == ord("q"):
            print("Calibration cancelled.")
            return None

    if col.n < CALIB_MIN_SAMPLES:
        print(f"Calibration failed: only {col.n} usable frames"
              f"{' — your face was never detected' if not seen_face else ''}.\n"
              "  - light your face from the front, sit head-and-shoulders in frame, and try again")
        return None
    base = col.finish()
    print(f"Calibrated on {base.samples} frames. Your neutral face:")
    for name in ("jawOpen", "noseSneerLeft", "browDownLeft", "mouthFrownLeft", "eyeSquintLeft"):
        if name in base.mean:
            print(f"  {name:16s} {base.mean[name]:.3f} ± {base.sigma[name]:.3f}")
    for w in calibration_warnings(base):
        print(f"  ! {w}")
    return base


def draw_calibration(img, elapsed, samples, face):
    H, W = img.shape[:2]
    left = max(0.0, CALIB_SECONDS - elapsed)
    cv2.rectangle(img, (0, 0), (W, 96), (0, 0, 0), -1)
    cv2.putText(img, "CALIBRATING - hold a bored face", (16, 34), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 255), 2)
    cv2.putText(img, f"{left:0.1f}s   {samples} frames" + ("" if face is not None else "   NO FACE"),
                (16, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255) if face is not None else (0, 140, 255), 2)
    done = int(W * min(elapsed / CALIB_SECONDS, 1.0))
    cv2.rectangle(img, (0, 84), (done, 96), (0, 220, 0), -1)
    if face is not None:
        x0, y0, x1, y1 = face.box
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 220, 0), 1)


class Asset:
    """One reaction: a list of BGRA frames plus per-frame durations (ms) for GIFs."""

    def __init__(self, frames, durations):
        self.frames = frames
        self.durations = durations
        self.cum = np.cumsum(durations)
        self.total = int(self.cum[-1])
        h, w = frames[0].shape[:2]
        self.aspect = w / h
        self._cache = {}

    def frame_at(self, ms):
        if len(self.frames) == 1:
            return 0
        return int(np.searchsorted(self.cum, ms % self.total, side="right"))

    def scaled(self, idx, height):
        key = (idx, height)
        if key not in self._cache:
            if len(self._cache) > 64:
                self._cache.clear()
            w = max(1, int(round(height * self.aspect)))
            self._cache[key] = cv2.resize(self.frames[idx], (w, height), interpolation=cv2.INTER_AREA)
        return self._cache[key]


def to_bgra(img):
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    if img.shape[2] == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return img


def placeholder(label):
    """Create a lightweight original reaction sticker when no custom art exists."""
    img = np.zeros((420, 420, 4), np.uint8)
    palettes = {
        "shocked": (30, 170, 255, 255), "laughing": (60, 220, 90, 255),
        "crying": (230, 120, 70, 255), "confused": (210, 90, 210, 255),
        "facepalm": (100, 180, 240, 255), "clapping": (70, 210, 230, 255),
        "head_nod": (100, 220, 170, 255), "head_shake": (180, 120, 240, 255),
        "shrug": (90, 190, 255, 255), "arms_up": (80, 220, 120, 255),
        "angry": (70, 70, 240, 255), "wink": (210, 190, 60, 255),
    }
    color = palettes.get(label, (80, 180, 240, 255))
    cv2.circle(img, (210, 190), 164, color, -1, cv2.LINE_AA)
    cv2.circle(img, (210, 190), 164, (255, 255, 255, 255), 9, cv2.LINE_AA)
    # Expression face artwork is intentionally original and generated locally.
    eye_y = 145
    if label == "wink":
        cv2.ellipse(img, (150, eye_y), (28, 12), 0, 0, 180, (20, 20, 20, 255), 9)
    else:
        cv2.circle(img, (150, eye_y), 17, (20, 20, 20, 255), -1, cv2.LINE_AA)
    cv2.circle(img, (265, eye_y), 17, (20, 20, 20, 255), -1, cv2.LINE_AA)
    if label in ("shocked", "confused", "crying"):
        cv2.ellipse(img, (210, 235), (35, 48 if label == "shocked" else 25), 0, 0, 360,
                    (20, 20, 20, 255), -1, cv2.LINE_AA)
    elif label in ("laughing", "clapping"):
        cv2.ellipse(img, (210, 220), (58, 35), 0, 0, 180, (20, 20, 20, 255), 9, cv2.LINE_AA)
    else:
        cv2.ellipse(img, (210, 235), (42, 12), 0, 0, 180, (20, 20, 20, 255), 8, cv2.LINE_AA)
    if label == "crying":
        cv2.ellipse(img, (150, 190), (12, 30), 15, 0, 360, (255, 255, 255, 230), -1)
        cv2.ellipse(img, (265, 190), (12, 30), 15, 0, 360, (255, 255, 255, 230), -1)
    cv2.putText(img, label.replace("_", " ").upper(), (45, 365), cv2.FONT_HERSHEY_DUPLEX,
                0.75, (255, 255, 255, 255), 2, cv2.LINE_AA)
    return Asset([img], [100])


def find_asset_file(pose):
    adir = os.path.join(HERE, "assets")
    if not os.path.isdir(adir):
        return None
    exts = (".gif", ".png", ".jpg", ".jpeg")
    for fn in sorted(os.listdir(adir)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() in exts and (stem == pose or stem.endswith("_" + pose)):
            return os.path.join(adir, fn)
    return None


def load_asset(pose):
    path = find_asset_file(pose)
    if path is None:
        print(f"  {pose:16s} missing -> placeholder")
        return placeholder(pose)
    frames, durations = [], []
    if path.lower().endswith(".gif"):
        from PIL import Image, ImageSequence
        with Image.open(path) as im:
            for f in ImageSequence.Iterator(im):
                frames.append(cv2.cvtColor(np.array(f.convert("RGBA")), cv2.COLOR_RGBA2BGRA))
                durations.append(max(20, int(f.info.get("duration", 100))))
    else:
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            frames, durations = [to_bgra(img)], [100]
    if not frames:
        print(f"  {pose:16s} could not read {os.path.basename(path)} -> placeholder")
        return placeholder(pose)
    print(f"  {pose:16s} {os.path.basename(path)}  ({len(frames)} frame{'s' if len(frames) > 1 else ''})")
    return Asset(frames, durations)


def overlay(frame, sprite, x, y):
    """Alpha-composite BGRA sprite onto BGR frame at top-left (x, y), clipped to the frame."""
    H, W = frame.shape[:2]
    h, w = sprite.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return frame
    s = sprite[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[:, :, 3:4].astype(np.float32) / 255.0
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (a * s[:, :, :3] + (1 - a) * roi).astype(np.uint8)
    return frame


def replace_face(frame, sprite, face, scale=1.24):
    """Place an opaque, head-tilt-aligned meme plate over the complete detected face.

    The meme is cover-cropped to the padded face bounds and flattened to opaque
    pixels before rotation, so transparent PNG areas cannot reveal the camera image.
    """
    H, W = frame.shape[:2]
    cx, cy = face.center
    target_w = max(8, int(round(face.w * scale)))
    target_h = max(8, int(round(face.h * scale)))
    sh, sw = sprite.shape[:2]
    # Cover-crop without stretching the meme's aspect ratio.
    factor = max(target_w / max(sw, 1), target_h / max(sh, 1))
    nw, nh = max(target_w, int(round(sw * factor))), max(target_h, int(round(sh * factor)))
    resized = cv2.resize(sprite, (nw, nh), interpolation=cv2.INTER_AREA if factor < 1 else cv2.INTER_LINEAR)
    ox, oy = (nw - target_w) // 2, (nh - target_h) // 2
    plate = resized[oy:oy + target_h, ox:ox + target_w].copy()
    if plate.shape[2] == 4:
        # Preserve the meme artwork but make every pixel opaque to guarantee face coverage.
        plate[:, :, 3] = 255
    else:
        plate = cv2.cvtColor(plate, cv2.COLOR_BGR2BGRA)
    matrix = cv2.getRotationMatrix2D((target_w / 2, target_h / 2), face.roll, 1.0)
    cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
    out_w = int(target_h * sin + target_w * cos)
    out_h = int(target_h * cos + target_w * sin)
    matrix[0, 2] += out_w / 2 - target_w / 2
    matrix[1, 2] += out_h / 2 - target_h / 2
    rotated = cv2.warpAffine(plate, matrix, (out_w, out_h), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REPLICATE)
    x, y = int(round(cx - out_w / 2)), int(round(cy - out_h / 2))
    # Reuse the alpha compositor; the rotated plate is fully opaque.
    return overlay(frame, rotated, x, y)


def enhance_camera_frame(frame):
    """Adaptive cleanup for dim, low-contrast or mildly soft webcam frames."""
    if frame is None or frame.size == 0:
        return frame
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    result = frame

    # Lift underexposed frames without aggressively washing out normal lighting.
    if brightness < 92:
        gamma = 1.0 + min(0.55, (92.0 - brightness) / 150.0)
        lut = np.array([min(255, round(((i / 255.0) ** (1.0 / gamma)) * 255))
                        for i in range(256)], dtype=np.uint8)
        result = cv2.LUT(result, lut)

    # Local contrast enhancement helps faces remain separable in haze or flat lighting.
    if contrast < 48:
        lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
        light, a, b = cv2.split(lab)
        light = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8)).apply(light)
        result = cv2.cvtColor(cv2.merge((light, a, b)), cv2.COLOR_LAB2BGR)

    # Mild edge recovery for slightly soft lenses; skip very noisy/dark frames.
    if sharpness < 85 and brightness > 35 and contrast > 10:
        softened = cv2.GaussianBlur(result, (0, 0), 1.0)
        result = cv2.addWeighted(result, 1.35, softened, -0.35, 0)
    return result


def dist(a, b):
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


class Face:
    def __init__(self, lms, blendshapes, W, H):
        p = np.array([[l.x * W, l.y * H] for l in lms], np.float32)
        self.pts = p
        x0, y0 = p.min(0)
        x1, y1 = p.max(0)
        self.box = (int(x0), int(y0), int(x1), int(y1))
        self.w, self.h = float(x1 - x0), float(y1 - y0)
        self.center = ((x0 + x1) / 2, (y0 + y1) / 2)
        self.nose, self.chin, self.top = p[1], p[152], p[10]
        self.mouth = (p[13] + p[14]) / 2
        self.eye_y = float((p[33][1] + p[263][1]) / 2)
        # Roll follows the eye line so the replacement stays aligned as the head tilts.
        self.roll = float(np.degrees(np.arctan2(p[263][1] - p[33][1], p[263][0] - p[33][0])))
        cl, cr = p[234], p[454]
        self.turn_signed = float((self.nose[0] - cl[0]) / max(cr[0] - cl[0], 1e-3) - 0.5)
        self.bs = {c.category_name: c.score for c in (blendshapes or [])}

    def b(self, name):
        return self.bs.get(name, 0.0)


class Hand:
    def __init__(self, lms, W, H):
        p = np.array([[l.x * W, l.y * H] for l in lms], np.float32)
        self.palm = p[[0, 5, 9, 13, 17]].mean(0)
        self.thumb, self.index, self.middle = p[4], p[8], p[12]
        d = p[9] - p[0]
        self.horizontal = abs(d[0]) > 1.5 * abs(d[1])
        self.vertical = abs(d[1]) > 1.5 * abs(d[0])
        ext = [dist(p[0], p[t]) > 1.2 * dist(p[0], p[t - 2]) for t in (8, 12, 16, 20)]
        self.open = sum(ext) >= 3


class Body:
    """Upper-body pose: shoulders 11/12, elbows 13/14, wrists 15/16."""

    def __init__(self, lms, W, H):
        p = np.array([[l.x * W, l.y * H] for l in lms], np.float32)
        self.shoulders, self.elbows, self.wrists = p[[11, 12]], p[[13, 14]], p[[15, 16]]
        vis = [getattr(lms[i], "visibility", 1.0) for i in (11, 12, 13, 14)]
        self.seen = min(vis) > 0.5
        shoulder_y = float(self.shoulders[:, 1].mean())
        self.elbows_up = self.seen and bool((self.elbows[:, 1] < shoulder_y).all())

def assign_track_ids(faces, person_state, next_id):
    """Match faces to prior-frame centers so reactions stay with people as they move."""
    available = set(person_state)
    ids = []
    for face in faces:
        match = None
        if available:
            candidate = min(available, key=lambda key: dist(face.center, person_state[key]["center"]))
            if dist(face.center, person_state[candidate]["center"]) <= max(face.w * 1.8, 100):
                match = candidate
                available.remove(candidate)
        if match is None:
            match = next_id
            next_id += 1
        ids.append(match)
    for stale_id in available:
        del person_state[stale_id]
    return ids, next_id


def associate_people(faces, hands, bodies):
    """Assign each detected hand/body to at most one nearest face."""
    result = []
    if not faces:
        return result
    hand_groups = [[] for _ in faces]
    body_groups = [[] for _ in faces]
    for hand in hands:
        index = min(range(len(faces)), key=lambda i: dist(hand.palm, faces[i].center))
        if dist(hand.palm, faces[index].center) < max(faces[index].w * 1.8, 75):
            hand_groups[index].append(hand)
    for body in bodies:
        center = body.shoulders.mean(axis=0)
        index = min(range(len(faces)), key=lambda i: dist(center, faces[i].center))
        if dist(center, faces[index].center) < faces[index].h * 2.8:
            body_groups[index].append(body)
    for i in range(len(faces)):
        nearest_body = min(body_groups[i], key=lambda item: dist(item.shoulders.mean(axis=0), faces[i].center)) \
            if body_groups[i] else None
        result.append((hand_groups[i], nearest_body))
    return result



def tongue_score(frame, face, hands, jaw_ready):
    """Fraction of the mouth opening that reads pink: saturated and lit, unlike teeth or throat."""
    if not jaw_ready:
        return 0.0
    if any(dist(h.palm, face.mouth) < 0.7 * face.w for h in hands):
        return 0.0
    poly = face.pts[INNER_LIPS].astype(np.int32)
    x0, y0 = poly.min(0)
    x1, y1 = poly.max(0)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return 0.0
    x0, y0 = max(x0, 0), max(y0, 0)
    roi = frame[y0:y1 + 1, x0:x1 + 1]
    if roi.size == 0:
        return 0.0
    mask = np.zeros(roi.shape[:2], np.uint8)
    cv2.fillPoly(mask, [poly - [x0, y0]], 255)
    k = max(3, int(0.15 * (y1 - y0)))
    mask = cv2.erode(mask, np.ones((k, k), np.uint8))
    n = int(np.count_nonzero(mask))
    if n < 40:
        return 0.0
    h, s, v = cv2.split(cv2.cvtColor(roi, cv2.COLOR_BGR2HSV))
    pink = ((h < 12) | (h > 160)) & (s > 70) & (v > 110)
    return float(np.count_nonzero(pink & (mask > 0)) / n)


class Motion:
    """Smoothed hand speed across frames, in face-widths per frame."""

    def __init__(self):
        self.prev, self.energy, self.fw = [], 0.0, 200.0
        self.prev_face = None
        self.prev_body = None
        self.nod = self.shake = self.shrug = self.clap = False

    def update(self, hands, face, body=None):
        if face is not None:
            self.fw = max(face.w, 1.0)
        cur = [h.palm for h in hands]
        speed = 0.0
        if cur and self.prev:
            moved = [min(dist(c, p) for p in self.prev) for c in cur]
            moved = [m for m in moved if m < self.fw]
            if moved:
                speed = max(moved) / self.fw
        self.energy = 0.8 * self.energy + 0.2 * speed
        self.nod = self.shake = self.shrug = self.clap = False
        if face is not None and self.prev_face is not None:
            dx = (face.center[0] - self.prev_face[0]) / self.fw
            dy = (face.center[1] - self.prev_face[1]) / self.fw
            self.nod = abs(dy) > 0.035 and abs(dy) > abs(dx) * 1.2
            self.shake = abs(dx) > 0.045 and abs(dx) > abs(dy) * 1.2
        if face is not None:
            self.prev_face = face.center
        if body is not None and body.seen and face is not None:
            shoulders_y = float(body.shoulders[:, 1].mean())
            relative = (face.center[1] - shoulders_y) / self.fw
            if self.prev_body is not None:
                self.shrug = relative - self.prev_body > 0.035
            self.prev_body = relative
        if len(cur) >= 2:
            self.clap = dist(cur[0], cur[1]) < 0.42 * self.fw
        self.prev = cur
        return self.energy


def measure(face, base):
    """Every expression channel, raw and in sigma above your own neutral."""
    zpair = lambda n: (base.z(n + "Left", face.b(n + "Left")) + base.z(n + "Right", face.b(n + "Right"))) / 2
    pair = lambda n: (face.b(n + "Left") + face.b(n + "Right")) / 2
    m = {
        "jaw": face.b("jawOpen"), "z_jaw": base.z("jawOpen", face.b("jawOpen")),
        "sneer": pair("noseSneer"), "z_sneer": zpair("noseSneer"),
        "z_brow": zpair("browDown"), "z_frown": zpair("mouthFrown"), "z_lip": zpair("mouthUpperUp"),
        "squint": max(pair("eyeSquint"), pair("eyeBlink")),
        "z_squint": max(zpair("eyeSquint"), zpair("eyeBlink")),
        "turn": abs(face.turn_signed - base.neutral_turn),
        "smile": pair("mouthSmile"),
        "pucker": face.b("mouthPucker"),
        "eyes_wide": pair("eyeWide"),
        "brow_up": face.b("browInnerUp"),
        "wink": abs(face.b("eyeBlinkLeft") - face.b("eyeBlinkRight")),
    }
    cap = lambda v: min(v, Z_CAP)
    m["z_disgust"] = 2 * cap(m["z_sneer"]) + cap(m["z_brow"]) + cap(m["z_frown"]) + cap(m["z_lip"])
    return m


def over(key, m, zkey, rawkey):
    """Sigma above your neutral AND a raw floor, so a tiny sigma can't become a hair trigger."""
    return m[zkey] >= Z[key] and m[rawkey] >= FLOOR[key]


def decide(face, hands, body, tongue, gesture, m):
    """Return (pose or None, debug dict)."""
    d = {"hands": len(hands)}
    if face is None:
        gone = not hands and (body is None or not body.seen)
        return ("spin" if gone else None), d

    fw = face.w
    near = lambda a, b, k: dist(a, b) < k * fw
    elbows_up = bool(body and body.elbows_up)
    d.update(m, gesture=gesture, tongue=tongue, elbows_up=elbows_up)
    # Shock is the direct first-frame match; reserve crashing_out for the
    # stronger two-hands-on-head gesture below.
    if m.get("eyes_wide", 0.0) > 0.30 and m.get("jaw", 0.0) > 0.18:
        return "shocked", d
    screaming = over("scream_jaw", m, "z_jaw", "jaw")

    if len(hands) >= 2:
        a, b = hands[0], hands[1]
        for top, under in ((a, b), (b, a)):
            if top.horizontal and under.vertical and top.palm[1] < under.palm[1] \
                    and near(under.middle, top.palm, 0.6):
                return "time_out", d
        if near(a.index, b.index, 0.3) and near(a.thumb, b.thumb, 0.3) \
                and (a.index[1] + b.index[1]) < (a.thumb[1] + b.thumb[1]):
            return "heart", d
        if near(a.palm, face.mouth, 0.6) and near(b.palm, face.mouth, 0.6):
            return "cover_nose", d
        on_head = lambda h: (h.palm[1] < face.eye_y and abs(h.palm[0] - face.nose[0]) < 1.1 * fw
                             and h.palm[1] > face.top[1] - 0.8 * face.h)
        if on_head(a) and on_head(b) and screaming:
            return "crashing_out", d

    near_head = lambda h: abs(h.palm[0] - face.nose[0]) < 1.3 * fw and h.palm[1] < face.eye_y + 0.3 * face.h
    if elbows_up and all(near_head(h) for h in hands):
        return ("crashing_out" if screaming else "dance"), d

    for h in hands:
        if near(h.thumb, face.nose, 0.35) and near(h.index, face.nose, 0.35) and near(h.thumb, h.index, 0.3):
            return "nose_closed", d
        if near(h.index, face.mouth, 0.22) and not near(h.palm, face.mouth, 0.3):
            return "flirty", d
        if h.open and h.palm[1] < face.nose[1] and abs(h.palm[0] - face.nose[0]) > 0.8 * fw:
            return "hand_up", d

    # Additional direct expression cues work without personal calibration.
    if m.get("eyes_wide", 0.0) > 0.30 and m.get("jaw", 0.0) > 0.18:
        return "shocked", d
    if m.get("mouthSmile", m.get("smile", 0.0)) > 0.68:
        return "laughing", d
    if m.get("brow_up", 0.0) > 0.48 and m.get("z_frown", 0.0) > 1.0:
        return "crying", d
    if m.get("brow_up", 0.0) > 0.42 and m.get("eyes_wide", 0.0) > 0.22:
        return "confused", d
    if m.get("wink", 0.0) > 0.38:
        return "wink", d
    if m.get("pucker", 0.0) > 0.38:
        return "flirty", d
    if m.get("smile", 0.0) > 0.52:
        return "dance", d
    if m.get("z_brow", 0.0) > 3.2 and m.get("jaw", 0.0) < 0.18:
        return "angry", d
    if tongue > T["tongue"]:
        return "tongue_out", d
    if over("jaw_open", m, "z_jaw", "jaw"):
        return "open_mouth", d
    if over("sneer", m, "z_sneer", "sneer") or m["z_disgust"] >= Z["disgust"]:
        return "disgusted", d
    if hands and gesture > T["gesture"]:
        return "talking_to_wall", d
    if m["turn"] > T["head_turn"] and over("squint", m, "z_squint", "squint"):
        return "suspicious", d
    return None, d


def match_face_confidences(faces, detections, width, height):
    """Attach the nearest overlapping FaceDetector score to each FaceLandmarker face."""
    boxes = []
    for detection in detections:
        box = detection.bounding_box
        x0, y0 = float(box.origin_x), float(box.origin_y)
        x1, y1 = x0 + float(box.width), y0 + float(box.height)
        score = float(detection.categories[0].score) if detection.categories else None
        boxes.append(((x0, y0, x1, y1), score))
    for face in faces:
        fx0, fy0, fx1, fy1 = face.box
        best_iou, best_score = 0.0, None
        for (dx0, dy0, dx1, dy1), score in boxes:
            ix0, iy0 = max(fx0, dx0), max(fy0, dy0)
            ix1, iy1 = min(fx1, dx1), min(fy1, dy1)
            intersection = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
            face_area = max(0.0, fx1 - fx0) * max(0.0, fy1 - fy0)
            det_area = max(0.0, dx1 - dx0) * max(0.0, dy1 - dy0)
            union = face_area + det_area - intersection
            iou = intersection / union if union > 0 else 0.0
            if iou > best_iou:
                best_iou, best_score = iou, score
        face.detection_confidence = best_score if best_iou >= 0.03 else None
    return sum(1 for _, score in boxes if score is not None)


def draw_hud(img, shown, raw, d, face, hands, body, base, person_id, face_count,
             detector_count=0):
    """Draw per-person tracking diagnostics on the local preview only."""
    if face:
        x0, y0, x1, y1 = face.box
        confidence = getattr(face, "detection_confidence", None)
        colour = (60, 220, 80) if shown else (0, 190, 255)
        cv2.rectangle(img, (x0, y0), (x1, y1), colour, 2)
        selected = shown or "waiting"
        candidate = raw or "none"
        confidence_label = f"{confidence * 100:.0f}%" if confidence is not None else "n/a"
        label = f"ID {person_id} | det: {confidence_label} | meme: {selected} | raw: {candidate}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale, thickness = 0.48, 1
        (tw, th), baseline = cv2.getTextSize(label, font, scale, thickness)
        label_y = max(th + 8, y0 - 8)
        cv2.rectangle(img, (max(0, x0), label_y - th - 6),
                      (min(img.shape[1] - 1, x0 + tw + 10), label_y + baseline),
                      (24, 24, 24), -1)
        cv2.putText(img, label, (max(4, x0 + 5), label_y),
                    font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    for h in hands:
        cv2.circle(img, (int(h.palm[0]), int(h.palm[1])), 5, (0, 200, 255), -1)
    if body and body.seen:
        for pt in np.vstack([body.shoulders, body.elbows]):
            cv2.circle(img, (int(pt[0]), int(pt[1])), 5, (255, 120, 0), -1)
    panel = f"SCREENFILTER DEBUG  detector: {detector_count}  |  landmarks: {face_count}/8  |  D: hide overlay"
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(panel, font, 0.58, 2)
    cv2.rectangle(img, (6, 6), (min(img.shape[1] - 1, tw + 18), th + baseline + 16), (18, 18, 18), -1)
    cv2.putText(img, panel, (12, th + 10), font, 0.58, (255, 255, 255), 2, cv2.LINE_AA)
    if base.generic:
        cv2.putText(img, "Calibration: generic baseline", (12, th + 34), font, 0.45, (0, 165, 255), 1, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=0, help="webcam index (try 1 if 0 is your iPhone)")
    ap.add_argument("--calibrate", action="store_true", help="learn your neutral face, save it, and exit")
    ap.add_argument("--no-calibration", action="store_true", help="ignore calibration.json; use the generic baseline")
    ap.add_argument("--no-vcam", action="store_true", help="preview only; don't start the virtual camera")
    ap.add_argument("--skip-check", action="store_true", help="skip the MediaPipe startup check")
    ap.add_argument("--size", default="1280x720", help="capture size, e.g. 1280x720 or 640x480 (lower = faster)")
    ap.add_argument("--no-flip", action="store_true", help="don't mirror the image")
    args = ap.parse_args()

    calib_path = os.path.join(USER_DATA_DIR, CALIB_FILE)
    base = Baseline() if args.no_calibration else Baseline.load(calib_path)
    if base.generic and not args.calibrate and not args.no_calibration:
        print(f"No usable {CALIB_FILE}. Running on the generic baseline — everything is harder to\n"
              f"trigger than it should be. Run:  python {os.path.basename(__file__)} --calibrate")

    model_paths = ensure_models()
    if not args.skip_check:
        preflight(model_paths["face_landmarker.task"])

    cap = cv2.VideoCapture(args.camera)
    if cap.isOpened() and "x" in args.size:
        w, h = args.size.lower().split("x")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(w))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(h))
    ok, frame = False, None
    if cap.isOpened():
        for _ in range(5):
            ok, frame = cap.read()
            if not ok:
                break
    if not ok:
        sys.exit(f"Could not read from camera {args.camera}.\n"
                 "  - try --camera 1\n"
                 "  - System Settings > Privacy & Security > Camera: allow your terminal app, then re-run")
    H, W = frame.shape[:2]
    print(f"Camera {args.camera}: {W}x{H}")

    clock = Clock()
    window = "it's giving v2  (q quit, d HUD, c recalibrate, 1-9 0 - = [ ] test)"

    if args.calibrate:
        face_det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=model_paths["face_landmarker.task"]),
            running_mode=vision.RunningMode.VIDEO, num_faces=8, output_face_blendshapes=True))
        try:
            new = run_calibration(cap, face_det, clock, args, W, H, window)
        finally:
            face_det.close()
            cap.release()
            cv2.destroyAllWindows()
        if new is None:
            sys.exit(1)
        new.save(calib_path)
        print(f"Saved {CALIB_FILE}. Now run:  python {os.path.basename(__file__)}")
        return

    print("Assets:")
    assets = {pose: load_asset(pose) for pose in POSES}

    vcam = None
    if not args.no_vcam:
        try:
            import pyvirtualcam
            vcam = pyvirtualcam.Camera(
                width=W, height=H, fps=30, fmt=pyvirtualcam.PixelFormat.BGR,
                device="OBS Virtual Camera", backend="obs")
            print(f"Virtual camera: '{vcam.device}' (backend: {vcam.backend})  <- pick OBS Virtual Camera in Zoom / Meet")
        except Exception as e:
            print(f"Virtual camera unavailable ({e}). Preview-only.")

    face_det, score_face_det, hand_det, pose_det = build_detectors(model_paths)
    person_state = {}
    next_person_id = 0
    show_hud = True
    forced, forced_until = None, 0.0
    sm_center, sm_h = np.array([W / 2, H / 2], np.float32), H * 0.45
    print("Running. Focus the preview window: q quit, d HUD, c recalibrate, 1-9 0 - = [ ] test a pose")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Camera stopped returning frames.")
                break
            if frame.shape[0] != H or frame.shape[1] != W:
                frame = cv2.resize(frame, (W, H))
            if not args.no_flip:
                frame = cv2.flip(frame, 1)
            frame = enhance_camera_frame(frame)

            ts = clock.next()
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            fr = face_det.detect_for_video(mp_img, ts)
            hr = hand_det.detect_for_video(mp_img, ts)
            pr = pose_det.detect_for_video(mp_img, ts)
            faces = [
                Face(landmarks, fr.face_blendshapes[i] if i < len(fr.face_blendshapes) else None, W, H)
                for i, landmarks in enumerate(fr.face_landmarks)
            ]
            score_result = score_face_det.detect_for_video(mp_img, ts)
            detector_count = match_face_confidences(faces, score_result.detections, W, H)
            # Stable left-to-right ordering keeps each person's state independent in a frame.
            faces.sort(key=lambda item: item.center[0])
            all_hands = [Hand(h, W, H) for h in hr.hand_landmarks]
            all_bodies = [Body(p, W, H) for p in pr.pose_landmarks]
            now = time.monotonic()
            face_ids, next_person_id = assign_track_ids(faces, person_state, next_person_id)
            people = associate_people(faces, all_hands, all_bodies)
            shown_items = []
            for person_id, face, (hands, body) in zip(face_ids, faces, people):
                # The association list is frame-ordered; persistent track IDs are
                # dictionary keys and must never be used as list indexes.

                state = person_state.setdefault(person_id, {
                    "motion": Motion(), "shown": None, "hold": 0,
                    "arm": {pose: 0 for pose in POSES}, "shown_since": now,
                    "center": face.center,
                })
                state["center"] = face.center
                m = measure(face, base)
                tongue = tongue_score(frame, face, hands, over("tongue_jaw", m, "z_jaw", "jaw"))
                gesture = state["motion"].update(hands, face, body)
                motion = state["motion"]
                if motion.clap:
                    raw = "clapping"
                    dbg = {"hands": len(hands), **m, "gesture": gesture}
                elif motion.nod:
                    raw = "head_nod"
                    dbg = {"hands": len(hands), **m, "gesture": gesture}
                elif motion.shake:
                    raw = "head_shake"
                    dbg = {"hands": len(hands), **m, "gesture": gesture}
                elif motion.shrug:
                    raw = "shrug"
                    dbg = {"hands": len(hands), **m, "gesture": gesture}
                elif body and body.seen and body.elbows_up:
                    raw = "arms_up"
                    dbg = {"hands": len(hands), **m, "gesture": gesture}
                elif any(h.palm[1] < face.top[1] + 0.25 * face.h for h in hands):
                    raw = "facepalm"
                    dbg = {"hands": len(hands), **m, "gesture": gesture}
                else:
                    raw, dbg = decide(face, hands, body, tongue, gesture, m)

                fired = None
                for pose in POSES:
                    state["arm"][pose] = state["arm"][pose] + 1 if raw == pose else 0
                    if raw == pose and state["arm"][pose] >= ARM.get(pose, 2):
                        fired = pose
                if forced and now < forced_until:
                    fired = forced
                if fired:
                    if fired != state["shown"]:
                        state["shown_since"] = now
                    state["shown"], state["hold"] = fired, HOLD_FRAMES
                elif state["hold"] > 0:
                    state["hold"] -= 1
                else:
                    state["shown"] = None

                if state["shown"]:
                    asset = assets[state["shown"]]
                    idx = asset.frame_at(int((now - state["shown_since"]) * 1000))
                    sprite = asset.scaled(idx, max(8, int(face.h * 1.30)))
                    replace_face(frame, sprite, face, scale=1.24)
                shown_items.append((person_id, state["shown"], raw, dbg, face, hands, body))

            # Faces disappearing from view should not leave stale state behind.
            if show_hud:
                preview = frame.copy()
                face_count = len(shown_items)
                for person_id, shown, raw, dbg, face, hands, body in shown_items:
                    draw_hud(preview, shown, raw, dbg, face, hands, body, base,
                             person_id, face_count, detector_count)
                if not shown_items:
                    message = (f"SCREENFILTER DEBUG  detector: {detector_count}  |  landmarks: 0/8"
                               if detector_count else
                               "SCREENFILTER DEBUG  detector: 0  |  landmarks: 0/8  |  no face found")
                    cv2.putText(preview, message, (12, 28), cv2.FONT_HERSHEY_SIMPLEX,
                                0.58, (0, 0, 255), 2, cv2.LINE_AA)
            else:
                preview = frame

            # OBS receives only the clean processed camera frame. Diagnostic
            # landmarks/dots are drawn on a separate preview copy, never output.
            if vcam:
                vcam.send(frame)
                vcam.sleep_until_next_frame()

            cv2.imshow(window, preview)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            # Closing the OpenCV preview with its title-bar X exits the engine too.
            try:
                if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                    break
            except cv2.error:
                break
            if key == ord("d"):
                show_hud = not show_hud
            elif key == ord("c"):
                new = run_calibration(cap, face_det, clock, args, W, H, window)
                if new is not None:
                    base = new
                    base.save(calib_path)
                    print(f"Saved {CALIB_FILE}.")
                person_state.clear()
            elif 0 < key < 256 and chr(key) in TEST_KEYS:
                forced, forced_until = POSES[TEST_KEYS.index(chr(key))], now + 2.0
    finally:
        cap.release()
        face_det.close()
        score_face_det.close()
        hand_det.close()
        pose_det.close()
        if vcam:
            vcam.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
