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


import config
from sonar_config import DEFAULT_LEVEL_CONFIG

from controllers import (
    AdbController,
    NetworkController,
    PageController,
)
from flows import (
    build_default_hit_config,
    run_auto_probe_once,
)
from sonar import (
    CheckerboardHuntStrategy,
    SonarBoard,
)


def print_recognition(result) -> None:
    recognition = result.recognition

    print("识别指标：")
    print(f"  state={recognition.state}")
    print(f"  confidence={recognition.confidence:.3f}")
    print(f"  score={recognition.score:.3f}")
    print(f"  changed_ratio={recognition.changed_ratio:.3f}")
    print(f"  center_gray_ratio={recognition.center_gray_ratio:.3f}")
    print(f"  ring_gray_ratio={recognition.ring_gray_ratio:.3f}")
    print(f"  gray_excess={recognition.gray_excess:.3f}")
    print(f"  component_ratio={recognition.component_ratio:.3f}")
    print(f"  s_center={recognition.s_center:.1f}")
    print(f"  s_ring={recognition.s_ring:.1f}")
    print(f"  s_drop={recognition.s_drop:.1f}")
    print(f"  edge_density={recognition.edge_density:.3f}")


def main() -> int:
    if DEFAULT_LEVEL_CONFIG.board_quad is None:
        raise RuntimeError(
            "DEFAULT_LEVEL_CONFIG.board_quad 还没有填写"
        )

    print("完整自动一发闭环测试")
    print()
    print("本测试会真实执行：")
    print(
        "页面准备 -> 弱网 -> 策略选格 -> 点击 -> 退出/重进 -> "
        "自动 HIT/MISS -> 策略写回 -> 分支恢复 -> 下一发准备"
    )
    print()
    print("结束成功时应满足：")
    print("1. 页面重新停在声纳活动详情页。")
    print("2. 弱网 DROP 已重新开启。")
    print("3. REJECT 已关闭。")
    print("4. 策略已经给出下一格，或本轮策略已经完成。")
    print()
    print("识别规则：只有 state=hit 记 HIT，其余状态统一记 MISS。")
    print("HIT：直接联网 5 秒后重新开启弱网；MISS：继续 REJECT/retry。")
    print()

    command = input(
        "准备好后按 Enter 开始，输入 q 退出："
    ).strip().lower()

    if command == "q":
        return 0

    config.ensure_directories()

    adb = AdbController()
    adb.ensure_device_online()

    page = PageController(adb)
    network = NetworkController(adb)

    board = SonarBoard(
        grid_size=DEFAULT_LEVEL_CONFIG.grid_size,
        submarines=DEFAULT_LEVEL_CONFIG.submarines,
    )
    board.set_screen_quad(
        DEFAULT_LEVEL_CONFIG.board_quad
    )

    strategy = CheckerboardHuntStrategy(
        board,
        hunt_parity=DEFAULT_LEVEL_CONFIG.hunt_parity,
        use_safety_rule=DEFAULT_LEVEL_CONFIG.use_safety_rule,
    )

    hit_config = build_default_hit_config(
        debug=True,
    )

    try:
        result = run_auto_probe_once(
            adb=adb,
            page=page,
            network=network,
            board=board,
            strategy=strategy,
            hit_config=hit_config,
        )

    except Exception as exc:
        print()
        print(f"测试失败：{exc}")

        try:
            state = network.get_state()
            print()
            print("失败后的当前网络状态：")
            print(state.to_text())
        except Exception as state_exc:
            print(
                f"读取网络状态也失败：{state_exc}"
            )

        print()
        print(
            "异常路径不会主动释放仍存在的弱网 DROP；"
            "确认游戏画面后，可执行：python main.py network-reset"
        )
        return 1

    print()
    print("================ 测试结果 ================")
    print(f"本发逻辑格：{result.context.cell}")
    print(f"模拟器坐标：{result.context.screen_point}")
    print(f"before：{result.context.before_path}")
    print(f"after：{result.context.after_path}")
    print()

    print_recognition(result)

    print()
    print(
        "正式写回结果："
        f"{'HIT' if result.hit else 'MISS'}"
    )

    if result.newly_confirmed:
        for ship in result.newly_confirmed:
            print(
                "新确认潜艇："
                f"长度={ship.length}，"
                f"方向={ship.direction}，"
                f"格子={ship.cells}"
            )
    else:
        print("本发没有新确认完整潜艇。")

    print()
    print("恢复链：")
    print(
        f"  mode={result.recovery.mode}"
    )
    print(
        f"  retry_found={result.recovery.retry_found}"
    )
    print(
        f"  final_page={result.recovery.final_state.value}"
    )
    print(
        f"  weak={result.recovery.weak_network_enabled}"
    )
    print(
        f"  reject={result.recovery.reject_network_enabled}"
    )

    print()
    print(f"策略下一格：{result.next_cell}")
    print(f"策略完成：{strategy.done}")
    print("==========================================")
    print()

    cleanup = input(
        "按 Enter 恢复正常网络并退出；"
        "输入 k 保持当前弱网、停在下一发准备状态："
    ).strip().lower()

    if cleanup == "k":
        print("保持当前下一发准备状态。")
        return 0

    network.restore_network()
    print("游戏网络已经恢复正常。")
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
