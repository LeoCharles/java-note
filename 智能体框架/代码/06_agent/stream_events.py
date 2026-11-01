"""06 | 流式观察：astream_events 拿到 Agent 的每一步。

对应文档：06-第一个Agent与ReAct循环.md「流式观察」

运行：
    python 06_agent/stream_events.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import get_model, print_divider
from first_agent import SYSTEM, TOOLS

TOOL_LABELS = {
    "get_order_detail": "正在查询订单…",
    "search_orders": "正在搜索订单…",
    "apply_refund": "正在提交退款申请…",
}


async def demo_events(agent) -> None:
    question = "订单 12345 到哪了？如果还没到我要退款"
    print(f"  用户：{question}\n")

    t0 = time.time()
    first_token_at = None
    tool_seq = []

    async for ev in agent.astream_events(
        {"messages": [("user", question)]},
        config={"recursion_limit": 10},
        version="v2",
    ):
        kind = ev["event"]
        name = ev.get("name", "")

        if kind == "on_chat_model_stream":
            content = ev["data"]["chunk"].content
            if content:
                if first_token_at is None:
                    first_token_at = time.time() - t0
                    print(f"  [首字 {first_token_at:.2f}s] ", end="")
                print(content, end="", flush=True)

        elif kind == "on_tool_start":
            tool_seq.append(name)
            label = TOOL_LABELS.get(name, f"正在执行 {name}…")
            print(f"\n  [{time.time() - t0:.2f}s] 🔍 {label}")
            print(f"           参数：{json.dumps(ev['data'].get('input'), ensure_ascii=False)}")

        elif kind == "on_tool_end":
            out = ev["data"].get("output")
            body = str(out)
            print(f"  [{time.time() - t0:.2f}s] ✅ 完成：{body[:100]}"
                  f"{'…' if len(body) > 100 else ''}")

    print(f"\n\n  总耗时：{time.time() - t0:.2f}s")
    print(f"  首字延迟：{first_token_at:.2f}s" if first_token_at else "  无输出")
    print(f"  工具序列：{tool_seq}")


async def demo_sse(agent) -> None:
    """模拟给前端的 SSE 数据。"""

    def sse(obj: dict) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    async def generate():
        async for ev in agent.astream_events(
            {"messages": [("user", "订单 12345 到哪了")]},
            config={"recursion_limit": 10},
            version="v2",
        ):
            k = ev["event"]
            if k == "on_chat_model_stream":
                c = ev["data"]["chunk"].content
                if c:
                    yield sse({"type": "token", "text": c})
            elif k == "on_tool_start":
                yield sse({"type": "tool_start",
                           "label": TOOL_LABELS.get(ev["name"], "正在处理…")})
            elif k == "on_tool_end":
                yield sse({"type": "tool_end", "name": ev["name"]})
        yield sse({"type": "done"})

    print("  【前端会收到的数据流】\n")
    async for chunk in generate():
        print("  " + chunk.strip())


async def demo_stream_modes() -> None:
    """对比 LangGraph 的四种 stream_mode（需要图对象，这里用 Agent 的底层图）。"""
    print_divider("stream_mode 差异")

    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    from typing import Annotated, TypedDict
    from langchain_core.messages import AIMessage

    class S(TypedDict):
        messages: Annotated[list, add_messages]
        stage: str

    model = get_model()

    def step1(state):
        return {"messages": [AIMessage("第一步完成")], "stage": "s1"}

    def step2(state):
        return {"messages": [AIMessage("第二步完成")], "stage": "s2"}

    b = StateGraph(S)
    b.add_node("step1", step1)
    b.add_node("step2", step2)
    b.add_edge(START, "step1")
    b.add_edge("step1", "step2")
    b.add_edge("step2", END)
    g = b.compile()

    print("\n  --- stream_mode='values'（每步的完整状态）---")
    for s in g.stream({"messages": []}, stream_mode="values"):
        print(f"    stage={s.get('stage')}  messages={len(s['messages'])} 条")

    print("\n  --- stream_mode='updates'（每步的增量）---")
    for u in g.stream({"messages": []}, stream_mode="updates"):
        print(f"    {u}")

    print("\n  👉 values 适合调试，updates 适合展示进度")


async def main() -> None:
    from langchain.agents import create_agent

    model = get_model()
    agent = create_agent(model=model, tools=TOOLS, system_prompt=SYSTEM,
                         name="demo_agent")

    print_divider("① astream_events：完整事件流")
    await demo_events(agent)

    print_divider("② SSE 格式（给前端）")
    await demo_sse(agent)

    await demo_stream_modes()

    print_divider("小结")
    print("  · on_chat_model_stream：逐字输出")
    print("  · on_tool_start / on_tool_end：工具进度")
    print("  · 首字延迟远小于总延迟，感知体验靠这个")
    print("  · 工具名要翻译成人话再给用户看")


if __name__ == "__main__":
    asyncio.run(main())
