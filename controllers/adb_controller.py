from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

import config


class AdbCommandError(RuntimeError):
    """ADB 命令执行失败。"""

    def __init__(
        self,
        command: Sequence[str],
        returncode: int,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.command = list(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

        message = (
            stderr.strip()
            or stdout.strip()
            or "ADB 命令执行失败"
        )

        super().__init__(
            f"{' '.join(self.command)}: {message}"
        )


class AdbController:
    """封装单台安卓设备的基础 ADB 操作。"""

    def __init__(
        self,
        serial: str = config.ADB_SERIAL,
        adb_path: str | Path | None = None,
    ) -> None:
        self.serial = serial.strip()

        if not self.serial:
            raise ValueError(
                "ADB 设备编号不能为空"
            )

        self.adb_path = self._find_adb(
            adb_path
        )

        # ROOT 状态缓存。
        self._root_shell_ready = False
        self._su_fallback = False
        self._su_available: bool | None = None

        # 游戏 UID 缓存。
        self._package_uid_cache: dict[
            str,
            int,
        ] = {}

    @staticmethod
    def _find_adb(
        adb_path: str | Path | None,
    ) -> Path:
        """
        查找 adb.exe。

        顺序：
        1. 手动传入路径
        2. config.py
        3. 系统 PATH
        """
        candidates: list[Path] = []

        if adb_path is not None:
            candidates.append(
                Path(adb_path)
            )

        candidates.append(
            config.ADB_PATH
        )

        for candidate in candidates:
            candidate = (
                candidate.expanduser()
            )

            if candidate.is_file():
                return candidate.resolve()

        path_result = shutil.which(
            "adb"
        )

        if path_result:
            return Path(
                path_result
            ).resolve()

        checked_paths = ", ".join(
            str(path)
            for path in candidates
        )

        raise FileNotFoundError(
            "没有找到 adb.exe。"
            f"已检查：{checked_paths}。"
            "请修改 config.py 中的 ADB_PATH。"
        )

    def _build_command(
        self,
        args: Sequence[str],
        *,
        device: bool,
    ) -> list[str]:
        """组装完整 ADB 命令。"""
        command = [
            str(self.adb_path)
        ]

        if device:
            command.extend(
                [
                    "-s",
                    self.serial,
                ]
            )

        command.extend(
            str(arg)
            for arg in args
        )

        return command

    def run(
        self,
        args: Sequence[str],
        *,
        device: bool = True,
        check: bool = True,
        timeout: float = config.ADB_COMMAND_TIMEOUT,
    ) -> subprocess.CompletedProcess[str]:
        """执行文本形式的 ADB 命令。"""
        command = self._build_command(
            args,
            device=device,
        )

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "ADB 命令超时："
                f"{' '.join(command)}"
            ) from exc

        if (
            check
            and result.returncode != 0
        ):
            raise AdbCommandError(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        return result

    def list_devices(
        self,
    ) -> dict[str, str]:
        """获取 ADB 设备列表。"""
        result = self.run(
            ["devices"],
            device=False,
        )

        devices: dict[
            str,
            str,
        ] = {}

        lines = (
            result.stdout.splitlines()
        )

        for line in lines[1:]:
            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]

                devices[serial] = state

        return devices

    def ensure_device_online(
        self,
    ) -> None:
        """确认目标设备在线。"""
        devices = self.list_devices()

        state = devices.get(
            self.serial
        )

        if state == "device":
            return

        if state is None:
            raise RuntimeError(
                f"没有发现设备 {self.serial}。"
                "请先启动模拟器，并执行 adb devices 检查。"
            )

        raise RuntimeError(
            f"设备 {self.serial} "
            f"当前状态为 {state}"
        )

    def wait_until_online(
        self,
        timeout: float = 8.0,
    ) -> None:
        """等待 adb root 后设备重新上线。"""
        deadline = (
            time.monotonic()
            + timeout
        )

        while (
            time.monotonic()
            < deadline
        ):
            try:
                self.ensure_device_online()
                return

            except RuntimeError:
                time.sleep(0.4)

        self.ensure_device_online()

    # =========================================================
    # ROOT
    # =========================================================

    def ensure_root_shell(
        self,
    ) -> str:
        """
        准备 ROOT shell。

        返回：
        adb-root
        su-c
        """
        self.ensure_device_online()

        if self._root_shell_ready:
            if self._su_fallback:
                return "su-c"

            return "adb-root"

        # 当前 shell 已经是 ROOT。
        if self._is_root_shell():
            self._root_shell_ready = True
            self._su_fallback = False

            return "adb-root"

        # 尝试 adb root。
        self.run(
            ["root"],
            check=False,
        )

        time.sleep(1.0)

        try:
            self.wait_until_online()

        except RuntimeError:
            pass

        if self._is_root_shell():
            self._root_shell_ready = True
            self._su_fallback = False

            return "adb-root"

        # adb root 不可用时尝试 su -c。
        if self._is_su_available():
            self._root_shell_ready = True
            self._su_fallback = True

            return "su-c"

        raise RuntimeError(
            "当前模拟器没有可用 ROOT 权限。"
            "请先在雷电模拟器设置中开启 ROOT 权限。"
        )

    def run_privileged(
        self,
        script: str,
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """使用 ROOT 权限执行 shell 命令。"""
        if not script.strip():
            raise ValueError(
                "特权命令不能为空"
            )

        self.ensure_root_shell()

        quoted_script = (
            self._quote_shell_arg(
                script
            )
        )

        if self._su_fallback:
            return self.run(
                [
                    "shell",
                    "su",
                    "-c",
                    quoted_script,
                ],
                check=check,
            )

        return self.run(
            [
                "shell",
                "sh",
                "-c",
                quoted_script,
            ],
            check=check,
        )

    def get_package_uid(
        self,
        package_name: str,
    ) -> int:
        """获取指定应用的安卓 UID。"""
        package_name = (
            package_name.strip()
        )

        if not package_name:
            raise ValueError(
                "应用包名不能为空"
            )

        cached = (
            self._package_uid_cache.get(
                package_name
            )
        )

        if cached is not None:
            return cached

        result = self.run(
            [
                "shell",
                "cmd",
                "package",
                "list",
                "packages",
                "-U",
                package_name,
            ],
            check=False,
        )

        match = re.search(
            rf"package:{re.escape(package_name)}"
            rf"\s+uid:(\d+)",
            result.stdout,
        )

        if match is None:
            raise RuntimeError(
                "没有找到游戏 UID："
                f"{package_name}"
            )

        uid = int(
            match.group(1)
        )

        self._package_uid_cache[
            package_name
        ] = uid

        return uid

    def _is_root_shell(
        self,
    ) -> bool:
        """检查 adb shell 是否拥有 ROOT。"""
        result = self.run(
            [
                "shell",
                "id",
                "-u",
            ],
            check=False,
        )

        return (
            result.returncode == 0
            and result.stdout.strip()
            == "0"
        )

    def _is_su_available(
        self,
    ) -> bool:
        """检查 su -c 是否可以获取 ROOT。"""
        if (
            self._su_available
            is not None
        ):
            return self._su_available

        result = self.run(
            [
                "shell",
                "su",
                "-c",
                "id -u",
            ],
            check=False,
        )

        self._su_available = (
            result.returncode == 0
            and result.stdout.strip()
            == "0"
        )

        return self._su_available

    @staticmethod
    def _quote_shell_arg(
        text: str,
    ) -> str:
        """把文本包成 shell 单引号参数。"""
        return (
            "'"
            + text.replace(
                "'",
                "'\\''",
            )
            + "'"
        )

    # =========================================================
    # 截图
    # =========================================================

    def take_screenshot(
        self,
        output_path: str | Path | None = None,
    ) -> Path:
        """截取设备画面并保存 PNG。"""
        self.ensure_device_online()

        config.ensure_directories()

        if output_path is None:
            path = (
                config.SCREENSHOT_DIR
                / config.DEFAULT_SCREENSHOT_NAME
            )
        else:
            path = Path(
                output_path
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        command = self._build_command(
            [
                "exec-out",
                "screencap",
                "-p",
            ],
            device=True,
        )

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=config.SCREENSHOT_TIMEOUT,
                check=False,
            )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "模拟器截图超时，"
                f"超过 {config.SCREENSHOT_TIMEOUT:g} 秒"
            ) from exc

        if result.returncode != 0:
            stderr = (
                result.stderr.decode(
                    "utf-8",
                    errors="replace",
                )
            )

            raise AdbCommandError(
                command=command,
                returncode=result.returncode,
                stderr=stderr,
            )

        if not result.stdout:
            raise RuntimeError(
                "ADB 截图返回了空数据"
            )

        path.write_bytes(
            result.stdout
        )

        image = self.read_image(
            path
        )

        if image.size == 0:
            raise RuntimeError(
                "截图文件没有有效内容："
                f"{path}"
            )

        return path.resolve()

    def read_screenshot(
        self,
    ) -> np.ndarray:
        """直接读取当前模拟器截图。"""
        self.ensure_device_online()

        command = self._build_command(
            [
                "exec-out",
                "screencap",
                "-p",
            ],
            device=True,
        )

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=config.SCREENSHOT_TIMEOUT,
                check=False,
            )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "模拟器截图超时，"
                f"超过 {config.SCREENSHOT_TIMEOUT:g} 秒"
            ) from exc

        if result.returncode != 0:
            stderr = (
                result.stderr.decode(
                    "utf-8",
                    errors="replace",
                )
            )

            raise AdbCommandError(
                command=command,
                returncode=result.returncode,
                stderr=stderr,
            )

        if not result.stdout:
            raise RuntimeError(
                "ADB 截图返回了空数据"
            )

        image_data = np.frombuffer(
            result.stdout,
            dtype=np.uint8,
        )

        image = cv2.imdecode(
            image_data,
            cv2.IMREAD_COLOR,
        )

        if (
            image is None
            or image.size == 0
        ):
            raise RuntimeError(
                "无法解码 ADB 返回的截图数据"
            )

        return image

    @staticmethod
    def read_image(
        path: str | Path,
    ) -> np.ndarray:
        """读取图片，兼容中文路径。"""
        image_path = Path(
            path
        )

        if not image_path.is_file():
            raise FileNotFoundError(
                "图片不存在："
                f"{image_path}"
            )

        image_data = np.fromfile(
            str(image_path),
            dtype=np.uint8,
        )

        image = cv2.imdecode(
            image_data,
            cv2.IMREAD_COLOR,
        )

        if (
            image is None
            or image.size == 0
        ):
            raise RuntimeError(
                "图片解码失败："
                f"{image_path}"
            )

        return image

    def get_screenshot_size(
        self,
    ) -> tuple[int, int]:
        """返回截图宽度和高度。"""
        image = (
            self.read_screenshot()
        )

        height, width = (
            image.shape[:2]
        )

        return width, height

    # =========================================================
    # 输入控制
    # =========================================================

    def click(
        self,
        x: int,
        y: int,
    ) -> None:
        """点击指定坐标。"""
        self.run(
            [
                "shell",
                "input",
                "tap",
                str(int(x)),
                str(int(y)),
            ]
        )

    def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 300,
    ) -> None:
        """从一个坐标滑动到另一个坐标。"""
        self.run(
            [
                "shell",
                "input",
                "swipe",
                str(int(start_x)),
                str(int(start_y)),
                str(int(end_x)),
                str(int(end_y)),
                str(int(duration_ms)),
            ]
        )

    # =========================================================
    # APP 控制
    # =========================================================

    def is_package_installed(
        self,
        package_name: str,
    ) -> bool:
        """检查应用是否安装。"""
        package_name = (
            package_name.strip()
        )

        if not package_name:
            raise ValueError(
                "应用包名不能为空"
            )

        result = self.run(
            [
                "shell",
                "pm",
                "path",
                package_name,
            ],
            check=False,
        )

        return (
            result.returncode == 0
            and bool(
                result.stdout.strip()
            )
        )

    def open_app(
        self,
        package_name: str,
    ) -> None:
        """通过包名启动游戏。"""
        package_name = (
            package_name.strip()
        )

        if not package_name:
            raise ValueError(
                "游戏包名不能为空"
            )

        args = [
            "shell",
            "monkey",
            "-p",
            package_name,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ]

        result = self.run(
            args,
            check=False,
        )

        if result.returncode != 0:
            raise AdbCommandError(
                command=self._build_command(
                    args,
                    device=True,
                ),
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

    def close_app(
        self,
        package_name: str,
    ) -> None:
        """强制关闭应用。"""
        package_name = (
            package_name.strip()
        )

        if not package_name:
            raise ValueError(
                "游戏包名不能为空"
            )

        self.run(
            [
                "shell",
                "am",
                "force-stop",
                package_name,
            ]
        )

    @staticmethod
    def delay(
        seconds: float,
    ) -> None:
        """等待指定秒数。"""
        seconds = float(
            seconds
        )

        if seconds < 0:
            raise ValueError(
                "等待时间不能小于 0"
            )

        time.sleep(
            seconds
        )