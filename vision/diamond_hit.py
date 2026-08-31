from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass, replace

import cv2
import numpy as np

Point = tuple[int, int]

_STATE_PRIORITY = {
    "hit": 3,
    "miss": 2,
    "unopened": 1,
    "unknown": 0,
}


@dataclass
class DiamondHitConfig:
    """菱形格命中判断配置。"""

    diamond_w: int = 80
    diamond_h: int = 56
    search_radius: int = 14
    max_refine_radius: int = 5
    refine_step: int = 1

    inner_scale: float = 0.72
    center_scale: float = 0.52

    diff_threshold: int = 18
    min_changed_ratio: float = 0.08

    gray_s_max: int = 85
    rgb_delta_max: int = 55
    v_min: int = 28
    v_max: int = 230

    min_center_gray_ratio: float = 0.085
    min_gray_excess: float = 0.045
    min_component_ratio: float = 0.026
    min_s_drop: float = 8.0
    min_edge_density: float = 0.014
    hit_score_threshold: float = 0.85

    probe_offsets: tuple[tuple[int, int], ...] = (
        (0, 0),
        (0, -9),
        (0, 9),
        (-12, 0),
        (12, 0),
        (-8, -6),
        (8, -6),
        (-8, 6),
        (8, 6),
    )
    se_probe_min_gray: float = 0.80
    se_probe_max_s: float = 50.0
    se_probe_min_excess: float = 0.32
    se_probe_min_s_drop: float = 28.0

    min_hit_gray_ratio: float = 0.80
    min_hull_gray_ratio: float = 0.90
    min_metal_gray_ratio: float = 0.80
    min_metal_s_drop: float = 16.0
    min_metal_gray_excess: float = 0.25
    max_metal_s: float = 55.0
    min_wreck_gray_ratio: float = 0.85
    min_wreck_edge_density: float = 0.27
    max_hull_gray_excess: float = 0.18
    max_hull_s: float = 60.0

    miss_min_s: float = 145.0
    miss_max_mean_v: float = 140.0
    miss_max_gray_ratio: float = 0.20

    miss_min_s_occluded: float = 128.0
    miss_ui_border_white_min: float = 0.20

    miss_max_v_rel: float = -5.0
    miss_max_border_white: float = 0.08
    min_ambiguous_gray_ratio: float = 0.35

    min_unopened_white_ratio: float = 0.20
    min_unopened_border_white: float = 0.12
    border_outer_scale: float = 1.05
    border_inner_scale: float = 0.82
    border_white_s_max: int = 70
    border_white_v_min: int = 160
    max_miss_white_ratio: float = 0.12

    white_s_max: int = 65
    white_v_min: int = 125
    min_white_cover_ratio: float = 0.28

    ship_inside_scale: float = 0.72
    ship_boundary_outer_scale: float = 1.06
    ship_outside_outer_scale: float = 1.18
    min_inside_ship_ratio: float = 0.10
    min_boundary_ship_ratio: float = 0.025
    min_outside_ship_ratio: float = 0.012
    min_cross_boundary_score: float = 0.55
    min_cross_component_pixels: int = 4
    cross_direction_aspect_ratio: float = 1.25

    ambiguous_confidence_threshold: float = 0.68
    ambiguous_score_margin: float = 0.08

    debug: bool = False
    debug_dir: str = "debug_diamond_pair"


@dataclass
class DiamondHitResult:
    """菱形格识别结果与调试指标。"""

    state: str
    confidence: float
    score: float
    rough_center: Point
    refined_center: Point
    changed_ratio: float
    center_gray_ratio: float
    ring_gray_ratio: float
    gray_excess: float
    component_ratio: float
    s_center: float
    s_ring: float
    s_drop: float
    edge_density: float
    best_probe_offset: Point = (0, 0)
    inside_ship_ratio: float = 0.0
    boundary_ship_ratio: float = 0.0
    outside_ship_ratio: float = 0.0
    cross_boundary_score: float = 0.0
    cross_boundary_direction: str | None = None
    sunk_candidate: bool = False


def is_diamond_hit(
    before_screenshot: np.ndarray,
    after_screenshot: np.ndarray,
    center: Point,
    diamond_w: int = 80,
    diamond_h: int = 56,
    search_radius: int = 14,
) -> bool:
    config = DiamondHitConfig(
        diamond_w=diamond_w,
        diamond_h=diamond_h,
        search_radius=search_radius,
    )
    result = classify_diamond_hit(
        before_screenshot,
        after_screenshot,
        center,
        config,
    )
    return result.state == "hit"


def classify_diamond_hit(
    before_screenshot: np.ndarray,
    after_screenshot: np.ndarray,
    center: Point,
    config: DiamondHitConfig | None = None,
    index: int = 0,
) -> DiamondHitResult:
    """返回 hit / miss / unopened / unknown。"""

    _validate_screenshot("before_screenshot", before_screenshot)
    _validate_screenshot("after_screenshot", after_screenshot)

    if before_screenshot.shape[:2] != after_screenshot.shape[:2]:
        raise ValueError("before_screenshot 和 after_screenshot 的图片尺寸必须一致")

    config = config or DiamondHitConfig()
    rough_center = _to_point(center)

    # 探针保持九宫格对称；每个探针只允许在格内小范围细化。
    limited_radius = max(
        0,
        min(
            int(config.search_radius),
            int(config.max_refine_radius),
            max(1, int(config.diamond_w * 0.10)),
            max(1, int(config.diamond_h * 0.14)),
        ),
    )
    probe_config = replace(
        config,
        search_radius=limited_radius,
    )
    measured: list[dict] = []

    for dx, dy in config.probe_offsets:
        candidate = _measure_cell_metrics(
            before_screenshot,
            after_screenshot,
            (rough_center[0] + dx, rough_center[1] + dy),
            probe_config,
        )
        candidate["best_probe_offset"] = (dx, dy)
        candidate["probe_rank"] = _probe_rank(
            candidate,
            config,
            dx=dx,
            dy=dy,
        )
        measured.append(candidate)

    best = max(
        measured,
        key=lambda item: item["probe_rank"],
    )

    center_gray_ratio = best["center_gray_ratio"]
    ring_gray_ratio = best["ring_gray_ratio"]
    gray_excess = best["gray_excess"]
    component_ratio = best["component_ratio"]
    changed_ratio = best["changed_ratio"]
    s_center = best["s_center"]
    s_ring = best["s_ring"]
    s_drop = best["s_drop"]
    edge_density = best["edge_density"]
    inside_ship_ratio = best["inside_ship_ratio"]
    boundary_ship_ratio = best["boundary_ship_ratio"]
    outside_ship_ratio = best["outside_ship_ratio"]
    cross_boundary_score = best["cross_boundary_score"]
    cross_boundary_direction = best["cross_boundary_direction"]
    white_cover_ratio = best["white_cover_ratio"]
    border_white_ratio = best["border_white_ratio"]
    mean_v = best["mean_v"]
    v_rel = best["v_rel"]

    score = 0.0
    score += score_piece(center_gray_ratio, config.min_center_gray_ratio, 0.28)
    score += score_piece(max(0.0, gray_excess), config.min_gray_excess, 0.22)
    score += score_piece(component_ratio, config.min_component_ratio, 0.25)
    score += score_piece(max(0.0, s_drop), config.min_s_drop, 0.15)
    score += score_piece(edge_density, config.min_edge_density, 0.10)
    score = max(0.0, min(1.0, score))

    hull_feature = (
        center_gray_ratio >= config.min_hull_gray_ratio
        and gray_excess <= config.max_hull_gray_excess
        and s_center <= config.max_hull_s
    )
    metal_feature = (
        center_gray_ratio >= config.min_metal_gray_ratio
        and s_center <= config.max_metal_s
        and gray_excess >= config.min_metal_gray_excess
        and s_drop >= config.min_metal_s_drop
    )
    wreck_feature = (
        center_gray_ratio >= config.min_wreck_gray_ratio
        and edge_density >= config.min_wreck_edge_density
        and s_center <= config.max_metal_s
    )
    moderate_feature = (
        center_gray_ratio >= 0.08
        and center_gray_ratio < config.min_metal_gray_ratio
        and changed_ratio >= config.min_changed_ratio
        and s_center < config.miss_min_s
    )
    compact_gray_feature = (
        center_gray_ratio >= 0.28
        and changed_ratio >= config.min_changed_ratio
        and s_center <= config.max_metal_s
    )

    supporting_features = sum(
        (
            center_gray_ratio >= config.min_center_gray_ratio,
            gray_excess >= config.min_gray_excess,
            component_ratio >= config.min_component_ratio,
            s_drop >= config.min_s_drop,
            edge_density >= config.min_edge_density,
            inside_ship_ratio >= config.min_inside_ship_ratio,
        )
    )
    strong_features = sum(
        (
            hull_feature,
            metal_feature,
            wreck_feature,
            compact_gray_feature,
        )
    )
    is_hit = (
        changed_ratio >= config.min_changed_ratio
        and (
            strong_features >= 1
            or (
                moderate_feature
                and supporting_features >= 3
            )
            or (
                score >= config.hit_score_threshold
                and supporting_features >= 4
            )
        )
    )

    sunk_candidate = (
        is_hit
        and cross_boundary_direction in {"H", "V"}
        and inside_ship_ratio >= config.min_inside_ship_ratio
        and boundary_ship_ratio >= config.min_boundary_ship_ratio
        and outside_ship_ratio >= config.min_outside_ship_ratio
        and cross_boundary_score >= config.min_cross_boundary_score
    )

    if is_hit:
        state = "hit"
        confidence = min(
            1.0,
            max(
                score,
                center_gray_ratio,
                0.55 + 0.10 * strong_features,
                0.45 + 0.08 * supporting_features,
            ),
        )

    elif (
        s_center >= config.miss_min_s
        and mean_v <= config.miss_max_mean_v
        and center_gray_ratio <= config.miss_max_gray_ratio
        and component_ratio < 0.02
    ):
        state = "miss"
        confidence = min(1.0, (s_center - config.miss_min_s) / 50.0)

    elif (
        center_gray_ratio <= config.miss_max_gray_ratio
        and center_gray_ratio < 0.10
        and s_center >= config.miss_min_s_occluded
        and mean_v <= config.miss_max_mean_v
        and component_ratio < 0.02
        and border_white_ratio >= config.miss_ui_border_white_min
        and white_cover_ratio < config.min_unopened_white_ratio
    ):
        state = "miss"
        confidence = min(
            1.0,
            (s_center - config.miss_min_s_occluded) / 50.0,
        )

    elif (
        border_white_ratio >= config.min_unopened_border_white
        or white_cover_ratio >= config.min_unopened_white_ratio
    ):
        state = "unopened"
        confidence = min(1.0, max(border_white_ratio, white_cover_ratio))

    elif center_gray_ratio >= config.min_ambiguous_gray_ratio:
        state = "unknown"
        confidence = min(1.0, center_gray_ratio)

    elif (
        changed_ratio < config.min_changed_ratio
        and white_cover_ratio <= config.max_miss_white_ratio
    ):
        state = "unopened" if changed_ratio <= 1e-9 else "unknown"
        confidence = 1.0 - changed_ratio / max(
            config.min_changed_ratio,
            1e-6,
        )
        confidence = max(0.0, min(1.0, confidence))

    else:
        state = "unopened"
        confidence = min(
            1.0,
            max(
                border_white_ratio,
                white_cover_ratio,
                mean_v / 255.0,
            ),
        )

    if config.debug:
        save_debug_images(
            before_crop=best["before_crop"],
            after_crop=best["after_crop"],
            diff_gray=best["diff_gray"],
            gray_candidate=best["gray_candidate"],
            inner_mask=best["inner_mask"],
            center_mask=best["center_mask"],
            ring_mask=best["ring_mask"],
            local_center=best["local_center"],
            result_text=(
                f"{state} score={score:.3f} "
                f"chg={changed_ratio:.3f} "
                f"white={white_cover_ratio:.3f} "
                f"borderW={border_white_ratio:.3f} "
                f"gray={center_gray_ratio:.3f} "
                f"V={mean_v:.1f} "
                f"Vrel={v_rel:.1f} "
                f"ex={gray_excess:.3f} "
                 f"comp={component_ratio:.3f} "
                 f"sdrop={s_drop:.1f} "
                 f"edge={edge_density:.3f} "
                 f"inside={inside_ship_ratio:.3f} "
                 f"boundary={boundary_ship_ratio:.3f} "
                 f"outside={outside_ship_ratio:.3f} "
                 f"cross={cross_boundary_score:.3f}/"
                 f"{cross_boundary_direction or '-'}"
            ),
            config=config,
            index=index,
        )

    return DiamondHitResult(
        state=state,
        confidence=confidence,
        score=score,
        rough_center=rough_center,
        refined_center=best["refined_center"],
        changed_ratio=changed_ratio,
        center_gray_ratio=center_gray_ratio,
        ring_gray_ratio=ring_gray_ratio,
        gray_excess=gray_excess,
        component_ratio=component_ratio,
        s_center=s_center,
        s_ring=s_ring,
        s_drop=s_drop,
        edge_density=edge_density,
        best_probe_offset=best["best_probe_offset"],
        inside_ship_ratio=inside_ship_ratio,
        boundary_ship_ratio=boundary_ship_ratio,
        outside_ship_ratio=outside_ship_ratio,
        cross_boundary_score=cross_boundary_score,
        cross_boundary_direction=cross_boundary_direction,
        sunk_candidate=sunk_candidate,
    )


def classify_diamond_hit_multiframe(
    before_screenshot: np.ndarray,
    after_screenshots: list[np.ndarray],
    center: Point,
    config: DiamondHitConfig | None = None,
    index: int = 0,
) -> DiamondHitResult:
    """多帧识别；任一帧命中时 HIT 优先。"""

    if not after_screenshots:
        raise ValueError("after_screenshots 不能为空")

    config = config or DiamondHitConfig()

    results = [
        classify_diamond_hit(
            before_screenshot,
            after,
            center,
            config,
            index,
        )
        for after in after_screenshots
    ]

    hit_frames = [
        item
        for item in results
        if item.state == "hit"
    ]
    if hit_frames:
        return max(
            hit_frames,
            key=lambda item: (
                item.sunk_candidate,
                item.cross_boundary_score,
                item.score,
                item.center_gray_ratio,
            ),
        )

    chosen_state = majority_cell_state(
        [item.state for item in results]
    )

    for item in results:
        if item.state == chosen_state:
            return item

    return results[0]


def needs_multiframe_confirmation(
    result: DiamondHitResult,
    config: DiamondHitConfig,
) -> bool:
    """判断单帧是否处于需要第二帧确认的模糊区。"""
    if result.state in {"unknown", "unopened"}:
        return True
    return (
        result.confidence < config.ambiguous_confidence_threshold
        and result.state in {"hit", "miss"}
        and abs(result.score - config.hit_score_threshold)
        <= config.ambiguous_score_margin
    )


def majority_cell_state(states: list[str]) -> str:
    if not states:
        return "unknown"

    counts = Counter(states)
    return max(
        counts.items(),
        key=lambda item: (
            item[1],
            _STATE_PRIORITY.get(item[0], -1),
        ),
    )[0]


def clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def diamond_points(
    center: Point,
    diamond_w: int,
    diamond_h: int,
    scale: float = 1.0,
) -> np.ndarray:
    cx, cy = center
    half_w = diamond_w * scale / 2.0
    half_h = diamond_h * scale / 2.0

    return np.array(
        [
            [int(round(cx)), int(round(cy - half_h))],
            [int(round(cx + half_w)), int(round(cy))],
            [int(round(cx)), int(round(cy + half_h))],
            [int(round(cx - half_w)), int(round(cy))],
        ],
        dtype=np.int32,
    )


def make_diamond_mask(
    shape_hw: tuple[int, int],
    center: Point,
    diamond_w: int,
    diamond_h: int,
    scale: float = 1.0,
) -> np.ndarray:
    h, w = shape_hw
    mask = np.zeros((h, w), dtype=np.uint8)
    points = diamond_points(
        center,
        diamond_w,
        diamond_h,
        scale,
    )
    cv2.fillConvexPoly(mask, points, 255)
    return mask


def crop_around(
    image: np.ndarray,
    center: Point,
    crop_w: int,
    crop_h: int,
) -> tuple[np.ndarray, Point, Point]:
    h, w = image.shape[:2]
    cx, cy = center

    x1 = clamp_int(cx - crop_w // 2, 0, w - 1)
    y1 = clamp_int(cy - crop_h // 2, 0, h - 1)
    x2 = clamp_int(cx + crop_w // 2, 0, w)
    y2 = clamp_int(cy + crop_h // 2, 0, h)

    crop = image[y1:y2, x1:x2].copy()
    return crop, (cx - x1, cy - y1), (x1, y1)


def mean_in_mask(
    image_2d: np.ndarray,
    mask: np.ndarray,
) -> float:
    values = image_2d[mask > 0]
    if values.size == 0:
        return 0.0
    return float(np.mean(values))


def ratio_in_mask(
    binary_mask: np.ndarray,
    area_mask: np.ndarray,
) -> float:
    area = int(np.count_nonzero(area_mask))
    if area <= 0:
        return 0.0

    count = int(
        np.count_nonzero(
            (binary_mask > 0)
            & (area_mask > 0)
        )
    )
    return count / area


def get_largest_component_area(
    binary_mask: np.ndarray,
) -> int:
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(
        binary_mask,
        connectivity=8,
    )

    if num_labels <= 1:
        return 0

    areas = stats[1:, cv2.CC_STAT_AREA]
    if len(areas) == 0:
        return 0

    return int(np.max(areas))


def build_gray_candidate_mask(
    after_bgr: np.ndarray,
    config: DiamondHitConfig,
) -> np.ndarray:
    hsv = cv2.cvtColor(
        after_bgr,
        cv2.COLOR_BGR2HSV,
    )
    b, g, r = cv2.split(after_bgr)
    _, s, v = cv2.split(hsv)

    max_rgb = np.maximum(np.maximum(r, g), b)
    min_rgb = np.minimum(np.minimum(r, g), b)
    rgb_delta = (
        max_rgb.astype(np.int16)
        - min_rgb.astype(np.int16)
    )

    mask = (
        (s <= config.gray_s_max)
        & (rgb_delta <= config.rgb_delta_max)
        & (v >= config.v_min)
        & (v <= config.v_max)
    ).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (3, 3),
    )
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel,
    )
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel,
    )
    return mask


def _measure_cell_metrics(
    before_bgr: np.ndarray,
    after_bgr: np.ndarray,
    center: Point,
    config: DiamondHitConfig,
) -> dict:
    refined_center = refine_center_by_pair(
        before_bgr,
        after_bgr,
        _to_point(center),
        config,
    )

    crop_w = int(config.diamond_w * 1.7)
    crop_h = int(config.diamond_h * 1.9)

    before_crop, local_center, _ = crop_around(
        before_bgr,
        refined_center,
        crop_w,
        crop_h,
    )
    after_crop, _, _ = crop_around(
        after_bgr,
        refined_center,
        crop_w,
        crop_h,
    )

    h, w = after_crop.shape[:2]

    inner_mask = make_diamond_mask(
        (h, w),
        local_center,
        config.diamond_w,
        config.diamond_h,
        config.inner_scale,
    )
    center_mask = make_diamond_mask(
        (h, w),
        local_center,
        config.diamond_w,
        config.diamond_h,
        config.center_scale,
    )
    ring_mask = cv2.subtract(
        inner_mask,
        center_mask,
    )

    before_gray = cv2.cvtColor(
        before_crop,
        cv2.COLOR_BGR2GRAY,
    )
    after_gray = cv2.cvtColor(
        after_crop,
        cv2.COLOR_BGR2GRAY,
    )
    diff_gray = cv2.absdiff(
        before_gray,
        after_gray,
    )

    changed_mask = (
        diff_gray >= config.diff_threshold
    ).astype(np.uint8) * 255
    changed_ratio = ratio_in_mask(
        changed_mask,
        inner_mask,
    )

    gray_candidate = build_gray_candidate_mask(
        after_crop,
        config,
    )
    center_gray_mask = cv2.bitwise_and(
        gray_candidate,
        gray_candidate,
        mask=center_mask,
    )
    ring_gray_mask = cv2.bitwise_and(
        gray_candidate,
        gray_candidate,
        mask=ring_mask,
    )

    center_gray_ratio = ratio_in_mask(
        center_gray_mask,
        center_mask,
    )
    ring_gray_ratio = ratio_in_mask(
        ring_gray_mask,
        ring_mask,
    )
    gray_excess = (
        center_gray_ratio
        - ring_gray_ratio
    )

    largest_component = get_largest_component_area(
        center_gray_mask
    )
    center_area = max(
        1,
        int(np.count_nonzero(center_mask)),
    )
    component_ratio = (
        largest_component
        / center_area
    )

    after_hsv = cv2.cvtColor(
        after_crop,
        cv2.COLOR_BGR2HSV,
    )
    _, s_after, v_after = cv2.split(after_hsv)

    s_center = mean_in_mask(
        s_after,
        center_mask,
    )
    s_ring = mean_in_mask(
        s_after,
        ring_mask,
    )
    s_drop = s_ring - s_center

    mean_v = mean_in_mask(
        v_after,
        center_mask,
    )
    mean_v_ring = mean_in_mask(
        v_after,
        ring_mask,
    )
    v_rel = mean_v - mean_v_ring

    white_mask = (
        (s_after <= config.white_s_max)
        & (v_after >= config.white_v_min)
    ).astype(np.uint8) * 255
    white_cover_ratio = ratio_in_mask(
        white_mask,
        center_mask,
    )

    outer_mask = make_diamond_mask(
        (h, w),
        local_center,
        config.diamond_w,
        config.diamond_h,
        config.border_outer_scale,
    )
    inner_border_mask = make_diamond_mask(
        (h, w),
        local_center,
        config.diamond_w,
        config.diamond_h,
        config.border_inner_scale,
    )
    border_mask = cv2.subtract(
        outer_mask,
        inner_border_mask,
    )

    border_white_mask = (
        (s_after <= config.border_white_s_max)
        & (v_after >= config.border_white_v_min)
    ).astype(np.uint8) * 255
    border_white_ratio = ratio_in_mask(
        border_white_mask,
        border_mask,
    )

    blur = cv2.GaussianBlur(
        after_gray,
        (3, 3),
        0,
    )
    edges = cv2.Canny(
        blur,
        35,
        90,
    )
    center_edges = cv2.bitwise_and(
        edges,
        edges,
        mask=center_mask,
    )
    edge_density = ratio_in_mask(
        center_edges,
        center_mask,
    )

    changed_support = cv2.dilate(
        changed_mask,
        cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (5, 5),
        ),
        iterations=1,
    )
    ship_candidate = cv2.bitwise_and(
        gray_candidate,
        changed_support,
    )
    ship_inner_mask = make_diamond_mask(
        (h, w),
        local_center,
        config.diamond_w,
        config.diamond_h,
        config.ship_inside_scale,
    )
    ship_full_mask = make_diamond_mask(
        (h, w),
        local_center,
        config.diamond_w,
        config.diamond_h,
        1.0,
    )
    ship_boundary_outer = make_diamond_mask(
        (h, w),
        local_center,
        config.diamond_w,
        config.diamond_h,
        config.ship_boundary_outer_scale,
    )
    ship_outside_outer = make_diamond_mask(
        (h, w),
        local_center,
        config.diamond_w,
        config.diamond_h,
        config.ship_outside_outer_scale,
    )
    ship_boundary_mask = cv2.subtract(
        ship_boundary_outer,
        ship_inner_mask,
    )
    ship_outside_mask = cv2.subtract(
        ship_outside_outer,
        ship_full_mask,
    )
    inside_ship_ratio = ratio_in_mask(
        ship_candidate,
        ship_inner_mask,
    )
    boundary_ship_ratio = ratio_in_mask(
        ship_candidate,
        ship_boundary_mask,
    )
    outside_ship_ratio = ratio_in_mask(
        ship_candidate,
        ship_outside_mask,
    )
    cross_boundary_score, cross_boundary_direction = (
        _measure_cross_boundary(
            ship_candidate,
            ship_inner_mask,
            ship_boundary_mask,
            ship_outside_mask,
            config,
        )
    )

    return {
        "refined_center": refined_center,
        "before_crop": before_crop,
        "after_crop": after_crop,
        "local_center": local_center,
        "inner_mask": inner_mask,
        "center_mask": center_mask,
        "ring_mask": ring_mask,
        "diff_gray": diff_gray,
        "gray_candidate": gray_candidate,
        "changed_ratio": changed_ratio,
        "center_gray_ratio": center_gray_ratio,
        "ring_gray_ratio": ring_gray_ratio,
        "gray_excess": gray_excess,
        "component_ratio": component_ratio,
        "s_center": s_center,
        "s_ring": s_ring,
        "s_drop": s_drop,
        "white_cover_ratio": white_cover_ratio,
        "border_white_ratio": border_white_ratio,
        "edge_density": edge_density,
        "mean_v": mean_v,
        "v_rel": v_rel,
        "inside_ship_ratio": inside_ship_ratio,
        "boundary_ship_ratio": boundary_ship_ratio,
        "outside_ship_ratio": outside_ship_ratio,
        "cross_boundary_score": cross_boundary_score,
        "cross_boundary_direction": cross_boundary_direction,
    }


def _measure_cross_boundary(
    ship_candidate: np.ndarray,
    inside_mask: np.ndarray,
    boundary_mask: np.ndarray,
    outside_mask: np.ndarray,
    config: DiamondHitConfig,
) -> tuple[float, str | None]:
    """寻找同时穿过格内、边界和格外的同一船体连通区域。"""
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        ship_candidate,
        connectivity=8,
    )
    best_score = 0.0
    best_direction: str | None = None
    min_pixels = max(1, int(config.min_cross_component_pixels))

    for label in range(1, count):
        component = labels == label
        inside_pixels = int(np.count_nonzero(component & (inside_mask > 0)))
        boundary_pixels = int(np.count_nonzero(component & (boundary_mask > 0)))
        outside_pixels = int(np.count_nonzero(component & (outside_mask > 0)))
        if min(inside_pixels, boundary_pixels, outside_pixels) < min_pixels:
            continue

        component_mask = component.astype(np.uint8) * 255
        inside_ratio = ratio_in_mask(component_mask, inside_mask)
        boundary_ratio = ratio_in_mask(component_mask, boundary_mask)
        outside_ratio = ratio_in_mask(component_mask, outside_mask)
        score = (
            0.40
            * min(
                1.0,
                inside_ratio / max(config.min_inside_ship_ratio, 1e-6),
            )
            + 0.30
            * min(
                1.0,
                boundary_ratio / max(config.min_boundary_ship_ratio, 1e-6),
            )
            + 0.30
            * min(
                1.0,
                outside_ratio / max(config.min_outside_ship_ratio, 1e-6),
            )
        )

        width = int(stats[label, cv2.CC_STAT_WIDTH])
        height = int(stats[label, cv2.CC_STAT_HEIGHT])
        aspect = float(config.cross_direction_aspect_ratio)
        if width >= max(1.0, height * aspect):
            direction = "H"
        elif height >= max(1.0, width * aspect):
            direction = "V"
        else:
            direction = None

        if score > best_score:
            best_score = score
            best_direction = direction

    return min(1.0, best_score), best_direction


def _probe_rank(
    metrics: dict,
    config: DiamondHitConfig,
    *,
    dx: int,
    dy: int,
) -> float:
    """用多项目标特征选择最有信息量的对称探针。"""
    rank = 0.0
    rank += 2.0 * metrics["center_gray_ratio"]
    rank += 1.2 * metrics["component_ratio"]
    rank += 0.8 * metrics["changed_ratio"]
    rank += 0.6 * metrics["edge_density"]
    rank += 0.8 * metrics["inside_ship_ratio"]
    rank += 0.3 * metrics["cross_boundary_score"]
    rank += 0.004 * max(0.0, metrics["s_drop"])
    if (
        metrics["center_gray_ratio"] >= config.se_probe_min_gray
        and metrics["s_center"] <= config.se_probe_max_s
        and metrics["gray_excess"] >= config.se_probe_min_excess
        and metrics["s_drop"] >= config.se_probe_min_s_drop
    ):
        rank += 0.30

    distance = (
        abs(dx) / max(1.0, config.diamond_w / 2.0)
        + abs(dy) / max(1.0, config.diamond_h / 2.0)
    )
    return rank - 0.08 * distance


def refine_center_by_pair(
    before_bgr: np.ndarray,
    after_bgr: np.ndarray,
    rough_center: Point,
    config: DiamondHitConfig,
) -> Point:
    crop_w = (
        config.diamond_w
        + config.search_radius * 2
        + 60
    )
    crop_h = (
        config.diamond_h
        + config.search_radius * 2
        + 60
    )

    before_crop, local_center, offset = crop_around(
        before_bgr,
        rough_center,
        crop_w,
        crop_h,
    )
    after_crop, _, _ = crop_around(
        after_bgr,
        rough_center,
        crop_w,
        crop_h,
    )

    before_gray = cv2.cvtColor(
        before_crop,
        cv2.COLOR_BGR2GRAY,
    )
    after_gray = cv2.cvtColor(
        after_crop,
        cv2.COLOR_BGR2GRAY,
    )
    diff_gray = cv2.absdiff(
        before_gray,
        after_gray,
    )

    before_hsv = cv2.cvtColor(
        before_crop,
        cv2.COLOR_BGR2HSV,
    )
    _, s_before, v_before = cv2.split(before_hsv)

    before_white = (
        (s_before <= 65)
        & (v_before >= 125)
    ).astype(np.uint8) * 255

    h, w = before_crop.shape[:2]
    step = max(
        1,
        int(config.refine_step),
    )

    best_score = -1e9
    best_center = local_center

    for dy in range(
        -config.search_radius,
        config.search_radius + 1,
        step,
    ):
        for dx in range(
            -config.search_radius,
            config.search_radius + 1,
            step,
        ):
            candidate = (
                local_center[0] + dx,
                local_center[1] + dy,
            )

            inner_mask = make_diamond_mask(
                (h, w),
                candidate,
                config.diamond_w,
                config.diamond_h,
                config.inner_scale,
            )
            full_mask = make_diamond_mask(
                (h, w),
                candidate,
                config.diamond_w,
                config.diamond_h,
                1.0,
            )
            outer_big = make_diamond_mask(
                (h, w),
                candidate,
                config.diamond_w,
                config.diamond_h,
                1.34,
            )
            outer_ring = cv2.subtract(
                outer_big,
                full_mask,
            )

            inner_diff = mean_in_mask(
                diff_gray,
                inner_mask,
            )
            outer_diff = mean_in_mask(
                diff_gray,
                outer_ring,
            )
            white_ratio = ratio_in_mask(
                before_white,
                inner_mask,
            )

            score = (
                inner_diff
                - 0.35 * outer_diff
                + 35.0 * white_ratio
            )

            if score > best_score:
                best_score = score
                best_center = candidate

    return (
        best_center[0] + offset[0],
        best_center[1] + offset[1],
    )


def score_piece(
    value: float,
    threshold: float,
    weight: float,
) -> float:
    if threshold <= 0:
        return 0.0

    if value >= threshold:
        return weight

    ratio = max(
        0.0,
        min(1.0, value / threshold),
    )
    return (
        weight
        * 0.35
        * ratio
    )


def save_debug_images(
    before_crop: np.ndarray,
    after_crop: np.ndarray,
    diff_gray: np.ndarray,
    gray_candidate: np.ndarray,
    inner_mask: np.ndarray,
    center_mask: np.ndarray,
    ring_mask: np.ndarray,
    local_center: Point,
    result_text: str,
    config: DiamondHitConfig,
    index: int,
) -> None:
    os.makedirs(
        config.debug_dir,
        exist_ok=True,
    )

    vis = after_crop.copy()

    overlay = np.zeros_like(vis)
    overlay[:, :, 2] = cv2.bitwise_and(
        gray_candidate,
        gray_candidate,
        mask=center_mask,
    )
    vis = cv2.addWeighted(
        vis,
        0.78,
        overlay,
        0.55,
        0,
    )

    inner_points = diamond_points(
        local_center,
        config.diamond_w,
        config.diamond_h,
        config.inner_scale,
    )
    center_points = diamond_points(
        local_center,
        config.diamond_w,
        config.diamond_h,
        config.center_scale,
    )

    cv2.polylines(
        vis,
        [inner_points],
        True,
        (0, 255, 255),
        1,
    )
    cv2.polylines(
        vis,
        [center_points],
        True,
        (0, 0, 255),
        1,
    )

    cv2.putText(
        vis,
        result_text,
        (5, max(18, vis.shape[0] - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.36,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )

    diff_norm = cv2.normalize(
        diff_gray,
        None,
        0,
        255,
        cv2.NORM_MINMAX,
    )
    diff_color = cv2.applyColorMap(
        diff_norm.astype(np.uint8),
        cv2.COLORMAP_JET,
    )

    cv2.imwrite(
        os.path.join(
            config.debug_dir,
            f"{index:02d}_before_crop.png",
        ),
        before_crop,
    )
    cv2.imwrite(
        os.path.join(
            config.debug_dir,
            f"{index:02d}_after_overlay.png",
        ),
        vis,
    )
    cv2.imwrite(
        os.path.join(
            config.debug_dir,
            f"{index:02d}_diff.png",
        ),
        diff_color,
    )
    cv2.imwrite(
        os.path.join(
            config.debug_dir,
            f"{index:02d}_gray_candidate.png",
        ),
        gray_candidate,
    )
    cv2.imwrite(
        os.path.join(
            config.debug_dir,
            f"{index:02d}_center_mask.png",
        ),
        center_mask,
    )
    cv2.imwrite(
        os.path.join(
            config.debug_dir,
            f"{index:02d}_ring_mask.png",
        ),
        ring_mask,
    )


def classify_diamond_pair(
    before_bgr: np.ndarray,
    after_bgr: np.ndarray,
    rough_center: Point,
    config: "DiamondHitConfig | DiamondPairConfig",
    index: int = 0,
) -> DiamondHitResult:
    return classify_diamond_hit(
        before_bgr,
        after_bgr,
        rough_center,
        config,
        index,
    )


def _validate_screenshot(
    name: str,
    screenshot: np.ndarray,
) -> None:
    if not isinstance(screenshot, np.ndarray):
        raise TypeError(
            f"{name} 必须是 OpenCV 图像对象"
        )

    if (
        screenshot.ndim != 3
        or screenshot.shape[2] != 3
    ):
        raise ValueError(
            f"{name} 必须是 BGR 彩色图片"
        )

    if screenshot.size == 0:
        raise ValueError(
            f"{name} 不能为空"
        )


def _to_point(center: Point) -> Point:
    if len(center) != 2:
        raise ValueError(
            f"center 必须是 (x, y): {center}"
        )

    return int(center[0]), int(center[1])


DiamondPairConfig = DiamondHitConfig
DiamondPairResult = DiamondHitResult


__all__ = [
    "DiamondHitConfig",
    "DiamondHitResult",
    "DiamondPairConfig",
    "DiamondPairResult",
    "classify_diamond_hit",
    "classify_diamond_hit_multiframe",
    "classify_diamond_pair",
    "is_diamond_hit",
    "majority_cell_state",
    "needs_multiframe_confirmation",
]
