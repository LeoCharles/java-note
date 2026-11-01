"""07 | LangGraph 最小图：State / Node / Edge。

对应文档：07-LangGraph状态图核心机制.md

运行：
    python 07_langgraph/basic_graph.py
"""

import sys
from pathlib import Path
from typing import Annotated, Literal, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from common import print_divider


# ---------- ① 定义一个带 reducer 的 State ----------

class State(TypedDict):
    messages: Annotated[list, add_messages]     # 追加
    query: str
    category: str
    answer: str
    steps: Annotated[int, lambda a, b: a + b]   # 累加


# ---------- ② 节点：纯函数，返回增量 ----------

def classify(state: State) -> dict:
    q = state["query"]
    if any(k in q for k in ("退款", "退货", "退钱")):
        cat = "refund"
    elif any(k in q for k in ("订单", "物流", "发货")):
        cat = "order"
    elif any(k in q for k in ("怎么", "如何", "是什么")):
        cat = "howto"
    else:
        cat = "other"
    return {"category": cat, "steps": 1}


def handle_refund(state: State) -> dict:
    return {"answer": "退款需要提供订单号，我会为您提交申请。", "steps": 1}


def handle_order(state: State) -> dict:
    return {"answer": "请提供订单号，我帮您查询。", "steps": 1}


def handle_howto(state: State) -> dict:
    return {"answer": "请查看知识库中的操作手册。", "steps": 1}


def handle_other(state: State) -> dict:
    return {"answer": "抱歉，我暂时无法处理这个问题，已为您转接人工。", "steps": 1}


# ---------- ③ 路由函数 ----------

def route(state: State) -> Literal["refund", "order", "howto", "other"]:
    return state["category"]


# ---------- ④ 组图 ----------

def build():
    b = StateGraph(State)

    b.add_node("classify", classify)
    b.add_node("refund", handle_refund)
    b.add_node("order", handle_order)
    b.add_node("howto", handle_howto)
    b.add_node("other", handle_other)

    b.add_edge(START, "classify")
    b.add_conditional_edges(
        "classify",
        route,
        {"refund": "refund", "order": "order", "howto": "howto", "other": "other"},
    )
    for n in ("refund", "order", "howto", "other"):
        b.add_edge(n, END)

    return b.compile()


def main() -> None:
    print_divider("① 图的 Mermaid 定义")
    graph = build()
    print(graph.get_graph().draw_mermaid())

    print_divider("② 执行")

    for q in ["我要退款", "订单在哪", "怎么开发票", "今天天气如何"]:
        out = graph.invoke({"messages": [], "query": q, "steps": 0})
        print(f"  用户：{q}")
        print(f"    分类：{out['category']}")
        print(f"    回答：{out['answer']}")
        print(f"    步数累计：{out['steps']}\n")

    print_divider("③ 默认 reducer vs 自定义 reducer")

    class Demo(TypedDict):
        default_field: str
        appended: Annotated[list, add_messages]
        summed: Annotated[int, lambda a, b: a + b]

    from langgraph.graph.message import add_messages as am  # noqa: F401

    def n1(state):
        return {"default_field": "A 写的",
                "appended": [{"role": "x", "content": "A"}],
                "summed": 1}

    def n2(state):
        return {"default_field": "B 写的",     # 会覆盖 A
                "appended": [{"role": "y", "content": "B"}],   # 会追加
                "summed": 2}                    # 会累加

    b = StateGraph(Demo)
    b.add_node("n1", n1)
    b.add_node("n2", n2)
    b.add_edge(START, "n1")
    b.add_edge("n1", "n2")
    b.add_edge("n2", END)
    g = b.compile()

    r = g.invoke({"default_field": "", "appended": [], "summed": 0})
    print(f"  default_field（默认覆盖）: {r['default_field']}")
    print(f"  appended（add_messages） : {len(r['appended'])} 条")
    print(f"  summed（自定义累加）      : {r['summed']}")

    print_divider("④ 循环图（Agent 的骨架）")

    class LoopState(TypedDict):
        messages: Annotated[list, add_messages]
        rounds: Annotated[int, lambda a, b: a + b]

    def model_node(state):
        # 模拟：前 2 轮要调工具，第 3 轮给答案
        r = state["rounds"]
        if r < 2:
            from langchain_core.messages import AIMessage
            return {"messages": [AIMessage(f"第 {r + 1} 轮：调用工具")],
                    "rounds": 1, "_needs_tool": True}
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage("完成，这是最终答案。")], "rounds": 1}

    def tool_node(state):
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage("工具执行完毕")]}

    def should_continue(state) -> str:
        if state["rounds"] >= 5:
            return "end"
        last = state["messages"][-1]
        if "调用工具" in str(getattr(last, "content", "")):
            return "tools"
        return "end"

    b = StateGraph(LoopState)
    b.add_node("model", model_node)
    b.add_node("tools", tool_node)
    b.add_edge(START, "model")
    b.add_conditional_edges("model", should_continue, {"tools": "tools", "end": END})
    b.add_edge("tools", "model")
    lg = b.compile()

    print(lg.get_graph().draw_mermaid())

    out = lg.invoke({"messages": [], "rounds": 0})
    print("\n  执行轨迹：")
    for m in out["messages"]:
        print(f"    {m.type}: {m.content}")
    print(f"  总轮次：{out['rounds']}")

    print_divider("小结")
    print("  · State 的字段用 Annotated 指定 reducer；没有 reducer 就是覆盖")
    print("  · 节点只返回「要改的字段」，不要返回整个 state")
    print("  · 循环必须靠条件边 + 终止条件，否则 recursion_limit 兜底抛异常")
    print("  · draw_mermaid() 是设计评审的好材料")


if __name__ == "__main__":
    main()
