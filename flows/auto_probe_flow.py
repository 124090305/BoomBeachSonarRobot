from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Callable

import config

from controllers.adb_controller import AdbController
from controllers.network_controller import NetworkController
from controllers.page_controller import PageController
from logger import get_logger
from sonar import (
    Cell,
    ConfirmedShip,
    SonarBoard,
    SonarStrategy,
)
from sonar_config import (
    ACTIVITY_PAGE_CONFIG,
    AUTO_PROBE_CONFIG,
)
from stop_control import raise_if_stop_requested
from vision import (
    DiamondHitConfig,
    DiamondHitResult,
    classify_diamond_hit,
)

from .auto_probe_ready import ensure_auto_probe_ready
from .auto_probe_recovery import (
    ProbeRecoveryResult,
    _recover_after_strategy_done_once,
    recover_after_hit_once,
    recover_after_miss_once,
    wait_retry_with_failure_capture,
)
from .probe_flow import (
    ProbeContext,
    ProbeProgress,
    prepare_probe_once,
)


logger = get_logger(__name__)


@dataclass(frozen=True)
class AutoProbeOnceResult:
    """完整自动一发探测的结果。"""

    context: ProbeContext
    recognition: DiamondHitResult
    hit: bool
    newly_confirmed: tuple[ConfirmedShip, ...]
    recovery: ProbeRecoveryResult
    next_cell: Cell | None


@dataclass(frozen=True)
class AutoProbeCommittedResult:
    """HIT/MISS 已完成策略与棋盘同步的结果。"""

    context: ProbeContext
    recognition: DiamondHitResult
    hit: bool
    newly_confirmed: tuple[ConfirmedShip, ...]


ResultCommittedCallback = Callable[
    [AutoProbeCommittedResult],
    None,
]


@dataclass
class AutoProbeProgress:
    """一发自动探测跨异常重启保留的执行进度。"""

    probe: ProbeProgress = field(
        default_factory=ProbeProgress
    )
    context: ProbeContext | None = None
    recognition: DiamondHitResult | None = None
    hit: bool | None = None
    newly_confirmed: tuple[ConfirmedShip, ...] = ()
    result_committed: bool = False
    result_notified: bool = False
    restart_recovery: ProbeRecoveryResult | None = None
    hit_replay_required: bool = False
    completed_recovery: ProbeRecoveryResult | None = None

    def apply_restart_recovery(
        self,
        recovery: ProbeRecoveryResult,
    ) -> None:
        """根据识别阶段处理游戏重启造成的点击回档。"""
        if self.recognition is None or self.hit is None:
            self.probe.reset_after_game_rollback()
            self.context = None
            self.recognition = None
            self.hit = None
            self.newly_confirmed = ()
            self.result_committed = False
            self.result_notified = False
            self.restart_recovery = None
            self.hit_replay_required = False
            self.completed_recovery = None

            logger.info(
                "异常发生在 HIT/MISS 识别完成前；"
                "已丢弃本发截图进度，保留 pending_cell 重新探测"
            )
            return

        if self.completed_recovery is not None:
            return

        if self.hit:
            self.restart_recovery = None
            self.hit_replay_required = True
            logger.info(
                "已识别 HIT，但游戏因重启回档；"
                "恢复后将重新点击该格并完成联网提交"
            )
            return

        self.restart_recovery = recovery
        self.hit_replay_required = False
        logger.info(
            "已识别 MISS；重启已丢弃本次游戏请求，"
            "保留策略结果继续运行"
        )


def is_hit_recognition_state(
    state: str,
) -> bool:
    """只有 diamond_hit 的 hit 状态按 HIT 写回策略。"""
    return str(state).strip().lower() == "hit"


def is_conclusive_recognition_state(
    state: str,
) -> bool:
    """只有明确的 hit / miss 才允许写入策略。"""
    return str(state).strip().lower() in {
        "hit",
        "miss",
    }


def _replay_recognized_hit(
    page: PageController,
    context: ProbeContext,
    *,
    stop_event: Event | None = None,
) -> None:
    """重启回档后重新点击已识别的 HIT，等待后续联网提交。"""
    x, y = context.screen_point

    logger.warning(
        "重新点击已识别 HIT：cell=%s，模拟器坐标=(%s, %s)",
        context.cell,
        x,
        y,
    )

    page.click_point(
        x,
        y,
        wait_seconds=(
            ACTIVITY_PAGE_CONFIG.probe_after_click_delay
        ),
        stop_event=stop_event,
    )


def _complete_recognition_and_sync(
    adb: AdbController,
    strategy: SonarStrategy,
    context: ProbeContext,
    actual_progress: AutoProbeProgress,
    *,
    hit_config: DiamondHitConfig | None,
    recognition_index: int,
    on_result_committed: ResultCommittedCallback | None,
) -> None:
    """完整完成识别、策略写入和棋盘同步，中间不检查停止。"""
    if actual_progress.recognition is None:
        before = adb.read_image(
            context.before_path
        )
        after = adb.read_image(
            context.after_path
        )

        classifier_config = (
            hit_config
            if hit_config is not None
            else build_default_hit_config()
        )

        actual_progress.recognition = classify_diamond_hit(
            before_screenshot=before,
            after_screenshot=after,
            center=context.screen_point,
            config=classifier_config,
            index=int(recognition_index),
        )

        recognition_state = (
            actual_progress.recognition.state
        )

        if not is_conclusive_recognition_state(
            recognition_state
        ):
            raise RuntimeError(
                "自动命中识别结果无效："
                f"state={recognition_state}；"
                "本次结果不会写入策略"
            )

        actual_progress.hit = is_hit_recognition_state(
            recognition_state
        )

    recognition = actual_progress.recognition
    hit = actual_progress.hit

    if recognition is None or hit is None:
        raise RuntimeError(
            "自动探测进度缺少 HIT/MISS 判断结果"
        )

    logger.info(
        "自动命中判断："
        "cell=%s，state=%s，confidence=%.3f，"
        "score=%.3f -> %s",
        context.cell,
        recognition.state,
        recognition.confidence,
        recognition.score,
        "HIT" if hit else "MISS",
    )

    if not actual_progress.result_committed:
        pending = strategy.pending_cell

        if pending != context.cell:
            raise RuntimeError(
                "自动识别结果对应格与策略 pending_cell 不一致："
                f"pending={pending}, context={context.cell}"
            )

        actual_progress.newly_confirmed = tuple(
            strategy.report_result(
                context.cell,
                hit=hit,
            )
        )
        actual_progress.result_committed = True

    if (
        on_result_committed is not None
        and not actual_progress.result_notified
    ):
        on_result_committed(
            AutoProbeCommittedResult(
                context=context,
                recognition=recognition,
                hit=hit,
                newly_confirmed=(
                    actual_progress.newly_confirmed
                ),
            )
        )
        actual_progress.result_notified = True


def build_default_hit_config(
    *,
    debug: bool = True,
    debug_dir: str | Path | None = None,
) -> DiamondHitConfig:
    """创建当前固定 10x10 关卡使用的命中识别参数。"""
    actual_debug_dir = (
        Path(debug_dir)
        if debug_dir is not None
        else (
            config.SCREENSHOT_DIR
            / AUTO_PROBE_CONFIG.diamond_debug_dir_name
        )
    )

    return DiamondHitConfig(
        diamond_w=AUTO_PROBE_CONFIG.diamond_w,
        diamond_h=AUTO_PROBE_CONFIG.diamond_h,
        search_radius=(
            AUTO_PROBE_CONFIG.diamond_search_radius
        ),
        debug=bool(debug),
        debug_dir=str(actual_debug_dir),
    )


def run_auto_probe_once(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    board: SonarBoard,
    strategy: SonarStrategy,
    *,
    hit_config: DiamondHitConfig | None = None,
    output_dir: str | Path | None = None,
    recognition_index: int = 0,
    progress: AutoProbeProgress | None = None,
    stop_event: Event | None = None,
    on_result_committed: ResultCommittedCallback | None = None,
) -> AutoProbeOnceResult:
    """执行一整发自动探测，并按结果完成对应恢复。"""
    raise_if_stop_requested(
        stop_event
    )

    logger.info(
        "开始完整自动单发探测"
    )

    ensure_auto_probe_ready(
        adb=adb,
        page=page,
        network=network,
        stop_event=stop_event,
    )

    actual_progress = progress or AutoProbeProgress()

    actual_output_dir = (
        Path(output_dir)
        if output_dir is not None
        else (
            config.SCREENSHOT_DIR
            / AUTO_PROBE_CONFIG.auto_probe_dir_name
        )
    )

    if actual_progress.context is None:
        actual_progress.context = prepare_probe_once(
            adb=adb,
            page=page,
            board=board,
            strategy=strategy,
            output_dir=actual_output_dir,
            progress=actual_progress.probe,
            stop_event=stop_event,
        )

    context = actual_progress.context

    if actual_progress.hit_replay_required:
        _replay_recognized_hit(
            page=page,
            context=context,
            stop_event=stop_event,
        )
        actual_progress.hit_replay_required = False

    raise_if_stop_requested(
        stop_event
    )

    _complete_recognition_and_sync(
        adb=adb,
        strategy=strategy,
        context=context,
        actual_progress=actual_progress,
        hit_config=hit_config,
        recognition_index=recognition_index,
        on_result_committed=on_result_committed,
    )

    raise_if_stop_requested(
        stop_event
    )

    recognition = actual_progress.recognition
    hit = actual_progress.hit

    if recognition is None or hit is None:
        raise RuntimeError(
            "自动探测进度缺少 HIT/MISS 判断结果"
        )

    newly_confirmed = actual_progress.newly_confirmed

    if newly_confirmed:
        logger.info(
            "本发新确认潜艇：%s",
            [
                {
                    "length": ship.length,
                    "direction": ship.direction,
                    "cells": ship.cells,
                }
                for ship in newly_confirmed
            ],
        )

    if actual_progress.completed_recovery is not None:
        recovery = actual_progress.completed_recovery
    else:
        if actual_progress.restart_recovery is not None:
            recovery = actual_progress.restart_recovery
        elif strategy.done:
            recovery = _recover_after_strategy_done_once(
                adb=adb,
                page=page,
                network=network,
                hit=hit,
                stop_event=stop_event,
            )
        elif hit:
            recovery = recover_after_hit_once(
                adb=adb,
                page=page,
                network=network,
                stop_event=stop_event,
            )
        else:
            recovery = recover_after_miss_once(
                adb=adb,
                page=page,
                network=network,
                stop_event=stop_event,
            )

        actual_progress.completed_recovery = recovery

    raise_if_stop_requested(
        stop_event
    )

    next_cell = strategy.choose_next_cell()

    result = AutoProbeOnceResult(
        context=context,
        recognition=recognition,
        hit=hit,
        newly_confirmed=newly_confirmed,
        recovery=recovery,
        next_cell=next_cell,
    )

    logger.info(
        "完整自动单发完成："
        "cell=%s -> %s，next=%s，strategy_done=%s",
        result.context.cell,
        "HIT" if result.hit else "MISS",
        result.next_cell,
        strategy.done,
    )

    return result


__all__ = [
    "AutoProbeCommittedResult",
    "AutoProbeOnceResult",
    "ProbeRecoveryResult",
    "build_default_hit_config",
    "ensure_auto_probe_ready",
    "is_conclusive_recognition_state",
    "is_hit_recognition_state",
    "recover_after_hit_once",
    "recover_after_miss_once",
    "run_auto_probe_once",
    "wait_retry_with_failure_capture",
]
