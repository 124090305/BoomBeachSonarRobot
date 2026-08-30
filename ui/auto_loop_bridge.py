from __future__ import annotations

import queue
import threading

from flows import (
    AutoProbeCommittedResult,
    AutoProbeOnceResult,
    LevelState,
    run_multi_level_loop,
)
from logger import get_logger

from .runtime_context import AppRuntimeContext


AutoLoopEvent = tuple[str, object]


logger = get_logger(__name__)


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

    def mark_finished(self) -> bool:
        """仅在线程真正退出后清除引用。"""
        thread = self.thread
        if thread is not None and thread.is_alive():
            return False
        self.thread = None
        return True

    def wait(
        self,
        timeout: float | None,
    ) -> bool:
        """等待后台线程结束，返回是否已经结束。"""
        thread = self.thread

        if thread is None:
            return True

        thread.join(timeout=timeout)
        return not thread.is_alive()

    def shutdown_and_restore_network(self) -> None:
        """关闭程序时等待后台退出，再独占恢复网络。"""
        self.request_stop()
        self.wait(timeout=None)
        self.mark_finished()

        context = self.context

        with context.control_lock:
            context.network.restore_network()

    def _worker(self) -> None:
        context = self.context

        try:
            with context.control_lock:
                summary = run_multi_level_loop(
                    adb=context.adb,
                    page=context.page,
                    network=context.network,
                    initial_state=LevelState(
                        context.current_level,
                        context.board,
                        context.strategy,
                    ),
                    game=context.game,
                    stop_event=self.stop_event,
                    on_round=self._queue_round,
                    on_result=self._queue_result,
                    on_level_changed=self._queue_level,
                )

                if summary.stop_reason != "requested":
                    context.network.restore_network()

        except Exception as exc:
            try:
                with context.control_lock:
                    context.network.restore_network()
            except Exception:
                logger.exception(
                    "自动循环异常退出后的网络清理失败"
                )

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

    def _queue_result(
        self,
        index: int,
        result: AutoProbeCommittedResult,
    ) -> None:
        self.events.put(
            ("result", (index, result))
        )

    def _queue_level(self, state: LevelState) -> None:
        self.context = self.context.with_level_state(state)
        self.events.put(("level", self.context))


__all__ = [
    "AutoLoopEvent",
    "AutoProbeLoopBridge",
]
