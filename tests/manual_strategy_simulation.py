from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sonar_config import DEFAULT_LEVEL_CONFIG

from sonar import (
    CheckerboardHuntStrategy,
    SonarBoard,
)


# 固定隐藏布局，只用于验证策略流程。
# 这里没有连接模拟器，也不会真的点击游戏。
HIDDEN_SHIPS = (
    ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4)),
    ((3, 6), (3, 7), (3, 8), (3, 9)),
    ((5, 0), (6, 0), (7, 0)),
    ((9, 3), (9, 4)),
    ((6, 7), (7, 7)),
)


def main() -> None:
    board = SonarBoard(
        grid_size=DEFAULT_LEVEL_CONFIG.grid_size,
        submarines=DEFAULT_LEVEL_CONFIG.submarines,
    )

    strategy = CheckerboardHuntStrategy(
        board,
        hunt_parity=DEFAULT_LEVEL_CONFIG.hunt_parity,
        use_safety_rule=DEFAULT_LEVEL_CONFIG.use_safety_rule,
    )

    occupied = {
        cell
        for ship in HIDDEN_SHIPS
        for cell in ship
    }

    print("第一种棋盘颜色固定遍历表：")
    print(strategy.hunt_order)
    print()

    step = 0

    while not strategy.done:
        cell = strategy.choose_next_cell()

        if cell is None:
            print("没有可继续选择的格子，流程提前结束")
            break

        step += 1
        hit = cell in occupied

        newly_confirmed = strategy.report_result(
            cell,
            hit=hit,
        )

        print(
            f"{step:02d}. 探测 {cell} -> "
            f"{'HIT' if hit else 'MISS'}"
        )

        for ship in newly_confirmed:
            print(
                "    确认潜艇："
                f"长度={ship.length}，"
                f"方向={ship.direction}，"
                f"格子={ship.cells}"
            )

    print()
    print(
        "完成：",
        strategy.done,
    )
    print(
        "总探测次数：",
        step,
    )
    print(
        "已确认潜艇：",
        [
            ship.length
            for ship in strategy.get_confirmed_ships()
        ],
    )
    print(
        "排除格数量：",
        len(strategy.excluded_cells),
    )


if __name__ == "__main__":
    main()
