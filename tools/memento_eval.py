"""Optional Memento-54K annotation-only downloader and offline evaluator."""
import argparse, json, re, sys
from pathlib import Path
from collections import Counter

REPO_ID = "liarzone/Memento-54K"

def load_jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{n}: expected JSON object")
                rows.append(value)
    return rows

def download_annotations(split, cache_dir, revision):
    if split not in ("train", "test"):
        raise ValueError("split must be train or test")
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError("Install optional dependencies: pip install -r requirements-memento-eval.txt") from exc
    return Path(hf_hub_download(repo_id=REPO_ID, repo_type="dataset",
        filename=f"data/{split}.jsonl", revision=revision, cache_dir=str(cache_dir)))

def flatten_targets(rows):
    targets = {}
    for sample_index, row in enumerate(rows):
        uid, turns = row.get("video_uid"), row.get("conversation")
        if not isinstance(uid, str) or not isinstance(turns, list):
            raise ValueError(f"Annotation row {sample_index} lacks video_uid/conversation")
        pending, assistant_index = None, 0
        for turn in turns:
            if not isinstance(turn, dict): continue
            if turn.get("role") == "user":
                pending = turn
            elif turn.get("role") == "assistant":
                if pending is not None:
                    targets[(uid, sample_index, assistant_index)] = {
                        "query": str(pending.get("content", "")),
                        "reference": str(turn.get("content", "")),
                        "time": turn.get("time"), "task": turn.get("task", pending.get("task"))}
                assistant_index += 1
                pending = None
    return targets

def tokens(text):
    return re.findall(r"[a-z0-9]+", str(text).lower())

def token_f1(prediction, reference):
    p, r = tokens(prediction), tokens(reference)
    if not p or not r: return float(p == r)
    overlap = sum((Counter(p) & Counter(r)).values())
    if not overlap: return 0.0
    precision, recall = overlap / len(p), overlap / len(r)
    return 2 * precision * recall / (precision + recall)

def evaluate(annotation_path, predictions_path, timing_tolerance=2.0):
    targets = flatten_targets(load_jsonl(annotation_path))
    predictions = load_jsonl(predictions_path)
    seen, scores, exact, timed, on_time, errors = set(), [], 0, 0, 0, []
    for item in predictions:
        try:
            key = (str(item["video_uid"]), int(item["sample_index"]), int(item["turn_index"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Predictions require video_uid, sample_index, and turn_index") from exc
        if key in seen: raise ValueError(f"Duplicate prediction key: {key}")
        seen.add(key)
        target = targets.get(key)
        if target is None: raise ValueError(f"Prediction does not match test target: {key}")
        predicted = str(item.get("predicted_text", ""))
        reference = target["reference"]
        scores.append(token_f1(predicted, reference))
        exact += tokens(predicted) == tokens(reference)
        if item.get("predicted_time") is not None and target["time"] is not None:
            error = abs(float(item["predicted_time"]) - float(target["time"]))
            errors.append(error); timed += 1; on_time += error <= timing_tolerance
    count = len(scores)
    return {"dataset": REPO_ID, "split": "test", "reference_turns": len(targets),
        "predictions": count, "missing_predictions": len(targets) - len(seen),
        "exact_match": exact / count if count else 0.0,
        "token_f1": sum(scores) / count if count else 0.0,
        "timed_predictions": timed, "temporal_accuracy": on_time / timed if timed else None,
        "mean_absolute_time_error_seconds": sum(errors) / timed if timed else None,
        "timing_tolerance_seconds": timing_tolerance,
        "note": "Lexical diagnostics only; token F1/exact match are not semantic judge scores."}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("download", help="Download annotation JSONL only")
    d.add_argument("--split", choices=("train", "test"), default="test")
    d.add_argument("--cache-dir", type=Path, default=Path(".cache/memento-54k"))
    d.add_argument("--revision", default="main")
    e = sub.add_parser("evaluate", help="Score predictions against test annotations")
    e.add_argument("--annotations", type=Path, required=True)
    e.add_argument("--predictions", type=Path, required=True)
    e.add_argument("--timing-tolerance", type=float, default=2.0)
    args = parser.parse_args(argv)
    try:
        if args.command == "download":
            print(download_annotations(args.split, args.cache_dir, args.revision)); return 0
        if args.timing_tolerance < 0: parser.error("--timing-tolerance must be non-negative")
        print(json.dumps(evaluate(args.annotations, args.predictions, args.timing_tolerance), indent=2)); return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"memento-eval: {exc}", file=sys.stderr); return 2

if __name__ == "__main__":
    raise SystemExit(main())
