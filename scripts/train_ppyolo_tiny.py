"""Train PaddleRS PP-YOLO Tiny on the tutorial VOC dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from geo_utils import repository_root


def build_parser() -> argparse.ArgumentParser:
    root = repository_root()
    parser = argparse.ArgumentParser(description="使用PaddleRS训练PP-YOLO Tiny建筑物检测模型")
    parser.add_argument("--dataset", type=Path, default=root / "outputs/detection")
    parser.add_argument("--output", type=Path, default=root / "runs/ppyolotiny")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--smoke", action="store_true", help="使用2+2样本训练1轮")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--paddlers-root", type=Path)
    return parser


def subset(source: Path, destination: Path) -> Path:
    lines = [line for line in source.read_text(encoding="utf-8").splitlines() if line]
    if len(lines) < 2:
        raise RuntimeError(f"{source} 至少需要2条记录")
    destination.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
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
        raise SystemExit("无法导入PaddlePaddle/PaddleRS，请先完成训练环境安装。") from exc

    args.output.mkdir(parents=True, exist_ok=True)
    train_list = args.dataset / "train.txt"
    val_list = args.dataset / "val.txt"
    if args.smoke:
        train_list = subset(train_list, args.output / "smoke_train.txt")
        val_list = subset(val_list, args.output / "smoke_val.txt")
    if args.cpu:
        paddle.set_device("cpu")
    elif paddle.is_compiled_with_cuda():
        paddle.set_device("gpu:0")
    else:
        paddle.set_device("cpu")

    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]
    train_transforms = T.Compose(
        [
            T.DecodeImg(),
            T.RandomHorizontalFlip(),
            T.RandomVerticalFlip(),
            T.Normalize(mean=mean, std=std),
            T.ArrangeDetector("train"),
        ]
    )
    eval_transforms = T.Compose(
        [
            T.DecodeImg(),
            T.Resize(target_size=512),
            T.Normalize(mean=mean, std=std),
            T.ArrangeDetector("eval"),
        ]
    )
    train_dataset = pdrs.datasets.VOCDetDataset(
        str(args.dataset), str(train_list), train_transforms, str(args.dataset / "labels.txt"),
        num_workers=0, shuffle=True, allow_empty=True
    )
    eval_dataset = pdrs.datasets.VOCDetDataset(
        str(args.dataset), str(val_list), eval_transforms, str(args.dataset / "labels.txt"),
        num_workers=0, shuffle=False, allow_empty=True
    )
    model = pdrs.tasks.det.PPYOLOTiny(num_classes=len(train_dataset.labels))
    model.train(
        num_epochs=1 if args.smoke else args.epochs,
        train_dataset=train_dataset,
        train_batch_size=1 if args.smoke else args.batch_size,
        eval_dataset=eval_dataset,
        save_interval_epochs=1,
        log_interval_steps=1 if args.smoke else 20,
        save_dir=str(args.output),
        pretrain_weights=None,
        learning_rate=0.0001,
        use_vdl=False,
    )
    print(f"训练完成：{args.output.resolve()}")


if __name__ == "__main__":
    main()
