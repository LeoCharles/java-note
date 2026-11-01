"""10 | 评测：行为断言 + LLM Judge。

对应文档：10-工程化与生产落地.md「评测」

运行：
    python 10_production/eval_demo.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel, Field
from langchain_core.tools import tool

from common import get_model, print_divider


# ============ 被测对象：一个简单的售后 Agent ============

ORDERS = {
    "12345": {"status": "已发货", "amount": 299.0, "can_refund": True},
    "11111": {"status": "待付款", "amount": 99.0, "can_refund": False},
}
REFUNDS: dict[str, dict] = {}


@tool
def get_order_detail(order_no: str) -> dict:
    """查询订单详情。"""
    o = ORDERS.get(order_no)
    if not o:
        return {"success": False, "error": "订单不存在"}
    return {"success": True, "order_no": order_no, **o}


@tool
def apply_refund(order_no: str, reason: str) -> dict:
    """申请退款。前置条件：can_refund=true 且用户明确要求。"""
    o = ORDERS.get(order_no)
    if not o or not o["can_refund"]:
        return {"success": False, "error": "不支持退款"}
    if order_no in REFUNDS:
        return {"success": True, "already_exists": True}
    REFUNDS[order_no] = {"refund_id": f"RF{len(REFUNDS) + 1}"}
    return {"success": True, "refund_id": REFUNDS[order_no]["refund_id"]}


SYSTEM = """你是售后助手。
规则：
1. 涉及订单必须调用 get_order_detail，不要编造。
2. 退款前必须确认 can_refund=true 且用户明确要求。
3. 用户未提供订单号时，先询问订单号，不要调用 apply_refund。
4. 回答不超过 80 字。
"""


def build_agent():
    from langchain.agents import create_agent

    return create_agent(get_model(), [get_order_detail, apply_refund], SYSTEM)


# ============ 评测用例 ============

CASES = [
    {
        "id": "order_001",
        "input": "订单 12345 到哪了",
        "must_call": ["get_order_detail"],
        "must_not_call": ["apply_refund"],
        "answer_contains": ["已发货"],
        "max_steps": 4,
    },
    {
        "id": "order_002",
        "input": "订单 11111 什么状态",
        "must_call": ["get_order_detail"],
        "must_not_call": ["apply_refund"],
        "answer_contains": ["待付款"],
        "max_steps": 4,
    },
    {
        "id": "refund_001",
        "input": "订单 12345 我要退款，商品有问题",
        "must_call": ["get_order_detail", "apply_refund"],
        "must_not_call": [],
        "answer_contains": ["退款"],
        "max_steps": 6,
    },
    {
        "id": "refund_002",
        "input": "订单 11111 我要退款",
        "must_call": ["get_order_detail"],
        "must_not_call": ["apply_refund"],
        "answer_contains": [],
        "max_steps": 4,
    },
    {
        "id": "no_order_no",
        "input": "我要退款",
        "must_call": [],
        "must_not_call": ["apply_refund"],
        "answer_contains": ["订单号"],
        "max_steps": 3,
    },
    {
        "id": "not_exist",
        "input": "订单 99999 到哪了",
        "must_call": ["get_order_detail"],
        "must_not_call": [],
        "answer_contains": [],
        "max_steps": 3,
    },
]


# ============ 检查逻辑 ============

def check(case: dict, result: dict) -> dict:
    msgs = result["messages"]
    called = [tc["name"] for m in msgs if getattr(m, "tool_calls", None)
              for tc in m.tool_calls]
    answer = msgs[-1].content or ""

    return {
        "id": case["id"],
        "input": case["input"],
        "must_call_ok": all(t in called for t in case["must_call"]),
        "must_not_call_ok": not any(t in called for t in case["must_not_call"]),
        "answer_ok": all(k in answer for k in case["answer_contains"]),
        "steps_ok": len(msgs) <= case["max_steps"] * 2,
        "called": called,
        "answer": answer,
    }


def passed(row: dict) -> bool:
    return row["must_call_ok"] and row["must_not_call_ok"] and row["answer_ok"]


# ============ LLM Judge ============

class JudgeResult(BaseModel):
    score: int = Field(ge=1, le=5, description="1=很差 5=很好")
    reason: str


JUDGE_PROMPT = """你是严格的评审。评价客服助手的回答。

【用户问题】{q}
【参考要点】{ref}
【助手回答】{a}

评分：
5 = 准确、完整、简洁
4 = 准确但稍冗长
3 = 部分正确或遗漏要点
2 = 有明显错误
1 = 完全无关或有害
"""


def judge(q: str, ref: str, a: str) -> JudgeResult:
    return get_model().with_structured_output(JudgeResult).invoke(
        JUDGE_PROMPT.format(q=q, ref=ref, a=a)
    )


async def run_eval() -> None:
    agent = build_agent()

    print_divider("① 行为断言（可全自动）")

    rows = []
    for case in CASES:
        REFUNDS.clear()
        r = await agent.ainvoke(
            {"messages": [("user", case["input"])]},
            config={"configurable": {"thread_id": f"eval:{case['id']}"},
                    "recursion_limit": 8},
        )
        row = check(case, r)
        rows.append(row)

        mark = "✅" if passed(row) else "❌"
        print(f"\n  {mark} [{row['id']}] {row['input']}")
        print(f"     调用：{row['called']}")
        print(f"     must_call    : {row['must_call_ok']}")
        print(f"     must_not_call: {row['must_not_call_ok']}")
        print(f"     answer       : {row['answer_ok']}")
        print(f"     回答：{row['answer'][:100]}")

    ok = sum(1 for r in rows if passed(r))
    print(f"\n  通过率：{ok}/{len(rows)} = {ok / len(rows):.1%}")

    print_divider("② LLM as Judge（主观质量）")

    REFERENCE = {
        "order_001": "订单已发货，并提供物流信息",
        "refund_001": "确认可退款后提交申请，告知预计到账时间",
        "no_order_no": "询问用户订单号，不要直接退款",
    }

    for row in rows[:3]:
        ref = REFERENCE.get(row["id"])
        if not ref:
            continue
        j = judge(row["input"], ref, row["answer"])
        print(f"  [{row['id']}] 评分 {j.score}/5")
        print(f"     理由：{j.reason[:120]}")

    print_divider("③ 汇总报告")

    report = {
        "total": len(rows),
        "passed": ok,
        "rate": ok / len(rows),
        "failures": [r for r in rows if not passed(r)],
    }
    print(json.dumps({k: v for k, v in report.items() if k != "failures"},
                     ensure_ascii=False, indent=2))

    if report["failures"]:
        print("\n  失败用例：")
        for f in report["failures"]:
            print(f"    · [{f['id']}] {f['input']}")
            print(f"      调用 {f['called']}，回答 {f['answer'][:60]}")

    print_divider("④ 接进 CI")
    print("""
  # .github/workflows/eval.yml
  - name: Agent eval
    run: python 10_production/eval_demo.py

  - name: Check baseline
    run: |
      python -c "
      import json, glob
      latest = sorted(glob.glob('eval/reports/*.json'))[-1]
      rows = json.load(open(latest))
      rate = sum(1 for r in rows if r['must_call_ok'] and r['answer_ok']) / len(rows)
      assert rate >= 0.80, f'通过率 {rate:.1%} 低于基线'
      "

  👉 Agent 的评测不要断言「输出文本完全一致」（模型不确定）
     要断言「行为」：调了什么工具、说了什么关键信息、有没有越权
""")


def main() -> None:
    asyncio.run(run_eval())

    print_divider("小结")
    print("  · 三层评测：单元（工具/单次调用）、组件（检索/分类）、端到端（Agent）")
    print("  · must_call / must_not_call 是 Agent 评测最有价值的断言")
    print("  · LLM Judge 要有参考答案，并用人工标注校准 20 条")
    print("  · 每次线上出 bug，第一件事是把它变成评测用例")


if __name__ == "__main__":
    main()
