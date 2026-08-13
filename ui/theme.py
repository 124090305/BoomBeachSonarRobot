from __future__ import annotations

from dataclasses import dataclass

import ttkbootstrap as ttk


APP_THEME = "flatly"
APP_TITLE = "BoomBeach Sonar Robot"
APP_GEOMETRY = "1770x1170"   # 默认启动宽度 × 高度
APP_MIN_SIZE = (1180, 780)  # 用户缩放窗口时允许的最小尺寸


@dataclass(frozen=True)
class UiSpacing:
    xxs: int = 4
    xs: int = 6
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 20


@dataclass(frozen=True)
class UiPalette:
    app_background: str = "#f4f7fb"
    surface: str = "#ffffff"
    surface_muted: str = "#f8fafc"
    border: str = "#dce3ec"
    border_strong: str = "#b8c4d2"
    text: str = "#1f2937"
    text_muted: str = "#667085"
    primary: str = "#2f74d0"
    success: str = "#238b62"
    warning: str = "#d97706"
    danger: str = "#cf3d4f"
    neutral: str = "#8a94a3"
    board_unknown: str = "#f1f5f9"
    board_miss: str = "#d9e0e8"
    board_hit: str = "#f4c95d"
    board_grid: str = "#c4ced9"
    board_selected: str = "#2478d4"
    board_sunk: str = "#ed7d24"


@dataclass(frozen=True)
class UiTypography:
    family: str = "Microsoft YaHei UI"
    body_size: int = 10
    small_size: int = 9
    section_size: int = 11
    title_size: int = 16
    metric_size: int = 20

    @property
    def body(self) -> tuple[str, int]:
        return self.family, self.body_size

    @property
    def body_bold(self) -> tuple[str, int, str]:
        return self.family, self.body_size, "bold"

    @property
    def small(self) -> tuple[str, int]:
        return self.family, self.small_size

    @property
    def section(self) -> tuple[str, int, str]:
        return self.family, self.section_size, "bold"

    @property
    def title(self) -> tuple[str, int, str]:
        return self.family, self.title_size, "bold"

    @property
    def metric(self) -> tuple[str, int, str]:
        return self.family, self.metric_size, "bold"


SPACING = UiSpacing()
PALETTE = UiPalette()
TYPOGRAPHY = UiTypography()

BOARD_CELL_SCALE = 0.92
BOARD_SELECTED_WIDTH = 3
BOARD_SUNK_WIDTH = 4
LOG_COLLAPSED_HEIGHT = 4
LOG_EXPANDED_HEIGHT = 12
SIDEBAR_WIDTH = 400       # 右侧栏宽度
SIDEBAR_SCROLL_STEP = 4   # 每次滚轮滚动距离

STATUS_TONE_COLORS = {
    "success": PALETTE.success,
    "info": PALETTE.primary,
    "warning": PALETTE.warning,
    "danger": PALETTE.danger,
    "neutral": PALETTE.neutral,
}


def configure_styles(style: ttk.Style) -> None:
    """集中配置主窗口使用的字体、面板和状态样式。"""
    style.configure(
        ".",
        font=TYPOGRAPHY.body,
    )
    style.configure(
        "App.TFrame",
        background=PALETTE.app_background,
    )
    style.configure(
        "Card.TFrame",
        background=PALETTE.surface,
        relief="flat",
    )
    style.configure(
        "StatusBar.TFrame",
        background=PALETTE.surface,
    )
    style.configure(
        "SummaryBar.TFrame",
        background=PALETTE.surface_muted,
    )
    style.configure(
        "Card.TLabel",
        background=PALETTE.surface,
        foreground=PALETTE.text,
    )
    style.configure(
        "Muted.Card.TLabel",
        background=PALETTE.surface,
        foreground=PALETTE.text_muted,
        font=TYPOGRAPHY.small,
    )
    style.configure(
        "StatusTitle.TLabel",
        background=PALETTE.surface,
        foreground=PALETTE.text_muted,
        font=TYPOGRAPHY.small,
    )
    style.configure(
        "Summary.TLabel",
        background=PALETTE.surface_muted,
        foreground=PALETTE.text,
        font=TYPOGRAPHY.body_bold,
    )
    style.configure(
        "Section.Card.TLabel",
        background=PALETTE.surface,
        foreground=PALETTE.text,
        font=TYPOGRAPHY.section,
    )
    style.configure(
        "Metric.Card.TLabel",
        background=PALETTE.surface,
        foreground=PALETTE.text,
        font=TYPOGRAPHY.metric,
    )
    style.configure(
        "MetricCaption.Card.TLabel",
        background=PALETTE.surface,
        foreground=PALETTE.text_muted,
        font=TYPOGRAPHY.small,
    )
    style.configure(
        "BoardTitle.Card.TLabel",
        background=PALETTE.surface,
        foreground=PALETTE.text,
        font=TYPOGRAPHY.title,
    )
    style.configure(
        "Tool.TButton",
        font=TYPOGRAPHY.body,
        anchor="w",
    )

    for tone, color in STATUS_TONE_COLORS.items():
        style.configure(
            f"{tone}.Status.TLabel",
            background=PALETTE.surface,
            foreground=color,
            font=TYPOGRAPHY.body_bold,
        )


__all__ = [
    "APP_GEOMETRY",
    "APP_MIN_SIZE",
    "APP_THEME",
    "APP_TITLE",
    "BOARD_CELL_SCALE",
    "BOARD_SELECTED_WIDTH",
    "BOARD_SUNK_WIDTH",
    "LOG_COLLAPSED_HEIGHT",
    "LOG_EXPANDED_HEIGHT",
    "PALETTE",
    "SIDEBAR_SCROLL_STEP",
    "SIDEBAR_WIDTH",
    "SPACING",
    "STATUS_TONE_COLORS",
    "TYPOGRAPHY",
    "configure_styles",
]
