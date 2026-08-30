"""当前声纳功能的正式配置入口。

固定 10×10 关卡继续作为默认值。后续增加不同关卡时，可以新增
``SonarLevelConfig`` 实例，页面、网络和 GUI 流程无需跟随改写。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


Point = tuple[int, int]
Quad = tuple[Point, Point, Point, Point]


@dataclass(frozen=True)
class SonarLevelConfig:
    """单个声纳关卡及其选格策略参数。"""

    grid_size: int
    submarines: tuple[int, ...]
    board_quad: Quad | None
    hunt_parity: int = 0
    use_safety_rule: bool = True


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


DEFAULT_LEVEL_CONFIG = SonarLevelConfig(
    grid_size=10,
    submarines=(2, 2, 3, 4, 5),
    board_quad=(
        (662, 47),
        (1069, 291),
        (666, 625),
        (259, 288),
    ),
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
        )
    return DEFAULT_LEVEL_CONFIG

ACTIVITY_PAGE_CONFIG = ActivityPageConfig()
AUTO_PROBE_CONFIG = AutoProbeConfig()
GUI_CONFIG = GuiConfig()


__all__ = [
    "ACTIVITY_PAGE_CONFIG",
    "AUTO_PROBE_CONFIG",
    "DEFAULT_LEVEL_CONFIG",
    "GUI_CONFIG",
    "INITIAL_LEVEL",
    "ActivityPageConfig",
    "AutoProbeConfig",
    "GuiConfig",
    "SonarLevelConfig",
    "get_level_config",
]
