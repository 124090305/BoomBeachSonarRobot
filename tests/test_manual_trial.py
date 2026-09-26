"""人工输入驱动原业务流程；仅替换设备边界和等待时长。"""
from contextlib import ExitStack, contextmanager
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread
from types import SimpleNamespace
import math
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from controllers.page_controller import PageController
from flows.auto_probe_loop import run_auto_probe_loop
from flows.level_loop import create_level_state, run_multi_level_loop
from flows.sonar_page import detect_sonar_page_state
from manual_recognition import ManualResultProvider
from sonar import CellState
from stop_control import StopRequestedError, raise_if_stop_requested
from ui.auto_loop_bridge import AutoProbeLoopBridge
from ui.runtime_context import AppRuntimeContext


class Device:
    """设备替身不提供任何视觉测量。"""
    def __init__(self):
        self.image = np.zeros((720, 1280, 3), np.uint8)
        self.click = Mock()
        self.swipe = Mock()
        self.capture_count = 0
        self.saved_images = {}
        self.image_reads = []

    def ensure_device_online(self):
        pass

    def read_screenshot(self):
        self.capture_count += 1
        return self.image

    def take_screenshot(self, path):
        self.capture_count += 1
        self.saved_images[Path(path)] = self.image.copy()
        return Path(path)

    def read_image(self, path):
        self.image_reads.append(Path(path))
        return self.saved_images[Path(path)]


class Network:
    def __init__(self):
        self.weak = False
        self.reject = False
        self.calls = []

    def get_state(self):
        return SimpleNamespace(weak_enabled=self.weak, reject_enabled=self.reject)

    def enable_weak_network(self):
        self.calls.append("weak_on")
        self.weak = True

    def disable_weak_network(self):
        self.calls.append("weak_off")
        self.weak = False

    def enable_reject_network(self):
        self.calls.append("reject_on")
        self.reject = True

    def disable_reject_network(self):
        self.calls.append("reject_off")
        self.reject = False

    def restore_network(self):
        self.calls.append("restore")
        self.weak = self.reject = False


@contextmanager
def fast_flow():
    def wait(_seconds, stop_event=None, **_kwargs):
        raise_if_stop_requested(stop_event)
    with ExitStack() as stack:
        for module in ("controllers.page_controller", "flows.activity_flow", "flows.sonar_page", "flows.auto_probe_recovery"):
            stack.enter_context(patch(module + ".interruptible_wait", side_effect=wait))
        for name in ("controllers.page_controller.find_template_with_score", "flows.sonar_page.find_template",
                     "flows.sonar_page.find_template_with_score", "flows.auto_probe_recovery.find_template_with_score",
                     "flows.auto_probe_flow.classify_diamond_hit", "flows.auto_probe_flow.classify_diamond_hit_multiframe"):
            stack.enter_context(patch(name, side_effect=AssertionError("试运行不得调用视觉识别")))
        yield


class TrialFlowTests(unittest.TestCase):
    def setUp(self):
        self.device, self.network = Device(), Network()
        self.state = create_level_state(1)
        self.requests = []
        self.provider = ManualResultProvider(self.answer)
        self.provider.bind(1, self.state.board, self.state.strategy)
        self.page = PageController(self.device, manual_results=self.provider)
        self.stop = Event()
        self.choice = lambda request: "hit" if request.kind == "probe" else None
        self.game = Mock()
        self.game.restart_game.side_effect = lambda **kwargs: self.network.restore_network()
        self.output = tempfile.TemporaryDirectory()
        self.addCleanup(self.output.cleanup)

    def answer(self, request):
        self.requests.append(request)
        value = self.choice(request)
        if value is None:
            value = {"page": "activity_detail", "template": "found"}[request.kind]
        coordinates = (10, 20) if request.needs_position else ()
        self.provider.submit(request.request_id, value=value, coordinates=coordinates)

    def run_round(self):
        with fast_flow():
            return run_auto_probe_loop(self.device, self.page, self.network, self.state.board, self.state.strategy,
                                       game=self.game, stop_event=self.stop, max_rounds=1, output_dir=self.output.name)

    def test_hit_and_miss_follow_original_recovery_and_strategy(self):
        for value, next_cell, network_action in (("hit", (1, 0), "restore"), ("miss", (0, 2), "reject_on")):
            with self.subTest(value=value):
                self.state = create_level_state(1)
                self.provider.bind(1, self.state.board, self.state.strategy)
                self.network = Network()
                self.choice = lambda request: value if request.kind == "probe" else None
                summary = self.run_round()
                self.assertEqual(summary.rounds, 1)
                self.assertEqual((summary.hits, summary.misses), (1, 0) if value == "hit" else (0, 1))
                self.assertEqual(self.state.strategy.pending_cell, next_cell)
                self.assertIn(network_action, self.network.calls)
                self.assertEqual(summary.last_result.recognition.source, "manual_trial")
                self.assertTrue(math.isnan(summary.last_result.recognition.confidence))
                self.assertEqual(summary.last_result.context.screen_point,
                                 self.state.board.screen_point(0, 0))
                self.assertTrue(all(r.kind in {"page", "template", "probe"} for r in self.requests))
                self.device.click.assert_any_call(*self.state.board.screen_point(0, 0))
                probe = next(r for r in reversed(self.requests) if r.kind == "probe")
                self.assertIs(probe.images[0], self.device.saved_images[summary.last_result.context.before_path])
                self.assertIs(probe.images[1], self.device.saved_images[summary.last_result.context.after_path])

    def test_missing_activity_entrance_still_runs_original_entry_actions(self):
        pages = iter(("home", "home", "activity_detail", "activity_detail"))
        sonar_checks = 0
        def choose(request):
            nonlocal sonar_checks
            if request.kind == "page":
                return next(pages, "activity_detail")
            if "海边声纳" in request.step:
                sonar_checks += 1
                return "missing" if sonar_checks == 1 else "found"
            return "miss" if request.kind == "probe" else None
        self.choice = choose
        summary = self.run_round()
        self.assertEqual(summary.misses, 1)
        self.assertEqual(sonar_checks, 2)
        self.assertGreaterEqual(self.device.swipe.call_count, 3)
        self.assertGreater(self.device.capture_count, 2)

    def test_retry_timeout_runs_original_restart_without_double_commit(self):
        self.choice = lambda r: "miss" if r.kind == "probe" else "timeout" if "重试按钮" in r.step else None
        summary = self.run_round()
        self.game.restart_game.assert_called_once()
        self.assertEqual(summary.misses, 1)
        self.assertEqual(sum(r.kind == "probe" for r in self.requests), 1)
        self.assertFalse(self.network.reject)

    def test_inconclusive_results_retry_same_target_without_recording(self):
        for uncertain in ("unknown", "unopened"):
            with self.subTest(uncertain=uncertain):
                self.state = create_level_state(1)
                self.provider.bind(1, self.state.board, self.state.strategy)
                self.requests.clear()
                probes = iter((uncertain, "hit"))
                self.choice = lambda r: next(probes) if r.kind == "probe" else None
                summary = self.run_round()
                requests = [r for r in self.requests if r.kind == "probe"]
                self.assertEqual(summary.rounds, 1)
                self.assertEqual([r.cell for r in requests], [(0, 0), (0, 0)])
                self.assertNotEqual(requests[0].request_id, requests[1].request_id)

    def test_victory_runs_transition_and_changes_to_clean_next_level(self):
        victory_checks = 0
        def choose(request):
            nonlocal victory_checks
            if "胜利画面" in request.step:
                victory_checks += 1
                return "found" if victory_checks == 1 else "missing"
            return "hit" if request.kind == "probe" else None
        self.choice = choose
        changed = []
        def on_level(state):
            changed.append(state)
            self.stop.set()
        with fast_flow():
            summary = run_multi_level_loop(self.device, self.page, self.network, initial_state=self.state,
                                           game=self.game, stop_event=self.stop, on_level_changed=on_level,
                                           output_dir=self.output.name)
        self.assertEqual((summary.hits, summary.completed_levels, summary.current_level), (3, 1, 2))
        self.assertEqual(victory_checks, 2)
        self.assertEqual(summary.stop_reason, "requested")
        self.assertEqual(changed[0].strategy.remaining_submarines, (2, 2))
        self.assertTrue(all(s in {CellState.UNKNOWN, CellState.SELECTED}
                            for row in changed[0].board.snapshot().states for s in row))

    def test_duplicate_submit_and_stop_after_accept_commit_exactly_once(self):
        original = self.provider.publish
        def publish(request):
            original(request)
            if request.kind == "probe":
                with self.assertRaises(ValueError):
                    self.provider.submit(request.request_id, value="hit")
                self.stop.set()
                self.provider.cancel()
        self.provider.publish = publish
        summary = self.run_round()
        self.assertEqual((summary.rounds, summary.hits, summary.stop_reason), (1, 1, "requested"))
        self.assertEqual(self.state.board.get_state(0, 0), CellState.HIT)
        self.assertIsNone(self.state.strategy.pending_cell)
        self.assertNotIn("restore", self.network.calls)
        self.game.restart_game.assert_not_called()

    def test_single_hit_does_not_confirm_ship(self):
        original = self.provider.publish
        def publish(request):
            if request.kind == "probe":
                self.provider.submit(request.request_id, value="hit")
            else:
                original(request)
        self.provider.publish = publish
        summary = self.run_round()
        self.assertEqual(summary.last_result.outcome.value, "HIT")
        self.assertEqual(self.state.strategy.get_confirmed_ships(), ())

    def test_stop_at_each_input_boundary_never_triggers_restart(self):
        for kind in ("page", "template", "probe"):
            with self.subTest(kind=kind):
                self.state = create_level_state(1)
                self.provider.bind(1, self.state.board, self.state.strategy)
                self.provider.begin_run()
                self.stop.clear()
                def publish(request):
                    if request.kind == kind:
                        self.stop.set()
                        self.provider.cancel()
                    else:
                        self.answer(request)
                self.provider.publish = publish
                summary = self.run_round()
                self.assertEqual((summary.rounds, summary.stop_reason), (0, "requested"))
                self.game.restart_game.assert_not_called()
                self.assertEqual(self.state.board.get_state(0, 0), CellState.SELECTED)

    def test_missing_mapping_is_not_silently_replaced(self):
        self.state.board.clear_screen_mapping()
        self.run_round()
        self.assertFalse(self.state.board.has_complete_mapping)
        self.assertFalse(any(r.kind == "probe" for r in self.requests))



class TrialChannelTests(unittest.TestCase):
    def test_wait_does_not_expire_and_stop_releases_without_control_lock(self):
        device, stop, requests = Device(), Event(), Queue()
        provider = ManualResultProvider(requests.put)
        page = PageController(device, manual_results=provider)
        result = Queue()
        control_lock = Lock()
        def worker():
            with control_lock:
                try:
                    result.put(page.wait_template("retry1.png", timeout=0, stop_event=stop))
                except Exception as exc:
                    result.put(exc)
        thread = Thread(target=worker)
        thread.start()
        request = requests.get(timeout=2)
        self.assertTrue(control_lock.locked())
        self.assertTrue(result.empty())
        self.assertTrue(requests.empty())
        stop.set()
        provider.cancel()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(result.get_nowait(), StopRequestedError)
        with self.assertRaises(ValueError):
            provider.submit(request.request_id, value="found", coordinates=(1, 1))

    def test_bounds_and_old_request_ids_are_rejected_and_clicks_execute(self):
        provider = ManualResultProvider()
        device = Device()
        page = PageController(device, manual_results=provider)
        old = []
        def publish(request):
            if old:
                with self.assertRaises(ValueError):
                    provider.submit(old[0], value="found", coordinates=(10, 20))
            with self.assertRaises(ValueError):
                provider.submit(request.request_id, value="found", coordinates=(1280, 720))
            provider.submit(request.request_id, value="found", coordinates=(10, 20))
            old.append(request.request_id)
        provider.publish = publish
        page.wait_and_click("retry1.png", wait_seconds=0)
        device.click.assert_called_once_with(10, 20)
        page.wait_and_click("retry1.png", wait_seconds=0)
        self.assertEqual(device.click.call_count, 2)
        device.click.assert_called_with(10, 20)

    def test_close_releases_wait_and_restores_network_after_worker_exit(self):
        device, network, requests = Device(), Network(), Queue()
        provider = ManualResultProvider(requests.put)
        state = create_level_state(1)
        page = PageController(device, manual_results=provider)
        context = AppRuntimeContext(device, network, page, Mock(), state.board, state.strategy, Lock(), 1)
        bridge = AutoProbeLoopBridge(context)
        self.assertTrue(bridge.start())
        kind, request = bridge.events.get(timeout=2)
        self.assertEqual(kind, "manual_request")
        closer = Thread(target=bridge.shutdown_and_restore_network)
        closer.start()
        closer.join(2)
        self.assertFalse(closer.is_alive())
        self.assertFalse(bridge.running)
        self.assertIn("restore", network.calls)
        context.game.restart_game.assert_not_called()
        with self.assertRaises(ValueError):
            provider.submit(request.request_id, value="home")

    def test_detaching_provider_restores_original_vision(self):
        device = Device()
        provider = ManualResultProvider()
        page = PageController(device, manual_results=provider)
        provider.publish = lambda r: provider.submit(r.request_id, value="activity_detail")
        self.assertEqual(detect_sonar_page_state(page).value, "activity_detail")
        page.manual_results = None
        with patch("flows.sonar_page.find_template", return_value=object()) as vision:
            self.assertEqual(detect_sonar_page_state(page).value, "activity_detail")
        vision.assert_called_once()


if __name__ == "__main__":
    unittest.main()
