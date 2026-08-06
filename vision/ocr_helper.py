from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np


@dataclass(frozen=True)
class OCRResult:
    """单条 OCR 识别结果。"""

    text: str
    confidence: float


_reader_cache: dict[
    tuple[str, ...],
    object,
] = {}


def _get_reader(
    languages: Sequence[str],
) -> object:
    """
    延迟加载 EasyOCR。

    只有真正调用 OCR 时才加载模型。
    """
    key = tuple(languages)

    reader = _reader_cache.get(key)

    if reader is None:
        import easyocr

        reader = easyocr.Reader(
            list(key),
            gpu=False,
            verbose=False,
        )

        _reader_cache[key] = reader

    return reader


def read_text(
    image: np.ndarray,
    *,
    languages: Sequence[str] = ("en",),
    allowlist: str | None = None,
) -> list[OCRResult]:
    """
    识别图片中的文字。

    当前先提供通用接口，
    截图最小流程暂时不会调用它。
    """
    if (
        not isinstance(image, np.ndarray)
        or image.size == 0
    ):
        raise ValueError(
            "image 必须是有效的 OpenCV 图片"
        )

    if image.ndim == 2:
        rgb_image = cv2.cvtColor(
            image,
            cv2.COLOR_GRAY2RGB,
        )
    else:
        rgb_image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB,
        )

    reader = _get_reader(
        languages
    )

    raw_results = reader.readtext(
        rgb_image,
        allowlist=allowlist,
    )

    results: list[OCRResult] = []

    for _box, text, confidence in raw_results:
        results.append(
            OCRResult(
                text=str(text),
                confidence=float(confidence),
            )
        )

    return results


def read_number(
    image: np.ndarray,
) -> int | None:
    """
    识别图片中的数字。

    识别失败时返回 None。
    """
    results = read_text(
        image,
        allowlist="0123456789",
    )

    results.sort(
        key=lambda item: item.confidence,
        reverse=True,
    )

    for result in results:
        digits = "".join(
            character
            for character in result.text
            if character.isdigit()
        )

        if digits:
            return int(digits)

    return None