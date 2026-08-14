"""Shared GDAL helpers for the tutorial command-line tools."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import numpy as np
from osgeo import gdal, ogr
from PIL import Image


gdal.UseExceptions()
ogr.UseExceptions()


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def open_raster(path: Path):
    dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f"无法打开栅格影像：{path}")
    return dataset


def open_vector(path: Path):
    dataset = ogr.Open(str(path), 0)
    if dataset is None:
        raise RuntimeError(f"无法打开矢量标注：{path}")
    return dataset


def tile_starts(length: int, window_size: int, stride: int) -> list[int]:
    if length <= 0 or window_size <= 0 or stride <= 0:
        raise ValueError("length、window_size 和 stride 必须为正数")
    if length <= window_size:
        return [0]
    count = math.ceil((length - window_size) / stride) + 1
    return [index * stride for index in range(count)]


def spatial_split_rows(rows: Iterable[int], train_ratio: float = 0.67):
    unique_rows = sorted(set(rows))
    if len(unique_rows) < 3:
        raise ValueError("空间划分至少需要三个包含有效样本的切片行")
    train_count = max(1, min(len(unique_rows) - 2, int(len(unique_rows) * train_ratio)))
    train_rows = set(unique_rows[:train_count])
    buffer_row = unique_rows[train_count]
    validation_rows = set(unique_rows[train_count + 1 :])
    return train_rows, buffer_row, validation_rows


def shifted_geotransform(source, x_offset: int, y_offset: int):
    origin_x = source[0] + x_offset * source[1] + y_offset * source[2]
    origin_y = source[3] + x_offset * source[4] + y_offset * source[5]
    return (
        origin_x,
        source[1],
        source[2],
        origin_y,
        source[4],
        source[5],
    )


def bounds_from_geotransform(geotransform, width: int, height: int):
    corners = [
        gdal.ApplyGeoTransform(geotransform, 0, 0),
        gdal.ApplyGeoTransform(geotransform, width, 0),
        gdal.ApplyGeoTransform(geotransform, 0, height),
        gdal.ApplyGeoTransform(geotransform, width, height),
    ]
    xs = [point[0] for point in corners]
    ys = [point[1] for point in corners]
    return min(xs), min(ys), max(xs), max(ys)


def extents_overlap(first: Iterable[float], second: Iterable[float]) -> bool:
    a_min_x, a_min_y, a_max_x, a_max_y = first
    b_min_x, b_min_y, b_max_x, b_max_y = second
    return not (
        a_max_x <= b_min_x
        or b_max_x <= a_min_x
        or a_max_y <= b_min_y
        or b_max_y <= a_min_y
    )


def raster_extent(dataset):
    return bounds_from_geotransform(
        dataset.GetGeoTransform(), dataset.RasterXSize, dataset.RasterYSize
    )


def layer_extent(layer):
    min_x, max_x, min_y, max_y = layer.GetExtent()
    return min_x, min_y, max_x, max_y


def validate_raster_vector(raster, layer) -> dict:
    raster_srs = raster.GetSpatialRef()
    vector_srs = layer.GetSpatialRef()
    if raster_srs is None or vector_srs is None:
        raise ValueError("影像或矢量缺少空间参考")

    geometry_type = ogr.GT_Flatten(layer.GetLayerDefn().GetGeomType())
    if geometry_type not in (ogr.wkbPolygon, ogr.wkbMultiPolygon):
        raise ValueError("标注图层必须为 Polygon 或 MultiPolygon")

    raster_bounds = raster_extent(raster)
    vector_bounds = layer_extent(layer)
    same_srs = bool(raster_srs.IsSame(vector_srs))
    overlap = extents_overlap(raster_bounds, vector_bounds) if same_srs else False
    return {
        "same_srs": same_srs,
        "overlap": overlap,
        "raster_extent": raster_bounds,
        "vector_extent": vector_bounds,
        "feature_count": int(layer.GetFeatureCount()),
        "geometry_type": ogr.GeometryTypeToName(layer.GetLayerDefn().GetGeomType()),
        "raster_width": int(raster.RasterXSize),
        "raster_height": int(raster.RasterYSize),
        "raster_bands": int(raster.RasterCount),
        "projection_name": raster_srs.GetName() or "unknown",
    }


def read_padded_rgb(raster, x_offset: int, y_offset: int, size: int) -> np.ndarray:
    read_width = min(size, raster.RasterXSize - x_offset)
    read_height = min(size, raster.RasterYSize - y_offset)
    if read_width <= 0 or read_height <= 0:
        raise ValueError(f"窗口超出影像范围：x={x_offset}, y={y_offset}")
    array = raster.ReadAsArray(x_offset, y_offset, read_width, read_height)
    if array is None:
        raise RuntimeError(f"读取影像失败：x={x_offset}, y={y_offset}")
    if array.ndim == 2:
        array = array[np.newaxis, :, :]
    if array.shape[0] < 3:
        raise ValueError("教程要求至少三个影像波段")
    if array.dtype != np.uint8:
        raise ValueError(f"教程JPEG导出要求Byte影像，当前类型为 {array.dtype}")
    padded = np.zeros((3, size, size), dtype=np.uint8)
    padded[:, :read_height, :read_width] = array[:3]
    return np.moveaxis(padded, 0, -1)


def rasterize_mask(layer, geotransform, projection: str, size: int) -> np.ndarray:
    bounds = bounds_from_geotransform(geotransform, size, size)
    layer.SetSpatialFilterRect(*bounds)
    try:
        if layer.GetFeatureCount() == 0:
            return np.zeros((size, size), dtype=np.uint8)
        memory = gdal.GetDriverByName("MEM").Create("", size, size, 1, gdal.GDT_Byte)
        memory.SetGeoTransform(geotransform)
        memory.SetProjection(projection)
        band = memory.GetRasterBand(1)
        band.Fill(0)
        result = gdal.RasterizeLayer(memory, [1], layer, burn_values=[255])
        if result != 0:
            raise RuntimeError("建筑物面栅格化失败")
        mask = band.ReadAsArray()
        memory = None
        if mask is None:
            raise RuntimeError("无法读取栅格化标签")
        return mask.astype(np.uint8, copy=False)
    finally:
        layer.SetSpatialFilter(None)


def save_rgb_jpeg(array: np.ndarray, path: Path, quality: int = 95) -> None:
    Image.fromarray(array, mode="RGB").save(
        path, format="JPEG", quality=quality, subsampling=0
    )


def save_mask_png(mask: np.ndarray, path: Path) -> None:
    Image.fromarray(mask, mode="L").save(path, format="PNG", compress_level=6)


def collect_stems(directory: Path, pattern: str) -> set[str]:
    return {path.stem for path in directory.glob(pattern)}


def validate_segmentation_pairs(images_dir: Path, labels_dir: Path, size: int) -> dict:
    image_stems = collect_stems(images_dir, "*.jpg")
    label_stems = collect_stems(labels_dir, "*.png")
    if image_stems != label_stems:
        raise RuntimeError(
            f"影像标签未一一对应：缺标签 {len(image_stems-label_stems)}，"
            f"缺影像 {len(label_stems-image_stems)}"
        )

    invalid = []
    empty = []
    for stem in sorted(image_stems):
        with Image.open(images_dir / f"{stem}.jpg") as image:
            image.load()
            if image.format != "JPEG" or image.mode != "RGB" or image.size != (size, size):
                invalid.append(stem)
        with Image.open(labels_dir / f"{stem}.png") as label:
            label.load()
            values = set(np.unique(np.asarray(label)).tolist())
            if label.format != "PNG" or label.mode != "L" or label.size != (size, size):
                invalid.append(stem)
            if not values.issubset({0, 255}):
                invalid.append(stem)
            if label.getbbox() is None:
                empty.append(stem)
    if invalid or empty:
        raise RuntimeError(f"数据审计失败：格式异常 {len(set(invalid))}，空标签 {len(empty)}")
    return {"pairs": len(image_stems), "invalid": 0, "empty": 0}
