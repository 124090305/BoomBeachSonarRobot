from __future__ import annotations

import unittest
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

from flows.auto_probe_loop import AutoProbeLoopSummary
from flows.level_loop import create_level_state, run_multi_level_loop
from sonar.board import CellState
from stop_control import StopRequestedError


def done_summary(rounds: int = 1) -> AutoProbeLoopSummary:
    return AutoProbeLoopSummary(
        rounds=rounds,
        hits=rounds,
        misses=0,
        stop_reason="strategy_done",
        strategy_done=True,
        last_result=SimpleNamespace(context=SimpleNamespace(cell=(0, 0))),
    )


class LevelLoopTests(unittest.TestCase):
    def test_new_level_has_clean_board_and_strategy(self) -> None:
        old = create_level_state(10)
        old.strategy.choose_next_cell()
        pending = old.strategy.pending_cell
        self.assertIsNotNone(pending)
        old.board.report_result(*pending, hit=True)

        new = create_level_state(11)

        snapshot = new.board.snapshot()
        self.assertTrue(
            all(state in (CellState.UNKNOWN, CellState.SELECTED) for row in snapshot.states for state in row)
        )
        self.assertEqual(new.strategy.get_confirmed_ships(), ())
        self.assertEqual(new.strategy.excluded_cells, frozenset())
        self.assertIsNot(new.board, old.board)
        self.assertIsNot(new.strategy, old.strategy)

    def test_completes_two_virtual_levels_and_increments_level(self) -> None:
        initial = create_level_state(10)
        changed = []

        with (
            patch("flows.level_loop.run_auto_probe_loop", side_effect=[done_summary(), done_summary()]),
            patch("flows.level_loop.handle_victory_transition", return_value=1) as victory,
        ):
            summary = run_multi_level_loop(
                adb=object(),
                page=object(),
                network=object(),
                initial_state=initial,
                on_level_changed=changed.append,
                max_levels=2,
            )

        self.assertEqual(victory.call_count, 2)
        self.assertEqual(summary.completed_levels, 2)
        self.assertEqual(summary.current_level, 11)
        self.assertEqual(summary.rounds, 2)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0].level, 11)
        self.assertIsNot(changed[0].board, initial.board)

    def test_progresses_9_to_12_using_11_plus_config(self) -> None:
        initial = create_level_state(9)
        changed = []

        with (
            patch(
                "flows.level_loop.run_auto_probe_loop",
                side_effect=[
                    done_summary(),
                    done_summary(),
                    done_summary(),
                    done_summary(),
                ],
            ),
            patch("flows.level_loop.handle_victory_transition", return_value=1),
        ):
            summary = run_multi_level_loop(
                adb=object(),
                page=object(),
                network=object(),
                initial_state=initial,
                on_level_changed=changed.append,
                max_levels=4,
            )

        self.assertEqual([state.level for state in changed], [10, 11, 12])
        self.assertEqual(summary.current_level, 12)
        self.assertEqual(
            changed[-1].board.submarines,
            create_level_state(11).board.submarines,
        )

    def test_stop_during_victory_wait_does_not_advance(self) -> None:
        initial = create_level_state(10)
        stop_event = Event()

        def request_stop(*_args, **_kwargs):
            stop_event.set()
            raise StopRequestedError("stop")

        with (
            patch("flows.level_loop.run_auto_probe_loop", return_value=done_summary()),
            patch("flows.level_loop.handle_victory_transition", side_effect=request_stop),
            patch("flows.level_loop.create_level_state") as create_next,
        ):
            summary = run_multi_level_loop(
                adb=object(), page=object(), network=object(),
                initial_state=initial, stop_event=stop_event,
            )

        create_next.assert_not_called()
        self.assertEqual(summary.stop_reason, "requested")
        self.assertEqual(summary.current_level, 10)

    def test_victory_failure_does_not_advance(self) -> None:
        initial = create_level_state(10)
        with (
            patch("flows.level_loop.run_auto_probe_loop", return_value=done_summary()),
            patch("flows.level_loop.handle_victory_transition", side_effect=RuntimeError("no victory")),
            patch("flows.level_loop.create_level_state") as create_next,
        ):
            with self.assertRaisesRegex(RuntimeError, "no victory"):
                run_multi_level_loop(
                    adb=object(), page=object(), network=object(), initial_state=initial,
                )
        create_next.assert_not_called()


if __name__ == "__main__":
    unittest.main()
