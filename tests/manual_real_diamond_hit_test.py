from __future__ import annotations

# =========================================================
# 手动配置区：TARGET_CELL 与 GUI 标签一致，格式为 (行, 列)，从 1 开始。
# =========================================================

BEFORE_IMAGE_PATH = r"D:\Desktop\hdqb\BoomBeachSonar\resources\calibration\images\11.png"
AFTER_IMAGE_PATH = r"D:\Desktop\hdqb\BoomBeachSonarRobot\runtime\screenshots\auto_probe\probe_20260809_164513_297348_r0_c0_after.png"
TARGET_CELL = (3, 2)
GRID_SIZE = 10
DEBUG = True

# 可选：需要多帧兜底时填写额外的 after 静态截图。
EXTRA_AFTER_IMAGE_PATHS: tuple[str, ...] = ()

# 可选：填写本次点击前已经记录为 HIT 的 GUI 格号，供正式 SUNK 策略校验。
EXISTING_HIT_CELLS: tuple[tuple[int, int], ...] = ()


import sys
from dataclasses import asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from flows.auto_probe_flow import (
    ProbeOutcome,
    build_default_hit_config,
    is_conclusive_recognition_state,
    is_hit_recognition_state,
)
from sonar import (
    Cell,
    CellState,
    CheckerboardHuntStrategy,
    SonarBoard,
)
from sonar_config import DEFAULT_LEVEL_CONFIG
from vision import (
    classify_diamond_hit,
    classify_diamond_hit_multiframe,
    needs_multiframe_confirmation,
    read_image,
)


def gui_cell_to_internal(board: SonarBoard, gui_cell: tuple[int, int]) -> Cell:
    """按 GUI 的 1 基行列标签转换为项目内部逻辑格。"""
    if len(gui_cell) != 2:
        raise ValueError("TARGET_CELL 必须写成 (行, 列)")
    gui_row, gui_col = (int(value) for value in gui_cell)
    return board.cell_from_index(
        board.index_of(gui_row - 1, gui_col - 1)
    )


def main() -> None:
    if GRID_SIZE != DEFAULT_LEVEL_CONFIG.grid_size:
        raise ValueError(
            "当前正式默认映射要求 GRID_SIZE="
            f"{DEFAULT_LEVEL_CONFIG.grid_size}"
        )
    if DEFAULT_LEVEL_CONFIG.board_quad is None:
        raise RuntimeError("DEFAULT_LEVEL_CONFIG.board_quad 尚未配置")

    before = read_image(BEFORE_IMAGE_PATH)
    after = read_image(AFTER_IMAGE_PATH)

    # 全部棋盘与策略对象均为本进程内的一次性离线状态。
    board = SonarBoard(
        grid_size=GRID_SIZE,
        submarines=DEFAULT_LEVEL_CONFIG.submarines,
    )
    board.set_screen_quad(DEFAULT_LEVEL_CONFIG.board_quad)
    target_cell = gui_cell_to_internal(board, TARGET_CELL)
    target_center = board.screen_point(*target_cell)

    strategy = CheckerboardHuntStrategy(
        board,
        hunt_parity=DEFAULT_LEVEL_CONFIG.hunt_parity,
        use_safety_rule=DEFAULT_LEVEL_CONFIG.use_safety_rule,
    )
    for gui_cell in EXISTING_HIT_CELLS:
        row, col = gui_cell_to_internal(board, gui_cell)
        board.set_state(row, col, CellState.HIT)

    debug_dir = PROJECT_ROOT / "tests" / "manual_real_diamond_hit_debug"
    classifier_config = build_default_hit_config(
        debug=DEBUG,
        debug_dir=debug_dir,
    )
    recognition = classify_diamond_hit(
        before_screenshot=before,
        after_screenshot=after,
        center=target_center,
        config=classifier_config,
        index=board.index_of(*target_cell),
    )

    needs_extra_frame = needs_multiframe_confirmation(
        recognition,
        classifier_config,
    )
    if needs_extra_frame and EXTRA_AFTER_IMAGE_PATHS:
        extra_after_images = [
            read_image(path)
            for path in EXTRA_AFTER_IMAGE_PATHS
        ]
        recognition = classify_diamond_hit_multiframe(
            before_screenshot=before,
            after_screenshots=[after, *extra_after_images],
            center=target_center,
            config=classifier_config,
            index=board.index_of(*target_cell),
        )

    is_hit = is_hit_recognition_state(recognition.state)
    commit = None
    if is_conclusive_recognition_state(recognition.state):
        commit = strategy.report_recognition_result(
            target_cell,
            hit=is_hit,
            sunk_direction=(
                recognition.cross_boundary_direction
                if recognition.sunk_candidate
                else None
            ),
        )
        outcome = ProbeOutcome(commit.final_state.value.upper())
        final_state = outcome.value
    else:
        final_state = recognition.state.upper()

    is_sunk = final_state == ProbeOutcome.SUNK.value

    print("\n真实截图单格识别结果")
    print(f"目标格编号（GUI）：{TARGET_CELL[0]},{TARGET_CELL[1]}")
    print(f"目标格内部坐标：{target_cell}")
    print(f"目标格像素中心：{target_center}")
    print(f"最终 state：{final_state}")
    print(f"识别器 state：{recognition.state}")
    print(f"confidence：{recognition.confidence:.6f}")
    print(f"score：{recognition.score:.6f}")
    print(f"是否 HIT：{is_hit}")
    print(f"是否确认潜艇 / SUNK：{is_sunk}")
    print(f"需要多帧确认：{needs_extra_frame}")
    print(f"实际使用 after 帧数：{1 + (len(EXTRA_AFTER_IMAGE_PATHS) if needs_extra_frame else 0)}")

    print("\n识别结果对象完整参数：")
    for name, value in asdict(recognition).items():
        print(f"  {name}={value}")

    if commit is not None:
        print("\n正式策略校验结果：")
        print(f"  confirmation_source={commit.confirmation_source}")
        print(f"  newly_confirmed={commit.newly_confirmed}")
        print(f"  sunk_validation={commit.sunk_validation}")

    if DEBUG:
        print(f"\ndebug 图片目录：{debug_dir}")


if __name__ == "__main__":
    main()
