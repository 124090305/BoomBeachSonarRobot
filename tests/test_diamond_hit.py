from __future__ import annotations

import unittest

import cv2
import numpy as np

from vision.diamond_hit import (
    DiamondHitConfig,
    classify_diamond_hit,
    diamond_points,
    make_diamond_mask,
    majority_cell_state,
)


_CENTER = (100, 100)


def synthetic_pair(draw_after=None):
    before = np.zeros((200, 200, 3), dtype=np.uint8)
    before[:] = (180, 100, 30)
    after = before.copy()
    diamond = make_diamond_mask(
        after.shape[:2],
        _CENTER,
        80,
        56,
        1.0,
    )
    after[diamond > 0] = (90, 45, 20)
    if draw_after is not None:
        draw_after(after)
    return before, after


def classify_synthetic(draw_after=None):
    before, after = synthetic_pair(draw_after)
    return classify_diamond_hit(
        before,
        after,
        _CENTER,
        DiamondHitConfig(
            search_radius=6,
            debug=False,
        ),
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


class DiamondHitClassificationTest(unittest.TestCase):
    def test_plain_miss(self) -> None:
        result = classify_synthetic()
        self.assertEqual(result.state, "miss")
        self.assertFalse(result.sunk_candidate)

    def test_plain_hit(self) -> None:
        result = classify_synthetic(
            lambda image: cv2.ellipse(
                image,
                _CENTER,
                (18, 9),
                0,
                0,
                360,
                (95, 95, 95),
                -1,
            )
        )
        self.assertEqual(result.state, "hit")
        self.assertFalse(result.sunk_candidate)

    def test_symmetric_probes_find_offset_ship_features(self) -> None:
        cases = {
            "up": ((0, -12), (0, -9)),
            "down": ((0, 12), (0, 9)),
            "left": ((-16, 0), (-12, 0)),
            "right": ((16, 0), (12, 0)),
        }
        for name, (offset, expected_probe) in cases.items():
            with self.subTest(name=name):
                dx, dy = offset
                result = classify_synthetic(
                    lambda image, dx=dx, dy=dy: cv2.ellipse(
                        image,
                        (_CENTER[0] + dx, _CENTER[1] + dy),
                        (18, 9),
                        0,
                        0,
                        360,
                        (95, 95, 95),
                        -1,
                    )
                )
                self.assertEqual(result.state, "hit")
                self.assertEqual(result.best_probe_offset, expected_probe)

    def test_near_edge_without_outside_continuity_stays_hit(self) -> None:
        result = classify_synthetic(
            lambda image: cv2.rectangle(
                image,
                (90, 90),
                (129, 110),
                (95, 95, 95),
                -1,
            )
        )
        self.assertEqual(result.state, "hit")
        self.assertFalse(result.sunk_candidate)
        self.assertEqual(result.outside_ship_ratio, 0.0)

    def test_horizontal_cross_boundary_is_sunk_candidate(self) -> None:
        result = classify_synthetic(
            lambda image: cv2.rectangle(
                image,
                (50, 93),
                (150, 107),
                (95, 95, 95),
                -1,
            )
        )
        self.assertTrue(result.sunk_candidate)
        self.assertEqual(result.cross_boundary_direction, "H")

    def test_vertical_cross_boundary_is_sunk_candidate(self) -> None:
        result = classify_synthetic(
            lambda image: cv2.rectangle(
                image,
                (94, 55),
                (106, 145),
                (95, 95, 95),
                -1,
            )
        )
        self.assertTrue(result.sunk_candidate)
        self.assertEqual(result.cross_boundary_direction, "V")


if __name__ == "__main__":
    unittest.main()
