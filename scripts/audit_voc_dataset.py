"""审核图像/XML配对、类别、框和空间分割覆盖范围。"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from geo_utils import repository_root

""" 配置 ArgumentParser 对象 """
def build_parser() -> argparse.ArgumentParser:
    root = repository_root()
    parser = argparse.ArgumentParser(description="审计PASCAL VOC建筑物检测数据集")
    parser.add_argument("--dataset", type=Path, default=root / "outputs/detection")
    parser.add_argument("--write-report", action="store_true")
    return parser

""" 读取文件名 """
def read_split(path: Path) -> set[str]:
    return {
        line.split()[0].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    }


def main() -> None:
    args = build_parser().parse_args()
    images = {path.stem: path for path in (args.dataset / "images").glob("*.jpg")}
    labels = {path.stem: path for path in (args.dataset / "labels").glob("*.xml")}
    errors = []
    if set(images) != set(labels):
        errors.append(
            f"配对不一致：缺XML {len(set(images)-set(labels))}，缺影像 {len(set(labels)-set(images))}"
        )
    object_count = 0
    empty_samples = 0
    for stem in sorted(set(images) & set(labels)):
        with Image.open(images[stem]) as image:
            image.load()
            width, height = image.size
            if image.format != "JPEG" or image.mode != "RGB":
                errors.append(f"影像格式异常：{stem}")
        root = ET.parse(labels[stem]).getroot()
        objects = root.findall("object")
        if not objects:
            empty_samples += 1
        for obj in objects:
            object_count += 1
            if obj.findtext("name") != "building":
                errors.append(f"类别异常：{stem}")
            box = obj.find("bndbox")
            values = [int(float(box.findtext(name))) for name in ("xmin", "ymin", "xmax", "ymax")]
            x1, y1, x2, y2 = values
            if not (0 <= x1 < x2 < width and 0 <= y1 < y2 < height):
                errors.append(f"边界框越界：{stem} -> {values}")

    splits = {name: read_split(args.dataset / f"{name}.txt") for name in ("train", "val", "holdout")}
    if splits["train"] & splits["val"] or splits["train"] & splits["holdout"] or splits["val"] & splits["holdout"]:
        errors.append("训练、验证和缓冲集存在重叠")
    if set().union(*splits.values()) != set(images):
        errors.append("划分列表未完整覆盖数据集")
    report = {
        "images": len(images),
        "labels": len(labels),
        "objects": object_count,
        "empty_samples": empty_samples,
        "train": len(splits["train"]),
        "validation": len(splits["val"]),
        "holdout": len(splits["holdout"]),
        "errors": errors,
        "passed": not errors,
    }
    if args.write_report:
        (args.dataset / "audit_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
