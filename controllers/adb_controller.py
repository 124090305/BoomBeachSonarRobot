from __future__ import annotations

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
            raise ValueError("ADB 设备编号不能为空")

        self.adb_path = self._find_adb(adb_path)

    @staticmethod
    def _find_adb(
        adb_path: str | Path | None,
    ) -> Path:
        """
        查找 adb.exe。

        查找顺序：
        1. 创建控制器时传入的路径
        2. config.py 中配置的路径
        3. 系统 PATH
        """
        candidates: list[Path] = []

        if adb_path is not None:
            candidates.append(Path(adb_path))

        candidates.append(config.ADB_PATH)

        for candidate in candidates:
            candidate = candidate.expanduser()

            if candidate.is_file():
                return candidate.resolve()

        path_result = shutil.which("adb")

        if path_result:
            return Path(path_result).resolve()

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
        """组装完整的 ADB 命令。"""
        command = [str(self.adb_path)]

        if device:
            command.extend(
                ["-s", self.serial]
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
                f"ADB 命令超时：{' '.join(command)}"
            ) from exc

        if check and result.returncode != 0:
            raise AdbCommandError(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        return result

    def list_devices(self) -> dict[str, str]:
        """
        获取 ADB 设备列表。

        返回示例：
        {
            "emulator-5554": "device"
        }
        """
        result = self.run(
            ["devices"],
            device=False,
        )

        devices: dict[str, str] = {}

        lines = result.stdout.splitlines()

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

    def ensure_device_online(self) -> None:
        """确认目标设备在线并且状态正常。"""
        devices = self.list_devices()

        state = devices.get(self.serial)

        if state == "device":
            return

        if state is None:
            raise RuntimeError(
                f"没有发现设备 {self.serial}。"
                "请先启动模拟器，并执行 adb devices 检查。"
            )

        raise RuntimeError(
            f"设备 {self.serial} 当前状态为 {state}，暂时不可用"
        )

    def take_screenshot(
        self,
        output_path: str | Path | None = None,
    ) -> Path:
        """截取设备画面并保存为 PNG 文件。"""
        self.ensure_device_online()
        config.ensure_directories()

        if output_path is None:
            path = (
                config.SCREENSHOT_DIR
                / config.DEFAULT_SCREENSHOT_NAME
            )
        else:
            path = Path(output_path)

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
            stderr = result.stderr.decode(
                "utf-8",
                errors="replace",
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

        path.write_bytes(result.stdout)

        # 保存后立即读取一次，确认 PNG 有效。
        image = self.read_image(path)

        if image.size == 0:
            raise RuntimeError(
                f"截图文件没有有效内容：{path}"
            )

        return path.resolve()

    def read_screenshot(self) -> np.ndarray:
        """
        直接获取模拟器截图。

        返回 OpenCV 图片，不保存文件。
        """
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
            stderr = result.stderr.decode(
                "utf-8",
                errors="replace",
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

        if image is None or image.size == 0:
            raise RuntimeError(
                "无法解码 ADB 返回的截图数据"
            )

        return image

    @staticmethod
    def read_image(
        path: str | Path,
    ) -> np.ndarray:
        """读取图片，兼容中文文件路径。"""
        image_path = Path(path)

        if not image_path.is_file():
            raise FileNotFoundError(
                f"图片不存在：{image_path}"
            )

        image_data = np.fromfile(
            str(image_path),
            dtype=np.uint8,
        )

        image = cv2.imdecode(
            image_data,
            cv2.IMREAD_COLOR,
        )

        if image is None or image.size == 0:
            raise RuntimeError(
                f"图片解码失败：{image_path}"
            )

        return image

    def get_screenshot_size(
        self,
    ) -> tuple[int, int]:
        """返回实际截图的宽度和高度。"""
        image = self.read_screenshot()

        height, width = image.shape[:2]

        return width, height

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

    def is_package_installed(
        self,
        package_name: str,
    ) -> bool:
        """检查设备中是否安装了指定应用。"""
        package_name = package_name.strip()

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
            and bool(result.stdout.strip())
        )

    def open_app(
        self,
        package_name: str,
    ) -> None:
        """通过应用包名启动游戏。"""
        package_name = package_name.strip()

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
        """通过应用包名强制关闭游戏。"""
        package_name = package_name.strip()

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
        seconds = float(seconds)

        if seconds < 0:
            raise ValueError(
                "等待时间不能小于 0"
            )

        time.sleep(seconds)