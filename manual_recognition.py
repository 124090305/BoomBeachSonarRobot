"""人工试运行的同步通道及识别适配。此模块不依赖 Tk 或 control_lock。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Condition
from uuid import uuid4
import time
import json

import cv2

import config
from logger import get_logger
from sonar_config import INITIAL_LEVEL
from stop_control import StopRequestedError, raise_if_stop_requested
from vision import DiamondHitResult, MatchResult
from vision.image_match import read_image


SOURCE = "manual_trial"
WAIT_POLL_SECONDS = config.STOP_POLL_INTERVAL
PAGE_OPTIONS = (("activity_detail", "活动棋盘页面"), ("home_sonar_visible", "主岛，声纳浮标可见"),
                ("home", "主岛"), ("unknown", "无法判断"))
TEMPLATE_OPTIONS = (("found", "找到"), ("missing", "未找到"), ("timeout", "判定超时"))
PROBE_OPTIONS = (("hit", "命中 HIT"), ("miss", "未命中 MISS"),
                 ("unopened", "未开启"), ("unknown", "无法判断本格结果"))
TEMPLATE_NAMES = {"activity_button.png": "主岛活动按钮", "sonar_join.png": "海边声纳浮标",
                  "sonar_join_label.png": "声纳标签", "quit_activity.png": "退出活动按钮",
                  "retry.png": "重试按钮", "retry1.png": "重试按钮", "victory.png": "胜利画面"}
logger = get_logger(__name__)


@dataclass(frozen=True)
class ManualFrame:
    request_id: str
    number: int
    image: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class ManualRequest:
    request_id: str
    kind: str
    step: str
    detail: str
    level: int
    cell: tuple[int, int] | None
    revision: int | None
    options: tuple[tuple[str, str], ...]
    screen_size: tuple[int, int]
    images: tuple = field(repr=False, compare=False)
    image_labels: tuple[str, ...]
    templates: tuple = field(default=(), repr=False, compare=False)
    needs_position: bool = False
    target_point: tuple[int, int] | None = None
    wait_started_at: float | None = None
    reference_timeout: float | None = None


@dataclass(frozen=True)
class ManualAnswer:
    value: str
    coordinates: tuple[int, ...] = ()
    source: str = SOURCE
    request_id: str = ""
    frame: ManualFrame | None = field(default=None, repr=False, compare=False)
    submitted_at: float = 0.


class ManualResultProvider:
    """一个请求、一次提交、一次消费；提交先于停止时保证交给写回区。"""

    def __init__(self, publish=None, *, diagnostic_dir=None):
        self.publish = publish or (lambda request: None)
        self.session_id = uuid4().hex
        self.level = INITIAL_LEVEL
        self.board = self.strategy = None
        self.target = None
        self._condition = Condition()
        self._sequence = 0
        self._pending = None
        self._answer = None
        self._cancelled = False
        self._stop_event = None
        self._latest_frame = self._displayed_frame = None
        self._frame_number = 0
        self.diagnostic_dir = Path(diagnostic_dir) if diagnostic_dir is not None else config.SCREENSHOT_DIR / "manual_recognition" / self.session_id
        self.last_diagnostic_path = None

    def bind(self, level, board, strategy):
        with self._condition:
            if self._pending is not None:
                raise RuntimeError("等待人工输入时不能换关或换盘")
            self.level, self.board, self.strategy = level, board, strategy
            self.target = strategy.pending_cell

    def begin_run(self):
        with self._condition:
            if self._pending is not None:
                raise RuntimeError("上次人工请求尚未结束")
            self._cancelled = False

    @property
    def pending(self):
        with self._condition:
            return self._pending

    def cancel(self):
        with self._condition:
            self._cancelled = True
            self._latest_frame = self._displayed_frame = None
            self._condition.notify_all()

    def take_latest_frame(self):
        """GUI 沿用原消息轮询；未显示的中间帧直接覆盖，最多保留一帧。"""
        with self._condition:
            frame, self._latest_frame = self._latest_frame, None
            return frame

    def mark_displayed(self, frame):
        with self._condition:
            if (self._pending is None or self._pending.request_id != frame.request_id
                    or self._answer is not None or self._cancelled
                    or (self._stop_event is not None and self._stop_event.is_set())
                    or not (1 <= frame.number <= self._frame_number)
                    or (self._displayed_frame is not None and frame.number < self._displayed_frame.number)):
                return False
            self._displayed_frame = frame
            return True

    def submit(self, request_id, *, value, coordinates=(), frame_id=None):
        """Tk 可直接调用；只获取专用条件锁，绝不等待业务互斥锁。"""
        with self._condition:
            request = self._pending
            if (request is None or request.request_id != request_id or self._answer is not None
                    or self._cancelled or (self._stop_event is not None and self._stop_event.is_set())):
                raise ValueError("请求已结束、已提交或已过期")
            if self.board is not None and self.board.revision != request.revision:
                raise ValueError("棋盘已改变，请停止并重新启动试运行")
            if value not in dict(request.options):
                raise ValueError("请选择当前请求提供的结果")
            frame = self._displayed_frame
            if frame is None or (frame_id is not None and frame_id != frame.number):
                raise ValueError("截图已过期，请基于当前显示画面判断")
            points = tuple(coordinates)
            if request.needs_position and value == "found":
                if len(points) != 2:
                    raise ValueError("请在截图上点选目标")
                try:
                    points = tuple(int(str(item).strip()) for item in points)
                except ValueError as exc:
                    raise ValueError("坐标必须为整数") from exc
                for i in range(0, len(points), 2):
                    self.validate_point(points[i:i+2], (frame.image.shape[1], frame.image.shape[0]))
            else:
                points = ()
            self._answer = ManualAnswer(value, points, request_id=request_id, frame=frame,
                                        submitted_at=time.monotonic())
            self._latest_frame = None
            logger.info("[人工试运行] 提交 %s：%s，帧=%s，坐标=%s", request_id, value, frame.number, points)
            self._condition.notify_all()

    @staticmethod
    def validate_point(point, size):
        x, y = point
        width, height = size
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"坐标 {point} 超出真实截图范围：x=0～{width-1}，y=0～{height-1}")

    def ask(self, images, *, kind, step, detail, options, stop_event=None,
            image_labels=("当前截图",), templates=(), needs_position=False, target_point=None,
            refresh=None, wait_started_at=None, reference_timeout=None, poll_interval=None):
        raise_if_stop_requested(stop_event)
        # 首帧由原调用处传入；仅等待型请求使用该调用传入的截图方法刷新。
        height, width = images[0].shape[:2]
        with self._condition:
            if self._cancelled:
                raise StopRequestedError("人工试运行已停止")
            raise_if_stop_requested(stop_event)
            if self._pending is not None:
                raise RuntimeError("同一人工提供器同时出现多个请求")
            self._sequence += 1
            request = ManualRequest(
                f"{self.session_id}:{self._sequence}", kind, step, detail,
                self.level, self.target, self.board.revision if self.board is not None else None,
                options, (width, height), tuple(images), tuple(image_labels),
                tuple(templates), needs_position, target_point, wait_started_at, reference_timeout,
            )
            self._pending, self._answer, self._stop_event = request, None, stop_event
            self._frame_number = 1
            self._displayed_frame = ManualFrame(request.request_id, 1, images[0])
            self._latest_frame = None
        logger.info("[人工试运行] 等待 %s：第%s关，目标=%s，%s", request.request_id, self.level, self.target, step)
        try:
            self.publish(request)
            next_capture = self._next_capture_time(request, poll_interval) if refresh else None
            while True:
                with self._condition:
                    if self._answer is not None:
                        return self._answer
                    self._check_cancelled(stop_event)
                    delay = next_capture - time.monotonic() if refresh else WAIT_POLL_SECONDS
                    if delay > 0:
                        self._condition.wait(min(delay, WAIT_POLL_SECONDS))
                        continue
                # 同一业务线程顺序采图；任何 I/O 都不占用提交用的条件锁。
                try:
                    screenshot = refresh()
                except Exception:
                    with self._condition:
                        self._check_cancelled(stop_event)
                    raise
                with self._condition:
                    if self._answer is not None:
                        return self._answer  # 提交后到达的帧不再发布。
                    self._check_cancelled(stop_event)
                    self._frame_number += 1
                    self._latest_frame = ManualFrame(request.request_id, self._frame_number, screenshot)
                next_capture = self._next_capture_time(request, poll_interval)
        finally:
            with self._condition:
                self._pending = self._answer = self._stop_event = None
                self._latest_frame = self._displayed_frame = None

    def _check_cancelled(self, stop_event):
        if self._cancelled:
            raise StopRequestedError("人工等待已取消")
        raise_if_stop_requested(stop_event)

    @staticmethod
    def _next_capture_time(request, poll_interval):
        now = time.monotonic()
        remaining = request.wait_started_at + request.reference_timeout - now
        # 参考期限前保持原 min(interval, remaining) 节奏，期限后继续按原间隔刷新。
        delay = min(poll_interval, remaining) if remaining > 0 else poll_interval
        return now + delay

    def _save_decision(self, answer, started_at):
        """只保存最终提交所依据的原图；不保存轮询中间帧，不伪造相似度。"""
        self.last_diagnostic_path = None
        path = self.diagnostic_dir / f"{answer.request_id.split(':')[-1]}_frame_{answer.frame.number}_{answer.value}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        ok, encoded = cv2.imencode(".png", answer.frame.image)
        if not ok:
            raise RuntimeError("人工判断依据截图编码失败")
        encoded.tofile(str(path))
        metadata = dict(source=SOURCE, request_id=answer.request_id, frame_id=answer.frame.number,
                        value=answer.value, coordinates=answer.coordinates,
                        elapsed_seconds=answer.submitted_at - started_at)
        path.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        self.last_diagnostic_path = path
        logger.info("[人工试运行] 判断依据：请求=%s，帧=%s，结果=%s，截图=%s",
                    answer.request_id, answer.frame.number, answer.value, path)


    def template(self, screenshot, name, *, waiting=False, needs_position=False, stop_event=None,
                 refresh=None, started_at=None, timeout=None, poll_interval=None):
        if waiting and (refresh is None or started_at is None or timeout is None
                        or poll_interval is None or poll_interval <= 0 or timeout < 0):
            raise ValueError("等待型人工测试模式需要原截图方法、计时起点、超时和轮询间隔")
        names = (name,) if isinstance(name, (str, Path)) else tuple(name)
        paths = tuple(Path(item) if Path(item).is_absolute() else config.TEMPLATE_DIR / item for item in names)
        templates = tuple(read_image(path) for path in paths)
        label = " / ".join(TEMPLATE_NAMES.get(path.name, path.name) for path in paths)
        options = TEMPLATE_OPTIONS if waiting else TEMPLATE_OPTIONS[:2]
        answer = self.ask((screenshot,), kind="template", step=("等待" if waiting else "查找") + label,
                          detail="截图中能找到所示模板吗？" + ("找到时直接点选截图中的目标。" if needs_position else ""),
                          options=options, templates=templates, needs_position=needs_position, stop_event=stop_event,
                          refresh=refresh if waiting else None, wait_started_at=started_at if waiting else None,
                          reference_timeout=timeout if waiting else None, poll_interval=poll_interval)
        if waiting:
            self._save_decision(answer, started_at)
        if answer.value != "found":
            return None
        # 有无判断没有定位信息，禁止填造中心坐标。
        point = answer.coordinates if needs_position else None
        return MatchResult(float("nan"), point, point, source=SOURCE, request_id=answer.request_id)

    def page_state(self, screenshot, stop_event=None):
        answer = self.ask((screenshot,), kind="page", step="判断当前页面", detail="当前截图属于哪个页面？",
                          options=PAGE_OPTIONS, stop_event=stop_event)
        return answer.value

    def probe(self, before, after, context, stop_event=None):
        self.target = context.cell
        answer = self.ask((before, after), kind="probe", step="判断本发结果",
                          detail="对照探测前后截图，标记的目标格是什么结果？",
                          options=PROBE_OPTIONS, image_labels=("探测前 before", "探测后 after"),
                          target_point=context.screen_point, stop_event=stop_event)
        # nan 明确表示没有视觉测量；禁止填造置信度或灰度等测量值。
        unknown = float("nan")
        return DiamondHitResult(
            answer.value, unknown, unknown, context.screen_point, context.screen_point,
            unknown, unknown, unknown, unknown, unknown, unknown, unknown, unknown, unknown,
            inside_ship_ratio=unknown, boundary_ship_ratio=unknown, outside_ship_ratio=unknown,
            cross_boundary_score=unknown, cross_boundary_direction=None,
            sunk_candidate=False, source=SOURCE, request_id=answer.request_id,
        )


def manual_provider(page):
    """仅读取显式注入值，兼容旧调用方及无此属性的测试替身。"""
    return vars(page).get("manual_results") if hasattr(page, "__dict__") else None
