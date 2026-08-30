from __future__ import annotations

from threading import Event

from controllers.page_controller import PageController
from logger import get_logger
from sonar_config import ACTIVITY_PAGE_CONFIG, ActivityPageConfig
from stop_control import raise_if_stop_requested


logger = get_logger(__name__)


class VictoryTransitionError(RuntimeError):
    """胜利画面缺失或无法进入下一关。"""


def handle_victory_transition(
    page: PageController,
    *,
    stop_event: Event | None = None,
    flow_config: ActivityPageConfig = ACTIVITY_PAGE_CONFIG,
) -> int:
    """识别并连续跳过胜利页面，确认下一关详情页就绪。"""
    raise_if_stop_requested(stop_event)
    match = page.wait_template(
        flow_config.victory_template,
        timeout=flow_config.victory_wait_timeout,
        stop_event=stop_event,
    )
    if match is None:
        raise VictoryTransitionError(
            f"等待胜利画面超时（{flow_config.victory_wait_timeout:.1f} 秒）"
        )

    handled = 0
    while match is not None and handled < flow_config.victory_max_rounds:
        handled += 1
        x, y = flow_config.activity_tap_to_start_point
        logger.info("处理第 %s 个胜利/结算页面", handled)
        page.click_point(
            x,
            y,
            wait_seconds=flow_config.victory_after_click_delay,
            stop_event=stop_event,
        )
        page.click_point(
            x,
            y,
            wait_seconds=flow_config.victory_click_delay,
            stop_event=stop_event,
        )
        match = page.wait_template(
            flow_config.victory_template,
            timeout=flow_config.victory_followup_timeout,
            stop_event=stop_event,
        )

    if match is not None:
        raise VictoryTransitionError(
            f"连续胜利页面超过上限 {flow_config.victory_max_rounds}"
        )

    ready = page.wait_template(
        flow_config.quit_activity_template,
        timeout=flow_config.next_level_ready_timeout,
        stop_event=stop_event,
    )
    if ready is None:
        raise VictoryTransitionError(
            f"胜利处理后未进入下一关（{flow_config.next_level_ready_timeout:.1f} 秒）"
        )

    logger.info("胜利页面处理完成，下一关详情页已就绪")
    return handled


__all__ = ["VictoryTransitionError", "handle_victory_transition"]
