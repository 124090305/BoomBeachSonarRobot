"""人工测试窗口文案。只描述既有调用分支，不执行策略或设备动作。"""
from dataclasses import dataclass

PAGE_OPTIONS = (("activity_detail", "活动棋盘页面"), ("home_sonar_visible", "主岛，声纳浮标可见"),
                ("home", "主岛"), ("unknown", "无法判断"))
TEMPLATE_OPTIONS = (("found", "找到"), ("missing", "未找到"), ("timeout", "判定超时"))
PROBE_OPTIONS = (("hit", "命中 HIT"), ("miss", "未命中 MISS"),
                 ("unopened", "未开启"), ("unknown", "无法判断本格结果"))
TEMPLATE_NAMES = {"activity_button.png": "主岛活动按钮", "sonar_join.png": "海边声纳浮标",
                  "sonar_join_label.png": "声纳标签", "quit_activity.png": "退出活动按钮",
                  "retry.png": "重试按钮", "retry1.png": "重试按钮", "victory.png": "胜利画面"}

@dataclass(frozen=True)
class PromptText:
    title: str
    expectation: str
    actions: tuple[tuple[str, str], ...]
    location: str

FAIL = "返回未找到，由当前流程报告失败并进入原异常处理"
def template(title, expectation, found, missing=FAIL, location="controllers/page_controller.py"):
    return PromptText(title, expectation, (("found", found), ("missing", missing), ("timeout", missing)), location)
def page(title, expectation, board, other, location):
    return PromptText(title, expectation, tuple((v, board if v == "activity_detail" else other) for v, _ in PAGE_OPTIONS), location)

# Key 对应明确的调用位置。同一模板在不同位置各有一条文案。
PROMPTS = {
    "ready.initial": page("单发准备 · 判断当前页面", "活动棋盘页面", "按需开启 DROP，再复查页面与网络", "按需关闭 DROP，再执行原活动进入流程", "flows/auto_probe_ready.py · ensure_auto_probe_ready"),
    "ready.final": page("单发准备 · 复查棋盘", "棋盘页面，且网络状态符合探测要求", "继续核验网络，通过后准备本发目标", "报告准备失败，进入原异常恢复", "flows/auto_probe_ready.py · ensure_auto_probe_ready"),
    "entry.initial": page("进入活动 · 判断起点", "当前页面类型", "按需开启 DROP，再读取最终页面", "等待主岛活动按钮和声纳浮标", "flows/activity_flow.py · enter_activity_initial"),
    "entry.final": page("进入活动 · 检查结果", "活动棋盘页面", "返回页面结果，由调用方继续核验", "返回页面结果，由调用方核验并决定是否恢复", "flows/activity_flow.py · enter_activity_initial"),
    "entry.home": template("进入活动 · 等待主岛按键", "主岛活动按钮可见", "接着查找海边声纳浮标", location="flows/sonar_page.py · wait_home_island_ready"),
    "entry.sonar.first": template("进入活动 · 查找海边声纳浮标", "浮标或声纳标签可见", "等待并点击主岛活动按钮", "上划主岛，再等待海边声纳浮标", "flows/sonar_page.py · wait_sonar_ready"),
    "entry.sonar.wait": template("进入活动 · 等待海边声纳浮标", "浮标或声纳标签可见", "等待并点击主岛活动按钮", location="flows/sonar_page.py · wait_sonar_ready"),
    "entry.button": template("进入活动 · 打开活动列表", "主岛活动按钮可见", "点击所选位置，再按原流程准备网络、滑动列表", location="flows/activity_flow.py · enter_activity_initial"),
    "entry.board": template("进入活动 · 确认棋盘", "棋盘页，退出按钮可见", "按原等待点击安全位置，处理开始提示", location="flows/activity_flow.py · enter_activity_initial"),
    "probe.ready": template("单格探测 · 确认棋盘", "棋盘页，退出按钮可见", "保存 before 截图，随后点击当前目标格", "补充判断当前页面用于诊断，然后报告本发准备失败", "flows/probe_flow.py · prepare_probe_once"),
    "probe.diagnostic": page("单格探测 · 失败页面诊断", "确认刚才页面检查失败时的画面", "记录诊断页面，然后进入原异常恢复", "记录诊断页面，然后进入原异常恢复", "flows/probe_flow.py · prepare_probe_once"),
    "probe.quit": template("单格探测 · 准备退出棋盘", "退出活动按钮可见", "点击所选退出位置，再重新进入活动", location="flows/probe_flow.py · prepare_probe_once"),
    "probe.button": template("单格探测 · 重新打开活动列表", "主岛活动按钮可见", "点击所选位置，按原等待点击活动入口", location="flows/activity_flow.py · reenter_activity_for_probe"),
    "probe.return": template("单格探测 · 确认已返回棋盘", "棋盘页，退出按钮可见", "处理开始提示，再保存 after 截图并判断本格", location="flows/activity_flow.py · reenter_activity_for_probe"),
    "probe.result": PromptText("单格探测 · 判断本格结果", "对照本发前后图片，判断标记格",
        (("hit", "登记 HIT，由原策略校验整艇；随后按本关是否完成选择恢复"),
         ("miss", "登记 MISS；本关未完成时进入原 retry 恢复"),
         ("unopened", "不登记本格结果，进入原异常恢复"),
         ("unknown", "不登记本格结果，进入原异常恢复")), "flows/auto_probe_flow.py · run_auto_probe_once"),
    "retry": template("MISS 恢复 · 等待重试按钮", "retry 按钮可见", "关闭 REJECT，按原等待点击所选 retry 位置，再恢复活动", "关闭 REJECT，报告重试等待失败并进入原异常恢复", "flows/auto_probe_recovery.py · wait_retry_with_failure_capture"),
    "hit.final": page("HIT 恢复 · 复查棋盘", "棋盘页面，DROP 开启且 REJECT 关闭", "继续核验网络，通过后选择下一格", "报告 HIT 恢复失败，进入原异常恢复", "flows/auto_probe_recovery.py · recover_after_hit_once"),
    "miss.final": page("MISS 恢复 · 复查棋盘", "棋盘页面，DROP 开启且 REJECT 关闭", "继续核验网络，通过后选择下一格", "报告 MISS 恢复失败，进入原异常恢复", "flows/auto_probe_recovery.py · recover_after_miss_once"),
    "done.final": page("本关完成 · 记录当前页面", "当前页面类型，可能已出现结算", "记录页面与网络状态，返回后进入胜利检查", "记录页面与网络状态，返回后进入胜利检查", "flows/auto_probe_recovery.py · _recover_after_strategy_done_once"),
    "restart.final": page("异常恢复 · 复查棋盘", "棋盘页面，DROP 开启且 REJECT 关闭", "继续核验网络，通过后按原进度继续本发", "本次恢复失败，由原重启额度决定后续处理", "flows/auto_probe_exception_recovery.py · restart_auto_probe_once"),
    "victory.first": template("胜利处理 · 首次检查胜利画面", "胜利画面可见", "按原间隔点击两次安全位置，再检查胜利画面", "报告胜利等待失败，结束本次循环", "flows/victory_flow.py · handle_victory_transition"),
    "victory.followup": template("胜利处理 · 后续检查胜利画面", "判断胜利画面是否仍在", "未达原处理上限则再处理一轮；已达上限则报告失败", "继续等待下一关棋盘的退出按钮", "flows/victory_flow.py · handle_victory_transition"),
    "victory.next": template("胜利处理 · 确认下一关", "下一关棋盘的退出按钮可见", "完成本关结算；未停止且未达关数上限时创建下一关", "报告下一关页面等待失败，结束本次循环", "flows/victory_flow.py · handle_victory_transition"),
}
ACTIONS = {
    "weak_on": "正在开启 DROP 弱网规则",
    "weak_off": "正在关闭 DROP 弱网规则",
    "reject_on": "正在开启 REJECT 断网规则",
    "reject_off": "正在关闭 REJECT 断网规则",
    "restore": "正在恢复网络",
    "network_query": "正在读取真实网络状态",
    "wait": "正在按原流程等待 {seconds:g} 秒",
    "click": "正在发送点击命令：{point}",
    "swipe": "正在滑动画面并等待响应",
    "recognize": "正在截图并计算自动识别参考",
    "before": "正在保存本发 before 截图",
    "after": "正在保存本发 after 截图",
    "reference": "正在计算本发自动识别参考（含原规则需要的补帧）",
    "commit": "正在登记人工结果并同步棋盘、策略和计数",
    "restart": "正在按原异常恢复流程重启游戏",
    "next": "正在按原策略选择下一格",
}

def prompt_text(key, kind, label, needs_position=False):
    if key in PROMPTS:
        return PROMPTS[key]
    if kind == "page":
        return page("判断当前页面", "当前页面类型", "返回此页面类型，由当前调用位置继续处理", "返回此页面类型，由当前调用位置继续处理", "flows/sonar_page.py · detect_sonar_page_state")
    name = label.removeprefix("查找").removeprefix("等待")
    return template(label, name + "可见", "返回找到与所选位置，由调用方继续处理" if needs_position else "返回找到，由调用方继续处理", "返回未找到，由调用方继续处理")

def preview(request, value):
    return dict(request.continuations).get(value, "请选择本次判断，再确认继续")
