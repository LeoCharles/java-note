"""10 | 结构化日志 + 全链路追踪 ID。

对应文档：10-工程化与生产落地.md「可观测性」

运行：
    python 10_production/logging_demo.py
"""

import json
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import get_model, print_divider

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")
LOG_BUFFER: list[dict] = []


def log_event(event: str, **fields) -> None:
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "trace_id": trace_id_var.get(),
        "event": event,
        **fields,
    }
    LOG_BUFFER.append(record)
    print("  " + json.dumps(record, ensure_ascii=False))


@contextmanager
def traced(name: str, **attrs):
    """计时 + 异常捕获的上下文管理器。"""
    t0 = time.time()
    log_event(f"{name}.start", **attrs)
    try:
        yield
        log_event(f"{name}.end", latency_ms=int((time.time() - t0) * 1000))
    except Exception as e:
        log_event(f"{name}.error", error=type(e).__name__, message=str(e)[:100],
                  latency_ms=int((time.time() - t0) * 1000))
        raise


def mask(text: str) -> str:
    """日志脱敏：不记录完整用户输入。"""
    if len(text) <= 8:
        return text[0] + "*" * (len(text) - 1) if text else ""
    return f"{text[:4]}***{text[-2:]}({len(text)}字)"


def demo_structured_log() -> None:
    print_divider("① 一次完整请求的日志序列")

    tid = uuid.uuid4().hex[:12]
    trace_id_var.set(tid)

    user_input = "帮我查一下订单 12345 到哪了，我要退款"
    log_event("request.start", user_id="u1001", thread_id="t1:u1:web:abc",
              input_len=len(user_input))

    model = get_model()

    with traced("llm_call", model="gpt-4o-mini", purpose="intent"):
        r = model.invoke(f"判断意图，只输出 订单/售后/产品/其他 之一：{user_input}")

    log_event("intent", result=r.content.strip(), input_preview=mask(user_input))

    with traced("tool_call", tool="get_order_detail", args={"order_no": "12345"}):
        time.sleep(0.05)
        result = {"success": True, "status": "已发货", "amount": 299.0}

    log_event("tool_result", tool="get_order_detail", success=result["success"],
              status=result.get("status"))

    log_event("request.end", status="success", total_ms=1234,
              input_tokens=850, output_tokens=120)

    print("\n  👉 用 trace_id 能把这一串串起来，也能连到 LangSmith 的追踪")


def demo_mask() -> None:
    print_divider("② 日志脱敏")

    samples = [
        "13800138000",
        "北京市朝阳区建国路 88 号 SOHO 现代城 A 座 1801",
        "我的身份证是 110101199001011234",
        "订单 12345 退款",
    ]
    for s in samples:
        print(f"  原文：{s}")
        print(f"  脱敏：{mask(s)}\n")

    print("  👉 生产上不要记录完整 prompt 和用户原文")
    print("     记长度、哈希、或脱敏版本")


def demo_cost_tracking() -> None:
    print_divider("③ 成本记录（按租户）")

    PRICE = {"gpt-4o-mini": (0.15, 0.60), "gpt-4o": (2.50, 10.00)}

    records = [
        {"tenant": "t1", "model": "gpt-4o-mini", "in": 1850, "out": 120},
        {"tenant": "t1", "model": "gpt-4o-mini", "in": 2100, "out": 150},
        {"tenant": "t2", "model": "gpt-4o", "in": 2400, "out": 400},
        {"tenant": "t2", "model": "gpt-4o", "in": 1800, "out": 350},
    ]

    total = {}
    for r in records:
        pin, pout = PRICE[r["model"]]
        cost = r["in"] / 1e6 * pin + r["out"] / 1e6 * pout
        total[r["tenant"]] = total.get(r["tenant"], 0) + cost
        log_event("llm_usage", tenant=r["tenant"], model=r["model"],
                  input_tokens=r["in"], output_tokens=r["out"],
                  cost_usd=round(cost, 6))

    print()
    for tenant, c in total.items():
        print(f"  {tenant}: ${c:.6f}")

    print("\n  👉 多租户系统必须能「分租户算清成本」，否则无法定价")


def demo_metrics() -> None:
    print_divider("④ 应该暴露哪些指标")

    metrics = {
        "agent_requests_total": "按 status 分：success/error/interrupted",
        "agent_request_duration_seconds": "P50/P95/P99",
        "agent_steps_per_request": "每请求超步数分布（找异常长尾）",
        "agent_tokens_total": "按 model/type 分",
        "agent_tool_calls_total": "按 tool/status 分",
        "agent_tool_duration_seconds": "按 tool 分",
        "agent_cost_yuan_total": "按 tenant/model 分",
        "agent_interrupt_pending": "挂起中的审批数",
    }
    for k, v in metrics.items():
        print(f"  {k:36s} {v}")

    print("\n  【告警规则】")
    alerts = [
        ("错误率", "> 5% 持续 5 分钟", "模型或工具异常"),
        ("P95 延迟", "> 15s", "性能劣化"),
        ("平均超步数", "突增 50%", "工具或提示词有问题"),
        ("单请求 token", "> 20000", "上下文失控"),
        ("挂起审批数", "> 100 且持续增长", "没人处理"),
        ("工具失败率", "> 10%", "下游系统问题"),
    ]
    for name, cond, meaning in alerts:
        print(f"  {name:14s} {cond:24s} {meaning}")

    print("\n  👉 「拒答率突增」是知识库系统最有价值的告警")
    print("     「平均超步数突增」是 Agent 系统最有价值的告警")


def demo_trace_walkthrough() -> None:
    print_divider("⑤ 一次真实的排障流程")
    print("""
  ① 用户投诉「机器人答非所问」
        ↓
  ② 用 trace_id 找到这条请求
        ↓
  ③ 看追踪：模型调了什么工具？拿到什么结果？
        ↓
  ④ 发现 get_order 返回 {"error": "timeout"}
     但模型把它当成了「订单不存在」
        ↓
  ⑤ 根因：工具的错误信息误导了模型
        ↓
  ⑥ 修复：区分 timeout 和 not_found，返回不同提示 + hint

  这条链路能走通的前提：追踪里记录了工具的原始返回值。
""")


def main() -> None:
    demo_structured_log()
    demo_mask()
    demo_cost_tracking()
    demo_metrics()
    demo_trace_walkthrough()

    print_divider("小结")
    print("  · 结构化 JSON 日志，字段固定，方便检索和聚合")
    print("  · trace_id 贯穿全链路，是排障的第一把钥匙")
    print("  · 别记完整 prompt 和用户原文，脱敏或只记哈希")
    print("  · 从第一天就配成本看板，否则第一次账单会吓人")
    print(f"\n  本次产生日志 {len(LOG_BUFFER)} 条（仅内存，生产应输出到文件/ELK）")


if __name__ == "__main__":
    main()
