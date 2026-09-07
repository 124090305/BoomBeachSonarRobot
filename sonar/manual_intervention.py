from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Iterable, Protocol

from .board import BoardSnapshot, Cell, CellState, SonarBoard
from .strategy import ConfirmedShip, StrategySnapshot


class ManualEditError(ValueError):
    """人工编辑操作不允许执行。"""


@dataclass(frozen=True)
class _EditState:
    states: tuple[tuple[CellState, ...], ...]
    confirmed_ships: tuple[ConfirmedShip, ...]
    review_cells: frozenset[Cell]
    recognition_confidences: tuple[tuple[float | None, ...], ...]
    recognition_reasons: tuple[tuple[str, ...], ...]
    recognition_summary: str | None


@dataclass(frozen=True)
class ManualApplyResult:
    """一次人工修改正式应用后的内存状态。"""

    next_cell: Cell | None
    board_snapshot: BoardSnapshot
    strategy_snapshot: StrategySnapshot


class RebuildableStrategy(Protocol):
    use_safety_rule: bool

    def snapshot(self) -> StrategySnapshot:
        ...

    def rebuild_from_board(
        self,
        confirmed_ships: Iterable[ConfirmedShip],
    ) -> StrategySnapshot:
        ...

    def restore_from_snapshot(self, snapshot: StrategySnapshot) -> None:
        ...

    def choose_next_cell(self) -> Cell | None:
        ...


class ManualEditSession:
    """与正式棋盘和策略隔离的人工编辑缓存及历史。"""

    def __init__(
        self,
        board: SonarBoard,
        confirmed_ships: Iterable[ConfirmedShip] = (),
    ) -> None:
        snapshot = board.snapshot()
        self.grid_size = snapshot.grid_size
        self.submarines = snapshot.submarines
        self.screen_points = snapshot.screen_points
        states = self._normalize_states(snapshot)
        ships = tuple(confirmed_ships) or self._ships_from_sunk_cells(states)
        empty_confidence = tuple(
            tuple(None for _col in range(self.grid_size))
            for _row in range(self.grid_size)
        )
        empty_reasons = tuple(
            tuple("" for _col in range(self.grid_size))
            for _row in range(self.grid_size)
        )
        self._initial = _EditState(
            states,
            ships,
            frozenset(),
            empty_confidence,
            empty_reasons,
            None,
        )
        self._current = self._initial
        self._undo: list[_EditState] = []
        self._redo: list[_EditState] = []
        self._revision = 0

    @staticmethod
    def _normalize_states(snapshot: BoardSnapshot):
        return tuple(
            tuple(
                CellState.UNKNOWN if state == CellState.SELECTED else state
                for state in row
            )
            for row in snapshot.states
        )

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def states(self) -> tuple[tuple[CellState, ...], ...]:
        return self._current.states

    @property
    def confirmed_ships(self) -> tuple[ConfirmedShip, ...]:
        return self._current.confirmed_ships

    @property
    def review_cells(self) -> frozenset[Cell]:
        return self._current.review_cells

    @property
    def recognition_summary(self) -> str | None:
        return self._current.recognition_summary

    def recognition_confidence_at(self, cell: Cell) -> float | None:
        row, col = self._validate_cell(cell)
        return self._current.recognition_confidences[row][col]

    def recognition_reason_at(self, cell: Cell) -> str:
        row, col = self._validate_cell(cell)
        return self._current.recognition_reasons[row][col]

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def changed_cells(self) -> frozenset[Cell]:
        return frozenset(
            (row, col)
            for row in range(self.grid_size)
            for col in range(self.grid_size)
            if self.states[row][col] != self._initial.states[row][col]
        )

    @property
    def pending_confirmed_cells(self) -> frozenset[Cell]:
        original = {ship.cells for ship in self._initial.confirmed_ships}
        return frozenset(
            cell
            for ship in self.confirmed_ships
            if ship.cells not in original
            for cell in ship.cells
        )

    @property
    def pending_cancelled_cells(self) -> frozenset[Cell]:
        current = {ship.cells for ship in self.confirmed_ships}
        return frozenset(
            cell
            for ship in self._initial.confirmed_ships
            if ship.cells not in current
            for cell in ship.cells
        )

    def state_at(self, cell: Cell) -> CellState:
        row, col = self._validate_cell(cell)
        return self.states[row][col]

    def cycle_cell(self, cell: Cell) -> CellState:
        row, col = self._validate_cell(cell)
        current = self.states[row][col]
        if current == CellState.SUNK:
            raise ManualEditError("请先长按取消整艘潜艇确认")
        next_state = {
            CellState.UNKNOWN: CellState.HIT,
            CellState.SELECTED: CellState.HIT,
            CellState.HIT: CellState.MISS,
            CellState.MISS: CellState.UNKNOWN,
        }[current]
        review, confidences, reasons = self._without_recognition_review((cell,))
        self._commit(
            self._replace_cells(self.states, (cell,), next_state),
            self.confirmed_ships,
            review_cells=review,
            recognition_confidences=confidences,
            recognition_reasons=reasons,
        )
        return next_state

    def validate_ship_candidate(self, cells: Iterable[Cell]) -> tuple[Cell, ...]:
        ordered = self._ordered_straight_cells(cells)
        if len(ordered) not in self.submarines:
            raise ManualEditError("候选长度不符合当前关卡潜艇配置")
        if any(self.state_at(cell) != CellState.HIT for cell in ordered):
            raise ManualEditError("候选潜艇必须全部由连续 HIT 格组成")
        available = Counter(self.submarines)
        existing = Counter(ship.length for ship in self.confirmed_ships)
        if existing[len(ordered)] >= available[len(ordered)]:
            raise ManualEditError("该长度潜艇的可确认数量已经用完")
        return ordered

    def confirm_ship(self, cells: Iterable[Cell]) -> ConfirmedShip:
        ordered = self.validate_ship_candidate(cells)
        direction = "H" if len({row for row, _col in ordered}) == 1 else "V"
        ship = ConfirmedShip(
            length=len(ordered),
            direction=direction,
            cells=ordered,
            safety_area=frozenset(),
        )
        review, confidences, reasons = self._without_recognition_review(ordered)
        self._commit(
            self._replace_cells(self.states, ordered, CellState.SUNK),
            self.confirmed_ships + (ship,),
            review_cells=review,
            recognition_confidences=confidences,
            recognition_reasons=reasons,
        )
        return ship

    def cancel_ship_at(self, cell: Cell) -> ConfirmedShip:
        self._validate_cell(cell)
        ship = next(
            (item for item in self.confirmed_ships if cell in item.cells),
            None,
        )
        if ship is None:
            raise ManualEditError("该 SUNK 格没有对应的完整潜艇记录")
        review, confidences, reasons = self._without_recognition_review(ship.cells)
        self._commit(
            self._replace_cells(self.states, ship.cells, CellState.HIT),
            tuple(item for item in self.confirmed_ships if item != ship),
            review_cells=review,
            recognition_confidences=confidences,
            recognition_reasons=reasons,
        )
        return ship

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self._current)
        self._current = self._undo.pop()
        self._revision += 1
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self._current)
        self._current = self._redo.pop()
        self._revision += 1
        return True

    def discard_changes(self) -> None:
        self._current = self._initial
        self._undo.clear()
        self._redo.clear()
        self._revision += 1

    def apply_recognition_preview(
        self,
        states: Iterable[Iterable[CellState]],
        confirmed_ships: Iterable[ConfirmedShip],
        *,
        review_cells: Iterable[Cell] = (),
        confidences: Iterable[Iterable[float | None]] | None = None,
        reasons: Iterable[Iterable[str]] | None = None,
        summary: str | None = None,
    ) -> None:
        """把一次整盘识别作为一条独立人工历史写入临时缓存。"""
        normalized_states = tuple(
            tuple(CellState(value) for value in row)
            for row in states
        )
        if len(normalized_states) != self.grid_size or any(
            len(row) != self.grid_size for row in normalized_states
        ):
            raise ManualEditError("识别棋盘尺寸与人工编辑棋盘不一致")
        if any(state == CellState.SELECTED for row in normalized_states for state in row):
            raise ManualEditError("全局识别结果不能包含 SELECTED")
        normalized_ships = tuple(confirmed_ships)
        normalized_review = frozenset(self._validate_cell(cell) for cell in review_cells)
        if confidences is None:
            normalized_confidences = tuple(
                tuple(None for _col in range(self.grid_size))
                for _row in range(self.grid_size)
            )
        else:
            normalized_confidences = tuple(tuple(value for value in row) for row in confidences)
        if reasons is None:
            normalized_reasons = tuple(
                tuple("" for _col in range(self.grid_size))
                for _row in range(self.grid_size)
            )
        else:
            normalized_reasons = tuple(tuple(str(value) for value in row) for row in reasons)
        for matrix, name in (
            (normalized_confidences, "置信度"),
            (normalized_reasons, "原因"),
        ):
            if len(matrix) != self.grid_size or any(len(row) != self.grid_size for row in matrix):
                raise ManualEditError(f"识别{name}矩阵尺寸不一致")
        next_state = _EditState(
            normalized_states,
            normalized_ships,
            normalized_review,
            normalized_confidences,
            normalized_reasons,
            str(summary) if summary else None,
        )
        self._commit_state(next_state, force=True)

    def validate_for_apply(self, *, use_safety_rule: bool) -> None:
        """在写入正式状态前校验当前完整人工结果。"""
        available = Counter(self.submarines)
        used: Counter[int] = Counter()
        occupied: set[Cell] = set()
        normalized_ships: list[tuple[Cell, ...]] = []

        for index, ship in enumerate(self.confirmed_ships, start=1):
            try:
                cells = self._ordered_straight_cells(ship.cells)
            except ManualEditError as exc:
                raise ManualEditError(f"第 {index} 艘潜艇：{exc}") from exc
            length = len(cells)
            if available[length] <= 0:
                raise ManualEditError(f"长度 {length} 不属于当前潜艇配置")
            used[length] += 1
            if used[length] > available[length]:
                raise ManualEditError(f"长度 {length} 的潜艇数量超过关卡配置")
            overlap = occupied.intersection(cells)
            if overlap:
                raise ManualEditError(f"已确认潜艇发生重叠：{sorted(overlap)}")
            for cell in cells:
                state = self.state_at(cell)
                if state == CellState.MISS:
                    raise ManualEditError(f"已确认潜艇内部包含 MISS：{cell}")
                if state != CellState.SUNK:
                    raise ManualEditError(
                        f"已确认潜艇与棋盘状态冲突：{cell}={state.value}"
                    )
            occupied.update(cells)
            normalized_ships.append(cells)

        sunk_cells = {
            (row, col)
            for row in range(self.grid_size)
            for col in range(self.grid_size)
            if self.states[row][col] == CellState.SUNK
        }
        if sunk_cells != occupied:
            raise ManualEditError("SUNK 格与已确认潜艇记录不一致")

        if use_safety_rule:
            for index, cells in enumerate(normalized_ships, start=1):
                safety = self._calc_safety_area(cells)
                ship_conflicts = safety.intersection(occupied)
                if ship_conflicts:
                    raise ManualEditError(
                        f"第 {index} 艘潜艇违反安全间距："
                        f"{sorted(ship_conflicts)}"
                    )
                hit_conflicts = {
                    cell
                    for cell in safety
                    if self.state_at(cell) == CellState.HIT
                }
                if hit_conflicts:
                    raise ManualEditError(
                        f"第 {index} 艘潜艇安全区域存在 HIT："
                        f"{sorted(hit_conflicts)}"
                    )

    def _commit(
        self,
        states,
        ships: tuple[ConfirmedShip, ...],
        *,
        review_cells=None,
        recognition_confidences=None,
        recognition_reasons=None,
    ) -> None:
        next_state = _EditState(
            states,
            ships,
            self.review_cells if review_cells is None else frozenset(review_cells),
            self._current.recognition_confidences if recognition_confidences is None else recognition_confidences,
            self._current.recognition_reasons if recognition_reasons is None else recognition_reasons,
            self.recognition_summary,
        )
        self._commit_state(next_state)

    def _commit_state(self, next_state: _EditState, *, force: bool = False) -> None:
        if next_state == self._current and not force:
            return
        self._undo.append(self._current)
        self._current = next_state
        self._redo.clear()
        self._revision += 1

    def _without_recognition_review(self, cells: Iterable[Cell]):
        targets = {self._validate_cell(cell) for cell in cells}
        review = self.review_cells.difference(targets)
        confidences = [list(row) for row in self._current.recognition_confidences]
        reasons = [list(row) for row in self._current.recognition_reasons]
        for row, col in targets:
            confidences[row][col] = None
            reasons[row][col] = ""
        return review, tuple(tuple(row) for row in confidences), tuple(tuple(row) for row in reasons)

    @staticmethod
    def _replace_cells(states, cells: Iterable[Cell], state: CellState):
        mutable = [list(row) for row in states]
        for row, col in cells:
            mutable[row][col] = state
        return tuple(tuple(row) for row in mutable)

    def _ordered_straight_cells(self, cells: Iterable[Cell]) -> tuple[Cell, ...]:
        raw = tuple(self._validate_cell(cell) for cell in cells)
        if not raw or len(set(raw)) != len(raw):
            raise ManualEditError("候选潜艇格为空或重复")
        rows = {row for row, _col in raw}
        cols = {col for _row, col in raw}
        if len(rows) == 1:
            ordered = tuple(sorted(raw, key=lambda item: item[1]))
            values = [col for _row, col in ordered]
        elif len(cols) == 1:
            ordered = tuple(sorted(raw, key=lambda item: item[0]))
            values = [row for row, _col in ordered]
        else:
            raise ManualEditError("候选潜艇只能横向或纵向")
        if values != list(range(values[0], values[0] + len(values))):
            raise ManualEditError("候选潜艇格必须连续")
        return ordered

    def _validate_cell(self, cell: Cell) -> Cell:
        row, col = int(cell[0]), int(cell[1])
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            raise ManualEditError(f"格子超出棋盘范围：{cell}")
        return row, col

    def _calc_safety_area(self, cells: tuple[Cell, ...]) -> set[Cell]:
        rows = [row for row, _col in cells]
        cols = [col for _row, col in cells]
        body = set(cells)
        return {
            (row, col)
            for row in range(min(rows) - 1, max(rows) + 2)
            for col in range(min(cols) - 1, max(cols) + 2)
            if 0 <= row < self.grid_size
            and 0 <= col < self.grid_size
            and (row, col) not in body
        }

    def _ships_from_sunk_cells(self, states) -> tuple[ConfirmedShip, ...]:
        remaining = {
            (row, col)
            for row in range(self.grid_size)
            for col in range(self.grid_size)
            if states[row][col] == CellState.SUNK
        }
        result: list[ConfirmedShip] = []
        while remaining:
            start = min(remaining)
            queue = deque([start])
            group = {start}
            remaining.remove(start)
            while queue:
                row, col = queue.popleft()
                for neighbor in (
                    (row - 1, col), (row + 1, col),
                    (row, col - 1), (row, col + 1),
                ):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        group.add(neighbor)
                        queue.append(neighbor)
            ordered = tuple(sorted(group))
            result.append(
                ConfirmedShip(
                    length=len(ordered),
                    direction=(
                        "H" if len({row for row, _col in ordered}) == 1 else "V"
                    ),
                    cells=ordered,
                    safety_area=frozenset(),
                )
            )
        return tuple(result)


def apply_manual_edits(
    session: ManualEditSession,
    board: SonarBoard,
    strategy: RebuildableStrategy,
) -> ManualApplyResult:
    """事务式写入人工棋盘事实并重建策略；失败时恢复正式状态。"""
    if board.grid_size != session.grid_size or board.submarines != session.submarines:
        raise ManualEditError("人工缓存与当前正式棋盘配置不一致")

    session.validate_for_apply(
        use_safety_rule=bool(strategy.use_safety_rule),
    )
    board_before = board.snapshot()
    strategy_before = strategy.snapshot()

    try:
        board.replace_states(session.states)
        strategy.rebuild_from_board(session.confirmed_ships)
        next_cell = strategy.choose_next_cell()
    except Exception as exc:
        rollback_errors: list[Exception] = []
        try:
            board.replace_states(board_before.states)
        except Exception as rollback_exc:
            rollback_errors.append(rollback_exc)
        try:
            strategy.restore_from_snapshot(strategy_before)
        except Exception as rollback_exc:
            rollback_errors.append(rollback_exc)
        if rollback_errors:
            details = "；".join(str(item) for item in rollback_errors)
            raise RuntimeError(f"人工修改应用失败，回滚同时失败：{details}") from exc
        raise

    return ManualApplyResult(
        next_cell=next_cell,
        board_snapshot=board.snapshot(),
        strategy_snapshot=strategy.snapshot(),
    )


__all__ = [
    "ManualApplyResult",
    "ManualEditError",
    "ManualEditSession",
    "apply_manual_edits",
]
