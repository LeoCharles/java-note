"""08 | interrupt：真正的人工介入。

对应文档：08-LangGraph持久化与人工介入.md「interrupt」

运行：
    python 08_persistence/interrupt_demo.py

这个例子演示：退款金额 > 阈值时暂停，等人工审批后继续。
关键点：中断可以跨进程、跨天，且不会重复执行副作用。
"""

import sys
from pathlib import Path
from typing import Annotated, Literal, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt

from common import print_divider

# 模拟业务系统
REFUNDS: dict[str, dict] = {}
ORDERS = {
    "12345": {"amount": 299.0, "status": "已发货"},
    "67890": {"amount": 8999.0, "status": "已发货"},
}

AUTO_APPROVE_LIMIT = 2000


class State(TypedDict):
    order_no: str
    amount: float
    risk: str
    decision: dict | None
    refund_id: str | None
    messages: Annotated[list, add_messages]


# ---------- 节点 ----------

def check_node(state: State) -> dict:
    """纯查询，无副作用 —— 因为 interrupt 恢复时节点会从头重跑。"""
    o = ORDERS.get(state["order_no"])
    if not o:
        return {"risk": "invalid", "amount": 0}
    return {"amount": o["amount"],
            "risk": "high" if o["amount"] > AUTO_APPROVE_LIMIT else "low"}


def approval_node(state: State) -> dict:
    """需要人工审批时暂停。"""
    if state["risk"] != "high":
        return {"decision": {"approved": True, "by": "auto",
                             "reason": "金额在自动审批范围内"}}

    # ⚠️ 重要：interrupt 之前的代码在恢复时会重跑，
    #    所以这里不能有写操作
    answer = interrupt({
        "type": "refund_approval",
        "order_no": state["order_no"],
        "amount": state["amount"],
        "risk": state["risk"],
        "question": f"订单 {state['order_no']} 申请退款 {state['amount']} 元，是否批准？",
    })

    return {"decision": {
        "approved": bool(answer.get("approved")),
        "by": answer.get("operator", "human"),
        "reason": answer.get("comment", ""),
    }}


def route(state: State) -> Literal["execute", "reject"]:
    return "execute" if (state.get("decision") or {}).get("approved") else "reject"


def execute_node(state: State) -> dict:
    """真正执行 —— 幂等键防止恢复时重复执行。"""
    key = state["order_no"]
    if key in REFUNDS:
        print(f"    [execute] 已存在退款单，直接返回（幂等）")
        return {"refund_id": REFUNDS[key]["refund_id"],
                "messages": [AIMessage(f"退款已提交，单号 {REFUNDS[key]['refund_id']}")]}

    rid = f"RF{len(REFUNDS) + 1001}"
    REFUNDS[key] = {"refund_id": rid, "amount": state["amount"]}
    print(f"    [execute] 实际执行退款：{rid}，{state['amount']} 元")

    return {"refund_id": rid,
            "messages": [AIMessage(f"退款已提交，金额 {state['amount']} 元，"
                                   f"单号 {rid}，预计 1-3 个工作日到账。")]}


def reject_node(state: State) -> dict:
    reason = (state.get("decision") or {}).get("reason", "未通过审核")
    return {"messages": [AIMessage(f"退款申请未通过：{reason}")]}


def build(saver):
    b = StateGraph(State)
    b.add_node("check", check_node)
    b.add_node("approve", approval_node)
    b.add_node("execute", execute_node)
    b.add_node("reject", reject_node)

    b.add_edge(START, "check")
    b.add_edge("check", "approve")
    b.add_conditional_edges("approve", route,
                            {"execute": "execute", "reject": "reject"})
    b.add_edge("execute", END)
    b.add_edge("reject", END)

    return b.compile(checkpointer=saver)


def show_interrupts(graph, cfg) -> dict | None:
    snap = graph.get_state(cfg)
    payload = None
    for task in snap.tasks:
        for itr in getattr(task, "interrupts", []):
            payload = itr.value
    return payload


def main() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    graph = build(InMemorySaver())

    print_divider("① 小额：自动通过，不中断")

    cfg = {"configurable": {"thread_id": "refund:small"}}
    out = graph.invoke({"order_no": "12345", "amount": 0, "risk": "",
                        "decision": None, "refund_id": None, "messages": []}, cfg)
    print(f"  回答：{out['messages'][-1].content}")
    print(f"  退款单：{out['refund_id']}")

    print_divider("② 大额：跑到 approve 节点挂起")

    cfg2 = {"configurable": {"thread_id": "refund:big"}}
    out = graph.invoke({"order_no": "67890", "amount": 0, "risk": "",
                        "decision": None, "refund_id": None, "messages": []}, cfg2)

    snap = graph.get_state(cfg2)
    print(f"  是否挂起：{bool(snap.next)}  等待节点：{snap.next}")

    payload = show_interrupts(graph, cfg2)
    print(f"  中断载荷：\n    {payload}")

    print("\n  👉 此时进程可以退出、可以重启、可以等到明天")
    print("     状态已经存在 checkpoint 里，不占用任何资源")

    print_divider("③ 恢复：传入审批结果")

    out = graph.invoke(Command(resume={"approved": True,
                                       "operator": "admin-001",
                                       "comment": "客户是老客户，同意"}), cfg2)
    print(f"  回答：{out['messages'][-1].content}")
    print(f"  退款单：{out['refund_id']}")

    print_divider("④ 驳回的分支")

    cfg3 = {"configurable": {"thread_id": "refund:reject"}}
    graph.invoke({"order_no": "67890", "amount": 0, "risk": "",
                  "decision": None, "refund_id": None, "messages": []}, cfg3)
    out = graph.invoke(Command(resume={"approved": False,
                                       "comment": "订单已完成超过 30 天"}), cfg3)
    print(f"  回答：{out['messages'][-1].content}")

    print_divider("⑤ 恢复的幂等性验证")

    print("  场景：执行成功后由于网络问题又收到一次 resume")
    before = len(REFUNDS)
    try:
        out = graph.invoke(Command(resume={"approved": True}), cfg2)
        print(f"  再次恢复结果：{out['messages'][-1].content}")
    except Exception as e:
        print(f"  恢复失败（正常，因为已恢复过）：{type(e).__name__}")
    print(f"  退款记录数：{before} → {len(REFUNDS)}（应不变）")

    print("\n  👉 就算被执行两次，幂等键保证了不会重复退款")

    print_divider("⑥ 检查中断状态的正确姿势")

    for t in ["refund:small", "refund:big", "refund:reject"]:
        snap = graph.get_state({"configurable": {"thread_id": t}})
        status = "挂起" if snap.next else "已完成"
        print(f"  {t:18s} {status}")

    print_divider("④ 生产注意")
    print("""
  ✅ 副作用放在 interrupt 之后
     interrupt 恢复时节点从头重跑，之前的代码会再执行一次

  ✅ 写操作必须幂等
     用业务幂等键，而不是 random uuid

  ✅ 检查是否已中断
     用 get_state().next，不要靠异常类型判断

  ✅ 超时要处理
     定时任务扫描挂起超过 N 小时的单子，自动驳回或升级

  ✅ 审批人要校验
     接口层检查 operator 是否有审批权限
""")


if __name__ == "__main__":
    main()
