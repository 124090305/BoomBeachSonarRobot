from __future__ import annotations

import tkinter as tk
import unittest

from flows.level_loop import create_level_state
from ui.board_view import SonarBoardView
from ui.level_selector import (
    LEVEL_CHOICES,
    LevelSelector,
    format_level_label,
    level_from_label,
)


class LevelDisplayMappingTests(unittest.TestCase):
    def test_internal_levels_map_to_required_labels(self) -> None:
        expected = {
            1: "第1关",
            10: "第10关",
            11: "第11关+",
            12: "第11关+",
            50: "第11关+",
        }
        for level, label in expected.items():
            with self.subTest(level=level):
                self.assertEqual(format_level_label(level), label)
        self.assertEqual(level_from_label("第1关"), 1)
        self.assertEqual(level_from_label("第10关"), 10)
        self.assertEqual(level_from_label("第11关+"), 11)


class LevelWidgetTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk 不可用：{exc}")
        self.root.withdraw()

    def tearDown(self) -> None:
        if hasattr(self, "root"):
            self.root.destroy()

    def test_popup_has_limited_rows_and_draggable_scrollbar(self) -> None:
        selected: list[int] = []
        selector = LevelSelector(
            self.root,
            current_level=10,
            on_select=selected.append,
            visible_rows=6,
        )
        selector.pack()
        self.root.update_idletasks()
        selector.open_popup()
        self.root.update_idletasks()

        self.assertIsNotNone(selector._listbox)
        self.assertIsNotNone(selector._scrollbar)
        self.assertEqual(selector._listbox.size(), len(LEVEL_CHOICES))
        self.assertEqual(int(selector._listbox.cget("height")), 6)
        self.assertEqual(selector._scrollbar.winfo_manager(), "pack")

        selector._move_selection(1)
        selector._confirm_selection()
        self.assertEqual(selected, [11])

    def test_board_view_rebinds_3_middle_and_10_grids(self) -> None:
        state = create_level_state(1)
        view = SonarBoardView(self.root, state.board, state.strategy)
        view.pack()
        self.root.update_idletasks()

        for level, size in ((1, 3), (5, 7), (10, 10)):
            with self.subTest(level=level):
                state = create_level_state(level)
                view.set_models(state.board, state.strategy)
                self.root.update_idletasks()
                self.assertEqual(len(view._cell_items), size * size)
                self.assertIn(f"{size}×{size}", view.info_var.get())
                submarines = ",".join(str(item) for item in state.board.submarines)
                self.assertIn(f"潜艇 [{submarines}]", view.info_var.get())
                self.assertEqual(
                    state.strategy.remaining_submarines,
                    state.board.submarines,
                )
                self.assertIn("已探测 0", view.strategy_var.get())
                self.assertIn("已确认 0", view.strategy_var.get())
                self.assertIn("下一格", view.strategy_var.get())
        view.shutdown()


if __name__ == "__main__":
    unittest.main()
