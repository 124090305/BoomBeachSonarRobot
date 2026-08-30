from __future__ import annotations

import unittest
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

from flows.victory_flow import VictoryTransitionError, handle_victory_transition
from sonar_config import ActivityPageConfig
from stop_control import StopRequestedError


class VictoryFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ActivityPageConfig(
            victory_wait_timeout=0.1,
            victory_followup_timeout=0.1,
            next_level_ready_timeout=0.1,
        )

    def test_handles_multiple_victory_pages_and_enters_next_level(self) -> None:
        page = Mock()
        match = SimpleNamespace(center=(1, 1))
        ready = SimpleNamespace(center=(2, 2))
        page.wait_template.side_effect = [match, match, None, ready]

        handled = handle_victory_transition(page, flow_config=self.config)

        self.assertEqual(handled, 2)
        self.assertEqual(page.click_point.call_count, 4)
        self.assertEqual(
            page.wait_template.call_args_list[-1].args[0],
            self.config.quit_activity_template,
        )

    def test_missing_victory_raises_and_never_clicks(self) -> None:
        page = Mock()
        page.wait_template.return_value = None

        with self.assertRaises(VictoryTransitionError):
            handle_victory_transition(page, flow_config=self.config)

        page.click_point.assert_not_called()

    def test_stop_during_victory_wait_propagates(self) -> None:
        page = Mock()
        stop_event = Event()

        def stop_while_waiting(*_args, **_kwargs):
            stop_event.set()
            raise StopRequestedError("stop")

        page.wait_template.side_effect = stop_while_waiting
        with self.assertRaises(StopRequestedError):
            handle_victory_transition(
                page,
                stop_event=stop_event,
                flow_config=self.config,
            )


if __name__ == "__main__":
    unittest.main()
