"""记录一次暂停到恢复之间是否已有成功的人工校准。"""
from __future__ import annotations

from enum import Enum
from threading import Lock


class ResumeCalibrationDecision(str, Enum):
    NONE = "none"
    SKIP_MANUAL = "skip_manual"
    AUTO = "auto"


class BoardSyncState:
    """线程安全的一次性恢复判定；不保存棋盘内容。"""

    def __init__(self) -> None:
        self._lock = Lock()
        self._paused = False
        self._manual_applied = False
        self._review_token = None

    def mark_requested_pause(self) -> None:
        with self._lock:
            self._paused = True
            self._manual_applied = False
            self._review_token = None

    def mark_manual_applied(self, token=None) -> None:
        with self._lock:
            if self._paused:
                self._manual_applied = True
                self._review_token = token

    def resume_decision(self, token=None) -> ResumeCalibrationDecision:
        with self._lock:
            if not self._paused:
                return ResumeCalibrationDecision.NONE
            if self._manual_applied and self._review_token == token:
                return ResumeCalibrationDecision.SKIP_MANUAL
            return ResumeCalibrationDecision.AUTO

    def mark_resume_succeeded(self) -> None:
        with self._lock:
            self._paused = False
            self._manual_applied = False
            self._review_token = None

    def invalidate(self) -> None:
        """对象/设备改变使旧审核失效，保留暂停后的校准义务。"""
        with self._lock:
            self._manual_applied = False
            self._review_token = None


__all__ = ["BoardSyncState", "ResumeCalibrationDecision"]
