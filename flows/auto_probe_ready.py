from __future__ import annotations

import config

from controllers.adb_controller import AdbController
from controllers.network_controller import NetworkController
from controllers.page_controller import PageController
from logger import get_logger

from .activity_flow import enter_activity_initial
from .sonar_page import (
    SonarPageState,
    detect_sonar_page_state,
)


logger = get_logger(__name__)


def ensure_auto_probe_ready(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
) -> None:
    """整理到活动详情页、弱网开启、REJECT 关闭的探测状态。"""
    config.ensure_directories()
    adb.ensure_device_online()

    network_state = network.get_state()

    if network_state.reject_enabled:
        raise RuntimeError(
            "开始自动探测前仍存在 REJECT 断网。"
            "请先恢复网络。"
        )

    page_state = detect_sonar_page_state(
        page
    )

    if page_state == SonarPageState.ACTIVITY_DETAIL:
        if not network_state.weak_enabled:
            network.enable_weak_network()

    else:
        if network_state.weak_enabled:
            network.disable_weak_network()

        entry = enter_activity_initial(
            adb=adb,
            page=page,
            network=network,
        )

        if (
            entry.final_state
            != SonarPageState.ACTIVITY_DETAIL
        ):
            raise RuntimeError(
                "自动探测准备失败："
                "没有进入活动详情页"
            )

    final_network = network.get_state()
    final_page = detect_sonar_page_state(
        page
    )

    if (
        final_page
        != SonarPageState.ACTIVITY_DETAIL
    ):
        raise RuntimeError(
            "自动探测准备失败："
            f"最终页面={final_page.value}"
        )

    if final_network.reject_enabled:
        raise RuntimeError(
            "自动探测准备失败："
            "REJECT 仍然开启"
        )

    if not final_network.weak_enabled:
        raise RuntimeError(
            "自动探测准备失败："
            "弱网 DROP 没有开启"
        )

    logger.info(
        "自动单发准备完成："
        "page=%s，weak=%s，reject=%s",
        final_page.value,
        final_network.weak_enabled,
        final_network.reject_enabled,
    )


__all__ = [
    "ensure_auto_probe_ready",
]
