from __future__ import annotations

import logging
import os
import queue
import threading
import tkinter as tk

from tkinter import (
    messagebox,
    ttk,
)

from typing import Callable

import config
import config_test

from controllers import (
    AdbController,
    GameController,
    NetworkController,
)

from flows import (
    run_screenshot_check,
)

from logger import (
    GuiLogFormatter,
    attach_log_handler,
    detach_log_handler,
    get_logger,
)

from sonar import (
    CheckerboardHuntStrategy,
    SonarBoard,
)

from ui import (
    SonarBoardView,
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


class App(tk.Tk):
    """当前阶段的轻量控制界面。"""

    def __init__(
        self,
    ) -> None:
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

        self._log_queue: queue.Queue[str] = (
            queue.Queue()
        )

        self._log_handler = QueueLogHandler(
            self._log_queue
        )

        attach_log_handler(
            self._log_handler
        )

        self.adb = AdbController()

        self.network = (
            NetworkController(
                self.adb
            )
        )

        self.game = (
            GameController(
                self.adb,
                network=self.network,
            )
        )

        # 当前阶段先使用 config_test 中的固定棋盘配置。
        self.sonar_board = SonarBoard(
            n=config_test.TEST_GRID_SIZE,
            submarines=config_test.TEST_SUBMARINES,
        )

        if config_test.TEST_BOARD_QUAD is not None:
            self.sonar_board.set_screen_quad(
                config_test.TEST_BOARD_QUAD
            )

        # 选格策略和棋盘使用同一个 SonarBoard。
        # UI 只读取 strategy.snapshot()，后续切换概率策略时，
        # 这里替换策略对象即可继续复用棋盘显示层。
        self.sonar_strategy = CheckerboardHuntStrategy(
            self.sonar_board,
            hunt_parity=config_test.TEST_HUNT_PARITY,
            use_safety_rule=config_test.TEST_USE_SAFETY_RULE,
        )

        # GUI 启动后先准备第一格，让棋盘立即显示“下一步选择”。
        self.sonar_strategy.choose_next_cell()

        self.status_var = (
            tk.StringVar(
                value="等待操作"
            )
        )

        self.device_var = (
            tk.StringVar(
                value=config.ADB_SERIAL
            )
        )

        self._closing = False

        self._build_ui()

        self.after(
            100,
            self._drain_logs,
        )

        self.protocol(
            "WM_DELETE_WINDOW",
            self.on_close,
        )

        logger.info(
            "GUI 已启动"
        )

    def _build_ui(
        self,
    ) -> None:
        """创建界面。"""
        container = ttk.Frame(
            self,
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
            textvariable=self.device_var,
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
            command=self.apply_device,
        ).grid(
            row=0,
            column=2,
        )

        # 基础控制按钮
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
            command=self.check_device,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            basic_row,
            text="获取截图",
            command=self.take_screenshot,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            basic_row,
            text="重启游戏",
            command=self.restart_game,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            basic_row,
            text="打开截图目录",
            command=self.open_screenshot_dir,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        # 网络控制按钮
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
            command=self.check_root,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            network_row,
            text="开启弱网",
            command=self.enable_weak_network,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            network_row,
            text="关闭弱网",
            command=self.disable_weak_network,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            network_row,
            text="开启断网",
            command=self.enable_reject_network,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            network_row,
            text="关闭断网",
            command=self.disable_reject_network,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            network_row,
            text="恢复网络",
            command=self.restore_network,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            network_row,
            text="网络状态",
            command=self.check_network_state,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Label(
            container,
            text="状态：",
        ).grid(
            row=3,
            column=0,
            sticky=tk.NW,
        )

        ttk.Label(
            container,
            textvariable=self.status_var,
        ).grid(
            row=3,
            column=1,
            columnspan=2,
            sticky=tk.W,
        )

        self.log_text = tk.Text(
            container,
            height=10,
            wrap=tk.WORD,
        )

        self.log_text.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky=tk.NSEW,
            pady=(12, 0),
        )

        # 声纳棋盘
        board_section = ttk.LabelFrame(
            container,
            text="棋盘与策略同步",
            padding=10,
        )

        board_section.grid(
            row=5,
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
            command=self.reset_sonar_board,
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

        self.board_view = SonarBoardView(
            board_section,
            board=self.sonar_board,
            strategy=self.sonar_strategy,
        )

        self.board_view.pack(
            fill=tk.BOTH,
            expand=True,
        )

        container.columnconfigure(
            1,
            weight=1,
        )

        container.rowconfigure(
            4,
            weight=1,
        )

        container.rowconfigure(
            5,
            weight=2,
        )

    # =========================================================
    # 控制器切换
    # =========================================================

    def apply_device(
        self,
    ) -> None:
        """切换 ADB 设备。"""
        serial = (
            self.device_var.get()
            .strip()
        )

        if not serial:
            messagebox.showwarning(
                "设备编号为空",
                "请输入 ADB 设备编号",
            )

            return

        try:
            self.adb = (
                AdbController(
                    serial=serial
                )
            )

            self.network = (
                NetworkController(
                    self.adb
                )
            )

            self.game = (
                GameController(
                    self.adb,
                    network=self.network,
                )
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

    def check_device(
        self,
    ) -> None:
        """检查设备。"""

        def task() -> str:
            self.adb.ensure_device_online()

            devices = (
                self.adb.list_devices()
            )

            return (
                f"设备正常：{self.adb.serial}\n"
                f"在线设备：{devices}"
            )

        self._run_task(
            "正在检查设备...",
            task,
        )

    def take_screenshot(
        self,
    ) -> None:
        """截图。"""

        def task() -> str:
            result = (
                run_screenshot_check(
                    self.adb
                )
            )

            return (
                f"截图完成：{result.path}\n"
                f"尺寸：{result.width}x{result.height}"
            )

        self._run_task(
            "正在获取截图...",
            task,
        )

    def restart_game(
        self,
    ) -> None:
        """恢复网络并重启游戏。"""

        def task() -> str:
            self.game.restart_game()

            return (
                "网络已恢复，游戏已重启"
            )

        self._run_task(
            "正在恢复网络并重启游戏...",
            task,
        )

    # =========================================================
    # 网络功能
    # =========================================================

    def check_root(
        self,
    ) -> None:
        """检查 ROOT 与 UID。"""

        def task() -> str:
            return (
                self.network
                .get_root_info()
            )

        self._run_task(
            "正在检查 ROOT...",
            task,
        )

    def enable_weak_network(
        self,
    ) -> None:
        """开启弱网。"""

        def task() -> str:
            self.network.enable_weak_network()

            return (
                "弱网 DROP 已开启"
            )

        self._run_task(
            "正在开启弱网...",
            task,
        )

    def disable_weak_network(
        self,
    ) -> None:
        """关闭弱网。"""

        def task() -> str:
            self.network.disable_weak_network()

            return (
                "弱网 DROP 已关闭"
            )

        self._run_task(
            "正在关闭弱网...",
            task,
        )

    def enable_reject_network(
        self,
    ) -> None:
        """开启断网。"""

        def task() -> str:
            self.network.enable_reject_network()

            return (
                "断网 REJECT 已开启"
            )

        self._run_task(
            "正在开启断网...",
            task,
        )

    def disable_reject_network(
        self,
    ) -> None:
        """关闭断网。"""

        def task() -> str:
            self.network.disable_reject_network()

            return (
                "断网 REJECT 已关闭"
            )

        self._run_task(
            "正在关闭断网...",
            task,
        )

    def restore_network(
        self,
    ) -> None:
        """恢复正常网络。"""

        def task() -> str:
            self.network.restore_network()

            return (
                "游戏网络已恢复"
            )

        self._run_task(
            "正在恢复游戏网络...",
            task,
        )

    def check_network_state(
        self,
    ) -> None:
        """读取网络状态。"""

        def task() -> str:
            state = (
                self.network.get_state()
            )

            return state.to_text()

        self._run_task(
            "正在检查网络状态...",
            task,
        )

    # =========================================================
    # 棋盘与策略同步
    # =========================================================

    def reset_sonar_board(
        self,
    ) -> None:
        """重置棋盘和策略，并立即准备新一轮第一格。"""
        self.sonar_strategy.reset()

        next_cell = (
            self.sonar_strategy
            .choose_next_cell()
        )

        self._write_log(
            "声纳棋盘和策略状态已重置；"
            f"下一格={next_cell}"
        )

    def set_board_selected(
        self,
        row: int,
        col: int,
    ) -> None:
        """
        手动调试时直接高亮一个格子。

        正式自动流程应优先调用：
        self.sonar_strategy.choose_next_cell()
        """
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
        """
        写入一次探测结果。

        如果这个格子正是策略等待结果的格子，
        会同步更新策略并立即准备下一格；
        其他格子仍保留为手动棋盘调试入口。
        """
        cell = (
            int(row),
            int(col),
        )

        if (
            self.sonar_strategy.pending_cell
            == cell
        ):
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
        """
        正式策略流程使用的结果入口。

        流程：
        当前选择 -> 写 HIT/MISS -> 自动确认潜艇 -> 自动排除安全区
        -> 立即选择并高亮下一格。
        """
        cell = (
            int(row),
            int(col),
        )

        newly_confirmed = (
            self.sonar_strategy
            .report_result(
                cell,
                hit=hit,
            )
        )

        next_cell = (
            self.sonar_strategy
            .choose_next_cell()
        )

        result_text = (
            "HIT"
            if hit
            else "MISS"
        )

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
        """
        手动调试入口：直接把一组格子标记为已确认潜艇。

        正式策略确认潜艇时会自动调用 SonarBoard.mark_sunk()。
        """
        self.sonar_board.mark_sunk(
            cells
        )

    # =========================================================
    # 其他 GUI 功能
    # =========================================================

    def open_screenshot_dir(
        self,
    ) -> None:
        """打开截图目录。"""
        config.ensure_directories()

        path = (
            config.SCREENSHOT_DIR
            .resolve()
        )

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

    def on_close(
        self,
    ) -> None:
        """关闭程序前恢复网络。"""
        if self._closing:
            return

        self._closing = True

        self.status_var.set(
            "正在恢复网络并退出..."
        )

        self._write_log(
            "窗口关闭：正在清理网络规则..."
        )

        def worker() -> None:
            try:
                self.network.restore_network()

            except Exception as exc:
                message = (
                    "退出清理失败："
                    f"{exc}"
                )

            else:
                message = (
                    "退出清理完成"
                )

            self.after(
                0,
                lambda text=message:
                self._finish_close(
                    text
                ),
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
            logger.error(
                message
            )
        else:
            logger.info(
                message
            )

        detach_log_handler(
            self._log_handler
        )

        self.destroy()

    # =========================================================
    # 通用线程处理
    # =========================================================

    def _run_task(
        self,
        running_text: str,
        task: Callable[
            [],
            str,
        ],
    ) -> None:
        """后台执行耗时任务。"""
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
                    lambda error=exc:
                    self._show_error(
                        error
                    ),
                )

                return

            self.after(
                0,
                lambda text=message:
                self._show_success(
                    text
                ),
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
        message = str(
            error
        )

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

    def _drain_logs(
        self,
    ) -> None:
        """把后台日志安全写入 Tkinter 文本框。"""
        while True:
            try:
                message = (
                    self._log_queue
                    .get_nowait()
                )

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

    app = App()

    app.mainloop()


if __name__ == "__main__":
    main()
