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
    toggle_weak_network: Action
    toggle_reject_network: Action
    restore_network: Action
    check_network_state: Action
    toggle_auto_loop: Action
    toggle_manual_intervention: Action
    undo_manual_edit: Action
    redo_manual_edit: Action
    discard_manual_changes: Action
    apply_manual_changes: Action
    reset_sonar_board: Action


@dataclass(frozen=True)
class AppLayout:
    """主窗口后续需要更新的控件引用。"""

    apply_device_button: ttk.Button
    restart_game_button: tk.Button
    weak_network_button: tk.Button
    reject_network_button: tk.Button
    auto_loop_button: tk.Button
    manual_intervention_button: tk.Button
    reset_board_button: ttk.Button
    manual_edit_toolbar: ttk.Frame
    manual_undo_button: ttk.Button
    manual_redo_button: ttk.Button
    manual_apply_button: ttk.Button
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

    apply_device_button = ttk.Button(
        container,
        text="应用设备",
        command=actions.apply_device,
    )
    apply_device_button.grid(
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

    restart_game_button = tk.Button(
        basic_row,
        text="重启游戏",
        command=actions.restart_game,
    )
    restart_game_button.pack(
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

    weak_network_button = tk.Button(
        network_row,
        text="开启弱网",
        command=actions.toggle_weak_network,
    )
    weak_network_button.pack(
        side=tk.LEFT,
        padx=4,
    )

    reject_network_button = tk.Button(
        network_row,
        text="开启断网",
        command=actions.toggle_reject_network,
    )
    reject_network_button.pack(
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

    auto_loop_button = tk.Button(
        auto_loop_section,
        text="启动循环",
        command=actions.toggle_auto_loop,
    )
    auto_loop_button.pack(
        side=tk.LEFT,
        padx=(0, 6),
    )

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

    reset_board_button = ttk.Button(
        board_actions,
        text="重置棋盘状态",
        command=actions.reset_sonar_board,
    )
    reset_board_button.pack(
        side=tk.LEFT,
    )

    manual_intervention_button = tk.Button(
        board_actions,
        text="开启人工干预",
        command=actions.toggle_manual_intervention,
    )
    manual_intervention_button.pack(
        side=tk.LEFT,
        padx=(8, 0),
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

    manual_edit_toolbar = ttk.Frame(board_section)
    manual_undo_button = ttk.Button(
        manual_edit_toolbar,
        text="撤回",
        command=actions.undo_manual_edit,
    )
    manual_undo_button.pack(side=tk.LEFT, padx=(0, 6))
    manual_redo_button = ttk.Button(
        manual_edit_toolbar,
        text="重做",
        command=actions.redo_manual_edit,
    )
    manual_redo_button.pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(
        manual_edit_toolbar,
        text="取消修改",
        command=actions.discard_manual_changes,
    ).pack(side=tk.LEFT, padx=(0, 6))
    manual_apply_button = ttk.Button(
        manual_edit_toolbar,
        text="应用修改",
        command=actions.apply_manual_changes,
    )
    manual_apply_button.pack(side=tk.LEFT)

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
        apply_device_button=apply_device_button,
        restart_game_button=restart_game_button,
        weak_network_button=weak_network_button,
        reject_network_button=reject_network_button,
        auto_loop_button=auto_loop_button,
        manual_intervention_button=manual_intervention_button,
        reset_board_button=reset_board_button,
        manual_edit_toolbar=manual_edit_toolbar,
        manual_undo_button=manual_undo_button,
        manual_redo_button=manual_redo_button,
        manual_apply_button=manual_apply_button,
        log_text=log_text,
        board_view=board_view,
    )


__all__ = [
    "AppActions",
    "AppLayout",
    "build_app_layout",
]
