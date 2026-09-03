"""素材质量预审：不执行格子状态推断，不根据文件名推断格子真值。"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .board_alignment import align_board, rectify
from .board_features import panel_occlusion, text_occlusion
from .board_types import AlignmentResult, BoardRecognitionConfig


@dataclass(frozen=True)
class MaterialQuality:
    category: str
    suitable_for_tuning: bool
    alignment: AlignmentResult | None
    occlusion_ratio: float
    water_ratio: float
    reasons: tuple[str, ...]


def assess_board_material(reference, current, level_config, config=None):
    cfg = config or BoardRecognitionConfig()
    if current.shape != reference.shape:
        return MaterialQuality("unusable", False, None, 0, 0, ("图片尺寸与基准不同",))
    aligned, valid, alignment = align_board(reference, current, level_config, cfg)
    rect, matrix, padding = rectify(aligned, level_config, cfg)
    side = level_config.grid_size * cfg.cell_pixels
    inside = np.s_[padding:padding+side, padding:padding+side]
    hsv = cv2.cvtColor(rect, cv2.COLOR_BGR2HSV)[inside]
    water = float(((hsv[:, :, 0] >= cfg.water_hue_range[0]) & (hsv[:, :, 0] <= cfg.water_hue_range[1])
                    & (hsv[:, :, 1] >= cfg.water_saturation_min)).mean())
    quad = np.float32(level_config.board_quad)
    width = np.ptp(quad[:, 0]) / level_config.grid_size
    text = text_occlusion(aligned, width, cfg)
    static_text = text_occlusion(reference, width, cfg)
    dynamic_text = text & (255-static_text)
    mask = cv2.warpPerspective(dynamic_text, matrix, rect.shape[1::-1])[inside]
    mask = np.maximum(mask, panel_occlusion(rect, cfg)[inside])
    extreme = (hsv[:, :, 2] < cfg.occlusion_value_low) | (
        (hsv[:, :, 2] > cfg.occlusion_value_high) & (hsv[:, :, 1] < 35))
    # 只把整块极端颜色计入遮挡，排除船体局部高光和阴影。
    broad = cv2.boxFilter(extreme.astype(np.float32), -1,
                           (cfg.cell_pixels//2, cfg.cell_pixels//2)) >= cfg.occlusion_extreme_ratio
    occlusion = float(((mask > 0) | broad).mean())
    reasons = []
    if not alignment.success and water < cfg.wrong_page_water_ratio:
        category = "wrong_page"
        reasons.append("缺少可靠网格和海面证据")
    elif occlusion >= cfg.quality_occluded_fraction:
        category = "occluded"
        reasons.append(f"动态文字/面板遮挡占比={occlusion:.3f}")
        if not alignment.success:
            reasons.append(alignment.reason)
    elif not alignment.success:
        category = "alignment_suspicious"
        reasons.append(alignment.reason)
    else:
        category = "usable"
    return MaterialQuality(category, category == "usable", alignment, occlusion, water, tuple(reasons))
