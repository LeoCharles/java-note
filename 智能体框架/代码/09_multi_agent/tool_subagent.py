"""09 | 模式一：工具即子 Agent。

对应文档：09-多Agent协作模式.md「工具即子 Agent」

运行：
    python 09_multi_agent/tool_subagent.py

主 Agent 只看到 3 个"工具"，每个工具背后是一个完整的子 Agent。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.tools import tool

from common import get_model, print_divider
from shared import build_agents


def build_super_tools(agents: dict):
    """把子 Agent 包成工具。"""

    @tool
    def order_assistant(question: str) -> dict:
        """处理订单相关咨询：订单查询、物流跟踪、修改收货地址、取消订单。

        需要用户提供订单号。不处理退款、换货、产品咨询。"""
        r = agents["order_agent"].invoke(
            {"messages": [("user", question)]},
            config={"recursion_limit": 6},
        )
        return _pack(r, "订单")

    @tool
    def after_sale_assistant(question: str, order_no: str | None = None) -> dict:
        """处理售后相关咨询：退款、换货、维修。

        需要用户提供订单号，或从上下文已知。"""
        prompt = question if not order_no else f"订单号 {order_no}。{question}"
        r = agents["after_sale_agent"].invoke(
            {"messages": [("user", prompt)]},
            config={"recursion_limit": 8},
        )
        return _pack(r, "售后")

    @tool
    def product_assistant(question: str) -> dict:
        """处理产品咨询：功能、参数、使用方法、选购建议。"""
        r = agents["product_agent"].invoke(
            {"messages": [("user", question)]},
            config={"recursion_limit": 6},
        )
        return _pack(r, "产品")

    return [order_assistant, after_sale_assistant, product_assistant]


def _pack(result: dict, domain: str) -> dict:
    """只回传最终答案，避免子 Agent 的 ToolMessage 撑爆主上下文。"""
    last = result["messages"][-1]
    called = [
        tc["name"]
        for m in result["messages"] if getattr(m, "tool_calls", None)
        for tc in m.tool_calls
    ]
    return {
        "domain": domain,
        "answer": last.content,
        "tools_used": called,
    }


SUPER_PROMPT = """你是客服总入口。

规则：
1. 根据用户问题，选择最合适的助手工具。
2. 一次只调一个助手。
3. 助手的回答已经是最终答案，直接转述给用户，不要改写或补充。
4. 如果用户问题跨多个领域，先处理最重要的一个，再处理另一个。
5. 不要自己编造业务信息。
"""


def main() -> None:
    from langchain.agents import create_agent

    model = get_model()

    print_divider("① 构建子 Agent")
    sub_agents = build_agents()
    print("  已构建：", ", ".join(sub_agents))

    print_divider("② 包装成工具，构建主 Agent")
    super_tools = build_super_tools(sub_agents)
    router = create_agent(model, super_tools, SUPER_PROMPT, name="cs_router")

    print("  主 Agent 只看到这些工具：")
    for t in super_tools:
        print(f"    · {t.name}: {t.description.splitlines()[0]}")

    print_divider("③ 测试")

    cases = [
        "我的订单 12345 到哪了？",
        "订单 12345 我要退款，电饭锅有问题",
        "电饭锅容量多大？保修多久？",
        "我买了耳机，订单 67890，能退吗",
    ]

    for q in cases:
        print(f"\n  {'─' * 60}")
        print(f"  用户：{q}")
        r = router.invoke({"messages": [("user", q)]},
                          config={"recursion_limit": 8})

        print(f"\n  【主 Agent 轨迹】")
        for m in r["messages"]:
            if getattr(m, "tool_calls", None):
                for tc in m.tool_calls:
                    print(f"    [主→{tc['name']}] {tc['args']}")

        print(f"\n  回答：{r['messages'][-1].content}")

    print_divider("④ 与单 Agent 的对比")

    print("""
  ┌────────────────┬──────────────┬──────────────┐
  │                │ 单 Agent     │ 工具即子 Agent│
  ├────────────────┼──────────────┼──────────────┤
  │ 工具数量        │ 6 个全暴露    │ 3 个（每个是专家）│
  │ 提示词复杂度    │ 3 套规则混一起 │ 各管各的       │
  │ 权限隔离        │ 靠提示词      │ 物理隔离       │
  │ 延迟            │ 低            │ 多一层          │
  │ 独立开发测试    │ 难            │ 易              │
  └────────────────┴──────────────┴──────────────┘

  ✅ 优点：实现简单、上下文干净、权限天然隔离
  ⚠️ 缺点：子 Agent 拿不到完整上下文（要显式传）、看不到中间步骤
  💡 修复：传结构化 TaskBrief（见 with_contract.py 思路），返回结构化结果
""")


if __name__ == "__main__":
    main()
