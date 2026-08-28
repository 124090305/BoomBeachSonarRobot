from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

from controllers.adb_controller import AdbController
from controllers.game_controller import GameController
from controllers.network_controller import NetworkController
from controllers.page_controller import PageController
from logger import get_logger
from sonar import SonarBoard, SonarStrategy
from sonar_config import AUTO_PROBE_CONFIG
from stop_control import (
    StopRequestedError,
    raise_if_stop_requested,
)
from vision import DiamondHitConfig

from .auto_probe_exception_recovery import (
    restart_auto_probe_once,
    restore_auto_probe_network_safely,
)
from .auto_probe_flow import (
    AutoProbeCommittedResult,
    AutoProbeOnceResult,
    AutoProbeProgress,
    run_auto_probe_once,
)


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
ResultCallback = Callable[[int, AutoProbeCommittedResult], None]
StatusCallback = Callable[[str], None]


class AutoProbeRecoveryExhaustedError(RuntimeError):
    """当前一发耗尽异常重启次数。"""


def _run_once_with_restart_fallback(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    board: SonarBoard,
    strategy: SonarStrategy,
    *,
    game: GameController | None,
    hit_config: DiamondHitConfig | None,
    output_dir: str | Path | None,
    recognition_index: int,
    stop_event: Event | None,
    on_result_committed: Callable[
        [AutoProbeCommittedResult],
        None,
    ] | None,
) -> AutoProbeOnceResult:
    """执行当前一发，并在可恢复异常后按配置重启。"""
    max_attempts = int(
        AUTO_PROBE_CONFIG.max_restart_attempts
    )

    if max_attempts <= 0:
        raise ValueError(
            "max_restart_attempts 必须大于 0"
        )

    progress = AutoProbeProgress()
    restart_attempts = 0
    recovery_game = game
    last_error: Exception | None = None

    while True:
        raise_if_stop_requested(
            stop_event
        )

        try:
            return run_auto_probe_once(
                adb=adb,
                page=page,
                network=network,
                board=board,
                strategy=strategy,
                hit_config=hit_config,
                output_dir=output_dir,
                recognition_index=recognition_index,
                progress=progress,
                stop_event=stop_event,
                on_result_committed=on_result_committed,
            )
        except StopRequestedError:
            raise

        except RuntimeError as exc:
            raise_if_stop_requested(
                stop_event
            )

            last_error = exc
            logger.exception(
                "自动探测当前发发生可恢复异常：%s",
                exc,
            )

        recovered = False

        while restart_attempts < max_attempts:
            raise_if_stop_requested(
                stop_event
            )

            restart_attempts += 1

            try:
                if recovery_game is None:
                    recovery_game = GameController(
                        adb,
                        network=network,
                    )

                restart_recovery = restart_auto_probe_once(
                    game=recovery_game,
                    adb=adb,
                    page=page,
                    network=network,
                    attempt=restart_attempts,
                    max_attempts=max_attempts,
                    stop_event=stop_event,
                )
            except StopRequestedError:
                raise

            except Exception as exc:
                raise_if_stop_requested(
                    stop_event
                )

                last_error = exc
                logger.exception(
                    "自动探测第 %s/%s 次异常重启恢复失败：%s",
                    restart_attempts,
                    max_attempts,
                    exc,
                )
                continue

            progress.apply_restart_recovery(
                restart_recovery
            )
            recovered = True
            break

        if recovered:
            continue

        cleanup_ok = restore_auto_probe_network_safely(
            network
        )
        message = (
            "自动探测异常恢复失败："
            f"已尝试重启 {max_attempts} 次；"
            f"网络清理={'成功' if cleanup_ok else '失败'}；"
            f"最后错误={last_error}"
        )
        logger.error(message)
        raise AutoProbeRecoveryExhaustedError(
            message
        ) from last_error


def run_auto_probe_loop(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    board: SonarBoard,
    strategy: SonarStrategy,
    *,
    game: GameController | None = None,
    stop_event: Event | None = None,
    hit_config: DiamondHitConfig | None = None,
    output_dir: str | Path | None = None,
    on_round: RoundCallback | None = None,
    on_result: ResultCallback | None = None,
    on_status: StatusCallback | None = None,
    max_rounds: int | None = None,
) -> AutoProbeLoopSummary:
    """
    连续执行完整自动单发流程。

    停止规则：
    1. 用户发出 stop_event：当前不可拆小动作结束后停止；
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

        round_committed = False

        def record_committed_result(
            committed: AutoProbeCommittedResult,
        ) -> None:
            nonlocal rounds, hits, misses, round_committed

            if round_committed:
                return

            rounds += 1

            if committed.hit:
                hits += 1
            else:
                misses += 1

            round_committed = True

            if on_result is not None:
                on_result(
                    rounds,
                    committed,
                )

        try:
            result = _run_once_with_restart_fallback(
                adb=adb,
                page=page,
                network=network,
                board=board,
                strategy=strategy,
                game=game,
                hit_config=hit_config,
                output_dir=output_dir,
                recognition_index=rounds,
                stop_event=actual_stop_event,
                on_result_committed=record_committed_result,
            )
        except StopRequestedError:
            logger.info(
                "自动探测已在最近可中断点响应用户停止"
            )
            stop_reason = "requested"
            break

        except AutoProbeRecoveryExhaustedError:
            logger.exception(
                "自动探测连续循环已安全停止"
            )
            stop_reason = "recovery_failed"
            break

        if not round_committed:
            rounds += 1

            if result.hit:
                hits += 1
            else:
                misses += 1

            round_committed = True

        last_result = result

        logger.info(
            "连续循环第 %s 发完成：cell=%s -> %s，next=%s",
            rounds,
            result.context.cell,
            "HIT" if result.hit else "MISS",
            result.next_cell,
        )

        if on_round is not None:
            on_round(rounds, result)

        if actual_stop_event.is_set():
            stop_reason = "requested"
            break

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
