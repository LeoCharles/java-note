"""09 | 模式二：Handoff（转接，原 Agent 退出）。

对应文档：09-多Agent协作模式.md「Handoff 转接」

运行：
    python 09_multi_agent/handoff.py

与 Supervisor 的区别：转接后前台退出，不回来。
延迟更低，成本更省。
"""

import sys
from pathlib import Path
from typing import Annotated, Literal, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, AnyMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command
from pydantic import BaseModel, Field

from common import get_model, get_small_model, print_divider
from shared import build_agents


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    agent: str
    order_no: str | None
    escalated: bool


class Route(BaseModel):
    target: Literal["order", "after_sale", "product", "human"] = Field(
        description="order=订单物流, after_sale=退款换货, product=产品咨询, human=投诉/转人工"
    )
    order_no: str | None = Field(default=None, description="提取到的订单号")
    urgency: Literal["low", "normal", "high"] = Field(default="normal")


FORCE_HUMAN = ["投诉", "差评", "举报", "曝光", "起诉", "骗子", "转人工", "叫你们领导"]


def triage(state: State) -> Command[Literal["order", "after_sale", "product", "human"]]:
    """入口分流。只在首轮或话题变化时运行。"""
    text = state["messages"][-1].content

    if any(w in text for w in FORCE_HUMAN):
        return Command(goto="human", update={"agent": "human", "escalated": True})

    # 已经有归属且没明显换话题，留在原处
    if state.get("agent") and len(state["messages"]) <= 2:
        pass

    r = get_small_model().with_structured_output(Route).invoke(
        f"判断意图并提取订单号。\n用户：{text}"
    )

    if r.urgency == "high":
        return Command(goto="human", update={"agent": "human", "escalated": True,
                                             "order_no": r.order_no})

    return Command(goto=r.target, update={"agent": r.target, "order_no": r.order_no})


def make_agent_node(name: str, agent):
    def node(state: State) -> Command:
        r = agent.invoke(
            {"messages": state["messages"]},
            config={"recursion_limit": 8},
        )
        last = r["messages"][-1]
        return Command(goto=END, update={"messages": [last]})

    node.__name__ = name
    return node


def human_node(state: State) -> dict:
    summary = {
        "problem": state["messages"][-1].content,
        "order_no": state.get("order_no"),
    }
    return {
        "messages": [AIMessage(
            f"已为您转接人工客服。工单已创建（订单：{summary['order_no'] or '无'}），"
            f"客服会尽快联系您。"
        )],
        "escalated": True,
    }


def build(saver=None):
    agents = build_agents()

    b = StateGraph(State)
    b.add_node("triage", triage)
    b.add_node("order", make_agent_node("order", agents["order_agent"]))
    b.add_node("after_sale", make_agent_node("after_sale",
                                             agents["after_sale_agent"]))
    b.add_node("product", make_agent_node("product", agents["product_agent"]))
    b.add_node("human", human_node)

    b.add_edge(START, "triage")
    for n in ("order", "after_sale", "product", "human"):
        b.add_edge(n, END)

    return b.compile(checkpointer=saver)


def main() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    graph = build(InMemorySaver())

    print_divider("① 图结构")
    print(graph.get_graph().draw_mermaid())

    print_divider("② 分流测试")

    cases = [
        "我的订单 12345 到哪了",
        "订单 12345 我要退款",
        "电饭锅功率多少",
        "我要投诉你们，太差了",
        "转人工",
    ]

    for q in cases:
        print(f"\n  {'─' * 55}")
        print(f"  用户：{q}")
        r = graph.invoke(
            {"messages": [("user", q)], "agent": "", "order_no": None,
             "escalated": False},
            config={"configurable": {"thread_id": f"ho:{hash(q)}"}},
        )
        print(f"  路由到：{r['agent']}")
        print(f"  回答：{r['messages'][-1].content[:150]}")

    print_divider("③ Handoff vs Supervisor")
    print("""
  ┌──────────────┬──────────────────┬──────────────────┐
  │              │ Supervisor       │ Handoff          │
  ├──────────────┼──────────────────┼──────────────────┤
  │ 控制权        │ 主管始终持有      │ 转给专家后前台退出│
  │ 每次交互       │ 回到主管再决策    │ 直接进专家        │
  │ 延迟          │ 高（多一次调度）  │ 低                │
  │ 成本          │ 高                │ 低                │
  │ 适合          │ 需要多轮协作      │ 一次分流到位      │
  └──────────────┴──────────────────┴──────────────────┘

  💡 客服场景通常用 Handoff：用户的问题是 "订单/售后/产品" 之一，
     分流一次之后就在一个领域里多轮对话，不需要主管反复插手。
""")


if __name__ == "__main__":
    main()
