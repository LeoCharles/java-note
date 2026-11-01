"""11 | 知识库问答 Agent（完整小项目）。

对应文档：11-实战-企业知识库问答Agent.md

运行：
    python 11_kb_agent/build_index.py       # 建索引
    python 11_kb_agent/chat.py              # 交互问答
    python 11_kb_agent/chat.py "VPN 连不上"  # 单次提问
"""

import re
import sys
from pathlib import Path

import numpy as np

# 复用 04 的 RAG 组件
RAG_DIR = Path(__file__).resolve().parent.parent / "04_rag"
sys.path.insert(0, str(RAG_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rag_lib  # noqa: E402

# 让 11 可以有自己的文档目录
DOCS_DIR = Path(__file__).resolve().parent / "docs"
INDEX_DIR = Path(__file__).resolve().parent / ".index"


def load_docs_with_acl() -> list[dict]:
    """加载文档，从文件头解析 ACL 和更新时间。

    文件格式（可选）：
        <!-- acl: all, dept:HR -->
        <!-- updated: 2026-03-01 -->
        # 标题
        正文…

    返回的每篇文档形如：
        {"doc_id", "title", "content", "acl": [...], "source_path", "updated_at"}
    """
    docs = []
    for p in sorted(DOCS_DIR.glob("*.md")):
        raw = p.read_text(encoding="utf-8")

        acl = ["all"]
        updated = "2026-01-01"

        m_acl = re.search(r"<!--\s*acl:\s*([^-]+?)\s*-->", raw)
        if m_acl:
            acl = [a.strip() for a in m_acl.group(1).split(",") if a.strip()]

        m_up = re.search(r"<!--\s*updated:\s*([\d-]+)\s*-->", raw)
        if m_up:
            updated = m_up.group(1)

        content = re.sub(r"<!--.*?-->", "", raw, flags=re.S).strip()
        content = rag_lib.clean_text(content)

        docs.append({
            "doc_id": p.stem,
            "title": p.stem,
            "content": content,
            "acl": acl,
            "source_path": str(p.name),
            "updated_at": updated,
        })
    return docs


def build_chunks_with_acl(docs: list[dict]) -> list[dict]:
    """切分并保留 ACL 元数据。"""
    chunks = []
    for doc in docs:
        for path, body in rag_lib.split_by_headers(doc["content"]):
            prefix = f"【文档】{doc['title']}"
            if path:
                prefix += f"【章节】{path}"

            for piece in rag_lib.split_long(body, 400, 80):
                if len(piece) < 30:
                    continue
                chunks.append({
                    "chunk_id": f"{doc['doc_id']}#{len(chunks)}",
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "section": path,
                    "content": f"{prefix}\n\n{piece}",
                    "raw": piece,
                    "source": doc["source_path"],
                    "acl": doc["acl"],
                    "updated_at": doc["updated_at"],
                })
    return chunks


def build_and_save() -> None:
    docs = load_docs_with_acl()
    chunks = build_chunks_with_acl(docs)

    print(f"  文档 {len(docs)} 篇，切分 {len(chunks)} 个 chunk")

    emb = rag_lib.get_embedder()
    vectors = emb.embed_documents([c["content"] for c in chunks])

    store = {
        "chunks": chunks,
        "vectors": vectors,
    }

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    import pickle

    with open(INDEX_DIR / "kb.pkl", "wb") as f:
        pickle.dump(store, f)

    print(f"  ✅ 索引已保存到 {INDEX_DIR / 'kb.pkl'}")


def load_store() -> dict:
    import pickle

    p = INDEX_DIR / "kb.pkl"
    if not p.exists():
        raise SystemExit("索引不存在，请先运行：\n    python 11_kb_agent/build_index.py")
    with open(p, "rb") as f:
        return pickle.load(f)


# ============ 带权限的检索 ============

def retrieve_with_acl(store: dict, query: str, user_acls: list[str],
                      top_k: int = 20, top_n: int = 4) -> list[dict]:
    """关键：权限过滤发生在检索阶段，不是取回后再筛。"""
    chunks = store["chunks"]
    vectors = store["vectors"]

    # ① 先在候选集里按 ACL 过滤（生产上这是 SQL 的 WHERE acl && user_acls）
    allowed = [
        i for i, c in enumerate(chunks)
        if set(c["acl"]) & set(user_acls)
    ]
    if not allowed:
        return []

    # ② 只在允许的范围内做向量检索
    emb = rag_lib.get_embedder()
    qv = emb.embed_query(query)
    sub = vectors[allowed]
    scores = sub @ qv

    k = min(top_k, len(allowed))
    order = np.argsort(-scores)[:k]
    candidates = [(allowed[int(i)], float(scores[int(i)])) for i in order]

    # ③ 关键词召回（同样限在 allowed 内）
    #    中文没有空格，按二元组匹配，效果比按空格切词好得多。
    #    但二元组噪声也多（「店能」「能报」这种跨词边界的组合），
    #    所以要求**至少命中 2 个**才进候选 —— 只命中 1 个的基本是巧合。
    qb = _bigrams(_normalize_query(query))
    kw_hits = []
    if qb:
        for idx in allowed:
            hit = len(qb & _bigrams(chunks[idx]["raw"] + chunks[idx]["section"]))
            if hit >= 2:
                kw_hits.append((idx, hit))
        kw_hits.sort(key=lambda x: -x[1])

    # ④ RRF 融合
    scores_map: dict[int, float] = {}
    for rank, (idx, _) in enumerate(candidates, 1):
        scores_map[idx] = scores_map.get(idx, 0) + 1 / (60 + rank)
    for rank, (idx, _) in enumerate(kw_hits[:top_k], 1):
        scores_map[idx] = scores_map.get(idx, 0) + 1 / (60 + rank)

    fused = sorted(scores_map, key=scores_map.get, reverse=True)[:top_n]

    return [{
        "chunk_id": chunks[i]["chunk_id"],
        "title": chunks[i]["title"],
        "section": chunks[i]["section"],
        "content": chunks[i]["raw"],
        "source": chunks[i]["source"],
        "updated_at": chunks[i]["updated_at"],
        "score": scores_map[i],
    } for i in fused]


def user_acls(user: dict) -> list[str]:
    acls = ["all"]
    for d in user.get("departments", []):
        acls.append(f"dept:{d}")
    if user.get("level") in ("manager", "director"):
        acls.append("level:manager")
    return acls


# ============ 检索质量判定 ============

# 常见虚词/问句套话，不参与「是否相关」判断
STOP_BIGRAMS = {
    "公司", "我们", "你们", "请问", "什么", "多少", "怎么", "如何",
    "可以", "是否", "有没", "没有", "一个", "这个", "那个", "是不",
    "有什", "么样", "么办", "哪些", "为什",
}

# 领域同义词：用户口语 → 文档用词
#
# 这是中文 RAG 里性价比最高的一步。用户说「酒店」，文档写「住宿标准」；
# 用户问「薪资范围」，制度里叫「薪酬带宽」。字面一个字都对不上，
# 向量还能勉强沾边，关键词召回直接全军覆没。
#
# 生产上这张表要从**真实会话里挖**：把「搜不到/答不准」的 query 捞出来，
# 人工看几条，补一次表，比换嵌入模型见效快。
SYNONYMS = [
    ("薪资", "薪酬"),
    ("工资", "薪酬"),
    ("酒店", "住宿"),
    ("能报", "报销"),
    ("报多少", "报销"),
    ("怎么报", "报销"),
    ("年休假", "年假"),
]


def _normalize_query(text: str) -> str:
    out = text
    for a, b in SYNONYMS:
        out = out.replace(a, b)
    return out


def _bigrams(text: str) -> set[str]:
    """把文本切成二元组（中文按字，英文/数字按整体）。

    不用分词器，是为了让示例少一个依赖；生产上换成 jieba + 词表更准。
    """
    out: set[str] = set()
    for run in re.findall(r"[A-Za-z0-9]+|[一-龥]+", text):
        if re.match(r"[A-Za-z0-9]", run):
            if len(run) >= 2:
                out.add(run)
            continue
        for i in range(len(run) - 1):
            bg = run[i:i + 2]
            if bg not in STOP_BIGRAMS:
                out.add(bg)
    return out


def is_relevant(docs: list[dict], query: str) -> bool:
    """相关性判定：决定「回答」还是「说不知道」。

    两条通路，满足其一就算相关：
      · strong：查询词命中了某条结果的**标题/章节**（如「VPN」「年假」）
      · weak  ：命中了**正文**，且至少 2 个二元组

    「P7 的薪资范围」这种，普通员工只能匹配到住宿标准里的一个 P7，
    所以会被判为不相关 —— 这正是我们要的：**拒答，而不是答错。**

    ⚠️ 生产上不要用这种字符匹配做阈值，用「过滤后的向量/重排分数 + 评测集校准」，
       见 04_rag 的 MIN_RELEVANCE 与文档 11 的阈值标定流程。
    """
    if not docs:
        return False

    qb = _bigrams(_normalize_query(query))
    if not qb:
        return True

    strong = weak = 0
    for d in docs[:3]:
        strong += len(qb & _bigrams(f"{d['title']} {d['section']}"))
        weak += len(qb & _bigrams(d["content"]))

    return strong >= 1 or weak >= 2
