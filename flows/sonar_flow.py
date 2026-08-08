from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

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
    Point,
    SonarBoard,
    SonarStrategy,
)
from vision.image_match import (
    MatchResult,
    find_template,
    find_template_with_score,
)


logger = get_logger(__name__)


class SonarPageState(str, Enum):
    """当前声纳相关页面的大致状态。"""

    ACTIVITY_DETAIL = "activity_detail"
    HOME_SONAR_VISIBLE = "home_sonar_visible"
    HOME = "home"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ActivityEntryResult:
    """初始进入声纳活动后的结果。"""

    initial_state: SonarPageState
    final_state: SonarPageState
    sonar_point: Point | None
    weak_network_enabled: bool


@dataclass(frozen=True)
class ScreenshotCheckResult:
    """截图检查流程的执行结果。"""

    serial: str
    path: Path
    width: int
    height: int


@dataclass(frozen=True)
class ManualProbeContext:
    """
    一次人工判定探测已经完成实际页面操作后，
    留给人工填写 HIT / MISS 的上下文。
    """

    cell: Cell
    screen_point: Point
    before_path: Path
    after_path: Path


@dataclass(frozen=True)
class ManualProbeResult:
    """人工提交 HIT / MISS 后的最终结果。"""

    context: ManualProbeContext
    hit: bool
    newly_confirmed: tuple[ConfirmedShip, ...]


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
    """
    在同一张截图中检查两个声纳模板。

    返回：
    匹配结果
    + 两个模板中的最高相似度。
    """
    best_score = 0.0

    for template_name in (
        config_test.TEST_SONAR_TEMPLATE,
        config_test.TEST_SONAR_LABEL_TEMPLATE,
    ):
        match, score = (
            find_template_with_score(
                screenshot,
                _template_path(
                    template_name
                ),
                threshold=(
                    config_test
                    .TEST_SONAR_MATCH_THRESHOLD
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
) -> SonarPageState:
    """
    只截图检查，不进行任何点击。

    判断顺序：
    活动详情页
    → 主岛且声纳已经可见
    → 主岛
    → 未知页面
    """
    screenshot = (
        page.adb.read_screenshot()
    )

    quit_match = find_template(
        screenshot,
        _template_path(
            config_test
            .TEST_QUIT_ACTIVITY_TEMPLATE
        ),
        threshold=(
            config.DEFAULT_MATCH_THRESHOLD
        ),
    )

    if quit_match is not None:
        logger.info(
            "页面状态：活动详情页"
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
        logger.info(
            "页面状态：主岛，声纳已可见；"
            "中心=%s，相似度=%.3f",
            sonar_match.center,
            sonar_match.score,
        )
        return (
            SonarPageState
            .HOME_SONAR_VISIBLE
        )

    activity_match = find_template(
        screenshot,
        _template_path(
            config_test
            .TEST_ACTIVITY_BUTTON_TEMPLATE
        ),
        threshold=(
            config.DEFAULT_MATCH_THRESHOLD
        ),
    )

    if activity_match is not None:
        logger.info(
            "页面状态：主岛；"
            "活动按钮中心=%s；"
            "当前声纳最高相似度=%.3f",
            activity_match.center,
            sonar_score,
        )
        return SonarPageState.HOME

    logger.warning(
        "页面状态：未知；"
        "未识别到活动详情、声纳或主岛活动按钮；"
        "当前声纳最高相似度=%.3f",
        sonar_score,
    )

    return SonarPageState.UNKNOWN


def wait_home_island_ready(
    page: PageController,
    timeout: float | None = None,
) -> bool:
    """
    等待主岛就绪。

    当前用 activity_button.png 作为主岛已经加载完成的标志。
    """
    actual_timeout = (
        config_test.TEST_HOME_READY_TIMEOUT
        if timeout is None
        else float(timeout)
    )

    logger.info(
        "等待主岛就绪"
    )

    match = page.wait_template(
        config_test
        .TEST_ACTIVITY_BUTTON_TEMPLATE,
        timeout=actual_timeout,
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

    return True


def swipe_home_up(
    page: PageController,
) -> None:
    """主岛向上拖动画面，露出海边声纳。"""
    start_x, start_y = (
        config_test.TEST_HOME_SWIPE_START
    )
    end_x, end_y = (
        config_test.TEST_HOME_SWIPE_END
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
            config_test
            .TEST_HOME_SWIPE_DURATION_MS
        ),
    )


def wait_sonar_ready(
    page: PageController,
    timeout: float | None = None,
) -> MatchResult | None:
    """
    等主岛加载完成，然后确认声纳是否出现。

    声纳已经在画面中：
    直接返回。

    声纳不在画面中：
    主岛上划一次，再持续等待。
    """
    actual_timeout = (
        config_test.TEST_SONAR_WAIT_TIMEOUT
        if timeout is None
        else float(timeout)
    )

    if not wait_home_island_ready(
        page
    ):
        return None

    screenshot = (
        page.adb.read_screenshot()
    )

    match, score = (
        _find_sonar_match(
            screenshot
        )
    )

    if match is not None:
        logger.info(
            "声纳已经在画面中："
            "中心=%s，相似度=%.3f",
            match.center,
            match.score,
        )
        return match

    logger.info(
        "当前未看到声纳，"
        "最高相似度=%.3f，执行主岛上划",
        score,
    )

    swipe_home_up(
        page
    )

    deadline = (
        time.monotonic()
        + actual_timeout
    )

    best_score_seen = score
    attempts = 0

    while True:
        attempts += 1

        screenshot = (
            page.adb.read_screenshot()
        )

        match, score = (
            _find_sonar_match(
                screenshot
            )
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
                config_test
                .TEST_SONAR_MATCH_THRESHOLD,
            )
            return None

        page.adb.delay(
            min(
                config.PAGE_POLL_INTERVAL,
                remaining,
            )
        )


def dismiss_activity_start_hint(
    page: PageController,
) -> None:
    """点击棋盘外安全点，关闭“点击任意地方开始”提示。"""
    page.adb.delay(
        config_test
        .TEST_ACTIVITY_TAP_TO_START_DELAY
    )

    x, y = (
        config_test
        .TEST_ACTIVITY_TAP_TO_START_POINT
    )

    page.click_point(
        x,
        y,
        wait_seconds=(
            config_test
            .TEST_ACTIVITY_TAP_TO_START_AFTER_DELAY
        ),
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
) -> ActivityEntryResult:
    """
    从主岛初次进入声纳活动。

    流程：
    检查当前页面
    → 等主岛活动按钮
    → 检查声纳
    → 必要时主岛上划
    → 点击活动按钮
    → 开启弱网
    → 活动列表上划两次
    → 点击声纳活动详情入口
    → 等待退出按钮
    → 关闭“点击任意地方开始”
    → 再次确认活动详情页

    当前阶段不包含重启游戏重试。
    """
    config.ensure_directories()
    adb.ensure_device_online()

    initial_state = (
        detect_sonar_page_state(
            page
        )
    )

    network_state = (
        network.get_state()
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

            final_state = (
                detect_sonar_page_state(
                    page
                )
            )

            return ActivityEntryResult(
                initial_state=initial_state,
                final_state=final_state,
                sonar_point=None,
                weak_network_enabled=True,
            )

        sonar_match = wait_sonar_ready(
            page
        )

        if sonar_match is None:
            raise RuntimeError(
                "初始进入活动失败："
                "主岛上没有检测到声纳"
            )

        activity_match = (
            page.wait_and_click(
                config_test
                .TEST_ACTIVITY_BUTTON_TEMPLATE,
                timeout=(
                    config_test
                    .TEST_ACTIVITY_BUTTON_TIMEOUT
                ),
                wait_seconds=(
                    config_test
                    .TEST_ACTIVITY_BUTTON_CLICK_DELAY
                ),
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

        adb.delay(
            config_test
            .TEST_INITIAL_WEAK_APPLY_DELAY
        )

        adb.delay(
            config_test
            .TEST_ACTIVITY_LIST_BEFORE_SWIPE_DELAY
        )

        start_x, start_y = (
            config_test
            .TEST_ACTIVITY_LIST_SWIPE_START
        )
        end_x, end_y = (
            config_test
            .TEST_ACTIVITY_LIST_SWIPE_END
        )

        for index in range(
            config_test
            .TEST_ACTIVITY_LIST_SWIPE_COUNT
        ):
            logger.info(
                "活动列表上划：%s/%s",
                index + 1,
                config_test
                .TEST_ACTIVITY_LIST_SWIPE_COUNT,
            )

            page.swipe(
                start_x,
                start_y,
                end_x,
                end_y,
                duration_ms=(
                    config_test
                    .TEST_ACTIVITY_LIST_SWIPE_DURATION_MS
                ),
                wait_seconds=(
                    config_test
                    .TEST_ACTIVITY_LIST_SWIPE_INTERVAL
                ),
            )

        adb.delay(
            config_test
            .TEST_ACTIVITY_DETAIL_ENTRY_DELAY
        )

        detail_x, detail_y = (
            config_test
            .TEST_ACTIVITY_DETAIL_ENTRY_POINT
        )

        page.click_point(
            detail_x,
            detail_y,
            wait_seconds=0,
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
                    config_test
                    .TEST_ACTIVITY_DETAIL_READY_TIMEOUT
                ),
            )
        )

        if not ready:
            raise RuntimeError(
                "初始进入活动失败："
                "点击详情入口后没有检测到退出按钮"
            )

        dismiss_activity_start_hint(
            page
        )

        final_state = (
            detect_sonar_page_state(
                page
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

    except Exception:
        # 如果弱网原本就是关闭的，
        # 且本流程开启弱网后又在中途失败，
        # 把网络恢复到进入流程之前的状态。
        if weak_enabled_by_flow:
            try:
                network.disable_weak_network()
            except Exception:
                logger.exception(
                    "初始进入活动失败后，"
                    "关闭弱网也失败"
                )

        raise


def run_screenshot_check(
    adb: AdbController | None = None,
    output_path: str | Path | None = None,
) -> ScreenshotCheckResult:
    """
    完成当前阶段的最小截图流程。

    流程：
    检查目录
    → 检查设备
    → 获取截图
    → 保存截图
    → 读取截图
    → 验证截图尺寸
    """
    logger.info(
        "开始截图检查流程"
    )

    config.ensure_directories()

    controller = (
        adb
        if adb is not None
        else AdbController()
    )

    controller.ensure_device_online()

    if output_path is None:
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_path = (
            config.SCREENSHOT_DIR
            / f"screenshot_{timestamp}.png"
        )

    screenshot_path = controller.take_screenshot(
        output_path
    )

    image = controller.read_image(
        screenshot_path
    )

    height, width = image.shape[:2]

    result = ScreenshotCheckResult(
        serial=controller.serial,
        path=screenshot_path,
        width=width,
        height=height,
    )

    logger.info(
        "截图检查完成：设备=%s，尺寸=%sx%s，文件=%s",
        result.serial,
        result.width,
        result.height,
        result.path,
    )

    return result


def wait_activity_detail_ready(
    page: PageController,
    timeout: float | None = None,
) -> bool:
    """
    等待声纳活动详情页就绪。

    当前先使用退出按钮 quit_activity.png
    作为“已经处于活动详情页”的判断标志。
    """
    actual_timeout = (
        config_test.TEST_ACTIVITY_DETAIL_READY_TIMEOUT
        if timeout is None
        else float(timeout)
    )

    match = page.wait_template(
        config_test.TEST_QUIT_ACTIVITY_TEMPLATE,
        timeout=actual_timeout,
    )

    if match is None:
        logger.warning(
            "活动详情页未就绪：未找到 %s",
            config_test.TEST_QUIT_ACTIVITY_TEMPLATE,
        )
        return False

    logger.info(
        "活动详情页已就绪：退出按钮中心=%s",
        match.center,
    )

    return True


def reenter_activity_for_probe(
    adb: AdbController,
    page: PageController,
) -> None:
    """
    退出活动详情后重新进入当前声纳活动。

    当前完全按参考项目 re_enter=True 的最小逻辑处理：

    等待活动按钮
    → 点击活动按钮
    → 等待短暂页面展开
    → 点击右下角活动详情入口
    → 等待退出按钮重新出现
    → 点击棋盘外安全点关闭开始提示
    """
    logger.info(
        "开始重新进入声纳活动"
    )

    activity_match = page.wait_and_click(
        config_test.TEST_ACTIVITY_BUTTON_TEMPLATE,
        timeout=config_test.TEST_ACTIVITY_BUTTON_TIMEOUT,
        wait_seconds=(
            config_test.TEST_ACTIVITY_BUTTON_CLICK_DELAY
        ),
    )

    if activity_match is None:
        raise RuntimeError(
            "重新进入活动失败："
            f"未找到 {config_test.TEST_ACTIVITY_BUTTON_TEMPLATE}"
        )

    logger.info(
        "已点击活动按钮：中心=%s，相似度=%.3f",
        activity_match.center,
        activity_match.score,
    )

    adb.delay(
        config_test.TEST_ACTIVITY_DETAIL_ENTRY_DELAY
    )

    detail_x, detail_y = (
        config_test.TEST_ACTIVITY_DETAIL_ENTRY_POINT
    )

    page.click_point(
        detail_x,
        detail_y,
        wait_seconds=0,
    )

    logger.info(
        "已点击活动详情入口：(%s, %s)",
        detail_x,
        detail_y,
    )

    ready = wait_activity_detail_ready(
        page,
        timeout=(
            config_test.TEST_ACTIVITY_DETAIL_READY_TIMEOUT
        ),
    )

    if not ready:
        raise RuntimeError(
            "重新进入活动失败："
            "点击活动详情入口后没有检测到退出按钮"
        )

    dismiss_activity_start_hint(
        page
    )

    logger.info(
        "重新进入声纳活动完成"
    )


def prepare_manual_probe_once(
    adb: AdbController,
    page: PageController,
    board: SonarBoard,
    strategy: SonarStrategy,
    output_dir: str | Path | None = None,
) -> ManualProbeContext:
    """
    执行一次“等待人工判定结果”的真实单发探测。

    流程：
    策略拿下一格
    → 逻辑格映射到模拟器坐标
    → 确认当前在活动详情页
    → 点击前截图
    → 点击目标格
    → 点击退出活动
    → 重新进入活动
    → 点击后截图
    → 返回上下文，等待人工填写 HIT / MISS

    注意：
    这个函数不会调用 strategy.report_result()。
    只有人工确认结果后，才能调用 submit_manual_probe_result()。
    页面途中出现异常时，策略 pending_cell 会继续保留，
    方便修复页面后重试同一格。
    """
    logger.info(
        "开始单发人工探测流程"
    )

    config.ensure_directories()
    adb.ensure_device_online()

    if not board.has_complete_mapping:
        raise RuntimeError(
            "棋盘坐标映射不完整，"
            "无法执行真实格点点击"
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

    logger.info(
        "本次策略选格：逻辑格=%s，模拟器坐标=(%s, %s)",
        cell,
        x,
        y,
    )

    ready = wait_activity_detail_ready(
        page,
        timeout=(
            config_test.TEST_PROBE_DETAIL_READY_TIMEOUT
        ),
    )

    if not ready:
        current_state = (
            detect_sonar_page_state(
                page
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

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    prefix = (
        f"probe_{timestamp}"
        f"_r{row}_c{col}"
    )

    before_path = (
        probe_dir
        / f"{prefix}_before.png"
    )

    after_path = (
        probe_dir
        / f"{prefix}_after.png"
    )

    logger.info(
        "点击目标格前截图"
    )

    saved_before = adb.take_screenshot(
        before_path
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
            config_test.TEST_PROBE_AFTER_CLICK_DELAY
        ),
    )

    logger.info(
        "准备退出当前活动详情页"
    )

    quit_match = page.click_template(
        config_test.TEST_QUIT_ACTIVITY_TEMPLATE,
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
    )

    logger.info(
        "重新进入活动后截图"
    )

    saved_after = adb.take_screenshot(
        after_path
    )

    context = ManualProbeContext(
        cell=cell,
        screen_point=(x, y),
        before_path=saved_before,
        after_path=saved_after,
    )

    logger.info(
        "单发页面操作完成："
        "cell=%s，before=%s，after=%s；"
        "等待人工填写 HIT / MISS",
        context.cell,
        context.before_path,
        context.after_path,
    )

    return context


def submit_manual_probe_result(
    strategy: SonarStrategy,
    context: ManualProbeContext,
    *,
    hit: bool,
) -> ManualProbeResult:
    """
    把人工确认的 HIT / MISS 交回策略。

    这里才真正更新：
    SonarBoard
    + strategy 内部状态。
    """
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
