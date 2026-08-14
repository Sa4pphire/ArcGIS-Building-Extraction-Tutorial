"""Train a PaddleRS UNet with either a tiny smoke subset or the full dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from geo_utils import repository_root


def build_parser() -> argparse.ArgumentParser:
    root = repository_root()
    parser = argparse.ArgumentParser(description="使用PaddleRS训练建筑物UNet语义分割模型")
    parser.add_argument("--dataset", type=Path, default=root / "outputs/segmentation")
    parser.add_argument("--output", type=Path, default=root / "runs/unet")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--smoke", action="store_true", help="使用2个训练和2个验证样本训练1轮")
    parser.add_argument("--cpu", action="store_true", help="强制使用CPU")
    parser.add_argument("--paddlers-root", type=Path, help="可选的PaddleRS源码目录")
    return parser


def subset_file(source: Path, destination: Path, count: int) -> Path:
    lines = [line for line in source.read_text(encoding="utf-8").splitlines() if line]
    if len(lines) < count:
        raise RuntimeError(f"{source} 至少需要 {count} 条记录")
    destination.write_text("\n".join(lines[:count]) + "\n", encoding="utf-8")
    return destination


def main() -> None:
    args = build_parser().parse_args()
    if args.paddlers_root:
        sys.path.insert(0, str(args.paddlers_root.resolve()))

    try:
        import paddle
        import paddlers as pdrs
        from paddlers import transforms as T
    except ImportError as exc:
        raise SystemExit(
            "无法导入PaddlePaddle/PaddleRS。请按 tutorials/04_paddlers_unet.md 安装环境，"
            "或使用 --paddlers-root 指定PaddleRS源码目录。"
        ) from exc

    train_list = args.dataset / "train.txt"
    val_list = args.dataset / "val.txt"
    labels = args.dataset / "labels.txt"
    for required in (train_list, val_list, labels):
        if not required.is_file():
            raise SystemExit(f"缺少数据集文件：{required}")

    args.output.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        train_list = subset_file(train_list, args.output / "smoke_train.txt", 2)
        val_list = subset_file(val_list, args.output / "smoke_val.txt", 2)
        epochs = 1
        batch_size = 1
    else:
        epochs = args.epochs
        batch_size = args.batch_size

    if args.cpu:
        paddle.set_device("cpu")
    elif paddle.is_compiled_with_cuda():
        paddle.set_device("gpu:0")
    else:
        print("当前PaddlePaddle不含CUDA，自动使用CPU。")
        paddle.set_device("cpu")

    train_transforms = T.Compose(
        [
            T.DecodeImg(),
            T.RandomHorizontalFlip(prob=0.5),
            T.RandomVerticalFlip(prob=0.5),
            T.Normalize(mean=[0.5] * 3, std=[0.5] * 3),
            T.ArrangeSegmenter("train"),
        ]
    )
    eval_transforms = T.Compose(
        [
            T.DecodeImg(),
            T.Normalize(mean=[0.5] * 3, std=[0.5] * 3),
            T.ReloadMask(),
            T.ArrangeSegmenter("eval"),
        ]
    )
    train_dataset = pdrs.datasets.SegDataset(
        data_dir=str(args.dataset),
        file_list=str(train_list),
        label_list=str(labels),
        transforms=train_transforms,
        num_workers=0,
        shuffle=True,
    )
    eval_dataset = pdrs.datasets.SegDataset(
        data_dir=str(args.dataset),
        file_list=str(val_list),
        label_list=str(labels),
        transforms=eval_transforms,
        num_workers=0,
        shuffle=False,
    )
    print(
        f"device={paddle.device.get_device()}, train={len(train_dataset)}, "
        f"validation={len(eval_dataset)}, epochs={epochs}"
    )
    model = pdrs.tasks.seg.UNet(in_channels=3, num_classes=2)
    model.train(
        num_epochs=epochs,
        train_dataset=train_dataset,
        train_batch_size=batch_size,
        eval_dataset=eval_dataset,
        save_interval_epochs=1,
        log_interval_steps=1 if args.smoke else 20,
        save_dir=str(args.output),
        pretrain_weights=None,
        learning_rate=args.learning_rate,
        early_stop=False,
        use_vdl=False,
    )
    print(f"训练完成：{args.output.resolve()}")


if __name__ == "__main__":
    main()
