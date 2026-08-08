from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import FrozenSet

from .board import Cell, SonarBoard


@dataclass(frozen=True)
class ConfirmedShip:
    """策略已经确认的一艘完整潜艇。"""

    length: int
    direction: str
    cells: tuple[Cell, ...]
    safety_area: FrozenSet[Cell]


@dataclass(frozen=True)
class StrategySnapshot:
    """
    给 UI 读取的一份策略状态快照。

    当前轻量策略只会使用前几个字段。
    calculation_progress / calculation_status 先作为以后概率云、
    蒙特卡洛、有限探寻等耗时策略的统一预留接口。
    """

    mode: str
    pending_cell: Cell | None
    excluded_cells: FrozenSet[Cell]
    remaining_submarines: tuple[int, ...]
    confirmed_ships: tuple[ConfirmedShip, ...]
    calculation_progress: float | None = None
    calculation_status: str = ""


class SonarStrategy(ABC):
    """
    声纳选格策略的统一接口。

    当前流程只依赖这几个接口：
    1. choose_next_cell()：拿下一格；
    2. report_result()：写入命中结果；
    3. reset()：新一轮时重置；
    4. snapshot()：给 UI 读取策略状态。

    后续增加概率云、蒙特卡洛时，只需要新增另一个策略类，
    外层 ADB / 页面 / 网络流程和棋盘 UI 可以继续使用相同接口。
    """

    def __init__(
        self,
        board: SonarBoard,
    ) -> None:
        self.board = board

    @property
    @abstractmethod
    def done(self) -> bool:
        """当前配置中的潜艇是否已经全部确认。"""

    @property
    @abstractmethod
    def pending_cell(self) -> Cell | None:
        """已经选出、正在等待真实探测结果的格子。"""

    @property
    @abstractmethod
    def excluded_cells(self) -> FrozenSet[Cell]:
        """策略已经排除、后续不再选择的格子。"""

    @property
    def mode(self) -> str:
        """给 UI 显示的当前策略模式。"""
        if self.done:
            return "DONE"

        return "HUNT"

    @property
    def remaining_submarines(self) -> tuple[int, ...]:
        """
        给 UI 显示的剩余潜艇长度。

        具体策略如果会跟踪剩余潜艇，应覆盖这个属性。
        """
        return ()

    def get_confirmed_ships(self) -> tuple[ConfirmedShip, ...]:
        """
        给 UI 显示的已确认潜艇。

        具体策略如果会确认潜艇，应覆盖这个方法。
        """
        return ()

    @property
    def calculation_progress(self) -> float | None:
        """
        复杂策略计算进度，范围 0.0 ~ 1.0。

        当前轻量策略没有耗时计算，所以返回 None。
        """
        return None

    @property
    def calculation_status(self) -> str:
        """复杂策略计算阶段文字；当前轻量策略为空。"""
        return ""

    def snapshot(self) -> StrategySnapshot:
        """生成一份稳定的 UI 状态快照。"""
        return StrategySnapshot(
            mode=self.mode,
            pending_cell=self.pending_cell,
            excluded_cells=self.excluded_cells,
            remaining_submarines=self.remaining_submarines,
            confirmed_ships=self.get_confirmed_ships(),
            calculation_progress=self.calculation_progress,
            calculation_status=self.calculation_status,
        )

    @abstractmethod
    def choose_next_cell(self) -> Cell | None:
        """选择下一次要探测的逻辑格子。"""

    @abstractmethod
    def report_result(
        self,
        cell: Cell,
        hit: bool,
    ) -> tuple[ConfirmedShip, ...]:
        """写入一次真实探测结果，并返回本次新确认的潜艇。"""

    @abstractmethod
    def reset(self) -> None:
        """开始新一轮关卡。"""
