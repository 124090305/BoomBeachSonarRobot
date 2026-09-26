"""真实 Tk 主窗口、消息队列和后台原循环的联调；ADB/网络使用替身。"""
import time
import gc
import tkinter as tk
import unittest
from threading import Lock
from unittest.mock import Mock, patch

from flows.level_loop import create_level_state
from manual_recognition import manual_provider
from sonar import CellState
from tests.test_manual_trial import Device, Network, fast_flow
from ui.gui_app import BoomBeachSonarApp
from ui.runtime_context import AppRuntimeContext
from controllers.page_controller import PageController


def window_closed(app):
    try:
        return not app.winfo_exists()
    except tk.TclError:
        return True


class ManualTrialGuiTests(unittest.TestCase):
    def setUp(self):
        # 多个 Tk 根窗口的测试遗留循环引用在主线程回收。
        gc.collect()
        self.device, self.network = Device(), Network()
        state = create_level_state(1)
        self.formal = state
        context = AppRuntimeContext(self.device, self.network, PageController(self.device), Mock(),
                                    state.board, state.strategy, Lock(), 1)
        with patch("ui.gui_app.AppRuntimeContext.create", return_value=context):
            try:
                self.app = BoomBeachSonarApp()
            except tk.TclError as exc:
                self.skipTest(str(exc))
        self.app.withdraw()
        self.pump(lambda: self.app._level_change_allowed())
        self.toggle = self.app.manual_recognition_toggle

    def tearDown(self):
        app = getattr(self, "app", None)
        if app is None:
            return
        app._auto_loop_bridge.request_stop()
        app._auto_loop_bridge.wait(2)
        if not app._closing:
            app.on_close()
        self.pump(lambda: window_closed(app), timeout=3)
        self.app = self.toggle = None
        del app
        gc.collect()

    def pump(self, condition, timeout=3):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.update()
            if condition():
                return
            time.sleep(.005)
        self.fail("Tk/后台线程没有在限定时间内到达预期状态")

    def enable(self):
        with patch("ui.gui_app.messagebox.showwarning") as warning:
            self.toggle.invoke()
        warning.assert_called_once()
        self.assertIsNotNone(manual_provider(self.app.page))

    def dialog_ready(self):
        dialog = self.app._recognition_dialog
        return dialog is not None and dialog.winfo_exists()

    def respond(self, value):
        dialog = self.app._recognition_dialog
        if value == "found" and dialog.request.needs_position:
            from types import SimpleNamespace
            dialog.select_position(SimpleNamespace(x=10, y=20))
        else:
            dialog.buttons[value].invoke()

    def test_mode_isolation_idle_lock_and_no_extra_confirmation(self):
        self.assertFalse(self.app.manual_recognition_var.get())
        self.enable()
        self.app._enter_manual_intervention()
        self.app._manual_session.cycle_cell((0, 0))
        self.app.apply_manual_changes()
        self.assertFalse(self.app._auto_loop_running())
        self.assertEqual(self.app.sonar_board.get_state(0, 0), CellState.HIT)
        self.assertEqual(self.formal.board.get_state(0, 0), CellState.SELECTED)
        self.assertIn("disabled", self.toggle.state())
        self.app._exit_manual_intervention()
        self.toggle.invoke()
        self.assertIsNone(manual_provider(self.app.page))
        self.assertIs(self.app.sonar_board, self.formal.board)
        self.assertFalse(self.app._auto_loop_running())
        self.assertIsNone(self.app._recognition_dialog)
        # 正常模式原模板识别继续执行，且没有人工请求。
        with patch("controllers.page_controller.find_template_with_score", return_value=(None, .1)) as vision:
            self.assertIsNone(self.app.page.find_template("retry1.png"))
        vision.assert_called_once()
        self.assertIsNone(self.app._recognition_dialog)

    def test_running_popup_submission_updates_board_strategy_and_counters_then_stops(self):
        self.enable()
        seen = set()
        with fast_flow():
            self.app.start_auto_loop()
            while True:
                self.pump(self.dialog_ready)
                request = self.app._recognition_dialog.request
                self.assertNotIn(request.request_id, seen)
                seen.add(request.request_id)
                self.assertTrue(self.app._runtime.control_lock.locked())
                self.assertIn("disabled", self.toggle.state())
                dialog = self.app._recognition_dialog
                self.assertTrue(dialog.photos)
                # 同一队列事件重复到达时保留同一个弹窗。
                self.app._auto_loop_bridge.events.put(("manual_request", request))
                self.app._drain_auto_loop_events()
                self.assertIs(self.app._recognition_dialog, dialog)
                if request.kind == "probe":
                    self.assertEqual(len(dialog.canvases), 2)
                    self.assertEqual(request.target_point, self.app.sonar_board.screen_point(*request.cell))
                    for canvas, photo, original in zip(dialog.canvases, dialog.photos, request.images):
                        self.assertEqual(len(canvas.find_all()), 4)  # 原图与三个目标标记
                        self.assertEqual(photo.get(0, 0), tuple(int(v) for v in original[0, 0, ::-1]))
                        self.assertEqual(int(original.max()), 0)  # Canvas 标记未改动输入图
                self.assertFalse(self.app._recognition_dialog.grab_current())
                value = {"template": "found",
                         "page": "activity_detail", "probe": "hit"}[request.kind]
                self.respond(value)
                if request.kind == "probe":
                    # 使用原 GUI 停止入口；已接受结果必须完整同步。
                    self.app.toggle_auto_loop()
                    break
            self.pump(lambda: not self.app._auto_loop_running() and self.app._level_change_allowed())
        self.assertEqual(self.app.sonar_board.get_state(0, 0), CellState.HIT)
        self.assertEqual(self.app.auto_loop_total_var.get(), "发数：1 | HIT：1 | MISS：0")
        self.assertIn("HIT", self.app.auto_loop_last_var.get())
        self.assertIsNone(self.app._recognition_dialog)
        self.assertEqual(self.app.auto_loop_state_var.get(), "已停止")
        self.assertGreater(self.device.click.call_count, 0)

    def test_popup_close_cancels_without_restart_or_default_result(self):
        self.enable()
        self.app.start_auto_loop()
        self.pump(self.dialog_ready)
        self.app._recognition_dialog.cancel()
        self.pump(lambda: self.app._level_change_allowed())
        self.assertEqual(self.app.auto_loop_total_var.get(), "发数：0 | HIT：0 | MISS：0")
        self.app.game.restart_game.assert_not_called()
        self.assertIsNone(manual_provider(self.app.page).pending)

    def test_template_click_scaling_and_screenshot_identity(self):
        from queue import Queue
        from threading import Thread
        from ui.manual_recognition_dialog import ManualRecognitionDialog
        from ui.manual_recognition_dialog import ImageTransform
        import numpy as np
        self.enable()
        provider = manual_provider(self.app.page)
        requests, results = Queue(), Queue()
        provider.publish = requests.put
        # 非整比例缩放，同时校验边缘和范围。
        transform = ImageTransform(1280, 720, 777, 437)
        self.assertEqual(transform.original_point(776, 436), (1278, 718))
        for point in ((-1, 0), (777, 0), (0, 437)):
            with self.assertRaises(ValueError):
                transform.original_point(*point)
        self.device.image[:, :] = (10, 20, 30)
        original = self.device.image.copy()
        thread = Thread(target=lambda: results.put(self.app.page.wait_and_click("retry1.png", wait_seconds=0)))
        thread.start()
        request = requests.get(timeout=2)
        self.assertIs(request.images[0], self.device.image)
        self.assertEqual(self.device.capture_count, 1)
        self.assertEqual(len(request.templates), 1)
        self.app.deiconify()
        dialog = ManualRecognitionDialog(self.app, request, on_submit=self.app.submit_trial_result,
                                         on_stop=self.app.stop_auto_loop)
        self.app._recognition_dialog = dialog
        self.pump(lambda: dialog.canvases[0].winfo_viewable())
        self.assertEqual(dialog.photos[0].get(5, 5), (30, 20, 10))
        x, y = 100, 80
        expected = dialog.transforms[0].original_point(x, y)
        dialog.canvases[0].event_generate("<Button-1>", x=x, y=y)
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results.get_nowait().center, expected)
        self.device.click.assert_called_once_with(*expected)
        np.testing.assert_array_equal(self.device.image, original)
        # 弹窗收到双击或残留事件也不会再次写入。
        dialog.answer("found", coordinates=expected)
        self.assertEqual(self.device.click.call_count, 1)

    def _launch_refreshing_wait(self, timeout=.02):
        from types import SimpleNamespace
        self.enable()
        provider = manual_provider(self.app.page)
        provider.bind(1, self.app.sonar_board, self.app.sonar_strategy)
        self.wait_results = []
        def run_wait(**kwargs):
            match = kwargs["page"].wait_and_click("retry1.png", timeout=timeout,
                      poll_interval=.02, wait_seconds=0, stop_event=kwargs["stop_event"])
            self.wait_results.append(match)
            return SimpleNamespace(stop_reason="requested", rounds=0, hits=0, misses=0)
        runner = patch("ui.auto_loop_bridge.run_multi_level_loop", side_effect=run_wait)
        runner.start()
        self.addCleanup(runner.stop)
        self.app.start_auto_loop()
        self.pump(self.dialog_ready)
        return self.app._recognition_dialog

    def _observe_new_frame(self, dialog):
        import numpy as np
        first_number = dialog.displayed_frame.number
        template = dialog.request.templates[0]
        height, width = template.shape[:2]
        self.device.image = np.full((max(400, height+40), max(600, width+40), 3), (20, 100, 40), np.uint8)
        self.device.image[20:20+height, 20:20+width] = template
        self.pump(lambda: dialog.displayed_frame.number > first_number and
                  dialog.photos[0].get(5, 5) == (40, 100, 20))
        self.assertIs(dialog, self.app._recognition_dialog)
        self.assertEqual(len(dialog.photos), 2)  # 主图和模板引用均不积压。
        self.assertEqual(len(dialog.canvases[0].find_all()), 1)
        np.testing.assert_array_equal(dialog.displayed_frame.image[20:20+height, 20:20+width], template)
        self.assertEqual(self.wait_results, [])
        self.device.click.assert_not_called()

    def test_wait_popup_refreshes_past_reference_and_click_binds_displayed_frame(self):
        from types import SimpleNamespace
        from vision.image_match import read_image
        import numpy as np
        dialog = self._launch_refreshing_wait()
        first_text = dialog.timer_text.get()
        self._observe_new_frame(dialog)
        self.assertEqual(float(dialog.wait_progress["value"]), 100.)
        self.assertIn("仍在等待人工判断", dialog.timer_text.get())
        count = self.device.capture_count
        self.pump(lambda: self.device.capture_count >= count + 4)
        self.assertNotEqual(dialog.timer_text.get(), first_text)
        self.assertTrue(self.app._runtime.control_lock.locked())
        frame = dialog.displayed_frame
        expected = dialog.transforms[0].original_point(40, 25)
        dialog.select_position(SimpleNamespace(x=40, y=25))
        self.pump(lambda: self.app._level_change_allowed())
        self.assertEqual(len(self.wait_results), 1)
        self.assertEqual(self.wait_results[0].center, expected)
        self.device.click.assert_called_once_with(*expected)
        provider = manual_provider(self.app.page)
        np.testing.assert_array_equal(read_image(provider.last_diagnostic_path), frame.image)
        self.assertIsNone(provider.take_latest_frame())
        self.assertIsNone(dialog.displayed_frame)
        self.assertEqual(dialog.photos, [])
        dialog.update_frame(frame)  # 迟到回调不得访问销毁的窗口。
        dialog.update_elapsed()
        dialog.select_position(SimpleNamespace(x=-1, y=-1))

    def test_wait_timeout_button_works_before_reference(self):
        dialog = self._launch_refreshing_wait(timeout=30)
        self._observe_new_frame(dialog)
        self.assertLess(float(dialog.wait_progress["value"]), 100.)
        dialog.buttons["timeout"].invoke()
        self.pump(lambda: self.app._level_change_allowed())
        self.assertEqual(self.wait_results, [None])
        self.device.click.assert_not_called()

    def _stop_refreshing_wait(self, close_kind):
        dialog = self._launch_refreshing_wait()
        self._observe_new_frame(dialog)
        provider = manual_provider(self.app.page)
        if close_kind == "main":
            self.app.on_close()
            self.pump(lambda: window_closed(self.app))
        elif close_kind == "popup":
            # 调用实际注册的窗口关闭回调。
            dialog.tk.call(dialog.protocol("WM_DELETE_WINDOW"))
            self.pump(lambda: self.app._level_change_allowed())
        else:
            self.app.toggle_auto_loop()
            self.pump(lambda: self.app._level_change_allowed())
        self.assertFalse(self.app._auto_loop_bridge.running)
        self.assertIsNone(provider.pending)
        self.assertIsNone(provider.take_latest_frame())
        self.assertEqual(dialog.photos, [])
        self.assertIsNone(dialog.timer_text)
        self.assertEqual(self.wait_results, [])
        self.app.game.restart_game.assert_not_called()
        if close_kind == "main":
            self.assertTrue(self.app._auto_loop_bridge.events.empty())
            self.app = self.toggle = None

    def test_stop_button_during_refresh(self):
        self._stop_refreshing_wait("stop")

    def test_popup_close_during_refresh(self):
        self._stop_refreshing_wait("popup")

    def test_main_close_during_refresh(self):
        self._stop_refreshing_wait("main")

    def test_window_close_while_waiting_exits_without_restart(self):
        self.enable()
        self.app.start_auto_loop()
        self.pump(self.dialog_ready)
        self.app.on_close()
        self.pump(lambda: window_closed(self.app))
        self.assertFalse(self.app._auto_loop_running())
        self.app.game.restart_game.assert_not_called()
        self.assertFalse(self.network.weak)
        self.assertFalse(self.network.reject)
        self.app = None

    def test_victory_next_level_models_and_ui_are_synchronized(self):
        self.enable()
        victory_seen = False
        with fast_flow():
            self.app.start_auto_loop()
            while True:
                self.pump(self.dialog_ready)
                request = self.app._recognition_dialog.request
                if request.level == 2:
                    self.assertEqual(self.app.level_selector.current_level, 2)
                    self.assertEqual(self.app.sonar_board.grid_size, 4)
                    self.assertIs(self.app.board_view.board, self.app.sonar_board)
                    self.assertIs(self.app.board_view.strategy, self.app.sonar_strategy)
                    self.assertEqual(self.app.auto_loop_total_var.get(), "发数：3 | HIT：3 | MISS：0")
                    self.assertEqual(self.app.sonar_strategy.remaining_submarines, (2, 2))
                    self.app.toggle_auto_loop()
                    break
                value = {"template": "found",
                         "page": "activity_detail", "probe": "hit"}[request.kind]
                if "胜利画面" in request.step:
                    value = "missing" if victory_seen else "found"
                    victory_seen = True
                self.respond(value)
            self.pump(lambda: self.app._level_change_allowed())
        self.assertTrue(victory_seen)
        self.assertEqual(self.formal.strategy.get_confirmed_ships(), ())


if __name__ == "__main__":
    unittest.main()
