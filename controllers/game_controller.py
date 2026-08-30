from __future__ import annotations

from pathlib import Path
from threading import Event

import config
from controllers.adb_controller import (
    AdbController,
)
from controllers.network_controller import (
    NetworkController,
)
from logger import get_logger
from stop_control import interruptible_wait, raise_if_stop_requested


logger = get_logger(__name__)


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

        logger.debug(
            "游戏安装检查通过：%s",
            self.package_name,
        )

    def restart_game(
        self,
        wait_seconds: float = config.GAME_RESTART_DELAY,
        *,
        stop_event: Event | None = None,
    ) -> None:
        """关闭游戏、恢复网络，然后重新启动游戏。"""
        raise_if_stop_requested(stop_event)
        logger.info(
            "开始重启游戏：%s",
            self.package_name,
        )

        self.adb.ensure_device_online()
        self.ensure_game_installed()

        # 1. 关闭游戏
        self.adb.close_app(
            self.package_name
        )

        self.adb.delay(
            1.0
        )

        # 2. 恢复网络
        if self.network is not None:
            self.network.restore_network()

        # 3. 启动游戏
        self.adb.open_app(
            self.package_name
        )

        # 4. 游戏已经重新拉起，后续加载等待允许响应停止。
        interruptible_wait(wait_seconds, stop_event)

        logger.info(
            "游戏重启完成，已等待 %.1f 秒",
            wait_seconds,
        )

    def take_screenshot(
        self,
        output_path: str | Path | None = None,
    ) -> Path:
        """获取当前游戏截图。"""
        logger.debug(
            "获取游戏截图"
        )

        return self.adb.take_screenshot(
            output_path
        )
