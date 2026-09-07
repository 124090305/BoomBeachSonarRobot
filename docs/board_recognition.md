# 全局棋盘识别：单帧核心与实时接入

入口：`vision.board_recognition.recognize_board(empty_reference, current_screenshot, level_config=...)`。

只输入空基准、当前单帧和静态关卡配置。识别器不创建或修改 SonarBoard，不使用 pending、历史探测、策略推理、HIT/MISS 模板、ADB、网络或 Tkinter。单格 diamond_hit 及正式自动循环保持原样。

## 运行

在项目根目录执行：

```powershell
.venv\Scripts\python.exe tests\manual_global_board_recognition_test.py --image "D:\xxx\screen.png" --level 10
.venv\Scripts\python.exe tests\manual_global_board_recognition_test.py --image "D:\xxx\screen.png" --level 10 --reference "D:\xxx\empty.png"
.venv\Scripts\python.exe tests\manual_global_board_recognition_test.py
```

无参数会询问图片路径、关卡和可选基准。终端行列从 1 开始，与 GUI 标签一致；API、JSON 中 row/col 从 0 开始，与 CellState/策略接口一致。`--output` 可指定空目录。退出码：0=结果通过总体质量门槛；1=输入或输出错误；2=已生成结果，但总体质量不足。

每轮默认保存到 `outputs/manual_global_board/<时间戳>/`，包含原图、配准图、空基准、原比例 overlay、透视展开 overlay、差异、船体归属 mask、遮挡 mask、完整 JSON。红色边框及 `!` 表示复核；绿色粗框表示通过结构校验的 SUNK。结果目录禁止覆盖。outputs 已加入 Git 忽略规则。

## 流程与判定

1. 从基准中的每格实际亮边抽取锚点，在当前图对应位置附近有限搜索。RANSAC 排除错配，再检查锚点覆盖、残差、四角位移和面积变化。
2. 把当前图变换到基准坐标；沿用现有四角顺序和逻辑行列，将菱形盘透视展开成正方形格。自动测试逐格核对与 SonarBoard 中心映射一致。
3. 用匹配亮边做有界亮度补偿。逐格比较亮边保留、Lab 颜色、HSV 饱和度和亮度，提取相对空基准新增的中性前景及纹理。
4. UNKNOWN 证据来自未探测亮框和基准相似性；MISS 来自开格边框减弱、水面变化及船体证据缺失；HIT 来自新增中性船体、轮廓/纹理与开格证据。完整亮框会压低浪花导致的假船体分。
5. 对船体统一进行立体落点回投。明确的长轴与主体行/列占比用于减少船壳擦入邻格的归属错误。
6. 对每个船体连通块提取 H/V 方向、同一直线格支持、逐边界连接宽度和全段覆盖。只有真实连接、长度合法、数量未超限且无重叠/安全间距冲突的候选进入 SUNK。不会根据缺少船体证据的其他格补全潜艇。

H/V 使用棋盘逻辑坐标：H 为同一行，V 为同一列。屏幕上的两条轴随菱形棋盘倾斜。

UNKNOWN 始终是“未探测”候选状态。不确定性使用 confidence、needs_review、reason、state_scores 和 feature_scores。对齐失败后输出仅为低可信候选，全盘 valid=False；禁止用这类矩阵自动同步棋盘。

## 置信度与质量

基础置信度综合最高状态分、前两名分差和证据一致性，再乘配准质量、当前遮挡、基准可观测性。SUNK 会重新计算排他状态分及结构证据。失败/冲突另设置信度上限。大量复核格会使 valid=False。

confidence 是统一的证据可靠性分，当前没有人工标注集支持概率校准。0.9 不代表已验证 90% 正确率。quality_score 结合配准、遮挡及逐格置信度；quality 是素材类别，valid 是整盘质量门槛，二者用途不同。

文字预审使用横排白色描边字符组；面板预审使用大面积低饱和、低方差连通区域。它们可以发现部分弹窗与脏截图，无法保证覆盖全部有色/半透明遮挡。海面大幅变化、密集船体导致网格不足、错误关卡、裁剪或不同分辨率会造成降级或明确报错。

## 素材预审

```powershell
.venv\Scripts\python.exe tests\audit_board_screenshots.py --level 11 --recognize-limit 24
```

先为目录全部图片写 `quality.jsonl`，分为 usable、alignment_suspicious、occluded、wrong_page、unusable；然后均匀选取 usable 素材执行完整识别。生成类别联系表、识别 debug 及 summary.json。目录截图无标签，因此这些统计只描述素材预审和算法输出。默认按 11 关的 10×10 几何审查；其他关卡必须显式指定。

## 参数

全部主要参数集中于 `vision/board_types.py` 的 `BoardRecognitionConfig`。每个字段的 metadata.help 说明作用和增大效果，减小效果相反。结果 JSON 保存本轮全部参数，便于复现。

优先调节顺序：

1. alignment_*：锚点强度、搜索半径、误差、覆盖、四角位移；先确认格点确实对齐。
2. border_band、border_tolerance_px、inner_margin：边框采样与残余偏差容忍。
3. ship_*、intact_border_ship_penalty：金属分割、浪花抑制、立体回投和宽船体归属。
4. sunk_*：短艇轴比、跨边界宽度、可见长度及结构置信门槛。
5. text_*、panel_*、occlusion_*：文字、面板与可见性。
6. review_*、confidence_weights、max_review_fraction：复核门槛；应使用人工标签校准，勿为减少红框盲目降低。

## 验证边界

合成测试验证输入输出契约、几何不变性和设计的边界情况。真实基准平移/亮度测试验证空盘稳定性。无标签实机抽查用于找明显错误和观察结构，不足以证明任意画面的分类准确率。

后续最有价值的标注：每关全空原图；孤立 MISS、普通 HIT；两方向各长度完整潜艇；同一画面完整格子矩阵与潜艇起止格；标题遮挡、半透明弹窗、强浪花、不同亮度、轻微移位样本。第一阶段不自动写回任何正式状态。

## UI 与恢复循环接入

人工干预工具栏中的“识别当前棋盘”执行以下流程：检查活动棋盘页面，后台连续采集 3 帧，逐帧调用同一套单帧核心，检查状态一致性，再将结果一次性覆盖到 `ManualEditSession`。有分歧或末尾画面失效时，最多补到 5 帧。识别按钮保持 BUSY（灰色、下沉、禁用），同时锁住棋盘、撤回/重做、应用、取消、退出、设备/关卡切换和网络/重启操作。关闭窗口会通知识别停止，并沿用原退出清理流程。

识别结果仍是待应用修改；红框及问号表示需复核格，悬停可查看置信度及原因。顶部显示当前预览的质量摘要；不叠加旧正式策略的排除区域。用户可继续修正；应用时如仍有复核标记，会再次要求确认。一次成功识别对应一条撤回／重做记录，状态相同的再次识别也保留完整操作记录。历史同时保存状态、潜艇段、置信度、原因和复核标记。失败不增加历史，不修改人工缓存和正式棋盘。

多帧合并要求同一完整 SUNK 船段得到多数支持，船段分歧不会被单格 SUNK 投票掩盖。置信度使用支持帧均值并按一致性降低；任一可用帧的复核提示都会保留。末尾连续画面必须可用；合并后重新检查复核格比例。固定文字遮挡不会因重复拍摄而自动消失。每张参与分析的原图同时接受页面检测；结束前再次检查页面。参数集中在 `sonar_config.py` 的 `GlobalBoardSyncConfig`。

自动循环停止或异常退出后，`BoardSyncState` 开启一次恢复校准周期。暂停期间成功执行“应用修改”，下一次启动采用人工结果并消费标记。标记绑定棋盘对象、版本、关卡和设备；重置、重启或切换上下文会使旧审核失效。临时编辑、撤回、取消、退出均不构成人工审核；成功应用后再取消一批新临时编辑，不影响已经生效的正式审核。首次启动保留原行为。

没有有效人工应用时，循环线程先识别并严格审核：页面、末帧、总体质量、任何时间状态分歧、低可信已探测格、严重不确定 UNKNOWN 和潜艇结构冲突均可阻止接管。随后先在一次性模型中运行现有策略重建，再复用策略合法摆放集合检查剩余船队至少存在一种兼容布局；无解或搜索超过 `feasibility_node_limit` 均要求人工处理。搜索只用于审核，不据此猜填遮挡格。最终使用现有 `apply_manual_edits` 事务提交，保留唯一合法 HIT 解释的逻辑 SUNK 确认。

采帧、审核过程中可停止且不修改正式状态；进入正式棋盘写回后，完整完成棋盘与策略同步再响应停止。原单格识别的原子边界保持不变。审核失败不会进入探测循环；非用户停止的退出仍沿用原网络清理行为。页面停在主岛或弹窗时，需要先人工回到活动棋盘。

实机只读联调命令：

```powershell
.venv\Scripts\python.exe -X utf8 tests\manual_live_global_board_recognition_test.py --level 11
.venv\Scripts\python.exe -X utf8 tests\manual_live_global_board_recognition_test.py --level 25 --audit-auto
```

该入口只读取 ADB 实时截图，不点击页面、不修改网络、不写正式棋盘。`--audit-auto` 在一次性内存模型中额外验证自动接管，拒绝时退出码为 2。每轮调试保存到 `outputs/global_board_sync/<时间戳>/`：`frame_XX/` 为逐帧原图、overlay 和特征；`live_result.json` 为最终合并结果及本轮配置。逐帧 overlay 不代表合并后的最终状态，请结合 JSON/UI 查看。

## 接入阶段验证（2026-09-07）

- 先完整阅读当前源码、测试及既有单帧实现；保留工作区已有的接入改动。进入本轮时 167 项基线测试通过；本轮新增 33 项回归测试，完整 200 项通过，包含真实 Tk 控件的预览、历史和应用路径。
- 新增覆盖：自动补帧、坏末帧、遮挡提示保留、合并质量重新审核、完整撤回/重做、失败无历史、非法/无空间船队、搜索超限、正式写回原子性、BUSY 锁定、线程启动失败、关闭、人工审核消费与失效、异常退出后的重新校准。原停止、网络恢复、胜利及多关测试继续通过。
- 实机只读采集：`emulator-5554` 主岛页面被正确识别；用户切换到第 25 关后获得 3 张活动棋盘帧，输出全部 UNKNOWN，时间状态一致率 1.0，顶部文字遮挡的 3 格保持复核标记。调试目录：`outputs/global_board_sync/20260907_144245_125866/`。
- 第二次实机复测时设备已断开，未继续点击或修改网络。使用上述 3 张原始实机帧离线回放完整实时合并/自动审核：因 (1,1)、(1,2)、(2,1) 低可信而拒绝接管，正式棋盘快照保持不变。未执行真实自动探测闭环，未验证非空实机盘的分类准确率。
- 静态编译、启动脚本 `--check`、`git diff --check` 通过。首次编译受现有缓存写权限影响，批准后重新编译通过。

本阶段文件：

- `vision/board_live.py`、`vision/__init__.py`：实时合并及导出。
- `flows/board_sync_flow.py`、`flows/board_sync_state.py`、`flows/sonar_page.py`、`flows/__init__.py`：共用接入、审核、事务及恢复周期。
- `sonar/manual_intervention.py`、`sonar_config.py`：完整编辑历史和集中参数。
- `ui/gui_app.py`、`ui/app_layout.py`、`ui/auto_loop_bridge.py`、`ui/board_view.py`：按钮、后台队列、锁定、复核显示和恢复接管。
- `tests/test_board_live.py`、`tests/test_board_sync_flow.py`、`tests/test_board_sync_safety.py`、`tests/test_global_board_integration.py`、`tests/test_manual_intervention.py`、`tests/test_gui_close.py`、`tests/test_public_api.py`、`tests/manual_live_global_board_recognition_test.py`：测试和只读实机入口。
- 本说明文件。未改动单格检测、探测循环、网络恢复、胜利及多关主体。

## 本轮验证记录（2026-09-02）

- 基线为 `36053442298a804159573a59aa2f2902a06c5d99`，该工作区没有旧版全局实验代码。本实现独立新增；稳定的 diamond_hit、board、strategy、flows、controllers、ui 均未修改。
- 1～11 关基准均与用户提供的源文件 SHA256 一致；12 关以后沿用第 11 关。真实空盘逐关施加平移和亮度变化后，测试仍输出全部 UNKNOWN。
- 完整自动测试命令：`.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'`。148 项全部通过，包括新增的 28 项全局识别测试和原有识别、策略、恢复、停止原子性测试。
- 素材目录共 1052 张图片，统一按第 11 关几何进行启发式预审：usable 1048、occluded 2、alignment_suspicious 2、wrong_page 0、unusable 0。人工抽查了类别联系表及若干完整图；未逐张人工标注。
- 两张 occluded 图片含连接中断弹窗。两张 alignment_suspicious 图片分别涉及关卡几何不匹配和较大位置偏移。没有把这四张图片纳入正常识别抽样。
- 从 usable 中均匀选取 24 张完成识别并保存 debug。统计及逐图结果在 `outputs/material_audit/verified/summary.json`，全部素材预审记录在同目录 `quality.jsonl`。
- 独立示例 `probe_20260809_163912_314116_r0_c0_after.png` 输出 UNKNOWN=45、MISS=40、HIT=1、SUNK=14，包含长度 2/3/4/5 的四艘潜艇，14 格提示复核。这是算法输出，未作为准确率证据。
- 迭代修正了文字与网格混淆、立体船体邻格归属、短艇轴比、完整亮框上的浪花误判、弹窗分类及共享连通块的多解冲突。
- 静态编译、启动脚本 `--check` 与 `git diff --check` 已通过。未连接模拟器或执行点击、网络修改、棋盘写回。
