"""当前识别请求的非模态截图弹窗，仅由 Tk 主线程操作。"""
from __future__ import annotations

import base64
import time
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

import cv2

from manual_recognition import ManualFrame


SCREEN_FRACTION = .88
IMAGE_HEIGHT_FRACTION = .58
TEMPLATE_MAX_SIZE = (220, 90)
TARGET_RADIUS = 12


@dataclass(frozen=True)
class ImageTransform:
    original_width: int
    original_height: int
    display_width: int
    display_height: int

    @classmethod
    def fit(cls, image, max_width, max_height):
        height, width = image.shape[:2]
        scale = min(1., max_width / width, max_height / height)
        return cls(width, height, max(1, int(width * scale)), max(1, int(height * scale)))

    def original_point(self, x, y):
        if not (0 <= x < self.display_width and 0 <= y < self.display_height):
            raise ValueError("请点选截图范围内的目标")
        return (int(x * self.original_width / self.display_width),
                int(y * self.original_height / self.display_height))

    def display_point(self, point):
        x, y = point
        return (x * self.display_width / self.original_width,
                y * self.display_height / self.original_height)


class ManualRecognitionDialog(tk.Toplevel):
    def __init__(self, master, request, *, on_submit, on_stop, on_frame_displayed=None):
        super().__init__(master)
        self.request = request
        self._submit = on_submit
        self._stop = on_stop
        self._submitted = False
        self._destroyed = False
        self._mark_displayed = on_frame_displayed
        self.displayed_frame = ManualFrame(request.request_id, 1, request.images[0])
        self.timer_text = self.wait_progress = None
        self.photos = []
        self.canvases = []
        self.transforms = []
        self.buttons = {}
        self.title("人工识别")
        self.transient(master)
        # 不 grab、不 wait_window：原窗口停止按钮和消息刷新始终可用。
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.resizable(False, False)
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        cell = "" if request.cell is None else f" · 第{request.cell[0]+1}行 第{request.cell[1]+1}列"
        ttk.Label(frame, text=f"第{request.level}关{cell} · {request.step}").pack(anchor=tk.W)
        ttk.Label(frame, text=request.detail, wraplength=800).pack(anchor=tk.W, pady=(4, 8))
        image_row = ttk.Frame(frame)
        image_row.pack()
        max_width = int(self.winfo_screenwidth() * SCREEN_FRACTION / len(request.images)) - 24
        max_height = int(self.winfo_screenheight() * IMAGE_HEIGHT_FRACTION)
        self._image_limits = (max_width, max_height)
        for index, (label, original) in enumerate(zip(request.image_labels, request.images)):
            column = ttk.Frame(image_row)
            column.pack(side=tk.LEFT, padx=3)
            ttk.Label(column, text=label).pack()
            transform = ImageTransform.fit(original, max_width, max_height)
            photo = self._photo(original, transform)
            canvas = tk.Canvas(column, width=transform.display_width, height=transform.display_height,
                               highlightthickness=0, borderwidth=0)
            canvas.pack()
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            if request.target_point is not None:
                x, y = transform.display_point(request.target_point)
                r = TARGET_RADIUS
                canvas.create_oval(x-r, y-r, x+r, y+r, outline="#ff3030", width=2)
                canvas.create_line(x-r-5, y, x+r+5, y, fill="#ff3030", width=2)
                canvas.create_line(x, y-r-5, x, y+r+5, fill="#ff3030", width=2)
            if request.needs_position and index == 0:
                canvas.configure(cursor="crosshair")
                canvas.bind("<Button-1>", self.select_position)
            self.canvases.append(canvas)
            self.transforms.append(transform)
        if request.templates:
            templates = ttk.Frame(frame)
            templates.pack(pady=6)
            ttk.Label(templates, text="要找的模板（任一匹配）：" if len(request.templates) > 1 else "要找的模板：").pack(side=tk.LEFT)
            for template in request.templates:
                transform = ImageTransform.fit(template, *TEMPLATE_MAX_SIZE)
                ttk.Label(templates, image=self._photo(template, transform)).pack(side=tk.LEFT, padx=4)
        if request.wait_started_at is not None:
            self.timer_text = tk.StringVar(self)
            self.wait_progress = ttk.Progressbar(frame, maximum=100, mode="determinate")
            self.wait_progress.pack(fill=tk.X, pady=(8, 0))
            ttk.Label(frame, textvariable=self.timer_text).pack(anchor=tk.W)
            self.update_elapsed()
        controls = ttk.Frame(frame)
        controls.pack(pady=(8, 0))
        for value, label in request.options:
            if value == "found" and request.needs_position:
                ttk.Label(controls, text="找到：直接点击上方截图中的目标").pack(side=tk.LEFT, padx=6)
                continue
            button = ttk.Button(controls, text=label, command=lambda choice=value: self.answer(choice))
            button.pack(side=tk.LEFT, padx=4)
            self.buttons[value] = button
        self.error = tk.StringVar(self)
        ttk.Label(frame, textvariable=self.error, foreground="#b02a37").pack(anchor=tk.W)
        self.lift()

    def _photo(self, original, transform, *, retain=True):
        # 缩放发生在新图上；目标标记是 Canvas 图层，原截图完全保留。
        display = cv2.resize(original, (transform.display_width, transform.display_height))
        ok, png = cv2.imencode(".png", display)
        if not ok:
            raise ValueError("本次截图无法展示")
        photo = tk.PhotoImage(master=self, data=base64.b64encode(png).decode("ascii"))
        if retain:
            self.photos.append(photo)
        return photo

    def update_elapsed(self):
        if self._destroyed or self.timer_text is None:
            return
        elapsed = max(0., time.monotonic() - self.request.wait_started_at)
        reference = self.request.reference_timeout
        self.wait_progress["value"] = min(100., elapsed / reference * 100.) if reference > 0 else 100.
        text = f"已等待{elapsed:.1f}秒／参考{reference:g}秒"
        if elapsed >= reference:
            text += " · 已达到参考时长，仍在等待人工判断"
        self.timer_text.set(text)

    def update_frame(self, frame):
        if (self._destroyed or self._submitted or self.request.wait_started_at is None
                or frame.request_id != self.request.request_id or frame.number <= self.displayed_frame.number):
            return
        transform = ImageTransform.fit(frame.image, *self._image_limits)
        photo = self._photo(frame.image, transform, retain=False)
        if self._mark_displayed is not None and not self._mark_displayed(frame):
            return
        canvas = self.canvases[0]
        canvas.configure(width=transform.display_width, height=transform.display_height)
        canvas.itemconfigure(canvas.find_all()[0], image=photo)
        self.photos[0] = photo  # 主线程立即释放上一张 Tk 图片。
        self.transforms[0] = transform
        self.displayed_frame = frame

    def select_position(self, event):
        if self._destroyed or self._submitted:
            return
        try:
            point = self.transforms[0].original_point(event.x, event.y)
        except ValueError as exc:
            self.error.set(str(exc))
            return
        self.answer("found", coordinates=point)

    def answer(self, value, *, coordinates=()):
        if self._submitted or self._destroyed:
            return
        try:
            self._submit(self.request.request_id, value=value, coordinates=coordinates,
                         frame_id=self.displayed_frame.number)
        except ValueError as exc:
            self.error.set(str(exc))
            return
        self._submitted = True
        self.destroy()

    def cancel(self):
        if self._destroyed:
            return
        self._stop()
        if self.winfo_exists():
            self.destroy()

    def destroy(self):
        # Tk 图片与变量必须在主线程释放，不能留给后台触发的循环垃圾回收。
        if self._destroyed:
            return
        self._destroyed = True
        super().destroy()
        self.photos.clear()
        self.error = None
        self.canvases.clear()
        self.buttons.clear()
        self._submit = self._stop = self._mark_displayed = None
        self.displayed_frame = self.request = None
        self.timer_text = self.wait_progress = None
