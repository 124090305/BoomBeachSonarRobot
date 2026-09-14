# 运行时棋盘定位与状态识别

## 需求与边界

- 棋盘允许小幅平移、缩放和透视变化，回拖后无需逐像素重合。
- 逻辑格号保持 GUI 的行、列规则；代码内部从 0 开始，人工工具显示从 1 开始。
- 每次点击和重启后的 HIT 重放都重新定位，两帧几何稳定后才能点击。
- before、after 和补拍帧分别定位，统一还原到基准视角，复用原单格识别算法。
- 全局识别复用同一定位核心，继续输出 UNKNOWN/MISS/HIT/SUNK、质量与复核信息。
- 定位失败不使用旧坐标兜底，也不进入自动重启后继续点击的恢复链。
- 自动拖动仍属于独立实验，本次不启用自动拖动。

## 定位方法

`vision/board_geometry.py` 先提取棋盘外轮廓，以左右和下方外角固定格号，避免重复网格错配到相邻格。部分外角已探测时，可用仍可见的长外边求交补足角点；外边缺失时拒绝推算。

外轮廓粗定位后，复用 `align_board()` 做受限局部网格匹配和 RANSAC 透视配准。最终检查外角误差、网格覆盖、置信度、面积变化、画面边界和变换方向。失败会抛出 `BoardGeometryError`。

这是有界定位能力。它依赖当前关卡配置、同分辨率空棋盘参考图和足够可见的外轮廓/网格；整条外边消失、大幅拖出画面、遮挡严重时会停止。关卡号仍由当前运行上下文提供，本次没有增加关卡 OCR。

## 正式流程

`create_level_state()` 为每关装配独立 `RuntimeBoardLocator`，参考图在当前实例内缓存。永久 `board_quad` 不变。

一发探测：

1. 原流程确认页面并选格，保存 before 截图。
2. 复用 before 做定位，再采一帧确认位置稳定；最后一帧作为实际 before。
3. 检查目标格可见，通过 `SonarBoard.set_screen_quad()` 一次更新当前实例全部坐标，点击该格。
4. 沿用退出/重新进入活动的流程，保存 after，重新定位并更新当前坐标快照。
5. before/after 各自变换到基准视角，在同一基准格中心调用原识别器。模糊结果追加帧也重新定位。
6. 原有 HIT/MISS/SUNK 策略写回和恢复流程继续执行；识别与策略写入仍在同一不可中断区内。

定位期间响应停止；正式识别开始后，仍先完成结果与策略同步，再响应停止。几何异常向 UI 原有错误处理传递，不自动重启游戏。UI 原有异常退出网络清理仍会执行。

纯逻辑 `SonarBoard` 默认不装配定位器，既有离线测试和自定义手动映射接口保持可用；自行构造真实点击流程时，应使用 `create_level_state()` 或显式装配 `RuntimeBoardLocator`。

## 全局状态识别

人工 UI 识别和暂停后自动校准通过 `recognize_current_board()` 启用运行时定位。各帧复用原整盘状态算法和多帧投票，并额外审核末尾帧坐标是否稳定。

识别结果仍先进入人工待编辑缓存，撤回/重做和应用流程不变。暂停后是否做整盘状态校准仍按原有一次性人工应用标记决定；无论是否跳过状态校准，正式点击前都会重新定位。

首次启动、新关卡和日常每发不新增整盘状态覆盖。若程序棋盘与游戏事实可能不同，应先使用人工全局识别并应用，或走已有暂停恢复校准。坐标校准只更新映射，不推断或改写棋盘事实。

空参考图自身被文字遮挡的格子仍保留低可信标记，坐标定位成功不代表遮挡内容已经可靠识别。

## 参数与速度

参数集中于 `BoardGeometryConfig`：最大移动为画面高度的 18%，面积变化上限 30%，外角误差上限为格宽的 8%，两帧四角最大漂移 2.5px。目标点击区域还检查文字遮挡和屏幕边界。

优先复用已有截图和参考图，不增加固定等待；每发点击前增加一张稳定性检查截图。几何不稳定直接拦截，不无期限补拍。实际耗时需在活动开放后的设备上测量。

## 验收入口

历史截图离线检查：

```powershell
.venv\Scripts\python.exe -X utf8 tests/manual_runtime_board_geometry_test.py --level 25 --image "原始截图路径.png" --cell 1 1
```

活动开放后只读实机检查：

```powershell
.venv\Scripts\python.exe -X utf8 tests/manual_runtime_board_geometry_test.py --level 25 --live --cell 1 1
.venv\Scripts\python.exe -X utf8 tests/manual_live_global_board_recognition_test.py --level 25 --audit-auto
```

输出包含当前四角、所有格点、叠加坐标图、归一化截图、质量和待复核格。上述入口不点击、不拖动、不修改网络、不更新正式棋盘。

2026-09-11：已用 25 关历史拖动前、拖动后和回拖截图检查定位叠加；三种视角均通过几何校验。活动未开放，当前版本尚未完成真实点击和实时恢复联调；不得将离线通过视为零误点保证。

全量回归：`python -m unittest discover -s tests -p "test_*.py" -q`，231 项通过，其中新增 19 项覆盖坐标映射、平移/缩放/透视、缺角与缺边、遮挡、稳定性、前后截图、补帧、重放及失败不重启。GUI 测试退出时出现 Tk `after` 回调告警，测试结果仍为 OK；本次未改动 GUI 关闭代码。

## 文件范围

- 新增：`vision/board_geometry.py`、`flows/board_geometry_flow.py`。
- 接入：`flows/probe_flow.py`、`flows/auto_probe_flow.py`、`flows/auto_probe_loop.py`、`flows/level_loop.py`、`flows/board_sync_flow.py`、`sonar/board.py`、`vision/board_live.py`、`vision/board_recognition.py`。
- 测试：`tests/test_board_geometry.py`、`tests/test_runtime_probe_geometry.py`、`tests/manual_runtime_board_geometry_test.py`。
- 原有拖动实验三个未跟踪文件保持原样；本次未修改策略、网络恢复、胜利或 GUI 主体。
