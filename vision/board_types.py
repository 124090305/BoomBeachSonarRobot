"""单帧全盘识别的数据契约；不含棋盘历史或策略对象。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sonar.board import CellState


def parameter(default, help_text: str):
    return field(default=default, metadata={"help": help_text})


@dataclass(frozen=True)
class BoardRecognitionConfig:
    """所有视觉可调参数。help 描述增大参数的效果，减小则相反。"""

    cell_pixels: int = parameter(64, "透视校正后每格像素；增大提高细节与开销")
    padding_cells: float = parameter(0.75, "校正图外围留白格数；增大保留更多船体外延")
    alignment_search_px: int = parameter(12, "原图局部配准搜索半径；增大容忍更大位移，也增加错配风险")
    alignment_max_shift_px: float = parameter(22.0, "四角最大位移；增大放宽配准几何约束")
    alignment_min_anchor_score: float = parameter(0.42, "网格锚点最低匹配分；增大减少弱锚点")
    alignment_min_anchors: int = parameter(5, "配准最少锚点；增大要求更多可见网格")
    alignment_ransac_px: float = parameter(2.2, "RANSAC内点误差；增大容忍局部变形")
    alignment_min_coverage: float = parameter(0.24, "锚点凸包占棋盘面积下限；增大抑制局部配准冒充全盘")
    alignment_min_confidence: float = parameter(0.55, "可用配准置信度下限；增大更保守")
    alignment_max_area_change: float = parameter(0.12, "棋盘面积变化比例上限；增大容忍缩放")
    line_blur_sigma: float = parameter(3.0, "提取亮边框的背景模糊尺度；增大突出较宽线条")
    line_contrast: float = parameter(30.0, "亮边框局部对比度归一尺度；增大降低边框响应")
    line_saturation_max: float = parameter(160.0, "边框颜色饱和度上限；增大接受更蓝的线条")
    line_saturation_scale: float = parameter(70.0, "边框饱和度权重的过渡范围；增大降低颜色响应")
    line_value_min: float = parameter(100.0, "边框最低亮度；增大排除暗纹理")
    reference_line_threshold: float = parameter(0.30, "基准亮线阈值；增大只保留强边框")
    border_band: float = parameter(0.18, "每格边界带宽占比；增大覆盖更偏移的实际边框")
    inner_margin: float = parameter(0.19, "格内统计的边缘排除占比；增大减少边缘污染")
    border_tolerance_px: int = parameter(1, "校正图边框匹配膨胀半径；增大容忍残余偏差")
    brightness_offset_limit: float = parameter(28.0, "全局亮度补偿上限；增大接受更明显光照变化")
    color_difference_scale: float = parameter(35.0, "Lab中值差异归一尺度；增大降低差异证据")
    ship_saturation_max: float = parameter(82.0, "中性船体像素饱和度上限；增大接受更蓝的金属")
    ship_value_min: float = parameter(65.0, "船体最低亮度；增大排除暗部")
    ship_chroma_max: float = parameter(64.0, "船体BGR最大通道差；增大放宽中性色限制")
    ship_saturation_drop: float = parameter(22.0, "相对基准的饱和度下降；增大要求更明显金属变化")
    ship_luma_change: float = parameter(32.0, "相对基准的亮度差；增大抑制海面闪光")
    ship_component_min_ratio: float = parameter(0.012, "船体最小连通块占单格面积比例；增大排除碎噪声")
    ship_close_ratio: float = parameter(0.035, "船体闭运算尺寸占单格比例；增大连接较宽小裂缝")
    ship_ratio_scale: float = parameter(0.14, "格内船体占比归一尺度；增大要求更多船体证据")
    ship_texture_scale: float = parameter(0.10, "船体边缘密度尺度；增大要求更多纹理")
    ship_evidence_weights: tuple = parameter((0.72, 0.28), "船体覆盖和纹理权重；增大第二项更依赖纹理")
    edge_thresholds: tuple = parameter((50, 115), "Canny弱/强边缘阈值；增大减少细纹理响应")
    intact_border_ship_penalty: float = parameter(0.75, "完整亮边框对船体证据的抑制；增大减少未探测格浪花误报")
    open_saturation_scale: float = parameter(58.0, "探测后饱和度上升尺度；增大降低水面证据")
    open_darkening_scale: float = parameter(45.0, "探测后变暗尺度；增大降低暗水面证据")
    open_evidence_weights: tuple = parameter((0.68, 0.20, 0.12), "开格的边框缺失、饱和度、变暗权重；增大某项提高其影响")
    unknown_evidence_weights: tuple = parameter((0.85, 0.15), "未探测的边框、颜色相似权重；增大某项提高其影响")
    ship_suppression: tuple = parameter((0.90, 0.92), "船体对UNKNOWN/MISS的抑制权重；增大更偏向HIT")
    review_confidence: float = parameter(0.66, "低可信复核阈值；增大标记更多格")
    review_margin: float = parameter(0.20, "候选分差下限；增大对竞争状态更保守")
    confidence_weights: tuple = parameter((0.45, 0.35, 0.20), "最高分、分差、证据一致性的权重；增大某项提高其影响")
    failed_confidence_cap: float = parameter(0.20, "对齐失败时置信度上限；增大提高失败结果的上限")
    conflict_confidence_cap: float = parameter(0.50, "结构冲突时置信度上限；增大提高冲突结果的上限")
    occlusion_value_low: int = parameter(28, "黑色遮挡亮度上限；增大覆盖更多暗面板")
    occlusion_value_high: int = parameter(239, "白色遮挡亮度下限；增大减少白色面板检出")
    occlusion_extreme_ratio: float = parameter(0.50, "格内极黑/白比例；增大减少遮挡误报")
    occlusion_review_ratio: float = parameter(0.20, "遮挡比例复核阈值；增大容忍更大遮挡")
    panel_saturation_max: float = parameter(35.0, "大块面板的饱和度上限；增大接受带颜色的面板")
    panel_std_max: float = parameter(5.0, "面板局部亮度标准差上限；增大接受更有纹理的面板")
    panel_min_cells: float = parameter(2.5, "平坦面板最小面积，以格为单位；增大减少船壳误报")
    panel_min_extent: float = parameter(1.4, "面板最短边对应格数；增大减少窄船体误报")
    text_white_min: int = parameter(212, "文字白色笔画亮度；增大减少波纹误检")
    text_saturation_max: int = parameter(70, "文字低饱和范围；增大接受有色文字")
    text_dark_max: int = parameter(60, "文字描边最大亮度；增大接受更浅的描边")
    text_dark_fraction: float = parameter(0.16, "白色笔画附近深色比例；增大减少浪花/格线误报")
    text_min_glyphs: int = parameter(5, "水平文字组最少小连通块；增大减少船体误判")
    text_max_glyph_height: int = parameter(30, "文字单块最大原图高度；增大接受大字")
    text_glyph_area: tuple = parameter((4, 240), "文字块面积范围；扩大范围接受更多字体及噪声")
    text_glyph_width: tuple = parameter((2, 32), "文字块宽度范围；扩大范围接受更多字体及噪声")
    text_group_width_cells: float = parameter(1.4, "文字组最小宽度相对原图格宽；增大减少短字符误检")
    text_join_px: int = parameter(20, "文字横向组团距离；增大连接更疏的字")
    wrong_page_water_ratio: float = parameter(0.15, "对齐失败时水面占比下限；增大更容易判为错误页面")
    sunk_cell_support: float = parameter(0.055, "船体连通块覆盖单格比例下限；增大排除擦边格")
    sunk_axis_ratio: float = parameter(1.35, "船体主/次轴比例下限；增大要求更直更长，可能漏掉短艇")
    sunk_direction_degrees: float = parameter(25.0, "主轴与逻辑H/V的角度容差；增大接受更斜的船体")
    sunk_bridge_min: float = parameter(0.16, "跨相邻格界的船体宽度占比；增大要求更明显连接")
    sunk_min_extent: float = parameter(0.60, "船体沿候选段长度的最低覆盖比例；增大要求船体更完整")
    sunk_anchor_shift: float = parameter(0.16, "船体立体上浮的逻辑格回投补偿；增大将船体归属向下移动")
    ship_lane_dominance: float = parameter(0.60, "连续船体归属单一逻辑行/列所需像素占比；增大对宽船体归属更保守")
    sunk_min_confidence: float = parameter(0.68, "SUNK结构确认最低综合证据；增大减少提前确认")
    sunk_evidence_weights: tuple = parameter((0.40, 0.35, 0.25), "SUNK单格支持、边界连接、长度覆盖权重；增大某项提高其影响")
    water_hue_range: tuple = parameter((75, 125), "OpenCV海水色相范围；扩大范围减少错误页面报警")
    water_saturation_min: int = parameter(50, "海水最低饱和度；增大排除灰色面板")
    quality_occluded_fraction: float = parameter(0.06, "动态遮挡占棋盘比例；增大放宽素材可用门槛")
    max_review_fraction: float = parameter(0.25, "整盘可用标志允许的最大复核格比例；增大放宽总体门槛")

    def __post_init__(self):
        if self.cell_pixels < 16 or self.alignment_search_px < 0 or self.padding_cells < 0:
            raise ValueError("cell_pixels至少16，搜索半径和padding不得为负")
        if not 0 < self.inner_margin < 0.5 or not 0 < self.border_band < 0.5:
            raise ValueError("格内margin和边界band必须在(0, 0.5)内")
        for name in ("confidence_weights", "ship_evidence_weights", "open_evidence_weights",
                     "unknown_evidence_weights", "sunk_evidence_weights"):
            weights = getattr(self, name)
            if any(v < 0 for v in weights) or abs(sum(weights)-1) > 1e-6:
                raise ValueError(f"{name}必须是和为1的非负权重")


@dataclass(frozen=True)
class AlignmentResult:
    success: bool
    confidence: float
    score: float
    current_to_reference: tuple[tuple[float, ...], ...]
    anchor_count: int
    inlier_count: int
    coverage: float
    residual_px: float
    max_shift_px: float
    reason: str
    method: str = "grid_local_ransac_homography"


@dataclass(frozen=True)
class CellRecognitionResult:
    row: int
    col: int
    state: CellState
    confidence: float
    needs_review: bool
    reason: str
    feature_scores: dict[str, float]
    state_scores: dict[str, float]


@dataclass(frozen=True)
class RecognizedSubmarine:
    cells: tuple[tuple[int, int], ...]
    direction: str
    length: int
    confidence: float
    bridge_scores: tuple[float, ...]
    reason: str


@dataclass(frozen=True)
class BoardRecognitionResult:
    grid_size: int
    states: tuple[tuple[CellState, ...], ...]
    cells: tuple[CellRecognitionResult, ...]
    counts: dict[str, int]
    review_cells: tuple[tuple[int, int], ...]
    sunk_submarines: tuple[RecognizedSubmarine, ...]
    alignment: AlignmentResult
    quality: str
    quality_score: float
    valid: bool
    issues: tuple[str, ...]
    debug_paths: dict[str, str] = field(default_factory=dict)
    schema_version: int = 1

    def cell_at(self, row: int, col: int) -> CellRecognitionResult:
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            raise IndexError((row, col))
        return self.cells[row * self.grid_size + col]


@dataclass
class BoardImages:
    """仅供诊断输出的中间图；不进入可序列化结果契约。"""
    original: Any
    aligned: Any
    reference: Any
    rectified: Any
    rectified_reference: Any
    difference: Any
    ship_mask: Any
    occlusion_mask: Any
    reference_to_rectified: Any
    padding: int
