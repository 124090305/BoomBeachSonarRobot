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
# 初始进入活动 + 页面状态检验
# =========================================================

# 主岛活动按钮。
TEST_ACTIVITY_BUTTON_TEMPLATE = "activity_button.png"

# 声纳浮标“参加”图标 / 文字。
# 这两个模板需要从参考项目 template/ 目录下载。
TEST_SONAR_TEMPLATE = "sonar_join.png"
TEST_SONAR_LABEL_TEMPLATE = "sonar_join_label.png"

# 声纳位于动态水面上，参考项目使用较低阈值。
TEST_SONAR_MATCH_THRESHOLD = 0.60

# 主岛和声纳等待时间。
TEST_HOME_READY_TIMEOUT = 45.0
TEST_SONAR_WAIT_TIMEOUT = 60.0

# 主岛上划：1280x720 下参考项目使用的中心上划。
TEST_HOME_SWIPE_START = (
    640,
    500,
)
TEST_HOME_SWIPE_END = (
    640,
    200,
)
TEST_HOME_SWIPE_DURATION_MS = 800

# 点击活动按钮进入活动列表后，上划两次露出声纳活动入口。
TEST_ACTIVITY_LIST_SWIPE_START = (
    1000,
    660,
)
TEST_ACTIVITY_LIST_SWIPE_END = (
    1000,
    180,
)
TEST_ACTIVITY_LIST_SWIPE_DURATION_MS = 300
TEST_ACTIVITY_LIST_SWIPE_COUNT = 2
TEST_ACTIVITY_LIST_BEFORE_SWIPE_DELAY = 0.4
TEST_ACTIVITY_LIST_SWIPE_INTERVAL = 0.2

# 初次进入活动列表后开启弱网，给规则一点生效时间。
TEST_INITIAL_WEAK_APPLY_DELAY = 0.2

# =========================================================
# 单发真实探测测试
# =========================================================

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

# =========================================================
# 自动完整一发：识别 + REJECT + retry + 恢复
# =========================================================

TEST_RETRY_TEMPLATE = "retry.png"
TEST_RETRY_WAIT_TIMEOUT = 20.0
TEST_RETRY_MATCH_THRESHOLD = 0.85
TEST_RETRY_BEFORE_CLICK_DELAY = 0.1
TEST_RETRY_AFTER_CLICK_DELAY = 0.5

# retry 等待超时时，保存等待期间相似度最高的那一帧。
TEST_RETRY_FAILURE_DIR_NAME = "retry_failure"

# 自动单发截图保存目录名。
TEST_AUTO_PROBE_DIR_NAME = "auto_probe"

# 当前 diamond_hit 参数沿用已经完成真实联调的第一版配置。
TEST_DIAMOND_W = 80
TEST_DIAMOND_H = 56
TEST_DIAMOND_SEARCH_RADIUS = 14
TEST_DIAMOND_DEBUG_DIR_NAME = "diamond_hit_debug"

# GUI 临时显示参数。
TEST_BOARD_VIEW_WIDTH = 620
TEST_BOARD_VIEW_HEIGHT = 300
TEST_BOARD_VIEW_PADDING = 20
TEST_BOARD_SHOW_COORDS = True
TEST_BOARD_REFRESH_MS = 120
