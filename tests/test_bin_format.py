import tempfile
import unittest
from pathlib import Path

from bin_format import BIN_TRAILER, FRAME_UNIT, inspect_bin


class BinFormatTests(unittest.TestCase):
    def test_observed_container(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.BIN"
            path.write_bytes(b"\0" * FRAME_UNIT + BIN_TRAILER)
            info = inspect_bin(path)
            self.assertEqual(info.frame_units, 1)
            self.assertEqual(info.trailing_bytes, 0)

    def test_missing_trailer_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.BIN"
            path.write_bytes(b"not a bin")
            with self.assertRaises(ValueError):
                inspect_bin(path)
