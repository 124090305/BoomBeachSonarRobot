from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from flows.auto_probe_flow import (
    recognition_state_is_hit,
)


class RecognitionStateRuleTest(unittest.TestCase):
    def test_hit_is_hit(self) -> None:
        self.assertTrue(
            recognition_state_is_hit("hit")
        )

    def test_miss_is_miss(self) -> None:
        self.assertFalse(
            recognition_state_is_hit("miss")
        )

    def test_unopened_is_miss(self) -> None:
        self.assertFalse(
            recognition_state_is_hit("unopened")
        )

    def test_unknown_is_miss(self) -> None:
        self.assertFalse(
            recognition_state_is_hit("unknown")
        )

    def test_rule_is_case_insensitive(self) -> None:
        self.assertTrue(
            recognition_state_is_hit(" HIT ")
        )


if __name__ == "__main__":
    unittest.main()