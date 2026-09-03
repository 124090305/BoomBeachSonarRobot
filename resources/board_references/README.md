# 全空棋盘基准

1～11 关图片由用户指定的 `D:\Desktop\hdqb\BoomBeachSonar\resources\calibration\images\1.png`～`11.png` 原样复制。12 关及以后复用 `level_11_empty.png`。

`sonar_config.get_level_config(level).empty_reference_path` 指向唯一基准。测试程序的 `--reference` 可以覆盖路径。缺失文件会直接报错；程序不会从普通运行截图中自动选择替代图。

图片必须为对应关卡的完全未探测棋盘、原始分辨率和完整画面。基准中的水面动画可与当前图不同；顶部标题等固有遮挡会影响可观测性，相关格仍需人工复核。1～8 关图片右上角存在工具浮层，目前位于棋盘之外。

更新基准时保留旧文件备份，并重新运行全空、平移和亮度回归测试。调整四角位置仍使用现有 `sonar_config.py` 配置；无需编辑识别算法。
