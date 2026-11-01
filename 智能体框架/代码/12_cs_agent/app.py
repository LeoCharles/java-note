"""12 | FastAPI 服务：SSE 流式 + 审批接口 + 人工工作台。

对应文档：12-实战-智能客服工单Agent.md 第十一、十四章

启动：
    pip install fastapi uvicorn httpx
    python 12_cs_agent/app.py
    # 浏览器打开 http://localhost:8000/docs

接口：
    POST /cs/chat                流式对话（SSE）
    POST /cs/chat/sync           同步对话（调试用）
    GET  /cs/approvals           待审批列表
    GET  /cs/state/{thread_id}   会话状态（是否挂起、挂在哪）
    POST /cs/approve             审批决定
    GET  /workbench/dispatch     人工客服待办
    GET  /audit                  审计日志

⚠️ 这是教学用服务：鉴权用 X-User-Id 头模拟。
   生产上必须是登录态 / 网关签名，绝不能信客户端自称的身份。
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import BaseModel, Field

import domain
from graph import build, build_config

app = FastAPI(title="智能客服 Agent", version="1.0")

# 生产上换成 PostgresSaver（见 08_persistence / 文档 08）
SAVER = InMemorySaver()
GRAPH = build(SAVER)

TOOL_LABELS = {
    "get_order_detail": "正在查询订单…",
    "search_orders": "正在搜索您的订单…",
    "get_refund_status": "正在查询退款进度…",
    "apply_refund": "正在提交退款申请…",
    "cancel_order": "正在取消订单…",
    "change_address": "正在修改收货地址…",
    "get_product_info": "正在查询产品资料…",
}


def humanize(name: str) -> str:
    """工具名不暴露给用户 —— 既是体验问题，也是安全考虑。"""
    return TOOL_LABELS.get(name, "正在处理…")


def sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


# ============ 请求体 ============

class ChatReq(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    thread_id: str | None = None


class ApproveReq(BaseModel):
    thread_id: str
    approved: bool
    comment: str | None = None


# ============ 对话 ============

@app.post("/cs/chat")
async def cs_chat(req: ChatReq, x_user_id: str = Header(default="u1001")):
    """流式对话。前端按 data: {...} 逐行解析。"""
    thread_id = req.thread_id or f"u1001:cs:{uuid.uuid4().hex[:8]}"
    cfg = build_config(thread_id, x_user_id, trace_id=uuid.uuid4().hex)

    async def gen():
        yield sse({"type": "meta", "thread_id": thread_id})
        try:
            async for ev in GRAPH.astream_events(
                {"messages": [("user", req.message)]}, cfg, version="v2"
            ):
                k = ev["event"]
                if k == "on_chat_model_stream":
                    chunk = ev["data"]["chunk"]
                    if c := chunk.content:
                        yield sse({"type": "token", "text": c})
                elif k == "on_tool_start":
                    yield sse({"type": "tool", "name": humanize(ev["name"])})
                elif k == "on_chain_end" and ev["name"] in ("execute", "escalate",
                                                           "reject"):
                    out = ev["data"].get("output") or {}
                    if isinstance(out, dict) and out.get("ticket_no"):
                        yield sse({"type": "ticket",
                                   "ticket_no": out["ticket_no"]})
        except Exception as e:
            print(f"  [error] {type(e).__name__}: {e}")
            yield sse({"type": "error",
                       "message": "系统繁忙，请稍后重试或转人工"})
        finally:
            snap = GRAPH.get_state(cfg)
            if snap.next:
                payload = None
                for t in snap.tasks:
                    for itr in getattr(t, "interrupts", []):
                        payload = itr.value
                yield sse({"type": "interrupt",
                           "thread_id": thread_id,
                           "payload": payload})
            yield sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/cs/chat/sync")
async def cs_chat_sync(req: ChatReq, x_user_id: str = Header(default="u1001")):
    """同步对话，方便 curl / 调试。"""
    thread_id = req.thread_id or f"u1001:cs:{uuid.uuid4().hex[:8]}"
    cfg = build_config(thread_id, x_user_id, trace_id=uuid.uuid4().hex)

    out = GRAPH.invoke({"messages": [("user", req.message)]}, cfg)
    snap = GRAPH.get_state(cfg)

    payload = None
    for t in snap.tasks:
        for itr in getattr(t, "interrupts", []):
            payload = itr.value

    return {
        "thread_id": thread_id,
        "reply": (out.get("messages") or [None])[-1].content
                 if out.get("messages") else None,
        "ticket_no": out.get("ticket_no"),
        "intent": out.get("intent"),
        "need_human": out.get("need_human"),
        "resolved": out.get("resolved"),
        "suspended": bool(snap.next),
        "interrupt": payload,
    }


# ============ 审批 ============

@app.get("/cs/state/{thread_id}")
async def get_state(thread_id: str, x_user_id: str = Header(default="u1001")):
    """检查会话是否挂起、挂在哪个节点。

    ⚠️ 生产上必须校验 thread_id 是否属于当前用户，
       否则 A 用户能看到 B 用户的审批载荷（里面可能有金额、订单号）。
    """
    cfg = build_config(thread_id, x_user_id)
    snap = GRAPH.get_state(cfg)

    payload = None
    for t in snap.tasks:
        for itr in getattr(t, "interrupts", []):
            payload = itr.value

    return {
        "thread_id": thread_id,
        "next": list(snap.next),
        "suspended": bool(snap.next),
        "interrupt": payload,
        "ticket_no": (snap.values or {}).get("ticket_no"),
        "intent": (snap.values or {}).get("intent"),
    }


@app.get("/cs/approvals")
async def list_approvals():
    """待审批列表：扫描所有挂起的会话。

    生产上应该用数据库查（tickets.status='pending_approval'），
    而不是遍历 checkpoint —— 后者在会话量大时很慢。
    """
    out = []
    for t in domain.TICKETS.values():
        if t["status"] in ("pending_approval",):
            out.append(t)
    return {"total": len(out), "items": out}


@app.post("/cs/approve")
async def approve(req: ApproveReq, x_user_id: str = Header(default="admin-001")):
    """审批决定。

    ⚠️ 三件必须做的事，这里简化了：
       ① 校验审批人权限（x_user_id 是不是管理员 / 有没有该金额的审批权）
       ② 校验工单状态确实是 pending_approval（防重复审批）
       ③ 写审批日志（谁批的、什么时候、理由）
    """
    cfg = build_config(req.thread_id, x_user_id)
    snap = GRAPH.get_state(cfg)

    if not snap.next:
        raise HTTPException(400, "该会话没有等待中的审批")

    # 工单状态由主图（execute_node / reject_node）推进，接口层只负责
    # ① 校验权限 ② 记录是谁批的 ③ 把决定送回图里
    ticket_no = (snap.values or {}).get("ticket_no")
    if ticket_no:
        domain.audit(actor=f"human:{x_user_id}", action="approve_decision",
                     user_id=x_user_id, ticket_no=ticket_no,
                     args={"approved": req.approved, "comment": req.comment})

    out = GRAPH.invoke(
        Command(resume={"approved": req.approved, "operator": x_user_id,
                        "comment": req.comment or ""}),
        cfg,
    )

    return {
        "thread_id": req.thread_id,
        "ticket_no": out.get("ticket_no"),
        "reply": (out.get("messages") or [None])[-1].content
                 if out.get("messages") else None,
        "refund": domain.refund_of((snap.values or {}).get("order_no") or ""),
    }


# ============ 人工工作台 ============

@app.get("/workbench/dispatch")
async def dispatch(agent_id: str | None = None):
    """人工客服的待办：按优先级 + 创建时间排序。"""
    rows = domain.list_escalated()
    if agent_id:
        rows = [r for r in rows
                if r["assignee"] in (None, agent_id)]
    return {"total": len(rows), "items": rows}


@app.get("/audit")
async def audit(limit: int = 50):
    return {"items": domain.dump_audit(limit)}


@app.get("/tickets")
async def tickets():
    return {"items": list(domain.TICKETS.values())}


@app.get("/tickets/{ticket_no}/events")
async def ticket_events(ticket_no: str):
    return {"items": [e for e in domain.EVENTS if e["ticket_no"] == ticket_no]}


# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn

    print("""
  ============================================================
    智能客服 Agent 已启动

    API 文档：  http://localhost:8000/docs
    同步对话：  POST /cs/chat/sync
    流式对话：  POST /cs/chat
    待审批：    GET  /cs/approvals
    审批：      POST /cs/approve
    工作台：    GET  /workbench/dispatch

    试试：
      curl -X POST localhost:8000/cs/chat/sync \\
        -H "Content-Type: application/json" \\
        -H "X-User-Id: u1001" \\
        -d '{"message":"订单 12345 到哪了"}'

      # 大额退款 → 返回 suspended=true + interrupt 载荷
      curl -X POST localhost:8000/cs/chat/sync \\
        -H "Content-Type: application/json" \\
        -d '{"message":"订单 22222 我要退款，质量问题"}'

      # 用返回的 thread_id 审批
      curl -X POST localhost:8000/cs/approve \\
        -H "Content-Type: application/json" \\
        -d '{"thread_id":"<上一步的thread_id>","approved":true,"comment":"同意"}'
  ============================================================
""")
    uvicorn.run(app, host="0.0.0.0", port=8000)
