"""当前声纳功能的正式配置入口。

固定 10×10 关卡继续作为默认值。后续增加不同关卡时，可以新增
``SonarLevelConfig`` 实例，页面、网络和 GUI 流程无需跟随改写。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


Point = tuple[int, int]
Quad = tuple[Point, Point, Point, Point]
BOARD_REFERENCE_DIR = Path(__file__).resolve().parent / "resources" / "board_references"


@dataclass(frozen=True)
class SonarLevelConfig:
    """单个声纳关卡及其选格策略参数。"""

    grid_size: int
    submarines: tuple[int, ...]
    board_quad: Quad | None
    hunt_parity: int = 0
    use_safety_rule: bool = True
    empty_reference_path: Path | None = None


@dataclass(frozen=True)
class ActivityPageConfig:
    """声纳活动页面模板、坐标和等待时间。"""

    activity_button_template: str = "activity_button.png"
    sonar_template: str = "sonar_join.png"
    sonar_label_template: str = "sonar_join_label.png"
    sonar_match_threshold: float = 0.60

    home_ready_timeout: float = 45.0
    sonar_wait_timeout: float = 60.0
    home_swipe_start: tuple[int, int] = (640, 500)
    home_swipe_end: tuple[int, int] = (640, 200)
    home_swipe_duration_ms: int = 800

    activity_list_swipe_start: tuple[int, int] = (1000, 660)
    activity_list_swipe_end: tuple[int, int] = (1000, 180)
    activity_list_swipe_duration_ms: int = 300
    activity_list_swipe_count: int = 2
    activity_list_before_swipe_delay: float = 0.4
    activity_list_swipe_interval: float = 0.2
    initial_weak_apply_delay: float = 0.2

    quit_activity_template: str = "quit_activity.png"
    activity_detail_entry_point: tuple[int, int] = (1205, 644)
    activity_tap_to_start_point: tuple[int, int] = (300, 140)

    activity_button_timeout: float = 20.0
    activity_detail_ready_timeout: float = 15.0
    probe_detail_ready_timeout: float = 6.0

    activity_button_click_delay: float = 0.4
    activity_detail_entry_delay: float = 0.7
    activity_tap_to_start_delay: float = 0.4
    activity_tap_to_start_after_delay: float = 0.5
    probe_after_click_delay: float = 0.3

    victory_template: str = "victory.png"
    victory_wait_timeout: float = 12.0
    victory_followup_timeout: float = 0.5
    victory_max_rounds: int = 3
    victory_click_delay: float = 0.3
    victory_after_click_delay: float = 1.0
    next_level_ready_timeout: float = 15.0


@dataclass(frozen=True)
class AutoProbeConfig:
    """自动单发识别、恢复和调试输出参数。"""

    max_restart_attempts: int = 3

    retry_template: str = "retry.png"
    retry_wait_timeout: float = 20.0
    retry_match_threshold: float = 0.85
    retry_before_click_delay: float = 0.1
    retry_after_click_delay: float = 0.5
    hit_online_wait_seconds: float = 5.0

    retry_failure_dir_name: str = "retry_failure"
    auto_probe_dir_name: str = "auto_probe"

    diamond_w: int = 80
    diamond_h: int = 56
    diamond_search_radius: int = 14
    diamond_debug_dir_name: str = "diamond_hit_debug"


@dataclass(frozen=True)
class GuiConfig:
    """声纳棋盘 GUI 的显示参数。"""

    board_view_width: int = 620
    board_view_height: int = 300
    board_view_padding: int = 20
    board_show_coords: bool = True
    board_refresh_ms: int = 120


@dataclass(frozen=True)
class GlobalBoardSyncConfig:
    """实机多帧全局识别及自动校准的安全门槛。"""

    frame_count: int = 3
    maximum_frame_count: int = 5  # 有分歧/质量不足时追加；增大提高复核开销
    frame_interval_seconds: float = 0.18
    minimum_usable_frames: int = 2
    cell_agreement_threshold: float = 2 / 3
    minimum_mean_agreement: float = 0.97
    maximum_disagreement_cells: int = 3
    auto_minimum_known_confidence: float = 0.66
    auto_minimum_unknown_review_confidence: float = 0.58
    output_dir_name: str = "global_board_sync"
    save_debug: bool = True
    feasibility_node_limit: int = 20000  # 自动校准布局审核搜索上限；超限要求人工处理

    def __post_init__(self) -> None:
        if self.frame_count <= 0 or self.minimum_usable_frames <= 0:
            raise ValueError("实时识别帧数必须大于 0")
        if self.minimum_usable_frames > self.frame_count:
            raise ValueError("最少可用帧数不能超过总帧数")
        if self.maximum_frame_count < self.frame_count or self.feasibility_node_limit <= 0:
            raise ValueError("最大帧数不能小于初始帧数，布局审核上限必须为正")
        if self.maximum_disagreement_cells < 0 or self.cell_agreement_threshold <= 0.5:
            raise ValueError("分歧格上限不得为负，船段支持比例必须超过一半")
        if self.frame_interval_seconds < 0:
            raise ValueError("实时识别帧间隔不能小于 0")
        for value in (
            self.cell_agreement_threshold,
            self.minimum_mean_agreement,
            self.auto_minimum_known_confidence,
            self.auto_minimum_unknown_review_confidence,
        ):
            if not 0 <= value <= 1:
                raise ValueError("实时识别比例和置信度必须位于 0~1")


DEFAULT_LEVEL_CONFIG = SonarLevelConfig(
    grid_size=10,
    submarines=(2, 2, 3, 4, 5),
    board_quad=(
        (662, 47),
        (1069, 291),
        (666, 625),
        (259, 288),
    ),
    empty_reference_path=BOARD_REFERENCE_DIR / "level_11_empty.png",
)

INITIAL_LEVEL = int(os.getenv("SONAR_INITIAL_LEVEL", "10"))

_EARLY_LEVEL_SUBMARINES = {
    1: (3,),
    2: (2, 2),
    3: (2, 2, 3),
    4: (2, 3, 4),
    5: (2, 3, 3, 4),
    6: (2, 2, 3, 3, 5),
    7: (2, 2, 3, 3, 4, 5),
    8: (2, 2, 3, 3, 4, 4, 5),
    9: (2, 3, 3, 4, 4, 5),
    10: (2, 2, 3, 4, 4, 5),
    11: (2, 2, 3, 4, 5),
}

_EARLY_LEVEL_QUADS = {
    1: ((666, 247), (786, 329), (662, 420), (543, 327)),
    2: ((661, 247), (831, 357), (669, 488), (499, 362)),
    3: ((662, 225), (874, 363), (669, 532), (455, 367)),
    4: ((667, 192), (916, 362), (665, 562), (413, 359)),
    5: ((660, 165), (958, 353), (670, 593), (372, 356)),
    6: ((664, 125), (998, 336), (670, 609), (333, 338)),
    7: ((661, 89), (1034, 321), (666, 625), (294, 317)),
    8: ((664, 48), (1071, 288), (671, 625), (259, 290)),
    9: ((664, 48), (1069, 288), (671, 625), (259, 290)),
    10: ((664, 48), (1069, 288), (671, 625), (259, 290)),
    11: DEFAULT_LEVEL_CONFIG.board_quad,
}


def get_level_config(level: int) -> SonarLevelConfig:
    """返回关卡配置；11 关以后沿用当前 10x10 活动配置。"""
    actual_level = int(level)
    if actual_level <= 0:
        raise ValueError("关卡编号必须大于 0")
    if actual_level <= 11:
        return SonarLevelConfig(
            grid_size=min(actual_level + 2, 10),
            submarines=_EARLY_LEVEL_SUBMARINES[actual_level],
            board_quad=_EARLY_LEVEL_QUADS[actual_level],
            empty_reference_path=BOARD_REFERENCE_DIR / f"level_{actual_level:02d}_empty.png",
        )
    return DEFAULT_LEVEL_CONFIG

ACTIVITY_PAGE_CONFIG = ActivityPageConfig()
AUTO_PROBE_CONFIG = AutoProbeConfig()
GUI_CONFIG = GuiConfig()
GLOBAL_BOARD_SYNC_CONFIG = GlobalBoardSyncConfig()


__all__ = [
    "ACTIVITY_PAGE_CONFIG",
    "AUTO_PROBE_CONFIG",
    "DEFAULT_LEVEL_CONFIG",
    "GUI_CONFIG",
    "GLOBAL_BOARD_SYNC_CONFIG",
    "INITIAL_LEVEL",
    "ActivityPageConfig",
    "AutoProbeConfig",
    "GuiConfig",
    "GlobalBoardSyncConfig",
    "SonarLevelConfig",
    "get_level_config",
]
