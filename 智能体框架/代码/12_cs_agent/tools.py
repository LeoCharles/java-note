"""12 | 工具层：安全规则真正落地的地方。

对应文档：12-实战-智能客服工单Agent.md 第五、六章

四条铁律，看代码时对照着找：

  ① 身份从 config 取，绝不从工具参数取     → _ctx(config)
  ② 金额由服务端算，工具不接受金额参数        → apply_refund 没有 amount
  ③ 写操作必须带幂等键                    → Idempotency-Key
  ④ 错误必须分类，并且带 hint              → 每个 return 里都有一句告诉模型下一步怎么做的话

另外：每个工具都返回「结构化 dict」，不是自然语言。
   模型读到 {"success": false, "error": "...", "hint": "..."} 才知道下一步怎么走。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

import domain


# ============ 上下文：身份的唯一起点 ============

def _ctx(config: RunnableConfig) -> dict:
    """从 config 里拿身份。

    ⚠️ RunnableConfig 由服务端注入（从登录态来），模型改不了。
       如果把 user_id 写成工具参数，模型就能「扮演」别人 —— 这是最经典的越权漏洞。
    """
    c = (config or {}).get("configurable", {})
    return {
        "user_id": c.get("user_id", ""),
        "thread_id": c.get("thread_id", ""),
        "trace_id": c.get("trace_id", ""),
        "tenant": c.get("tenant", "default"),
    }


# ============ 查询类工具 ============

@tool
def get_order_detail(order_no: str, config: RunnableConfig) -> dict:
    """查询订单详情：状态、金额、商品、物流、是否能退款/取消/改地址。

    用户询问订单进度、物流、金额、退款条件时使用。
    只能查询当前用户自己的订单。
    """
    ctx = _ctx(config)
    code, body = domain.api_get_order(order_no, ctx["user_id"])

    if code == 404:
        return {"success": False, "error": f"订单 {order_no} 不存在",
                "hint": "请与用户核对订单号，不要反复尝试其他号码。"}
    if code == 403:
        # 注意话术：不确认「这个订单存在但不属于你」
        return {"success": False, "error": f"订单 {order_no} 不存在",
                "hint": "告知用户无法查询到该订单，建议其登录自己的账号查看。"}
    if code != 200:
        return {"success": False, "error": f"查询失败({code})",
                "hint": "告诉用户系统繁忙，请稍后重试，不要编造订单信息。"}

    return {"success": True, **body}


@tool
def search_orders(keyword: str, config: RunnableConfig) -> dict:
    """按关键词（订单号或商品名）搜索当前用户的订单列表。"""
    ctx = _ctx(config)
    code, body = domain.api_search_orders(ctx["user_id"], keyword)
    if code != 200:
        return {"success": False, "error": f"搜索失败({code})",
                "hint": "告知用户系统繁忙，请稍后重试。"}
    if body["total"] == 0:
        return {"success": True, "total": 0,
                "hint": "未找到订单。直接告诉用户没找到，建议核对关键词或订单号，"
                        "不要反复换词重搜。"}
    return {"success": True, **body}


@tool
def get_product_info(name: str) -> dict:
    """查询产品参数：规格、保修、使用方法。"""
    p = domain.PRODUCTS.get(name)
    if not p:
        # 模糊匹配：用户可能说「耳机」而不是「降噪耳机」
        for k, v in domain.PRODUCTS.items():
            if name in k or k in name:
                return {"success": True, **v}
        return {"success": False, "error": f"未收录产品「{name}」",
                "hint": "如实告知未查到该产品资料，建议用户查看商品详情页或转人工。"}
    return {"success": True, **p}


@tool
def get_refund_status(order_no: str, config: RunnableConfig) -> dict:
    """查询某订单的退款进度。"""
    ctx = _ctx(config)
    code, body = domain.api_get_order(order_no, ctx["user_id"])
    if code != 200:
        return {"success": False, "error": "查询不到该订单",
                "hint": "核对订单号后再试，不要编造退款进度。"}

    r = domain.refund_of(order_no)
    if not r:
        return {"success": True, "has_refund": False,
                "hint": "该订单没有退款申请。询问用户是否需要申请退款。"}
    return {"success": True, "has_refund": True,
            "refund_id": r["refund_id"], "amount": r["amount"],
            "status": r["status"], "reason": r["reason"],
            "created_at": r["created_at"]}


# ============ 写操作类工具 ============

class RefundInput(BaseModel):
    order_no: str = Field(pattern=r"^\d{5,20}$", description="订单号，纯数字")
    reason: Literal["七天无理由", "质量问题", "发错货", "少件漏发", "其他"] = Field(
        description="退款原因，只能从这几个里选"
    )
    remark: str | None = Field(default=None, max_length=200,
                               description="补充说明，可为空")


@tool("apply_refund", args_schema=RefundInput)
def apply_refund(order_no: str, reason: str, remark: str | None,
                 config: RunnableConfig) -> dict:
    """提交退款申请（进入审核流程，不会立即退款）。

    前置条件（全部满足才可调用）：
    1. 已调用 get_order_detail 且 can_refund=true
    2. 用户明确表达了退款意愿
    3. 已向用户说明退款金额（由系统计算，无需询问用户）

    注意：退款金额由系统按订单实付金额自动计算，不要传金额参数。
    """
    ctx = _ctx(config)
    key = f"refund:{order_no}"

    code, body = domain.api_create_refund(
        order_no=order_no, user_id=ctx["user_id"], reason=reason,
        remark=remark, session=ctx["thread_id"], idempotency_key=key,
    )

    if code == 409:
        return {"success": True, "already_exists": True,
                "refund_id": body.get("refundId"),
                "amount": body.get("amount"),
                "message": "该订单已有退款申请，无需重复提交。"}
    if code == 403:
        return {"success": False, "error": "该订单不属于当前用户",
                "hint": "告知用户无法操作他人订单。"}
    if code == 422:
        return {"success": False, "error": body.get("message", "订单不满足退款条件"),
                "hint": "如实告知用户不能退款的原因，不要辩解，不要承诺补偿。"}
    if code == 404:
        return {"success": False, "error": "订单不存在",
                "hint": "与用户核对订单号。"}
    if code != 200:
        return {"success": False, "error": "退款申请提交失败",
                "hint": "告知用户系统暂时无法处理，已创建工单由人工跟进。"}

    domain.audit(actor="ai:agent", action="apply_refund", user_id=ctx["user_id"],
                 args={"order_no": order_no, "reason": reason, "key": key},
                 result={"refund_id": body["refund_id"], "amount": body["amount"]})

    return {
        "success": True,
        "refund_id": body["refund_id"],
        "amount": body["amount"],            # 服务端算的，模型不能改
        "status": body["status"],
        "estimated_days": 3,
        "hint": "告诉用户退款单号和金额，说明进入审核，1-3 个工作日到账。",
    }


class CancelInput(BaseModel):
    order_no: str = Field(pattern=r"^\d{5,20}$")
    reason: str = Field(min_length=1, max_length=100, description="取消原因")


@tool("cancel_order", args_schema=CancelInput)
def cancel_order(order_no: str, reason: str, config: RunnableConfig) -> dict:
    """取消订单（仅待付款/待发货可用）。

    前置条件：已调用 get_order_detail 且 can_cancel=true。
    """
    ctx = _ctx(config)
    code, body = domain.api_cancel_order(order_no, ctx["user_id"], reason)

    if code == 409:
        return {"success": False, "error": body["message"],
                "hint": "让用户重新查询订单状态后再决定，不要反复尝试取消。"}
    if code in (403, 404):
        return {"success": False, "error": "查询不到该订单",
                "hint": "核对订单号。"}
    if code != 200:
        return {"success": False, "error": "取消失败，请转人工",
                "hint": "告知用户系统处理失败，已转人工。"}

    domain.audit(actor="ai:agent", action="cancel_order", user_id=ctx["user_id"],
                 args={"order_no": order_no, "reason": reason}, result=body)
    return {"success": True, **body,
            "hint": "告知用户订单已取消。"}


class AddressInput(BaseModel):
    order_no: str = Field(pattern=r"^\d{5,20}$")
    receiver: str = Field(min_length=1, max_length=20, description="收货人姓名")
    phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="11 位手机号")
    province: str = Field(min_length=2, description="省")
    city: str = Field(min_length=2, description="市")
    district: str = Field(min_length=2, description="区/县")
    detail: str = Field(min_length=5, max_length=100, description="详细地址")


@tool("change_address", args_schema=AddressInput)
def change_address(order_no: str, receiver: str, phone: str, province: str,
                   city: str, district: str, detail: str,
                   config: RunnableConfig) -> dict:
    """修改收货地址（仅待发货状态，每单最多改 2 次）。

    前置条件：已调用 get_order_detail 且 can_change_address=true，
    且用户已确认完整的新地址（省市区 + 详细地址 + 姓名 + 手机号）。
    """
    ctx = _ctx(config)
    addr = {"receiver": receiver, "phone": phone, "province": province,
            "city": city, "district": district, "detail": detail}
    code, body = domain.api_change_address(order_no, ctx["user_id"], addr)

    if code == 422:
        return {"success": False, "error": body["message"],
                "hint": "如实告知用户原因，不要承诺例外。"}
    if code in (403, 404):
        return {"success": False, "error": "查询不到该订单", "hint": "核对订单号。"}
    if code != 200:
        return {"success": False, "error": "修改失败，请转人工", "hint": "转人工处理。"}

    domain.audit(actor="ai:agent", action="change_address", user_id=ctx["user_id"],
                 args={"order_no": order_no, "address": addr}, result=body)
    return {"success": True, **body,
            "hint": "把新地址完整复述一遍让用户确认。"}


# ============ 分组 ============
#
# ⚠️ 注意这里的分法：子 Agent 只拿到**读工具**。
#
#   如果售后子 Agent 手里有 apply_refund，它就会直接退，
#   主图的审批环节形同虚设 —— 这是这类系统最典型的事故来源。
#
#   所以：
#     子 Agent  = 查（get_* / search_*）
#     写操作    = 由主图的 execute_node 在审批之后调用（见 graph.py）
#
#   工具级别的权限隔离是物理的，不是提示词里写一句「不要退款」就有的。

ORDER_TOOLS = [get_order_detail, search_orders, get_refund_status]
AFTER_SALE_TOOLS = [get_order_detail, get_refund_status]   # 只读
PRODUCT_TOOLS = [get_product_info]

WRITE_TOOLS = {"apply_refund", "cancel_order", "change_address"}

ALL_TOOLS = [*ORDER_TOOLS, *AFTER_SALE_TOOLS, *PRODUCT_TOOLS,
             cancel_order, change_address, apply_refund]
