from __future__ import annotations

import unittest
from unittest.mock import patch

import ui.runtime_context as runtime_context


class RuntimeContextTests(unittest.TestCase):
    def test_device_switch_preserves_board_and_strategy(self) -> None:
        board = object()
        strategy = object()

        with (
            patch.object(
                runtime_context,
                "AdbController",
                side_effect=lambda serial: ("adb", serial),
            ),
            patch.object(
                runtime_context,
                "NetworkController",
                side_effect=lambda adb: ("network", adb),
            ),
            patch.object(
                runtime_context,
                "PageController",
                side_effect=lambda adb: ("page", adb),
            ),
            patch.object(
                runtime_context,
                "GameController",
                side_effect=lambda adb, network: (
                    "game",
                    adb,
                    network,
                ),
            ),
        ):
            original = runtime_context.AppRuntimeContext.create(
                serial="device-a",
                board=board,
                strategy=strategy,
            )
            switched = original.with_device(
                "device-b"
            )

        self.assertIs(switched.board, board)
        self.assertIs(switched.strategy, strategy)
        self.assertEqual(
            switched.adb,
            ("adb", "device-b"),
        )


if __name__ == "__main__":
    unittest.main()
