from __future__ import annotations

import logging
import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Callable

import config

from flows import run_screenshot_check
from logger import (
    GuiLogFormatter,
    attach_log_handler,
    detach_log_handler,
    get_logger,
)

from .app_layout import (
    AppActions,
    build_app_layout,
)
from .auto_loop_bridge import AutoProbeLoopBridge
from .button_state import (
    ButtonLabels,
    ButtonState,
    StatefulButton,
)
from .runtime_context import AppRuntimeContext
from sonar import ManualEditError, ManualEditSession, apply_manual_edits


logger = get_logger(__name__)


class QueueLogHandler(logging.Handler):
    """把日志放进队列，由 Tkinter 主线程读取。"""

    def __init__(
        self,
        log_queue: queue.Queue[str],
    ) -> None:
        super().__init__()
        self.log_queue = log_queue
        self.setFormatter(
            GuiLogFormatter()
        )

    def emit(
        self,
        record: logging.LogRecord,
    ) -> None:
        try:
            self.log_queue.put(
                self.format(record)
            )
        except Exception:
            self.handleError(record)


class BoomBeachSonarApp(tk.Tk):
    """声纳控制主窗口。"""

    def __init__(self) -> None:
        super().__init__()

        self.title(
            "BoomBeach Sonar Robot"
        )
        self.geometry(
            "980x780"
        )
        self.minsize(
            900,
            700,
        )

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._log_handler = QueueLogHandler(
            self._log_queue
        )
        attach_log_handler(
            self._log_handler
        )

        self._runtime = AppRuntimeContext.create()
        self._bind_runtime(
            self._runtime
        )

        self.status_var = tk.StringVar(
            value="等待操作"
        )
        self.device_var = tk.StringVar(
            value=config.ADB_SERIAL
        )
        self.auto_loop_state_var = tk.StringVar(
            value="已停止"
        )
        self.auto_loop_total_var = tk.StringVar(
            value="发数：0 | HIT：0 | MISS：0"
        )
        self.auto_loop_last_var = tk.StringVar(
            value="上一发：-"
        )

        self._auto_loop_bridge = AutoProbeLoopBridge(
            self._runtime
        )
        self._manual_session: ManualEditSession | None = None
        self._pending_auto_loop_terminal: tuple[str, object] | None = None
        self._ui_callbacks: queue.Queue[Callable[[], None]] = queue.Queue()
        self._close_results: queue.Queue[str] = queue.Queue()
        self._startup_after_id: str | None = None
        self._ui_callback_after_id: str | None = None
        self._log_after_id: str | None = None
        self._auto_loop_after_id: str | None = None
        self._close_poll_after_id: str | None = None
        self._closing = False

        self._build_ui()
        self._startup_after_id = self.after(
            0,
            self._refresh_network_buttons_async,
        )

        self._ui_callback_after_id = self.after(
            50,
            self._drain_ui_callbacks,
        )
        self._log_after_id = self.after(
            100,
            self._drain_logs,
        )
        self._auto_loop_after_id = self.after(
            100,
            self._drain_auto_loop_events,
        )
        self.protocol(
            "WM_DELETE_WINDOW",
            self.on_close,
        )

        logger.info(
            "GUI 已启动"
        )

    def _bind_runtime(
        self,
        context: AppRuntimeContext,
    ) -> None:
        """保留主窗口既有属性，同时统一从运行上下文取对象。"""
        self.adb = context.adb
        self.network = context.network
        self.page = context.page
        self.game = context.game
        self.sonar_board = context.board
        self.sonar_strategy = context.strategy

    def _build_ui(self) -> None:
        actions = AppActions(
            apply_device=self.apply_device,
            check_device=self.check_device,
            take_screenshot=self.take_screenshot,
            restart_game=self.restart_game,
            open_screenshot_dir=self.open_screenshot_dir,
            check_root=self.check_root,
            toggle_weak_network=self.toggle_weak_network,
            toggle_reject_network=self.toggle_reject_network,
            restore_network=self.restore_network,
            check_network_state=self.check_network_state,
            toggle_auto_loop=self.toggle_auto_loop,
            toggle_manual_intervention=self.toggle_manual_intervention,
            undo_manual_edit=self.undo_manual_edit,
            redo_manual_edit=self.redo_manual_edit,
            discard_manual_changes=self.discard_manual_changes,
            apply_manual_changes=self.apply_manual_changes,
            reset_sonar_board=self.reset_sonar_board,
        )

        layout = build_app_layout(
            self,
            device_var=self.device_var,
            status_var=self.status_var,
            auto_loop_state_var=self.auto_loop_state_var,
            auto_loop_total_var=self.auto_loop_total_var,
            auto_loop_last_var=self.auto_loop_last_var,
            board=self.sonar_board,
            strategy=self.sonar_strategy,
            actions=actions,
        )

        self._restart_button = StatefulButton(
            layout.restart_game_button,
            ButtonLabels(
                ready="重启游戏",
                active="重启游戏",
                busy_on="正在重启…",
                busy_off="正在重启…",
                locked="自动流程不可中断",
                error="重启失败，点击重试",
            ),
            is_toggle=False,
        )
        self._weak_network_button = StatefulButton(
            layout.weak_network_button,
            ButtonLabels(
                ready="开启弱网",
                active="关闭弱网",
                busy_on="正在开启弱网…",
                busy_off="正在关闭弱网…",
                locked="自动流程中",
                error="弱网状态未知",
            ),
            is_toggle=True,
        )
        self._reject_network_button = StatefulButton(
            layout.reject_network_button,
            ButtonLabels(
                ready="开启断网",
                active="关闭断网",
                busy_on="正在开启断网…",
                busy_off="正在关闭断网…",
                locked="自动流程中",
                error="断网状态未知",
            ),
            is_toggle=True,
        )
        self._auto_loop_button = StatefulButton(
            layout.auto_loop_button,
            ButtonLabels(
                ready="启动循环",
                active="停止循环",
                busy_on="正在启动…",
                busy_off="正在停止…",
                locked="自动流程不可中断",
                error="循环异常，点击重试",
            ),
            is_toggle=True,
        )
        self._manual_intervention_button = StatefulButton(
            layout.manual_intervention_button,
            ButtonLabels(
                ready="开启人工干预",
                active="退出人工干预",
                busy_on="正在开启人工干预…",
                busy_off="正在退出人工干预…",
                locked="自动循环中",
                error="人工干预不可用",
            ),
            is_toggle=True,
        )
        self._apply_device_button = layout.apply_device_button
        self._reset_board_button = layout.reset_board_button
        self._manual_edit_toolbar = layout.manual_edit_toolbar
        self._manual_undo_button = layout.manual_undo_button
        self._manual_redo_button = layout.manual_redo_button
        self._manual_apply_button = layout.manual_apply_button
        self.log_text = layout.log_text
        self.board_view = layout.board_view

    # =========================================================
    # 控制器切换
    # =========================================================

    def apply_device(self) -> None:
        """切换 ADB 设备，保留当前棋盘和策略状态。"""
        if self._manual_session is not None:
            messagebox.showwarning(
                "人工干预中",
                "请先退出人工干预，再切换 ADB 设备。",
            )
            return
        if self._auto_loop_running():
            messagebox.showwarning(
                "自动循环运行中",
                "请先停止自动循环，再切换 ADB 设备。",
            )
            return

        serial = self.device_var.get().strip()

        if not serial:
            messagebox.showwarning(
                "设备编号为空",
                "请输入 ADB 设备编号",
            )
            return

        try:
            context = self._runtime.with_device(
                serial
            )
            self._auto_loop_bridge.set_context(
                context
            )
            self._runtime = context
            self._bind_runtime(
                context
            )
            self._refresh_network_buttons_async()
            self._write_log(
                f"已切换设备：{serial}"
            )
        except Exception as exc:
            self._show_error(
                exc
            )

    # =========================================================
    # 基础功能
    # =========================================================

    def check_device(self) -> None:
        def task() -> str:
            self.adb.ensure_device_online()
            devices = self.adb.list_devices()
            return (
                f"设备正常：{self.adb.serial}\n"
                f"在线设备：{devices}"
            )

        self._run_task(
            "正在检查设备...",
            task,
        )

    def take_screenshot(self) -> None:
        def task() -> str:
            result = run_screenshot_check(
                self.adb
            )
            return (
                f"截图完成：{result.path}\n"
                f"尺寸：{result.width}x{result.height}"
            )

        self._run_task(
            "正在获取截图...",
            task,
        )

    def restart_game(self) -> None:
        if not self._manual_control_available():
            return

        if self._restart_button.begin() is None:
            return

        def task() -> str:
            self.game.restart_game()
            return "网络已恢复，游戏已重启"

        self._run_action_button_task(
            self._restart_button,
            "正在恢复网络并重启游戏...",
            task,
        )

    # =========================================================
    # 网络功能
    # =========================================================

    def check_root(self) -> None:
        if not self._manual_control_available():
            return

        def task() -> str:
            return self.network.get_root_info()

        self._run_task(
            "正在检查 ROOT...",
            task,
        )

    def toggle_weak_network(self) -> None:
        if not self._manual_control_available():
            return

        target = self._weak_network_button.begin()
        if target is None:
            return

        self._run_network_toggle(
            button=self._weak_network_button,
            target=target,
            apply=(
                self.network.enable_weak_network
                if target
                else self.network.disable_weak_network
            ),
            enabled=lambda state: state.weak_enabled,
            success_text=(
                "弱网 DROP 已开启"
                if target
                else "弱网 DROP 已关闭"
            ),
        )

    def toggle_reject_network(self) -> None:
        if not self._manual_control_available():
            return

        target = self._reject_network_button.begin()
        if target is None:
            return

        self._run_network_toggle(
            button=self._reject_network_button,
            target=target,
            apply=(
                self.network.enable_reject_network
                if target
                else self.network.disable_reject_network
            ),
            enabled=lambda state: state.reject_enabled,
            success_text=(
                "断网 REJECT 已开启"
                if target
                else "断网 REJECT 已关闭"
            ),
        )

    def restore_network(self) -> None:
        if not self._manual_control_available():
            return

        def task() -> str:
            self.network.restore_network()
            return "游戏网络已恢复"

        self._run_task(
            "正在恢复游戏网络...",
            task,
        )
        self._refresh_network_buttons_async()

    def check_network_state(self) -> None:
        if not self._manual_control_available():
            return

        def task() -> str:
            return self.network.get_state().to_text()

        self._run_task(
            "正在检查网络状态...",
            task,
        )
        self._refresh_network_buttons_async()

    # =========================================================
    # 棋盘与策略同步
    # =========================================================

    def reset_sonar_board(self) -> None:
        if self._manual_session is not None:
            messagebox.showwarning(
                "人工干预中",
                "请先退出人工干预，再重置棋盘。",
            )
            return
        if self._auto_loop_running():
            messagebox.showwarning(
                "自动循环运行中",
                "请先停止自动循环，再重置棋盘。",
            )
            return

        self.sonar_strategy.reset()
        next_cell = self.sonar_strategy.choose_next_cell()
        self._write_log(
            "声纳棋盘和策略状态已重置；"
            f"下一格={next_cell}"
        )

    def set_board_selected(
        self,
        row: int,
        col: int,
    ) -> None:
        """手动调试时直接高亮一个格子。"""
        self.sonar_board.select_cell(
            row,
            col,
        )

    def set_board_result(
        self,
        row: int,
        col: int,
        hit: bool,
    ) -> None:
        """写入调试结果；当前策略格会同步推进策略。"""
        cell = (
            int(row),
            int(col),
        )

        if self.sonar_strategy.pending_cell == cell:
            self.report_strategy_result(
                row=row,
                col=col,
                hit=hit,
            )
            return

        self.sonar_board.report_result(
            row,
            col,
            hit=hit,
        )

    def report_strategy_result(
        self,
        row: int,
        col: int,
        hit: bool,
    ) -> None:
        """写入正式策略结果并准备下一格。"""
        cell = (
            int(row),
            int(col),
        )
        newly_confirmed = self.sonar_strategy.report_result(
            cell,
            hit=hit,
        )
        next_cell = self.sonar_strategy.choose_next_cell()
        result_text = "HIT" if hit else "MISS"
        message = (
            f"策略结果：{cell} -> {result_text}；"
            f"下一格={next_cell}"
        )

        if newly_confirmed:
            lengths = ",".join(
                str(ship.length)
                for ship in newly_confirmed
            )
            message += (
                f"；新确认潜艇=[{lengths}]"
            )

        self._write_log(message)

    def set_board_sunk(
        self,
        cells: list[tuple[int, int]],
    ) -> None:
        """手动调试入口：标记一组已确认潜艇格。"""
        self.sonar_board.mark_sunk(
            cells
        )

    # =========================================================
    # 基础人工干预
    # =========================================================

    def toggle_manual_intervention(self) -> None:
        if self._manual_intervention_button.state == ButtonState.ACTIVE:
            self._exit_manual_intervention()
            return
        self._enter_manual_intervention()

    def _enter_manual_intervention(self) -> None:
        if self._auto_loop_running():
            self._manual_intervention_button.set_locked(True)
            return
        if self._manual_intervention_button.begin() is None:
            return

        self._manual_session = ManualEditSession(
            self.sonar_board,
            self.sonar_strategy.get_confirmed_ships(),
        )
        self.board_view.set_manual_session(
            self._manual_session,
            on_message=self._show_manual_edit_message,
        )
        self._manual_edit_toolbar.pack(
            fill=tk.X,
            pady=(0, 8),
            before=self.board_view,
        )
        self._refresh_manual_history_buttons()
        self._manual_intervention_button.complete_toggle(True)
        self._set_edit_conflicting_controls_locked(True)
        self.status_var.set("人工干预中：棋盘修改仅保存在临时缓存")
        self._write_log("已进入基础人工干预模式；未操作模拟器和网络")

    def _exit_manual_intervention(self) -> None:
        if self._manual_intervention_button.begin() is None:
            return
        self.board_view.clear_manual_interaction()
        self.board_view.set_manual_session(None)
        self._manual_edit_toolbar.pack_forget()
        self._manual_session = None
        self._manual_intervention_button.complete_toggle(False)
        self._set_edit_conflicting_controls_locked(False)
        self.status_var.set("已退出人工干预，临时修改已丢弃")
        self._write_log("已退出人工干预模式；正式棋盘保持不变")

    def _set_edit_conflicting_controls_locked(self, locked: bool) -> None:
        self._auto_loop_button.set_locked(locked)
        state = ["disabled"] if locked else ["!disabled"]
        self._apply_device_button.state(state)
        self._reset_board_button.state(state)

    def _show_manual_edit_message(self, message: str) -> None:
        self.status_var.set(f"人工编辑：{message}")
        self._write_log(f"人工编辑：{message}")
        self._refresh_manual_history_buttons()

    def _refresh_manual_history_buttons(self) -> None:
        session = self._manual_session
        if session is None:
            return
        self._manual_undo_button.state(
            ["!disabled"] if session.can_undo else ["disabled"]
        )
        self._manual_redo_button.state(
            ["!disabled"] if session.can_redo else ["disabled"]
        )

    def undo_manual_edit(self) -> None:
        session = self._manual_session
        if session is None or not session.undo():
            return
        self.board_view.clear_manual_interaction()
        self.board_view.refresh()
        self._show_manual_edit_message("已撤回最近一次人工操作")

    def redo_manual_edit(self) -> None:
        session = self._manual_session
        if session is None or not session.redo():
            return
        self.board_view.clear_manual_interaction()
        self.board_view.refresh()
        self._show_manual_edit_message("已重做最近一次人工操作")

    def discard_manual_changes(self) -> None:
        session = self._manual_session
        if session is None:
            return
        self.board_view.clear_manual_interaction()
        session.discard_changes()
        self.board_view.refresh()
        self._show_manual_edit_message("已取消本次全部临时修改")

    def apply_manual_changes(self) -> None:
        """只提交棋盘事实并重建策略，保留人工模式和停止状态。"""
        session = self._manual_session
        if session is None:
            return
        if self._auto_loop_running():
            messagebox.showwarning(
                "自动循环仍在运行",
                "等待自动循环完全停止后才能应用人工修改。",
            )
            return

        self.board_view.clear_manual_interaction()
        self._manual_apply_button.state(["disabled"])
        try:
            result = apply_manual_edits(
                session,
                self.sonar_board,
                self.sonar_strategy,
            )
        except ManualEditError as exc:
            self.status_var.set(f"人工修改校验失败：{exc}")
            self._write_log(f"人工修改校验失败：{exc}")
            messagebox.showwarning("无法应用人工修改", str(exc))
            return
        except Exception as exc:
            self.status_var.set("人工修改应用失败，正式状态已回滚")
            self._write_log(f"人工修改应用失败，已回滚：{exc}")
            self._show_error(exc)
            return
        finally:
            self._manual_apply_button.state(["!disabled"])

        # 成功后以新的正式状态作为下一轮人工编辑基线。
        self._manual_session = ManualEditSession(
            self.sonar_board,
            self.sonar_strategy.get_confirmed_ships(),
        )
        self.board_view.set_manual_session(
            self._manual_session,
            on_message=self._show_manual_edit_message,
        )
        self._refresh_manual_history_buttons()
        self.status_var.set(
            f"人工修改已应用；下一目标格={result.next_cell}；自动循环保持停止"
        )
        self._write_log(
            "人工修改已应用："
            f"已确认={len(result.strategy_snapshot.confirmed_ships)}，"
            f"剩余={result.strategy_snapshot.remaining_submarines}，"
            f"已排除={len(result.strategy_snapshot.excluded_cells)}，"
            f"下一格={result.next_cell}；未操作模拟器和网络"
        )

    # =========================================================
    # 自动连续循环
    # =========================================================

    def _auto_loop_running(self) -> bool:
        return self._auto_loop_bridge.running

    def _manual_control_available(self) -> bool:
        """后台真正退出后才允许人工网络和重启操作。"""
        if not self._auto_loop_running():
            return True

        messagebox.showwarning(
            "自动循环仍在退出",
            "请等待自动循环在安全点停止后再执行人工操作。",
        )
        return False

    def _refresh_manual_button_locks(self) -> None:
        """沿用既有互斥边界：循环线程存活期间人工控制保持锁定。"""
        locked = self._auto_loop_running()
        self._restart_button.set_locked(locked)
        self._weak_network_button.set_locked(locked)
        self._reject_network_button.set_locked(locked)
        self._manual_intervention_button.set_locked(locked)

    def start_auto_loop(self) -> None:
        if self._manual_session is not None:
            messagebox.showwarning(
                "人工干预中",
                "请先退出人工干预，再启动自动循环。",
            )
            return
        if self._auto_loop_running():
            return

        if self._auto_loop_button.begin() is None:
            return

        self._manual_intervention_button.set_locked(True)

        self.auto_loop_state_var.set("启动中")
        self.auto_loop_total_var.set("发数：0 | HIT：0 | MISS：0")
        self.auto_loop_last_var.set("上一发：-")
        self.status_var.set("自动循环启动中...")
        self._write_log(
            "自动循环启动：停止请求会在最近的安全可中断点生效。"
        )
        if not self._auto_loop_bridge.start():
            self._auto_loop_button.complete_toggle(False)
            self._manual_intervention_button.set_locked(False)
            return

        self._auto_loop_button.complete_toggle(True)
        self._refresh_manual_button_locks()

    def toggle_auto_loop(self) -> None:
        """同一按钮按后台真实状态分派启动或停止。"""
        if self._auto_loop_running() or self._auto_loop_button.active:
            self.stop_auto_loop()
            return
        self.start_auto_loop()

    def stop_auto_loop(self) -> None:
        if not self._auto_loop_running():
            return

        if self._auto_loop_button.begin() is None:
            return

        self._auto_loop_bridge.request_stop()
        self.auto_loop_state_var.set("停止中")
        self.status_var.set("已请求停止：等待当前小动作完成...")
        self._write_log(
            "已请求停止自动循环：后台将在最近可中断点退出并保留当前现场。"
        )

    def _drain_auto_loop_events(self) -> None:
        """在 Tkinter 主线程中刷新循环状态。"""
        if self._pending_auto_loop_terminal is not None:
            if self._auto_loop_bridge.mark_finished():
                terminal = self._pending_auto_loop_terminal
                self._pending_auto_loop_terminal = None
                self._finish_auto_loop_terminal(*terminal)

        while True:
            try:
                kind, payload = self._auto_loop_bridge.get_event_nowait()
            except queue.Empty:
                break

            if kind == "result":
                index, result = payload
                result_text = "HIT" if result.hit else "MISS"
                current = self.auto_loop_total_var.get()

                try:
                    parts = (
                        current
                        .replace("发数：", "")
                        .replace("HIT：", "")
                        .replace("MISS：", "")
                        .split(" | ")
                    )
                    hits = int(parts[1])
                    misses = int(parts[2])
                except Exception:
                    hits = 0
                    misses = 0

                if result.hit:
                    hits += 1
                else:
                    misses += 1

                self.auto_loop_total_var.set(
                    f"发数：{index} | HIT：{hits} | MISS：{misses}"
                )
                self.auto_loop_last_var.set(
                    f"上一发：{result.context.cell} {result_text} | 结果已登记"
                )
                self.auto_loop_state_var.set("运行中")
                self.status_var.set(
                    f"自动循环运行中：第 {index} 发结果已登记"
                )
                continue

            if kind == "round":
                index, result = payload
                result_text = "HIT" if result.hit else "MISS"
                self.auto_loop_last_var.set(
                    f"上一发：{result.context.cell} {result_text} | 下一格：{result.next_cell}"
                )
                self.auto_loop_state_var.set("运行中")
                self.status_var.set(
                    f"自动循环运行中：第 {index} 发恢复完成"
                )
                continue

            if kind == "level":
                context = payload
                self._runtime = context
                self._bind_runtime(context)
                self.board_view.set_models(
                    context.board,
                    context.strategy,
                )
                self.auto_loop_state_var.set(f"第 {context.current_level} 关运行中")
                self.status_var.set(f"已进入第 {context.current_level} 关")
                self._write_log(
                    f"关卡切换完成：第 {context.current_level} 关；新棋盘和新策略已同步。"
                )
                continue

            if kind == "summary":
                self._pending_auto_loop_terminal = (kind, payload)
                break

            if kind == "error":
                self._pending_auto_loop_terminal = (kind, payload)
                break

        if (
            self._pending_auto_loop_terminal is not None
            and self._auto_loop_bridge.mark_finished()
        ):
            terminal = self._pending_auto_loop_terminal
            self._pending_auto_loop_terminal = None
            self._finish_auto_loop_terminal(*terminal)

        if self.winfo_exists() and not self._closing:
            self._auto_loop_after_id = self.after(
                100,
                self._drain_auto_loop_events,
            )

    def _finish_auto_loop_terminal(self, kind: str, payload: object) -> None:
        """后台线程退出后才把循环按钮恢复为空闲。"""
        self._auto_loop_button.complete_toggle(False)
        self._refresh_manual_button_locks()
        self._refresh_network_buttons_async()

        if kind == "error":
            self.auto_loop_state_var.set("错误")
            self.status_var.set("自动循环异常停止")
            self._show_error(payload)
            return

        summary = payload
        self.auto_loop_total_var.set(
            f"发数：{summary.rounds} | HIT：{summary.hits} | MISS：{summary.misses}"
        )

        if summary.stop_reason == "recovery_failed":
            state_text = "异常恢复失败，已安全停止"
        elif summary.stop_reason == "requested":
            state_text = "已停止"
        elif summary.stop_reason == "max_levels":
            state_text = f"已完成 {summary.completed_levels} 关"
        elif summary.strategy_done:
            state_text = "当前关卡策略完成"
        else:
            state_text = f"已停止：{summary.stop_reason}"

        self.auto_loop_state_var.set(state_text)
        self.status_var.set(state_text)

        if summary.stop_reason == "requested":
            network_text = "已保留安全断点处的页面和网络状态。"
        else:
            network_text = "游戏网络已按安全退出流程处理。"

        self._write_log(
            "自动循环结束："
            f"rounds={summary.rounds}，HIT={summary.hits}，MISS={summary.misses}，"
            f"reason={summary.stop_reason}；{network_text}"
        )

    # =========================================================
    # 其他 GUI 功能
    # =========================================================

    def open_screenshot_dir(self) -> None:
        config.ensure_directories()
        path = config.SCREENSHOT_DIR.resolve()

        try:
            os.startfile(
                str(path)
            )
            logger.info(
                "打开截图目录：%s",
                path,
            )
        except Exception as exc:
            self._show_error(
                exc
            )

    def on_close(self) -> None:
        """关闭程序前等待当前不可拆动作并恢复网络。"""
        if self._closing:
            return

        self._closing = True
        self._auto_loop_bridge.request_stop()
        self._cancel_regular_after_callbacks()
        board_view = getattr(self, "board_view", None)
        if board_view is not None:
            board_view.shutdown()
        self.status_var.set(
            "正在恢复网络并退出..."
        )
        self._write_log(
            "窗口关闭：等待自动线程退出后清理网络规则..."
        )

        def worker() -> None:
            try:
                self._auto_loop_bridge.shutdown_and_restore_network()
            except Exception as exc:
                message = (
                    "退出清理失败："
                    f"{exc}"
                )
            else:
                message = "退出清理完成"

            self._close_results.put(message)

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()
        self._close_poll_after_id = self.after(
            50,
            self._poll_close_result,
        )

    def _poll_close_result(self) -> None:
        """仅由 Tk 主线程轮询关闭清理结果。"""
        try:
            message = self._close_results.get_nowait()
        except queue.Empty:
            self._close_poll_after_id = self.after(
                50,
                self._poll_close_result,
            )
            return
        self._close_poll_after_id = None
        self._finish_close(message)

    def _finish_close(
        self,
        message: str,
    ) -> None:
        if message.startswith(
            "退出清理失败"
        ):
            logger.error(message)
        else:
            logger.info(message)

        detach_log_handler(
            self._log_handler
        )
        self.destroy()

    def _queue_ui_callback(self, callback: Callable[[], None]) -> None:
        """后台线程只入队，由 Tk 主线程统一执行 UI 回调。"""
        if self._closing:
            return
        self._ui_callbacks.put(callback)

    def _drain_ui_callbacks(self) -> None:
        while not self._closing:
            try:
                callback = self._ui_callbacks.get_nowait()
            except queue.Empty:
                break
            callback()

        if not self._closing and self.winfo_exists():
            self._ui_callback_after_id = self.after(
                50,
                self._drain_ui_callbacks,
            )

    def _cancel_regular_after_callbacks(self) -> None:
        """窗口关闭前取消所有周期性 Tk 回调。"""
        for attribute in (
            "_startup_after_id",
            "_ui_callback_after_id",
            "_log_after_id",
            "_auto_loop_after_id",
        ):
            after_id = getattr(self, attribute, None)
            if after_id is None:
                continue
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
            setattr(self, attribute, None)

    # =========================================================
    # 通用线程与日志处理
    # =========================================================

    def _run_action_button_task(
        self,
        button: StatefulButton,
        running_text: str,
        task: Callable[[], str],
    ) -> None:
        """一次性按钮只在后台动作完整返回后复位。"""
        self.status_var.set(running_text)
        self._write_log(running_text)

        def worker() -> None:
            try:
                with self._runtime.control_lock:
                    message = task()
            except Exception as exc:
                self._queue_ui_callback(
                    lambda error=exc: self._finish_action_failure(
                        button,
                        error,
                    ),
                )
                return

            self._queue_ui_callback(
                lambda text=message: self._finish_action_success(
                    button,
                    text,
                ),
            )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _finish_action_success(
        self,
        button: StatefulButton,
        message: str,
    ) -> None:
        button.complete_action()
        self._show_success(message)

    def _finish_action_failure(
        self,
        button: StatefulButton,
        error: Exception,
    ) -> None:
        button.complete_action()
        self._show_error(error)

    def _run_network_toggle(
        self,
        *,
        button: StatefulButton,
        target: bool,
        apply: Callable[[], None],
        enabled: Callable[[object], bool],
        success_text: str,
    ) -> None:
        """执行规则修改，再以 NetworkController 的真实查询结果收尾。"""
        running_text = (
            "正在开启网络控制..."
            if target
            else "正在关闭网络控制..."
        )
        self.status_var.set(running_text)
        self._write_log(running_text)

        def worker() -> None:
            operation_error: Exception | None = None
            actual_state: object | None = None

            with self._runtime.control_lock:
                try:
                    apply()
                except Exception as exc:
                    operation_error = exc

                try:
                    actual_state = self.network.get_state()
                except Exception as state_error:
                    if operation_error is None:
                        operation_error = state_error
                    else:
                        operation_error = RuntimeError(
                            f"{operation_error}；真实网络状态复核失败：{state_error}"
                        )

            if actual_state is None:
                self._queue_ui_callback(
                    lambda error=operation_error: self._finish_unknown_network_state(
                        button,
                        error,
                    ),
                )
                return

            is_active = enabled(actual_state)
            if operation_error is None and is_active != target:
                operation_error = RuntimeError(
                    "网络规则操作已返回，但真实状态与目标不一致"
                )

            self._queue_ui_callback(
                lambda active=is_active, error=operation_error: self._finish_network_toggle(
                    button,
                    active,
                    success_text,
                    error,
                ),
            )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _finish_network_toggle(
        self,
        button: StatefulButton,
        active: bool,
        success_text: str,
        error: Exception | None,
    ) -> None:
        button.complete_toggle(active)
        self._refresh_manual_button_locks()
        if error is None:
            self._show_success(success_text)
            return

        self._show_error(error)

    def _finish_unknown_network_state(
        self,
        button: StatefulButton,
        error: Exception | None,
    ) -> None:
        button.set_error()
        self._refresh_manual_button_locks()
        self._show_error(
            error
            if error is not None
            else RuntimeError("无法读取真实网络状态"),
        )

    def _refresh_network_buttons_async(self) -> None:
        """启动及自动流程结束后，读取设备规则而不从本地点击记录推断。"""
        self._weak_network_button.set_busy_message("正在读取弱网状态…")
        self._reject_network_button.set_busy_message("正在读取断网状态…")

        def worker() -> None:
            try:
                with self._runtime.control_lock:
                    state = self.network.get_state()
            except Exception:
                self._queue_ui_callback(self._mark_network_state_unknown)
                return

            self._queue_ui_callback(
                lambda actual=state: self._apply_network_state(actual),
            )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _apply_network_state(self, state: object) -> None:
        self._weak_network_button.complete_toggle(
            bool(getattr(state, "weak_enabled")),
        )
        self._reject_network_button.complete_toggle(
            bool(getattr(state, "reject_enabled")),
        )
        self._refresh_manual_button_locks()

    def _mark_network_state_unknown(self) -> None:
        self._weak_network_button.set_error()
        self._reject_network_button.set_error()
        self._refresh_manual_button_locks()

    def _run_task(
        self,
        running_text: str,
        task: Callable[[], str],
    ) -> None:
        self.status_var.set(
            running_text
        )
        self._write_log(
            running_text
        )

        def worker() -> None:
            try:
                control_lock = self._runtime.control_lock

                with control_lock:
                    message = task()
            except Exception as exc:
                self._queue_ui_callback(
                    lambda error=exc: self._show_error(error),
                )
                return

            self._queue_ui_callback(
                lambda text=message: self._show_success(text),
            )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _show_success(
        self,
        message: str,
    ) -> None:
        self.status_var.set(
            "操作完成"
        )
        self._write_log(
            message
        )

    def _show_error(
        self,
        error: Exception,
    ) -> None:
        message = str(error)
        self.status_var.set(
            "操作失败"
        )
        logger.error(
            "操作失败：%s",
            message,
        )
        messagebox.showerror(
            "操作失败",
            message,
        )

    def _write_log(
        self,
        message: str,
    ) -> None:
        logger.info(
            "%s",
            message,
        )

    def _drain_logs(self) -> None:
        while True:
            try:
                message = self._log_queue.get_nowait()
            except queue.Empty:
                break

            self.log_text.insert(
                tk.END,
                message + "\n",
            )
            self.log_text.see(
                tk.END
            )

        if self.winfo_exists() and not self._closing:
            self._log_after_id = self.after(
                100,
                self._drain_logs,
            )


def main() -> None:
    config.ensure_directories()
    app = BoomBeachSonarApp()
    app.mainloop()


if __name__ == "__main__":
    main()
