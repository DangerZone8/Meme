import json, tempfile, unittest
from pathlib import Path
from tools.memento_eval import evaluate, flatten_targets, token_f1

class MementoEvaluationTests(unittest.TestCase):
    def test_turn_pairing_and_order(self):
        rows = [{"video_uid":"v","conversation":[
            {"role":"user","content":"What changed?","time":1},
            {"role":"assistant","content":"A red car appeared.","time":2},
            {"role":"user","content":"When?","time":3},
            {"role":"assistant","content":"At eight seconds.","time":8}]}]
        result = flatten_targets(rows)
        self.assertEqual(result[("v",0,0)]["query"], "What changed?")
        self.assertEqual(result[("v",0,1)]["time"], 8)
    def test_token_f1(self):
        self.assertEqual(token_f1("A red car!", "a red car"), 1.0)
        self.assertEqual(token_f1("blue", "red"), 0.0)
    def test_text_and_temporal_metrics(self):
        ann = {"video_uid":"v","conversation":[{"role":"user","content":"What appeared?","time":1},{"role":"assistant","content":"A red car appeared.","time":3}]}
        pred = {"video_uid":"v","sample_index":0,"turn_index":0,"predicted_text":"A red car appeared","predicted_time":3.5}
        with tempfile.TemporaryDirectory() as tmp:
            a,p=Path(tmp)/"test.jsonl",Path(tmp)/"pred.jsonl"
            a.write_text(json.dumps(ann)+"\n",encoding="utf-8")
            p.write_text(json.dumps(pred)+"\n",encoding="utf-8")
            result=evaluate(a,p,1.0)
        self.assertEqual(result["exact_match"],1.0)
        self.assertEqual(result["temporal_accuracy"],1.0)
        self.assertEqual(result["missing_predictions"],0)
    def test_duplicate_prediction_rejected(self):
        ann={"video_uid":"v","conversation":[{"role":"user","content":"q"},{"role":"assistant","content":"a","time":1}]}
        pred={"video_uid":"v","sample_index":0,"turn_index":0,"predicted_text":"a"}
        with tempfile.TemporaryDirectory() as tmp:
            a,p=Path(tmp)/"a.jsonl",Path(tmp)/"p.jsonl"
            a.write_text(json.dumps(ann)+"\n",encoding="utf-8")
            p.write_text((json.dumps(pred)+"\n")*2,encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"Duplicate"): evaluate(a,p)
if __name__ == "__main__": unittest.main()
