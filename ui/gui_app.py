from __future__ import annotations

import logging
import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Callable

import ttkbootstrap as ttk

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
from .runtime_context import AppRuntimeContext
from .status_model import RuntimeStatusModel
from .theme import (
    APP_GEOMETRY,
    APP_MIN_SIZE,
    APP_THEME,
    APP_TITLE,
    LOG_COLLAPSED_HEIGHT,
    LOG_EXPANDED_HEIGHT,
    configure_styles,
)


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


class BoomBeachSonarApp(ttk.Window):
    """声纳控制主窗口。"""

    def __init__(self) -> None:
        super().__init__(
            themename=APP_THEME,
        )
        configure_styles(
            ttk.Style()
        )

        self.title(APP_TITLE)
        self.geometry(APP_GEOMETRY)
        self.minsize(*APP_MIN_SIZE)

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

        self._status_model = RuntimeStatusModel()
        self.device_var = tk.StringVar(
            value=config.ADB_SERIAL
        )
        self.operation_var = tk.StringVar(
            value="等待操作"
        )
        self.device_status_var = tk.StringVar()
        self.page_status_var = tk.StringVar()
        self.network_status_var = tk.StringVar()
        self.auto_status_var = tk.StringVar()
        self.round_summary_var = tk.StringVar()
        self.phase_summary_var = tk.StringVar()
        self.target_summary_var = tk.StringVar()
        self.total_var = tk.StringVar()
        self.hit_var = tk.StringVar()
        self.miss_var = tk.StringVar()
        self.last_result_var = tk.StringVar()
        self.recovery_attempt_var = tk.StringVar()

        self._auto_loop_bridge = AutoProbeLoopBridge(
            self._runtime
        )
        self._closing = False
        self._log_expanded = False

        self._build_ui()
        self._refresh_dashboard()

        self.after(
            100,
            self._drain_logs,
        )
        self.after(
            100,
            self._drain_auto_loop_events,
        )
        self.protocol(
            "WM_DELETE_WINDOW",
            self.on_close,
        )

        logger.info("GUI 已启动")

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
            enable_weak_network=self.enable_weak_network,
            disable_weak_network=self.disable_weak_network,
            enable_reject_network=self.enable_reject_network,
            disable_reject_network=self.disable_reject_network,
            restore_network=self.restore_network,
            check_network_state=self.check_network_state,
            start_auto_loop=self.start_auto_loop,
            stop_auto_loop=self.stop_auto_loop,
            reset_sonar_board=self.reset_sonar_board,
            toggle_log=self.toggle_log,
        )

        layout = build_app_layout(
            self,
            device_var=self.device_var,
            operation_var=self.operation_var,
            device_status_var=self.device_status_var,
            page_status_var=self.page_status_var,
            network_status_var=self.network_status_var,
            auto_status_var=self.auto_status_var,
            round_summary_var=self.round_summary_var,
            phase_summary_var=self.phase_summary_var,
            target_summary_var=self.target_summary_var,
            total_var=self.total_var,
            hit_var=self.hit_var,
            miss_var=self.miss_var,
            last_result_var=self.last_result_var,
            recovery_attempt_var=self.recovery_attempt_var,
            board=self.sonar_board,
            strategy=self.sonar_strategy,
            actions=actions,
        )

        self.auto_loop_start_button = layout.auto_loop_start_button
        self.auto_loop_stop_button = layout.auto_loop_stop_button
        self.manual_control_buttons = layout.manual_control_buttons
        self.status_labels = layout.status_labels
        self.log_toggle_button = layout.log_toggle_button
        self.log_text = layout.log_text
        self.board_view = layout.board_view
        self.sidebar_scroller = layout.sidebar_scroller

    def _refresh_dashboard(self) -> None:
        snapshot = self._status_model.snapshot()
        status_items = {
            "device": (self.device_status_var, snapshot.device),
            "page": (self.page_status_var, snapshot.page),
            "network": (self.network_status_var, snapshot.network),
            "auto": (self.auto_status_var, snapshot.auto),
        }

        for name, (variable, item) in status_items.items():
            variable.set(f"● {item.text}")
            self.status_labels[name].configure(
                style=f"{item.tone}.Status.TLabel"
            )

        self.round_summary_var.set(snapshot.round_text)
        self.phase_summary_var.set(snapshot.phase_text)
        self.target_summary_var.set(snapshot.target_text)
        self.total_var.set(snapshot.total)
        self.hit_var.set(snapshot.hits)
        self.miss_var.set(snapshot.misses)
        self.last_result_var.set(snapshot.last_result)
        self.recovery_attempt_var.set(snapshot.recovery_attempt)

    # =========================================================
    # 控制器切换
    # =========================================================

    def apply_device(self) -> None:
        """切换 ADB 设备，保留当前棋盘和策略状态。"""
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
            self._bind_runtime(context)
            self._status_model.reset_detection()
            self.operation_var.set(
                f"已切换设备：{serial}"
            )
            self._refresh_dashboard()
            self._write_log(
                f"已切换设备：{serial}"
            )
        except Exception as exc:
            self._show_error(exc)

    # =========================================================
    # 基础功能
    # =========================================================

    def check_device(self) -> None:
        if not self._manual_control_available():
            return

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
            on_success=self._mark_device_online,
        )

    def take_screenshot(self) -> None:
        if not self._manual_control_available():
            return

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
            on_success=self._mark_device_online,
        )

    def restart_game(self) -> None:
        if not self._manual_control_available():
            return

        def task() -> str:
            self.game.restart_game()
            return "网络已恢复，游戏已重启"

        def success() -> None:
            self._status_model.device_online = True
            self._status_model.page_state = None
            self._set_network_facts(False, False)

        self._run_task(
            "正在恢复网络并重启游戏...",
            task,
            on_success=success,
        )

    # =========================================================
    # 网络功能
    # =========================================================

    def check_root(self) -> None:
        if not self._manual_control_available():
            return

        self._run_task(
            "正在检查 ROOT...",
            self.network.get_root_info,
            on_success=self._mark_device_online,
        )

    def enable_weak_network(self) -> None:
        if not self._manual_control_available():
            return

        def task() -> str:
            self.network.enable_weak_network()
            return "弱网 DROP 已开启"

        self._run_task(
            "正在开启弱网 DROP...",
            task,
            on_success=lambda: self._set_network_facts(True, None),
        )

    def disable_weak_network(self) -> None:
        if not self._manual_control_available():
            return

        def task() -> str:
            self.network.disable_weak_network()
            return "弱网 DROP 已关闭"

        self._run_task(
            "正在关闭弱网 DROP...",
            task,
            on_success=lambda: self._set_network_facts(False, None),
        )

    def enable_reject_network(self) -> None:
        if not self._manual_control_available():
            return

        def task() -> str:
            self.network.enable_reject_network()
            return "断网 REJECT 已开启"

        self._run_task(
            "正在开启断网 REJECT...",
            task,
            on_success=lambda: self._set_network_facts(None, True),
        )

    def disable_reject_network(self) -> None:
        if not self._manual_control_available():
            return

        def task() -> str:
            self.network.disable_reject_network()
            return "断网 REJECT 已关闭"

        self._run_task(
            "正在关闭断网 REJECT...",
            task,
            on_success=lambda: self._set_network_facts(None, False),
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
            on_success=lambda: self._set_network_facts(False, False),
        )

    def check_network_state(self) -> None:
        if not self._manual_control_available():
            return

        state_holder: list[object] = []

        def task() -> str:
            state = self.network.get_state()
            state_holder.append(state)
            return state.to_text()

        def success() -> None:
            state = state_holder[0]
            self._status_model.device_online = True
            self._set_network_facts(
                state.weak_enabled,
                state.reject_enabled,
            )

        self._run_task(
            "正在检查网络状态...",
            task,
            on_success=success,
        )

    def _mark_device_online(self) -> None:
        self._status_model.device_online = True

    def _set_network_facts(
        self,
        weak: bool | None,
        reject: bool | None,
    ) -> None:
        self._status_model.device_online = True

        if weak is not None:
            self._status_model.weak_network_enabled = weak

        if reject is not None:
            self._status_model.reject_network_enabled = reject

    # =========================================================
    # 棋盘与策略同步
    # =========================================================

    def reset_sonar_board(self) -> None:
        if not self._manual_control_available():
            return

        self.sonar_strategy.reset()
        next_cell = self.sonar_strategy.choose_next_cell()
        self._status_model.target_mode = "next"
        self._status_model.target_cell = next_cell
        self._refresh_dashboard()
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
        self.sonar_board.select_cell(row, col)

    def set_board_result(
        self,
        row: int,
        col: int,
        hit: bool,
    ) -> None:
        """写入调试结果；当前策略格会同步推进策略。"""
        cell = (int(row), int(col))

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
        cell = (int(row), int(col))
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
            message += f"；新确认潜艇=[{lengths}]"

        self._write_log(message)

    def set_board_sunk(
        self,
        cells: list[tuple[int, int]],
    ) -> None:
        """手动调试入口：标记一组已确认潜艇格。"""
        self.sonar_board.mark_sunk(cells)

    # =========================================================
    # 自动连续循环
    # =========================================================

    def _auto_loop_running(self) -> bool:
        return self._auto_loop_bridge.running

    def _manual_control_available(self) -> bool:
        """后台真正退出后才允许人工设备、网络和棋盘操作。"""
        if not self._auto_loop_running():
            return True

        messagebox.showwarning(
            "自动循环仍在退出",
            "请等待自动循环在安全点停止后再执行人工操作。",
        )
        return False

    def _set_auto_loop_running(
        self,
        running: bool,
    ) -> None:
        if running:
            self.auto_loop_start_button.state(["disabled"])
            self.auto_loop_stop_button.state(["!disabled"])
            manual_state = "disabled"
        else:
            self.auto_loop_start_button.state(["!disabled"])
            self.auto_loop_stop_button.state(["disabled"])
            manual_state = "!disabled"

        for button in self.manual_control_buttons:
            button.state([manual_state])

    def start_auto_loop(self) -> None:
        if self._auto_loop_running():
            return

        if self.sonar_strategy.done:
            messagebox.showwarning(
                "策略已经完成",
                "当前棋盘策略已经完成。胜利处理尚未接入，请先重置棋盘再测试下一轮。",
            )
            return

        self._status_model.begin_run(
            self.sonar_strategy.pending_cell
        )
        self.operation_var.set("自动探测启动中...")
        self._set_auto_loop_running(True)
        self._refresh_dashboard()
        self._write_log(
            "自动循环启动：停止请求会在最近的安全可中断点生效。"
        )

        if not self._auto_loop_bridge.start():
            self._status_model.loop_state = "stopped"
            self._set_auto_loop_running(False)
            self._refresh_dashboard()

    def stop_auto_loop(self) -> None:
        if not self._auto_loop_running():
            return

        self._auto_loop_bridge.request_stop()
        self._status_model.request_stop()
        self.operation_var.set(
            "已请求停止，等待当前安全动作完成..."
        )
        self._refresh_dashboard()
        self._write_log(
            "已请求停止自动循环：后台将在最近可中断点退出并保留当前现场。"
        )

    def _drain_auto_loop_events(self) -> None:
        """在 Tkinter 主线程中刷新循环状态。"""
        changed = False

        while True:
            try:
                kind, payload = self._auto_loop_bridge.get_event_nowait()
            except queue.Empty:
                break

            changed = True

            if kind == "status":
                self._status_model.apply_progress(payload)
                continue

            if kind == "result":
                index, result = payload
                self._status_model.record_result(
                    index,
                    cell=result.context.cell,
                    hit=result.hit,
                )
                self.operation_var.set(
                    f"第 {index} 发结果已登记"
                )
                continue

            if kind == "round":
                index, result = payload
                self._status_model.record_round(
                    next_cell=result.next_cell,
                )
                self.operation_var.set(
                    f"第 {index} 发恢复完成"
                )
                continue

            if kind == "summary":
                summary = payload
                self._auto_loop_bridge.mark_finished()
                self._set_auto_loop_running(False)
                self._status_model.finish(
                    rounds=summary.rounds,
                    hits=summary.hits,
                    misses=summary.misses,
                    stop_reason=summary.stop_reason,
                    strategy_done=summary.strategy_done,
                )

                if not summary.strategy_done:
                    pending_cell = self.sonar_strategy.pending_cell
                    self._status_model.target_mode = (
                        "next"
                        if pending_cell is not None
                        else "none"
                    )
                    self._status_model.target_cell = pending_cell

                if summary.stop_reason == "recovery_failed":
                    state_text = "异常恢复失败，已安全停止"
                elif summary.stop_reason == "requested":
                    state_text = "已停止，现场已保留"
                elif summary.strategy_done:
                    state_text = "策略完成，等待胜利处理"
                else:
                    state_text = f"已停止：{summary.stop_reason}"

                self.operation_var.set(state_text)
                network_text = (
                    "已保留当前页面和网络状态。"
                    if summary.stop_reason == "requested"
                    else "游戏网络已按安全退出流程处理。"
                )
                self._write_log(
                    "自动循环结束："
                    f"rounds={summary.rounds}，HIT={summary.hits}，MISS={summary.misses}，"
                    f"reason={summary.stop_reason}；{network_text}"
                )
                continue

            if kind == "error":
                self._auto_loop_bridge.mark_finished()
                self._set_auto_loop_running(False)
                self._status_model.fail()
                self.operation_var.set("自动循环异常停止")
                self._show_error(payload)

        if changed:
            self._refresh_dashboard()

        if self.winfo_exists():
            self.after(
                100,
                self._drain_auto_loop_events,
            )

    # =========================================================
    # 其他 GUI 功能
    # =========================================================

    def toggle_log(self) -> None:
        self._log_expanded = not self._log_expanded
        height = (
            LOG_EXPANDED_HEIGHT
            if self._log_expanded
            else LOG_COLLAPSED_HEIGHT
        )
        self.log_text.configure(height=height)
        self.log_toggle_button.configure(
            text="收起" if self._log_expanded else "展开"
        )

    def open_screenshot_dir(self) -> None:
        config.ensure_directories()
        path = config.SCREENSHOT_DIR.resolve()

        try:
            os.startfile(str(path))
            logger.info(
                "打开截图目录：%s",
                path,
            )
        except Exception as exc:
            self._show_error(exc)

    def on_close(self) -> None:
        """关闭程序前等待当前不可拆动作并恢复网络。"""
        if self._closing:
            return

        self._closing = True
        self._auto_loop_bridge.request_stop()

        if self._auto_loop_running():
            self._status_model.request_stop()

        self.operation_var.set(
            "正在恢复网络并退出..."
        )
        self._refresh_dashboard()
        self._write_log(
            "窗口关闭：等待自动线程退出后清理网络规则..."
        )

        def worker() -> None:
            try:
                self._auto_loop_bridge.shutdown_and_restore_network()
            except Exception as exc:
                message = f"退出清理失败：{exc}"
            else:
                message = "退出清理完成"

            self.after(
                0,
                lambda text=message: self._finish_close(text),
            )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _finish_close(
        self,
        message: str,
    ) -> None:
        if message.startswith("退出清理失败"):
            logger.error(message)
        else:
            logger.info(message)

        detach_log_handler(
            self._log_handler
        )
        self.destroy()

    # =========================================================
    # 通用线程与日志处理
    # =========================================================

    def _run_task(
        self,
        running_text: str,
        task: Callable[[], str],
        *,
        on_success: Callable[[], None] | None = None,
    ) -> None:
        self.operation_var.set(running_text)
        self._write_log(running_text)

        def worker() -> None:
            try:
                with self._runtime.control_lock:
                    message = task()
            except Exception as exc:
                self.after(
                    0,
                    lambda error=exc: self._show_error(error),
                )
                return

            self.after(
                0,
                lambda text=message: self._show_success(
                    text,
                    on_success=on_success,
                ),
            )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _show_success(
        self,
        message: str,
        *,
        on_success: Callable[[], None] | None = None,
    ) -> None:
        if on_success is not None:
            on_success()

        self.operation_var.set("操作完成")
        self._refresh_dashboard()
        self._write_log(message)

    def _show_error(
        self,
        error: Exception,
    ) -> None:
        message = str(error)
        self.operation_var.set("操作失败")
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
        logger.info("%s", message)

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
            self.log_text.see(tk.END)

        if self.winfo_exists():
            self.after(
                100,
                self._drain_logs,
            )


def main() -> None:
    config.ensure_directories()
    app = BoomBeachSonarApp()
    app.mainloop()


if __name__ == "__main__":
    main()
