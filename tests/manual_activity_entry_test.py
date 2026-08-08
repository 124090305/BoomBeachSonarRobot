from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from controllers import (
    AdbController,
    NetworkController,
    PageController,
)
from flows import (
    SonarPageState,
    detect_sonar_page_state,
    enter_activity_initial,
)


PAGE_STATE_TEXT = {
    SonarPageState.ACTIVITY_DETAIL: (
        "活动详情页"
    ),
    SonarPageState.HOME_SONAR_VISIBLE: (
        "主岛，声纳已可见"
    ),
    SonarPageState.HOME: (
        "主岛"
    ),
    SonarPageState.UNKNOWN: (
        "未知页面"
    ),
}


def main() -> None:
    print(
        "初始进入声纳活动 + 页面状态检验"
    )
    print()
    print(
        "建议测试起点："
        "游戏已经打开并停在主岛，网络正常。"
    )
    print(
        "程序会自己检查主岛、寻找声纳、"
        "开启弱网并进入活动详情。"
    )
    print()
    print(
        "测试结束后弱网会保持开启，"
        "这就是后续开始探测时需要的状态。"
    )
    print(
        "如果测试后不继续探测，"
        "可用 GUI 的“恢复网络”或运行："
    )
    print(
        "python main.py network-reset"
    )
    print()

    command = input(
        "准备好后按 Enter 开始，"
        "输入 q 退出："
    ).strip().lower()

    if command == "q":
        return

    adb = AdbController()
    adb.ensure_device_online()

    page = PageController(
        adb
    )

    network = NetworkController(
        adb
    )

    initial_state = (
        detect_sonar_page_state(
            page
        )
    )

    print()
    print(
        "进入流程前页面状态："
        f"{PAGE_STATE_TEXT[initial_state]}"
        f" ({initial_state.value})"
    )

    result = enter_activity_initial(
        adb=adb,
        page=page,
        network=network,
    )

    final_state = (
        detect_sonar_page_state(
            page
        )
    )

    network_state = (
        network.get_state()
    )

    print()
    print(
        "初始进入流程完成"
    )
    print(
        "起始页面："
        f"{PAGE_STATE_TEXT[result.initial_state]}"
    )
    print(
        "最终页面："
        f"{PAGE_STATE_TEXT[final_state]}"
    )
    print(
        f"检测到的声纳中心：{result.sonar_point}"
    )
    print(
        "弱网状态："
        f"{'开启' if network_state.weak_enabled else '关闭'}"
    )
    print(
        "REJECT 状态："
        f"{'开启' if network_state.reject_enabled else '关闭'}"
    )

    if (
        final_state
        != SonarPageState.ACTIVITY_DETAIL
    ):
        raise RuntimeError(
            "最终页面检验失败："
            f"{final_state.value}"
        )

    if not network_state.weak_enabled:
        raise RuntimeError(
            "最终弱网状态检验失败"
        )

    if network_state.reject_enabled:
        raise RuntimeError(
            "最终 REJECT 状态异常"
        )

    print()
    print(
        "测试通过："
        "当前已经位于声纳活动详情页，"
        "并保持弱网 DROP。"
    )


if __name__ == "__main__":
    main()
