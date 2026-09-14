"""运行时棋盘几何：外轮廓消除格号歧义，局部网格精配准。

只处理坐标，不修改棋盘事实；轮廓不足或变换可疑时拒绝返回可点击坐标。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path

import cv2
import numpy as np

from .board_alignment import align_board, grid_transform, project
from .board_debug import write_image
from .board_types import AlignmentResult, BoardRecognitionConfig


@dataclass(frozen=True)
class BoardGeometryConfig:
    # 按画面/格宽限定搜索和误差；不修改关卡永久配置。
    maximum_shift_height_ratio: float = .18
    maximum_area_change: float = .30
    outline_saturation_max: int = 140
    outline_value_min: int = 70
    outline_close_cell_ratio: float = .09
    title_exclusion_height_ratio: float = .16
    outline_minimum_area_ratio: float = .55
    outline_error_cell_ratio: float = .08
    minimum_coverage: float = .28
    minimum_confidence: float = .60
    stable_error_px: float = 2.5
    target_margin_cell_ratio: float = .20
    outline_edge_minimum_fraction: float = .15
    outline_edge_angle_degrees: float = 12.0

    def __post_init__(self):
        for name in ("maximum_shift_height_ratio", "maximum_area_change", "outline_close_cell_ratio",
                     "outline_minimum_area_ratio", "outline_error_cell_ratio", "minimum_coverage",
                     "minimum_confidence", "target_margin_cell_ratio", "outline_edge_minimum_fraction"):
            if not 0 < getattr(self, name) < 1:
                raise ValueError(f"{name} 必须位于 (0,1)")
        if not 0 <= self.title_exclusion_height_ratio < 1 or not self.stable_error_px > 0:
            raise ValueError("标题范围或稳定误差配置无效")
        if not 0 < self.outline_edge_angle_degrees < 45:
            raise ValueError("外边角度容差必须位于 (0,45)")
        if not 0 < self.outline_saturation_max <= 255 or not 0 <= self.outline_value_min < 255:
            raise ValueError("外轮廓颜色阈值无效")


GEOMETRY_CONFIG = BoardGeometryConfig()


class BoardGeometryError(RuntimeError):
    """不可恢复的定位安全拦截；禁止自动重启后继续点击。"""


@dataclass(frozen=True)
class BoardGeometry:
    current_quad: tuple[tuple[float, float], ...]
    current_to_reference: tuple[tuple[float, ...], ...]
    image_size: tuple[int, int]
    alignment: AlignmentResult
    outline_error_px: float

    def normalize(self, image):
        if image.shape[1::-1] != self.image_size:
            raise BoardGeometryError("截图分辨率变化，坐标已失效")
        return cv2.warpPerspective(image, np.asarray(self.current_to_reference), self.image_size)

    def points(self, level):
        matrix = grid_transform(self.current_quad, level.grid_size)
        return project([(c+.5, r+.5) for r in range(level.grid_size)
                        for c in range(level.grid_size)], matrix)

    def screen_point(self, level, cell):
        r, c = cell
        if not 0 <= r < level.grid_size or not 0 <= c < level.grid_size:
            raise BoardGeometryError("目标格超出当前关卡")
        return tuple(int(round(v)) for v in self.points(level)[r*level.grid_size+c])

    def require_visible_target(self, image, level, cell, cfg=GEOMETRY_CONFIG):
        from .board_features import panel_occlusion, text_occlusion
        point = self.screen_point(level, cell)
        width = np.ptp(np.asarray(self.current_quad)[:, 0]) / level.grid_size
        radius = max(2, round(width * cfg.target_margin_cell_ratio))
        x, y = point
        h, w = image.shape[:2]
        if x-radius < 0 or y-radius < 0 or x+radius >= w or y+radius >= h:
            raise BoardGeometryError("目标格靠近画面外侧，禁止点击")
        vision_cfg = replace(BoardRecognitionConfig(), cell_pixels=max(16, round(width)))
        mask = np.maximum(text_occlusion(image, width, vision_cfg), panel_occlusion(image, vision_cfg))
        if mask[y-radius:y+radius+1, x-radius:x+radius+1].any():
            raise BoardGeometryError("目标格被文字或面板遮挡，请先调整页面或人工检查")
        return point


def _outline_anchors(image, level, cfg, repair_corners=False):
    """取左右、下方三个可见外尖角；标题遮挡的上角不参与粗定位。"""
    h, w = image.shape[:2]
    quad = np.float32(level.board_quad)
    cell_width = np.ptp(quad[:, 0]) / level.grid_size
    margin = round(h * cfg.maximum_shift_height_ratio)
    x0, x1 = max(0, int(quad[:, 0].min())-margin), min(w, int(quad[:, 0].max())+margin)
    y0 = max(0, round(h*cfg.title_exclusion_height_ratio))
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = np.uint8((hsv[:, :, 1] < cfg.outline_saturation_max)
                    & (hsv[:, :, 2] > cfg.outline_value_min)) * 255
    mask[:y0] = 0
    mask[:, :x0] = 0
    mask[:, x1:] = 0
    kernel = max(3, round(cell_width*cfg.outline_close_cell_ratio) | 1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((kernel, kernel), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise BoardGeometryError("缺少可见棋盘外轮廓")
    contour = max(contours, key=cv2.contourArea)
    area = abs(cv2.contourArea(contour))
    if area < abs(cv2.contourArea(quad))*cfg.outline_minimum_area_ratio:
        raise BoardGeometryError("完整外轮廓证据不足，请人工检查；保留原棋盘事实")
    hull = cv2.convexHull(contour).reshape(-1, 2)
    anchors = np.float32([hull[np.argmax(hull[:, 0])], hull[np.argmax(hull[:, 1])],
                          hull[np.argmin(hull[:, 0])]])
    if repair_corners:
        # 已开格会留下角部缺口。只允许用仍可见的长外边延长求交，禁止补造整条外边。
        lines = []
        center = hull.mean(axis=0)
        for a, b in zip(quad, np.roll(quad, -1, axis=0)):
            axis = b-a
            length = np.linalg.norm(axis)
            axis /= length
            normal = np.array([axis[1], -axis[0]])
            candidates = []
            for p, q in zip(hull, np.roll(hull, -1, axis=0)):
                edge = q-p
                extent = np.linalg.norm(edge)
                if (extent >= length*cfg.outline_edge_minimum_fraction
                        and abs(np.dot(edge/extent, axis)) >= np.cos(np.deg2rad(cfg.outline_edge_angle_degrees))
                        and np.dot((p+q)/2-center, normal) > 0):
                    candidates.append((extent, np.cross(np.r_[p, 1.], np.r_[q, 1.])))
            if not candidates:
                raise BoardGeometryError("外角缺失且外边支持不足，禁止推测格号")
            lines.append(max(candidates, key=lambda item: item[0])[1])
        corners = [np.cross(lines[index-1], lines[index]) for index in range(4)]
        if any(abs(point[2]) < 1e-6 for point in corners):
            raise BoardGeometryError("外边交点退化")
        anchors = np.float32([corners[index][:2]/corners[index][2] for index in (1, 2, 3)])
    if (anchors[:, 0].min() <= x0+1 or anchors[:, 0].max() >= x1-2
            or anchors[:, 1].max() >= h-2 or anchors[:, 1].min() <= y0+1):
        raise BoardGeometryError("棋盘外角被裁切或遮挡，无法可靠确定格号")
    return anchors


def locate_board(reference, current, level, *, cfg=GEOMETRY_CONFIG, output_dir=None):
    try:
        return _locate_board(reference, current, level, cfg=cfg, output_dir=output_dir)
    except BoardGeometryError as first_error:
        try:
            return _locate_board(reference, current, level, cfg=cfg, output_dir=output_dir, repair_corners=True)
        except BoardGeometryError as exc:
            raise BoardGeometryError(f"{first_error}；外边复核也未通过：{exc}") from exc


def _locate_board(reference, current, level, *, cfg, output_dir, repair_corners=False):
    """两图均使用同一关卡；输出当前画面的整盘透视映射。"""
    if (not isinstance(reference, np.ndarray) or not isinstance(current, np.ndarray)
            or reference.dtype != np.uint8 or current.dtype != np.uint8
            or reference.ndim != 3 or reference.shape != current.shape
            or reference.shape[2] != 3 or not reference.size):
        raise BoardGeometryError("定位需要同分辨率的完整 BGR 截图和空棋盘参考图")
    if level.board_quad is None or level.grid_size <= 0:
        raise BoardGeometryError("缺少关卡棋盘基准配置")
    source = _outline_anchors(reference, level, cfg, repair_corners)
    target = _outline_anchors(current, level, cfg, repair_corners)
    seed = np.vstack((cv2.getAffineTransform(target, source), [0., 0., 1.]))
    size = reference.shape[1::-1]
    compensated = cv2.warpPerspective(current, seed, size)
    vision_cfg = replace(BoardRecognitionConfig(), alignment_min_coverage=cfg.minimum_coverage,
                         alignment_min_confidence=cfg.minimum_confidence)
    _, _, local = align_board(reference, compensated, level, vision_cfg)
    if not local.success or local.coverage < cfg.minimum_coverage:
        raise BoardGeometryError(f"网格精定位未通过：{local.reason}")
    transform = np.asarray(local.current_to_reference) @ seed
    quad = project(level.board_quad, np.linalg.inv(transform))
    errors = np.linalg.norm(project(target, transform)-source, axis=1)
    outline_error = float(errors.max())
    cell_width = np.ptp(np.float32(level.board_quad)[:, 0]) / level.grid_size
    h, w = current.shape[:2]
    area_change = abs(abs(cv2.contourArea(quad))/abs(cv2.contourArea(np.float32(level.board_quad)))-1)
    shift = float(np.linalg.norm(quad-np.float32(level.board_quad), axis=1).max())
    if (not np.isfinite(quad).all() or not cv2.isContourConvex(quad)
            or cv2.contourArea(quad, oriented=True)*cv2.contourArea(np.float32(level.board_quad), oriented=True) <= 0
            or area_change > cfg.maximum_area_change
            or shift > h*cfg.maximum_shift_height_ratio
            or outline_error > max(2., cell_width*cfg.outline_error_cell_ratio)
            or (quad < 0).any() or (quad[:, 0] >= w).any() or (quad[:, 1] >= h).any()):
        raise BoardGeometryError(f"几何/外轮廓校验失败：偏移={shift:.1f}px，外角误差={outline_error:.1f}px")
    values = tuple(tuple(float(v) for v in row) for row in transform)
    alignment = replace(local, current_to_reference=values, max_shift_px=shift,
                        method="outline_seeded_grid_homography", reason="外轮廓锚定格号，网格与透视几何复核通过")
    result = BoardGeometry(tuple(tuple(float(v) for v in row) for row in quad), values,
                           size, alignment, outline_error)
    if output_dir is not None:
        save_geometry_debug(result, current, level, output_dir)
    return result


def save_geometry_debug(result, current, level, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    overlay = current.copy()
    cv2.polylines(overlay, [np.int32(result.current_quad)], True, (0, 255, 255), 2)
    for index, point in enumerate(result.points(level)):
        x, y = np.rint(point).astype(int)
        cv2.circle(overlay, (x, y), 3, (0, 0, 255), -1)
        cv2.putText(overlay, f"{index//level.grid_size+1},{index%level.grid_size+1}",
                    (x+3, y), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 0, 0), 1)
    write_image(output / "coordinates.png", overlay)
    write_image(output / "normalized.png", result.normalize(current))
    (output / "geometry.json").write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
