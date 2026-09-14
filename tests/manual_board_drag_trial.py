"""拖动可行性实验：先查看路线图，再显式执行；不接入正式循环。"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from controllers import AdbController, PageController
from flows.board_drag_trial import run_board_drag_trial
from sonar_config import get_level_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", type=int, required=True)
    parser.add_argument("--serial", default=config.ADB_SERIAL)
    parser.add_argument("--execute", action="store_true", help="确认循环已停止且已检查 plan.png 后，执行下移和复位")
    args = parser.parse_args()
    output = PROJECT_ROOT / "outputs/board_drag_trial" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    print("请保持自动循环停止；不修改网络、不探测格子。")
    print(f"调试目录：{output}")
    try:
        adb = AdbController(serial=args.serial)
        result = run_board_drag_trial(adb, PageController(adb), get_level_config(args.level), output,
                                      execute=args.execute)
    except Exception as exc:
        print(f"实验未完成：{exc}。请检查现场和调试目录。", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not args.execute:
        print("仅生成路线图，尚未拖动。检查 plan.png 后才可加 --execute。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
