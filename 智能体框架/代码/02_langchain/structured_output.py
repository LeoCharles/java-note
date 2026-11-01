"""02 | 结构化输出：三种方式对比。

对应文档：02-LangChain快速上手.md「结构化输出」

运行：
    python 02_langchain/structured_output.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel, Field
from typing import Literal

from common import get_model, print_divider


# ---------- Schema ----------

class Contact(BaseModel):
    """从一个名片或消息里提取联系信息。"""

    name: str = Field(description="姓名")
    phone: str | None = Field(default=None, description="手机号，没有则为 null")
    city: str | None = Field(default=None, description="城市")
    intent: Literal["咨询", "投诉", "退款", "其他"] = Field(description="用户意图")


class OrderItem(BaseModel):
    name: str
    qty: int = Field(ge=1)


class OrderInfo(BaseModel):
    order_no: str = Field(pattern=r"^\d{5,20}$")
    amount: float = Field(gt=0)
    items: list[OrderItem]
    can_refund: bool


COLLOQUIAL = "我叫张伟，电话 13800138000，人在上海，你们那个电饭锅坏了要退钱。"


def main() -> None:
    model = get_model()

    print_divider("① with_structured_output（推荐）")

    extractor = model.with_structured_output(Contact)
    result = extractor.invoke(f"提取联系信息：{COLLOQUIAL}")
    print("  类型:", type(result).__name__)
    print("  字段:", result.model_dump())
    print("  访问:", f"{result.name} / {result.intent}")

    print_divider("② include_raw=True：同时拿到解析结果和原始响应")

    extractor_raw = model.with_structured_output(Contact, include_raw=True)
    out = extractor_raw.invoke(f"提取联系信息：{COLLOQUIAL}")
    print("  parsed   :", out["parsed"].model_dump() if out["parsed"] else None)
    print("  parsing_error:", out.get("parsing_error"))
    print("  raw 类型  :", type(out["raw"]).__name__)

    print("\n  👉 生产上一定要用 include_raw，解析失败时可以重试或降级")

    print_divider("③ JsonOutputParser（更底层，可自定义修复）")

    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    parser = JsonOutputParser(pydantic_object=OrderInfo)
    chain = (
        ChatPromptTemplate.from_messages([
            ("system", "从用户描述中提取订单信息。\n{format}"),
            ("human", "{text}"),
        ])
        .partial(format=parser.get_format_instructions())
        | model
        | parser
    )

    order = chain.invoke({
        "text": "订单号 12345678，花了 299.5 元，买了电饭锅 1 个、饭勺 2 个，能退吗"
    })
    print("  解析结果:", json.dumps(order, ensure_ascii=False, indent=2))

    print_divider("④ 手工解析（最容易出错，仅作对比）")

    raw = model.invoke(
        "提取：订单号 12345678，299.5 元，电饭锅。输出 JSON。"
    )
    print("  模型原文:")
    print(f"    {raw.content!r}")

    def naive_parse(text: str) -> dict:
        # 常见坑：```json 包装、前后有解释文字
        t = text.strip()
        if "```" in t:
            t = t.split("```")[1]
            if t.startswith("json"):
                t = t[4:]
        return json.loads(t.strip())

    try:
        print("  手工解析:", naive_parse(raw.content))
    except Exception as e:
        print(f"  手工解析失败：{type(e).__name__}: {e}")
        print("  👉 这就是为什么要用 with_structured_output")

    print_divider("⑤ 嵌套结构与约束校验")

    nested = model.with_structured_output(OrderInfo).invoke(
        "订单 A12345678 金额 88.8，一只笔 qty 3，可退款"
    )
    print("  嵌套解析:", nested.model_dump())
    print("  👉 pattern / gt / ge 约束由 Pydantic 校验，失败可 catch 后重试")

    print_divider("小结")
    print("  · 首选 with_structured_output + Pydantic")
    print("  · 生产加 include_raw，解析失败可重试")
    print("  · 字段少、格式固定时，JsonOutputParser 更可控")


if __name__ == "__main__":
    main()
