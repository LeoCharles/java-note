"""12 | 出站质检：模型说完话之后，再检查一遍。

对应文档：12-实战-智能客服工单Agent.md 第十二章

模型在客服场景最容易犯的四种错：
  ① 超授权承诺：「我们赔您 500 元」
  ② 内部信息泄露：「系统显示您有 3 次投诉记录」「这是 A 级风险」
  ③ 责任判定：「这肯定是我们的责任」
  ④ 数字与事实不一致：订单 299 元，它说 199 元

出站质检 = 在把回答交给用户之前，做一次确定性的检查。
它不是「可选的体验优化」，是**合规和赔付风险的最后一关**。
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

# ============ ① 承诺类 ============

COMMITMENT_PATTERNS = [
    (r"(我们|公司)(会|将|可以)?(赔|赔偿|补偿|报销|承担)", "未经授权的赔偿承诺"),
    (r"(保证|承诺|一定)(能|会|可以)?(退款|赔偿|解决|处理|到账)", "过度承诺"),
    (r"(全额|双倍|三倍)(赔偿|退款)", "超权限赔偿"),
    (r"永久(免费|保修)", "超出政策的承诺"),
]

# ============ ② 内部信息 ============

INTERNAL_PATTERNS = [
    (r"(风险等级|风控|高信用|黑名单|A 级|B 级)", "暴露风控标签"),
    (r"(系统|后台)(显示|记录)(您|你).{0,30}(投诉|退款|黑名单|次数|记录)", "暴露内部记录"),
    (r"(内部|策略|规则)(规定|显示|要求|说明)", "暴露内部规则"),
    (r"(模型|AI|算法)(认为|判断|打分|识别)", "暴露 AI 机制"),
]

# ============ ③ 责任判定 ============

LIABILITY_PATTERNS = [
    (r"(肯定|一定|百分之百|绝对是?)(是)?(我们|我司|公司)的(责任|问题|错)", "擅自承认责任"),
    (r"(是|属于)(我们|我司)的(责任|过错)", "擅自承认责任"),
    (r"(违法|违规|欺诈|侵权|违约)", "法律定性"),
]

# ============ ④ 语气 ============

TONE_PATTERNS = [
    (r"(你|您)(自己|明明)(没|不)(说清楚|看明白|注意|核对)", "指责用户"),
    (r"(这|那)(都|也)不知道", "轻视用户"),
    (r"(随便|爱咋咋地|不关我事|爱莫能助)", "消极应对"),
]

# ============ ⑤ 未经证实的事实陈述 ============

FACT_PATTERNS = [
    (r"(已经|已)(成功)?为您(退|取消|提交|处理)", "声称已完成操作"),
    (r"(退款|款项)(已经|已)(到账|打入|退回)", "声称资金已到账"),
    (r"(保证|确保)(明天|今天|48|24)\s*(小时|天)?内(到账|送达)", "保证时效"),
]

ALL_PATTERNS = {
    "commitment": COMMITMENT_PATTERNS,
    "internal": INTERNAL_PATTERNS,
    "liability": LIABILITY_PATTERNS,
    "tone": TONE_PATTERNS,
    "fact": FACT_PATTERNS,
}

# 整句替换话术：命中就把它所在的那一句整体换掉。
# 为什么整句换而不是替换命中的几个字？
#   局部替换会留下语法残渣（「我们赔您 500 元」→「…，您 500 元」），
#   读起来是半句话，比什么都不说更糟。
REPLACEMENTS = {
    "commitment": "具体赔付方案需要人工审核后确认，我先为您提交申请。",
    "internal": "我这边能查到的是订单本身的信息。",
    "liability": "这个情况需要进一步核实，我会为您转接专员处理。",
    "tone": "非常抱歉给您带来不便，我帮您看看怎么处理。",
    "fact": "具体进度请以系统查询结果为准，我帮您查一下。",
}


class Violation(BaseModel):
    kind: Literal["commitment", "internal", "liability", "tone", "fact"]
    matched: str = Field(description="命中的原文")
    reason: str = Field(description="为什么是问题")


def check_text(text: str) -> list[Violation]:
    """确定性的正则检查。便宜、快、可解释，先用它。

    重叠命中会被折叠（「肯定是我们的责任」不会同时算两条），
    否则回执里同一个问题报两三遍，人工看日志会被干扰。
    """
    out: list[Violation] = []
    spans: list[tuple[int, int]] = []

    for kind, patterns in ALL_PATTERNS.items():
        for pat, reason in patterns:
            for m in re.finditer(pat, text):
                s, e = m.span()
                if any(s >= a and e <= b for a, b in spans):
                    continue
                spans.append((s, e))
                out.append(Violation(kind=kind, matched=m.group(0), reason=reason))
    return out


_SENT_SPLIT = re.compile(r"(?<=[。！？!?；;\n])")


def _split_sentences(text: str) -> list[str]:
    return [s for s in _SENT_SPLIT.split(text) if s]


def scrub(text: str) -> tuple[str, list[Violation]]:
    """出站清洗：命中违规的**整句**替换成安全话术。

    返回 (清洗后文本, 问题列表)。问题列表为空 = 原样放行。
    """
    violations = check_text(text)
    if not violations:
        return text, []

    out = []
    for sent in _split_sentences(text):
        kinds = {v.kind for v in check_text(sent)}
        if kinds:
            # 一句话里可能有多种问题，取最严重的那一类替换
            for k in ("liability", "commitment", "internal", "fact", "tone"):
                if k in kinds:
                    out.append(REPLACEMENTS[k])
                    break
        else:
            out.append(sent)

    cleaned = re.sub(r"\s{2,}", " ", "".join(out)).strip()
    if not cleaned:
        cleaned = "非常抱歉，我这边需要进一步核实，帮您转接专员处理。"
    return cleaned, violations


class JudgeResult(BaseModel):
    safe: bool = Field(description="是否可以发给用户")
    violations: list[str] = Field(default_factory=list,
                                  description="问题列表，没有则为空")
    rewritten: str | None = Field(default=None,
                                  description="不安全时给出的改写版本")


JUDGE_PROMPT = """你是客服质检员，检查 AI 客服的回答是否可以发给用户。

检查四类问题：
1. 未经授权的承诺（赔偿、补偿、保证解决）
2. 泄露内部信息（风控标签、用户历史记录、内部规则）
3. 擅自做责任判定或法律定性
4. 指责、轻视用户的语气

如果有问题，给出一版**保留原意但去掉风险**的改写。
如果没问题，safe=true，rewritten 留空。

用户问题：{question}
AI 回答：{answer}
"""


async def judge(text: str, question: str, model) -> JudgeResult:
    """第二道：正则没命中、但这一轮涉及写操作时再交给模型看一眼。"""
    return await model.with_structured_output(JudgeResult).ainvoke(
        JUDGE_PROMPT.format(question=question, answer=text)
    )


# ============ 数字一致性：最容易翻车、最难自动发现 ============

NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def check_numbers(answer: str, facts: list[str]) -> list[str]:
    """回答里出现的数字，必须在事实里出现过。

    「退款金额 299 元，预计 3 个工作日到账」——
    299 和 3 都应该能在这轮工具返回里找到。

    白名单：纯序号、明确的时间常量、礼貌用语。
    """
    whitelist = {"1", "2", "3", "5", "7", "10", "15", "24", "30", "48", "72",
                 "100", "200", "2000"}
    fact_text = " ".join(facts)
    problems = []
    for m in NUM_RE.finditer(answer):
        n = m.group(0)
        if n in whitelist:
            continue
        if n not in fact_text:
            problems.append(n)
    return problems
