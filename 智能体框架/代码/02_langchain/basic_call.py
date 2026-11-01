"""02 | LangChain 最小调用：三条路都通。

对应文档：02-LangChain快速上手.md「三种调用方式」

运行：
    python 02_langchain/basic_call.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import get_model, print_divider, settings


def main() -> None:
    print_divider("① 显式构造 ChatOpenAI")
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=settings.model,
        temperature=0,
        api_key=settings.api_key,
        base_url=settings.base_url,
    )
    print(llm.invoke("一句话解释什么是依赖注入").content)

    print_divider("② init_chat_model（推荐，可换厂商）")
    model = get_model()
    print(model.invoke("一句话解释什么是依赖注入").content)

    print_divider("③ 消息类型与元组简写")

    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    # 完整写法
    full = [
        SystemMessage("你是简洁的助手。"),
        HumanMessage("1+1 等于几？"),
        AIMessage("2"),
        HumanMessage("再加 3 呢？"),
    ]
    print("完整写法:", model.invoke(full).content)
    print("元组简写:", model.invoke([("system", "你是简洁的助手。"), ("human", "3+3 等于几？")]).content)

    print_divider("④ invoke / batch / stream")

    qs = ["用一句话说明 Redis", "用一句话说明 Kafka", "用一句话说明 Nginx"]

    print("--- batch（并发，更快）---")
    for r in model.batch(qs):
        print(" ", r.content.strip())

    print("\n--- stream（首字更快）---")
    for chunk in model.stream("用三句话介绍什么是向量数据库。"):
        print(chunk.content, end="", flush=True)
    print()

    print_divider("⑤ 响应对象结构")

    resp = model.invoke("返回 OK")
    print("  type           :", type(resp).__name__)
    print("  content        :", repr(resp.content))
    print("  usage_metadata :", getattr(resp, "usage_metadata", None))
    print("  id             :", getattr(resp, "id", None))

    print("\n  👉 content 在部分模型上是「内容块列表」而不是字符串：")
    print("     if isinstance(resp.content, list): 拼接 text 字段")


if __name__ == "__main__":
    main()
