from __future__ import annotations

from dataclasses import dataclass
from threading import Event

import config

from controllers.adb_controller import AdbController
from controllers.network_controller import NetworkController
from controllers.page_controller import PageController
from logger import get_logger
from sonar import Point
from sonar_config import ACTIVITY_PAGE_CONFIG
from stop_control import (
    StopRequestedError,
    interruptible_wait,
    raise_if_stop_requested,
)

from .sonar_page import (
    SonarPageState,
    detect_sonar_page_state,
    wait_activity_detail_ready,
    wait_sonar_ready,
)


logger = get_logger(__name__)


@dataclass(frozen=True)
class ActivityEntryResult:
    """初始进入声纳活动后的结果。"""

    initial_state: SonarPageState
    final_state: SonarPageState
    sonar_point: Point | None
    weak_network_enabled: bool


def dismiss_activity_start_hint(
    page: PageController,
    *,
    stop_event: Event | None = None,
) -> None:
    """点击棋盘外安全点，关闭“点击任意地方开始”提示。"""
    interruptible_wait(
        ACTIVITY_PAGE_CONFIG
        .activity_tap_to_start_delay,
        stop_event,
    )

    x, y = (
        ACTIVITY_PAGE_CONFIG
        .activity_tap_to_start_point
    )

    page.click_point(
        x,
        y,
        wait_seconds=(
            ACTIVITY_PAGE_CONFIG
            .activity_tap_to_start_after_delay
        ),
        stop_event=stop_event,
    )

    logger.info(
        "已点击安全点关闭活动开始提示："
        "(%s, %s)",
        x,
        y,
    )


def enter_activity_initial(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    *,
    stop_event: Event | None = None,
) -> ActivityEntryResult:
    """从主岛初次进入声纳活动。"""
    raise_if_stop_requested(
        stop_event
    )

    config.ensure_directories()
    adb.ensure_device_online()

    raise_if_stop_requested(
        stop_event
    )

    initial_state = (
        detect_sonar_page_state(
            page,
            stop_event=stop_event,
        )
    )

    network_state = (
        network.get_state()
    )

    raise_if_stop_requested(
        stop_event
    )

    if network_state.reject_enabled:
        raise RuntimeError(
            "当前仍开启 REJECT 断网，"
            "请先恢复网络再执行初始进入活动"
        )

    weak_enabled_by_flow = False

    try:
        if (
            initial_state
            == SonarPageState.ACTIVITY_DETAIL
        ):
            if not network_state.weak_enabled:
                network.enable_weak_network()
                weak_enabled_by_flow = True

                raise_if_stop_requested(
                    stop_event
                )

            final_state = (
                detect_sonar_page_state(
                    page,
                    stop_event=stop_event,
                )
            )

            return ActivityEntryResult(
                initial_state=initial_state,
                final_state=final_state,
                sonar_point=None,
                weak_network_enabled=True,
            )

        sonar_match = wait_sonar_ready(
            page,
            stop_event=stop_event,
        )

        if sonar_match is None:
            raise RuntimeError(
                "初始进入活动失败："
                "主岛上没有检测到声纳"
            )

        activity_match = (
            page.wait_and_click(
                ACTIVITY_PAGE_CONFIG
                .activity_button_template,
                timeout=(
                    ACTIVITY_PAGE_CONFIG
                    .activity_button_timeout
                ),
                wait_seconds=(
                    ACTIVITY_PAGE_CONFIG
                    .activity_button_click_delay
                ),
                stop_event=stop_event,
            )
        )

        if activity_match is None:
            raise RuntimeError(
                "初始进入活动失败："
                "没有找到主岛活动按钮"
            )

        logger.info(
            "已点击主岛活动按钮："
            "中心=%s，相似度=%.3f",
            activity_match.center,
            activity_match.score,
        )

        if not network_state.weak_enabled:
            network.enable_weak_network()
            weak_enabled_by_flow = True

        raise_if_stop_requested(
            stop_event
        )

        interruptible_wait(
            ACTIVITY_PAGE_CONFIG
            .initial_weak_apply_delay,
            stop_event,
        )

        interruptible_wait(
            ACTIVITY_PAGE_CONFIG
            .activity_list_before_swipe_delay,
            stop_event,
        )

        start_x, start_y = (
            ACTIVITY_PAGE_CONFIG
            .activity_list_swipe_start
        )
        end_x, end_y = (
            ACTIVITY_PAGE_CONFIG
            .activity_list_swipe_end
        )

        for index in range(
            ACTIVITY_PAGE_CONFIG
            .activity_list_swipe_count
        ):
            logger.info(
                "活动列表上划：%s/%s",
                index + 1,
                ACTIVITY_PAGE_CONFIG
                .activity_list_swipe_count,
            )

            page.swipe(
                start_x,
                start_y,
                end_x,
                end_y,
                duration_ms=(
                    ACTIVITY_PAGE_CONFIG
                    .activity_list_swipe_duration_ms
                ),
                wait_seconds=(
                    ACTIVITY_PAGE_CONFIG
                    .activity_list_swipe_interval
                ),
                stop_event=stop_event,
            )

        interruptible_wait(
            ACTIVITY_PAGE_CONFIG
            .activity_detail_entry_delay,
            stop_event,
        )

        detail_x, detail_y = (
            ACTIVITY_PAGE_CONFIG
            .activity_detail_entry_point
        )

        page.click_point(
            detail_x,
            detail_y,
            wait_seconds=0,
            stop_event=stop_event,
        )

        logger.info(
            "已点击声纳活动详情入口："
            "(%s, %s)",
            detail_x,
            detail_y,
        )

        ready = (
            wait_activity_detail_ready(
                page,
                timeout=(
                    ACTIVITY_PAGE_CONFIG
                    .activity_detail_ready_timeout
                ),
                stop_event=stop_event,
            )
        )

        if not ready:
            raise RuntimeError(
                "初始进入活动失败："
                "点击详情入口后没有检测到退出按钮"
            )

        dismiss_activity_start_hint(
            page,
            stop_event=stop_event,
        )

        final_state = (
            detect_sonar_page_state(
                page,
                stop_event=stop_event,
            )
        )

        if (
            final_state
            != SonarPageState.ACTIVITY_DETAIL
        ):
            raise RuntimeError(
                "初始进入活动后的最终页面检验失败："
                f"{final_state.value}"
            )

        current_network_state = (
            network.get_state()
        )

        raise_if_stop_requested(
            stop_event
        )

        if not current_network_state.weak_enabled:
            raise RuntimeError(
                "初始进入活动后的弱网状态检验失败"
            )

        result = ActivityEntryResult(
            initial_state=initial_state,
            final_state=final_state,
            sonar_point=(
                sonar_match.center
            ),
            weak_network_enabled=(
                current_network_state
                .weak_enabled
            ),
        )

        logger.info(
            "初始进入声纳活动完成："
            "initial=%s，final=%s，"
            "sonar=%s，weak=%s",
            result.initial_state.value,
            result.final_state.value,
            result.sonar_point,
            result.weak_network_enabled,
        )

        return result

    except StopRequestedError:
        raise

    except Exception:
        if weak_enabled_by_flow:
            try:
                network.disable_weak_network()
            except Exception:
                logger.exception(
                    "初始进入活动失败后，"
                    "关闭弱网也失败"
                )

        raise


def reenter_activity_for_probe(
    adb: AdbController,
    page: PageController,
    *,
    stop_event: Event | None = None,
) -> None:
    """退出活动详情后重新进入当前声纳活动。"""
    raise_if_stop_requested(
        stop_event
    )

    logger.info(
        "开始重新进入声纳活动"
    )

    activity_match = page.wait_and_click(
        ACTIVITY_PAGE_CONFIG.activity_button_template,
        timeout=ACTIVITY_PAGE_CONFIG.activity_button_timeout,
        wait_seconds=(
            ACTIVITY_PAGE_CONFIG.activity_button_click_delay
        ),
        stop_event=stop_event,
    )

    if activity_match is None:
        raise RuntimeError(
            "重新进入活动失败："
            f"未找到 {ACTIVITY_PAGE_CONFIG.activity_button_template}"
        )

    logger.info(
        "已点击活动按钮：中心=%s，相似度=%.3f",
        activity_match.center,
        activity_match.score,
    )

    interruptible_wait(
        ACTIVITY_PAGE_CONFIG.activity_detail_entry_delay,
        stop_event,
    )

    detail_x, detail_y = (
        ACTIVITY_PAGE_CONFIG.activity_detail_entry_point
    )

    page.click_point(
        detail_x,
        detail_y,
        wait_seconds=0,
        stop_event=stop_event,
    )

    logger.info(
        "已点击活动详情入口：(%s, %s)",
        detail_x,
        detail_y,
    )

    ready = wait_activity_detail_ready(
        page,
        timeout=(
            ACTIVITY_PAGE_CONFIG.activity_detail_ready_timeout
        ),
        stop_event=stop_event,
    )

    if not ready:
        raise RuntimeError(
            "重新进入活动失败："
            "点击活动详情入口后没有检测到退出按钮"
        )

    dismiss_activity_start_hint(
        page,
        stop_event=stop_event,
    )

    logger.info(
        "重新进入声纳活动完成"
    )


__all__ = [
    "ActivityEntryResult",
    "dismiss_activity_start_hint",
    "enter_activity_initial",
    "reenter_activity_for_probe",
]
