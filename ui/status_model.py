from __future__ import annotations

from dataclasses import dataclass

from flows import SonarPageState
from flows.progress import AutoProbeStatusEvent
from sonar import Cell


PAGE_STATE_TEXT = {
    SonarPageState.HOME.value: "主岛页面",
    SonarPageState.HOME_SONAR_VISIBLE.value: "声纳图标可见",
    SonarPageState.ACTIVITY_DETAIL.value: "活动棋盘页面",
    SonarPageState.UNKNOWN.value: "未知页面",
}

NETWORK_STATE_TEXT = {
    "normal": "正常联网",
    "weak": "弱网 DROP",
    "reject": "断网 REJECT",
    "unknown": "未检测",
}

AUTO_STATE_TEXT = {
    "stopped": "已停止",
    "starting": "启动中",
    "running": "运行中",
    "stopping": "停止中",
    "error": "异常",
    "complete": "完成",
}

AUTO_PHASE_TEXT = {
    "idle": "等待启动",
    "preparing_activity": "准备活动",
    "preparing_probe": "准备探测",
    "executing_probe": "执行探测",
    "judging_result": "判断结果",
    "hit_recovery": "HIT 恢复",
    "miss_recovery": "MISS 恢复",
    "exception_recovery": "异常恢复",
    "complete": "完成",
}


@dataclass(frozen=True)
class StatusItem:
    text: str
    tone: str


@dataclass(frozen=True)
class DashboardSnapshot:
    device: StatusItem
    page: StatusItem
    network: StatusItem
    auto: StatusItem
    round_text: str
    phase_text: str
    target_text: str
    total: str
    hits: str
    misses: str
    last_result: str
    recovery_attempt: str


@dataclass
class RuntimeStatusModel:
    """保存 GUI 需要的三层运行状态和本轮统计。"""

    device_online: bool | None = None
    page_state: str | None = None
    weak_network_enabled: bool | None = None
    reject_network_enabled: bool | None = None
    loop_state: str = "stopped"
    phase: str = "idle"
    target_mode: str = "none"
    target_cell: Cell | None = None
    round_index: int = 0
    total: int = 0
    hits: int = 0
    misses: int = 0
    last_cell: Cell | None = None
    last_hit: bool | None = None
    recovery_attempt: int = 0

    def begin_run(
        self,
        next_cell: Cell | None,
    ) -> None:
        self.loop_state = "starting"
        self.phase = "preparing_activity"
        self.target_mode = "next" if next_cell is not None else "none"
        self.target_cell = next_cell
        self.round_index = 1
        self.total = 0
        self.hits = 0
        self.misses = 0
        self.last_cell = None
        self.last_hit = None
        self.recovery_attempt = 0

    def request_stop(self) -> None:
        self.loop_state = "stopping"

    def apply_progress(
        self,
        event: AutoProbeStatusEvent,
    ) -> None:
        for field_name in (
            "loop_state",
            "phase",
            "page_state",
            "device_online",
            "weak_network_enabled",
            "reject_network_enabled",
            "round_index",
            "recovery_attempt",
        ):
            value = getattr(event, field_name)

            if value is not None:
                setattr(self, field_name, value)

        if event.target_mode is not None:
            self.target_mode = event.target_mode
            self.target_cell = event.target_cell

    def record_result(
        self,
        index: int,
        *,
        cell: Cell,
        hit: bool,
    ) -> None:
        self.loop_state = "running"
        self.round_index = int(index)
        self.total = max(self.total, int(index))
        self.last_cell = cell
        self.last_hit = bool(hit)

        if hit:
            self.hits += 1
        else:
            self.misses += 1

    def record_round(
        self,
        *,
        next_cell: Cell | None,
    ) -> None:
        self.target_mode = "next" if next_cell is not None else "none"
        self.target_cell = next_cell
        self.recovery_attempt = 0

    def finish(
        self,
        *,
        rounds: int,
        hits: int,
        misses: int,
        stop_reason: str,
        strategy_done: bool,
    ) -> None:
        self.total = int(rounds)
        self.hits = int(hits)
        self.misses = int(misses)
        self.target_mode = "none" if strategy_done else self.target_mode

        if stop_reason == "recovery_failed":
            self.loop_state = "error"
            self.phase = "exception_recovery"
        elif strategy_done or stop_reason == "strategy_done":
            self.loop_state = "complete"
            self.phase = "complete"
            self.target_cell = None
        else:
            self.loop_state = "stopped"

    def fail(self) -> None:
        self.loop_state = "error"

    def reset_detection(self) -> None:
        self.device_online = None
        self.page_state = None
        self.weak_network_enabled = None
        self.reject_network_enabled = None

    def snapshot(self) -> DashboardSnapshot:
        return DashboardSnapshot(
            device=self._device_item(),
            page=self._page_item(),
            network=self._network_item(),
            auto=self._auto_item(),
            round_text=self._round_text(),
            phase_text=(
                "当前阶段："
                + AUTO_PHASE_TEXT.get(self.phase, self.phase)
            ),
            target_text=self._target_text(),
            total=str(self.total),
            hits=str(self.hits),
            misses=str(self.misses),
            last_result=self._last_result_text(),
            recovery_attempt=(
                str(self.recovery_attempt)
                if self.recovery_attempt > 0
                else "-"
            ),
        )

    def _device_item(self) -> StatusItem:
        if self.device_online is True:
            return StatusItem("在线", "success")

        if self.device_online is False:
            return StatusItem("离线", "danger")

        return StatusItem("未检测", "neutral")

    def _page_item(self) -> StatusItem:
        if self.page_state is None:
            return StatusItem("未检测", "neutral")

        text = PAGE_STATE_TEXT.get(self.page_state, self.page_state)
        tone = "danger" if self.page_state == SonarPageState.UNKNOWN.value else "success"
        return StatusItem(text, tone)

    def _network_item(self) -> StatusItem:
        if self.reject_network_enabled is True:
            key = "reject"
            tone = "warning"
        elif self.weak_network_enabled is True:
            key = "weak"
            tone = "info"
        elif (
            self.weak_network_enabled is False
            and self.reject_network_enabled is False
        ):
            key = "normal"
            tone = "success"
        else:
            key = "unknown"
            tone = "neutral"

        return StatusItem(
            NETWORK_STATE_TEXT[key],
            tone,
        )

    def _auto_item(self) -> StatusItem:
        tones = {
            "stopped": "neutral",
            "starting": "warning",
            "running": "info",
            "stopping": "warning",
            "error": "danger",
            "complete": "success",
        }
        return StatusItem(
            AUTO_STATE_TEXT.get(self.loop_state, self.loop_state),
            tones.get(self.loop_state, "neutral"),
        )

    def _round_text(self) -> str:
        if self.round_index <= 0:
            return "自动探测：未开始"

        return f"自动探测：第 {self.round_index} 发"

    def _target_text(self) -> str:
        if self.target_cell is None or self.target_mode == "none":
            return "目标格：-"

        prefix = "当前目标格" if self.target_mode == "current" else "下一目标格"
        return f"{prefix}：{self.target_cell}"

    def _last_result_text(self) -> str:
        if self.last_hit is None or self.last_cell is None:
            return "-"

        result = "HIT" if self.last_hit else "MISS"
        return f"{result} · {self.last_cell}"


__all__ = [
    "AUTO_PHASE_TEXT",
    "AUTO_STATE_TEXT",
    "DashboardSnapshot",
    "NETWORK_STATE_TEXT",
    "PAGE_STATE_TEXT",
    "RuntimeStatusModel",
    "StatusItem",
]
