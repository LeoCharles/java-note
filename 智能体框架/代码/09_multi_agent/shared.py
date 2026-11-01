"""09 | 工具即子 Agent + Handoff + Supervisor 三种模式。

对应文档：09-多Agent协作模式.md

运行：
    python 09_multi_agent/tool_subagent.py
    python 09_multi_agent/handoff.py
    python 09_multi_agent/supervisor.py

本文件是三者共用的工具和 Agent 定义。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.tools import tool

from common import get_model


# ============ 模拟业务数据 ============

ORDERS = {
    "12345": {"status": "已发货", "amount": 299.0, "can_refund": True,
              "tracking": "SF1234567890", "items": "电饭锅 x1"},
    "67890": {"status": "已完成", "amount": 1299.0, "can_refund": True,
              "tracking": "YT9876543210", "items": "耳机 x1"},
    "11111": {"status": "待付款", "amount": 99.0, "can_refund": False,
              "tracking": None, "items": "数据线 x2"},
}

PRODUCTS = {
    "电饭锅": {"price": 299, "capacity": "4L", "power": "800W",
               "warranty": "2 年保修"},
    "耳机": {"price": 1299, "type": "降噪入耳式", "battery": "8 小时",
             "warranty": "1 年保修"},
}

REFUNDS: dict[str, dict] = {}


# ============ 工具 ============

@tool
def get_order(order_no: str) -> dict:
    """查询订单详情。"""
    o = ORDERS.get(order_no)
    if not o:
        return {"success": False, "error": f"订单 {order_no} 不存在"}
    return {"success": True, "order_no": order_no, **o}


@tool
def apply_refund(order_no: str, reason: str) -> dict:
    """申请退款。前置条件：is can_refund=true。"""
    o = ORDERS.get(order_no)
    if not o or not o["can_refund"]:
        return {"success": False, "error": "订单不支持退款"}
    if order_no in REFUNDS:
        return {"success": True, "already_exists": True,
                "refund_id": REFUNDS[order_no]["refund_id"]}
    rid = f"RF{len(REFUNDS) + 1001}"
    REFUNDS[order_no] = {"refund_id": rid}
    return {"success": True, "refund_id": rid, "amount": o["amount"]}


@tool
def get_product(name: str) -> dict:
    """查询产品参数。"""
    p = PRODUCTS.get(name)
    if not p:
        return {"success": False, "error": f"未找到产品 {name}"}
    return {"success": True, "name": name, **p}


ORDER_TOOLS = [get_order]
AFTER_SALE_TOOLS = [get_order, apply_refund]
PRODUCT_TOOLS = [get_product]

ORDER_PROMPT = """你是订单专员。负责：订单查询、物流跟踪、取消订单、修改地址。

规则：
1. 必须调用 get_order 查询，不要凭记忆回答。
2. 不处理退款和产品咨询。
3. 回答简洁，不超过 80 字。"""

AFTER_SALE_PROMPT = """你是售后专员。负责：退款、换货、维修。

规则：
1. 退款前必须先调用 get_order 确认 can_refund=true。
2. 用户需明确表达退款意愿。
3. 不处理订单查询和产品咨询。
4. 回答简洁，不超过 80 字。"""

PRODUCT_PROMPT = """你是产品专员。负责：产品功能、参数、使用方法、选购建议。

规则：
1. 涉及具体参数时调用 get_product。
2. 不处理订单和退款。
3. 回答简洁，不超过 100 字。"""


def build_agents():
    from langchain.agents import create_agent

    model = get_model()
    return {
        "order_agent": create_agent(model, ORDER_TOOLS, ORDER_PROMPT,
                                    name="order_agent"),
        "after_sale_agent": create_agent(model, AFTER_SALE_TOOLS,
                                         AFTER_SALE_PROMPT, name="after_sale_agent"),
        "product_agent": create_agent(model, PRODUCT_TOOLS, PRODUCT_PROMPT,
                                      name="product_agent"),
    }
