from __future__ import annotations

import unittest

from sonar_config import DEFAULT_LEVEL_CONFIG, get_level_config


class LevelConfigurationTests(unittest.TestCase):
    def test_early_and_boundary_level_configs(self) -> None:
        expected = {
            1: (3, (3,)),
            5: (7, (2, 3, 3, 4)),
            10: (10, (2, 2, 3, 4, 4, 5)),
            11: (10, (2, 2, 3, 4, 5)),
        }
        for level, (grid_size, submarines) in expected.items():
            with self.subTest(level=level):
                config = get_level_config(level)
                self.assertEqual(config.grid_size, grid_size)
                self.assertEqual(config.submarines, submarines)
                self.assertIsNotNone(config.board_quad)

    def test_levels_after_11_reuse_11_plus_config(self) -> None:
        level_11 = get_level_config(11)
        for level in (12, 20, 50):
            with self.subTest(level=level):
                self.assertEqual(get_level_config(level), level_11)
                self.assertEqual(get_level_config(level), DEFAULT_LEVEL_CONFIG)


if __name__ == "__main__":
    unittest.main()
