"""MJPEG frame splitter — the piece of the live viewfinder that can be
verified without a sensor."""
import unittest

from box.camera import split_jpegs

J1 = b"\xff\xd8AAAA\xff\xd9"
J2 = b"\xff\xd8BBBBBB\xff\xd9"


class SplitterTest(unittest.TestCase):
    def test_two_complete_frames(self):
        frames, rest = split_jpegs(J1 + J2)
        self.assertEqual(frames, [J1, J2])
        self.assertEqual(rest, b"")

    def test_partial_frame_carries_over(self):
        frames, rest = split_jpegs(J1 + J2[:4])
        self.assertEqual(frames, [J1])
        self.assertEqual(rest, J2[:4])
        frames2, rest2 = split_jpegs(rest + J2[4:])
        self.assertEqual(frames2, [J2])
        self.assertEqual(rest2, b"")

    def test_garbage_between_frames_dropped(self):
        frames, _ = split_jpegs(b"junk" + J1 + b"noise" + J2)
        self.assertEqual(frames, [J1, b"\xff\xd8BBBBBB\xff\xd9"])

    def test_no_frames(self):
        self.assertEqual(split_jpegs(b"nothing here"), ([], b""))


if __name__ == "__main__":
    unittest.main()
