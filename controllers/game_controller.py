from __future__ import annotations

from pathlib import Path

import config
from controllers.adb_controller import (
    AdbController,
)
from controllers.network_controller import (
    NetworkController,
)


class GameController:
    """把多个 ADB 动作组合成游戏操作。"""

    def __init__(
        self,
        adb: AdbController,
        package_name: str = config.GAME_PACKAGE_NAME,
        network: NetworkController | None = None,
    ) -> None:
        self.adb = adb

        self.package_name = (
            package_name.strip()
        )

        self.network = network

        if not self.package_name:
            raise ValueError(
                "游戏包名不能为空"
            )

    def ensure_game_installed(
        self,
    ) -> None:
        """确认游戏已经安装。"""
        installed = (
            self.adb.is_package_installed(
                self.package_name
            )
        )

        if not installed:
            raise RuntimeError(
                "设备中没有找到游戏包 "
                f"{self.package_name}。"
                "请确认 config.py 中的 GAME_PACKAGE_NAME。"
            )

    def restart_game(
        self,
        wait_seconds: float = config.GAME_RESTART_DELAY,
    ) -> None:
        """恢复网络后重启游戏。"""
        self.adb.ensure_device_online()

        self.ensure_game_installed()

        if self.network is not None:
            self.network.restore_network()

        self.adb.close_app(
            self.package_name
        )

        self.adb.delay(
            1.0
        )

        self.adb.open_app(
            self.package_name
        )

        self.adb.delay(
            wait_seconds
        )

    def take_screenshot(
        self,
        output_path: str | Path | None = None,
    ) -> Path:
        """获取当前游戏截图。"""
        return self.adb.take_screenshot(
            output_path
        )