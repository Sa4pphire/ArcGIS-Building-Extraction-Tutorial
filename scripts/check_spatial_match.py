"""Check projection and extent compatibility before producing tiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from geo_utils import open_raster, open_vector, repository_root, validate_raster_vector


def build_parser() -> argparse.ArgumentParser:
    root = repository_root()
    parser = argparse.ArgumentParser(description="检查遥感影像与建筑物面标注是否空间匹配")
    parser.add_argument("--raster", type=Path, default=root / "demo_data/raster/demo_image.tif")
    parser.add_argument("--vector", type=Path, default=root / "demo_data/vector/buildings.shp")
    parser.add_argument("--json", action="store_true", help="以JSON输出检查结果")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raster = open_raster(args.raster)
    vector = open_vector(args.vector)
    layer = vector.GetLayer(0)
    result = validate_raster_vector(raster, layer)
    result["raster"] = str(args.raster.resolve())
    result["vector"] = str(args.vector.resolve())

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"影像：{args.raster}")
        print(f"标注：{args.vector}")
        print(f"影像尺寸：{result['raster_width']} × {result['raster_height']} × {result['raster_bands']}")
        print(f"矢量要素：{result['feature_count']} ({result['geometry_type']})")
        print(f"空间参考：{result['projection_name']}")
        print(f"坐标系一致：{'是' if result['same_srs'] else '否'}")
        print(f"空间范围重叠：{'是' if result['overlap'] else '否'}")
        print(f"影像范围：{result['raster_extent']}")
        print(f"矢量范围：{result['vector_extent']}")

    if not result["same_srs"]:
        raise SystemExit("检查失败：坐标系不一致，请先在ArcGIS Pro中投影标注。")
    if not result["overlap"]:
        raise SystemExit("检查失败：影像和标注不重叠，0样本可能是正确结果。")
    if not args.json:
        print("空间预检通过。")


if __name__ == "__main__":
    main()
