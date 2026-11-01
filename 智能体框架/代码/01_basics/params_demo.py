"""01 | 参数演示：temperature / max_tokens / 结构化提示。

对应文档：01-大模型应用开发基础.md「参数」「Prompt」

运行：
    python 01_basics/params_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import get_model, print_divider


def main() -> None:
    print_divider("① max_tokens：截断")

    model = get_model()
    for mt in (20, 80):
        r = model.bind(max_tokens=mt).invoke("介绍一下杭州西湖的历史。")
        print(f"  max_tokens={mt:3d} 实际长度={len(r.content):3d}")
        print(f"    {r.content[:120]}...")
        print()

    print("  👉 max_tokens 截断会得到半句话。生成长内容时要注意。")

    print_divider("② 同一个问题，不同提示的差异")

    question = "公司要给员工发中秋节礼品，预算每人 100 元。帮我出个主意。"

    prompts = {
        "模糊": question,
        "要结构": question + "\n\n请用「推荐 + 理由 + 预算明细」三段式回答。",
        "要具体": question + "\n\n要求：给出 3 个具体商品，每个含名称、单价、购买渠道，不要泛泛而谈。",
        "要简短": question + "\n\n用一句话回答，不超过 30 字。",
    }

    for label, p in prompts.items():
        r = get_model().invoke(p)
        print(f"  【{label}】")
        print(f"    {r.content.strip()[:200]}")
        print()

    print_divider("③ 系统提示决定人设与边界")

    sys_prompts = {
        "无系统提示": None,
        "专家": "你是一位有 15 年经验的 Java 架构师，回答专业、直接指出问题。",
        "小学生": "你是一个 8 岁的小学生，用很简单的话解释。",
        "严格": "你只回答与编程相关的问题。其他问题统一回复「这不在我的专业范围内」。",
    }

    q = "什么是缓存穿透？"

    for label, sp in sys_prompts.items():
        msgs = ([("system", sp)] if sp else []) + [("human", q)]
        r = get_model().invoke(msgs)
        print(f"  【{label}】{r.content.strip()[:150]}")
        print()

    print("  --- 用「严格」人设问一个非编程问题 ---")
    r = get_model().invoke([
        ("system", sys_prompts["严格"]),
        ("human", "今天天气怎么样？"),
    ])
    print(f"  {r.content.strip()}")

    print_divider("④ 用 assistant 预填充控制输出格式")

    # 有些厂商支持：给 assistant 一个开头，模型会接着写
    try:
        r = get_model().invoke([
            ("system", "你输出 JSON，不要任何解释。"),
            ("human", "提取信息：张三 13800138000 北京市朝阳区"),
            ("assistant", '{"name": "'),
        ])
        print("  预填充结果:", r.content[:100])
    except Exception as e:
        print(f"  该接口不支持 assistant 预填充：{type(e).__name__}")
        print("  → 改用结构化输出（见 02/structured_output.py）更可靠")

    print_divider("⑤ 结构化输出的必要性")

    # 反面：让模型自由输出，然后自己解析
    r = get_model().invoke(
        "提取：张三 13800138000 北京市朝阳区。"
        "输出 name/phone/city 三个字段，JSON 格式。"
    )
    print("  自由输出：")
    print(f"    {r.content.strip()}")
    print("\n  👉 可能带 ```json 包装，可能字段名不一致，可能多解释一句。")
    print("     解析会失败 → 这就是为什么需要 with_structured_output（02 篇）")


if __name__ == "__main__":
    main()
