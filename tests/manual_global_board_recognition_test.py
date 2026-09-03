"""独立离线全盘测试。无参数时询问截图、关卡和可选全空基准路径。"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vision.board_recognition import recognize_board_files


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="当前单帧实机截图")
    parser.add_argument("--level", type=int, help="关卡号，默认11")
    parser.add_argument("--reference", help="显式指定全空基准图；不会自动猜测")
    parser.add_argument("--output", type=Path, help="本轮独立输出目录")
    args = parser.parse_args(argv)
    if not args.image:
        args.image = input("当前截图路径：").strip().strip('"')
        if args.level is None:
            try:
                args.level = int(input("关卡号 [11]：").strip() or "11")
            except ValueError:
                parser.error("关卡号必须为正整数")
        if args.reference is None:
            args.reference = input("全空基准路径 [Enter使用关卡配置]：").strip().strip('"') or None
    output = args.output or PROJECT_ROOT / "outputs" / "manual_global_board" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    try:
        result = recognize_board_files(args.image, level=args.level if args.level is not None else 11,
                                       reference_path=args.reference, output_dir=output)
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as exc:
        print(f"识别未完成：{exc}", file=sys.stderr)
        return 1
    symbols = {"unknown": "U", "miss": "M", "hit": "H", "sunk": "S"}
    print("\nU=UNKNOWN(未探测) M=MISS H=HIT S=SUNK；行列显示从1开始")
    for row in result.states:
        print(" ".join(symbols[state.value] for state in row))
    for cell in result.cells:
        print(f"({cell.row+1},{cell.col+1}) {cell.state.value.upper():7s} "
              f"confidence={cell.confidence:.3f} needs_review={cell.needs_review} {cell.reason}")
    print(f"\n数量：{result.counts}")
    print(f"低可信格：{[(r+1, c+1) for r, c in result.review_cells]}")
    print("SUNK潜艇（行列从1开始）：")
    for ship in result.sunk_submarines:
        print(f"  {ship.direction} 长度={ship.length} "
              f"格子={[(r+1, c+1) for r, c in ship.cells]} "
              f"confidence={ship.confidence:.3f} {ship.reason}")
    if not result.sunk_submarines:
        print("  无")
    print(f"对齐：{result.alignment}")
    print(f"素材质量：{result.quality} / {result.quality_score:.3f}，整盘可用={result.valid}")
    print(f"异常：{result.issues}")
    print(f"debug目录：{output.resolve()}")
    print("结果需要人工复核；confidence 是证据分，尚未用人工标签校准。")
    return 0 if result.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
