"""06 | 中间件：日志、限额、审批、循环检测。

对应文档：06-第一个Agent与ReAct循环.md「中间件」

运行：
    python 06_agent/with_middleware.py

说明：
    LangChain 1.x 的中间件 API 在不同小版本间有差异。
    本文件的做法是「优先用官方中间件，没有就手写等价逻辑」，
    保证任何版本都能跑。
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, ToolMessage

from common import get_model, print_divider
from first_agent import SYSTEM, TOOLS


def run_with_hooks(model, tools, question: str, *, max_model_calls: int = 6,
                   max_tool_calls: int = 8, require_approval: set[str] | None = None,
                   approved: set[str] | None = None, verbose: bool = True):
    """手写一个带中间件逻辑的循环 —— 理解中间件在做什么。

    真实的中间件只是把这些钩子标准化了，逻辑是一样的。
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    bound = model.bind_tools(tools)
    tool_map = {t.name: t for t in tools}
    require_approval = require_approval or set()
    approved = approved or set()

    messages = [SystemMessage(SYSTEM), HumanMessage(question)]

    stats = {"model_calls": 0, "tool_calls": 0, "tokens": 0,
             "recent_sigs": [], "blocked": []}
    t_start = time.time()

    for step in range(1, 20):
        # ── before_model 钩子 ──
        stats["model_calls"] += 1
        if stats["model_calls"] > max_model_calls:
            if verbose:
                print(f"  [限额] 模型调用超过 {max_model_calls} 次，终止")
            return "这个请求比较复杂，已为您转接人工客服。", messages, stats

        t0 = time.time()
        ai: AIMessage = bound.invoke(messages)
        latency = time.time() - t0

        usage = getattr(ai, "usage_metadata", None) or {}
        stats["tokens"] += usage.get("total_tokens", 0)

        if verbose:
            print(f"  [模型] 第 {stats['model_calls']} 次，{latency:.2f}s，"
                  f"tokens={usage.get('total_tokens', '?')}")
        messages.append(ai)

        # ── after_model 钩子：无 tool_calls 即结束 ──
        if not ai.tool_calls:
            return ai.content, messages, stats

        # ── after_model 钩子：循环检测 ──
        sig = tuple((tc["name"], json.dumps(tc["args"], sort_keys=True, ensure_ascii=False))
                    for tc in ai.tool_calls)
        if sig in stats["recent_sigs"][-1:]:
            if verbose:
                print("  [循环检测] 与上一轮完全相同，终止")
            messages.append(AIMessage("检测到重复操作，已停止。请补充更多信息或转人工。"))
            return messages[-1].content, messages, stats
        stats["recent_sigs"].append(sig)

        # ── wrap_tool_call 钩子 ──
        for tc in ai.tool_calls:
            stats["tool_calls"] += 1
            if stats["tool_calls"] > max_tool_calls:
                if verbose:
                    print(f"  [限额] 工具调用超过 {max_tool_calls} 次")
                return "工具调用次数超限，已转人工。", messages, stats

            name, args = tc["name"], tc["args"]

            # 审批拦截
            if name in require_approval and name not in approved:
                if verbose:
                    print(f"  [审批] {name} 需要人工确认 → 拒绝")
                stats["blocked"].append(name)
                content = json.dumps({
                    "success": False,
                    "error": f"操作「{name}」需要人工确认后才能执行",
                    "hint": "请向用户说明需要确认，不要重复尝试。",
                }, ensure_ascii=False)
            else:
                if verbose:
                    print(f"  [工具] {name}({json.dumps(args, ensure_ascii=False)})")
                fn = tool_map.get(name)
                try:
                    out = fn.invoke(args) if fn else {"error": f"未知工具 {name}"}
                    content = json.dumps(out, ensure_ascii=False) if not isinstance(out, str) else out
                except Exception as e:
                    content = json.dumps({"success": False,
                                          "error": f"{type(e).__name__}: {e}"},
                                         ensure_ascii=False)

            if verbose:
                print(f"         ← {content[:100]}{'…' if len(content) > 100 else ''}")

            messages.append(ToolMessage(content=content, tool_call_id=tc["id"]))

    return "达到最大步数", messages, stats


def demo_official_middleware(model) -> None:
    print_divider("① 官方中间件（如果版本支持）")

    try:
        from langchain.agents import create_agent
        from langchain.agents.middleware import (
            ModelCallLimitMiddleware, ToolCallLimitMiddleware,
        )

        agent = create_agent(
            model=model,
            tools=TOOLS,
            system_prompt=SYSTEM,
            middleware=[
                ModelCallLimitMiddleware(max_model_calls=6),
                ToolCallLimitMiddleware(max_tool_calls=8),
            ],
        )
        r = agent.invoke({"messages": [("user", "订单 12345 到哪了")]},
                         config={"recursion_limit": 10})
        print(f"  ✅ 官方中间件可用")
        print(f"  回答：{r['messages'][-1].content[:100]}")

    except ImportError as e:
        print(f"  ⚠️ 当前版本没有内置中间件（{e}）")
        print("  → 用手写钩子，逻辑完全一样（见下面几个 demo）")

    except Exception as e:
        print(f"  ⚠️ 官方中间件调用失败：{type(e).__name__}: {e}")
        print("  → 用手写钩子")


def demo_logging_and_limit(model) -> None:
    print_divider("② 日志 + 限额（手写钩子）")

    answer, msgs, stats = run_with_hooks(
        model, TOOLS, "订单 12345 有问题，我要退款", max_model_calls=6, max_tool_calls=8
    )
    print(f"\n  最终回答：{answer}")
    print(f"  统计：模型调用 {stats['model_calls']} 次，"
          f"工具调用 {stats['tool_calls']} 次，"
          f"tokens {stats['tokens']}")


def demo_approval(model) -> None:
    print_divider("③ 工具审批（软审批）")

    print("  --- 未审批 ---")
    answer, msgs, stats = run_with_hooks(
        model, TOOLS, "订单 12345 退款",
        require_approval={"apply_refund"}, approved=set(),
    )
    print(f"\n  回答：{answer}")
    print(f"  被拦截：{stats['blocked']}")

    print("\n  --- 已审批 ---")
    answer, msgs, stats = run_with_hooks(
        model, TOOLS, "订单 12345 退款",
        require_approval={"apply_refund"}, approved={"apply_refund"},
    )
    print(f"\n  回答：{answer}")
    print(f"  被拦截：{stats['blocked']}")

    print("\n  👉 这是「软审批」：返回拒绝消息，模型转述给用户")
    print("     真正的「硬审批」（挂起等人工）用 LangGraph 的 interrupt，见第 08 篇")


def demo_loop_detection(model) -> None:
    print_divider("④ 循环检测")

    from langchain_core.tools import tool

    @tool
    def stuck_search(keyword: str) -> dict:
        """搜索订单（这个例子永远返回找不到，用来演示死循环）。"""
        return {"success": True, "total": 0,
                "hint": "未找到订单。"}   # 故意不给引导，看会不会循环

    answer, msgs, stats = run_with_hooks(
        model, [stuck_search],
        "帮我找一下那个买电饭锅的订单，不记得订单号了",
        max_model_calls=6,
    )
    print(f"\n  回答：{answer}")
    print(f"  模型调用次数：{stats['model_calls']}（触发限额或循环检测即停）")


def demo_budget(model) -> None:
    print_divider("⑤ Token 预算闸门")

    MAX_TOKENS = 3000
    from langchain_core.messages import HumanMessage, SystemMessage

    bound = model.bind_tools(TOOLS)
    tool_map = {t.name: t for t in TOOLS}
    messages = [SystemMessage(SYSTEM), HumanMessage("帮我查下所有订单再逐一说下状态")]
    used = 0

    for _ in range(8):
        ai = bound.invoke(messages)
        u = (getattr(ai, "usage_metadata", None) or {}).get("total_tokens", 0)
        used += u
        print(f"  本次 {u} token，累计 {used}/{MAX_TOKENS}")

        if used > MAX_TOKENS:
            print(f"  [预算] 超出 {MAX_TOKENS}，降级：直接返回固定话术")
            break

        messages.append(ai)
        if not ai.tool_calls:
            print(f"  回答：{ai.content[:80]}")
            break

        for tc in ai.tool_calls:
            out = tool_map[tc["name"]].invoke(tc["args"])
            messages.append(ToolMessage(
                content=json.dumps(out, ensure_ascii=False), tool_call_id=tc["id"]
            ))


def main() -> None:
    model = get_model()

    demo_official_middleware(model)
    demo_logging_and_limit(model)
    demo_approval(model)
    demo_loop_detection(model)
    demo_budget(model)

    print_divider("中间件要解决的问题一览")
    print("""
  ┌──────────────────┬──────────────────────────────────┐
  │ 需求             │ 钩子                             │
  ├──────────────────┼──────────────────────────────────┤
  │ 日志、埋点、计时  │ before_model / after_model       │
  │ 注入用户上下文    │ before_model                     │
  │ 上下文压缩        │ before_model（改 messages）      │
  │ 限额、预算        │ before_model / wrap_model_call   │
  │ 工具审批          │ wrap_tool_call                   │
  │ 工具重试          │ wrap_tool_call                   │
  │ 循环检测          │ after_model                      │
  │ 最终输出过滤      │ after_model / 图末尾节点         │
  └──────────────────┴──────────────────────────────────┘

  ⚠️ 顺序会改变行为：脱敏要在入模前，限额要在真调用前。
""")

    print_divider("小结")
    print("  · 中间件 = Agent 的 AOP，把横切逻辑从主流程里拿出来")
    print("  · 手写钩子理解原理，然后用官方中间件落地")
    print("  · 生产必备：限额、审批、日志、循环检测")


if __name__ == "__main__":
    main()
