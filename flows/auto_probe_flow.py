from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import time

import cv2

import config
import config_test

from controllers.adb_controller import (
    AdbController,
)
from controllers.network_controller import (
    NetworkController,
)
from controllers.page_controller import (
    PageController,
)
from logger import get_logger
from sonar import (
    Cell,
    ConfirmedShip,
    SonarBoard,
    SonarStrategy,
)
from vision import (
    DiamondHitConfig,
    DiamondHitResult,
    MatchResult,
    classify_diamond_hit,
    find_template_with_score,
)

from .sonar_flow import (
    ManualProbeContext,
    SonarPageState,
    detect_sonar_page_state,
    enter_activity_initial,
    prepare_manual_probe_once,
)


logger = get_logger(__name__)


@dataclass(frozen=True)
class ProbeRecoveryResult:
    """一次探测结束后的网络与页面恢复结果。"""

    retry_found: bool
    final_state: SonarPageState
    weak_network_enabled: bool
    reject_network_enabled: bool


@dataclass(frozen=True)
class AutoProbeOnceResult:
    """完整自动一发探测的结果。"""

    context: ManualProbeContext
    recognition: DiamondHitResult
    hit: bool
    newly_confirmed: tuple[ConfirmedShip, ...]
    recovery: ProbeRecoveryResult
    next_cell: Cell | None


def recognition_state_is_hit(
    state: str,
) -> bool:
    """
    把 diamond_hit 的识别状态转换成策略需要的 HIT / MISS。

    当前正式规则：
    hit -> HIT
    其余状态 -> MISS
    """
    return str(state).strip().lower() == "hit"


def build_test_hit_config(
    *,
    debug: bool = True,
    debug_dir: str | Path | None = None,
) -> DiamondHitConfig:
    """创建当前固定 10x10 测试关卡使用的命中识别参数。"""
    actual_debug_dir = (
        Path(debug_dir)
        if debug_dir is not None
        else (
            config.SCREENSHOT_DIR
            / config_test.TEST_DIAMOND_DEBUG_DIR_NAME
        )
    )

    return DiamondHitConfig(
        diamond_w=config_test.TEST_DIAMOND_W,
        diamond_h=config_test.TEST_DIAMOND_H,
        search_radius=(
            config_test.TEST_DIAMOND_SEARCH_RADIUS
        ),
        debug=bool(debug),
        debug_dir=str(actual_debug_dir),
    )


def ensure_auto_probe_ready(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
) -> None:
    """
    把当前游戏整理到“一发探测可以开始”的状态。

    最终要求：
    活动详情页
    + 弱网 DROP 开启
    + REJECT 关闭
    """
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
        # enter_activity_initial() 的设计是先正常打开活动列表，
        # 再在正确节点开启弱网。
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



def wait_retry_with_failure_capture(
    adb: AdbController,
) -> tuple[MatchResult | None, Path | None]:
    """
    等待 retry.png 出现。

    等待期间持续记录“相似度最高”的那一帧。
    如果最终超时，就把最高分画面保存到 retry_failure 目录，
    方便直接检查模板为什么没有识别成功。
    """
    template_path = (
        config.TEMPLATE_DIR
        / config_test.TEST_RETRY_TEMPLATE
    )

    if not template_path.is_file():
        raise FileNotFoundError(
            f"缺少 retry 模板：{template_path}"
        )

    timeout = float(
        config_test.TEST_RETRY_WAIT_TIMEOUT
    )
    threshold = float(
        config_test.TEST_RETRY_MATCH_THRESHOLD
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
        attempts += 1
        screenshot = adb.read_screenshot()

        match, best_score = find_template_with_score(
            screenshot,
            template_path,
            threshold=threshold,
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
                / config_test.TEST_RETRY_FAILURE_DIR_NAME
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

        adb.delay(
            min(
                poll_interval,
                remaining,
            )
        )


def recover_after_probe_once(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
) -> ProbeRecoveryResult:
    """
    完成一次探测后的 REJECT / retry / 网络 / 页面恢复。

    流程：
    确认弱网仍开启
    -> 开启 REJECT
    -> 等 retry
    -> 关闭 REJECT
    -> 点击 retry
    -> 关闭弱网
    -> 自动重新进入声纳活动
    -> 重新开启弱网
    -> 检查活动详情页

    如果 retry 没有出现：
    关闭 REJECT，但保留弱网 DROP，直接报错。
    这样测试异常时不会主动把本次请求放回正常网络。
    """
    logger.info(
        "开始执行单发探测恢复链"
    )

    state = network.get_state()

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

        retry_match, retry_failure_path = (
            wait_retry_with_failure_capture(
                adb=adb,
            )
        )

    finally:
        if reject_enabled_by_flow:
            try:
                network.disable_reject_network()
            except Exception:
                logger.exception(
                    "等待 retry 结束后关闭 REJECT 失败"
                )
                raise

    if retry_match is None:
        logger.error(
            "REJECT 后没有检测到 retry；"
            "已关闭 REJECT，弱网 DROP 保持开启"
        )
        raise RuntimeError(
            "单发恢复失败："
            f"{config_test.TEST_RETRY_WAIT_TIMEOUT:g} 秒内"
            "没有出现 retry 按钮；"
            f"失败截图={retry_failure_path}"
        )

    adb.delay(
        config_test.TEST_RETRY_BEFORE_CLICK_DELAY
    )

    page.click_match(
        retry_match,
        wait_seconds=(
            config_test.TEST_RETRY_AFTER_CLICK_DELAY
        ),
    )

    logger.info(
        "已点击 retry：中心=%s，相似度=%.3f",
        retry_match.center,
        retry_match.score,
    )

    # retry 已经点击后，再释放 DROP，恢复正常联网。
    network.disable_weak_network()

    # 复用现有入口流程。
    # 它会根据当前位置重新找到声纳，并在正确节点重新开启弱网。
    entry = enter_activity_initial(
        adb=adb,
        page=page,
        network=network,
    )

    final_network = network.get_state()
    final_state = detect_sonar_page_state(
        page
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
        "单发探测恢复完成："
        "page=%s，weak=%s，reject=%s",
        result.final_state.value,
        result.weak_network_enabled,
        result.reject_network_enabled,
    )

    return result


def run_auto_probe_once(
    adb: AdbController,
    page: PageController,
    network: NetworkController,
    board: SonarBoard,
    strategy: SonarStrategy,
    *,
    hit_config: DiamondHitConfig | None = None,
    output_dir: str | Path | None = None,
    recognition_index: int = 0,
) -> AutoProbeOnceResult:
    """
    执行一整发自动探测，并恢复到下一发可以继续的状态。

    完整链条：
    页面 / 网络准备
    -> 策略选格
    -> before 截图
    -> 点击目标格
    -> 退出活动
    -> 重进活动
    -> after 截图
    -> diamond_hit 自动判断
    -> 写回策略
    -> REJECT
    -> 等 retry
    -> 关闭 REJECT
    -> 点击 retry
    -> 关闭弱网
    -> 重进活动
    -> 再开弱网
    -> 选择下一格

    当前识别结果解释规则：
    state == "hit" -> HIT
    其他状态 -> MISS
    """
    logger.info(
        "开始完整自动单发探测"
    )

    ensure_auto_probe_ready(
        adb=adb,
        page=page,
        network=network,
    )

    actual_output_dir = (
        Path(output_dir)
        if output_dir is not None
        else (
            config.SCREENSHOT_DIR
            / config_test.TEST_AUTO_PROBE_DIR_NAME
        )
    )

    context = prepare_manual_probe_once(
        adb=adb,
        page=page,
        board=board,
        strategy=strategy,
        output_dir=actual_output_dir,
    )

    before = adb.read_image(
        context.before_path
    )
    after = adb.read_image(
        context.after_path
    )

    classifier_config = (
        hit_config
        if hit_config is not None
        else build_test_hit_config()
    )

    recognition = classify_diamond_hit(
        before_screenshot=before,
        after_screenshot=after,
        center=context.screen_point,
        config=classifier_config,
        index=int(recognition_index),
    )

    hit = recognition_state_is_hit(
        recognition.state
    )

    logger.info(
        "自动命中判断："
        "cell=%s，state=%s，confidence=%.3f，"
        "score=%.3f -> %s",
        context.cell,
        recognition.state,
        recognition.confidence,
        recognition.score,
        "HIT" if hit else "MISS",
    )

    pending = strategy.pending_cell

    if pending != context.cell:
        raise RuntimeError(
            "自动识别结果对应格与策略 pending_cell 不一致："
            f"pending={pending}, context={context.cell}"
        )

    newly_confirmed = tuple(
        strategy.report_result(
            context.cell,
            hit=hit,
        )
    )

    if newly_confirmed:
        logger.info(
            "本发新确认潜艇：%s",
            [
                {
                    "length": ship.length,
                    "direction": ship.direction,
                    "cells": ship.cells,
                }
                for ship in newly_confirmed
            ],
        )

    recovery = recover_after_probe_once(
        adb=adb,
        page=page,
        network=network,
    )

    next_cell = strategy.choose_next_cell()

    result = AutoProbeOnceResult(
        context=context,
        recognition=recognition,
        hit=hit,
        newly_confirmed=newly_confirmed,
        recovery=recovery,
        next_cell=next_cell,
    )

    logger.info(
        "完整自动单发完成："
        "cell=%s -> %s，next=%s，strategy_done=%s",
        result.context.cell,
        "HIT" if result.hit else "MISS",
        result.next_cell,
        strategy.done,
    )

    return result
