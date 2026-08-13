from __future__ import annotations

import time
from enum import Enum
from pathlib import Path
from threading import Event

import config

from controllers.page_controller import PageController
from logger import get_logger
from sonar_config import ACTIVITY_PAGE_CONFIG
from stop_control import (
    interruptible_wait,
    raise_if_stop_requested,
)
from vision.image_match import (
    MatchResult,
    find_template,
    find_template_with_score,
)

from .progress import (
    ProgressCallback,
    emit_progress,
)


logger = get_logger(__name__)


class SonarPageState(str, Enum):
    """当前声纳相关页面的大致状态。"""

    ACTIVITY_DETAIL = "activity_detail"
    HOME_SONAR_VISIBLE = "home_sonar_visible"
    HOME = "home"
    UNKNOWN = "unknown"


def _template_path(
    template_name: str,
) -> Path:
    """取得 resources/templates 下的模板路径。"""
    path = (
        config.TEMPLATE_DIR
        / template_name
    )

    if not path.is_file():
        raise FileNotFoundError(
            "缺少模板图片："
            f"{path}"
        )

    return path


def _find_sonar_match(
    screenshot,
) -> tuple[MatchResult | None, float]:
    """在同一张截图中检查两个声纳模板。"""
    best_score = 0.0

    for template_name in (
        ACTIVITY_PAGE_CONFIG.sonar_template,
        ACTIVITY_PAGE_CONFIG.sonar_label_template,
    ):
        match, score = (
            find_template_with_score(
                screenshot,
                _template_path(
                    template_name
                ),
                threshold=(
                    ACTIVITY_PAGE_CONFIG
                    .sonar_match_threshold
                ),
            )
        )

        best_score = max(
            best_score,
            score,
        )

        if match is not None:
            return match, best_score

    return None, best_score


def detect_sonar_page_state(
    page: PageController,
    *,
    stop_event: Event | None = None,
    on_progress: ProgressCallback | None = None,
) -> SonarPageState:
    """只截图检查当前声纳相关页面，不进行点击。"""
    raise_if_stop_requested(
        stop_event
    )

    screenshot = (
        page.adb.read_screenshot()
    )

    quit_match = find_template(
        screenshot,
        _template_path(
            ACTIVITY_PAGE_CONFIG
            .quit_activity_template
        ),
        threshold=(
            config.DEFAULT_MATCH_THRESHOLD
        ),
    )

    if quit_match is not None:
        raise_if_stop_requested(
            stop_event
        )
        logger.info(
            "页面状态：活动详情页"
        )
        emit_progress(
            on_progress,
            page_state=SonarPageState.ACTIVITY_DETAIL.value,
        )
        return (
            SonarPageState.ACTIVITY_DETAIL
        )

    sonar_match, sonar_score = (
        _find_sonar_match(
            screenshot
        )
    )

    if sonar_match is not None:
        raise_if_stop_requested(
            stop_event
        )
        logger.info(
            "页面状态：主岛，声纳已可见；"
            "中心=%s，相似度=%.3f",
            sonar_match.center,
            sonar_match.score,
        )
        emit_progress(
            on_progress,
            page_state=SonarPageState.HOME_SONAR_VISIBLE.value,
        )
        return (
            SonarPageState
            .HOME_SONAR_VISIBLE
        )

    activity_match = find_template(
        screenshot,
        _template_path(
            ACTIVITY_PAGE_CONFIG
            .activity_button_template
        ),
        threshold=(
            config.DEFAULT_MATCH_THRESHOLD
        ),
    )

    if activity_match is not None:
        raise_if_stop_requested(
            stop_event
        )
        logger.info(
            "页面状态：主岛；"
            "活动按钮中心=%s；"
            "当前声纳最高相似度=%.3f",
            activity_match.center,
            sonar_score,
        )
        emit_progress(
            on_progress,
            page_state=SonarPageState.HOME.value,
        )
        return SonarPageState.HOME

    raise_if_stop_requested(
        stop_event
    )

    logger.warning(
        "页面状态：未知；"
        "未识别到活动详情、声纳或主岛活动按钮；"
        "当前声纳最高相似度=%.3f",
        sonar_score,
    )

    emit_progress(
        on_progress,
        page_state=SonarPageState.UNKNOWN.value,
    )

    return SonarPageState.UNKNOWN


def wait_home_island_ready(
    page: PageController,
    timeout: float | None = None,
    *,
    stop_event: Event | None = None,
    on_progress: ProgressCallback | None = None,
) -> bool:
    """等待主岛活动按钮出现。"""
    actual_timeout = (
        ACTIVITY_PAGE_CONFIG.home_ready_timeout
        if timeout is None
        else float(timeout)
    )

    logger.info(
        "等待主岛就绪"
    )

    match = page.wait_template(
        ACTIVITY_PAGE_CONFIG
        .activity_button_template,
        timeout=actual_timeout,
        stop_event=stop_event,
    )

    if match is None:
        logger.warning(
            "主岛等待失败："
            "没有检测到活动按钮"
        )
        return False

    logger.info(
        "主岛已就绪：活动按钮中心=%s",
        match.center,
    )

    emit_progress(
        on_progress,
        page_state=SonarPageState.HOME.value,
    )

    return True


def swipe_home_up(
    page: PageController,
    *,
    stop_event: Event | None = None,
) -> None:
    """主岛向上拖动画面，露出海边声纳。"""
    start_x, start_y = (
        ACTIVITY_PAGE_CONFIG.home_swipe_start
    )
    end_x, end_y = (
        ACTIVITY_PAGE_CONFIG.home_swipe_end
    )

    logger.info(
        "主岛上划，准备寻找声纳"
    )

    page.swipe(
        start_x,
        start_y,
        end_x,
        end_y,
        duration_ms=(
            ACTIVITY_PAGE_CONFIG
            .home_swipe_duration_ms
        ),
        stop_event=stop_event,
    )


def wait_sonar_ready(
    page: PageController,
    timeout: float | None = None,
    *,
    stop_event: Event | None = None,
    on_progress: ProgressCallback | None = None,
) -> MatchResult | None:
    """等待主岛就绪，并在必要时上划寻找声纳。"""
    actual_timeout = (
        ACTIVITY_PAGE_CONFIG.sonar_wait_timeout
        if timeout is None
        else float(timeout)
    )

    if not wait_home_island_ready(
        page,
        stop_event=stop_event,
        on_progress=on_progress,
    ):
        return None

    raise_if_stop_requested(
        stop_event
    )

    screenshot = (
        page.adb.read_screenshot()
    )

    match, score = (
        _find_sonar_match(
            screenshot
        )
    )

    raise_if_stop_requested(
        stop_event
    )

    if match is not None:
        logger.info(
            "声纳已经在画面中："
            "中心=%s，相似度=%.3f",
            match.center,
            match.score,
        )
        emit_progress(
            on_progress,
            page_state=SonarPageState.HOME_SONAR_VISIBLE.value,
        )
        return match

    logger.info(
        "当前未看到声纳，"
        "最高相似度=%.3f，执行主岛上划",
        score,
    )

    swipe_home_up(
        page,
        stop_event=stop_event,
    )

    deadline = (
        time.monotonic()
        + actual_timeout
    )

    best_score_seen = score
    attempts = 0

    while True:
        raise_if_stop_requested(
            stop_event
        )

        attempts += 1

        screenshot = (
            page.adb.read_screenshot()
        )

        match, score = (
            _find_sonar_match(
                screenshot
            )
        )

        raise_if_stop_requested(
            stop_event
        )

        best_score_seen = max(
            best_score_seen,
            score,
        )

        if match is not None:
            logger.info(
                "声纳等待成功："
                "中心=%s，相似度=%.3f，检测次数=%s",
                match.center,
                match.score,
                attempts,
            )
            emit_progress(
                on_progress,
                page_state=SonarPageState.HOME_SONAR_VISIBLE.value,
            )
            return match

        remaining = (
            deadline
            - time.monotonic()
        )

        if remaining <= 0:
            logger.warning(
                "声纳等待超时："
                "%.1f 秒内未出现；"
                "最高相似度=%.3f，阈值=%.3f",
                actual_timeout,
                best_score_seen,
                ACTIVITY_PAGE_CONFIG
                .sonar_match_threshold,
            )
            return None

        interruptible_wait(
            min(
                config.PAGE_POLL_INTERVAL,
                remaining,
            ),
            stop_event,
        )


def wait_activity_detail_ready(
    page: PageController,
    timeout: float | None = None,
    *,
    stop_event: Event | None = None,
    on_progress: ProgressCallback | None = None,
) -> bool:
    """等待退出按钮出现，以确认活动详情页已就绪。"""
    actual_timeout = (
        ACTIVITY_PAGE_CONFIG.activity_detail_ready_timeout
        if timeout is None
        else float(timeout)
    )

    match = page.wait_template(
        ACTIVITY_PAGE_CONFIG.quit_activity_template,
        timeout=actual_timeout,
        stop_event=stop_event,
    )

    if match is None:
        logger.warning(
            "活动详情页未就绪：未找到 %s",
            ACTIVITY_PAGE_CONFIG.quit_activity_template,
        )
        return False

    logger.info(
        "活动详情页已就绪：退出按钮中心=%s",
        match.center,
    )

    emit_progress(
        on_progress,
        page_state=SonarPageState.ACTIVITY_DETAIL.value,
    )

    return True


__all__ = [
    "SonarPageState",
    "detect_sonar_page_state",
    "swipe_home_up",
    "wait_activity_detail_ready",
    "wait_home_island_ready",
    "wait_sonar_ready",
]
