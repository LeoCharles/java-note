# 06 - 第一个 Agent 与 ReAct 循环

> 前面几篇，模型的角色是"输入 → 输出"。这一篇，模型开始**自己决定下一步做什么**。
> Agent 的魅力在于"它能自己想办法"，危险也在于同一件事。
> 本篇用 `create_agent` 十分钟跑起来，然后**把它的黑盒拆开看**——理解循环、停止条件、中间件，以及它什么时候会失控。

---

## 📖 目录

1. [Agent 与普通调用的本质区别](#一agent-与普通调用的本质区别)
2. [ReAct：思考-行动-观察](#二react思考-行动-观察)
3. [用 `create_agent` 十分钟跑起来 ⭐](#三用-create_agent-十分钟跑起来-)
4. [把黑盒拆开：它就是一张图 ⭐⭐](#四把黑盒拆开它就是一张图-)
5. [中间件：在循环中插入你的逻辑 ⭐⭐](#五中间件在循环中插入你的逻辑-)
6. [流式观察 Agent 在干什么 ⭐](#六流式观察-agent-在干什么-)
7. [控制循环：步数、成本、终止](#七控制循环步数成本终止)
8. [工具路由：如何不让模型在 30 个工具里乱选](#八工具路由如何不让模型在-30-个工具里乱选)
9. [常见失败模式与修复 ⭐⭐](#九常见失败模式与修复-)
10. [调试 Agent 的方法论](#十调试-agent-的方法论)
11. [什么时候该放弃 create_agent](#十一什么时候该放弃-create_agent)
12. [完整示例：订单售后 Agent](#十二完整示例订单售后-agent)
13. [本章小结与练习](#本章小结与练习)

---

## 一、Agent 与普通调用的本质区别

### 1.1 三条代码线

```python
# ① 单次调用：你决定一切
answer = model.invoke("帮我查订单 12345 的状态")

# ② 工具调用：你决定"可以调什么"，模型决定"调不调"
resp = model.bind_tools([get_order]).invoke("帮我查订单 12345 的状态")

# ③ Agent：模型决定"调什么、调几次、什么时候停"
agent = create_agent(model, tools=[get_order, refund_order, search_kb])
result = agent.invoke({"messages": [("user", "帮我查订单 12345，有问题就退款")]})
```

**差别在哪**：`result` 里有多少步、调了哪些工具、顺序如何——**在运行之前你并不知道**。

### 1.2 控制权转移

| | 普通程序 | Agent |
| :--- | :--- | :--- |
| 分支 | 你写 `if` | 模型决定 |
| 循环 | 你写 `for/while` | 模型决定是否继续 |
| 终止 | 你写 `return` | 模型判断"可以回答了" |
| 错误处理 | 你写 `catch` | 你写 + 模型自适应 |

> 💡 **理解成"把控制流交给了模型"就够了**。所有 Agent 工程的难点——可观测、可测试、可回滚、限权——都源自这一句话。

### 1.3 适合与不适合

| 适合 Agent | 不适合 Agent |
| :--- | :--- |
| 需要动态选择工具 | 流程固定（用工作流/状态图更稳） |
| 步骤数不确定 | 步骤可枚举 |
| 需要根据中间结果调整 | 每个分支都已知 |
| 探索型任务（研究、排查） | 高确定性要求（对账、计费） |

> ⚠️ **"用 Agent 做一个分类"是典型的过度设计**。分类用一次结构化输出就够了。

---

## 二、ReAct：思考-行动-观察

### 2.1 原始论文的思路

**ReAct = Reasoning + Acting**。让模型交替输出"思考"和"行动"：

```text
思考：用户想知道订单状态，我需要调用订单查询工具。
行动：get_order(order_no="12345")
观察：{"status": "已发货", "carrier": "顺丰", "tracking": "SF123"}

思考：用户还问能不能退款，订单是"已发货"，符合退款条件，但需要用户确认金额。
行动：向用户确认退款金额
```

### 2.2 现代实现其实是"工具调用循环"

今天的模型通过 **Function Calling** 实现 ReAct，不需要在 Prompt 里教它输出 `Thought:/Action:` 格式：

```text
循环:
  response = model(messages, tools)
  if response.tool_calls:
      for call in response.tool_calls:
          result = execute(call)
          messages.append(ToolMessage(result, call.id))
      continue          # 再问模型
  else:
      return response.content     # 结束
```

**"思考"去哪了？** 部分模型（如带推理能力的模型）会在内部产生 reasoning content；普通模型则把"思考"隐含在 `tool_calls` 的选择里。

> 💡 **想要显式的思考过程**，可以在系统提示里要求："在调用工具前，先用一句话说明你为什么调用它。"这能显著改善可调试性。

### 2.3 停止条件

模型什么时候停？**当它返回没有 `tool_calls` 的回复时。** 除此之外，你必须自己加：

| 停止条件 | 实现 |
| :--- | :--- |
| 模型认为可以回答 | 天然条件 |
| 达到最大步数 | `max_steps` / `recursion_limit` |
| 成本超预算 | 中间件统计 token |
| 检测到重复调用 | 对比最近 N 次工具名+参数 |
| 命中危险操作 | 中断，转人工 |
| 超时 | 外部 `asyncio.wait_for` |

> ⚠️ **只靠"模型自己停"是不够的**。模型可能陷入循环（反复调同一个工具）。**必须有外部硬性上限。**

---

## 三、用 `create_agent` 十分钟跑起来 ⭐

### 3.1 最小示例

```python
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.tools import tool

load_dotenv()

model = init_chat_model("gpt-4o-mini", temperature=0)


@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。用户询问天气、气温、是否下雨时使用。"""
    return f"{city}：晴，18~26℃"


agent = create_agent(
    model=model,
    tools=[get_weather],
    system_prompt="你是一个简洁的助手。",
)

result = agent.invoke({"messages": [("user", "北京和上海今天天气怎么样？")]})
print(result["messages"][-1].content)
```

**输出**：`北京晴，18~26℃；上海晴，18~26℃。`

### 3.2 返回结构

```python
{
    "messages": [
        HumanMessage("北京和上海今天天气怎么样？"),
        AIMessage(tool_calls=[get_weather(北京), get_weather(上海)]),
        ToolMessage("北京：晴，18~26℃", tool_call_id="call_1"),
        ToolMessage("上海：晴，18~26℃", tool_call_id="call_2"),
        AIMessage("北京晴，18~26℃；上海晴，18~26℃。"),
    ]
}
```

> 💡 **`result["messages"]` 是最重要的调试入口**。它完整记录了 Agent 的"思考轨迹"。生产上建议把它连同 `thread_id`、`user_id` 一起落库。

### 3.3 常用参数

```python
agent = create_agent(
    model=model,                      # 必需
    tools=[...],                      # 工具列表
    system_prompt="...",              # 系统提示
    checkpointer=saver,               # 记忆（第 05 篇）
    middleware=[...],                 # 中间件（见第五节）
    state_schema=MyState,             # 自定义状态（高级）
    response_format=MySchema,         # 结构化最终输出
    name="order_agent",               # 追踪里显示的名字
)
```

```python
result = agent.invoke(
    {"messages": [("user", "...")]},
    config={
        "configurable": {"thread_id": "u1001"},
        "recursion_limit": 25,                # 最大递归步数
        "tags": ["prod", "order"],
        "metadata": {"user_id": "u1001"},
    },
)
```

### 3.4 `recursion_limit` 的含义

LangGraph 用"超步"计数。每次"模型节点 + 工具节点"算一次。超过就抛 `GraphRecursionError`。

```python
from langgraph.errors import GraphRecursionError

try:
    agent.invoke(inputs, config={"recursion_limit": 15})
except GraphRecursionError:
    # 兜底：返回"任务复杂，已转人工"
    ...
```

> ⚠️ **默认值通常偏大**（25 左右）。实际业务建议设 **8–12**，超出说明工具或描述有问题。

---

## 四、把黑盒拆开：它就是一张图 ⭐⭐

`create_agent` 在内部**就是编译好的 LangGraph 图**。理解这张图，第 07 篇就顺理成章了。

### 4.1 结构

```text
        START
          │
          ▼
   ┌─────────────┐
   │  model 节点  │◀──────────┐
   └──────┬──────┘           │
          │                  │
   有 tool_calls?            │
      │        │             │
    是│        │否           │
      ▼        ▼             │
 ┌─────────┐  END            │
 │ tools 节点│───────────────┘
 └─────────┘
```

**翻译成代码**：

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def call_model(state: AgentState):
    resp = model.bind_tools(tools).invoke(
        [SystemMessage("你是简洁的助手。")] + state["messages"]
    )
    return {"messages": [resp]}


def call_tools(state: AgentState):
    last = state["messages"][-1]
    results = []
    for tc in last.tool_calls:
        fn = TOOL_MAP[tc["name"]]
        out = fn.invoke(tc["args"])
        results.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
    return {"messages": results}


def should_continue(state: AgentState):
    return "tools" if state["messages"][-1].tool_calls else END


builder = StateGraph(AgentState)
builder.add_node("model", call_model)
builder.add_node("tools", call_tools)
builder.add_edge(START, "model")
builder.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
builder.add_edge("tools", "model")          # 回到模型

graph = builder.compile()
```

### 4.2 为什么值得看这段代码

| 你困扰的问题 | 在这段代码里的答案 |
| :--- | :--- |
| 为什么它会循环？ | `tools → model` 这条边 |
| 它什么时候停？ | `should_continue` 返回 `END` |
| 我能在中间加逻辑吗？ | 加节点、改边、或加中间件 |
| 为什么消息会累积？ | `add_messages` reducer |
| 怎么让它先检索再回答？ | 在 `call_model` 之前插入检索节点 |

> 💡 **第 07 篇会把这段代码讲透**。现在你只需知道：**`create_agent` 不是什么魔法，就是一个"模型↔工具"的循环图。**

### 4.3 和手写循环的对比

| | 手写循环（03 篇 5.1） | `create_agent` |
| :--- | :--- | :--- |
| 代码量 | 30 行 | 3 行 |
| 记忆 | 自己做 | `checkpointer` 一行 |
| 流式 | 自己做 | 原生支持 |
| 中断恢复 | 很难 | 原生支持 |
| 可观测 | 自己打日志 | 自动接追踪 |
| 定制 | 随意 | 通过中间件 / 自定义图 |

---

## 五、中间件：在循环中插入你的逻辑 ⭐⭐

### 5.1 中间件解决什么

在"模型调用"和"工具调用"的前后，你总需要插一些逻辑：

- 日志、埋点、计时
- 动态注入上下文（用户信息、当前时间）
- 上下文压缩
- 敏感词过滤
- 工具调用审批
- 重试、降级
- 预算控制

**没有中间件时**，你只能改 Agent 源码或写一堆 wrapper。**中间件就是 Agent 的 AOP。**

### 5.2 五种钩子

```python
from langchain.agents.middleware import (
    before_agent,      # Agent 开始前（整个会话一次）
    before_model,      # 每次调模型前
    after_model,       # 每次模型返回后
    wrap_model_call,   # 包裹模型调用（可重试、可缓存）
    wrap_tool_call,    # 包裹工具调用（可审批、可重试）
)
```

```text
before_agent
   └─ 循环 {
        before_model → [model] → after_model
                                        ↓
                                  有 tool_calls?
                                        ↓
                              wrap_tool_call → [tool]
      }
```

### 5.3 示例：动态注入当前时间与用户信息

```python
from dataclasses import dataclass
from langchain.agents.middleware import before_model
from langchain.agents import AgentState
from langgraph.runtime import Runtime
from langchain_core.messages import SystemMessage

@dataclass
class Context:
    user_id: str
    user_name: str
    tenant: str

@before_model
def inject_context(state: AgentState, runtime: Runtime[Context]):
    ctx = runtime.context
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "messages": [
            SystemMessage(f"当前时间：{now}；当前用户：{ctx.user_name}（ID={ctx.user_id}）")
        ] + list(state["messages"])
    }

agent = create_agent(model, tools, middleware=[inject_context])

result = agent.invoke(
    {"messages": [("user", "现在几点了？")]},
    context=Context(user_id="u1001", user_name="张三", tenant="t1"),
)
```

> ⚠️ **每次 `before_model` 注入的消息会累积**。上面写法每次都插一条，多轮后会重复。**更好的做法是替换而非追加**，或只在首轮注入。

### 5.4 示例：工具调用审批

```python
from langchain.agents.middleware import wrap_tool_call

DANGEROUS = {"refund_order", "delete_user", "send_email"}

@wrap_tool_call
def require_approval(request, handler):
    tool_name = request.tool_call["name"]
    if tool_name in DANGEROUS:
        approved = request.runtime.context.approved_tools   # 由外部传入
        if tool_name not in approved:
            return ToolMessage(
                content=f"操作「{tool_name}」需要人工确认，已暂停。",
                tool_call_id=request.tool_call["id"],
            )
    return handler(request)
```

> 💡 **这是"软审批"**：返回一条拒绝消息，让模型告诉用户"需要确认"。
> **"硬审批"**（真的暂停、等后台批准后继续）要用 LangGraph 的 `interrupt`，见第 08 篇。

### 5.5 示例：循环检测

```python
from langchain.agents.middleware import after_model

@after_model
def detect_loop(state: AgentState, runtime):
    last = state["messages"][-1]
    if not getattr(last, "tool_calls", None):
        return None

    sig = tuple((tc["name"], json.dumps(tc["args"], sort_keys=True))
                for tc in last.tool_calls)

    seen = runtime.context.get("_recent_sigs", [])
    if sig in seen[-2:]:
        return {"jump_to": "end",
                "messages": [AIMessage("检测到重复操作，已停止。请补充更多信息或转人工。")]}
    seen.append(sig)
    return None
```

### 5.6 示例：上下文压缩

```python
from langchain.agents.middleware import SummarizationMiddleware

middleware = [
    SummarizationMiddleware(
        model=small_model,               # 用便宜模型做摘要
        max_tokens_before_summary=4000,
        messages_to_keep=10,
    )
]
```

### 5.7 内置中间件一览（LangChain 1.x 常见）

| 中间件 | 作用 |
| :--- | :--- |
| `SummarizationMiddleware` | 上下文超限时自动摘要 |
| `HumanInTheLoopMiddleware` | 危险工具暂停等审批 |
| `ModelCallLimitMiddleware` | 限制模型调用次数 |
| `ToolCallLimitMiddleware` | 限制工具调用次数 |
| `PIIMiddleware` | 脱敏（手机号、身份证等） |
| `TodoListMiddleware` | 让 Agent 维护任务清单（规划类任务） |
| `ToolRetryMiddleware` | 工具失败重试 |

> ⚠️ **版本提示**：中间件的具体名称与参数在不同小版本间有调整。用之前先确认：
> ```python
> from langchain.agents import middleware as mw
> print([n for n in dir(mw) if not n.startswith("_")])
> ```

### 5.8 中间件的顺序

```python
agent = create_agent(model, tools, middleware=[
    mw_pii,          # 最先：先脱敏
    mw_limit,        # 其次：先判断额度
    mw_retry,        # 包裹调用
    mw_summarize,    # 最后：内容已过滤再压缩
])
```

> ⚠️ **顺序会改变行为**。例如脱敏必须在"带入模型"之前，限额必须在"真正调用"之前。**把顺序当成设计的一部分，不要随手加。**

---

## 六、流式观察 Agent 在干什么 ⭐

### 6.1 问题

Agent 跑 20 秒，用户看到的是什么？空白。

**必须让用户看到进度**：`正在检索…` → `找到 3 篇文档` → `正在查询订单…` → 逐字回答。

### 6.2 用 `stream` 拿状态快照

```python
for chunk in agent.stream(
    {"messages": [("user", "帮我查订单 12345 并处理退款")]},
    stream_mode="updates",
):
    for node, update in chunk.items():
        print(f"[{node}] {update}")
```

`stream_mode` 取值：

| 模式 | 输出 | 用途 |
| :--- | :--- | :--- |
| `values` | 每步后的完整状态 | 调试 |
| `updates` | 每步的增量 | 展示进度 |
| `messages` | 消息级（含 token） | 逐字输出 |
| `custom` | 自定义事件 | 业务埋点 |

### 6.3 token 级流式 + 工具进度

```python
async for event in agent.astream_events(
    {"messages": [("user", "...")]}, version="v2"
):
    kind = event["event"]
    if kind == "on_chat_model_stream":
        content = event["data"]["chunk"].content
        if content:
            print(content, end="", flush=True)
    elif kind == "on_tool_start":
        print(f"\n🔍 调用 {event['name']} 参数={event['data'].get('input')}")
    elif kind == "on_tool_end":
        print(f"✅ {event['name']} 完成")
```

### 6.4 SSE 推给前端

```python
@app.post("/agent/stream")
async def agent_stream(req: ChatRequest):
    async def gen():
        async for event in agent.astream_events(
            {"messages": [("user", req.message)]},
            config={"configurable": {"thread_id": req.thread_id}, "recursion_limit": 12},
            version="v2",
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream" and event["data"]["chunk"].content:
                yield sse({"type": "token", "text": event["data"]["chunk"].content})
            elif kind == "on_tool_start":
                yield sse({"type": "tool_start", "name": event["name"],
                           "args": event["data"].get("input")})
            elif kind == "on_tool_end":
                yield sse({"type": "tool_end", "name": event["name"]})
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


def sse(obj):
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"
```

> 💡 **给用户看工具名要"翻译成人话"**：`get_order` → "正在查询订单…"。可以用一个映射表，**不要直接把内部工具名暴露给用户**（既难懂，也泄露实现）。

### 6.5 取消

```python
import asyncio

task = asyncio.create_task(run_agent())
try:
    await asyncio.wait_for(task, timeout=60)
except asyncio.TimeoutError:
    task.cancel()
    yield sse({"type": "timeout", "message": "处理超时，请稍后重试"})
```

> ⚠️ **取消要通知下游**：如果工具调用已经发出去了（比如正在退款），**取消不代表副作用没发生**。危险操作要用幂等键 + 状态查询兜底。

---

## 七、控制循环：步数、成本、终止

### 7.1 四道闸门

```text
① 步数上限     recursion_limit = 10
② 工具次数     ToolCallLimitMiddleware(max_tool_calls=8)
③ 模型次数     ModelCallLimitMiddleware(max_model_calls=6)
④ 时间/成本    asyncio.wait_for + 中间件累加 usage
```

### 7.2 实现

```python
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware

agent = create_agent(
    model=model,
    tools=tools,
    middleware=[
        ModelCallLimitMiddleware(max_model_calls=6),
        ToolCallLimitMiddleware(max_tool_calls=8),
        SummarizationMiddleware(model=small_model, max_tokens_before_summary=4000),
    ],
)

async def run_safely(message: str, thread_id: str):
    try:
        return await asyncio.wait_for(
            agent.ainvoke(
                {"messages": [("user", message)]},
                config={"configurable": {"thread_id": thread_id}, "recursion_limit": 12},
            ),
            timeout=60,
        )
    except (asyncio.TimeoutError, GraphRecursionError) as e:
        logger.warning(f"agent aborted: {type(e).__name__}")
        return {"messages": [AIMessage("这个请求比较复杂，已为您转接人工客服。")]}
```

### 7.3 成本闸门（自定义中间件）

```python
@wrap_model_call
def budget_guard(request, handler):
    used = request.runtime.context.get("tokens_used", 0)
    if used > 50000:
        raise BudgetExceeded("本次会话 token 已超额")
    resp = handler(request)
    request.runtime.context["tokens_used"] = used + (
        (resp.usage_metadata or {}).get("total_tokens", 0)
    )
    return resp
```

---

## 八、工具路由：如何不让模型在 30 个工具里乱选

### 8.1 问题

| 工具数 | 表现 |
| :--- | :--- |
| 3–5 | 准确 |
| 10 | 开始偶尔选错 |
| 20 | 明显误调、token 高 |
| 50 | 基本不可用 |

**根因**：工具太多，描述互相干扰，模型注意力被稀释。

### 8.2 方案 A：意图分类 + 动态工具集

```python
INTENTS = {
    "order":   ["get_order", "search_orders", "cancel_order"],
    "refund":  ["get_order", "apply_refund", "refund_status"],
    "general": ["search_kb"],
}

def classify(text: str) -> str:
    resp = model.with_structured_output(IntentResult).invoke(
        f"判断用户意图，只能从 {list(INTENTS)} 中选一个：\n{text}"
    )
    return resp.intent


def build_agent(intent: str):
    names = set(INTENTS[intent])
    return create_agent(
        model=model,
        tools=[t for t in ALL_TOOLS if t.name in names],
        system_prompt=PROMPTS[intent],
    )


def handle(text, user_id):
    agent = build_agent(classify(text))
    return agent.invoke({"messages": [("user", text)]},
                        config={"configurable": {"user_id": user_id}})
```

**代价**：多一次模型调用（约 200–500 token，几百毫秒）。
**收益**：准确率显著提升，token 大幅下降。

> 💡 **分类可以用更便宜的模型**（甚至小模型/关键词规则）。**这一步的准确性比灵活性重要。**

### 8.3 方案 B：工具子 Agent（每个领域一个 Agent）

```python
order_agent = create_agent(model, tools=ORDER_TOOLS, name="order_agent")
refund_agent = create_agent(model, tools=REFUND_TOOLS, name="refund_agent")

@tool
def order_assistant(question: str) -> str:
    """处理订单相关咨询：查询、物流、修改地址、取消订单。"""
    r = order_agent.invoke({"messages": [("user", question)]})
    return r["messages"][-1].content

@tool
def refund_assistant(question: str) -> str:
    """处理退款相关：申请退款、查询退款进度、退款规则。"""
    r = refund_agent.invoke({"messages": [("user", question)]})
    return r["messages"][-1].content

supervisor = create_agent(model, tools=[order_assistant, refund_assistant])
```

> 💡 **工具即子 Agent** 是非常实用的模式：主 Agent 只看到 2 个"工具"，每个工具内部有自己的专业工具集和提示词。**这就是多 Agent 的雏形**（第 09 篇）。

### 8.4 方案 C：两段式（先规划再执行）

```python
PLAN_PROMPT = """根据用户需求，列出需要调用的工具及顺序（JSON）。

可用工具：{tools}
用户需求：{question}

输出：{"steps": [{"tool": "...", "reason": "..."}]}
"""
```

让模型先出计划，**代码校验计划**（工具白名单、步数上限），再逐步执行。

> ⚠️ 两段式增加了延迟，但在**高风险场景**（涉及资金、删除）很值得：你可以在执行前拦截不合规的计划。

---

## 九、常见失败模式与修复 ⭐⭐

### 9.1 不调工具，直接编答案

**现象**：

```text
用户：我的订单 12345 到哪了
Agent：您的订单已发货，预计明天送达。   ← 没调工具！编的
```

**原因**：

- 工具描述没写清"必须调用"
- 模型觉得"我知道答案"
- 系统提示没有强制

**修复**：

```python
system_prompt = """你是订单助手。

【硬性规则】
1. 任何涉及订单状态、物流、金额的问题，必须先调用 get_order_detail 查询。
2. 禁止凭记忆回答订单相关信息。
3. 工具返回失败时，如实告知用户，不要编造。
"""
```

```python
# 更强的手段：第一步强制调工具
model.bind_tools(tools, tool_choice="required")
```

> 💡 **验证手段**：在评测里检查"涉及订单的问题，`messages` 里是否出现了 `get_order_detail` 的 `tool_call`"。这是**可自动化的断言**。

### 9.2 反复调同一个工具（死循环）

**现象**：连续 5 次调用 `search_orders`，参数略有不同。

**原因**：工具返回"未找到"，模型不断改参数重试。

**修复**：

```python
@tool
def search_orders(keyword: str) -> str:
    """..."""
    rows = db.search(keyword)
    if not rows:
        return ("未找到订单。不要再换关键词重复搜索，"
                "请直接告诉用户没有找到，并建议其核对订单号或联系客服。")
    return json.dumps(...)
```

**在工具返回值里"教"模型下一步怎么做**，比在系统提示里写规则有效得多。

再配合 `ToolCallLimitMiddleware` 兜底。

### 9.3 调用了不该用的工具

**现象**：用户说"我要退款"，Agent 直接 `apply_refund`，没确认也没查订单。

**修复**：

1. 工具描述写明前置条件：
   ```python
   @tool
   def apply_refund(...):
       """申请退款。

       前置条件（必须满足才可调用）：
       1. 已调用 get_order_detail 且 can_refund=true
       2. 用户明确表达了退款意愿
       3. 用户已确认退款金额
       """
   ```
2. 代码层强制校验（**不能只靠描述**）：
   ```python
   def _check_prereq(state, order_no):
       called = any(
           tc["name"] == "get_order_detail" and tc["args"].get("order_no") == order_no
           for m in state["messages"] if getattr(m, "tool_calls", None)
           for tc in m.tool_calls
       )
       if not called:
           raise PermissionError("必须先查询订单详情")
   ```

### 9.4 参数错误

**现象**：`order_no` 传成了 `"12345号"`、日期格式不对、金额为负。

**修复**：

- `Literal` / `pattern` 约束
- 工具内部**宽容解析 + 明确报错**：
  ```python
  m = re.search(r"\d{5,20}", order_no)
  if not m:
      return {"success": False, "error": "订单号必须是 5-20 位数字，请向用户确认"}
  order_no = m.group()
  ```

### 9.5 上下文爆炸

**现象**：第 6 轮后每次请求 20K token。

**修复**：`SummarizationMiddleware` + 工具返回精简 + 减少工具数。

### 9.6 回答太长 / 格式不对

**现象**：用户要"一句话"，Agent 输出 800 字。

**修复**：

- 系统提示写死长度约束（"不超过 100 字"）
- **用 `response_format` 约束结构**
- 后处理截断（最后手段，可能截断语义）

### 9.7 失败模式速查

| 现象 | 优先怀疑 | 修复 |
| :--- | :--- | :--- |
| 不调工具 | 描述不清 / 提示词弱 | 强制规则 + `tool_choice` |
| 死循环 | 工具返回无引导 | 返回中给"下一步建议" + 限额 |
| 误调用 | 工具太多/名字相似 | 意图路由 |
| 参数错 | schema 不严 | `Literal`/`pattern` + 宽容解析 |
| 上下文爆 | 无裁剪 | 摘要中间件 |
| 编造结果 | 缺校验 | 以工具结果为准 + 明确拒答 |
| 越权 | 缺鉴权 | `config` 取身份 + 服务端校验 |

---

## 十、调试 Agent 的方法论

### 10.1 三步定位

```text
① 看消息序列：它到底调了什么、传了什么参数、拿到什么结果
② 看工具返回值：模型"看到的信息"是否足够、是否被误导
③ 看 Prompt：系统提示和工具描述能否支撑期望行为
```

**顺序不能反**。先看轨迹，再改提示——90% 的问题看一眼轨迹就清楚了。

### 10.2 打印轨迹

```python
def print_trace(result):
    for i, m in enumerate(result["messages"]):
        t = m.type
        if t == "human":
            print(f"{i:02d} [用户] {m.content}")
        elif t == "ai":
            if getattr(m, "tool_calls", None):
                for tc in m.tool_calls:
                    print(f"{i:02d} [模型→工具] {tc['name']}({tc['args']})")
            else:
                print(f"{i:02d} [模型] {m.content}")
        elif t == "tool":
            body = m.content if len(str(m.content)) < 200 else str(m.content)[:200] + "..."
            print(f"{i:02d} [工具] {body}")
```

**输出示例**：

```text
00 [用户] 我的订单 12345 到哪了
01 [模型→工具] get_order_detail({'order_no': '12345'})
02 [工具] {"success": true, "status": "已发货", ...}
03 [模型] 您的订单已发货，预计明天送达。
```

### 10.3 LangSmith 追踪

配好 `LANGSMITH_TRACING=true` 后，每次调用都会有一条完整链路：

- 每一步的输入输出
- 每个工具的耗时和返回值
- token 用量、成本
- 失败点

> 💡 **不开追踪调 Agent = 盲调**。这一步的投入产出比极高，建议第一天就配好。

### 10.4 可复现的调试

```python
# 用固定输入 + temperature=0 + 记录完整 messages
result = agent.invoke({"messages": [("user", FIXED_CASE)]})

# 把整个 result 存下来，作为回归用例
json.dump(serialize_messages(result["messages"]),
          open(f"cases/{case_id}.json", "w"), ensure_ascii=False)
```

> ⚠️ **Agent 的输出不保证可复现**。所以测试要断言"**是否调了正确的工具、是否包含了关键字段**"，而不是"输出文本完全一致"。

### 10.5 一个务实的测试策略

```python
def test_order_agent_calls_detail_tool():
    result = agent.invoke({"messages": [("user", "订单 12345 到哪了")]})
    called = [
        tc["name"]
        for m in result["messages"] if getattr(m, "tool_calls", None)
        for tc in m.tool_calls
    ]
    assert "get_order_detail" in called
    assert "apply_refund" not in called        # 不该误调写操作
    assert "12345" in json.dumps(result["messages"][1].tool_calls, ensure_ascii=False)
```

---

## 十一、什么时候该放弃 `create_agent`

### 11.1 信号

| 信号 | 说明 |
| :--- | :--- |
| 需要"必须按某个顺序走" | 固定流程用状态图更稳 |
| 需要人工审批（真暂停） | 用 `interrupt`（第 08 篇） |
| 需要断点续跑/时间旅行 | Checkpointer + 回放 |
| 需要严格的可测试性 | 每个节点可单测 |
| 需要在中间插入复杂的业务逻辑 | 图节点比中间件清晰 |
| 需要多 Agent 协作 | 子图（第 09 篇） |
| 流程本身是"业务编排"而不是"探索" | 不要硬塞给 Agent |

### 11.2 判断标准

```text
问：你的流程能不能画成一张图？
  能，且节点边界清晰  → 用 LangGraph 显式图（第 07 篇）
  不能，需要动态决策    → 用 create_agent，加中间件约束

问：需要人/外部系统在中间介入吗？
  需要            → LangGraph + interrupt
  不需要          → create_agent 够用
```

> 💡 **实战常见做法**：**外层用 LangGraph 管业务流程，某个节点内部用 `create_agent` 做灵活决策**。两者不是互斥的。

---

## 十二、完整示例：订单售后 Agent

```python
# after_sale_agent.py
import json, os, httpx
from dataclasses import dataclass
from typing import Literal
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware, ToolCallLimitMiddleware, SummarizationMiddleware,
)
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres import PostgresSaver

model = init_chat_model("gpt-4o-mini", temperature=0)
small = init_chat_model("gpt-4o-mini", temperature=0)
BASE = os.getenv("ORDER_API", "http://localhost:8080/api")


class RefundInput(BaseModel):
    order_no: str = Field(pattern=r"^\d{5,20}$", description="订单号，5-20 位数字")
    reason: Literal["七天无理由", "质量问题", "发错货", "其他"] = Field(
        description="退款原因"
    )
    remark: str | None = Field(default=None, description="补充说明")


@tool
async def get_order_detail(order_no: str, config: RunnableConfig) -> dict:
    """查询订单详情：状态、金额、商品、能否退款。

    用户询问订单进度、物流、金额、退款条件时使用。
    不适用于查询订单列表（用 search_orders）。
    """
    uid = config["configurable"]["user_id"]
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE}/orders/{order_no}", headers={"X-User-Id": uid})
    if r.status_code == 404:
        return {"success": False, "error": f"订单 {order_no} 不存在，请与用户核对"}
    if r.status_code == 403:
        return {"success": False, "error": "无权查看该订单"}
    d = r.json()
    return {
        "success": True, "order_no": d["orderNo"], "status": d["status"],
        "amount": d["amount"], "can_refund": d["status"] in ("已发货", "已完成"),
        "items": [{"name": i["name"], "qty": i["qty"]} for i in d["items"]],
    }


@tool("apply_refund", args_schema=RefundInput)
async def apply_refund(order_no: str, reason: str, remark: str | None,
                       config: RunnableConfig) -> dict:
    """申请退款（写操作，进入人工审批流程，不会立即到账）。

    前置条件（全部满足才可调用）：
    1. 已调用 get_order_detail 且 can_refund=true
    2. 用户明确要求退款
    3. 用户已确认退款

    退款金额由系统按订单实付金额自动计算，不要传金额。
    """
    uid = config["configurable"]["user_id"]
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"{BASE}/orders/{order_no}/refund",
            json={"reason": reason, "remark": remark},
            headers={"X-User-Id": uid,
                     "Idempotency-Key": f"{uid}:{order_no}:{reason}"},
        )
    if r.status_code == 409:
        return {"success": False, "error": "该订单已有进行中的退款申请"}
    if r.status_code != 200:
        return {"success": False, "error": f"退款申请失败（{r.status_code}）"}
    d = r.json()
    return {"success": True, "refund_id": d["refundId"], "amount": d["amount"],
            "status": "待审批"}


@tool
async def search_orders(keyword: str, config: RunnableConfig) -> dict:
    """按关键词搜索当前用户的订单列表（订单号、商品名）。"""
    uid = config["configurable"]["user_id"]
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE}/orders", params={"q": keyword},
                        headers={"X-User-Id": uid})
    items = r.json().get("items", [])[:10]
    if not items:
        return {"success": True, "total": 0,
                "hint": "未找到订单。请告诉用户没有找到，建议核对订单号，不要反复换关键词重搜。"}
    return {"success": True, "total": len(items),
            "items": [{"order_no": i["orderNo"], "status": i["status"],
                       "amount": i["amount"]} for i in items]}


SYSTEM = """你是 {company} 的售后助手。

【规则】
1. 涉及订单状态/金额/物流，必须先调用 get_order_detail，不要凭记忆回答。
2. 退款必须先确认 can_refund=true，且征得用户明确同意。
3. 只能操作当前用户自己的订单；工具返回无权时如实告知。
4. 工具返回 success=false 时，把 error 转述给用户，不要编造成功。
5. 回答简洁，不超过 150 字；不确定就问用户。

【用户】{user_name}
"""


def build(user_name: str):
    return create_agent(
        model=model,
        tools=[get_order_detail, search_orders, apply_refund],
        system_prompt=SYSTEM.format(company="XX 商城", user_name=user_name),
        middleware=[
            ModelCallLimitMiddleware(max_model_calls=6),
            ToolCallLimitMiddleware(max_tool_calls=8),
            SummarizationMiddleware(model=small, max_tokens_before_summary=4000,
                                    messages_to_keep=10),
        ],
        name="after_sale_agent",
    )


async def chat(user_id: str, user_name: str, thread_id: str, message: str):
    agent = build(user_name)
    return await agent.ainvoke(
        {"messages": [("user", message)]},
        config={
            "configurable": {"user_id": user_id, "thread_id": thread_id},
            "recursion_limit": 12,
            "metadata": {"user_id": user_id},
        },
    )
```

### 12.1 这个例子里值得学的点

| 设计 | 为什么 |
| :--- | :--- |
| 退款金额不让模型传 | 防止模型编造金额 |
| `Idempotency-Key` | 重试不重复退款 |
| 工具返回带 `hint` | 引导模型停止无效重试 |
| 身份从 `config` 取 | 防越权 |
| 工具描述写了"前置条件" | 降低误调用 |
| 三道限额 | 防失控 |
| 摘要中间件 | 控成本 |

---

## 十三、本章小结与练习

### 核心结论

1. **Agent 的本质是把控制流交给模型**，这是它灵活性和风险的共同来源。
2. **ReAct 在今天就是"工具调用循环"**，停止条件是"没有 tool_calls"。
3. **`create_agent` 内部就是一张"模型 ↔ 工具"的图**，理解它，第 07 篇就通了。
4. **中间件 = Agent 的 AOP**，用来做日志、注入、压缩、审批、限额；**顺序很重要**。
5. **必须做流式**，让用户看到工具调用和逐字输出。
6. **四道闸门**：步数、模型次数、工具次数、超时/预算。
7. **工具超过 10 个就要做路由**，意图分类或子 Agent。
8. **失败模式有规律**：不调工具/死循环/误调用/参数错/上下文爆，各有对应修法。
9. **调试先看轨迹**：工具名、参数、返回值，再改 Prompt。
10. **流程固定就用状态图**，不要硬让 Agent 自由发挥。

### 动手练习

1. 用 `create_agent` 接入 2 个工具，跑通；然后用第 4 节的代码手写一个等价的图，对比行为差异。
2. 写一个 `before_model` 中间件注入当前时间和用户名，验证模型能正确回答"现在几点"。
3. 写一个 `wrap_tool_call` 中间件，让 `refund` 类工具在未获审批时返回"需要确认"，验证 Agent 会把这句话转述给用户。
4. 构造一个"不调工具直接编答案"的场景，用系统提示修复，并用断言验证 `messages` 里出现了 `tool_call`。
5. 构造一个死循环场景（工具一直返回"未找到"），分别用"工具返回带 hint"和 `ToolCallLimitMiddleware` 修复。
6. 用 `astream_events` 做一个带"正在查询订单…"进度的 SSE 接口。
7. 把工具扩到 12 个，观察误调用率；然后加意图分类路由，对比效果和 token 消耗。

### 下一篇

[07 - LangGraph 状态图核心机制](07-LangGraph状态图核心机制.md) —— 把 Agent 从"黑盒循环"变成"你能看见、能测、能改"的显式状态机。
