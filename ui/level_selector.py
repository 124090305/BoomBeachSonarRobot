from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


LEVEL_CHOICES = tuple(range(1, 12))
LEVEL_PLUS_START = 11


def format_level_label(level: int) -> str:
    """把内部真实关卡号映射为 UI 显示文字。"""
    actual_level = int(level)
    if actual_level <= 0:
        raise ValueError("关卡编号必须大于 0")
    if actual_level >= LEVEL_PLUS_START:
        return "第11关+"
    return f"第{actual_level}关"


def level_from_label(label: str) -> int:
    """把选择器文字转换为起始关卡号。"""
    text = str(label).strip()
    if text == "第11关+":
        return LEVEL_PLUS_START
    if text.startswith("第") and text.endswith("关"):
        level = int(text[1:-1])
        if 1 <= level < LEVEL_PLUS_START:
            return level
    raise ValueError(f"无效关卡选项：{label}")


class LevelSelector(ttk.Frame):
    """带独立滚动条的关卡下拉选择器。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        current_level: int,
        on_select: Callable[[int], None],
        visible_rows: int = 6,
    ) -> None:
        super().__init__(master)
        if visible_rows <= 0:
            raise ValueError("visible_rows 必须大于 0")

        self._on_select = on_select
        self._visible_rows = int(visible_rows)
        self._enabled = True
        self._popup: tk.Toplevel | None = None
        self._listbox: tk.Listbox | None = None
        self._scrollbar: ttk.Scrollbar | None = None
        self._level = int(current_level)
        self._display_var = tk.StringVar(
            master=self,
            value=format_level_label(self._level),
        )

        self._entry = ttk.Entry(
            self,
            textvariable=self._display_var,
            width=9,
            state="readonly",
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._button = ttk.Button(
            self,
            text="▼",
            width=3,
            command=self.open_popup,
        )
        self._button.pack(side=tk.LEFT)
        self._entry.bind("<Button-1>", self._open_from_event)
        self._entry.bind("<Down>", self._open_from_event)
        self._entry.bind("<Return>", self._open_from_event)

    @property
    def current_level(self) -> int:
        return self._level

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def display_text(self) -> str:
        return self._display_var.get()

    def set_level(self, level: int) -> None:
        self._level = int(level)
        self._display_var.set(format_level_label(self._level))
        self.close_popup()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        state = ["!disabled"] if self._enabled else ["disabled"]
        self._entry.state(state)
        self._button.state(state)
        if not self._enabled:
            self.close_popup()

    def _open_from_event(self, _event: tk.Event) -> str:
        self.open_popup()
        return "break"

    def open_popup(self) -> None:
        if not self._enabled or self._popup is not None:
            return

        popup = tk.Toplevel(self)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.transient(self.winfo_toplevel())

        body = ttk.Frame(popup, relief=tk.SOLID, borderwidth=1)
        body.pack(fill=tk.BOTH, expand=True)
        listbox = tk.Listbox(
            body,
            height=self._visible_rows,
            exportselection=False,
            activestyle="dotbox",
        )
        scrollbar = ttk.Scrollbar(
            body,
            orient=tk.VERTICAL,
            command=listbox.yview,
        )
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for level in LEVEL_CHOICES:
            listbox.insert(tk.END, format_level_label(level))

        selected = min(self._level, LEVEL_PLUS_START) - 1
        listbox.selection_set(selected)
        listbox.activate(selected)
        listbox.see(selected)

        listbox.bind("<ButtonRelease-1>", self._confirm_mouse_selection)
        listbox.bind("<Return>", self._confirm_keyboard_selection)
        listbox.bind("<Escape>", self._close_from_event)
        listbox.bind("<Up>", lambda event: self._move_selection(-1))
        listbox.bind("<Down>", lambda event: self._move_selection(1))
        popup.bind("<Escape>", self._close_from_event)
        for widget in (popup, body, listbox, scrollbar):
            widget.bind("<MouseWheel>", self._scroll_popup, add="+")
            widget.bind("<Button-4>", self._scroll_popup, add="+")
            widget.bind("<Button-5>", self._scroll_popup, add="+")

        self._popup = popup
        self._listbox = listbox
        self._scrollbar = scrollbar
        self.update_idletasks()
        popup.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        width = max(self.winfo_width(), popup.winfo_reqwidth())
        height = popup.winfo_reqheight()
        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.deiconify()
        popup.grab_set()
        listbox.focus_set()

    def close_popup(self) -> None:
        popup = self._popup
        self._popup = None
        self._listbox = None
        self._scrollbar = None
        if popup is None:
            return
        try:
            popup.grab_release()
        except tk.TclError:
            pass
        popup.destroy()

    def _move_selection(self, delta: int) -> str:
        listbox = self._listbox
        if listbox is None:
            return "break"
        selection = listbox.curselection()
        current = selection[0] if selection else 0
        target = max(0, min(listbox.size() - 1, current + int(delta)))
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(target)
        listbox.activate(target)
        listbox.see(target)
        return "break"

    def _confirm_mouse_selection(self, event: tk.Event) -> str:
        listbox = self._listbox
        if listbox is None:
            return "break"
        index = listbox.nearest(event.y)
        bounds = listbox.bbox(index)
        if bounds is None or not (bounds[1] <= event.y <= bounds[1] + bounds[3]):
            return "break"
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(index)
        return self._confirm_selection()

    def _confirm_keyboard_selection(self, _event: tk.Event) -> str:
        return self._confirm_selection()

    def _confirm_selection(self) -> str:
        listbox = self._listbox
        if listbox is None:
            return "break"
        selection = listbox.curselection()
        if not selection:
            return "break"
        level = level_from_label(listbox.get(selection[0]))
        self.close_popup()
        self._on_select(level)
        return "break"

    def _close_from_event(self, _event: tk.Event) -> str:
        self.close_popup()
        return "break"

    def _scroll_popup(self, event: tk.Event) -> str:
        listbox = self._listbox
        if listbox is None:
            return "break"
        if getattr(event, "num", None) == 4:
            units = -1
        elif getattr(event, "num", None) == 5:
            units = 1
        else:
            delta = int(getattr(event, "delta", 0))
            units = -1 if delta > 0 else 1
        listbox.yview_scroll(units, "units")
        return "break"


__all__ = [
    "LEVEL_CHOICES",
    "LEVEL_PLUS_START",
    "LevelSelector",
    "format_level_label",
    "level_from_label",
]
