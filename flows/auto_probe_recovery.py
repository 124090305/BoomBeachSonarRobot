from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event

import cv2

import config

from controllers.adb_controller import AdbController
from controllers.network_controller import NetworkController
from controllers.page_controller import PageController
from logger import get_logger
from sonar_config import AUTO_PROBE_CONFIG
from stop_control import (
    StopRequestedError,
    interruptible_wait,
    raise_if_stop_requested,
)
from vision import MatchResult, find_template_with_score

from .activity_flow import enter_activity_initial
from .auto_probe_ready import ensure_auto_probe_ready
from .sonar_page import (
    SonarPageState,
    detect_sonar_page_state,
)


logger = get_logger(__name__)


@dataclass(frozen=True)
class ProbeRecoveryResult:
    """一次探测结束后的网络与页面恢复结果。"""

    mode: str
    retry_found: bool | None
    final_state: SonarPageState
    weak_network_enabled: bool
    reject_network_enabled: bool


def wait_retry_with_failure_capture(
    adb: AdbController,
    *,
    stop_event: Event | None = None,
) -> tuple[MatchResult | None, Path | None]:
    """等待 retry；超时时保存相似度最高的一帧。"""
    raise_if_stop_requested(
        stop_event
    )

    template_path = (
        config.TEMPLATE_DIR
        / AUTO_PROBE_CONFIG.retry_template
    )

    if not template_path.is_file():
        raise FileNotFoundError(
            f"缺少 retry 模板：{template_path}"
        )

    timeout = float(
        AUTO_PROBE_CONFIG.retry_wait_timeout
    )
    threshold = float(
        AUTO_PROBE_CONFIG.retry_match_threshold
    )
    poll_interval = float(
        config.PAGE_POLL_INTERVAL
    )

    deadline = time.monotonic() + timeout
    attempts = 0
    best_score_seen = 0.0
    best_screenshot = None

    logger.info(
        "开始等待模板：%s，超时=%.1f秒，阈值=%.3f",
        template_path.name,
        timeout,
        threshold,
    )

    while True:
        raise_if_stop_requested(
            stop_event
        )

        attempts += 1
        screenshot = adb.read_screenshot()

        match, best_score = find_template_with_score(
            screenshot,
            template_path,
            threshold=threshold,
        )

        raise_if_stop_requested(
            stop_event
        )

        if (
            best_screenshot is None
            or best_score > best_score_seen
        ):
            best_score_seen = best_score
            best_screenshot = screenshot.copy()

        if match is not None:
            logger.info(
                "等待模板成功：%s，相似度=%.3f，中心=%s，检测次数=%s",
                template_path.name,
                match.score,
                match.center,
                attempts,
            )
            return match, None

        remaining = deadline - time.monotonic()

        if remaining <= 0:
            failure_dir = (
                config.SCREENSHOT_DIR
                / AUTO_PROBE_CONFIG.retry_failure_dir_name
            )
            failure_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )
            failure_path = (
                failure_dir
                / (
                    f"retry_fail_{timestamp}"
                    f"_score_{best_score_seen:.3f}.png"
                )
            )

            if best_screenshot is not None:
                ok = cv2.imwrite(
                    str(failure_path),
                    best_screenshot,
                )

                if not ok:
                    raise RuntimeError(
                        "retry 识别失败截图保存失败："
                        f"{failure_path}"
                    )

            logger.warning(
                "等待模板超时：%s，%.1f秒内未出现，"
                "最高相似度=%.3f，阈值=%.3f，检测次数=%s，"
                "失败截图=%s",
                template_path.name,
                timeout,
                best_score_seen,
                threshold,
                attempts,
                failure_path,
            )

            return None, failure_path

        interruptible_wait(
            min(
                poll_interval,
                remaining,
            ),
            stop_event,
        )


def recover_after_hit_once(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    *,
    stop_event: Event | None = None,
) -> ProbeRecoveryResult:
    """HIT 后恢复联网等待，再整理到下一发弱网状态。"""
    raise_if_stop_requested(
        stop_event
    )

    logger.info(
        "检测到 HIT：跳过 REJECT/retry，直接恢复正常联网"
    )

    state = network.get_state()

    raise_if_stop_requested(
        stop_event
    )

    if state.reject_enabled:
        raise RuntimeError(
            "HIT 恢复前 REJECT 已经开启，当前网络状态异常"
        )

    if not state.weak_enabled:
        raise RuntimeError(
            "HIT 恢复前弱网 DROP 没有开启"
        )

    network.restore_network()

    raise_if_stop_requested(
        stop_event
    )

    online_wait = float(
        AUTO_PROBE_CONFIG.hit_online_wait_seconds
    )

    logger.info(
        "HIT 已恢复正常联网，等待 %.1f 秒让结果稳定",
        online_wait,
    )

    interruptible_wait(
        online_wait,
        stop_event,
    )

    ensure_auto_probe_ready(
        adb=adb,
        page=page,
        network=network,
        stop_event=stop_event,
    )

    final_network = network.get_state()

    raise_if_stop_requested(
        stop_event
    )

    final_state = detect_sonar_page_state(
        page,
        stop_event=stop_event,
    )

    if (
        final_state
        != SonarPageState.ACTIVITY_DETAIL
    ):
        raise RuntimeError(
            "HIT 恢复失败：5 秒联网后没有回到活动详情页"
        )

    if final_network.reject_enabled:
        raise RuntimeError(
            "HIT 恢复失败：REJECT 意外处于开启状态"
        )

    if not final_network.weak_enabled:
        raise RuntimeError(
            "HIT 恢复失败：弱网 DROP 没有重新开启"
        )

    result = ProbeRecoveryResult(
        mode="hit_online_wait",
        retry_found=None,
        final_state=final_state,
        weak_network_enabled=(
            final_network.weak_enabled
        ),
        reject_network_enabled=(
            final_network.reject_enabled
        ),
    )

    logger.info(
        "HIT 恢复完成：联网等待=%.1f秒，page=%s，weak=%s，reject=%s",
        online_wait,
        result.final_state.value,
        result.weak_network_enabled,
        result.reject_network_enabled,
    )

    return result


def _recover_after_strategy_done_once(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    *,
    hit: bool,
    stop_event: Event | None = None,
) -> ProbeRecoveryResult:
    """策略完成时提交最后结果并保持正常联网。"""
    raise_if_stop_requested(
        stop_event
    )

    logger.info(
        "策略已确认全部潜艇：进入胜利处理边界，停止重新弱网和重进活动"
    )

    network.restore_network()

    raise_if_stop_requested(
        stop_event
    )

    if hit:
        online_wait = float(
            AUTO_PROBE_CONFIG.hit_online_wait_seconds
        )
        logger.info(
            "最后一发 HIT 已恢复正常联网，等待 %.1f 秒完成结算",
            online_wait,
        )
        interruptible_wait(
            online_wait,
            stop_event,
        )

    final_network = network.get_state()

    raise_if_stop_requested(
        stop_event
    )

    final_state = detect_sonar_page_state(
        page,
        stop_event=stop_event,
    )

    result = ProbeRecoveryResult(
        mode="strategy_done_online",
        retry_found=None,
        final_state=final_state,
        weak_network_enabled=final_network.weak_enabled,
        reject_network_enabled=final_network.reject_enabled,
    )

    logger.info(
        "策略完成后的临时收尾完成：page=%s，weak=%s，reject=%s",
        result.final_state.value,
        result.weak_network_enabled,
        result.reject_network_enabled,
    )

    return result


def recover_after_miss_once(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    *,
    stop_event: Event | None = None,
) -> ProbeRecoveryResult:
    """执行 MISS 后的 REJECT、retry、联网和页面恢复链。"""
    raise_if_stop_requested(
        stop_event
    )

    logger.info(
        "开始执行 MISS 恢复链"
    )

    state = network.get_state()

    raise_if_stop_requested(
        stop_event
    )

    if state.reject_enabled:
        raise RuntimeError(
            "进入恢复链前 REJECT 已经开启，"
            "当前网络状态异常"
        )

    if not state.weak_enabled:
        raise RuntimeError(
            "进入恢复链前弱网 DROP 没有开启"
        )

    retry_match = None
    retry_failure_path: Path | None = None
    reject_enabled_by_flow = False

    try:
        network.enable_reject_network()
        reject_enabled_by_flow = True

        raise_if_stop_requested(
            stop_event
        )

        retry_match, retry_failure_path = (
            wait_retry_with_failure_capture(
                adb=adb,
                stop_event=stop_event,
            )
        )

    except StopRequestedError:
        raise

    except Exception:
        if reject_enabled_by_flow:
            try:
                network.disable_reject_network()
            except Exception:
                logger.exception(
                    "等待 retry 结束后关闭 REJECT 失败"
                )
                raise

        raise

    if reject_enabled_by_flow:
        network.disable_reject_network()
        reject_enabled_by_flow = False

    raise_if_stop_requested(
        stop_event
    )

    if retry_match is None:
        logger.error(
            "REJECT 后没有检测到 retry；"
            "已关闭 REJECT，弱网 DROP 保持开启"
        )
        raise RuntimeError(
            "单发恢复失败："
            f"{AUTO_PROBE_CONFIG.retry_wait_timeout:g} 秒内"
            "没有出现 retry 按钮；"
            f"失败截图={retry_failure_path}"
        )

    interruptible_wait(
        AUTO_PROBE_CONFIG.retry_before_click_delay,
        stop_event,
    )

    page.click_match(
        retry_match,
        wait_seconds=(
            AUTO_PROBE_CONFIG.retry_after_click_delay
        ),
        stop_event=stop_event,
    )

    raise_if_stop_requested(
        stop_event
    )

    logger.info(
        "已点击 retry：中心=%s，相似度=%.3f",
        retry_match.center,
        retry_match.score,
    )

    network.disable_weak_network()

    raise_if_stop_requested(
        stop_event
    )

    entry = enter_activity_initial(
        adb=adb,
        page=page,
        network=network,
        stop_event=stop_event,
    )

    final_network = network.get_state()

    raise_if_stop_requested(
        stop_event
    )

    final_state = detect_sonar_page_state(
        page,
        stop_event=stop_event,
    )

    if (
        entry.final_state
        != SonarPageState.ACTIVITY_DETAIL
        or final_state
        != SonarPageState.ACTIVITY_DETAIL
    ):
        raise RuntimeError(
            "单发恢复失败："
            "恢复后没有回到活动详情页"
        )

    if final_network.reject_enabled:
        raise RuntimeError(
            "单发恢复失败："
            "恢复后 REJECT 仍然开启"
        )

    if not final_network.weak_enabled:
        raise RuntimeError(
            "单发恢复失败："
            "恢复后弱网 DROP 没有重新开启"
        )

    result = ProbeRecoveryResult(
        mode="miss_retry",
        retry_found=True,
        final_state=final_state,
        weak_network_enabled=(
            final_network.weak_enabled
        ),
        reject_network_enabled=(
            final_network.reject_enabled
        ),
    )

    logger.info(
        "MISS 恢复完成："
        "page=%s，weak=%s，reject=%s",
        result.final_state.value,
        result.weak_network_enabled,
        result.reject_network_enabled,
    )

    return result


__all__ = [
    "ProbeRecoveryResult",
    "recover_after_hit_once",
    "recover_after_miss_once",
    "wait_retry_with_failure_capture",
]
