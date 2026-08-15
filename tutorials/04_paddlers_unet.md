# 第4章：使用 PaddleRS 训练 UNet

在PaddleRS官方仓库中了解Paddle: [Paddle](https://github.com/PaddlePaddle/PaddleRS/tree/develop)

## 1. 安装原则

PaddlePaddle 的CPU/GPU安装包与操作系统、Python版本和CUDA版本有关。请先按飞桨官方安装说明选择匹配版本，再安装或准备 PaddleRS。

验证环境：

```powershell
python -c "import paddle; print(paddle.__version__); print(paddle.is_compiled_with_cuda())"
python -c "import paddlers; print(paddlers.__version__)"
```

如果直接使用 PaddleRS 源码，不必修改脚本，可以传入：

```powershell
--paddlers-root D:\path\to\PaddleRS
```

## 2. 先做冒烟训练

```powershell
python scripts/train_unet.py --smoke
```

冒烟模式只取2个训练样本和2个验证样本，训练1轮。它只回答三个问题：

1. Paddle环境能否导入；
2. 数据格式能否被读取；
3. 模型能否完成一次前向、反向、评价和保存。

冒烟模式的mIoU没有统计意义。

## 3. 正式训练

```powershell
python scripts/train_unet.py --epochs 30 --batch-size 2
```

默认训练配置：

- 模型：UNet；
- 输入：3波段RGB；
- 类别：背景、建筑物；
- 增强：随机水平翻转、随机垂直翻转；
- 归一化：mean/std均为0.5；
- 学习率：0.001；
- 每轮保存并在验证集评价。

显存不足时先减小 `--batch-size`。没有CUDA时脚本会回退到CPU，也可以显式添加 `--cpu`。

正式数据集应包含足够多的区域和建筑形态。仓库演示数据只适合确认流程，不适合训练可部署模型。
