import unittest

from fan_protocol import Frame, decode_frame, parse_file_index


DEVICE_INDEX_RESPONSE = bytes.fromhex(
    "43304545423743394241413300686669013103414b4904414b49320748414b4f303132"
    "0548414b4f310648414b4f31320548414b4f320648414b4f32320548414b4f330554"
    "41544532055441544534085441544559414d41010c000000010001000000000000000043"
    "3045454244463945354237"
)


class ProtocolTests(unittest.TestCase):
    def test_frame_round_trip(self):
        self.assertEqual(decode_frame(Frame(b"abc").encode()).payload, b"abc")

    def test_known_device_index(self):
        result = parse_file_index(decode_frame(DEVICE_INDEX_RESPONSE))
        self.assertEqual(result, [
            "1", "AKI", "AKI2", "HAKO012", "HAKO1", "HAKO12", "HAKO2",
            "HAKO22", "HAKO3", "TATE2", "TATE4", "TATEYAMA",
        ])


if __name__ == "__main__":
    unittest.main()
