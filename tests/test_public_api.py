from __future__ import annotations

import unittest

import flows
from flows import activity_flow, auto_probe_flow, probe_flow, screenshot_flow
from sonar_config import (
    ACTIVITY_PAGE_CONFIG,
    AUTO_PROBE_CONFIG,
    DEFAULT_LEVEL_CONFIG,
    GUI_CONFIG,
)
from ui.gui_app import BoomBeachSonarApp


class PublicApiTests(unittest.TestCase):
    def test_flow_package_exports_formal_entry_points(self) -> None:
        self.assertIs(
            flows.run_auto_probe_once,
            auto_probe_flow.run_auto_probe_once,
        )
        self.assertIs(
            flows.enter_activity_initial,
            activity_flow.enter_activity_initial,
        )
        self.assertIs(
            flows.prepare_probe_once,
            probe_flow.prepare_probe_once,
        )
        self.assertIs(
            flows.run_screenshot_check,
            screenshot_flow.run_screenshot_check,
        )

    def test_formal_config_objects_are_available(self) -> None:
        self.assertEqual(DEFAULT_LEVEL_CONFIG.grid_size, 10)
        self.assertTrue(ACTIVITY_PAGE_CONFIG.activity_button_template)
        self.assertEqual(AUTO_PROBE_CONFIG.max_restart_attempts, 3)
        self.assertGreater(AUTO_PROBE_CONFIG.hit_online_wait_seconds, 0)
        self.assertGreater(GUI_CONFIG.board_view_width, 0)

    def test_gui_uses_descriptive_class_name(self) -> None:
        self.assertEqual(BoomBeachSonarApp.__name__, "BoomBeachSonarApp")


if __name__ == "__main__":
    unittest.main()
