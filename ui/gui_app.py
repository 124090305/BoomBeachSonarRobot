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
from .runtime_context import AppRuntimeContext


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
        self._closing = False

        self._build_ui()

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
            enable_weak_network=self.enable_weak_network,
            disable_weak_network=self.disable_weak_network,
            enable_reject_network=self.enable_reject_network,
            disable_reject_network=self.disable_reject_network,
            restore_network=self.restore_network,
            check_network_state=self.check_network_state,
            start_auto_loop=self.start_auto_loop,
            stop_auto_loop=self.stop_auto_loop,
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

        self.auto_loop_start_button = (
            layout.auto_loop_start_button
        )
        self.auto_loop_stop_button = (
            layout.auto_loop_stop_button
        )
        self.log_text = layout.log_text
        self.board_view = layout.board_view

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
            self._bind_runtime(
                context
            )
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
        def task() -> str:
            self.game.restart_game()
            return "网络已恢复，游戏已重启"

        self._run_task(
            "正在恢复网络并重启游戏...",
            task,
        )

    # =========================================================
    # 网络功能
    # =========================================================

    def check_root(self) -> None:
        def task() -> str:
            return self.network.get_root_info()

        self._run_task(
            "正在检查 ROOT...",
            task,
        )

    def enable_weak_network(self) -> None:
        def task() -> str:
            self.network.enable_weak_network()
            return "弱网 DROP 已开启"

        self._run_task(
            "正在开启弱网...",
            task,
        )

    def disable_weak_network(self) -> None:
        def task() -> str:
            self.network.disable_weak_network()
            return "弱网 DROP 已关闭"

        self._run_task(
            "正在关闭弱网...",
            task,
        )

    def enable_reject_network(self) -> None:
        def task() -> str:
            self.network.enable_reject_network()
            return "断网 REJECT 已开启"

        self._run_task(
            "正在开启断网...",
            task,
        )

    def disable_reject_network(self) -> None:
        def task() -> str:
            self.network.disable_reject_network()
            return "断网 REJECT 已关闭"

        self._run_task(
            "正在关闭断网...",
            task,
        )

    def restore_network(self) -> None:
        def task() -> str:
            self.network.restore_network()
            return "游戏网络已恢复"

        self._run_task(
            "正在恢复游戏网络...",
            task,
        )

    def check_network_state(self) -> None:
        def task() -> str:
            return self.network.get_state().to_text()

        self._run_task(
            "正在检查网络状态...",
            task,
        )

    # =========================================================
    # 棋盘与策略同步
    # =========================================================

    def reset_sonar_board(self) -> None:
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
    # 自动连续循环
    # =========================================================

    def _auto_loop_running(self) -> bool:
        return self._auto_loop_bridge.running

    def _set_auto_loop_running(
        self,
        running: bool,
    ) -> None:
        if running:
            self.auto_loop_start_button.state(["disabled"])
            self.auto_loop_stop_button.state(["!disabled"])
        else:
            self.auto_loop_start_button.state(["!disabled"])
            self.auto_loop_stop_button.state(["disabled"])

    def start_auto_loop(self) -> None:
        if self._auto_loop_running():
            return

        if self.sonar_strategy.done:
            messagebox.showwarning(
                "策略已经完成",
                "当前棋盘策略已经完成。胜利处理尚未接入，请先重置棋盘再测试下一轮。",
            )
            return

        self.auto_loop_state_var.set("启动中")
        self.auto_loop_total_var.set("发数：0 | HIT：0 | MISS：0")
        self.auto_loop_last_var.set("上一发：-")
        self.status_var.set("自动循环启动中...")
        self._set_auto_loop_running(True)
        self._write_log(
            "自动循环启动：将连续执行完整单发闭环；停止按钮会在当前发完整结束后停止。"
        )
        self._auto_loop_bridge.start()

    def stop_auto_loop(self) -> None:
        if not self._auto_loop_running():
            return

        self._auto_loop_bridge.request_stop()
        self.auto_loop_state_var.set("停止中")
        self.status_var.set("已请求停止：等待当前发完整结束...")
        self._write_log(
            "已请求停止自动循环：当前发会完整走完网络恢复链后停止。"
        )

    def _drain_auto_loop_events(self) -> None:
        """在 Tkinter 主线程中刷新循环状态。"""
        while True:
            try:
                kind, payload = self._auto_loop_bridge.get_event_nowait()
            except queue.Empty:
                break

            if kind == "round":
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
                    f"上一发：{result.context.cell} {result_text} | 下一格：{result.next_cell}"
                )
                self.auto_loop_state_var.set("运行中")
                self.status_var.set(
                    f"自动循环运行中：第 {index} 发完成"
                )
                continue

            if kind == "summary":
                summary = payload
                self._auto_loop_bridge.mark_finished()
                self._set_auto_loop_running(False)
                self.auto_loop_total_var.set(
                    f"发数：{summary.rounds} | HIT：{summary.hits} | MISS：{summary.misses}"
                )

                if summary.strategy_done:
                    state_text = "策略完成，等待胜利处理"
                elif summary.stop_reason == "requested":
                    state_text = "已停止"
                else:
                    state_text = f"已停止：{summary.stop_reason}"

                self.auto_loop_state_var.set(state_text)
                self.status_var.set(state_text)
                self._write_log(
                    "自动循环结束："
                    f"rounds={summary.rounds}，HIT={summary.hits}，MISS={summary.misses}，"
                    f"reason={summary.stop_reason}；游戏网络已恢复正常。"
                )
                continue

            if kind == "error":
                self._auto_loop_bridge.mark_finished()
                self._set_auto_loop_running(False)
                self.auto_loop_state_var.set("错误")
                self.status_var.set("自动循环异常停止")
                self._show_error(payload)

        if self.winfo_exists():
            self.after(
                100,
                self._drain_auto_loop_events,
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
        """关闭程序前等待当前发并恢复网络。"""
        if self._closing:
            return

        self._closing = True
        self._auto_loop_bridge.request_stop()
        self.status_var.set(
            "正在恢复网络并退出..."
        )
        self._write_log(
            "窗口关闭：正在清理网络规则..."
        )

        def worker() -> None:
            try:
                if self._auto_loop_bridge.running:
                    finished = self._auto_loop_bridge.wait(
                        timeout=65.0
                    )
                    if not finished:
                        logger.warning(
                            "关闭窗口时自动循环仍未结束，将继续执行退出网络清理"
                        )

                self.network.restore_network()
            except Exception as exc:
                message = (
                    "退出清理失败："
                    f"{exc}"
                )
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

    # =========================================================
    # 通用线程与日志处理
    # =========================================================

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
                message = task()
            except Exception as exc:
                self.after(
                    0,
                    lambda error=exc: self._show_error(error),
                )
                return

            self.after(
                0,
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
