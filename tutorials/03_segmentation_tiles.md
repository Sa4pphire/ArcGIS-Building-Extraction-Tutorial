# 第3章：制作语义分割切片

制作切片有两种方式。想快速完成数据制作，可以使用图形界面；想了解处理原理或批量处理，可以使用本仓库脚本。

<img width="700" height="700" alt="demo_raster" src="https://github.com/user-attachments/assets/2999e04e-905a-4a36-803b-4f7c6a0fc56c" />

完整图像 将对其进行切片处理进行训练

## 1. 方法一：使用图形界面工具

[Remote-sensing-image-Segment](https://github.com/Sa4pphire/Remote-sensing-image-Segment) 提供了现成的图形界面，可以选择遥感影像、Shapefile和输出目录来制作训练切片。

如果你刚开始接触Python或只想尽快准备数据，建议先使用这个工具。具体安装和按钮操作以该仓库README为准。

无论使用哪个程序，导出完成后都要确认：

- 影像和标签文件名一一对应；
- 切片尺寸都是512×512；
- 没有全黑的空标签；
- 遥感影像可以使用JPEG，类别标签必须使用无损PNG；
- 标签中的背景和建筑物像元值保持一致。

## 2. 方法二：使用本仓库脚本

原有脚本继续完整保留，适合学习GDAL栅格化过程、批量运行和二次开发。

### 导出影像与标签

```powershell
python scripts/export_segmentation_tiles.py
```

自己的数据可以显式指定路径：

```powershell
python scripts/export_segmentation_tiles.py `
  --raster D:\data\image.tif `
  --vector D:\data\buildings.shp `
  --output D:\data\segmentation `
  --window-size 512 `
  --stride 256
```

若输出目录已有本教程生成的切片，确认后使用 `--overwrite`。



## 3. 参数含义

- `window-size=512`：每个训练样本为512×512像素；
- `stride=256`：窗口每次移动256像素，因此相邻样本有50%重叠；
- `jpeg-quality=95`：RGB影像采用高质量JPEG；
- 标签始终使用PNG，以防有损压缩改变类别值。

窗口超出原影像右侧或底部时会使用0填充。演示影像尺寸正好为2048×2048，因此不会出现边缘填充。

## 4. 空标签与一一对应

程序先把当前窗口内的建筑物面栅格化为：

- `0`：背景；
- `255`：建筑物。

若标签全为0，则影像和标签都不写出。完成后程序重新检查：

- JPEG和PNG的文件名stem完全一致；
- 影像为RGB JPEG；
- 标签为单通道PNG；
- 尺寸都是512×512；
- 标签值仅包含0和255；
- 不存在全零标签。

### 一一对应演示


<img width="256" height="256" alt="sample_tile" src="https://github.com/user-attachments/assets/8256a3b0-9832-468d-8e23-1c6b1ebbc0fd" />

切片后的jpg图像,与下方的mask图像对应。单张分辨率为预设的512x512，其在输出文件夹image中被命名为` corp_示例编号1 `,对应下方生成的label中生成的文件

<img width="256" height="256" alt="sample_mask_overlay" src="https://github.com/user-attachments/assets/7871ae23-ed33-4208-94ba-bd5eb69e5dec" />


<img width="256" height="256" alt="sample_mask" src="https://github.com/user-attachments/assets/ac98f835-71c4-4e91-b66c-528e80fb1fe2" />

切片后的在label文件夹中生成的png图像,单张分辨率为预设的512x512，其在输出文件夹label中被命名为` corp_示例编号1 `,对应上方生成的image中生成的文件


## 5. 空间划分

```powershell
python scripts/split_segmentation_dataset.py
```

切片具有50%重叠。如果随机把相邻切片分别放入训练集和验证集，验证结果会过于乐观。因此脚本按地理行划分，在训练区域和验证区域之间留出一整行缓冲样本。

该步骤还会生成 `masks/`，将可视化标签 `{0,255}` 转换为 PaddleRS 类别索引 `{0,1}`。不要直接把255当作类别编号传给二分类模型。
