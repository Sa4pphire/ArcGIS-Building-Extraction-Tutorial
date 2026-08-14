from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from geo_utils import validate_segmentation_pairs  # noqa: E402


class DatasetPairingTests(unittest.TestCase):
    def make_pair(self, images: Path, labels: Path, stem: str):
        rgb = np.full((32, 32, 3), 127, dtype=np.uint8)
        mask = np.zeros((32, 32), dtype=np.uint8)
        mask[8:24, 8:24] = 255
        Image.fromarray(rgb, mode="RGB").save(images / f"{stem}.jpg", format="JPEG")
        Image.fromarray(mask, mode="L").save(labels / f"{stem}.png", format="PNG")

    def test_valid_pairs_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "images"
            labels = root / "labels"
            images.mkdir()
            labels.mkdir()
            self.make_pair(images, labels, "tile_001")
            self.make_pair(images, labels, "tile_002")
            report = validate_segmentation_pairs(images, labels, 32)
            self.assertEqual(report["pairs"], 2)

    def test_missing_label_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "images"
            labels = root / "labels"
            images.mkdir()
            labels.mkdir()
            self.make_pair(images, labels, "tile_001")
            (labels / "tile_001.png").unlink()
            with self.assertRaises(RuntimeError):
                validate_segmentation_pairs(images, labels, 32)

    def test_empty_mask_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "images"
            labels = root / "labels"
            images.mkdir()
            labels.mkdir()
            rgb = np.zeros((32, 32, 3), dtype=np.uint8)
            Image.fromarray(rgb, mode="RGB").save(images / "tile_001.jpg", format="JPEG")
            Image.fromarray(np.zeros((32, 32), dtype=np.uint8), mode="L").save(
                labels / "tile_001.png", format="PNG"
            )
            with self.assertRaises(RuntimeError):
                validate_segmentation_pairs(images, labels, 32)


if __name__ == "__main__":
    unittest.main()
