from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import config_test

from controllers.adb_controller import AdbController
from controllers.page_controller import PageController
from sonar import (
    CheckerboardHuntStrategy,
    SonarBoard,
)


def main() -> None:
    if config_test.TEST_BOARD_QUAD is None:
        raise RuntimeError(
            "config_test.TEST_BOARD_QUAD 还没有填写"
        )

    adb = AdbController()
    adb.ensure_device_online()

    page = PageController(adb)

    board = SonarBoard(
        n=config_test.TEST_GRID_SIZE,
        submarines=config_test.TEST_SUBMARINES,
    )
    board.set_screen_quad(
        config_test.TEST_BOARD_QUAD
    )

    strategy = CheckerboardHuntStrategy(
        board,
        hunt_parity=config_test.TEST_HUNT_PARITY,
        use_safety_rule=config_test.TEST_USE_SAFETY_RULE,
    )

    print("策略 + 棋盘映射 + ADB 点击人工联调")
    print("流程：策略选格 -> ADB 点击 -> 你人工输入 HIT / MISS -> 策略继续")
    print("输入 q 可以随时退出。")
    print()

    shot_count = 0

    while not strategy.done:
        cell = strategy.choose_next_cell()

        if cell is None:
            print("策略没有找到可继续探测的格子")
            break

        row, col = cell
        x, y = board.screen_point(
            row,
            col,
        )

        print(
            f"下一格：逻辑 ({row}, {col}) "
            f"-> 模拟器 ({x}, {y})"
        )

        command = input(
            "按 Enter 实际点击；输入 q 退出："
        ).strip().lower()

        if command == "q":
            break

        page.click_point(
            x,
            y,
        )

        shot_count += 1

        while True:
            result = input(
                "输入结果 h=命中，m=未命中，q=退出："
            ).strip().lower()

            if result == "q":
                print("已退出；当前格仍在等待结果")
                return

            if result not in ("h", "m"):
                print("输入无效")
                continue

            hit = result == "h"

            newly_confirmed = strategy.report_result(
                cell,
                hit=hit,
            )

            print(
                f"记录：{cell} -> "
                f"{'HIT' if hit else 'MISS'}"
            )

            for ship in newly_confirmed:
                print(
                    "确认潜艇："
                    f"长度={ship.length}，"
                    f"方向={ship.direction}，"
                    f"格子={ship.cells}"
                )
                print(
                    "已排除周围格子：",
                    sorted(ship.safety_area),
                )

            print(
                "剩余潜艇：",
                strategy.remaining_submarines,
            )
            print()
            break

    if strategy.done:
        print("当前固定关卡配置中的潜艇已经全部确认")

    print(
        "本次实际点击次数：",
        shot_count,
    )


if __name__ == "__main__":
    main()
