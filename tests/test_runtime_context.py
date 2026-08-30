from __future__ import annotations

import threading
import unittest
from unittest.mock import patch

import ui.runtime_context as runtime_context
from flows.level_loop import create_level_state


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

    def test_level_switch_preserves_controllers_and_rebuilds_models(self) -> None:
        state = create_level_state(3)
        original = runtime_context.AppRuntimeContext(
            adb=object(),
            network=object(),
            page=object(),
            game=object(),
            board=state.board,
            strategy=state.strategy,
            control_lock=threading.Lock(),
            current_level=3,
        )

        switched = original.with_level(8)

        self.assertIs(switched.adb, original.adb)
        self.assertIs(switched.network, original.network)
        self.assertIs(switched.page, original.page)
        self.assertIs(switched.game, original.game)
        self.assertIs(switched.control_lock, original.control_lock)
        self.assertEqual(switched.current_level, 8)
        self.assertIsNot(switched.board, original.board)
        self.assertIsNot(switched.strategy, original.strategy)


if __name__ == "__main__":
    unittest.main()
