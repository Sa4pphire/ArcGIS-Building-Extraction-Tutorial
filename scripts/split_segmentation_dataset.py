"""Convert masks to class indices and create a spatial train/validation split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from geo_utils import repository_root, spatial_split_rows


def build_parser() -> argparse.ArgumentParser:
    root = repository_root()
    parser = argparse.ArgumentParser(description="按空间行划分PaddleRS语义分割数据集")
    parser.add_argument("--dataset", type=Path, default=root / "outputs/segmentation")
    parser.add_argument("--train-ratio", type=float, default=0.67)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not 0.1 <= args.train_ratio <= 0.9:
        raise SystemExit("--train-ratio 必须位于0.1到0.9之间")
    manifest_path = args.dataset / "dataset_manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"缺少数据清单：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = manifest.get("samples", [])
    if not samples:
        raise SystemExit("数据清单中没有有效样本")

    train_rows, buffer_row, val_rows = spatial_split_rows(
        [int(sample["row"]) for sample in samples], args.train_ratio
    )
    masks_dir = args.dataset / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)
    expected_masks = set()
    split = {"train": [], "val": [], "holdout": []}

    for sample in samples:
        label_path = args.dataset / sample["label"]
        with Image.open(label_path) as label:
            label.load()
            source = np.asarray(label)
        values = set(np.unique(source).tolist())
        if not values.issubset({0, 255}) or 255 not in values:
            raise RuntimeError(f"标签值异常：{label_path} -> {sorted(values)}")
        indexed = (source == 255).astype(np.uint8)
        mask_name = f"{sample['stem']}.png"
        Image.fromarray(indexed, mode="L").save(masks_dir / mask_name, format="PNG")
        expected_masks.add(mask_name)
        line = f"{sample['image']} masks/{mask_name}"
        row = int(sample["row"])
        if row in train_rows:
            split["train"].append(line)
        elif row == buffer_row:
            split["holdout"].append(line)
        elif row in val_rows:
            split["val"].append(line)

    for path in masks_dir.glob("*.png"):
        if path.name not in expected_masks:
            path.unlink()
    if not split["train"] or not split["val"]:
        raise RuntimeError("空间划分产生了空训练集或验证集")
    for name, lines in split.items():
        (args.dataset / f"{name}.txt").write_text(
            "\n".join(sorted(lines)) + "\n", encoding="utf-8"
        )
    (args.dataset / "labels.txt").write_text("background\nbuilding\n", encoding="utf-8")
    report = {
        "train_rows": sorted(train_rows),
        "buffer_row": buffer_row,
        "validation_rows": sorted(val_rows),
        "train_samples": len(split["train"]),
        "holdout_samples": len(split["holdout"]),
        "validation_samples": len(split["val"]),
        "mask_values": [0, 1],
    }
    (args.dataset / "split_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
