from __future__ import annotations

# 当前阶段临时使用的声纳棋盘配置。
# 后续关卡配置体系稳定后，再迁移到正式 config.py。

TEST_GRID_SIZE = 10
TEST_SUBMARINES = (2, 2, 3, 4, 5)

TEST_BOARD_QUAD = (
    (662, 47),    # top
    (1069, 291),  # right
    (666, 625),   # bottom
    (259, 288),   # left
)

# 第一版选格策略。
# 0 -> 优先遍历 (row + col) % 2 == 0 的棋盘颜色。
# 1 -> 优先遍历另一种颜色。
TEST_HUNT_PARITY = 0

# 当前按“潜艇周围一圈不会出现其他潜艇”的规则排除格子。
TEST_USE_SAFETY_RULE = True

# GUI 临时显示参数。
TEST_BOARD_VIEW_WIDTH = 620
TEST_BOARD_VIEW_HEIGHT = 300
TEST_BOARD_VIEW_PADDING = 20
TEST_BOARD_SHOW_COORDS = True
TEST_BOARD_REFRESH_MS = 120
