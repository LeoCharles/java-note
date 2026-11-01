"""08 | 时间旅行：回放与分叉。

对应文档：08-LangGraph持久化与人工介入.md「时间旅行与回放」

运行：
    python 08_persistence/time_travel.py
"""

import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from common import get_model, print_divider


class State(TypedDict):
    question: str
    answer: str
    score: int
    messages: Annotated[list, add_messages]


def build(saver):
    model = get_model()

    def draft(state: State) -> dict:
        r = model.invoke(f"用一句话回答：{state['question']}")
        return {"answer": r.content, "messages": [AIMessage(r.content)]}

    def self_check(state: State) -> dict:
        """自我评分：低于 6 分则触发重写。"""
        r = model.invoke(
            f"评价这个回答是否准确完整，只输出 1-10 的整数。\n"
            f"问题：{state['question']}\n回答：{state['answer']}"
        )
        try:
            score = int("".join(c for c in r.content if c.isdigit())[:2] or "5")
        except ValueError:
            score = 5
        return {"score": min(max(score, 1), 10)}

    def improve(state: State) -> dict:
        r = model.invoke(
            f"改进这个回答，更准确、更具体：\n{state['answer']}"
        )
        return {"answer": r.content, "messages": [AIMessage(f"[改进版] {r.content}")]}

    def done(state: State) -> dict:
        return {}

    def route(state: State) -> str:
        return "improve" if state["score"] < 6 else "done"

    b = StateGraph(State)
    b.add_node("draft", draft)
    b.add_node("check", self_check)
    b.add_node("improve", improve)
    b.add_node("done", done)
    b.add_edge(START, "draft")
    b.add_edge("draft", "check")
    b.add_conditional_edges("check", route, {"improve": "improve", "done": "done"})
    b.add_edge("improve", "done")
    b.add_edge("done", END)

    return b.compile(checkpointer=saver)


def main() -> None:
    graph = build(InMemorySaver())

    print_divider("① 跑一次，产生历史")

    cfg = {"configurable": {"thread_id": "tt:1"}}
    out = graph.invoke({"question": "什么是向量数据库？", "answer": "", "score": 0,
                        "messages": []}, cfg)
    print(f"  最终回答：{out['answer'][:100]}")
    print(f"  自评分数：{out['score']}")

    print_divider("② 列出所有快照")

    history = list(graph.get_state_history(cfg))
    print(f"  共 {len(history)} 个快照")
    for i, s in enumerate(history):
        cp = s.config["configurable"]["checkpoint_id"]
        print(f"  [{i}] step={s.metadata.get('step'):>2}  "
              f"score={s.values.get('score', '-'):>2}  "
              f"next={s.next}")

    print_divider("③ 回放：从某个历史点重新执行")

    # 找 draft 之后的快照
    target = None
    for s in history:
        if s.next and "check" in s.next:
            target = s
            break

    if target:
        cp_id = target.config["configurable"]["checkpoint_id"]
        print(f"  选中 step={target.metadata.get('step')} 的快照")
        print(f"  该点之后会执行：{target.next}")

        cfg_from = {"configurable": {"thread_id": "tt:1", "checkpoint_id": cp_id}}
        out2 = graph.invoke(None, cfg_from)
        print(f"\n  重跑后的回答：{out2['answer'][:100]}")
        print(f"  重跑后的分数：{out2['score']}")
        print("\n  👉 这就是「时间旅行」：同一个起点，可以再跑一次")

    print_divider("④ 分叉：改动一个值再跑")

    # 找到最初的快照（step 0 附近）
    first = history[-1]
    cp_id = first.config["configurable"]["checkpoint_id"]

    cfg_branch = {"configurable": {"thread_id": "tt:1", "checkpoint_id": cp_id}}

    # 改问题，跑出一个全新的分支
    new_cfg = graph.update_state(
        cfg_branch,
        {"question": "向量数据库和传统数据库有什么区别？"},
        as_node="draft",
    )
    out3 = graph.invoke(None, new_cfg)
    print(f"  分叉问题：向量数据库和传统数据库有什么区别？")
    print(f"  分叉回答：{out3['answer'][:120]}")

    print("\n  👉 分支不影响主线历史。这就是「what-if 实验」的基础。")

    print_divider("⑤ 这些能力在实战里用来做什么")

    print("""
  · 复现 bug：拿到用户投诉的 thread_id + checkpoint_id，本地重放
  · 效果评估：同一批历史快照，用新 Prompt 重跑，对比结果
  · 制作评测集：从历史轨迹里挑典型案例
  · 客服复盘：展示"机器人当时每一步想了什么"
  · 调试：定位是哪一步开始跑偏

  ⚠️ 回放会重新执行节点，可能有副作用。
     涉及写操作的，要用只读模式或 mock 工具。
""")


if __name__ == "__main__":
    main()
