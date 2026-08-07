from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)


from controllers import (
    AdbController,
    PageController,
)


def read_numbers(
    prompt: str,
    count: int,
) -> list[int] | None:
    """读取一组整数，输入空内容时取消。"""
    text = input(prompt).strip()

    if not text:
        return None

    parts = text.split()

    if len(parts) != count:
        print(f"需要输入 {count} 个数字")
        return None

    try:
        return [
            int(value)
            for value in parts
        ]
    except ValueError:
        print("坐标必须是整数")
        return None


def read_template() -> str | None:
    """读取模板路径或模板文件名。"""
    text = input(
        "模板路径或文件名："
    ).strip()

    if not text:
        return None

    return text


def print_match(match) -> None:
    """打印模板匹配结果。"""
    if match is None:
        print("没有找到模板")
        return

    print("找到模板")
    print(f"相似度：{match.score:.3f}")
    print(f"中心坐标：{match.center}")
    print(f"左上角：{match.top_left}")
    print(f"右下角：{match.bottom_right}")


def main() -> None:
    adb = AdbController()
    page = PageController(adb)

    adb.ensure_device_online()

    width, height = adb.get_screenshot_size()

    print(f"设备：{adb.serial}")
    print(f"截图尺寸：{width}x{height}")

    print()
    print("p：固定坐标点击")
    print("s：坐标滑动")
    print("f：查找模板")
    print("c：查找模板并点击")
    print("w：等待模板出现并点击")
    print("q：退出")

    while True:
        print()

        key = input("> ").strip().lower()

        try:
            if key == "p":
                point = read_numbers(
                    "输入 x y：",
                    2,
                )

                if point is None:
                    continue

                page.click_point(
                    point[0],
                    point[1],
                )

                print(
                    f"已点击：{tuple(point)}"
                )

            elif key == "s":
                points = read_numbers(
                    (
                        "输入 start_x start_y "
                        "end_x end_y："
                    ),
                    4,
                )

                if points is None:
                    continue

                duration_text = input(
                    "滑动时间毫秒，直接回车使用 300："
                ).strip()

                duration_ms = (
                    int(duration_text)
                    if duration_text
                    else 300
                )

                page.swipe(
                    points[0],
                    points[1],
                    points[2],
                    points[3],
                    duration_ms=duration_ms,
                )

                print("滑动完成")

            elif key == "f":
                template = read_template()

                if template is None:
                    continue

                match = page.find_template(
                    template
                )

                print_match(match)

            elif key == "c":
                template = read_template()

                if template is None:
                    continue

                match = page.click_template(
                    template
                )

                if match is None:
                    print(
                        "没有找到模板，未点击"
                    )
                else:
                    print(
                        "已点击模板中心："
                        f"{match.center}"
                    )
                    print(
                        f"相似度：{match.score:.3f}"
                    )

            elif key == "w":
                template = read_template()

                if template is None:
                    continue

                timeout_text = input(
                    "等待秒数，直接回车使用默认值："
                ).strip()

                if timeout_text:
                    match = page.wait_and_click(
                        template,
                        timeout=float(
                            timeout_text
                        ),
                    )
                else:
                    match = page.wait_and_click(
                        template
                    )

                if match is None:
                    print(
                        "等待超时，未找到模板"
                    )
                else:
                    print(
                        "模板出现，已点击："
                        f"{match.center}"
                    )
                    print(
                        f"相似度：{match.score:.3f}"
                    )

            elif key == "q":
                print("页面控制测试结束")
                break

            else:
                print("未知命令")

        except Exception as exc:
            print(f"操作失败：{exc}")


if __name__ == "__main__":
    main()