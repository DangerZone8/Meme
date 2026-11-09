import unittest
from types import SimpleNamespace

import numpy as np

from its_giving_v2 import replace_face


class FaceReplacementTests(unittest.TestCase):
    def test_transparent_meme_pixels_never_reveal_camera_frame(self):
        frame = np.full((240, 320, 3), (10, 20, 30), dtype=np.uint8)
        # Fully transparent input should still become an opaque face-covering plate.
        sprite = np.zeros((100, 100, 4), dtype=np.uint8)
        sprite[:, :, :3] = (20, 180, 240)
        face = SimpleNamespace(center=(160.0, 120.0), w=80.0, h=100.0, roll=0.0)
        result = replace_face(frame, sprite, face)
        self.assertFalse(np.array_equal(result[120, 160], np.array((10, 20, 30), dtype=np.uint8)))
        self.assertTrue(np.array_equal(result[120, 160], np.array((20, 180, 240), dtype=np.uint8)))

    def test_replacement_tracks_face_center_and_tilt(self):
        frame = np.zeros((300, 400, 3), dtype=np.uint8)
        sprite = np.full((120, 100, 4), (0, 255, 0, 255), dtype=np.uint8)
        face = SimpleNamespace(center=(230.0, 140.0), w=90.0, h=110.0, roll=18.0)
        result = replace_face(frame, sprite, face)
        self.assertGreater(int(np.count_nonzero(result[:, :, 1])), 1000)
        self.assertTrue(np.array_equal(result[140, 230], np.array((0, 255, 0), dtype=np.uint8)))


if __name__ == "__main__":
    unittest.main()
