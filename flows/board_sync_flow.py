"""实机全局识别、人工预览和正式棋盘校准的共同流程。"""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from datetime import datetime
import math

import config

from controllers.adb_controller import AdbController
from controllers.page_controller import PageController
from sonar import CellState, CheckerboardHuntStrategy, ConfirmedShip, ManualEditSession, SonarBoard, SonarStrategy, apply_manual_edits
from sonar.manual_intervention import ManualApplyResult
from sonar_config import GLOBAL_BOARD_SYNC_CONFIG, GlobalBoardSyncConfig, get_level_config
from stop_control import raise_if_stop_requested
from vision.board_live import LiveBoardRecognitionResult, recognize_live_board
from vision.board_recognition import resolve_reference_path
from vision.image_match import read_image

from .sonar_page import SonarPageState, detect_sonar_page_state


class BoardSyncError(RuntimeError):
    """当前实机画面无法安全形成整盘预览或正式校准。"""


@dataclass(frozen=True)
class BoardSyncApplyResult:
    recognition: LiveBoardRecognitionResult
    applied: ManualApplyResult


def recognize_current_board(
    adb: AdbController,
    page: PageController,
    *,
    level: int,
    stop_event=None,
    live_config: GlobalBoardSyncConfig = GLOBAL_BOARD_SYNC_CONFIG,
) -> LiveBoardRecognitionResult:
    """只读实机：确认页面，连续采帧并复核页面保持稳定。"""
    initial_page = detect_sonar_page_state(page, stop_event=stop_event)
    if initial_page != SonarPageState.ACTIVITY_DETAIL:
        raise BoardSyncError(
            f"当前页面无法识别棋盘：{initial_page.value}；请进入声纳活动棋盘页面"
        )
    level_config = get_level_config(level)
    reference = read_image(resolve_reference_path(level))
    output = (config.PROJECT_ROOT / "outputs" / live_config.output_dir_name /
              datetime.now().strftime("%Y%m%d_%H%M%S_%f")) if live_config.save_debug else None

    def checked_capture():
        image = adb.read_screenshot()
        if detect_sonar_page_state(page, stop_event=stop_event, screenshot=image) != SonarPageState.ACTIVITY_DETAIL:
            raise BoardSyncError("识别期间页面发生变化，已丢弃本轮结果")
        return image

    live = recognize_live_board(
        checked_capture,
        level_config=level_config,
        live_config=live_config,
        empty_reference=reference,
        stop_event=stop_event,
        output_dir=output,
        runtime_geometry=True,
    )
    raise_if_stop_requested(stop_event)
    final_page = detect_sonar_page_state(page, stop_event=stop_event)
    if final_page != SonarPageState.ACTIVITY_DETAIL:
        raise BoardSyncError("识别期间页面发生变化，已丢弃本轮结果")
    if not live.board_result.valid:
        detail = "；".join(live.board_result.issues) or live.board_result.quality
        raise BoardSyncError(f"全局识别整体质量不足：{detail}；调试目录={output}")
    return live


def _validate_result(recognition: LiveBoardRecognitionResult) -> None:
    """在缓存和正式提交的边界检查完整契约，拒绝残缺/自相矛盾结果。"""
    result = recognition.board_result
    if not recognition.stable or not recognition.latest_frame_usable or not result.valid:
        raise BoardSyncError("多帧全局识别未通过稳定性检查")
    n = result.grid_size
    if (n <= 0 or len(result.cells) != n*n or len(result.states) != n
            or any(len(row) != n for row in result.states)):
        raise BoardSyncError("全局识别结果尺寸不完整")
    if result.quality != "usable" or not result.alignment.success:
        raise BoardSyncError("全局识别定位或整体质量不足")
    for index, cell in enumerate(result.cells):
        row, col = divmod(index, n)
        if ((cell.row, cell.col) != (row, col) or cell.state == CellState.SELECTED
                or cell.state != result.states[row][col]
                or not math.isfinite(cell.confidence) or not 0 <= cell.confidence <= 1):
            raise BoardSyncError("全局识别状态/格号/置信度存在冲突")
    if set(result.review_cells) != {(cell.row, cell.col) for cell in result.cells if cell.needs_review}:
        raise BoardSyncError("全局识别复核标记不一致")
    if not math.isfinite(result.quality_score) or not 0 <= result.quality_score <= 1:
        raise BoardSyncError("全局识别质量分无效")
    occupied = set()
    for ship in result.sunk_submarines:
        cells = tuple(sorted(ship.cells))
        if (not cells or len(set(cells)) != len(cells) or len(cells) != ship.length
                or ship.direction not in ("H", "V")):
            raise BoardSyncError("SUNK 船段记录不完整")
        r, c = cells[0]
        expected = tuple((r, c+i) if ship.direction == "H" else (r+i, c)
                         for i in range(ship.length))
        if cells != expected or occupied.intersection(cells):
            raise BoardSyncError("SUNK 船段不连续或存在重叠")
        occupied.update(cells)
    if occupied != {(cell.row, cell.col) for cell in result.cells if cell.state == CellState.SUNK}:
        raise BoardSyncError("SUNK 船段与格子状态存在冲突")


def apply_recognition_preview(
    session: ManualEditSession,
    recognition: LiveBoardRecognitionResult,
    *,
    expected_revision: int | None = None,
) -> None:
    """把整盘结果一次性写入人工缓存，不接触正式棋盘。"""
    result = recognition.board_result
    if expected_revision is not None and session.revision != expected_revision:
        raise BoardSyncError("识别期间人工棋盘已变化，已丢弃过期结果")
    _validate_result(recognition)
    if result.grid_size != session.grid_size:
        raise BoardSyncError("识别结果与当前关卡棋盘尺寸不一致")
    if Counter(ship.length for ship in result.sunk_submarines) - Counter(session.submarines):
        raise BoardSyncError("SUNK 潜艇数量/长度与当前关卡配置冲突")
    ships = tuple(
        ConfirmedShip(
            length=ship.length,
            direction=ship.direction,
            cells=ship.cells,
            safety_area=frozenset(),
        )
        for ship in result.sunk_submarines
    )
    n = result.grid_size
    confidences = tuple(
        tuple(result.cell_at(row, col).confidence for col in range(n))
        for row in range(n)
    )
    reasons = tuple(
        tuple(result.cell_at(row, col).reason for col in range(n))
        for row in range(n)
    )
    summary = (
        f"多帧一致率={recognition.mean_state_agreement:.3f}，"
        f"质量={result.quality_score:.3f}，复核格={len(result.review_cells)}"
        + (f"；异常：{'；'.join(result.issues)}" if result.issues else "")
    )
    session.apply_recognition_preview(
        result.states,
        ships,
        review_cells=result.review_cells,
        confidences=confidences,
        reasons=reasons,
        summary=summary,
    )


def validate_automatic_board_sync(
    recognition: LiveBoardRecognitionResult,
    *,
    live_config: GlobalBoardSyncConfig = GLOBAL_BOARD_SYNC_CONFIG,
) -> None:
    """自动接管使用更严格门槛；可疑已探测事实一律要求人工复核。"""
    result = recognition.board_result
    _validate_result(recognition)
    if recognition.disagreement_cells:
        raise BoardSyncError("实时画面仍有状态分歧，请等待稳定或人工检查")
    conflict_words = ("冲突", "方向不明确", "不连续", "长度")
    conflicts = [issue for issue in result.issues if any(word in issue for word in conflict_words)]
    if conflicts:
        raise BoardSyncError(f"潜艇结构存在冲突：{'；'.join(conflicts)}")
    unsafe = []
    for row, col in result.review_cells:
        cell = result.cell_at(row, col)
        if cell.state.value != "unknown":
            unsafe.append((row, col, cell.state.value))
        elif cell.confidence < live_config.auto_minimum_unknown_review_confidence:
            unsafe.append((row, col, cell.state.value))
    if unsafe:
        shown = [(row + 1, col + 1, state.upper()) for row, col, state in unsafe]
        raise BoardSyncError(f"关键低可信格需要人工检查：{shown}")
    weak_known = [
        (cell.row + 1, cell.col + 1, cell.state.value.upper())
        for cell in result.cells
        if cell.state.value != "unknown"
        and cell.confidence < live_config.auto_minimum_known_confidence
    ]
    if weak_known:
        raise BoardSyncError(f"已探测格置信度不足：{weak_known}")


def apply_automatic_board_sync(
    recognition: LiveBoardRecognitionResult,
    board: SonarBoard,
    strategy: SonarStrategy,
    *,
    stop_event=None,
    live_config: GlobalBoardSyncConfig = GLOBAL_BOARD_SYNC_CONFIG,
) -> BoardSyncApplyResult:
    """严格审核后事务写入正式棋盘；策略重建可继续执行唯一解确认。"""
    validate_automatic_board_sync(recognition, live_config=live_config)
    session = ManualEditSession(board, strategy.get_confirmed_ships())
    apply_recognition_preview(session, recognition)
    # 先在一次性模型中审核整体布局和现有逻辑推理，正式对象不参与试算。
    trial_board = SonarBoard(board.grid_size, board.submarines)
    trial_strategy = CheckerboardHuntStrategy(trial_board,
        hunt_parity=strategy.hunt_parity, use_safety_rule=strategy.use_safety_rule)
    apply_manual_edits(session, trial_board, trial_strategy)
    ManualEditSession(trial_board, trial_strategy.get_confirmed_ships()).validate_for_apply(
        use_safety_rule=strategy.use_safety_rule)
    _validate_remaining_fleet(trial_strategy, live_config.feasibility_node_limit, stop_event)
    raise_if_stop_requested(stop_event)
    # 本次写回+策略重建为原子区，收到停止后完成同步再退出。
    applied = apply_manual_edits(session, board, strategy)
    return BoardSyncApplyResult(recognition=recognition, applied=applied)


def _validate_remaining_fleet(strategy, node_limit, stop_event):
    """复用策略合法摆放集合，检查剩余船队至少存在一种兼容布局。"""
    n = strategy.board.grid_size
    hit_mask = sum(1 << (r*n+c) for r in range(n) for c in range(n)
                   if strategy.board.get_state(r, c) == CellState.HIT)
    remaining = Counter(strategy.remaining_submarines)
    if hit_mask.bit_count() > sum(length*count for length, count in remaining.items()):
        raise BoardSyncError("HIT 数量超过剩余潜艇容量")
    placements = {}
    for length in remaining:
        options = []
        for _direction, cells in strategy._all_placements(length):
            mask = sum(1 << (r*n+c) for r, c in cells)
            area = strategy._calc_safety_area(cells) if strategy.use_safety_rule else ()
            blocked = mask | sum(1 << (r*n+c) for r, c in area)
            if (blocked & hit_mask) & ~mask:
                continue
            options.append((mask, blocked))
        placements[length] = options
    nodes = 0

    def search(counts, blocked, uncovered):
        nonlocal nodes
        nodes += 1
        if nodes > node_limit:
            raise BoardSyncError("剩余潜艇布局审核超时，需要人工检查")
        if nodes % 64 == 1:
            raise_if_stop_requested(stop_event)
        if not any(counts.values()):
            return not uncovered
        available = [(length, mask, area) for length, count in counts.items() if count
                     for mask, area in placements[length] if not mask & blocked]
        if uncovered:
            hit_options = [[item for item in available if item[1] & (1 << index)]
                           for index in range(n*n) if uncovered & (1 << index)]
            choices = min(hit_options, key=len)
        else:
            length = min((length for length, count in counts.items() if count),
                         key=lambda length: sum(item[0] == length for item in available))
            choices = [item for item in available if item[0] == length]
        for length, mask, area in choices:
            counts[length] -= 1
            if search(counts, blocked | area, uncovered & ~mask):
                return True
            counts[length] += 1
        return False

    if not search(remaining, 0, hit_mask):
        raise BoardSyncError("HIT/MISS 与剩余潜艇无法组成合法布局，请人工检查")


__all__ = [
    "BoardSyncApplyResult",
    "BoardSyncError",
    "apply_automatic_board_sync",
    "apply_recognition_preview",
    "recognize_current_board",
    "validate_automatic_board_sync",
]
