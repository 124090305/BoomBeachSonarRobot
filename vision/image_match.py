from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

import config


@dataclass(frozen=True)
class MatchResult:
    """模板匹配结果。"""

    score: float
    top_left: tuple[int, int]
    bottom_right: tuple[int, int]

    @property
    def center(self) -> tuple[int, int]:
        """返回匹配区域的中心坐标。"""
        x1, y1 = self.top_left
        x2, y2 = self.bottom_right

        return (
            (x1 + x2) // 2,
            (y1 + y2) // 2,
        )


def read_image(
    path: str | Path,
) -> np.ndarray:
    """读取图片，兼容中文文件路径。"""
    image_path = Path(path)

    if not image_path.is_file():
        raise FileNotFoundError(
            f"图片不存在：{image_path}"
        )

    image_data = np.fromfile(
        str(image_path),
        dtype=np.uint8,
    )

    image = cv2.imdecode(
        image_data,
        cv2.IMREAD_COLOR,
    )

    if image is None or image.size == 0:
        raise RuntimeError(
            f"图片解码失败：{image_path}"
        )

    return image


def find_template(
    screenshot: np.ndarray,
    template: str | Path | np.ndarray,
    threshold: float = config.DEFAULT_MATCH_THRESHOLD,
) -> MatchResult | None:
    """
    在截图中查找模板。

    找到并达到相似度要求时返回 MatchResult。
    没有找到时返回 None。
    """
    if (
        not isinstance(screenshot, np.ndarray)
        or screenshot.size == 0
    ):
        raise ValueError(
            "screenshot 必须是有效的 OpenCV 图片"
        )

    if isinstance(template, (str, Path)):
        template_image = read_image(template)
    else:
        template_image = template

    if (
        not isinstance(template_image, np.ndarray)
        or template_image.size == 0
    ):
        raise ValueError(
            "template 必须是有效的 OpenCV 图片"
        )

    if not 0 <= threshold <= 1:
        raise ValueError(
            "threshold 必须位于 0 到 1 之间"
        )

    screenshot_height, screenshot_width = (
        screenshot.shape[:2]
    )

    template_height, template_width = (
        template_image.shape[:2]
    )

    if (
        template_height > screenshot_height
        or template_width > screenshot_width
    ):
        raise ValueError(
            "模板尺寸不能大于截图尺寸"
        )

    match_data = cv2.matchTemplate(
        screenshot,
        template_image,
        cv2.TM_CCOEFF_NORMED,
    )

    (
        _min_score,
        max_score,
        _min_location,
        max_location,
    ) = cv2.minMaxLoc(match_data)

    if max_score < threshold:
        return None

    x, y = max_location

    return MatchResult(
        score=float(max_score),
        top_left=(x, y),
        bottom_right=(
            x + template_width,
            y + template_height,
        ),
    )