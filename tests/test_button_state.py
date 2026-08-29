from __future__ import annotations

import unittest
from threading import Lock
from types import SimpleNamespace
from unittest.mock import patch

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
        app.status_var = FakeVar()
        app._restart_button = StatefulButton(
            FakeButton(), toggle_labels(), is_toggle=False
        )
        app._weak_network_button = StatefulButton(
            FakeButton(), toggle_labels(), is_toggle=True
        )
        app._reject_network_button = StatefulButton(
            FakeButton(), toggle_labels(), is_toggle=True
        )
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

        app._auto_loop_bridge = SimpleNamespace(running=False)
        app._refresh_manual_button_locks()
        self.assertEqual(app._restart_button.state, ButtonState.READY)

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
