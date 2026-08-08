from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import config_test

from sonar import (
    CheckerboardHuntStrategy,
    SonarBoard,
)
from ui import SonarBoardView


HIDDEN_SHIPS = (
    ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4)),
    ((3, 6), (3, 7), (3, 8), (3, 9)),
    ((5, 0), (6, 0), (7, 0)),
    ((9, 3), (9, 4)),
    ((6, 7), (7, 7)),
)

OCCUPIED = {
    cell
    for ship in HIDDEN_SHIPS
    for cell in ship
}


class StrategyUiDemo(tk.Tk):
    """完全离线的策略 + 棋盘 UI 演示。"""

    def __init__(self) -> None:
        super().__init__()

        self.title("Sonar Strategy UI Demo")
        self.geometry("900x620")

        self.board = SonarBoard(
            n=config_test.TEST_GRID_SIZE,
            submarines=config_test.TEST_SUBMARINES,
        )

        if config_test.TEST_BOARD_QUAD is not None:
            self.board.set_screen_quad(
                config_test.TEST_BOARD_QUAD
            )

        self.strategy = CheckerboardHuntStrategy(
            self.board,
            hunt_parity=config_test.TEST_HUNT_PARITY,
            use_safety_rule=config_test.TEST_USE_SAFETY_RULE,
        )

        self.strategy.choose_next_cell()

        self.step_count = 0
        self._auto_after_id: str | None = None

        self.status_var = tk.StringVar(
            value="已准备第一格"
        )

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(
            self,
            padding=12,
        )
        container.pack(
            fill=tk.BOTH,
            expand=True,
        )

        controls = ttk.Frame(container)
        controls.pack(
            fill=tk.X,
            pady=(0, 8),
        )

        ttk.Button(
            controls,
            text="执行当前一步",
            command=self.run_one_step,
        ).pack(
            side=tk.LEFT,
            padx=(0, 6),
        )

        ttk.Button(
            controls,
            text="自动演示",
            command=self.start_auto,
        ).pack(
            side=tk.LEFT,
            padx=(0, 6),
        )

        ttk.Button(
            controls,
            text="停止",
            command=self.stop_auto,
        ).pack(
            side=tk.LEFT,
            padx=(0, 6),
        )

        ttk.Button(
            controls,
            text="重置",
            command=self.reset_demo,
        ).pack(
            side=tk.LEFT,
        )

        ttk.Label(
            controls,
            textvariable=self.status_var,
        ).pack(
            side=tk.LEFT,
            padx=(16, 0),
        )

        board_view = SonarBoardView(
            container,
            board=self.board,
            strategy=self.strategy,
        )
        board_view.pack(
            fill=tk.BOTH,
            expand=True,
        )

    def run_one_step(self) -> None:
        if self.strategy.done:
            self.status_var.set(
                f"完成，共 {self.step_count} 次探测"
            )
            self.stop_auto()
            return

        cell = self.strategy.pending_cell

        if cell is None:
            cell = self.strategy.choose_next_cell()

        if cell is None:
            self.status_var.set("没有可继续探测的格子")
            self.stop_auto()
            return

        hit = cell in OCCUPIED

        newly_confirmed = self.strategy.report_result(
            cell,
            hit=hit,
        )

        self.step_count += 1

        next_cell = self.strategy.choose_next_cell()

        result_text = "HIT" if hit else "MISS"

        text = (
            f"第 {self.step_count} 步：{cell} -> {result_text}；"
            f"下一格={next_cell}"
        )

        if newly_confirmed:
            lengths = ",".join(
                str(ship.length)
                for ship in newly_confirmed
            )
            text += f"；确认潜艇 [{lengths}]"

        self.status_var.set(text)

        if self.strategy.done:
            self.status_var.set(
                f"完成，共 {self.step_count} 次探测"
            )
            self.stop_auto()

    def start_auto(self) -> None:
        if self._auto_after_id is not None:
            return

        self._auto_step()

    def _auto_step(self) -> None:
        self._auto_after_id = None

        if self.strategy.done:
            return

        self.run_one_step()

        if not self.strategy.done:
            self._auto_after_id = self.after(
                250,
                self._auto_step,
            )

    def stop_auto(self) -> None:
        if self._auto_after_id is None:
            return

        self.after_cancel(
            self._auto_after_id
        )
        self._auto_after_id = None

    def reset_demo(self) -> None:
        self.stop_auto()
        self.strategy.reset()
        self.strategy.choose_next_cell()
        self.step_count = 0
        self.status_var.set("已重置并准备第一格")


def main() -> None:
    app = StrategyUiDemo()
    app.mainloop()


if __name__ == "__main__":
    main()
