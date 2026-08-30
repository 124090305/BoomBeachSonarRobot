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
    SonarBoard,
    SonarStrategy,
)
from flows.level_loop import LevelState, create_level_state
from sonar_config import INITIAL_LEVEL


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
    current_level: int

    @classmethod
    def create(
        cls,
        *,
        serial: str = config.ADB_SERIAL,
        board: SonarBoard | None = None,
        strategy: SonarStrategy | None = None,
        current_level: int = INITIAL_LEVEL,
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

        if (board is None) != (strategy is None):
            raise ValueError("board 和 strategy 必须同时提供")

        if board is None:
            level_state = create_level_state(current_level)
            actual_board = level_state.board
            actual_strategy = level_state.strategy
        else:
            actual_board = board
            actual_strategy = strategy

        return cls(
            adb=adb,
            network=network,
            page=page,
            game=game,
            board=actual_board,
            strategy=actual_strategy,
            control_lock=threading.Lock(),
            current_level=int(current_level),
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
            current_level=self.current_level,
        )

    def with_level_state(self, state: LevelState) -> AppRuntimeContext:
        """沿用控制器和互斥锁，切换到新关卡的全新棋盘与策略。"""
        return AppRuntimeContext(
            adb=self.adb,
            network=self.network,
            page=self.page,
            game=self.game,
            board=state.board,
            strategy=state.strategy,
            control_lock=self.control_lock,
            current_level=state.level,
        )


__all__ = [
    "AppRuntimeContext",
]
