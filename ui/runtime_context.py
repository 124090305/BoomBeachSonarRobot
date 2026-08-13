from __future__ import annotations

import threading
from dataclasses import dataclass

import config

from controllers import (
    AdbController,
    GameController,
    NetworkController,
    PageController,
)
from sonar import (
    CheckerboardHuntStrategy,
    SonarBoard,
    SonarStrategy,
)
from sonar_config import DEFAULT_LEVEL_CONFIG


@dataclass(frozen=True)
class AppRuntimeContext:
    """GUI 一次运行所需的控制器、棋盘和策略集合。"""

    adb: AdbController
    network: NetworkController
    page: PageController
    game: GameController
    board: SonarBoard
    strategy: SonarStrategy
    control_lock: threading.Lock

    @classmethod
    def create(
        cls,
        *,
        serial: str = config.ADB_SERIAL,
        board: SonarBoard | None = None,
        strategy: SonarStrategy | None = None,
    ) -> AppRuntimeContext:
        """创建完整运行上下文；传入棋盘时可保留当前局状态。"""
        adb = AdbController(
            serial=serial
        )
        network = NetworkController(
            adb
        )
        page = PageController(
            adb
        )
        game = GameController(
            adb,
            network=network,
        )

        actual_board = board

        if actual_board is None:
            actual_board = SonarBoard(
                grid_size=DEFAULT_LEVEL_CONFIG.grid_size,
                submarines=DEFAULT_LEVEL_CONFIG.submarines,
            )
            if DEFAULT_LEVEL_CONFIG.board_quad is not None:
                actual_board.set_screen_quad(
                    DEFAULT_LEVEL_CONFIG.board_quad
                )

        actual_strategy = strategy

        if actual_strategy is None:
            actual_strategy = CheckerboardHuntStrategy(
                actual_board,
                hunt_parity=DEFAULT_LEVEL_CONFIG.hunt_parity,
                use_safety_rule=DEFAULT_LEVEL_CONFIG.use_safety_rule,
            )
            actual_strategy.choose_next_cell()

        return cls(
            adb=adb,
            network=network,
            page=page,
            game=game,
            board=actual_board,
            strategy=actual_strategy,
            control_lock=threading.Lock(),
        )

    def with_device(
        self,
        serial: str,
    ) -> AppRuntimeContext:
        """切换设备控制器，同时保留当前棋盘和策略状态。"""
        return self.create(
            serial=serial,
            board=self.board,
            strategy=self.strategy,
        )


__all__ = [
    "AppRuntimeContext",
]
