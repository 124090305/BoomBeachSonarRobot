"""单帧全局入口：空棋盘基准 + 当前图 + 静态关卡配置 -> 结果。

不实例化 SonarBoard，不读取 Strategy，不调用单格 before/after 检测器。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

from sonar_config import SonarLevelConfig, get_level_config
from .board_alignment import align_board, rectify
from .board_features import anchor_ship_features, classify_cells, confirm_sunk, panel_occlusion, prepare_features, text_occlusion
from .board_types import (
    AlignmentResult, BoardImages, BoardRecognitionConfig, BoardRecognitionResult,
    CellRecognitionResult, RecognizedSubmarine,
)
from .image_match import read_image


def resolve_reference_path(level: int, reference_path: str | Path | None = None) -> Path:
    path = reference_path if reference_path is not None else get_level_config(level).empty_reference_path
    if path is None or not Path(path).is_file():
        raise FileNotFoundError(f"缺少第 {level} 关全空基准图：{path}；请用 --reference 明确指定全空截图")
    return Path(path)


def recognize_board_files(image_path: str | Path, *, level: int = 11,
                          reference_path: str | Path | None = None,
                          config: BoardRecognitionConfig | None = None,
                          output_dir: str | Path | None = None) -> BoardRecognitionResult:
    reference = resolve_reference_path(level, reference_path)
    return recognize_board(read_image(reference), read_image(image_path),
                           level_config=get_level_config(level), config=config,
                           output_dir=output_dir)


def recognize_board(empty_reference: np.ndarray, current_screenshot: np.ndarray, *,
                    level_config: SonarLevelConfig,
                    config: BoardRecognitionConfig | None = None,
                    output_dir: str | Path | None = None,
                    runtime_geometry: bool = False) -> BoardRecognitionResult:
    cfg = config or BoardRecognitionConfig()
    for name, image in (("empty_reference", empty_reference), ("current_screenshot", current_screenshot)):
        if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(f"{name} 必须是非空 uint8 BGR 三通道图片")
        if not image.size:
            raise ValueError(f"{name} 图片为空")
    if empty_reference.shape != current_screenshot.shape:
        raise ValueError("空基准与当前截图尺寸不同；请提供相同分辨率、未经裁剪的实机截图")
    if level_config.board_quad is None or level_config.grid_size <= 0:
        raise ValueError("关卡缺少有效 board_quad/grid_size")
    if cfg.cell_pixels < 16 or cfg.alignment_search_px < 0:
        raise ValueError("cell_pixels 至少16，alignment_search_px 不得为负")
    n = level_config.grid_size
    reference = empty_reference
    current = current_screenshot
    if runtime_geometry:
        from .board_geometry import locate_board, save_geometry_debug
        geometry = locate_board(reference, current, level_config)
        aligned = geometry.normalize(current)
        valid_pixels = cv2.warpPerspective(np.full(current.shape[:2], 255, np.uint8),
            np.asarray(geometry.current_to_reference), current.shape[1::-1])
        alignment = geometry.alignment
    else:
        aligned, valid_pixels, alignment = align_board(reference, current, level_config, cfg)
    rect_ref, matrix, padding = rectify(reference, level_config, cfg)
    rect_current, _, _ = rectify(aligned, level_config, cfg)
    valid_rect = cv2.warpPerspective(valid_pixels, matrix, rect_current.shape[1::-1])
    quad = np.float32(level_config.board_quad)
    cell_width = (quad[:, 0].max()-quad[:, 0].min()) / n
    static_text = text_occlusion(reference, cell_width, cfg)
    current_text = text_occlusion(aligned, cell_width, cfg)
    static_rect = cv2.warpPerspective(static_text, matrix, rect_current.shape[1::-1])
    current_rect = cv2.warpPerspective(current_text, matrix, rect_current.shape[1::-1])
    current_rect = np.maximum(current_rect, panel_occlusion(rect_current, cfg))
    static_rect = np.maximum(static_rect, panel_occlusion(rect_ref, cfg))
    features = prepare_features(rect_ref, rect_current, cfg)
    # 字符区域不允许参与船体结构连接。
    features["ship"][(static_rect > 0) | (current_rect > 0)] = 0
    # 立体船体绘制在水面落点上方；在逻辑平面回投后统计归属，减少邻格擦边。
    anchor_ship_features(features, padding, n, cfg)
    cells = classify_cells(features, current_rect, 255-valid_rect, static_rect,
                           n, padding, alignment, cfg)
    cells, ships, structure_issues = confirm_sunk(cells, features["ship"], level_config,
                                                 padding, alignment, cfg)
    issues = list(structure_issues)
    if not alignment.success:
        issues.insert(0, alignment.reason)
    dynamic_occlusion = float(np.mean([c.feature_scores["occlusion_ratio"] for c in cells]))
    hsv = features["hsv"][padding:padding+n*cfg.cell_pixels, padding:padding+n*cfg.cell_pixels]
    water_ratio = float(((hsv[:, :, 0] >= cfg.water_hue_range[0]) & (hsv[:, :, 0] <= cfg.water_hue_range[1])
                         & (hsv[:, :, 1] >= cfg.water_saturation_min)).mean())
    if not alignment.success and water_ratio < cfg.wrong_page_water_ratio:
        quality = "wrong_page"
        issues.append("棋盘定位失败且预期海水颜色不足，可能处于其他页面")
    elif dynamic_occlusion >= cfg.quality_occluded_fraction:
        quality = "occluded"
        issues.append(f"遮挡比例较高：{dynamic_occlusion:.3f}")
    elif not alignment.success:
        quality = "alignment_suspicious"
    else:
        quality = "usable"
    if any(c.feature_scores["reference_occlusion"] >= cfg.occlusion_review_ratio for c in cells):
        issues.append("基准图本身有文字遮挡的格子，已单独降低可信度")
    states = tuple(tuple(cells[row*n+col].state for col in range(n)) for row in range(n))
    counts = Counter(cell.state.value.upper() for cell in cells)
    review_fraction = np.mean([cell.needs_review for cell in cells])
    if review_fraction > cfg.max_review_fraction:
        issues.append(f"需复核格比例过高：{review_fraction:.3f}，整盘标记不可直接使用")
    result = BoardRecognitionResult(
        grid_size=n, states=states, cells=tuple(cells),
        counts={name: counts[name] for name in ("UNKNOWN", "MISS", "HIT", "SUNK")},
        review_cells=tuple((c.row, c.col) for c in cells if c.needs_review),
        sunk_submarines=ships, alignment=alignment, quality=quality,
        quality_score=float(alignment.confidence * (1-dynamic_occlusion)
                            * np.mean([cell.confidence for cell in cells])),
        valid=bool(quality == "usable" and review_fraction <= cfg.max_review_fraction), issues=tuple(issues),
    )
    if output_dir is not None:
        from .board_debug import save_board_debug
        images = BoardImages(current, aligned, reference, rect_current, rect_ref,
                             features["difference"], features["ship"],
                             np.maximum(static_rect, current_rect), matrix, padding)
        result = replace(result, debug_paths=save_board_debug(result, images, cfg, output_dir))
        if runtime_geometry:
            save_geometry_debug(geometry, current, level_config, Path(output_dir) / "geometry")
    return result


__all__ = ["recognize_board", "recognize_board_files", "resolve_reference_path",
           "BoardRecognitionConfig", "BoardRecognitionResult", "CellRecognitionResult",
           "RecognizedSubmarine", "AlignmentResult"]
