# 12 - 实战：智能客服工单 Agent

> 知识库 Agent 只到"回答问题"为止。客服 Agent 要**处理问题**——查订单、改地址、发起退款、升级工单。
> 一旦牵涉写操作，难度会上一个台阶：**出错有代价、需要审批、要能回滚、要能追责**。
> 这一篇做一个真的能上线的客服 Agent：**订单查询 → 售后处理 → 人工升级 → 工单闭环**。

---

## 📖 目录

1. [与知识库 Agent 的本质差别](#一与知识库-agent-的本质差别)
2. [业务流程与 Agent 边界 ⭐⭐](#二业务流程与-agent-边界-)
3. [架构设计 ⭐](#三架构设计-)
4. [工单模型与状态机](#四工单模型与状态机)
5. [工具设计：查询类 ⭐](#五工具设计查询类-)
6. [工具设计：写操作类 ⭐⭐⭐](#六工具设计写操作类-)
7. [意图路由与多 Agent ⭐](#七意图路由与多-agent-)
8. [审批：金额、风控、人工 ⭐⭐](#八审批金额风控人工-)
9. [转人工：什么时候该放弃](#九转人工什么时候该放弃)
10. [工单状态机与 LangGraph 结合 ⭐⭐](#十工单状态机与-langgraph-结合-)
11. [完整的会话主流程](#十一完整的会话主流程)
12. [质检出站：避免说错话](#十二质检出站避免说错话)
13. [回访与满意度](#十三回访与满意度)
14. [可观测与追责 ⭐](#十四可观测与追责-)
15. [上线节奏与灰度](#十五上线节奏与灰度)
16. [常见事故与预案](#十六常见事故与预案)
17. [本章小结与练习](#十七本章小结与练习)

---

## 一、与知识库 Agent 的本质差别

| | 知识库 Agent | 客服工单 Agent |
| :--- | :--- | :--- |
| **核心动作** | 检索 + 生成 | 查询 + **执行** |
| **出错代价** | 回答不准，用户再问 | **退错钱、改错地址、货丢了** |
| **可逆性** | 完全可逆 | 部分不可逆 |
| **权限要求** | 只读 | **读写，且分角色** |
| **审批** | 不需要 | **必须** |
| **审计** | 建议 | **强制** |
| **评测重点** | 准确性、拒答率 | **误操作率、越权率** |

> ⚠️ **一句话**：知识库 Agent 答错了顶多被骂，客服 Agent 做错了要赔钱。
> **所以这一篇的重点不在"让 Agent 更聪明"，而在"让 Agent 少犯错、犯错可控"。**

---

## 二、业务流程与 Agent 边界 ⭐⭐

### 2.1 先画业务流程

```text
用户进线
  │
  ├─ 售前咨询（产品、价格、库存）        → Agent 可完全处理
  ├─ 订单查询（状态、物流）              → Agent 可完全处理
  ├─ 售后申请（退款、换货、维修）        → Agent 处理 + 条件审批
  ├─ 投诉 / 情绪激烈                     → 直接转人工
  └─ 系统故障 / 复杂纠纷                 → 转人工
```

### 2.2 Agent 能力边界（非常重要）

| 动作 | 谁能做 | 条件 |
| :--- | :--- | :--- |
| 查订单状态 | Agent | 仅本人订单 |
| 查物流 | Agent | 仅本人订单 |
| 改收货地址 | Agent | **未发货**且 ≤ 2 次 |
| 取消订单 | Agent | **未发货** |
| 申请退款 | Agent | 满足退款政策 → 自动提交 |
| 退款 ≤ 200 元 | Agent 直接执行 | 有自动审核 |
| 200–2000 元 | Agent 提交 + **AI 初审** | 通过则执行 |
| > 2000 元 | Agent 提交 + **人工审批** | `interrupt` |
| 补偿 / 优惠券 | Agent 不可 | 仅人工 |
| 修改金额 | Agent 不可 | 仅人工 |
| 删除订单 | Agent 不可 | 不存在此接口 |

> 💡 **这张表要先和业务方签字确认**。**Agent 能做什么不能做什么，是产品决策，不是技术决策。**

### 2.3 三个"绝不"

```text
① 绝不让模型决定金额        金额由系统按规则计算
② 绝不让模型传用户身份      身份来自服务端上下文
③ 绝不让模型直接执行不可逆操作  必须经过服务端校验 + 审批
```

---

## 三、架构设计 ⭐

### 3.1 整体

```text
用户（App / IM / Web）
   │
   ▼
┌─────────────────────────────────────┐
│ 接入层：鉴权、限流、会话管理          │
├─────────────────────────────────────┤
│ 编排层：LangGraph 主图               │
│   intent → 子 Agent → 审批 → 执行    │
├─────────────────────────────────────┤
│ Agent 层                             │
│   order / after_sale / product       │
│   + human（转人工）                   │
├─────────────────────────────────────┤
│ 工具层（HTTP → 业务系统）             │
│   OrderAPI / RefundAPI / TicketAPI   │
├─────────────────────────────────────┤
│ 数据层                               │
│   PostgreSQL（checkpoint + 工单）    │
│   Redis（会话、限流、幂等）           │
└─────────────────────────────────────┘
```

### 3.2 关键原则

| 原则 | 说明 |
| :--- | :--- |
| **Agent 不碰数据库** | 所有读写走业务 API |
| **Agent 不算钱** | 金额由业务系统计算并返回 |
| **Agent 不持有权限** | 权限在业务系统，Agent 只是带着用户 token 调用 |
| **Agent 的每个写操作有幂等键** | 重试/恢复不重复执行 |
| **所有决策留痕** | 谁在什么时候基于什么做了什么 |

### 3.3 与业务系统的契约

```python
# 工具调用业务 API 时，携带：
{
    "X-User-Id": "u1001",              # 服务端注入，不是模型传
    "X-Trace-Id": "trace-xxx",
    "X-Agent-Session": "thread-xxx",
    "Idempotency-Key": "refund:order12345",   # 写操作必带
}
```

**业务系统要做的**：

- 校验 `X-User-Id` 与实际操作对象的关系（防越权）
- 幂等键去重
- 记录"由 Agent 发起"标记，便于统计和审计

---

## 四、工单模型与状态机

### 4.1 工单表

```sql
CREATE TABLE tickets (
    id             BIGSERIAL PRIMARY KEY,
    ticket_no      TEXT UNIQUE NOT NULL,
    thread_id      TEXT NOT NULL,              -- 关联 Agent 会话
    user_id        TEXT NOT NULL,
    tenant         TEXT NOT NULL,
    category       TEXT NOT NULL,              -- order | after_sale | complaint
    sub_type       TEXT,                       -- refund | exchange | repair
    order_no       TEXT,
    status         TEXT NOT NULL,              -- 见状态机
    priority       TEXT DEFAULT 'normal',      -- low | normal | high | urgent
    assignee       TEXT,                       -- 人工客服 ID
    ai_summary     TEXT,                       -- Agent 生成的问题摘要
    ai_handled     BOOLEAN DEFAULT true,       -- 是否 AI 闭环
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now(),
    closed_at      TIMESTAMPTZ
);

CREATE INDEX idx_tickets_user ON tickets(user_id, created_at DESC);
CREATE INDEX idx_tickets_status ON tickets(status, created_at);
CREATE INDEX idx_tickets_assignee ON tickets(assignee) WHERE assignee IS NOT NULL;
```

### 4.2 状态机

```text
   created
      │
      ▼
   ai_handling ──┬──► resolved（AI 解决）──► closed
                 │
                 ├──► pending_approval（待审批）
                 │         ├──► approved ──► executing ──► resolved
                 │         └──► rejected ──► ai_handling / human
                 │
                 └──► escalated（转人工）
                           │
                           ▼
                      human_handling ──► resolved ──► closed
```

```python
STATUS = {
    "created", "ai_handling", "pending_approval", "approved", "rejected",
    "executing", "resolved", "escalated", "human_handling", "closed",
}

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


def transition(ticket_no: str, to: str, meta: dict | None = None):
    cur = db.get_status(ticket_no)
    if to not in TRANSITIONS.get(cur, set()):
        raise InvalidTransition(f"{cur} -> {to} 不允许")
    db.update_status(ticket_no, to, meta)
    db.insert_ticket_event(ticket_no, cur, to, meta)
```

> ⚠️ **状态机必须落在数据库里，不能只在 Agent 的内存里**。工单可能跨越几天、跨越多个服务。

### 4.3 事件表（审计）

```sql
CREATE TABLE ticket_events (
    id         BIGSERIAL PRIMARY KEY,
    ticket_no  TEXT NOT NULL,
    from_status TEXT,
    to_status   TEXT,
    actor       TEXT NOT NULL,      -- ai:agent | ai:approval | user:u1001 | human:h001
    action      TEXT,               -- tool_name 或操作名
    detail      JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

> 💡 **`actor` 字段是关键**。出事时能回答"是模型做的还是人做的"。

---

## 五、工具设计：查询类 ⭐

### 5.1 订单查询

```python
# app/tools/order_tools.py
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
import httpx

API = "http://order-service/api"
TIMEOUT = httpx.Timeout(8.0, connect=2.0)


@tool
async def get_order_detail(order_no: str, config: RunnableConfig) -> dict:
    """查询订单详情：状态、金额、商品、物流、是否可退款。

    用户询问订单进度、物流、金额、退款条件时使用。
    只能查询当前用户自己的订单。
    """
    uid = config["configurable"]["user_id"]
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        try:
            r = await c.get(f"{API}/orders/{order_no}",
                            headers={"X-User-Id": uid,
                                     "X-Trace-Id": config["configurable"]["trace_id"]})
        except httpx.TimeoutException:
            return {"success": False, "error": "查询超时",
                    "hint": "告诉用户系统繁忙，请稍后重试，不要编造订单信息。"}

    if r.status_code == 404:
        return {"success": False, "error": f"订单 {order_no} 不存在",
                "hint": "请与用户核对订单号，不要反复尝试其他号码。"}
    if r.status_code == 403:
        return {"success": False, "error": "该订单不属于当前用户",
                "hint": "告知用户无法查询他人订单，建议其登录自己的账号查看。"}
    if r.status_code != 200:
        return {"success": False, "error": f"查询失败({r.status_code})"}

    d = r.json()
    return {
        "success": True,
        "order_no": d["orderNo"],
        "status": d["status"],                 # 待付款/待发货/已发货/已完成/已取消
        "amount": d["payAmount"],
        "created_at": d["createdAt"],
        "items": [{"name": i["name"], "qty": i["qty"], "price": i["price"]}
                  for i in d["items"]],
        "logistics": {
            "carrier": d.get("carrier"),
            "tracking_no": d.get("trackingNo"),
            "latest": d.get("latestTrack"),
        } if d.get("trackingNo") else None,
        "can_refund": d["status"] in ("已发货", "已完成"),
        "can_cancel": d["status"] in ("待付款", "待发货"),
        "can_change_address": d["status"] == "待发货",
    }


@tool
async def search_orders(keyword: str, config: RunnableConfig) -> dict:
    """按关键词（订单号/商品名）搜索当前用户的订单列表。"""
    uid = config["configurable"]["user_id"]
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{API}/orders", params={"q": keyword, "size": 10},
                        headers={"X-User-Id": uid})
    items = r.json().get("items", [])
    if not items:
        return {"success": True, "total": 0,
                "hint": "未找到订单。直接告诉用户没找到，建议核对关键词或订单号，不要反复换词重搜。"}
    return {"success": True, "total": len(items),
            "items": [{"order_no": i["orderNo"], "status": i["status"],
                       "amount": i["payAmount"], "item": i["items"][0]["name"]}
                      for i in items]}
```

### 5.2 查询类工具的设计要点

| 要点 | 说明 |
| :--- | :--- |
| **返回 `can_*` 布尔字段** | 让模型不用自己判断状态，减少推理错误 |
| **带 `hint` 字段** | 指导模型下一步，防止无效重试 |
| **错误分类明确** | 超时 vs 不存在 vs 无权，处理方式不同 |
| **只要必要字段** | 别把整个订单对象塞进去（省 token + 减干扰） |
| **超时短** | 查询 8s 足够，超时转人工 |

---

## 六、工具设计：写操作类 ⭐⭐⭐

**这是整个系统最需要谨慎的地方。**

### 6.1 三条规则

```text
① 金额、状态由系统决定，不由模型传
② 必须有幂等键
③ 必须有前置条件校验（服务端，不是提示词）
```

### 6.2 申请退款

```python
# app/tools/refund_tools.py
from pydantic import BaseModel, Field
from typing import Literal

class RefundInput(BaseModel):
    order_no: str = Field(pattern=r"^\d{5,20}$", description="订单号")
    reason: Literal["七天无理由", "质量问题", "发错货", "少件漏发", "其他"] = Field(
        description="退款原因"
    )
    remark: str | None = Field(default=None, max_length=200,
                               description="补充说明，可为空")


@tool("apply_refund", args_schema=RefundInput)
async def apply_refund(order_no: str, reason: str, remark: str | None,
                       config: RunnableConfig) -> dict:
    """提交退款申请（进入审核流程，不会立即退款）。

    前置条件（全部满足才可调用）：
    1. 已调用 get_order_detail 且 can_refund=true
    2. 用户明确表达了退款意愿
    3. 已向用户说明退款金额（由系统计算，无需询问用户）

    注意：退款金额由系统按订单实付金额自动计算，不要传金额参数。
    """
    uid = config["configurable"]["user_id"]
    tid = config["configurable"]["thread_id"]
    trace = config["configurable"]["trace_id"]

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as c:
        r = await c.post(
            f"{API}/orders/{order_no}/refunds",
            json={"reason": reason, "remark": remark,
                  "channel": "ai_agent", "session": tid},
            headers={
                "X-User-Id": uid,
                "X-Trace-Id": trace,
                "Idempotency-Key": f"refund:{order_no}",   # 关键
            },
        )

    if r.status_code == 409:
        d = r.json()
        return {"success": True, "already_exists": True,
                "refund_id": d.get("refundId"),
                "message": "该订单已有退款申请，无需重复提交。"}
    if r.status_code == 403:
        return {"success": False, "error": "该订单不属于当前用户"}
    if r.status_code == 422:
        return {"success": False,
                "error": r.json().get("message", "订单不满足退款条件"),
                "hint": "如实告知用户不能退款的原因，不要辩解或承诺补偿。"}
    if r.status_code != 200:
        return {"success": False, "error": "退款申请提交失败，请转人工",
                "hint": "告知用户系统暂时无法处理，已为其创建工单，请人工处理。"}

    d = r.json()
    return {
        "success": True,
        "refund_id": d["refundId"],
        "amount": d["amount"],           # 服务端计算
        "status": d["status"],           # 待审核 / 已通过 / 已退款
        "estimated_days": d.get("estimatedDays", 3),
    }
```

### 6.3 取消订单

```python
@tool
async def cancel_order(order_no: str, reason: str, config: RunnableConfig) -> dict:
    """取消订单（仅在待付款/待发货状态可用，会同时触发退款）。

    前置条件：已调用 get_order_detail 且 can_cancel=true。
    """
    uid = config["configurable"]["user_id"]
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as c:
        r = await c.post(
            f"{API}/orders/{order_no}/cancel",
            json={"reason": reason},
            headers={"X-User-Id": uid,
                     "Idempotency-Key": f"cancel:{order_no}",
                     "X-Trace-Id": config["configurable"]["trace_id"]},
        )
    if r.status_code == 409:
        return {"success": False, "error": "订单状态已变更，无法取消",
                "hint": "让用户重新查询订单状态后再决定。"}
    ...
```

### 6.4 改地址

```python
class AddressInput(BaseModel):
    order_no: str = Field(pattern=r"^\d{5,20}$")
    receiver: str = Field(min_length=1, max_length=20, description="收货人姓名")
    phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="手机号")
    province: str
    city: str
    district: str
    detail: str = Field(min_length=5, max_length=100, description="详细地址")


@tool("change_address", args_schema=AddressInput)
async def change_address(order_no: str, receiver: str, phone: str,
                         province: str, city: str, district: str, detail: str,
                         config: RunnableConfig) -> dict:
    """修改收货地址（仅待发货状态，每单最多改 2 次）。

    前置条件：已调用 get_order_detail 且 can_change_address=true，
    且用户已确认完整新地址。
    """
    ...
```

### 6.5 写操作工具的统一模板

```python
@tool(...)
async def write_tool(..., config) -> dict:
    # ① 从 config 取身份（绝不从参数）
    uid = config["configurable"]["user_id"]

    # ② 服务端前置校验（工具内或业务 API 内）
    #    不要只依赖提示词里的"前置条件"

    # ③ 带幂等键
    headers = {"Idempotency-Key": f"{action}:{key}", "X-User-Id": uid}

    # ④ 明确的错误分类，每类都有 hint
    # ⑤ 返回结构化结果 + 服务端计算的权威数据
    # ⑥ 审计日志
    audit.log(action=..., user=uid, args=..., result=...)
```

| 检查项 | 为什么 |
| :--- | :--- |
| 身份来自 config | 防模型伪造 |
| 幂等键 | 重置/重试不重复执行 |
| 错误分类 | 让模型能正确应对 |
| 返回权威数据 | 模型不编造金额/状态 |
| 审计日志 | 出事能追责 |

### 6.6 最容易犯的错

```python
# ❌ 模型传金额
@tool
def refund(order_no: str, amount: float) -> dict: ...

# ❌ 模型传用户 ID
@tool
def get_order(order_no: str, user_id: str) -> dict: ...

# ❌ 没有幂等
@tool
def refund(order_no: str) -> dict:
    return httpx.post(f"/refund/{order_no}").json()

# ❌ 返回模糊错误
return {"error": "failed"}      # 模型只能瞎猜

# ✅ 正确
@tool
def refund(order_no: str, config) -> dict:
    uid = config["configurable"]["user_id"]
    r = httpx.post(f"/refunds", json={"order_no": order_no},
                   headers={"X-User-Id": uid, "Idempotency-Key": f"refund:{order_no}"})
    # 分类返回 + hint
```

---

## 七、意图路由与多 Agent ⭐

### 7.1 为什么不用单个 Agent

| 问题 | 说明 |
| :--- | :--- |
| 工具数量 | 订单 4 + 售后 5 + 产品 2 + 工单 2 = 13 个，误调用上升 |
| 提示词冲突 | 订单规则和售后规则混在一起 |
| 权限差异 | 售后能写，产品只读 |
| 独立迭代 | 售后规则改得频繁，不想带着订单一起测 |

### 7.2 路由设计

```python
from pydantic import BaseModel, Field
from typing import Literal

class Route(BaseModel):
    intent: Literal["order", "after_sale", "product", "complaint", "other"] = Field(
        description=(
            "order=订单查询/物流/取消/改地址；"
            "after_sale=退款/换货/维修；"
            "product=产品功能/参数/使用方法；"
            "complaint=投诉/情绪激烈/要求赔偿；"
            "other=其他"
        )
    )
    keywords: list[str] = Field(default_factory=list, description="提取的关键信息")
    order_no: str | None = Field(default=None, description="提到的订单号，若无可为 null")
    urgency: Literal["low", "normal", "high"] = Field(
        default="normal", description="用户情绪激烈或明确要求紧急时为 high"
    )


async def route_intent(text: str) -> Route:
    return await small_model.with_structured_output(Route).ainvoke(
        f"判断用户意图，并提取关键信息。\n用户消息：{text}"
    )
```

> 💡 **用规则做第一层兜底**：包含"投诉/差评/曝光"直接走 `complaint` → 转人工，不用问模型。

```python
FORCE_HUMAN = ["投诉", "差评", "举报", "曝光", "律师", "起诉", "骗子"]

def force_human(text: str) -> bool:
    return any(k in text for k in FORCE_HUMAN)
```

**⚠️ 关键词列表里千万不要放纯数字。** 这是个真实踩过的坑：

```python
# ❌ 早期版本
FORCE_HUMAN = ["投诉", "12315", "12345", ...]
# 结果：「帮我查订单 12345」→ 命中 12345 → 所有这个订单号的查询全被转人工
```

投诉热线要用**上下文正则**而不是裸关键词：

```python
import re
HOTLINE_RE = re.compile(
    r"(打|拨|投诉到|找)\s*(12315|12345|96315)"    # 打 12345
    r"|(12315|12345|96315)\s*(投诉|举报|热线)"      # 12345 投诉
)

def force_human(text: str) -> bool:
    if HOTLINE_RE.search(text):
        return True
    return any(k in text for k in FORCE_HUMAN)
```

> 💡 **规则引擎的每一条都要问一句「什么情况下会误伤」**。订单号、金额、日期这些
> 和业务数据同形的字面量，是规则误判的重灾区。

### 7.3 主图

```python
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    ticket_no: str
    intent: str
    order_no: str | None
    urgency: str
    need_human: bool
    resolved: bool


async def triage(state: State, config) -> Command:
    last = state["messages"][-1].content

    # 投诉强制转人工
    if force_human(last):
        return Command(goto="escalate", update={"intent": "complaint",
                                                "need_human": True})

    r = await route_intent(last)
    update = {"intent": r.intent, "order_no": r.order_no, "urgency": r.urgency}
    if r.urgency == "high":
        return Command(goto="escalate", update={**update, "need_human": True})
    return Command(goto=r.intent, update=update)
```

---

## 八、审批：金额、风控、人工 ⭐⭐

### 8.1 三档策略

```text
金额 ≤ 200       → 自动执行（AI 闭环）
200 < 金额 ≤ 2000 → AI 初审（规则 + 模型判断）→ 通过则执行
金额 > 2000       → 必须人工审批（interrupt）
```

### 8.2 规则初审

```python
def auto_review(user_id: str, order: dict, reason: str) -> tuple[bool, str]:
    """返回 (是否通过, 原因)。规则确定，不用模型。"""
    if order["amount"] <= 200:
        return True, "小额自动通过"

    # 风险信号
    recent = db.count_refunds(user_id, days=30)
    if recent >= 3:
        return False, f"近 30 天已申请 {recent} 次退款，需人工审核"

    if reason == "质量问题":
        return True, "质量问题，金额在 2000 元以内"

    if reason == "七天无理由" and order["status"] == "已完成":
        days = (now() - order["completed_at"]).days
        if days > 7:
            return False, f"已超出七天无理由期限（{days} 天）"

    if order["amount"] <= 2000:
        return True, "金额在自动审核范围内"

    return False, "需人工审核"
```

> 💡 **规则能覆盖 80% 的情况，不要一上来就用模型判断**。模型只用在"规则边界模糊但金额可控"的地方，且要有规则兜底。

### 8.3 人工审批（`interrupt`）

```python
async def approval_node(state: State, config) -> dict:
    order = await fetch_order(state["order_no"], config)
    passed, reason = auto_review(config["configurable"]["user_id"], order,
                                 state.get("refund_reason", ""))

    if passed:
        return {"approval": {"approved": True, "by": "auto", "reason": reason}}

    # 需要人工 → 真的暂停
    decision = interrupt({
        "type": "refund_approval",
        "ticket_no": state["ticket_no"],
        "order_no": state["order_no"],
        "amount": order["amount"],
        "reason": state.get("refund_reason"),
        "auto_reason": reason,
        "user": config["configurable"]["user_id"],
    })

    return {"approval": {
        "approved": bool(decision.get("approved")),
        "by": decision.get("operator", "human"),
        "reason": decision.get("comment", ""),
    }}
```

### 8.4 审批后的分支

```python
def route_approval(state: State) -> Literal["execute", "reject"]:
    return "execute" if state["approval"]["approved"] else "reject"


async def execute_node(state: State, config) -> dict:
    # ⚠️ 幂等：恢复时可能重复执行
    result = await apply_refund.func(
        state["order_no"], state.get("refund_reason", "其他"), None, config
    )
    if not result["success"]:
        return {"messages": [AIMessage(f"退款提交失败：{result['error']}，已转人工")],
                "need_human": True}
    return {"messages": [AIMessage(
                f"退款申请已提交，退款金额 {result['amount']} 元，"
                f"预计 {result['estimated_days']} 个工作日到账。单号 {result['refund_id']}。"
            )],
            "resolved": True}
```

> ⚠️ **`interrupt` 恢复时节点从头重跑**（第 08 篇）。所以 `auto_review` 和 `interrupt` 的顺序要确保 `auto_review` 是纯函数（只读）。**真正的写操作在 `execute_node`，它在 `interrupt` 之后，且带幂等键。**

### 8.5 审批的超时与升级

```python
# 定时任务
async def expire_approvals():
    rows = db.query("""
        SELECT ticket_no FROM tickets
        WHERE status='pending_approval' AND updated_at < now() - interval '2 hours'
    """)
    for t in rows:
        # 未及时审批 → 升级为 urgent，重新分配
        db.update_ticket(t, priority="urgent", status="escalated")
        notify_supervisor(t)
```

---

## 九、转人工：什么时候该放弃

### 9.1 触发条件

| 条件 | 说明 |
| :--- | :--- |
| **情绪激烈** | 关键词 "投诉/骗子/起诉"，或模型判断情绪 high |
| **多次未解决** | 同一会话连续 3 次"未解决" |
| **超出能力** | 工具连续失败、无可用工具 |
| **高风险** | 金额 > 阈值、涉及法律/媒体 |
| **用户明确要求** | "转人工""找客服" |
| **死循环** | 同一工具连续调用 3 次 |
| **特殊类别** | 未成年人、跨境、发票争议 |

### 9.2 实现

```python
ESCALATE_WORDS = ["转人工", "人工客服", "找客服", "我要投诉", "叫你们领导"]


async def should_escalate(state: State, config) -> tuple[bool, str]:
    msgs = state["messages"]

    # ① 用户明确要求
    if any(w in msgs[-1].content for w in ESCALATE_WORDS):
        return True, "用户要求转人工"

    # ② 反复未解决
    未解决 = sum(1 for m in msgs if isinstance(m, AIMessage)
                 and "抱歉" in (m.content or ""))
    if 未解决 >= 3:
        return True, "连续多次未能解决"

    # ③ 工具连续失败
    fails = config["configurable"].get("_tool_fails", 0)
    if fails >= 3:
        return True, "系统多次查询失败"

    # ④ 模型判断
    r = await small_model.with_structured_output(EscalateCheck).ainvoke(
        f"对话记录：{format_messages(msgs[-4:])}\n"
        f"判断是否需要转人工客服（情绪激烈、问题超出客服能力、需要特殊权限）。"
    )
    if r.should_escalate:
        return True, r.reason

    return False, ""
```

### 9.3 交接：给人看的摘要

**转人工最容易失败的地方是"人接手后要从头看聊天记录"。**

```python
class HandoffSummary(BaseModel):
    problem: str = Field(description="用户的核心诉求，一句话")
    attempted: list[str] = Field(description="AI 已经做了什么")
    key_facts: dict = Field(description="关键事实：订单号、金额、状态")
    blocker: str = Field(description="为什么 AI 解决不了")
    suggested_action: str = Field(description="建议人工如何处理")
    sentiment: Literal["calm", "anxious", "angry"] = Field(description="用户情绪")


async def build_handoff(state: State) -> dict:
    s = await model.with_structured_output(HandoffSummary).ainvoke(
        f"根据以下对话生成人工客服交接摘要。\n\n{format_messages(state['messages'])}"
    )
    return s.model_dump()


async def escalate_node(state: State, config) -> dict:
    summary = await build_handoff(state)
    ticket = await ticket_service.create(
        thread_id=config["configurable"]["thread_id"],
        user_id=config["configurable"]["user_id"],
        category=state.get("intent", "other"),
        order_no=state.get("order_no"),
        priority="urgent" if state.get("urgency") == "high" else "high",
        ai_summary=summary,
    )
    return {
        "messages": [AIMessage(
            f"已为您转接人工客服，工单号 {ticket.ticket_no}。"
            f"客服已了解您的情况，会尽快联系您。"
        )],
        "ticket_no": ticket.ticket_no,
        "need_human": True,
    }
```

> 💡 **交接摘要的质量直接决定了人工客服的效率**。**"AI 已做了什么"这一项特别重要**——避免人工重复问、重复操作。

### 9.4 人工侧的工作台

```python
@app.get("/workbench/dispatch")
def dispatch(agent_id: str):
    """人工客服的待办列表，按优先级 + 创建时间排序。"""
    return db.query("""
        SELECT ticket_no, category, priority, ai_summary, order_no, created_at,
               EXTRACT(EPOCH FROM (now() - created_at)) / 60 AS waiting_minutes
        FROM tickets
        WHERE status = 'escalated'
          AND (assignee IS NULL OR assignee = %s)
        ORDER BY
          CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 ELSE 3 END,
          created_at
        LIMIT 50
    """, (agent_id,))
```

**工作台要展示**：

- AI 交接摘要（结构化）
- 完整对话记录
- 已执行的操作（读了什么、写了什么）
- 一键继续对话（接续同一个 `thread_id`）

---

## 十、工单状态机与 LangGraph 结合 ⭐⭐

### 10.1 两种状态的关系

```text
LangGraph 的 State  = 本次执行的上下文（消息、订单数据、审批结果）
工单的 status       = 业务生命周期（跨会话、跨系统）
```

**不要混用。** Agent 的 State 存在 checkpoint 里；工单的 status 存在业务表里。

**同步点**：

```python
async def sync_ticket(state: State, status: str, meta: dict | None = None):
    if state.get("ticket_no"):
        transition(state["ticket_no"], status, meta)
```

### 10.2 完整的主图

```python
def build(saver):
    b = StateGraph(State)

    b.add_node("triage", triage)                 # Command 路由
    b.add_node("order", order_node)
    b.add_node("after_sale", after_sale_node)
    b.add_node("product", product_node)
    b.add_node("approval", approval_node)
    b.add_node("execute", execute_node)
    b.add_node("reject", reject_node)
    b.add_node("escalate", escalate_node)

    b.add_edge(START, "triage")
    # triage 用 Command 去 order/after_sale/product/escalate
    # after_sale 内部用 Command 去 approval 或 END

    b.add_conditional_edges("approval", route_approval,
                            {"execute": "execute", "reject": "reject"})
    b.add_edge("execute", END)
    b.add_edge("reject", END)
    b.add_edge("escalate", END)
    b.add_edge("order", END)
    b.add_edge("product", END)

    return b.compile(checkpointer=saver)
```

### 10.3 子 Agent 里如何跳回主图

**售后 Agent 内部决定"需要审批"，要跳回主图的 `approval` 节点：**

```python
from langgraph.types import Command

async def after_sale_node(state: State, config) -> Command:
    result = await after_sale_agent.ainvoke(
        {"messages": state["messages"]}, config
    )
    last = result["messages"][-1]

    # 子 Agent 通过"意向标记"告诉主图要审批
    if getattr(last, "additional_kwargs", {}).get("need_approval"):
        return Command(goto="approval", update={
            "refund_reason": last.additional_kwargs.get("refund_reason"),
            "messages": [AIMessage("正在为您提交退款申请，请稍候…")],
        })

    return Command(goto=END, update={"messages": [last]})
```

**更清晰的做法**：让子 Agent 用结构化输出返回决策。

```python
class AfterSaleDecision(BaseModel):
    action: Literal["answer", "submit_refund", "escalate"]
    order_no: str | None = None
    reason: str | None = None
    reply: str
```

```python
async def after_sale_node(state: State, config) -> Command:
    d = await after_sale_agent.ainvoke(...)     # 返回 AfterSaleDecision
    if d.action == "submit_refund":
        return Command(goto="approval", update={...})
    if d.action == "escalate":
        return Command(goto="escalate", update={...})
    return Command(goto=END, update={"messages": [AIMessage(d.reply)]})
```

> 💡 **子 Agent 输出"决策结构"而不是"自然语言 + 魔法标记"**，这样主图的跳转逻辑是类型安全的。

---

## 十一、完整的会话主流程

```python
# app/api/chat.py
@app.post("/cs/chat")
async def cs_chat(req: ChatReq, user=Depends(current_user)):
    thread_id = req.thread_id or f"{user['tenant']}:{user['id']}:cs:{uuid4().hex}"
    cfg = {"configurable": {
        "thread_id": thread_id,
        "user_id": user["id"],
        "tenant": user["tenant"],
        "trace_id": req.trace_id or uuid4().hex,
    }, "recursion_limit": 15}

    async def gen():
        yield sse({"type": "meta", "thread_id": thread_id})
        try:
            async for ev in graph.astream_events(
                {"messages": [("user", req.message)]}, cfg, version="v2"
            ):
                k = ev["event"]
                if k == "on_chat_model_stream":
                    if c := ev["data"]["chunk"].content:
                        yield sse({"type": "token", "text": c})
                elif k == "on_tool_start":
                    yield sse({"type": "tool", "name": humanize(ev["name"])})
                elif k == "on_chain_end" and ev["name"] in ("execute", "escalate"):
                    out = ev["data"].get("output") or {}
                    if out.get("ticket_no"):
                        yield sse({"type": "ticket", "ticket_no": out["ticket_no"]})
            yield sse({"type": "done"})
        except Exception:
            logger.exception("cs_chat failed", extra={"trace_id": cfg["configurable"]["trace_id"]})
            yield sse({"type": "error", "message": "系统繁忙，请稍后重试或转人工"})

    return StreamingResponse(gen(), media_type="text/event-stream")


TOOL_LABELS = {
    "get_order_detail": "正在查询订单…",
    "search_orders": "正在搜索您的订单…",
    "apply_refund": "正在提交退款申请…",
    "cancel_order": "正在取消订单…",
    "change_address": "正在修改收货地址…",
}

def humanize(name: str) -> str:
    return TOOL_LABELS.get(name, "正在处理…")
```

### 11.1 消息协议

```text
data: {"type":"meta","thread_id":"t1:u1:cs:abc"}
data: {"type":"tool","name":"正在查询订单…"}
data: {"type":"token","text":"您的订单 12345"}
data: {"type":"token","text":"已发货，顺丰 SF123…"}
data: {"type":"done"}
```

**转人工时**：

```text
data: {"type":"ticket","ticket_no":"CS20261101001"}
data: {"type":"token","text":"已为您转接人工客服…"}
```

> ⚠️ **工具名不要暴露给用户**。`get_order_detail` → "正在查询订单…"，这既是体验问题，也是安全考虑（不暴露内部结构）。

---

## 十二、质检出站：避免说错话

### 12.1 为什么需要出站检查

**模型可能在客服场景说出**：

- 未经授权承诺："我们赔您 500 元"
- 法律风险："这肯定是我们的责任"
- 泄露内部信息："系统里显示您有 3 次投诉记录"
- 不恰当表达："您别激动"

### 12.2 三类检查

```python
# app/security/output_guard.py
import re

# ① 承诺类（必须拦截，转成合规说法）
COMMITMENT_PATTERNS = [
    (r"赔偿|赔付|补偿|赔您", "关于赔偿，我需要为您转接专员处理，他们会给您一个满意的方案。"),
    (r"保证|一定能|肯定可以", "我会尽力为您处理，具体结果以系统审核为准。"),
    (r"全额退款" if False else r"立即退款", "退款申请提交后需经审核，通常 1-3 个工作日到账。"),
]

# ② 内部信息泄露
INTERNAL_PATTERNS = [
    r"内部记录|系统里显示您的.{0,10}次数|黑名单|风险等级",
    r"客服评分|工单积压|系统日志",
]

# ③ 不当表达
TONE_PATTERNS = [
    (r"您别激动|冷静一下|你懂不懂", "我理解您的心情，我们一起来解决这个问题。"),
]


def guard(text: str) -> tuple[str, list[str]]:
    """返回 (修正后文本, 命中的规则)。"""
    hits = []
    for patterns, repl in [(COMMITMENT_PATTERNS, None), (TONE_PATTERNS, None)]:
        for p, r in patterns:
            if re.search(p, text):
                hits.append(p)
                text = re.sub(p, r, text)

    for p in INTERNAL_PATTERNS:
        if re.search(p, text):
            hits.append(p)
            return "抱歉，这个问题我需要转接专员为您处理。", hits

    return text, hits
```

> ⚠️ **出站检查命中时，必须记录并告警**。频繁命中说明 Prompt 需要改。

### 12.3 事实检查

**回答里的关键数字必须和工具结果一致。**

```python
def check_numbers(answer: str, tool_results: list[dict]) -> list[str]:
    """检查回答里的金额/单号是否都出现在工具结果中。"""
    nums = set(re.findall(r"\d+(?:\.\d+)?", answer))
    known = set()
    for r in tool_results:
        known.update(re.findall(r"\d+(?:\.\d+)?", json.dumps(r, ensure_ascii=False)))
    return [n for n in nums if len(n) >= 3 and n not in known]
```

**发现不一致时**：

```python
if suspects:
    logger.error("number_mismatch", extra={"answer": answer, "suspects": suspects})
    answer = "抱歉，我需要再核实一下信息，请稍等。"     # 宁可重来
```

### 12.4 Prompt 层的约束

```python
SYSTEM = """你是 XX 商城的客服助手。

【绝对禁止】
1. 不要承诺任何赔偿、补偿、优惠（只能说明"会转接专员处理"）。
2. 不要判断责任归属（不要说"是我们的问题"或"是您操作不当"）。
3. 不要透露内部信息（风控等级、投诉次数、其他用户信息）。
4. 不要编造订单状态、物流信息、金额——只能引用工具返回的结果。
5. 不要主动提供"如何投诉""如何索赔"以外渠道的信息。

【语气】
- 简洁、专业、有温度，但不谄媚
- 用户情绪激动时，先共情，再给方案
- 不知道就说不知道，不要猜
"""
```

> 💡 **"绝对禁止"比"尽量不要"更有效**。用明确的、可判定的规则。

---

## 十三、回访与满意度

### 13.1 收集

```python
@app.post("/cs/feedback")
def feedback(body: FeedbackReq, user=Depends(current_user)):
    db.insert("cs_feedback", {
        "thread_id": body.thread_id,
        "ticket_no": body.ticket_no,
        "score": body.score,           # 1-5
        "resolved": body.resolved,
        "comment": body.comment,
        "handled_by": db.get_actor(body.ticket_no),    # ai | human
    })
```

### 13.2 关键指标

| 指标 | 计算 | 目标 |
| :--- | :--- | :--- |
| **AI 解决率** | AI 闭环工单 / 总工单 | > 60% |
| **转人工率** | 转人工 / 总工单 | < 40% |
| **一次解决率** | 无重复进线的工单占比 | > 75% |
| **满意度** | 平均星级 | > 4.2 |
| **误操作率** | 需人工纠正的写操作 / 总写操作 | < 1% |
| **审批通过率** | 通过 / 提交 | 用于校准规则 |

### 13.3 用数据反推优化

```sql
-- 哪类问题最容易转人工
SELECT category, COUNT(*) FILTER (WHERE status='escalated')::float / COUNT(*) AS rate
FROM tickets GROUP BY category ORDER BY rate DESC;

-- 哪些工具最常失败
SELECT tool, COUNT(*) FILTER (WHERE success=false)::float / COUNT(*) AS fail_rate
FROM tool_logs GROUP BY tool HAVING COUNT(*) > 100 ORDER BY fail_rate DESC;

-- 转人工原因分布
SELECT ai_summary->>'blocker' AS blocker, COUNT(*)
FROM tickets WHERE status='escalated' GROUP BY 1 ORDER BY 2 DESC;
```

> 💡 **"转人工原因分布"是最有价值的报表**。它直接告诉你：**该补什么工具、该改什么规则、该调整什么阈值**。

---

## 十四、可观测与追责 ⭐

### 14.1 每次写操作都要留痕

```sql
CREATE TABLE action_audit (
    id          BIGSERIAL PRIMARY KEY,
    trace_id    TEXT NOT NULL,
    thread_id   TEXT NOT NULL,
    ticket_no   TEXT,
    user_id     TEXT NOT NULL,
    actor       TEXT NOT NULL,          -- ai:agent | ai:auto_approval | human:h001
    action      TEXT NOT NULL,          -- apply_refund / cancel_order / ...
    args        JSONB NOT NULL,
    idempotency_key TEXT,
    result      JSONB,
    success     BOOLEAN,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_action_user ON action_audit(user_id, created_at DESC);
CREATE INDEX idx_action_ticket ON action_audit(ticket_no);
```

```python
async def audited(action: str, args: dict, fn, config):
    key = f"{action}:{args.get('order_no', '')}"
    try:
        result = await fn()
        db.insert("action_audit", {
            "trace_id": config["configurable"]["trace_id"],
            "thread_id": config["configurable"]["thread_id"],
            "user_id": config["configurable"]["user_id"],
            "actor": "ai:agent", "action": action, "args": args,
            "idempotency_key": key, "result": result, "success": result.get("success", False),
        })
        return result
    except Exception as e:
        db.insert("action_audit", {..., "success": False,
                                   "result": {"error": str(e)}})
        raise
```

### 14.2 追责链路

```text
用户投诉"莫名其妙退款了"
  → 按 user_id 查 action_audit
  → 找到 apply_refund 记录
  → 看 trace_id → 查 LangGraph checkpoint
  → 回放 messages，看到：
      用户："这个不好用"
      Agent 调用了 apply_refund
  → 定位：工具描述太宽泛，模型误判为退款意图
  → 修复：描述加"仅在用户明确说'退款''退货'时使用"
  → 加评测用例
```

> 💡 **这条链路必须能在 10 分钟内走完**。做不到，说明可观测性不够。

### 14.3 关键告警

| 指标 | 阈值 |
| :--- | :--- |
| 写操作失败率 | > 2% |
| 审批积压 | > 50 且平均等待 > 30 分钟 |
| 转人工率突增 | 相比昨日 +50% |
| 出站检查命中率 | > 10% |
| 单用户日退款次数 | > 3 |
| 单请求超步数 | > 12 |

---

## 十五、上线节奏与灰度

### 15.1 四个阶段

```text
阶段 1（2 周）：影子模式
  用户正常进人工，Agent 在后台也跑一遍，只记录不生效
  对比：Agent 的处理方案 vs 人工的处理方案

阶段 2（2 周）：只读上线
  Agent 只做订单/物流查询，写操作一律转人工
  目标：验证意图理解、工具调用准确性

阶段 3（2 周）：小额写操作
  只开放 ≤200 元自动退款、未发货取消订单
  目标：验证写操作的安全性和幂等

阶段 4：全量
  开放审批流程，逐步放宽限额
```

### 15.2 灰度维度

```python
def in_rollout(user_id: str) -> bool:
    h = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return h % 100 < ROLLOUT_PERCENT      # 按用户稳定分桶
```

**叠加维度**：

- 订单金额（小额先上）
- 客户等级（内部测试账号先上）
- 时段（工作时间先上，避免夜间无人兜底）
- 渠道（App 先上，IM 后上）

### 15.3 一键降级

```python
@app.post("/admin/kill-switch")
def kill_switch(enabled: bool, admin=Depends(require_admin)):
    redis.set("cs:agent:enabled", "1" if enabled else "0")
    audit_log("kill_switch", admin.id, {"enabled": enabled})
```

```python
async def cs_chat(req, user):
    if redis.get("cs:agent:enabled") != "1":
        return redirect_to_human(req, reason="系统维护中")
    ...
```

> ⚠️ **一键降级必须能在 30 秒内生效**，而且**不需要发版**。这是上线前的硬性要求。

### 15.4 回滚准备

| 回滚对象 | 方式 |
| :--- | :--- |
| 代码 | 镜像 tag 回退 |
| Prompt | 配置中心切换版本 |
| 工具开关 | Redis 开关，逐工具关闭 |
| 模型 | 配置切换 |
| 整个 Agent | kill switch |

---

## 十六、常见事故与预案

### 16.1 六个真实事故

| 事故 | 原因 | 预案 |
| :--- | :--- | :--- |
| **重复退款** | 恢复时重复执行，无幂等 | 幂等键 + 执行前查状态 |
| **给错人退款** | 模型传了别人的 order_no | 服务端校验归属 |
| **承诺赔偿** | Prompt 没禁止 | 出站检查 + Prompt 强化 |
| **越权查询** | 工具没校验 user 归属 | 服务端强制校验 |
| **无限循环** | 工具一直失败，模型反复重试 | 工具失败计数 + 转人工 |
| **上下文串话** | thread_id 用了固定值 | 每会话唯一 + 归属校验 |

### 16.2 应急流程

```text
发现异常
  ↓
① 关开关（30 秒内）
  ↓
② 查影响面：action_audit 里近 1 小时的写操作
  ↓
③ 止损：撤销可撤销的操作（退款拦截、订单回滚）
  ↓
④ 通知：受影响用户 + 业务方
  ↓
⑤ 复盘：定位根因，加评测用例，加防护
```

### 16.3 复盘模板

```markdown
## 事故：2026-11-01 重复退款 3 笔

**影响**：3 名用户，共 ¥680
**时间线**：
- 10:12 首次退款成功
- 10:13 用户刷新，Agent 恢复执行，再次调用
- 10:15 财务发现重复
- 10:18 关闭开关

**根因**：`execute_node` 在 `interrupt` 之后，但幂等键用了 `refund:{order_no}`，
         而业务系统按 `refund:{order_no}:{timestamp}` 去重，键不匹配。

**修复**：
1. 业务系统幂等键改为 `refund:{order_no}`（唯一）
2. `execute_node` 执行前先查退款单是否已存在
3. 加评测用例：模拟恢复场景，断言只执行一次

**改进项**：
- [ ] 所有写操作工具加"执行前查状态"（负责人：张三，11-05）
- [ ] 幂等键规范写入开发文档（李四，11-08）
- [ ] 加监控：同一订单 5 分钟内 2 次写操作告警（王五，11-10）
```

---

## 十七、本章小结与练习

### 核心结论

1. **客服 Agent 的难点不在智能，在安全**：答错和做错的代价完全不同。
2. **Agent 的能力边界要和业务方签字确认**，写清楚"能做什么、不能做什么、什么条件"。
3. **金额、状态、身份绝不由模型传入**，一律服务端决定。
4. **写操作三件套**：服务端前置校验、幂等键、明确错误分类 + hint。
5. **分档审批**：小额自动、中额规则初审、大额人工 `interrupt`。
6. **规则能覆盖 80%**，模型只用在模糊边界，且必须有规则兜底。
7. **转人工要交接摘要**：AI 做了什么、关键事实、卡在哪、建议怎么办。
8. **Agent State 和工单状态要分离**，通过事件表关联。
9. **出站质检三层**：承诺拦截、内部信息拦截、语气修正；外加数字一致性检查。
10. **可观测的终点是"10 分钟内能追责"**：action_audit + trace_id + checkpoint 回放。
11. **上线四阶段**：影子 → 只读 → 小额写 → 全量。
12. **一键降级是硬性要求**，30 秒内生效，不需要发版。

### 动手练习

1. 画出你们业务的 Agent 能力边界表（能做什么/条件/不能做什么），找业务方确认。
2. 实现一个 `apply_refund` 工具，带幂等键和五类错误返回；写测试验证重复调用只生效一次。
3. 用 `interrupt` 实现审批，模拟"提交 → 挂起 → 审批 → 执行"，再故意中断恢复，验证不重复执行。
4. 实现转人工的交接摘要（六字段结构化），找一位真实客服评价是否"看完就能接手"。
5. 写三个出站检查规则，构造能触发它们的模型输出，验证被拦下。
6. 把工单状态机和 LangGraph 接起来：每个关键节点写 `ticket_events`。
7. 做一个 kill switch，验证从开启到生效的耗时。
8. 造一个"不该退款却退了"的场景，走完整个追责链路（audit → trace → checkpoint 回放 → 定位）。

---

## 结语：这套东西该怎么学、怎么用

到这里，12 篇走完了从"大模型是什么"到"两个能上线的 Agent 项目"的全程。

**如果你只记三句话**：

> **① Agent = 大模型 + 工具 + 循环。所有复杂度都来自"把控制流交给模型"这一件事。**
>
> **② 能用代码写的用代码，能用流程图的用图，只有真正需要"动态决策"的地方才交给模型。**
>
> **③ 上线不是终点，"可评测、可观测、可降级、可追责"才是能持续迭代的起点。**

**接下来可以做什么**：

| 方向 | 建议 |
| :--- | :--- |
| 练手 | 用第 11 篇的骨架，接你们公司真实的一个文档源，跑通并评测 |
| 深入 | 读 LangGraph 源码里的 `Pregel` 执行引擎，理解超步和并行 |
| 工程 | 把第 10 篇的检查清单逐项补齐 |
| Java 团队 | 看 `00-学习路线图.md` 里的 Java 方案对比，LangChain4j / Spring AI |
| 前沿 | 关注 MCP（Model Context Protocol）、Agent 评测基准、上下文工程 |

**最后一个建议**：

> **不要一开始就追求"全自动"。先把"人机协作"做扎实**——AI 做 60%，人在关键处补 40%。
> 这个形态上线快、风险低、用户接受度高，而且**做得久了，你会自然知道哪 40% 可以交给 AI。**

祝你在自己的项目里，把它跑起来。
