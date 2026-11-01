"""12 | 客服工单 Agent 的「业务系统」模拟层。

真实项目里这一层是订单服务 / 工单服务的 HTTP 客户端。
这里用内存 + 状态机模拟，**接口形状保持一致**：

    api_* 函数统统返回 (status_code, payload)

这样 tools.py 里处理 403/404/409/422 的代码，换成真的 httpx 调用时
一行都不用改 —— 只有被调用的函数变了。

对应文档：12-实战-智能客服工单Agent.md 第四、五、六章
"""

from __future__ import annotations

import itertools
import threading
from datetime import datetime, timedelta

_lock = threading.Lock()


def now() -> datetime:
    return datetime.now()


# ============ 订单数据 ============

ORDERS: dict[str, dict] = {
    "12345": {
        "order_no": "12345", "user_id": "u1001", "status": "已发货",
        "amount": 299.0, "items": [{"name": "电饭锅", "qty": 1, "price": 299.0}],
        "carrier": "顺丰", "tracking_no": "SF1234567890",
        "latest_track": "已到达上海转运中心",
        "created_at": "2026-10-28", "completed_at": None,
        "address": {"receiver": "张三", "phone": "13800138000",
                    "province": "上海市", "city": "上海市",
                    "district": "浦东新区", "detail": "张江路 1 号"},
        "address_changes": 0,
    },
    "67890": {
        "order_no": "67890", "user_id": "u1001", "status": "已完成",
        "amount": 1299.0, "items": [{"name": "降噪耳机", "qty": 1, "price": 1299.0}],
        "carrier": "圆通", "tracking_no": "YT9876543210",
        "latest_track": "已签收",
        "created_at": "2026-10-20", "completed_at": "2026-10-23",
        "address": {"receiver": "张三", "phone": "13800138000",
                    "province": "上海市", "city": "上海市",
                    "district": "浦东新区", "detail": "张江路 1 号"},
        "address_changes": 0,
    },
    # 大额订单：退款必然触发人工审批
    "22222": {
        "order_no": "22222", "user_id": "u1001", "status": "已发货",
        "amount": 8999.0, "items": [{"name": "笔记本电脑", "qty": 1, "price": 8999.0}],
        "carrier": "京东物流", "tracking_no": "JD0001112222",
        "latest_track": "运输中",
        "created_at": "2026-10-30", "completed_at": None,
        "address": {"receiver": "张三", "phone": "13800138000",
                    "province": "上海市", "city": "上海市",
                    "district": "浦东新区", "detail": "张江路 1 号"},
        "address_changes": 0,
    },
    # 待付款：可取消、可改地址
    "11111": {
        "order_no": "11111", "user_id": "u1001", "status": "待付款",
        "amount": 99.0, "items": [{"name": "数据线 x2", "qty": 2, "price": 49.5}],
        "carrier": None, "tracking_no": None, "latest_track": None,
        "created_at": "2026-11-01", "completed_at": None,
        "address": {"receiver": "张三", "phone": "13800138000",
                    "province": "上海市", "city": "上海市",
                    "district": "浦东新区", "detail": "张江路 1 号"},
        "address_changes": 0,
    },
    # 待发货：可改地址（每单限 2 次）
    "33333": {
        "order_no": "33333", "user_id": "u1001", "status": "待发货",
        "amount": 459.0, "items": [{"name": "空气炸锅", "qty": 1, "price": 459.0}],
        "carrier": None, "tracking_no": None, "latest_track": None,
        "created_at": "2026-11-01", "completed_at": None,
        "address": {"receiver": "张三", "phone": "13800138000",
                    "province": "上海市", "city": "上海市",
                    "district": "浦东新区", "detail": "张江路 1 号"},
        "address_changes": 0,
    },
    # 别人的订单：用来演示越权
    "55555": {
        "order_no": "55555", "user_id": "u2002", "status": "已发货",
        "amount": 199.0, "items": [{"name": "台灯", "qty": 1, "price": 199.0}],
        "carrier": "中通", "tracking_no": "ZT5555555555",
        "latest_track": "派送中",
        "created_at": "2026-10-31", "completed_at": None,
        "address": {"receiver": "李四", "phone": "13900139000",
                    "province": "北京市", "city": "北京市",
                    "district": "朝阳区", "detail": "建国路 2 号"},
        "address_changes": 0,
    },
}

PRODUCTS = {
    "电饭锅": {"name": "电饭锅", "price": 299, "capacity": "4L",
               "power": "800W", "warranty": "2 年保修",
               "usage": "内胆可拆卸清洗，禁止用钢丝球"},
    "降噪耳机": {"name": "降噪耳机", "price": 1299, "type": "主动降噪入耳式",
                 "battery": "单次 8 小时，配合充电盒 32 小时",
                 "warranty": "1 年保修",
                 "usage": "长按右耳 2 秒切换降噪/通透模式"},
    "笔记本电脑": {"name": "笔记本电脑", "price": 8999, "cpu": "i7",
                   "ram": "16GB", "ssd": "512GB", "warranty": "2 年保修"},
}

# ============ 退款数据（服务端权威） ============

REFUNDS: dict[str, dict] = {}          # order_no -> refund
_attempts: list[tuple[str, datetime]] = []
_refund_seq = itertools.count(1001)

IDEMPOTENCY: dict[str, str] = {}  # idempotency_key -> refund_id


def _refund_attempts_recent(user_id: str, days: int = 30) -> int:
    cutoff = now() - timedelta(days=days)
    return sum(1 for uid, ts in _attempts if uid == user_id and ts >= cutoff)


def _order_view(o: dict) -> dict:
    return {
        "order_no": o["order_no"],
        "status": o["status"],
        "amount": o["amount"],
        "created_at": o["created_at"],
        "completed_at": o["completed_at"],   # 七天无理由要算天数
        "items": o["items"],
        "logistics": ({
            "carrier": o["carrier"],
            "tracking_no": o["tracking_no"],
            "latest": o["latest_track"],
        } if o["tracking_no"] else None),
        "address": o["address"],
        "can_refund": o["status"] in ("已发货", "已完成"),
        "can_cancel": o["status"] in ("待付款", "待发货"),
        "can_change_address": o["status"] == "待发货" and o["address_changes"] < 2,
    }


# ============ 订单 API ============

def api_get_order(order_no: str, user_id: str) -> tuple[int, dict]:
    """GET /orders/{order_no}"""
    o = ORDERS.get(order_no)
    if not o:
        return 404, {"message": f"订单 {order_no} 不存在"}
    if o["user_id"] != user_id:
        # ⚠️ 注意：这里返回 403，而不是「不存在」。
        #    to 用户的话术统一为「查不到」，但服务端日志要分开（见文档 10 安全章节）
        return 403, {"message": "无权限查询该订单"}
    return 200, _order_view(o)


def api_search_orders(user_id: str, keyword: str, size: int = 10) -> tuple[int, dict]:
    """GET /orders?q={keyword}"""
    kw = (keyword or "").strip()
    hits = []
    for o in ORDERS.values():
        if o["user_id"] != user_id:
            continue
        if not kw or kw in o["order_no"] or any(kw in i["name"] for i in o["items"]):
            hits.append({"order_no": o["order_no"], "status": o["status"],
                         "amount": o["amount"],
                         "item": o["items"][0]["name"]})
    hits.sort(key=lambda x: x["order_no"], reverse=True)
    return 200, {"total": len(hits), "items": hits[:size]}


def api_create_refund(order_no: str, user_id: str, reason: str,
                      remark: str | None, session: str,
                      idempotency_key: str) -> tuple[int, dict]:
    """POST /orders/{order_no}/refunds

    三条铁律在这里落地：
      ① 金额由服务端算（从订单取），不接受客户端传
      ② 幂等键：同一个 key 第二次调用返回同一个退款单
      ③ 前置条件在服务端校验，不信任提示词
    """
    with _lock:
        o = ORDERS.get(order_no)
        if not o:
            return 404, {"message": "订单不存在"}
        if o["user_id"] != user_id:
            return 403, {"message": "无权限操作该订单"}

        # ② 幂等
        if idempotency_key in IDEMPOTENCY:
            rid = IDEMPOTENCY[idempotency_key]
            r = REFUNDS[order_no]
            return 409, {"refundId": rid, "amount": r["amount"],
                         "status": r["status"],
                         "message": "该订单已有退款申请"}

        # ③ 前置条件
        if o["status"] not in ("已发货", "已完成"):
            return 422, {"message": f"订单状态为「{o['status']}」，不支持退款"}
        if o["status"] == "已完成" and o["completed_at"]:
            days = (now().date() - datetime.fromisoformat(o["completed_at"]).date()).days
            if reason == "七天无理由" and days > 7:
                return 422, {"message": f"订单已完成 {days} 天，已超出七天无理由期限"}

        rid = f"RF{next(_refund_seq)}"
        refund = {
            "refund_id": rid,
            "order_no": order_no,
            "amount": o["amount"],          # ① 服务端计算
            "reason": reason,
            "remark": remark,
            "status": "待审核",
            "session": session,
            "created_at": now().isoformat(timespec="seconds"),
        }
        REFUNDS[order_no] = refund
        IDEMPOTENCY[idempotency_key] = rid
        _attempts.append((user_id, now()))

        o["status"] = "退款中"
        return 200, refund


def api_cancel_order(order_no: str, user_id: str, reason: str) -> tuple[int, dict]:
    with _lock:
        o = ORDERS.get(order_no)
        if not o:
            return 404, {"message": "订单不存在"}
        if o["user_id"] != user_id:
            return 403, {"message": "无权限操作该订单"}
        if o["status"] not in ("待付款", "待发货"):
            return 409, {"message": f"订单状态为「{o['status']}」，无法取消"}
        o["status"] = "已取消"
        return 200, {"order_no": order_no, "status": "已取消",
                     "refund_triggered": False, "reason": reason}


def api_change_address(order_no: str, user_id: str, address: dict) -> tuple[int, dict]:
    with _lock:
        o = ORDERS.get(order_no)
        if not o:
            return 404, {"message": "订单不存在"}
        if o["user_id"] != user_id:
            return 403, {"message": "无权限操作该订单"}
        if o["status"] != "待发货":
            return 422, {"message": f"订单状态为「{o['status']}」，无法修改地址"}
        if o["address_changes"] >= 2:
            return 422, {"message": "该订单已修改地址 2 次，无法再次修改"}
        o["address"] = address
        o["address_changes"] += 1
        return 200, {"order_no": order_no, "address": address,
                     "remaining": 2 - o["address_changes"]}


def refund_of(order_no: str) -> dict | None:
    return REFUNDS.get(order_no)


def pending_order_view(order_no: str) -> dict | None:
    o = ORDERS.get(order_no)
    return _order_view(o) if o else None


# ============ 工单：状态机 ============

STATUS = {"created", "ai_handling", "pending_approval", "approved", "rejected",
          "executing", "resolved", "escalated", "human_handling", "closed"}

TRANSITIONS = {
    "created": {"ai_handling"},
    "ai_handling": {"resolved", "pending_approval", "escalated"},
    "pending_approval": {"approved", "rejected", "escalated"},
    "approved": {"executing"},
    "rejected": {"ai_handling", "escalated"},
    "executing": {"resolved", "escalated"},
    "resolved": {"closed"},
    "escalated": {"human_handling"},
    "human_handling": {"resolved"},
    "closed": set(),
}

TICKETS: dict[str, dict] = {}
EVENTS: list[dict] = []
_ticket_seq = itertools.count(1)


class InvalidTransition(Exception):
    pass


def create_ticket(thread_id: str, user_id: str, category: str,
                  order_no: str | None, priority: str,
                  ai_summary: dict | None, ai_handled: bool = True) -> dict:
    with _lock:
        # 同一会话复用同一张工单，避免「问三次生成三张单」
        for t in TICKETS.values():
            if t["thread_id"] == thread_id and t["status"] not in ("closed",):
                return t

        no = f"CS20261101{next(_ticket_seq):03d}"
        t = {
            "ticket_no": no,
            "thread_id": thread_id,
            "user_id": user_id,
            "tenant": "default",
            "category": category,
            "order_no": order_no,
            "status": "ai_handling",
            "priority": priority,
            "assignee": None,
            "ai_summary": ai_summary,
            "ai_handled": ai_handled,
            "created_at": now().isoformat(timespec="seconds"),
        }
        TICKETS[no] = t
        _event(no, None, "ai_handling", actor="ai:agent", action="create_ticket")
        return t


def _event(ticket_no: str, from_status: str | None, to_status: str,
           actor: str, action: str = "", detail: dict | None = None) -> None:
    EVENTS.append({
        "ticket_no": ticket_no, "from_status": from_status, "to_status": to_status,
        "actor": actor, "action": action, "detail": detail or {},
        "created_at": now().isoformat(timespec="seconds"),
    })


def transition(ticket_no: str, to: str, actor: str = "ai:agent",
               action: str = "", detail: dict | None = None) -> dict:
    """状态机校验 + 事件留痕。非法流转直接抛错，不静默放过。"""
    with _lock:
        t = TICKETS.get(ticket_no)
        if not t:
            raise InvalidTransition(f"工单 {ticket_no} 不存在")
        cur = t["status"]
        if to not in TRANSITIONS.get(cur, set()):
            raise InvalidTransition(f"{cur} -> {to} 不允许")
        t["status"] = to
        _event(ticket_no, cur, to, actor=actor, action=action, detail=detail)
        return t


def set_assignee(ticket_no: str, assignee: str) -> None:
    TICKETS[ticket_no]["assignee"] = assignee


def list_escalated(limit: int = 50) -> list[dict]:
    order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
    rows = [t for t in TICKETS.values() if t["status"] == "escalated"]
    rows.sort(key=lambda t: (order.get(t["priority"], 9), t["created_at"]))
    return rows[:limit]


# ============ 审计 ============

AUDIT_LOG: list[dict] = []


def audit(actor: str, action: str, user_id: str, ticket_no: str | None = None,
          args: dict | None = None, result: dict | None = None) -> None:
    """每一次写操作都留痕：谁、在哪个会话、做了什么、结果如何。"""
    AUDIT_LOG.append({
        "at": now().isoformat(timespec="milliseconds"),
        "actor": actor,
        "action": action,
        "user_id": user_id,
        "ticket_no": ticket_no,
        "args": args or {},
        "result": result or {},
    })


def dump_audit(limit: int = 20) -> list[dict]:
    return AUDIT_LOG[-limit:]


def reset() -> None:
    """测试用：清空运行期数据。"""
    REFUNDS.clear()
    IDEMPOTENCY.clear()
    _attempts.clear()
    TICKETS.clear()
    EVENTS.clear()
    AUDIT_LOG.clear()
