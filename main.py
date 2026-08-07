from __future__ import annotations

import argparse

import config

from controllers import (
    AdbController,
    GameController,
    NetworkController,
)

from flows import (
    run_screenshot_check,
)


NETWORK_ACTIONS = {
    "root-check",
    "uid",
    "weak-on",
    "weak-off",
    "reject-on",
    "reject-off",
    "network-status",
    "network-reset",
}


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
            "root-check",
            "uid",
            "weak-on",
            "weak-off",
            "reject-on",
            "reject-off",
            "network-status",
            "network-reset",
        ),
        default="screenshot",
        help="默认执行 screenshot",
    )

    return parser.parse_args()


def run_network_action(
    action: str,
    network: NetworkController,
) -> int:
    """执行单次网络控制命令。"""

    if action == "root-check":
        print(
            network.get_root_info()
        )

        return 0

    if action == "uid":
        _mode, uid = (
            network.ensure_ready()
        )

        print(
            f"游戏 UID：{uid}"
        )

        return 0

    if action == "weak-on":
        network.enable_weak_network()

        print(
            "弱网 DROP 已开启"
        )

        return 0

    if action == "weak-off":
        network.disable_weak_network()

        print(
            "弱网 DROP 已关闭"
        )

        return 0

    if action == "reject-on":
        network.enable_reject_network()

        print(
            "断网 REJECT 已开启"
        )

        return 0

    if action == "reject-off":
        network.disable_reject_network()

        print(
            "断网 REJECT 已关闭"
        )

        return 0

    if action == "network-status":
        state = network.get_state()

        print(
            state.to_text()
        )

        return 0

    if action == "network-reset":
        network.restore_network()

        print(
            "游戏网络已恢复"
        )

        return 0

    raise ValueError(
        f"未知网络操作：{action}"
    )


def main() -> int:
    args = parse_args()

    config.ensure_directories()

    if args.action == "gui":
        from ui.gui_app import (
            main as run_gui,
        )

        run_gui()

        return 0

    try:
        adb = AdbController()

        if args.action == "devices":
            devices = (
                adb.list_devices()
            )

            print(
                f"ADB 路径：{adb.adb_path}"
            )

            print(
                f"在线设备：{devices}"
            )

            return 0

        network = NetworkController(
            adb
        )

        if (
            args.action
            in NETWORK_ACTIONS
        ):
            return run_network_action(
                args.action,
                network,
            )

        if args.action == "restart":
            game = GameController(
                adb,
                network=network,
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