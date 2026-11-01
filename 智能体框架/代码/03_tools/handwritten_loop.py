"""03 | 手写工具调用循环：理解 Agent 的最底层。

对应文档：03-工具调用与结构化输出.md「手写循环」

这个文件可能是整个项目里最重要的一个 —— 它只有 40 行，
但把「Agent 是什么」讲清楚了。强烈建议逐行读、逐行改。

运行：
    python 03_tools/handwritten_loop.py
"""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import (
    AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage,
)
from langchain_core.tools import tool

from common import get_model, print_divider


# ---------- 工具（模拟业务系统） ----------

ORDERS = {
    "12345": {"status": "已发货", "amount": 299.0, "can_refund": True,
              "tracking": "SF1234567890", "items": "电饭锅 x1"},
    "67890": {"status": "已完成", "amount": 1299.0, "can_refund": True,
              "tracking": "YT9876543210", "items": "耳机 x1"},
    "11111": {"status": "待付款", "amount": 99.0, "can_refund": False,
              "tracking": None, "items": "数据线 x2"},
}

REFUNDS: dict[str, dict] = {}          # 幂等：order_no -> refund


@tool
def get_order(order_no: str) -> str:
    """查询订单详情：状态、金额、物流、是否可退款。"""
    o = ORDERS.get(order_no)
    if not o:
        return json.dumps({
            "success": False,
            "error": f"订单 {order_no} 不存在",
            "hint": "请与用户核对订单号，不要反复尝试其他号码。",
        }, ensure_ascii=False)
    return json.dumps({"success": True, "order_no": order_no, **o}, ensure_ascii=False)


@tool
def apply_refund(order_no: str, reason: str) -> str:
    """申请退款。前置条件：已查询订单且 can_refund 为 true，且用户明确要求退款。"""
    o = ORDERS.get(order_no)
    if not o:
        return json.dumps({"success": False, "error": "订单不存在"}, ensure_ascii=False)
    if not o["can_refund"]:
        return json.dumps({"success": False,
                           "error": f"订单状态为「{o['status']}」，不支持退款",
                           "hint": "如实告知用户原因，不要承诺补偿。"},
                          ensure_ascii=False)
    if order_no in REFUNDS:                       # 幂等
        return json.dumps({"success": True, "already_exists": True,
                           "refund_id": REFUNDS[order_no]["refund_id"]},
                          ensure_ascii=False)

    rid = f"RF{len(REFUNDS) + 1001}"
    REFUNDS[order_no] = {"refund_id": rid, "amount": o["amount"]}
    return json.dumps({"success": True, "refund_id": rid, "amount": o["amount"],
                       "status": "待审核", "estimated_days": 3},
                      ensure_ascii=False)


TOOLS = [get_order, apply_refund]
TOOL_MAP = {t.name: t for t in TOOLS}


# ---------- 核心：手写的 Agent 循环 ----------

def run_with_tools(
    model,
    tools: list,
    user_input: str,
    max_steps: int = 6,
    verbose: bool = True,
) -> tuple[str, list[BaseMessage]]:
    """手写 ReAct 循环。

    三个关键点：
    1. 每轮都把「完整历史」发给模型
    2. 模型返回 tool_calls → 执行 → 追加 ToolMessage → 再问
    3. 模型返回纯文本（没有 tool_calls）→ 结束
    """
    bound = model.bind_tools(tools)
    messages: list[BaseMessage] = [
        SystemMessage(
            "你是售后助手。规则：\n"
            "1. 涉及订单状态必须先调用 get_order\n"
            "2. 退款前必须确认 can_refund=true 且用户明确要求\n"
            "3. 工具返回失败时如实告知，不要编造\n"
            "4. 回答不超过 100 字"
        ),
        HumanMessage(user_input),
    ]

    for step in range(1, max_steps + 1):
        if verbose:
            print(f"\n  ── 第 {step} 步 ──")

        ai: AIMessage = bound.invoke(messages)
        messages.append(ai)                       # ⚠️ 一定要 append，否则模型失忆

        if not ai.tool_calls:
            if verbose:
                print("  [模型] 可以回答了，结束循环")
            return ai.content, messages

        if verbose:
            print(f"  [模型] 请求调用 {len(ai.tool_calls)} 个工具")

        for tc in ai.tool_calls:
            name, args, call_id = tc["name"], tc["args"], tc["id"]
            if verbose:
                print(f"    → {name}({json.dumps(args, ensure_ascii=False)})")

            fn = TOOL_MAP.get(name)
            if fn is None:
                content = json.dumps({"success": False,
                                      "error": f"未知工具 {name}"}, ensure_ascii=False)
            else:
                try:
                    out = fn.invoke(args)
                    content = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
                except Exception as e:
                    # 关键：把错误喂回给模型，让它自己调整
                    content = json.dumps({
                        "success": False,
                        "error": f"工具执行异常：{type(e).__name__}: {e}",
                        "hint": "检查参数格式，或告知用户系统异常。",
                    }, ensure_ascii=False)

            if verbose:
                preview = content if len(content) < 120 else content[:120] + "…"
                print(f"    ← {preview}")

            messages.append(ToolMessage(content=content, tool_call_id=call_id))

    # 超过最大步数
    if verbose:
        print(f"  [警告] 达到最大步数 {max_steps}，强制结束")
    return "这个请求比较复杂，已为您转接人工客服。", messages


# ---------- 演示 ----------

def show_trace(messages: list[BaseMessage]) -> None:
    print("\n  【完整轨迹】")
    for i, m in enumerate(messages):
        t = m.type
        if t == "system":
            continue
        if t == "human":
            print(f"   {i:02d} [用户] {m.content}")
        elif t == "ai":
            if getattr(m, "tool_calls", None):
                for tc in m.tool_calls:
                    print(f"   {i:02d} [模型→工具] {tc['name']}({tc['args']})")
            else:
                print(f"   {i:02d} [模型] {m.content}")
        elif t == "tool":
            body = str(m.content)
            print(f"   {i:02d} [工具] {body[:100]}{'…' if len(body) > 100 else ''}")


def main() -> None:
    model = get_model()

    cases = [
        ("简单查询", "我的订单 12345 到哪了？"),
        ("先查后退", "订单 12345 有问题，我要退款"),
        ("不存在的订单", "订单 99999 现在什么状态"),
        ("不可退款", "订单 11111 我要退款"),
    ]

    for title, q in cases:
        print_divider(f"场景：{title}")
        print(f"  用户：{q}")
        answer, msgs = run_with_tools(model, TOOLS, q, max_steps=6)
        print(f"\n  最终回答：{answer}")
        show_trace(msgs)

    print_divider("验证幂等：同一订单退款两次")
    REFUNDS.clear()
    _, _ = run_with_tools(model, TOOLS, "订单 12345 退款", max_steps=4, verbose=False)
    _, _ = run_with_tools(model, TOOLS, "再给订单 12345 退一次", max_steps=4, verbose=False)
    print(f"  实际退款记录数：{len(REFUNDS)}（应为 1）")

    print_divider("小结")
    print("  · Agent 循环 = while + tool_calls 判断，没有魔法")
    print("  · 每轮必须把完整 messages 传给模型（含 ToolMessage）")
    print("  · 工具错误要喂回模型，让它自己调整，而不是直接崩溃")
    print("  · 必须有 max_steps，防止死循环")
    print("  · 第 06 篇的 create_agent 就是这个循环 + 记忆 + 流式 + 中间件")


if __name__ == "__main__":
    main()
