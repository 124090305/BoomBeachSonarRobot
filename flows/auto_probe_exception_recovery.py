from __future__ import annotations

from threading import Event

from controllers.adb_controller import AdbController
from controllers.game_controller import GameController
from controllers.network_controller import NetworkController
from controllers.page_controller import PageController
from logger import get_logger
from sonar_config import AUTO_PROBE_CONFIG
from stop_control import raise_if_stop_requested

from .auto_probe_ready import ensure_auto_probe_ready
from .auto_probe_recovery import ProbeRecoveryResult
from .sonar_page import (
    SonarPageState,
    detect_sonar_page_state,
)


logger = get_logger(__name__)


def restart_auto_probe_once(
    game: GameController,
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    *,
    attempt: int,
    max_attempts: int,
    stop_event: Event | None = None,
) -> ProbeRecoveryResult:
    """复用游戏重启，并恢复到下一发可探测状态。"""
    logger.warning(
        "自动探测异常恢复：开始第 %s/%s 次重启",
        attempt,
        max_attempts,
    )

    game.restart_game(stop_event=stop_event)

    raise_if_stop_requested(
        stop_event
    )

    ensure_auto_probe_ready(
        adb=adb,
        page=page,
        network=network,
        stop_event=stop_event,
    )

    final_state = detect_sonar_page_state(
        page,
        stop_event=stop_event,
    )
    final_network = network.get_state()

    raise_if_stop_requested(
        stop_event
    )

    if final_state != SonarPageState.ACTIVITY_DETAIL:
        raise RuntimeError(
            "异常重启恢复失败："
            f"最终页面={final_state.value}"
        )

    if final_network.reject_enabled:
        raise RuntimeError(
            "异常重启恢复失败：REJECT 仍然开启"
        )

    if not final_network.weak_enabled:
        raise RuntimeError(
            "异常重启恢复失败：弱网 DROP 没有重新开启"
        )

    result = ProbeRecoveryResult(
        mode="exception_restart",
        retry_found=None,
        final_state=final_state,
        weak_network_enabled=final_network.weak_enabled,
        reject_network_enabled=final_network.reject_enabled,
    )

    logger.info(
        "自动探测异常重启恢复成功：attempt=%s，page=%s，weak=%s，reject=%s",
        attempt,
        result.final_state.value,
        result.weak_network_enabled,
        result.reject_network_enabled,
    )

    return result


def restore_auto_probe_network_safely(
    network: NetworkController,
) -> bool:
    """停止自动循环前清理并核验 DROP / REJECT。"""
    max_attempts = max(
        1,
        int(AUTO_PROBE_CONFIG.max_restart_attempts),
    )

    for attempt in range(1, max_attempts + 1):
        try:
            network.restore_network()
            final_state = network.get_state()
        except Exception:
            logger.exception(
                "自动循环安全停止时第 %s/%s 次恢复或核验网络失败",
                attempt,
                max_attempts,
            )
            continue

        if (
            final_state.weak_enabled
            or final_state.reject_enabled
        ):
            logger.error(
                "自动循环安全停止后网络规则仍存在："
                "attempt=%s/%s，weak=%s，reject=%s",
                attempt,
                max_attempts,
                final_state.weak_enabled,
                final_state.reject_enabled,
            )
            continue

        logger.info(
            "自动循环安全停止清理完成：DROP=False，REJECT=False"
        )
        return True

    logger.critical(
        "自动循环安全停止网络清理耗尽 %s 次尝试",
        max_attempts,
    )
    return False


__all__ = [
    "restart_auto_probe_once",
    "restore_auto_probe_network_safely",
]
