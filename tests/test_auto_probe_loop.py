from __future__ import annotations

import unittest
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flows.auto_probe_loop import run_auto_probe_loop
from flows.sonar_page import SonarPageState


class FakeStrategy:
    def __init__(self, *, done: bool = False) -> None:
        self.done = done


def probe_result(
    *,
    hit: bool,
    cell: tuple[int, int],
) -> SimpleNamespace:
    return SimpleNamespace(
        hit=hit,
        context=SimpleNamespace(cell=cell),
        next_cell=(cell[0], cell[1] + 1),
    )


class AutoProbeLoopTests(unittest.TestCase):
    def test_pre_requested_stop_runs_zero_rounds(self) -> None:
        stop_event = Event()
        stop_event.set()

        with patch(
            "flows.auto_probe_loop.run_auto_probe_once"
        ) as run_once:
            summary = run_auto_probe_loop(
                adb=object(),
                page=object(),
                network=object(),
                board=object(),
                strategy=FakeStrategy(),
                stop_event=stop_event,
            )

        run_once.assert_not_called()
        self.assertEqual(summary.rounds, 0)
        self.assertEqual(summary.stop_reason, "requested")

    def test_strategy_done_runs_zero_rounds(self) -> None:
        with patch(
            "flows.auto_probe_loop.run_auto_probe_once"
        ) as run_once:
            summary = run_auto_probe_loop(
                adb=object(),
                page=object(),
                network=object(),
                board=object(),
                strategy=FakeStrategy(done=True),
            )

        run_once.assert_not_called()
        self.assertEqual(summary.rounds, 0)
        self.assertEqual(summary.stop_reason, "strategy_done")

    def test_max_rounds_keeps_hit_miss_statistics(self) -> None:
        results = [
            probe_result(hit=True, cell=(0, 0)),
            probe_result(hit=False, cell=(0, 1)),
        ]

        with patch(
            "flows.auto_probe_loop.run_auto_probe_once",
            side_effect=results,
        ):
            summary = run_auto_probe_loop(
                adb=object(),
                page=object(),
                network=object(),
                board=object(),
                strategy=FakeStrategy(),
                max_rounds=2,
            )

        self.assertEqual(summary.rounds, 2)
        self.assertEqual(summary.hits, 1)
        self.assertEqual(summary.misses, 1)
        self.assertEqual(summary.stop_reason, "max_rounds")

    def test_stop_requested_by_round_callback_stops_next_round(self) -> None:
        stop_event = Event()

        def request_stop(_index, _result) -> None:
            stop_event.set()

        with patch(
            "flows.auto_probe_loop.run_auto_probe_once",
            return_value=probe_result(
                hit=False,
                cell=(0, 0),
            ),
        ) as run_once:
            summary = run_auto_probe_loop(
                adb=object(),
                page=object(),
                network=object(),
                board=object(),
                strategy=FakeStrategy(),
                stop_event=stop_event,
                on_round=request_stop,
            )

        run_once.assert_called_once()
        self.assertEqual(summary.rounds, 1)
        self.assertEqual(summary.stop_reason, "requested")

    def test_recoverable_error_restarts_and_continues(self) -> None:
        expected = probe_result(
            hit=False,
            cell=(0, 0),
        )
        game = Mock()
        network = Mock()
        network.get_state.return_value = SimpleNamespace(
            weak_enabled=True,
            reject_enabled=False,
        )
        board = object()
        strategy = FakeStrategy()
        attempt = 0

        def fail_after_click_then_continue(
            *_args,
            **kwargs,
        ):
            nonlocal attempt
            progress = kwargs["progress"]

            if attempt == 0:
                attempt += 1
                progress.probe.cell = (0, 0)
                progress.probe.screen_point = (10, 20)
                progress.probe.before_path = Path("before.png")
                progress.probe.after_path = Path("after.png")
                progress.probe.click_committed = True
                raise RuntimeError("点击后页面识别异常")

            self.assertFalse(
                progress.probe.click_committed
            )
            self.assertIsNone(progress.probe.cell)
            return expected

        with (
            patch(
                "flows.auto_probe_loop.run_auto_probe_once",
                side_effect=fail_after_click_then_continue,
            ) as run_once,
            patch(
                "flows.auto_probe_exception_recovery.ensure_auto_probe_ready"
            ) as ensure_ready,
            patch(
                "flows.auto_probe_exception_recovery.detect_sonar_page_state",
                return_value=SonarPageState.ACTIVITY_DETAIL,
            ),
        ):
            summary = run_auto_probe_loop(
                adb=object(),
                page=object(),
                network=network,
                board=board,
                strategy=strategy,
                game=game,
                max_rounds=1,
            )

        self.assertEqual(run_once.call_count, 2)
        game.restart_game.assert_called_once_with()
        ensure_ready.assert_called_once()
        self.assertIs(
            run_once.call_args_list[0].kwargs["board"],
            board,
        )
        self.assertIs(
            run_once.call_args_list[1].kwargs["strategy"],
            strategy,
        )
        self.assertEqual(summary.rounds, 1)
        self.assertEqual(summary.misses, 1)
        self.assertEqual(summary.stop_reason, "max_rounds")

    def test_three_restart_failures_restore_network_and_stop(self) -> None:
        game = Mock()
        game.restart_game.side_effect = RuntimeError(
            "重启失败"
        )
        network = Mock()
        network.get_state.return_value = SimpleNamespace(
            weak_enabled=False,
            reject_enabled=False,
        )

        with patch(
            "flows.auto_probe_loop.run_auto_probe_once",
            side_effect=RuntimeError("retry 超时"),
        ) as run_once:
            summary = run_auto_probe_loop(
                adb=object(),
                page=object(),
                network=network,
                board=object(),
                strategy=FakeStrategy(),
                game=game,
            )

        run_once.assert_called_once()
        self.assertEqual(game.restart_game.call_count, 3)
        network.restore_network.assert_called_once_with()
        network.get_state.assert_called_once_with()
        self.assertEqual(summary.rounds, 0)
        self.assertEqual(summary.stop_reason, "recovery_failed")


if __name__ == "__main__":
    unittest.main()
