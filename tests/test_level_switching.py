from __future__ import annotations

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from flows.level_loop import create_level_state
from sonar import CellState
from ui.gui_app import BoomBeachSonarApp
from ui.runtime_context import AppRuntimeContext


class FakeVar:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class LevelSwitchingTests(unittest.TestCase):
    def build_shell(self, level: int = 3) -> BoomBeachSonarApp:
        app = object.__new__(BoomBeachSonarApp)
        state = create_level_state(level)
        app._runtime = AppRuntimeContext(
            adb=object(),
            network=object(),
            page=object(),
            game=object(),
            board=state.board,
            strategy=state.strategy,
            control_lock=threading.Lock(),
            current_level=level,
        )
        app._bind_runtime(app._runtime)
        app._closing = False
        app._manual_session = None
        app._pending_auto_loop_terminal = None
        app._context_operation_count = 0
        app._auto_loop_bridge = SimpleNamespace(
            running=False,
            set_context=Mock(),
        )
        app.level_selector = SimpleNamespace(
            set_level=Mock(),
            set_enabled=Mock(),
        )
        app.board_view = SimpleNamespace(set_models=Mock())
        app.auto_loop_total_var = FakeVar()
        app.auto_loop_last_var = FakeVar()
        app.status_var = FakeVar()
        app._write_log = Mock()
        app._show_error = Mock()
        return app

    def test_manual_switch_rebuilds_clean_board_strategy_and_ui(self) -> None:
        app = self.build_shell(3)
        old_board = app.sonar_board
        old_strategy = app.sonar_strategy
        old_board.report_result(0, 0, hit=True)
        old_board.report_result(0, 1, hit=False)
        old_board.mark_sunk(((1, 0), (1, 1)))

        app.change_level(8)

        self.assertEqual(app._runtime.current_level, 8)
        self.assertIsNot(app.sonar_board, old_board)
        self.assertIsNot(app.sonar_strategy, old_strategy)
        snapshot = app.sonar_board.snapshot()
        self.assertEqual(snapshot.grid_size, 10)
        self.assertTrue(
            all(
                state in (CellState.UNKNOWN, CellState.SELECTED)
                for row in snapshot.states
                for state in row
            )
        )
        self.assertEqual(app.sonar_strategy.get_confirmed_ships(), ())
        self.assertEqual(
            app.sonar_strategy.remaining_submarines,
            app.sonar_board.submarines,
        )
        app._auto_loop_bridge.set_context.assert_called_once_with(app._runtime)
        app.board_view.set_models.assert_called_once_with(
            app.sonar_board,
            app.sonar_strategy,
        )
        app.level_selector.set_level.assert_called_with(8)

    def test_level_selector_lock_covers_loop_stop_manual_and_context_task(self) -> None:
        app = self.build_shell()
        self.assertTrue(app._level_change_allowed())

        app._auto_loop_bridge.running = True
        self.assertFalse(app._level_change_allowed())
        app._auto_loop_bridge.running = False

        app._pending_auto_loop_terminal = ("summary", object())
        self.assertFalse(app._level_change_allowed())
        app._pending_auto_loop_terminal = None

        app._manual_session = object()
        self.assertFalse(app._level_change_allowed())
        app._manual_session = None

        app._context_operation_count = 1
        self.assertFalse(app._level_change_allowed())
        app._context_operation_count = 0
        self.assertTrue(app._level_change_allowed())

    def test_locked_selector_cannot_change_level(self) -> None:
        app = self.build_shell(4)
        app._auto_loop_bridge.running = True

        app.change_level(8)

        self.assertEqual(app._runtime.current_level, 4)
        app._auto_loop_bridge.set_context.assert_not_called()
        app.level_selector.set_level.assert_called_once_with(4)


if __name__ == "__main__":
    unittest.main()
