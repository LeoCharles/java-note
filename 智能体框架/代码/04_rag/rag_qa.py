"""04 | RAG 问答：检索 → 判定 → 生成 → 引用校验。

对应文档：04-RAG检索增强生成.md「在线链路」

运行：
    python 04_rag/rag_qa.py                    # 交互式
    python 04_rag/rag_qa.py "年假有几天"        # 单次提问
    python 04_rag/rag_qa.py --compare "年假"    # 对比检索策略
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.prompts import ChatPromptTemplate

from common import get_model, print_divider
from config import MAX_ANSWER_CHARS
from rag_lib import format_docs, is_relevant, load_index, retrieve


SYSTEM = """你是公司内部知识库助手。

【回答规则】
1. 只依据【资料】回答，不使用资料外的知识。
2. 每个结论后用 [编号] 标注来源，例如「年假 5 天[1]」。
3. 资料不足以回答时，明确说「知识库中没有找到相关信息」，并建议咨询对应部门。
4. 回答控制在 {max_chars} 字以内，直接答问题，不要复述资料。
5. 涉及金额、天数、比例，必须与资料完全一致，不要换算或推断。
6. 若资料相互矛盾，指出矛盾并建议确认最新版本。

【资料】
{docs}
"""

CITE_RE = re.compile(r"\[(\d+)\]")


def validate_citations(answer: str, docs: list[dict]) -> tuple[str, list[dict]]:
    """模型经常编造引用编号，必须校验。"""
    valid = {str(i) for i in range(1, len(docs) + 1)}
    used: set[int] = set()

    def fix(m):
        n = m.group(1)
        if n in valid:
            used.add(int(n))
            return m.group(0)
        return ""

    cleaned = CITE_RE.sub(fix, answer)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned, [docs[i - 1] for i in sorted(used)]


def answer(question: str, store, model,
           use_hybrid: bool = True, use_rerank: bool = True, verbose: bool = True) -> dict:
    docs = retrieve(store, question, use_hybrid=use_hybrid, use_rerank=use_rerank)

    if verbose and docs:
        print("\n  【检索结果】")
        for i, d in enumerate(docs, 1):
            print(f"    [{i}] {d['title']} / {d['section']}  score={d['score']:.3f}")

    if not is_relevant(docs):
        if verbose:
            print(f"\n  【判定】最高分 {max((d['score'] for d in docs), default=0):.3f} "
                  f"< 阈值 → 拒答")
        return {
            "answer": (f"知识库中没有找到与「{question}」直接相关的内容。\n\n"
                       f"建议：\n"
                       f"- 换个说法再问一次（例如用制度名称、流程名称）\n"
                       f"- 咨询 HR / IT 服务台\n"
                       f"- 如果这份文档应该有，请联系知识库管理员补充"),
            "sources": [],
            "relevant": False,
            "docs": docs,
        }

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM.replace("{max_chars}", str(MAX_ANSWER_CHARS))),
        ("human", "{question}"),
    ])
    resp = (prompt | model).invoke({
        "docs": format_docs(docs),
        "question": question,
    })

    text, sources = validate_citations(resp.content, docs)

    warning = ""
    if docs and not sources:
        warning = "\n\n（注：本条回答未引用知识库原文，建议核实）"

    return {
        "answer": text + warning,
        "sources": [{"title": s["title"], "section": s["section"],
                     "source": s["source"], "score": s["score"]} for s in sources],
        "relevant": True,
        "docs": docs,
    }


def print_result(result: dict) -> None:
    print("\n  【回答】")
    print(f"    {result['answer']}")

    if result["sources"]:
        print("\n  【来源】")
        for i, s in enumerate(result["sources"], 1):
            print(f"    [{i}] 《{s['title']}》{(' — ' + s['section']) if s['section'] else ''}")


def compare_strategies(question: str, store, model) -> None:
    print_divider(f"对比检索策略：「{question}」")

    configs = [
        ("纯向量", False, False),
        ("向量 + 关键词", True, False),
        ("向量 + 关键词 + 重排", True, True),
    ]

    for name, hybrid, rerank in configs:
        print(f"\n  ── {name} ──")
        result = answer(question, store, model, use_hybrid=hybrid,
                        use_rerank=rerank, verbose=True)
        print(f"    回答：{result['answer'][:120]}")
        if result["sources"]:
            print(f"    来源：{[s['title'] for s in result['sources']]}")


def interactive(store, model) -> None:
    print_divider("知识库问答（输入 q 退出）")
    print("  试试这些：")
    print("    · 入职满三年有几天年假？")
    print("    · 出差住酒店能报多少？")
    print("    · VPN 连不上怎么办？")
    print("    · 公司有食堂吗？（应该拒答）")
    print()

    while True:
        try:
            q = input("  问：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in ("q", "quit", "exit"):
            break
        print_result(answer(q, store, model))
        print()


def main() -> None:
    store = load_index()
    model = get_model()

    print(f"索引已加载：{len(store)} 个 chunk")

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if "--compare" in sys.argv and args:
        compare_strategies(args[0], store, model)
    elif args:
        print_divider(f"问题：{args[0]}")
        print_result(answer(args[0], store, model))
    else:
        interactive(store, model)


if __name__ == "__main__":
    main()
