from __future__ import annotations

import threading
import time
import unittest

from controllers.page_controller import PageController
from flows.probe_flow import ProbeProgress
from stop_control import (
    StopRequestedError,
    interruptible_wait,
)


class StopDuringClickAdb:
    def __init__(self, stop_event: threading.Event) -> None:
        self.stop_event = stop_event
        self.clicks: list[tuple[int, int]] = []

    def click(self, x: int, y: int) -> None:
        self.clicks.append((x, y))
        self.stop_event.set()


class StopControlTests(unittest.TestCase):
    def test_normal_wait_stops_promptly(self) -> None:
        stop_event = threading.Event()
        timer = threading.Timer(
            0.02,
            stop_event.set,
        )
        timer.start()
        started = time.monotonic()

        try:
            with self.assertRaises(StopRequestedError):
                interruptible_wait(
                    2.0,
                    stop_event,
                    poll_interval=0.005,
                )
        finally:
            timer.cancel()

        self.assertLess(
            time.monotonic() - started,
            0.5,
        )

    def test_target_click_marks_committed_before_stopping(self) -> None:
        stop_event = threading.Event()
        adb = StopDuringClickAdb(
            stop_event
        )
        page = PageController(adb)
        progress = ProbeProgress()

        with self.assertRaises(StopRequestedError):
            page.click_point(
                100,
                200,
                wait_seconds=1.0,
                after_click=progress.mark_click_committed,
                stop_event=stop_event,
            )

        self.assertEqual(
            adb.clicks,
            [(100, 200)],
        )
        self.assertTrue(
            progress.click_committed
        )


if __name__ == "__main__":
    unittest.main()
