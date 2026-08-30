from __future__ import annotations

import unittest
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sonar import CellState, CheckerboardHuntStrategy, SonarBoard

from ui.button_state import (
    ButtonLabels,
    ButtonState,
    StatefulButton,
)
from ui.gui_app import BoomBeachSonarApp


class FakeButton:
    def __init__(self) -> None:
        self.options: dict[str, object] = {}

    def configure(self, **kwargs: object) -> None:
        self.options.update(kwargs)

    def state(self, states: list[str]) -> None:
        self.options["ttk_state"] = tuple(states)

    def pack(self, **kwargs: object) -> None:
        self.options["packed"] = kwargs

    def pack_forget(self) -> None:
        self.options["packed"] = False


class FakeVar:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class ImmediateThread:
    def __init__(self, *, target, daemon: bool) -> None:
        self.target = target
        self.daemon = daemon

    def start(self) -> None:
        self.target()


def toggle_labels() -> ButtonLabels:
    return ButtonLabels(
        ready="开启",
        active="关闭",
        busy_on="正在开启…",
        busy_off="正在关闭…",
        locked="不可中断",
        error="状态未知",
    )


class StatefulButtonTests(unittest.TestCase):
    def test_busy_toggle_rejects_repeated_click_until_real_completion(self) -> None:
        widget = FakeButton()
        button = StatefulButton(
            widget,
            toggle_labels(),
            is_toggle=True,
        )

        self.assertTrue(button.begin())
        self.assertEqual(button.state, ButtonState.BUSY)
        self.assertEqual(widget.options["text"], "正在开启…")
        self.assertEqual(widget.options["state"], "disabled")
        self.assertEqual(widget.options["relief"], "sunken")
        self.assertIsNone(button.begin())
        button.complete_toggle(True)
        self.assertEqual(button.state, ButtonState.ACTIVE)
        self.assertEqual(widget.options["text"], "关闭")
        self.assertEqual(widget.options["background"], "#c92a2a")


class GuiButtonIntegrationTests(unittest.TestCase):
    def build_app_shell(self) -> tuple[BoomBeachSonarApp, list[Exception]]:
        app = object.__new__(BoomBeachSonarApp)
        app._runtime = SimpleNamespace(control_lock=Lock())
        app._auto_loop_bridge = SimpleNamespace(running=False)
        app._closing = False
        app._queue_ui_callback = lambda callback: callback()
        app._manual_session = None
        app.status_var = FakeVar()
        app.auto_loop_state_var = FakeVar()
        app.auto_loop_total_var = FakeVar()
        app.auto_loop_last_var = FakeVar()
        app._restart_button = StatefulButton(
            FakeButton(), toggle_labels(), is_toggle=False
        )
        app._weak_network_button = StatefulButton(
            FakeButton(), toggle_labels(), is_toggle=True
        )
        app._reject_network_button = StatefulButton(
            FakeButton(), toggle_labels(), is_toggle=True
        )
        app._manual_intervention_button = StatefulButton(
            FakeButton(), toggle_labels(), is_toggle=True
        )
        app._auto_loop_button = StatefulButton(
            FakeButton(), toggle_labels(), is_toggle=True
        )
        app._apply_device_button = FakeButton()
        app._reset_board_button = FakeButton()
        app.sonar_board = SonarBoard(grid_size=4, submarines=(2,))
        app.sonar_strategy = CheckerboardHuntStrategy(
            app.sonar_board,
        )
        app.board_view = Mock()
        app._manual_edit_toolbar = FakeButton()
        app._manual_undo_button = FakeButton()
        app._manual_redo_button = FakeButton()
        app._manual_apply_button = FakeButton()
        app.after = lambda _delay, callback: callback()
        app._write_log = lambda _message: None
        app._show_success = lambda _message: None
        errors: list[Exception] = []
        app._show_error = errors.append
        return app, errors

    def test_network_toggle_uses_verified_state_after_success(self) -> None:
        app, errors = self.build_app_shell()
        applied: list[str] = []
        app.network = SimpleNamespace(
            get_state=lambda: SimpleNamespace(
                weak_enabled=True,
                reject_enabled=False,
            )
        )
        target = app._weak_network_button.begin()

        with patch("ui.gui_app.threading.Thread", ImmediateThread):
            app._run_network_toggle(
                button=app._weak_network_button,
                target=bool(target),
                apply=lambda: applied.append("enabled"),
                enabled=lambda state: state.weak_enabled,
                success_text="弱网 DROP 已开启",
            )

        self.assertEqual(applied, ["enabled"])
        self.assertEqual(app._weak_network_button.state, ButtonState.ACTIVE)
        self.assertFalse(errors)

    def test_network_toggle_failure_restores_verified_actual_state(self) -> None:
        app, errors = self.build_app_shell()
        app.network = SimpleNamespace(
            get_state=lambda: SimpleNamespace(
                weak_enabled=True,
                reject_enabled=False,
            )
        )
        app._weak_network_button.complete_toggle(True)
        target = app._weak_network_button.begin()

        with patch("ui.gui_app.threading.Thread", ImmediateThread):
            app._run_network_toggle(
                button=app._weak_network_button,
                target=bool(target),
                apply=lambda: (_ for _ in ()).throw(RuntimeError("关闭失败")),
                enabled=lambda state: state.weak_enabled,
                success_text="弱网 DROP 已关闭",
            )

        self.assertEqual(app._weak_network_button.state, ButtonState.ACTIVE)
        self.assertTrue(app._weak_network_button.active)
        self.assertEqual(len(errors), 1)

    def test_running_loop_locks_restart_until_safe_exit(self) -> None:
        app, _errors = self.build_app_shell()
        app._auto_loop_bridge = SimpleNamespace(running=True)

        app._refresh_manual_button_locks()
        self.assertEqual(app._restart_button.state, ButtonState.LOCKED)
        self.assertEqual(
            app._manual_intervention_button.state,
            ButtonState.LOCKED,
        )

        app._auto_loop_bridge = SimpleNamespace(running=False)
        app._refresh_manual_button_locks()
        self.assertEqual(app._restart_button.state, ButtonState.READY)
        self.assertEqual(
            app._manual_intervention_button.state,
            ButtonState.READY,
        )

    def test_idle_app_can_enter_and_exit_manual_intervention(self) -> None:
        app, _errors = self.build_app_shell()

        app._enter_manual_intervention()

        self.assertIsNotNone(app._manual_session)
        self.assertEqual(
            app._manual_intervention_button.state,
            ButtonState.ACTIVE,
        )
        self.assertEqual(app._auto_loop_button.state, ButtonState.LOCKED)
        self.assertEqual(
            app._apply_device_button.options["ttk_state"],
            ("disabled",),
        )
        app.board_view.set_manual_session.assert_called_once()

        app._exit_manual_intervention()

        self.assertIsNone(app._manual_session)
        self.assertEqual(
            app._manual_intervention_button.state,
            ButtonState.READY,
        )
        self.assertEqual(app._auto_loop_button.state, ButtonState.READY)

    def test_apply_manual_changes_keeps_loop_stopped_and_manual_mode_active(self) -> None:
        app, errors = self.build_app_shell()
        app.game = Mock()
        app.network = Mock()
        app.page = Mock()
        app.start_auto_loop = Mock()
        app._enter_manual_intervention()
        app._manual_session.cycle_cell((1, 1))

        app.apply_manual_changes()

        self.assertEqual(app.sonar_board.get_state(1, 1), CellState.HIT)
        self.assertFalse(app._auto_loop_bridge.running)
        self.assertEqual(
            app._manual_intervention_button.state,
            ButtonState.ACTIVE,
        )
        self.assertEqual(app._auto_loop_button.state, ButtonState.LOCKED)
        self.assertFalse(app._manual_session.can_undo)
        app.start_auto_loop.assert_not_called()
        self.assertEqual(app.game.mock_calls, [])
        self.assertEqual(app.network.mock_calls, [])
        self.assertEqual(app.page.mock_calls, [])
        self.assertFalse(errors)

    def test_loop_toggle_dispatches_running_button_to_stop(self) -> None:
        app, _errors = self.build_app_shell()
        request_stop = Mock()
        app._auto_loop_bridge = SimpleNamespace(
            running=True,
            request_stop=request_stop,
        )
        app._auto_loop_button.complete_toggle(True)

        app.toggle_auto_loop()

        request_stop.assert_called_once_with()
        self.assertEqual(app._auto_loop_button.state, ButtonState.BUSY)
        self.assertEqual(app.auto_loop_state_var.value, "停止中")

    def test_exit_manual_mode_has_no_automatic_side_effects(self) -> None:
        app, _errors = self.build_app_shell()
        app.game = Mock()
        app.network = Mock()
        app.page = Mock()
        app._auto_loop_bridge = SimpleNamespace(running=False, start=Mock())
        app._enter_manual_intervention()

        app._exit_manual_intervention()

        self.assertIsNone(app._manual_session)
        self.assertEqual(app._auto_loop_button.state, ButtonState.READY)
        app._auto_loop_bridge.start.assert_not_called()
        self.assertEqual(app.game.mock_calls, [])
        self.assertEqual(app.network.mock_calls, [])
        self.assertEqual(app.page.mock_calls, [])

    def test_user_start_after_manual_exit_keeps_rebuilt_pending_cell(self) -> None:
        app, _errors = self.build_app_shell()
        app._enter_manual_intervention()
        app._manual_session.cycle_cell((1, 1))
        app.apply_manual_changes()
        rebuilt_pending = app.sonar_strategy.pending_cell
        app._exit_manual_intervention()

        class StartingBridge:
            running = False

            def __init__(self) -> None:
                self.start_calls = 0

            def start(self) -> bool:
                self.start_calls += 1
                self.running = True
                return True

        bridge = StartingBridge()
        app._auto_loop_bridge = bridge

        app.toggle_auto_loop()

        self.assertEqual(bridge.start_calls, 1)
        self.assertEqual(app.sonar_strategy.pending_cell, rebuilt_pending)
        self.assertEqual(app._auto_loop_button.state, ButtonState.ACTIVE)

    def test_failed_toggle_reconciles_to_actual_state(self) -> None:
        widget = FakeButton()
        button = StatefulButton(
            widget,
            toggle_labels(),
            is_toggle=True,
        )
        button.complete_toggle(True)

        self.assertFalse(button.begin())
        self.assertEqual(widget.options["text"], "正在关闭…")

        # 关闭指令失败后，后台查询仍显示规则存在。
        button.complete_toggle(True)
        self.assertEqual(button.state, ButtonState.ACTIVE)
        self.assertTrue(button.active)
        self.assertEqual(widget.options["text"], "关闭")

    def test_stop_stays_busy_until_worker_summary_arrives(self) -> None:
        widget = FakeButton()
        button = StatefulButton(
            widget,
            toggle_labels(),
            is_toggle=True,
        )
        button.complete_toggle(True)

        self.assertFalse(button.begin())
        self.assertEqual(button.state, ButtonState.BUSY)
        self.assertEqual(widget.options["text"], "正在关闭…")

        # request_stop 只发送请求，summary 前不允许回到 READY。
        self.assertEqual(button.state, ButtonState.BUSY)
        button.complete_toggle(False)
        self.assertEqual(button.state, ButtonState.READY)
        self.assertEqual(widget.options["text"], "开启")

    def test_action_lock_and_error_have_distinct_visual_states(self) -> None:
        widget = FakeButton()
        button = StatefulButton(
            widget,
            toggle_labels(),
            is_toggle=False,
        )

        button.set_locked(True)
        self.assertEqual(button.state, ButtonState.LOCKED)
        self.assertEqual(widget.options["state"], "disabled")
        self.assertEqual(widget.options["relief"], "sunken")
        self.assertIsNone(button.begin())

        button.set_locked(False)
        self.assertTrue(button.begin())
        button.set_error()
        self.assertEqual(button.state, ButtonState.ERROR)
        self.assertEqual(widget.options["text"], "状态未知")
        self.assertEqual(widget.options["state"], "disabled")
        self.assertIsNone(button.begin())


if __name__ == "__main__":
    unittest.main()
