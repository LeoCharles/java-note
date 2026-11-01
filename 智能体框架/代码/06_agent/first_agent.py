"""06 | 第一个 Agent：create_agent 十分钟跑起来。

对应文档：06-第一个Agent与ReAct循环.md

运行：
    python 06_agent/first_agent.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.tools import tool

from common import get_model, print_divider


# ---------- 工具 ----------

ORDERS = {
    "12345": {"status": "已发货", "amount": 299.0, "can_refund": True,
              "tracking": "SF1234567890"},
    "67890": {"status": "已完成", "amount": 1299.0, "can_refund": True,
              "tracking": "YT9876543210"},
}

REFUNDS: dict[str, dict] = {}


@tool
def get_order_detail(order_no: str) -> dict:
    """查询订单详情：状态、金额、物流、是否能退款。

    用户询问订单进度、物流、金额、退款条件时使用。
    不适用于查询订单列表。
    """
    o = ORDERS.get(order_no)
    if not o:
        return {"success": False, "error": f"订单 {order_no} 不存在",
                "hint": "请与用户核对订单号，不要反复尝试其他号码。"}
    return {"success": True, "order_no": order_no, **o}


@tool
def apply_refund(order_no: str, reason: str) -> dict:
    """申请退款（进入审核，不会立即到账）。

    前置条件（全部满足才可调用）：
    1. 已调用 get_order_detail 且 can_refund=true
    2. 用户明确要求退款

    退款金额由系统按订单实付金额自动计算，不要传金额。
    """
    o = ORDERS.get(order_no)
    if not o:
        return {"success": False, "error": "订单不存在"}
    if not o["can_refund"]:
        return {"success": False, "error": f"订单状态为「{o['status']}」，不支持退款",
                "hint": "如实告知用户原因，不要承诺补偿。"}
    if order_no in REFUNDS:
        return {"success": True, "already_exists": True,
                "refund_id": REFUNDS[order_no]["refund_id"]}

    rid = f"RF{len(REFUNDS) + 1001}"
    REFUNDS[order_no] = {"refund_id": rid, "amount": o["amount"]}
    return {"success": True, "refund_id": rid, "amount": o["amount"], "status": "待审核"}


@tool
def search_orders(keyword: str) -> dict:
    """按关键词搜索订单列表。"""
    items = [{"order_no": k, "status": v["status"], "amount": v["amount"]}
             for k, v in ORDERS.items()]
    if not items:
        return {"success": True, "total": 0,
                "hint": "未找到订单，直接告诉用户即可，不要反复换关键词重搜。"}
    return {"success": True, "total": len(items), "items": items}


TOOLS = [get_order_detail, apply_refund, search_orders]

SYSTEM = """你是售后助手。

【硬性规则】
1. 任何涉及订单状态、物流、金额的问题，必须先调用 get_order_detail。禁止凭记忆回答。
2. 退款前必须确认 can_refund=true 且用户明确要求。
3. 工具返回 success=false 时，如实告知用户，不要编造成功。
4. 回答简洁，不超过 100 字。
"""


def show_trace(messages) -> None:
    print("\n  【决策轨迹】")
    for i, m in enumerate(messages):
        if m.type == "system":
            continue
        if m.type == "human":
            print(f"   {i:02d} [用户] {m.content}")
        elif m.type == "ai":
            if getattr(m, "tool_calls", None):
                for tc in m.tool_calls:
                    print(f"   {i:02d} [模型→工具] {tc['name']}({tc['args']})")
            else:
                print(f"   {i:02d} [模型] {m.content}")
        elif m.type == "tool":
            body = str(m.content)
            print(f"   {i:02d} [工具] {body[:110]}{'…' if len(body) > 110 else ''}")


def main() -> None:
    from langchain.agents import create_agent

    model = get_model()

    agent = create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM,
        name="after_sale_agent",
    )

    cases = [
        "我的订单 12345 到哪了？",
        "订单 12345 有问题，我要退款",
        "订单 99999 现在什么状态？",
        "帮我查下所有订单",
    ]

    for q in cases:
        print_divider(f"用户：{q}")
        result = agent.invoke(
            {"messages": [("user", q)]},
            config={"recursion_limit": 10, "metadata": {"scene": "demo"}},
        )
        print(f"  回答：{result['messages'][-1].content}")
        show_trace(result["messages"])

    print_divider("幂等验证：连续两次退款")
    REFUNDS.clear()
    for q in ["订单 12345 退款", "再给订单 12345 退一次"]:
        r = agent.invoke({"messages": [("user", q)]}, config={"recursion_limit": 10})
        print(f"  {q} -> {r['messages'][-1].content[:80]}")
    print(f"  实际退款记录：{len(REFUNDS)} 条（应为 1）")

    print_divider("小结")
    print("  · create_agent = 模型 ↔ 工具 的循环图，第 07 篇会把它拆开")
    print("  · 一定要设 recursion_limit（生产建议 8-12）")
    print("  · 想看每一步去 with_middleware.py 和 stream_events.py")


if __name__ == "__main__":
    main()
