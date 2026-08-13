from __future__ import annotations

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ui.auto_loop_bridge import AutoProbeLoopBridge


def bridge_context():
    return SimpleNamespace(
        adb=object(),
        page=object(),
        network=Mock(),
        board=object(),
        strategy=object(),
        game=object(),
        control_lock=threading.Lock(),
    )


class AutoLoopBridgeTests(unittest.TestCase):
    def test_requested_summary_preserves_network_state(self) -> None:
        context = bridge_context()
        bridge = AutoProbeLoopBridge(
            context
        )
        summary = SimpleNamespace(
            stop_reason="requested"
        )

        with patch(
            "ui.auto_loop_bridge.run_auto_probe_loop",
            return_value=summary,
        ):
            bridge._worker()

        context.network.restore_network.assert_not_called()
        self.assertEqual(
            bridge.get_event_nowait(),
            ("summary", summary),
        )

    def test_close_waits_for_background_before_network_cleanup(self) -> None:
        context = bridge_context()
        bridge = AutoProbeLoopBridge(
            context
        )
        action_started = threading.Event()
        release_action = threading.Event()
        action_finished = threading.Event()
        network_restored = threading.Event()

        def background_action() -> None:
            with context.control_lock:
                action_started.set()
                release_action.wait(1.0)
                action_finished.set()

        def restore_network() -> None:
            self.assertTrue(
                action_finished.is_set()
            )
            network_restored.set()

        context.network.restore_network.side_effect = restore_network
        bridge.thread = threading.Thread(
            target=background_action,
        )
        bridge.thread.start()
        self.assertTrue(
            action_started.wait(1.0)
        )

        close_thread = threading.Thread(
            target=bridge.shutdown_and_restore_network,
        )
        close_thread.start()

        self.assertFalse(
            network_restored.wait(0.05)
        )
        release_action.set()
        self.assertTrue(
            network_restored.wait(1.0)
        )
        close_thread.join(1.0)

        self.assertFalse(
            close_thread.is_alive()
        )
        self.assertTrue(
            bridge.stop_event.is_set()
        )
        context.network.restore_network.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
