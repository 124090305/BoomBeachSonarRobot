from __future__ import annotations

from collections import deque
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
from sonar_config import GUI_CONFIG

from .theme import (
    BOARD_CELL_SCALE,
    BOARD_SELECTED_WIDTH,
    BOARD_SUNK_WIDTH,
    PALETTE,
    SPACING,
    TYPOGRAPHY,
)


# =========================================================
# 棋盘显示颜色
# =========================================================

# 未探测和“下一步选择”都保持淡蓝底色；
# 下一步选择额外使用高亮边框区分。
_UNKNOWN_FILL = PALETTE.board_unknown
_MISS_FILL = PALETTE.board_miss
_HIT_FILL = PALETTE.board_hit

_GRID_OUTLINE = PALETTE.board_grid
_SELECTED_OUTLINE = PALETTE.board_selected
_SUNK_OUTLINE = PALETTE.board_sunk
_BOARD_OUTLINE = PALETTE.border_strong

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

        self.info_var = tk.StringVar()
        self.strategy_mode_var = tk.StringVar(value="-")
        self.remaining_var = tk.StringVar(value="-")
        self.confirmed_var = tk.StringVar(value="0")
        self.excluded_var = tk.StringVar(value="0")
        self.hover_var = tk.StringVar(
            value="移动鼠标到格子上，可查看逻辑坐标、模拟器坐标和当前状态"
        )

        self._build_ui()

        self.after(
            GUI_CONFIG.board_refresh_ms,
            self._poll_board,
        )

    # =========================================================
    # UI 结构
    # =========================================================

    def _build_ui(self) -> None:
        self.configure(style="Card.TFrame")

        header = ttk.Frame(
            self,
            style="Card.TFrame",
        )
        header.pack(
            fill=tk.X,
            pady=(0, SPACING.sm),
        )

        ttk.Label(
            header,
            text="声纳棋盘",
            style="BoardTitle.Card.TLabel",
        ).pack(side=tk.LEFT)

        ttk.Label(
            header,
            textvariable=self.info_var,
            style="Muted.Card.TLabel",
        ).pack(
            side=tk.RIGHT,
        )

        strategy_row = ttk.Frame(
            self,
            style="Card.TFrame",
        )
        strategy_row.pack(
            fill=tk.X,
            pady=(0, SPACING.sm),
        )

        strategy_specs = (
            ("策略", self.strategy_mode_var),
            ("剩余潜艇", self.remaining_var),
            ("已确认", self.confirmed_var),
            ("已排除", self.excluded_var),
        )

        for index, (caption, variable) in enumerate(strategy_specs):
            item = ttk.Frame(
                strategy_row,
                style="Card.TFrame",
            )
            item.grid(
                row=0,
                column=index,
                sticky=tk.EW,
                padx=(0, SPACING.md),
            )
            ttk.Label(
                item,
                text=caption,
                style="MetricCaption.Card.TLabel",
            ).pack(anchor=tk.W)
            ttk.Label(
                item,
                textvariable=variable,
                style="Card.TLabel",
                font=TYPOGRAPHY.body_bold,
            ).pack(anchor=tk.W)
            strategy_row.columnconfigure(index, weight=1)

        self.canvas = tk.Canvas(
            self,
            width=GUI_CONFIG.board_view_width,
            height=GUI_CONFIG.board_view_height,
            highlightthickness=0,
            borderwidth=0,
            background=PALETTE.surface_muted,
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

        footer = ttk.Frame(
            self,
            style="Card.TFrame",
        )
        footer.pack(
            fill=tk.X,
            pady=(SPACING.sm, 0),
        )

        ttk.Label(
            footer,
            textvariable=self.hover_var,
            style="Muted.Card.TLabel",
        ).pack(
            fill=tk.X,
            anchor=tk.W,
        )

        legend = ttk.Frame(
            footer,
            style="Card.TFrame",
        )
        legend.pack(
            fill=tk.X,
            pady=(SPACING.xs, 0),
        )

        legend_items = (
            ("未探测", _UNKNOWN_FILL, _GRID_OUTLINE, 1),
            ("下一步选择", _UNKNOWN_FILL, _SELECTED_OUTLINE, 3),
            ("未命中 / 已排除", _MISS_FILL, _GRID_OUTLINE, 1),
            ("命中", _HIT_FILL, _GRID_OUTLINE, 1),
            ("已确认潜艇", _HIT_FILL, _SUNK_OUTLINE, 3),
        )

        for text, fill, border, thickness in legend_items:
            item = tk.Frame(
                legend,
                background=fill,
                width=12,
                height=12,
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
                style="Muted.Card.TLabel",
            ).pack(
                side=tk.LEFT,
                padx=(0, SPACING.md),
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
            board_snapshot.revision != self._last_board_revision
            or strategy_snapshot != self._last_strategy_snapshot
        ):
            self.refresh(
                board_snapshot=board_snapshot,
                strategy_snapshot=strategy_snapshot,
            )

        self.after(
            GUI_CONFIG.board_refresh_ms,
            self._poll_board,
        )

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

        self._last_board_revision = board_snapshot.revision
        self._last_strategy_snapshot = strategy_snapshot

        self._update_info(
            board_snapshot,
            strategy_snapshot,
        )

        self._draw_board(
            board_snapshot,
            strategy_snapshot,
        )

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
            f"潜艇 [{submarine_text}] · "
            f"坐标映射 {board_snapshot.mapped_count}/{total}"
        )

        if strategy_snapshot is None:
            self.strategy_mode_var.set("未绑定")
            self.remaining_var.set("-")
            self.confirmed_var.set("0")
            self.excluded_var.set("0")
            return

        mode_text = _MODE_TEXT.get(
            strategy_snapshot.mode,
            strategy_snapshot.mode,
        )

        if strategy_snapshot.remaining_submarines:
            remaining_text = " / ".join(
                str(length)
                for length in strategy_snapshot.remaining_submarines
            )
        else:
            remaining_text = "无"

        self.strategy_mode_var.set(mode_text)
        self.remaining_var.set(remaining_text)
        self.confirmed_var.set(
            str(len(strategy_snapshot.confirmed_ships))
        )
        self.excluded_var.set(
            str(len(strategy_snapshot.excluded_cells))
        )

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
            200,
        )
        height = max(
            self.canvas.winfo_height(),
            180,
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
                    scale=BOARD_CELL_SCALE,
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
                    BOARD_SELECTED_WIDTH
                    if is_selected
                    else 1
                )

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
                        fill=PALETTE.text_muted,
                        font=(TYPOGRAPHY.family, 7),
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
            width=1,
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
                    fill=_SUNK_OUTLINE,
                    width=BOARD_SUNK_WIDTH,
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
        scale: float = 1.0,
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

        points = (
            p_top[0], p_top[1],
            p_right[0], p_right[1],
            p_bottom[0], p_bottom[1],
            p_left[0], p_left[1],
        )

        if scale >= 0.999:
            return points

        center = self._cell_center(points)
        scaled: list[float] = []

        for x, y in zip(
            points[0::2],
            points[1::2],
        ):
            scaled.extend(
                (
                    center[0] + (x - center[0]) * scale,
                    center[1] + (y - center[1]) * scale,
                )
            )

        return tuple(scaled)

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
        self._hover_cell = None
        self.hover_var.set(
            "移动鼠标到格子上，可查看逻辑坐标、模拟器坐标和当前状态"
        )

    def _on_resize(
        self,
        _event: tk.Event,
    ) -> None:
        self.refresh()
