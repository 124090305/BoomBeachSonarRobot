from __future__ import annotations

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flows.auto_probe_loop import run_auto_probe_loop
from stop_control import StopRequestedError


class ActiveStrategy:
    done = False


class RequestedStopLoopTests(unittest.TestCase):
    def test_committed_result_reaches_ui_and_summary_before_stop(self) -> None:
        stop_event = threading.Event()
        committed = SimpleNamespace(
            hit=True
        )
        on_result = Mock()

        def commit_then_stop(*_args, **kwargs):
            kwargs["on_result_committed"](
                committed
            )
            stop_event.set()
            raise StopRequestedError(
                "结果登记后停止"
            )

        with patch(
            "flows.auto_probe_loop.run_auto_probe_once",
            side_effect=commit_then_stop,
        ):
            summary = run_auto_probe_loop(
                adb=object(),
                page=object(),
                network=Mock(),
                board=object(),
                strategy=ActiveStrategy(),
                stop_event=stop_event,
                on_result=on_result,
            )

        self.assertEqual(summary.rounds, 1)
        self.assertEqual(summary.hits, 1)
        self.assertEqual(summary.misses, 0)
        self.assertEqual(
            summary.stop_reason,
            "requested",
        )
        on_result.assert_called_once_with(
            1,
            committed,
        )

    def test_requested_stop_does_not_restart_or_change_network(self) -> None:
        stop_event = threading.Event()
        game = Mock()
        network = Mock()

        def fail_when_stop_arrives(*_args, **_kwargs):
            stop_event.set()
            raise RuntimeError("页面异常")

        with patch(
            "flows.auto_probe_loop.run_auto_probe_once",
            side_effect=fail_when_stop_arrives,
        ):
            summary = run_auto_probe_loop(
                adb=object(),
                page=object(),
                network=network,
                board=object(),
                strategy=ActiveStrategy(),
                game=game,
                stop_event=stop_event,
            )

        self.assertEqual(
            summary.stop_reason,
            "requested",
        )
        game.restart_game.assert_not_called()
        network.restore_network.assert_not_called()
        network.enable_weak_network.assert_not_called()
        network.disable_weak_network.assert_not_called()
        network.enable_reject_network.assert_not_called()
        network.disable_reject_network.assert_not_called()

    def test_stop_while_reentering_after_restart_uses_one_restart(self) -> None:
        stop_event = threading.Event()
        game = Mock()
        network = Mock()

        def stop_during_ready(*_args, **_kwargs):
            stop_event.set()
            raise StopRequestedError(
                "重新进入活动时停止"
            )

        with (
            patch(
                "flows.auto_probe_loop.run_auto_probe_once",
                side_effect=RuntimeError("页面识别异常"),
            ),
            patch(
                "flows.auto_probe_exception_recovery.ensure_auto_probe_ready",
                side_effect=stop_during_ready,
            ) as ensure_ready,
        ):
            summary = run_auto_probe_loop(
                adb=object(),
                page=object(),
                network=network,
                board=object(),
                strategy=ActiveStrategy(),
                game=game,
                stop_event=stop_event,
            )

        self.assertEqual(
            summary.stop_reason,
            "requested",
        )
        game.restart_game.assert_called_once_with(
            stop_event=stop_event,
        )
        ensure_ready.assert_called_once()
        network.restore_network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
