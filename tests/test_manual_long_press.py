from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sonar import CellState, ManualEditSession, SonarBoard
from ui.board_view import SonarBoardView


class FakeCanvas:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.ovals: list[tuple] = []
        self.arcs: list[tuple] = []

    def delete(self, tag: str) -> None:
        self.deleted.append(tag)

    def create_oval(self, *args, **kwargs) -> None:
        self.ovals.append((args, kwargs))

    def create_arc(self, *args, **kwargs) -> None:
        self.arcs.append((args, kwargs))


class ManualLongPressTests(unittest.TestCase):
    def build_view(self):
        board = SonarBoard(grid_size=4, submarines=(2,))
        session = ManualEditSession(board)
        session.cycle_cell((0, 0))
        session.cycle_cell((0, 1))
        view = object.__new__(SonarBoardView)
        view._manual_session = session
        view._manual_message = Mock()
        view._press_cell = None
        view._press_position = None
        view._press_started_at = 0.0
        view._long_press_after_id = None
        view._long_press_triggered = False
        view._selection_origin = None
        view._candidate_cells = ()
        view._candidate_error = None
        view._hover_cell = None
        view.hover_var = SimpleNamespace(set=lambda _value: None)
        view.canvas = FakeCanvas()
        callbacks: list[object] = []
        cancelled: list[str] = []

        def after(_delay, callback):
            callbacks.append(callback)
            return "timer-1"

        view.after = after
        view.after_cancel = cancelled.append
        view.refresh = Mock()
        view._cell_at = lambda _x, _y: (0, 0)
        return view, session, callbacks, cancelled

    def test_release_before_one_second_runs_single_click_only(self) -> None:
        view, session, callbacks, cancelled = self.build_view()
        event = SimpleNamespace(x=10, y=20)
        with patch("ui.board_view.time.monotonic", side_effect=(0.0, 0.0)):
            view._on_button_press(event)

        self.assertTrue(callbacks)
        self.assertTrue(view.canvas.arcs)
        view._on_button_release(event)

        self.assertEqual(session.state_at((0, 0)), CellState.MISS)
        self.assertEqual(cancelled, ["timer-1"])

    def test_full_long_press_selects_ship_without_extra_click(self) -> None:
        view, session, callbacks, _cancelled = self.build_view()
        event = SimpleNamespace(x=10, y=20)
        with patch("ui.board_view.time.monotonic", side_effect=(0.0, 0.0)):
            view._on_button_press(event)
        with patch("ui.board_view.time.monotonic", return_value=1.01):
            callbacks[-1]()

        view._cell_at = lambda _x, _y: (0, 1)
        view._on_button_drag(SimpleNamespace(x=30, y=20))
        view._on_button_release(SimpleNamespace(x=30, y=20))

        self.assertEqual(session.state_at((0, 0)), CellState.SUNK)
        self.assertEqual(session.state_at((0, 1)), CellState.SUNK)
        self.assertEqual(len(session.confirmed_ships), 1)

    def test_mouse_leave_cleans_ring_timer_and_candidate(self) -> None:
        view, _session, _callbacks, cancelled = self.build_view()
        event = SimpleNamespace(x=10, y=20)
        with patch("ui.board_view.time.monotonic", side_effect=(0.0, 0.0)):
            view._on_button_press(event)

        view._on_mouse_leave(event)

        self.assertEqual(cancelled, ["timer-1"])
        self.assertIsNone(view._press_cell)
        self.assertIn("manual-hold-progress", view.canvas.deleted)

    def test_ring_position_follows_pointer_before_long_press(self) -> None:
        view, _session, callbacks, _cancelled = self.build_view()
        with patch("ui.board_view.time.monotonic", side_effect=(0.0, 0.0)):
            view._on_button_press(SimpleNamespace(x=10, y=20))
        view._on_button_drag(SimpleNamespace(x=35, y=45))

        with patch("ui.board_view.time.monotonic", return_value=0.5):
            callbacks[-1]()

        bounds = view.canvas.ovals[-1][0]
        self.assertEqual(bounds, (17, 27, 53, 63))

    def test_long_press_sunk_cancels_whole_ship_as_one_action(self) -> None:
        board = SonarBoard(grid_size=4, submarines=(2,))
        board.mark_sunk(((1, 1), (1, 2)))
        session = ManualEditSession(board)
        view, _unused, callbacks, _cancelled = self.build_view()
        view._manual_session = session
        view._cell_at = lambda _x, _y: (1, 2)

        with patch("ui.board_view.time.monotonic", side_effect=(0.0, 0.0)):
            view._on_button_press(SimpleNamespace(x=10, y=20))
        with patch("ui.board_view.time.monotonic", return_value=1.01):
            callbacks[-1]()
        view._on_button_release(SimpleNamespace(x=10, y=20))

        self.assertEqual(session.state_at((1, 1)), CellState.HIT)
        self.assertEqual(session.state_at((1, 2)), CellState.HIT)
        self.assertTrue(session.undo())
        self.assertEqual(session.state_at((1, 1)), CellState.SUNK)

    def test_board_shutdown_cancels_poll_and_long_press_callbacks(self) -> None:
        view, _session, _callbacks, cancelled = self.build_view()
        view._board_poll_after_id = "board-poll"
        view._long_press_after_id = "long-press"

        view.shutdown()

        self.assertEqual(cancelled, ["long-press", "board-poll"])
        self.assertIsNone(view._board_poll_after_id)


if __name__ == "__main__":
    unittest.main()
