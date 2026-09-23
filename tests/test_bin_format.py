import tempfile
import unittest
from pathlib import Path

from bin_format import BIN_TRAILER, FRAME_UNIT, inspect_bin
from upload import UPLOAD_FRAME_START, encode_upload_name


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

    def test_upload_filename_header_uses_observed_radix(self):
        self.assertEqual(encode_upload_name("01KADO.BIN"), b"\x00md01KADO.BIN")
        self.assertEqual(UPLOAD_FRAME_START, b"B2DDDDED")
