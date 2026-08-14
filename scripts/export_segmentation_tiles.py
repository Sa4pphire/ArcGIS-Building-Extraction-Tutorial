"""Export paired JPEG images and lossless PNG building masks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from tqdm import tqdm

from geo_utils import (
    open_raster,
    open_vector,
    rasterize_mask,
    read_padded_rgb,
    repository_root,
    save_mask_png,
    save_rgb_jpeg,
    shifted_geotransform,
    tile_starts,
    validate_raster_vector,
    validate_segmentation_pairs,
)


def build_parser() -> argparse.ArgumentParser:
    root = repository_root()
    parser = argparse.ArgumentParser(description="将遥感影像和建筑物面标注导出为语义分割切片")
    parser.add_argument("--raster", type=Path, default=root / "demo_data/raster/demo_image.tif")
    parser.add_argument("--vector", type=Path, default=root / "demo_data/vector/buildings.shp")
    parser.add_argument("--output", type=Path, default=root / "outputs/segmentation")
    parser.add_argument("--window-size", type=int, default=512)
    parser.add_argument("--stride", type=int, default=256)
    parser.add_argument("--jpeg-quality", type=int, default=95)
    parser.add_argument("--overwrite", action="store_true", help="清理输出目录中已有的教程切片")
    return parser


def clear_outputs(images_dir: Path, labels_dir: Path) -> None:
    for path in images_dir.glob("tile_*.jpg"):
        path.unlink()
    for path in labels_dir.glob("tile_*.png"):
        path.unlink()


def main() -> None:
    args = build_parser().parse_args()
    if not 1 <= args.jpeg_quality <= 100:
        raise SystemExit("--jpeg-quality 必须位于1到100之间")

    images_dir = args.output / "images"
    labels_dir = args.output / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    if any(images_dir.glob("*.jpg")) or any(labels_dir.glob("*.png")):
        if not args.overwrite:
            raise SystemExit("输出目录已有文件；确认后使用 --overwrite 重新生成。")
        clear_outputs(images_dir, labels_dir)

    raster = open_raster(args.raster)
    vector = open_vector(args.vector)
    layer = vector.GetLayer(0)
    preflight = validate_raster_vector(raster, layer)
    if not preflight["same_srs"] or not preflight["overlap"]:
        raise SystemExit("空间预检未通过，请先运行 check_spatial_match.py。")

    x_starts = tile_starts(raster.RasterXSize, args.window_size, args.stride)
    y_starts = tile_starts(raster.RasterYSize, args.window_size, args.stride)
    projection = raster.GetProjection()
    source_geotransform = raster.GetGeoTransform()
    manifest = []
    skipped = 0

    total = len(x_starts) * len(y_starts)
    with tqdm(total=total, desc="导出语义分割切片", unit="窗") as progress:
        for row_index, y_offset in enumerate(y_starts):
            for column_index, x_offset in enumerate(x_starts):
                geotransform = shifted_geotransform(source_geotransform, x_offset, y_offset)
                mask = rasterize_mask(layer, geotransform, projection, args.window_size)
                if not np.any(mask):
                    skipped += 1
                    progress.update(1)
                    continue

                stem = f"tile_r{row_index:03d}_c{column_index:03d}"
                image_path = images_dir / f"{stem}.jpg"
                label_path = labels_dir / f"{stem}.png"
                rgb = read_padded_rgb(raster, x_offset, y_offset, args.window_size)
                save_rgb_jpeg(rgb, image_path, args.jpeg_quality)
                save_mask_png(mask, label_path)
                manifest.append(
                    {
                        "stem": stem,
                        "row": row_index,
                        "column": column_index,
                        "x_offset": x_offset,
                        "y_offset": y_offset,
                        "image": f"images/{image_path.name}",
                        "label": f"labels/{label_path.name}",
                    }
                )
                progress.update(1)

    audit = validate_segmentation_pairs(images_dir, labels_dir, args.window_size)
    report = {
        "raster": str(args.raster),
        "vector": str(args.vector),
        "window_size": args.window_size,
        "stride": args.stride,
        "total_windows": total,
        "skipped_empty": skipped,
        "exported_pairs": audit["pairs"],
        "samples": manifest,
    }
    (args.output / "dataset_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"有效样本：{audit['pairs']} 对；跳过空窗口：{skipped} 个。")
    print(f"输出目录：{args.output.resolve()}")


if __name__ == "__main__":
    main()
