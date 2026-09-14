"""只读定位与整盘状态验收：支持历史截图，或活动开放后的实时截图。"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sonar_config import get_level_config
from vision.board_geometry import locate_board
from vision.board_recognition import recognize_board
from vision.board_debug import write_image
from vision.image_match import read_image


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--level', required=True, type=int)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--image', type=Path, help='历史原始截图；完全离线')
    mode.add_argument('--live', action='store_true', help='只读当前模拟器画面，无点击或拖动')
    parser.add_argument('--serial', default=None)
    parser.add_argument('--cell', nargs=2, type=int, metavar=('ROW', 'COL'), help='与 GUI 一致，从 1 开始的行、列')
    args = parser.parse_args(argv)
    output = PROJECT_ROOT/'outputs/runtime_board_geometry'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    try:
        level = get_level_config(args.level)
        reference = read_image(level.empty_reference_path)
        start = time.perf_counter()
        if args.live:
            from controllers import AdbController, PageController
            from flows.sonar_page import SonarPageState, detect_sonar_page_state
            import config
            adb = AdbController(serial=args.serial or config.ADB_SERIAL)
            image = adb.read_screenshot()
            if detect_sonar_page_state(PageController(adb), screenshot=image) != SonarPageState.ACTIVITY_DETAIL:
                raise RuntimeError('当前画面无法识别，请在活动开放后进入声纳棋盘页')
        else:
            image = read_image(args.image)
        geometry = locate_board(reference, image, level, output_dir=output)
        write_image(output/'original.png', image)
        print(f'定位耗时（含读取/调试输出）：{time.perf_counter()-start:.3f} 秒')
        print(f'当前四角：{geometry.current_quad}')
        print(f'定位置信度：{geometry.alignment.confidence:.3f}；外角复核误差：{geometry.outline_error_px:.2f}px')
        for index, point in enumerate(geometry.points(level)):
            print(f'({index//level.grid_size+1},{index%level.grid_size+1}) -> {tuple(round(float(v), 2) for v in point)}')
        if args.cell:
            cell = tuple(value-1 for value in args.cell)
            print(f'目标格 {tuple(args.cell)}：{geometry.screen_point(level, cell)}')
            try:
                geometry.require_visible_target(image, level, cell)
                print('目标格可见；单张图片无法证明实时稳定或允许点击。')
            except RuntimeError as exc:
                print(f'目标格拦截：{exc}')
        result = recognize_board(reference, image, level_config=level,
                                 runtime_geometry=True, output_dir=output/'recognition')
        print(f'整盘状态：{result.counts}；可用={result.valid}；质量={result.quality_score:.3f}')
        print(f'待复核：{[(r+1,c+1) for r,c in result.review_cells]}')
        print(f'异常：{result.issues}')
        print(f'调试目录：{output}')
        print('未点击、未拖动、未修改网络，未写入正式棋盘或策略。')
        return 0
    except Exception as exc:
        print(f'定位/识别未通过：{exc}；调试目录={output}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
