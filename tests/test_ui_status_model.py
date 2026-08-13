from __future__ import annotations

import unittest

from flows.progress import AutoProbeStatusEvent
from ui.status_model import RuntimeStatusModel


class RuntimeStatusModelTests(unittest.TestCase):
    def test_maps_page_network_phase_and_current_target(self) -> None:
        model = RuntimeStatusModel()
        model.apply_progress(
            AutoProbeStatusEvent(
                loop_state="running",
                phase="miss_recovery",
                page_state="activity_detail",
                device_online=True,
                weak_network_enabled=True,
                reject_network_enabled=False,
                target_mode="current",
                target_cell=(7, 1),
                round_index=12,
            )
        )

        snapshot = model.snapshot()

        self.assertEqual(snapshot.device.text, "在线")
        self.assertEqual(snapshot.page.text, "活动棋盘页面")
        self.assertEqual(snapshot.network.text, "弱网 DROP")
        self.assertEqual(snapshot.auto.text, "运行中")
        self.assertEqual(snapshot.phase_text, "当前阶段：MISS 恢复")
        self.assertEqual(snapshot.target_text, "当前目标格：(7, 1)")
        self.assertEqual(snapshot.round_text, "自动探测：第 12 发")

    def test_reject_has_priority_and_uses_warning_tone(self) -> None:
        model = RuntimeStatusModel(
            weak_network_enabled=True,
            reject_network_enabled=True,
        )

        snapshot = model.snapshot()

        self.assertEqual(snapshot.network.text, "断网 REJECT")
        self.assertEqual(snapshot.network.tone, "warning")

    def test_result_statistics_and_recovery_failure(self) -> None:
        model = RuntimeStatusModel()
        model.begin_run((0, 0))
        model.record_result(
            1,
            cell=(0, 0),
            hit=True,
        )
        model.finish(
            rounds=1,
            hits=1,
            misses=0,
            stop_reason="recovery_failed",
            strategy_done=False,
        )

        snapshot = model.snapshot()

        self.assertEqual(snapshot.total, "1")
        self.assertEqual(snapshot.hits, "1")
        self.assertEqual(snapshot.misses, "0")
        self.assertEqual(snapshot.last_result, "HIT · (0, 0)")
        self.assertEqual(snapshot.auto.text, "异常")
        self.assertEqual(snapshot.phase_text, "当前阶段：异常恢复")


if __name__ == "__main__":
    unittest.main()
