from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from flows.auto_probe_flow import (
    is_conclusive_recognition_state,
    is_hit_recognition_state,
)


class RecognitionStateRuleTest(unittest.TestCase):
    def test_hit_is_hit(self) -> None:
        self.assertTrue(
            is_hit_recognition_state("hit")
        )

    def test_miss_is_miss(self) -> None:
        self.assertFalse(
            is_hit_recognition_state("miss")
        )

    def test_unopened_is_not_hit_or_conclusive(self) -> None:
        self.assertFalse(
            is_hit_recognition_state("unopened")
        )
        self.assertFalse(
            is_conclusive_recognition_state("unopened")
        )

    def test_unknown_is_not_hit_or_conclusive(self) -> None:
        self.assertFalse(
            is_hit_recognition_state("unknown")
        )
        self.assertFalse(
            is_conclusive_recognition_state("unknown")
        )

    def test_hit_and_miss_are_conclusive(self) -> None:
        self.assertTrue(
            is_conclusive_recognition_state("hit")
        )
        self.assertTrue(
            is_conclusive_recognition_state("miss")
        )

    def test_rule_is_case_insensitive(self) -> None:
        self.assertTrue(
            is_hit_recognition_state(" HIT ")
        )


if __name__ == "__main__":
    unittest.main()
