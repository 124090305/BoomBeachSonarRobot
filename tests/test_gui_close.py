from __future__ import annotations

import queue
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ui.gui_app import BoomBeachSonarApp


class GuiCloseTests(unittest.TestCase):
    def test_close_waits_for_cleanup_and_only_main_thread_schedules_tk(self) -> None:
        app = object.__new__(BoomBeachSonarApp)
        app._closing = False
        app._manual_recognition_stop = threading.Event()
        app._close_results = queue.Queue()
        app.status_var = SimpleNamespace(set=Mock())
        app._write_log = Mock()
        app._cancel_regular_after_callbacks = Mock()
        app.board_view = SimpleNamespace(shutdown=Mock())
        app._log_handler = object()
        app.destroy = Mock()
        release = threading.Event()
        cleanup_finished = threading.Event()
        request_stop = Mock()

        def shutdown_and_restore_network() -> None:
            release.wait(1.0)
            cleanup_finished.set()

        app._auto_loop_bridge = SimpleNamespace(
            request_stop=request_stop,
            shutdown_and_restore_network=shutdown_and_restore_network,
        )
        callbacks: list[object] = []
        after_threads: list[str] = []

        def after(_delay, callback):
            after_threads.append(threading.current_thread().name)
            callbacks.append(callback)
            return f"after-{len(callbacks)}"

        app.after = after

        with patch("ui.gui_app.detach_log_handler") as detach:
            app.on_close()
            self.assertTrue(app._manual_recognition_stop.is_set())
            request_stop.assert_called_once_with()
            app.board_view.shutdown.assert_called_once_with()
            app.destroy.assert_not_called()

            release.set()
            self.assertTrue(cleanup_finished.wait(1.0))
            deadline = time.monotonic() + 1.0
            while app._close_results.empty() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertFalse(app._close_results.empty())
            callbacks.pop(0)()

            app.destroy.assert_called_once_with()
            detach.assert_called_once_with(app._log_handler)

        self.assertEqual(after_threads, [threading.current_thread().name])


if __name__ == "__main__":
    unittest.main()
