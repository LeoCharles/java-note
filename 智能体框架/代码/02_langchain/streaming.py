"""02 | 流式输出：终端与 SSE 两种形态。

对应文档：02-LangChain快速上手.md「流式」

运行：
    python 02_langchain/streaming.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import get_model, print_divider


async def demo_astream() -> None:
    model = get_model()
    print("  正在生成… ", end="", flush=True)
    async for chunk in model.astream("用 3 句话说明什么是 Prompt 注入。"):
        if chunk.content:
            print(chunk.content, end="", flush=True)
    print("\n")


async def demo_sse_format() -> None:
    """模拟 FastAPI 的 SSE 输出格式：前端按 data: {...}\\n\\n 解析。"""
    model = get_model()

    def sse(obj: dict) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    print("  【SSE 数据流】")
    async for chunk in model.astream("用两句话说明什么是 RAG。"):
        if chunk.content:
            print("  " + sse({"type": "token", "text": chunk.content}).strip())
    print("  " + sse({"type": "done"}).strip())

    print("\n  👉 前端用 EventSource 或 fetch + ReadableStream 解析")


async def demo_batch_vs_serial() -> None:
    import time

    model = get_model()
    qs = [f"用一句话说明第 {i} 号设计模式" for i in range(1, 6)]

    t0 = time.time()
    for q in qs:
        await model.ainvoke(q)
    serial = time.time() - t0

    t0 = time.time()
    await model.abatch(qs)
    batch = time.time() - t0

    print(f"  串行 5 次: {serial:.2f}s")
    print(f"  并发 5 次: {batch:.2f}s")
    print(f"  加速: {serial / batch:.1f}x")


async def main() -> None:
    print_divider("① 异步流式（终端打字机效果）")
    await demo_astream()

    print_divider("② SSE 格式（给前端用）")
    await demo_sse_format()

    print_divider("③ 并发 batch 的加速效果")
    await demo_batch_vs_serial()

    print_divider("小结")
    print("  · stream/astream：首字延迟从 2s 降到 0.3s，感知提升巨大")
    print("  · batch/abatch：独立请求并发，吞吐提升")
    print("  · 生产上：流式给用户看，batch 做批处理")


if __name__ == "__main__":
    asyncio.run(main())
