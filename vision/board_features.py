"""空基准对照特征、遮挡识别及图像内的整船连续性校验。"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
import math

import cv2
import numpy as np

from sonar.board import CellState
from .board_alignment import line_strength
from .board_types import CellRecognitionResult, RecognizedSubmarine


def unit(value):
    return float(np.clip(value, 0.0, 1.0))


def panel_occlusion(rectified, cfg):
    hsv = cv2.cvtColor(rectified, cv2.COLOR_BGR2HSV).astype(np.float32)
    value = hsv[:, :, 2]
    size = max(3, cfg.cell_pixels//4)
    mean = cv2.boxFilter(value, -1, (size, size))
    variance = np.maximum(0, cv2.boxFilter(value*value, -1, (size, size))-mean*mean)
    flat = ((hsv[:, :, 1] < cfg.panel_saturation_max) & (variance < cfg.panel_std_max**2)).astype(np.uint8)
    _, labels, stats, _ = cv2.connectedComponentsWithStats(flat)
    result = np.zeros_like(flat)
    for label, (x, y, w, h, area) in enumerate(stats[1:], start=1):
        if area >= cfg.panel_min_cells*cfg.cell_pixels**2 and min(w, h) >= cfg.panel_min_extent*cfg.cell_pixels:
            result[labels == label] = 255
    return cv2.dilate(result, np.ones((size, size), np.uint8))


def anchor_ship_features(features, padding, grid_size, cfg):
    """立体船体回投到水面；方向明确时用主体所在行/列消除船壳擦边。"""
    side = cfg.cell_pixels
    shift = round(side*cfg.sunk_anchor_shift)
    matrix = np.float32([[1, 0, shift], [0, 1, shift]])
    shape = features["ship"].shape[1::-1]
    ship = cv2.warpAffine(features["ship"], matrix, shape)
    features["edge"] = cv2.warpAffine(features["edge"].astype(np.uint8), matrix, shape) > 0
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ship)
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        if max(w, h) < side*1.2:
            continue
        ys, xs = np.where(labels[y:y+h, x:x+w] == label)
        xs, ys = xs+x, ys+y
        centered = np.column_stack((xs-xs.mean(), ys-ys.mean()))
        values, vectors = np.linalg.eigh(centered.T @ centered / len(xs))
        ratio = math.sqrt(max(values[-1], 1)/max(values[0], 1))
        axis = vectors[:, -1]
        angle = math.degrees(math.atan2(abs(axis[1]), abs(axis[0])))
        if ratio < cfg.sunk_axis_ratio:
            continue
        if angle <= cfg.sunk_direction_degrees:
            lanes = (ys-padding)//side
        elif angle >= 90-cfg.sunk_direction_degrees:
            lanes = (xs-padding)//side
        else:
            continue
        lane, support = Counter(lanes).most_common(1)[0]
        if 0 <= lane < grid_size and support/area >= cfg.ship_lane_dominance:
            remove = lanes != lane
            ship[ys[remove], xs[remove]] = 0
    features["ship"] = ship


def text_occlusion(image, cell_width, cfg):
    """把多块横排白字合组，避免把单块船体当作文字。"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    white = ((hsv[:, :, 1] < cfg.text_saturation_max)
             & (hsv[:, :, 2] > cfg.text_white_min)).astype(np.uint8)
    dark_neighbor = cv2.dilate((hsv[:, :, 2] < cfg.text_dark_max).astype(np.uint8),
                               np.ones((5, 5), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(white)
    glyphs = np.zeros_like(white)
    boxes = []
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        local = labels[y:y+h, x:x+w] == label
        outlined = float(dark_neighbor[y:y+h, x:x+w][local].mean())
        if (cfg.text_glyph_area[0] <= area <= cfg.text_glyph_area[1]
                and 4 <= h <= cfg.text_max_glyph_height
                and cfg.text_glyph_width[0] <= w <= cfg.text_glyph_width[1]
                and outlined >= cfg.text_dark_fraction):
            boxes.append((x, y, w, h))
            glyphs[y+h//2, x+w//2] = 255
    grouped = cv2.dilate(glyphs, np.ones((9, cfg.text_join_px+8), np.uint8))
    _, groups, group_stats, _ = cv2.connectedComponentsWithStats(grouped)
    result = np.zeros_like(white)
    for label, (x, y, w, h, _) in enumerate(group_stats[1:], start=1):
        members = [(gx, gy, gw, gh) for gx, gy, gw, gh in boxes
                   if groups[gy+gh//2, gx+gw//2] == label]
        if (len(members) >= cfg.text_min_glyphs and w >= cell_width * cfg.text_group_width_cells
                and h <= cfg.text_max_glyph_height*1.8 and w >= h*2):
            left, top = min(v[0] for v in members), min(v[1] for v in members)
            right, bottom = max(v[0]+v[2] for v in members), max(v[1]+v[3] for v in members)
            cv2.rectangle(result, (left-2, top-2), (right+2, bottom+2), 255, -1)
    return result


def prepare_features(reference, current, cfg):
    # 使用整盘中位数做有界色偏补偿；大面积已探测时只补偿亮度共同分量。
    ref_hsv = cv2.cvtColor(reference, cv2.COLOR_BGR2HSV).astype(np.float32)
    cur_hsv = cv2.cvtColor(current, cv2.COLOR_BGR2HSV).astype(np.float32)
    ref_lines, cur_lines = line_strength(reference, cfg), line_strength(current, cfg)
    matched = (ref_lines > cfg.reference_line_threshold) & (cur_lines > cfg.reference_line_threshold)
    offset = float(np.median(cur_hsv[:, :, 2][matched]-ref_hsv[:, :, 2][matched])) if matched.any() else 0.0
    offset = np.clip(offset, -cfg.brightness_offset_limit, cfg.brightness_offset_limit)
    corrected = np.clip(current.astype(np.float32)-offset, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(corrected, cv2.COLOR_BGR2HSV).astype(np.float32)
    ref_lab = cv2.cvtColor(reference, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab = cv2.cvtColor(corrected, cv2.COLOR_BGR2LAB).astype(np.float32)
    difference = np.linalg.norm(cv2.GaussianBlur(lab, (5, 5), 0)
                                - cv2.GaussianBlur(ref_lab, (5, 5), 0), axis=2)
    neutral = ((hsv[:, :, 1] < cfg.ship_saturation_max)
               & (hsv[:, :, 2] > cfg.ship_value_min)
               & (np.ptp(corrected.astype(np.float32), axis=2) < cfg.ship_chroma_max))
    novelty = ((ref_hsv[:, :, 1]-hsv[:, :, 1] > cfg.ship_saturation_drop)
               | (np.abs(hsv[:, :, 2]-ref_hsv[:, :, 2]) > cfg.ship_luma_change))
    ship = (neutral & novelty).astype(np.uint8)
    kernel = max(1, round(cfg.cell_pixels * cfg.ship_close_ratio))
    ship = cv2.morphologyEx(ship, cv2.MORPH_CLOSE, np.ones((kernel, kernel), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ship)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] < cfg.cell_pixels**2 * cfg.ship_component_min_ratio:
            ship[labels == label] = 0
    edge = cv2.Canny(cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY), *cfg.edge_thresholds) > 0
    return dict(reference_hsv=ref_hsv, hsv=hsv, reference_lab=ref_lab, lab=lab,
                reference_lines=ref_lines, lines=line_strength(corrected, cfg),
                ship=ship, edge=edge, difference=difference, brightness_offset=offset)


def classify_cells(features, occlusion, missing_pixels, static_occlusion,
                   grid_size, padding, alignment, cfg):
    cells = []
    side = cfg.cell_pixels
    coordinates = np.indices((side, side))
    distance = np.minimum.reduce([coordinates[0], coordinates[1],
                                  side-1-coordinates[0], side-1-coordinates[1]]) / side
    inner = distance >= cfg.inner_margin
    ring = distance < cfg.border_band
    tolerance = cfg.border_tolerance_px
    tolerant_lines = cv2.dilate(features["lines"], np.ones((2*tolerance+1, 2*tolerance+1), np.uint8))
    for row in range(grid_size):
        for col in range(grid_size):
            y, x = padding+row*side, padding+col*side
            box = np.s_[y:y+side, x:x+side]
            ref_hsv, hsv = features["reference_hsv"][box], features["hsv"][box]
            ref_line = features["reference_lines"][box]
            weights = (ref_line > cfg.reference_line_threshold) & ring
            border = unit(np.mean(tolerant_lines[box][weights]) /
                          max(np.mean(ref_line[weights]), 0.01)) if weights.any() else 0.0
            ref_color = np.median(features["reference_lab"][box][inner], axis=0)
            color = np.median(features["lab"][box][inner], axis=0)
            color_change = unit(np.linalg.norm(color-ref_color) / cfg.color_difference_scale)
            sat_rise = unit((np.median(hsv[:, :, 1][inner])-np.median(ref_hsv[:, :, 1][inner])) / cfg.open_saturation_scale)
            darkening = unit((np.median(ref_hsv[:, :, 2][inner])-np.median(hsv[:, :, 2][inner])) / cfg.open_darkening_scale)
            ship_patch = features["ship"][box]
            ship_ratio = float(ship_patch[inner].mean())
            edge_density = float((features["edge"][box] & (ship_patch > 0))[inner].mean())
            ship_strength = unit(ship_ratio / cfg.ship_ratio_scale)
            texture = unit(edge_density / cfg.ship_texture_scale)
            # 船体需要中性前景与轮廓/纹理的联合支持。
            ship_base, ship_texture = cfg.ship_evidence_weights
            hit = (ship_strength * (ship_base + ship_texture * texture)
                   * (1-cfg.intact_border_ship_penalty*border**3))
            o_border, o_sat, o_dark = cfg.open_evidence_weights
            u_border, u_color = cfg.unknown_evidence_weights
            opened = unit(o_border*(1-border) + o_sat*sat_rise + o_dark*darkening)
            unknown = unit((u_border*border+u_color*(1-color_change))*(1-cfg.ship_suppression[0]*hit))
            miss = unit(opened * (1-cfg.ship_suppression[1]*hit))
            state_scores = {"unknown": unknown, "miss": miss, "hit": hit, "sunk": 0.0}
            ordered = sorted(state_scores, key=state_scores.get, reverse=True)
            chosen, runner = ordered[:2]
            margin = state_scores[chosen]-state_scores[runner]
            extreme = ((hsv[:, :, 2] < cfg.occlusion_value_low)
                       | ((hsv[:, :, 2] > cfg.occlusion_value_high) & (hsv[:, :, 1] < 35)))
            extreme_ratio = float(extreme[inner].mean())
            occluded = max(float((occlusion[box][inner] > 0).mean()),
                           extreme_ratio if extreme_ratio >= cfg.occlusion_extreme_ratio else 0.0,
                           float((missing_pixels[box][inner] > 0).mean()))
            static_ratio = float((static_occlusion[box][inner] > 0).mean())
            # 没有可观测亮框的基准区域不能给予高置信 UNKNOWN。
            observable = min(1.0, float(weights.sum()) / max(1, side * 1.5))
            evidence_agreement = (border if chosen == "unknown" else
                                  (opened if chosen == "miss" else ship_strength))
            a, b, c = cfg.confidence_weights
            confidence = unit((a*state_scores[chosen] + b*unit(margin) + c*evidence_agreement)
                              * alignment.confidence * (1-occluded) * (1-static_ratio)
                              * (0.5+0.5*observable))
            reasons = [f"{chosen}: border={border:.2f}, ship={ship_ratio:.3f}, margin={margin:.2f}"]
            if not alignment.success:
                confidence = min(confidence, cfg.failed_confidence_cap)
                reasons.append("对齐失败，仅保留低可信候选")
            if occluded >= cfg.occlusion_review_ratio or static_ratio >= cfg.occlusion_review_ratio:
                reasons.append("当前或基准区域存在遮挡")
            if margin < cfg.review_margin:
                reasons.append("多个状态证据接近")
            cells.append(CellRecognitionResult(
                row=row, col=col, state=CellState(chosen), confidence=confidence,
                needs_review=(confidence < cfg.review_confidence or margin < cfg.review_margin),
                reason="；".join(reasons), state_scores=state_scores,
                feature_scores=dict(border_retention=border, color_change=color_change,
                                    saturation_rise=sat_rise, darkening=darkening,
                                    ship_ratio=ship_ratio, ship_texture=texture,
                                    occlusion_ratio=occluded, reference_occlusion=static_ratio,
                                    reference_observable=observable, candidate_margin=margin),
            ))
    return cells


def confirm_sunk(cells, ship_mask, level, padding, alignment, cfg):
    """只从本张图的连通船体形成段，再做整盘长度/数量/重叠校验。"""
    side, n = cfg.cell_pixels, level.grid_size
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ship_mask)
    candidates, warnings, conflicts = [], [], set()
    candidate_components = {}
    for label in range(1, count):
        ys, xs = np.where(labels == label)
        if len(xs) < side**2 * cfg.sunk_cell_support:
            continue
        centered = np.column_stack((xs-xs.mean(), ys-ys.mean()))
        values, vectors = np.linalg.eigh(centered.T @ centered / len(xs))
        axis = vectors[:, -1]
        ratio = math.sqrt(max(values[-1], 1) / max(values[0], 1))
        angle = math.degrees(math.atan2(abs(axis[1]), abs(axis[0])))
        direction = "H" if angle <= cfg.sunk_direction_degrees else "V" if angle >= 90-cfg.sunk_direction_degrees else None
        contacts = []
        for cell in cells:
            x, y = padding+cell.col*side, padding+cell.row*side
            overlap = float((labels[y:y+side, x:x+side] == label).mean())
            if overlap >= cfg.sunk_cell_support and cell.state == CellState.HIT:
                contacts.append((cell.row, cell.col))
        if len(contacts) < 2:
            continue
        if direction is None or ratio < cfg.sunk_axis_ratio:
            conflicts.update(contacts)
            warnings.append(f"船体连通块方向不明确：{contacts}")
            continue
        groups = {}
        for row, col in contacts:
            groups.setdefault(row if direction == "H" else col, []).append((row, col))
        for group in groups.values():
            group.sort()
            indexes = [col if direction == "H" else row for row, col in group]
            if len(group) < 2:
                continue
            if indexes != list(range(indexes[0], indexes[-1]+1)):
                conflicts.update(group)
                warnings.append(f"船体跨格支持不连续：{group}")
                continue
            bridges = []
            for (r1, c1), (r2, c2) in zip(group, group[1:]):
                if direction == "H":
                    x = padding+c2*side
                    y = padding+r1*side
                    corridor = labels[y:y+side, x-2:x+3] == label
                    bridge = float(np.mean(np.any(corridor, axis=1)))
                else:
                    y = padding+r2*side
                    x = padding+c1*side
                    corridor = labels[y-2:y+3, x:x+side] == label
                    bridge = float(np.mean(np.any(corridor, axis=0)))
                bridges.append(bridge)
            extent = (np.ptp(xs) if direction == "H" else np.ptp(ys)) / (len(group)*side)
            if min(bridges) < cfg.sunk_bridge_min or extent < cfg.sunk_min_extent:
                continue
            if len(group) not in level.submarines:
                conflicts.update(group)
                warnings.append(f"连续船体长度{len(group)}不在当前关卡配置：{group}")
                continue
            support = np.mean([cells[r*n+c].state_scores["hit"] for r, c in group])
            quality = min(1-cells[r*n+c].feature_scores["occlusion_ratio"] for r, c in group)
            s_support, s_bridge, s_extent = cfg.sunk_evidence_weights
            structure = unit(s_support*support + s_bridge*min(1, min(bridges)/cfg.sunk_bridge_min)
                             + s_extent*min(1, extent))
            confidence = structure * alignment.confidence * quality
            if not alignment.success or confidence < cfg.sunk_min_confidence:
                conflicts.update(group)
                continue
            candidates.append(RecognizedSubmarine(tuple(group), direction, len(group),
                                                   confidence, tuple(bridges),
                                                   "同一船体连通块跨越全部相邻格界，方向/长度一致"))
            candidate_components[(tuple(group), direction)] = label
    # 相交、多解释、超出数量的候选全部保留为 HIT 待复核，不按遍历顺序抢占。
    candidates = list({(ship.cells, ship.direction): ship for ship in candidates}.values())
    available, used = Counter(level.submarines), Counter(ship.length for ship in candidates)
    accepted = []
    for ship in candidates:
        overlap = any(set(ship.cells).intersection(other.cells) for other in candidates if other is not ship)
        ambiguous_component = any(
            candidate_components[(ship.cells, ship.direction)]
            == candidate_components[(other.cells, other.direction)]
            for other in candidates if other is not ship
        )
        touching = level.use_safety_rule and any(
            min(max(abs(r-r2), abs(c-c2)) for r, c in ship.cells for r2, c2 in other.cells) <= 1
            for other in candidates if other is not ship
        )
        adjacent_hit = level.use_safety_rule and any(
            cell.state == CellState.HIT and not cell.needs_review
            and (cell.row, cell.col) not in ship.cells
            and min(max(abs(cell.row-r), abs(cell.col-c)) for r, c in ship.cells) <= 1
            for cell in cells
        )
        if overlap or ambiguous_component or touching or adjacent_hit or used[ship.length] > available[ship.length]:
            conflicts.update(ship.cells)
            warnings.append(f"潜艇候选多解释/重叠/安全间距/数量冲突：{ship.cells}")
            continue
        accepted.append(ship)
    for ship in accepted:
        for row, col in ship.cells:
            index = row*n+col
            cell = cells[index]
            evidence = unit(ship.confidence / max(alignment.confidence, 0.01))
            scores = {**cell.state_scores, "hit": cell.state_scores["hit"]*(1-evidence), "sunk": evidence}
            margin = scores["sunk"]-max(v for k, v in scores.items() if k != "sunk")
            a, b, c = cfg.confidence_weights
            confidence = unit((a*evidence+b*margin+c*evidence) * alignment.confidence
                              * (1-cell.feature_scores["occlusion_ratio"])
                              * (1-cell.feature_scores["reference_occlusion"]))
            cells[index] = replace(cell, state=CellState.SUNK, confidence=confidence,
                                   needs_review=confidence < cfg.review_confidence,
                                   reason=ship.reason, state_scores=scores,
                                   feature_scores={**cell.feature_scores, "candidate_margin": margin,
                                                   "sunk_structure": evidence})
    for row, col in conflicts:
        index = row*n+col
        cells[index] = replace(cells[index], confidence=min(cells[index].confidence, cfg.conflict_confidence_cap),
                               needs_review=True, reason=cells[index].reason+"；整船结构存在冲突")
    return cells, tuple(accepted), tuple(dict.fromkeys(warnings))
