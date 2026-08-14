"""Export image tiles and PASCAL VOC boxes from the same polygon annotations."""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from osgeo import gdal, ogr
from tqdm import tqdm

from geo_utils import (
    bounds_from_geotransform,
    open_raster,
    open_vector,
    read_padded_rgb,
    repository_root,
    save_rgb_jpeg,
    shifted_geotransform,
    spatial_split_rows,
    tile_starts,
    validate_raster_vector,
)


def build_parser() -> argparse.ArgumentParser:
    root = repository_root()
    parser = argparse.ArgumentParser(description="从遥感影像和建筑物面标注导出VOC目标检测数据集")
    parser.add_argument("--raster", type=Path, default=root / "demo_data/raster/demo_image.tif")
    parser.add_argument("--vector", type=Path, default=root / "demo_data/vector/buildings.shp")
    parser.add_argument("--output", type=Path, default=root / "outputs/detection")
    parser.add_argument("--window-size", type=int, default=512)
    parser.add_argument("--stride", type=int, default=256)
    parser.add_argument("--train-ratio", type=float, default=0.67)
    parser.add_argument("--include-empty", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def tile_polygon(bounds):
    min_x, min_y, max_x, max_y = bounds
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in ((min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y), (min_x, min_y)):
        ring.AddPoint(x, y)
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(ring)
    return polygon


def boxes_for_tile(layer, geotransform, size: int):
    bounds = bounds_from_geotransform(geotransform, size, size)
    clip_geometry = tile_polygon(bounds)
    inverse = gdal.InvGeoTransform(geotransform)
    layer.SetSpatialFilterRect(*bounds)
    boxes = []
    try:
        layer.ResetReading()
        for feature in layer:
            geometry = feature.GetGeometryRef()
            if geometry is None or not geometry.Intersects(clip_geometry):
                continue
            clipped = geometry.Intersection(clip_geometry)
            if clipped is None or clipped.IsEmpty():
                continue
            min_x, max_x, min_y, max_y = clipped.GetEnvelope()
            pixels = [
                gdal.ApplyGeoTransform(inverse, min_x, min_y),
                gdal.ApplyGeoTransform(inverse, min_x, max_y),
                gdal.ApplyGeoTransform(inverse, max_x, min_y),
                gdal.ApplyGeoTransform(inverse, max_x, max_y),
            ]
            xs = [point[0] for point in pixels]
            ys = [point[1] for point in pixels]
            x1 = max(0, min(size - 1, math.floor(min(xs))))
            y1 = max(0, min(size - 1, math.floor(min(ys))))
            x2 = max(0, min(size - 1, math.ceil(max(xs))))
            y2 = max(0, min(size - 1, math.ceil(max(ys))))
            if x2 > x1 and y2 > y1:
                boxes.append((x1, y1, x2, y2))
    finally:
        layer.SetSpatialFilter(None)
    return boxes


def write_voc(path: Path, filename: str, size: int, boxes) -> None:
    root = ET.Element("annotation")
    ET.SubElement(root, "filename").text = filename
    size_node = ET.SubElement(root, "size")
    ET.SubElement(size_node, "width").text = str(size)
    ET.SubElement(size_node, "height").text = str(size)
    ET.SubElement(size_node, "depth").text = "3"
    for x1, y1, x2, y2 in boxes:
        obj = ET.SubElement(root, "object")
        ET.SubElement(obj, "name").text = "building"
        box = ET.SubElement(obj, "bndbox")
        for name, value in zip(("xmin", "ymin", "xmax", "ymax"), (x1, y1, x2, y2)):
            ET.SubElement(box, name).text = str(value)
    ET.indent(root, space="    ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    args = build_parser().parse_args()
    images_dir = args.output / "images"
    labels_dir = args.output / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    if any(images_dir.glob("*.jpg")) or any(labels_dir.glob("*.xml")):
        if not args.overwrite:
            raise SystemExit("输出目录已有文件；确认后使用 --overwrite 重新生成。")
        for path in images_dir.glob("det_*.jpg"):
            path.unlink()
        for path in labels_dir.glob("det_*.xml"):
            path.unlink()

    raster = open_raster(args.raster)
    vector = open_vector(args.vector)
    layer = vector.GetLayer(0)
    preflight = validate_raster_vector(raster, layer)
    if not preflight["same_srs"] or not preflight["overlap"]:
        raise SystemExit("空间预检未通过")

    x_starts = tile_starts(raster.RasterXSize, args.window_size, args.stride)
    y_starts = tile_starts(raster.RasterYSize, args.window_size, args.stride)
    source_gt = raster.GetGeoTransform()
    samples = []
    total = len(x_starts) * len(y_starts)
    with tqdm(total=total, desc="导出VOC切片", unit="窗") as progress:
        for row, y_offset in enumerate(y_starts):
            for column, x_offset in enumerate(x_starts):
                gt = shifted_geotransform(source_gt, x_offset, y_offset)
                boxes = boxes_for_tile(layer, gt, args.window_size)
                if not boxes and not args.include_empty:
                    progress.update(1)
                    continue
                stem = f"det_r{row:03d}_c{column:03d}"
                image_name = f"{stem}.jpg"
                label_name = f"{stem}.xml"
                rgb = read_padded_rgb(raster, x_offset, y_offset, args.window_size)
                save_rgb_jpeg(rgb, images_dir / image_name)
                write_voc(labels_dir / label_name, image_name, args.window_size, boxes)
                samples.append({"stem": stem, "row": row, "boxes": len(boxes)})
                progress.update(1)

    train_rows, buffer_row, val_rows = spatial_split_rows(
        [sample["row"] for sample in samples], args.train_ratio
    )
    split = {"train": [], "val": [], "holdout": []}
    for sample in samples:
        line = f"images/{sample['stem']}.jpg labels/{sample['stem']}.xml"
        if sample["row"] in train_rows:
            split["train"].append(line)
        elif sample["row"] == buffer_row:
            split["holdout"].append(line)
        elif sample["row"] in val_rows:
            split["val"].append(line)
    for name, lines in split.items():
        (args.output / f"{name}.txt").write_text("\n".join(sorted(lines)) + "\n", encoding="utf-8")
    (args.output / "labels.txt").write_text("building\n", encoding="utf-8")
    report = {
        "total_windows": total,
        "exported_samples": len(samples),
        "total_boxes": sum(sample["boxes"] for sample in samples),
        "train_samples": len(split["train"]),
        "holdout_samples": len(split["holdout"]),
        "validation_samples": len(split["val"]),
        "buffer_row": buffer_row,
    }
    (args.output / "export_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
