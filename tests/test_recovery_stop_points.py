from __future__ import annotations

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flows.auto_probe_exception_recovery import (
    restart_auto_probe_once,
)
from flows.auto_probe_recovery import (
    recover_after_miss_once,
)
from stop_control import StopRequestedError
from vision import MatchResult


class MissNetwork:
    def __init__(
        self,
        stop_event: threading.Event,
        stop_after: str,
    ) -> None:
        self.stop_event = stop_event
        self.stop_after = stop_after
        self.weak_enabled = True
        self.reject_enabled = False
        self.calls: list[str] = []

    def get_state(self):
        return SimpleNamespace(
            weak_enabled=self.weak_enabled,
            reject_enabled=self.reject_enabled,
        )

    def _finish(self, action: str) -> None:
        self.calls.append(action)

        if self.stop_after == action:
            self.stop_event.set()

    def enable_reject_network(self) -> None:
        self.reject_enabled = True
        self._finish("reject_on")

    def disable_reject_network(self) -> None:
        self.reject_enabled = False
        self._finish("reject_off")

    def disable_weak_network(self) -> None:
        self.weak_enabled = False
        self._finish("drop_off")


class MissPage:
    def __init__(
        self,
        stop_event: threading.Event,
        stop_after: str,
    ) -> None:
        self.stop_event = stop_event
        self.stop_after = stop_after
        self.clicks = 0

    def click_match(self, *_args, **_kwargs) -> None:
        self.clicks += 1

        if self.stop_after == "retry_click":
            self.stop_event.set()


class RecoveryStopPointTests(unittest.TestCase):
    def test_miss_recovery_stops_between_network_and_click_steps(self) -> None:
        retry_match = MatchResult(
            score=0.95,
            top_left=(0, 0),
            bottom_right=(20, 20),
        )
        cases = (
            (
                "reject_on",
                True,
                True,
                0,
                ["reject_on"],
            ),
            (
                "reject_off",
                True,
                False,
                0,
                ["reject_on", "reject_off"],
            ),
            (
                "retry_click",
                True,
                False,
                1,
                ["reject_on", "reject_off"],
            ),
            (
                "drop_off",
                False,
                False,
                1,
                ["reject_on", "reject_off", "drop_off"],
            ),
        )

        for (
            stop_after,
            expected_weak,
            expected_reject,
            expected_clicks,
            expected_calls,
        ) in cases:
            with self.subTest(stop_after=stop_after):
                stop_event = threading.Event()
                network = MissNetwork(
                    stop_event,
                    stop_after,
                )
                page = MissPage(
                    stop_event,
                    stop_after,
                )

                with (
                    patch(
                        "flows.auto_probe_recovery.wait_retry_with_failure_capture",
                        return_value=(retry_match, None),
                    ),
                    patch(
                        "flows.auto_probe_recovery.enter_activity_initial",
                    ) as enter_activity,
                ):
                    with self.assertRaises(StopRequestedError):
                        recover_after_miss_once(
                            adb=object(),
                            page=page,
                            network=network,
                            stop_event=stop_event,
                        )

                self.assertEqual(
                    network.weak_enabled,
                    expected_weak,
                )
                self.assertEqual(
                    network.reject_enabled,
                    expected_reject,
                )
                self.assertEqual(
                    page.clicks,
                    expected_clicks,
                )
                self.assertEqual(
                    network.calls,
                    expected_calls,
                )
                enter_activity.assert_not_called()

    def test_restart_game_finishes_before_stop_is_raised(self) -> None:
        stop_event = threading.Event()
        game = Mock()
        game.restart_game.side_effect = stop_event.set

        with patch(
            "flows.auto_probe_exception_recovery.ensure_auto_probe_ready"
        ) as ensure_ready:
            with self.assertRaises(StopRequestedError):
                restart_auto_probe_once(
                    game=game,
                    adb=object(),
                    page=object(),
                    network=object(),
                    attempt=1,
                    max_attempts=3,
                    stop_event=stop_event,
                )

        game.restart_game.assert_called_once_with()
        ensure_ready.assert_not_called()


if __name__ == "__main__":
    unittest.main()
