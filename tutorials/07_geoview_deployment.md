# 第7章：把训练好的模型导入GeoView检验效果

本章默认你已经安装并启动GeoView，只介绍如何导入训练好的UNet并查看建筑物分割结果。

## 1. 选择最佳模型

训练目录中通常包含 `best_model` 和多个 `epoch_N` 检查点。用于检验和部署时应选择验证集表现最好的 `best_model`，不要因为最后一轮编号最大就直接使用它。

## 2. 导出到GeoView模型目录

GeoView不能直接使用训练目录中的 `model.pdparams`，需要先通过PaddleRS导出部署模型。

```powershell
python <PaddleRS目录>/deploy/export/export_model.py `
  --model_dir runs/unet/best_model `
  --save_dir <GeoView目录>/backend/model/semantic_segmentation/building_unet
```

`building_unet` 是模型文件夹名称，可以改成其他容易识别的英文名称。

导出后检查目录中是否包含：

```text
building_unet/
├── model.pdmodel
├── model.pdiparams
├── model.pdiparams.info
├── model.yml
└── pipeline.yml
```

五个文件都存在，才是GeoView可以使用的部署模型。

## 3. 在GeoView中查看结果

1. 刷新GeoView页面；如果新模型没有出现，再重启GeoView后端。
2. 在左侧导航栏进入“地物分类”。
3. 点击上传，选择验证集中的遥感影像。
4. 在“可选训练模型”中选择刚导入的UNet。
5. 点击“开始处理”，等待建筑物分割结果显示。
6. 找到该影像对应的真实PNG掩膜，对比预测结果。

对比时主要观察：

- 建筑物是否有明显漏检；
- 道路、裸地等区域是否被误判为建筑物；
- 建筑物轮廓是否完整；
- 相邻建筑物是否被错误连接。

GeoView适合直观展示模型效果，但正式评价仍应使用验证集上的mIoU、建筑物IoU和F1等指标。

## 常见问题

### 模型没有出现在列表中

确认模型位于：

```text
<GeoView目录>/backend/model/semantic_segmentation/<模型名称>/
```

### 选择模型后无法运行

确认目录中是前面列出的五文件部署格式。不要把训练阶段的 `best_model` 文件夹直接复制进GeoView。
