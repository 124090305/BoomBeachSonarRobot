from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

from controllers.adb_controller import AdbController
from controllers.network_controller import NetworkController
from controllers.page_controller import PageController
from logger import get_logger
from sonar import SonarBoard, SonarStrategy
from vision import DiamondHitConfig

from .auto_probe_flow import AutoProbeOnceResult, run_auto_probe_once


logger = get_logger(__name__)


@dataclass(frozen=True)
class AutoProbeLoopSummary:
    """一次连续自动循环结束后的简要结果。"""

    rounds: int
    hits: int
    misses: int
    stop_reason: str
    strategy_done: bool
    last_result: AutoProbeOnceResult | None


RoundCallback = Callable[[int, AutoProbeOnceResult], None]
StatusCallback = Callable[[str], None]


def run_auto_probe_loop(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    board: SonarBoard,
    strategy: SonarStrategy,
    *,
    stop_event: Event | None = None,
    hit_config: DiamondHitConfig | None = None,
    output_dir: str | Path | None = None,
    on_round: RoundCallback | None = None,
    on_status: StatusCallback | None = None,
    max_rounds: int | None = None,
) -> AutoProbeLoopSummary:
    """
    连续执行完整自动单发流程。

    停止规则：
    1. 用户发出 stop_event：当前这一发完整结束后停止；
    2. strategy.done：全部潜艇已确认后停止；
    3. max_rounds：仅用于调试限制轮数。

    当前版本不处理胜利画面，因此 strategy.done 后会停住，
    等后续胜利处理功能接管。
    """
    actual_stop_event = stop_event or Event()

    rounds = 0
    hits = 0
    misses = 0
    last_result: AutoProbeOnceResult | None = None

    if max_rounds is not None and int(max_rounds) <= 0:
        raise ValueError("max_rounds 必须大于 0")

    logger.info("连续自动探测循环开始")

    if on_status is not None:
        on_status("running")

    while True:
        if actual_stop_event.is_set():
            stop_reason = "requested"
            break

        if strategy.done:
            stop_reason = "strategy_done"
            break

        result = run_auto_probe_once(
            adb=adb,
            page=page,
            network=network,
            board=board,
            strategy=strategy,
            hit_config=hit_config,
            output_dir=output_dir,
            recognition_index=rounds,
        )

        rounds += 1
        last_result = result

        if result.hit:
            hits += 1
        else:
            misses += 1

        logger.info(
            "连续循环第 %s 发完成：cell=%s -> %s，next=%s",
            rounds,
            result.context.cell,
            "HIT" if result.hit else "MISS",
            result.next_cell,
        )

        if on_round is not None:
            on_round(rounds, result)

        if max_rounds is not None and rounds >= int(max_rounds):
            stop_reason = "max_rounds"
            break

    summary = AutoProbeLoopSummary(
        rounds=rounds,
        hits=hits,
        misses=misses,
        stop_reason=stop_reason,
        strategy_done=strategy.done,
        last_result=last_result,
    )

    logger.info(
        "连续自动探测循环结束：rounds=%s，hits=%s，misses=%s，reason=%s，strategy_done=%s",
        summary.rounds,
        summary.hits,
        summary.misses,
        summary.stop_reason,
        summary.strategy_done,
    )

    if on_status is not None:
        on_status(stop_reason)

    return summary
