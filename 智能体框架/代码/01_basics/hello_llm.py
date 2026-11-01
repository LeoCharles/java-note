"""01 | 最小的一次大模型调用。

对应文档：01-大模型应用开发基础.md「把大模型当成一个奇怪的远端服务」

运行：
    python 01_basics/hello_llm.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import get_model, print_divider


def main() -> None:
    model = get_model()

    print_divider("① 最简单的一次调用")
    resp = model.invoke("用一句话解释什么是 HTTP。")
    print(resp.content)

    print_divider("② 返回对象里有什么")
    print("类型      :", type(resp).__name__)
    print("内容      :", resp.content[:50], "...")
    print("元信息    :", getattr(resp, "response_metadata", {}))
    print("token 用量:", getattr(resp, "usage_metadata", None))

    print_divider("③ 多轮对话：必须自己把历史带上")
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage("你是一个简洁的技术助手，回答不超过 30 字。"),
        HumanMessage("Java 的 HashMap 线程安全吗？"),
    ]
    r1 = model.invoke(messages)
    print("第 1 轮:", r1.content)

    # 关键：要把上一轮的 AI 回复也加进去，模型才知道上下文
    messages.append(r1)
    messages.append(HumanMessage("那用什么替代？"))
    r2 = model.invoke(messages)
    print("第 2 轮:", r2.content)

    print_divider("④ 温度参数的影响（跑 3 次看差异）")
    creative = get_model(temperature=1.0)
    for i in range(3):
        r = creative.invoke("给一家咖啡店起个名字，只输出名字。")
        print(f"  temperature=1.0 第 {i + 1} 次: {r.content.strip()}")

    deterministic = get_model(temperature=0.0)
    for i in range(3):
        r = deterministic.invoke("给一家咖啡店起个名字，只输出名字。")
        print(f"  temperature=0.0 第 {i + 1} 次: {r.content.strip()}")


if __name__ == "__main__":
    main()
