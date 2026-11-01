# 08 - LangGraph 持久化与人工介入

> 前一篇的图，进程一停就什么都没了。
> 这一篇给图装上**记忆**（Checkpointer）和**暂停键**（`interrupt`）。
> 学完你能做出这样的系统：用户填一半的工单，第二天回来接着说；Agent 要退款，先停下等人点"同意"；线上出了错，回放那个 `thread_id` 看看它当时到底想了什么。

---

## 📖 目录

1. [持久化解决哪三个问题](#一持久化解决哪三个问题)
2. [Checkpointer 是什么](#二checkpointer-是什么)
3. [四种后端对比与选型 ⭐](#三四种后端对比与选型-)
4. [thread_id：会话的主键 ⭐⭐](#四thread_id会话的主键-)
5. [读状态：`get_state` / `get_state_history` ⭐](#五读状态get_state--get_state_history-)
6. [写状态：`update_state` 与"人工纠正"](#六写状态update_state-与人工纠正)
7. [`interrupt`：真正的人工介入 ⭐⭐⭐](#七interrupt真正的人工介入-)
8. [审批流程的完整实现 ⭐⭐](#八审批流程的完整实现-)
9. [人工编辑状态：修改后继续 ⭐](#九人工编辑状态修改后继续-)
10. [时间旅行与回放 ⭐](#十时间旅行与回放-)
11. [恢复的边界条件](#十一恢复的边界条件)
12. [Store 与 Checkpointer 的区别](#十二store-与-checkpointer-的区别)
13. [生产落地：存储、清理、隔离](#十三生产落地存储清理隔离)
14. [完整示例：退款审批系统](#十四完整示例退款审批系统)
15. [本章小结与练习](#本章小结与练习)

---

## 一、持久化解决哪三个问题

### 1.1 三个问题

| 问题 | 没有持久化 | 有持久化 |
| :--- | :--- | :--- |
| **多轮对话** | 每次重新传全部 messages | 传 `thread_id` 即可续上 |
| **人工审批** | 进程内 `while` 等，重启就丢 | 落盘挂起，任意时刻恢复 |
| **线上排查** | 只看到最终答案 | 回放每一步的输入输出 |

### 1.2 三个问题其实是一个

**它们都要求"状态"离开进程内存。** 一旦状态落到外部存储，这三个能力同时就都有了。

```text
进程内存里的 state
        ↓ 序列化
   ┌────────────┐
   │ Checkpoint │  ← 按 thread_id 存储
   └────────────┘
        ↓ 反序列化
再次执行 or 查看 or 恢复
```

### 1.3 关键认知

> 💡 **LangGraph 的持久化不是"存聊天记录"，而是"存图的每一步状态快照"**。
> 因此它既能恢复对话，也能恢复中断，还能回放历史——这是它和普通"聊天历史表"的根本区别。

---

## 二、Checkpointer 是什么

### 2.1 定义

**每个超步结束后，把完整 State 存一份快照，记下 `thread_id` 和 `checkpoint_id`。**

```text
thread_id = "u1001:conv-abc"
  ├── checkpoint_001  (START 之后)
  ├── checkpoint_002  (retrieve 之后)
  ├── checkpoint_003  (model 之后)
  └── checkpoint_004  (END)
```

### 2.2 最小配置

```python
from langgraph.checkpoint.memory import InMemorySaver

graph = builder.compile(checkpointer=InMemorySaver())

graph.invoke(
    {"messages": [("user", "你好")]},
    config={"configurable": {"thread_id": "t1"}},   # 必填！
)
```

**再调用一次就是多轮对话**：

```python
graph.invoke({"messages": [("user", "刚才我说了什么？")]},
             config={"configurable": {"thread_id": "t1"}})
```

> 💡 **第二次传入的 `messages` 会通过 `add_messages` 追加**，历史自动带上。这是"自动多轮"的来源。

### 2.3 它到底存了什么

```python
snapshot = graph.get_state(config)
print(snapshot.values)        # 当时的完整 State
print(snapshot.next)          # 下一步要去哪个节点（空元组=结束）
print(snapshot.metadata)      # step、source、writes
print(snapshot.config)        # 含 checkpoint_id
```

---

## 三、四种后端对比与选型 ⭐

### 3.1 对比

| 后端 | 包 | 持久 | 并发 | 适用 |
| :--- | :--- | :--- | :--- | :--- |
| `InMemorySaver` | 内置 | ❌ | 单进程 | 开发、测试 |
| `SqliteSaver` | `langgraph-checkpoint-sqlite` | ✅ | 单机 | 单机部署、桌面应用 |
| `PostgresSaver` | `langgraph-checkpoint-postgres` | ✅ | ✅ | **生产首选** |
| `RedisSaver` | `langgraph-checkpoint-redis` | ✅ | ✅ | 已有 Redis 的团队 |

### 3.2 代码

```python
# 开发
from langgraph.checkpoint.memory import InMemorySaver
saver = InMemorySaver()

# SQLite
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
saver = SqliteSaver(conn)

# Postgres（推荐）
from langgraph.checkpoint.postgres import PostgresSaver
DB_URI = "postgresql://user:pwd@localhost:5432/app"
with PostgresSaver.from_conn_string(DB_URI) as saver:
    saver.setup()          # 首次建表
    graph = builder.compile(checkpointer=saver)
```

**异步版本**：

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
async with AsyncPostgresSaver.from_conn_string(DB_URI) as saver:
    await saver.setup()
    graph = builder.compile(checkpointer=saver)
```

> ⚠️ **`from_conn_string` 是上下文管理器**，拿到的 saver 在 `with` 外不可用。生产上通常在应用启动时创建一次、全局复用，而不是每次请求都建连接。

### 3.3 选型建议

```text
开发阶段     → InMemorySaver
单机小工具   → SqliteSaver
已有 PostgreSQL → PostgresSaver
已有 Redis   → RedisSaver
需要审计/合规 → PostgresSaver + 外部归档
```

> 💡 **PostgresSaver 的额外好处**：可以 SQL 直接查到某个用户的所有会话、某个时间段的快照，方便做运营和审计。

---

## 四、thread_id：会话的主键 ⭐⭐

### 4.1 设计原则

**一个 `thread_id` 就是一条独立的会话线**。同一 `thread_id` 的调用，共享状态。

| 场景 | 推荐格式 |
| :--- | :--- |
| 单用户多会话 | `{user_id}:{conversation_id}` |
| 多租户 | `{tenant}:{user_id}:{conversation_id}` |
| 带渠道 | `{tenant}:{user_id}:{channel}:{conversation_id}` |
| 工单类 | `ticket:{ticket_id}` |
| 一次性任务 | `task:{uuid4()}` |

```python
def make_thread_id(tenant: str, user_id: str, channel: str, conv_id: str) -> str:
    return f"{tenant}:{user_id}:{channel}:{conv_id}"
```

### 4.2 反例

| ❌ 错误 | 后果 |
| :--- | :--- |
| 固定 `"default"` | 所有用户共享上下文，**串话 + 数据泄露** |
| 用 `user_id` 当 thread_id | 一个用户只有一个会话，无法新建会话 |
| 每次请求 `uuid4()` | 永远无法续接，**失去上下文** |
| 带特殊字符/超长 | 某些后端有长度限制 |

### 4.3 用户主动"新建对话"

```python
@app.post("/conversations")
def new_conversation(user_id: str):
    conv_id = uuid.uuid4().hex
    return {"thread_id": make_thread_id(TENANT, user_id, "web", conv_id)}
```

**"新建对话" = 换一个新的 `thread_id`。** 老数据还在，只是不再加载。

### 4.4 权限校验（关键）

```python
def authorize_thread(thread_id: str, request_user: str):
    parts = thread_id.split(":")
    if len(parts) < 4:
        raise HTTPException(400, "非法 thread_id")
    tenant, owner = parts[0], parts[1]
    if owner != request_user or tenant != TENANT:
        raise HTTPException(403, "无权访问该会话")
```

> ⚠️ **`thread_id` 由前端传 = 可伪造**。**必须服务端校验归属**，否则用户 A 能读到用户 B 的对话。

---

## 五、读状态：`get_state` / `get_state_history` ⭐

### 5.1 当前状态

```python
snap = graph.get_state(config)
snap.values        # dict，完整 State
snap.next          # tuple[str, ...]，下一步节点；() 表示已结束
snap.tasks         # 待执行任务
snap.metadata      # {"step": 3, "source": "loop", "writes": {...}}
```

**判断是否挂起**：

```python
snap = graph.get_state(config)
if snap.next:                 # 还有下一步 → 被中断或还没跑完
    print("等待中的节点：", snap.next)
```

### 5.2 历史

```python
for snap in graph.get_state_history(config):
    print(snap.metadata["step"], snap.next, snap.config["configurable"]["checkpoint_id"])
```

**新到旧排列**。可以用来：

- 展示"Agent 的决策过程"
- 定位"哪一步开始跑偏"
- 实现"回退到某个点重跑"

### 5.3 `checkpoint_id`

```python
config_with_cp = {"configurable": {
    "thread_id": tid,
    "checkpoint_id": "1ef7..."      # 指定历史快照
}}
snap = graph.get_state(config_with_cp)
```

> 💡 **带上 `checkpoint_id` 调用 `invoke` 就是从那个快照开始分支**（时间旅行）。

---

## 六、写状态：`update_state` 与"人工纠正"

### 6.1 直接改状态

```python
graph.update_state(
    config,
    {"status": "人工修正为已审核"},
    as_node="review",        # 假装是 review 节点写的
)
```

**`as_node` 很重要**：LangGraph 用它判断"下一步该去哪"（按 `review` 节点的出边走）。

### 6.2 使用场景

| 场景 | 做法 |
| :--- | :--- |
| 人工纠正模型输出 | `update_state({"draft": 修改后})` |
| 外部系统回填数据 | `update_state({"order_status": "已支付"})` |
| 强制跳过某步 | `as_node` 指定为跳转前节点 |
| 注入调试数据 | 开发时手动设置状态 |

### 6.3 与 reducer 的关系

**`update_state` 也会走 reducer**。对 `messages` 字段：

```python
graph.update_state(config, {"messages": [HumanMessage("人工插入一条")]})
# 是追加，不是替换
```

**要替换**，需要手动清空或用特殊值。

> ⚠️ **`update_state` 会写入新的 checkpoint**，历史里能查到"这是人工改的"。生产上建议记录操作人和原因。

---

## 七、`interrupt`：真正的人工介入 ⭐⭐⭐

### 7.1 为什么需要

**软审批（第 06 篇中间件返回拒绝消息）不够**：

- 模型可能换个说法再试
- 无法"等真人"几小时
- 进程重启就没了

**`interrupt` 做的是硬暂停**：把状态落盘，退出执行，等人来恢复。

### 7.2 基本用法

```python
from langgraph.types import interrupt, Command

def approval_node(state: State) -> dict:
    # 执行到这里会抛出一个特殊的中断，图停止
    decision = interrupt({
        "question": "是否批准该退款？",
        "order_no": state["order_no"],
        "amount": state["amount"],
    })
    # ↓ 恢复后，decision 就是 resume 传进来的值
    return {"approved": decision["approved"]}
```

**调用方**：

```python
cfg = {"configurable": {"thread_id": "t1"}}

# 第一次：跑到 interrupt 停住
state = graph.invoke({"order_no": "12345"}, cfg)

# 检查是否中断
snapshot = graph.get_state(cfg)
for task in snapshot.tasks:
    for itr in task.interrupts:
        print(itr.value)      # {"question": "...", "order_no": "...", "amount": ...}

# 恢复
state = graph.invoke(Command(resume={"approved": True}), cfg)
```

### 7.3 心智模型

```text
invoke(inputs)
   │
   ├─ 节点执行 …
   ├─ 遇到 interrupt(value)
   │     └─ 存 checkpoint，抛出 GraphInterrupt，退出
   ▼
（进程空闲，可以几分钟、几天）
   │
invoke(Command(resume=answer))
   │
   ├─ 从 checkpoint 恢复
   ├─ 重新执行那个节点（从头！）
   ├─ interrupt() 这次直接返回 answer，不抛异常
   ▼
继续执行
```

> ⚠️ **关键：`interrupt` 所在的节点，恢复时会从头重新执行**。
> 所以 **`interrupt` 之前的所有代码会再跑一遍**。有副作用的操作（写库、发消息）必须放在 `interrupt` **之后**，或者做幂等。

```python
def bad_node(state):
    order_service.lock(state["order_no"])     # ❌ 恢复时会再锁一次
    decision = interrupt({...})
    ...

def good_node(state):
    decision = interrupt({...})                # ✅ 先在纯计算位置中断
    order_service.lock(state["order_no"])      # 恢复后才执行
```

### 7.4 多次中断

```python
def multi_step_node(state):
    name = interrupt({"ask": "请输入姓名"})
    age = interrupt({"ask": "请输入年龄"})
    return {"name": name, "age": age}
```

**每次 `invoke(Command(resume=...))` 恢复一个**。LangGraph 用"已恢复次数"来区分。

> 💡 **实际项目更推荐"一个节点一次 interrupt"**，多次中断的调试成本高。

### 7.5 `interrupt` 的返回值类型

**可以是任何可序列化对象**：dict、list、字符串、`Pydantic` 模型。

```python
# 用 Pydantic 让前端更好处理
from pydantic import BaseModel

class ApprovalRequest(BaseModel):
    type: str = "approval"
    title: str
    fields: list[dict]

def approve(state):
    result = interrupt(ApprovalRequest(
        title="退款审批",
        fields=[{"key": "amount", "label": "金额", "value": state["amount"]}],
    ).model_dump())
    return {"approved": result["approved"]}
```

---

## 八、审批流程的完整实现 ⭐⭐

### 8.1 后端

```python
# approval.py
import uuid
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import interrupt, Command
from langchain_core.messages import AnyMessage, AIMessage


class ApprovalState(TypedDict):
    request_id: str
    order_no: str
    amount: float
    risk: str
    decision: dict | None
    messages: Annotated[list[AnyMessage], add_messages]


def check_node(state: ApprovalState) -> dict:
    detail = order_service.get(state["order_no"])
    amount = detail.amount
    risk = "high" if amount > 5000 else "low"
    return {"amount": amount, "risk": risk}


def human_node(state: ApprovalState) -> dict:
    result = interrupt({
        "type": "approval",
        "request_id": state["request_id"],
        "order_no": state["order_no"],
        "amount": state["amount"],
        "risk": state["risk"],
    })
    return {"decision": result,
            "messages": [AIMessage(f"审批：{'通过' if result.get('approved') else '驳回'}")]}


def route(state: ApprovalState) -> Literal["execute", "reject"]:
    return "execute" if (state.get("decision") or {}).get("approved") else "reject"


def execute_node(state: ApprovalState) -> dict:
    order_service.refund(state["order_no"], state["amount"],
                         idempotency_key=f"approve:{state['request_id']}")
    return {"messages": [AIMessage("已执行退款")]}


def reject_node(state: ApprovalState) -> dict:
    return {"messages": [AIMessage("已驳回")]}


def build(saver):
    b = StateGraph(ApprovalState)
    b.add_node("check", check_node)
    b.add_node("human", human_node)
    b.add_node("execute", execute_node)
    b.add_node("reject", reject_node)
    b.add_edge(START, "check")
    b.add_edge("check", "human")
    b.add_conditional_edges("human", route, {"execute": "execute", "reject": "reject"})
    b.add_edge("execute", END)
    b.add_edge("reject", END)
    return b.compile(checkpointer=saver)
```

### 8.2 提交与恢复的 API

```python
@app.post("/approvals")
def create_approval(req: ApprovalReq, user=Depends(current_user)):
    thread_id = f"approval:{uuid.uuid4().hex}"
    cfg = {"configurable": {"thread_id": thread_id}}
    graph.invoke({"request_id": thread_id, "order_no": req.order_no}, cfg)

    snap = graph.get_state(cfg)
    payload = next(
        (i.value for t in snap.tasks for i in t.interrupts), None
    )
    return {"thread_id": thread_id, "status": "pending", "payload": payload}


@app.post("/approvals/{thread_id}/decide")
def decide(thread_id: str, body: DecideReq, user=Depends(admin_user)):
    # 幂等：已处理过就返回当前结果
    snap = graph.get_state({"configurable": {"thread_id": thread_id}})
    if not snap.next:
        return {"status": "already_done", "state": snap.values}

    graph.invoke(
        Command(resume={"approved": body.approved, "operator": user.id,
                        "comment": body.comment}),
        {"configurable": {"thread_id": thread_id}},
    )
    return {"status": "done"}
```

### 8.3 前端轮询 vs 推送

```python
# 轮询
@app.get("/approvals/{thread_id}")
def get_status(thread_id: str):
    snap = graph.get_state({"configurable": {"thread_id": thread_id}})
    if snap.next:
        payload = next((i.value for t in snap.tasks for i in t.interrupts), None)
        return {"status": "pending", "payload": payload}
    return {"status": "done", "result": snap.values.get("messages", [])[-1].content}
```

> ⚠️ **`invoke` 返回时线程已经结束**，所以 `create_approval` 里能立刻读到 `interrupt` 的 payload。但如果用 `astream`，要读到 `__interrupt__` 事件才停。

### 8.4 超时自动处理

```python
async def expire_pending_approvals():
    """定时任务：超过 24 小时未处理的自动驳回。"""
    rows = db.query("SELECT thread_id FROM pending_approvals WHERE created_at < now() - interval '24 hours'")
    for tid in rows:
        cfg = {"configurable": {"thread_id": tid}}
        snap = graph.get_state(cfg)
        if snap.next:
            graph.invoke(Command(resume={"approved": False, "reason": "超时自动驳回"}), cfg)
```

> 💡 **超时处理必须做**。否则挂起的会话永远占着，且用户不知道结果。

---

## 九、人工编辑状态：修改后继续 ⭐

### 9.1 场景

Agent 生成了草稿，人工改了几个字，然后再继续。

```python
# 在草稿节点之后暂停
graph = builder.compile(
    checkpointer=saver,
    interrupt_after=["draft"],       # 这个节点执行完就停
)

# 跑到 draft 后停住
graph.invoke({"query": "..."}, cfg)

# 人工修改
graph.update_state(cfg, {"draft": "人工改过的版本"}, as_node="draft")

# 继续
graph.invoke(None, cfg)      # 传 None 表示"用现有状态继续"
```

> 💡 **`invoke(None, config)` 是"继续执行"的标准写法**。等价于不带新输入地恢复。

### 9.2 `interrupt_before` / `interrupt_after`

```python
graph.compile(
    checkpointer=saver,
    interrupt_before=["execute"],    # 这个节点执行前停
    interrupt_after=["generate"],    # 这个节点执行后停
)
```

| | 适合 |
| :--- | :--- |
| `interrupt_before` | 危险操作前拦一道（执行前审批） |
| `interrupt_after` | 结果出来先给人看（草稿审阅） |
| 节点内 `interrupt()` | 需要传自定义 payload、需要清楚拿到返回值 |

> ⚠️ **`interrupt_before/after` 是静态的（编译期配置）**；`interrupt()` 是动态的（运行期决定是否中断，可以带条件）。**生产上做审批优选 `interrupt()`**。

---

## 十、时间旅行与回放 ⭐

### 10.1 回放到某个快照

```python
# 找到某个历史点
target = None
for snap in graph.get_state_history(cfg):
    if snap.metadata["step"] == 5:
        target = snap
        break

# 从该点重跑
result = graph.invoke(
    None,
    {"configurable": {
        "thread_id": cfg["configurable"]["thread_id"],
        "checkpoint_id": target.config["configurable"]["checkpoint_id"],
    }},
)
```

### 10.2 分叉：改一个值重跑

```python
# 从某个点，注入不同的输入，跑出一个新分支
new_cfg = graph.update_state(
    {"configurable": {"thread_id": tid,
                      "checkpoint_id": target_cp_id}},
    {"query": "换个说法再试一次"},
)
graph.invoke(None, new_cfg)
```

> 💡 **这就是"what-if 实验"**。可以在不影响主线的历史的前提下，测试"如果当时用户说的是另一句话会怎样"。

### 10.3 回放的用途

| 用途 | 做法 |
| :--- | :--- |
| 复现 bug | 拿到 `thread_id` + `checkpoint_id` 本地重放 |
| 评估改动的效果 | 同一批快照，用新 Prompt 重跑 |
| 训练/标注 | 导出历史轨迹做微调或评测集 |
| 客服复盘 | 展示"机器人当时做了什么" |

> ⚠️ **回放会重新执行节点，可能有副作用**。涉及写操作的，务必用"只读模式"（换一个 `checkpointer` 或 mock 工具）重放。

---

## 十一、恢复的边界条件

### 11.1 常见问题

| 问题 | 原因 | 解决 |
| :--- | :--- | :--- |
| `Command(resume=...)` 报错 | 不是中断状态 | 先 `get_state().next` 检查 |
| 恢复后重复执行副作用 | `interrupt` 前有写操作 | 副作用后置 + 幂等键 |
| 恢复后模型又说一遍同样的话 | 消息重复追加 | 检查是否手动又传了一遍 messages |
| 换了代码后恢复失败 | 节点/边变了 | checkpoint 与图结构不兼容；升级时做迁移 |
| 恢复超时 | 节点内有长同步任务 | 异步节点 + 超时 |

### 11.2 代码升级的兼容性

> ⚠️ **修改图结构（加/删节点、改 State 字段）可能导致旧 checkpoint 无法恢复。**
> 生产建议：
> 1. State 只增字段，不删不改名
> 2. 新增字段给默认值（节点里 `.get("x", default)`）
> 3. 大改版时，用新的 `thread_id` 前缀或做数据迁移

### 11.3 恢复的幂等

```python
def execute_node(state):
    key = f"refund:{state['order_no']}"
    existing = order_service.find_refund(key)
    if existing:
        return {"refund_id": existing.id}      # 已经做过，直接返回
    return {"refund_id": order_service.refund(..., idempotency_key=key)}
```

> 💡 **任何 `interrupt` 之后的写操作，都应当幂等**。这是恢复逻辑能安全重试的前提。

### 11.4 未完成的会话清理

```sql
-- Postgres：找出挂起超过 7 天的会话
SELECT thread_id, MAX(created_at) AS last_active
FROM checkpoints
GROUP BY thread_id
HAVING MAX(created_at) < now() - interval '7 days';
```

---

## 十二、Store 与 Checkpointer 的区别

很多人会问："都有持久化了，为什么还要 Store？"

### 12.1 对比

| | Checkpointer | Store |
| :--- | :--- | :--- |
| 作用域 | 单个 `thread_id` | 跨线程、跨会话 |
| 内容 | 图的完整 State 快照 | 键值对（JSON + 可选向量） |
| 生命周期 | 会话结束可删 | 长期保留 |
| 典型用途 | 对话续接、中断恢复、回放 | 用户画像、偏好、知识 |
| 键 | `thread_id` | `namespace` + `key` |

### 12.2 配合使用

```python
# Checkpointer：这次对话的过程
graph.invoke(inputs, {"configurable": {"thread_id": "t1"}})

# Store：跨对话的长期记忆
def remember_node(state, runtime: Runtime):
    runtime.store.put(("user_profile",), "u1001", {"name": "张三", "vip": True})
    profile = runtime.store.get(("user_profile",), "u1001")
    return {"messages": [AIMessage(f"你好 {profile.value['name']}")]}
```

```python
from langgraph.store.memory import InMemoryStore
from langgraph.store.postgres import PostgresStore

store = InMemoryStore()      # 开发
graph = builder.compile(checkpointer=saver, store=store)
```

> 💡 **一句话区分**：**Checkpointer 存"这次怎么跑的"，Store 存"这个人是谁"**。

### 12.3 Store 的语义搜索

```python
store.put(("memories", "u1001"), "m1", {"text": "用户喜欢简洁回答"},
          index=["text"])       # 建向量索引

hits = store.search(("memories", "u1001"), query="回答风格", limit=5)
```

---

## 十三、生产落地：存储、清理、隔离

### 13.1 存储增长

**checkpoint 会存每一步的完整 State**，长会话很容易膨胀：

```text
60 轮对话 × 每轮 3–5 个 checkpoint × 5–20KB = 数十 MB
```

### 13.2 治理手段

| 手段 | 做法 |
| :--- | :--- |
| **裁剪 State** | 定期把老消息摘要成一段（`SummarizationMiddleware`） |
| **限制会话长度** | 超过 N 轮强制新建 thread |
| **定期清理** | 定时任务删除 N 天前的 thread |
| **归档** | 冷数据转对象存储 |
| **拆分 thread** | 按"话题"切分，而不是按"用户" |

```sql
-- 清理 30 天前的会话
DELETE FROM checkpoints WHERE thread_id IN (
  SELECT thread_id FROM checkpoints
  GROUP BY thread_id HAVING MAX(created_at) < now() - interval '30 days'
);
```

> ⚠️ **注意 checkpoints / checkpoint_blobs / checkpoint_writes 三张表**，要按依赖顺序清理或级联删除。

### 13.3 隔离

| 层级 | 做法 |
| :--- | :--- |
| 数据隔离 | 多租户按 `tenant` 前缀 + 行级校验 |
| 连接隔离 | 每租户独立库（强隔离要求时） |
| 加密 | 敏感字段加密后入 State |
| 访问控制 | 查询接口必须校验 thread 归属 |

### 13.4 监控指标

```text
- 挂起的会话数（interrupt 未恢复）
- 平均恢复时延
- checkpoint 表大小增长速率
- 每会话超步数分布（找异常长尾）
```

---

## 十四、完整示例：退款审批系统

```python
# refund_system.py
import os, uuid
from typing import Annotated, Literal, TypedDict
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import interrupt, Command
from langchain_core.messages import AnyMessage, AIMessage

DB = os.getenv("PG_URI")
app = FastAPI()


class St(TypedDict):
    order_no: str
    amount: float
    risk: str
    decision: dict | None
    refund_id: str | None
    messages: Annotated[list[AnyMessage], add_messages]


def check(state: St) -> dict:
    d = order_service.get(state["order_no"])
    if not d or d.status not in ("已发货", "已完成"):
        return {"risk": "invalid"}
    return {"amount": d.amount, "risk": "high" if d.amount > 5000 else "low"}


def wait_human(state: St) -> dict:
    if state["risk"] == "invalid":
        return {"decision": {"approved": False, "reason": "订单不可退款"}}

    ans = interrupt({
        "type": "refund_approval",
        "order_no": state["order_no"],
        "amount": state["amount"],
        "risk": state["risk"],
    })
    return {"decision": ans}


def route(state: St) -> Literal["execute", "reject"]:
    return "execute" if (state.get("decision") or {}).get("approved") else "reject"


def execute(state: St) -> dict:
    key = f"refund:{state['order_no']}"
    rid = order_service.refund(state["order_no"], state["amount"], idempotency_key=key)
    return {"refund_id": rid,
            "messages": [AIMessage(f"退款已提交，单号 {rid}")]}


def reject(state: St) -> dict:
    reason = (state.get("decision") or {}).get("reason", "未通过审核")
    return {"messages": [AIMessage(f"退款未通过：{reason}")]}


def build():
    b = StateGraph(St)
    b.add_node("check", check)
    b.add_node("wait_human", wait_human)
    b.add_node("execute", execute)
    b.add_node("reject", reject)
    b.add_edge(START, "check")
    b.add_edge("check", "wait_human")
    b.add_conditional_edges("wait_human", route,
                            {"execute": "execute", "reject": "reject"})
    b.add_edge("execute", END)
    b.add_edge("reject", END)
    return b


saver_ctx = PostgresSaver.from_conn_string(DB)
saver = saver_ctx.__enter__()
saver.setup()
graph = build().compile(checkpointer=saver)


class CreateReq(BaseModel):
    order_no: str


class DecideReq(BaseModel):
    approved: bool
    comment: str | None = None


@app.post("/refunds")
def create(req: CreateReq, user: str = Depends(current_user)):
    tid = f"refund:{user}:{uuid.uuid4().hex[:12]}"
    cfg = {"configurable": {"thread_id": tid}}
    graph.invoke({"order_no": req.order_no}, cfg)

    snap = graph.get_state(cfg)
    payload = next((i.value for t in snap.tasks for i in t.interrupts), None)
    if payload:
        db.insert_pending(tid, req.order_no, payload)
        return {"thread_id": tid, "status": "pending", "payload": payload}
    return {"thread_id": tid, "status": "done",
            "message": snap.values["messages"][-1].content}


@app.post("/refunds/{tid}/decide")
def decide(tid: str, body: DecideReq, admin: str = Depends(current_admin)):
    check_owner(tid, admin)
    cfg = {"configurable": {"thread_id": tid}}
    snap = graph.get_state(cfg)

    if not snap.next:                       # 已处理，幂等返回
        return {"status": "already_done",
                "message": snap.values["messages"][-1].content}

    graph.invoke(Command(resume={"approved": body.approved,
                                 "reason": body.comment,
                                 "operator": admin}), cfg)
    db.mark_pending_done(tid)

    final = graph.get_state(cfg).values
    return {"status": "done",
            "refund_id": final.get("refund_id"),
            "message": final["messages"][-1].content}


@app.get("/refunds/{tid}")
def status(tid: str, user: str = Depends(current_user)):
    check_owner(tid, user)
    snap = graph.get_state({"configurable": {"thread_id": tid}})
    if snap.next:
        payload = next((i.value for t in snap.tasks for i in t.interrupts), None)
        return {"status": "pending", "payload": payload}
    return {"status": "done", "message": snap.values["messages"][-1].content}
```

### 14.1 设计要点

| 要点 | 说明 |
| :--- | :--- |
| `thread_id` 含用户 | 天然隔离 |
| `decide` 幂等 | 重复点击不重复退款 |
| 副作用放在 `interrupt` 之后 | 恢复时不会重复 |
| 幂等键 `refund:{order_no}` | 底层兜底 |
| `pending_approvals` 表 | 方便运营查待办、做超时 |
| `check_owner` | 防越权 |

---

## 十五、本章小结与练习

### 核心结论

1. **Checkpointer 存的是"每一步的 State 快照"**，因此同时解决多轮、中断、回放三件事。
2. **`thread_id` 是会话主键**，格式要能表达租户/用户/渠道，且**必须服务端校验归属**。
3. **`interrupt()` 是硬暂停**：落盘退出，可跨重启恢复；**恢复时该节点从头重跑**。
4. **`interrupt` 之前不写副作用**，之后的写操作必须幂等。
5. **`Command(resume=...)` 恢复**，`invoke(None, cfg)` 是"继续执行"。
6. **`update_state` + `as_node`** 可人工纠正状态，也会写入 checkpoint。
7. **`checkpoint_id` 支持时间旅行和 what-if 分支**，回放前注意副作用。
8. **Store 管长期记忆（用户是谁），Checkpointer 管过程（这次怎么跑的）**。
9. **State 只增不删**，保证跨版本可恢复。
10. **checkpoint 会膨胀**，必须有清理策略和监控。

### 动手练习

1. 把第 07 篇的图加上 `InMemorySaver`，验证同一 `thread_id` 两次 invoke 能续上上下文。
2. 换成 `PostgresSaver`，重启进程后验证会话仍在。
3. 实现"新建对话"接口：返回新的 `thread_id`，验证老会话不受影响。
4. 用 `interrupt` 做一个审批节点，写一个 `/decide` 接口，重复调用验证幂等。
5. 故意在 `interrupt` 之前加一个"写数据库"操作，观察恢复时执行了两次，然后修复。
6. 用 `get_state_history` 列出所有快照，挑一个 `checkpoint_id` 从那里重跑。
7. 用 `interrupt_after` 实现"草稿审阅"，用 `update_state` 改草稿后继续。
8. 写一个清理任务，删除 30 天前的 checkpoint，先数一下表有多大。

### 下一篇

[09 - 多 Agent 协作模式](09-多Agent协作模式.md) —— 当一个 Agent 的提示词已经写了两千字时，该拆了。
