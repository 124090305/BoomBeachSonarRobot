from __future__ import annotations

from collections import deque
import time
import tkinter as tk
from tkinter import ttk

from sonar import (
    BoardSnapshot,
    Cell,
    CellState,
    SonarBoard,
    SonarStrategy,
    StrategySnapshot,
)
from sonar.manual_intervention import (
    ManualEditError,
    ManualEditSession,
)
from sonar_config import GUI_CONFIG


# =========================================================
# 棋盘显示颜色
# =========================================================

# 未探测和“下一步选择”都保持淡蓝底色；
# 下一步选择额外使用高亮边框区分。
_UNKNOWN_FILL = "#dbeafe"
_MISS_FILL = "#94a3b8"
_HIT_FILL = "#facc15"

_GRID_OUTLINE = "#475569"
_SELECTED_OUTLINE = "#0ea5e9"
_SUNK_OUTLINE = "#f97316"
_MANUAL_EDIT_OUTLINE = "#a855f7"
_MANUAL_CONFIRM_OUTLINE = "#7c3aed"
_MANUAL_CANCEL_OUTLINE = "#dc2626"
_CANDIDATE_VALID_OUTLINE = "#16a34a"
_CANDIDATE_INVALID_OUTLINE = "#ef4444"
_BOARD_OUTLINE = "#0f172a"

_LONG_PRESS_SECONDS = 1.0
_LONG_PRESS_REFRESH_MS = 25

_STATE_COLORS = {
    CellState.UNKNOWN: _UNKNOWN_FILL,
    CellState.SELECTED: _UNKNOWN_FILL,
    CellState.MISS: _MISS_FILL,
    CellState.HIT: _HIT_FILL,
    CellState.SUNK: _HIT_FILL,
}

_MODE_TEXT = {
    "HUNT": "巡航",
    "TARGET": "追击",
    "DONE": "完成",
}


class SonarBoardView(ttk.Frame):
    """
    GUI 中的声纳棋盘。

    显示分成两层：

    1. SonarBoard
       保存真实棋盘结果：未探测 / 未命中 / 命中 / 已确认潜艇。

    2. SonarStrategy
       提供策略附加信息：下一步选择、排除格、剩余潜艇、已确认潜艇。

    后续加入概率云、蒙特卡洛时，UI 继续读取 SonarStrategy.snapshot()，
    不需要改变真实棋盘数据结构。
    """

    def __init__(
        self,
        master: tk.Misc,
        board: SonarBoard,
        strategy: SonarStrategy | None = None,
    ) -> None:
        super().__init__(master)

        self.board = board
        self.strategy = strategy

        self._last_board_revision = -1
        self._last_strategy_snapshot: StrategySnapshot | None = None

        self._cell_items: dict[Cell, int] = {}
        self._hover_cell: Cell | None = None
        self._manual_session: ManualEditSession | None = None
        self._manual_message = None
        self._last_manual_revision = -1
        self._press_cell: Cell | None = None
        self._press_position: tuple[int, int] | None = None
        self._press_started_at = 0.0
        self._long_press_after_id: str | None = None
        self._long_press_triggered = False
        self._selection_origin: Cell | None = None
        self._candidate_cells: tuple[Cell, ...] = ()
        self._candidate_error: str | None = None
        self._board_poll_after_id: str | None = None

        self.info_var = tk.StringVar()
        self.strategy_var = tk.StringVar()
        self.hover_var = tk.StringVar(
            value="移动鼠标到格子上，可查看逻辑坐标、模拟器坐标和当前状态"
        )

        self._build_ui()

        self._board_poll_after_id = self.after(
            GUI_CONFIG.board_refresh_ms,
            self._poll_board,
        )

    # =========================================================
    # UI 结构
    # =========================================================

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(
            fill=tk.X,
            pady=(0, 4),
        )

        ttk.Label(
            header,
            text="声纳棋盘",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(
            side=tk.LEFT,
        )

        ttk.Label(
            header,
            textvariable=self.info_var,
        ).pack(
            side=tk.LEFT,
            padx=(12, 0),
        )

        ttk.Label(
            header,
            textvariable=self.hover_var,
        ).pack(
            side=tk.RIGHT,
        )

        ttk.Label(
            self,
            textvariable=self.strategy_var,
        ).pack(
            fill=tk.X,
            pady=(0, 6),
        )

        self.canvas = tk.Canvas(
            self,
            width=GUI_CONFIG.board_view_width,
            height=GUI_CONFIG.board_view_height,
            highlightthickness=1,
            highlightbackground="#cbd5e1",
            background="#f8fafc",
        )

        self.canvas.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.canvas.bind(
            "<Configure>",
            self._on_resize,
        )

        self.canvas.bind(
            "<Motion>",
            self._on_mouse_move,
        )

        self.canvas.bind(
            "<Leave>",
            self._on_mouse_leave,
        )

        self.canvas.bind("<ButtonPress-1>", self._on_button_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self.canvas.bind("<B1-Motion>", self._on_button_drag)

        legend = ttk.Frame(self)
        legend.pack(
            fill=tk.X,
            pady=(6, 0),
        )

        legend_items = (
            ("未探测", _UNKNOWN_FILL, _GRID_OUTLINE, 1),
            ("下一步选择", _UNKNOWN_FILL, _SELECTED_OUTLINE, 3),
            ("未命中 / 已排除", _MISS_FILL, _GRID_OUTLINE, 1),
            ("命中", _HIT_FILL, _GRID_OUTLINE, 1),
            ("已确认潜艇", _HIT_FILL, _SUNK_OUTLINE, 3),
            ("人工临时修改", _UNKNOWN_FILL, _MANUAL_EDIT_OUTLINE, 3),
        )

        for text, fill, border, thickness in legend_items:
            item = tk.Frame(
                legend,
                background=fill,
                width=14,
                height=14,
                highlightbackground=border,
                highlightcolor=border,
                highlightthickness=thickness,
            )
            item.pack(
                side=tk.LEFT,
                padx=(0, 4),
            )
            item.pack_propagate(False)

            ttk.Label(
                legend,
                text=text,
            ).pack(
                side=tk.LEFT,
                padx=(0, 12),
            )

    # =========================================================
    # 自动同步
    # =========================================================

    def _poll_board(self) -> None:
        if not self.winfo_exists():
            return

        board_snapshot = self.board.snapshot()
        strategy_snapshot = self._strategy_snapshot()

        if (
            self._manual_session is not None
            and self._manual_session.revision != self._last_manual_revision
        ) or (
            board_snapshot.revision != self._last_board_revision
            or strategy_snapshot != self._last_strategy_snapshot
        ):
            self.refresh(
                board_snapshot=board_snapshot,
                strategy_snapshot=strategy_snapshot,
            )

        self._board_poll_after_id = self.after(
            GUI_CONFIG.board_refresh_ms,
            self._poll_board,
        )

    def shutdown(self) -> None:
        """窗口销毁前取消棋盘轮询和长按定时任务。"""
        self.clear_manual_interaction()
        if self._board_poll_after_id is None:
            return
        try:
            self.after_cancel(self._board_poll_after_id)
        except tk.TclError:
            pass
        self._board_poll_after_id = None

    def _strategy_snapshot(self) -> StrategySnapshot | None:
        if self.strategy is None:
            return None

        return self.strategy.snapshot()

    def refresh(
        self,
        board_snapshot: BoardSnapshot | None = None,
        strategy_snapshot: StrategySnapshot | None = None,
    ) -> None:
        if board_snapshot is None:
            board_snapshot = self.board.snapshot()

        if strategy_snapshot is None:
            strategy_snapshot = self._strategy_snapshot()

        if self._manual_session is not None:
            board_snapshot = BoardSnapshot(
                revision=board_snapshot.revision,
                grid_size=board_snapshot.grid_size,
                submarines=board_snapshot.submarines,
                states=self._manual_session.states,
                screen_points=board_snapshot.screen_points,
            )
            if strategy_snapshot is not None:
                strategy_snapshot = StrategySnapshot(
                    mode=strategy_snapshot.mode,
                    pending_cell=strategy_snapshot.pending_cell,
                    excluded_cells=strategy_snapshot.excluded_cells,
                    remaining_submarines=strategy_snapshot.remaining_submarines,
                    confirmed_ships=strategy_snapshot.confirmed_ships,
                    calculation_progress=strategy_snapshot.calculation_progress,
                    calculation_status=strategy_snapshot.calculation_status,
                )

        self._last_board_revision = board_snapshot.revision
        self._last_strategy_snapshot = strategy_snapshot
        self._last_manual_revision = (
            self._manual_session.revision
            if self._manual_session is not None
            else -1
        )

        self._update_info(
            board_snapshot,
            strategy_snapshot,
        )

        self._draw_board(
            board_snapshot,
            strategy_snapshot,
        )

    def set_manual_session(
        self,
        session: ManualEditSession | None,
        *,
        on_message=None,
    ) -> None:
        """切换棋盘的临时人工编辑视图。"""
        self.clear_manual_interaction()
        self._manual_session = session
        self._manual_message = on_message
        self._last_manual_revision = -1
        self.refresh()

    def set_models(
        self,
        board: SonarBoard,
        strategy: SonarStrategy | None,
    ) -> None:
        """关卡切换时绑定新的棋盘和策略对象。"""
        self.clear_manual_interaction()
        self._manual_session = None
        self.board = board
        self.strategy = strategy
        self._last_board_revision = -1
        self._last_strategy_snapshot = None
        self._last_manual_revision = -1
        self.refresh()

    def clear_manual_interaction(self) -> None:
        """取消长按、候选选择及其 Canvas 定时任务。"""
        if self._long_press_after_id is not None:
            try:
                self.after_cancel(self._long_press_after_id)
            except tk.TclError:
                pass
        self._long_press_after_id = None
        self._press_cell = None
        self._press_position = None
        self._long_press_triggered = False
        self._selection_origin = None
        self._candidate_cells = ()
        self._candidate_error = None
        if hasattr(self, "canvas"):
            self.canvas.delete("manual-hold-progress")

    # =========================================================
    # 顶部信息
    # =========================================================

    def _update_info(
        self,
        board_snapshot: BoardSnapshot,
        strategy_snapshot: StrategySnapshot | None,
    ) -> None:
        submarine_text = ",".join(
            str(length)
            for length in board_snapshot.submarines
        )

        total = board_snapshot.grid_size * board_snapshot.grid_size

        self.info_var.set(
            f"{board_snapshot.grid_size}×{board_snapshot.grid_size} | "
            f"潜艇 [{submarine_text}] | "
            f"坐标映射 {board_snapshot.mapped_count}/{total}"
        )

        if strategy_snapshot is None:
            self.strategy_var.set(
                "策略：未绑定"
            )
            return

        explored_count = sum(
            state in (
                CellState.MISS,
                CellState.HIT,
                CellState.SUNK,
            )
            for row in board_snapshot.states
            for state in row
        )

        mode_text = _MODE_TEXT.get(
            strategy_snapshot.mode,
            strategy_snapshot.mode,
        )

        if strategy_snapshot.pending_cell is None:
            next_text = "无"
        else:
            next_text = str(
                strategy_snapshot.pending_cell
            )

        if strategy_snapshot.remaining_submarines:
            remaining_text = ",".join(
                str(length)
                for length in strategy_snapshot.remaining_submarines
            )
        else:
            remaining_text = "无"

        text = (
            f"策略：{mode_text} | "
            f"下一格 {next_text} | "
            f"已探测 {explored_count} | "
            f"已排除 {len(strategy_snapshot.excluded_cells)} | "
            f"已确认 {len(strategy_snapshot.confirmed_ships)} | "
            f"剩余 [{remaining_text}]"
        )

        if strategy_snapshot.calculation_progress is not None:
            percent = int(
                max(
                    0.0,
                    min(
                        1.0,
                        strategy_snapshot.calculation_progress,
                    ),
                )
                * 100
            )

            text += (
                f" | 计算 {percent}%"
            )

            if strategy_snapshot.calculation_status:
                text += (
                    f" {strategy_snapshot.calculation_status}"
                )

        self.strategy_var.set(text)

    # =========================================================
    # 菱形棋盘绘制
    # =========================================================

    def _draw_board(
        self,
        snapshot: BoardSnapshot,
        strategy_snapshot: StrategySnapshot | None,
    ) -> None:
        self.canvas.delete("all")
        self._cell_items.clear()

        width = max(
            self.canvas.winfo_width(),
            GUI_CONFIG.board_view_width,
        )
        height = max(
            self.canvas.winfo_height(),
            GUI_CONFIG.board_view_height,
        )

        padding = GUI_CONFIG.board_view_padding

        usable_width = max(
            100,
            width - padding * 2,
        )
        usable_height = max(
            100,
            height - padding * 2,
        )

        cell_width = min(
            usable_width / snapshot.grid_size,
            (usable_height * 2.0) / snapshot.grid_size,
        )

        cell_height = min(
            cell_width * 0.52,
            usable_height / snapshot.grid_size,
        )

        board_width = snapshot.grid_size * cell_width
        board_height = snapshot.grid_size * cell_height

        center_x = width / 2.0
        top_y = max(
            padding,
            (height - board_height) / 2.0,
        )

        excluded_cells = (
            strategy_snapshot.excluded_cells
            if strategy_snapshot is not None
            else frozenset()
        )

        pending_cell = (
            strategy_snapshot.pending_cell
            if strategy_snapshot is not None
            else None
        )

        for row in range(snapshot.grid_size):
            for col in range(snapshot.grid_size):
                cell = (row, col)

                points = self._cell_polygon(
                    row=row,
                    col=col,
                    center_x=center_x,
                    top_y=top_y,
                    cell_width=cell_width,
                    cell_height=cell_height,
                )

                state = snapshot.states[row][col]

                fill = self._cell_fill(
                    cell=cell,
                    state=state,
                    excluded_cells=excluded_cells,
                )

                if strategy_snapshot is not None:
                    is_selected = (
                        cell == pending_cell
                    )
                else:
                    is_selected = (
                        state == CellState.SELECTED
                    )

                outline = (
                    _SELECTED_OUTLINE
                    if is_selected
                    else _GRID_OUTLINE
                )

                outline_width = (
                    3
                    if is_selected
                    else 1
                )

                if (
                    self._manual_session is not None
                    and cell in self._manual_session.changed_cells
                ):
                    outline = _MANUAL_EDIT_OUTLINE
                    outline_width = 3

                if self._manual_session is not None:
                    if cell in self._manual_session.pending_cancelled_cells:
                        outline = _MANUAL_CANCEL_OUTLINE
                        outline_width = 4
                    elif cell in self._manual_session.pending_confirmed_cells:
                        outline = _MANUAL_CONFIRM_OUTLINE
                        outline_width = 4

                if cell in self._candidate_cells:
                    outline = (
                        _CANDIDATE_VALID_OUTLINE
                        if self._candidate_error is None
                        else _CANDIDATE_INVALID_OUTLINE
                    )
                    outline_width = 4

                item_id = self.canvas.create_polygon(
                    *points,
                    fill=fill,
                    outline=outline,
                    width=outline_width,
                    tags=(
                        "board-cell",
                        f"cell-{row}-{col}",
                    ),
                )

                self._cell_items[cell] = item_id

                if GUI_CONFIG.board_show_coords:
                    center = self._cell_center(points)

                    self.canvas.create_text(
                        center[0],
                        center[1],
                        text=f"{row + 1},{col + 1}",
                        fill="#0f172a",
                        font=("TkDefaultFont", 7),
                        tags=("cell-label",),
                    )

        # 整个棋盘外轮廓。
        top = (
            center_x,
            top_y,
        )
        right = (
            center_x + board_width / 2.0,
            top_y + board_height / 2.0,
        )
        bottom = (
            center_x,
            top_y + board_height,
        )
        left = (
            center_x - board_width / 2.0,
            top_y + board_height / 2.0,
        )

        self.canvas.create_polygon(
            *top,
            *right,
            *bottom,
            *left,
            fill="",
            outline=_BOARD_OUTLINE,
            width=2,
            tags=("board-outline",),
        )

        # 已确认潜艇最后绘制高亮外框，保证它盖在普通网格线上方。
        confirmed_groups = self._confirmed_ship_groups(
            snapshot,
            strategy_snapshot,
        )

        for ship_cells in confirmed_groups:
            self._draw_ship_outline(
                ship_cells=ship_cells,
                center_x=center_x,
                top_y=top_y,
                cell_width=cell_width,
                cell_height=cell_height,
            )

        if self._manual_session is not None:
            cancelled = self._manual_session.pending_cancelled_cells
            if cancelled:
                self._draw_ship_outline(
                    ship_cells=cancelled,
                    center_x=center_x,
                    top_y=top_y,
                    cell_width=cell_width,
                    cell_height=cell_height,
                    color=_MANUAL_CANCEL_OUTLINE,
                )

    @staticmethod
    def _cell_fill(
        cell: Cell,
        state: CellState,
        excluded_cells: frozenset[Cell],
    ) -> str:
        # 已知命中和已确认潜艇始终显示黄色。
        if state in (
            CellState.HIT,
            CellState.SUNK,
        ):
            return _HIT_FILL

        # 真正点过但未命中，或者策略已经确认可以排除，统一显示灰色。
        if (
            state == CellState.MISS
            or cell in excluded_cells
        ):
            return _MISS_FILL

        # 未探测 / 下一步选择使用淡蓝色。
        return _UNKNOWN_FILL

    # =========================================================
    # 已确认潜艇高亮外框
    # =========================================================

    def _confirmed_ship_groups(
        self,
        snapshot: BoardSnapshot,
        strategy_snapshot: StrategySnapshot | None,
    ) -> tuple[frozenset[Cell], ...]:
        if self._manual_session is not None:
            pending = self._manual_session.pending_confirmed_cells
            return tuple(
                frozenset(ship.cells)
                for ship in self._manual_session.confirmed_ships
                if not set(ship.cells).issubset(pending)
            )
        if (
            strategy_snapshot is not None
            and strategy_snapshot.confirmed_ships
        ):
            return tuple(
                frozenset(ship.cells)
                for ship in strategy_snapshot.confirmed_ships
            )

        # 兼容手动调用 SonarBoard.mark_sunk() 的情况。
        return self._sunk_components(snapshot)

    def _sunk_components(
        self,
        snapshot: BoardSnapshot,
    ) -> tuple[frozenset[Cell], ...]:
        sunk_cells = {
            (row, col)
            for row in range(snapshot.grid_size)
            for col in range(snapshot.grid_size)
            if snapshot.states[row][col]
            == CellState.SUNK
        }

        visited: set[Cell] = set()
        groups: list[frozenset[Cell]] = []

        for start in sorted(sunk_cells):
            if start in visited:
                continue

            queue = deque([start])
            visited.add(start)
            group = {start}

            while queue:
                row, col = queue.popleft()

                for next_cell in (
                    (row - 1, col),
                    (row + 1, col),
                    (row, col - 1),
                    (row, col + 1),
                ):
                    if (
                        next_cell in sunk_cells
                        and next_cell not in visited
                    ):
                        visited.add(next_cell)
                        group.add(next_cell)
                        queue.append(next_cell)

            groups.append(
                frozenset(group)
            )

        return tuple(groups)

    def _draw_ship_outline(
        self,
        ship_cells: frozenset[Cell],
        center_x: float,
        top_y: float,
        cell_width: float,
        cell_height: float,
        color: str = _SUNK_OUTLINE,
    ) -> None:
        """只绘制潜艇整体最外侧边缘，形成一个连续高亮框。"""
        for row, col in ship_cells:
            points = self._cell_polygon(
                row=row,
                col=col,
                center_x=center_x,
                top_y=top_y,
                cell_width=cell_width,
                cell_height=cell_height,
            )

            p_top, p_right, p_bottom, p_left = (
                self._polygon_points(points)
            )

            edges = (
                ((row - 1, col), p_top, p_right),
                ((row, col + 1), p_right, p_bottom),
                ((row + 1, col), p_bottom, p_left),
                ((row, col - 1), p_left, p_top),
            )

            for neighbor, start, end in edges:
                if neighbor in ship_cells:
                    continue

                self.canvas.create_line(
                    start[0],
                    start[1],
                    end[0],
                    end[1],
                    fill=color,
                    width=4,
                    capstyle=tk.ROUND,
                    tags=("confirmed-ship-outline",),
                )

    @staticmethod
    def _polygon_points(
        points: tuple[float, ...],
    ) -> tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ]:
        return (
            (points[0], points[1]),
            (points[2], points[3]),
            (points[4], points[5]),
            (points[6], points[7]),
        )

    # =========================================================
    # 菱形坐标辅助
    # =========================================================

    @staticmethod
    def _grid_point(
        row_line: float,
        col_line: float,
        center_x: float,
        top_y: float,
        cell_width: float,
        cell_height: float,
    ) -> tuple[float, float]:
        """
        把逻辑网格交点转成 GUI 菱形坐标。

        col 增大：向右下移动
        row 增大：向左下移动
        """
        x = center_x + (
            col_line - row_line
        ) * cell_width / 2.0

        y = top_y + (
            col_line + row_line
        ) * cell_height / 2.0

        return x, y

    def _cell_polygon(
        self,
        row: int,
        col: int,
        center_x: float,
        top_y: float,
        cell_width: float,
        cell_height: float,
    ) -> tuple[float, ...]:
        p_top = self._grid_point(
            row,
            col,
            center_x,
            top_y,
            cell_width,
            cell_height,
        )

        p_right = self._grid_point(
            row,
            col + 1,
            center_x,
            top_y,
            cell_width,
            cell_height,
        )

        p_bottom = self._grid_point(
            row + 1,
            col + 1,
            center_x,
            top_y,
            cell_width,
            cell_height,
        )

        p_left = self._grid_point(
            row + 1,
            col,
            center_x,
            top_y,
            cell_width,
            cell_height,
        )

        return (
            p_top[0], p_top[1],
            p_right[0], p_right[1],
            p_bottom[0], p_bottom[1],
            p_left[0], p_left[1],
        )

    @staticmethod
    def _cell_center(
        points: tuple[float, ...],
    ) -> tuple[float, float]:
        xs = points[0::2]
        ys = points[1::2]

        return (
            sum(xs) / len(xs),
            sum(ys) / len(ys),
        )

    # =========================================================
    # 鼠标查看格子信息
    # =========================================================

    def _cell_at(self, x: int, y: int) -> Cell | None:
        items = self.canvas.find_overlapping(x, y, x, y)
        for item_id in reversed(items):
            for tag in self.canvas.gettags(item_id):
                parts = tag.split("-")
                if len(parts) == 3 and parts[0] == "cell":
                    return int(parts[1]), int(parts[2])
        return None

    def _on_button_press(self, event: tk.Event) -> None:
        session = self._manual_session
        if session is None:
            return
        cell = self._cell_at(event.x, event.y)
        if cell is None:
            return
        self.clear_manual_interaction()
        self._press_cell = cell
        self._press_position = (event.x, event.y)
        self._press_started_at = time.monotonic()
        if session.state_at(cell) in (CellState.HIT, CellState.SUNK):
            self._update_long_press()

    def _update_long_press(self) -> None:
        if self._press_cell is None or self._press_position is None:
            return
        elapsed = time.monotonic() - self._press_started_at
        progress = min(1.0, elapsed / _LONG_PRESS_SECONDS)
        self._draw_long_press_progress(
            self._press_position[0],
            self._press_position[1],
            progress,
        )
        if progress >= 1.0:
            self._long_press_after_id = None
            self._trigger_long_press()
            return
        self._long_press_after_id = self.after(
            _LONG_PRESS_REFRESH_MS,
            self._update_long_press,
        )

    def _draw_long_press_progress(
        self,
        x: int,
        y: int,
        progress: float,
    ) -> None:
        self.canvas.delete("manual-hold-progress")
        radius = 18
        bounds = (x - radius, y - radius, x + radius, y + radius)
        self.canvas.create_oval(
            *bounds,
            outline="#64748b",
            width=2,
            tags=("manual-hold-progress",),
        )
        self.canvas.create_arc(
            *bounds,
            start=90,
            extent=-360 * progress,
            style=tk.ARC,
            outline="#2563eb",
            width=4,
            tags=("manual-hold-progress",),
        )

    def _trigger_long_press(self) -> None:
        session = self._manual_session
        cell = self._press_cell
        self.canvas.delete("manual-hold-progress")
        if session is None or cell is None:
            return
        self._long_press_triggered = True
        try:
            if session.state_at(cell) == CellState.SUNK:
                ship = session.cancel_ship_at(cell)
                self._emit_manual_message(
                    f"已暂存取消长度 {ship.length} 的整艘潜艇确认"
                )
                self.refresh()
                return
            self._selection_origin = cell
            self._candidate_cells = (cell,)
            self._update_candidate_validation()
            self._emit_manual_message("长按完成：拖动选择连续 HIT 潜艇")
            self.refresh()
        except ManualEditError as exc:
            self._emit_manual_message(str(exc))

    def _on_button_drag(self, event: tk.Event) -> None:
        if self._press_cell is None:
            return
        self._press_position = (event.x, event.y)
        if self._selection_origin is None:
            return
        target = self._cell_at(event.x, event.y)
        if target is None:
            return
        self._candidate_cells = self._straight_cells(
            self._selection_origin,
            target,
        )
        self._update_candidate_validation()
        self.refresh()

    def _update_candidate_validation(self) -> None:
        session = self._manual_session
        if session is None or not self._candidate_cells:
            self._candidate_error = None
            return
        try:
            session.validate_ship_candidate(self._candidate_cells)
        except ManualEditError as exc:
            self._candidate_error = str(exc)
        else:
            self._candidate_error = None

    @staticmethod
    def _straight_cells(origin: Cell, target: Cell) -> tuple[Cell, ...]:
        row, col = origin
        target_row, target_col = target
        if abs(target_col - col) >= abs(target_row - row):
            step = 1 if target_col >= col else -1
            return tuple(
                (row, value)
                for value in range(col, target_col + step, step)
            )
        step = 1 if target_row >= row else -1
        return tuple(
            (value, col)
            for value in range(row, target_row + step, step)
        )

    def _on_button_release(self, _event: tk.Event) -> None:
        session = self._manual_session
        cell = self._press_cell
        long_pressed = self._long_press_triggered
        candidate = self._candidate_cells
        candidate_error = self._candidate_error
        self.clear_manual_interaction()
        if session is None or cell is None:
            return
        try:
            if long_pressed:
                if candidate:
                    if candidate_error is not None:
                        raise ManualEditError(candidate_error)
                    ship = session.confirm_ship(candidate)
                    self._emit_manual_message(
                        f"已暂存确认长度 {ship.length} 的潜艇"
                    )
            else:
                state = session.cycle_cell(cell)
                self._emit_manual_message(
                    f"格子 {cell} 临时修改为 {state.value.upper()}"
                )
        except ManualEditError as exc:
            self._emit_manual_message(str(exc))
        self.refresh()

    def _emit_manual_message(self, message: str) -> None:
        if self._manual_message is not None:
            self._manual_message(message)

    def _on_mouse_move(
        self,
        event: tk.Event,
    ) -> None:
        items = self.canvas.find_overlapping(
            event.x,
            event.y,
            event.x,
            event.y,
        )

        found: Cell | None = None

        for item_id in reversed(items):
            tags = self.canvas.gettags(item_id)

            for tag in tags:
                if not tag.startswith("cell-"):
                    continue

                parts = tag.split("-")

                if len(parts) != 3:
                    continue

                found = (
                    int(parts[1]),
                    int(parts[2]),
                )
                break

            if found is not None:
                break

        if found == self._hover_cell:
            return

        self._hover_cell = found

        if found is None:
            self.hover_var.set(
                "移动鼠标到格子上，可查看逻辑坐标、模拟器坐标和当前状态"
            )
            return

        row, col = found
        board_snapshot = self.board.snapshot()
        strategy_snapshot = self._strategy_snapshot()

        point = board_snapshot.screen_points[row][col]
        state = board_snapshot.states[row][col]

        if point is None:
            point_text = "模拟器坐标：未绑定"
        else:
            point_text = f"模拟器坐标：{point}"

        state_text = self._cell_state_text(
            cell=found,
            state=state,
            strategy_snapshot=strategy_snapshot,
        )

        self.hover_var.set(
            f"逻辑格：({row},{col}) | "
            f"{point_text} | "
            f"状态：{state_text}"
        )

    @staticmethod
    def _cell_state_text(
        cell: Cell,
        state: CellState,
        strategy_snapshot: StrategySnapshot | None,
    ) -> str:
        if (
            strategy_snapshot is not None
            and cell == strategy_snapshot.pending_cell
        ):
            return "下一步选择"

        if state == CellState.SUNK:
            return "已确认潜艇"

        if state == CellState.HIT:
            return "命中"

        if state == CellState.MISS:
            return "未命中"

        if (
            strategy_snapshot is not None
            and cell in strategy_snapshot.excluded_cells
        ):
            return "策略排除"

        return "未探测"

    def _on_mouse_leave(
        self,
        _event: tk.Event,
    ) -> None:
        had_interaction = self._press_cell is not None
        self.clear_manual_interaction()
        if had_interaction and self._manual_session is not None:
            self.refresh()
        self._hover_cell = None
        self.hover_var.set(
            "移动鼠标到格子上，可查看逻辑坐标、模拟器坐标和当前状态"
        )

    def _on_resize(
        self,
        _event: tk.Event,
    ) -> None:
        self.refresh()
