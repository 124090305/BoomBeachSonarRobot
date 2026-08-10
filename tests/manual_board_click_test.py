from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sonar_config import DEFAULT_LEVEL_CONFIG

from controllers.adb_controller import AdbController
from controllers.page_controller import PageController
from sonar import SonarBoard


TEST_CELLS = [
    (0, 0),
    (0, 9),
    (9, 0),
    (9, 9),
    (4, 4),
]


def main() -> None:
    if DEFAULT_LEVEL_CONFIG.board_quad is None:
        raise RuntimeError(
            "DEFAULT_LEVEL_CONFIG.board_quad 还没有填写"
        )

    # 连接模拟器
    adb = AdbController()
    adb.ensure_device_online()

    page = PageController(adb)

    # 建立程序棋盘
    board = SonarBoard(
        grid_size=DEFAULT_LEVEL_CONFIG.grid_size,
        submarines=DEFAULT_LEVEL_CONFIG.submarines,
    )

    # 根据四角生成 100 个点击中心
    board.set_screen_quad(
        DEFAULT_LEVEL_CONFIG.board_quad
    )

    print("棋盘坐标映射完成")
    print()

    for index, (row, col) in enumerate(
        TEST_CELLS,
        start=1,
    ):
        x, y = board.screen_point(
            row,
            col,
        )

        print(
            f"{index}. "
            f"逻辑格 ({row}, {col}) "
            f"→ 模拟器 ({x}, {y})"
        )

    print()
    print("q. 退出")

    while True:
        choice = input(
            "\n输入要测试的编号："
        ).strip().lower()

        if choice == "q":
            break

        try:
            index = int(choice) - 1
            row, col = TEST_CELLS[index]

        except (
            ValueError,
            IndexError,
        ):
            print("输入无效")
            continue

        x, y = board.screen_point(
            row,
            col,
        )

        confirm = input(
            f"准备点击逻辑格 ({row}, {col}) "
            f"→ ({x}, {y})，输入 y 确认："
        ).strip().lower()

        if confirm != "y":
            print("已取消")
            continue

        page.click_point(
            x,
            y,
        )

        print(
            f"已点击 ({row}, {col}) "
            f"→ ({x}, {y})"
        )


if __name__ == "__main__":
    main()