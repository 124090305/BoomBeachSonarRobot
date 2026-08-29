from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ButtonState(str, Enum):
    """受后台结果驱动的控制按钮状态。"""

    READY = "ready"
    BUSY = "busy"
    ACTIVE = "active"
    LOCKED = "locked"
    ERROR = "error"


class ConfigurableButton(Protocol):
    """Tk 按钮及测试替身共同使用的最小接口。"""

    def configure(self, **kwargs: object) -> object:
        ...


@dataclass(frozen=True)
class ButtonLabels:
    """一个按钮在各状态下显示的文案。"""

    ready: str
    active: str
    busy_on: str
    busy_off: str
    locked: str
    error: str


_BUTTON_COLORS = {
    ButtonState.READY: "#2f9e44",
    ButtonState.BUSY: "#777777",
    ButtonState.ACTIVE: "#c92a2a",
    ButtonState.LOCKED: "#6c757d",
    ButtonState.ERROR: "#b02a37",
}


class StatefulButton:
    """统一管理 Toggle / Action 按钮的文本、可点性与实体按下效果。"""

    def __init__(
        self,
        button: ConfigurableButton,
        labels: ButtonLabels,
        *,
        is_toggle: bool,
    ) -> None:
        self.button = button
        self.labels = labels
        self.is_toggle = is_toggle
        self.state = ButtonState.READY
        self.active = False
        self._render()

    def begin(self) -> bool | None:
        """开始一次用户操作；返回 Toggle 的目标状态，Action 返回 True。"""
        if self.state in {
            ButtonState.BUSY,
            ButtonState.LOCKED,
            ButtonState.ERROR,
        }:
            return None

        target = not self.active if self.is_toggle else True
        self.state = ButtonState.BUSY
        self._busy_target = target
        self._busy_message = None
        self._render()
        return target

    def set_busy_message(self, message: str) -> None:
        """显示无副作用的后台状态读取过程。"""
        self.state = ButtonState.BUSY
        self._busy_message = str(message)
        self._render()

    def complete_toggle(self, active: bool) -> None:
        """网络控制已完成并复核后，按真实状态显示。"""
        self.active = bool(active)
        self.state = (
            ButtonState.ACTIVE
            if self.active
            else ButtonState.READY
        )
        self._render()

    def complete_action(self) -> None:
        """一次性操作完整返回后恢复可用状态。"""
        self.active = False
        self.state = ButtonState.READY
        self._render()

    def set_locked(self, locked: bool) -> None:
        """锁定期间保留真实 active 值，解锁后立即恢复对应外观。"""
        if locked:
            self.state = ButtonState.LOCKED
        else:
            self.state = (
                ButtonState.ACTIVE
                if self.active
                else ButtonState.READY
            )
        self._render()

    def set_error(self) -> None:
        """真实状态无法复核时，明确显示错误而不猜测 Toggle 状态。"""
        self.state = ButtonState.ERROR
        self._render()

    def _render(self) -> None:
        if self.state == ButtonState.BUSY:
            text = getattr(self, "_busy_message", None)
            if text is None:
                target = getattr(self, "_busy_target", True)
                text = (
                    self.labels.busy_on
                    if target
                    else self.labels.busy_off
                )
        elif self.state == ButtonState.ACTIVE:
            text = self.labels.active
        elif self.state == ButtonState.LOCKED:
            text = self.labels.locked
        elif self.state == ButtonState.ERROR:
            text = self.labels.error
        else:
            text = self.labels.ready

        disabled = self.state in {
            ButtonState.BUSY,
            ButtonState.LOCKED,
            ButtonState.ERROR,
        }
        pressed = self.state in {
            ButtonState.BUSY,
            ButtonState.LOCKED,
        }

        self.button.configure(
            text=text,
            state="disabled" if disabled else "normal",
            background=_BUTTON_COLORS[self.state],
            activebackground=_BUTTON_COLORS[self.state],
            foreground="white",
            activeforeground="white",
            disabledforeground="#eeeeee",
            relief="sunken" if pressed else "raised",
            borderwidth=1 if pressed else 3,
        )


__all__ = [
    "ButtonLabels",
    "ButtonState",
    "StatefulButton",
]
