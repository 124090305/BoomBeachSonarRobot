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
    NetworkController,
)


def main() -> None:
    adb = AdbController()

    network = NetworkController(
        adb
    )

    print(
        network.get_root_info()
    )

    print()
    print("w：开启弱网")
    print("s：关闭弱网")
    print("r：开启断网")
    print("f：关闭断网")
    print("c：查看状态")
    print("q：恢复网络并退出")

    try:
        while True:
            key = (
                input("> ")
                .strip()
                .lower()
            )

            if key == "w":
                network.enable_weak_network()

                print(
                    "弱网已开启"
                )

            elif key == "s":
                network.disable_weak_network()

                print(
                    "弱网已关闭"
                )

            elif key == "r":
                network.enable_reject_network()

                print(
                    "断网已开启"
                )

            elif key == "f":
                network.disable_reject_network()

                print(
                    "断网已关闭"
                )

            elif key == "c":
                state = (
                    network.get_state()
                )

                print(
                    state.to_text()
                )

            elif key == "q":
                break

            else:
                print(
                    "未知命令"
                )

    finally:
        network.restore_network()

        print(
            "网络已恢复"
        )


if __name__ == "__main__":
    main()