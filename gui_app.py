from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

import config
from controllers import (
    AdbController,
    GameController,
)
from flows import run_screenshot_check


class App(tk.Tk):
    """当前阶段的轻量图形控制界面。"""

    def __init__(self) -> None:
        super().__init__()

        self.title(
            "BoomBeach Sonar Robot"
        )

        self.geometry(
            "680x420"
        )

        self.minsize(
            620,
            360,
        )

        self.adb = AdbController()

        self.game = GameController(
            self.adb
        )

        self.status_var = tk.StringVar(
            value="等待操作"
        )

        self.device_var = tk.StringVar(
            value=config.ADB_SERIAL
        )

        self._build_ui()

    def _build_ui(self) -> None:
        """创建界面控件。"""
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

        button_row = ttk.Frame(
            container
        )

        button_row.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky=tk.EW,
            pady=16,
        )

        ttk.Button(
            button_row,
            text="检查设备",
            command=self.check_device,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            button_row,
            text="获取截图",
            command=self.take_screenshot,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            button_row,
            text="重启游戏",
            command=self.restart_game,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Button(
            button_row,
            text="打开截图目录",
            command=self.open_screenshot_dir,
        ).pack(
            side=tk.LEFT,
            padx=4,
        )

        ttk.Label(
            container,
            text="状态：",
        ).grid(
            row=2,
            column=0,
            sticky=tk.NW,
        )

        ttk.Label(
            container,
            textvariable=self.status_var,
        ).grid(
            row=2,
            column=1,
            columnspan=2,
            sticky=tk.W,
        )

        self.log_text = tk.Text(
            container,
            height=14,
            wrap=tk.WORD,
        )

        self.log_text.grid(
            row=3,
            column=0,
            columnspan=3,
            sticky=tk.NSEW,
            pady=(12, 0),
        )

        container.columnconfigure(
            1,
            weight=1,
        )

        container.rowconfigure(
            3,
            weight=1,
        )

    def apply_device(self) -> None:
        """使用输入框中的设备编号创建控制器。"""
        serial = self.device_var.get().strip()

        if not serial:
            messagebox.showwarning(
                "设备编号为空",
                "请输入 ADB 设备编号",
            )
            return

        try:
            self.adb = AdbController(
                serial=serial
            )

            self.game = GameController(
                self.adb
            )

            self._write_log(
                f"已切换设备：{serial}"
            )

        except Exception as exc:
            self._show_error(exc)

    def check_device(self) -> None:
        """检查当前模拟器是否在线。"""

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
        """执行截图检查流程。"""

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
        """重启海岛奇兵应用。"""

        def task() -> str:
            self.game.restart_game()

            return "游戏已重启"

        self._run_task(
            "正在重启游戏...",
            task,
        )

    def open_screenshot_dir(self) -> None:
        """使用资源管理器打开截图目录。"""
        config.ensure_directories()

        path = config.SCREENSHOT_DIR.resolve()

        try:
            os.startfile(
                str(path)
            )
        except Exception as exc:
            self._show_error(exc)

    def _run_task(
        self,
        running_text: str,
        task: Callable[[], str],
    ) -> None:
        """在线程中执行耗时任务，防止界面卡住。"""
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
                    lambda error=exc: self._show_error(
                        error
                    ),
                )
                return

            self.after(
                0,
                lambda text=message: self._show_success(
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
        message = str(error)

        self.status_var.set(
            "操作失败"
        )

        self._write_log(
            f"错误：{message}"
        )

        messagebox.showerror(
            "操作失败",
            message,
        )

    def _write_log(
        self,
        message: str,
    ) -> None:
        self.log_text.insert(
            tk.END,
            message + "\n",
        )

        self.log_text.see(
            tk.END
        )


def main() -> None:
    config.ensure_directories()

    app = App()

    app.mainloop()


if __name__ == "__main__":
    main()