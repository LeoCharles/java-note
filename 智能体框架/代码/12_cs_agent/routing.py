"""12 | 意图路由：规则先行，模型兜底。

对应文档：12-实战-智能客服工单Agent.md 第七章

为什么要分层？

  规则（关键词）→ 覆盖 60% 的明确场景，0 延迟、0 成本、结果确定
  模型（结构化输出）→ 处理剩下的模糊表达

反过来做（全靠模型）的代价：
  · 每次请求多一次模型调用（延迟 +200~800ms）
  · 「我要投诉」这种必须转人工的，模型有可能判成 normal
  · 模型升级/切换会改变路由结果，线上行为不稳定
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel, Field

# 出现这些词，不走模型，直接转人工。
# 这类是「就算模型觉得能答也不能答」的硬性红线。
FORCE_HUMAN = [
    "投诉", "差评", "举报", "曝光", "律师", "起诉",
    "骗子", "诈骗", "曝光你们", "叫你们领导", "找媒体",
]

# 投诉热线单独处理：这些**数字**和订单号长得一样。
# 「帮我查订单 12345」里的 12345 是订单号，不是投诉热线 ——
# 早期版本把它和关键词放在一个列表里，结果所有订单号 12345 的查询都被转人工了。
HOTLINE_RE = re.compile(
    r"(打|拨|投诉到|找)\s*(12315|12345|96315)"      # 打 12345
    r"|(12315|12345|96315)\s*(投诉|举报|热线)"        # 12345 投诉
)

# 用户明确要求转人工
EXPLICIT_HUMAN = [
    "转人工", "人工客服", "找客服", "真人", "叫人工", "转接人工",
]


class Route(BaseModel):
    intent: Literal["order", "after_sale", "product", "complaint", "other"] = Field(
        description=(
            "order=订单查询/物流/取消/改地址；"
            "after_sale=退款/换货/维修；"
            "product=产品功能/参数/使用方法；"
            "complaint=投诉/情绪激烈/要求赔偿；"
            "other=其他"
        )
    )
    keywords: list[str] = Field(default_factory=list,
                                description="提取的关键信息，如商品名、问题现象")
    order_no: str | None = Field(default=None,
                                 description="提到的订单号，若无可为 null")
    urgency: Literal["low", "normal", "high"] = Field(
        default="normal", description="用户情绪激烈或明确要求紧急时为 high"
    )


ROUTE_PROMPT = """判断用户意图并提取关键信息。

意图定义：
- order：查订单、查物流、取消订单、改收货地址
- after_sale：退款、退货、换货、维修、质量问题
- product：问产品参数、功能、使用方法
- complaint：投诉、要求赔偿、情绪激烈
- other：闲聊、无法归类

用户消息：{text}
"""


def force_human(text: str) -> bool:
    if HOTLINE_RE.search(text):
        return True
    return any(k in text for k in FORCE_HUMAN)


def explicit_human(text: str) -> bool:
    return any(k in text for k in EXPLICIT_HUMAN)


async def route_intent(text: str, model) -> Route:
    """模型路由。用 small_model —— 分类任务不需要大模型。"""
    return await model.with_structured_output(Route).ainvoke(
        ROUTE_PROMPT.format(text=text)
    )


# ============ 规则兜底：路由前的快速判断 ============

ORDER_WORDS = ("订单", "物流", "快递", "发货", "到哪了", "取消", "地址")
AFTER_SALE_WORDS = ("退款", "退货", "换货", "维修", "坏了", "质量问题", "少发", "漏发")
PRODUCT_WORDS = ("怎么用", "参数", "保修", "多少度", "能装多少", "支持", "说明书")


def rule_route(text: str) -> str | None:
    """能靠关键词确定的直接返回，确定不了返回 None 交给模型。

    这只是示例级别的规则。生产上应该配一份从真实会话里挖出来的词表，
    并且每周用误判样本回补。
    """
    if force_human(text) or explicit_human(text):
        return "complaint"

    scores = {
        "order": sum(1 for k in ORDER_WORDS if k in text),
        "after_sale": sum(1 for k in AFTER_SALE_WORDS if k in text),
        "product": sum(1 for k in PRODUCT_WORDS if k in text),
    }
    best = max(scores, key=scores.get)
    # 只有「明显领先」才直接裁决，否则交给模型（避免「退款后订单怎么查」被误判）
    if scores[best] >= 1 and sum(scores.values()) - scores[best] == 0:
        return best
    return None
