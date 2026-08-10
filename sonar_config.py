"""当前声纳功能的正式配置入口。

固定 10×10 关卡继续作为默认值。后续增加不同关卡时，可以新增
``SonarLevelConfig`` 实例，页面、网络和 GUI 流程无需跟随改写。
"""

from __future__ import annotations

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


@dataclass(frozen=True)
class AutoProbeConfig:
    """自动单发识别、恢复和调试输出参数。"""

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

ACTIVITY_PAGE_CONFIG = ActivityPageConfig()
AUTO_PROBE_CONFIG = AutoProbeConfig()
GUI_CONFIG = GuiConfig()


__all__ = [
    "ACTIVITY_PAGE_CONFIG",
    "AUTO_PROBE_CONFIG",
    "DEFAULT_LEVEL_CONFIG",
    "GUI_CONFIG",
    "ActivityPageConfig",
    "AutoProbeConfig",
    "GuiConfig",
    "SonarLevelConfig",
]
