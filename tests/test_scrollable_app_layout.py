from __future__ import annotations

from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk
import unittest

from ui.app_layout import ScrollableAppContent


class ScrollableAppContentTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk 不可用：{exc}")

        self.root.geometry("500x260")
        self.scroll = ScrollableAppContent(self.root)
        self.scroll.pack(fill=tk.BOTH, expand=True)
        self.tall_content = ttk.Frame(
            self.scroll.content,
            height=900,
        )
        self.tall_content.pack(fill=tk.X)
        self.tall_content.pack_propagate(False)
        self.label = ttk.Label(
            self.tall_content,
            text="页面内容",
        )
        self.label.pack()
        self.log_text = tk.Text(
            self.tall_content,
            height=3,
        )
        self.log_text.pack(fill=tk.X)
        self.scroll.bind_mousewheel_tree()
        self.scroll.refresh()
        self.root.update()

    def tearDown(self) -> None:
        root = getattr(self, "root", None)
        if root is None:
            return
        scroll = getattr(self, "scroll", None)
        if scroll is not None:
            scroll.shutdown()
        try:
            root.destroy()
        except tk.TclError:
            pass

    def test_content_width_tracks_canvas_and_scrollregion_tracks_height(
        self,
    ) -> None:
        canvas_width = self.scroll.canvas.winfo_width()
        content_width = self.scroll.content.winfo_width()
        self.assertEqual(content_width, canvas_width)

        scrollregion = tuple(
            int(float(value))
            for value in self.scroll.canvas.cget(
                "scrollregion"
            ).split()
        )
        self.assertGreater(
            scrollregion[3] - scrollregion[1],
            self.scroll.canvas.winfo_height(),
        )

    def test_mousewheel_scrolls_page_but_leaves_text_scroll_local(
        self,
    ) -> None:
        self.scroll.canvas.yview_moveto(0)
        result = self.scroll._on_mousewheel(
            SimpleNamespace(
                widget=self.label,
                delta=-120,
                num=None,
            )
        )
        self.root.update()
        self.assertEqual(result, "break")
        self.assertGreater(
            self.scroll.canvas.yview()[0],
            0,
        )

        previous_view = self.scroll.canvas.yview()
        result = self.scroll._on_mousewheel(
            SimpleNamespace(
                widget=self.log_text,
                delta=-120,
                num=None,
            )
        )
        self.assertIsNone(result)
        self.assertEqual(
            self.scroll.canvas.yview(),
            previous_view,
        )

    def test_shutdown_removes_mousewheel_class_binding(self) -> None:
        bindtag = self.scroll._wheel_bindtag
        self.assertTrue(
            self.root.bind_class(bindtag, "<MouseWheel>")
        )
        self.scroll.shutdown()
        self.assertFalse(
            self.root.bind_class(bindtag, "<MouseWheel>")
        )


if __name__ == "__main__":
    unittest.main()
