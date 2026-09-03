"""使用空棋盘实际亮边框做受限局部配准，避免水面纹理主导对齐。"""
from __future__ import annotations

import cv2
import numpy as np

from .board_types import AlignmentResult, BoardRecognitionConfig


def grid_transform(quad, grid_size: int) -> np.ndarray:
    # 与 SonarBoard.set_screen_quad 相同的逻辑轴和四角顺序。
    source = np.float32([[0, 0], [grid_size, 0],
                         [grid_size, grid_size], [0, grid_size]])
    return cv2.getPerspectiveTransform(source, np.float32(quad))


def project(points, matrix: np.ndarray) -> np.ndarray:
    return cv2.perspectiveTransform(np.float32(points).reshape(1, -1, 2), matrix)[0]


def cell_polygon(row: int, col: int, matrix: np.ndarray, scale=1.0):
    center = np.float32([col + 0.5, row + 0.5])
    corners = np.float32([[-0.5, -0.5], [0.5, -0.5],
                          [0.5, 0.5], [-0.5, 0.5]])
    return project(center + corners * scale, matrix)


def line_strength(image: np.ndarray, cfg: BoardRecognitionConfig) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    value, saturation = hsv[:, :, 2], hsv[:, :, 1]
    background = cv2.GaussianBlur(value, (0, 0), cfg.line_blur_sigma)
    contrast = np.clip((value - background) / cfg.line_contrast, 0, 1)
    color = np.clip((cfg.line_saturation_max - saturation) / cfg.line_saturation_scale, 0, 1)
    return (contrast * color * (value >= cfg.line_value_min)).astype(np.float32)


def align_board(reference, current, level, cfg: BoardRecognitionConfig):
    height, width = reference.shape[:2]
    matrix = grid_transform(level.board_quad, level.grid_size)
    ref_lines, cur_lines = line_strength(reference, cfg), line_strength(current, cfg)
    anchors, matches, scores = [], [], []
    radius = cfg.alignment_search_px
    for row in range(level.grid_size):
        for col in range(level.grid_size):
            polygon = cell_polygon(row, col, matrix)
            x, y, w, h = cv2.boundingRect(np.int32(polygon))
            if x-radius < 0 or y-radius < 0 or x+w+radius > width or y+h+radius > height:
                continue
            ring = np.zeros((h, w), np.uint8)
            cv2.fillConvexPoly(ring, np.int32(polygon - [x, y]), 1)
            inner = cell_polygon(row, col, matrix, 1 - cfg.border_band * 2)
            cv2.fillConvexPoly(ring, np.int32(inner - [x, y]), 0)
            template = ((ref_lines[y:y+h, x:x+w] > cfg.reference_line_threshold)
                        & (ring > 0)).astype(np.float32)
            if template.sum() < max(8, (w+h)*0.18):
                continue
            search = cur_lines[y-radius:y+h+radius, x-radius:x+w+radius]
            corr = cv2.matchTemplate(search, template, cv2.TM_CCORR) / template.sum()
            _, score, _, location = cv2.minMaxLoc(corr)
            if score < cfg.alignment_min_anchor_score:
                continue
            center = project([[col+0.5, row+0.5]], matrix)[0]
            anchors.append(center)
            matches.append(center + [location[0]-radius, location[1]-radius])
            scores.append(score)

    identity = np.eye(3, dtype=np.float64)
    transform = identity
    inliers = np.zeros(len(anchors), bool)
    residual, coverage, shift, confidence, score = 0.0, 0.0, 0.0, 0.0, 0.0
    reason = "可见网格锚点不足，无法可靠对齐"
    if len(anchors) >= cfg.alignment_min_anchors:
        source, target = np.float32(anchors), np.float32(matches)
        fitted, inlier_mask = cv2.findHomography(
            source, target, cv2.RANSAC, cfg.alignment_ransac_px,
        )
        if fitted is not None and inlier_mask is not None and np.isfinite(fitted).all():
            inliers = inlier_mask.ravel().astype(bool)
            if inliers.sum() >= cfg.alignment_min_anchors:
                estimated = project(source, fitted)
                residual = float(np.median(np.linalg.norm(estimated[inliers]-target[inliers], axis=1)))
                quad = np.float32(level.board_quad)
                moved_quad = project(quad, fitted)
                shift = float(np.max(np.linalg.norm(moved_quad-quad, axis=1)))
                board_area = abs(cv2.contourArea(quad))
                coverage = float(abs(cv2.contourArea(cv2.convexHull(source[inliers]))) / board_area)
                area_change = abs(abs(cv2.contourArea(moved_quad)) / board_area - 1)
                score = float(np.mean(np.array(scores)[inliers]))
                confidence = float(np.clip(
                    score * (0.65 + 0.35 * inliers.mean())
                    * min(1, coverage / cfg.alignment_min_coverage)
                    * np.exp(-residual / (3 * cfg.alignment_ransac_px)), 0, 1))
                geometry_ok = (shift <= cfg.alignment_max_shift_px
                               and area_change <= cfg.alignment_max_area_change
                               and cv2.isContourConvex(moved_quad))
                if geometry_ok:
                    transform = np.linalg.inv(fitted)
                    reason = "网格局部匹配通过RANSAC和四角几何校验"
                else:
                    confidence = 0.0
                    reason = "配准变换超出位移/面积容差，拒绝应用"
    success = confidence >= cfg.alignment_min_confidence
    if not success and reason.startswith("网格局部"):
        reason = "配准证据覆盖或置信度不足"
    aligned = cv2.warpPerspective(current, transform, (width, height))
    valid_pixels = cv2.warpPerspective(np.full(current.shape[:2], 255, np.uint8),
                                      transform, (width, height))
    result = AlignmentResult(
        success=success, confidence=confidence, score=score,
        current_to_reference=tuple(tuple(float(v) for v in line) for line in transform),
        anchor_count=len(anchors), inlier_count=int(inliers.sum()), coverage=coverage,
        residual_px=residual, max_shift_px=shift, reason=reason,
    )
    return aligned, valid_pixels, result


def rectify(image, level, cfg: BoardRecognitionConfig):
    padding = round(cfg.cell_pixels * cfg.padding_cells)
    side = cfg.cell_pixels * level.grid_size
    destination = np.float32([[padding, padding], [padding+side, padding],
                              [padding+side, padding+side], [padding, padding+side]])
    matrix = cv2.getPerspectiveTransform(np.float32(level.board_quad), destination)
    return cv2.warpPerspective(image, matrix, (side+2*padding, side+2*padding)), matrix, padding
