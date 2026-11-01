"""09 | 模式三：Supervisor（主管调度）。

对应文档：09-多Agent协作模式.md「Supervisor」

运行：
    python 09_multi_agent/supervisor.py

主管只做两件事：决定下一步交给谁、判断是否可以结束。
"""

import sys
from pathlib import Path
from typing import Annotated, Literal, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from common import get_model, get_small_model, print_divider
from shared import build_agents

MEMBERS = ["order_agent", "after_sale_agent", "product_agent"]


class TeamState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    next: str
    history: Annotated[list[str], lambda a, b: a + b]
    findings: Annotated[list[str], lambda a, b: a + b]


class Decision(BaseModel):
    next: Literal["order_agent", "after_sale_agent", "product_agent", "FINISH"] = Field(
        description="下一个发言者，或 FINISH 表示信息已足够"
    )
    reason: str = Field(description="选择理由，一句话")


SUPERVISOR_PROMPT = """你是客服主管，负责分派任务给团队成员。

成员职责：
- order_agent：订单查询、物流、改地址、取消订单
- after_sale_agent：退款、换货、维修
- product_agent：产品功能、参数、使用方法

规则：
1. 每次只派给一个成员。
2. 成员完成后，判断信息是否足够回答用户。
3. 足够则返回 FINISH。
4. 同一个成员连续派发不得超过 2 次。

已派发历史：{history}
已获得信息：{findings}
"""


def make_supervisor():
    model = get_small_model()     # 路由用小模型，省钱

    def supervisor(state: TeamState) -> dict:
        # 硬性轮次上限，防止无限循环
        if len(state.get("history", [])) >= 6:
            return {"next": "FINISH", "history": ["FINISH"]}

        prompt = SUPERVISOR_PROMPT.format(
            history=state.get("history", []) or "无",
            findings=state.get("findings", []) or "无",
        )
        d = model.with_structured_output(Decision).invoke(
            [SystemMessage(prompt)] + state["messages"]
        )
        return {"next": d.next, "history": [f"{d.next}({d.reason})"]}

    return supervisor


def make_member(name: str, agent):
    def node(state: TeamState) -> dict:
        r = agent.invoke({"messages": state["messages"]},
                         config={"recursion_limit": 8})
        last = r["messages"][-1]
        # 只回传最终答案，避免子 Agent 的 tool 消息污染主状态
        return {"messages": [AIMessage(f"[{name}] {last.content}")],
                "findings": [f"{name}: {last.content[:80]}"]}

    node.__name__ = name
    return node


def synthesize(state: TeamState) -> dict:
    model = get_model()
    r = model.invoke(
        [SystemMessage("根据以下团队讨论，给用户一个完整、简洁的最终答复，不超过 150 字。")]
        + state["messages"]
    )
    return {"messages": [r]}


def route(state: TeamState) -> str:
    if len(state.get("history", [])) >= 6:
        return "synthesize"
    return "synthesize" if state["next"] == "FINISH" else state["next"]


def build(saver=None):
    agents = build_agents()

    b = StateGraph(TeamState)
    b.add_node("supervisor", make_supervisor())
    for name in MEMBERS:
        b.add_node(name, make_member(name, agents[name]))
    b.add_node("synthesize", synthesize)

    b.add_edge(START, "supervisor")
    b.add_conditional_edges(
        "supervisor", route,
        {**{m: m for m in MEMBERS}, "synthesize": "synthesize"},
    )
    for name in MEMBERS:
        b.add_edge(name, "supervisor")
    b.add_edge("synthesize", END)

    return b.compile(checkpointer=saver)


def main() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    graph = build(InMemorySaver())

    print_divider("① 图结构")
    print(graph.get_graph().draw_mermaid())

    print_divider("② 多 Agent 协作测试")

    cases = [
        "订单 12345 到哪了？",
        "订单 12345 我要退款，另外电饭锅保修多久？",
        "你好",
    ]

    for q in cases:
        print(f"\n  {'─' * 60}")
        print(f"  用户：{q}")

        r = graph.invoke(
            {"messages": [("user", q)], "next": "", "history": [], "findings": []},
            config={"configurable": {"thread_id": f"sup:{hash(q)}"},
                    "recursion_limit": 25},
        )

        print(f"\n  调度历史：")
        for h in r["history"]:
            print(f"    · {h}")

        print(f"\n  最终回答：{r['messages'][-1].content}")

    print_divider("③ 成本账")
    print("""
  单 Agent（2 轮工具）：
    输入 ≈ 1900 × 3 次 = 5700 token，输出 600      ≈ 6300

  Supervisor（3 专家，平均转 2 次）：
    主管决策 1900 × 4 = 7600
    专家 1500 × 2 = 3000
    汇总 1000
                                        ≈ 14600（2.3 倍）

  延迟：
    单 Agent    ≈ 4.5s
    Supervisor  ≈ 10s

  👉 多 Agent 要有明确收益才做。
     降本：路由用小模型（本例）、只回传摘要、前置意图分类跳过主管。
""")

    print_divider("④ 最常见的 bug：无限循环")
    print("""
  现象：主管 → A → 主管 → B → 主管 → A → …

  三层防护：
  1. history 长度上限（本例：6）
  2. 同一成员最多 2 次（可在 supervisor prompt 里约束 + 代码校验）
  3. recursion_limit 兜底

  根因通常是：
  · 成员职责描述重叠，"谁都能处理"
  · 成员回答"我处理不了"却没转给别人
  · FINISH 判断逻辑不清
""")


if __name__ == "__main__":
    main()
