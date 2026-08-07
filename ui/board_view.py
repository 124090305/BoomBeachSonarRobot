from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import config_test

from sonar import (
    BoardSnapshot,
    CellState,
    SonarBoard,
)


_STATE_COLORS = {
    CellState.UNKNOWN: "#dbeafe",
    CellState.SELECTED: "#facc15",
    CellState.MISS: "#94a3b8",
    CellState.HIT: "#ef4444",
    CellState.SUNK: "#22c55e",
}


class SonarBoardView(ttk.Frame):
    """
    GUI 中的声纳棋盘。

    它只读取 SonarBoard：
    Board 是数据源，Canvas 只负责把当前状态画出来。
    """

    def __init__(
        self,
        master: tk.Misc,
        board: SonarBoard,
    ) -> None:
        super().__init__(master)

        self.board = board
        self._last_revision = -1
        self._cell_items: dict[tuple[int, int], int] = {}
        self._hover_cell: tuple[int, int] | None = None

        self.info_var = tk.StringVar()
        self.hover_var = tk.StringVar(
            value="移动鼠标到格子上，可查看逻辑坐标和模拟器坐标"
        )

        self._build_ui()

        self.after(
            config_test.TEST_BOARD_REFRESH_MS,
            self._poll_board,
        )

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(
            fill=tk.X,
            pady=(0, 6),
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

        self.canvas = tk.Canvas(
            self,
            width=config_test.TEST_BOARD_VIEW_WIDTH,
            height=config_test.TEST_BOARD_VIEW_HEIGHT,
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

        legend = ttk.Frame(self)
        legend.pack(
            fill=tk.X,
            pady=(6, 0),
        )

        legend_items = (
            ("空白", CellState.UNKNOWN),
            ("当前选择", CellState.SELECTED),
            ("未命中", CellState.MISS),
            ("命中", CellState.HIT),
            ("已确认潜艇", CellState.SUNK),
        )

        for text, state in legend_items:
            item = tk.Frame(
                legend,
                background=_STATE_COLORS[state],
                width=12,
                height=12,
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

        snapshot = self.board.snapshot()

        if snapshot.revision != self._last_revision:
            self.refresh(snapshot)

        self.after(
            config_test.TEST_BOARD_REFRESH_MS,
            self._poll_board,
        )

    def refresh(
        self,
        snapshot: BoardSnapshot | None = None,
    ) -> None:
        if snapshot is None:
            snapshot = self.board.snapshot()

        self._last_revision = snapshot.revision

        self._update_info(snapshot)
        self._draw_board(snapshot)

    def _update_info(
        self,
        snapshot: BoardSnapshot,
    ) -> None:
        submarine_text = ",".join(
            str(length)
            for length in snapshot.submarines
        )

        total = snapshot.n * snapshot.n

        self.info_var.set(
            f"{snapshot.n}×{snapshot.n} | "
            f"潜艇 [{submarine_text}] | "
            f"坐标映射 {snapshot.mapped_count}/{total}"
        )

    # =========================================================
    # 菱形棋盘绘制
    # =========================================================

    def _draw_board(
        self,
        snapshot: BoardSnapshot,
    ) -> None:
        self.canvas.delete("all")
        self._cell_items.clear()

        width = max(
            self.canvas.winfo_width(),
            config_test.TEST_BOARD_VIEW_WIDTH,
        )
        height = max(
            self.canvas.winfo_height(),
            config_test.TEST_BOARD_VIEW_HEIGHT,
        )

        padding = config_test.TEST_BOARD_VIEW_PADDING

        usable_width = max(100, width - padding * 2)
        usable_height = max(100, height - padding * 2)

        # 整块棋盘是一个大菱形。
        # n 个格子横向叠加后的总宽约为 n * cell_width，
        # 总高约为 n * cell_height。
        cell_width = min(
            usable_width / snapshot.n,
            (usable_height * 2.0) / snapshot.n,
        )

        cell_height = min(
            cell_width * 0.52,
            usable_height / snapshot.n,
        )

        board_width = snapshot.n * cell_width
        board_height = snapshot.n * cell_height

        center_x = width / 2.0
        top_y = max(
            padding,
            (height - board_height) / 2.0,
        )

        for row in range(snapshot.n):
            for col in range(snapshot.n):
                points = self._cell_polygon(
                    row=row,
                    col=col,
                    center_x=center_x,
                    top_y=top_y,
                    cell_width=cell_width,
                    cell_height=cell_height,
                )

                state = snapshot.states[row][col]

                item_id = self.canvas.create_polygon(
                    *points,
                    fill=_STATE_COLORS[state],
                    outline="#475569",
                    width=1,
                    tags=(
                        "board-cell",
                        f"cell-{row}-{col}",
                    ),
                )

                self._cell_items[(row, col)] = item_id

                if config_test.TEST_BOARD_SHOW_COORDS:
                    center = self._cell_center(points)

                    self.canvas.create_text(
                        center[0],
                        center[1],
                        text=f"{row + 1},{col + 1}",
                        fill="#0f172a",
                        font=("TkDefaultFont", 7),
                        tags=("cell-label",),
                    )

        # 外轮廓更粗一点，方便和游戏中的大菱形对应。
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
            outline="#0f172a",
            width=2,
            tags=("board-outline",),
        )

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

        found: tuple[int, int] | None = None

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
                "移动鼠标到格子上，可查看逻辑坐标和模拟器坐标"
            )
            return

        row, col = found
        snapshot = self.board.snapshot()
        point = snapshot.screen_points[row][col]

        if point is None:
            point_text = "模拟器坐标：未绑定"
        else:
            point_text = f"模拟器坐标：{point}"

        self.hover_var.set(
            f"逻辑格：({row},{col}) | {point_text}"
        )

    def _on_mouse_leave(
        self,
        _event: tk.Event,
    ) -> None:
        self._hover_cell = None
        self.hover_var.set(
            "移动鼠标到格子上，可查看逻辑坐标和模拟器坐标"
        )

    def _on_resize(
        self,
        _event: tk.Event,
    ) -> None:
        self.refresh()
