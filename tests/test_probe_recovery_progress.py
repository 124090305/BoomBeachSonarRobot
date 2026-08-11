from __future__ import annotations

import unittest
from pathlib import Path

from flows.auto_probe_flow import AutoProbeProgress
from flows.probe_flow import (
    ProbeContext,
    ProbeProgress,
)
from sonar import (
    CheckerboardHuntStrategy,
    SonarBoard,
)


def probe_context() -> ProbeContext:
    return ProbeContext(
        cell=(2, 3),
        screen_point=(100, 200),
        before_path=Path("before_restart.png"),
        after_path=Path("after_restart.png"),
    )


class ProbeRecoveryProgressTests(unittest.TestCase):
    def test_restart_before_recognition_resets_temporary_click(self) -> None:
        board = SonarBoard(
            grid_size=4,
            submarines=(2,),
        )
        strategy = CheckerboardHuntStrategy(board)
        pending_cell = strategy.choose_next_cell()

        progress = AutoProbeProgress(
            probe=ProbeProgress(
                cell=pending_cell,
                screen_point=(100, 200),
                before_path=Path("before_restart.png"),
                after_path=Path("after_restart.png"),
                click_committed=True,
                after_captured=False,
            ),
            context=None,
        )

        progress.apply_restart_recovery(object())

        self.assertIsNone(progress.probe.cell)
        self.assertFalse(progress.probe.click_committed)
        self.assertIsNone(progress.context)
        self.assertIsNone(progress.recognition)
        self.assertFalse(progress.result_committed)
        self.assertIsNone(progress.restart_recovery)

        self.assertEqual(strategy.pending_cell, pending_cell)

    def test_recognized_miss_uses_restart_as_recovery(self) -> None:
        restart_recovery = object()
        progress = AutoProbeProgress(
            context=probe_context(),
            recognition=object(),
            hit=False,
        )

        progress.apply_restart_recovery(
            restart_recovery
        )

        self.assertIs(
            progress.restart_recovery,
            restart_recovery,
        )
        self.assertFalse(progress.hit_replay_required)

    def test_recognized_hit_requires_replay_after_restart(self) -> None:
        progress = AutoProbeProgress(
            context=probe_context(),
            recognition=object(),
            hit=True,
        )

        progress.apply_restart_recovery(object())

        self.assertTrue(progress.hit_replay_required)
        self.assertIsNone(progress.restart_recovery)


if __name__ == "__main__":
    unittest.main()
