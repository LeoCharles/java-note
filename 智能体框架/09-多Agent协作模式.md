# 09 - 多 Agent 协作模式

> 单 Agent 会在某个点撞墙：提示词写了三千字、工具三十个、什么都想做、什么都做不好。
> 这一篇讲清楚**什么时候该拆**、**怎么拆**、**拆完怎么让它们协作**。
> 也讲一件更重要的事：**大多数"多 Agent 需求"其实是单 Agent + 好工具就够了的**。

---

## 📖 目录

1. [什么时候该拆](#一什么时候该拆)
2. [拆分的三种维度](#二拆分的三种维度)
3. [五种协作拓扑 ⭐⭐](#三五种协作拓扑-)
4. [模式一：工具即子 Agent](#四模式一工具即子-agent)
5. [模式二：Supervisor 调度 ⭐⭐](#五模式二supervisor-调度-)
6. [模式三：Handoff 转接 ⭐](#六模式三handoff-转接-)
7. [模式四：流水线 Pipeline](#七模式四流水线-pipeline)
8. [模式五：辩论 / 评审（谨慎使用）](#八模式五辩论--评审谨慎使用)
9. [Agent 之间的通信契约 ⭐⭐](#九agent-之间的通信契约-)
10. [状态共享与隔离](#十状态共享与隔离)
11. [多 Agent 的成本账 ⭐](#十一多-agent-的成本账-)
12. [常见失败模式](#十二常见失败模式)
13. [什么时候"不要"多 Agent](#十三什么时候不要多-agent)
14. [完整示例：电商客服系统](#十四完整示例电商客服系统)
15. [本章小结与练习](#本章小结与练习)

---

## 一、什么时候该拆

### 1.1 六个信号

| 信号 | 具体表现 |
| :--- | :--- |
| **提示词过长** | 系统提示 > 1000 字，规则互相打架 |
| **工具过多** | 工具 > 10 个，误调用明显增加 |
| **领域冲突** | 退款规则和产品咨询规则混在一个提示里 |
| **权限不同** | 有的 Agent 能看财务数据，有的不能 |
| **开发协作** | 不同团队维护不同领域 |
| **可测试性差** | 改一处提示词，别处就退化 |

### 1.2 一个判断测试

> **假设你把这两个"Agent"合并成一个，加入它的工具列表——工具数是否超过 10？提示词是否出现"如果…另外…但是…"这类条件堆叠？**
>
> 如果都是，**该拆**。

### 1.3 拆分代价（先看代价再决定）

| 代价 | 说明 |
| :--- | :--- |
| **延迟增加** | 每多一层调度 = 多一次模型调用 |
| **成本上升** | 通常 2–5 倍 token |
| **调试困难** | 错误可能在任意一层，链路长 |
| **信息损失** | 上下文在 Agent 之间传递时会丢 |
| **一致性** | 不同 Agent 说法可能矛盾 |

> ⚠️ **多 Agent 不是"更高级"，是"更贵更难的另一种选择"**。**能用单 Agent 解决就别拆。**

---

## 二、拆分的三种维度

### 2.1 按领域拆（最常见）

```text
客服系统
├─ 订单 Agent：查询、物流、改地址、取消
├��� 售后 Agent：退款、换货、维修
└─ 产品 Agent：功能介绍、参数、使用说明
```

**依据**：业务边界、数据权限、团队归属。

### 2.2 按职责拆

```text
内容生产
├─ 研究 Agent：检索资料
├─ 撰写 Agent：写初稿
└─ 审核 Agent：检查事实、风格
```

**依据**：同一任务的不同阶段，需要的提示词和工具完全不同。

### 2.3 按角色拆（谨慎）

```text
辩论
├─ 正方 Agent
└─ 反方 Agent
```

**依据**：需要"对抗"以提升质量。**成本最高，收益最不稳定。**

---

## 三、五种协作拓扑 ⭐⭐

### 3.1 全景

```text
① 工具即子 Agent（嵌套）
   主 Agent ──tool──> 子 Agent

② Supervisor（调度中心）
   Supervisor ──> A / B / C ──> Supervisor

③ Handoff（转接，单线）
   前台 Agent ──转接──> 专家 Agent（前台退出）

④ Pipeline（流水线）
   A ──> B ──> C

⑤ 辩论 / 评审
   A ⇄ B，C 裁决
```

### 3.2 选型表

| 模式 | 控制流 | 成本 | 适用 |
| :--- | :--- | :--- | :--- |
| 工具即子 Agent | 主 Agent 掌控 | 中 | 领域清晰、主 Agent 只需"调用" |
| Supervisor | 中心调度 | 高 | 多个领域、需要汇总 |
| Handoff | 线性转移 | 低–中 | 客服分流、专家转接 |
| Pipeline | 固定顺序 | 低 | 内容生产、数据处理 |
| 辩论 | 对抗 | 很高 | 高风险决策、研究 |

> 💡 **实战顺序建议**：单 Agent → 工具即子 Agent → Handoff → Supervisor。**逐级升级，不要一步到位。**

---

## 四、模式一：工具即子 Agent

### 4.1 原理

**把子 Agent 包装成一个 `@tool`，主 Agent 完全不知道下面还有图。**

```python
from langchain_core.tools import tool
from langchain.agents import create_agent

order_agent = create_agent(model, tools=ORDER_TOOLS, name="order_agent",
                           system_prompt=ORDER_PROMPT)
refund_agent = create_agent(model, tools=REFUND_TOOLS, name="refund_agent",
                            system_prompt=REFUND_PROMPT)


@tool
def order_assistant(question: str) -> str:
    """处理订单相关咨询：订单查询、物流跟踪、修改收货地址、取消订单。
    不处理退款、换货、产品咨询。"""
    r = order_agent.invoke({"messages": [("user", question)]})
    return r["messages"][-1].content


@tool
def refund_assistant(question: str) -> str:
    """处理退款、换货、维修相关咨询。
    需要用户提供订单号。"""
    r = refund_agent.invoke({"messages": [("user", question)]})
    return r["messages"][-1].content


router = create_agent(
    model,
    tools=[order_assistant, refund_assistant],
    system_prompt="你是客服总入口，根据用户问题选择合适的助手。不要自己编造业务信息。",
)
```

### 4.2 优点

| 优点 | 说明 |
| :--- | :--- |
| 实现简单 | 几行代码 |
| 主 Agent 上下文干净 | 只看到 2 个工具 |
| 子 Agent 可独立开发测试 | 各团队维护 |
| 权限天然隔离 | 子 Agent 内部才有对应工具 |

### 4.3 缺点与修复

| 缺点 | 修复 |
| :--- | :--- |
| 子 Agent 拿不到完整上下文 | 把关键信息拼进 `question` |
| 只能"一问一答"，不能多轮 | 子 Agent 内自己维护（用 checkpointer + 子 thread） |
| 主 Agent 无法看子 Agent 中间步 | 子 Agent 返回结构化摘要 |

**改进：传结构化上下文**

```python
from pydantic import BaseModel, Field

class SubRequest(BaseModel):
    question: str = Field(description="用户的问题原文")
    order_no: str | None = Field(default=None, description="已知订单号")
    summary: str = Field(default="", description="对话摘要，供子 Agent 参考")


@tool("order_assistant", args_schema=SubRequest)
def order_assistant(question: str, order_no: str | None = None, summary: str = "") -> str:
    """处理订单相关咨询。"""
    prompt = f"【对话背景】{summary}\n【订单号】{order_no or '未提供'}\n【用户问题】{question}"
    r = order_agent.invoke({"messages": [("user", prompt)]})
    return r["messages"][-1].content
```

**改进：返回结构化结果**

```python
class SubReply(BaseModel):
    answer: str
    resolved: bool = Field(description="是否已解决，false 表示需要转人工")
    data: dict = Field(default_factory=dict, description="关键数据，如订单号、金额")

@tool("order_assistant", args_schema=SubRequest)
def order_assistant(...) -> dict:
    r = order_agent.invoke({"messages": [("user", prompt)]},
                           config={"configurable": {"thread_id": f"sub:{uuid4().hex}"}})
    # 子 Agent 用结构化输出
    return json.dumps({...})
```

> 💡 **返回 dict/JSON 比返回自然语言好**：主 Agent 能拿到字段，方便判断"要不要转人工"。

---

## 五、模式二：Supervisor 调度 ⭐⭐

### 5.1 结构

```text
              ┌──────────────┐
              │  Supervisor  │
              └──┬────┬────┬─┘
                 │    │    │
              ┌──▼┐ ┌▼──┐ ┌▼──┐
              │ A │ │ B │ │ C │
              └─┬─┘ └┬──┘ └┬──┘
                └────┴─────┘
                     │
                 回到 Supervisor
```

**Supervisor 只做两件事**：决定"下一步交给谁"、判断"是否可以结束"。

### 5.2 用 LangGraph 实现

```python
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage

MEMBERS = ["order_agent", "refund_agent", "product_agent"]


class TeamState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    next: str
    history: Annotated[list[str], lambda a, b: a + b]


SUPERVISOR_PROMPT = """你是客服主管，负责分派任务给团队成员。

成员及职责：
- order_agent：订单查询、物流、改地址、取消订单
- refund_agent：退款、换货、维修
- product_agent：产品功能、参数、使用方法

规则：
1. 每次只派给一个最合适的成员。
2. 成员完成后，判断是否已解决用户问题。
3. 已解决或无法继续时，返回 FINISH。
4. 不要在同一个成员上连续派发超过 2 次。

历史分工：{history}
"""


def supervisor_node(state: TeamState) -> dict:
    resp = model.with_structured_output(RouteDecision).invoke(
        [SystemMessage(SUPERVISOR_PROMPT.format(history=state.get("history", [])))]
        + state["messages"]
    )
    return {"next": resp.next, "history": [resp.next]}


def make_member(name: str, prompt: str, tools: list):
    agent = create_agent(model, tools=tools, system_prompt=prompt, name=name)

    def node(state: TeamState) -> dict:
        r = agent.invoke({"messages": state["messages"]})
        # 只把最终回答回传，避免子 Agent 的中间 tool 消息污染主状态
        return {"messages": [r["messages"][-1]]}

    node.__name__ = name
    return node


def route(state: TeamState) -> str:
    return END if state["next"] == "FINISH" else state["next"]


builder = StateGraph(TeamState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("order_agent", make_member("order_agent", ORDER_PROMPT, ORDER_TOOLS))
builder.add_node("refund_agent", make_member("refund_agent", REFUND_PROMPT, REFUND_TOOLS))
builder.add_node("product_agent", make_member("product_agent", PRODUCT_PROMPT, PRODUCT_TOOLS))

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", route,
                              {**{m: m for m in MEMBERS}, END: END})
for m in MEMBERS:
    builder.add_edge(m, "supervisor")        # 每个成员做完都回到主管

team = builder.compile(checkpointer=InMemorySaver())
```

```python
from pydantic import BaseModel, Field
from typing import Literal

class RouteDecision(BaseModel):
    next: Literal["order_agent", "refund_agent", "product_agent", "FINISH"] = Field(
        description="下一个发言者，或 FINISH 表示结束"
    )
    reason: str = Field(description="选择理由，简短")
```

### 5.3 关键设计点

| 设计 | 为什么 |
| :--- | :--- |
| **只回传成员的最终回答** | 避免子 Agent 的 tool 消息撑爆主状态 |
| **`history` 记录分工** | 防止无限循环派给同一人 |
| **`FINISH` 显式结束** | 比"成员不说话"可靠 |
| **结构化路由** | 比解析文本可靠 |
| **成员节点独立** | 可单独测试 |

### 5.4 循环保护

```python
def route(state: TeamState) -> str:
    if len(state.get("history", [])) >= 8:      # 硬上限
        return END
    if state["next"] == "FINISH":
        return END
    return state["next"]
```

> ⚠️ **Supervisor 最常见的 bug 是无限循环**：A 说"搞不定"，主管又派给 A。**必须限制轮次 + 记录历史。**

### 5.5 最后汇总

```python
def synthesize(state: TeamState) -> dict:
    resp = model.invoke(
        [SystemMessage("根据以下对话，给用户一个完整、简洁的最终答复。")] + state["messages"]
    )
    return {"messages": [resp]}

builder.add_edge("supervisor", "synthesize")   # 当 route 返回 END 前先汇总
```

> 💡 更简单的做法：**让 `FINISH` 指向一个 `synthesize` 节点，再由它连到 END**。

---

## 六、模式三：Handoff 转接 ⭐

### 6.1 与 Supervisor 的区别

| | Supervisor | Handoff |
| :--- | :--- | :--- |
| 控制权 | 主管始终持有，每次回来 | 转接后**原 Agent 退出** |
| 延迟 | 每步多一次调度调用 | 无额外调度 |
| 成本 | 高 | 低 |
| 适合 | 需要多次协作 | 一次分流到位 |

### 6.2 用 `Command` 实现

```python
from langgraph.types import Command
from typing import Literal

class SupportState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    current_agent: str


def triage_node(state: SupportState) -> Command[Literal["order", "refund", "human"]]:
    resp = model.with_structured_output(Triage).invoke(state["messages"])
    return Command(goto=resp.target, update={"current_agent": resp.target})


def order_node(state: SupportState) -> Command:
    agent = create_agent(model, tools=ORDER_TOOLS, system_prompt=ORDER_PROMPT)
    r = agent.invoke({"messages": state["messages"]})
    last = r["messages"][-1]

    # 订单 Agent 自己判断要转给谁
    if "退款" in last.content or getattr(last, "tool_calls", None):
        ...
    return Command(goto=END, update={"messages": [last]})
```

### 6.3 显式转接工具

更清晰的做法——**给每个 Agent 一个"转接"工具**：

```python
@tool
def transfer_to_refund(reason: str) -> str:
    """把用户转接给退款专员。仅在用户问题涉及退款、退货时使用。"""
    return json.dumps({"action": "transfer", "to": "refund", "reason": reason})


def order_node(state):
    result = agent.invoke({"messages": state["messages"]})
    last = result["messages"][-1]

    for tc in (getattr(last, "tool_calls", None) or []):
        if tc["name"].startswith("transfer_to_"):
            target = tc["name"].replace("transfer_to_", "")
            return Command(goto=target,
                           update={"messages": [AIMessage(f"正在为您转接…")],
                                   "current_agent": target})
    return Command(goto=END, update={"messages": [last]})
```

### 6.4 何时用哪个

```text
一次分流就能定下来 → Handoff
需要来回多次判定       → Supervisor
不需要多个专家        → 单 Agent + 工具
```

---

## 七、模式四：流水线 Pipeline

### 7.1 结构

```text
[研究] → [撰写] → [审核] → [定稿]
```

**每个阶段职责单一，前一个的输出是后一个的输入。**

```python
class ContentState(TypedDict):
    topic: str
    research: str
    draft: str
    review: str
    final: str


def research_node(state):
    r = create_agent(model, tools=[web_search], system_prompt=RESEARCH_PROMPT).invoke(
        {"messages": [("user", f"研究主题：{state['topic']}，输出要点和来源")]}
    )
    return {"research": r["messages"][-1].content}


def write_node(state):
    r = model.invoke([
        SystemMessage(WRITER_PROMPT),
        HumanMessage(f"主题：{state['topic']}\n资料：{state['research']}\n请写初稿。"),
    ])
    return {"draft": r.content}


def review_node(state):
    r = model.with_structured_output(ReviewResult).invoke([
        SystemMessage(REVIEWER_PROMPT),
        HumanMessage(f"初稿：\n{state['draft']}"),
    ])
    return {"review": r.model_dump_json(), "draft": r.revised}


def finalize_node(state):
    return {"final": state["draft"] if state["review_pass"] else state["draft"]}
```

### 7.2 带分支的流水线

```python
def need_revision(state) -> Literal["write", "finalize"]:
    return "write" if not state["review_pass"] and state["revisions"] < 2 else "finalize"
```

> ⚠️ **必须限制返工次数**，否则审核-修改会无限循环。

### 7.3 何时用 Pipeline

- 阶段划分天然清晰
- 每阶段有明确的输入输出契约
- 不需要"回头问用户"
- 适合批处理（批量生成、批量审核）

---

## 八、模式五：辩论 / 评审（谨慎使用）

### 8.1 结构

```text
问题 → [正方] ⇄ [反方] → [裁判] → 答案
```

### 8.2 现实

| 宣称的好处 | 实际情况 |
| :--- | :--- |
| 提高准确性 | 在**有明显客观答案**的任务上有提升（数学、事实核查） |
| 减少幻觉 | 有限；两个模型可能一起错 |
| 更全面 | 可能，但成本 3–5 倍 |

### 8.3 建议

> ⚠️ **不要默认用辩论**。先用"单 Agent + 自我检查（self-critique）"试试，效果不够再升级。
> 真正值得用的场景：**高风险、可验证、答案唯一**（代码正确性、数学、合规判断）。

```python
def debate(state):
    pro = model.invoke([SystemMessage("你是正方，为方案 A 辩护。")] + state["messages"])
    con = model.invoke([SystemMessage("你是反方，指出方案 A 的问题。")] + state["messages"] + [pro])
    judge = model.with_structured_output(Verdict).invoke(
        [SystemMessage("你是裁判，给出结论和理由。")] + state["messages"] + [pro, con]
    )
    return {"verdict": judge.model_dump()}
```

---

## 九、Agent 之间的通信契约 ⭐⭐

### 9.1 核心问题

**Agent 之间传什么？** 这决定了系统的稳定性和成本。

### 9.2 三种传法对比

| 传法 | 优点 | 缺点 |
| :--- | :--- | :--- |
| 传完整 messages | 信息最全 | token 爆炸、互相干扰 |
| 传自然语言摘要 | 简单 | 信息丢失、格式不稳 |
| **传结构化对象** | 稳定、省 token | 需要设计 schema |

### 9.3 推荐：结构化契约

```python
from pydantic import BaseModel, Field

class TaskBrief(BaseModel):
    """主 Agent 交给子 Agent 的任务说明。"""
    objective: str = Field(description="要达成的目标，一句话")
    context: dict = Field(default_factory=dict,
                          description="已知事实，如 order_no、user_id")
    constraints: list[str] = Field(default_factory=list,
                                   description="限制条件，如'不要调用退款接口'")
    prior_findings: list[str] = Field(default_factory=list,
                                      description="前面 Agent 已确认的结论")


class TaskResult(BaseModel):
    """子 Agent 返回给主 Agent 的结果。"""
    answer: str
    resolved: bool
    data: dict = Field(default_factory=dict)
    next_suggestion: str | None = Field(default=None,
                                        description="建议下一步交给谁，或 None")
```

```python
def run_sub_agent(agent, brief: TaskBrief) -> TaskResult:
    prompt = f"""【目标】{brief.objective}
【已知信息】{json.dumps(brief.context, ensure_ascii=False)}
【限制】{'; '.join(brief.constraints) or '无'}
【已有结论】{'；'.join(brief.prior_findings) or '无'}
"""
    result = agent.invoke({"messages": [("user", prompt)]})
    # 用结构化输出抽取
    return extractor.invoke(result["messages"])
```

### 9.4 契约设计原则

| 原则 | 说明 |
| :--- | :--- |
| **只传必要信息** | 5 个字段以内 |
| **事实与指令分离** | `context` 是事实，`objective` 是指令 |
| **限制显式化** | 避免子 Agent 越权 |
| **结果可判定** | `resolved` 布尔值，比"我觉得解决了"可靠 |
| **留扩展位** | `data` 放任意业务字段 |

> 💡 **把 Agent 之间当成"微服务调用"来设计**：有契约、有超时、有错误码。

### 9.5 错误传递

```python
class TaskResult(BaseModel):
    ...
    error: str | None = None
    retryable: bool = False
```

**子 Agent 失败时，主 Agent 需要知道"能不能重试"**，而不是只看到一句"失败了"。

---

## 十、状态共享与隔离

### 10.1 共享 vs 隔离

| | 共享 State | 隔离 State |
| :--- | :--- | :--- |
| 实现 | 子图共用父 State 键 | 子图有自己的 State |
| 优点 | 信息透明、无需转换 | 互不污染、可独立演化 |
| 缺点 | 字段冲突、state 膨胀 | 需要显式传参 |
| 适合 | 紧耦合的流程 | 松耦合的专家 |

### 10.2 子图隔离 + 显式接缝

```python
class ParentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    brief: dict
    result: dict


def call_specialist(state: ParentState) -> dict:
    """在父图的一个节点里调用独立子图。"""
    sub_input = {"messages": [], "task": state["brief"]}
    out = specialist_graph.invoke(sub_input)
    return {"result": out["result"], "messages": [AIMessage(out["result"]["answer"])]}
```

> 💡 **这种写法最容易调试**：子图可以完全独立测试，父图只关心输入输出。

### 10.3 消息膨胀问题

**Supervisor 模式下，所有成员的消息都会累积到主 State**，几十轮后上下文爆炸。

**修复**：

```python
def member_node(state):
    result = agent.invoke({"messages": state["messages"]})
    last = result["messages"][-1]
    # 只回传最终答案 + 一段标注
    return {"messages": [AIMessage(f"[{name}] {last.content}")]}
```

再配合 `SummarizationMiddleware` 或定期裁剪。

---

## 十一、多 Agent 的成本账 ⭐

### 11.1 一次请求的成本估算

**单 Agent（2 轮工具）**：

```text
输入 token：系统提示 800 + 工具定义 600 + 历史 500 ≈ 1900
           × 3 次调用 ≈ 5700
输出 token：≈ 600
合计 ≈ 6300 token
```

**Supervisor（3 个专家，平均转 2 次）**：

```text
主管决策：1900 × 4 ≈ 7600
每个专家：1500 × 2 ≈ 3000 × 2 = 6000
汇总：1000
合计 ≈ 14600 token  →  2.3 倍
```

### 11.2 延迟

```text
单 Agent：        2 次模型 × 2s + 工具 0.5s ≈ 4.5s
Supervisor：      4 次调度 × 1.5s + 2 次专家 × 2s ≈ 10s
```

> ⚠️ **延迟翻倍是用户能明显感知的**。多 Agent 要有明确收益才做。

### 11.3 降本手段

| 手段 | 效果 |
| :--- | :--- |
| 路由用小模型 | 调度成本降 80% |
| 只回传摘要 | 上下文减半 |
| 意图分类前置（不走 LLM 调度） | 省一次调用 |
| 缓存子 Agent 结果 | 重复问题直接返回 |
| 并行执行独立子任务 | 降延迟 |

```python
# 前置意图分类，直接跳转，不用 Supervisor 反复决策
def fast_route(text: str) -> str:
    intent = small_model.with_structured_output(Intent).invoke(text).intent
    return {"order": "order_agent", "refund": "refund_agent"}.get(intent, "general_agent")
```

---

## 十二、常见失败模式

### 12.1 无限转接

```text
主管 → A → 主管 → B → 主管 → A → …
```

**修复**：`history` 长度上限 + 同一成员最多 2 次 + `recursion_limit`。

### 12.2 信息在转接中丢失

```text
用户：订单 12345 退款
A：查询到订单 12345，已发货
B：请问订单号是多少？        ← 丢了
```

**修复**：用 `TaskBrief` 传结构化 `context`，不要让下家从自然语言里猜。

### 12.3 责任重叠 / 都不处理

```text
用户：我想退货并重新下单
A：这是售后问题…（转 B）
B：这是下单问题…（转 A）
```

**修复**：每个 Agent 的描述写清"负责什么、**不负责什么**"，并有一个兜底 Agent。

### 12.4 说法不一致

```text
A：可以退款
B：超过 7 天不能退款
```

**修复**：业务规则下沉到**工具/服务层**，不让每个 Agent 各自理解规则。

### 12.5 权限越界

```text
产品 Agent 调用了退款工具
```

**修复**：**工具集物理隔离**（不是靠提示词）。每个子 Agent 只 `bind` 自己的工具。

> ⚠️ **这是最重要的一条**：多 Agent 的权限隔离必须靠**代码层的工具集划分**，绝不能只靠提示词说"你不能退款"。

### 12.6 失败速查

| 现象 | 原因 | 修复 |
| :--- | :--- | :--- |
| 无限循环 | 无轮次上限 | history 上限 + 限额 |
| 重复问同样问题 | 上下文没传 | 结构化 `context` |
| 转来转去 | 职责重叠 | 明确边界 + 兜底 |
| token 爆炸 | 传完整 messages | 只传摘要 |
| 延迟高 | 调度层数多 | 前置分类 / 并行 |
| 权限越界 | 工具集共享 | 物理隔离 |

---

## 十三、什么时候"不要"多 Agent

### 13.1 五个"不要"

```text
① 工具少于 10 个 → 单 Agent + 好描述
② 流程确定 → 用状态图，不要 Agent
③ 只是"看起来更架构化" → 不要
④ 团队只有 1 人维护 → 拆分增加维护成本
⑤ 延迟要求 < 3s → 多 Agent 很难满足
```

### 13.2 一个真实的反例

```text
❌ 某项目把"查天气"和"查时间"拆成两个 Agent + 一个主管
   结果：一次问答 4 次模型调用、延迟 9 秒、成本 3 倍
   正确做法：一个 Agent，两个工具
```

### 13.3 渐进式演进

```text
阶段 1：单 Agent，5 个工具          （覆盖 80% 场景）
阶段 2：单 Agent + 意图路由         （工具涨到 15 个时）
阶段 3：工具即子 Agent              （某领域特别复杂时）
阶段 4：Supervisor / Handoff        （多领域、需要协作时）
```

> 💡 **每一步都要有明确的"触发条件"和"收益验证"**。不要因为"架构好看"就跳级。

---

## 十四、完整示例：电商客服系统

### 14.1 架构选型

```text
用户
 │
 ▼
[意图路由]（小模型，结构化输出）
 │
 ├─ order  → 订单 Agent（工具：4 个）
 ├─ refund → 售后 Agent（工具：3 个，含审批 interrupt）
 ├─ product→ 产品 Agent（工具：RAG 检索）
 └─ other  → 通用 Agent（工具：2 个）
       │
       ▼
    [汇总/兜底]
```

**选择 Handoff（一次分流）而不是 Supervisor**：分流一次后就是单领域的多轮对话，不需要主管反复调度。

### 14.2 代码骨架

```python
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from pydantic import BaseModel, Field


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    agent: str
    resolved: bool


class Intent(BaseModel):
    target: Literal["order", "refund", "product", "general"] = Field(
        description="order=订单物流, refund=退款售后, product=产品咨询, general=其他"
    )


def triage(state: State) -> Command[Literal["order", "refund", "product", "general"]]:
    # 只有第一轮需要路由；后续轮次留在当前 Agent
    if state.get("agent") in ("order", "refund", "product", "general"):
        return Command(goto=state["agent"])

    text = state["messages"][-1].content
    target = small_model.with_structured_output(Intent).invoke(text).target
    return Command(goto=target, update={"agent": target})


order_agent = create_agent(model, tools=ORDER_TOOLS, system_prompt=ORDER_PROMPT)
refund_agent = create_agent(model, tools=REFUND_TOOLS, system_prompt=REFUND_PROMPT)
product_agent = create_agent(model, tools=[kb_search], system_prompt=PRODUCT_PROMPT)
general_agent = create_agent(model, tools=[kb_search, transfer_tool],
                             system_prompt=GENERAL_PROMPT)


def order_node(state: State) -> Command:
    r = order_agent.invoke({"messages": state["messages"]})
    return {"messages": [r["messages"][-1]]}


def refund_node(state: State) -> Command:
    r = refund_agent.invoke({"messages": state["messages"]})
    last = r["messages"][-1]

    # 售后 Agent 内的转接工具
    for tc in (getattr(last, "tool_calls", None) or []):
        if tc["name"] == "transfer_to_human":
            return Command(goto="human",
                           update={"messages": [AIMessage("正在为您转接人工客服…")]})
    return {"messages": [last]}


def human_node(state: State) -> Command:
    # 创建人工工单，结束 Agent 流程
    ticket = ticket_service.create(user_id=..., thread_id=..., messages=state["messages"])
    return Command(goto=END, update={
        "messages": [AIMessage(f"已为您创建工单 {ticket.no}，客服会在 24 小时内联系您。")],
        "resolved": False,
    })


builder = StateGraph(State)
builder.add_node("triage", triage)
builder.add_node("order", order_node)
builder.add_node("refund", refund_node)
builder.add_node("product", lambda s: {"messages": [product_agent.invoke({"messages": s["messages"]})["messages"][-1]]})
builder.add_node("general", lambda s: {"messages": [general_agent.invoke({"messages": s["messages"]})["messages"][-1]]})
builder.add_node("human", human_node)

builder.add_edge(START, "triage")
# triage 用 Command 决定去向，无需 add_conditional_edges
for n in ["order", "refund", "product", "general"]:
    builder.add_edge(n, END)          # 单轮完成；多轮靠 checkpointer 续接

support = builder.compile(checkpointer=saver)
```

### 14.3 多轮的处理

**关键问题**：用户第二轮说话时，`triage` 会重新判断意图。

```python
def triage(state):
    # 如果当前已有归属且用户没换话题，直接留在原 Agent
    if state.get("agent") and not is_topic_switch(state["messages"]):
        return Command(goto=state["agent"])
    ...
```

**`is_topic_switch` 可以用规则**（关键词）**或小模型判断**：

```python
def is_topic_switch(messages) -> bool:
    recent = messages[-2:]
    resp = small_model.with_structured_output(SwitchCheck).invoke(
        f"上一轮主题：{recent[0].content}\n用户新消息：{recent[-1].content}\n"
        f"用户是否切换了话题？"
    )
    return resp.switched
```

> 💡 **不要每轮都重新路由**，否则用户在一个 Agent 里聊到一半被抢走。**只在"话题明显变化"时切换。**

### 14.4 这个设计的取舍

| 决策 | 理由 |
| :--- | :--- |
| Handoff 而非 Supervisor | 分流一次即定，不需要反复调度，延迟低 |
| 意图分类用**小模型** | 便宜、快，准确率够用 |
| **不每轮重路由** | 避免上下文割裂 |
| 每个 Agent 工具物理隔离 | 权限安全 |
| 兜底 `general` + `human` | 避免"无人负责" |
| 多轮靠 checkpointer | 天然支持 |

---

## 十五、本章小结与练习

### 核心结论

1. **多 Agent 是"更贵更难"，不是"更高级"**。先用单 Agent，撞墙再拆。
2. **六个拆分信号**：提示词过长、工具过多、领域冲突、权限不同、协作需要、难测试。
3. **五种拓扑**：工具即子 Agent、Supervisor、Handoff、Pipeline、辩论。
4. **工具即子 Agent 最省事**，主 Agent 只看到几个"工具"。
5. **Supervisor 必须防无限循环**：轮次上限 + 历史记录。
6. **Handoff 适合一次分流到位**，比 Supervisor 便宜得多。
7. **Agent 之间用结构化契约通信**（`TaskBrief` / `TaskResult`），不要传自然语言。
8. **只回传最终答案**，避免子 Agent 的 tool 消息撑爆主状态。
9. **权限隔离靠工具集物理隔离**，不是靠提示词。
10. **成本通常 2–5 倍，延迟翻倍**，必须有明确收益才做。

### 动手练习

1. 把一个 12 工具的 Agent 拆成"主 Agent + 2 个子 Agent 工具"，对比误调用率和 token。
2. 用 LangGraph 实现 Supervisor，加 `history` 上限，构造一个会无限循环的场景并验证被拦住。
3. 用 `Command` 实现 Handoff，验证转接后原 Agent 不再参与。
4. 设计一个 `TaskBrief` / `TaskResult`，用 Pydantic 定义并校验。
5. 把第 14 节的例子跑通，测三种输入（订单、退款、产品）的路由准确性。
6. 故意让两个 Agent 职责重叠，观察"转来转去"，然后用"不负责说明"修复。
7. 测算第 14 节架构的单次请求 token 和延迟，与单 Agent 版本对比。

### 下一篇

[10 - 工程化与生产落地](10-工程化与生产落地.md) —— 能跑 demo 和能上线之间，隔着一整个工程体系。
