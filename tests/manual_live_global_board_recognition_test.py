"""从当前 ADB 实机连续采帧测试全局识别；只读画面，不写棋盘或操作网络。"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from controllers import AdbController, PageController
from flows.board_sync_flow import recognize_current_board, apply_automatic_board_sync
from flows.level_loop import create_level_state


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", type=int, default=11)
    parser.add_argument("--serial", default=config.ADB_SERIAL)
    parser.add_argument("--audit-auto", action="store_true", help="在一次性内存模型验证自动接管审核，不启动循环")
    args = parser.parse_args(argv)
    try:
        adb = AdbController(serial=args.serial)
        page = PageController(adb)
        live = recognize_current_board(adb, page, level=args.level)
    except Exception as exc:
        print(f"实时识别失败：{exc}", file=sys.stderr)
        return 1
    result = live.board_result
    symbols = {"unknown": "U", "miss": "M", "hit": "H", "sunk": "S"}
    for row in result.states:
        print(" ".join(symbols[state.value] for state in row))
    print(f"数量：{result.counts}")
    print(f"多帧一致率：{live.mean_state_agreement:.3f}，稳定={live.stable}")
    print(f"低可信格：{[(r + 1, c + 1) for r, c in result.review_cells]}")
    print(f"质量：{result.quality} / {result.quality_score:.3f}，可用={result.valid}")
    print(f"帧数：{live.frame_count}，可用帧：{live.usable_frame_count}，末帧可用：{live.latest_frame_usable}")
    print(f"异常：{result.issues}")
    print(f"调试：{result.debug_paths}")
    for cell in result.cells:
        print(f"({cell.row + 1},{cell.col + 1}) {cell.state.value.upper()} "
              f"confidence={cell.confidence:.3f} review={cell.needs_review} {cell.reason}")
    if args.audit_auto:
        state = create_level_state(args.level)
        try:
            sync = apply_automatic_board_sync(live, state.board, state.strategy)
        except Exception as exc:
            print(f"自动接管审核拒绝：{exc}；请人工检查。")
            return 2
        print(f"一次性模型审核通过，下一格={sync.applied.next_cell}；未进入循环")
    print("本工具只读取实时截图，不修改正式棋盘、策略、页面或网络。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
