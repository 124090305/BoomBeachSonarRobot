# 现用功能与阶段命名清单

扫描基线：`main` · `44fd3b76ce326b0871793c8986ba7013a1c39982` · 2026-09-26T21:47:10+08:00。

本文件记录现用名称，已按用户确认更新显示文案；改名结果见文末。所有“修改后名称”继续留空，供下一轮填写。分组标题均为**整理用标题**，只有表中“当前名称原文”代表程序原文；“当前未单独命名”是现状说明。

## 功能目录与主要流程（整理用标题）

日常入口包括设备与截图、网络控制、关卡与自动循环、人工测试模式、棋盘与策略、人工干预改盘、停止与退出；独立联调、离线识别和演示列在附录。当前主界面没有独立菜单栏，操作通过按钮、开关、关卡选择器及弹窗进行。

主要流程：启动主窗口 → 选择设备和起始关卡 → 可选开启“人工测试模式” → 点击“启动循环” → 判断页面并进入活动 → 策略选格、保存 before、点击、退出重进、保存 after → 自动识别或人工回答 → 完整登记棋盘、策略及计数 → HIT 联网等待或 MISS 断网／retry 恢复 → 下一发 → 策略完成、胜利处理 → 创建下一关棋盘与策略。异常按原重启恢复路径处理；停止与关闭按原安全边界退出。

人工测试模式只更换结果来源；等待型请求在同一弹窗持续更新真实截图，计时供参考。人工干预改盘是另一功能：完全停止后编辑临时棋盘 → 撤回／重做或取消 → 应用合法修改，应用后保持停止。

## 填写与定位说明

- 在最后一列填写新名称，或后续按 N 编号告知；当前合理名称也保留供核对。
- 动态文案保留源码占位符和格式；`f"…"`、多段字符串和 `%s` 是原表达式形式，实际界面会填入当前值。`<br>` 只用于表内展示换行，精确原文在 JSON 中。
- 相同用途的重复位置可合并；同名但不同按钮、答案用途、图例与悬停、标题与正文分别登记。关联编号供一起检查，不表示默认一并改名。
- 位置栏列出首要位置及定位数量，JSON 的 `locations` 登记全部可编辑显示位置，`related_locations` 记录判断依赖、测试、同文引用和说明文档；后者默认不自动修改。
- 普通临时变量不逐项罗列；内部状态、函数／类、配置常量、结构字段、文件路径和命令行参数在索引与附录中独立维护。

## 扫描范围与统计

- 完整读取 98 个源码、配置、启动器和说明文件，其中 Python 90 个，共 23,132 行；解析 2,803 个顶层字符串节点。
- 主清单 548 项，独立工具及预留入口附录 407 项，共 955 个 N 编号、975 个显示／阶段定位；内部标识索引 1571 条，调用位置 4082 处。
- 文件范围：源码／配置／启动器 53 个、说明文档 3 个、独立工具／演示 13 个、自动测试 29 个。
- Git 范围：tracked=97、ignored_source_included=1；首次清单扫描前工作区干净，当前快照包含本次尚未提交的文案修改。忽略规则没有阻止读取 `.vscode/settings.json` 这类本地配置。
- 排除虚拟环境、第三方依赖目录、Git 元数据、缓存、截图、运行日志、`runtime/`、`outputs/` 历史产物、`tests/real_game_images/` 和其他图片／二进制素材；排除记录存入 JSON，目录排除不冒充逐文件统计。
- 本地已跟踪、未跟踪及忽略目录内的相关源码均按磁盘内容记录；本次校验值包含尚未提交的文案修改。每个相关文件保存原始字节 SHA-256，能识别同一提交下未提交内容变化。
- `docs/manual_trial.md`、`docs/board_recognition.md` 和素材说明已读取；其中历史验证数字、旧说明及未来计划没有当作现用功能名。

## 主清单

### 01 启动与主窗口通用提示（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N001 | 窗口标题<br><code>ui/gui_app.py:73</code><br>关联：N003, N004, N005, N006, N012 | <code>BoomBeach Sonar Robot</code> | 通过原启动入口打开主界面后，窗口标题栏显示的程序名称。 | |
| N002 | 界面文字<br><code>ui/app_layout.py:462</code><br>关联：N145 | <code>状态：</code> | 标注主窗口最近一次操作的总体状态。 | |
| N003 | 状态显示<br><code>ui/gui_app.py:97</code><br>关联：N001, N004, N005, N006, N012 | <code>等待操作</code> | 主窗口初始化后的总体状态，表示当前没有操作任务。 | |
| N004 | 状态显示<br><code>ui/gui_app.py:103</code><br>关联：N001, N003, N005, N006, N012, N483（其余见索引） | <code>已停止</code> | 循环尚未启动或后台已退出时，显示当前没有继续运行的循环。 | |
| N005 | 状态显示<br><code>ui/gui_app.py:106</code><br>关联：N001, N003, N004, N006, N012, N153（其余见索引） | <code>发数：0 &#124; HIT：0 &#124; MISS：0</code> | 新建窗口、切换关卡或模式以及启动循环时，把本次累计发数、命中和未命中显示为零。<br>注意：统计栏文字用于提取发数、HIT 和 MISS；标点与分隔符变化需同步核对解析。 | |
| N006 | 状态显示<br><code>ui/gui_app.py:109</code><br>关联：N001, N003, N004, N005, N012, N154（其余见索引） | <code>上一发：-</code> | 尚无本次循环可显示的上一发结果时，用横线占位。 | |
| N007 | 状态显示<br><code>ui/gui_app.py:1506</code> | <code>操作完成</code> | 主窗口的一次后台操作成功返回时更新总体状态。 | |
| N008 | 状态显示<br><code>ui/gui_app.py:1518</code><br>关联：N010, N013 | <code>操作失败</code> | 主窗口的一次后台操作返回异常时显示失败状态或错误窗口。 | |
| N009 | 弹窗标题<br><code>ui/gui_app.py:882</code><br>关联：N011 | <code>自动循环仍在退出</code> | 后台仍未退出、人工操作被暂时锁定时，标明本次提醒的主题。 | |
| N010 | 弹窗标题<br><code>ui/gui_app.py:1525</code><br>关联：N008, N013 | <code>操作失败</code> | 主窗口的一次后台操作返回异常时显示失败状态或错误窗口。 | |
| N011 | 弹窗正文<br><code>ui/gui_app.py:883</code><br>关联：N009 | <code>请等待自动循环在安全点停止后再执行人工操作。</code> | 后台仍未退出、人工操作被暂时锁定时，说明当前操作的条件、结果或注意事项。 | |
| N012 | 日志<br><code>ui/gui_app.py:153</code><br>关联：N001, N003, N004, N005, N006 | <code>GUI 已启动</code> | 主窗口和后台消息处理初始化完成后记录启动日志。 | |
| N013 | 日志<br><code>ui/gui_app.py:1521</code><br>关联：N008, N010 | <code>操作失败：%s</code> | 主窗口刷新操作状态或处理结果时，记录这一步的参数、结果或异常。 | |
| N014 | 日志<br><code>ui/gui_app.py:1536</code><br>关联：N015 | <code>%s</code> | GUI 操作日志的通用正文格式，实际消息由调用方传入。 | |
| N949 | 日志格式<br><code>logger.py:38</code><br>关联：N950, N951 | <code>%(asctime)s [%(levelname)s] %(name)s &#124; %(message)s</code> | 输出日志时组合时间、等级、模块名和正文，或指定对应时间的显示格式。 | |
| N950 | 日志格式<br><code>logger.py:39</code><br>关联：N949, N952 | <code>%H:%M:%S</code> | 输出日志时组合时间、等级、模块名和正文，或指定对应时间的显示格式。 | |
| N951 | 日志格式<br><code>logger.py:86；logger.py:91</code><br>关联：N949, N952, N953 | <code>%(asctime)s [%(levelname)s] %(name)s &#124; %(message)s</code> | 输出日志时组合时间、等级、模块名和正文，或指定对应时间的显示格式。 | |
| N952 | 日志格式<br><code>logger.py:87</code><br>关联：N950, N951, N953 | <code>%H:%M:%S</code> | 输出日志时组合时间、等级、模块名和正文，或指定对应时间的显示格式。 | |
| N953 | 日志格式<br><code>logger.py:92</code><br>关联：N951, N952 | <code>%Y-%m-%d %H:%M:%S</code> | 输出日志时组合时间、等级、模块名和正文，或指定对应时间的显示格式。 | |
| N015 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1534</code><br>关联：N014 | <code>[人工试运行] </code> | 把操作消息写入 GUI 日志时，组成界面提示或该步骤的诊断信息。<br>注意：人工日志前缀参与来源标记检查；不应连带改动内部 manual_trial 值。 | |
| N016 | 启动终端提示<br><code>启动程序.bat:8</code><br>关联：N017, N018, N019 | <code>Python environment not found:</code> | 启动检查或环境失败时在启动终端显示相应信息。 | |
| N017 | 启动终端提示<br><code>启动程序.bat:9</code><br>关联：N016, N018, N019 | <code>%SONAR_PYTHON%</code> | 启动检查或环境失败时在启动终端显示相应信息。 | |
| N018 | 启动终端提示<br><code>启动程序.bat:11</code><br>关联：N016, N017, N019 | <code>Create .venv and install requirements.txt first.</code> | 启动检查或环境失败时在启动终端显示相应信息。 | |
| N019 | 启动终端提示<br><code>启动程序.bat:31</code><br>关联：N016, N017, N018 | <code>Program exited with error code: %SONAR_EXIT_CODE%</code> | 启动检查或环境失败时在启动终端显示相应信息。 | |
| N020 | 校验或错误提示<br><code>logger.py:55</code> | <code>f"不支持的日志等级：{level}"</code> | 格式化和输出运行日志时，在输入或执行结果不符合条件时给出原因。 | |

### 02 设备、截图与游戏重启（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N021 | 界面文字<br><code>ui/app_layout.py:259</code> | <code>ADB 设备：</code> | 构建原主窗口操作区时，标注相应操作区或提示信息。 | |
| N022 | 按钮文案<br><code>ui/gui_app.py:208；ui/gui_app.py:209</code><br>关联：N023, N024, N028 | <code>正在重启…</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N023 | 按钮文案<br><code>ui/gui_app.py:210</code><br>关联：N022, N024, N028, N150 | <code>自动流程不可中断</code> | 该按钮在自动流程占用控制时显示锁定状态，循环停止仍按原安全边界处理。 | |
| N024 | 按钮文案<br><code>ui/gui_app.py:211</code><br>关联：N022, N023, N028 | <code>重启失败，点击重试</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N025 | 按钮文案<br><code>ui/app_layout.py:279</code> | <code>应用设备</code> | 将输入的 ADB 编号绑定到当前运行环境，保留棋盘和策略。 | |
| N026 | 按钮文案<br><code>ui/app_layout.py:301</code> | <code>检查设备</code> | 查询在线设备并检查当前编号是否可连接。 | |
| N027 | 按钮文案<br><code>ui/app_layout.py:310</code> | <code>获取截图</code> | 通过真实 ADB 保存当前画面，并报告保存路径和尺寸。 | |
| N028 | 按钮文案<br><code>ui/app_layout.py:319；ui/gui_app.py:206</code><br>共 3 处，完整位置见索引<br>关联：N022, N023, N024 | <code>重启游戏</code> | 恢复网络后关闭并重新启动游戏。 | |
| N029 | 按钮文案<br><code>ui/app_layout.py:329</code> | <code>打开截图目录</code> | 打开当前截图保存目录。 | |
| N030 | 弹窗标题<br><code>ui/gui_app.py:434</code><br>关联：N031, N032, N033, N034, N035, N036（其余见索引） | <code>人工干预中</code> | 手动切换 ADB 设备时，标明本次提醒的主题。 | |
| N031 | 弹窗标题<br><code>ui/gui_app.py:440</code><br>关联：N030, N032, N033, N034, N035, N036（其余见索引） | <code>自动循环运行中</code> | 手动切换 ADB 设备时，标明本次提醒的主题。 | |
| N032 | 弹窗标题<br><code>ui/gui_app.py:449</code><br>关联：N030, N031, N033, N034, N035, N036 | <code>设备编号为空</code> | 手动切换 ADB 设备时，标明本次提醒的主题。 | |
| N033 | 弹窗正文<br><code>ui/gui_app.py:435</code><br>关联：N030, N031, N032, N034, N035, N036 | <code>请先退出人工干预，再切换 ADB 设备。</code> | 手动切换 ADB 设备时，说明当前操作的条件、结果或注意事项。 | |
| N034 | 弹窗正文<br><code>ui/gui_app.py:441</code><br>关联：N030, N031, N032, N033, N035, N036 | <code>请先停止自动循环，再切换 ADB 设备。</code> | 手动切换 ADB 设备时，说明当前操作的条件、结果或注意事项。 | |
| N035 | 弹窗正文<br><code>ui/gui_app.py:450</code><br>关联：N030, N031, N032, N033, N034, N036 | <code>请输入 ADB 设备编号</code> | 手动切换 ADB 设备时，说明当前操作的条件、结果或注意事项。 | |
| N036 | GUI 日志<br><code>ui/gui_app.py:467</code><br>关联：N030, N031, N032, N033, N034, N035 | <code>f"已切换设备：{serial}"</code> | 手动切换 ADB 设备时，把这一步的操作及结果写入主窗口日志。 | |
| N037 | 日志<br><code>controllers/adb_controller.py:341；controllers/adb_controller.py:365</code><br>关联：N038, N073 | <code>ROOT 已就绪：adb-root</code> | 执行真实设备连接、截图、输入或应用命令时，记录这一步的参数、结果或异常。 | |
| N038 | 日志<br><code>controllers/adb_controller.py:376</code><br>关联：N037, N073 | <code>ROOT 已就绪：su-c</code> | 执行真实设备连接、截图、输入或应用命令时，记录这一步的参数、结果或异常。 | |
| N039 | 日志<br><code>controllers/adb_controller.py:495</code><br>关联：N052, N075, N076 | <code>获取游戏 UID：%s -&gt; %s</code> | 执行真实设备连接、截图、输入或应用命令时，记录这一步的参数、结果或异常。 | |
| N040 | 日志<br><code>controllers/game_controller.py:73</code><br>关联：N041 | <code>开始重启游戏：%s</code> | 恢复网络并重启游戏时，记录这一步的参数、结果或异常。 | |
| N041 | 日志<br><code>controllers/game_controller.py:102</code><br>关联：N040 | <code>游戏重启完成，已等待 %.1f 秒</code> | 恢复网络并重启游戏时，记录这一步的参数、结果或异常。 | |
| N042 | 日志<br><code>flows/screenshot_flow.py:32</code><br>关联：N043 | <code>开始截图检查流程</code> | 按原截图流程保存图像并检查尺寸时，记录这一步的参数、结果或异常。 | |
| N043 | 日志<br><code>flows/screenshot_flow.py:73</code><br>关联：N042 | <code>截图检查完成：设备=%s，尺寸=%sx%s，文件=%s</code> | 按原截图流程保存图像并检查尺寸时，记录这一步的参数、结果或异常。 | |
| N044 | 日志<br><code>ui/gui_app.py:1144</code> | <code>打开截图目录：%s</code> | 打开当前截图保存目录时，记录这一步的参数、结果或异常。 | |
| N045 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:77</code><br>关联：N067 | <code>ADB 控制器创建：serial=%s，adb=%s</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N046 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:114</code><br>关联：N047, N069 | <code>找到 adb.exe：%s</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N047 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:130</code><br>关联：N046, N069 | <code>从 PATH 找到 adb.exe：%s</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N048 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:188</code><br>关联：N049, N070 | <code>执行 ADB：%s</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N049 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:210</code><br>关联：N048, N070 | <code>ADB 返回码：%s</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N050 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:260</code> | <code>ADB 设备列表：%s</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N051 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:401</code><br>关联：N074 | <code>执行 ROOT shell：%s</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N052 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:454</code><br>关联：N039, N075, N076 | <code>使用缓存 UID：%s -&gt; %s</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N053 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:601</code><br>关联：N054, N077, N078, N079 | <code>保存模拟器截图：%s</code> | 保存并检查当前设备截图时，在启用 DEBUG 日志时记录细节。 | |
| N054 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:655</code><br>关联：N053, N077, N078, N079 | <code>截图保存完成：%s</code> | 保存并检查当前设备截图时，在启用 DEBUG 日志时记录细节。 | |
| N055 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:790</code> | <code>ADB 点击：(%s, %s)</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N056 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:815</code> | <code>ADB 滑动：(%s, %s) -&gt; (%s, %s)，%sms</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N057 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:886</code><br>关联：N086 | <code>启动应用：%s</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N058 | 日志（DEBUG，默认不显示）<br><code>controllers/adb_controller.py:931</code><br>关联：N087 | <code>关闭应用：%s</code> | 执行真实设备连接、截图、输入或应用命令时，在启用 DEBUG 日志时记录细节。 | |
| N059 | 日志（DEBUG，默认不显示）<br><code>controllers/game_controller.py:60</code><br>关联：N088 | <code>游戏安装检查通过：%s</code> | 管理游戏检查与重启时，在启用 DEBUG 日志时记录细节。 | |
| N060 | 显示组成文字／诊断消息<br><code>controllers/adb_controller.py:38</code> | <code>ADB 命令执行失败</code> | 执行真实设备连接、截图、输入或应用命令时，组成界面提示或该步骤的诊断信息。 | |
| N061 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:483</code> | <code>f"设备正常：{self.adb.serial}\n"<br>                f"在线设备：{devices}"</code> | 检查当前设备在线状态时，组成界面提示或该步骤的诊断信息。 | |
| N062 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:488</code> | <code>正在检查设备...</code> | 检查当前设备在线状态时，组成界面提示或该步骤的诊断信息。 | |
| N063 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:498</code> | <code>f"截图完成：{result.path}\n"<br>                f"尺寸：{result.width}x{result.height}"</code> | 保存并检查当前设备截图时，组成界面提示或该步骤的诊断信息。 | |
| N064 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:503</code> | <code>正在获取截图...</code> | 保存并检查当前设备截图时，组成界面提示或该步骤的诊断信息。 | |
| N065 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:516</code> | <code>网络已恢复，游戏已重启</code> | 恢复网络并重启游戏时，组成界面提示或该步骤的诊断信息。 | |
| N066 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:520</code> | <code>正在恢复网络并重启游戏...</code> | 恢复网络并重启游戏时，组成界面提示或该步骤的诊断信息。 | |
| N067 | 校验或错误提示<br><code>controllers/adb_controller.py:58</code><br>关联：N045 | <code>ADB 设备编号不能为空</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N068 | 校验或错误提示<br><code>controllers/game_controller.py:39</code><br>关联：N086, N087, N136 | <code>游戏包名不能为空</code> | 管理游戏检查与重启时，在输入或执行结果不符合条件时给出原因。 | |
| N069 | 校验或错误提示<br><code>controllers/adb_controller.py:142</code><br>关联：N046, N047 | <code>"没有找到 adb.exe。"<br>            f"已检查：{checked_paths}。"<br>            "请修改 config.py 中的 ADB_PATH。"</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N070 | 校验或错误提示<br><code>controllers/adb_controller.py:205</code><br>关联：N048, N049 | <code>"ADB 命令超时："<br>                f"{' '.join(command)}"</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N071 | 校验或错误提示<br><code>controllers/adb_controller.py:281</code><br>关联：N072 | <code>f"没有发现设备 {self.serial}。"<br>                "请先启动模拟器，并执行 adb devices 检查。"</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N072 | 校验或错误提示<br><code>controllers/adb_controller.py:286</code><br>关联：N071 | <code>f"设备 {self.serial} "<br>            f"当前状态为 {state}"</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N073 | 校验或错误提示<br><code>controllers/adb_controller.py:382</code><br>关联：N037, N038 | <code>当前模拟器没有可用 ROOT 权限。请先在雷电模拟器设置中开启 ROOT 权限。</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N074 | 校验或错误提示<br><code>controllers/adb_controller.py:395</code><br>关联：N051 | <code>特权命令不能为空</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N075 | 校验或错误提示<br><code>controllers/adb_controller.py:443</code><br>关联：N039, N052, N076, N085 | <code>应用包名不能为空</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N076 | 校验或错误提示<br><code>controllers/adb_controller.py:482</code><br>关联：N039, N052, N075 | <code>"没有找到游戏 UID："<br>                f"{package_name}"</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N077 | 校验或错误提示<br><code>controllers/adb_controller.py:615</code><br>关联：N053, N054, N078, N079, N080 | <code>"模拟器截图超时，"<br>                f"超过 {config.SCREENSHOT_TIMEOUT:g} 秒"</code> | 保存并检查当前设备截图时，在输入或执行结果不符合条件时给出原因。 | |
| N078 | 校验或错误提示<br><code>controllers/adb_controller.py:635</code><br>关联：N053, N054, N077, N079, N081 | <code>ADB 截图返回了空数据</code> | 保存并检查当前设备截图时，在输入或执行结果不符合条件时给出原因。 | |
| N079 | 校验或错误提示<br><code>controllers/adb_controller.py:648</code><br>关联：N053, N054, N077, N078 | <code>"截图文件没有有效内容："<br>                f"{path}"</code> | 保存并检查当前设备截图时，在输入或执行结果不符合条件时给出原因。 | |
| N080 | 校验或错误提示<br><code>controllers/adb_controller.py:686</code><br>关联：N077, N081, N082 | <code>"模拟器截图超时，"<br>                f"超过 {config.SCREENSHOT_TIMEOUT:g} 秒"</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N081 | 校验或错误提示<br><code>controllers/adb_controller.py:706</code><br>关联：N078, N080, N082 | <code>ADB 截图返回了空数据</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N082 | 校验或错误提示<br><code>controllers/adb_controller.py:724</code><br>关联：N080, N081 | <code>无法解码 ADB 返回的截图数据</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N083 | 校验或错误提示<br><code>controllers/adb_controller.py:740</code><br>关联：N084 | <code>"图片不存在："<br>                f"{image_path}"</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N084 | 校验或错误提示<br><code>controllers/adb_controller.py:759</code><br>关联：N083 | <code>"图片解码失败："<br>                f"{image_path}"</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N085 | 校验或错误提示<br><code>controllers/adb_controller.py:851</code><br>关联：N075 | <code>应用包名不能为空</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N086 | 校验或错误提示<br><code>controllers/adb_controller.py:882</code><br>关联：N057, N068, N087, N136 | <code>游戏包名不能为空</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N087 | 校验或错误提示<br><code>controllers/adb_controller.py:927</code><br>关联：N058, N068, N086, N136 | <code>游戏包名不能为空</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N088 | 校验或错误提示<br><code>controllers/game_controller.py:54</code><br>关联：N059 | <code>"设备中没有找到游戏包 "<br>                f"{self.package_name}。"<br>                "请确认 config.py 中的 GAME_PACKAGE_NAME。"</code> | 管理游戏检查与重启时，在输入或执行结果不符合条件时给出原因。 | |

### 03 网络控制与真实状态（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N089 | 按钮文案<br><code>ui/gui_app.py:219</code><br>关联：N090, N091, N092, N093, N100 | <code>关闭弱网</code> | 移除游戏应用的 DROP 网络规则。 | |
| N090 | 按钮文案<br><code>ui/gui_app.py:220</code><br>关联：N089, N091, N092, N093, N100 | <code>正在开启弱网…</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N091 | 按钮文案<br><code>ui/gui_app.py:221</code><br>关联：N089, N090, N092, N093, N100 | <code>正在关闭弱网…</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N092 | 按钮文案<br><code>ui/gui_app.py:222</code><br>关联：N089, N090, N091, N093, N097, N100 | <code>自动流程中</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N093 | 按钮文案<br><code>ui/gui_app.py:223</code><br>关联：N089, N090, N091, N092, N100 | <code>弱网状态未知</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N094 | 按钮文案<br><code>ui/gui_app.py:231</code><br>关联：N095, N096, N097, N098, N101 | <code>关闭断网</code> | 移除游戏应用的 REJECT 网络规则。 | |
| N095 | 按钮文案<br><code>ui/gui_app.py:232</code><br>关联：N094, N096, N097, N098, N101 | <code>正在开启断网…</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N096 | 按钮文案<br><code>ui/gui_app.py:233</code><br>关联：N094, N095, N097, N098, N101 | <code>正在关闭断网…</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N097 | 按钮文案<br><code>ui/gui_app.py:234</code><br>关联：N092, N094, N095, N096, N098, N101 | <code>自动流程中</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N098 | 按钮文案<br><code>ui/gui_app.py:235</code><br>关联：N094, N095, N096, N097, N101 | <code>断网状态未知</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N099 | 按钮文案<br><code>ui/app_layout.py:350</code> | <code>检查 ROOT</code> | 检查网络控制所需 ROOT 模式并读取游戏 UID。 | |
| N100 | 按钮文案<br><code>ui/app_layout.py:359；ui/gui_app.py:218</code><br>关联：N089, N090, N091, N092, N093 | <code>开启弱网</code> | 为游戏应用启用 DROP 网络规则。 | |
| N101 | 按钮文案<br><code>ui/app_layout.py:369；ui/gui_app.py:230</code><br>关联：N094, N095, N096, N097, N098 | <code>开启断网</code> | 为游戏应用启用 REJECT 网络规则。 | |
| N102 | 按钮文案<br><code>ui/app_layout.py:379</code> | <code>恢复网络</code> | 清除游戏应用的 DROP 和 REJECT 规则。 | |
| N103 | 按钮文案<br><code>ui/app_layout.py:388</code> | <code>网络状态</code> | 查询并显示设备中当前真实网络规则。 | |
| N104 | 状态显示<br><code>ui/gui_app.py:1422</code><br>关联：N105 | <code>正在读取弱网状态…</code> | 启动或循环结束后读取网络状态时，显示当前进度或操作结果。 | |
| N105 | 状态显示<br><code>ui/gui_app.py:1423</code><br>关联：N104 | <code>正在读取断网状态…</code> | 启动或循环结束后读取网络状态时，显示当前进度或操作结果。 | |
| N106 | 日志<br><code>controllers/network_controller.py:179</code><br>关联：N107 | <code>正在开启弱网 DROP</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，记录这一步的参数、结果或异常。 | |
| N107 | 日志<br><code>controllers/network_controller.py:209</code><br>关联：N106 | <code>弱网 DROP 已开启：UID=%s</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，记录这一步的参数、结果或异常。 | |
| N108 | 日志<br><code>controllers/network_controller.py:218</code><br>关联：N109 | <code>正在关闭弱网 DROP</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，记录这一步的参数、结果或异常。 | |
| N109 | 日志<br><code>controllers/network_controller.py:248</code><br>关联：N108 | <code>弱网 DROP 已关闭：UID=%s</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，记录这一步的参数、结果或异常。 | |
| N110 | 日志<br><code>controllers/network_controller.py:261</code><br>关联：N111 | <code>正在开启断网 REJECT</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，记录这一步的参数、结果或异常。 | |
| N111 | 日志<br><code>controllers/network_controller.py:291</code><br>关联：N110 | <code>断网 REJECT 已开启：UID=%s</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，记录这一步的参数、结果或异常。 | |
| N112 | 日志<br><code>controllers/network_controller.py:300</code><br>关联：N113 | <code>正在关闭断网 REJECT</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，记录这一步的参数、结果或异常。 | |
| N113 | 日志<br><code>controllers/network_controller.py:330</code><br>关联：N112 | <code>断网 REJECT 已关闭：UID=%s</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，记录这一步的参数、结果或异常。 | |
| N114 | 日志<br><code>controllers/network_controller.py:343</code><br>关联：N115 | <code>正在恢复游戏网络</code> | 手动清除游戏网络限制时，记录这一步的参数、结果或异常。 | |
| N115 | 日志<br><code>controllers/network_controller.py:376</code><br>关联：N114 | <code>游戏网络已恢复：UID=%s</code> | 手动清除游戏网络限制时，记录这一步的参数、结果或异常。 | |
| N116 | 日志（DEBUG，默认不显示）<br><code>controllers/network_controller.py:108</code><br>关联：N117, N137, N138 | <code>检查网络控制环境</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，在启用 DEBUG 日志时记录细节。 | |
| N117 | 日志（DEBUG，默认不显示）<br><code>controllers/network_controller.py:150</code><br>关联：N116, N137, N138 | <code>网络控制环境正常：ROOT=%s，UID=%s</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，在启用 DEBUG 日志时记录细节。 | |
| N118 | 日志（DEBUG，默认不显示）<br><code>controllers/network_controller.py:434</code> | <code>网络状态：弱网=%s，断网=%s</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，在启用 DEBUG 日志时记录细节。 | |
| N119 | 日志（DEBUG，默认不显示）<br><code>controllers/network_controller.py:485</code> | <code>ip6tables 可用：%s</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，在启用 DEBUG 日志时记录细节。 | |
| N120 | 日志（DEBUG，默认不显示）<br><code>controllers/network_controller.py:553</code><br>关联：N139 | <code>应用网络规则：command=%s，chain=%s，uid=%s，mode=%s，enabled=%s</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，在启用 DEBUG 日志时记录细节。 | |
| N121 | 显示组成文字／诊断消息<br><code>controllers/network_controller.py:52</code><br>关联：N122, N123 | <code>不可用</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，组成界面提示或该步骤的诊断信息。 | |
| N122 | 显示组成文字／诊断消息<br><code>controllers/network_controller.py:55</code><br>关联：N121, N123 | <code>开启</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，组成界面提示或该步骤的诊断信息。 | |
| N123 | 显示组成文字／诊断消息<br><code>controllers/network_controller.py:57</code><br>关联：N121, N122 | <code>关闭</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，组成界面提示或该步骤的诊断信息。 | |
| N124 | 显示组成文字／诊断消息<br><code>controllers/network_controller.py:61</code> | <code>f"游戏 UID：{self.uid}\n"<br>            f"弱网 IPv4：{mark(self.weak_ipv4)}\n"<br>            f"弱网 IPv6：{mark(self.weak_ipv6)}\n"<br>            f"断网 IPv4：{mark(self.reject_ipv4)}\n"<br>            f"断网 IPv6：{mark(self.reject_ipv6)}"</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，组成界面提示或该步骤的诊断信息。 | |
| N125 | 显示组成文字／诊断消息<br><code>controllers/network_controller.py:166</code> | <code>f"ROOT 模式：{root_mode}\n"<br>            f"游戏 UID：{uid}"</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，组成界面提示或该步骤的诊断信息。 | |
| N126 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:536</code> | <code>正在检查 ROOT...</code> | 核验设备 ROOT 与游戏 UID 时，组成界面提示或该步骤的诊断信息。 | |
| N127 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:558</code><br>关联：N128, N547 | <code>弱网 DROP 已开启</code> | 手动切换 DROP 弱网时，组成界面提示或该步骤的诊断信息。 | |
| N128 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:560</code><br>关联：N127, N548 | <code>弱网 DROP 已关闭</code> | 手动切换 DROP 弱网时，组成界面提示或该步骤的诊断信息。 | |
| N129 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:582</code><br>关联：N130, N549 | <code>断网 REJECT 已开启</code> | 手动切换 REJECT 断网时，组成界面提示或该步骤的诊断信息。 | |
| N130 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:584</code><br>关联：N129, N550 | <code>断网 REJECT 已关闭</code> | 手动切换 REJECT 断网时，组成界面提示或该步骤的诊断信息。 | |
| N131 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:594</code><br>关联：N551 | <code>游戏网络已恢复</code> | 手动清除游戏网络限制时，组成界面提示或该步骤的诊断信息。 | |
| N132 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:597</code> | <code>正在恢复游戏网络...</code> | 手动清除游戏网络限制时，组成界面提示或该步骤的诊断信息。 | |
| N133 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:610</code> | <code>正在检查网络状态...</code> | 读取设备上的真实网络规则时，组成界面提示或该步骤的诊断信息。 | |
| N134 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1333</code><br>关联：N135 | <code>正在开启网络控制...</code> | 修改网络规则并复核真实状态时，组成界面提示或该步骤的诊断信息。 | |
| N135 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1335</code><br>关联：N134 | <code>正在关闭网络控制...</code> | 修改网络规则并复核真实状态时，组成界面提示或该步骤的诊断信息。 | |
| N136 | 校验或错误提示<br><code>controllers/network_controller.py:85</code><br>关联：N068, N086, N087 | <code>游戏包名不能为空</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，在输入或执行结果不符合条件时给出原因。 | |
| N137 | 校验或错误提示<br><code>controllers/network_controller.py:121</code><br>关联：N116, N117, N138 | <code>"设备中没有找到游戏包 "<br>                f"{self.package_name}"</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，在输入或执行结果不符合条件时给出原因。 | |
| N138 | 校验或错误提示<br><code>controllers/network_controller.py:141</code><br>关联：N116, N117, N137 | <code>当前模拟器没有可用 iptables，无法控制游戏网络</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，在输入或执行结果不符合条件时给出原因。 | |
| N139 | 校验或错误提示<br><code>controllers/network_controller.py:548</code><br>关联：N120 | <code>"未知网络规则类型："<br>                f"{mode}"</code> | 读取或修改游戏应用的 DROP／REJECT 网络规则时，在输入或执行结果不符合条件时给出原因。 | |
| N140 | 校验或错误提示<br><code>ui/gui_app.py:1358</code><br>关联：N141 | <code>f"{operation_error}；真实网络状态复核失败：{state_error}"</code> | 修改网络规则并复核真实状态时，在输入或执行结果不符合条件时给出原因。 | |
| N141 | 校验或错误提示<br><code>ui/gui_app.py:1373</code><br>关联：N140 | <code>网络规则操作已返回，但真实状态与目标不一致</code> | 修改网络规则并复核真实状态时，在输入或执行结果不符合条件时给出原因。 | |
| N142 | 校验或错误提示<br><code>ui/gui_app.py:1417</code> | <code>无法读取真实网络状态</code> | 无法复核真实网络状态时，在输入或执行结果不符合条件时给出原因。 | |

### 04 关卡选择与循环启动（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N143 | 界面文字<br><code>ui/app_layout.py:397</code><br>关联：N144, N145 | <code>自动循环</code> | 构建原主窗口操作区时，标注相应操作区或提示信息。 | |
| N144 | 界面文字<br><code>ui/app_layout.py:410</code><br>关联：N143, N145 | <code>当前关卡：</code> | 构建原主窗口操作区时，标注相应操作区或提示信息。 | |
| N145 | 界面文字<br><code>ui/app_layout.py:435</code><br>关联：N002, N143, N144 | <code>状态：</code> | 标注自动循环当前运行状态。 | |
| N146 | 按钮文案<br><code>ui/level_selector.py:70</code> | <code>▼</code> | 打开起始关卡选择列表。 | |
| N147 | 按钮文案<br><code>ui/gui_app.py:243</code><br>关联：N148, N149, N150, N151, N152 | <code>停止循环</code> | 请求后台在最近安全动作边界退出并保留当前进度。 | |
| N148 | 按钮文案<br><code>ui/gui_app.py:244</code><br>关联：N147, N149, N150, N151, N152 | <code>正在启动…</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N149 | 按钮文案<br><code>ui/gui_app.py:245</code><br>关联：N147, N148, N150, N151, N152 | <code>正在停止…</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N150 | 按钮文案<br><code>ui/gui_app.py:246</code><br>关联：N023, N147, N148, N149, N151, N152 | <code>自动流程不可中断</code> | 该按钮在自动流程占用控制时显示锁定状态，循环停止仍按原安全边界处理。 | |
| N151 | 按钮文案<br><code>ui/gui_app.py:247</code><br>关联：N147, N148, N149, N150, N152 | <code>循环异常，点击重试</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N152 | 按钮文案<br><code>ui/app_layout.py:425；ui/gui_app.py:242</code><br>关联：N147, N148, N149, N150, N151 | <code>启动循环</code> | 从所选关卡的当前棋盘状态启动原后台自动流程。 | |
| N153 | 状态显示<br><code>ui/gui_app.py:416；ui/gui_app.py:915</code><br>关联：N005, N154, N155, N160, N284 | <code>发数：0 &#124; HIT：0 &#124; MISS：0</code> | 新建窗口、切换关卡或模式以及启动循环时，把本次累计发数、命中和未命中显示为零。<br>注意：统计栏文字用于提取发数、HIT 和 MISS；标点与分隔符变化需同步核对解析。 | |
| N154 | 状态显示<br><code>ui/gui_app.py:417；ui/gui_app.py:916</code><br>关联：N006, N153, N155, N160, N285 | <code>上一发：-</code> | 尚无本次循环可显示的上一发结果时，用横线占位。 | |
| N155 | 状态显示<br><code>ui/gui_app.py:418</code><br>关联：N153, N154, N160 | <code>f"已切换到第 {actual_level} 关"</code> | 用户在停止状态下切换内部关卡并重建棋盘与策略时，显示当前进度或操作结果。 | |
| N156 | 状态显示<br><code>ui/gui_app.py:914</code><br>关联：N157, N158, N159, N161 | <code>启动中</code> | 启动原后台多关循环时，显示当前进度或操作结果。 | |
| N157 | 状态显示<br><code>ui/gui_app.py:917</code><br>关联：N156, N158, N159, N161 | <code>自动循环启动中...</code> | 启动原后台多关循环时，显示当前进度或操作结果。 | |
| N158 | 弹窗标题<br><code>ui/gui_app.py:899</code><br>关联：N030, N156, N157, N159, N161, N416 | <code>人工干预中</code> | 启动原后台多关循环时，标明本次提醒的主题。 | |
| N159 | 弹窗正文<br><code>ui/gui_app.py:900</code><br>关联：N156, N157, N158, N161 | <code>请先退出人工干预，再启动自动循环。</code> | 启动原后台多关循环时，说明当前操作的条件、结果或注意事项。 | |
| N160 | GUI 日志<br><code>ui/gui_app.py:420</code><br>关联：N153, N154, N155 | <code>f"人工切换关卡完成：内部关卡={actual_level}；新棋盘和新策略已初始化。"</code> | 用户在停止状态下切换内部关卡并重建棋盘与策略时，把这一步的操作及结果写入主窗口日志。 | |
| N161 | GUI 日志<br><code>ui/gui_app.py:919</code><br>关联：N156, N157, N158, N159 | <code>自动循环启动：停止请求会在最近的安全可中断点生效。</code> | 启动原后台多关循环时，把这一步的操作及结果写入主窗口日志。 | |
| N162 | 日志<br><code>flows/auto_probe_loop.py:225</code><br>关联：N163, N168 | <code>连续自动探测循环开始</code> | 连续执行当前关卡的探测并累计结果时，记录这一步的参数、结果或异常。 | |
| N163 | 日志<br><code>flows/auto_probe_loop.py:305</code><br>关联：N162, N168 | <code>连续循环第 %s 发完成：cell=%s -&gt; %s，next=%s</code> | 连续执行当前关卡的探测并累计结果时，记录这一步的参数、结果或异常。 | |
| N164 | 显示组成文字／诊断消息<br><code>ui/level_selector.py:18</code><br>关联：N165, N167 | <code>第11关+</code> | 选择第 11 关起始档位，运行中的更高关卡也统一显示这一档。<br>注意：关卡显示被 level_from_label 解析，文案与解析需作为同一变更核对。 | |
| N165 | 显示组成文字／诊断消息<br><code>ui/level_selector.py:19</code><br>关联：N164, N167 | <code>f"第{actual_level}关"</code> | 显示并解析用户选择的起始关卡时，组成界面提示或该步骤的诊断信息。<br>注意：关卡显示被 level_from_label 解析，文案与解析需作为同一变更核对。 | |
| N166 | 校验或错误提示<br><code>ui/level_selector.py:47</code> | <code>visible_rows 必须大于 0</code> | 显示并解析用户选择的起始关卡时，在输入或执行结果不符合条件时给出原因。 | |
| N167 | 校验或错误提示<br><code>ui/level_selector.py:16</code><br>关联：N164, N165, N169 | <code>关卡编号必须大于 0</code> | 显示并解析用户选择的起始关卡时，在输入或执行结果不符合条件时给出原因。 | |
| N168 | 校验或错误提示<br><code>flows/auto_probe_loop.py:223</code><br>关联：N162, N163 | <code>max_rounds 必须大于 0</code> | 连续执行当前关卡的探测并累计结果时，在输入或执行结果不符合条件时给出原因。 | |
| N169 | 校验或错误提示<br><code>sonar_config.py:157</code><br>关联：N167 | <code>关卡编号必须大于 0</code> | 按关卡建立棋盘配置时，在输入或执行结果不符合条件时给出原因。 | |
| N170 | 校验或错误提示<br><code>ui/auto_loop_bridge.py:48</code> | <code>自动循环运行中，无法切换运行上下文</code> | 后台执行原循环并向主线程投递消息时，在输入或执行结果不符合条件时给出原因。 | |
| N171 | 校验或错误提示<br><code>ui/level_selector.py:31</code> | <code>f"无效关卡选项：{label}"</code> | 显示并解析用户选择的起始关卡时，在输入或执行结果不符合条件时给出原因。 | |
| N172 | 校验或错误提示<br><code>ui/runtime_context.py:61</code> | <code>board 和 strategy 必须同时提供</code> | 维护设备、关卡、棋盘与策略对象的对应关系时，在输入或执行结果不符合条件时给出原因。 | |

### 05 页面判断与进入活动（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N173 | 日志<br><code>flows/auto_probe_ready.py:124</code><br>关联：N207, N208, N209, N210, N211 | <code>自动单发准备完成：page=%s，weak=%s，reject=%s</code> | 开始单发前核验活动棋盘页面、弱网及断网状态时，记录这一步的参数、结果或异常。 | |
| N174 | 日志<br><code>flows/sonar_page.py:202</code><br>关联：N175, N176 | <code>等待主岛按键出现</code> | 等待主岛活动按钮确认主岛就绪时，记录这一步的参数、结果或异常。 | |
| N175 | 日志<br><code>flows/sonar_page.py:214</code><br>关联：N174, N176 | <code>主岛等待失败：没有检测到活动按钮</code> | 等待主岛活动按钮确认主岛就绪时，记录这一步的参数、结果或异常。 | |
| N176 | 日志<br><code>flows/sonar_page.py:220</code><br>关联：N174, N175 | <code>主岛已就绪：活动按钮中心=%s</code> | 等待主岛活动按钮确认主岛就绪时，记录这一步的参数、结果或异常。 | |
| N177 | 日志<br><code>flows/sonar_page.py:123</code><br>关联：N178, N179, N180 | <code>页面状态：活动棋盘页面</code> | 只截图判断当前声纳页面、供进入和恢复选择分支时，记录这一步的参数、结果或异常。 | |
| N178 | 日志<br><code>flows/sonar_page.py:140</code><br>关联：N177, N179, N180 | <code>页面状态：主岛，声纳已可见；中心=%s，相似度=%.3f</code> | 只截图判断当前声纳页面、供进入和恢复选择分支时，记录这一步的参数、结果或异常。 | |
| N179 | 日志<br><code>flows/sonar_page.py:166</code><br>关联：N177, N178, N180 | <code>页面状态：主岛；活动按钮中心=%s；当前声纳最高相似度=%.3f</code> | 只截图判断当前声纳页面、供进入和恢复选择分支时，记录这一步的参数、结果或异常。 | |
| N180 | 日志<br><code>flows/sonar_page.py:179</code><br>关联：N177, N178, N179 | <code>页面状态：未知；未识别到活动棋盘页面、声纳或主岛活动按钮；当前声纳最高相似度=%.3f</code> | 只截图判断当前声纳页面、供进入和恢复选择分支时，记录这一步的参数、结果或异常。 | |
| N181 | 日志<br><code>flows/sonar_page.py:241</code> | <code>主岛上划，准备寻找声纳</code> | 在主岛向上拖动画面以露出海边声纳时，记录这一步的参数、结果或异常。 | |
| N182 | 日志<br><code>flows/sonar_page.py:298</code><br>关联：N183, N184, N185 | <code>声纳已经在画面中：中心=%s，相似度=%.3f</code> | 等待主岛就绪并上划寻找声纳入口时，记录这一步的参数、结果或异常。 | |
| N183 | 日志<br><code>flows/sonar_page.py:306</code><br>关联：N182, N184, N185 | <code>当前未看到声纳，最高相似度=%.3f，执行主岛上划</code> | 等待主岛就绪并上划寻找声纳入口时，记录这一步的参数、结果或异常。 | |
| N184 | 日志<br><code>flows/sonar_page.py:354</code><br>关联：N182, N183, N185 | <code>等待声纳成功出现：中心=%s，相似度=%.3f，检测次数=%s</code> | 等待主岛就绪并上划寻找声纳入口时，记录这一步的参数、结果或异常。 | |
| N185 | 日志<br><code>flows/sonar_page.py:369</code><br>关联：N182, N183, N184 | <code>声纳等待超时：%.1f 秒内未出现；最高相似度=%.3f，阈值=%.3f</code> | 等待主岛就绪并上划寻找声纳入口时，记录这一步的参数、结果或异常。 | |
| N186 | 日志<br><code>flows/activity_flow.py:179</code><br>关联：N187, N188, N189, N190, N212, N213（其余见索引） | <code>已点击主岛活动按钮：中心=%s，相似度=%.3f</code> | 从主岛首次进入声纳活动、整理弱网状态时，记录这一步的参数、结果或异常。 | |
| N187 | 日志<br><code>flows/activity_flow.py:219</code><br>关联：N186, N188, N189, N190, N212, N213（其余见索引） | <code>活动列表上划：%s/%s</code> | 从主岛首次进入声纳活动、整理弱网状态时，记录这一步的参数、结果或异常。 | |
| N188 | 日志<br><code>flows/activity_flow.py:260</code><br>关联：N186, N187, N189, N190, N212, N213（其余见索引） | <code>已点击声纳活动入口：(%s, %s)</code> | 从主岛首次进入声纳活动、整理弱网状态时，记录这一步的参数、结果或异常。 | |
| N189 | 日志<br><code>flows/activity_flow.py:330</code><br>关联：N186, N187, N188, N190, N212, N213（其余见索引） | <code>进入声纳活动并完成初始化：initial=%s，final=%s，sonar=%s，weak=%s</code> | 从主岛首次进入声纳活动、整理弱网状态时，记录这一步的参数、结果或异常。 | |
| N190 | 日志<br><code>flows/activity_flow.py:350</code><br>关联：N186, N187, N188, N189, N212, N213（其余见索引） | <code>初始进入活动失败后，关闭弱网也失败</code> | 从主岛首次进入声纳活动、整理弱网状态时，记录这一步的参数、结果或异常。 | |
| N191 | 日志<br><code>flows/sonar_page.py:409</code><br>关联：N192 | <code>棋盘页面未准备就绪：未找到 %s</code> | 等待退出活动按钮确认活动棋盘页面就绪时，记录这一步的参数、结果或异常。 | |
| N192 | 日志<br><code>flows/sonar_page.py:415</code><br>关联：N191 | <code>棋盘页面已准备就绪：退出按钮中心=%s</code> | 等待退出活动按钮确认活动棋盘页面就绪时，记录这一步的参数、结果或异常。 | |
| N193 | 日志<br><code>controllers/page_controller.py:90</code><br>关联：N219 | <code>页面滑动：(%s, %s) -&gt; (%s, %s)，%sms</code> | 截图查找模板并按需要等待或点击时，记录这一步的参数、结果或异常。 | |
| N194 | 日志<br><code>controllers/page_controller.py:141</code><br>关联：N195 | <code>未找到模板：%s，最高相似度=%.3f，阈值=%.3f</code> | 截图查找模板并按需要等待或点击时，记录这一步的参数、结果或异常。 | |
| N195 | 日志<br><code>controllers/page_controller.py:148</code><br>关联：N194 | <code>找到模板：%s，相似度=%.3f，中心=%s</code> | 截图查找模板并按需要等待或点击时，记录这一步的参数、结果或异常。 | |
| N196 | 日志<br><code>controllers/page_controller.py:200</code><br>关联：N197, N198, N206, N220, N221, N353 | <code>开始等待模板：%s，超时=%.1f秒，阈值=%.3f</code> | 截图查找模板并按需要等待或点击时，记录这一步的参数、结果或异常。 | |
| N197 | 日志<br><code>controllers/page_controller.py:237</code><br>关联：N196, N198, N206, N220, N221, N354 | <code>等待模板成功：%s，相似度=%.3f，中心=%s，检测次数=%s</code> | 截图查找模板并按需要等待或点击时，记录这一步的参数、结果或异常。 | |
| N198 | 日志<br><code>controllers/page_controller.py:250</code><br>关联：N196, N197, N206, N220, N221 | <code>等待模板超时：%s，%.1f秒内未出现，最高相似度=%.3f，阈值=%.3f，检测次数=%s</code> | 截图查找模板并按需要等待或点击时，记录这一步的参数、结果或异常。 | |
| N199 | 日志<br><code>controllers/page_controller.py:343</code><br>关联：N222 | <code>点击匹配区域中心：(%s, %s)，相似度=%.3f</code> | 截图查找模板并按需要等待或点击时，记录这一步的参数、结果或异常。 | |
| N200 | 日志<br><code>flows/activity_flow.py:69</code> | <code>已点击安全点关闭活动开始提示：(%s, %s)</code> | 点击棋盘外安全点关闭活动开始提示时，记录这一步的参数、结果或异常。 | |
| N201 | 日志<br><code>flows/activity_flow.py:369</code><br>关联：N202, N203, N204, N225, N226 | <code>开始重新进入声纳活动</code> | 退出活动后重新进入当前活动时，记录这一步的参数、结果或异常。 | |
| N202 | 日志<br><code>flows/activity_flow.py:388</code><br>关联：N201, N203, N204, N225, N226 | <code>已点击活动按钮：中心=%s，相似度=%.3f</code> | 退出活动后重新进入当前活动时，记录这一步的参数、结果或异常。 | |
| N203 | 日志<br><code>flows/activity_flow.py:410</code><br>关联：N201, N202, N204, N225, N226 | <code>已点击活动入口：(%s, %s)</code> | 退出活动后重新进入当前活动时，记录这一步的参数、结果或异常。 | |
| N204 | 日志<br><code>flows/activity_flow.py:435</code><br>关联：N201, N202, N203, N225, N226 | <code>重新进入声纳活动棋盘页面完成</code> | 退出活动后重新进入当前活动时，记录这一步的参数、结果或异常。 | |
| N205 | 日志（DEBUG，默认不显示）<br><code>controllers/page_controller.py:53</code><br>关联：N218 | <code>点击坐标：(%s, %s)</code> | 截图查找模板并按需要等待或点击时，在启用 DEBUG 日志时记录细节。 | |
| N206 | 日志（DEBUG，默认不显示）<br><code>controllers/page_controller.py:261</code><br>关联：N196, N197, N198, N220, N221 | <code>等待模板中：%s，第%s次未命中，本次最高相似度=%.3f，累计最高相似度=%.3f</code> | 截图查找模板并按需要等待或点击时，在启用 DEBUG 日志时记录细节。 | |
| N207 | 校验或错误提示<br><code>flows/auto_probe_ready.py:50</code><br>关联：N173, N208, N209, N210, N211 | <code>开始自动探测前仍处于REJECT 断网状态。请先恢复网络。</code> | 开始单发前核验活动棋盘页面、弱网及断网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N208 | 校验或错误提示<br><code>flows/auto_probe_ready.py:87</code><br>关联：N173, N207, N209, N210, N211 | <code>自动探测准备失败：没有进入活动棋盘页面</code> | 开始单发前核验活动棋盘页面、弱网及断网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N209 | 校验或错误提示<br><code>flows/auto_probe_ready.py:107</code><br>关联：N173, N207, N208, N210, N211 | <code>"自动探测准备失败："<br>            f"最终页面={final_page.value}"</code> | 开始单发前核验活动棋盘页面、弱网及断网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N210 | 校验或错误提示<br><code>flows/auto_probe_ready.py:113</code><br>关联：N173, N207, N208, N209, N211 | <code>自动探测准备失败：REJECT 断网状态仍然开启</code> | 开始单发前核验活动棋盘页面、弱网及断网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N211 | 校验或错误提示<br><code>flows/auto_probe_ready.py:119</code><br>关联：N173, N207, N208, N209, N210 | <code>自动探测准备失败：DROP 弱网状态没有开启</code> | 开始单发前核验活动棋盘页面、弱网及断网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N212 | 校验或错误提示<br><code>flows/activity_flow.py:112</code><br>关联：N186, N187, N188, N189, N190, N213（其余见索引） | <code>当前仍处于 REJECT 断网状态，请先恢复网络再执行初始进入活动</code> | 从主岛首次进入声纳活动、整理弱网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N213 | 校验或错误提示<br><code>flows/activity_flow.py:152</code><br>关联：N186, N187, N188, N189, N190, N212（其余见索引） | <code>初始进入活动失败：主岛上没有检测到声纳</code> | 从主岛首次进入声纳活动、整理弱网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N214 | 校验或错误提示<br><code>flows/activity_flow.py:174</code><br>关联：N186, N187, N188, N189, N190, N212（其余见索引） | <code>初始进入活动失败：没有找到主岛活动按钮</code> | 从主岛首次进入声纳活动、整理弱网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N215 | 校验或错误提示<br><code>flows/activity_flow.py:279</code><br>关联：N186, N187, N188, N189, N190, N212（其余见索引） | <code>初始进入活动失败：点击详情入口后没有检测到退出按钮</code> | 从主岛首次进入声纳活动、整理弱网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N216 | 校验或错误提示<br><code>flows/activity_flow.py:300</code><br>关联：N186, N187, N188, N189, N190, N212（其余见索引） | <code>"初始进入活动后的最终页面检验失败："<br>                f"{final_state.value}"</code> | 从主岛首次进入声纳活动、整理弱网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N217 | 校验或错误提示<br><code>flows/activity_flow.py:314</code><br>关联：N186, N187, N188, N189, N190, N212（其余见索引） | <code>初始进入活动后的弱网状态检验失败</code> | 从主岛首次进入声纳活动、整理弱网状态时，在输入或执行结果不符合条件时给出原因。 | |
| N218 | 校验或错误提示<br><code>controllers/page_controller.py:46</code><br>关联：N205 | <code>点击坐标不能小于 0</code> | 截图查找模板并按需要等待或点击时，在输入或执行结果不符合条件时给出原因。 | |
| N219 | 校验或错误提示<br><code>controllers/page_controller.py:83</code><br>关联：N193 | <code>滑动时间必须大于 0</code> | 截图查找模板并按需要等待或点击时，在输入或执行结果不符合条件时给出原因。 | |
| N220 | 校验或错误提示<br><code>controllers/page_controller.py:189</code><br>关联：N196, N197, N198, N206, N221 | <code>等待超时不能小于 0</code> | 截图查找模板并按需要等待或点击时，在输入或执行结果不符合条件时给出原因。 | |
| N221 | 校验或错误提示<br><code>controllers/page_controller.py:192</code><br>关联：N196, N197, N198, N206, N220 | <code>检查间隔必须大于 0</code> | 截图查找模板并按需要等待或点击时，在输入或执行结果不符合条件时给出原因。 | |
| N222 | 校验或错误提示<br><code>controllers/page_controller.py:339</code><br>关联：N199 | <code>模板结果没有点击位置</code> | 截图查找模板并按需要等待或点击时，在输入或执行结果不符合条件时给出原因。 | |
| N223 | 校验或错误提示<br><code>controllers/page_controller.py:381</code> | <code>f"没有找到模板图片。已检查：{checked}"</code> | 截图查找模板并按需要等待或点击时，在输入或执行结果不符合条件时给出原因。 | |
| N224 | 校验或错误提示<br><code>controllers/page_controller.py:394</code><br>关联：N506, N947 | <code>等待时间不能小于 0</code> | 截图查找模板并按需要等待或点击时，在输入或执行结果不符合条件时给出原因。 | |
| N225 | 校验或错误提示<br><code>flows/activity_flow.py:383</code><br>关联：N201, N202, N203, N204, N226 | <code>"重新进入活动失败："<br>            f"未找到 {ACTIVITY_PAGE_CONFIG.activity_button_template}"</code> | 退出活动后重新进入当前活动时，在输入或执行结果不符合条件时给出原因。 | |
| N226 | 校验或错误提示<br><code>flows/activity_flow.py:425</code><br>关联：N201, N202, N203, N204, N225 | <code>重新进入活动失败：点击活动棋盘页面入口后没有检测到退出按钮</code> | 退出活动后重新进入当前活动时，在输入或执行结果不符合条件时给出原因。 | |
| N227 | 校验或错误提示<br><code>flows/sonar_page.py:48</code> | <code>"缺少模板图片："<br>            f"{path}"</code> | 判断主岛、寻找声纳或核验活动棋盘页面时，在输入或执行结果不符合条件时给出原因。 | |

### 06 选格、单发识别与结果登记（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N228 | 状态显示<br><code>ui/gui_app.py:995</code><br>关联：N229, N230, N231, N232, N233, N257（其余见索引） | <code>f"发数：{index} &#124; HIT：{hits} &#124; MISS：{misses}"</code> | 主线程接收后台结果、恢复或换关消息时，显示当前进度或操作结果。<br>注意：统计栏文字用于提取发数、HIT 和 MISS；标点与分隔符变化需同步核对解析。 | |
| N229 | 状态显示<br><code>ui/gui_app.py:998</code><br>关联：N228, N230, N231, N232, N233, N257（其余见索引） | <code>f"上一发：{result.context.cell} {result_text} &#124; 结果已登记"</code> | 主线程接收后台结果、恢复或换关消息时，显示当前进度或操作结果。 | |
| N230 | 状态显示<br><code>ui/gui_app.py:1000；ui/gui_app.py:1034</code><br>关联：N228, N229, N231, N232, N233, N257（其余见索引） | <code>运行中</code> | 主线程接收后台结果、恢复或换关消息时，显示当前进度或操作结果。 | |
| N231 | 状态显示<br><code>ui/gui_app.py:1002</code><br>关联：N228, N229, N230, N232, N233, N257（其余见索引） | <code>f"自动循环运行中：第 {index} 发结果已登记"</code> | 主线程接收后台结果、恢复或换关消息时，显示当前进度或操作结果。 | |
| N232 | 状态显示<br><code>ui/gui_app.py:1032</code><br>关联：N228, N229, N230, N231, N233, N257（其余见索引） | <code>f"上一发：{result.context.cell} {result_text} &#124; 下一格：{result.next_cell}"</code> | 主线程接收后台结果、恢复或换关消息时，显示当前进度或操作结果。 | |
| N233 | 状态显示<br><code>ui/gui_app.py:1036</code><br>关联：N228, N229, N230, N231, N232, N257（其余见索引） | <code>f"自动循环运行中：第 {index} 发恢复完成"</code> | 主线程接收后台结果、恢复或换关消息时，显示当前进度或操作结果。 | |
| N234 | 日志<br><code>flows/probe_flow.py:113</code><br>关联：N235, N236, N237, N238, N239, N240（其余见索引） | <code>开始单发探测页面操作</code> | 选格后保留前图、点击并退出重进以取得后图时，记录这一步的参数、结果或异常。 | |
| N235 | 日志<br><code>flows/probe_flow.py:167</code><br>关联：N234, N236, N237, N238, N239, N240（其余见索引） | <code>本次策略选格：逻辑格=%s，模拟器坐标=(%s, %s)</code> | 选格后保留前图、点击并退出重进以取得后图时，记录这一步的参数、结果或异常。 | |
| N236 | 日志<br><code>flows/probe_flow.py:230</code><br>关联：N234, N235, N237, N238, N239, N240（其余见索引） | <code>点击目标格前截图</code> | 选格后保留前图、点击并退出重进以取得后图时，记录这一步的参数、结果或异常。 | |
| N237 | 日志<br><code>flows/probe_flow.py:246</code><br>关联：N234, N235, N236, N238, N239, N240（其余见索引） | <code>点击目标格：逻辑格=%s，模拟器坐标=(%s, %s)</code> | 选格后保留前图、点击并退出重进以取得后图时，记录这一步的参数、结果或异常。 | |
| N238 | 日志<br><code>flows/probe_flow.py:265</code><br>关联：N234, N235, N236, N237, N239, N240（其余见索引） | <code>准备退出当前活动棋盘页面</code> | 选格后保留前图、点击并退出重进以取得后图时，记录这一步的参数、结果或异常。 | |
| N239 | 日志<br><code>flows/probe_flow.py:281</code><br>关联：N234, N235, N236, N237, N238, N240（其余见索引） | <code>已点击退出活动按钮：中心=%s，相似度=%.3f</code> | 选格后保留前图、点击并退出重进以取得后图时，记录这一步的参数、结果或异常。 | |
| N240 | 日志<br><code>flows/probe_flow.py:293</code><br>关联：N234, N235, N236, N237, N238, N239（其余见索引） | <code>重新进入活动后截图</code> | 选格后保留前图、点击并退出重进以取得后图时，记录这一步的参数、结果或异常。 | |
| N241 | 日志<br><code>flows/probe_flow.py:308</code><br>关联：N234, N235, N236, N237, N238, N239（其余见索引） | <code>单发页面操作完成：cell=%s，before=%s，after=%s；等待 HIT / MISS 结果处理</code> | 选格后保留前图、点击并退出重进以取得后图时，记录这一步的参数、结果或异常。 | |
| N242 | 日志<br><code>flows/auto_probe_flow.py:245</code><br>关联：N243, N244, N245, N256, N266, N267（其余见索引） | <code>单帧识别处于模糊区，采集第二帧确认：cell=%s，state=%s，confidence=%.3f，score=%.3f</code> | 识别本发结果并完整同步棋盘、策略和计数时，记录这一步的参数、结果或异常。 | |
| N243 | 日志<br><code>flows/auto_probe_flow.py:288</code><br>关联：N242, N244, N245, N256, N266, N267（其余见索引） | <code>自动命中判断（来源=%s）：cell=%s，state=%s，confidence=%.3f，score=%.3f，center=%s，probe_offset=%s，inside=%.3f，boundary=%.3f，outside=%.3f，cross=%.3f，direction=%s，sunk_candidate=%s -&gt; %s</code> | 识别本发结果并完整同步棋盘、策略和计数时，记录这一步的参数、结果或异常。 | |
| N244 | 日志<br><code>flows/auto_probe_flow.py:306</code><br>关联：N242, N243, N245, N256, N257, N260（其余见索引） | <code>HIT</code> | 识别本发结果并完整同步棋盘、策略和计数时，记录这一步的参数、结果或异常。 | |
| N245 | 日志<br><code>flows/auto_probe_flow.py:306</code><br>关联：N242, N243, N244, N256, N258, N259（其余见索引） | <code>MISS</code> | 识别本发结果并完整同步棋盘、策略和计数时，记录这一步的参数、结果或异常。 | |
| N246 | 日志<br><code>flows/auto_probe_flow.py:416</code><br>关联：N247, N248 | <code>普通 HIT 由既有唯一解释逻辑确认 SUNK：cell=%s，ships=%s</code> | 对照视觉击沉候选与策略合法性检查结果记录证据时，记录这一步的参数、结果或异常。 | |
| N247 | 日志<br><code>flows/auto_probe_flow.py:427</code><br>关联：N246, N248 | <code>SUNK 视觉候选缺少策略校验接口：cell=%s，direction=%s，remaining=%s，final=%s</code> | 对照视觉击沉候选与策略合法性检查结果记录证据时，记录这一步的参数、结果或异常。 | |
| N248 | 日志<br><code>flows/auto_probe_flow.py:437</code><br>关联：N246, N247 | <code>SUNK 候选策略校验：cell=%s，candidate_direction=%s，hit_cells=%s，candidate_length=%s，remaining=%s，valid=%s，reason=%s，source=%s，final=%s</code> | 对照视觉击沉候选与策略合法性检查结果记录证据时，记录这一步的参数、结果或异常。 | |
| N249 | 日志<br><code>flows/auto_probe_flow.py:502</code><br>关联：N250, N251, N269 | <code>开始完整自动单发探测</code> | 执行本发探测、结果登记及对应恢复时，记录这一步的参数、结果或异常。 | |
| N250 | 日志<br><code>flows/auto_probe_flow.py:584</code><br>关联：N249, N251, N269 | <code>本发新确认潜艇：%s</code> | 执行本发探测、结果登记及对应恢复时，记录这一步的参数、结果或异常。 | |
| N251 | 日志<br><code>flows/auto_probe_flow.py:642</code><br>关联：N249, N250, N269 | <code>完整自动单发完成：cell=%s -&gt; %s，next=%s，strategy_done=%s</code> | 执行本发探测、结果登记及对应恢复时，记录这一步的参数、结果或异常。 | |
| N252 | 日志<br><code>flows/auto_probe_flow.py:130</code><br>关联：N253, N254 | <code>异常发生在 HIT/MISS 识别完成前；已丢弃本发截图进度，保留 pending_cell 重新探测</code> | 把本发图像结果写入策略并恢复下一发时，记录这一步的参数、结果或异常。 | |
| N253 | 日志<br><code>flows/auto_probe_flow.py:142</code><br>关联：N252, N254 | <code>已识别 HIT，但游戏因重启回档；恢复后将重新点击该格并完成联网提交</code> | 把本发图像结果写入策略并恢复下一发时，记录这一步的参数、结果或异常。 | |
| N254 | 日志<br><code>flows/auto_probe_flow.py:150</code><br>关联：N252, N253 | <code>已识别 MISS；重启已丢弃本次游戏请求，保留策略结果继续运行</code> | 把本发图像结果写入策略并恢复下一发时，记录这一步的参数、结果或异常。 | |
| N255 | 日志<br><code>flows/auto_probe_flow.py:183</code> | <code>重新点击已识别 HIT：cell=%s，模拟器坐标=(%s, %s)</code> | 把本发图像结果写入策略并恢复下一发时，记录这一步的参数、结果或异常。 | |
| N256 | 无独立显示的流程阶段<br><code>flows/auto_probe_flow.py:199</code><br>关联：N242, N243, N244, N245, N266, N267（其余见索引） | <code>当前未单独命名</code> | 人工或自动结果已取得后，完整同步棋盘、策略和计数，再响应停止；当前没有独立阶段标题。<br>注意：当前没有原文可直接替换；新增显示需另行明确范围。 | |
| N257 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:971；ui/gui_app.py:1029</code><br>关联：N228, N229, N230, N231, N232, N233（其余见索引） | <code>HIT</code> | 主线程接收后台结果、恢复或换关消息时，组成界面提示或该步骤的诊断信息。 | |
| N258 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:971；ui/gui_app.py:1029</code><br>关联：N228, N229, N230, N231, N232, N233（其余见索引） | <code>MISS</code> | 主线程接收后台结果、恢复或换关消息时，组成界面提示或该步骤的诊断信息。 | |
| N259 | 显示组成文字／诊断消息<br><code>flows/auto_probe_flow.py:58</code><br>关联：N245, N258, N260, N939, N944 | <code>MISS</code> | 把本发图像结果写入策略并恢复下一发时，组成界面提示或该步骤的诊断信息。 | |
| N260 | 显示组成文字／诊断消息<br><code>flows/auto_probe_flow.py:59</code><br>关联：N244, N257, N259, N938, N943 | <code>HIT</code> | 把本发图像结果写入策略并恢复下一发时，组成界面提示或该步骤的诊断信息。 | |
| N261 | 校验或错误提示<br><code>flows/probe_flow.py:125</code><br>关联：N234, N235, N236, N237, N238, N239（其余见索引） | <code>棋盘坐标映射不完整，无法执行真实格点点击</code> | 选格后保留前图、点击并退出重进以取得后图时，在输入或执行结果不符合条件时给出原因。 | |
| N262 | 校验或错误提示<br><code>flows/probe_flow.py:134</code><br>关联：N234, N235, N236, N237, N238, N239（其余见索引） | <code>"单发恢复进度与策略 pending_cell 不一致："<br>            f"progress={cell}, pending={strategy.pending_cell}"</code> | 选格后保留前图、点击并退出重进以取得后图时，在输入或执行结果不符合条件时给出原因。 | |
| N263 | 校验或错误提示<br><code>flows/probe_flow.py:145</code><br>关联：N234, N235, N236, N237, N238, N239（其余见索引） | <code>策略没有可继续探测的格子</code> | 选格后保留前图、点击并退出重进以取得后图时，在输入或执行结果不符合条件时给出原因。 | |
| N264 | 校验或错误提示<br><code>flows/probe_flow.py:190</code><br>关联：N234, N235, N236, N237, N238, N239（其余见索引） | <code>"执行单发探测前没有检测到活动棋盘页面。"<br>            "当前页面状态="<br>            f"{current_state.value}"</code> | 选格后保留前图、点击并退出重进以取得后图时，在输入或执行结果不符合条件时给出原因。 | |
| N265 | 校验或错误提示<br><code>flows/probe_flow.py:275</code><br>关联：N234, N235, N236, N237, N238, N239（其余见索引） | <code>目标格点击后没有找到退出活动按钮。当前页面状态可能异常；本次结果不会提交给策略。</code> | 选格后保留前图、点击并退出重进以取得后图时，在输入或执行结果不符合条件时给出原因。 | |
| N266 | 校验或错误提示<br><code>flows/auto_probe_flow.py:270</code><br>关联：N242, N243, N244, N245, N256, N267（其余见索引） | <code>"自动命中识别结果无效："<br>                f"state={recognition_state}；"<br>                "本次结果不会写入策略"</code> | 识别本发结果并完整同步棋盘、策略和计数时，在输入或执行结果不符合条件时给出原因。 | |
| N267 | 校验或错误提示<br><code>flows/auto_probe_flow.py:284</code><br>关联：N242, N243, N244, N245, N256, N266（其余见索引） | <code>自动探测进度缺少 HIT/MISS 判断结果</code> | 识别本发结果并完整同步棋盘、策略和计数时，在输入或执行结果不符合条件时给出原因。 | |
| N268 | 校验或错误提示<br><code>flows/auto_probe_flow.py:314</code><br>关联：N242, N243, N244, N245, N256, N266（其余见索引） | <code>"自动识别结果对应格与策略 pending_cell 不一致："<br>                f"pending={pending}, context={context.cell}"</code> | 识别本发结果并完整同步棋盘、策略和计数时，在输入或执行结果不符合条件时给出原因。 | |
| N269 | 校验或错误提示<br><code>flows/auto_probe_flow.py:577</code><br>关联：N249, N250, N251 | <code>自动探测进度缺少正式 MISS/HIT/SUNK 结果</code> | 执行本发探测、结果登记及对应恢复时，在输入或执行结果不符合条件时给出原因。 | |
| N270 | 校验或错误提示<br><code>flows/probe_flow.py:78</code> | <code>单发探测进度不完整，无法生成识别上下文</code> | 执行本发选格、截图和活动进出时，在输入或执行结果不符合条件时给出原因。 | |
| N271 | 校验或错误提示<br><code>vision/diamond_hit.py:179</code> | <code>before_screenshot 和 after_screenshot 的图片尺寸必须一致</code> | 根据本发前后截图判断目标格、保存识别诊断时，在输入或执行结果不符合条件时给出原因。 | |
| N272 | 校验或错误提示<br><code>vision/diamond_hit.py:454</code> | <code>after_screenshots 不能为空</code> | 根据本发前后截图判断目标格、保存识别诊断时，在输入或执行结果不符合条件时给出原因。 | |
| N273 | 校验或错误提示<br><code>vision/diamond_hit.py:1369</code><br>关联：N274, N275 | <code>f"{name} 必须是 OpenCV 图像对象"</code> | 根据本发前后截图判断目标格、保存识别诊断时，在输入或执行结果不符合条件时给出原因。 | |
| N274 | 校验或错误提示<br><code>vision/diamond_hit.py:1377</code><br>关联：N273, N275 | <code>f"{name} 必须是 BGR 彩色图片"</code> | 根据本发前后截图判断目标格、保存识别诊断时，在输入或执行结果不符合条件时给出原因。 | |
| N275 | 校验或错误提示<br><code>vision/diamond_hit.py:1382</code><br>关联：N273, N274 | <code>f"{name} 不能为空"</code> | 根据本发前后截图判断目标格、保存识别诊断时，在输入或执行结果不符合条件时给出原因。 | |
| N276 | 校验或错误提示<br><code>vision/diamond_hit.py:1389</code> | <code>f"center 必须是 (x, y): {center}"</code> | 根据本发前后截图判断目标格、保存识别诊断时，在输入或执行结果不符合条件时给出原因。 | |

### 07 人工测试模式弹窗与等待（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N277 | 窗口标题<br><code>ui/manual_recognition_dialog.py:61</code><br>关联：N278, N279, N280, N281, N282, N315（其余见索引） | <code>人工测试模式</code> | 开启后沿用原循环和真实设备操作，把识别结果交给用户回答。 | |
| N278 | 界面文字<br><code>ui/manual_recognition_dialog.py:69</code><br>关联：N277, N279, N280, N281, N315 | <code>f"第{request.level}关{cell} · {request.step}"</code> | 显示当前人工判断弹窗、图像和等待计时时，标注相应操作区或提示信息。 | |
| N279 | 界面文字<br><code>ui/manual_recognition_dialog.py:100</code><br>关联：N277, N278, N280, N281, N315 | <code>要找的模板（任一匹配）：</code> | 显示当前人工判断弹窗、图像和等待计时时，标注相应操作区或提示信息。 | |
| N280 | 界面文字<br><code>ui/manual_recognition_dialog.py:100</code><br>关联：N277, N278, N279, N281, N315 | <code>要找的模板：</code> | 显示当前人工判断弹窗、图像和等待计时时，标注相应操作区或提示信息。 | |
| N281 | 界面文字<br><code>ui/manual_recognition_dialog.py:114</code><br>关联：N277, N278, N279, N280, N315 | <code>找到：直接点击上方截图中的目标</code> | 显示当前人工判断弹窗、图像和等待计时时，标注相应操作区或提示信息。 | |
| N282 | 按钮文案<br><code>ui/gui_app.py:275</code><br>关联：N277, N318 | <code>人工测试模式</code> | 开启后沿用原循环和真实设备操作，把识别结果交给用户回答。 | |
| N283 | 状态显示<br><code>ui/gui_app.py:1020</code> | <code>等待人工测试结果</code> | 后台已提出识别请求，原流程等待人工回答。 | |
| N284 | 状态显示<br><code>ui/gui_app.py:307</code><br>关联：N005, N153, N285, N318, N319, N320（其余见索引） | <code>发数：0 &#124; HIT：0 &#124; MISS：0</code> | 新建窗口、切换关卡或模式以及启动循环时，把本次累计发数、命中和未命中显示为零。<br>注意：统计栏文字用于提取发数、HIT 和 MISS；标点与分隔符变化需同步核对解析。 | |
| N285 | 状态显示<br><code>ui/gui_app.py:308</code><br>关联：N006, N154, N284, N318, N319, N320（其余见索引） | <code>上一发：-</code> | 尚无本次循环可显示的上一发结果时，用横线占位。 | |
| N286 | 状态显示<br><code>ui/gui_app.py:323</code><br>关联：N230, N287, N341 | <code>运行中</code> | 接收当前人工请求的答案并交回原流程时，显示当前进度或操作结果。 | |
| N287 | 状态显示<br><code>ui/gui_app.py:324</code><br>关联：N286, N341 | <code>人工结果已提交，原流程继续</code> | 接收当前人工请求的答案并交回原流程时，显示当前进度或操作结果。 | |
| N288 | 答案选项<br><code>manual_recognition.py:23</code><br>关联：N289, N290, N291, N292, N293, N294（其余见索引） | <code>活动棋盘页面</code> | 人工确认当前位于可继续声纳活动操作的活动棋盘页面。 | |
| N289 | 答案选项<br><code>manual_recognition.py:23</code><br>关联：N288, N290, N291, N292, N293, N294（其余见索引） | <code>主岛，声纳浮标可见</code> | 人工确认当前位于主岛且已露出声纳入口。 | |
| N290 | 答案选项<br><code>manual_recognition.py:24</code><br>关联：N288, N289, N291, N292, N293, N294（其余见索引） | <code>主岛</code> | 人工确认当前是主岛，尚未确认声纳可见。 | |
| N291 | 答案选项<br><code>manual_recognition.py:24</code><br>关联：N288, N289, N290, N292, N293, N294（其余见索引） | <code>无法判断</code> | 用户无法确认当前页面类型，返回原未知页面分支。 | |
| N292 | 答案选项<br><code>manual_recognition.py:25</code><br>关联：N288, N289, N290, N291, N293, N294（其余见索引） | <code>找到</code> | 用户确认本次模板存在；需要坐标的请求通过截图点选提交成功结果。 | |
| N293 | 答案选项<br><code>manual_recognition.py:25</code><br>关联：N288, N289, N290, N291, N292, N294（其余见索引） | <code>未找到</code> | 用户明确确认本次模板未找到，返回原未找到或等待失败分支。 | |
| N294 | 答案选项<br><code>manual_recognition.py:25</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>判定超时</code> | 由用户主动结束等待并返回原超时分支，计时条到点不会自行提交。 | |
| N295 | 答案选项<br><code>manual_recognition.py:26</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>命中 HIT</code> | 人工把本发目标格判断为命中，后续登记和击沉校验仍走原策略。 | |
| N296 | 答案选项<br><code>manual_recognition.py:26</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>未命中 MISS</code> | 人工把本发目标格判断为未命中，登记后走原 MISS 恢复。 | |
| N297 | 答案选项<br><code>manual_recognition.py:27</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>未开启</code> | 人工认为目标格尚未开启，随后进入原不确定结果处理分支。 | |
| N298 | 答案选项<br><code>manual_recognition.py:27</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>无法判断本格结果</code> | 用户无法确定本发格子结果，返回原不确定结果分支。 | |
| N299 | 模板显示名称<br><code>manual_recognition.py:28</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>主岛活动按钮</code> | 在人工弹窗中说明本次要寻找的模板目标，实际模板文件绑定保留在索引。 | |
| N300 | 模板显示名称<br><code>manual_recognition.py:28</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>海边声纳浮标</code> | 在人工弹窗中说明本次要寻找的模板目标，实际模板文件绑定保留在索引。 | |
| N301 | 模板显示名称<br><code>manual_recognition.py:29</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>声纳标签</code> | 在人工弹窗中说明本次要寻找的模板目标，实际模板文件绑定保留在索引。 | |
| N302 | 模板显示名称<br><code>manual_recognition.py:29</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>退出活动按钮</code> | 在人工弹窗中说明本次要寻找的模板目标，实际模板文件绑定保留在索引。 | |
| N303 | 模板显示名称<br><code>manual_recognition.py:30；manual_recognition.py:30</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>重试按钮</code> | 在人工弹窗中说明本次要寻找的模板目标，实际模板文件绑定保留在索引。 | |
| N304 | 模板显示名称<br><code>manual_recognition.py:30</code><br>关联：N288, N289, N290, N291, N292, N293（其余见索引） | <code>胜利画面</code> | 在人工弹窗中说明本次要寻找的模板目标，实际模板文件绑定保留在索引。 | |
| N305 | 人工判断问题／步骤／图片标签<br><code>manual_recognition.py:267</code><br>关联：N306, N307, N308, N340 | <code>等待</code> | 人工判断本次模板有无或位置时，提示当前需要判断的内容或图片用途。 | |
| N306 | 人工判断问题／步骤／图片标签<br><code>manual_recognition.py:267</code><br>关联：N305, N307, N308, N340 | <code>查找</code> | 人工判断本次模板有无或位置时，提示当前需要判断的内容或图片用途。 | |
| N307 | 人工判断问题／步骤／图片标签<br><code>manual_recognition.py:268</code><br>关联：N305, N306, N308, N340 | <code>截图中能找到所示模板吗？</code> | 人工判断本次模板有无或位置时，提示当前需要判断的内容或图片用途。 | |
| N308 | 人工判断问题／步骤／图片标签<br><code>manual_recognition.py:268</code><br>关联：N305, N306, N307, N340 | <code>找到时直接点选截图中的目标。</code> | 人工判断本次模板有无或位置时，提示当前需要判断的内容或图片用途。 | |
| N309 | 人工判断问题／步骤／图片标签<br><code>manual_recognition.py:281</code><br>关联：N310 | <code>判断当前页面</code> | 人工选择当前完整截图的页面类型时，提示当前需要判断的内容或图片用途。 | |
| N310 | 人工判断问题／步骤／图片标签<br><code>manual_recognition.py:281</code><br>关联：N309 | <code>当前截图属于哪个页面？</code> | 人工选择当前完整截图的页面类型时，提示当前需要判断的内容或图片用途。 | |
| N311 | 人工判断问题／步骤／图片标签<br><code>manual_recognition.py:287</code><br>关联：N312, N313, N314 | <code>判断本发结果</code> | 人工对照本发前后截图判断目标格时，提示当前需要判断的内容或图片用途。 | |
| N312 | 人工判断问题／步骤／图片标签<br><code>manual_recognition.py:288</code><br>关联：N311, N313, N314 | <code>对照探测前后截图，标记的目标格是什么结果？</code> | 人工对照本发前后截图判断目标格时，提示当前需要判断的内容或图片用途。 | |
| N313 | 人工判断问题／步骤／图片标签<br><code>manual_recognition.py:289</code><br>关联：N311, N312, N314 | <code>探测前 before</code> | 人工对照本发前后截图判断目标格时，提示当前需要判断的内容或图片用途。 | |
| N314 | 人工判断问题／步骤／图片标签<br><code>manual_recognition.py:289</code><br>关联：N311, N312, N313 | <code>探测后 after</code> | 人工对照本发前后截图判断目标格时，提示当前需要判断的内容或图片用途。 | |
| N315 | 人工弹窗显示<br><code>ui/manual_recognition_dialog.py:68</code><br>关联：N277, N278, N279, N280, N281 | <code>f" · 第{request.cell[0]+1}行 第{request.cell[1]+1}列"</code> | 显示当前人工判断弹窗、图像和等待计时时，说明当前判断对象或等待进度。 | |
| N316 | 人工弹窗显示<br><code>ui/manual_recognition_dialog.py:140</code><br>关联：N317 | <code>f"已等待{elapsed:.1f}秒／参考{reference:g}秒"</code> | 显示当前人工判断弹窗、图像和等待计时时，说明当前判断对象或等待进度。 | |
| N317 | 人工弹窗显示<br><code>ui/manual_recognition_dialog.py:142</code><br>关联：N316 | <code> · 已达到参考时长，仍在等待人工判断</code> | 显示当前人工判断弹窗、图像和等待计时时，说明当前判断对象或等待进度。 | |
| N318 | 弹窗标题<br><code>ui/gui_app.py:310</code><br>关联：N277, N282, N284, N285, N319, N320（其余见索引） | <code>人工测试模式</code> | 开启后沿用原循环和真实设备操作，把识别结果交给用户回答。 | |
| N319 | 弹窗正文<br><code>ui/gui_app.py:311</code><br>关联：N284, N285, N318, N320, N321 | <code>本模式仍会真实操作模拟器，包括点击、滑动、网络控制和游戏重启。<br>活动缺失或人工判断错误可能导致误触。</code> | 完全空闲时开启人工测试模式并复制测试状态，或关闭后恢复正式状态时，说明当前操作的条件、结果或注意事项。 | |
| N320 | GUI 日志<br><code>ui/gui_app.py:298</code><br>关联：N284, N285, N318, N319, N321 | <code>[人工试运行] 已复制当前棋盘和策略；正式棋盘独立保留。</code> | 完全空闲时开启人工测试模式并复制测试状态，或关闭后恢复正式状态时，把这一步的操作及结果写入主窗口日志。<br>注意：人工日志前缀参与来源标记检查；不应连带改动内部 manual_trial 值。 | |
| N321 | GUI 日志<br><code>ui/gui_app.py:303</code><br>关联：N284, N285, N318, N319, N320 | <code>已关闭人工测试模式，恢复原正式棋盘；循环保持停止。</code> | 完全空闲时开启人工测试模式并复制测试状态，或关闭后恢复正式状态时，把这一步的操作及结果写入主窗口日志。 | |
| N322 | 日志<br><code>manual_recognition.py:161</code><br>关联：N329, N330, N331, N332, N333, N334 | <code>[人工试运行] 提交 %s：%s，帧=%s，坐标=%s</code> | 校验人工请求、显示帧及答案并防止重复提交时，记录这一步的参数、结果或异常。<br>注意：人工日志前缀参与来源标记检查；不应连带改动内部 manual_trial 值。 | |
| N323 | 日志<br><code>manual_recognition.py:194</code><br>关联：N326, N336, N337 | <code>[人工试运行] 等待 %s：第%s关，目标=%s，%s</code> | 后台把本次真实截图交给人工并等待答案时，记录这一步的参数、结果或异常。<br>注意：人工日志前缀参与来源标记检查；不应连带改动内部 manual_trial 值。 | |
| N324 | 日志<br><code>manual_recognition.py:253</code><br>关联：N339 | <code>[人工试运行] 判断依据：请求=%s，帧=%s，结果=%s，截图=%s</code> | 保存人工最终判断所依据的原图和记录时，记录这一步的参数、结果或异常。<br>注意：人工日志前缀参与来源标记检查；不应连带改动内部 manual_trial 值。 | |
| N325 | 显示组成文字／诊断消息<br><code>logger.py:18</code> | <code>f"[人工试运行 {session[:8]}] {record.getMessage()}"</code> | 格式化和输出运行日志时，组成界面提示或该步骤的诊断信息。<br>注意：人工日志前缀参与来源标记检查；不应连带改动内部 manual_trial 值。 | |
| N326 | 显示组成文字／诊断消息<br><code>manual_recognition.py:172</code><br>关联：N323, N336, N337 | <code>当前截图</code> | 后台把本次真实截图交给人工并等待答案时，组成界面提示或该步骤的诊断信息。 | |
| N327 | 校验或错误提示<br><code>manual_recognition.py:94</code> | <code>等待人工输入时不能换关或换盘</code> | 接收并校验原识别入口的人工答案时，在输入或执行结果不符合条件时给出原因。 | |
| N328 | 校验或错误提示<br><code>manual_recognition.py:101</code> | <code>上次人工请求尚未结束</code> | 接收并校验原识别入口的人工答案时，在输入或执行结果不符合条件时给出原因。 | |
| N329 | 校验或错误提示<br><code>manual_recognition.py:138</code><br>关联：N322, N330, N331, N332, N333, N334 | <code>请求已结束、已提交或已过期</code> | 校验人工请求、显示帧及答案并防止重复提交时，在输入或执行结果不符合条件时给出原因。 | |
| N330 | 校验或错误提示<br><code>manual_recognition.py:140</code><br>关联：N322, N329, N331, N332, N333, N334 | <code>棋盘已改变，请停止并重新启动试运行</code> | 校验人工请求、显示帧及答案并防止重复提交时，在输入或执行结果不符合条件时给出原因。 | |
| N331 | 校验或错误提示<br><code>manual_recognition.py:142</code><br>关联：N322, N329, N330, N332, N333, N334 | <code>请选择当前请求提供的结果</code> | 校验人工请求、显示帧及答案并防止重复提交时，在输入或执行结果不符合条件时给出原因。 | |
| N332 | 校验或错误提示<br><code>manual_recognition.py:145</code><br>关联：N322, N329, N330, N331, N333, N334 | <code>截图已过期，请基于当前显示画面判断</code> | 校验人工请求、显示帧及答案并防止重复提交时，在输入或执行结果不符合条件时给出原因。 | |
| N333 | 校验或错误提示<br><code>manual_recognition.py:149</code><br>关联：N322, N329, N330, N331, N332, N334 | <code>请在截图上点选目标</code> | 校验人工请求、显示帧及答案并防止重复提交时，在输入或执行结果不符合条件时给出原因。 | |
| N334 | 校验或错误提示<br><code>manual_recognition.py:153</code><br>关联：N322, N329, N330, N331, N332, N333 | <code>坐标必须为整数</code> | 校验人工请求、显示帧及答案并防止重复提交时，在输入或执行结果不符合条件时给出原因。 | |
| N335 | 校验或错误提示<br><code>manual_recognition.py:169</code> | <code>f"坐标 {point} 超出真实截图范围：x=0～{width-1}，y=0～{height-1}"</code> | 将人工点选位置校验为当前原图范围内坐标时，在输入或执行结果不符合条件时给出原因。 | |
| N336 | 校验或错误提示<br><code>manual_recognition.py:179</code><br>关联：N323, N326, N337 | <code>人工试运行已停止</code> | 后台把本次真实截图交给人工并等待答案时，在输入或执行结果不符合条件时给出原因。<br>注意：人工日志前缀参与来源标记检查；不应连带改动内部 manual_trial 值。 | |
| N337 | 校验或错误提示<br><code>manual_recognition.py:182</code><br>关联：N323, N326, N336 | <code>同一人工提供器同时出现多个请求</code> | 后台把本次真实截图交给人工并等待答案时，在输入或执行结果不符合条件时给出原因。 | |
| N338 | 校验或错误提示<br><code>manual_recognition.py:228</code> | <code>人工等待已取消</code> | 人工请求被停止或关闭取消时，在输入或执行结果不符合条件时给出原因。 | |
| N339 | 校验或错误提示<br><code>manual_recognition.py:246</code><br>关联：N324 | <code>人工判断依据截图编码失败</code> | 保存人工最终判断所依据的原图和记录时，在输入或执行结果不符合条件时给出原因。 | |
| N340 | 校验或错误提示<br><code>manual_recognition.py:261</code><br>关联：N305, N306, N307, N308 | <code>等待型人工测试模式需要原截图方法、计时起点、超时和轮询间隔</code> | 人工判断本次模板有无或位置时，在输入或执行结果不符合条件时给出原因。 | |
| N341 | 校验或错误提示<br><code>ui/gui_app.py:321</code><br>关联：N286, N287 | <code>人工测试模式已关闭</code> | 接收当前人工请求的答案并交回原流程时，在输入或执行结果不符合条件时给出原因。 | |
| N342 | 校验或错误提示<br><code>ui/manual_recognition_dialog.py:36</code> | <code>请点选截图范围内的目标</code> | 显示当前人工判断弹窗、图像和等待计时时，在输入或执行结果不符合条件时给出原因。 | |
| N343 | 校验或错误提示<br><code>ui/manual_recognition_dialog.py:128</code> | <code>本次截图无法展示</code> | 显示当前人工判断弹窗、图像和等待计时时，在输入或执行结果不符合条件时给出原因。 | |

### 08 HIT／MISS 恢复与异常重启（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N344 | 日志<br><code>flows/auto_probe_recovery.py:203</code><br>关联：N345, N346, N368, N369, N370, N371（其余见索引） | <code>检测到 HIT：跳过 REJECT/retry，直接恢复正常联网</code> | 命中写回后恢复联网等待、再准备下一发时，记录这一步的参数、结果或异常。 | |
| N345 | 日志<br><code>flows/auto_probe_recovery.py:233</code><br>关联：N344, N346, N368, N369, N370, N371（其余见索引） | <code>HIT 已恢复正常联网，等待 %.1f 秒让结果稳定</code> | 命中写回后恢复联网等待、再准备下一发时，记录这一步的参数、结果或异常。 | |
| N346 | 日志<br><code>flows/auto_probe_recovery.py:291</code><br>关联：N344, N345, N368, N369, N370, N371（其余见索引） | <code>HIT 恢复完成：联网等待=%.1f秒，page=%s，weak=%s，reject=%s</code> | 命中写回后恢复联网等待、再准备下一发时，记录这一步的参数、结果或异常。 | |
| N347 | 日志<br><code>flows/auto_probe_recovery.py:379</code><br>关联：N348, N349, N350, N351, N352, N373（其余见索引） | <code>开始执行 MISS 恢复链</code> | 未命中写回后断网等待重试、再恢复活动时，记录这一步的参数、结果或异常。 | |
| N348 | 日志<br><code>flows/auto_probe_recovery.py:426</code><br>关联：N347, N349, N350, N351, N352, N373（其余见索引） | <code>响应停止请求时关闭 REJECT 失败</code> | 未命中写回后断网等待重试、再恢复活动时，记录这一步的参数、结果或异常。 | |
| N349 | 日志<br><code>flows/auto_probe_recovery.py:436</code><br>关联：N347, N348, N350, N351, N352, N373（其余见索引） | <code>等待 retry 结束后关闭 REJECT 失败</code> | 未命中写回后断网等待重试、再恢复活动时，记录这一步的参数、结果或异常。 | |
| N350 | 日志<br><code>flows/auto_probe_recovery.py:452</code><br>关联：N347, N348, N349, N351, N352, N373（其余见索引） | <code>REJECT 后没有检测到 retry；已关闭 REJECT，弱网 DROP 保持开启</code> | 未命中写回后断网等待重试、再恢复活动时，记录这一步的参数、结果或异常。 | |
| N351 | 日志<br><code>flows/auto_probe_recovery.py:480</code><br>关联：N347, N348, N349, N350, N352, N373（其余见索引） | <code>已点击 retry：中心=%s，相似度=%.3f</code> | 未命中写回后断网等待重试、再恢复活动时，记录这一步的参数、结果或异常。 | |
| N352 | 日志<br><code>flows/auto_probe_recovery.py:545</code><br>关联：N347, N348, N349, N350, N351, N373（其余见索引） | <code>MISS 恢复完成：page=%s，weak=%s，reject=%s</code> | 未命中写回后断网等待重试、再恢复活动时，记录这一步的参数、结果或异常。 | |
| N353 | 日志<br><code>flows/auto_probe_recovery.py:86</code><br>关联：N196, N354, N355, N379, N380 | <code>开始等待模板：%s，超时=%.1f秒，阈值=%.3f</code> | 未命中后等待重试按钮时，记录这一步的参数、结果或异常。 | |
| N354 | 日志<br><code>flows/auto_probe_recovery.py:124</code><br>关联：N197, N353, N355, N379, N380 | <code>等待模板成功：%s，相似度=%.3f，中心=%s，检测次数=%s</code> | 未命中后等待重试按钮时，记录这一步的参数、结果或异常。 | |
| N355 | 日志<br><code>flows/auto_probe_recovery.py:168</code><br>关联：N353, N354, N379, N380 | <code>等待模板超时：%s，%.1f秒内未出现，最高相似度=%.3f，阈值=%.3f，检测次数=%s，失败截图=%s</code> | 未命中后等待重试按钮时，记录这一步的参数、结果或异常。 | |
| N356 | 日志<br><code>flows/auto_probe_recovery.py:315</code><br>关联：N357, N358 | <code>策略已确认全部潜艇：进入胜利处理边界，停止重新弱网和重进活动</code> | 策略完成后提交最后结果并保持正常联网时，记录这一步的参数、结果或异常。 | |
| N357 | 日志<br><code>flows/auto_probe_recovery.py:329</code><br>关联：N356, N358 | <code>最后一发 HIT 已恢复正常联网，等待 %.1f 秒完成结算</code> | 策略完成后提交最后结果并保持正常联网时，记录这一步的参数、结果或异常。 | |
| N358 | 日志<br><code>flows/auto_probe_recovery.py:357</code><br>关联：N356, N357 | <code>策略完成后的临时收尾完成：page=%s，weak=%s，reject=%s</code> | 策略完成后提交最后结果并保持正常联网时，记录这一步的参数、结果或异常。 | |
| N359 | 日志<br><code>flows/auto_probe_exception_recovery.py:36</code><br>关联：N360, N381, N382, N383 | <code>自动探测异常恢复：开始第 %s/%s 次重启</code> | 单发异常后重启游戏并恢复当前进度时，记录这一步的参数、结果或异常。 | |
| N360 | 日志<br><code>flows/auto_probe_exception_recovery.py:89</code><br>关联：N359, N381, N382, N383 | <code>自动探测异常重启恢复成功：attempt=%s，page=%s，weak=%s，reject=%s</code> | 单发异常后重启游戏并恢复当前进度时，记录这一步的参数、结果或异常。 | |
| N361 | 日志<br><code>flows/auto_probe_loop.py:118</code><br>关联：N362, N367, N384 | <code>自动探测当前发发生可恢复异常：%s</code> | 本发发生可恢复异常后按原次数重启并继续时，记录这一步的参数、结果或异常。 | |
| N362 | 日志<br><code>flows/auto_probe_loop.py:157</code><br>关联：N361, N367, N384 | <code>自动探测第 %s/%s 次异常重启恢复失败：%s</code> | 本发发生可恢复异常后按原次数重启并继续时，记录这一步的参数、结果或异常。 | |
| N363 | 日志<br><code>flows/auto_probe_exception_recovery.py:114</code><br>关联：N364, N365, N366 | <code>自动循环安全停止时第 %s/%s 次恢复或核验网络失败</code> | 异常停止前清理并核验网络规则时，记录这一步的参数、结果或异常。 | |
| N364 | 日志<br><code>flows/auto_probe_exception_recovery.py:125</code><br>关联：N363, N365, N366 | <code>自动循环安全停止后网络规则仍存在：attempt=%s/%s，weak=%s，reject=%s</code> | 异常停止前清理并核验网络规则时，记录这一步的参数、结果或异常。 | |
| N365 | 日志<br><code>flows/auto_probe_exception_recovery.py:135</code><br>关联：N363, N364, N366 | <code>自动循环安全停止清理完成：DROP=False，REJECT=False</code> | 异常停止前清理并核验网络规则时，记录这一步的参数、结果或异常。 | |
| N366 | 日志<br><code>flows/auto_probe_exception_recovery.py:140</code><br>关联：N363, N364, N365 | <code>自动循环安全停止网络清理耗尽 %s 次尝试</code> | 异常停止前清理并核验网络规则时，记录这一步的参数、结果或异常。 | |
| N367 | 显示组成文字／诊断消息<br><code>flows/auto_probe_loop.py:177</code><br>关联：N361, N362, N384 | <code>"自动探测异常恢复失败："<br>            f"已尝试重启 {max_attempts} 次；"<br>            f"网络清理={'成功' if cleanup_ok else '失败'}；"<br>            f"最后错误={last_error}"</code> | 本发发生可恢复异常后按原次数重启并继续时，组成界面提示或该步骤的诊断信息。 | |
| N368 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:214</code><br>关联：N344, N345, N346, N369, N370, N371（其余见索引） | <code>HIT 恢复前 REJECT 已经开启，当前网络状态异常</code> | 命中写回后恢复联网等待、再准备下一发时，在输入或执行结果不符合条件时给出原因。 | |
| N369 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:219</code><br>关联：N344, N345, N346, N368, N370, N371（其余见索引） | <code>HIT 恢复前DROP 弱网状态没有开启</code> | 命中写回后恢复联网等待、再准备下一发时，在输入或执行结果不符合条件时给出原因。 | |
| N370 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:265</code><br>关联：N344, N345, N346, N368, N369, N371（其余见索引） | <code>HIT 恢复失败：5 秒联网后没有回到活动棋盘页面</code> | 命中写回后恢复联网等待、再准备下一发时，在输入或执行结果不符合条件时给出原因。 | |
| N371 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:270</code><br>关联：N344, N345, N346, N368, N369, N370（其余见索引） | <code>HIT 恢复失败：REJECT 意外处于开启状态</code> | 命中写回后恢复联网等待、再准备下一发时，在输入或执行结果不符合条件时给出原因。 | |
| N372 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:275</code><br>关联：N344, N345, N346, N368, N369, N370（其余见索引） | <code>HIT 恢复失败：DROP 弱网状态没有重新开启</code> | 命中写回后恢复联网等待、再准备下一发时，在输入或执行结果不符合条件时给出原因。 | |
| N373 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:390</code><br>关联：N347, N348, N349, N350, N351, N352（其余见索引） | <code>进入恢复链前 REJECT 已经开启，当前网络状态异常</code> | 未命中写回后断网等待重试、再恢复活动时，在输入或执行结果不符合条件时给出原因。 | |
| N374 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:396</code><br>关联：N347, N348, N349, N350, N351, N352（其余见索引） | <code>进入恢复链前DROP 弱网状态没有开启</code> | 未命中写回后断网等待重试、再恢复活动时，在输入或执行结果不符合条件时给出原因。 | |
| N375 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:456</code><br>关联：N347, N348, N349, N350, N351, N352（其余见索引） | <code>"单发恢复失败："<br>            f"{AUTO_PROBE_CONFIG.retry_wait_timeout:g} 秒内"<br>            "没有出现 retry 按钮；"<br>            f"失败截图={retry_failure_path}"</code> | 未命中写回后断网等待重试、再恢复活动时，在输入或执行结果不符合条件时给出原因。 | |
| N376 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:516</code><br>关联：N347, N348, N349, N350, N351, N352（其余见索引） | <code>单发恢复失败：恢复后没有回到活动棋盘页面</code> | 未命中写回后断网等待重试、再恢复活动时，在输入或执行结果不符合条件时给出原因。 | |
| N377 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:522</code><br>关联：N347, N348, N349, N350, N351, N352（其余见索引） | <code>单发恢复失败：恢复后 REJECT 断网状态仍然开启</code> | 未命中写回后断网等待重试、再恢复活动时，在输入或执行结果不符合条件时给出原因。 | |
| N378 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:528</code><br>关联：N347, N348, N349, N350, N351, N352（其余见索引） | <code>单发恢复失败：恢复后DROP 弱网状态没有重新开启</code> | 未命中写回后断网等待重试、再恢复活动时，在输入或执行结果不符合条件时给出原因。 | |
| N379 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:67</code><br>关联：N353, N354, N355, N380 | <code>f"缺少 retry 模板：{template_path}"</code> | 未命中后等待重试按钮时，在输入或执行结果不符合条件时给出原因。 | |
| N380 | 校验或错误提示<br><code>flows/auto_probe_recovery.py:163</code><br>关联：N353, N354, N355, N379 | <code>"retry 识别失败截图保存失败："<br>                        f"{failure_path}"</code> | 未命中后等待重试按钮时，在输入或执行结果不符合条件时给出原因。 | |
| N381 | 校验或错误提示<br><code>flows/auto_probe_exception_recovery.py:66</code><br>关联：N359, N360, N382, N383 | <code>"异常重启恢复失败："<br>            f"最终页面={final_state.value}"</code> | 单发异常后重启游戏并恢复当前进度时，在输入或执行结果不符合条件时给出原因。 | |
| N382 | 校验或错误提示<br><code>flows/auto_probe_exception_recovery.py:72</code><br>关联：N359, N360, N381, N383 | <code>异常重启恢复失败：REJECT 断网状态仍然开启</code> | 单发异常后重启游戏并恢复当前进度时，在输入或执行结果不符合条件时给出原因。 | |
| N383 | 校验或错误提示<br><code>flows/auto_probe_exception_recovery.py:77</code><br>关联：N359, N360, N381, N382 | <code>异常重启恢复失败：DROP 弱网状态没有重新开启</code> | 单发异常后重启游戏并恢复当前进度时，在输入或执行结果不符合条件时给出原因。 | |
| N384 | 校验或错误提示<br><code>flows/auto_probe_loop.py:81</code><br>关联：N361, N362, N367 | <code>max_restart_attempts 必须大于 0</code> | 本发发生可恢复异常后按原次数重启并继续时，在输入或执行结果不符合条件时给出原因。 | |

### 09 胜利处理与下一关（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N385 | 状态显示<br><code>ui/gui_app.py:1043</code><br>关联：N386, N387 | <code>f"第 {context.current_level} 关运行中"</code> | 主线程接收后台结果、恢复或换关消息时，显示当前进度或操作结果。 | |
| N386 | 状态显示<br><code>ui/gui_app.py:1044</code><br>关联：N385, N387 | <code>f"已进入第 {context.current_level} 关"</code> | 主线程接收后台结果、恢复或换关消息时，显示当前进度或操作结果。 | |
| N387 | GUI 日志<br><code>ui/gui_app.py:1046</code><br>关联：N385, N386 | <code>f"关卡切换完成：第 {context.current_level} 关；新棋盘和新策略已同步。"</code> | 主线程接收后台结果、恢复或换关消息时，把这一步的操作及结果写入主窗口日志。 | |
| N388 | 日志<br><code>flows/victory_flow.py:40</code><br>关联：N389, N391, N392, N393 | <code>处理第 %s 个胜利/结算页面</code> | 等待胜利画面并继续到下一关活动棋盘页面时，记录这一步的参数、结果或异常。 | |
| N389 | 日志<br><code>flows/victory_flow.py:74</code><br>关联：N388, N391, N392, N393 | <code>胜利页面处理完成，下一关活动棋盘页面已就绪</code> | 等待胜利画面并继续到下一关活动棋盘页面时，记录这一步的参数、结果或异常。 | |
| N390 | 日志<br><code>flows/level_loop.py:135</code><br>关联：N394 | <code>进入第 %s 关：已创建新棋盘和新策略</code> | 串联单关循环、胜利处理与下一关状态创建时，记录这一步的参数、结果或异常。 | |
| N391 | 校验或错误提示<br><code>flows/victory_flow.py:33</code><br>关联：N388, N389, N392, N393 | <code>f"等待胜利画面超时（{flow_config.victory_wait_timeout:.1f} 秒）"</code> | 等待胜利画面并继续到下一关活动棋盘页面时，在输入或执行结果不符合条件时给出原因。 | |
| N392 | 校验或错误提示<br><code>flows/victory_flow.py:61</code><br>关联：N388, N389, N391, N393 | <code>f"连续胜利页面超过上限 {flow_config.victory_max_rounds}"</code> | 等待胜利画面并继续到下一关活动棋盘页面时，在输入或执行结果不符合条件时给出原因。 | |
| N393 | 校验或错误提示<br><code>flows/victory_flow.py:71</code><br>关联：N388, N389, N391, N392 | <code>f"胜利处理后未进入下一关（{flow_config.next_level_ready_timeout:.1f} 秒）"</code> | 等待胜利画面并继续到下一关活动棋盘页面时，在输入或执行结果不符合条件时给出原因。 | |
| N394 | 校验或错误提示<br><code>flows/level_loop.py:80</code><br>关联：N390 | <code>max_levels 必须大于 0</code> | 串联单关循环、胜利处理与下一关状态创建时，在输入或执行结果不符合条件时给出原因。 | |

### 10 棋盘、策略、图例与悬停（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N395 | 界面文字<br><code>ui/board_view.py:132</code><br>关联：N404, N405, N406, N407, N408, N409 | <code>声纳棋盘</code> | 显示原棋盘与策略信息时，标注相应操作区或提示信息。 | |
| N396 | 界面文字<br><code>ui/app_layout.py:495</code><br>关联：N397 | <code>棋盘与策略同步</code> | 构建原主窗口操作区时，标注相应操作区或提示信息。 | |
| N397 | 界面文字<br><code>ui/app_layout.py:538</code><br>关联：N396 | <code>棋盘与当前选格策略同步；灰色同时表示实际未命中和策略排除格</code> | 构建原主窗口操作区时，标注相应操作区或提示信息。 | |
| N398 | 界面文字<br><code>ui/board_view.py:614</code> | <code>f"{row + 1},{col + 1}"</code> | 显示原棋盘与策略信息时，标注相应操作区或提示信息。 | |
| N399 | 按钮文案<br><code>ui/app_layout.py:518</code> | <code>重置棋盘状态</code> | 在允许操作时重新建立当前关卡的棋盘和策略。 | |
| N400 | 状态显示<br><code>ui/board_view.py:109；ui/board_view.py:353</code><br>共 4 处，完整位置见索引 | <code>移动鼠标到格子上，可查看逻辑坐标、模拟器坐标和当前状态</code> | 显示原棋盘与策略信息时，显示当前进度或操作结果。 | |
| N401 | 状态显示<br><code>ui/board_view.py:394</code><br>关联：N402, N424, N425, N426 | <code>f"{board_snapshot.grid_size}×{board_snapshot.grid_size} &#124; "<br>            f"潜艇 [{submarine_text}] &#124; "<br>            f"坐标映射 {board_snapshot.mapped_count}/{total}"</code> | 刷新棋盘尺寸、策略、剩余潜艇和下一目标摘要时，显示当前进度或操作结果。 | |
| N402 | 状态显示<br><code>ui/board_view.py:401</code><br>关联：N401, N424, N425, N426 | <code>策略：未绑定</code> | 刷新棋盘尺寸、策略、剩余潜艇和下一目标摘要时，显示当前进度或操作结果。 | |
| N403 | 状态显示<br><code>ui/board_view.py:1161</code><br>关联：N427, N428 | <code>f"逻辑格：({row},{col}) &#124; "<br>            f"{point_text} &#124; "<br>            f"状态：{state_text}"</code> | 鼠标悬停格子、查看逻辑坐标及设备坐标时，显示当前进度或操作结果。 | |
| N404 | 棋盘图例<br><code>ui/board_view.py:201</code><br>关联：N395, N405, N406, N407, N408, N409（其余见索引） | <code>未探测</code> | 该格尚无探测结果。 | |
| N405 | 棋盘图例<br><code>ui/board_view.py:202</code><br>关联：N395, N404, N406, N407, N408, N409（其余见索引） | <code>下一步选择</code> | 该格被当前策略选为下一次探测目标。 | |
| N406 | 棋盘图例<br><code>ui/board_view.py:203</code><br>关联：N395, N404, N405, N407, N408, N409 | <code>未命中 / 已排除</code> | 棋盘用同一种灰色同时表示真实未命中和策略排除。 | |
| N407 | 棋盘图例<br><code>ui/board_view.py:204</code><br>关联：N395, N404, N405, N406, N408, N409（其余见索引） | <code>命中</code> | 显示原棋盘与策略信息时，说明对应棋盘颜色的含义。 | |
| N408 | 棋盘图例<br><code>ui/board_view.py:205</code><br>关联：N395, N404, N405, N406, N407, N409（其余见索引） | <code>已确认潜艇</code> | 该格属于经原策略或人工改盘合法性校验确认的整艘潜艇。 | |
| N409 | 棋盘图例<br><code>ui/board_view.py:206</code><br>关联：N395, N404, N405, N406, N407, N408 | <code>人工临时修改</code> | 该格包含尚未应用到正式棋盘的人工改动。 | |
| N410 | 格子悬停状态<br><code>ui/board_view.py:1176</code><br>关联：N405, N411, N412, N413, N414, N415 | <code>下一步选择</code> | 该格被当前策略选为下一次探测目标。 | |
| N411 | 格子悬停状态<br><code>ui/board_view.py:1179</code><br>关联：N408, N410, N412, N413, N414, N415 | <code>已确认潜艇</code> | 该格属于经原策略或人工改盘合法性校验确认的整艘潜艇。 | |
| N412 | 格子悬停状态<br><code>ui/board_view.py:1182</code><br>关联：N407, N410, N411, N413, N414, N415 | <code>命中</code> | 把格子当前状态转换为悬停提示时，显示该格的当前含义。 | |
| N413 | 格子悬停状态<br><code>ui/board_view.py:1185</code><br>关联：N410, N411, N412, N414, N415 | <code>未命中</code> | 把格子当前状态转换为悬停提示时，显示该格的当前含义。 | |
| N414 | 格子悬停状态<br><code>ui/board_view.py:1191</code><br>关联：N410, N411, N412, N413, N415 | <code>策略排除</code> | 策略已推断该格无需继续探测。 | |
| N415 | 格子悬停状态<br><code>ui/board_view.py:1193</code><br>关联：N404, N410, N411, N412, N413, N414 | <code>未探测</code> | 该格尚无探测结果。 | |
| N416 | 弹窗标题<br><code>ui/gui_app.py:622</code><br>关联：N030, N158, N417, N418, N419, N420 | <code>人工干预中</code> | 停止状态下重建当前关卡棋盘与策略时，标明本次提醒的主题。 | |
| N417 | 弹窗标题<br><code>ui/gui_app.py:628</code><br>关联：N031, N416, N418, N419, N420 | <code>自动循环运行中</code> | 停止状态下重建当前关卡棋盘与策略时，标明本次提醒的主题。 | |
| N418 | 弹窗正文<br><code>ui/gui_app.py:623</code><br>关联：N416, N417, N419, N420 | <code>请先退出人工干预，再重置棋盘。</code> | 停止状态下重建当前关卡棋盘与策略时，说明当前操作的条件、结果或注意事项。 | |
| N419 | 弹窗正文<br><code>ui/gui_app.py:629</code><br>关联：N416, N417, N418, N420 | <code>请先停止自动循环，再重置棋盘。</code> | 停止状态下重建当前关卡棋盘与策略时，说明当前操作的条件、结果或注意事项。 | |
| N420 | GUI 日志<br><code>ui/gui_app.py:636</code><br>关联：N416, N417, N418, N419 | <code>"声纳棋盘和策略状态已重置；"<br>            f"下一格={next_cell}"</code> | 停止状态下重建当前关卡棋盘与策略时，把这一步的操作及结果写入主窗口日志。 | |
| N421 | 显示组成文字／诊断消息<br><code>ui/board_view.py:55</code><br>关联：N422, N423 | <code>巡航</code> | 策略尚未追击未解决命中时，按巡航规则寻找下一个目标。 | |
| N422 | 显示组成文字／诊断消息<br><code>ui/board_view.py:56</code><br>关联：N421, N423 | <code>追击</code> | 策略沿已有未解决命中继续寻找潜艇所在格。 | |
| N423 | 显示组成文字／诊断消息<br><code>ui/board_view.py:57</code><br>关联：N421, N422 | <code>完成</code> | 策略已确认本关所需潜艇，准备进入完成及胜利流程。 | |
| N424 | 显示组成文字／诊断消息<br><code>ui/board_view.py:421</code><br>关联：N401, N402, N425, N426 | <code>无</code> | 策略当前没有可显示的下一目标格。 | |
| N425 | 显示组成文字／诊断消息<br><code>ui/board_view.py:433</code><br>关联：N401, N402, N424, N426 | <code>无</code> | 当前剩余潜艇列表为空。 | |
| N426 | 显示组成文字／诊断消息<br><code>ui/board_view.py:436</code><br>关联：N401, N402, N424, N425 | <code>f"策略：{mode_text} &#124; "<br>            f"下一格 {next_text} &#124; "<br>            f"已探测 {explored_count} &#124; "<br>            f"已排除 {len(strategy_snapshot.excluded_cells)} &#124; "<br>            f"已确认 {len(strategy_snapshot.confirmed_ships)} &#124; "<br>            f"剩余 [{remaining_text}]"</code> | 刷新棋盘尺寸、策略、剩余潜艇和下一目标摘要时，组成界面提示或该步骤的诊断信息。 | |
| N427 | 显示组成文字／诊断消息<br><code>ui/board_view.py:1150</code><br>关联：N403, N428 | <code>模拟器坐标：未绑定</code> | 鼠标悬停格子、查看逻辑坐标及设备坐标时，组成界面提示或该步骤的诊断信息。 | |
| N428 | 显示组成文字／诊断消息<br><code>ui/board_view.py:1152</code><br>关联：N403, N427 | <code>f"模拟器坐标：{point}"</code> | 鼠标悬停格子、查看逻辑坐标及设备坐标时，组成界面提示或该步骤的诊断信息。 | |

### 11 人工干预改盘（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N429 | 按钮文案<br><code>ui/gui_app.py:255</code><br>关联：N430, N431, N432, N433, N434 | <code>退出人工干预</code> | 丢弃尚未应用的临时修改并返回正式棋盘显示。 | |
| N430 | 按钮文案<br><code>ui/gui_app.py:256</code><br>关联：N429, N431, N432, N433, N434 | <code>正在开启人工干预…</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N431 | 按钮文案<br><code>ui/gui_app.py:257</code><br>关联：N429, N430, N432, N433, N434 | <code>正在退出人工干预…</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N432 | 按钮文案<br><code>ui/gui_app.py:258</code><br>关联：N429, N430, N431, N433, N434 | <code>自动循环中</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N433 | 按钮文案<br><code>ui/gui_app.py:259</code><br>关联：N429, N430, N431, N432, N434 | <code>人工干预不可用</code> | 主窗口刷新操作状态或处理结果时，显示可执行操作或按钮当前状态。 | |
| N434 | 按钮文案<br><code>ui/app_layout.py:527；ui/gui_app.py:254</code><br>关联：N429, N430, N431, N432, N433 | <code>开启人工干预</code> | 进入临时改盘模式，允许修改格子和潜艇事实。 | |
| N435 | 按钮文案<br><code>ui/app_layout.py:549</code> | <code>撤回</code> | 撤销最近一次临时人工编辑。 | |
| N436 | 按钮文案<br><code>ui/app_layout.py:555</code> | <code>重做</code> | 重新执行最近一次被撤销的临时人工编辑。 | |
| N437 | 按钮文案<br><code>ui/app_layout.py:561</code> | <code>取消修改</code> | 清除本轮临时改动，恢复进入编辑时的棋盘。 | |
| N438 | 按钮文案<br><code>ui/app_layout.py:566</code> | <code>应用修改</code> | 校验临时棋盘与潜艇合法性后重建正式策略，保持循环停止。 | |
| N439 | 状态显示<br><code>ui/gui_app.py:752</code><br>关联：N448 | <code>人工干预中：棋盘修改仅保存在临时缓存</code> | 进入仅修改临时棋盘的人工干预模式时，显示当前进度或操作结果。 | |
| N440 | 状态显示<br><code>ui/gui_app.py:764</code><br>关联：N449 | <code>已退出人工干预，临时修改已丢弃</code> | 退出人工干预并丢弃临时修改时，显示当前进度或操作结果。 | |
| N441 | 状态显示<br><code>ui/gui_app.py:775</code><br>关联：N450 | <code>f"人工编辑：{message}"</code> | 反馈临时棋盘编辑结果时，显示当前进度或操作结果。 | |
| N442 | 状态显示<br><code>ui/gui_app.py:836</code><br>关联：N443, N444, N445, N446, N447, N451（其余见索引） | <code>f"人工修改校验失败：{exc}"</code> | 校验人工改盘并重建正式策略、保持循环停止时，显示当前进度或操作结果。 | |
| N443 | 状态显示<br><code>ui/gui_app.py:841</code><br>关联：N442, N444, N445, N446, N447, N451（其余见索引） | <code>人工修改应用失败，正式状态已回滚</code> | 校验人工改盘并重建正式策略、保持循环停止时，显示当前进度或操作结果。 | |
| N444 | 状态显示<br><code>ui/gui_app.py:859</code><br>关联：N442, N443, N445, N446, N447, N451（其余见索引） | <code>f"人工修改已应用；下一目标格={result.next_cell}；自动循环保持停止"</code> | 校验人工改盘并重建正式策略、保持循环停止时，显示当前进度或操作结果。 | |
| N445 | 弹窗标题<br><code>ui/gui_app.py:822</code><br>关联：N442, N443, N444, N446, N447, N451（其余见索引） | <code>自动循环仍在运行</code> | 校验人工改盘并重建正式策略、保持循环停止时，标明本次提醒的主题。 | |
| N446 | 弹窗标题<br><code>ui/gui_app.py:838</code><br>关联：N442, N443, N444, N445, N447, N451（其余见索引） | <code>无法应用人工修改</code> | 校验人工改盘并重建正式策略、保持循环停止时，标明本次提醒的主题。 | |
| N447 | 弹窗正文<br><code>ui/gui_app.py:823</code><br>关联：N442, N443, N444, N445, N446, N451（其余见索引） | <code>等待自动循环完全停止后才能应用人工修改。</code> | 校验人工改盘并重建正式策略、保持循环停止时，说明当前操作的条件、结果或注意事项。 | |
| N448 | GUI 日志<br><code>ui/gui_app.py:753</code><br>关联：N439 | <code>已进入基础人工干预模式；未操作模拟器和网络</code> | 进入仅修改临时棋盘的人工干预模式时，把这一步的操作及结果写入主窗口日志。 | |
| N449 | GUI 日志<br><code>ui/gui_app.py:765</code><br>关联：N440 | <code>已退出人工干预模式；正式棋盘保持不变</code> | 退出人工干预并丢弃临时修改时，把这一步的操作及结果写入主窗口日志。 | |
| N450 | GUI 日志<br><code>ui/gui_app.py:776</code><br>关联：N441 | <code>f"人工编辑：{message}"</code> | 反馈临时棋盘编辑结果时，把这一步的操作及结果写入主窗口日志。 | |
| N451 | GUI 日志<br><code>ui/gui_app.py:837</code><br>关联：N442, N443, N444, N445, N446, N447（其余见索引） | <code>f"人工修改校验失败：{exc}"</code> | 校验人工改盘并重建正式策略、保持循环停止时，把这一步的操作及结果写入主窗口日志。 | |
| N452 | GUI 日志<br><code>ui/gui_app.py:842</code><br>关联：N442, N443, N444, N445, N446, N447（其余见索引） | <code>f"人工修改应用失败，已回滚：{exc}"</code> | 校验人工改盘并重建正式策略、保持循环停止时，把这一步的操作及结果写入主窗口日志。 | |
| N453 | GUI 日志<br><code>ui/gui_app.py:862</code><br>关联：N442, N443, N444, N445, N446, N447（其余见索引） | <code>"人工修改已应用："<br>            f"已确认={len(result.strategy_snapshot.confirmed_ships)}，"<br>            f"剩余={result.strategy_snapshot.remaining_submarines}，"<br>            f"已排除={len(result.strategy_snapshot.excluded_cells)}，"<br>            f"下一格={result.next_cell}；未操作模拟器和网络"</code> | 校验人工改盘并重建正式策略、保持循环停止时，把这一步的操作及结果写入主窗口日志。 | |
| N454 | 人工编辑反馈<br><code>ui/board_view.py:1010</code><br>关联：N455 | <code>f"已暂存取消长度 {ship.length} 的整艘潜艇确认"</code> | 长按棋盘格以选择或取消整艘潜艇时，提示本次临时改盘的结果。 | |
| N455 | 人工编辑反馈<br><code>ui/board_view.py:1017</code><br>关联：N454 | <code>长按完成：拖动选择连续 HIT 潜艇</code> | 长按棋盘格以选择或取消整艘潜艇时，提示本次临时改盘的结果。 | |
| N456 | 人工编辑反馈<br><code>ui/board_view.py:1082</code><br>关联：N457 | <code>f"已暂存确认长度 {ship.length} 的潜艇"</code> | 松开鼠标提交临时格子或潜艇编辑时，提示本次临时改盘的结果。 | |
| N457 | 人工编辑反馈<br><code>ui/board_view.py:1087</code><br>关联：N456 | <code>f"格子 {cell} 临时修改为 {state.value.upper()}"</code> | 松开鼠标提交临时格子或潜艇编辑时，提示本次临时改盘的结果。 | |
| N458 | 人工编辑反馈<br><code>ui/gui_app.py:796</code> | <code>已撤回最近一次人工操作</code> | 撤回最近一次临时改盘操作时，提示本次临时改盘的结果。 | |
| N459 | 人工编辑反馈<br><code>ui/gui_app.py:804</code> | <code>已重做最近一次人工操作</code> | 重做已撤回的临时改盘操作时，提示本次临时改盘的结果。 | |
| N460 | 人工编辑反馈<br><code>ui/gui_app.py:813</code> | <code>已取消本次全部临时修改</code> | 取消本轮全部临时改盘操作时，提示本次临时改盘的结果。 | |
| N461 | 校验或错误提示<br><code>sonar/manual_intervention.py:136</code> | <code>请先长按取消整艘潜艇确认</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N462 | 校验或错误提示<br><code>sonar/manual_intervention.py:152</code><br>关联：N463, N464 | <code>候选长度不符合当前关卡潜艇配置</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N463 | 校验或错误提示<br><code>sonar/manual_intervention.py:154</code><br>关联：N462, N464 | <code>候选潜艇必须全部由连续 HIT 格组成</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N464 | 校验或错误提示<br><code>sonar/manual_intervention.py:158</code><br>关联：N462, N463 | <code>该长度潜艇的可确认数量已经用完</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N465 | 校验或错误提示<br><code>sonar/manual_intervention.py:183</code> | <code>该 SUNK 格没有对应的完整潜艇记录</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N466 | 校验或错误提示<br><code>sonar/manual_intervention.py:223</code><br>关联：N467, N468, N469, N470, N471, N472（其余见索引） | <code>f"第 {index} 艘潜艇：{exc}"</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N467 | 校验或错误提示<br><code>sonar/manual_intervention.py:226</code><br>关联：N466, N468, N469, N470, N471, N472（其余见索引） | <code>f"长度 {length} 不属于当前潜艇配置"</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N468 | 校验或错误提示<br><code>sonar/manual_intervention.py:229</code><br>关联：N466, N467, N469, N470, N471, N472（其余见索引） | <code>f"长度 {length} 的潜艇数量超过关卡配置"</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N469 | 校验或错误提示<br><code>sonar/manual_intervention.py:232</code><br>关联：N466, N467, N468, N470, N471, N472（其余见索引） | <code>f"已确认潜艇发生重叠：{sorted(overlap)}"</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N470 | 校验或错误提示<br><code>sonar/manual_intervention.py:236</code><br>关联：N466, N467, N468, N469, N471, N472（其余见索引） | <code>f"已确认潜艇内部包含 MISS：{cell}"</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N471 | 校验或错误提示<br><code>sonar/manual_intervention.py:239</code><br>关联：N466, N467, N468, N469, N470, N472（其余见索引） | <code>f"已确认潜艇与棋盘状态冲突：{cell}={state.value}"</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N472 | 校验或错误提示<br><code>sonar/manual_intervention.py:251</code><br>关联：N466, N467, N468, N469, N470, N471（其余见索引） | <code>SUNK 格与已确认潜艇记录不一致</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N473 | 校验或错误提示<br><code>sonar/manual_intervention.py:259</code><br>关联：N466, N467, N468, N469, N470, N471（其余见索引） | <code>f"第 {index} 艘潜艇违反安全间距："<br>                        f"{sorted(ship_conflicts)}"</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N474 | 校验或错误提示<br><code>sonar/manual_intervention.py:269</code><br>关联：N466, N467, N468, N469, N470, N471（其余见索引） | <code>f"第 {index} 艘潜艇安全区域存在 HIT："<br>                        f"{sorted(hit_conflicts)}"</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N475 | 校验或错误提示<br><code>sonar/manual_intervention.py:292</code><br>关联：N476, N477 | <code>候选潜艇格为空或重复</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N476 | 校验或错误提示<br><code>sonar/manual_intervention.py:302</code><br>关联：N475, N477 | <code>候选潜艇只能横向或纵向</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N477 | 校验或错误提示<br><code>sonar/manual_intervention.py:304</code><br>关联：N475, N476 | <code>候选潜艇格必须连续</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N478 | 校验或错误提示<br><code>sonar/manual_intervention.py:310</code><br>关联：N537 | <code>f"格子超出棋盘范围：{cell}"</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N479 | 校验或错误提示<br><code>sonar/manual_intervention.py:370</code><br>关联：N480 | <code>人工缓存与当前正式棋盘配置不一致</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |
| N480 | 校验或错误提示<br><code>sonar/manual_intervention.py:394</code><br>关联：N479 | <code>f"人工修改应用失败，回滚同时失败：{details}"</code> | 检查临时改盘事实与潜艇合法性时，在输入或执行结果不符合条件时给出原因。 | |

### 12 停止、结束与窗口退出（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N481 | 状态显示<br><code>ui/gui_app.py:946</code><br>关联：N482, N489 | <code>停止中</code> | 请求后台在安全动作边界停止时，显示当前进度或操作结果。 | |
| N482 | 状态显示<br><code>ui/gui_app.py:947</code><br>关联：N481, N489 | <code>已请求停止：等待当前小动作完成...</code> | 请求后台在安全动作边界停止时，显示当前进度或操作结果。 | |
| N483 | 状态显示<br><code>ui/gui_app.py:1091</code><br>关联：N004, N484, N485, N486, N487, N490（其余见索引） | <code>已停止</code> | 循环尚未启动或后台已退出时，显示当前没有继续运行的循环。 | |
| N484 | 状态显示<br><code>ui/gui_app.py:1092</code><br>关联：N483, N485, N486, N487, N490, N496（其余见索引） | <code>已停止人工等待</code> | 后台退出后显示结束原因与累计结果时，显示当前进度或操作结果。 | |
| N485 | 状态显示<br><code>ui/gui_app.py:1096</code><br>关联：N483, N484, N486, N487, N490, N496（其余见索引） | <code>错误</code> | 后台退出后显示结束原因与累计结果时，显示当前进度或操作结果。 | |
| N486 | 状态显示<br><code>ui/gui_app.py:1097</code><br>关联：N483, N484, N485, N487, N490, N496（其余见索引） | <code>自动循环异常停止</code> | 后台退出后显示结束原因与累计结果时，显示当前进度或操作结果。 | |
| N487 | 状态显示<br><code>ui/gui_app.py:1103</code><br>关联：N483, N484, N485, N486, N490, N496（其余见索引） | <code>f"发数：{summary.rounds} &#124; HIT：{summary.hits} &#124; MISS：{summary.misses}"</code> | 后台退出后显示结束原因与累计结果时，显示当前进度或操作结果。<br>注意：统计栏文字用于提取发数、HIT 和 MISS；标点与分隔符变化需同步核对解析。 | |
| N488 | 状态显示<br><code>ui/gui_app.py:1170</code><br>关联：N491 | <code>正在恢复网络并退出...</code> | 关闭主窗口并等待后台退出、清理网络时，显示当前进度或操作结果。 | |
| N489 | GUI 日志<br><code>ui/gui_app.py:949</code><br>关联：N481, N482 | <code>已请求停止自动循环：后台将在最近可中断点退出并保留当前现场。</code> | 请求后台在安全动作边界停止时，把这一步的操作及结果写入主窗口日志。 | |
| N490 | GUI 日志<br><code>ui/gui_app.py:1126</code><br>关联：N483, N484, N485, N486, N487, N496（其余见索引） | <code>"自动循环结束："<br>            f"rounds={summary.rounds}，HIT={summary.hits}，MISS={summary.misses}，"<br>            f"reason={summary.stop_reason}；{network_text}"</code> | 后台退出后显示结束原因与累计结果时，把这一步的操作及结果写入主窗口日志。 | |
| N491 | GUI 日志<br><code>ui/gui_app.py:1173</code><br>关联：N488 | <code>窗口关闭：等待自动线程退出后清理网络规则...</code> | 关闭主窗口并等待后台退出、清理网络时，把这一步的操作及结果写入主窗口日志。 | |
| N492 | 日志<br><code>flows/auto_probe_loop.py:280</code><br>关联：N493, N494 | <code>自动探测已在最近可中断点响应用户停止</code> | 连续执行当前关卡的探测并累计结果时，记录这一步的参数、结果或异常。 | |
| N493 | 日志<br><code>flows/auto_probe_loop.py:287</code><br>关联：N492, N494 | <code>自动探测连续循环已安全停止</code> | 连续执行当前关卡的探测并累计结果时，记录这一步的参数、结果或异常。 | |
| N494 | 日志<br><code>flows/auto_probe_loop.py:337</code><br>关联：N492, N493 | <code>连续自动探测循环结束：rounds=%s，hits=%s，misses=%s，reason=%s，strategy_done=%s</code> | 连续执行当前关卡的探测并累计结果时，记录这一步的参数、结果或异常。 | |
| N495 | 日志<br><code>ui/auto_loop_bridge.py:157</code> | <code>自动循环异常退出后的网络清理失败</code> | 后台执行原循环并向主线程投递消息时，记录这一步的参数、结果或异常。 | |
| N496 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1107</code><br>关联：N483, N484, N485, N486, N487, N490（其余见索引） | <code>异常恢复失败，已安全停止</code> | 后台退出后显示结束原因与累计结果时，组成界面提示或该步骤的诊断信息。 | |
| N497 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1109</code><br>关联：N004, N483, N484, N485, N486, N487（其余见索引） | <code>已停止</code> | 循环尚未启动或后台已退出时，显示当前没有继续运行的循环。 | |
| N498 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1111</code><br>关联：N483, N484, N485, N486, N487, N490（其余见索引） | <code>f"已完成 {summary.completed_levels} 关"</code> | 后台退出后显示结束原因与累计结果时，组成界面提示或该步骤的诊断信息。 | |
| N499 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1113</code><br>关联：N483, N484, N485, N486, N487, N490（其余见索引） | <code>当前关卡策略完成</code> | 后台退出后显示结束原因与累计结果时，组成界面提示或该步骤的诊断信息。 | |
| N500 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1115</code><br>关联：N483, N484, N485, N486, N487, N490（其余见索引） | <code>f"已停止：{summary.stop_reason}"</code> | 后台退出后显示结束原因与累计结果时，组成界面提示或该步骤的诊断信息。 | |
| N501 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1121</code><br>关联：N483, N484, N485, N486, N487, N490（其余见索引） | <code>已保留安全断点处的页面和网络状态。</code> | 后台退出后显示结束原因与累计结果时，组成界面提示或该步骤的诊断信息。 | |
| N502 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1123</code><br>关联：N483, N484, N485, N486, N487, N490（其余见索引） | <code>游戏网络已按安全退出流程处理。</code> | 后台退出后显示结束原因与累计结果时，组成界面提示或该步骤的诊断信息。 | |
| N503 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1181</code><br>关联：N504 | <code>"退出清理失败："<br>                    f"{exc}"</code> | 关闭主窗口并等待后台退出、清理网络时，组成界面提示或该步骤的诊断信息。<br>注意：退出清理失败前缀被 startswith 判断使用。 | |
| N504 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:1185</code><br>关联：N503 | <code>退出清理完成</code> | 关闭主窗口并等待后台退出、清理网络时，组成界面提示或该步骤的诊断信息。 | |
| N505 | 校验或错误提示<br><code>stop_control.py:19</code><br>关联：N508 | <code>用户已请求停止自动探测</code> | 在动作边界或分段等待中响应停止时，在输入或执行结果不符合条件时给出原因。 | |
| N506 | 校验或错误提示<br><code>stop_control.py:35</code><br>关联：N224, N507, N508, N947 | <code>等待时间不能小于 0</code> | 在动作边界或分段等待中响应停止时，在输入或执行结果不符合条件时给出原因。 | |
| N507 | 校验或错误提示<br><code>stop_control.py:40</code><br>关联：N506, N508 | <code>停止检查间隔必须大于 0</code> | 在动作边界或分段等待中响应停止时，在输入或执行结果不符合条件时给出原因。 | |
| N508 | 校验或错误提示<br><code>stop_control.py:69</code><br>关联：N505, N506, N507 | <code>用户已请求停止自动探测</code> | 在动作边界或分段等待中响应停止时，在输入或执行结果不符合条件时给出原因。 | |

### 13 底层校验与故障诊断（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N509 | 显示组成文字／诊断消息<br><code>sonar/checkerboard_strategy.py:542</code><br>关联：N510, N511, N512 | <code>视觉方向必须是 H 或 V</code> | 选择下一格、追击命中并校验潜艇是否确认时，组成界面提示或该步骤的诊断信息。 | |
| N510 | 显示组成文字／诊断消息<br><code>sonar/checkerboard_strategy.py:578</code><br>关联：N509, N511, N512 | <code>"连续 HIT 段没有匹配剩余潜艇的合法解释；"<br>                f"连续长度={candidate_length}，"<br>                f"剩余={self.remaining_submarines}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，组成界面提示或该步骤的诊断信息。 | |
| N511 | 显示组成文字／诊断消息<br><code>sonar/checkerboard_strategy.py:596</code><br>关联：N509, N510, N512 | <code>"连续 HIT 段存在多个合法潜艇解释；"<br>                f"候选={unique_candidates}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，组成界面提示或该步骤的诊断信息。 | |
| N512 | 显示组成文字／诊断消息<br><code>sonar/checkerboard_strategy.py:623</code><br>关联：N509, N510, N511 | <code>唯一连续 HIT 段通过剩余潜艇与冲突校验</code> | 选择下一格、追击命中并校验潜艇是否确认时，组成界面提示或该步骤的诊断信息。 | |
| N513 | 校验或错误提示<br><code>sonar/board.py:62</code><br>关联：N514, N515, N516 | <code>棋盘尺寸 grid_size 必须大于 0</code> | 检查或写入棋盘格子与坐标映射时，在输入或执行结果不符合条件时给出原因。 | |
| N514 | 校验或错误提示<br><code>sonar/board.py:67</code><br>关联：N513, N515, N516 | <code>潜艇配置不能为空</code> | 检查或写入棋盘格子与坐标映射时，在输入或执行结果不符合条件时给出原因。 | |
| N515 | 校验或错误提示<br><code>sonar/board.py:70</code><br>关联：N513, N514, N516 | <code>潜艇长度必须大于 0</code> | 检查或写入棋盘格子与坐标映射时，在输入或执行结果不符合条件时给出原因。 | |
| N516 | 校验或错误提示<br><code>sonar/board.py:73</code><br>关联：N513, N514, N515 | <code>潜艇长度不能大于棋盘尺寸</code> | 检查或写入棋盘格子与坐标映射时，在输入或执行结果不符合条件时给出原因。 | |
| N517 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:46</code> | <code>hunt_parity 只能是 0 或 1</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N518 | 校验或错误提示<br><code>sonar/board.py:102</code> | <code>f"格子超出棋盘范围：row={row}, col={col}, grid_size={self.grid_size}"</code> | 检查或写入棋盘格子与坐标映射时，在输入或执行结果不符合条件时给出原因。 | |
| N519 | 校验或错误提示<br><code>sonar/board.py:245</code> | <code>"整盘状态尺寸错误："<br>                f"需要 {self.grid_size}×{self.grid_size}"</code> | 检查或写入棋盘格子与坐标映射时，在输入或执行结果不符合条件时给出原因。 | |
| N520 | 校验或错误提示<br><code>sonar/board.py:280</code> | <code>f"格点数量错误：需要 {expected} 个，实际 {len(point_list)} 个"</code> | 检查或写入棋盘格子与坐标映射时，在输入或执行结果不符合条件时给出原因。 | |
| N521 | 校验或错误提示<br><code>sonar/board.py:306</code> | <code>quad 必须包含 4 个外角坐标</code> | 检查或写入棋盘格子与坐标映射时，在输入或执行结果不符合条件时给出原因。 | |
| N522 | 校验或错误提示<br><code>sonar/board.py:380</code> | <code>f"格子 ({row}, {col}) 还没有绑定模拟器坐标"</code> | 检查或写入棋盘格子与坐标映射时，在输入或执行结果不符合条件时给出原因。 | |
| N523 | 校验或错误提示<br><code>sonar/board.py:412</code> | <code>f"格子编号超出范围：index={index}"</code> | 检查或写入棋盘格子与坐标映射时，在输入或执行结果不符合条件时给出原因。 | |
| N524 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:241</code><br>关联：N525 | <code>"返回结果的格子和当前等待结果的格子不一致："<br>                f"pending={self._pending_cell}, result={cell}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N525 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:259</code><br>关联：N524 | <code>f"格子 {cell} 已经有确定结果：{current_state.value}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N526 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:334</code><br>关联：N527, N528, N529, N530, N531, N532（其余见索引） | <code>f"第 {index} 艘潜艇格为空或存在重复"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N527 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:349</code><br>关联：N526, N528, N529, N530, N531, N532（其余见索引） | <code>f"第 {index} 艘潜艇只能横向或纵向"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N528 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:352</code><br>关联：N526, N527, N529, N530, N531, N532（其余见索引） | <code>f"第 {index} 艘潜艇格不连续"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N529 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:356</code><br>关联：N467, N526, N527, N528, N530, N531（其余见索引） | <code>f"长度 {length} 不属于当前潜艇配置"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N530 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:359</code><br>关联：N468, N526, N527, N528, N529, N531（其余见索引） | <code>f"长度 {length} 的潜艇数量超过关卡配置"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N531 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:363</code><br>关联：N469, N526, N527, N528, N529, N530（其余见索引） | <code>f"已确认潜艇发生重叠：{sorted(overlap)}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N532 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:368</code><br>关联：N526, N527, N528, N529, N530, N531（其余见索引） | <code>f"已确认潜艇内部包含 MISS：{(row, col)}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N533 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:371</code><br>关联：N526, N527, N528, N529, N530, N531（其余见索引） | <code>f"已确认潜艇与棋盘状态冲突：{(row, col)}={state.value}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N534 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:394</code><br>关联：N526, N527, N528, N529, N530, N531（其余见索引） | <code>"SUNK 格与已确认潜艇记录不一致："<br>                f"未归属={uncovered}，缺少SUNK={missing}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N535 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:404</code><br>关联：N526, N527, N528, N529, N530, N531（其余见索引） | <code>f"第 {index} 艘潜艇与其他已确认潜艇违反安全间距："<br>                        f"{sorted(conflicting_ships)}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N536 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:414</code><br>关联：N526, N527, N528, N529, N530, N531（其余见索引） | <code>f"第 {index} 艘潜艇安全区域存在 HIT："<br>                        f"{sorted(conflicting_hits)}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N537 | 校验或错误提示<br><code>sonar/checkerboard_strategy.py:960</code><br>关联：N478 | <code>f"格子超出棋盘范围：{cell}"</code> | 选择下一格、追击命中并校验潜艇是否确认时，在输入或执行结果不符合条件时给出原因。 | |
| N538 | 校验或错误提示<br><code>vision/image_match.py:44</code><br>关联：N539 | <code>f"图片不存在：{image_path}"</code> | 读取模板并计算图像匹配结果时，在输入或执行结果不符合条件时给出原因。 | |
| N539 | 校验或错误提示<br><code>vision/image_match.py:59</code><br>关联：N538 | <code>f"图片解码失败：{image_path}"</code> | 读取模板并计算图像匹配结果时，在输入或执行结果不符合条件时给出原因。 | |
| N540 | 校验或错误提示<br><code>vision/image_match.py:82</code><br>关联：N541, N542, N543 | <code>screenshot 必须是有效的 OpenCV 图片</code> | 读取模板并计算图像匹配结果时，在输入或执行结果不符合条件时给出原因。 | |
| N541 | 校验或错误提示<br><code>vision/image_match.py:95</code><br>关联：N540, N542, N543 | <code>template 必须是有效的 OpenCV 图片</code> | 读取模板并计算图像匹配结果时，在输入或执行结果不符合条件时给出原因。 | |
| N542 | 校验或错误提示<br><code>vision/image_match.py:100</code><br>关联：N540, N541, N543 | <code>threshold 必须位于 0 到 1 之间</code> | 读取模板并计算图像匹配结果时，在输入或执行结果不符合条件时给出原因。 | |
| N543 | 校验或错误提示<br><code>vision/image_match.py:116</code><br>关联：N540, N541, N542 | <code>模板尺寸不能大于截图尺寸</code> | 读取模板并计算图像匹配结果时，在输入或执行结果不符合条件时给出原因。 | |

## 附录：独立入口、离线工具与预留显示

以下代码当前存在，入口和使用方式独立于原主窗口；不代表自动循环已经启用这些功能。仍使用同一组 N 编号，方便按需填写。

### A01 独立命令行入口与启动检查（整理用标题）

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N544 | 命令行帮助<br><code>main.py:33</code><br>关联：N545 | <code>BoomBeachSonarRobot</code> | 用户通过独立命令行选择并执行相应工具时，说明该工具的用途或参数。 | |
| N545 | 命令行帮助<br><code>main.py:54</code><br>关联：N544 | <code>默认执行 screenshot</code> | 用户通过独立命令行选择并执行相应工具时，说明该工具的用途或参数。 | |
| N546 | 终端输出<br><code>main.py:79</code><br>关联：N547, N548, N549, N550, N551, N562 | <code>f"游戏 UID：{uid}"</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N547 | 终端输出<br><code>main.py:88</code><br>关联：N127, N546, N548, N549, N550, N551（其余见索引） | <code>弱网 DROP 已开启</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N548 | 终端输出<br><code>main.py:97</code><br>关联：N128, N546, N547, N549, N550, N551（其余见索引） | <code>弱网 DROP 已关闭</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N549 | 终端输出<br><code>main.py:106</code><br>关联：N129, N546, N547, N548, N550, N551（其余见索引） | <code>断网 REJECT 已开启</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N550 | 终端输出<br><code>main.py:115</code><br>关联：N130, N546, N547, N548, N549, N551（其余见索引） | <code>断网 REJECT 已关闭</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N551 | 终端输出<br><code>main.py:133</code><br>关联：N131, N546, N547, N548, N549, N550（其余见索引） | <code>游戏网络已恢复</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N552 | 终端输出<br><code>main.py:166</code><br>关联：N553, N554, N555, N556, N557, N558（其余见索引） | <code>f"ADB 路径：{adb.adb_path}"</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N553 | 终端输出<br><code>main.py:170</code><br>关联：N552, N554, N555, N556, N557, N558（其余见索引） | <code>f"在线设备：{devices}"</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N554 | 终端输出<br><code>main.py:197</code><br>关联：N552, N553, N555, N556, N557, N558（其余见索引） | <code>游戏重启完成</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N555 | 终端输出<br><code>main.py:207</code><br>关联：N552, N553, N554, N556, N557, N558（其余见索引） | <code>截图检查完成</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N556 | 终端输出<br><code>main.py:211</code><br>关联：N552, N553, N554, N555, N557, N558（其余见索引） | <code>f"设备：{result.serial}"</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N557 | 终端输出<br><code>main.py:215</code><br>关联：N552, N553, N554, N555, N556, N558（其余见索引） | <code>f"尺寸：{result.width}x{result.height}"</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N558 | 终端输出<br><code>main.py:219</code><br>关联：N552, N553, N554, N555, N556, N557（其余见索引） | <code>f"文件：{result.path}"</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N559 | 终端输出<br><code>main.py:226</code><br>关联：N552, N553, N554, N555, N556, N557（其余见索引） | <code>f"执行失败：{exc}"</code> | 用户通过独立命令行选择并执行相应工具时，在终端展示该工具的菜单或结果。 | |
| N560 | 启动终端提示<br><code>启动程序.bat:19</code><br>关联：N561 | <code>Launcher check failed.</code> | 启动检查或环境失败时在启动终端显示相应信息。 | |
| N561 | 启动终端提示<br><code>启动程序.bat:22</code><br>关联：N560 | <code>Launcher check passed.</code> | 启动检查或环境失败时在启动终端显示相应信息。 | |
| N562 | 校验或错误提示<br><code>main.py:139</code><br>关联：N546, N547, N548, N549, N550, N551 | <code>f"未知网络操作：{action}"</code> | 用户通过独立命令行选择并执行相应工具时，在输入或执行结果不符合条件时给出原因。 | |

### A02 独立设备联调脚本（整理用标题）

这些脚本可真实操作设备，当前没有通过主 GUI 调用；本轮仅阅读，没有执行。

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N563 | 显示组成文字／诊断消息<br><code>tests/manual_activity_entry_test.py:34</code><br>关联：N288, N564, N565, N566 | <code>活动棋盘页面</code> | 人工确认当前位于可继续声纳活动操作的活动棋盘页面。 | |
| N564 | 显示组成文字／诊断消息<br><code>tests/manual_activity_entry_test.py:37</code><br>关联：N563, N565, N566 | <code>主岛，声纳已可见</code> | 从真实主岛进入活动的独立联调时，组成界面提示或该步骤的诊断信息。 | |
| N565 | 显示组成文字／诊断消息<br><code>tests/manual_activity_entry_test.py:40</code><br>关联：N290, N563, N564, N566 | <code>主岛</code> | 人工确认当前是主岛，尚未确认声纳可见。 | |
| N566 | 显示组成文字／诊断消息<br><code>tests/manual_activity_entry_test.py:43</code><br>关联：N563, N564, N565 | <code>未知页面</code> | 从真实主岛进入活动的独立联调时，组成界面提示或该步骤的诊断信息。 | |
| N567 | 终端输出<br><code>tests/manual_activity_entry_test.py:50</code><br>关联：N568, N569, N570, N571, N572, N573（其余见索引） | <code>初始进入声纳活动 + 页面状态检验</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N568 | 终端输出<br><code>tests/manual_activity_entry_test.py:54</code><br>关联：N567, N569, N570, N571, N572, N573（其余见索引） | <code>建议测试起点：游戏已经打开并停在主岛，网络正常。</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N569 | 终端输出<br><code>tests/manual_activity_entry_test.py:58</code><br>关联：N567, N568, N570, N571, N572, N573（其余见索引） | <code>程序会自己检查主岛、寻找声纳、开启弱网并进入活动棋盘页面。</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N570 | 终端输出<br><code>tests/manual_activity_entry_test.py:63</code><br>关联：N567, N568, N569, N571, N572, N573（其余见索引） | <code>测试结束后弱网会保持开启，这就是后续开始探测时需要的状态。</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N571 | 终端输出<br><code>tests/manual_activity_entry_test.py:67</code><br>关联：N567, N568, N569, N570, N572, N573（其余见索引） | <code>如果测试后不继续探测，可用 GUI 的“恢复网络”或运行：</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N572 | 终端输出<br><code>tests/manual_activity_entry_test.py:71</code><br>关联：N567, N568, N569, N570, N571, N573（其余见索引） | <code>python main.py network-reset</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N573 | 终端输入提示<br><code>tests/manual_activity_entry_test.py:76</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>准备好后按 Enter 开始，输入 q 退出：</code> | 从真实主岛进入活动的独立联调时，要求终端用户输入选择。 | |
| N574 | 终端输出<br><code>tests/manual_activity_entry_test.py:102</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"进入流程前页面状态："<br>        f"{PAGE_STATE_TEXT[initial_state]}"<br>        f" ({initial_state.value})"</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N575 | 终端输出<br><code>tests/manual_activity_entry_test.py:125</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>初始进入流程完成</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N576 | 终端输出<br><code>tests/manual_activity_entry_test.py:128</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"起始页面："<br>        f"{PAGE_STATE_TEXT[result.initial_state]}"</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N577 | 终端输出<br><code>tests/manual_activity_entry_test.py:132</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"最终页面："<br>        f"{PAGE_STATE_TEXT[final_state]}"</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N578 | 终端输出<br><code>tests/manual_activity_entry_test.py:136</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"检测到的声纳中心：{result.sonar_point}"</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N579 | 终端输出<br><code>tests/manual_activity_entry_test.py:139</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"弱网状态："<br>        f"{'开启' if network_state.weak_enabled else '关闭'}"</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N580 | 终端输出<br><code>tests/manual_activity_entry_test.py:143</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"REJECT 状态："<br>        f"{'开启' if network_state.reject_enabled else '关闭'}"</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N581 | 终端输出<br><code>tests/manual_activity_entry_test.py:168</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>测试通过：当前已经位于声纳活动棋盘页面，并保持弱网 DROP。</code> | 从真实主岛进入活动的独立联调时，在终端展示该工具的菜单或结果。 | |
| N582 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:41</code><br>关联：N583, N584, N585, N586, N587, N588（其余见索引） | <code>识别指标：</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N583 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:42</code><br>关联：N582, N584, N585, N586, N587, N588（其余见索引） | <code>f"  state={recognition.state}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N584 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:43</code><br>关联：N582, N583, N585, N586, N587, N588（其余见索引） | <code>f"  confidence={recognition.confidence:.3f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N585 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:44</code><br>关联：N582, N583, N584, N586, N587, N588（其余见索引） | <code>f"  score={recognition.score:.3f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N586 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:45</code><br>关联：N582, N583, N584, N585, N587, N588（其余见索引） | <code>f"  changed_ratio={recognition.changed_ratio:.3f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N587 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:46</code><br>关联：N582, N583, N584, N585, N586, N588（其余见索引） | <code>f"  center_gray_ratio={recognition.center_gray_ratio:.3f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N588 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:47</code><br>关联：N582, N583, N584, N585, N586, N587（其余见索引） | <code>f"  ring_gray_ratio={recognition.ring_gray_ratio:.3f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N589 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:48</code><br>关联：N582, N583, N584, N585, N586, N587（其余见索引） | <code>f"  gray_excess={recognition.gray_excess:.3f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N590 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:49</code><br>关联：N582, N583, N584, N585, N586, N587（其余见索引） | <code>f"  component_ratio={recognition.component_ratio:.3f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N591 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:50</code><br>关联：N582, N583, N584, N585, N586, N587（其余见索引） | <code>f"  s_center={recognition.s_center:.1f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N592 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:51</code><br>关联：N582, N583, N584, N585, N586, N587（其余见索引） | <code>f"  s_ring={recognition.s_ring:.1f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N593 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:52</code><br>关联：N582, N583, N584, N585, N586, N587（其余见索引） | <code>f"  s_drop={recognition.s_drop:.1f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N594 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:53</code><br>关联：N582, N583, N584, N585, N586, N587（其余见索引） | <code>f"  edge_density={recognition.edge_density:.3f}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N595 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:62</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>完整自动一发闭环测试</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N596 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:64</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>本测试会真实执行：</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N597 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:66</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>页面准备 -&gt; 弱网 -&gt; 策略选格 -&gt; 点击 -&gt; 退出/重进 -&gt; 自动 HIT/MISS -&gt; 策略写回 -&gt; 分支恢复 -&gt; 下一发准备</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N598 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:70</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>结束成功时应满足：</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N599 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:71</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>1. 页面重新停在声纳活动棋盘页面。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N600 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:72</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>2. 弱网 DROP 已重新开启。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N601 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:73</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>3. REJECT 已关闭。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N602 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:74</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>4. 策略已经给出下一格，或本轮策略已经完成。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N603 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:76</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>识别规则：只有 state=hit/miss 才写入策略。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N604 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:77</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>unknown/unopened 不写入策略；连续循环会重启并重试同一格。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N605 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:78</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>本脚本只执行单发，遇到这两种状态会报告失败。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N606 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:79</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>HIT：直接联网 5 秒后重新开启弱网；MISS：继续 REJECT/retry。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N607 | 终端输入提示<br><code>tests/manual_auto_probe_cycle_test.py:83</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>准备好后按 Enter 开始，输入 q 退出：</code> | 自动单发及 HIT／MISS 恢复的独立联调时，要求终端用户输入选择。 | |
| N608 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:127</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"测试失败：{exc}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N609 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:132</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>失败后的当前网络状态：</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N610 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:136</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"读取网络状态也失败：{state_exc}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N611 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:141</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>异常路径不会主动释放仍存在的弱网 DROP；确认游戏画面后，可执行：python main.py network-reset</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N612 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:147</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>================ 测试结果 ================</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N613 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:148</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"本发逻辑格：{result.context.cell}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N614 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:149</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"模拟器坐标：{result.context.screen_point}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N615 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:150</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"before：{result.context.before_path}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N616 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:151</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"after：{result.context.after_path}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N617 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:158</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"正式写回结果："<br>        f"{'HIT' if result.hit else 'MISS'}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N618 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:165</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"新确认潜艇："<br>                f"长度={ship.length}，"<br>                f"方向={ship.direction}，"<br>                f"格子={ship.cells}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N619 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:171</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>本发没有新确认完整潜艇。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N620 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:174</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>恢复链：</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N621 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:176</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"  mode={result.recovery.mode}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N622 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:179</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"  retry_found={result.recovery.retry_found}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N623 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:182</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"  final_page={result.recovery.final_state.value}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N624 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:185</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"  weak={result.recovery.weak_network_enabled}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N625 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:188</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"  reject={result.recovery.reject_network_enabled}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N626 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:192</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"策略下一格：{result.next_cell}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N627 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:193</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"策略完成：{strategy.done}"</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N628 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:194</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>==========================================</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N629 | 终端输入提示<br><code>tests/manual_auto_probe_cycle_test.py:198</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>按 Enter 恢复正常网络并退出；输入 k 保持当前弱网、停在下一发准备状态：</code> | 自动单发及 HIT／MISS 恢复的独立联调时，要求终端用户输入选择。 | |
| N630 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:203</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>保持当前下一发准备状态。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N631 | 终端输出<br><code>tests/manual_auto_probe_cycle_test.py:207</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>游戏网络已经恢复正常。</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在终端展示该工具的菜单或结果。 | |
| N632 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:42</code><br>关联：N582, N633, N634, N635, N636, N637（其余见索引） | <code>识别指标：</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N633 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:43</code><br>关联：N632, N634, N635, N636, N637, N638（其余见索引） | <code>f"  state={result.state}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N634 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:44</code><br>关联：N632, N633, N635, N636, N637, N638（其余见索引） | <code>f"  confidence={result.confidence:.3f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N635 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:45</code><br>关联：N632, N633, N634, N636, N637, N638（其余见索引） | <code>f"  score={result.score:.3f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N636 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:46</code><br>关联：N632, N633, N634, N635, N637, N638（其余见索引） | <code>f"  rough_center={result.rough_center}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N637 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:47</code><br>关联：N632, N633, N634, N635, N636, N638（其余见索引） | <code>f"  refined_center={result.refined_center}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N638 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:48</code><br>关联：N632, N633, N634, N635, N636, N637（其余见索引） | <code>f"  changed_ratio={result.changed_ratio:.3f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N639 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:49</code><br>关联：N632, N633, N634, N635, N636, N637（其余见索引） | <code>f"  center_gray_ratio={result.center_gray_ratio:.3f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N640 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:50</code><br>关联：N632, N633, N634, N635, N636, N637（其余见索引） | <code>f"  ring_gray_ratio={result.ring_gray_ratio:.3f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N641 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:51</code><br>关联：N632, N633, N634, N635, N636, N637（其余见索引） | <code>f"  gray_excess={result.gray_excess:.3f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N642 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:52</code><br>关联：N632, N633, N634, N635, N636, N637（其余见索引） | <code>f"  component_ratio={result.component_ratio:.3f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N643 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:53</code><br>关联：N632, N633, N634, N635, N636, N637（其余见索引） | <code>f"  s_center={result.s_center:.1f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N644 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:54</code><br>关联：N632, N633, N634, N635, N636, N637（其余见索引） | <code>f"  s_ring={result.s_ring:.1f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N645 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:55</code><br>关联：N632, N633, N634, N635, N636, N637（其余见索引） | <code>f"  s_drop={result.s_drop:.1f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N646 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:56</code><br>关联：N632, N633, N634, N635, N636, N637（其余见索引） | <code>f"  edge_density={result.edge_density:.3f}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N647 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:65</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>单发真实探测自动 HIT/MISS 联调</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N648 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:67</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>流程：策略选格 -&gt; 点击前截图 -&gt; 点击目标格 -&gt; 退出活动 -&gt; 重进活动 -&gt; 点击后截图 -&gt; 自动识别 -&gt; HIT/MISS 写回策略</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N649 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:72</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>运行前要求：</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N650 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:73</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>1. 模拟器已经进入声纳活动棋盘页面，棋盘可见。</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N651 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:74</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>2. 如需按当前保护流程测试，请先开启弱网 DROP。</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N652 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:75</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>3. 本测试只执行一发，不处理 REJECT / retry。</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N653 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:76</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>4. unknown / unopened 不写回策略，pending_cell 会保留。</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N654 | 终端输入提示<br><code>tests/manual_auto_single_probe_test.py:80</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>准备好后按 Enter 开始，输入 q 退出：</code> | 单发截图自动识别的独立联调时，要求终端用户输入选择。 | |
| N655 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:143</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"本次逻辑格：{context.cell}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N656 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:144</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"模拟器坐标：{context.screen_point}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N657 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:145</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"点击前截图：{context.before_path}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N658 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:146</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"重进后截图：{context.after_path}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N659 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:147</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"调试图片目录：{debug_dir}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N660 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:160</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"自动结果已写回策略："<br>            f"{probe_result.context.cell} -&gt; HIT"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N661 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:171</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"自动结果已写回策略："<br>            f"{probe_result.context.cell} -&gt; MISS"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N662 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:177</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>自动识别结果暂时无法安全提交。</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N663 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:180</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"当前状态：{recognition.state}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N664 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:183</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>策略 pending_cell 保留，方便检查调试图后重试同一格。</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N665 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:191</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"新确认潜艇："<br>                f"长度={ship.length}，"<br>                f"方向={ship.direction}，"<br>                f"格子={ship.cells}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N666 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:199</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"策略给出的下一格：{next_cell}"</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N667 | 终端输出<br><code>tests/manual_auto_single_probe_test.py:202</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>本次只验证一发，不继续实际点击。</code> | 单发截图自动识别的独立联调时，在终端展示该工具的菜单或结果。 | |
| N668 | 终端输出<br><code>tests/manual_board_click_test.py:52</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>棋盘坐标映射完成</code> | 按预设棋盘坐标点击设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N669 | 终端输出<br><code>tests/manual_board_click_test.py:65</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"{index}. "<br>            f"逻辑格 ({row}, {col}) "<br>            f"→ 模拟器 ({x}, {y})"</code> | 按预设棋盘坐标点击设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N670 | 终端输出<br><code>tests/manual_board_click_test.py:71</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>q. 退出</code> | 按预设棋盘坐标点击设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N671 | 终端输入提示<br><code>tests/manual_board_click_test.py:75</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code><br>输入要测试的编号：</code> | 按预设棋盘坐标点击设备的独立联调时，要求终端用户输入选择。 | |
| N672 | 终端输出<br><code>tests/manual_board_click_test.py:89</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>输入无效</code> | 按预设棋盘坐标点击设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N673 | 终端输入提示<br><code>tests/manual_board_click_test.py:98</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"准备点击逻辑格 ({row}, {col}) "<br>            f"→ ({x}, {y})，输入 y 确认："</code> | 按预设棋盘坐标点击设备的独立联调时，要求终端用户输入选择。 | |
| N674 | 终端输出<br><code>tests/manual_board_click_test.py:103</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>已取消</code> | 按预设棋盘坐标点击设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N675 | 终端输出<br><code>tests/manual_board_click_test.py:112</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"已点击 ({row}, {col}) "<br>            f"→ ({x}, {y})"</code> | 按预设棋盘坐标点击设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N676 | 终端输出<br><code>tests/manual_network_test.py:37</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>w：开启弱网</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N677 | 终端输出<br><code>tests/manual_network_test.py:38</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>s：关闭弱网</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N678 | 终端输出<br><code>tests/manual_network_test.py:39</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>r：开启断网</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N679 | 终端输出<br><code>tests/manual_network_test.py:40</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f：关闭断网</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N680 | 终端输出<br><code>tests/manual_network_test.py:41</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>c：查看状态</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N681 | 终端输出<br><code>tests/manual_network_test.py:42</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>q：恢复网络并退出</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N682 | 终端输入提示<br><code>tests/manual_network_test.py:47</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>&gt; </code> | 交互切换设备网络规则的独立联调时，要求终端用户输入选择。 | |
| N683 | 终端输出<br><code>tests/manual_network_test.py:56</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>弱网已开启</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N684 | 终端输出<br><code>tests/manual_network_test.py:63</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>弱网已关闭</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N685 | 终端输出<br><code>tests/manual_network_test.py:70</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>断网已开启</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N686 | 终端输出<br><code>tests/manual_network_test.py:77</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>断网已关闭</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N687 | 终端输出<br><code>tests/manual_network_test.py:94</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>未知命令</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N688 | 终端输出<br><code>tests/manual_network_test.py:101</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>网络已恢复</code> | 交互切换设备网络规则的独立联调时，在终端展示该工具的菜单或结果。 | |
| N689 | 终端输出<br><code>tests/manual_page_control_test.py:38</code><br>关联：N690 | <code>f"需要输入 {count} 个数字"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N690 | 终端输出<br><code>tests/manual_page_control_test.py:47</code><br>关联：N689 | <code>坐标必须是整数</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N691 | 终端输入提示<br><code>tests/manual_page_control_test.py:54</code> | <code>模板路径或文件名：</code> | 交互检查页面和模板的独立联调时，要求终端用户输入选择。 | |
| N692 | 终端输出<br><code>tests/manual_page_control_test.py:66</code><br>关联：N693, N694, N695, N696, N697 | <code>没有找到模板</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N693 | 终端输出<br><code>tests/manual_page_control_test.py:69</code><br>关联：N692, N694, N695, N696, N697 | <code>找到模板</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N694 | 终端输出<br><code>tests/manual_page_control_test.py:70</code><br>关联：N692, N693, N695, N696, N697, N714 | <code>f"相似度：{match.score:.3f}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N695 | 终端输出<br><code>tests/manual_page_control_test.py:71</code><br>关联：N692, N693, N694, N696, N697 | <code>f"中心坐标：{match.center}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N696 | 终端输出<br><code>tests/manual_page_control_test.py:72</code><br>关联：N692, N693, N694, N695, N697 | <code>f"左上角：{match.top_left}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N697 | 终端输出<br><code>tests/manual_page_control_test.py:73</code><br>关联：N692, N693, N694, N695, N696 | <code>f"右下角：{match.bottom_right}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N698 | 终端输出<br><code>tests/manual_page_control_test.py:84</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"设备：{adb.serial}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N699 | 终端输出<br><code>tests/manual_page_control_test.py:85</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"截图尺寸：{width}x{height}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N700 | 终端输出<br><code>tests/manual_page_control_test.py:88</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>p：固定坐标点击</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N701 | 终端输出<br><code>tests/manual_page_control_test.py:89</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>s：坐标滑动</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N702 | 终端输出<br><code>tests/manual_page_control_test.py:90</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f：查找模板</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N703 | 终端输出<br><code>tests/manual_page_control_test.py:91</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>c：查找模板并点击</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N704 | 终端输出<br><code>tests/manual_page_control_test.py:92</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>w：等待模板出现并点击</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N705 | 终端输出<br><code>tests/manual_page_control_test.py:93</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>q：退出</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N706 | 终端输入提示<br><code>tests/manual_page_control_test.py:98</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>&gt; </code> | 交互检查页面和模板的独立联调时，要求终端用户输入选择。 | |
| N707 | 显示组成文字／诊断消息<br><code>tests/manual_page_control_test.py:103</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>输入 x y：</code> | 交互检查页面和模板的独立联调时，组成界面提示或该步骤的诊断信息。 | |
| N708 | 终端输出<br><code>tests/manual_page_control_test.py:116</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"已点击：{tuple(point)}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N709 | 显示组成文字／诊断消息<br><code>tests/manual_page_control_test.py:122</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>输入 start_x start_y end_x end_y：</code> | 交互检查页面和模板的独立联调时，组成界面提示或该步骤的诊断信息。 | |
| N710 | 终端输入提示<br><code>tests/manual_page_control_test.py:132</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>滑动时间毫秒，直接回车使用 300：</code> | 交互检查页面和模板的独立联调时，要求终端用户输入选择。 | |
| N711 | 终端输出<br><code>tests/manual_page_control_test.py:149</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>滑动完成</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N712 | 终端输出<br><code>tests/manual_page_control_test.py:175</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>没有找到模板，未点击</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N713 | 终端输出<br><code>tests/manual_page_control_test.py:179</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"已点击模板中心："<br>                        f"{match.center}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N714 | 终端输出<br><code>tests/manual_page_control_test.py:183；tests/manual_page_control_test.py:218</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"相似度：{match.score:.3f}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N715 | 终端输入提示<br><code>tests/manual_page_control_test.py:193</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>等待秒数，直接回车使用默认值：</code> | 交互检查页面和模板的独立联调时，要求终端用户输入选择。 | |
| N716 | 终端输出<br><code>tests/manual_page_control_test.py:210</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>等待超时，未找到模板</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N717 | 终端输出<br><code>tests/manual_page_control_test.py:214</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"模板出现，已点击："<br>                        f"{match.center}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N718 | 终端输出<br><code>tests/manual_page_control_test.py:222</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>页面控制测试结束</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N719 | 终端输出<br><code>tests/manual_page_control_test.py:226</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>未知命令</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N720 | 终端输出<br><code>tests/manual_page_control_test.py:229</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"操作失败：{exc}"</code> | 交互检查页面和模板的独立联调时，在终端展示该工具的菜单或结果。 | |
| N721 | 终端输入提示<br><code>tests/manual_single_probe_test.py:40</code><br>关联：N722 | <code>人工判断结果：h=HIT，m=MISS：</code> | 在终端填 HIT／MISS 的独立单发联调时，要求终端用户输入选择。 | |
| N722 | 终端输出<br><code>tests/manual_single_probe_test.py:50</code><br>关联：N721 | <code>输入无效，请输入 h 或 m</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N723 | 终端输出<br><code>tests/manual_single_probe_test.py:62</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>单发真实探测人工联调</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N724 | 终端输出<br><code>tests/manual_single_probe_test.py:65</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>流程：策略选格 -&gt; 点击前截图 -&gt; 点击目标格 -&gt; 退出活动 -&gt; 重进活动 -&gt; 人工判断 HIT/MISS -&gt; 更新策略</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N725 | 终端输出<br><code>tests/manual_single_probe_test.py:71</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>运行前要求：</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N726 | 终端输出<br><code>tests/manual_single_probe_test.py:74</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>1. 模拟器当前已经进入声纳活动棋盘页面，棋盘可见。</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N727 | 终端输出<br><code>tests/manual_single_probe_test.py:77</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>2. 如果你希望完全按参考项目的探测保护方式测试，请先自行开启弱网 DROP。</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N728 | 终端输出<br><code>tests/manual_single_probe_test.py:81</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>3. 本测试只执行一发，不处理 REJECT / retry。</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N729 | 终端输入提示<br><code>tests/manual_single_probe_test.py:86</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>准备好后按 Enter 开始，输入 q 退出：</code> | 在终端填 HIT／MISS 的独立单发联调时，要求终端用户输入选择。 | |
| N730 | 终端输出<br><code>tests/manual_single_probe_test.py:127</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>实际页面操作已经完成。</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N731 | 终端输出<br><code>tests/manual_single_probe_test.py:130</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"本次逻辑格：{context.cell}"</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N732 | 终端输出<br><code>tests/manual_single_probe_test.py:133</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"模拟器坐标：{context.screen_point}"</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N733 | 终端输出<br><code>tests/manual_single_probe_test.py:136</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"点击前截图：{context.before_path}"</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N734 | 终端输出<br><code>tests/manual_single_probe_test.py:139</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"重进后截图：{context.after_path}"</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N735 | 终端输出<br><code>tests/manual_single_probe_test.py:143</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>现在观察模拟器中的目标格，人工判断这一发是 HIT 还是 MISS。</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N736 | 终端输出<br><code>tests/manual_single_probe_test.py:157</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"结果已经写回策略："<br>        f"{result.context.cell} -&gt; "<br>        f"{'HIT' if result.hit else 'MISS'}"</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N737 | 终端输出<br><code>tests/manual_single_probe_test.py:165</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"新确认潜艇："<br>                f"长度={ship.length}，"<br>                f"方向={ship.direction}，"<br>                f"格子={ship.cells}"</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N738 | 终端输出<br><code>tests/manual_single_probe_test.py:176</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"策略给出的下一格：{next_cell}"</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N739 | 终端输出<br><code>tests/manual_single_probe_test.py:179</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>本次单发测试结束，不会继续实际点击下一格。</code> | 在终端填 HIT／MISS 的独立单发联调时，在终端展示该工具的菜单或结果。 | |
| N740 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:48</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>策略 + 棋盘映射 + ADB 点击人工联调</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N741 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:49</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>流程：策略选格 -&gt; ADB 点击 -&gt; 你人工输入 HIT / MISS -&gt; 策略继续</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N742 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:50</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>输入 q 可以随时退出。</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N743 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:59</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>策略没有找到可继续探测的格子</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N744 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:69</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"下一格：逻辑 ({row}, {col}) "<br>            f"-&gt; 模拟器 ({x}, {y})"</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N745 | 终端输入提示<br><code>tests/manual_strategy_board_click_test.py:74</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>按 Enter 实际点击；输入 q 退出：</code> | 用策略选格并点击真实设备的独立联调时，要求终端用户输入选择。 | |
| N746 | 终端输入提示<br><code>tests/manual_strategy_board_click_test.py:89</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>输入结果 h=命中，m=未命中，q=退出：</code> | 用策略选格并点击真实设备的独立联调时，要求终端用户输入选择。 | |
| N747 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:93</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>已退出；当前格仍在等待结果</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N748 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:97</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>输入无效</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N749 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:108</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>f"记录：{cell} -&gt; "<br>                f"{'HIT' if hit else 'MISS'}"</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N750 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:114</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"确认潜艇："<br>                    f"长度={ship.length}，"<br>                    f"方向={ship.direction}，"<br>                    f"格子={ship.cells}"</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N751 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:120</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>已排除周围格子：</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N752 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:125</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>剩余潜艇：</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N753 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:132</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>当前固定关卡配置中的潜艇已经全部确认</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N754 | 终端输出<br><code>tests/manual_strategy_board_click_test.py:135</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>本次实际点击次数：</code> | 用策略选格并点击真实设备的独立联调时，在终端展示该工具的菜单或结果。 | |
| N755 | 校验或错误提示<br><code>tests/manual_activity_entry_test.py:152</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>"最终页面检验失败："<br>            f"{final_state.value}"</code> | 从真实主岛进入活动的独立联调时，在输入或执行结果不符合条件时给出原因。 | |
| N756 | 校验或错误提示<br><code>tests/manual_activity_entry_test.py:158</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>最终弱网状态检验失败</code> | 从真实主岛进入活动的独立联调时，在输入或执行结果不符合条件时给出原因。 | |
| N757 | 校验或错误提示<br><code>tests/manual_activity_entry_test.py:163</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>最终 REJECT 状态异常</code> | 从真实主岛进入活动的独立联调时，在输入或执行结果不符合条件时给出原因。 | |
| N758 | 校验或错误提示<br><code>tests/manual_auto_probe_cycle_test.py:59</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>DEFAULT_LEVEL_CONFIG.board_quad 还没有填写</code> | 自动单发及 HIT／MISS 恢复的独立联调时，在输入或执行结果不符合条件时给出原因。 | |
| N759 | 校验或错误提示<br><code>tests/manual_auto_single_probe_test.py:62</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>DEFAULT_LEVEL_CONFIG.board_quad 还没有填写</code> | 单发截图自动识别的独立联调时，在输入或执行结果不符合条件时给出原因。 | |
| N760 | 校验或错误提示<br><code>tests/manual_board_click_test.py:32</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>DEFAULT_LEVEL_CONFIG.board_quad 还没有填写</code> | 按预设棋盘坐标点击设备的独立联调时，在输入或执行结果不符合条件时给出原因。 | |
| N761 | 校验或错误提示<br><code>tests/manual_single_probe_test.py:57</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>DEFAULT_LEVEL_CONFIG.board_quad 还没有填写</code> | 在终端填 HIT／MISS 的独立单发联调时，在输入或执行结果不符合条件时给出原因。 | |
| N762 | 校验或错误提示<br><code>tests/manual_strategy_board_click_test.py:26</code><br>关联：N567, N568, N569, N570, N571, N572（其余见索引） | <code>DEFAULT_LEVEL_CONFIG.board_quad 还没有填写</code> | 用策略选格并点击真实设备的独立联调时，在输入或执行结果不符合条件时给出原因。 | |

### A03 离线识别、素材预审与策略演示（整理用标题）

全盘图像识别、素材预审、OCR 和策略演示按独立入口登记；全盘识别结果不会通过此工具自动写回主循环棋盘。参数说明属于这些工具的帮助／诊断文案。

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N763 | 窗口标题<br><code>tests/manual_strategy_ui_demo.py:45</code><br>关联：N768 | <code>Sonar Strategy UI Demo</code> | 独立策略模拟或演示程序运行时，标明窗口用途。 | |
| N764 | 按钮文案<br><code>tests/manual_strategy_ui_demo.py:93</code> | <code>执行当前一步</code> | 独立策略模拟或演示程序运行时，显示可执行操作或按钮当前状态。 | |
| N765 | 按钮文案<br><code>tests/manual_strategy_ui_demo.py:102</code> | <code>自动演示</code> | 独立策略模拟或演示程序运行时，显示可执行操作或按钮当前状态。 | |
| N766 | 按钮文案<br><code>tests/manual_strategy_ui_demo.py:111</code> | <code>停止</code> | 独立策略模拟或演示程序运行时，显示可执行操作或按钮当前状态。 | |
| N767 | 按钮文案<br><code>tests/manual_strategy_ui_demo.py:120</code> | <code>重置</code> | 独立策略模拟或演示程序运行时，显示可执行操作或按钮当前状态。 | |
| N768 | 状态显示<br><code>tests/manual_strategy_ui_demo.py:70</code><br>关联：N763 | <code>已准备第一格</code> | 独立策略模拟或演示程序运行时，显示当前进度或操作结果。 | |
| N769 | 状态显示<br><code>tests/manual_strategy_ui_demo.py:147；tests/manual_strategy_ui_demo.py:191</code><br>关联：N770, N825, N826 | <code>f"完成，共 {self.step_count} 次探测"</code> | 独立策略模拟或演示程序运行时，显示当前进度或操作结果。 | |
| N770 | 状态显示<br><code>tests/manual_strategy_ui_demo.py:158</code><br>关联：N769, N825, N826 | <code>没有可继续探测的格子</code> | 独立策略模拟或演示程序运行时，显示当前进度或操作结果。 | |
| N771 | 状态显示<br><code>tests/manual_strategy_ui_demo.py:229</code> | <code>已重置并准备第一格</code> | 独立策略模拟或演示程序运行时，显示当前进度或操作结果。 | |
| N954 | 命令行帮助<br><code>tests/audit_board_screenshots.py:1</code><br>关联：N955 | <code>先预审无标签素材，再对可用样本做单帧识别；不计算准确率。</code> | 该独立工具将模块说明传给命令行帮助，用户执行 --help 时显示用途。 | |
| N772 | 命令行帮助<br><code>tests/audit_board_screenshots.py:27</code><br>关联：N773, N774, N775, N776, N777, N778（其余见索引） | <code>本批素材所用几何配置，不从文件名推断关卡</code> | 离线全盘识别或素材预审工具运行时，说明该工具的用途或参数。 | |
| N773 | 命令行帮助<br><code>tests/audit_board_screenshots.py:31</code><br>关联：N772, N774, N775, N776, N777, N778（其余见索引） | <code>独立素材预审线程数；不改变单张识别规则</code> | 离线全盘识别或素材预审工具运行时，说明该工具的用途或参数。 | |
| N774 | 终端输出<br><code>tests/audit_board_screenshots.py:60</code><br>关联：N772, N773, N775, N776, N777, N778（其余见索引） | <code>f"quality {index+1}/{len(paths)}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N775 | 终端输出<br><code>tests/audit_board_screenshots.py:73</code><br>关联：N772, N773, N774, N776, N777, N778（其余见索引） | <code>f"recognize {index+1}/{len(selected)} {result.counts} review={len(result.review_cells)}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N776 | 显示组成文字／诊断消息<br><code>tests/audit_board_screenshots.py:77</code><br>关联：N772, N773, N774, N775, N777, N778（其余见索引） | <code>素材无人工标签，质量类别为自动启发式预审；未计算识别准确率。关卡几何由命令行指定。</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N955 | 命令行帮助<br><code>tests/manual_global_board_recognition_test.py:1</code><br>关联：N954 | <code>独立离线全盘测试。无参数时询问截图、关卡和可选全空基准路径。</code> | 该独立工具将模块说明传给命令行帮助，用户执行 --help 时显示用途。 | |
| N777 | 命令行帮助<br><code>tests/manual_global_board_recognition_test.py:18</code><br>关联：N772, N773, N774, N775, N776, N778（其余见索引） | <code>当前单帧实机截图</code> | 离线全盘识别或素材预审工具运行时，说明该工具的用途或参数。 | |
| N778 | 命令行帮助<br><code>tests/manual_global_board_recognition_test.py:19</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>关卡号，默认11</code> | 离线全盘识别或素材预审工具运行时，说明该工具的用途或参数。 | |
| N779 | 命令行帮助<br><code>tests/manual_global_board_recognition_test.py:20</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>显式指定全空基准图；不会自动猜测</code> | 离线全盘识别或素材预审工具运行时，说明该工具的用途或参数。 | |
| N780 | 命令行帮助<br><code>tests/manual_global_board_recognition_test.py:21</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>本轮独立输出目录</code> | 离线全盘识别或素材预审工具运行时，说明该工具的用途或参数。 | |
| N781 | 终端输入提示<br><code>tests/manual_global_board_recognition_test.py:24</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>当前截图路径：</code> | 离线全盘识别或素材预审工具运行时，要求终端用户输入选择。 | |
| N782 | 终端输入提示<br><code>tests/manual_global_board_recognition_test.py:27</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>关卡号 [11]：</code> | 离线全盘识别或素材预审工具运行时，要求终端用户输入选择。 | |
| N783 | 显示组成文字／诊断消息<br><code>tests/manual_global_board_recognition_test.py:29</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>关卡号必须为正整数</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N784 | 终端输入提示<br><code>tests/manual_global_board_recognition_test.py:31</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>全空基准路径 [Enter使用关卡配置]：</code> | 离线全盘识别或素材预审工具运行时，要求终端用户输入选择。 | |
| N785 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:37</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"识别未完成：{exc}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N786 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:40</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code><br>U=UNKNOWN(未探测) M=MISS H=HIT S=SUNK；行列显示从1开始</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N787 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:44</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"({cell.row+1},{cell.col+1}) {cell.state.value.upper():7s} "<br>              f"confidence={cell.confidence:.3f} needs_review={cell.needs_review} {cell.reason}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N788 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:46</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"\n数量：{result.counts}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N789 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:47</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"低可信格：{[(r+1, c+1) for r, c in result.review_cells]}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N790 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:48</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>SUNK潜艇（行列从1开始）：</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N791 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:50</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"  {ship.direction} 长度={ship.length} "<br>              f"格子={[(r+1, c+1) for r, c in ship.cells]} "<br>              f"confidence={ship.confidence:.3f} {ship.reason}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N792 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:54</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>  无</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N793 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:55</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"对齐：{result.alignment}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N794 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:56</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"素材质量：{result.quality} / {result.quality_score:.3f}，整盘可用={result.valid}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N795 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:57</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"异常：{result.issues}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N796 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:58</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"debug目录：{output.resolve()}"</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N797 | 终端输出<br><code>tests/manual_global_board_recognition_test.py:59</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>结果需要人工复核；confidence 是证据分，尚未用人工标签校准。</code> | 离线全盘识别或素材预审工具运行时，在终端展示该工具的菜单或结果。 | |
| N798 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:140</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code><br>真实截图单格识别结果</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N799 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:141</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"目标格编号（GUI）：{TARGET_CELL[0]},{TARGET_CELL[1]}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N800 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:142</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"目标格内部坐标：{target_cell}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N801 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:143</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"目标格像素中心：{target_center}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N802 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:144</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"最终 state：{final_state}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N803 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:145</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"识别器 state：{recognition.state}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N804 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:146</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"confidence：{recognition.confidence:.6f}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N805 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:147</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"score：{recognition.score:.6f}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N806 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:148</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"是否 HIT：{is_hit}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N807 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:149</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"是否确认潜艇 / SUNK：{is_sunk}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N808 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:150</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"需要多帧确认：{needs_extra_frame}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N809 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:151</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"实际使用 after 帧数：{1 + (len(EXTRA_AFTER_IMAGE_PATHS) if needs_extra_frame else 0)}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N810 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:153</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code><br>识别结果对象完整参数：</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N811 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:155</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"  {name}={value}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N812 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:158</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code><br>正式策略校验结果：</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N813 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:159</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"  confirmation_source={commit.confirmation_source}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N814 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:160</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"  newly_confirmed={commit.newly_confirmed}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N815 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:161</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"  sunk_validation={commit.sunk_validation}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N816 | 终端输出<br><code>tests/manual_real_diamond_hit_test.py:164</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"\ndebug 图片目录：{debug_dir}"</code> | 用已保存截图独立验证命中识别时，在终端展示该工具的菜单或结果。 | |
| N817 | 终端输出<br><code>tests/manual_strategy_simulation.py:50</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>第一种棋盘颜色固定遍历表：</code> | 独立策略模拟或演示程序运行时，在终端展示该工具的菜单或结果。 | |
| N818 | 终端输出<br><code>tests/manual_strategy_simulation.py:60</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>没有可继续选择的格子，流程提前结束</code> | 独立策略模拟或演示程序运行时，在终端展示该工具的菜单或结果。 | |
| N819 | 终端输出<br><code>tests/manual_strategy_simulation.py:72</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>f"{step:02d}. 探测 {cell} -&gt; "<br>            f"{'HIT' if hit else 'MISS'}"</code> | 独立策略模拟或演示程序运行时，在终端展示该工具的菜单或结果。 | |
| N820 | 终端输出<br><code>tests/manual_strategy_simulation.py:78</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>"    确认潜艇："<br>                f"长度={ship.length}，"<br>                f"方向={ship.direction}，"<br>                f"格子={ship.cells}"</code> | 独立策略模拟或演示程序运行时，在终端展示该工具的菜单或结果。 | |
| N821 | 终端输出<br><code>tests/manual_strategy_simulation.py:86</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>完成：</code> | 独立策略模拟或演示程序运行时，在终端展示该工具的菜单或结果。 | |
| N822 | 终端输出<br><code>tests/manual_strategy_simulation.py:90</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>总探测次数：</code> | 独立策略模拟或演示程序运行时，在终端展示该工具的菜单或结果。 | |
| N823 | 终端输出<br><code>tests/manual_strategy_simulation.py:94</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>已确认潜艇：</code> | 独立策略模拟或演示程序运行时，在终端展示该工具的菜单或结果。 | |
| N824 | 终端输出<br><code>tests/manual_strategy_simulation.py:101</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>排除格数量：</code> | 独立策略模拟或演示程序运行时，在终端展示该工具的菜单或结果。 | |
| N825 | 显示组成文字／诊断消息<br><code>tests/manual_strategy_ui_demo.py:176</code><br>关联：N769, N770, N826 | <code>f"第 {self.step_count} 步：{cell} -&gt; {result_text}；"<br>            f"下一格={next_cell}"</code> | 独立策略模拟或演示程序运行时，组成界面提示或该步骤的诊断信息。 | |
| N826 | 显示组成文字／诊断消息<br><code>tests/manual_strategy_ui_demo.py:185</code><br>关联：N769, N770, N825 | <code>f"；确认潜艇 [{lengths}]"</code> | 独立策略模拟或演示程序运行时，组成界面提示或该步骤的诊断信息。 | |
| N827 | 显示组成文字／诊断消息<br><code>vision/board_alignment.py:71</code><br>关联：N828, N829, N830 | <code>可见网格锚点不足，无法可靠对齐</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N828 | 显示组成文字／诊断消息<br><code>vision/board_alignment.py:98</code><br>关联：N827, N829, N830 | <code>网格局部匹配通过RANSAC和四角几何校验</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N829 | 显示组成文字／诊断消息<br><code>vision/board_alignment.py:101</code><br>关联：N827, N828, N830 | <code>配准变换超出位移/面积容差，拒绝应用</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N830 | 显示组成文字／诊断消息<br><code>vision/board_alignment.py:104</code><br>关联：N827, N828, N829 | <code>配准证据覆盖或置信度不足</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N831 | 显示组成文字／诊断消息<br><code>vision/board_features.py:197</code><br>关联：N832, N833 | <code>对齐失败，仅保留低可信候选</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N832 | 显示组成文字／诊断消息<br><code>vision/board_features.py:199</code><br>关联：N831, N833 | <code>当前或基准区域存在遮挡</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N833 | 显示组成文字／诊断消息<br><code>vision/board_features.py:201</code><br>关联：N831, N832 | <code>多个状态证据接近</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N834 | 显示组成文字／诊断消息<br><code>vision/board_features.py:241</code><br>关联：N835, N836, N837, N838, N839 | <code>f"船体连通块方向不明确：{contacts}"</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N835 | 显示组成文字／诊断消息<br><code>vision/board_features.py:253</code><br>关联：N834, N836, N837, N838, N839 | <code>f"船体跨格支持不连续：{group}"</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N836 | 显示组成文字／诊断消息<br><code>vision/board_features.py:273</code><br>关联：N834, N835, N837, N838, N839 | <code>f"连续船体长度{len(group)}不在当前关卡配置：{group}"</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N837 | 显示组成文字／诊断消息<br><code>vision/board_features.py:286</code><br>关联：N834, N835, N836, N838, N839 | <code>同一船体连通块跨越全部相邻格界，方向/长度一致</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N838 | 显示组成文字／诊断消息<br><code>vision/board_features.py:311</code><br>关联：N834, N835, N836, N837, N839 | <code>f"潜艇候选多解释/重叠/安全间距/数量冲突：{ship.cells}"</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N839 | 显示组成文字／诊断消息<br><code>vision/board_features.py:333</code><br>关联：N834, N835, N836, N837, N838 | <code>；整船结构存在冲突</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N840 | 显示组成文字／诊断消息<br><code>vision/board_materials.py:27</code><br>关联：N841, N842 | <code>图片尺寸与基准不同</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N841 | 显示组成文字／诊断消息<br><code>vision/board_materials.py:51</code><br>关联：N840, N842 | <code>缺少可靠网格和海面证据</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N842 | 显示组成文字／诊断消息<br><code>vision/board_materials.py:54</code><br>关联：N840, N841 | <code>f"动态文字/面板遮挡占比={occlusion:.3f}"</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N843 | 显示组成文字／诊断消息<br><code>vision/board_recognition.py:90</code><br>关联：N844, N845, N846, N928, N929, N930（其余见索引） | <code>棋盘定位失败且预期海水颜色不足，可能处于其他页面</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N844 | 显示组成文字／诊断消息<br><code>vision/board_recognition.py:93</code><br>关联：N843, N845, N846, N928, N929, N930（其余见索引） | <code>f"遮挡比例较高：{dynamic_occlusion:.3f}"</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N845 | 显示组成文字／诊断消息<br><code>vision/board_recognition.py:99</code><br>关联：N843, N844, N846, N928, N929, N930（其余见索引） | <code>基准图本身有文字遮挡的格子，已单独降低可信度</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N846 | 显示组成文字／诊断消息<br><code>vision/board_recognition.py:104</code><br>关联：N843, N844, N845, N928, N929, N930（其余见索引） | <code>f"需复核格比例过高：{review_fraction:.3f}，整盘标记不可直接使用"</code> | 离线全盘识别或素材预审工具运行时，组成界面提示或该步骤的诊断信息。 | |
| N956 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:18</code><br>关联：N957, N958, N959, N960, N961, N962（其余见索引） | <code>透视校正后每格像素；增大提高细节与开销</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N957 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:19</code><br>关联：N956, N958, N959, N960, N961, N962（其余见索引） | <code>校正图外围留白格数；增大保留更多船体外延</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N958 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:20</code><br>关联：N956, N957, N959, N960, N961, N962（其余见索引） | <code>原图局部配准搜索半径；增大容忍更大位移，也增加错配风险</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N959 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:21</code><br>关联：N956, N957, N958, N960, N961, N962（其余见索引） | <code>四角最大位移；增大放宽配准几何约束</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N960 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:22</code><br>关联：N956, N957, N958, N959, N961, N962（其余见索引） | <code>网格锚点最低匹配分；增大减少弱锚点</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N961 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:23</code><br>关联：N956, N957, N958, N959, N960, N962（其余见索引） | <code>配准最少锚点；增大要求更多可见网格</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N962 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:24</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>RANSAC内点误差；增大容忍局部变形</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N963 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:25</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>锚点凸包占棋盘面积下限；增大抑制局部配准冒充全盘</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N964 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:26</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>可用配准置信度下限；增大更保守</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N965 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:27</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>棋盘面积变化比例上限；增大容忍缩放</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N966 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:28</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>提取亮边框的背景模糊尺度；增大突出较宽线条</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N967 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:29</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>亮边框局部对比度归一尺度；增大降低边框响应</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N968 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:30</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>边框颜色饱和度上限；增大接受更蓝的线条</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N969 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:31</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>边框饱和度权重的过渡范围；增大降低颜色响应</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N970 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:32</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>边框最低亮度；增大排除暗纹理</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N971 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:33</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>基准亮线阈值；增大只保留强边框</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N972 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:34</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>每格边界带宽占比；增大覆盖更偏移的实际边框</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N973 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:35</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>格内统计的边缘排除占比；增大减少边缘污染</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N974 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:36</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>校正图边框匹配膨胀半径；增大容忍残余偏差</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N975 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:37</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>全局亮度补偿上限；增大接受更明显光照变化</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N976 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:38</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>Lab中值差异归一尺度；增大降低差异证据</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N977 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:39</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>中性船体像素饱和度上限；增大接受更蓝的金属</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N978 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:40</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体最低亮度；增大排除暗部</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N979 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:41</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体BGR最大通道差；增大放宽中性色限制</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N980 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:42</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>相对基准的饱和度下降；增大要求更明显金属变化</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N981 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:43</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>相对基准的亮度差；增大抑制海面闪光</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N982 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:44</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体最小连通块占单格面积比例；增大排除碎噪声</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N983 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:45</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体闭运算尺寸占单格比例；增大连接较宽小裂缝</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N984 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:46</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>格内船体占比归一尺度；增大要求更多船体证据</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N985 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:47</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体边缘密度尺度；增大要求更多纹理</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N986 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:48</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体覆盖和纹理权重；增大第二项更依赖纹理</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N987 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:49</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>Canny弱/强边缘阈值；增大减少细纹理响应</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N988 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:50</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>完整亮边框对船体证据的抑制；增大减少未探测格浪花误报</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N989 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:51</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>探测后饱和度上升尺度；增大降低水面证据</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N990 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:52</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>探测后变暗尺度；增大降低暗水面证据</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N991 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:53</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>开格的边框缺失、饱和度、变暗权重；增大某项提高其影响</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N992 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:54</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>未探测的边框、颜色相似权重；增大某项提高其影响</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N993 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:55</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体对UNKNOWN/MISS的抑制权重；增大更偏向HIT</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N994 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:56</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>低可信复核阈值；增大标记更多格</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N995 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:57</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>候选分差下限；增大对竞争状态更保守</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N996 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:58</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>最高分、分差、证据一致性的权重；增大某项提高其影响</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N997 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:59</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>对齐失败时置信度上限；增大提高失败结果的上限</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N998 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:60</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>结构冲突时置信度上限；增大提高冲突结果的上限</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N999 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:61</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>黑色遮挡亮度上限；增大覆盖更多暗面板</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1000 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:62</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>白色遮挡亮度下限；增大减少白色面板检出</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1001 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:63</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>格内极黑/白比例；增大减少遮挡误报</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1002 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:64</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>遮挡比例复核阈值；增大容忍更大遮挡</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1003 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:65</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>大块面板的饱和度上限；增大接受带颜色的面板</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1004 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:66</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>面板局部亮度标准差上限；增大接受更有纹理的面板</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1005 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:67</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>平坦面板最小面积，以格为单位；增大减少船壳误报</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1006 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:68</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>面板最短边对应格数；增大减少窄船体误报</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1007 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:69</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>文字白色笔画亮度；增大减少波纹误检</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1008 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:70</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>文字低饱和范围；增大接受有色文字</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1009 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:71</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>文字描边最大亮度；增大接受更浅的描边</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1010 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:72</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>白色笔画附近深色比例；增大减少浪花/格线误报</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1011 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:73</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>水平文字组最少小连通块；增大减少船体误判</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1012 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:74</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>文字单块最大原图高度；增大接受大字</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1013 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:75</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>文字块面积范围；扩大范围接受更多字体及噪声</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1014 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:76</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>文字块宽度范围；扩大范围接受更多字体及噪声</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1015 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:77</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>文字组最小宽度相对原图格宽；增大减少短字符误检</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1016 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:78</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>文字横向组团距离；增大连接更疏的字</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1017 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:79</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>对齐失败时水面占比下限；增大更容易判为错误页面</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1018 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:80</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体连通块覆盖单格比例下限；增大排除擦边格</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1019 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:81</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体主/次轴比例下限；增大要求更直更长，可能漏掉短艇</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1020 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:82</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>主轴与逻辑H/V的角度容差；增大接受更斜的船体</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1021 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:83</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>跨相邻格界的船体宽度占比；增大要求更明显连接</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1022 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:84</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体沿候选段长度的最低覆盖比例；增大要求船体更完整</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1023 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:85</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>船体立体上浮的逻辑格回投补偿；增大将船体归属向下移动</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1024 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:86</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>连续船体归属单一逻辑行/列所需像素占比；增大对宽船体归属更保守</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1025 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:87</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>SUNK结构确认最低综合证据；增大减少提前确认</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1026 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:88</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>SUNK单格支持、边界连接、长度覆盖权重；增大某项提高其影响</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1027 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:89</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>OpenCV海水色相范围；扩大范围减少错误页面报警</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1028 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:90</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>海水最低饱和度；增大排除灰色面板</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1029 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:91</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>动态遮挡占棋盘比例；增大放宽素材可用门槛</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N1030 | 参数帮助元数据（未接入主界面）<br><code>vision/board_types.py:92</code><br>关联：N956, N957, N958, N959, N960, N961（其余见索引） | <code>整盘可用标志允许的最大复核格比例；增大放宽总体门槛</code> | 在离线全盘识别配置的 metadata.help 中解释该参数作用和调大效果，当前没有主界面显示入口。 | |
| N922 | 校验或错误提示<br><code>tests/manual_real_diamond_hit_test.py:54</code> | <code>TARGET_CELL 必须写成 (行, 列)</code> | 用已保存截图独立验证命中识别时，在输入或执行结果不符合条件时给出原因。 | |
| N923 | 校验或错误提示<br><code>tests/manual_real_diamond_hit_test.py:64</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>"当前正式默认映射要求 GRID_SIZE="<br>            f"{DEFAULT_LEVEL_CONFIG.grid_size}"</code> | 用已保存截图独立验证命中识别时，在输入或执行结果不符合条件时给出原因。 | |
| N924 | 校验或错误提示<br><code>tests/manual_real_diamond_hit_test.py:68</code><br>关联：N772, N773, N774, N775, N776, N777（其余见索引） | <code>DEFAULT_LEVEL_CONFIG.board_quad 尚未配置</code> | 用已保存截图独立验证命中识别时，在输入或执行结果不符合条件时给出原因。 | |
| N925 | 校验或错误提示<br><code>vision/board_debug.py:22</code> | <code>f"debug图片编码失败：{path}"</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N926 | 校验或错误提示<br><code>vision/board_debug.py:31</code> | <code>f"输出目录已有结果，请使用新目录：{output}"</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N927 | 校验或错误提示<br><code>vision/board_recognition.py:27</code> | <code>f"缺少第 {level} 关全空基准图：{path}；请用 --reference 明确指定全空截图"</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N928 | 校验或错误提示<br><code>vision/board_recognition.py:48</code><br>关联：N843, N844, N845, N846, N929, N930（其余见索引） | <code>f"{name} 必须是非空 uint8 BGR 三通道图片"</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N929 | 校验或错误提示<br><code>vision/board_recognition.py:50</code><br>关联：N843, N844, N845, N846, N928, N930（其余见索引） | <code>f"{name} 图片为空"</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N930 | 校验或错误提示<br><code>vision/board_recognition.py:52</code><br>关联：N843, N844, N845, N846, N928, N929（其余见索引） | <code>空基准与当前截图尺寸不同；请提供相同分辨率、未经裁剪的实机截图</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N931 | 校验或错误提示<br><code>vision/board_recognition.py:54</code><br>关联：N843, N844, N845, N846, N928, N929（其余见索引） | <code>关卡缺少有效 board_quad/grid_size</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N932 | 校验或错误提示<br><code>vision/board_recognition.py:56</code><br>关联：N843, N844, N845, N846, N928, N929（其余见索引） | <code>cell_pixels 至少16，alignment_search_px 不得为负</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N933 | 校验或错误提示<br><code>vision/board_types.py:96</code><br>关联：N934, N935 | <code>cell_pixels至少16，搜索半径和padding不得为负</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N934 | 校验或错误提示<br><code>vision/board_types.py:98</code><br>关联：N933, N935 | <code>格内margin和边界band必须在(0, 0.5)内</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N935 | 校验或错误提示<br><code>vision/board_types.py:103</code><br>关联：N933, N934 | <code>f"{name}必须是和为1的非负权重"</code> | 离线全盘识别或素材预审工具运行时，在输入或执行结果不符合条件时给出原因。 | |
| N936 | 校验或错误提示<br><code>vision/ocr_helper.py:67</code> | <code>image 必须是有效的 OpenCV 图片</code> | 调用尚未接入主循环的 OCR 辅助接口时，在输入或执行结果不符合条件时给出原因。 | |

### A04 预留显示与未接入主界面的辅助入口（整理用标题）

包括主窗口未绑定按钮的调试辅助方法、终端人工单发结果提交，以及当前策略未提供进度值时不会显示的“计算”文案；外部使用情况无法仅凭仓库确认。

| 编号 | 所属功能/出现位置 | 当前名称原文 | 实际含义及出现时机 | 修改后名称（用户填写） |
|---|---|---|---|---|
| N937 | 日志<br><code>flows/probe_flow.py:350</code><br>关联：N938, N939, N940, N948 | <code>人工探测结果已提交：%s -&gt; %s</code> | 执行本发选格、截图和活动进出时，记录这一步的参数、结果或异常。 | |
| N938 | 日志<br><code>flows/probe_flow.py:352</code><br>关联：N244, N257, N260, N937, N939, N940（其余见索引） | <code>HIT</code> | 执行本发选格、截图和活动进出时，记录这一步的参数、结果或异常。 | |
| N939 | 日志<br><code>flows/probe_flow.py:352</code><br>关联：N245, N258, N259, N937, N938, N940（其余见索引） | <code>MISS</code> | 执行本发选格、截图和活动进出时，记录这一步的参数、结果或异常。 | |
| N940 | 日志<br><code>flows/probe_flow.py:357</code><br>关联：N937, N938, N939, N948 | <code>本次新确认潜艇：%s</code> | 执行本发选格、截图和活动进出时，记录这一步的参数、结果或异常。 | |
| N941 | 日志（DEBUG，默认不显示）<br><code>controllers/game_controller.py:112</code> | <code>获取游戏截图</code> | 保存并检查当前设备截图时，在启用 DEBUG 日志时记录细节。 | |
| N942 | 显示组成文字／诊断消息<br><code>ui/board_view.py:457</code> | <code>f" &#124; 计算 {percent}%"</code> | 刷新棋盘尺寸、策略、剩余潜艇和下一目标摘要时，组成界面提示或该步骤的诊断信息。 | |
| N943 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:693</code><br>关联：N244, N257, N260, N938, N944, N945（其余见索引） | <code>HIT</code> | 主窗口刷新操作状态或处理结果时，组成界面提示或该步骤的诊断信息。 | |
| N944 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:693</code><br>关联：N245, N258, N259, N939, N943, N945（其余见索引） | <code>MISS</code> | 主窗口刷新操作状态或处理结果时，组成界面提示或该步骤的诊断信息。 | |
| N945 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:695</code><br>关联：N943, N944, N946 | <code>f"策略结果：{cell} -&gt; {result_text}；"<br>            f"下一格={next_cell}"</code> | 主窗口刷新操作状态或处理结果时，组成界面提示或该步骤的诊断信息。 | |
| N946 | 显示组成文字／诊断消息<br><code>ui/gui_app.py:705</code><br>关联：N943, N944, N945 | <code>f"；新确认潜艇=[{lengths}]"</code> | 主窗口刷新操作状态或处理结果时，组成界面提示或该步骤的诊断信息。 | |
| N947 | 校验或错误提示<br><code>controllers/adb_controller.py:955</code><br>关联：N224, N506 | <code>等待时间不能小于 0</code> | 执行真实设备连接、截图、输入或应用命令时，在输入或执行结果不符合条件时给出原因。 | |
| N948 | 校验或错误提示<br><code>flows/probe_flow.py:330</code><br>关联：N937, N938, N939, N940 | <code>"人工结果对应的格子和策略当前等待格不一致："<br>            f"pending={pending}, context={context.cell}"</code> | 执行本发选格、截图和活动进出时，在输入或执行结果不符合条件时给出原因。 | |

## 附录：内部业务标识与改动风险（整理用标题）

以下均为内部标识。默认显示文案改名不会自动扩展到这里，完整定义、引用、字段和路径在 `naming_locations.json` 中。

| 类别 | 当前标识原文 | 用途与风险 |
|---|---|---|
| 页面类型 | <code>activity_detail, home_sonar_visible, home, unknown</code> | 用于页面判断及恢复分支，中文选项修改不默认修改这些值。 |
| 策略阶段 | <code>HUNT, TARGET, DONE</code> | 内部状态与中文巡航／追击／完成分开维护。 |
| 格子状态 | <code>unknown, selected, miss, hit, sunk</code> | 用于棋盘快照、显示及策略判断。 |
| 人工答案 | <code>found, missing, timeout, hit, miss, unopened, unknown</code> | 答案值是接口协议，中文按钮标题可独立调整。 |
| 识别或击沉确认来源 | <code>manual_trial, visual, inference</code> | 部分值参与逻辑分支和诊断数据；显示前缀改名不应自动扩大到这些值。 |
| 恢复路径 | <code>hit_online_wait, miss_retry, strategy_done_online, exception_restart</code> | 恢复结果的 mode 字段，可能显示在日志及被测试校验。 |
| 循环终止原因 | <code>requested, strategy_done, max_rounds, max_levels, recovery_failed</code> | 用于停止、错误及完成分支。 |
| 主线程消息 | <code>manual_request, result, round, level, summary, error, stopped</code> | 队列发送端与接收端必须一致。 |
| 配置键与参数 | `config.py`、`sonar_config.py` 及识别配置类 | 调整名称会影响导入、构造参数和测试；本轮不改数值或键名。 |
| 文件路径与诊断字段 | 模板文件名、runtime 路径、截图／JSON 字段 | 会影响文件读取、诊断记录及外部工具，需另行确认兼容范围。 |
| 命令行参数 | `main.py` 与独立工具的 `add_argument` | 属于调用接口；显示帮助和参数本身需分开确认。 |
| 类与函数 | `internal_identifiers` 与 `call_index` | 索引记录定义与静态调用位置；仓库外调用无法确认。 |

## 独立工具定位目录（整理用标题）

| 当前文件／内部入口 | 实际用途 |
|---|---|
| `tests/manual_activity_entry_test.py` | 从真实主岛进入活动的独立联调。 |
| `tests/manual_auto_probe_cycle_test.py` | 自动单发及 HIT／MISS 恢复的独立联调。 |
| `tests/manual_auto_single_probe_test.py` | 单发截图自动识别的独立联调。 |
| `tests/manual_board_click_test.py` | 按预设棋盘坐标点击设备的独立联调。 |
| `tests/manual_network_test.py` | 交互切换设备网络规则的独立联调。 |
| `tests/manual_page_control_test.py` | 交互检查页面和模板的独立联调。 |
| `tests/manual_single_probe_test.py` | 在终端填 HIT／MISS 的独立单发联调。 |
| `tests/manual_strategy_board_click_test.py` | 用策略选格并点击真实设备的独立联调。 |
| `tests/manual_global_board_recognition_test.py` | 读取文件进行离线全盘识别。 |
| `tests/manual_real_diamond_hit_test.py` | 用保存的真实截图离线校验单发命中。 |
| `tests/manual_strategy_simulation.py` | 用固定隐藏潜艇离线模拟策略。 |
| `tests/manual_strategy_ui_demo.py` | 在独立演示窗口观察离线策略。 |
| `tests/audit_board_screenshots.py` | 离线审计棋盘截图素材质量。 |
| `main.py` | 独立设备、截图、网络与 GUI 命令行入口。 |
| `vision/ocr_helper.py` | OCR 辅助接口，主循环未调用；依赖与外部调用情况不据此认定可用。 |

## 明确的边界与未确认项

- `HUNT／TARGET／DONE` 的中文显示与内部值分开；`CellState`、页面枚举、结果来源及队列事件均单列，避免把接口值当成单纯文案。
- 全盘离线识别、策略演示与主循环分开登记；代码注释中的未来概率计算、截图回放、虚拟活动等不冒充现用功能。
- 原棋盘格内编号是 1 起算，悬停逻辑格和部分结果日志保留内部坐标表达式；本轮没有统一这些坐标文案。
- 动态设备输出、第三方报错和系统文件窗口没有固定、可穷举的项目原文；索引保留项目中的接入位置与格式。
- 首次清单按静态源码核对；本次改名另运行现有回归（设备和网络使用替身），结果见文末；未进行真实设备验证。

## 后续集中改名规则

1. 等用户填写最后一列或按编号提供新名称，并明确要求实施后才修改。留空、未指定或新旧相同的条目保持原样，用户新名称优先。
2. 默认只改该编号登记的显示位置；内部标识、配置键、文件名、命令行参数及外部保存格式必须另列范围确认。
3. 实施前重新读取文件，比较原始字节校验值、原文、表达式、类／函数和调用含义；代码变化或意图不清时先列冲突，不按旧行号或全局字符串机械替换。
4. 核对关联编号、解析依赖、占位符与格式、相关测试以及现行使用说明；历史归档保留原貌。
5. 输出“编号 → 旧名 → 新名 → 实际修改位置”结果表，并说明验证范围。
6. 后续补充保持已有 N 编号，新增编号从现有最大值之后追加，删除编号不重新分配。

编号允许不连续；预留编号记录在索引 `reserved_ids` 中，后续不复用。实际用于命令行 `--help` 的模块说明已按帮助文案登记，其余源码说明不作为显示名称。


## 已实施的文案修改

仅修改显示文字及相关注释、测试匹配文字、现行操作说明；内部状态、字段、路径和运行逻辑保持原样。页面判断的“无法判断”保留。

| 编号 | 旧名 | 新名 | 实际修改位置 |
|---|---|---|---|
| N174 | <code>等待主岛就绪</code> | <code>等待主岛按键出现</code> | <code>flows/sonar_page.py:202</code> |
| N184 | <code>声纳等待成功：中心=%s，相似度=%.3f，检测次数=%s</code> | <code>等待声纳成功出现：中心=%s，相似度=%.3f，检测次数=%s</code> | <code>flows/sonar_page.py:354</code> |
| N188 | <code>已点击声纳活动详情入口：(%s, %s)</code> | <code>已点击声纳活动入口：(%s, %s)</code> | <code>flows/activity_flow.py:260</code> |
| N189 | <code>初始进入声纳活动完成：initial=%s，final=%s，sonar=%s，weak=%s</code> | <code>进入声纳活动并完成初始化：initial=%s，final=%s，sonar=%s，weak=%s</code> | <code>flows/activity_flow.py:330</code> |
| N191 | <code>活动详情页未就绪：未找到 %s</code> | <code>棋盘页面未准备就绪：未找到 %s</code> | <code>flows/sonar_page.py:409</code> |
| N192 | <code>活动详情页已就绪：退出按钮中心=%s</code> | <code>棋盘页面已准备就绪：退出按钮中心=%s</code> | <code>flows/sonar_page.py:415</code> |
| N203 | <code>已点击活动详情入口：(%s, %s)</code> | <code>已点击活动入口：(%s, %s)</code> | <code>flows/activity_flow.py:410</code> |
| N204 | <code>重新进入声纳活动完成</code> | <code>重新进入声纳活动棋盘页面完成</code> | <code>flows/activity_flow.py:435</code> |
| N207 | <code>开始自动探测前仍存在 REJECT 断网。请先恢复网络。</code> | <code>开始自动探测前仍处于REJECT 断网状态。请先恢复网络。</code> | <code>flows/auto_probe_ready.py:50</code> |
| N210 | <code>自动探测准备失败：REJECT 仍然开启</code> | <code>自动探测准备失败：REJECT 断网状态仍然开启</code> | <code>flows/auto_probe_ready.py:113</code> |
| N211 | <code>自动探测准备失败：弱网 DROP 没有开启</code> | <code>自动探测准备失败：DROP 弱网状态没有开启</code> | <code>flows/auto_probe_ready.py:119</code> |
| N212 | <code>当前仍开启 REJECT 断网，请先恢复网络再执行初始进入活动</code> | <code>当前仍处于 REJECT 断网状态，请先恢复网络再执行初始进入活动</code> | <code>flows/activity_flow.py:112</code> |
| N277 | <code>人工识别</code> | <code>人工测试模式</code> | <code>ui/manual_recognition_dialog.py:61</code> |
| N282 | <code>人工识别</code> | <code>人工测试模式</code> | <code>ui/gui_app.py:275</code> |
| N283 | <code>等待人工识别</code> | <code>等待人工测试结果</code> | <code>ui/gui_app.py:1020</code> |
| N289 | <code>主岛，声纳可见</code> | <code>主岛，声纳浮标可见</code> | <code>manual_recognition.py:23</code> |
| N298 | <code>无法判断</code> | <code>无法判断本格结果</code> | <code>manual_recognition.py:27</code> |
| N300 | <code>海边声纳</code> | <code>海边声纳浮标</code> | <code>manual_recognition.py:28</code> |
| N318 | <code>人工识别</code> | <code>人工测试模式</code> | <code>ui/gui_app.py:310</code> |
| N321 | <code>已关闭人工识别，恢复原正式棋盘；循环保持停止。</code> | <code>已关闭人工测试模式，恢复原正式棋盘；循环保持停止。</code> | <code>ui/gui_app.py:303</code> |
| N340 | <code>等待型人工识别需要原截图方法、计时起点、超时和轮询间隔</code> | <code>等待型人工测试模式需要原截图方法、计时起点、超时和轮询间隔</code> | <code>manual_recognition.py:261</code> |
| N341 | <code>人工识别已关闭</code> | <code>人工测试模式已关闭</code> | <code>ui/gui_app.py:321</code> |
| N369 | <code>HIT 恢复前弱网 DROP 没有开启</code> | <code>HIT 恢复前DROP 弱网状态没有开启</code> | <code>flows/auto_probe_recovery.py:219</code> |
| N372 | <code>HIT 恢复失败：弱网 DROP 没有重新开启</code> | <code>HIT 恢复失败：DROP 弱网状态没有重新开启</code> | <code>flows/auto_probe_recovery.py:275</code> |
| N374 | <code>进入恢复链前弱网 DROP 没有开启</code> | <code>进入恢复链前DROP 弱网状态没有开启</code> | <code>flows/auto_probe_recovery.py:396</code> |
| N377 | <code>单发恢复失败：恢复后 REJECT 仍然开启</code> | <code>单发恢复失败：恢复后 REJECT 断网状态仍然开启</code> | <code>flows/auto_probe_recovery.py:522</code> |
| N378 | <code>单发恢复失败：恢复后弱网 DROP 没有重新开启</code> | <code>单发恢复失败：恢复后DROP 弱网状态没有重新开启</code> | <code>flows/auto_probe_recovery.py:528</code> |
| N382 | <code>异常重启恢复失败：REJECT 仍然开启</code> | <code>异常重启恢复失败：REJECT 断网状态仍然开启</code> | <code>flows/auto_probe_exception_recovery.py:72</code> |
| N383 | <code>异常重启恢复失败：弱网 DROP 没有重新开启</code> | <code>异常重启恢复失败：DROP 弱网状态没有重新开启</code> | <code>flows/auto_probe_exception_recovery.py:77</code> |

本次验证：45 项现有回归通过，覆盖人工结果、Tk 弹窗、连续等待与停止、HIT/MISS 恢复、胜利处理。另核验 98 个文件校验值、955 个清单编号及原文定位，并确认 Python 非字符串语法结构保持一致；无真实设备操作或实机验收。

改动文件：`flows/sonar_page.py`、`flows/activity_flow.py`、`flows/auto_probe_ready.py`、`flows/auto_probe_recovery.py`、`flows/auto_probe_exception_recovery.py`、`manual_recognition.py`、`ui/gui_app.py`、`ui/manual_recognition_dialog.py`、`tests/test_manual_trial.py`、`docs/manual_trial.md`，以及本清单和 `docs/naming_locations.json`。

## 活动棋盘页面文案统一

将页面判断选项、页面与恢复日志、报错、注释、独立联调提示及现行操作说明统一为“活动棋盘页面”；activity_detail 等内部标识保持原样。历史记录保留当时原文。

| 编号 | 旧名 | 新名 | 实际修改位置 |
|---|---|---|---|
| N177 | <code>页面状态：活动详情页</code> | <code>页面状态：活动棋盘页面</code> | <code>flows/sonar_page.py:123</code> |
| N180 | <code>页面状态：未知；未识别到活动详情、声纳或主岛活动按钮；当前声纳最高相似度=%.3f</code> | <code>页面状态：未知；未识别到活动棋盘页面、声纳或主岛活动按钮；当前声纳最高相似度=%.3f</code> | <code>flows/sonar_page.py:179</code> |
| N208 | <code>自动探测准备失败：没有进入活动详情页</code> | <code>自动探测准备失败：没有进入活动棋盘页面</code> | <code>flows/auto_probe_ready.py:87</code> |
| N226 | <code>重新进入活动失败：点击活动详情入口后没有检测到退出按钮</code> | <code>重新进入活动失败：点击活动棋盘页面入口后没有检测到退出按钮</code> | <code>flows/activity_flow.py:425</code> |
| N238 | <code>准备退出当前活动详情页</code> | <code>准备退出当前活动棋盘页面</code> | <code>flows/probe_flow.py:265</code> |
| N264 | <code>"执行单发探测前没有检测到活动详情页。"<br>            "当前页面状态="<br>            f"{current_state.value}"</code> | <code>"执行单发探测前没有检测到活动棋盘页面。"<br>            "当前页面状态="<br>            f"{current_state.value}"</code> | <code>flows/probe_flow.py:190</code> |
| N288 | <code>活动详情页</code> | <code>活动棋盘页面</code> | <code>manual_recognition.py:23</code> |
| N370 | <code>HIT 恢复失败：5 秒联网后没有回到活动详情页</code> | <code>HIT 恢复失败：5 秒联网后没有回到活动棋盘页面</code> | <code>flows/auto_probe_recovery.py:265</code> |
| N376 | <code>单发恢复失败：恢复后没有回到活动详情页</code> | <code>单发恢复失败：恢复后没有回到活动棋盘页面</code> | <code>flows/auto_probe_recovery.py:516</code> |
| N389 | <code>胜利页面处理完成，下一关详情页已就绪</code> | <code>胜利页面处理完成，下一关活动棋盘页面已就绪</code> | <code>flows/victory_flow.py:74</code> |
| N563 | <code>活动详情页</code> | <code>活动棋盘页面</code> | <code>tests/manual_activity_entry_test.py:34</code> |
| N569 | <code>程序会自己检查主岛、寻找声纳、开启弱网并进入活动详情。</code> | <code>程序会自己检查主岛、寻找声纳、开启弱网并进入活动棋盘页面。</code> | <code>tests/manual_activity_entry_test.py:58</code> |
| N581 | <code>测试通过：当前已经位于声纳活动详情页，并保持弱网 DROP。</code> | <code>测试通过：当前已经位于声纳活动棋盘页面，并保持弱网 DROP。</code> | <code>tests/manual_activity_entry_test.py:168</code> |
| N599 | <code>1. 页面重新停在声纳活动详情页。</code> | <code>1. 页面重新停在声纳活动棋盘页面。</code> | <code>tests/manual_auto_probe_cycle_test.py:71</code> |
| N650 | <code>1. 模拟器已经进入声纳活动详情，棋盘可见。</code> | <code>1. 模拟器已经进入声纳活动棋盘页面，棋盘可见。</code> | <code>tests/manual_auto_single_probe_test.py:73</code> |
| N726 | <code>1. 模拟器当前已经进入声纳活动详情，棋盘可见。</code> | <code>1. 模拟器当前已经进入声纳活动棋盘页面，棋盘可见。</code> | <code>tests/manual_single_probe_test.py:74</code> |

验证：27 项现有回归通过，覆盖人工结果、Tk 弹窗和胜利处理；源码校验值与全部登记原文位置匹配，Python 非字符串语法结构未变。未执行真实设备操作。

本轮涉及 `flows/activity_flow.py`、`flows/auto_probe_ready.py`、`flows/auto_probe_recovery.py`、`flows/probe_flow.py`、`flows/sonar_page.py`、`flows/victory_flow.py`、`manual_recognition.py`，四个独立联调脚本 `tests/manual_activity_entry_test.py`、`tests/manual_auto_probe_cycle_test.py`、`tests/manual_auto_single_probe_test.py`、`tests/manual_single_probe_test.py`，以及 `docs/manual_trial.md` 和两份命名清单／索引。

## 默认初始关卡调整

`sonar_config.py:122` 的 `INITIAL_LEVEL` 默认值从 10 调整为 11，界面显示“第11关+”，启动时使用第 11 关棋盘及策略配置。保留 `SONAR_INITIAL_LEVEL` 环境变量覆盖。7 项相关回归及默认配置检查通过；未操作真实设备。
