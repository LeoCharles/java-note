"""02 | LCEL：用管道符把组件串起来。

对应文档：02-LangChain快速上手.md「LCEL」

运行：
    python 02_langchain/lcel_chain.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import get_model, print_divider
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


def main() -> None:
    model = get_model()

    print_divider("① 最基础的链：prompt | model | parser")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个简洁的技术讲解员，回答不超过 50 字。"),
        ("human", "解释一下 {concept}"),
    ])
    chain = prompt | model | StrOutputParser()

    for c in ["索引", "事务", "缓存雪崩"]:
        print(f"  {c}: {chain.invoke({'concept': c}).strip()}")

    print_divider("② 管道能接任何 Runnable")

    # 自定义函数也能接（用 RunnableLambda 包装）
    from langchain_core.runnables import RunnableLambda

    def count_chars(text: str) -> dict:
        return {"text": text, "length": len(text)}

    chain2 = prompt | model | StrOutputParser() | RunnableLambda(count_chars)
    print(" ", chain2.invoke({"concept": "HTTP 2.0"}))

    print_divider("③ RunnableParallel：一次输入，多路输出")

    from langchain_core.runnables import RunnableParallel

    fan_out = RunnableParallel(
        explain=prompt | model | StrOutputParser(),
        one_line=(
            ChatPromptTemplate.from_messages([("human", "用 10 个字概括 {concept}")])
            | model
            | StrOutputParser()
        ),
        keywords=(
            ChatPromptTemplate.from_messages([
                ("human", "列出 {concept} 的 3 个关键词，逗号分隔，不要其他内容")
            ])
            | model
            | StrOutputParser()
        ),
    )

    result = fan_out.invoke({"concept": "幂等性"})
    print("  explain :", result["explain"].strip())
    print("  one_line:", result["one_line"].strip())
    print("  keywords:", result["keywords"].strip())

    print("\n  👉 三路并发执行，总耗时 ≈ 最慢那一路，而不是三者之和")

    print_divider("④ RunnablePassthrough：透传 + 扩展")

    from langchain_core.runnables import RunnablePassthrough

    chain4 = (
        RunnablePassthrough.assign(
            question=lambda x: x["raw"].strip()
        )
        | RunnablePassthrough.assign(
            answer=(
                ChatPromptTemplate.from_messages([("human", "{question}")])
                | model
                | StrOutputParser()
            )
        )
    )

    out = chain4.invoke({"raw": "  什么是 CAP 理论？  "})
    print("  输入:", repr(out["raw"]))
    print("  清洗:", repr(out["question"]))
    print("  回答:", out["answer"].strip()[:80])

    print_divider("⑤ 带 config 调用：打标签、方便追踪")

    r = chain.invoke(
        {"concept": "分区容错性"},
        config={
            "run_name": "explain_concept",
            "tags": ["demo", "lcel"],
            "metadata": {"user_id": "u1", "scene": "learning"},
        },
    )
    print(" ", r.strip())

    print("\n  👉 配上 LANGSMITH_TRACING=true，这些标签会显示在追踪里")

    print_divider("⑥ 批量执行")

    outs = chain.batch(
        [{"concept": c} for c in ["B+ 树", "LSM 树", "跳表"]],
        config={"max_concurrency": 3},
    )
    for o in outs:
        print(" ", o.strip())

    print_divider("小结")
    print("  · LCEL 的核心：所有组件都是 Runnable，都能用 | 组合")
    print("  · RunnableParallel 做并发聚合，RunnablePassthrough.assign 做增量构造")
    print("  · 生产中 LCEL 适合确定性流程；需要分支/循环/中断时用 LangGraph")


if __name__ == "__main__":
    main()
