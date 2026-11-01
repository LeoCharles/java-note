"""03 | 工具定义：从 @tool 到 Pydantic 参数。

对应文档：03-工具调用与结构化输出.md「工具定义」

运行：
    python 03_tools/tools_basic.py
"""

import json
import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel, Field
from langchain_core.tools import tool

from common import get_model, print_divider


# ---------- 工具定义 ----------

@tool
def get_weather(city: str) -> str:
    """查询指定城市今天的天气。

    用户询问天气、气温、是否下雨、穿衣建议时使用。
    不适用于查询历史天气或未来预报。
    """
    # 真实项目里这里是 HTTP 调用
    data = {"北京": "晴，18~26℃", "上海": "多云，20~28℃", "杭州": "小雨，17~22℃"}
    return data.get(city, f"{city}：暂无数据")


class OrderQuery(BaseModel):
    order_no: str = Field(
        pattern=r"^\d{5,20}$",
        description="订单号，5-20 位数字",
    )
    include_items: bool = Field(
        default=True,
        description="是否返回商品明细，只需要状态时传 false 可节省时间",
    )


@tool("query_order", args_schema=OrderQuery)
def query_order(order_no: str, include_items: bool = True) -> dict:
    """查询订单的状态、金额、商品明细。

    用户询问订单进度、物流、金额、是否可退款时使用。
    """
    db = {
        "12345": {"status": "已发货", "amount": 299.0,
                  "items": [{"name": "电饭锅", "qty": 1}],
                  "tracking": "SF1234567890"},
    }
    if order_no not in db:
        return {"success": False, "error": f"订单 {order_no} 不存在",
                "hint": "请与用户核对订单号，不要尝试其他号码"}
    d = db[order_no]
    out = {"success": True, "order_no": order_no, "status": d["status"],
           "amount": d["amount"], "tracking": d.get("tracking")}
    if include_items:
        out["items"] = d["items"]
    return out


@tool
def search_kb(query: str, top_k: int = 3) -> list[dict]:
    """在公司知识库中检索文档片段。

    用户询问公司制度、流程、产品说明时使用。
    """
    docs = [
        {"title": "员工手册", "content": "年假：入职满 1 年 5 天，满 5 年 10 天。"},
        {"title": "报销制度", "content": "差旅报销需在 15 天内提交，附发票原件。"},
        {"title": "IT 手册", "content": "VPN 连接失败请检查客户端版本。"},
    ]
    return [d for d in docs if any(w in d["content"] for w in query)][:top_k] or docs[:top_k]


TOOLS = [get_weather, query_order, search_kb]
TOOL_MAP = {t.name: t for t in TOOLS}


def show_tool_schema() -> None:
    print_divider("① 工具到底长什么样")
    for t in TOOLS:
        print(f"  名称    : {t.name}")
        print(f"  描述    : {t.description[:60]}...")
        print(f"  参数    : {json.dumps(t.args_schema.model_json_schema(), ensure_ascii=False)[:200]}")
        print()


def demo_bind_tools() -> None:
    print_divider("② bind_tools：模型返回的是「调用意图」，不是结果")

    model = get_model()
    bound = model.bind_tools(TOOLS)
    resp = bound.invoke("北京今天天气怎么样？订单 12345 到哪了？")

    print("  模型回复类型:", type(resp).__name__)
    print("  文本内容    :", repr(resp.content))
    print("  工具调用    :")
    for tc in getattr(resp, "tool_calls", []):
        print(f"    - {tc['name']}({tc['args']})  id={tc['id']}")

    print("\n  👉 模型只说了「我要调什么」，真正的执行要你的代码来做")


def demo_tool_choice() -> None:
    print_divider("③ tool_choice：强制 / 禁止调用工具")

    model = get_model()
    bound = model.bind_tools(TOOLS, tool_choice="any")     # 必须调一个
    r = bound.invoke("你好")
    print("  tool_choice='any' ->", [tc["name"] for tc in r.tool_calls])

    try:
        bound = model.bind_tools(TOOLS, tool_choice="required")
        r = bound.invoke("你好")
        print("  tool_choice='required' ->", [tc["name"] for tc in r.tool_calls])
    except Exception as e:
        print(f"  tool_choice='required' 不被该模型支持：{type(e).__name__}")

    bound = model.bind_tools(TOOLS, tool_choice="none")
    r = bound.invoke("北京天气如何")
    print("  tool_choice='none' ->", r.content[:60])


def demo_execute_tool() -> None:
    print_divider("④ 执行工具：用 .invoke 或 .run")

    result = get_weather.invoke({"city": "杭州"})
    print("  get_weather 结果:", result)

    r2 = query_order.invoke({"order_no": "12345"})
    print("  query_order 结果:", json.dumps(r2, ensure_ascii=False))

    print("\n  --- 参数校验：不合法会抛异常 ---")
    try:
        query_order.invoke({"order_no": "abc"})
    except Exception as e:
        print(f"  {type(e).__name__}: {str(e)[:120]}")

    print("\n  👉 参数校验发生在「工具执行前」，不会浪费一次业务调用")


def demo_lexical_invoke() -> None:
    print_divider("⑤ 完整一轮：模型意图 → 执行 → 回填")

    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

    model = get_model().bind_tools(TOOLS)
    messages = [
        SystemMessage("你是助手。涉及订单必须先查询，不要编造。"),
        HumanMessage("我的订单 12345 到哪了？"),
    ]

    ai = model.invoke(messages)
    messages.append(ai)

    for tc in ai.tool_calls:
        result = TOOL_MAP[tc["name"]].invoke(tc["args"])
        messages.append(ToolMessage(
            content=json.dumps(result, ensure_ascii=False)
            if not isinstance(result, str) else result,
            tool_call_id=tc["id"],
        ))

    final = model.invoke(messages)
    print("  最终回答:", final.content)


def main() -> None:
    show_tool_schema()
    demo_bind_tools()
    demo_tool_choice()
    demo_execute_tool()
    demo_lexical_invoke()

    print_divider("小结")
    print("  · 工具的 docstring 就是给模型看的 API 文档，要写清楚「什么时候用」「什么时候不用」")
    print("  · 参数用 Pydantic + Field 约束，能拦住大部分无效调用")
    print("  · 模型返回 tool_calls（意图），代码负责执行并回填 ToolMessage")
    print("  · 下一步：04 之前先看 handwritten_loop.py，把循环写出来")


if __name__ == "__main__":
    main()
