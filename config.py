from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

# 可以通过环境变量临时覆盖：
# $env:ADB_PATH = "D:\LDPlayer\adb.exe"
# $env:ADB_SERIAL = "emulator-5554"
ADB_PATH = Path(os.getenv("ADB_PATH", r"D:\LDPlayer\adb.exe"))
ADB_SERIAL = os.getenv("ADB_SERIAL", "emulator-5554")

# 国际服默认包名。
# 国服包名不同，需要根据实际安装包修改。
GAME_PACKAGE_NAME = os.getenv(
    "GAME_PACKAGE_NAME",
    "com.supercell.boombeach",
)

RESOURCE_DIR = PROJECT_ROOT / "resources"
TEMPLATE_DIR = RESOURCE_DIR / "templates"
SCREENSHOT_DIR = RESOURCE_DIR / "screenshots"

DEFAULT_SCREENSHOT_NAME = "latest.png"

ADB_COMMAND_TIMEOUT = 15.0
SCREENSHOT_TIMEOUT = 15.0

GAME_RESTART_DELAY = 10.0
DEFAULT_MATCH_THRESHOLD = 0.85


def ensure_directories() -> None:
    """创建程序运行需要的目录。"""
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)