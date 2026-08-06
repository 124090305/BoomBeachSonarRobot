from __future__ import annotations

from pathlib import Path

import config
from controllers.adb_controller import AdbController


class GameController:
    """把多个 ADB 基础动作组合成完整游戏操作。"""

    def __init__(
        self,
        adb: AdbController,
        package_name: str = config.GAME_PACKAGE_NAME,
    ) -> None:
        self.adb = adb
        self.package_name = package_name.strip()

        if not self.package_name:
            raise ValueError(
                "游戏包名不能为空"
            )

    def ensure_game_installed(self) -> None:
        """确认当前设备已经安装游戏。"""
        installed = self.adb.is_package_installed(
            self.package_name
        )

        if not installed:
            raise RuntimeError(
                f"设备中没有找到游戏包 {self.package_name}。"
                "请确认 config.py 中的 GAME_PACKAGE_NAME。"
            )

    def restart_game(
        self,
        wait_seconds: float = config.GAME_RESTART_DELAY,
    ) -> None:
        """
        强制关闭游戏，再重新启动。

        当前阶段只处理应用重启，
        暂时不加入弱网和断网清理。
        """
        self.adb.ensure_device_online()
        self.ensure_game_installed()

        self.adb.close_app(
            self.package_name
        )

        self.adb.delay(1.0)

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