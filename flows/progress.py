from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sonar import Cell


@dataclass(frozen=True)
class AutoProbeStatusEvent:
    """自动流程发给外层的事实补丁，不包含 GUI 文案。"""

    loop_state: str | None = None
    phase: str | None = None
    page_state: str | None = None
    device_online: bool | None = None
    weak_network_enabled: bool | None = None
    reject_network_enabled: bool | None = None
    target_mode: str | None = None
    target_cell: Cell | None = None
    round_index: int | None = None
    recovery_attempt: int | None = None


ProgressCallback = Callable[[AutoProbeStatusEvent], None]


def emit_progress(
    callback: ProgressCallback | None,
    **facts: object,
) -> None:
    """存在回调时发送一份不可变事实补丁。"""
    if callback is None:
        return

    callback(
        AutoProbeStatusEvent(**facts)
    )


__all__ = [
    "AutoProbeStatusEvent",
    "ProgressCallback",
    "emit_progress",
]
