from __future__ import annotations

import argparse

import config
from controllers import (
    AdbController,
    GameController,
)
from flows import run_screenshot_check


def parse_args() -> argparse.Namespace:
    """读取命令行操作类型。"""
    parser = argparse.ArgumentParser(
        description="BoomBeachSonarRobot"
    )

    parser.add_argument(
        "action",
        nargs="?",
        choices=(
            "screenshot",
            "devices",
            "restart",
            "gui",
        ),
        default="screenshot",
        help="默认执行 screenshot",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config.ensure_directories()

    if args.action == "gui":
        from gui_app import main as run_gui

        run_gui()

        return 0

    try:
        adb = AdbController()

        if args.action == "devices":
            devices = adb.list_devices()

            print(
                f"ADB 路径：{adb.adb_path}"
            )

            print(
                f"在线设备：{devices}"
            )

            return 0

        if args.action == "restart":
            game = GameController(
                adb
            )

            game.restart_game()

            print(
                "游戏重启完成"
            )

            return 0

        result = run_screenshot_check(
            adb
        )

        print(
            "截图检查完成"
        )

        print(
            f"设备：{result.serial}"
        )

        print(
            f"尺寸：{result.width}x{result.height}"
        )

        print(
            f"文件：{result.path}"
        )

        return 0

    except Exception as exc:
        print(
            f"执行失败：{exc}"
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )