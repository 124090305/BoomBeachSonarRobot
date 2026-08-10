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
    PageController,
)
from flows import (
    prepare_probe_once,
    submit_manual_probe_result,
)
from sonar import (
    CheckerboardHuntStrategy,
    SonarBoard,
)
from vision import (
    DiamondHitConfig,
    classify_diamond_hit,
)


def print_metrics(result) -> None:
    print("识别指标：")
    print(f"  state={result.state}")
    print(f"  confidence={result.confidence:.3f}")
    print(f"  score={result.score:.3f}")
    print(f"  rough_center={result.rough_center}")
    print(f"  refined_center={result.refined_center}")
    print(f"  changed_ratio={result.changed_ratio:.3f}")
    print(f"  center_gray_ratio={result.center_gray_ratio:.3f}")
    print(f"  ring_gray_ratio={result.ring_gray_ratio:.3f}")
    print(f"  gray_excess={result.gray_excess:.3f}")
    print(f"  component_ratio={result.component_ratio:.3f}")
    print(f"  s_center={result.s_center:.1f}")
    print(f"  s_ring={result.s_ring:.1f}")
    print(f"  s_drop={result.s_drop:.1f}")
    print(f"  edge_density={result.edge_density:.3f}")


def main() -> None:
    if DEFAULT_LEVEL_CONFIG.board_quad is None:
        raise RuntimeError(
            "DEFAULT_LEVEL_CONFIG.board_quad 还没有填写"
        )

    print("单发真实探测自动 HIT/MISS 联调")
    print(
        "流程：策略选格 -> 点击前截图 -> 点击目标格 -> "
        "退出活动 -> 重进活动 -> 点击后截图 -> "
        "自动识别 -> HIT/MISS 写回策略"
    )
    print()
    print("运行前要求：")
    print("1. 模拟器已经进入声纳活动详情，棋盘可见。")
    print("2. 如需按当前保护流程测试，请先开启弱网 DROP。")
    print("3. 本测试只执行一发，不处理 REJECT / retry。")
    print("4. unknown / unopened 不写回策略，pending_cell 会保留。")
    print()

    command = input(
        "准备好后按 Enter 开始，输入 q 退出："
    ).strip().lower()

    if command == "q":
        return

    config.ensure_directories()

    adb = AdbController()
    adb.ensure_device_online()

    page = PageController(adb)

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

    context = prepare_probe_once(
        adb=adb,
        page=page,
        board=board,
        strategy=strategy,
    )

    before = adb.read_image(
        context.before_path
    )
    after = adb.read_image(
        context.after_path
    )

    debug_dir = (
        config.SCREENSHOT_DIR
        / "diamond_hit_debug"
    )

    classifier_config = DiamondHitConfig(
        diamond_w=80,
        diamond_h=56,
        search_radius=14,
        debug=True,
        debug_dir=str(debug_dir),
    )

    recognition = classify_diamond_hit(
        before_screenshot=before,
        after_screenshot=after,
        center=context.screen_point,
        config=classifier_config,
        index=0,
    )

    print()
    print(f"本次逻辑格：{context.cell}")
    print(f"模拟器坐标：{context.screen_point}")
    print(f"点击前截图：{context.before_path}")
    print(f"重进后截图：{context.after_path}")
    print(f"调试图片目录：{debug_dir}")
    print()

    print_metrics(recognition)
    print()

    if recognition.state == "hit":
        probe_result = submit_manual_probe_result(
            strategy,
            context,
            hit=True,
        )
        print(
            f"自动结果已写回策略："
            f"{probe_result.context.cell} -> HIT"
        )

    elif recognition.state == "miss":
        probe_result = submit_manual_probe_result(
            strategy,
            context,
            hit=False,
        )
        print(
            f"自动结果已写回策略："
            f"{probe_result.context.cell} -> MISS"
        )

    else:
        print(
            "自动识别结果暂时无法安全提交。"
        )
        print(
            f"当前状态：{recognition.state}"
        )
        print(
            "策略 pending_cell 保留，"
            "方便检查调试图后重试同一格。"
        )
        return

    if probe_result.newly_confirmed:
        for ship in probe_result.newly_confirmed:
            print(
                "新确认潜艇："
                f"长度={ship.length}，"
                f"方向={ship.direction}，"
                f"格子={ship.cells}"
            )

    next_cell = strategy.choose_next_cell()
    print(
        f"策略给出的下一格：{next_cell}"
    )
    print(
        "本次只验证一发，不继续实际点击。"
    )


if __name__ == "__main__":
    main()
