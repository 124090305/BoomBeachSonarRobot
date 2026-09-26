"""等待型人工判断：持续采图、参考计时、帧绑定与停止边界。"""
from dataclasses import replace
import json
from queue import Queue
from threading import Event, Lock, Thread, current_thread
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import numpy as np

from controllers.page_controller import PageController
from flows.auto_probe_recovery import wait_retry_with_failure_capture
from flows.sonar_page import wait_sonar_ready
from manual_recognition import ManualResultProvider
from sonar_config import AUTO_PROBE_CONFIG
from stop_control import StopRequestedError
from vision.image_match import MatchResult, read_image


class Captures:
    def __init__(self, *, block_second=False, fail_second=False):
        self.calls = []
        self.second_started = Event()
        self.release = Event()
        self.block_second = block_second
        self.fail_second = fail_second
        self.click = Mock()
        self.swipe = Mock()

    def read_screenshot(self):
        self.calls.append((time.monotonic(), current_thread().ident))
        count = len(self.calls)
        if count == 2:
            self.second_started.set()
            if self.block_second and not self.release.wait(3):
                raise RuntimeError("测试未解除截图等待")
            if self.fail_second:
                raise RuntimeError("模拟 ADB 命令超时")
        # 后续帧有新内容且分辨率变化，可暴露误用首帧缩放及坐标范围的问题。
        shape = (30, 40, 3) if count == 1 else (80, 120, 3)
        return np.full(shape, count % 255, np.uint8)


class ManualWaitTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.requests = Queue()
        self.provider = ManualResultProvider(self.requests.put, diagnostic_dir=self.directory.name)
        self.stop = Event()
        self.result = Queue()
        self.control_lock = Lock()

    def start(self, operation, device):
        def worker():
            with self.control_lock:
                try:
                    self.result.put(operation())
                except Exception as exc:
                    self.result.put(exc)
        thread = Thread(target=worker)
        thread.start()

        def cleanup():
            self.stop.set()
            self.provider.cancel()
            device.release.set()
            thread.join(3)
        self.addCleanup(cleanup)
        return thread

    def until(self, predicate):
        deadline = time.monotonic() + 2
        while not predicate():
            if time.monotonic() >= deadline:
                self.fail("后台未到达预期等待位置")
            time.sleep(.005)

    def test_overdue_keeps_refreshing_latest_frame_without_advancing(self):
        device = Captures()
        page = PageController(device, manual_results=self.provider)
        with patch("controllers.page_controller.find_template_with_score", side_effect=AssertionError("自动识别被调用")):
            thread = self.start(lambda: page.wait_and_click("retry1.png", timeout=.025,
                                poll_interval=.02, wait_seconds=0, stop_event=self.stop), device)
            request = self.requests.get(timeout=2)
            self.until(lambda: len(device.calls) >= 5)
            self.assertGreater(time.monotonic() - request.wait_started_at, request.reference_timeout)
            self.assertTrue(self.control_lock.locked())
            self.assertTrue(self.result.empty())
            self.assertTrue(self.requests.empty())  # 一个逻辑请求，只入队一次。
            device.click.assert_not_called()
            frame = self.provider.take_latest_frame()
            self.assertGreaterEqual(frame.number, 4)  # 中间帧被覆盖。
            self.assertTrue(self.provider.mark_displayed(frame))
            with self.assertRaises(ValueError):
                self.provider.submit(request.request_id, value="found", coordinates=(90, 60), frame_id=1)
            self.provider.submit(request.request_id, value="found", coordinates=(90, 60), frame_id=frame.number)
            thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.result.get_nowait().center, (90, 60))
        device.click.assert_called_once_with(90, 60)
        np.testing.assert_array_equal(read_image(self.provider.last_diagnostic_path), frame.image)
        metadata = json.loads(self.provider.last_diagnostic_path.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["frame_id"], frame.number)
        self.assertEqual(metadata["coordinates"], [90, 60])
        self.assertEqual(len({thread_id for _, thread_id in device.calls}), 1)
        # 参考期限前最后一次等待可能缩短，其余刷新均沿用传入间隔。
        self.assertGreaterEqual(device.calls[-1][0] - device.calls[-2][0], .015)

    def test_answer_during_capture_uses_displayed_frame_and_discards_late_frame(self):
        device = Captures(block_second=True)
        page = PageController(device, manual_results=self.provider)
        thread = self.start(lambda: page.wait_and_click("retry1.png", timeout=0,
                            poll_interval=.01, wait_seconds=0, stop_event=self.stop), device)
        request = self.requests.get(timeout=2)
        self.assertTrue(device.second_started.wait(2))
        self.provider.submit(request.request_id, value="found", coordinates=(10, 20), frame_id=1)
        with self.assertRaises(ValueError):
            self.provider.submit(request.request_id, value="timeout", frame_id=1)
        self.assertTrue(thread.is_alive())  # 已接受答案，等待当前 ADB 命令结束。
        device.release.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.result.get_nowait().center, (10, 20))
        self.assertEqual(len(device.calls), 2)
        self.assertIsNone(self.provider.take_latest_frame())
        np.testing.assert_array_equal(read_image(self.provider.last_diagnostic_path), request.images[0])

    def test_cancel_during_capture_discards_frame_or_device_error(self):
        for fails in (False, True):
            with self.subTest(fails=fails):
                self.stop.clear()
                self.provider.begin_run()
                device = Captures(block_second=True, fail_second=fails)
                page = PageController(device, manual_results=self.provider)
                thread = self.start(lambda: page.wait_template("retry1.png", timeout=0,
                                    poll_interval=.01, stop_event=self.stop), device)
                request = self.requests.get(timeout=2)
                self.assertTrue(device.second_started.wait(2))
                self.stop.set()
                self.provider.cancel()
                device.release.set()
                thread.join(2)
                self.assertFalse(thread.is_alive())
                self.assertIsInstance(self.result.get_nowait(), StopRequestedError)
                self.assertIsNone(self.provider.pending)
                self.assertIsNone(self.provider.take_latest_frame())
                self.assertEqual(len(device.calls), 2)
                with self.assertRaises(ValueError):
                    self.provider.submit(request.request_id, value="missing", frame_id=1)

    def test_device_error_without_stop_keeps_original_exception_path(self):
        device = Captures(fail_second=True)
        page = PageController(device, manual_results=self.provider)
        thread = self.start(lambda: page.wait_template("retry1.png", timeout=0,
                            poll_interval=.01, stop_event=self.stop), device)
        self.requests.get(timeout=2)
        thread.join(2)
        self.assertIsInstance(self.result.get_nowait(), RuntimeError)
        self.assertIsNone(self.provider.pending)
        self.assertIsNone(self.provider.take_latest_frame())

    def test_retry_refresh_and_manual_timeout_return_displayed_diagnostic(self):
        device = Captures()
        page = PageController(device, manual_results=self.provider)
        with patch("flows.auto_probe_recovery.AUTO_PROBE_CONFIG", replace(AUTO_PROBE_CONFIG, retry_wait_timeout=0)), \
             patch("flows.auto_probe_recovery.config.PAGE_POLL_INTERVAL", .02), \
             patch("flows.auto_probe_recovery.find_template_with_score", side_effect=AssertionError("自动识别")):
            thread = self.start(lambda: wait_retry_with_failure_capture(device, page=page, stop_event=self.stop), device)
            request = self.requests.get(timeout=2)
            self.until(lambda: len(device.calls) >= 3)
            self.assertTrue(self.result.empty())
            self.provider.submit(request.request_id, value="timeout", frame_id=1)
            thread.join(2)
        match, path = self.result.get_nowait()
        self.assertIsNone(match)
        self.assertEqual(path, self.provider.last_diagnostic_path)
        np.testing.assert_array_equal(read_image(path), request.images[0])

    def test_direct_sonar_wait_preserves_interval_and_has_no_outer_timeout(self):
        device = Captures()
        page = PageController(device, manual_results=self.provider)
        def publish(request):
            if "活动按钮" in request.step:
                self.provider.submit(request.request_id, value="found")
            elif request.wait_started_at is None:
                self.provider.submit(request.request_id, value="missing")
            else:
                self.requests.put(request)
        self.provider.publish = publish
        with patch("flows.sonar_page.config.PAGE_POLL_INTERVAL", .02), \
             patch("controllers.page_controller.interruptible_wait"), \
             patch("flows.sonar_page.find_template_with_score", side_effect=AssertionError("自动识别")):
            thread = self.start(lambda: wait_sonar_ready(page, timeout=0, stop_event=self.stop), device)
            request = self.requests.get(timeout=2)
            self.assertEqual(len(request.templates), 2)
            self.until(lambda: len(device.calls) >= 6)
            self.assertTrue(self.result.empty())
            self.provider.submit(request.request_id, value="missing", frame_id=1)
            thread.join(2)
        self.assertIsNone(self.result.get_nowait())
        device.swipe.assert_called_once()

    def test_single_check_keeps_static_frame(self):
        device = Captures()
        page = PageController(device, manual_results=self.provider)
        thread = self.start(lambda: page.find_template("retry1.png", stop_event=self.stop), device)
        request = self.requests.get(timeout=2)
        self.assertIsNone(request.wait_started_at)
        self.assertFalse(device.second_started.wait(.12))
        self.provider.submit(request.request_id, value="missing", frame_id=1)
        thread.join(2)
        self.assertIsNone(self.result.get_nowait())
        self.assertEqual(len(device.calls), 1)

    def test_normal_mode_still_polls_and_times_out_automatically(self):
        device = Captures()
        page = PageController(device)
        match = MatchResult(.95, (1, 1), (3, 3))
        with patch("controllers.page_controller.find_template_with_score", side_effect=[(None, .1), (match, .95)]) as vision, \
             patch("controllers.page_controller.time.monotonic", side_effect=[10., 10.2]), \
             patch("controllers.page_controller.interruptible_wait") as wait, \
             patch.object(device, "read_screenshot", return_value=np.zeros((30, 40, 3), np.uint8)) as capture:
            self.assertIs(page.wait_template("retry1.png", timeout=1, poll_interval=.3), match)
            self.assertEqual(capture.call_count, 2)
            self.assertEqual(vision.call_count, 2)
            wait.assert_called_once_with(.3, None)
        with patch("controllers.page_controller.find_template_with_score", return_value=(None, .1)), \
             patch("controllers.page_controller.time.monotonic", side_effect=[10., 11.]), \
             patch("controllers.page_controller.interruptible_wait") as wait, \
             patch.object(device, "read_screenshot", return_value=np.zeros((30, 40, 3), np.uint8)):
            self.assertIsNone(page.wait_template("retry1.png", timeout=1))
            wait.assert_not_called()


if __name__ == "__main__":
    unittest.main()
