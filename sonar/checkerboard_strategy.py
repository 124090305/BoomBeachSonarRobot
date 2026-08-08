from __future__ import annotations

from collections import Counter, deque
from typing import FrozenSet, Iterable

from .board import (
    Cell,
    CellState,
    SonarBoard,
)
from .strategy import (
    ConfirmedShip,
    SonarStrategy,
)


class CheckerboardHuntStrategy(SonarStrategy):
    """
    第一版轻量声纳策略。

    Hunt：
    预先生成一种棋盘颜色的全部格子，按固定顺序遍历。

    Target：
    一旦出现未确认命中，暂时离开 Hunt，优先检查命中点周围。
    两个以上命中排成直线后，只继续探测直线两端。

    Sunk：
    当命中簇只剩一个合法完整潜艇解释时，确认潜艇，
    并把周围一圈加入 excluded_cells。
    """

    def __init__(
        self,
        board: SonarBoard,
        *,
        hunt_parity: int = 0,
        use_safety_rule: bool = True,
    ) -> None:
        super().__init__(board)

        if hunt_parity not in (0, 1):
            raise ValueError("hunt_parity 只能是 0 或 1")

        self.hunt_parity = int(hunt_parity)
        self.use_safety_rule = bool(use_safety_rule)

        self._initial_submarines = tuple(
            int(length)
            for length in self.board.submarines
        )

        self._primary_hunt_cells = self._build_hunt_cells(
            self.hunt_parity
        )

        # 正常情况下当前配置最短潜艇长度 >= 2，
        # 第一种颜色已经足够发现全部潜艇。
        # 第二种颜色只作为兜底，防止未来配置变化后完全卡死。
        self._fallback_hunt_cells = self._build_hunt_cells(
            1 - self.hunt_parity
        )

        self._remaining: Counter[int] = Counter()
        self._confirmed_ships: list[ConfirmedShip] = []
        self._blocked_cells: set[Cell] = set()
        self._pending_cell: Cell | None = None

        self._reset_reasoning_state()

    # =========================================================
    # 对外状态
    # =========================================================

    @property
    def done(self) -> bool:
        return sum(self._remaining.values()) == 0

    @property
    def pending_cell(self) -> Cell | None:
        return self._pending_cell

    @property
    def excluded_cells(self) -> FrozenSet[Cell]:
        return frozenset(self._blocked_cells)

    @property
    def mode(self) -> str:
        """给 UI 显示当前处于巡航、追击还是完成状态。"""
        if self.done:
            return "DONE"

        if self._get_hit_clusters():
            return "TARGET"

        return "HUNT"

    @property
    def hunt_order(self) -> tuple[Cell, ...]:
        """第一种棋盘颜色的固定遍历顺序。"""
        return self._primary_hunt_cells

    @property
    def remaining_submarines(self) -> tuple[int, ...]:
        """返回当前还没有确认的潜艇长度。"""
        result: list[int] = []

        for length in sorted(self._remaining):
            result.extend(
                [length] * self._remaining[length]
            )

        return tuple(result)

    def get_confirmed_ships(self) -> tuple[ConfirmedShip, ...]:
        return tuple(self._confirmed_ships)

    # =========================================================
    # 主接口
    # =========================================================

    def choose_next_cell(self) -> Cell | None:
        """
        给出下一格。

        优先级固定：
        等待中的格子 -> 命中追击 -> 棋盘颜色遍历 -> 兜底遍历。
        """
        if self._pending_cell is not None:
            return self._pending_cell

        self._try_confirm_ships()

        if self.done:
            return None

        target = self._choose_target_cell()

        if target is not None:
            return self._select(target)

        hunt = self._choose_hunt_cell()

        if hunt is not None:
            return self._select(hunt)

        return None

    def report_result(
        self,
        cell: Cell,
        hit: bool,
    ) -> tuple[ConfirmedShip, ...]:
        """
        写入真实 HIT / MISS。

        外层流程以后只需要：
        cell = strategy.choose_next_cell()
        hit = 实际探测(cell)
        strategy.report_result(cell, hit)
        """
        self._validate_cell(cell)

        if (
            self._pending_cell is not None
            and cell != self._pending_cell
        ):
            raise ValueError(
                "返回结果的格子和当前等待结果的格子不一致："
                f"pending={self._pending_cell}, result={cell}"
            )

        row, col = cell
        current_state = self.board.get_state(
            row,
            col,
        )

        expected_state = (
            CellState.HIT
            if hit
            else CellState.MISS
        )

        # 允许同一个结果重复上报，方便后续流程做重试。
        if current_state == expected_state:
            self._pending_cell = None
            return ()

        if current_state in (
            CellState.HIT,
            CellState.MISS,
            CellState.SUNK,
        ):
            raise ValueError(
                f"格子 {cell} 已经有确定结果：{current_state.value}"
            )

        self.board.report_result(
            row,
            col,
            hit=bool(hit),
        )

        self._pending_cell = None

        newly_confirmed = self._try_confirm_ships()

        return tuple(newly_confirmed)

    def reset(self) -> None:
        """清空本轮状态；坐标映射由 SonarBoard 保留。"""
        self.board.reset()
        self._reset_reasoning_state()

    # =========================================================
    # Hunt：固定棋盘颜色遍历
    # =========================================================

    def _build_hunt_cells(
        self,
        parity: int,
    ) -> tuple[Cell, ...]:
        """程序启动时一次性生成固定遍历表。"""
        return tuple(
            (row, col)
            for row in range(self.board.n)
            for col in range(self.board.n)
            if (row + col) % 2 == parity
        )

    def _choose_hunt_cell(self) -> Cell | None:
        # 第一阶段只遍历一种棋盘颜色。
        for cell in self._primary_hunt_cells:
            if self._is_selectable(cell):
                return cell

        # 理论兜底。
        for cell in self._fallback_hunt_cells:
            if self._is_selectable(cell):
                return cell

        return None

    # =========================================================
    # Target：命中以后追击
    # =========================================================

    def _choose_target_cell(self) -> Cell | None:
        clusters = self._get_hit_clusters()

        for cluster in clusters:
            ordered = sorted(cluster)

            if len(cluster) == 1:
                only = ordered[0]

                # 固定顺序：上、下、左、右。
                for cell in self._neighbors4(only):
                    if self._is_selectable(cell):
                        return cell

                continue

            rows = {
                row
                for row, _col in cluster
            }
            cols = {
                col
                for _row, col in cluster
            }

            if len(rows) == 1:
                row = next(iter(rows))
                min_col = min(
                    col
                    for _row, col in cluster
                )
                max_col = max(
                    col
                    for _row, col in cluster
                )

                for cell in (
                    (row, min_col - 1),
                    (row, max_col + 1),
                ):
                    if self._is_selectable(cell):
                        return cell

            elif len(cols) == 1:
                col = next(iter(cols))
                min_row = min(
                    row
                    for row, _col in cluster
                )
                max_row = max(
                    row
                    for row, _col in cluster
                )

                for cell in (
                    (min_row - 1, col),
                    (max_row + 1, col),
                ):
                    if self._is_selectable(cell):
                        return cell

            # 如果未来识别错误导致命中簇形状异常，
            # 仍然尝试它周围的未知格，避免策略直接停住。
            for hit_cell in ordered:
                for cell in self._neighbors4(hit_cell):
                    if self._is_selectable(cell):
                        return cell

        return None

    # =========================================================
    # Sunk：确认潜艇和排除周围格子
    # =========================================================

    def _try_confirm_ships(self) -> list[ConfirmedShip]:
        newly_confirmed: list[ConfirmedShip] = []
        changed = True

        while changed:
            changed = False

            for cluster in self._get_hit_clusters():
                candidates = (
                    self._candidate_placements_for_cluster(
                        cluster
                    )
                )

                if len(candidates) != 1:
                    continue

                length, direction, cells = candidates[0]

                if not all(
                    self.board.get_state(row, col)
                    == CellState.HIT
                    for row, col in cells
                ):
                    continue

                if self._remaining[length] <= 0:
                    continue

                safety_area = self._calc_safety_area(
                    cells
                )

                ship = ConfirmedShip(
                    length=length,
                    direction=direction,
                    cells=cells,
                    safety_area=frozenset(
                        safety_area
                    ),
                )

                self.board.mark_sunk(
                    cells
                )

                self._confirmed_ships.append(
                    ship
                )

                self._remaining[length] -= 1

                if self._remaining[length] == 0:
                    del self._remaining[length]

                if self.use_safety_rule:
                    self._blocked_cells.update(
                        safety_area
                    )

                newly_confirmed.append(
                    ship
                )

                changed = True
                break

        return newly_confirmed

    def _candidate_placements_for_cluster(
        self,
        cluster: set[Cell],
    ) -> list[tuple[int, str, tuple[Cell, ...]]]:
        result: list[
            tuple[int, str, tuple[Cell, ...]]
        ] = []

        cluster_cells = frozenset(
            cluster
        )

        for length, count in self._remaining.items():
            if count <= 0:
                continue

            for direction, cells in self._all_placements(
                length
            ):
                if cluster_cells.issubset(
                    frozenset(cells)
                ):
                    result.append(
                        (
                            length,
                            direction,
                            cells,
                        )
                    )

        return result

    def _all_placements(
        self,
        length: int,
    ) -> Iterable[tuple[str, tuple[Cell, ...]]]:
        invalid = self._invalid_for_ship_cells()

        for row in range(self.board.n):
            for col_start in range(
                self.board.n - length + 1
            ):
                cells = tuple(
                    (row, col)
                    for col in range(
                        col_start,
                        col_start + length,
                    )
                )

                if any(
                    cell in invalid
                    for cell in cells
                ):
                    continue

                yield "H", cells

        for col in range(self.board.n):
            for row_start in range(
                self.board.n - length + 1
            ):
                cells = tuple(
                    (row, col)
                    for row in range(
                        row_start,
                        row_start + length,
                    )
                )

                if any(
                    cell in invalid
                    for cell in cells
                ):
                    continue

                yield "V", cells

    def _invalid_for_ship_cells(self) -> set[Cell]:
        invalid = set(
            self._blocked_cells
        )

        snapshot = self.board.snapshot()

        for row in range(snapshot.n):
            for col in range(snapshot.n):
                if snapshot.states[row][col] in (
                    CellState.MISS,
                    CellState.SUNK,
                ):
                    invalid.add(
                        (row, col)
                    )

        return invalid

    def _calc_safety_area(
        self,
        cells: tuple[Cell, ...],
    ) -> set[Cell]:
        """潜艇外侧一圈；潜艇本身不放进排除集合。"""
        rows = [
            row
            for row, _col in cells
        ]
        cols = [
            col
            for _row, col in cells
        ]

        body = set(cells)
        result: set[Cell] = set()

        for row in range(
            min(rows) - 1,
            max(rows) + 2,
        ):
            for col in range(
                min(cols) - 1,
                max(cols) + 2,
            ):
                cell = (
                    row,
                    col,
                )

                if (
                    self._inside(cell)
                    and cell not in body
                ):
                    result.add(cell)

        return result

    # =========================================================
    # 棋盘辅助
    # =========================================================

    def _reset_reasoning_state(self) -> None:
        self._remaining = Counter(
            self._initial_submarines
        )
        self._confirmed_ships = []
        self._blocked_cells = set()
        self._pending_cell = None

    def _select(
        self,
        cell: Cell,
    ) -> Cell:
        row, col = cell

        self.board.select_cell(
            row,
            col,
        )

        self._pending_cell = cell

        return cell

    def _validate_cell(
        self,
        cell: Cell,
    ) -> None:
        if not self._inside(cell):
            raise ValueError(
                f"格子超出棋盘范围：{cell}"
            )

    def _inside(
        self,
        cell: Cell,
    ) -> bool:
        row, col = cell

        return (
            0 <= row < self.board.n
            and 0 <= col < self.board.n
        )

    def _is_selectable(
        self,
        cell: Cell,
    ) -> bool:
        if not self._inside(cell):
            return False

        if cell in self._blocked_cells:
            return False

        row, col = cell

        return (
            self.board.get_state(
                row,
                col,
            )
            == CellState.UNKNOWN
        )

    def _neighbors4(
        self,
        cell: Cell,
    ) -> Iterable[Cell]:
        row, col = cell

        # 固定顺序：上、下、左、右。
        for next_cell in (
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        ):
            if self._inside(next_cell):
                yield next_cell

    def _get_hit_clusters(self) -> list[set[Cell]]:
        snapshot = self.board.snapshot()
        hits = {
            (row, col)
            for row in range(snapshot.n)
            for col in range(snapshot.n)
            if snapshot.states[row][col]
            == CellState.HIT
        }

        visited: set[Cell] = set()
        clusters: list[set[Cell]] = []

        for start in sorted(hits):
            if start in visited:
                continue

            queue = deque([start])
            visited.add(start)
            cluster = {start}

            while queue:
                current = queue.popleft()

                for next_cell in self._neighbors4(
                    current
                ):
                    if (
                        next_cell in hits
                        and next_cell not in visited
                    ):
                        visited.add(next_cell)
                        cluster.add(next_cell)
                        queue.append(next_cell)

            clusters.append(cluster)

        clusters.sort(
            key=lambda item: (
                -len(item),
                min(item),
            )
        )

        return clusters
