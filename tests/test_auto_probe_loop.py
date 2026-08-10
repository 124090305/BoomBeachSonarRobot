from __future__ import annotations

import unittest
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

from flows.auto_probe_loop import run_auto_probe_loop


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


if __name__ == "__main__":
    unittest.main()
