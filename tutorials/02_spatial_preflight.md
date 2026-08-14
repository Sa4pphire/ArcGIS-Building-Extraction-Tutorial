# 第2章：影像与标注空间预检

数据切片最常见的失败不是循环或文件写入错误，而是影像和矢量根本不在同一坐标空间。

## 1. 运行检查

演示数据直接运行：

```powershell
python scripts/check_spatial_match.py
```

检查自己的数据：

```powershell
python scripts/check_spatial_match.py `
  --raster D:\data\image.tif `
  --vector D:\data\buildings.shp
```

需要机器可读结果时增加 `--json`。

## 2. 理解输出

脚本检查：

- 栅格宽、高和波段数；
- 矢量要素数和几何类型；
- 两者是否具有空间参考；
- 坐标系是否一致；
- 空间范围是否重叠。

只有坐标系一致时，才能直接比较两个范围。若坐标系不同，应在 ArcGIS Pro 中使用“投影”工具生成新图层，而不是只修改 `.prj` 文件。

## 3. 为什么0样本可能是正确结果

如果 Shapefile 的范围与影像不重叠，那么每一个滑动窗口都没有建筑物，导出0对样本是合理结果。此时应重新确认影像与标注的对应关系，而不是删除空标签判断。

例如完整项目有 `sample2.tif + sf1.shp` 不重叠；经核对后，正确组合是 `sample1.tif + sf1.shp` 与 `sample2.tif + sf2.shp`。这也是将空间预检设为独立步骤的原因。
