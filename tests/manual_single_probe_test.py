from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


import config_test

from controllers import (
    AdbController,
    PageController,
)
from flows import (
    prepare_manual_probe_once,
    submit_manual_probe_result,
)
from sonar import (
    CheckerboardHuntStrategy,
    SonarBoard,
)


def read_manual_result() -> bool:
    """读取人工 HIT / MISS。"""
    while True:
        value = input(
            "人工判断结果：h=HIT，m=MISS："
        ).strip().lower()

        if value == "h":
            return True

        if value == "m":
            return False

        print(
            "输入无效，请输入 h 或 m"
        )


def main() -> None:
    if config_test.TEST_BOARD_QUAD is None:
        raise RuntimeError(
            "config_test.TEST_BOARD_QUAD "
            "还没有填写"
        )

    print(
        "单发真实探测人工联调"
    )
    print(
        "流程：策略选格 -> 点击前截图 -> "
        "点击目标格 -> 退出活动 -> 重进活动 -> "
        "人工判断 HIT/MISS -> 更新策略"
    )
    print()
    print(
        "运行前要求："
    )
    print(
        "1. 模拟器当前已经进入声纳活动详情，棋盘可见。"
    )
    print(
        "2. 如果你希望完全按参考项目的探测保护方式测试，"
        "请先自行开启弱网 DROP。"
    )
    print(
        "3. 本测试只执行一发，不处理 REJECT / retry。"
    )
    print()

    command = input(
        "准备好后按 Enter 开始，输入 q 退出："
    ).strip().lower()

    if command == "q":
        return

    adb = AdbController()
    adb.ensure_device_online()

    page = PageController(
        adb
    )

    board = SonarBoard(
        n=config_test.TEST_GRID_SIZE,
        submarines=config_test.TEST_SUBMARINES,
    )

    board.set_screen_quad(
        config_test.TEST_BOARD_QUAD
    )

    strategy = CheckerboardHuntStrategy(
        board,
        hunt_parity=(
            config_test.TEST_HUNT_PARITY
        ),
        use_safety_rule=(
            config_test.TEST_USE_SAFETY_RULE
        ),
    )

    context = prepare_manual_probe_once(
        adb=adb,
        page=page,
        board=board,
        strategy=strategy,
    )

    print()
    print(
        "实际页面操作已经完成。"
    )
    print(
        f"本次逻辑格：{context.cell}"
    )
    print(
        f"模拟器坐标：{context.screen_point}"
    )
    print(
        f"点击前截图：{context.before_path}"
    )
    print(
        f"重进后截图：{context.after_path}"
    )
    print()
    print(
        "现在观察模拟器中的目标格，"
        "人工判断这一发是 HIT 还是 MISS。"
    )

    hit = read_manual_result()

    result = submit_manual_probe_result(
        strategy,
        context,
        hit=hit,
    )

    print()
    print(
        "结果已经写回策略："
        f"{result.context.cell} -> "
        f"{'HIT' if result.hit else 'MISS'}"
    )

    if result.newly_confirmed:
        for ship in result.newly_confirmed:
            print(
                "新确认潜艇："
                f"长度={ship.length}，"
                f"方向={ship.direction}，"
                f"格子={ship.cells}"
            )

    next_cell = (
        strategy.choose_next_cell()
    )

    print(
        f"策略给出的下一格：{next_cell}"
    )
    print(
        "本次单发测试结束，"
        "不会继续实际点击下一格。"
    )


if __name__ == "__main__":
    main()
