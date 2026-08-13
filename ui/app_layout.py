from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from typing import Callable

import ttkbootstrap as ttk

from sonar import SonarBoard, SonarStrategy

from .board_view import SonarBoardView
from .theme import (
    LOG_COLLAPSED_HEIGHT,
    PALETTE,
    SIDEBAR_SCROLL_STEP,
    SIDEBAR_WIDTH,
    SPACING,
    TYPOGRAPHY,
)


Action = Callable[[], None]


@dataclass(frozen=True)
class AppActions:
    """主窗口布局需要绑定的用户操作入口。"""

    apply_device: Action
    check_device: Action
    take_screenshot: Action
    restart_game: Action
    open_screenshot_dir: Action
    check_root: Action
    enable_weak_network: Action
    disable_weak_network: Action
    enable_reject_network: Action
    disable_reject_network: Action
    restore_network: Action
    check_network_state: Action
    start_auto_loop: Action
    stop_auto_loop: Action
    reset_sonar_board: Action
    toggle_log: Action


@dataclass(frozen=True)
class AppLayout:
    """主窗口后续需要更新的控件引用。"""

    auto_loop_start_button: ttk.Button
    auto_loop_stop_button: ttk.Button
    manual_control_buttons: tuple[ttk.Button, ...]
    status_labels: dict[str, ttk.Label]
    log_toggle_button: ttk.Button
    log_text: tk.Text
    board_view: SonarBoardView
    sidebar_scroller: ScrollableSidebar


class CollapsibleSection(ttk.Frame):
    """侧栏中的紧凑折叠区域。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        title: str,
    ) -> None:
        super().__init__(
            master,
            style="Card.TFrame",
        )
        self.title = title
        self.expanded = False

        self.toggle_button = ttk.Button(
            self,
            text=f"{title}  ▸",
            command=self.toggle,
            bootstyle="light",
        )
        self.toggle_button.pack(
            fill=tk.X,
        )

        self.content = ttk.Frame(
            self,
            style="Card.TFrame",
            padding=(SPACING.xs, SPACING.sm, SPACING.xs, SPACING.xs),
        )

    def toggle(self) -> None:
        self.expanded = not self.expanded

        if self.expanded:
            self.content.pack(fill=tk.X)
            marker = "▾"
        else:
            self.content.pack_forget()
            marker = "▸"

        self.toggle_button.configure(
            text=f"{self.title}  {marker}"
        )


class ScrollableSidebar(ttk.Frame):
    """带独立纵向滚动条和鼠标滚轮支持的右侧栏。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        width: int,
    ) -> None:
        super().__init__(
            master,
            style="App.TFrame",
            width=width,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        canvas_width = max(
            1,
            width - SPACING.xl,
        )
        self.canvas = tk.Canvas(
            self,
            width=canvas_width,
            highlightthickness=0,
            borderwidth=0,
            background=PALETTE.app_background,
            yscrollincrement=SPACING.md,
        )
        self.scrollbar = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL,
            command=self.canvas.yview,
        )
        self.canvas.configure(
            yscrollcommand=self.scrollbar.set,
        )

        self.canvas.grid(
            row=0,
            column=0,
            sticky=tk.NSEW,
        )
        self.scrollbar.grid(
            row=0,
            column=1,
            sticky=tk.NS,
            padx=(SPACING.xxs, 0),
        )

        self.content = ttk.Frame(
            self.canvas,
            style="App.TFrame",
        )
        self.content.columnconfigure(0, weight=1)
        self._content_window = self.canvas.create_window(
            0,
            0,
            window=self.content,
            anchor=tk.NW,
        )

        self.content.bind(
            "<Configure>",
            self._update_scroll_region,
        )
        self.canvas.bind(
            "<Configure>",
            self._fit_content_width,
        )

    def bind_mousewheel_tree(self) -> None:
        """让鼠标位于侧栏任意子控件时都能滚动。"""
        self._bind_mousewheel_widget(self)

    def _bind_mousewheel_widget(
        self,
        widget: tk.Misc,
    ) -> None:
        widget.bind(
            "<MouseWheel>",
            self._on_mousewheel,
            add="+",
        )
        widget.bind(
            "<Button-4>",
            self._on_mousewheel,
            add="+",
        )
        widget.bind(
            "<Button-5>",
            self._on_mousewheel,
            add="+",
        )

        for child in widget.winfo_children():
            self._bind_mousewheel_widget(child)

    def _update_scroll_region(
        self,
        _event: tk.Event,
    ) -> None:
        bounds = self.canvas.bbox("all")

        if bounds is not None:
            self.canvas.configure(
                scrollregion=bounds,
            )

    def _fit_content_width(
        self,
        event: tk.Event,
    ) -> None:
        self.canvas.itemconfigure(
            self._content_window,
            width=max(1, int(event.width)),
        )

    def _on_mousewheel(
        self,
        event: tk.Event,
    ) -> str:
        if self.canvas.yview() == (0.0, 1.0):
            return "break"

        button = getattr(event, "num", None)
        delta = int(getattr(event, "delta", 0))

        if button == 4 or delta > 0:
            direction = -SIDEBAR_SCROLL_STEP
        elif button == 5 or delta < 0:
            direction = SIDEBAR_SCROLL_STEP
        else:
            return "break"

        self.canvas.yview_scroll(
            direction,
            "units",
        )
        return "break"


def _status_item(
    master: tk.Misc,
    *,
    title: str,
    variable: tk.StringVar,
) -> ttk.Label:
    item = ttk.Frame(
        master,
        style="StatusBar.TFrame",
    )
    item.pack(
        side=tk.LEFT,
        fill=tk.X,
        expand=True,
        padx=(0, SPACING.md),
    )

    ttk.Label(
        item,
        text=title,
        style="StatusTitle.TLabel",
    ).pack(side=tk.LEFT)

    value_label = ttk.Label(
        item,
        textvariable=variable,
        style="neutral.Status.TLabel",
    )
    value_label.pack(
        side=tk.LEFT,
        padx=(SPACING.xs, 0),
    )
    return value_label


def _metric_card(
    master: tk.Misc,
    *,
    caption: str,
    variable: tk.StringVar,
    row: int,
    column: int,
    columnspan: int = 1,
) -> None:
    card = ttk.Frame(
        master,
        style="Card.TFrame",
        padding=(SPACING.sm, SPACING.xs),
    )
    card.grid(
        row=row,
        column=column,
        columnspan=columnspan,
        sticky=tk.NSEW,
        padx=SPACING.xxs,
        pady=SPACING.xxs,
    )
    ttk.Label(
        card,
        text=caption,
        style="MetricCaption.Card.TLabel",
    ).pack(anchor=tk.W)
    ttk.Label(
        card,
        textvariable=variable,
        style="Metric.Card.TLabel",
    ).pack(anchor=tk.W)


def _tool_button(
    master: tk.Misc,
    *,
    text: str,
    command: Action,
    row: int,
    column: int,
) -> ttk.Button:
    button = ttk.Button(
        master,
        text=text,
        command=command,
        bootstyle="light",
    )
    button.grid(
        row=row,
        column=column,
        sticky=tk.EW,
        padx=SPACING.xxs,
        pady=SPACING.xxs,
    )
    return button


def build_app_layout(
    master: tk.Misc,
    *,
    device_var: tk.StringVar,
    operation_var: tk.StringVar,
    device_status_var: tk.StringVar,
    page_status_var: tk.StringVar,
    network_status_var: tk.StringVar,
    auto_status_var: tk.StringVar,
    round_summary_var: tk.StringVar,
    phase_summary_var: tk.StringVar,
    target_summary_var: tk.StringVar,
    total_var: tk.StringVar,
    hit_var: tk.StringVar,
    miss_var: tk.StringVar,
    last_result_var: tk.StringVar,
    recovery_attempt_var: tk.StringVar,
    board: SonarBoard,
    strategy: SonarStrategy,
    actions: AppActions,
) -> AppLayout:
    """创建状态优先、棋盘主导的响应式主窗口。"""
    container = ttk.Frame(
        master,
        style="App.TFrame",
        padding=SPACING.md,
    )
    container.pack(
        fill=tk.BOTH,
        expand=True,
    )

    status_bar = ttk.Frame(
        container,
        style="StatusBar.TFrame",
        padding=(SPACING.md, SPACING.sm),
    )
    status_bar.grid(
        row=0,
        column=0,
        sticky=tk.EW,
    )

    status_labels = {
        "device": _status_item(
            status_bar,
            title="设备",
            variable=device_status_var,
        ),
        "page": _status_item(
            status_bar,
            title="页面",
            variable=page_status_var,
        ),
        "network": _status_item(
            status_bar,
            title="网络",
            variable=network_status_var,
        ),
        "auto": _status_item(
            status_bar,
            title="自动",
            variable=auto_status_var,
        ),
    }

    summary_bar = ttk.Frame(
        container,
        style="SummaryBar.TFrame",
        padding=(SPACING.md, SPACING.sm),
    )
    summary_bar.grid(
        row=1,
        column=0,
        sticky=tk.EW,
        pady=(SPACING.xs, SPACING.md),
    )

    for index, variable in enumerate(
        (
            round_summary_var,
            phase_summary_var,
            target_summary_var,
        )
    ):
        ttk.Label(
            summary_bar,
            textvariable=variable,
            style="Summary.TLabel",
        ).grid(
            row=0,
            column=index,
            sticky=tk.W,
            padx=(0, SPACING.xl),
        )
        summary_bar.columnconfigure(
            index,
            weight=1,
        )

    main_area = ttk.Frame(
        container,
        style="App.TFrame",
    )
    main_area.grid(
        row=2,
        column=0,
        sticky=tk.NSEW,
    )
    main_area.columnconfigure(0, weight=1)
    main_area.columnconfigure(1, weight=0, minsize=SIDEBAR_WIDTH)
    main_area.rowconfigure(0, weight=1)

    board_card = ttk.Frame(
        main_area,
        style="Card.TFrame",
        padding=SPACING.md,
    )
    board_card.grid(
        row=0,
        column=0,
        sticky=tk.NSEW,
        padx=(0, SPACING.md),
    )

    board_view = SonarBoardView(
        board_card,
        board=board,
        strategy=strategy,
    )
    board_view.pack(
        fill=tk.BOTH,
        expand=True,
    )

    sidebar = ScrollableSidebar(
        main_area,
        width=SIDEBAR_WIDTH,
    )
    sidebar.grid(
        row=0,
        column=1,
        sticky=tk.NSEW,
    )
    sidebar_content = sidebar.content

    control_card = ttk.Frame(
        sidebar_content,
        style="Card.TFrame",
        padding=SPACING.md,
    )
    control_card.grid(
        row=0,
        column=0,
        sticky=tk.EW,
    )
    ttk.Label(
        control_card,
        text="运行控制",
        style="Section.Card.TLabel",
    ).pack(anchor=tk.W, pady=(0, SPACING.sm))

    auto_loop_start_button = ttk.Button(
        control_card,
        text="启动自动探测",
        command=actions.start_auto_loop,
        bootstyle="primary",
        padding=(SPACING.md, SPACING.sm),
    )
    auto_loop_start_button.pack(fill=tk.X)

    auto_loop_stop_button = ttk.Button(
        control_card,
        text="停止自动探测",
        command=actions.stop_auto_loop,
        bootstyle="warning-outline",
        padding=(SPACING.md, SPACING.sm),
    )
    auto_loop_stop_button.pack(
        fill=tk.X,
        pady=(SPACING.xs, 0),
    )
    auto_loop_stop_button.state(["disabled"])

    ttk.Label(
        control_card,
        textvariable=operation_var,
        style="Muted.Card.TLabel",
        wraplength=SIDEBAR_WIDTH - SPACING.xl * 2,
    ).pack(
        fill=tk.X,
        pady=(SPACING.sm, 0),
    )

    stats_card = ttk.Frame(
        sidebar_content,
        style="Card.TFrame",
        padding=SPACING.sm,
    )
    stats_card.grid(
        row=1,
        column=0,
        sticky=tk.EW,
        pady=(SPACING.sm, 0),
    )
    ttk.Label(
        stats_card,
        text="本轮统计",
        style="Section.Card.TLabel",
    ).grid(
        row=0,
        column=0,
        columnspan=2,
        sticky=tk.W,
        padx=SPACING.xxs,
        pady=(0, SPACING.xs),
    )
    _metric_card(stats_card, caption="总发数", variable=total_var, row=1, column=0)
    _metric_card(stats_card, caption="HIT", variable=hit_var, row=1, column=1)
    _metric_card(stats_card, caption="MISS", variable=miss_var, row=2, column=0)
    _metric_card(
        stats_card,
        caption="异常恢复",
        variable=recovery_attempt_var,
        row=2,
        column=1,
    )
    last_card = ttk.Frame(
        stats_card,
        style="Card.TFrame",
        padding=(SPACING.sm, SPACING.xs),
    )
    last_card.grid(
        row=3,
        column=0,
        columnspan=2,
        sticky=tk.EW,
        padx=SPACING.xxs,
        pady=SPACING.xxs,
    )
    ttk.Label(
        last_card,
        text="上一发结果",
        style="MetricCaption.Card.TLabel",
    ).pack(anchor=tk.W)
    ttk.Label(
        last_card,
        textvariable=last_result_var,
        style="Card.TLabel",
        font=TYPOGRAPHY.body_bold,
    ).pack(anchor=tk.W)
    stats_card.columnconfigure(0, weight=1)
    stats_card.columnconfigure(1, weight=1)

    manual_section = CollapsibleSection(
        sidebar_content,
        title="人工工具",
    )
    manual_section.grid(
        row=2,
        column=0,
        sticky=tk.EW,
        pady=(SPACING.sm, 0),
    )

    device_row = ttk.Frame(
        manual_section.content,
        style="Card.TFrame",
    )
    device_row.grid(
        row=0,
        column=0,
        columnspan=2,
        sticky=tk.EW,
        pady=(0, SPACING.xs),
    )
    device_row.columnconfigure(0, weight=1)
    ttk.Entry(
        device_row,
        textvariable=device_var,
    ).grid(
        row=0,
        column=0,
        sticky=tk.EW,
        padx=(0, SPACING.xs),
    )
    apply_device_button = ttk.Button(
        device_row,
        text="应用设备",
        command=actions.apply_device,
        bootstyle="secondary-outline",
    )
    apply_device_button.grid(row=0, column=1)

    manual_specs = (
        ("检查设备", actions.check_device),
        ("获取截图", actions.take_screenshot),
        ("重启游戏", actions.restart_game),
        ("打开截图目录", actions.open_screenshot_dir),
        ("检查 ROOT", actions.check_root),
        ("重置棋盘", actions.reset_sonar_board),
    )
    manual_buttons: list[ttk.Button] = []

    for index, (text, command) in enumerate(manual_specs):
        button = _tool_button(
            manual_section.content,
            text=text,
            command=command,
            row=index // 2 + 1,
            column=index % 2,
        )
        manual_buttons.append(button)

    manual_section.content.columnconfigure(0, weight=1)
    manual_section.content.columnconfigure(1, weight=1)

    network_section = CollapsibleSection(
        sidebar_content,
        title="网络工具",
    )
    network_section.grid(
        row=3,
        column=0,
        sticky=tk.EW,
        pady=(SPACING.sm, 0),
    )
    network_specs = (
        ("开启弱网 DROP", actions.enable_weak_network),
        ("关闭弱网 DROP", actions.disable_weak_network),
        ("开启断网 REJECT", actions.enable_reject_network),
        ("关闭断网 REJECT", actions.disable_reject_network),
        ("恢复正常联网", actions.restore_network),
        ("检查网络状态", actions.check_network_state),
    )
    network_buttons: list[ttk.Button] = []

    for index, (text, command) in enumerate(network_specs):
        button = _tool_button(
            network_section.content,
            text=text,
            command=command,
            row=index // 2,
            column=index % 2,
        )
        network_buttons.append(button)

    network_section.content.columnconfigure(0, weight=1)
    network_section.content.columnconfigure(1, weight=1)
    sidebar.bind_mousewheel_tree()

    log_card = ttk.Frame(
        container,
        style="Card.TFrame",
        padding=(SPACING.md, SPACING.sm),
    )
    log_card.grid(
        row=3,
        column=0,
        sticky=tk.EW,
        pady=(SPACING.md, 0),
    )
    log_header = ttk.Frame(
        log_card,
        style="Card.TFrame",
    )
    log_header.pack(fill=tk.X)
    ttk.Label(
        log_header,
        text="运行日志",
        style="Section.Card.TLabel",
    ).pack(side=tk.LEFT)
    log_toggle_button = ttk.Button(
        log_header,
        text="展开",
        command=actions.toggle_log,
        bootstyle="link",
    )
    log_toggle_button.pack(side=tk.RIGHT)

    log_text = tk.Text(
        log_card,
        height=LOG_COLLAPSED_HEIGHT,
        wrap=tk.WORD,
        relief=tk.FLAT,
        borderwidth=0,
        background=PALETTE.surface_muted,
        foreground=PALETTE.text,
        insertbackground=PALETTE.text,
        selectbackground=PALETTE.primary,
        font=TYPOGRAPHY.small,
        padx=SPACING.sm,
        pady=SPACING.sm,
    )
    log_text.pack(
        fill=tk.X,
        pady=(SPACING.xs, 0),
    )

    container.columnconfigure(0, weight=1)
    container.rowconfigure(2, weight=1)

    manual_control_buttons = (
        apply_device_button,
        *(
            button
            for index, button in enumerate(manual_buttons)
            if index != 3
        ),
        *network_buttons,
    )

    return AppLayout(
        auto_loop_start_button=auto_loop_start_button,
        auto_loop_stop_button=auto_loop_stop_button,
        manual_control_buttons=tuple(manual_control_buttons),
        status_labels=status_labels,
        log_toggle_button=log_toggle_button,
        log_text=log_text,
        board_view=board_view,
        sidebar_scroller=sidebar,
    )


__all__ = [
    "AppActions",
    "AppLayout",
    "build_app_layout",
]
