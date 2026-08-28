from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk
from typing import Callable

from sonar import SonarBoard, SonarStrategy

from .board_view import SonarBoardView


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


@dataclass(frozen=True)
class AppLayout:
    """主窗口后续需要更新的控件引用。"""

    auto_loop_start_button: ttk.Button
    auto_loop_stop_button: ttk.Button
    log_text: tk.Text
    board_view: SonarBoardView


def build_app_layout(
    master: tk.Misc,
    *,
    device_var: tk.StringVar,
    status_var: tk.StringVar,
    auto_loop_state_var: tk.StringVar,
    auto_loop_total_var: tk.StringVar,
    auto_loop_last_var: tk.StringVar,
    board: SonarBoard,
    strategy: SonarStrategy,
    actions: AppActions,
) -> AppLayout:
    """创建主窗口控件并返回需要动态操作的控件。"""
    container = ttk.Frame(
        master,
        padding=18,
    )

    container.pack(
        fill=tk.BOTH,
        expand=True,
    )

    ttk.Label(
        container,
        text="ADB 设备：",
    ).grid(
        row=0,
        column=0,
        sticky=tk.W,
    )

    ttk.Entry(
        container,
        textvariable=device_var,
        width=28,
    ).grid(
        row=0,
        column=1,
        sticky=tk.EW,
        padx=(8, 8),
    )

    ttk.Button(
        container,
        text="应用设备",
        command=actions.apply_device,
    ).grid(
        row=0,
        column=2,
    )

    basic_row = ttk.Frame(
        container
    )

    basic_row.grid(
        row=1,
        column=0,
        columnspan=3,
        sticky=tk.EW,
        pady=(16, 8),
    )

    ttk.Button(
        basic_row,
        text="检查设备",
        command=actions.check_device,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    ttk.Button(
        basic_row,
        text="获取截图",
        command=actions.take_screenshot,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    ttk.Button(
        basic_row,
        text="重启游戏",
        command=actions.restart_game,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    ttk.Button(
        basic_row,
        text="打开截图目录",
        command=actions.open_screenshot_dir,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    network_row = ttk.Frame(
        container
    )

    network_row.grid(
        row=2,
        column=0,
        columnspan=3,
        sticky=tk.EW,
        pady=(0, 14),
    )

    ttk.Button(
        network_row,
        text="检查 ROOT",
        command=actions.check_root,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    ttk.Button(
        network_row,
        text="开启弱网",
        command=actions.enable_weak_network,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    ttk.Button(
        network_row,
        text="关闭弱网",
        command=actions.disable_weak_network,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    ttk.Button(
        network_row,
        text="开启断网",
        command=actions.enable_reject_network,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    ttk.Button(
        network_row,
        text="关闭断网",
        command=actions.disable_reject_network,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    ttk.Button(
        network_row,
        text="恢复网络",
        command=actions.restore_network,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    ttk.Button(
        network_row,
        text="网络状态",
        command=actions.check_network_state,
    ).pack(
        side=tk.LEFT,
        padx=4,
    )

    auto_loop_section = ttk.LabelFrame(
        container,
        text="自动循环",
        padding=8,
    )
    auto_loop_section.grid(
        row=3,
        column=0,
        columnspan=3,
        sticky=tk.EW,
        pady=(0, 12),
    )

    auto_loop_start_button = ttk.Button(
        auto_loop_section,
        text="启动循环",
        command=actions.start_auto_loop,
    )
    auto_loop_start_button.pack(
        side=tk.LEFT,
        padx=(0, 6),
    )

    auto_loop_stop_button = ttk.Button(
        auto_loop_section,
        text="停止循环",
        command=actions.stop_auto_loop,
    )
    auto_loop_stop_button.pack(
        side=tk.LEFT,
        padx=(0, 12),
    )
    auto_loop_stop_button.state(["disabled"])

    ttk.Label(
        auto_loop_section,
        text="状态：",
    ).pack(
        side=tk.LEFT,
    )
    ttk.Label(
        auto_loop_section,
        textvariable=auto_loop_state_var,
    ).pack(
        side=tk.LEFT,
        padx=(4, 14),
    )
    ttk.Label(
        auto_loop_section,
        textvariable=auto_loop_total_var,
    ).pack(
        side=tk.LEFT,
        padx=(0, 14),
    )
    ttk.Label(
        auto_loop_section,
        textvariable=auto_loop_last_var,
    ).pack(
        side=tk.LEFT,
    )

    ttk.Label(
        container,
        text="状态：",
    ).grid(
        row=4,
        column=0,
        sticky=tk.NW,
    )

    ttk.Label(
        container,
        textvariable=status_var,
    ).grid(
        row=4,
        column=1,
        columnspan=2,
        sticky=tk.W,
    )

    log_text = tk.Text(
        container,
        height=10,
        wrap=tk.WORD,
    )

    log_text.grid(
        row=5,
        column=0,
        columnspan=3,
        sticky=tk.NSEW,
        pady=(12, 0),
    )

    board_section = ttk.LabelFrame(
        container,
        text="棋盘与策略同步",
        padding=10,
    )

    board_section.grid(
        row=6,
        column=0,
        columnspan=3,
        sticky=tk.NSEW,
        pady=(12, 0),
    )

    board_actions = ttk.Frame(
        board_section
    )

    board_actions.pack(
        fill=tk.X,
        pady=(0, 8),
    )

    ttk.Button(
        board_actions,
        text="重置棋盘状态",
        command=actions.reset_sonar_board,
    ).pack(
        side=tk.LEFT,
    )

    ttk.Label(
        board_actions,
        text=(
            "棋盘与当前选格策略同步；"
            "灰色同时表示实际未命中和策略排除格"
        ),
    ).pack(
        side=tk.LEFT,
        padx=(12, 0),
    )

    board_view = SonarBoardView(
        board_section,
        board=board,
        strategy=strategy,
    )

    board_view.pack(
        fill=tk.BOTH,
        expand=True,
    )

    container.columnconfigure(
        1,
        weight=1,
    )

    container.rowconfigure(
        5,
        weight=1,
    )

    container.rowconfigure(
        6,
        weight=2,
    )

    return AppLayout(
        auto_loop_start_button=auto_loop_start_button,
        auto_loop_stop_button=auto_loop_stop_button,
        log_text=log_text,
        board_view=board_view,
    )


__all__ = [
    "AppActions",
    "AppLayout",
    "build_app_layout",
]
