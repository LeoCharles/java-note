"""12 | 主图：路由 → 子 Agent → 审批 → 执行 → 转人工。

对应文档：12-实战-智能客服工单Agent.md 第七、八、九、十章

图长这样：

    START → triage ─┬─→ order ────────────────────────────→ END
                    ├─→ product ──────────────────────────→ END
                    ├─→ after_sale ─┬─→ approval ─┬─→ execute → END
                    │               │             └─→ reject  → END
                    │               └─→ END
                    └─→ escalate ────────────────────────→ END

两个容易踩的坑，代码里都标了：

  ① interrupt 恢复时节点从头重跑
     → approval_node 里 interrupt 之前只能有只读操作
     → 真正的写在 execute_node，在 interrupt 之后，并且带幂等键

  ② 子 Agent 想让主图跳转，要输出「决策结构」而不是自然语言 + 魔法标记
     → AfterSaleDecision 是 Pydantic 模型，action 拼错会直接报错
     → 用 additional_kwargs 塞标记的做法会静默失效
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Literal, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

import domain
import guard
import routing
from common import get_model, get_small_model
from tools import AFTER_SALE_TOOLS, ORDER_TOOLS, PRODUCT_TOOLS


# ============ 状态 ============

class CSState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    ticket_no: str
    intent: str
    order_no: str | None
    urgency: str
    need_human: bool
    resolved: bool
    refund_reason: str | None
    approval: dict | None
    # 事实台账：本轮所有工具返回。出站质检拿它核对数字
    facts: Annotated[list[str], lambda a, b: a + b]


# ============ 小工具 ============

def _new_messages(before: list, after: list) -> list:
    """子 Agent 只返回增量消息（避免 message 膨胀，见文档 09）。

    子 Agent 是把父图的消息原样传进去的，所以 after 的前 len(before) 条
    应该就是 before。但不同版本的 create_agent 可能做裁剪，
    所以这里做一次校验：对不上就退化成「只取最后一条 AI 消息」。
    """
    if len(after) > len(before) and after[:len(before)] == before:
        return after[len(before):]
    return after[-1:] if after else []


def _last_ai_text(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, AIMessage) and (m.content or "").strip():
            return m.content
    return ""


def _tool_facts(messages: list) -> list[str]:
    import json
    out = []
    for m in messages:
        if isinstance(m, ToolMessage):
            c = m.content
            out.append(c if isinstance(c, str) else json.dumps(c, ensure_ascii=False))
    return out


# ============ 金额三档策略 ============

AUTO_LIMIT = 200          # ≤ 200          自动执行
AUTO_REVIEW_LIMIT = 2000  # 200 < x ≤ 2000 规则初审
#                         # > 2000         必须人工审批（interrupt）


def auto_review(order: dict, reason: str, user_id: str) -> tuple[bool, str]:
    """规则初审。纯函数、只读 —— 可以安全地放在 interrupt 之前。

    规则能覆盖 80% 的情况。模型只用在「规则边界模糊但金额可控」的地方。
    """
    if order["amount"] <= AUTO_LIMIT:
        return True, "小额自动通过"

    recent = domain._refund_attempts_recent(user_id, days=30)
    if recent >= 3:
        return False, f"近 30 天已申请 {recent} 次退款，需人工审核"

    if reason == "质量问题":
        if order["amount"] <= AUTO_REVIEW_LIMIT:
            return True, "质量问题，金额在自动审核范围内"
        return False, f"金额 {order['amount']} 元超过 {AUTO_REVIEW_LIMIT} 元，需人工审核"

    if reason == "七天无理由" and order["status"] == "已完成" and order["completed_at"]:
        days = (date.today() - datetime.fromisoformat(order["completed_at"]).date()).days
        if days > 7:
            return False, f"已超出七天无理由期限（{days} 天）"

    if order["amount"] <= AUTO_REVIEW_LIMIT:
        return True, "金额在自动审核范围内"

    return False, f"金额 {order['amount']} 元超过 {AUTO_REVIEW_LIMIT} 元，需人工审核"


# ============ 提示词 ============

ORDER_PROMPT = """你是订单助手，只处理：订单查询、物流进度、退款进度查询。
不处理退款申请、换货、产品咨询 —— 那些有别人负责。

规则：
1. 用户没给订单号就先问，不要猜。
2. 查不到就说查不到，不要反复换号试。
3. 工具返回的数字（金额、单号、时间）必须原样引用，不要改写。
4. 回答控制在 100 字以内。
"""

AFTER_SALE_PROMPT = """你是售后助手，负责了解情况、查询订单，然后给出处理建议。
你没有执行退款的权限 —— 是否退款由系统审批流程决定。

规则：
1. 先查订单，拿到 can_refund / can_cancel。不满足条件就如实说明原因。
2. 退款金额由系统计算，你绝不要报价、绝不承诺赔偿。
3. 不要在回复里说「已为您退款」，你只能「提交申请」。
4. 信息够了就给出结论；信息不够就先追问。
"""

PRODUCT_PROMPT = """你是产品顾问，只回答产品参数、功能、使用方法。不处理订单和售后。

规则：
1. 只依据工具返回的资料回答。
2. 没有资料就说没有，建议看商品详情页。
3. 不评价竞品。
"""


# ============ 子 Agent ============

class AfterSaleDecision(BaseModel):
    """子 Agent 的「决策结构」。主图根据它跳转，而不是猜自然语言。"""
    action: Literal["answer", "submit_refund", "escalate"] = Field(
        description="answer=直接回答用户；submit_refund=用户已明确要退款且订单可退；"
                    "escalate=需要人工介入"
    )
    order_no: str | None = Field(default=None, description="涉及的订单号")
    reason: Literal["七天无理由", "质量问题", "发错货", "少件漏发", "其他"] | None = Field(
        default=None, description="退款原因，action=submit_refund 时必填"
    )
    reply: str = Field(description="给用户的回复。action=answer 时是最终回答；"
                                   "submit_refund 时是「正在为您提交」之类")


DECISION_PROMPT = """根据下面的对话，判断售后助手下一步该做什么。

- 用户只是咨询/问进度 → answer
- 用户明确要求退款，且订单 can_refund=true → submit_refund（原因必填）
- 订单不能退、需要特殊权限、用户情绪激动 → escalate

对话：
{history}
"""


def _make_readonly_node(name: str, tools: list, prompt: str):
    """只读子 Agent：跑完直接结束。"""
    from langchain.agents import create_agent

    agent = create_agent(model=get_model(), tools=tools,
                         system_prompt=prompt, name=name)

    async def node(state: CSState, config
                   ) -> Command[Literal["escalate", "__end__"]]:
        out = await agent.ainvoke({"messages": state["messages"]}, config)
        new = _new_messages(state["messages"], out["messages"])

        text = _last_ai_text(new) or "抱歉，我这边没有查到进一步的信息。"
        clean, violations = guard.scrub(text)

        need_human = any(v.kind in ("commitment", "liability") for v in violations)
        if need_human:
            return Command(goto="escalate", update={
                "messages": [AIMessage(clean)],
                "facts": _tool_facts(new),
                "need_human": True,
            })
        return Command(goto=END, update={
            "messages": [AIMessage(clean)],
            "facts": _tool_facts(new),
            "resolved": True,
        })

    return node


def make_after_sale_node():
    """售后：两阶段 —— 先查（工具），再决策（结构化输出），最后交给主图。"""
    from langchain.agents import create_agent

    agent = create_agent(model=get_model(), tools=AFTER_SALE_TOOLS,
                         system_prompt=AFTER_SALE_PROMPT,
                         name="after_sale_agent")
    decision_llm = get_small_model().with_structured_output(AfterSaleDecision)

    async def node(state: CSState, config
                   ) -> Command[Literal["approval", "escalate", "__end__"]]:
        # 阶段 1：只读工具（查订单、查退款进度）
        out = await agent.ainvoke({"messages": state["messages"]}, config)
        new = _new_messages(state["messages"], out["messages"])
        facts = _tool_facts(new)

        # 阶段 2：让模型输出决策结构
        history = "\n".join(
            f"{'用户' if getattr(m, 'type', '') == 'human' else '售后'}："
            f"{m.content if isinstance(m.content, str) else ''}"
            for m in [*state["messages"], *new]
            if (m.content if isinstance(m.content, str) else "").strip()
        )[-3000:]

        decision = await decision_llm.ainvoke(
            DECISION_PROMPT.format(history=history)
        )

        if decision.action == "submit_refund" and decision.order_no:
            # 工单状态先落到 pending_approval —— 这一步在本节点里做，不在 approval_node
            # 里做，因为 approval_node 在 interrupt 之后会被重跑，重复写事件。
            _safe_transition(state.get("ticket_no"), "pending_approval",
                             "request_approval", actor="ai:agent")
            return Command(goto="approval", update={
                "messages": [AIMessage(decision.reply or "正在为您提交退款申请，请稍候…")],
                "order_no": decision.order_no,
                "refund_reason": decision.reason or "其他",
                "facts": facts,
            })

        if decision.action == "escalate":
            return Command(goto="escalate", update={
                "messages": [AIMessage(decision.reply or "我帮您转接人工处理。")],
                "facts": facts,
                "need_human": True,
            })

        clean, violations = guard.scrub(decision.reply)
        return Command(goto=END, update={
            "messages": [AIMessage(clean)],
            "facts": facts,
            "resolved": True,
        })

    return node


# ============ triage：规则 → 模型 ============

async def triage(state: CSState, config
                 ) -> Command[Literal["order", "product", "after_sale",
                                     "escalate"]]:
    """先规则、后模型。规则能确定的场景不要花一次模型调用。"""
    last = state["messages"][-1].content or ""

    # 每轮会话一张工单（同一 thread 复用）
    # ⚠️ thread_id 在 config 里，不在 state 里 —— 它是运行时上下文，不是业务数据
    tid = config["configurable"]["thread_id"]
    if not state.get("ticket_no"):
        t = domain.create_ticket(
            thread_id=tid,
            user_id=config["configurable"]["user_id"],
            category="other", order_no=None, priority="normal",
            ai_summary=None,
        )
        ticket_no = t["ticket_no"]
    else:
        ticket_no = state["ticket_no"]

    if routing.force_human(last) or routing.explicit_human(last):
        return Command(goto="escalate", update={
            "ticket_no": ticket_no,
            "intent": "complaint", "need_human": True, "urgency": "high",
            "messages": [AIMessage("我理解了，马上为您转接人工客服。")],
        })

    r = routing.rule_route(last)
    if r:
        return Command(goto=r, update={"ticket_no": ticket_no,
                                       "intent": r, "urgency": "normal"})

    route = await routing.route_intent(last, get_small_model())
    update = {"ticket_no": ticket_no, "intent": route.intent,
              "order_no": route.order_no, "urgency": route.urgency}

    if route.urgency == "high" or route.intent == "complaint":
        return Command(goto="escalate", update={
            **update, "need_human": True,
            "messages": [AIMessage("我理解了，马上为您转接人工客服。")]})

    if route.intent == "other":
        return Command(goto="escalate", update={
            **update, "need_human": True,
            "messages": [AIMessage("这个问题需要更专业的人来帮您，正在转接人工。")]})

    return Command(goto=route.intent, update=update)


# ============ 审批 ============

def approval_node(state: CSState, config) -> dict:
    """三档审批。

    ⚠️ interrupt 恢复时本节点从头重跑 —— 所以这里所有操作都必须只读。
       工单状态变更也放在这里会重复写事件，所以只做判定。
    """
    order_no = state.get("order_no") or ""
    user_id = config["configurable"]["user_id"]
    view = domain.pending_order_view(order_no)

    if not view:
        return {"approval": {"approved": False, "by": "system",
                             "reason": "订单不存在"}}

    if not view["can_refund"]:
        return {"approval": {"approved": False, "by": "system",
                             "reason": f"订单状态「{view['status']}」不支持退款"}}

    passed, reason = auto_review(view, state.get("refund_reason") or "其他", user_id)

    if passed:
        return {"approval": {"approved": True, "by": "auto", "reason": reason}}

    # 需要人工 → 真的暂停（进程可退出、可跨天）
    decision = interrupt({
        "type": "refund_approval",
        "ticket_no": state.get("ticket_no"),
        "order_no": order_no,
        "amount": view["amount"],
        "reason": state.get("refund_reason"),
        "auto_reason": reason,
        "user": user_id,
    })

    return {"approval": {
        "approved": bool(decision.get("approved")),
        "by": decision.get("operator", "human"),
        "reason": decision.get("comment", ""),
    }}


def route_approval(state: CSState) -> Literal["execute", "reject"]:
    return "execute" if (state.get("approval") or {}).get("approved") else "reject"


def execute_node(state: CSState, config) -> dict:
    """真正的写操作。在 interrupt 之后，且带幂等键。"""
    order_no = state["order_no"] or ""
    user_id = config["configurable"]["user_id"]
    reason = state.get("refund_reason") or "其他"
    approval = state.get("approval") or {}

    code, body = domain.api_create_refund(
        order_no=order_no, user_id=user_id, reason=reason,
        remark=f"审批人：{approval.get('by')}；{approval.get('reason') or ''}",
        session=config["configurable"]["thread_id"],
        idempotency_key=f"refund:{order_no}",         # ← 幂等键
    )

    if code == 409:
        return {
            "messages": [AIMessage(
                f"该订单已有退款申请（单号 {body.get('refundId')}，"
                f"金额 {body.get('amount')} 元），无需重复提交。")],
            "resolved": True,
        }
    if code != 200:
        return {
            "messages": [AIMessage(
                f"退款提交失败：{body.get('message', '系统异常')}。已为您转人工处理。")],
            "need_human": True,
        }

    domain.audit(actor="ai:approval", action="apply_refund", user_id=user_id,
                 ticket_no=state.get("ticket_no"),
                 args={"order_no": order_no, "reason": reason,
                       "approved_by": approval.get("by")},
                 result={"refund_id": body["refund_id"], "amount": body["amount"]})

    _safe_transition(state.get("ticket_no"), "approved", "execute_refund")
    _safe_transition(state.get("ticket_no"), "executing", "executing")
    _safe_transition(state.get("ticket_no"), "resolved", "resolved")

    return {
        "messages": [AIMessage(
            f"退款申请已提交。退款金额 {body['amount']} 元，"
            f"单号 {body['refund_id']}，预计 3 个工作日内原路退回。")],
        "resolved": True,
    }


def _safe_transition(ticket_no: str | None, to: str, action: str = "",
                     actor: str = "ai:approval") -> None:
    if not ticket_no:
        return
    try:
        domain.transition(ticket_no, to, actor=actor, action=action)
    except domain.InvalidTransition as e:
        # 状态机不允许的流转不该让主流程崩，但必须留痕
        domain.audit(actor=actor, action="invalid_transition", user_id="-",
                     ticket_no=ticket_no,
                     args={"to": to, "action": action},
                     result={"error": str(e)})


def reject_node(state: CSState) -> dict:
    approval = state.get("approval") or {}
    reason = approval.get("reason") or "未通过审核"

    tn = state.get("ticket_no")
    if tn:
        # 防御：正常路径下 after_sale 已经把工单推到 pending_approval。
        # 万一没有（比如从别处直接进了 approval），先补上这一步，
        # 否则 ai_handling -> rejected 会被状态机拒绝，工单卡在中间态。
        cur = domain.TICKETS.get(tn, {}).get("status")
        if cur == "ai_handling":
            _safe_transition(tn, "pending_approval", "approval_requested",
                             actor="ai:agent")
        _safe_transition(tn, "rejected", "reject")

    return {"messages": [AIMessage(
        f"您的退款申请未通过：{reason}。如有疑问，我可以帮您转人工。")]}


# ============ 转人工 ============

HANDOFF_PROMPT = """根据下面的对话，生成一份给人工客服的交接摘要。

要求：
- problem：用户的核心诉求，一句话
- attempted：AI 已经做了什么（调用了哪些工具、得到什么结论）
- key_facts：订单号、金额、状态等关键事实
- blocker：为什么 AI 解决不了
- suggested_action：建议人工怎么处理
- sentiment：calm / anxious / angry

对话：
{history}
"""


class HandoffSummary(BaseModel):
    problem: str = Field(description="用户的核心诉求，一句话")
    attempted: list[str] = Field(description="AI 已经做了什么")
    key_facts: dict = Field(description="关键事实：订单号、金额、状态")
    blocker: str = Field(description="为什么 AI 解决不了")
    suggested_action: str = Field(description="建议人工如何处理")
    sentiment: Literal["calm", "anxious", "angry"] = Field(description="用户情绪")


def _format_history(messages: list) -> str:
    role = {"human": "用户", "ai": "客服", "system": "系统", "tool": "工具"}
    lines = []
    for m in messages[-12:]:
        r = role.get(getattr(m, "type", ""), "其他")
        c = m.content if isinstance(m.content, str) else str(m.content)
        if c.strip():
            lines.append(f"{r}：{c[:300]}")
    return "\n".join(lines)


async def escalate_node(state: CSState, config) -> dict:
    try:
        s = await get_small_model().with_structured_output(HandoffSummary).ainvoke(
            HANDOFF_PROMPT.format(history=_format_history(state["messages"]))
        )
        summary = s.model_dump()
    except Exception as e:
        # 摘要失败不能阻断转人工 —— 转人工本身就是兜底
        print(f"    [warn] 交接摘要生成失败：{type(e).__name__}")
        summary = {
            "problem": (state["messages"][-1].content or "") if state["messages"] else "",
            "attempted": [],
            "key_facts": {"order_no": state.get("order_no")},
            "blocker": "AI 生成摘要失败，请人工查看完整对话",
            "suggested_action": "人工接手",
            "sentiment": "anxious",
        }

    t = domain.create_ticket(
        thread_id=config["configurable"]["thread_id"],
        user_id=config["configurable"]["user_id"],
        category=state.get("intent") or "other",
        order_no=state.get("order_no"),
        priority="urgent" if state.get("urgency") == "high" else "high",
        ai_summary=summary,
        ai_handled=False,
    )
    _safe_transition(t["ticket_no"], "escalated", "escalate")

    return {
        "messages": [AIMessage(
            f"已为您转接人工客服，工单号 {t['ticket_no']}。"
            f"客服已经了解您的情况，会尽快联系您。")],
        "ticket_no": t["ticket_no"],
        "need_human": True,
    }


# ============ 建图 ============

def build(saver=None):
    b = StateGraph(CSState)

    b.add_node("triage", triage)
    b.add_node("order", _make_readonly_node("order_agent", ORDER_TOOLS, ORDER_PROMPT))
    b.add_node("product", _make_readonly_node("product_agent", PRODUCT_TOOLS, PRODUCT_PROMPT))
    b.add_node("after_sale", make_after_sale_node())
    b.add_node("approval", approval_node)
    b.add_node("execute", execute_node)
    b.add_node("reject", reject_node)
    b.add_node("escalate", escalate_node)

    b.add_edge(START, "triage")
    # triage 用 Command 去 order / product / after_sale / escalate
    # after_sale 用 Command 去 approval / escalate / END
    b.add_conditional_edges("approval", route_approval,
                            {"execute": "execute", "reject": "reject"})
    b.add_edge("execute", END)
    b.add_edge("reject", END)
    b.add_edge("escalate", END)

    return b.compile(checkpointer=saver)


def build_config(thread_id: str, user_id: str, trace_id: str = "trace-demo",
                 tenant: str = "default", recursion_limit: int = 15) -> dict:
    return {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "trace_id": trace_id,
            "tenant": tenant,
        },
        "recursion_limit": recursion_limit,
    }


__all__ = ["CSState", "build", "build_config", "approval_node",
           "AfterSaleDecision", "HandoffSummary", "auto_review",
           "AUTO_LIMIT", "AUTO_REVIEW_LIMIT"]
