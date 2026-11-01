"""08 | Checkpointer：多轮、快照、历史。

对应文档：08-LangGraph持久化与人工介入.md

运行：
    python 08_persistence/checkpoint_demo.py

说明：
    默认用 InMemorySaver（进程内，重启丢失）。
    .env 里配了 PG_URI 时会尝试用 PostgresSaver。
"""

import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from common import get_model, print_divider, settings


class State(TypedDict):
    messages: Annotated[list, add_messages]
    turns: Annotated[int, lambda a, b: a + b]


def build_graph(saver):
    model = get_model()

    def chat(state: State) -> dict:
        r = model.invoke(state["messages"])
        return {"messages": [r], "turns": 1}

    b = StateGraph(State)
    b.add_node("chat", chat)
    b.add_edge(START, "chat")
    b.add_edge("chat", END)
    return b.compile(checkpointer=saver)


def get_saver():
    """按配置返回 saver。生产用 Postgres。"""
    if settings.pg_uri:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            print(f"  [存储] Postgres: {settings.pg_uri.split('@')[-1]}")
            ctx = PostgresSaver.from_conn_string(settings.pg_uri)
            saver = ctx.__enter__()
            saver.setup()
            return saver, ctx
        except Exception as e:
            print(f"  [警告] Postgres 不可用（{type(e).__name__}: {e}）")
            print("  [存储] 降级为 InMemorySaver（重启丢失）")

    from langgraph.checkpoint.memory import InMemorySaver

    print("  [存储] InMemorySaver（进程内，重启丢失）")
    return InMemorySaver(), None


def main() -> None:
    print_divider("① 准备工作")
    saver, ctx = get_saver()
    graph = build_graph(saver)

    print_divider("② 多轮对话：同一 thread_id 自动续接")

    cfg = {"configurable": {"thread_id": "demo:u1:conv1"}}

    for q in ["我叫张三", "我在研发部", "我刚才说我叫什么？"]:
        r = graph.invoke({"messages": [("user", q)], "turns": 0}, cfg)
        print(f"  用户：{q}")
        print(f"  助手：{r['messages'][-1].content[:80]}")
        print(f"  （当前会话共 {len(r['messages'])} 条消息）\n")

    print("  👉 第二次 invoke 只传了新消息，历史是 checkpointer 自动带上的")

    print_divider("③ 换一个 thread_id = 全新会话")

    cfg2 = {"configurable": {"thread_id": "demo:u1:conv2"}}
    r = graph.invoke({"messages": [("user", "我刚才说我叫什么？")], "turns": 0}, cfg2)
    print(f"  助手：{r['messages'][-1].content[:120]}")
    print("  👉 它不知道，因为这是新的会话线")

    print_divider("④ 读状态")

    snap = graph.get_state(cfg)
    print(f"  values.messages : {len(snap.values['messages'])} 条")
    print(f"  values.turns    : {snap.values['turns']}")
    print(f"  next            : {snap.next}  （空元组 = 已结束）")
    print(f"  metadata        : {snap.metadata}")

    print_divider("⑤ 历史快照")

    history = list(graph.get_state_history(cfg))
    print(f"  共 {len(history)} 个快照（新 → 旧）")
    for s in history[:8]:
        cp_id = s.config["configurable"].get("checkpoint_id", "?")
        print(f"    step={s.metadata.get('step'):>2}  next={s.next}  "
              f"cp={cp_id[:20]}…")

    print("\n  👉 每个超步一份快照，这是时间旅行和回放的基础")

    print_divider("⑥ 人工更正状态：update_state")

    graph.update_state(
        cfg,
        {"messages": [HumanMessage("（人工插入：已核实用户身份为张三，工号 1001）")]},
        as_node="chat",
    )
    snap = graph.get_state(cfg)
    print(f"  更新后消息数：{len(snap.values['messages'])}")
    print(f"  最后一条：{snap.values['messages'][-1].content}")

    print("\n  👉 messages 有 add_messages reducer，所以是追加不是替换")

    print_divider("⑦ 显式指定 checkpoint_id：从历史点重跑")

    target = None
    for s in history:
        if s.metadata.get("step") == 1:
            target = s
            break

    if target:
        cp_id = target.config["configurable"]["checkpoint_id"]
        new_cfg = {"configurable": {"thread_id": cfg["configurable"]["thread_id"],
                                    "checkpoint_id": cp_id}}
        hist_snap = graph.get_state(new_cfg)
        print(f"  从 step=1 读取：{len(hist_snap.values['messages'])} 条消息")
        print(f"  下一步：{hist_snap.next}")
        print("\n  👉 从这里 invoke(None, new_cfg) 就能分叉出一条新的执行路径")

    if ctx:
        ctx.__exit__(None, None, None)

    print_divider("小结")
    print("  · checkpointer + thread_id = 多轮对话，无需手动传历史")
    print("  · 每个超步一个快照，支持 get_state_history / 时间旅行")
    print("  · update_state 可人工更正，as_node 决定下一步走向")
    print("  · 生产用 PostgresSaver，注意 state 必须可序列化")
    print("  · InMemorySaver 只用于开发和测试")


if __name__ == "__main__":
    main()
