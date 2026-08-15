# 第6章：VOC与PP-YOLO Tiny目标检测扩展

语义分割预测每个像素是否属于建筑物；目标检测则为每个建筑物预测一个矩形框。二者可以使用同一份建筑物面标注，但标签生成方式不同。

在进行语义分割模型训练时需要：原始图像 + 对应的像素级标注图（Mask）。标注图上每个像素的灰度值或颜色，对应一个类别（如0代表背景，1代表人，2代表汽车）。

而训练目标检测训练时，则需要原始图像 + 对应的边界框标注文件（通常为XML、JSON或TXT格式）。每个框由类别标签 + 左上角坐标(x1,y1) + 右下角坐标(x2,y2) 组成。
现在我们来导出VOC数据集来进行目标检测模型训练

## 1. 导出VOC数据

```powershell
python scripts/export_voc_detection.py
```

脚本对每个512×512窗口执行：

1. 查找与窗口相交的建筑物面；
2. 将面裁剪到窗口范围；
3. 计算裁剪后几何的像素边界框；
4. 保存JPEG和同名PASCAL VOC XML；
5. 按空间行生成训练、验证和缓冲列表。

默认跳过没有建筑物框的窗口。需要保留负样本时添加 `--include-empty`。

## 2. 审计VOC数据

```powershell
python scripts/audit_voc_dataset.py --write-report
```

审计包括：

- JPEG与XML严格同名配对；
- 类别统一为 `building`；
- `xmin < xmax`、`ymin < ymax`；
- 坐标位于影像范围内；
- 训练、验证和缓冲集互不重叠；
- 三个列表完整覆盖导出数据。

## 3. 冒烟训练

```powershell
python scripts/train_ppyolo_tiny.py --smoke
```

正式训练入口：

```powershell
python scripts/train_ppyolo_tiny.py --epochs 30 --batch-size 2
```

教程默认不下载COCO预训练权重，避免把网络下载问题与数据格式问题混在一起。实际项目可在确认网络和权重来源后增加预训练配置。

当前完整目标检测项目已完成数据审计和训练入口准备，但本轮小样本冒烟训练与正式训练都尚未完成，因此仓库不宣称已有可部署的检测模型。
