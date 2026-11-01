"""05 | 会话管理：裁剪、摘要、长期记忆。

对应文档：05-记忆与会话管理.md

运行：
    python 05_memory/session_manager.py
"""

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import (
    AIMessage, BaseMessage, HumanMessage, SystemMessage, trim_messages,
)

from common import get_model, get_small_model, print_divider


# ============ 会话存储（生产上换 Redis / Postgres） ============

@dataclass
class Session:
    thread_id: str
    user_id: str
    messages: list[BaseMessage] = field(default_factory=list)
    summary: str = ""
    updated_at: str = ""

    def save(self, store: "SessionStore") -> None:
        self.updated_at = datetime.now().isoformat(timespec="seconds")
        store.data[self.thread_id] = self


class SessionStore:
    def __init__(self):
        self.data: dict[str, Session] = {}

    def load(self, thread_id: str, user_id: str) -> Session:
        return self.data.get(thread_id) or Session(thread_id=thread_id, user_id=user_id)

    def delete(self, thread_id: str) -> None:
        self.data.pop(thread_id, None)


# ============ 裁剪策略 ============

def trim_keep_last_n(messages: list[BaseMessage], n: int = 6) -> list[BaseMessage]:
    """保留最近 n 条。最简单，但会丢失早期关键信息。"""
    return messages[-n:]


def trim_by_tokens(messages: list[BaseMessage], max_tokens: int = 2000) -> list[BaseMessage]:
    """按 token 从后往前保留，且保证以 human 开头。"""
    return trim_messages(
        messages,
        max_tokens=max_tokens,
        strategy="last",
        token_counter=len,          # 简易：用字符数代替 token，避免依赖 tiktoken
        start_on="human",
        include_system=False,        # system 由我们自己拼
    )


SUMMARY_PROMPT = """把以下对话压缩成一段不超过 150 字的中文摘要。

要求：
1. 保留：用户身份信息、已确认的事实、未解决的问题、用户的偏好或要求。
2. 去掉：寒暄、重复内容、模棱两可的表述。
3. 用第三人称陈述，不要写"用户说""AI 回答"。

对话：
{conversation}

摘要："""


def summarize(messages: list[BaseMessage], model) -> str:
    conv = "\n".join(
        f"{'用户' if m.type == 'human' else '助手'}: {m.content}"
        for m in messages if m.type in ("human", "ai") and m.content
    )
    return model.invoke(SUMMARY_PROMPT.format(conversation=conv)).content.strip()


# ============ 长期记忆 ============

@dataclass
class UserProfile:
    user_id: str
    name: str = ""
    dept: str = ""
    preferences: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)


PROFILE_PROMPT = """从对话中更新用户画像。只提取明确陈述的事实，不要推测。

已有画像：
{profile}

新对话：
{conversation}

输出 JSON：{{"name": "", "dept": "", "preferences": [], "facts": []}}
没有新信息时字段保持原值。
"""


def update_profile(profile: UserProfile, messages: list[BaseMessage], model) -> UserProfile:
    """从对话里抽取用户画像。生产上应该用结构化输出 + 在后台异步跑。"""
    conv = "\n".join(
        f"{'用户' if m.type == 'human' else '助手'}: {m.content}"
        for m in messages[-6:] if m.type in ("human", "ai") and m.content
    )

    raw = model.invoke(PROFILE_PROMPT.format(
        profile=json.dumps(profile.__dict__, ensure_ascii=False),
        conversation=conv,
    )).content

    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return profile
    try:
        data = json.loads(m.group())
    except json.JSONDecodeError:
        return profile

    profile.name = data.get("name") or profile.name
    profile.dept = data.get("dept") or profile.dept
    profile.preferences = list(dict.fromkeys(
        profile.preferences + (data.get("preferences") or [])
    ))
    profile.facts = list(dict.fromkeys(
        profile.facts + (data.get("facts") or [])
    ))[:10]
    return profile


def build_system_prompt(base: str, profile: UserProfile) -> str:
    if not (profile.name or profile.facts or profile.preferences):
        return base
    extra = [f"【用户画像】"]
    if profile.name:
        extra.append(f"姓名：{profile.name}")
    if profile.dept:
        extra.append(f"部门：{profile.dept}")
    if profile.preferences:
        extra.append(f"偏好：{'；'.join(profile.preferences)}")
    if profile.facts:
        extra.append(f"已知信息：{'；'.join(profile.facts)}")
    return base + "\n\n" + "\n".join(extra)


# ============ 完整会话管理器 ============

class SessionManager:
    def __init__(self, model, small_model, store: SessionStore,
                 max_tokens: int = 1500, keep_turns: int = 6):
        self.model = model
        self.small = small_model
        self.store = store
        self.max_tokens = max_tokens
        self.keep_turns = keep_turns
        self.profiles: dict[str, UserProfile] = {}

    def _profile(self, user_id: str) -> UserProfile:
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile(user_id=user_id)
        return self.profiles[user_id]

    def _build_messages(self, session: Session, base_system: str) -> list[BaseMessage]:
        profile = self._profile(session.user_id)
        system = build_system_prompt(base_system, profile)

        parts: list[BaseMessage] = [SystemMessage(system)]
        if session.summary:
            parts.append(SystemMessage(f"【此前对话摘要】\n{session.summary}"))

        history = trim_by_tokens(session.messages, self.max_tokens)
        parts.extend(history)
        return parts

    def _maybe_compress(self, session: Session) -> None:
        if len(session.messages) <= self.keep_turns:
            return

        to_compress = session.messages[:-self.keep_turns]
        if not to_compress:
            return

        new_summary = summarize(to_compress, self.small)
        session.summary = (
            f"{session.summary}\n{new_summary}".strip()
            if session.summary else new_summary
        )
        session.messages = session.messages[-self.keep_turns:]
        print(f"    [压缩] {len(to_compress)} 条 → 摘要 {len(new_summary)} 字")

    def chat(self, thread_id: str, user_id: str, text: str,
             base_system: str = "你是公司知识库助手，回答简洁、准确。") -> str:
        session = self.store.load(thread_id, user_id)
        session.messages.append(HumanMessage(text))

        messages = self._build_messages(session, base_system)
        resp = self.model.invoke(messages)

        session.messages.append(AIMessage(resp.content))
        self._maybe_compress(session)
        session.save(self.store)

        # 异步更新画像（生产上放后台任务）
        self._profile(user_id)

        return resp.content


def main() -> None:
    model = get_model()
    small = get_small_model()

    print_divider("① 不裁剪会发生什么")
    msgs = []
    for i in range(12):
        msgs.append(HumanMessage(f"第 {i} 轮用户消息，" * 20))
        msgs.append(AIMessage(f"第 {i} 轮助手回复，" * 20))
    print(f"  原始 {len(msgs)} 条，总字数 {sum(len(m.content) for m in msgs)}")

    trimmed_n = trim_keep_last_n(msgs, 6)
    print(f"  keep_last_n(6) → {len(trimmed_n)} 条，{sum(len(m.content) for m in trimmed_n)} 字")

    trimmed_t = trim_by_tokens(msgs, 1000)
    print(f"  trim_by_tokens(1000) → {len(trimmed_t)} 条，{sum(len(m.content) for m in trimmed_t)} 字")
    print(f"  是否以 human 开头：{trimmed_t[0].type == 'human'}")

    print_divider("② 摘要压缩演示")
    fake_conv = [
        HumanMessage("你好，我是研发部的张三，想看下年假政策"),
        AIMessage("张三你好，入职满 1 年有 5 天，满 5 年 10 天。"),
        HumanMessage("我 2020 年入职的，那应该 10 天了？"),
        AIMessage("是的，满 5 年 10 天。"),
        HumanMessage("那能跨年结转到明年吗？"),
        AIMessage("可以，但不超过 5 天，需在次年 3 月 31 日前用完。"),
        HumanMessage("好的，那我还有个问题，出差住宿标准是多少？"),
    ]
    s = summarize(fake_conv, small)
    print(f"  原文 {sum(len(m.content) for m in fake_conv)} 字 → 摘要 {len(s)} 字")
    print(f"\n  摘要内容：\n    {s}")

    print("\n  👉 检查摘要是否保留了：张三、研发部、入职年份、年假天数、结转规则")

    print_divider("③ 长期记忆：用户画像")

    profile = UserProfile(user_id="u1001")
    convo = [
        HumanMessage("我叫张三，在研发部工作"),
        AIMessage("好的张三，记住了。"),
        HumanMessage("我比较喜欢简洁的回答，别太长"),
        AIMessage("明白，我会尽量简洁。"),
        HumanMessage("我 2020 年 3 月入职的"),
        AIMessage("了解。"),
    ]
    profile = update_profile(profile, convo, small)

    print(f"  画像：{json.dumps(profile.__dict__, ensure_ascii=False, indent=4)}")

    print("\n  --- 拼进系统提示 ---")
    prompt = build_system_prompt("你是公司助手。", profile)
    print(f"    {prompt}")

    print("\n  👉 下次用户只问「我还有几天年假」时，模型已知道他是 2020 年入职的")

    print_divider("④ 会话管理器：多轮 + 自动压缩")

    mgr = SessionManager(model, small, SessionStore(),
                         max_tokens=800, keep_turns=4)
    tid = "u1001:conv-demo"

    script = [
        "你好，我是研发部的张三，2020 年 3 月入职",
        "我年假有几天？",
        "能结转到明年吗？",
        "出差住酒店能报多少？",
        "出差后多久要报销？",
        "刚才说的年假结转规则能再说一遍吗？",
        "我是哪个部门的来着？",
    ]

    for i, q in enumerate(script, 1):
        print(f"\n  [第 {i} 轮] 用户：{q}")
        a = mgr.chat(tid, "u1001", q)
        print(f"           助手：{a[:150]}")

        sess = mgr.store.data[tid]
        print(f"           （会话：{len(sess.messages)} 条消息，"
              f"摘要 {len(sess.summary)} 字）")

    print_divider("小结")
    print("  · 短期记忆有 5 种策略：keep_last_n / trim_tokens / trim_keep_pinned / 摘要 / 检索")
    print("  · 摘要压缩能大幅降 token，但要注意别把关键信息摘要掉")
    print("  · 长期记忆（用户画像）跨会话保留，用异步任务更新")
    print("  · 生产上用 LangGraph 的 checkpointer + Store，见第 08 篇")


if __name__ == "__main__":
    main()
