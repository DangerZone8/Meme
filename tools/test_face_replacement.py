import unittest
from types import SimpleNamespace

import numpy as np

from its_giving_v2 import associate_people, decide, replace_face


class FaceReplacementTests(unittest.TestCase):
    def test_transparent_meme_pixels_never_reveal_camera_frame(self):
        original = np.full((240, 320, 3), (10, 20, 30), dtype=np.uint8)
        frame = original.copy()
        # Fully transparent input should still become an opaque face-covering plate.
        sprite = np.zeros((100, 100, 4), dtype=np.uint8)
        sprite[:, :, :3] = (20, 180, 240)
        face = SimpleNamespace(center=(160.0, 120.0), w=80.0, h=100.0, roll=0.0)
        result = replace_face(frame, sprite, face)
        self.assertTrue(np.array_equal(result[120, 160], np.array((20, 180, 240), dtype=np.uint8)))
        # The detected face rectangle, not just its centre point, must be covered.
        face_region = result[70:170, 120:200]
        original_region = original[70:170, 120:200]
        self.assertTrue(np.all(np.any(face_region != original_region, axis=2)))

    def test_replacement_tracks_face_center_and_tilt(self):
        frame = np.zeros((300, 400, 3), dtype=np.uint8)
        sprite = np.full((120, 100, 4), (0, 255, 0, 255), dtype=np.uint8)
        face = SimpleNamespace(center=(230.0, 140.0), w=90.0, h=110.0, roll=18.0)
        result = replace_face(frame, sprite, face)
        self.assertGreater(int(np.count_nonzero(result[:, :, 1])), 1000)
        self.assertTrue(np.array_equal(result[140, 230], np.array((0, 255, 0), dtype=np.uint8)))

    def test_multiple_people_get_independent_hand_and_body_assignments(self):
        faces = [
            SimpleNamespace(center=(80.0, 100.0), w=60.0, h=80.0),
            SimpleNamespace(center=(260.0, 100.0), w=60.0, h=80.0),
        ]
        hands = [
            SimpleNamespace(palm=np.array((75.0, 130.0))),
            SimpleNamespace(palm=np.array((265.0, 130.0))),
            SimpleNamespace(palm=np.array((400.0, 130.0))),
        ]
        bodies = [
            SimpleNamespace(shoulders=np.array(((65.0, 155.0), (95.0, 155.0)))),
            SimpleNamespace(shoulders=np.array(((245.0, 155.0), (275.0, 155.0)))),
        ]
        assigned = associate_people(faces, hands, bodies)
        self.assertEqual([len(item[0]) for item in assigned], [1, 1])
        self.assertIs(assigned[0][1], bodies[0])
        self.assertIs(assigned[1][1], bodies[1])
        self.assertIs(assigned[0][0][0], hands[0])
        self.assertIs(assigned[1][0][0], hands[1])

    def test_common_smile_and_pucker_expressions_trigger_without_calibration(self):
        face = SimpleNamespace(
            w=90.0, center=(150.0, 120.0), nose=(150.0, 105.0),
            mouth=(150.0, 145.0), eye_y=90.0, top=(150.0, 60.0), h=110.0,
        )
        baseline_measurements = {
            "jaw": 0.0, "z_jaw": 0.0, "sneer": 0.0, "z_sneer": 0.0,
            "z_brow": 0.0, "z_frown": 0.0, "z_lip": 0.0,
            "squint": 0.0, "z_squint": 0.0, "turn": 0.0,
            "z_disgust": 0.0, "smile": 0.0, "pucker": 0.0,
            "eyes_wide": 0.0, "brow_up": 0.0,
        }
        smile = dict(baseline_measurements, smile=0.7)
        pucker = dict(baseline_measurements, pucker=0.6)
        self.assertEqual(decide(face, [], None, 0.0, 0.0, smile)[0], "dance")
        self.assertEqual(decide(face, [], None, 0.0, 0.0, pucker)[0], "flirty")

    def test_expression_selected_meme_is_applied_as_full_face_replacement(self):
        original = np.full((240, 320, 3), (15, 25, 35), dtype=np.uint8)
        frame = original.copy()
        face = SimpleNamespace(
            center=(160.0, 120.0), w=80.0, h=100.0, roll=0.0,
            nose=(160.0, 110.0), mouth=(160.0, 145.0), eye_y=95.0,
            top=(160.0, 60.0),
        )
        measurements = {
            "jaw": 0.55, "z_jaw": 7.0,
            "sneer": 0.0, "z_sneer": 0.0, "z_disgust": 0.0,
            "z_brow": 0.0, "z_frown": 0.0, "z_lip": 0.0,
            "squint": 0.0, "z_squint": 0.0, "turn": 0.0,
        }
        pose, _ = decide(face, [], None, 0.0, 0.0, measurements)
        self.assertEqual(pose, "open_mouth")

        meme = np.zeros((120, 120, 4), dtype=np.uint8)
        meme[:, :, :3] = (220, 40, 180)
        result = replace_face(frame, meme, face)
        self.assertTrue(np.all(np.any(
            result[70:170, 120:200] != original[70:170, 120:200], axis=2
        )))


if __name__ == "__main__":
    unittest.main()
