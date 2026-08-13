from __future__ import annotations

import time
from threading import Event

import config


class StopRequestedError(Exception):
    """自动流程在安全可中断点收到用户停止请求。"""


def raise_if_stop_requested(
    stop_event: Event | None,
) -> None:
    """在动作边界检查用户停止请求。"""
    if stop_event is not None and stop_event.is_set():
        raise StopRequestedError(
            "用户已请求停止自动探测"
        )


def interruptible_wait(
    seconds: float,
    stop_event: Event | None,
    *,
    poll_interval: float = config.STOP_POLL_INTERVAL,
) -> None:
    """等待期间按短间隔检查停止请求。"""
    seconds = float(seconds)
    poll_interval = float(poll_interval)

    if seconds < 0:
        raise ValueError(
            "等待时间不能小于 0"
        )

    if poll_interval <= 0:
        raise ValueError(
            "停止检查间隔必须大于 0"
        )

    raise_if_stop_requested(
        stop_event
    )

    if seconds == 0:
        return

    deadline = time.monotonic() + seconds

    while True:
        remaining = deadline - time.monotonic()

        if remaining <= 0:
            return

        wait_seconds = min(
            poll_interval,
            remaining,
        )

        if stop_event is None:
            time.sleep(wait_seconds)
            continue

        if stop_event.wait(wait_seconds):
            raise StopRequestedError(
                "用户已请求停止自动探测"
            )


__all__ = [
    "StopRequestedError",
    "interruptible_wait",
    "raise_if_stop_requested",
]
