from __future__ import annotations

import queue
import threading

from flows import (
    AutoProbeOnceResult,
    run_auto_probe_loop,
)

from .runtime_context import AppRuntimeContext


AutoLoopEvent = tuple[str, object]


class AutoProbeLoopBridge:
    """连接自动探测后台线程与 Tkinter 主线程消息队列。"""

    def __init__(
        self,
        context: AppRuntimeContext,
    ) -> None:
        self.context = context
        self.stop_event = threading.Event()
        self.events: queue.Queue[AutoLoopEvent] = queue.Queue()
        self.thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        thread = self.thread
        return thread is not None and thread.is_alive()

    def set_context(
        self,
        context: AppRuntimeContext,
    ) -> None:
        if self.running:
            raise RuntimeError(
                "自动循环运行中，无法切换运行上下文"
            )

        self.context = context

    def start(self) -> bool:
        """启动后台循环；已经运行时返回 False。"""
        if self.running:
            return False

        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._worker,
            name="auto-probe-loop",
            daemon=True,
        )
        self.thread.start()
        return True

    def request_stop(self) -> None:
        self.stop_event.set()

    def get_event_nowait(self) -> AutoLoopEvent:
        return self.events.get_nowait()

    def mark_finished(self) -> None:
        self.thread = None

    def wait(
        self,
        timeout: float,
    ) -> bool:
        """等待后台线程结束，返回是否已经结束。"""
        thread = self.thread

        if thread is None:
            return True

        thread.join(timeout=timeout)
        return not thread.is_alive()

    def _worker(self) -> None:
        context = self.context

        try:
            summary = run_auto_probe_loop(
                adb=context.adb,
                page=context.page,
                network=context.network,
                board=context.board,
                strategy=context.strategy,
                stop_event=self.stop_event,
                on_round=self._queue_round,
            )

            context.network.restore_network()

        except Exception as exc:
            self.events.put(("error", exc))
            return

        self.events.put(("summary", summary))

    def _queue_round(
        self,
        index: int,
        result: AutoProbeOnceResult,
    ) -> None:
        self.events.put(
            ("round", (index, result))
        )


__all__ = [
    "AutoLoopEvent",
    "AutoProbeLoopBridge",
]
