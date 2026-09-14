"""正式探测共用的运行时定位；截图只读，坐标只在当前棋盘实例生效。"""
from __future__ import annotations

import numpy as np

from logger import get_logger
from sonar import SonarBoard
from stop_control import raise_if_stop_requested
from vision.board_debug import write_image
from vision.board_geometry import BoardGeometryError, GEOMETRY_CONFIG, locate_board
from vision.image_match import read_image
from .sonar_page import SonarPageState, detect_sonar_page_state


logger = get_logger(__name__)


class RuntimeBoardLocator:
    def __init__(self, level_config):
        self.level = level_config
        self._reference = None

    @property
    def reference(self):
        if self._reference is None:
            try:
                if self.level.empty_reference_path is None:
                    raise ValueError("没有空棋盘参考图")
                self._reference = read_image(self.level.empty_reference_path)
            except Exception as exc:
                raise BoardGeometryError(f"无法读取当前关卡定位参考图：{exc}") from exc
        return self._reference

    def locate(self, image, page=None):
        if page is not None and detect_sonar_page_state(page, screenshot=image) != SonarPageState.ACTIVITY_DETAIL:
            raise BoardGeometryError("当前画面不属于声纳棋盘页，已禁止使用旧坐标")
        return locate_board(self.reference, image, self.level)

    def reference_point(self, cell):
        baseline = SonarBoard(self.level.grid_size, self.level.submarines)
        baseline.set_screen_quad(self.level.board_quad)
        return baseline.screen_point(*cell)

    def prepare_target(self, adb, page, board, cell, *, first_image=None, stop_event=None):
        """连续两张图各自定位；全盘坐标稳定后才发布整套映射。"""
        raise_if_stop_requested(stop_event)
        first = first_image if first_image is not None else adb.read_screenshot()
        initial = self.locate(first, page)
        raise_if_stop_requested(stop_event)
        image = adb.read_screenshot()
        latest = self.locate(image, page)
        drift = float(np.linalg.norm(np.asarray(initial.current_quad)-latest.current_quad, axis=1).max())
        if drift > GEOMETRY_CONFIG.stable_error_px:
            raise BoardGeometryError(f"棋盘仍在移动：两帧最大偏差 {drift:.1f}px；请等待页面稳定")
        point = latest.require_visible_target(image, self.level, cell)
        raise_if_stop_requested(stop_event)
        # SonarBoard 的既有映射接口一次发布全部坐标；不改变任何 HIT/MISS/SUNK。
        board.set_screen_quad(latest.current_quad)
        logger.info("运行时坐标校准：cell=%s，point=%s，confidence=%.3f，shift=%.2f，outline_error=%.2f，drift=%.2f",
                    cell, point, latest.alignment.confidence, latest.alignment.max_shift_px,
                    latest.outline_error_px, drift)
        return image, latest, point


def save_latest_before(path, image):
    """复用最后一张定位截图作为 before，避免重复采帧。"""
    write_image(path, image)
