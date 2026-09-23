import unittest

from bin_format import FRAME_UNIT
from convert import SOURCE_SIZE, pack_rgb_frame
from preview import render_rgb_frame


class ConvertTests(unittest.TestCase):
    def test_rgb_planes_have_vendor_frame_size(self):
        source = bytes(SOURCE_SIZE * SOURCE_SIZE * 3)
        encoded = pack_rgb_frame(source, threshold=1)
        self.assertEqual(len(encoded), FRAME_UNIT * 3)
        self.assertEqual(encoded, bytes(len(encoded)))

    def test_red_pixel_sets_only_first_colour_plane(self):
        source = bytearray(SOURCE_SIZE * SOURCE_SIZE * 3)
        # The first polar sample is center + radius zero, so its source pixel
        # is the centre coordinate rounded by the encoder.
        center = round((SOURCE_SIZE - 1) / 2)
        source[(center * SOURCE_SIZE + center) * 3] = 255
        encoded = pack_rgb_frame(bytes(source))
        # Radius zero occurs at the centre for every angular sample. Nearest
        # neighbour rounding may also sample it at radius one, but it must
        # affect the red plane only.
        self.assertNotEqual(encoded[:FRAME_UNIT], bytes(FRAME_UNIT))
        self.assertEqual(encoded[FRAME_UNIT:], bytes(FRAME_UNIT * 2))

    def test_packed_frame_renders_back_to_red_preview(self):
        source = bytearray(SOURCE_SIZE * SOURCE_SIZE * 3)
        center = round((SOURCE_SIZE - 1) / 2)
        source[(center * SOURCE_SIZE + center) * 3] = 255
        preview = render_rgb_frame(pack_rgb_frame(bytes(source)))
        red_values = preview[0::3]
        self.assertGreater(sum(red_values), 0)
        self.assertEqual(preview[1::3], bytes(SOURCE_SIZE * SOURCE_SIZE))
        self.assertEqual(preview[2::3], bytes(SOURCE_SIZE * SOURCE_SIZE))


if __name__ == "__main__":
    unittest.main()
