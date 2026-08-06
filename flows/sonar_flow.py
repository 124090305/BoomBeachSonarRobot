from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import config
from controllers.adb_controller import AdbController


@dataclass(frozen=True)
class ScreenshotCheckResult:
    """截图检查流程的执行结果。"""

    serial: str
    path: Path
    width: int
    height: int


def run_screenshot_check(
    adb: AdbController | None = None,
    output_path: str | Path | None = None,
) -> ScreenshotCheckResult:
    """
    完成当前阶段的最小流程。

    流程：
    检查目录
    → 检查设备
    → 获取截图
    → 保存截图
    → 读取截图
    → 验证截图尺寸
    """
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

    return ScreenshotCheckResult(
        serial=controller.serial,
        path=screenshot_path,
        width=width,
        height=height,
    )