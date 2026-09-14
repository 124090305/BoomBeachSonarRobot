from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Iterable

import cv2
import numpy as np


Cell = tuple[int, int]
Point = tuple[int, int]
Quad = tuple[Point, Point, Point, Point]


class CellState(str, Enum):
    """程序内部记录的单格状态。"""

    UNKNOWN = "unknown"
    SELECTED = "selected"
    MISS = "miss"
    HIT = "hit"
    SUNK = "sunk"


@dataclass(frozen=True)
class BoardSnapshot:
    """给 GUI 读取的一份棋盘快照。"""

    revision: int
    grid_size: int
    submarines: tuple[int, ...]
    states: tuple[tuple[CellState, ...], ...]
    screen_points: tuple[tuple[Point | None, ...], ...]

    @property
    def mapped_count(self) -> int:
        return sum(
            point is not None
            for row in self.screen_points
            for point in row
        )


class SonarBoard:
    """
    声纳逻辑棋盘。

    负责三件事：
    1. 保存每个逻辑格子的状态；
    2. 保存逻辑格子和模拟器点击坐标的对应关系；
    3. 给 GUI 提供统一的数据快照。
    """

    def __init__(
        self,
        grid_size: int,
        submarines: Iterable[int],
    ) -> None:
        if grid_size <= 0:
            raise ValueError("棋盘尺寸 grid_size 必须大于 0")

        submarine_tuple = tuple(int(length) for length in submarines)

        if not submarine_tuple:
            raise ValueError("潜艇配置不能为空")

        if any(length <= 0 for length in submarine_tuple):
            raise ValueError("潜艇长度必须大于 0")

        if any(length > grid_size for length in submarine_tuple):
            raise ValueError("潜艇长度不能大于棋盘尺寸")

        self.grid_size = int(grid_size)
        self.submarines = submarine_tuple
        # 正式关卡工厂装配定位器；纯逻辑/离线棋盘不连接设备。
        self.runtime_locator = None

        self._lock = RLock()
        self._revision = 0

        self._states: list[list[CellState]] = [
            [CellState.UNKNOWN for _ in range(self.grid_size)]
            for _ in range(self.grid_size)
        ]

        self._screen_points: list[list[Point | None]] = [
            [None for _ in range(self.grid_size)]
            for _ in range(self.grid_size)
        ]

    # =========================================================
    # 基础检查
    # =========================================================

    def _validate_cell(
        self,
        row: int,
        col: int,
    ) -> None:
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            raise IndexError(
                f"格子超出棋盘范围：row={row}, col={col}, grid_size={self.grid_size}"
            )

    def _touch(self) -> None:
        self._revision += 1

    # =========================================================
    # 棋盘状态
    # =========================================================

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def get_state(
        self,
        row: int,
        col: int,
    ) -> CellState:
        self._validate_cell(row, col)

        with self._lock:
            return self._states[row][col]

    def set_state(
        self,
        row: int,
        col: int,
        state: CellState,
    ) -> None:
        self._validate_cell(row, col)

        if not isinstance(state, CellState):
            state = CellState(state)

        with self._lock:
            if self._states[row][col] == state:
                return

            self._states[row][col] = state
            self._touch()

    def select_cell(
        self,
        row: int,
        col: int,
    ) -> None:
        """
        标记当前准备探测的格子。

        旧的 SELECTED 会恢复为 UNKNOWN，
        方便 GUI 始终只突出显示当前选择。
        """
        self._validate_cell(row, col)

        with self._lock:
            changed = False

            for existing_row in range(self.grid_size):
                for existing_col in range(self.grid_size):
                    if (
                        self._states[existing_row][existing_col]
                        == CellState.SELECTED
                    ):
                        self._states[existing_row][existing_col] = (
                            CellState.UNKNOWN
                        )
                        changed = True

            if self._states[row][col] != CellState.SELECTED:
                self._states[row][col] = CellState.SELECTED
                changed = True

            if changed:
                self._touch()

    def report_result(
        self,
        row: int,
        col: int,
        hit: bool,
    ) -> None:
        """写入一次探测结果。"""
        self.set_state(
            row,
            col,
            CellState.HIT if hit else CellState.MISS,
        )

    def mark_sunk(
        self,
        cells: Iterable[Cell],
    ) -> None:
        """把已经确认属于完整潜艇的格子标记出来。"""
        cell_list = list(cells)

        for row, col in cell_list:
            self._validate_cell(row, col)

        with self._lock:
            changed = False

            for row, col in cell_list:
                if self._states[row][col] != CellState.SUNK:
                    self._states[row][col] = CellState.SUNK
                    changed = True

            if changed:
                self._touch()

    def reset(self) -> None:
        """清空棋盘探测状态，保留模拟器坐标映射。"""
        with self._lock:
            changed = False

            for row in range(self.grid_size):
                for col in range(self.grid_size):
                    if self._states[row][col] != CellState.UNKNOWN:
                        self._states[row][col] = CellState.UNKNOWN
                        changed = True

            if changed:
                self._touch()

    def replace_states(
        self,
        states: Iterable[Iterable[CellState]],
    ) -> None:
        """一次性替换整张棋盘状态，保留模拟器坐标映射。"""
        normalized = tuple(
            tuple(
                state if isinstance(state, CellState) else CellState(state)
                for state in row
            )
            for row in states
        )

        if len(normalized) != self.grid_size or any(
            len(row) != self.grid_size
            for row in normalized
        ):
            raise ValueError(
                "整盘状态尺寸错误："
                f"需要 {self.grid_size}×{self.grid_size}"
            )

        with self._lock:
            current = tuple(tuple(row) for row in self._states)
            if current == normalized:
                return
            self._states = [list(row) for row in normalized]
            self._touch()

    # =========================================================
    # 逻辑格子 <-> 模拟器坐标
    # =========================================================

    def set_screen_points(
        self,
        points: Iterable[Point],
    ) -> None:
        """
        直接写入全部格子的模拟器点击中心。

        points 使用逐行顺序：
        (0,0), (0,1), ... (0,grid_size-1),
        (1,0), ...
        """
        point_list = [
            (int(x), int(y))
            for x, y in points
        ]

        expected = self.grid_size * self.grid_size

        if len(point_list) != expected:
            raise ValueError(
                f"格点数量错误：需要 {expected} 个，实际 {len(point_list)} 个"
            )

        with self._lock:
            index = 0

            for row in range(self.grid_size):
                for col in range(self.grid_size):
                    self._screen_points[row][col] = point_list[index]
                    index += 1

            self._touch()

    def set_screen_quad(
        self,
        quad: Quad,
    ) -> None:
        """
        根据模拟器棋盘四个外角，自动生成 grid_size×grid_size 个格子中心。

        quad 顺序固定：
        上 -> 右 -> 下 -> 左

        逻辑棋盘中的每个格子中心通过透视变换映射到模拟器画面。
        """
        if len(quad) != 4:
            raise ValueError("quad 必须包含 4 个外角坐标")

        destination = np.array(
            quad,
            dtype=np.float32,
        )

        source = np.array(
            [
                [0.0, 0.0],
                [float(self.grid_size), 0.0],
                [float(self.grid_size), float(self.grid_size)],
                [0.0, float(self.grid_size)],
            ],
            dtype=np.float32,
        )

        matrix = cv2.getPerspectiveTransform(
            source,
            destination,
        )

        logical_centers = np.array(
            [
                [
                    [col + 0.5, row + 0.5]
                    for row in range(self.grid_size)
                    for col in range(self.grid_size)
                ]
            ],
            dtype=np.float32,
        )

        mapped = cv2.perspectiveTransform(
            logical_centers,
            matrix,
        )[0]

        points = [
            (int(round(x)), int(round(y)))
            for x, y in mapped
        ]

        self.set_screen_points(points)

    def clear_screen_mapping(self) -> None:
        with self._lock:
            has_mapping = any(
                point is not None
                for row in self._screen_points
                for point in row
            )

            if not has_mapping:
                return

            for row in range(self.grid_size):
                for col in range(self.grid_size):
                    self._screen_points[row][col] = None

            self._touch()

    def screen_point(
        self,
        row: int,
        col: int,
    ) -> Point:
        self._validate_cell(row, col)

        with self._lock:
            point = self._screen_points[row][col]

        if point is None:
            raise RuntimeError(
                f"格子 ({row}, {col}) 还没有绑定模拟器坐标"
            )

        return point

    @property
    def has_complete_mapping(self) -> bool:
        with self._lock:
            return all(
                point is not None
                for row in self._screen_points
                for point in row
            )

    # =========================================================
    # 行列与一维编号
    # =========================================================

    def index_of(
        self,
        row: int,
        col: int,
    ) -> int:
        self._validate_cell(row, col)
        return row * self.grid_size + col

    def cell_from_index(
        self,
        index: int,
    ) -> Cell:
        if not (0 <= index < self.grid_size * self.grid_size):
            raise IndexError(
                f"格子编号超出范围：index={index}"
            )

        return divmod(index, self.grid_size)

    # =========================================================
    # GUI 快照
    # =========================================================

    def snapshot(self) -> BoardSnapshot:
        with self._lock:
            states = tuple(
                tuple(row)
                for row in self._states
            )

            screen_points = tuple(
                tuple(row)
                for row in self._screen_points
            )

            return BoardSnapshot(
                revision=self._revision,
                grid_size=self.grid_size,
                submarines=self.submarines,
                states=states,
                screen_points=screen_points,
            )
