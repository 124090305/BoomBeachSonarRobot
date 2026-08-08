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

# =========================================================
# 单发真实探测测试
# =========================================================

# 参考项目退出活动后重新进入时，会先等待并点击主岛活动按钮，
# 然后点击活动列表右下角的进入按钮。
TEST_ACTIVITY_BUTTON_TEMPLATE = "activity_button.png"
TEST_QUIT_ACTIVITY_TEMPLATE = "quit_activity.png"

# 1280x720 下参考项目使用的活动详情入口固定坐标。
TEST_ACTIVITY_DETAIL_ENTRY_POINT = (
    1205,
    644,
)

# 进入活动详情后，用一个棋盘外的安全点关闭
# “点击任意地方开始”提示。
TEST_ACTIVITY_TAP_TO_START_POINT = (
    300,
    140,
)

# 页面等待时间。
TEST_ACTIVITY_BUTTON_TIMEOUT = 20.0
TEST_ACTIVITY_DETAIL_READY_TIMEOUT = 15.0
TEST_PROBE_DETAIL_READY_TIMEOUT = 6.0

# 页面动作之间的短等待。
TEST_ACTIVITY_BUTTON_CLICK_DELAY = 0.4
TEST_ACTIVITY_DETAIL_ENTRY_DELAY = 0.7
TEST_ACTIVITY_TAP_TO_START_DELAY = 0.4
TEST_ACTIVITY_TAP_TO_START_AFTER_DELAY = 0.5
TEST_PROBE_AFTER_CLICK_DELAY = 0.3

# GUI 临时显示参数。
TEST_BOARD_VIEW_WIDTH = 620
TEST_BOARD_VIEW_HEIGHT = 300
TEST_BOARD_VIEW_PADDING = 20
TEST_BOARD_SHOW_COORDS = True
TEST_BOARD_REFRESH_MS = 120
