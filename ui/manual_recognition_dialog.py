"""复用的人工测试窗口；Tk 只展示后台结果，选择与确认分离。"""
from __future__ import annotations

import base64
import json
import math
import time
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import cv2

from manual_recognition import ManualFrame
from manual_prompts import preview

SCREEN_FRACTION = .90
DEFAULT_SIZE = (980, 720)
MIN_SIZE = (480, 360)
TEMPLATE_MAX_SIZE = (220, 90)
TARGET_RADIUS = 12
RESIZE_DELAY_MS = 80

@dataclass(frozen=True)
class ImageTransform:
    original_width: int
    original_height: int
    display_width: int
    display_height: int

    @classmethod
    def fit(cls, image, max_width, max_height):
        height, width = image.shape[:2]
        scale = min(1., max(1, max_width) / width, max(1, max_height) / height)
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


def number(value):
    return f"{value:.2f}" if value is not None and math.isfinite(value) else "—"


class ManualRecognitionDialog(tk.Toplevel):
    def __init__(self, master, request, *, on_submit, on_stop, on_frame_displayed=None):
        super().__init__(master)
        self._submit, self._stop, self._mark_displayed = on_submit, on_stop, on_frame_displayed
        self._destroyed = self._submitted = False
        self._resize_after = None
        self.request = self.displayed_frame = None
        self.photos, self.canvases, self.transforms = [], [], []
        self._detail_photos = []
        self._point = None
        self._details_open = False
        self.title("人工测试模式")
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        # 不 grab、不 wait_window，主窗口停止按钮持续可用。
        width = min(DEFAULT_SIZE[0], int(self.winfo_screenwidth() * SCREEN_FRACTION))
        height = min(DEFAULT_SIZE[1], int(self.winfo_screenheight() * SCREEN_FRACTION))
        self.geometry(f"{width}x{height}")
        self._initial_image_area = (width - 20, height - 210)
        self.minsize(min(MIN_SIZE[0], width), min(MIN_SIZE[1], height))
        self.resizable(True, True)
        self.body = ttk.Frame(self, padding=10)
        self.body.pack(fill=tk.BOTH, expand=True)
        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(1, weight=1)
        header = ttk.Frame(self.body)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        header.columnconfigure(0, weight=1)
        self.title_text, self.level_text = tk.StringVar(self), tk.StringVar(self)
        self.title_label = ttk.Label(header, textvariable=self.title_text, font=("Microsoft YaHei UI", 11, "bold"))
        self.title_label.grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.level_text).grid(row=0, column=1, sticky="e")
        self.image_row = ttk.Frame(self.body)
        self.image_row.pack_propagate(False)
        self.image_row.grid(row=1, column=0, sticky="nsew")
        self.image_row.bind("<Configure>", self._schedule_resize)
        self.expect_text, self.reference_text, self.action_text = (tk.StringVar(self) for _ in range(3))
        info = ttk.Frame(self.body)
        info.grid(row=2, column=0, sticky="ew", pady=7)
        info.columnconfigure(1, weight=1)
        ttk.Label(info, text="期望：").grid(row=0, column=0, sticky="nw")
        self.expect_label = ttk.Label(info, textvariable=self.expect_text)
        self.expect_label.grid(row=0, column=1, sticky="ew")
        ttk.Label(info, text="识别：").grid(row=1, column=0, sticky="nw", pady=4)
        self.reference_label = ttk.Label(info, textvariable=self.reference_text)
        self.reference_label.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(info, text="判断：").grid(row=2, column=0, sticky="nw")
        choices = ttk.Frame(info)
        choices.grid(row=2, column=1, sticky="ew")
        choices.columnconfigure(1, weight=1)
        self.choice_var = tk.StringVar(self)
        self.choice = ttk.Combobox(choices, textvariable=self.choice_var, state="readonly", width=18)
        self.choice.grid(row=0, column=0, sticky="nw")
        self.choice.bind("<<ComboboxSelected>>", self.selection_changed)
        self.action_label = ttk.Label(choices, textvariable=self.action_text)
        self.action_label.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.details = ttk.Notebook(self.body, height=150)
        self.assumed_var = tk.BooleanVar(self, False)
        self.use_auto_var = tk.BooleanVar(self, True)
        bar = ttk.Frame(self.body)
        bar.grid(row=4, column=0, sticky="ew")
        bar.columnconfigure(2, weight=1)
        self.confirm_button = ttk.Button(bar, text="确认继续", command=self.confirm)
        self.confirm_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(bar, text="停止", command=self.cancel)
        self.stop_button.grid(row=0, column=1)
        self.timer_text = tk.StringVar(self)
        self.timer_label = ttk.Label(bar, textvariable=self.timer_text)
        self.timer_label.grid(row=0, column=2, sticky="e", padx=8)
        self.details_button = ttk.Button(bar, text="详情 ▸", command=self.toggle_details, width=8)
        self.details_button.grid(row=0, column=3)
        self.wait_progress = ttk.Progressbar(self.body, maximum=100, mode="determinate")
        self.wait_progress.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        self.buttons = {"confirm": self.confirm_button, "stop": self.stop_button}
        self.error = self.action_text
        self.set_request(request)
        self.lift()

    def set_request(self, request):
        """保留窗口、位置、控件和尺寸，只替换本次内容。"""
        if self._destroyed or (self.request is request):
            return
        self.request = request
        self._submitted = False
        self._point = None
        self.assumed_var.set(False)
        self.use_auto_var.set(True)
        self.choice.configure(values=[label for _, label in request.options], state="readonly")
        self.choice_var.set("请选择")
        self.confirm_button.state(["!disabled"])
        self.title_text.set(request.step)
        self.level_text.set(f"第{request.level}关")
        target = "" if request.cell is None else f" · 第{request.cell[0]+1}行 第{request.cell[1]+1}列"
        self.expect_text.set(request.detail + target)
        self.displayed_frame = ManualFrame(request.request_id, 1, request.images[0], request.reference)
        if self._mark_displayed is not None:
            self._mark_displayed(self.displayed_frame)
        self._render_images()
        self._update_reference()
        self.selection_changed()
        self.update_elapsed()
        if self._details_open:
            self._render_details()

    def selected_value(self):
        return next((v for v, label in self.request.options if label == self.choice_var.get()), None)

    def select_choice(self, value):
        if not self._submitted and not self._destroyed:
            self.choice_var.set(dict(self.request.options).get(value, "请选择"))
            self.selection_changed()

    def selection_changed(self, _event=None):
        if self._submitted or self._destroyed:
            return
        value = self.selected_value()
        text = preview(self.request, value)
        if value == "found" and self.request.needs_position:
            point = self._chosen_point()
            if point is None:
                text = "请先在当前截图点选目标；" + text
            else:
                origin = "蓝色自动候选" if self.use_auto_var.get() else "橙色人工点选"
                text = f"使用{origin}{point}；" + text
        self.action_text.set("→ " + text)

    def _chosen_point(self):
        if self.use_auto_var.get():
            ref = self.displayed_frame.reference
            return ref.point if ref is not None and ref.value == "found" else None
        return self._point

    def _schedule_resize(self, _event=None):
        if self._destroyed:
            return
        if self._resize_after is not None:
            self.after_cancel(self._resize_after)
        self._resize_after = self.after(RESIZE_DELAY_MS, self._resize)

    def _resize(self):
        self._resize_after = None
        if self._destroyed:
            return
        width = max(300, self.body.winfo_width())
        self.title_label.configure(wraplength=max(220, width - 110))
        self.expect_label.configure(wraplength=width - 65)
        self.reference_label.configure(wraplength=width - 65)
        self.action_label.configure(wraplength=max(120, width - 255))
        self.timer_label.configure(wraplength=max(120, width - 270))
        self._render_images()

    def _photo(self, original, transform):
        display = cv2.resize(original, (transform.display_width, transform.display_height))
        ok, png = cv2.imencode(".png", display)
        if not ok:
            raise ValueError("本次截图无法展示")
        return tk.PhotoImage(master=self, data=base64.b64encode(png).decode("ascii"))

    def _render_images(self):
        if self.request is None or self._destroyed:
            return
        images = (self.displayed_frame.image,) + self.request.images[1:]
        if len(self.canvases) != len(images):
            for child in self.image_row.winfo_children():
                child.destroy()
            self.canvases.clear()
            for i in range(len(images)):
                column = ttk.Frame(self.image_row)
                column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
                ttk.Label(column, text=self.request.image_labels[i]).pack()
                canvas = tk.Canvas(column, highlightthickness=0, borderwidth=0, background="#f1f3f5")
                canvas.pack()
                canvas.bind("<Button-1>", self.select_position if i == 0 else lambda e: None)
                self.canvases.append(canvas)
        else:
            for col, label in zip(self.image_row.winfo_children(), self.request.image_labels):
                col.winfo_children()[0].configure(text=label)
        area_width, area_height = self.image_row.winfo_width(), self.image_row.winfo_height()
        if area_width <= 1 or area_height <= 1:
            area_width, area_height = self._initial_image_area
        width = max(1, (area_width - 18) // len(images))
        height = max(50, area_height - 24)
        self._image_limits = (width, height)
        photos, transforms = [], []
        for i, (canvas, original) in enumerate(zip(self.canvases, images)):
            transform = ImageTransform.fit(original, width, height)
            photo = self._photo(original, transform)
            canvas.configure(width=transform.display_width, height=transform.display_height,
                             cursor="crosshair" if i == 0 and self.request.needs_position else "")
            canvas.delete("all")
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            if self.request.target_point is not None:
                self._mark(canvas, transform, self.request.target_point, "#e63b35")
            if i == 0 and self.request.needs_position:
                ref = self.displayed_frame.reference
                if ref is not None and ref.point is not None:
                    self._mark(canvas, transform, ref.point, "#1673ce")
                if self._point is not None:
                    self._mark(canvas, transform, self._point, "#d87500")
            photos.append(photo)
            transforms.append(transform)
        self.photos, self.transforms = photos, transforms

    @staticmethod
    def _mark(canvas, transform, point, color):
        x, y = transform.display_point(point)
        r = TARGET_RADIUS
        canvas.create_oval(x-r, y-r, x+r, y+r, outline=color, width=2)
        canvas.create_line(x-r-4, y, x+r+4, y, fill=color, width=2)
        canvas.create_line(x, y-r-4, x, y+r+4, fill=color, width=2)

    def _update_reference(self):
        ref = self.displayed_frame.reference
        if ref is None:
            self.reference_text.set("参考不可用｜评分 —")
            return
        label = dict(self.request.options).get(ref.value, {"sunk": "击沉候选", "unavailable": "参考不可用"}.get(ref.value, ref.value))
        if ref.details.get("sunk_candidate") and ref.value == "hit":
            label += "（击沉候选）"
        text = f"{label}｜{ref.metric}{number(ref.score)}"
        if ref.threshold is not None:
            text += f"／门槛{number(ref.threshold)}"
        if self.request.extra_images:
            text += "（含补帧，见详情）"
        self.reference_text.set(text)

    def update_elapsed(self):
        if self._destroyed or self.request is None:
            return
        if self._submitted:
            self.timer_text.set("已提交 · 等待下一次判断")
            return
        if self.request.wait_started_at is None:
            self.timer_text.set("单次判断 · 等待人工确认")
            self.wait_progress["value"] = 0
            return
        elapsed = max(0., time.monotonic() - self.request.wait_started_at)
        reference = self.request.reference_timeout
        self.wait_progress["value"] = min(100., elapsed / reference * 100.) if reference > 0 else 100.
        text = f"参考等待 {elapsed:.1f}/{reference:g} 秒"
        if elapsed >= reference:
            text += " · 仍在等待人工判断"
        self.timer_text.set(text)

    def update_frame(self, frame):
        if (self._destroyed or self._submitted or self.request.wait_started_at is None
                or frame.request_id != self.request.request_id or frame.number <= self.displayed_frame.number):
            return
        if self._mark_displayed is not None and not self._mark_displayed(frame):
            return
        self.displayed_frame = frame
        self._point = None  # 人工点选不能跨帧复用；下拉选择仍保留。
        self._render_images()
        self._update_reference()
        self.selection_changed()
        if self._details_open:
            self._render_details()

    def select_position(self, event):
        if self._destroyed or self._submitted or not self.request.needs_position:
            return
        try:
            self._point = self.transforms[0].original_point(event.x, event.y)
        except ValueError as exc:
            self.action_text.set(str(exc))
            return
        self.use_auto_var.set(False)
        self._render_images()
        self.selection_changed()  # 点图只定位，不代选答案、不提交。

    def confirm(self):
        if self._submitted or self._destroyed:
            return
        value = self.selected_value()
        if value is None:
            self.action_text.set("请先选择本次判断")
            return
        point = self._chosen_point() if self.request.needs_position and value == "found" else ()
        if point is None:
            self.action_text.set("当前帧没有可用位置，请重新点图，或在详情中选择使用自动候选")
            return
        try:
            self._submit(self.request.request_id, value=value, coordinates=point,
                         frame_id=self.displayed_frame.number,
                         basis="assumed" if self.assumed_var.get() else "observed")
        except ValueError as exc:
            self.action_text.set(str(exc))
            return
        self._submitted = True
        self.confirm_button.state(["disabled"])
        self.choice.configure(state="disabled")
        self.action_text.set("已提交，后台正在接回原流程")
        self.update_elapsed()
        if self._details_open:
            self._render_details()

    def show_action(self, request_id, text):
        if not self._destroyed and self._submitted and self.request.request_id == request_id:
            self.action_text.set(text)

    def toggle_details(self):
        self._details_open = not self._details_open
        if self._details_open:
            self._render_details()
            self.details.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        else:
            self.details.grid_remove()
        self.details_button.configure(text="详情 ▾" if self._details_open else "详情 ▸")

    def _render_details(self):
        selected = self.details.index(self.details.select()) if self.details.select() else 0
        for child in self.details.winfo_children():
            child.destroy()
        self._detail_photos.clear()
        info = ttk.Frame(self.details)
        self.details.add(info, text="依据与记录")
        options = ttk.Frame(info)
        options.pack(fill=tk.X)
        state = "disabled" if self._submitted else "normal"
        ttk.Checkbutton(options, text="本次答案为假定（测试）", variable=self.assumed_var, state=state).pack(side=tk.LEFT)
        if self.request.needs_position:
            ttk.Checkbutton(options, text="使用本帧蓝色自动候选位置", variable=self.use_auto_var,
                            command=self.selection_changed, state=state).pack(side=tk.LEFT)
        text = ScrolledText(info, height=5, wrap=tk.WORD, font=("Microsoft YaHei UI", 9))
        text.pack(fill=tk.BOTH, expand=True)
        ref = self.displayed_frame.reference
        record = ref.to_record() if ref else None
        text.insert("1.0", f"代码：{self.request.location}\n步骤键：{self.request.prompt_key}\n"
                    f"请求：{self.request.request_id}，显示帧：{self.displayed_frame.number}\n"
                    "自动结果仅供参考；相似度和置信度均非正确率。\n"
                    + json.dumps(record, ensure_ascii=False, indent=2)
                    + "\n近期已提交：\n" + "\n".join(self.request.history))
        text.configure(state="disabled")
        for title, images, limit in (("模板原图", self.request.templates, TEMPLATE_MAX_SIZE),
                                      ("参与判断的补帧", self.request.extra_images, (650, 125))):
            if not images:
                continue
            frame = ttk.Frame(self.details)
            self.details.add(frame, text=title)
            for original in images:
                transform = ImageTransform.fit(original, *limit)
                photo = self._photo(original, transform)
                self._detail_photos.append(photo)
                canvas = tk.Canvas(frame, width=transform.display_width, height=transform.display_height,
                                   highlightthickness=0)
                canvas.pack(side=tk.LEFT)
                canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                if title == "参与判断的补帧" and self.request.target_point is not None:
                    self._mark(canvas, transform, self.request.target_point, "#e63b35")
        self.details.select(min(selected, len(self.details.tabs()) - 1))

    def cancel(self):
        if self._destroyed:
            return
        self._stop()
        if self.winfo_exists():
            self.destroy()

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        if self._resize_after is not None:
            self.after_cancel(self._resize_after)
            self._resize_after = None
        super().destroy()
        self.photos.clear()
        self._detail_photos.clear()
        self.canvases.clear()
        self.transforms.clear()
        self.buttons.clear()
        self._submit = self._stop = self._mark_displayed = None
        self.displayed_frame = self.request = None
        self.error = self.timer_text = self.wait_progress = None
        # Tk 变量必须在主线程释放，避免循环引用随后由采图线程的 GC 析构。
        for name in ("title_text", "level_text", "expect_text", "reference_text", "action_text",
                     "choice_var", "assumed_var", "use_auto_var"):
            setattr(self, name, None)
