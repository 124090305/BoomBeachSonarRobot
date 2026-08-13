from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event

import config

from controllers.adb_controller import AdbController
from controllers.page_controller import PageController
from logger import get_logger
from sonar import (
    Cell,
    ConfirmedShip,
    Point,
    SonarBoard,
    SonarStrategy,
)
from sonar_config import ACTIVITY_PAGE_CONFIG
from stop_control import raise_if_stop_requested

from .activity_flow import reenter_activity_for_probe
from .sonar_page import (
    detect_sonar_page_state,
    wait_activity_detail_ready,
)


logger = get_logger(__name__)


@dataclass(frozen=True)
class ProbeContext:
    """一次探测完成页面操作后的上下文。"""

    cell: Cell
    screen_point: Point
    before_path: Path
    after_path: Path


@dataclass
class ProbeProgress:
    """单发页面操作的可恢复进度。"""

    cell: Cell | None = None
    screen_point: Point | None = None
    before_path: Path | None = None
    after_path: Path | None = None
    click_committed: bool = False
    after_captured: bool = False

    def mark_click_committed(self) -> None:
        """记录 ADB 已接受目标格点击。"""
        self.click_committed = True

    def reset_after_game_rollback(self) -> None:
        """游戏重启回档后丢弃本发未确认的页面进度。"""
        self.cell = None
        self.screen_point = None
        self.before_path = None
        self.after_path = None
        self.click_committed = False
        self.after_captured = False

    def build_context(self) -> ProbeContext:
        """把完整检查点转换成后续识别上下文。"""
        if (
            self.cell is None
            or self.screen_point is None
            or self.before_path is None
            or self.after_path is None
            or not self.after_captured
        ):
            raise RuntimeError(
                "单发探测进度不完整，无法生成识别上下文"
            )

        return ProbeContext(
            cell=self.cell,
            screen_point=self.screen_point,
            before_path=self.before_path,
            after_path=self.after_path,
        )


@dataclass(frozen=True)
class ManualProbeResult:
    """人工提交 HIT / MISS 后的最终结果。"""

    context: ProbeContext
    hit: bool
    newly_confirmed: tuple[ConfirmedShip, ...]


def prepare_probe_once(
    adb: AdbController,
    page: PageController,
    board: SonarBoard,
    strategy: SonarStrategy,
    output_dir: str | Path | None = None,
    progress: ProbeProgress | None = None,
    stop_event: Event | None = None,
) -> ProbeContext:
    """执行一次真实单发探测所需的公共页面操作。"""
    raise_if_stop_requested(
        stop_event
    )

    logger.info(
        "开始单发探测页面操作"
    )

    config.ensure_directories()
    adb.ensure_device_online()

    raise_if_stop_requested(
        stop_event
    )

    if not board.has_complete_mapping:
        raise RuntimeError(
            "棋盘坐标映射不完整，"
            "无法执行真实格点点击"
        )

    actual_progress = progress or ProbeProgress()
    cell = actual_progress.cell

    if cell is not None and strategy.pending_cell != cell:
        raise RuntimeError(
            "单发恢复进度与策略 pending_cell 不一致："
            f"progress={cell}, pending={strategy.pending_cell}"
        )

    cell = strategy.pending_cell

    if cell is None:
        cell = strategy.choose_next_cell()

    if cell is None:
        raise RuntimeError(
            "策略没有可继续探测的格子"
        )

    row, col = cell

    x, y = board.screen_point(
        row,
        col,
    )

    actual_progress.cell = cell
    actual_progress.screen_point = (x, y)

    raise_if_stop_requested(
        stop_event
    )

    logger.info(
        "本次策略选格：逻辑格=%s，模拟器坐标=(%s, %s)",
        cell,
        x,
        y,
    )

    ready = wait_activity_detail_ready(
        page,
        timeout=(
            ACTIVITY_PAGE_CONFIG.probe_detail_ready_timeout
        ),
        stop_event=stop_event,
    )

    if not ready:
        current_state = (
            detect_sonar_page_state(
                page,
                stop_event=stop_event,
            )
        )

        raise RuntimeError(
            "执行单发探测前没有检测到活动详情页。"
            "当前页面状态="
            f"{current_state.value}"
        )

    probe_dir = (
        Path(output_dir)
        if output_dir is not None
        else config.SCREENSHOT_DIR / "manual_probe"
    )

    probe_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        actual_progress.before_path is None
        or actual_progress.after_path is None
    ):
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        prefix = (
            f"probe_{timestamp}"
            f"_r{row}_c{col}"
        )

        actual_progress.before_path = (
            probe_dir
            / f"{prefix}_before.png"
        )

        actual_progress.after_path = (
            probe_dir
            / f"{prefix}_after.png"
        )

    logger.info(
        "点击目标格前截图"
    )

    raise_if_stop_requested(
        stop_event
    )

    actual_progress.before_path = adb.take_screenshot(
        actual_progress.before_path
    )

    raise_if_stop_requested(
        stop_event
    )

    logger.info(
        "点击目标格：逻辑格=%s，模拟器坐标=(%s, %s)",
        cell,
        x,
        y,
    )

    page.click_point(
        x,
        y,
        wait_seconds=(
            ACTIVITY_PAGE_CONFIG.probe_after_click_delay
        ),
        after_click=(
            actual_progress.mark_click_committed
        ),
        stop_event=stop_event,
    )

    logger.info(
        "准备退出当前活动详情页"
    )

    quit_match = page.click_template(
        ACTIVITY_PAGE_CONFIG.quit_activity_template,
        stop_event=stop_event,
    )

    if quit_match is None:
        raise RuntimeError(
            "目标格点击后没有找到退出活动按钮。"
            "当前页面状态可能异常；"
            "本次结果不会提交给策略。"
        )

    logger.info(
        "已点击退出活动按钮：中心=%s，相似度=%.3f",
        quit_match.center,
        quit_match.score,
    )

    reenter_activity_for_probe(
        adb,
        page,
        stop_event=stop_event,
    )

    logger.info(
        "重新进入活动后截图"
    )

    actual_progress.after_path = adb.take_screenshot(
        actual_progress.after_path
    )
    actual_progress.after_captured = True

    raise_if_stop_requested(
        stop_event
    )

    context = actual_progress.build_context()

    logger.info(
        "单发页面操作完成："
        "cell=%s，before=%s，after=%s；"
        "等待 HIT / MISS 结果处理",
        context.cell,
        context.before_path,
        context.after_path,
    )

    return context


def submit_manual_probe_result(
    strategy: SonarStrategy,
    context: ProbeContext,
    *,
    hit: bool,
) -> ManualProbeResult:
    """把人工确认的 HIT / MISS 交回策略。"""
    pending = strategy.pending_cell

    if pending != context.cell:
        raise RuntimeError(
            "人工结果对应的格子和策略当前等待格不一致："
            f"pending={pending}, context={context.cell}"
        )

    newly_confirmed = (
        strategy.report_result(
            context.cell,
            hit=bool(hit),
        )
    )

    result = ManualProbeResult(
        context=context,
        hit=bool(hit),
        newly_confirmed=(
            tuple(newly_confirmed)
        ),
    )

    logger.info(
        "人工探测结果已提交：%s -> %s",
        context.cell,
        "HIT" if result.hit else "MISS",
    )

    if result.newly_confirmed:
        logger.info(
            "本次新确认潜艇：%s",
            [
                {
                    "length": ship.length,
                    "direction": ship.direction,
                    "cells": ship.cells,
                }
                for ship in result.newly_confirmed
            ],
        )

    return result


__all__ = [
    "ManualProbeResult",
    "ProbeContext",
    "prepare_probe_once",
    "submit_manual_probe_result",
]
