from __future__ import annotations

from threading import Event

import config

from controllers.adb_controller import AdbController
from controllers.network_controller import NetworkController
from controllers.page_controller import PageController
from logger import get_logger
from stop_control import raise_if_stop_requested

from .activity_flow import enter_activity_initial
from .sonar_page import (
    SonarPageState,
    detect_sonar_page_state,
)
from .progress import (
    ProgressCallback,
    emit_progress,
)


logger = get_logger(__name__)


def ensure_auto_probe_ready(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    *,
    stop_event: Event | None = None,
    on_progress: ProgressCallback | None = None,
) -> None:
    """整理到活动详情页、弱网开启、REJECT 关闭的探测状态。"""
    raise_if_stop_requested(
        stop_event
    )

    config.ensure_directories()
    adb.ensure_device_online()
    emit_progress(
        on_progress,
        device_online=True,
        phase="preparing_activity",
    )

    raise_if_stop_requested(
        stop_event
    )

    network_state = network.get_state()
    emit_progress(
        on_progress,
        weak_network_enabled=network_state.weak_enabled,
        reject_network_enabled=network_state.reject_enabled,
    )

    raise_if_stop_requested(
        stop_event
    )

    if network_state.reject_enabled:
        raise RuntimeError(
            "开始自动探测前仍存在 REJECT 断网。"
            "请先恢复网络。"
        )

    page_state = detect_sonar_page_state(
        page,
        stop_event=stop_event,
        on_progress=on_progress,
    )

    if page_state == SonarPageState.ACTIVITY_DETAIL:
        if not network_state.weak_enabled:
            network.enable_weak_network()
            emit_progress(
                on_progress,
                weak_network_enabled=True,
                reject_network_enabled=False,
            )

            raise_if_stop_requested(
                stop_event
            )

    else:
        if network_state.weak_enabled:
            network.disable_weak_network()
            emit_progress(
                on_progress,
                weak_network_enabled=False,
            )

            raise_if_stop_requested(
                stop_event
            )

        entry = enter_activity_initial(
            adb=adb,
            page=page,
            network=network,
            stop_event=stop_event,
            on_progress=on_progress,
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
    emit_progress(
        on_progress,
        weak_network_enabled=final_network.weak_enabled,
        reject_network_enabled=final_network.reject_enabled,
    )

    raise_if_stop_requested(
        stop_event
    )

    final_page = detect_sonar_page_state(
        page,
        stop_event=stop_event,
        on_progress=on_progress,
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
