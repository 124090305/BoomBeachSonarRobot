from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import config
import config_test

from controllers.adb_controller import (
    AdbController,
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


logger = get_logger(__name__)


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

    adb.delay(
        config_test.TEST_ACTIVITY_TAP_TO_START_DELAY
    )

    safe_x, safe_y = (
        config_test.TEST_ACTIVITY_TAP_TO_START_POINT
    )

    page.click_point(
        safe_x,
        safe_y,
        wait_seconds=(
            config_test.TEST_ACTIVITY_TAP_TO_START_AFTER_DELAY
        ),
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
        raise RuntimeError(
            "执行单发探测前没有检测到活动详情页。"
            "请先手动进入声纳棋盘页面再运行测试。"
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
