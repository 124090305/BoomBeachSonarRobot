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


class SonarStrategy(ABC):
    """
    声纳选格策略的统一接口。

    当前流程只依赖这几个接口：
    1. choose_next_cell()：拿下一格；
    2. report_result()：写入命中结果；
    3. reset()：新一轮时重置。

    后续增加概率云、蒙特卡洛时，只需要新增另一个策略类，
    外层 ADB / 页面 / 网络流程可以继续调用相同接口。
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
