# 第5章：预测、评价与结果解释

## 1. 运行预测

训练后，PaddleRS会在输出目录中保存 `best_model` 和各轮检查点。使用最佳模型预测验证集第一张影像：

```powershell
python scripts/predict_unet.py
```

指定其他模型和影像：

```powershell
python scripts/predict_unet.py `
  --model runs\unet\best_model `
  --image outputs\segmentation\images\tile_r005_c000.jpg `
  --output runs\prediction.png
```

输出PNG中0表示背景，255表示预测建筑物。

## 2. 关注哪些指标

- `IoU`：预测区域与真实区域交集除以并集；
- `mIoU`：各类别IoU的平均值；
- `F1-score`：综合像素精确率与召回率；
- `oacc`：全部像素的总体准确率。

建筑物通常只占影像的一部分，因此不能只看总体准确率。模型把大多数像素预测为背景，也可能得到较高oacc，但建筑物IoU很低。

## 3. 正确比较模型

- 使用相同的空间验证区；
- 不要把重叠切片随机混入训练和验证；
- 同时报告最佳轮次与最终轮次；
- 保存混淆矩阵和预测图进行目视检查；
- 小型演示数据的结果不要与完整项目指标混为一谈。

完整项目最佳模型位于第12轮，验证集mIoU为0.7233。该结果来自1,237对正式数据中的空间划分验证集，不是本仓库29对演示样本的结果。
