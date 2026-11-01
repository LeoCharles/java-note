"""10 | 可靠性：重试、降级、熔断、兜底。

对应文档：10-工程化与生产落地.md「可靠性与降级」

运行：
    python 10_production/fallback_demo.py
"""

import asyncio
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import get_model, print_divider


# ============ ① 重试 ============

async def retry(fn, attempts: int = 3, base: float = 0.2, label: str = ""):
    last = None
    for i in range(attempts):
        try:
            return await fn()
        except Exception as e:
            last = e
            if i == attempts - 1:
                raise
            wait = base * (2 ** i)
            print(f"    [{label}] 第 {i + 1} 次失败（{type(e).__name__}），"
                  f"{wait:.1f}s 后重试")
            await asyncio.sleep(wait)
    raise last


async def demo_retry() -> None:
    print_divider("① 指数退避重试")

    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("模拟网络抖动")
        return f"第 {calls['n']} 次成功"

    r = await retry(flaky, attempts=4, label="flaky")
    print(f"  结果：{r}")

    print("\n  ⚠️ 只重试幂等操作。退款/下单重试必须带幂等键。")


# ============ ② 模型降级链 ============

MODEL_CHAIN = ["primary-model", "backup-model", "tiny-model"]


async def call_model_with_fallback(messages: str, simulate: dict[str, str]) -> str:
    for name in MODEL_CHAIN:
        if name in simulate:
            print(f"    [{name}] 失败：{simulate[name]}")
            continue
        print(f"    [{name}] 成功")
        try:
            m = get_model()
            r = await asyncio.to_thread(m.invoke, messages)
            return f"[{name}] {r.content[:80]}"
        except Exception as e:
            print(f"    [{name}] 真实调用失败：{type(e).__name__}")
            continue
    raise RuntimeError("所有模型都不可用")


async def demo_model_fallback() -> None:
    print_divider("② 模型降级链")

    print("  --- 主模型正常 ---")
    r = await call_model_with_fallback("用一句话说明什么是幂等", {})
    print(f"  结果：{r}")

    print("\n  --- 模拟主模型 429（限流）---")
    r = await call_model_with_fallback(
        "用一句话说明什么是幂等",
        {"primary-model": "429 Too Many Requests"},
    )
    print(f"  结果：{r}")

    print("\n  --- 模拟全部不可用 ---")
    try:
        await call_model_with_fallback(
            "x", {"primary-model": "down", "backup-model": "down",
                  "tiny-model": "down"},
        )
    except RuntimeError as e:
        print(f"  最终失败：{e}")
        print(f"  兜底话术：「系统繁忙，请稍后再试。」")


# ============ ③ 熔断器 ============

class CircuitBreaker:
    def __init__(self, name: str, threshold: int = 3, cooldown: float = 2.0):
        self.name = name
        self.threshold = threshold
        self.cooldown = cooldown
        self.fails = 0
        self.opened_at = 0.0
        self.state = "closed"

    def allow(self) -> bool:
        if self.fails < self.threshold:
            return True
        if time.time() - self.opened_at > self.cooldown:
            self.state = "half_open"
            self.fails = 0
            return True
        self.state = "open"
        return False

    def record(self, ok: bool) -> None:
        if ok:
            self.fails = 0
            self.state = "closed"
        else:
            self.fails += 1
            if self.fails >= self.threshold:
                self.opened_at = time.time()
                self.state = "open"


async def demo_circuit_breaker() -> None:
    print_divider("③ 熔断器")

    cb = CircuitBreaker("order_service", threshold=3, cooldown=1.0)
    results = []

    for i in range(8):
        if not cb.allow():
            results.append(f"{i}: 熔断中，直接降级")
            continue

        ok = i % 3 != 2      # 第 3、6 次失败
        cb.record(ok)
        results.append(f"{i}: {'成功' if ok else '失败'} (fails={cb.fails}, "
                       f"state={cb.state})")

    for r in results:
        print(f"  {r}")

    print(f"\n  等 {cb.cooldown}s 后进入半开…")
    await asyncio.sleep(cb.cooldown)
    print(f"  允许请求：{cb.allow()}  state={cb.state}")

    print("\n  👉 熔断的意义：下游挂了就别再打它，直接走降级")


# ============ ④ 功能降级 ============

async def retrieve_with_fallback(query: str, mode: str = "normal") -> tuple[list, str]:
    if mode == "normal":
        return [{"doc": "正常检索结果"}], "normal"

    if mode == "vector_down":
        # 向量库挂了 → 关键词兜底
        return [{"doc": "关键词检索结果"}], "keyword_fallback"

    return [], "unavailable"


async def demo_degradation() -> None:
    print_divider("④ 功能降级")

    for mode in ("normal", "vector_down", "all_down"):
        docs, used = await retrieve_with_fallback("年假怎么算", mode)
        print(f"  {mode:14s} -> 检索到 {len(docs)} 条，模式={used}")

        if not docs:
            print("    回答：抱歉，知识库暂时不可用，我先根据通用知识回答，"
                  "具体信息建议咨询人工客服。")

    print("\n  👉 降级 ≠ 假装没事。要告诉用户「这次可能不完整」。")


# ============ ⑤ 兜底话术 ============

FALLBACKS = {
    "timeout": "这个问题有点复杂，我先帮您转接人工客服，请稍等。",
    "model_down": "系统繁忙，请稍后再试。",
    "quota": "今日咨询量较大，请明日再来或联系人工客服。",
    "tool_error": "查询服务暂时不可用，建议稍后重试。",
    "loop": "抱歉，我没能很好地理解您的需求，已为您转接人工。",
}


def demo_fallback_messages() -> None:
    print_divider("⑤ 兜底话术")

    for k, v in FALLBACKS.items():
        print(f"  {k:12s} → {v}")

    print("\n  👉 兜底话术要：承认问题、给下一步、不甩锅")


# ============ ⑥ 超时 ============

async def demo_timeout() -> None:
    print_divider("⑥ 超时控制")

    async def slow_task():
        await asyncio.sleep(2)
        return "完成"

    for t in (0.5, 3.0):
        try:
            r = await asyncio.wait_for(slow_task(), timeout=t)
            print(f"  timeout={t}s -> {r}")
        except asyncio.TimeoutError:
            print(f"  timeout={t}s -> 超时，返回兜底话术")

    print("\n  👉 超时分级：查询 5-8s，写操作 15s，整个请求 60s")


# ============ ⑦ 一次完整的容错组合 ============

async def robust_call(user_input: str) -> str:
    """把上面所有手段组合起来。"""
    cb = CircuitBreaker("llm", threshold=2, cooldown=5)

    if not cb.allow():
        return FALLBACKS["model_down"]

    try:
        model = get_model()
        r = await asyncio.wait_for(
            asyncio.to_thread(model.invoke, user_input),
            timeout=30,
        )
        cb.record(True)
        return r.content
    except asyncio.TimeoutError:
        cb.record(False)
        return FALLBACKS["timeout"]
    except Exception as e:
        cb.record(False)
        print(f"    [robust_call] 失败：{type(e).__name__}")
        return FALLBACKS["model_down"]


async def demo_robust() -> None:
    print_divider("⑦ 组合起来")

    r = await robust_call("用一句话说明什么是缓存雪崩")
    print(f"  结果：{r[:100]}")

    print("\n  👉 生产上的 Agent 调用应该是这样一层层包起来的：")
    print("     超时 → 重试 → 降级链 → 熔断 → 兜底话术")


async def main() -> None:
    await demo_retry()
    await demo_model_fallback()
    await demo_circuit_breaker()
    await demo_degradation()
    demo_fallback_messages()
    await demo_timeout()
    await demo_robust()

    print_divider("小结")
    print("  · 重试：只重试幂等操作，指数退避")
    print("  · 降级链：主模型 → 备用 → 小模型 → 固定话术")
    print("  · 熔断：下游挂了就别打了，直接降级")
    print("  · 功能降级：检索挂了走关键词，模型挂了走规则")
    print("  · 降级要显式告知用户，不要假装正常")


if __name__ == "__main__":
    asyncio.run(main())
