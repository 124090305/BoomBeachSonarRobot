"""实机多帧全局识别；逐帧复用单帧核心，再做时间一致性审核。"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
import json
import math
from pathlib import Path
import time
from typing import Callable

import numpy as np

from sonar.board import CellState
from sonar_config import GlobalBoardSyncConfig, SonarLevelConfig
from stop_control import raise_if_stop_requested

from .board_recognition import recognize_board
from .board_types import BoardRecognitionConfig, BoardRecognitionResult, RecognizedSubmarine


FrameCapture = Callable[[], np.ndarray]


@dataclass(frozen=True)
class LiveBoardRecognitionResult:
    """多帧识别结果和稳定性证据。"""

    board_result: BoardRecognitionResult
    frame_count: int
    usable_frame_count: int
    mean_state_agreement: float
    disagreement_cells: tuple[tuple[int, int], ...]
    stable: bool
    issues: tuple[str, ...]
    latest_frame_usable: bool = True


def recognize_live_board(
    capture: FrameCapture,
    *,
    level_config: SonarLevelConfig,
    live_config: GlobalBoardSyncConfig,
    vision_config: BoardRecognitionConfig | None = None,
    empty_reference: np.ndarray,
    stop_event=None,
    output_dir: Path | None = None,
) -> LiveBoardRecognitionResult:
    """连续采集并合并整盘结果；停止检查不会插入单帧算法内部。"""
    if live_config.frame_count <= 0:
        raise ValueError("实时识别帧数必须大于 0")
    if not 1 <= live_config.minimum_usable_frames <= live_config.frame_count:
        raise ValueError("实时识别最少可用帧数超出范围")

    vision_config = vision_config or BoardRecognitionConfig()
    frames: list[BoardRecognitionResult] = []
    for index in range(live_config.maximum_frame_count):
        raise_if_stop_requested(stop_event)
        image = capture()
        frames.append(
            recognize_board(
                empty_reference,
                image,
                level_config=level_config,
                config=vision_config,
                output_dir=output_dir / f"frame_{index + 1:02d}" if output_dir else None,
            )
        )
        raise_if_stop_requested(stop_event)
        if len(frames) >= live_config.frame_count:
            live = _summarize_frames(frames, live_config, vision_config)
            # 少量固定遮挡不会无限补拍；时间分歧、末帧失效才追加观测。
            if live.stable and not live.disagreement_cells:
                break
        if index + 1 < live_config.maximum_frame_count:
            deadline = time.monotonic() + live_config.frame_interval_seconds
            while time.monotonic() < deadline:
                raise_if_stop_requested(stop_event)
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))

    if output_dir:
        path = output_dir / "live_result.json"
        result = replace(live.board_result, debug_paths={"live_result": str(path.resolve()),
                         "frames": str(output_dir.resolve())})
        live = replace(live, board_result=result)
        path.write_text(json.dumps({**asdict(live), "live_config": asdict(live_config)},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
    return live


def _usable(item):
    return item.valid and item.alignment.success and item.quality == "usable"


def _summarize_frames(frames, live_config, vision_config):
    usable = [item for item in frames if _usable(item)]
    pool = usable or frames
    best = max(pool, key=lambda item: item.quality_score)
    merged, agreements, merge_issues = _merge_results(pool, best, live_config)
    disagreements = tuple(
        (cell.row, cell.col)
        for cell, agreement in zip(merged.cells, agreements)
        if agreement < 1.0 or cell.feature_scores.get("temporal_ship_unconfirmed", 0)
    )
    mean_agreement = float(np.mean(agreements)) if agreements else 0.0
    stable = (
        len(usable) >= live_config.minimum_usable_frames
        and all(_usable(item) for item in frames[-live_config.minimum_usable_frames:])
        and mean_agreement >= live_config.minimum_mean_agreement
        and len(disagreements) <= live_config.maximum_disagreement_cells
    )
    issues = list(merge_issues)
    if len(usable) < live_config.minimum_usable_frames:
        issues.append(
            f"可用实时帧不足：{len(usable)}/{len(frames)}"
        )
    if mean_agreement < live_config.minimum_mean_agreement:
        issues.append(f"多帧平均状态一致率不足：{mean_agreement:.3f}")
    if len(disagreements) > live_config.maximum_disagreement_cells:
        issues.append(f"多帧状态不一致格过多：{len(disagreements)}")
    if not all(_usable(item) for item in frames[-live_config.minimum_usable_frames:]):
        issues.append("末尾连续画面尚未稳定或末帧不可用")
    if len(usable) < len(frames):
        issues.append(f"已排除 {len(frames) - len(usable)} 张不可用帧；详见逐帧调试结果")
    merged = replace(
        merged,
        valid=bool(merged.valid and stable and
                   len(merged.review_cells) / merged.grid_size ** 2 <= vision_config.max_review_fraction),
        quality_score=float(merged.quality_score * mean_agreement),
        issues=tuple(dict.fromkeys((*merged.issues, *issues))),
    )
    return LiveBoardRecognitionResult(
        board_result=merged,
        frame_count=len(frames),
        usable_frame_count=len(usable),
        mean_state_agreement=mean_agreement,
        disagreement_cells=disagreements,
        stable=stable,
        issues=tuple(dict.fromkeys(issues)),
        latest_frame_usable=_usable(frames[-1]),
    )


def _merge_results(results, best, config):
    """采用逐格多数状态；SUNK 还需整段在多数帧中出现。"""
    n = best.grid_size
    required = math.ceil(len(results) * config.cell_agreement_threshold)
    ship_votes: Counter[tuple[tuple[tuple[int, int], ...], str]] = Counter()
    ship_samples: dict[tuple[tuple[tuple[int, int], ...], str], list[RecognizedSubmarine]] = {}
    for result in results:
        seen = set()
        for ship in result.sunk_submarines:
            key = (tuple(sorted(ship.cells)), ship.direction)
            if key in seen:
                continue
            seen.add(key)
            ship_votes[key] += 1
            ship_samples.setdefault(key, []).append(ship)
    accepted_ships = []
    for key, count in ship_votes.items():
        if count < required:
            continue
        samples = ship_samples[key]
        source = max(samples, key=lambda item: item.confidence)
        accepted_ships.append(
            replace(source, confidence=float(np.mean([item.confidence for item in samples])))
        )
    accepted_cells = {cell for ship in accepted_ships for cell in ship.cells}
    segment_support = {cell: ship_votes[(tuple(sorted(ship.cells)), ship.direction)]
                       for ship in accepted_ships for cell in ship.cells}

    cells = []
    agreements = []
    for index in range(n * n):
        votes = Counter(result.cells[index].state for result in results)
        best_state = best.cells[index].state
        state, count = max(
            votes.items(),
            key=lambda item: (item[1], item[0] == best_state),
        )
        row, col = divmod(index, n)
        downgraded = state == CellState.SUNK and (row, col) not in accepted_cells
        if (row, col) in accepted_cells:
            state = CellState.SUNK
            count = segment_support[(row, col)]
        elif state == CellState.SUNK:
            state = CellState.HIT
        agreement = count / len(results)
        sources = [result.cells[index] for result in results if result.cells[index].state == state]
        if downgraded:
            sources = [result.cells[index] for result in results
                       if result.cells[index].state in (CellState.HIT, CellState.SUNK)]
        source = max(sources or [best.cells[index]], key=lambda item: item.confidence)
        confidence = float(np.mean([item.confidence for item in sources]) * agreement) if sources else 0.0
        review = bool(any(item.cells[index].needs_review for item in results)
                      or agreement < 1.0 or downgraded)
        reason = source.reason
        if review:
            reasons = dict.fromkeys(item.cells[index].reason for item in results
                                    if item.cells[index].needs_review)
            reason = "；".join(dict.fromkeys((reason, *reasons)))
        if downgraded:
            reason += "；完整船段未获多数支持，降为 HIT 待复核"
        if agreement < 1.0:
            reason += f"；多帧一致率={agreement:.2f}"
        scores = {name: float(np.mean([item.cells[index].state_scores.get(name, 0.0)
                                      for item in results]))
                  for name in ("unknown", "miss", "hit", "sunk")}
        cells.append(replace(source, state=state, confidence=confidence, needs_review=review, reason=reason,
                             state_scores=scores, feature_scores={**source.feature_scores,
                             "temporal_agreement": agreement, "temporal_support_frames": float(count),
                             "temporal_ship_unconfirmed": float(downgraded)}))
        agreements.append(agreement)

    states = tuple(tuple(cells[r * n + c].state for c in range(n)) for r in range(n))
    counts = Counter(cell.state.value.upper() for cell in cells)
    review_cells = tuple((cell.row, cell.col) for cell in cells if cell.needs_review)
    issues = []
    if any(count < required for count in ship_votes.values()):
        issues.append("部分 SUNK 船段未获得多帧多数支持，已保留为 HIT 待复核")
    return replace(
        best,
        states=states,
        cells=tuple(cells),
        counts={name: counts[name] for name in ("UNKNOWN", "MISS", "HIT", "SUNK")},
        review_cells=review_cells,
        sunk_submarines=tuple(accepted_ships),
        issues=tuple(dict.fromkeys(issue for item in results for issue in item.issues)),
        debug_paths={},
    ), tuple(agreements), tuple(issues)


__all__ = ["LiveBoardRecognitionResult", "recognize_live_board"]
