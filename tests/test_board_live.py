from __future__ import annotations

import threading
import unittest

import cv2

from sonar_config import GlobalBoardSyncConfig
from stop_control import StopRequestedError
from tests.test_board_recognition import hull, opened, scene
from vision.board_live import recognize_live_board


class LiveBoardRecognitionTests(unittest.TestCase):
    def config(self, **changes):
        values = dict(
            frame_count=3,
            maximum_frame_count=3,
            frame_interval_seconds=0,
            minimum_usable_frames=2,
            minimum_mean_agreement=.95,
            maximum_disagreement_cells=3,
        )
        values.update(changes)
        return GlobalBoardSyncConfig(**values)

    def test_identical_frames_are_stable(self):
        reference, level = scene()
        live = recognize_live_board(
            lambda: reference.copy(),
            level_config=level,
            live_config=self.config(),
            empty_reference=reference,
        )
        self.assertTrue(live.stable)
        self.assertEqual(live.mean_state_agreement, 1.0)
        self.assertEqual(live.board_result.counts["UNKNOWN"], 25)

    def test_single_frame_animation_disagreement_is_reviewed(self):
        reference, level = scene()
        miss = reference.copy()
        opened(miss, level, (2, 2))
        frames = iter((reference.copy(), miss, reference.copy()))
        live = recognize_live_board(
            lambda: next(frames),
            level_config=level,
            live_config=self.config(),
            empty_reference=reference,
        )
        self.assertTrue(live.stable)
        self.assertIn((2, 2), live.disagreement_cells)
        self.assertTrue(live.board_result.cell_at(2, 2).needs_review)

    def test_sunk_segment_requires_multiframe_majority(self):
        reference, level = scene()
        sunk = reference.copy()
        hull(sunk, level, [(2, 1), (2, 2), (2, 3)])
        hit_only = reference.copy()
        for cell in ((2, 1), (2, 2), (2, 3)):
            hull(hit_only, level, [cell])
        frames = iter((sunk.copy(), hit_only, sunk.copy()))
        live = recognize_live_board(
            lambda: next(frames),
            level_config=level,
            live_config=self.config(),
            empty_reference=reference,
        )
        self.assertEqual(live.board_result.counts["SUNK"], 3)
        self.assertEqual(len(live.board_result.sunk_submarines), 1)

        frames = iter((sunk.copy(), hit_only.copy(), hit_only.copy()))
        live = recognize_live_board(
            lambda: next(frames),
            level_config=level,
            live_config=self.config(),
            empty_reference=reference,
        )
        self.assertEqual(live.board_result.counts["SUNK"], 0)

    def test_stop_between_frames_aborts_without_partial_result(self):
        reference, level = scene()
        stop = threading.Event()
        calls = 0

        def capture():
            nonlocal calls
            calls += 1
            stop.set()
            return reference.copy()

        with self.assertRaises(StopRequestedError):
            recognize_live_board(
                capture,
                level_config=level,
                live_config=self.config(),
                empty_reference=reference,
                stop_event=stop,
            )
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
