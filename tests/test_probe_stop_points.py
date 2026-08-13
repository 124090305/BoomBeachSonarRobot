from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

import flows.auto_probe_flow as auto_probe_flow
import flows.probe_flow as probe_flow
from flows.probe_flow import ProbeContext, ProbeProgress
from sonar import (
    CellState,
    CheckerboardHuntStrategy,
    SonarBoard,
)
from stop_control import StopRequestedError
from vision import DiamondHitResult


class ScreenshotStopAdb:
    def __init__(self, stop_event: threading.Event) -> None:
        self.stop_event = stop_event
        self.screenshot_count = 0

    def ensure_device_online(self) -> None:
        return None

    def take_screenshot(self, path: Path) -> Path:
        self.screenshot_count += 1

        if self.screenshot_count == 2:
            self.stop_event.set()

        return Path(path)


class ProbePage:
    def click_point(
        self,
        _x: int,
        _y: int,
        *,
        after_click=None,
        **_kwargs,
    ) -> None:
        if after_click is not None:
            after_click()

    def click_template(self, *_args, **_kwargs):
        return type(
            "Match",
            (),
            {
                "center": (10, 20),
                "score": 0.95,
            },
        )()


class ProbeBoard:
    has_complete_mapping = True

    @staticmethod
    def screen_point(
        _row: int,
        _col: int,
    ) -> tuple[int, int]:
        return 100, 200


class ProbeStrategy:
    pending_cell = (0, 0)

    @staticmethod
    def choose_next_cell() -> tuple[int, int]:
        return 0, 0


class RecognitionAdb:
    @staticmethod
    def read_image(_path: Path) -> np.ndarray:
        return np.zeros(
            (8, 8, 3),
            dtype=np.uint8,
        )


def hit_recognition() -> DiamondHitResult:
    return DiamondHitResult(
        state="hit",
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


class ProbeStopPointTests(unittest.TestCase):
    def test_stop_after_after_screenshot_keeps_capture_checkpoint(self) -> None:
        stop_event = threading.Event()
        adb = ScreenshotStopAdb(
            stop_event
        )
        progress = ProbeProgress()

        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(
                    probe_flow,
                    "wait_activity_detail_ready",
                    return_value=True,
                ),
                patch.object(
                    probe_flow,
                    "reenter_activity_for_probe",
                ),
            ):
                with self.assertRaises(StopRequestedError):
                    probe_flow.prepare_probe_once(
                        adb=adb,
                        page=ProbePage(),
                        board=ProbeBoard(),
                        strategy=ProbeStrategy(),
                        output_dir=temp_dir,
                        progress=progress,
                        stop_event=stop_event,
                    )

        self.assertEqual(
            adb.screenshot_count,
            2,
        )
        self.assertTrue(
            progress.click_committed
        )
        self.assertTrue(
            progress.after_captured
        )
        self.assertIsNotNone(
            progress.after_path
        )

    def test_stop_during_recognition_still_commits_board_result(self) -> None:
        stop_event = threading.Event()
        board = SonarBoard(
            grid_size=4,
            submarines=(2,),
        )
        strategy = CheckerboardHuntStrategy(
            board
        )
        cell = strategy.choose_next_cell()
        self.assertEqual(cell, (0, 0))

        context = ProbeContext(
            cell=cell,
            screen_point=(10, 20),
            before_path=Path("before.png"),
            after_path=Path("after.png"),
        )
        progress = auto_probe_flow.AutoProbeProgress()
        on_result_committed = Mock()

        def classify_and_request_stop(*_args, **_kwargs):
            stop_event.set()
            return hit_recognition()

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
                side_effect=classify_and_request_stop,
            ),
            patch.object(
                auto_probe_flow,
                "recover_after_hit_once",
            ) as hit_recovery,
            patch.object(
                auto_probe_flow,
                "recover_after_miss_once",
            ) as miss_recovery,
        ):
            with self.assertRaises(StopRequestedError):
                auto_probe_flow.run_auto_probe_once(
                    adb=RecognitionAdb(),
                    page=object(),
                    network=object(),
                    board=board,
                    strategy=strategy,
                    progress=progress,
                    stop_event=stop_event,
                    on_result_committed=on_result_committed,
                )

        self.assertTrue(
            progress.result_committed
        )
        self.assertEqual(
            board.get_state(0, 0),
            CellState.HIT,
        )
        self.assertIsNone(
            strategy.pending_cell
        )
        on_result_committed.assert_called_once()
        committed = on_result_committed.call_args.args[0]
        self.assertEqual(
            committed.context.cell,
            (0, 0),
        )
        self.assertTrue(
            committed.hit
        )
        hit_recovery.assert_not_called()
        miss_recovery.assert_not_called()


if __name__ == "__main__":
    unittest.main()
