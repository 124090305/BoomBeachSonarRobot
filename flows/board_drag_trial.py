"""有界拖动可行性实验；不接入自动循环，不写棋盘和网络。"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import cv2
import numpy as np

from flows.sonar_page import SonarPageState, detect_sonar_page_state
from stop_control import raise_if_stop_requested
from vision.board_alignment import align_board, line_strength
from vision.board_debug import write_image
from vision.board_types import BoardRecognitionConfig
from vision.image_match import read_image


@dataclass(frozen=True)
class BoardDragTrialConfig:
    # 按截图/格宽比例生成手势；禁止在棋盘上起落手指。
    displacement_height_ratio: float = .10
    screen_margin_ratio: float = .025
    title_bottom_ratio: float = .16
    path_cell_margin: float = .6
    path_radius_cell_ratio: float = .12
    gesture_region: tuple[float, float, float, float] = (.86, .64, .96, .82)
    minimum_displacement_px: int = 20
    minimum_water_ratio: float = .96
    duration_ms: int = 700
    settle_seconds: float = .8
    minimum_phase_response: float = .30
    alignment_tolerance_px: float = 3.0
    maximum_horizontal_shift_px: float = 5.0
    minimum_board_motion_px: float = 12.0


class BoardDragTrialError(RuntimeError):
    pass


@dataclass(frozen=True)
class DragPlan:
    start: tuple[int, int]
    end: tuple[int, int]
    corridor_radius: int


def _water_corridor(image, plan, cfg, vision_cfg):
    mask = np.zeros(image.shape[:2], np.uint8)
    cv2.line(mask, plan.start, plan.end, 1, plan.corridor_radius * 2 + 1)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    water = ((hsv[:, :, 0] >= vision_cfg.water_hue_range[0])
             & (hsv[:, :, 0] <= vision_cfg.water_hue_range[1])
             & (hsv[:, :, 1] >= vision_cfg.water_saturation_min))
    return bool(mask.any() and float(water[mask > 0].mean()) >= cfg.minimum_water_ratio)


def plan_board_drag(image, level, cfg=BoardDragTrialConfig()) -> DragPlan:
    """只选右下弹药栏上方海面，向下移动后整个棋盘仍在屏幕内。"""
    if level.board_quad is None:
        raise BoardDragTrialError("缺少棋盘位置配置")
    height, width = image.shape[:2]
    quad = np.asarray(level.board_quad, dtype=float)
    margin = max(1, round(min(height, width) * cfg.screen_margin_ratio))
    displacement = min(round(height * cfg.displacement_height_ratio),
                       int(height - margin - quad[:, 1].max()))
    if displacement < cfg.minimum_displacement_px:
        raise BoardDragTrialError("棋盘下方空间不足，拒绝拖动")
    cell_width = np.ptp(quad[:, 0]) / level.grid_size
    radius = max(2, round(cell_width * cfg.path_radius_cell_ratio))
    rx0, ry0, rx1, ry1 = cfg.gesture_region
    x0, y0, x1, y1 = round(rx0*width), round(ry0*height), round(rx1*width), round(ry1*height)
    x = min(x1-radius-1, max(round((x0+x1)/2), round(quad[:, 0].max() + cell_width * cfg.path_cell_margin)))
    if (x - radius <= quad[:, 0].max() or x - radius < max(x0, margin)
            or x + radius >= min(x1, width-margin)):
        raise BoardDragTrialError("棋盘外没有足够宽的安全手势通道")
    start_y = max(y0+radius, round(height * cfg.title_bottom_ratio) + radius)
    for y in range(start_y, min(y1, height-margin) - displacement - radius, max(radius, 1)):
        plan = DragPlan((x, y), (x, y + displacement), radius)
        if _water_corridor(image, plan, cfg, BoardRecognitionConfig()):
            return plan
    raise BoardDragTrialError("棋盘外通道有按钮、文字或非海面区域，拒绝拖动")


def measure_translation(before, after, level, cfg=BoardDragTrialConfig()):
    """估计大位移，再复用正式网格配准复核；此结果只用于实验诊断。"""
    if before.shape != after.shape:
        raise BoardDragTrialError("截图分辨率发生变化")
    vision_cfg = BoardRecognitionConfig()
    mask = np.zeros(before.shape[:2], np.float32)
    quad = np.asarray(level.board_quad)
    height, width = mask.shape
    margin = round(min(height, width) * cfg.screen_margin_ratio)
    x0, x1 = max(margin, int(quad[:, 0].min())), min(width-margin, int(quad[:, 0].max()))
    y0 = max(margin, round(height * cfg.title_bottom_ratio))
    mask[y0:height-margin, x0:x1] = 1
    shift, response = cv2.phaseCorrelate(line_strength(before, vision_cfg) * mask,
                                        line_strength(after, vision_cfg) * mask)
    dx, dy = shift
    if not np.isfinite([dx, dy, response]).all() or response < cfg.minimum_phase_response:
        raise BoardDragTrialError("棋盘位移证据不足，不能确认相机位置")
    compensated = cv2.warpAffine(after, np.float32([[1, 0, -dx], [0, 1, -dy]]), (width, height))
    _, _, alignment = align_board(before, compensated, level, vision_cfg)
    if not alignment.success or alignment.max_shift_px > cfg.alignment_tolerance_px:
        raise BoardDragTrialError("位移估计未通过正式网格配准复核")
    return {"dx": float(dx), "dy": float(dy), "response": float(response),
            "alignment": asdict(alignment)}


def run_board_drag_trial(adb, page, level, output_dir, *, execute=False,
                         cfg=BoardDragTrialConfig(), stop_event=None):
    """默认只输出路线图。execute 必须由人工确认现场后显式开启。"""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    report = {"executed": False, "restored": None, "config": asdict(cfg)}
    before = adb.read_screenshot()
    write_image(output / "before.png", before)
    if detect_sonar_page_state(page, screenshot=before, stop_event=stop_event) != SonarPageState.ACTIVITY_DETAIL:
        raise BoardDragTrialError("请先暂停循环并进入声纳棋盘页")
    if level.empty_reference_path is None:
        raise BoardDragTrialError("缺少当前关卡空棋盘参考图")
    reference = read_image(level.empty_reference_path)
    if reference.shape != before.shape:
        raise BoardDragTrialError("参考图与实机分辨率不一致")
    _, _, alignment = align_board(reference, before, level, BoardRecognitionConfig())
    if not alignment.success:
        raise BoardDragTrialError("当前配置无法可靠定位棋盘，拒绝拖动")
    plan = plan_board_drag(before, level, cfg)
    report["plan"] = asdict(plan)
    overlay = before.copy()
    cv2.polylines(overlay, [np.int32(level.board_quad)], True, (0, 255, 255), 2)
    cv2.arrowedLine(overlay, plan.start, plan.end, (0, 255, 0), plan.corridor_radius * 2 + 1)
    write_image(output / "plan.png", overlay)
    if not execute:
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    raise_if_stop_requested(stop_event)
    try:
        # 一个手势不插入停止点；之后必须先判断位置并处理复位。
        report["executed"] = True
        page.swipe(*plan.start, *plan.end, duration_ms=cfg.duration_ms, wait_seconds=cfg.settle_seconds)
        after = adb.read_screenshot()
        write_image(output / "after.png", after)
        if detect_sonar_page_state(page, screenshot=after) != SonarPageState.ACTIVITY_DETAIL:
            raise BoardDragTrialError("拖动后页面异常，停止操作并请人工检查")
        movement = measure_translation(before, after, level, cfg)
        report["movement"] = movement
        if abs(movement["dx"]) > cfg.maximum_horizontal_shift_px:
            raise BoardDragTrialError("发生非预期横向位移，停止自动操作")
        if abs(movement["dy"]) <= cfg.alignment_tolerance_px:
            report["restored"] = True
            report["conclusion"] = "棋盘没有有效移动；不执行反向手势，不启用补拍"
        else:
            report["conclusion"] = "棋盘发生移动；需人工比较文字相对位置和格子内容"
    finally:
        # 出错/停止也检查现场；只有页面、位移和海面通道均可靠时才反向一次。
        if report["executed"] and report["restored"] is not True:
            try:
                current = adb.read_screenshot()
                if detect_sonar_page_state(page, screenshot=current) != SonarPageState.ACTIVITY_DETAIL:
                    raise BoardDragTrialError("页面异常，无法安全复位")
                move = measure_translation(before, current, level, cfg)
                if abs(move["dx"]) > cfg.maximum_horizontal_shift_px:
                    raise BoardDragTrialError("横向位移异常，需人工复位")
                if abs(move["dy"]) > cfg.alignment_tolerance_px:
                    requested = plan.end[1] - plan.start[1]
                    if not cfg.minimum_board_motion_px <= move["dy"] <= requested + cfg.alignment_tolerance_px:
                        raise BoardDragTrialError("位移方向/幅度不明确，需人工复位")
                    if not _water_corridor(current, plan, cfg, BoardRecognitionConfig()):
                        raise BoardDragTrialError("返回路径已被遮挡，需人工复位")
                    page.swipe(*plan.end, *plan.start, duration_ms=cfg.duration_ms, wait_seconds=cfg.settle_seconds)
                returned = adb.read_screenshot()
                write_image(output / "returned.png", returned)
                if detect_sonar_page_state(page, screenshot=returned) != SonarPageState.ACTIVITY_DETAIL:
                    raise BoardDragTrialError("返回后页面异常")
                final = measure_translation(before, returned, level, cfg)
                report["return_movement"] = final
                report["restored"] = max(abs(final["dx"]), abs(final["dy"])) <= cfg.alignment_tolerance_px
            except Exception as exc:
                report["restored"] = False
                report["restore_error"] = str(exc)
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not report["restored"]:
        raise BoardDragTrialError("未验证棋盘恢复原位；请人工检查，禁止直接恢复自动循环")
    raise_if_stop_requested(stop_event)
    return report
