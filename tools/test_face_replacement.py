import unittest
from types import SimpleNamespace

import numpy as np

from its_giving_v2 import (POSES, Motion, assign_track_ids, associate_people, decide, draw_hud, draw_untracked_detections, enhance_camera_frame, load_asset, match_face_confidences, replace_face)


class FaceReplacementTests(unittest.TestCase):
    def test_live_debug_overlay_draws_face_box_and_tracking_status(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        face = SimpleNamespace(box=(80, 50, 150, 140))
        draw_hud(frame, "shocked", "shocked", {}, face, [], None,
                 SimpleNamespace(generic=False), 7, 2)
        self.assertGreater(int(np.count_nonzero(frame)), 0)
        # The face rectangle is drawn in the overlay colour at its top edge.
        self.assertTrue(np.any(np.all(frame[50, 80:151] == (60, 220, 80), axis=1)))

    def test_live_debug_overlay_shows_real_detector_confidence_per_face(self):
        face = SimpleNamespace(box=(100, 80, 180, 170))
        detection = SimpleNamespace(
            bounding_box=SimpleNamespace(origin_x=92, origin_y=70, width=100, height=110),
            categories=[SimpleNamespace(score=0.873)],
        )
        count = match_face_confidences([face], [detection], 320, 240)
        self.assertEqual(count, 1)
        self.assertAlmostEqual(face.detection_confidence, 0.873, places=3)

        # A second person receives their own score, not the first person's value.
        second = SimpleNamespace(box=(220, 80, 290, 165))
        second_detection = SimpleNamespace(
            bounding_box=SimpleNamespace(origin_x=214, origin_y=74, width=88, height=100),
            categories=[SimpleNamespace(score=0.421)],
        )
        count = match_face_confidences([face, second], [detection, second_detection], 320, 240)
        self.assertEqual(count, 2)
        self.assertAlmostEqual(face.detection_confidence, 0.873, places=3)
        self.assertAlmostEqual(second.detection_confidence, 0.421, places=3)

    def test_detector_only_face_is_marked_when_landmarks_are_missing(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        detection = SimpleNamespace(
            bounding_box=SimpleNamespace(origin_x=30, origin_y=40, width=80, height=90),
            categories=[SimpleNamespace(score=0.612)],
        )
        draw_untracked_detections(frame, [detection], [])
        self.assertGreater(int(np.count_nonzero(frame)), 0)
        self.assertTrue(np.any(np.all(frame[40, 30:111] == (0, 120, 255), axis=1)))

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

    def test_low_quality_camera_enhancement_preserves_frame_shape_and_type(self):
        # Dim, flat image simulates a low-light/hazy webcam feed.
        frame = np.full((120, 160, 3), 38, dtype=np.uint8)
        enhanced = enhance_camera_frame(frame)
        self.assertEqual(enhanced.shape, frame.shape)
        self.assertEqual(enhanced.dtype, frame.dtype)
        self.assertGreater(float(np.mean(enhanced)), float(np.mean(frame)))

    def test_expanded_reaction_library_loads_every_asset_before_camera_loop(self):
        self.assertEqual(len(POSES), 26)
        loaded = {pose: load_asset(pose) for pose in POSES}
        self.assertEqual(set(loaded), set(POSES))
        self.assertTrue(all(asset.frames and asset.total > 0 for asset in loaded.values()))

    def test_shocked_expression_selects_shocked_meme(self):
        face = SimpleNamespace(w=90.0, center=(150.0, 120.0), nose=(150.0, 105.0),
                               mouth=(150.0, 145.0), eye_y=90.0, top=(150.0, 60.0), h=110.0)
        measurements = {
            'jaw': 0.42, 'z_jaw': 1.0, 'sneer': 0.0, 'z_sneer': 0.0,
            'z_brow': 0.0, 'z_frown': 0.0, 'z_lip': 0.0, 'squint': 0.0,
            'z_squint': 0.0, 'turn': 0.0, 'z_disgust': 0.0,
            'smile': 0.0, 'pucker': 0.0, 'eyes_wide': 0.75, 'brow_up': 0.1,
        }
        self.assertEqual(decide(face, [], None, 0.0, 0.0, measurements)[0], 'shocked')

    def test_head_movement_and_clap_are_detected_without_stationary_false_positives(self):
        motion = Motion()
        face_a = SimpleNamespace(w=100.0, center=(100.0, 100.0))
        face_jitter = SimpleNamespace(w=100.0, center=(101.0, 102.0))
        face_b = SimpleNamespace(w=100.0, center=(100.0, 106.0))
        motion.update([], face_a)
        motion.update([], face_jitter)
        self.assertFalse(motion.nod)
        motion.update([], face_b)
        self.assertTrue(motion.nod)

        apart = [SimpleNamespace(palm=np.array((70.0, 120.0))),
                 SimpleNamespace(palm=np.array((140.0, 120.0)))]
        together = [SimpleNamespace(palm=np.array((90.0, 120.0))),
                    SimpleNamespace(palm=np.array((120.0, 120.0)))]
        motion.update(apart, face_b)
        self.assertFalse(motion.clap)
        motion.update(together, face_b)
        self.assertTrue(motion.clap)
        motion.update(together, face_b)
        self.assertFalse(motion.clap)
    def test_decide_accepts_older_measurement_payloads(self):
        face = SimpleNamespace(
            w=80.0, center=(100.0, 100.0), nose=(100.0, 90.0),
            mouth=(100.0, 125.0), eye_y=80.0, top=(100.0, 50.0), h=100.0,
        )
        measurements = {
            "jaw": 0.55, "z_jaw": 7.0, "sneer": 0.0, "z_sneer": 0.0,
            "z_disgust": 0.0, "z_brow": 0.0, "z_frown": 0.0, "z_lip": 0.0,
            "squint": 0.0, "z_squint": 0.0, "turn": 0.0,
        }
        self.assertEqual(decide(face, [], None, 0.0, 0.0, measurements)[0], "open_mouth")

    def test_person_track_ids_follow_people_when_they_cross(self):
        state = {
            4: {"center": (220.0, 100.0)},
            9: {"center": (120.0, 100.0)},
        }
        # Faces are always supplied left-to-right; after crossing, their order swaps.
        faces = [
            SimpleNamespace(center=(110.0, 100.0), w=60.0),
            SimpleNamespace(center=(230.0, 100.0), w=60.0),
        ]
        ids, next_id = assign_track_ids(faces, state, 10)
        self.assertEqual(ids, [9, 4])
        self.assertEqual(next_id, 10)
        self.assertEqual(state[4]["center"], (220.0, 100.0))

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
        self.assertEqual(decide(face, [], None, 0.0, 0.0, smile)[0], "laughing")
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
