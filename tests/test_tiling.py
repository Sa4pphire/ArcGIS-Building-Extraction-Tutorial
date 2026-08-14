from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from geo_utils import extents_overlap, spatial_split_rows, tile_starts  # noqa: E402


class TilingTests(unittest.TestCase):
    def test_demo_grid_has_seven_starts_per_axis(self):
        self.assertEqual(tile_starts(2048, 512, 256), [0, 256, 512, 768, 1024, 1280, 1536])

    def test_small_raster_uses_one_padded_window(self):
        self.assertEqual(tile_starts(300, 512, 256), [0])

    def test_invalid_size_is_rejected(self):
        with self.assertRaises(ValueError):
            tile_starts(2048, 0, 256)

    def test_extent_overlap(self):
        self.assertTrue(extents_overlap((0, 0, 10, 10), (5, 5, 12, 12)))
        self.assertFalse(extents_overlap((0, 0, 10, 10), (10, 0, 20, 10)))

    def test_spatial_split_leaves_buffer_row(self):
        train, buffer_row, validation = spatial_split_rows(range(7), 0.67)
        self.assertEqual(train, {0, 1, 2, 3})
        self.assertEqual(buffer_row, 4)
        self.assertEqual(validation, {5, 6})


if __name__ == "__main__":
    unittest.main()
