"""07 | 进阶控制流：Command、Send（动态并行）、子图。

对应文档：07-LangGraph状态图核心机制.md「Command 与 Send」「子图」

运行：
    python 07_langgraph/parallel_send.py
"""

import operator
import sys
from pathlib import Path
from typing import Annotated, Literal, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send

from common import get_model, print_divider


# ============ ① Command：节点自己决定去哪 + 同时更新状态 ============

class CmdState(TypedDict):
    query: str
    intent: str
    result: str


def classify_with_command(state: CmdState) -> Command[Literal["billing", "tech", "other"]]:
    q = state["query"]
    if any(k in q for k in ("发票", "付款", "账单")):
        return Command(goto="billing", update={"intent": "billing"})
    if any(k in q for k in ("报错", "崩溃", "打不开")):
        return Command(goto="tech", update={"intent": "tech"})
    return Command(goto="other", update={"intent": "other"})


def billing(state): return {"result": "转财务处理"}
def tech(state): return {"result": "转技术支持"}
def other(state): return {"result": "转人工"}


def demo_command() -> None:
    b = StateGraph(CmdState)
    b.add_node("classify", classify_with_command)
    b.add_node("billing", billing)
    b.add_node("tech", tech)
    b.add_node("other", other)
    b.add_edge(START, "classify")
    for n in ("billing", "tech", "other"):
        b.add_edge(n, END)
    g = b.compile()

    print(g.get_graph().draw_mermaid())
    print()

    for q in ["发票怎么开", "系统报错了", "你好"]:
        out = g.invoke({"query": q, "intent": "", "result": ""})
        print(f"  {q} → intent={out['intent']}, result={out['result']}")

    print("\n  👉 Command 的优势：路由逻辑和状态更新写在同一个节点里，内聚")


# ============ ② Send：动态并行（Map-Reduce） ============

class MapState(TypedDict):
    topic: str
    subtopics: list[str]
    summaries: Annotated[list[str], operator.add]
    final: str


def plan(state: MapState) -> dict:
    """把主题拆成 N 个子问题（这里用规则模拟，实际可用模型）。"""
    t = state["topic"]
    return {"subtopics": [f"{t}的定义", f"{t}的使用场景", f"{t}的常见问题"]}


def fan_out(state: MapState):
    """关键：返回 N 个 Send，每个 Send 是一个并行任务。"""
    return [Send("summarize", {"topic": state["topic"], "subtopic": s})
            for s in state["subtopics"]]


def summarize(state: dict) -> dict:
    # 注意：Send 传进来的 state 只有指定字段
    return {"summaries": [f"[{state['subtopic']}] 摘要内容"]}


def aggregate(state: MapState) -> dict:
    return {"final": f"共 {len(state['summaries'])} 段摘要：\n" + "\n".join(
        f"  · {s}" for s in state["summaries"]
    )}


def demo_send() -> None:
    b = StateGraph(MapState)
    b.add_node("plan", plan)
    b.add_node("summarize", summarize)
    b.add_node("aggregate", aggregate)

    b.add_edge(START, "plan")
    b.add_conditional_edges("plan", fan_out, ["summarize"])
    b.add_edge("summarize", "aggregate")
    b.add_edge("aggregate", END)
    g = b.compile()

    print(g.get_graph().draw_mermaid())
    print()

    out = g.invoke({"topic": "Redis", "subtopics": [], "summaries": [], "final": ""})
    print(f"  {out['final']}")

    print("\n  👉 Send 适合「运行时才知道要并行几路」的场景")
    print("     比如：批量文档处理、多查询并行检索、批量工单分类")


# ============ ③ Send + 模型：真正有用的并行 ============

def demo_send_with_model() -> None:
    print_divider("Send + 模型：并行回答多个子问题")

    model = get_model()

    class S(TypedDict):
        question: str
        sub_questions: list[str]
        answers: Annotated[list[dict], operator.add]
        final: str

    def split(state: S) -> dict:
        raw = model.invoke(
            f"把这个问题拆成 3 个可独立回答的子问题，每行一个，不要编号：\n{state['question']}"
        ).content
        subs = [l.strip("- •0123456789. ") for l in raw.split("\n") if l.strip()]
        return {"sub_questions": subs[:3]}

    def fan(state: S):
        return [Send("answer_one", {"q": s}) for s in state["sub_questions"]]

    def answer_one(payload: dict) -> dict:
        a = model.invoke(f"简洁回答（不超过 40 字）：{payload['q']}").content
        return {"answers": [{"q": payload["q"], "a": a}]}

    def merge(state: S) -> dict:
        body = "\n".join(f"  {i}. {x['q']}\n     → {x['a']}"
                         for i, x in enumerate(state["answers"], 1))
        return {"final": f"问题：{state['question']}\n{body}"}

    b = StateGraph(S)
    b.add_node("split", split)
    b.add_node("answer_one", answer_one)
    b.add_node("merge", merge)
    b.add_edge(START, "split")
    b.add_conditional_edges("split", fan, ["answer_one"])
    b.add_edge("answer_one", "merge")
    b.add_edge("merge", END)
    g = b.compile()

    out = g.invoke({"question": "微服务架构相比单体有哪些优缺点？",
                    "sub_questions": [], "answers": [], "final": ""})
    print(f"\n  {out['final']}")


# ============ ④ 子图：把图当节点 ============

class SubState(TypedDict):
    text: str
    result: str


def sub_upper(state: SubState) -> dict:
    return {"result": state["text"].upper()}


def sub_reverse(state: SubState) -> dict:
    return {"result": state["text"][::-1]}


def build_sub(transform: str):
    b = StateGraph(SubState)
    b.add_node("do", sub_upper if transform == "upper" else sub_reverse)
    b.add_edge(START, "do")
    b.add_edge("do", END)
    return b.compile()


class ParentState(TypedDict):
    text: str
    outputs: Annotated[list[str], operator.add]


def demo_subgraph() -> None:
    print_divider("子图：在父图里调用独立的图")

    sub_up = build_sub("upper")
    sub_rev = build_sub("reverse")

    def call_upper(state: ParentState) -> dict:
        r = sub_up.invoke({"text": state["text"], "result": ""})
        return {"outputs": [f"upper: {r['result']}"]}

    def call_rev(state: ParentState) -> dict:
        r = sub_rev.invoke({"text": state["text"], "result": ""})
        return {"outputs": [f"reverse: {r['result']}"]}

    b = StateGraph(ParentState)
    b.add_node("up", call_upper)
    b.add_node("rev", call_rev)
    b.add_edge(START, "up")
    b.add_edge(START, "rev")
    b.add_edge(["up", "rev"], END)
    g = b.compile()

    out = g.invoke({"text": "hello", "outputs": []})
    for o in sorted(out["outputs"]):
        print(f"  {o}")

    print("\n  👉 子图让「多 Agent」成为可能：每个专家是一张图，独立开发测试")


def main() -> None:
    print_divider("① Command：节点自己决定跳转")
    demo_command()

    print_divider("② Send：动态并行")
    demo_send()

    demo_send_with_model()

    demo_subgraph()

    print_divider("小结")
    print("  · Command：适合分支不固定、需要同时更新状态的场景")
    print("  · Send：适合运行时才知道并行数量的场景（Map-Reduce）")
    print("  · 子图：适合把复杂流程拆成独立可测的模块")


if __name__ == "__main__":
    main()
