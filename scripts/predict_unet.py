"""Load a saved PaddleRS UNet checkpoint and save a building mask."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from geo_utils import repository_root


def build_parser() -> argparse.ArgumentParser:
    root = repository_root()
    parser = argparse.ArgumentParser(description="使用PaddleRS UNet检查点预测建筑物掩膜")
    parser.add_argument("--model", type=Path, default=root / "runs/unet/best_model")
    parser.add_argument("--image", type=Path, help="待预测JPEG；默认使用验证集第一张影像")
    parser.add_argument("--dataset", type=Path, default=root / "outputs/segmentation")
    parser.add_argument("--output", type=Path, default=root / "runs/prediction.png")
    parser.add_argument("--paddlers-root", type=Path, help="可选的PaddleRS源码目录")
    return parser


def first_validation_image(dataset: Path) -> Path:
    val_file = dataset / "val.txt"
    if not val_file.is_file():
        raise SystemExit(f"缺少验证列表：{val_file}")
    first = next((line for line in val_file.read_text(encoding="utf-8").splitlines() if line), None)
    if first is None:
        raise SystemExit("验证列表为空")
    return dataset / first.split()[0]


def main() -> None:
    args = build_parser().parse_args()
    if args.paddlers_root:
        sys.path.insert(0, str(args.paddlers_root.resolve()))
    try:
        import paddlers as pdrs
    except ImportError as exc:
        raise SystemExit("无法导入PaddleRS，请先完成训练环境安装。") from exc

    image_path = args.image or first_validation_image(args.dataset)
    model = pdrs.tasks.load_model(str(args.model))
    prediction = model.predict(str(image_path))
    mask = np.asarray(prediction["label_map"], dtype=np.uint8) * 255
    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask, mode="L").save(args.output, format="PNG")
    print(f"输入影像：{image_path.resolve()}")
    print(f"预测掩膜：{args.output.resolve()}")


if __name__ == "__main__":
    main()
