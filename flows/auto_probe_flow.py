from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
from sonar_config import AUTO_PROBE_CONFIG
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


def is_hit_recognition_state(
    state: str,
) -> bool:
    """只有 diamond_hit 的 hit 状态按 HIT 写回策略。"""
    return str(state).strip().lower() == "hit"


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
) -> AutoProbeOnceResult:
    """执行一整发自动探测，并按结果完成对应恢复。"""
    logger.info(
        "开始完整自动单发探测"
    )

    ensure_auto_probe_ready(
        adb=adb,
        page=page,
        network=network,
    )

    actual_output_dir = (
        Path(output_dir)
        if output_dir is not None
        else (
            config.SCREENSHOT_DIR
            / AUTO_PROBE_CONFIG.auto_probe_dir_name
        )
    )

    context = prepare_probe_once(
        adb=adb,
        page=page,
        board=board,
        strategy=strategy,
        output_dir=actual_output_dir,
    )

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

    recognition = classify_diamond_hit(
        before_screenshot=before,
        after_screenshot=after,
        center=context.screen_point,
        config=classifier_config,
        index=int(recognition_index),
    )

    hit = is_hit_recognition_state(
        recognition.state
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

    pending = strategy.pending_cell

    if pending != context.cell:
        raise RuntimeError(
            "自动识别结果对应格与策略 pending_cell 不一致："
            f"pending={pending}, context={context.cell}"
        )

    newly_confirmed = tuple(
        strategy.report_result(
            context.cell,
            hit=hit,
        )
    )

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

    if strategy.done:
        recovery = _recover_after_strategy_done_once(
            adb=adb,
            page=page,
            network=network,
            hit=hit,
        )
    elif hit:
        recovery = recover_after_hit_once(
            adb=adb,
            page=page,
            network=network,
        )
    else:
        recovery = recover_after_miss_once(
            adb=adb,
            page=page,
            network=network,
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
    "AutoProbeOnceResult",
    "ProbeRecoveryResult",
    "build_default_hit_config",
    "ensure_auto_probe_ready",
    "is_hit_recognition_state",
    "recover_after_hit_once",
    "recover_after_miss_once",
    "run_auto_probe_once",
    "wait_retry_with_failure_capture",
]
