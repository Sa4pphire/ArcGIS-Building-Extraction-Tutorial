# 第1章：在 ArcGIS Pro 中制作建筑物面标注

本章目标是从一幅有空间参考的 GeoTIFF 出发，得到与影像坐标系一致的建筑物面 Shapefile。

## 1. 新建工程并加载影像

1. 打开 ArcGIS Pro，新建“地图”工程。
2. 在“地图”选项卡中选择“添加数据”，加载 GeoTIFF。
3. 右键影像图层，打开“属性 → 源”，记录坐标系、像元大小和空间范围。

不要先假定数据是经纬度坐标。教程演示数据使用投影坐标，单位为米。

## 2. 创建面标注图层
<img height="700" alt="QQ20260814-173204" src="https://github.com/user-attachments/assets/21a2ac8b-6205-4e9a-804a-ab7bc2d8ce38" />

1. 在“目录”窗格中选择输出文件夹。
2. 新建 Shapefile 或面要素类，几何类型选择 `面`。
3. 坐标系选择“从当前地图/影像导入”。
4. 建议增加文本字段 `class_name`，统一填写 `building`。

<img  height="700" alt="QQ20260814-173351" src="https://github.com/user-attachments/assets/ae07d1da-845b-48ab-8754-b242d9f34e6c" />

Shapefile 不是单个文件。至少要一起保留：

```text
buildings.shp   几何
buildings.shx   几何索引
buildings.dbf   属性表
buildings.prj   坐标系
buildings.cpg   字符编码
```

## 3. 绘制建筑物
<img  height="700" alt="QQ20260814-175433" src="https://github.com/user-attachments/assets/cc2fa30c-07a7-416b-a47f-75a4b0cd1d0e" />

1. 打开“编辑 → 创建”，选择建筑物面模板。
2. 沿屋顶可见边界逐点绘制多边形。
3. 双击或按 `F2` 完成当前面。
4. 点击“保存编辑”，并抽查是否存在自相交、极小碎片和明显漏标。
<img  height="700" alt="QQ20260814-175514" src="https://github.com/user-attachments/assets/3f3d84c8-19b5-4bf9-b23c-7d40113b2f43" />

## 4. 导出与检查

完成后目标图层 Shapefile，确认：

- 图层坐标系与影像一致；
- 所有配套文件位于同一目录；
- 在 ArcGIS Pro 中关闭再重新加载后仍能正常显示；
- 建筑物面与影像屋顶位置一致，没有整体偏移。

接下来不要立刻切片，先进入[第2章](02_spatial_preflight.md)做程序化空间预检。
