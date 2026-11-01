"""12 | 客服工单 Agent 的演示脚本。

对应文档：12-实战-智能客服工单Agent.md

运行：
    python 12_cs_agent/demo.py                 # 跑完整场景
    python 12_cs_agent/demo.py --guard         # 只看质检规则
    python 12_cs_agent/demo.py --state-machine # 只看工单状态机
    python 12_cs_agent/demo.py --audit         # 只看审计日志

每个场景跑完都打印「发生了什么」，方便对照文档。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

import domain
import guard
from common import print_divider
from graph import build, build_config


# ============ 输出辅助 ============

def show_result(out: dict, graph=None, cfg=None) -> None:
    msgs = out.get("messages") or []
    if msgs:
        print(f"\n  【回复】{msgs[-1].content}")

    if out.get("ticket_no"):
        print(f"  【工单】{out['ticket_no']}")
    if out.get("resolved"):
        print("  【状态】AI 闭环解决")
    if out.get("need_human"):
        print("  【状态】已转人工")

    if graph and cfg:
        snap = graph.get_state(cfg)
        if snap.next:
            print(f"  【挂起】等待节点 {snap.next}")
            for task in snap.tasks:
                for itr in getattr(task, "interrupts", []):
                    print(f"  【审批载荷】{itr.value}")


async def run_turn(graph, text: str, thread: str, user: str = "u1001",
                   show: bool = True) -> dict:
    cfg = build_config(thread, user)
    print(f"\n  👤 {text}")
    out = graph.invoke({"messages": [("user", text)]}, cfg)
    if show:
        show_result(out, graph, cfg)
    return out


# ============ 场景 ============

def scene_guard() -> None:
    print_divider("① 出站质检：模型说错话会怎样")

    samples = [
        "您的订单已经发货了，3 天内送达。",
        "这个问题是我们的责任，我们赔您 500 元。",
        "系统显示您近 30 天申请了 3 次退款，属于高风险用户。",
        "这肯定是我们的责任，您可以去告我们。",
        "这一点您自己没说清楚，我也没办法。",
        "退款已经到账了，请注意查收。",
    ]

    for s in samples:
        clean, vs = guard.scrub(s)
        flag = "✅ 通过" if not vs else f"⚠️ 命中 {len(vs)} 处"
        print(f"\n  {flag}")
        print(f"    原文：{s}")
        if vs:
            for v in vs:
                print(f"    → [{v.kind}] {v.reason}：「{v.matched}」")
            print(f"    清洗后：{clean}")

    print_divider("② 数字一致性检查")
    answer = "您的退款金额为 299 元，退款单号 RF1001，预计 3 个工作日到账。"
    facts = ['{"refund_id": "RF1001", "amount": 299.0}']
    bad = guard.check_numbers(answer, facts)
    print(f"  回答：{answer}")
    print(f"  事实：{facts}")
    print(f"  对不上的数字：{bad or '无'}")

    answer2 = "您的退款金额为 199 元，退款单号 RF1001，预计 3 个工作日到账。"
    print(f"\n  回答：{answer2}")
    bad2 = guard.check_numbers(answer2, facts)
    print(f"  对不上的数字：{bad2 or '无'}")
    print("\n  👉 199 没在事实里出现 —— 这是典型的「模型改数字」，必须拦住")


def scene_state_machine() -> None:
    print_divider("③ 工单状态机：非法流转会被拒绝")

    t = domain.create_ticket("thread:sm", "u1001", "after_sale", "12345",
                             "normal", {"problem": "演示"})
    print(f"  新建工单 {t['ticket_no']}  状态={t['status']}")

    ok = [("pending_approval", "申请审批"), ("approved", "审批通过"),
          ("executing", "执行中"), ("resolved", "已解决"), ("closed", "关闭")]
    for to, label in ok:
        domain.transition(t["ticket_no"], to, actor="ai:agent", action=label)
        print(f"  ✅ {label}: → {to}")

    try:
        domain.transition(t["ticket_no"], "ai_handling", actor="ai:agent")
        print("  ❌ 居然通过了？状态机有问题")
    except domain.InvalidTransition as e:
        print(f"  ⛔ 拒绝：{e}")

    print("\n  事件流水：")
    for ev in domain.EVENTS[-6:]:
        print(f"    {ev['from_status'] or '—':16s} → {ev['to_status']:16s}"
              f" actor={ev['actor']:14s} {ev['action']}")
    print("\n  👉 actor 字段能回答「这次操作是模型做的还是人做的」")


def scene_audit() -> None:
    print_divider("· 审计日志：每一次写操作都留痕（独立视图，--audit）")
    if not domain.AUDIT_LOG:
        print("  还没有写操作。先跑一遍 demo 再来看。")
        return
    for a in domain.dump_audit(10):
        print(f"  {a['at']}  {a['actor']:14s} {a['action']:16s} "
              f"user={a['user_id']}  args={a['args']}")
    print("\n  👉 出事时按 trace_id / ticket_no / user_id 都能把链路串起来")


async def scene_normal() -> None:
    print_divider("④ 只读场景：查物流")

    graph = build(InMemorySaver())
    out = await run_turn(graph, "帮我查下订单 12345 到哪了", "t:order:1")
    facts = out.get("facts") or []
    print(f"\n  [事实台账] {len(facts)} 条工具返回")


async def scene_small_refund() -> None:
    print_divider("⑤ 小额退款：规则初审自动通过")

    graph = build(InMemorySaver())
    cfg = build_config("t:refund:small", "u1001")

    print("  👤 订单 12345 我要退款，质量问题")
    out = graph.invoke({"messages": [("user", "订单 12345 我要退款，质量问题")]}, cfg)
    show_result(out, graph, cfg)

    refund = domain.refund_of("12345")
    if refund:
        print(f"\n  【服务端退款单】{refund['refund_id']}  "
              f"金额={refund['amount']}（服务端算的，模型没传金额参数）")
    print("\n  👉 金额 299 > 200，但没有 >2000，所以走规则初审：")
    print("     质量问题 + 金额 ≤2000 → 自动通过，不打扰人工")


async def scene_big_refund() -> None:
    print_divider("⑥ 大额退款：必须人工审批（>2000 元 → interrupt）")

    graph = build(InMemorySaver())
    cfg = build_config("t:refund:big", "u1001")

    print("  👤 订单 22222 我要退款，质量问题")
    out = graph.invoke({"messages": [("user", "订单 22222 我要退款，质量问题")]}, cfg)
    show_result(out, graph, cfg)

    snap = graph.get_state(cfg)
    if not snap.next:
        print("  （没有挂起，检查规则阈值）")
        return

    print("\n  ⏸  图挂起了。此时进程可以退出、可以等到明天。")
    print("     状态在 checkpoint 里，不占资源。\n")

    print("  👮 审批人：同意退款")
    out = graph.invoke(Command(resume={"approved": True,
                                       "operator": "admin-001",
                                       "comment": "客户老客户，同意"}), cfg)
    show_result(out, graph, cfg)

    refund = domain.refund_of("22222")
    if refund:
        print(f"\n  【服务端退款单】{refund['refund_id']}  金额={refund['amount']}")

    print("\n  👉 幂等验证：再 resume 一次（模拟网络重试）")
    before = len(domain.REFUNDS)
    try:
        graph.invoke(Command(resume={"approved": True}), cfg)
    except Exception as e:
        print(f"     重复 resume：{type(e).__name__}（正常，已完成）")
    print(f"     退款单数量：{before} → {len(domain.REFUNDS)}（应不变）")


async def scene_reject() -> None:
    print_divider("⑦ 审批驳回")

    graph = build(InMemorySaver())
    cfg = build_config("t:refund:reject", "u1001")
    graph.invoke({"messages": [("user", "订单 22222 退款，七天无理由")]}, cfg)

    snap = graph.get_state(cfg)
    if not snap.next:
        print("  （未触发审批，可能订单状态不满足）")
        return

    out = graph.invoke(Command(resume={"approved": False,
                                       "comment": "已超过七天无理由期限"}), cfg)
    show_result(out, graph, cfg)


async def scene_escalate() -> None:
    print_divider("⑧ 转人工：投诉关键词 → 强制人工")

    graph = build(InMemorySaver())
    out = await run_turn(graph, "你们这什么破服务，我要投诉！", "t:escalate:1")

    tno = out.get("ticket_no")
    if tno and tno in domain.TICKETS:
        t = domain.TICKETS[tno]
        print(f"\n  【工单】{tno}  status={t['status']}  priority={t['priority']}")
        s = t.get("ai_summary") or {}
        print("  【交接摘要】")
        for k in ("problem", "attempted", "key_facts", "blocker",
                  "suggested_action", "sentiment"):
            print(f"    {k:18s} {s.get(k)}")

    print("\n  【人工工作台待办】")
    for row in domain.list_escalated():
        print(f"    {row['ticket_no']}  {row['priority']:8s} "
              f"{row['category']:10s} {row['created_at']}")


async def scene_permission() -> None:
    print_divider("⑨ 越权：查别人的订单")

    graph = build(InMemorySaver())
    # 55555 属于 u2002，但当前用户是 u1001
    await run_turn(graph, "帮我查订单 55555", "t:perm:1", user="u1001")

    print("\n  👉 服务端返回 403，但给用户的话术是「查不到」")
    print("     不确认「这个订单存在但不属于你」——否则等于泄露了订单存在性")


async def scene_multi_turn() -> None:
    print_divider("⑩ 多轮：先问再答（订单号后补）")

    graph = build(InMemorySaver())
    cfg = build_config("t:multi:1", "u1001")

    print("  👤 我买的东西到哪了？")
    out = graph.invoke({"messages": [("user", "我买的东西到哪了？")]}, cfg)
    show_result(out, graph, cfg)

    print("\n  👤 订单 12345")
    out = graph.invoke({"messages": [("user", "订单 12345")]}, cfg)
    show_result(out, graph, cfg)

    print("\n  👉 同一个 thread_id，历史自动带上，不用手工拼")


async def main() -> None:
    args = sys.argv[1:]

    if "--guard" in args:
        scene_guard()
        return
    if "--state-machine" in args:
        scene_state_machine()
        return
    if "--audit" in args:
        scene_audit()
        return

    print("=" * 64)
    print("  12 | 客服工单 Agent -- 模拟业务系统 + LangGraph 主图")
    print("=" * 64)
    print("""
  说明：这里用内存数据模拟订单/工单服务。
        工具层对 403/404/409/422 的处理，换成真 API 时一行都不用改。

  金额三档：
    ≤200         自动执行
    200~2000     规则初审
    >2000        人工审批（interrupt）
""")

    scene_guard()

    domain.reset()
    await scene_normal()

    domain.reset()
    await scene_small_refund()

    domain.reset()
    await scene_big_refund()

    domain.reset()
    await scene_reject()

    domain.reset()
    await scene_escalate()

    domain.reset()
    await scene_permission()

    domain.reset()
    await scene_multi_turn()

    print_divider("⑪ 审计与事件流水")
    for a in domain.dump_audit(6):
        print(f"  {a['at']}  {a['actor']:14s} {a['action']:16s} "
              f"order={a['args'].get('order_no', '-')}")
    print()
    for ev in domain.EVENTS[-8:]:
        print(f"  {ev['ticket_no']}  {ev['from_status'] or '—':16s} → "
              f"{ev['to_status']:16s} actor={ev['actor']}")

    print_divider("小结")
    print("""
  ✅ 身份从 config 取，不从工具参数取 —— 模型改不了
  ✅ 金额服务端算，工具没有 amount 参数
  ✅ 写操作带幂等键，重置/重试不重复执行
  ✅ interrupt 之前只做只读，副作用放在后面
  ✅ 子 Agent 输出决策结构，主图跳转类型安全
  ✅ 出站质检 + 数字核对，拦住「说错话」
  ✅ 转人工带结构化交接摘要，人工不用从头看记录

  下一步：
    启动 HTTP 服务：python 12_cs_agent/app.py
    浏览器打开 http://localhost:8000/docs
""")


if __name__ == "__main__":
    asyncio.run(main())
