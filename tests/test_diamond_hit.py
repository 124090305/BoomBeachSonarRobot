from __future__ import annotations

import unittest

import numpy as np

from vision.diamond_hit import (
    diamond_points,
    make_diamond_mask,
    majority_cell_state,
)


class DiamondHitHelpersTest(unittest.TestCase):
    def test_majority_vote(self) -> None:
        self.assertEqual(
            majority_cell_state(
                ["miss", "hit", "hit"]
            ),
            "hit",
        )

    def test_tie_uses_priority(self) -> None:
        self.assertEqual(
            majority_cell_state(
                ["miss", "hit"]
            ),
            "hit",
        )

    def test_empty_vote_is_unknown(self) -> None:
        self.assertEqual(
            majority_cell_state([]),
            "unknown",
        )

    def test_diamond_points(self) -> None:
        points = diamond_points(
            (50, 40),
            80,
            56,
        )
        expected = np.array(
            [
                [50, 12],
                [90, 40],
                [50, 68],
                [10, 40],
            ],
            dtype=np.int32,
        )
        np.testing.assert_array_equal(
            points,
            expected,
        )

    def test_mask_contains_center(self) -> None:
        mask = make_diamond_mask(
            (100, 100),
            (50, 50),
            80,
            56,
        )
        self.assertEqual(
            int(mask[50, 50]),
            255,
        )
        self.assertEqual(
            int(mask[0, 0]),
            0,
        )


if __name__ == "__main__":
    unittest.main()
