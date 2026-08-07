from __future__ import annotations

import time
from pathlib import Path

import config
from controllers.adb_controller import AdbController
from vision.image_match import MatchResult, find_template


class PageController:
    """组合截图、模板匹配、点击和滑动等页面操作。"""

    def __init__(self, adb: AdbController) -> None:
        self.adb = adb

    def click_point(
        self,
        x: int,
        y: int,
        wait_seconds: float = config.PAGE_ACTION_DELAY,
    ) -> None:
        """点击固定坐标，并等待页面响应。"""
        x = int(x)
        y = int(y)

        if x < 0 or y < 0:
            raise ValueError("点击坐标不能小于 0")

        self.adb.click(x, y)
        self._delay(wait_seconds)

    def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 300,
        wait_seconds: float = config.PAGE_ACTION_DELAY,
    ) -> None:
        """执行滑动，并等待页面响应。"""
        duration_ms = int(duration_ms)

        if duration_ms <= 0:
            raise ValueError("滑动时间必须大于 0")

        self.adb.swipe(
            int(start_x),
            int(start_y),
            int(end_x),
            int(end_y),
            duration_ms,
        )

        self._delay(wait_seconds)

    def find_template(
        self,
        template_path: str | Path,
        threshold: float = config.DEFAULT_MATCH_THRESHOLD,
    ) -> MatchResult | None:
        """截取当前画面并查找模板。"""
        template = self._resolve_template_path(template_path)
        screenshot = self.adb.read_screenshot()

        return find_template(
            screenshot,
            template,
            threshold=threshold,
        )

    def template_exists(
        self,
        template_path: str | Path,
        threshold: float = config.DEFAULT_MATCH_THRESHOLD,
    ) -> bool:
        """判断模板当前是否出现在画面中。"""
        return (
            self.find_template(
                template_path,
                threshold=threshold,
            )
            is not None
        )

    def wait_template(
        self,
        template_path: str | Path,
        timeout: float = config.PAGE_WAIT_TIMEOUT,
        threshold: float = config.DEFAULT_MATCH_THRESHOLD,
        poll_interval: float = config.PAGE_POLL_INTERVAL,
    ) -> MatchResult | None:
        """反复截图，等待模板出现。"""
        timeout = float(timeout)
        poll_interval = float(poll_interval)

        if timeout < 0:
            raise ValueError("等待超时不能小于 0")

        if poll_interval <= 0:
            raise ValueError("检查间隔必须大于 0")

        template = self._resolve_template_path(template_path)
        deadline = time.monotonic() + timeout

        while True:
            screenshot = self.adb.read_screenshot()

            match = find_template(
                screenshot,
                template,
                threshold=threshold,
            )

            if match is not None:
                return match

            remaining = deadline - time.monotonic()

            if remaining <= 0:
                return None

            self.adb.delay(
                min(poll_interval, remaining)
            )

    def click_template(
        self,
        template_path: str | Path,
        threshold: float = config.DEFAULT_MATCH_THRESHOLD,
        wait_seconds: float = config.PAGE_ACTION_DELAY,
    ) -> MatchResult | None:
        """查找模板并点击中心；找不到时返回 None。"""
        match = self.find_template(
            template_path,
            threshold=threshold,
        )

        if match is None:
            return None

        self.click_match(
            match,
            wait_seconds=wait_seconds,
        )

        return match

    def wait_and_click(
        self,
        template_path: str | Path,
        timeout: float = config.PAGE_WAIT_TIMEOUT,
        threshold: float = config.DEFAULT_MATCH_THRESHOLD,
        poll_interval: float = config.PAGE_POLL_INTERVAL,
        wait_seconds: float = config.PAGE_ACTION_DELAY,
    ) -> MatchResult | None:
        """等待模板出现并点击中心；超时返回 None。"""
        match = self.wait_template(
            template_path,
            timeout=timeout,
            threshold=threshold,
            poll_interval=poll_interval,
        )

        if match is None:
            return None

        self.click_match(
            match,
            wait_seconds=wait_seconds,
        )

        return match

    def click_match(
        self,
        match: MatchResult,
        wait_seconds: float = config.PAGE_ACTION_DELAY,
    ) -> None:
        """点击已经找到的匹配区域中心。"""
        x, y = match.center

        self.click_point(
            x,
            y,
            wait_seconds=wait_seconds,
        )

    @staticmethod
    def _resolve_template_path(
        template_path: str | Path,
    ) -> Path:
        """解析绝对路径、项目相对路径或模板文件名。"""
        path = Path(template_path).expanduser()

        if path.is_absolute():
            candidates = [path]
        else:
            candidates = [
                config.PROJECT_ROOT / path,
                config.TEMPLATE_DIR / path,
            ]

        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()

        checked = ", ".join(
            str(candidate)
            for candidate in candidates
        )

        raise FileNotFoundError(
            f"没有找到模板图片。已检查：{checked}"
        )

    @staticmethod
    def _delay(seconds: float) -> None:
        """等待页面响应。"""
        seconds = float(seconds)

        if seconds < 0:
            raise ValueError("等待时间不能小于 0")

        if seconds > 0:
            AdbController.delay(seconds)