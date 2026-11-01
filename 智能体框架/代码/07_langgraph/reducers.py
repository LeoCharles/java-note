"""07 | reducer 专题：覆盖、追加、累加、合并、去重、并行冲突。

对应文档：07-LangGraph状态图核心机制.md「State」

运行：
    python 07_langgraph/reducers.py
"""

import operator
import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from common import print_divider


def merge_dict(left: dict, right: dict) -> dict:
    return {**left, **right}


def dedupe(left: list, right: list) -> list:
    return list(dict.fromkeys(left + right))


def demo_coverage() -> None:
    print_divider("① 默认行为：覆盖")

    class S(TypedDict):
        value: str
        count: int

    def a(s): return {"value": "A", "count": 1}
    def b(s): return {"value": "B", "count": 2}

    g = StateGraph(S)
    g.add_node("a", a); g.add_node("b", b)
    g.add_edge(START, "a"); g.add_edge("a", "b"); g.add_edge("b", END)
    out = g.compile().invoke({"value": "", "count": 0})

    print(f"  最终 value={out['value']!r}  count={out['count']}")
    print("  👉 b 覆盖了 a 的写入，count 也是 b 的值")


def demo_append() -> None:
    print_divider("② add_messages：追加 + 按 id 更新")

    class S(TypedDict):
        messages: Annotated[list, add_messages]

    def a(s): return {"messages": [HumanMessage("你好")]}
    def b(s): return {"messages": [AIMessage("你好，有什么可以帮你")]}

    g = StateGraph(S)
    g.add_node("a", a); g.add_node("b", b)
    g.add_edge(START, "a"); g.add_edge("a", "b"); g.add_edge("b", END)
    out = g.compile().invoke({"messages": []})

    print(f"  消息数：{len(out['messages'])}")
    for m in out["messages"]:
        print(f"    {m.type}: {m.content}")

    print("\n  --- 按 id 更新（修正一条消息）---")

    class S2(TypedDict):
        messages: Annotated[list, add_messages]

    fixed = AIMessage("修正后的内容", id="msg-1")

    def seed(s):
        return {"messages": [AIMessage("原始内容", id="msg-1")]}

    def fix(s):
        return {"messages": [fixed]}

    g2 = StateGraph(S2)
    g2.add_node("seed", seed); g2.add_node("fix", fix)
    g2.add_edge(START, "seed"); g2.add_edge("seed", "fix"); g2.add_edge("fix", END)
    out2 = g2.compile().invoke({"messages": []})

    print(f"  消息数：{len(out2['messages'])}（同 id 是替换，不是追加）")
    print(f"  内容：{out2['messages'][0].content}")


def demo_custom() -> None:
    print_divider("③ 自定义 reducer：累加 / 合并 / 去重")

    class S(TypedDict):
        count: Annotated[int, operator.add]
        config: Annotated[dict, merge_dict]
        tags: Annotated[list, dedupe]

    def a(s):
        return {"count": 1, "config": {"a": 1}, "tags": ["x", "y"]}

    def b(s):
        return {"count": 10, "config": {"b": 2}, "tags": ["y", "z"]}

    g = StateGraph(S)
    g.add_node("a", a); g.add_node("b", b)
    g.add_edge(START, "a"); g.add_edge("a", "b"); g.add_edge("b", END)
    out = g.compile().invoke({"count": 0, "config": {}, "tags": []})

    print(f"  count（operator.add）: {out['count']}  (0+1+10)")
    print(f"  config（merge_dict）  : {out['config']}")
    print(f"  tags（dedupe）        : {out['tags']}")


def demo_parallel_merge() -> None:
    print_divider("④ 并行分支：有 reducer 就能合并")

    class S(TypedDict):
        results: Annotated[list, operator.add]

    def pa(s): return {"results": ["A"]}
    def pb(s): return {"results": ["B"]}
    def pc(s): return {"results": ["C"]}

    g = StateGraph(S)
    g.add_node("a", pa); g.add_node("b", pb); g.add_node("c", pc)
    g.add_edge(START, "a")
    g.add_edge(START, "b")
    g.add_edge(START, "c")
    g.add_edge(["a", "b", "c"], END)

    out = g.compile().invoke({"results": []})
    print(f"  三路并行结果：{out['results']}（顺序可能不同）")


def demo_parallel_conflict() -> None:
    print_divider("⑤ 并行写同一字段且无 reducer → 报错")

    class S(TypedDict):
        value: str            # 没有 reducer

    def pa(s): return {"value": "A"}
    def pb(s): return {"value": "B"}

    g = StateGraph(S)
    g.add_node("a", pa); g.add_node("b", pb)
    g.add_edge(START, "a"); g.add_edge(START, "b")
    g.add_edge(["a", "b"], END)

    try:
        g.compile().invoke({"value": ""})
        print("  （没有报错，说明当前版本容忍了）")
    except Exception as e:
        print(f"  ✅ 如期报错：{type(e).__name__}")
        print(f"     {str(e)[:200]}")
        print("\n  👉 修复：加 reducer，或让两路写不同字段，或合并成一个节点")


def demo_mutation_bug() -> None:
    print_divider("⑥ 常见 bug：原地修改 state")

    class S(TypedDict):
        items: Annotated[list, operator.add]

    def bad(s):
        s["items"].append("x")     # ❌ 原地修改
        return s                   # ❌ 返回整个 state

    def good(s):
        return {"items": ["x"]}    # ✅ 返回增量

    g = StateGraph(S)
    g.add_node("bad", bad)
    g.add_edge(START, "bad"); g.add_edge("bad", END)
    out = g.compile().invoke({"items": []})
    print(f"  bad 节点结果：{out['items']}（行为不确定，可能重复可能丢）")

    g2 = StateGraph(S)
    g2.add_node("good", good)
    g2.add_edge(START, "good"); g2.add_edge("good", END)
    out2 = g2.compile().invoke({"items": []})
    print(f"  good 节点结果：{out2['items']}（确定）")


def demo_unserializable() -> None:
    print_divider("⑦ State 里有不可序列化对象时的坑")

    class Bad(TypedDict):
        client: object          # 比如 httpx.Client

    print("  把数据库连接、HTTP 客户端放在 State 里，checkpoint 会失败。")
    print("  正确做法：")
    print("    · 客户端放模块级变量或 runtime.context")
    print("    · State 里只放可 JSON/msgpack 序列化的数据")
    print("    · 大对象存 ID，用时再查")


def main() -> None:
    demo_coverage()
    demo_append()
    demo_custom()
    demo_parallel_merge()
    demo_parallel_conflict()
    demo_mutation_bug()
    demo_unserializable()


if __name__ == "__main__":
    main()
