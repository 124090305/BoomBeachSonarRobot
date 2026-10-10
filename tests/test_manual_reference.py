"""自动参考、最终人工结果和只读预览的边界；全部使用设备替身。"""
from dataclasses import replace
import json
from pathlib import Path
from queue import Queue
from threading import Event, Thread, current_thread
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

import config
from controllers.page_controller import PageController
from flows.auto_probe_flow import recognize_probe_images
from flows.auto_probe_loop import run_auto_probe_loop
from flows.level_loop import create_level_state
from flows.sonar_page import detect_sonar_page_state
from manual_prompts import PROMPTS, preview
from manual_recognition import ManualResultProvider
from recognition_reference import RecognitionReference, template_reference
from sonar import CellState
from sonar_config import ACTIVITY_PAGE_CONFIG
from stop_control import StopRequestedError
from tests.test_auto_probe_branches import make_recognition
from tests.test_manual_trial import Device, Network, fast_flow
from vision import DiamondHitConfig
from vision.image_match import find_template_with_score, read_image


class ManualReferenceTests(unittest.TestCase):
    def setUp(self):
        self.output = tempfile.TemporaryDirectory()
        self.addCleanup(self.output.cleanup)
        self.device = Device()
        self.provider = ManualResultProvider(diagnostic_dir=self.output.name)
        self.page = PageController(self.device, manual_results=self.provider)

    def record(self):
        return json.loads(self.provider.last_diagnostic_path.with_suffix('.json').read_text(encoding='utf-8'))

    def test_template_original_algorithm_score_and_human_override(self):
        template = read_image(config.TEMPLATE_DIR / 'retry1.png')
        h, w = template.shape[:2]
        self.device.image[30:30+h, 50:50+w] = template
        expected, score = find_template_with_score(self.device.image, template, .93)
        seen = []
        def answer(request):
            seen.append(request)
            self.assertEqual(request.reference.point, expected.center)
            self.assertEqual(request.reference.score, score)
            self.assertEqual(request.reference.threshold, .93)
            self.device.click.assert_not_called()
            self.provider.submit(request.request_id, value='missing', basis='assumed')
        self.provider.publish = answer
        self.assertIsNone(self.page.wait_and_click('retry1.png', threshold=.93, wait_seconds=0))
        self.device.click.assert_not_called()
        self.assertEqual(len(seen), 1)
        record = self.record()
        self.assertEqual(record['automatic']['value'], 'found')
        self.assertEqual(record['human'], dict(value='missing', coordinates=[], basis='assumed'))
        np.testing.assert_array_equal(read_image(self.provider.last_diagnostic_path), self.device.image)

    def test_page_reference_uses_sonar_score_and_human_selects_different_page(self):
        from vision import MatchResult
        match = MatchResult(.91, (20, 30), (60, 70))
        self.provider.publish = lambda r: self.provider.submit(r.request_id, value='home')
        with patch('flows.sonar_page.find_template_with_score', side_effect=[(None, .2), (match, .91)]) as matcher:
            self.assertEqual(detect_sonar_page_state(self.page).value, 'home')
        self.assertEqual(self.device.capture_count, 1)
        for call in matcher.call_args_list:
            self.assertIs(call.args[0], self.device.image)
        record = self.record()
        self.assertEqual(record['automatic']['value'], 'home_sonar_visible')
        self.assertEqual(record['automatic']['score'], .91)
        self.assertEqual(record['automatic']['threshold'], ACTIVITY_PAGE_CONFIG.sonar_match_threshold)
        self.assertEqual(record['automatic']['details']['basis_template'], ACTIVITY_PAGE_CONFIG.sonar_template)
        self.assertEqual(record['human']['value'], 'home')
        self.device.click.assert_not_called()

    def test_probe_reference_does_not_commit_and_human_miss_overrides_auto_hit(self):
        state, network = create_level_state(1), Network()
        self.provider.bind(1, state.board, state.strategy)
        auto = make_recognition('hit')
        before_revision = state.board.revision
        references = []
        def answer(r):
            if r.kind == 'probe':
                references.append(r.reference)
                self.assertEqual(state.board.revision, before_revision)
                self.assertEqual(state.board.get_state(0, 0), CellState.SELECTED)
                self.assertEqual(state.strategy.get_confirmed_ships(), ())
                value = 'miss'
            else:
                value = 'activity_detail' if r.kind == 'page' else 'found'
            self.provider.submit(r.request_id, value=value, coordinates=(10, 20) if r.needs_position else ())
        self.provider.publish = answer
        with fast_flow(), patch('flows.auto_probe_flow.classify_diamond_hit', return_value=auto), \
                patch('flows.auto_probe_flow.needs_multiframe_confirmation', return_value=False):
            result = run_auto_probe_loop(self.device, self.page, network, state.board, state.strategy,
                                         max_rounds=1, output_dir=self.output.name)
        self.assertEqual((result.rounds, result.hits, result.misses), (1, 0, 1))
        self.assertEqual(state.board.get_state(0, 0), CellState.MISS)
        self.assertEqual(references[0].value, 'hit')
        self.assertEqual(references[0].metric, '置信度')
        records = [json.loads(p.read_text(encoding='utf-8')) for p in Path(self.output.name).glob('*.json')]
        record = next(r for r in records if r['prompt_key'] == 'probe.result')
        self.assertEqual((record['automatic']['value'], record['human']['value']), ('hit', 'miss'))

    def test_shared_probe_algorithm_preserves_parameters_and_supplementary_frame_rule(self):
        before, after, extra = (np.full((20, 30, 3), i, np.uint8) for i in range(3))
        self.device.image = extra
        context = SimpleNamespace(screen_point=(15, 10), cell=(0, 0))
        cfg = DiamondHitConfig(debug=False)
        initial, final = make_recognition('unknown'), make_recognition('hit')
        for needs_extra in (False, True):
            with self.subTest(extra=needs_extra), \
                    patch('flows.auto_probe_flow.classify_diamond_hit', return_value=initial) as single, \
                    patch('flows.auto_probe_flow.needs_multiframe_confirmation', return_value=needs_extra) as needs, \
                    patch('flows.auto_probe_flow.classify_diamond_hit_multiframe', return_value=final) as multi:
                result, frames = recognize_probe_images(self.device, before, after, context,
                                                        hit_config=cfg, recognition_index=7)
                self.assertIs(single.call_args.kwargs['before_screenshot'], before)
                self.assertIs(single.call_args.kwargs['after_screenshot'], after)
                self.assertIs(single.call_args.kwargs['config'], cfg)
                self.assertEqual(single.call_args.kwargs['index'], 7)
                needs.assert_called_once_with(initial, cfg)
                self.assertIs(result, final if needs_extra else initial)
                self.assertEqual(len(frames), int(needs_extra))
                if needs_extra:
                    self.assertIs(frames[0], extra)
                    self.assertIs(multi.call_args.kwargs['after_screenshots'][1], extra)
                    self.assertIs(multi.call_args.kwargs['config'], cfg)
                else:
                    multi.assert_not_called()
        self.assertEqual(self.device.capture_count, 1)
        self.device.click.assert_not_called()

    def test_context_preview_distinguishes_shared_templates_without_invoking_state(self):
        def action(key, value):
            return preview(SimpleNamespace(continuations=PROMPTS[key].actions), value)
        self.assertIn('before', action('probe.ready', 'found'))
        self.assertIn('退出', action('probe.quit', 'found'))
        self.assertIn('after', action('probe.return', 'found'))
        self.assertIn('失败', action('victory.first', 'missing'))
        self.assertIn('下一关', action('victory.followup', 'missing'))
        self.assertEqual(action('victory.followup', 'missing'), action('victory.followup', 'timeout'))

    def test_missing_score_is_unavailable_and_serializes_without_fake_number(self):
        result = template_reference(self.device.image, ('test',), .8,
                                    matcher=Mock(side_effect=ValueError('无有效图像')))
        self.assertEqual(result.value, 'unavailable')
        self.assertIsNone(result.score)
        self.assertIsNone(RecognitionReference('unknown', score=float('nan')).to_record()['score'])

    def test_answer_during_reference_calculation_discards_late_result(self):
        self._late_analysis(cancel=False)

    def test_stop_during_reference_calculation_discards_late_result(self):
        self._late_analysis(cancel=True)

    def _late_analysis(self, cancel):
        requests, results = Queue(), Queue()
        entered, release = Event(), Event()
        self.provider.publish = requests.put
        threads = []
        def analyze(image):
            threads.append(current_thread().ident)
            if len(threads) == 2:
                entered.set()
                release.wait(2)
            return RecognitionReference('found', score=.9, point=(10, 20))
        def run():
            import time
            try:
                results.put(self.provider.template(self.device.image, 'retry1.png', waiting=True,
                    refresh=self.device.read_screenshot, started_at=time.monotonic(), timeout=0,
                    poll_interval=.01, analyze=analyze))
            except Exception as exc:
                results.put(exc)
        worker = Thread(target=run)
        worker.start()
        try:
            request = requests.get(timeout=2)
            self.assertTrue(entered.wait(2))
            if cancel:
                self.provider.cancel()
            else:
                self.provider.submit(request.request_id, value='missing', frame_id=1)
                with self.assertRaises(ValueError):
                    self.provider.submit(request.request_id, value='found')
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        result = results.get_nowait()
        if cancel:
            self.assertIsInstance(result, StopRequestedError)
        else:
            self.assertIsNone(result)
            self.assertEqual(self.record()['frame_id'], 1)
            self.assertEqual(self.record()['automatic']['value'], 'found')
        self.assertIsNone(self.provider.take_latest_frame())
        self.assertEqual(len(set(threads)), 1)
        self.assertNotEqual(threads[0], current_thread().ident)


if __name__ == '__main__':
    unittest.main()
