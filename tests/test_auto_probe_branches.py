from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

import flows.auto_probe_flow as auto_probe_flow
from flows.probe_flow import ProbeContext
from vision import DiamondHitResult


class FakeAdb:
    def read_image(self, _path: Path) -> np.ndarray:
        return np.zeros((8, 8, 3), dtype=np.uint8)


class FakeStrategy:
    def __init__(self, *, done_after_report: bool) -> None:
        self.pending_cell = (2, 3)
        self.done = False
        self.done_after_report = done_after_report
        self.reported: tuple[tuple[int, int], bool] | None = None

    def report_result(
        self,
        cell: tuple[int, int],
        hit: bool,
    ) -> tuple[object, ...]:
        self.reported = (cell, hit)
        self.pending_cell = None
        self.done = self.done_after_report
        return ()

    def choose_next_cell(self) -> tuple[int, int] | None:
        if self.done:
            return None

        return (4, 5)


def make_recognition(state: str) -> DiamondHitResult:
    return DiamondHitResult(
        state=state,
        confidence=0.9,
        score=0.9,
        rough_center=(10, 20),
        refined_center=(10, 20),
        changed_ratio=0.2,
        center_gray_ratio=0.9,
        ring_gray_ratio=0.1,
        gray_excess=0.8,
        component_ratio=0.2,
        s_center=20.0,
        s_ring=80.0,
        s_drop=60.0,
        edge_density=0.3,
    )


class AutoProbeRecoveryBranchTests(unittest.TestCase):
    def run_branch(
        self,
        *,
        state: str,
        done_after_report: bool,
    ):
        context = ProbeContext(
            cell=(2, 3),
            screen_point=(10, 20),
            before_path=Path("before.png"),
            after_path=Path("after.png"),
        )
        strategy = FakeStrategy(
            done_after_report=done_after_report
        )
        recovery = object()

        with (
            patch.object(
                auto_probe_flow,
                "ensure_auto_probe_ready",
            ) as ready_mock,
            patch.object(
                auto_probe_flow,
                "prepare_probe_once",
                return_value=context,
            ),
            patch.object(
                auto_probe_flow,
                "classify_diamond_hit",
                return_value=make_recognition(state),
            ),
            patch.object(
                auto_probe_flow,
                "recover_after_hit_once",
                return_value=recovery,
            ) as hit_mock,
            patch.object(
                auto_probe_flow,
                "recover_after_miss_once",
                return_value=recovery,
            ) as miss_mock,
            patch.object(
                auto_probe_flow,
                "_recover_after_strategy_done_once",
                return_value=recovery,
            ) as done_mock,
        ):
            result = auto_probe_flow.run_auto_probe_once(
                adb=FakeAdb(),
                page=object(),
                network=object(),
                board=object(),
                strategy=strategy,
            )

        ready_mock.assert_called_once()
        self.assertEqual(
            strategy.reported,
            ((2, 3), state == "hit"),
        )

        return result, hit_mock, miss_mock, done_mock

    def test_hit_uses_hit_recovery(self) -> None:
        result, hit_mock, miss_mock, done_mock = self.run_branch(
            state="hit",
            done_after_report=False,
        )

        self.assertTrue(result.hit)
        hit_mock.assert_called_once()
        miss_mock.assert_not_called()
        done_mock.assert_not_called()

    def test_miss_uses_retry_recovery(self) -> None:
        result, hit_mock, miss_mock, done_mock = self.run_branch(
            state="miss",
            done_after_report=False,
        )

        self.assertFalse(result.hit)
        hit_mock.assert_not_called()
        miss_mock.assert_called_once()
        done_mock.assert_not_called()

    def test_strategy_done_has_highest_recovery_priority(self) -> None:
        result, hit_mock, miss_mock, done_mock = self.run_branch(
            state="hit",
            done_after_report=True,
        )

        self.assertTrue(result.hit)
        self.assertIsNone(result.next_cell)
        hit_mock.assert_not_called()
        miss_mock.assert_not_called()
        done_mock.assert_called_once()

    def test_unknown_does_not_write_strategy_result(self) -> None:
        context = ProbeContext(
            cell=(2, 3),
            screen_point=(10, 20),
            before_path=Path("before.png"),
            after_path=Path("after.png"),
        )
        strategy = FakeStrategy(
            done_after_report=False
        )

        with (
            patch.object(
                auto_probe_flow,
                "ensure_auto_probe_ready",
            ),
            patch.object(
                auto_probe_flow,
                "prepare_probe_once",
                return_value=context,
            ),
            patch.object(
                auto_probe_flow,
                "classify_diamond_hit",
                return_value=make_recognition("unknown"),
            ),
            patch.object(
                auto_probe_flow,
                "recover_after_hit_once",
            ) as hit_mock,
            patch.object(
                auto_probe_flow,
                "recover_after_miss_once",
            ) as miss_mock,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "识别结果无效",
            ):
                auto_probe_flow.run_auto_probe_once(
                    adb=FakeAdb(),
                    page=object(),
                    network=object(),
                    board=object(),
                    strategy=strategy,
                )

        self.assertIsNone(strategy.reported)
        self.assertEqual(strategy.pending_cell, (2, 3))
        hit_mock.assert_not_called()
        miss_mock.assert_not_called()

    def test_recognized_hit_is_replayed_after_restart(self) -> None:
        context = ProbeContext(
            cell=(2, 3),
            screen_point=(10, 20),
            before_path=Path("before.png"),
            after_path=Path("after.png"),
        )
        strategy = FakeStrategy(
            done_after_report=False
        )
        page = Mock()
        recovery = object()
        progress = auto_probe_flow.AutoProbeProgress(
            context=context,
            recognition=make_recognition("hit"),
            hit=True,
            hit_replay_required=True,
        )

        with (
            patch.object(
                auto_probe_flow,
                "ensure_auto_probe_ready",
            ),
            patch.object(
                auto_probe_flow,
                "prepare_probe_once",
            ) as prepare_mock,
            patch.object(
                auto_probe_flow,
                "classify_diamond_hit",
            ) as classify_mock,
            patch.object(
                auto_probe_flow,
                "recover_after_hit_once",
                return_value=recovery,
            ) as hit_mock,
        ):
            result = auto_probe_flow.run_auto_probe_once(
                adb=FakeAdb(),
                page=page,
                network=object(),
                board=object(),
                strategy=strategy,
                progress=progress,
            )

        prepare_mock.assert_not_called()
        classify_mock.assert_not_called()
        page.click_point.assert_called_once()
        self.assertEqual(
            page.click_point.call_args.args,
            (10, 20),
        )
        hit_mock.assert_called_once()
        self.assertEqual(strategy.reported, ((2, 3), True))
        self.assertTrue(result.hit)


if __name__ == "__main__":
    unittest.main()
