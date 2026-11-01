"""01 | Token 与成本：一次 Agent 请求到底花多少。

对应文档：01-大模型应用开发基础.md「Token 与成本」

运行：
    python 01_basics/token_cost.py

说明：
    不依赖网络也能跑（用 tiktoken 本地计数）。
    只有最后一步调模型，需要 API Key。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import get_model, print_divider, settings

# 粗略价格（美元 / 百万 token），仅用于演示，请以官网为准
PRICE = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "deepseek-chat": (0.27, 1.10),
}


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        # 没有 tiktoken 时的经验估算
        cjk = sum(1 for c in text if "一" <= c <= "鿿")
        other = len(text) - cjk
        return cjk + other // 4


def cost_of(in_tokens: int, out_tokens: int, model: str) -> float:
    pin, pout = PRICE.get(model, (1.0, 3.0))
    return in_tokens / 1_000_000 * pin + out_tokens / 1_000_000 * pout


def main() -> None:
    print_divider("① 中英文的 token 差异")

    samples = [
        ("中文", "人工智能正在改变软件开发的每一个环节。"),
        ("英文", "Artificial intelligence is changing every part of software development."),
        ("代码", "public static void main(String[] args) { System.out.println(\"hi\"); }"),
        ("数字", "订单号 123456789012，金额 1299.00 元"),
    ]
    for label, text in samples:
        n = count_tokens(text)
        ratio = len(text) / n if n else 0
        print(f"  {label:4s}  字符 {len(text):3d}  token {n:3d}  每 token {ratio:.2f} 字符")

    print("\n  👉 中文大约 1 字符 ≈ 1 token，英文约 4 字符 ≈ 1 token")
    print("     所以同样的内容，中文的成本通常是英文的 2–3 倍。")

    print_divider("② 一次 Agent 请求的 token 构成")

    system_prompt = (
        "你是 XX 商城的客服助手。"
        "规则：1) 涉及订单必须先查询；2) 不要编造金额；3) 回答不超过 150 字。"
    ) * 5  # 模拟一个 1000 字左右的系统提示

    tool_definitions = """
    get_order_detail: 查询订单详情，参数 order_no (string, 订单号)
    search_orders: 搜索订单列表，参数 keyword (string)
    apply_refund: 申请退款，参数 order_no (string), reason (string)
    """ * 8  # 模拟 10 个工具的定义

    history = "用户：我的订单到哪了\n助手：请提供订单号\n用户：12345" * 3
    user_input = "帮我看看订单 12345 现在什么状态"

    parts = {
        "系统提示": system_prompt,
        "工具定义": tool_definitions,
        "历史消息": history,
        "用户输入": user_input,
    }

    total_in = 0
    for name, text in parts.items():
        n = count_tokens(text)
        total_in += n
        print(f"  {name:6s}: {n:5d} token")

    out_est = 200
    print(f"  {'合计输入':6s}: {total_in:5d} token")
    print(f"  {'预估输出':6s}: {out_est:5d} token")

    print("\n  👉 注意：系统提示 + 工具定义是**每一轮都要重发**的固定成本。")

    print_divider("③ 多轮循环时的成本放大")

    print(f"  {'轮次':>4s} {'输入':>8s} {'输出':>6s} {'累计输入':>10s}")
    cum = 0
    fixed = count_tokens(system_prompt) + count_tokens(tool_definitions)
    growing = count_tokens(user_input)

    for round_no in range(1, 6):
        in_tok = fixed + growing
        out_tok = 150
        cum += in_tok
        print(f"  {round_no:>4d} {in_tok:>8d} {out_tok:>6d} {cum:>10d}")
        growing += out_tok + 300        # 工具返回值 + AI 回复进入历史

    print(f"\n  5 轮总输入 token: {cum}")
    print("  👉 输入 token 通常是输出的 10 倍以上 —— 优化的重点在输入。")

    print_divider("④ 不同模型的成本对比")

    total_out = 500
    print(f"  {'模型':16s} {'输入成本':>10s} {'输出成本':>10s} {'合计':>10s}")
    for m in PRICE:
        c_in = total_in / 1_000_000 * PRICE[m][0]
        c_out = total_out / 1_000_000 * PRICE[m][1]
        print(f"  {m:16s} ${c_in:>9.6f} ${c_out:>9.6f} ${c_in + c_out:>9.6f}")

    print("\n  👉 日均 1 万次请求时，模型选择带来的差距是几百美元/天。")

    print_divider("⑤ 真实调用，看实际用量")

    try:
        model = get_model()
        resp = model.invoke("用一句话说明什么是向量检索。")
        print("  回答:", resp.content)
        print("  实际用量:", getattr(resp, "usage_metadata", "（该模型未返回）"))
    except SystemExit:
        print("  （跳过：未配置 API Key）")
    except Exception as e:
        print(f"  调用失败：{type(e).__name__}: {e}")

    print_divider("小结")
    print("  · 固定成本：系统提示 + 工具定义，每轮重发 → 精简它们是最高 ROI")
    print("  · 增长成本：历史消息，随轮次线性增长 → 用裁剪 / 摘要")
    print(f"  · 当前模型：{settings.model}")


if __name__ == "__main__":
    main()
