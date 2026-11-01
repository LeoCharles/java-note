"""04 | 建索引。

对应文档：04-RAG检索增强生成.md「离线链路」

运行：
    python 04_rag/build_index.py            # 建索引
    python 04_rag/build_index.py --inspect  # 只看切分结果，不建索引
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DOCS_DIR
from rag_lib import build_chunks, build_index, load_markdown_docs, split_by_headers


def inspect_chunks() -> None:
    """切分质量检查：上线前一定要看。"""
    docs = load_markdown_docs(DOCS_DIR)
    print(f"文档数：{len(docs)}\n")

    for doc in docs:
        sections = split_by_headers(doc["content"])
        print(f"《{doc['title']}》 -> {len(sections)} 个章节")
        for path, body in sections:
            print(f"  · {path or '(正文)'}  {len(body)} 字")

    chunks = build_chunks(docs)
    print(f"\n切分结果：{len(chunks)} 个 chunk")
    print(f"平均长度：{sum(c.chars for c in chunks) // len(chunks)} 字")
    print(f"最短：{min(c.chars for c in chunks)} 字  "
          f"最长：{max(c.chars for c in chunks)} 字")

    print("\n" + "=" * 60)
    print("抽样查看 3 个 chunk（检查是否被切断、是否带上下文）")
    print("=" * 60)
    for c in chunks[:3]:
        print(f"\n[{c.chunk_id}] {c.title} / {c.section}")
        print("-" * 60)
        print(c.content[:400])
        print("-" * 60)


def main() -> None:
    if "--inspect" in sys.argv:
        inspect_chunks()
        return

    print("=" * 60)
    print("  建立索引")
    print("=" * 60)
    store = build_index(DOCS_DIR)
    print(f"\n✅ 完成：{len(store)} 个 chunk，索引已保存")
    print("   下一步：python 04_rag/rag_qa.py \"年假有几天\"")


if __name__ == "__main__":
    main()
