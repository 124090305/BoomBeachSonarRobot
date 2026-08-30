from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

from controllers import AdbController, GameController, NetworkController, PageController
from logger import get_logger
from sonar import CheckerboardHuntStrategy, SonarBoard, SonarStrategy
from sonar_config import get_level_config
from stop_control import StopRequestedError, raise_if_stop_requested
from vision import DiamondHitConfig

from .auto_probe_flow import AutoProbeOnceResult
from .auto_probe_loop import AutoProbeLoopSummary, run_auto_probe_loop
from .victory_flow import handle_victory_transition


logger = get_logger(__name__)


@dataclass(frozen=True)
class LevelState:
    level: int
    board: SonarBoard
    strategy: SonarStrategy


@dataclass(frozen=True)
class MultiLevelLoopSummary:
    rounds: int
    hits: int
    misses: int
    completed_levels: int
    current_level: int
    stop_reason: str
    strategy_done: bool
    last_result: AutoProbeOnceResult | None
    level_state: LevelState


LevelCallback = Callable[[LevelState], None]


def create_level_state(level: int) -> LevelState:
    """为一关创建全新的棋盘与策略，隔离上一关全部临时状态。"""
    level_config = get_level_config(level)
    board = SonarBoard(level_config.grid_size, level_config.submarines)
    if level_config.board_quad is not None:
        board.set_screen_quad(level_config.board_quad)
    strategy = CheckerboardHuntStrategy(
        board,
        hunt_parity=level_config.hunt_parity,
        use_safety_rule=level_config.use_safety_rule,
    )
    strategy.choose_next_cell()
    return LevelState(int(level), board, strategy)


def run_multi_level_loop(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    *,
    initial_state: LevelState,
    game: GameController | None = None,
    stop_event: Event | None = None,
    hit_config: DiamondHitConfig | None = None,
    output_dir: str | Path | None = None,
    on_round=None,
    on_result=None,
    on_level_changed: LevelCallback | None = None,
    max_levels: int | None = None,
) -> MultiLevelLoopSummary:
    """在单关探测循环之上管理胜利处理和关卡对象生命周期。"""
    actual_stop_event = stop_event or Event()
    if max_levels is not None and int(max_levels) <= 0:
        raise ValueError("max_levels 必须大于 0")

    state = initial_state
    total_rounds = total_hits = total_misses = completed_levels = 0
    last_result = None

    while True:
        round_offset = total_rounds

        def emit_round(index, result):
            if on_round is not None:
                on_round(round_offset + index, result)

        def emit_result(index, result):
            if on_result is not None:
                on_result(round_offset + index, result)

        summary: AutoProbeLoopSummary = run_auto_probe_loop(
            adb=adb,
            page=page,
            network=network,
            board=state.board,
            strategy=state.strategy,
            game=game,
            stop_event=actual_stop_event,
            hit_config=hit_config,
            output_dir=output_dir,
            on_round=emit_round,
            on_result=emit_result,
        )
        total_rounds += summary.rounds
        total_hits += summary.hits
        total_misses += summary.misses
        last_result = summary.last_result

        if summary.stop_reason != "strategy_done":
            stop_reason = summary.stop_reason
            break

        try:
            handle_victory_transition(page, stop_event=actual_stop_event)
        except StopRequestedError:
            stop_reason = "requested"
            break

        raise_if_stop_requested(actual_stop_event)
        completed_levels += 1
        if max_levels is not None and completed_levels >= int(max_levels):
            stop_reason = "max_levels"
            break

        state = create_level_state(state.level + 1)
        logger.info("进入第 %s 关：已创建新棋盘和新策略", state.level)
        if on_level_changed is not None:
            on_level_changed(state)

    return MultiLevelLoopSummary(
        rounds=total_rounds,
        hits=total_hits,
        misses=total_misses,
        completed_levels=completed_levels,
        current_level=state.level,
        stop_reason=stop_reason,
        strategy_done=state.strategy.done,
        last_result=last_result,
        level_state=state,
    )


__all__ = [
    "LevelState",
    "MultiLevelLoopSummary",
    "create_level_state",
    "run_multi_level_loop",
]
