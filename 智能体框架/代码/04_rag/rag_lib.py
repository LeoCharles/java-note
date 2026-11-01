"""04 | RAG 的核心库：切分、嵌入、索引、检索、重排。

为了不依赖外部数据库，这里用 numpy + pickle 做一个内存向量库。
生产上把它换成 pgvector / Milvus 即可，接口保持一致。
"""

from __future__ import annotations

import hashlib
import json
import pickle
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from config import (
    CHUNK_OVERLAP, CHUNK_SIZE, EMBED_MODEL, EMBED_PROVIDER, INDEX_DIR,
    KEYWORD_TOP_K, MIN_CHUNK_LEN, MIN_RELEVANCE, QUERY_PREFIX, RERANK_TOP_N,
    RRF_K, VECTOR_TOP_K,
)

INDEX_FILE = INDEX_DIR / "store.pkl"


# ============ 数据结构 ============

@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    section: str
    content: str          # 带上下文的完整文本（用于嵌入）
    raw: str              # 原始片段（用于展示）
    source_path: str
    chars: int = 0

    def __post_init__(self):
        self.chars = len(self.raw)


@dataclass
class Store:
    chunks: list[Chunk] = field(default_factory=list)
    vectors: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.chunks)


# ============ 嵌入 ============

class Embedder:
    """统一封装本地 / API 两种嵌入后端。"""

    def __init__(self):
        self._local = None
        self._dims: int | None = None

    def _load_local(self):
        if self._local is None:
            from sentence_transformers import SentenceTransformer

            print(f"  [加载嵌入模型] {EMBED_MODEL}（首次会下载，请稍候）…")
            self._local = SentenceTransformer(EMBED_MODEL)
        return self._local

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if EMBED_PROVIDER == "openai":
            return self._embed_openai(texts)
        model = self._load_local()
        vecs = model.encode(texts, normalize_embeddings=True,
                            batch_size=16, show_progress_bar=len(texts) > 20)
        return np.asarray(vecs, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        if EMBED_PROVIDER == "openai":
            return self._embed_openai([text])[0]
        model = self._load_local()
        # BGE 系列建议给查询加指令前缀
        q = QUERY_PREFIX + text if "bge" in EMBED_MODEL.lower() else text
        return np.asarray(model.encode(q, normalize_embeddings=True), dtype=np.float32)

    def _embed_openai(self, texts: list[str]) -> np.ndarray:
        from langchain_openai import OpenAIEmbeddings

        from common import settings

        emb = OpenAIEmbeddings(model=EMBED_MODEL, api_key=settings.api_key,
                               base_url=settings.base_url)
        return np.asarray(emb.embed_documents(texts), dtype=np.float32)


_embedder = Embedder()


def get_embedder() -> Embedder:
    return _embedder


# ============ 加载与清洗 ============

NOISE_PATTERNS = [
    r"^\s*第\s*\d+\s*页\s*共\s*\d+\s*页\s*$",
    r"^\s*Copyright\s*©.*$",
    r"^\s*内部资料.*严禁外传.*$",
    r"^\s*[-_=]{5,}\s*$",
]


def clean_text(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        s = line.rstrip()
        if any(re.match(p, s.strip(), re.I) for p in NOISE_PATTERNS):
            continue
        lines.append(s)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def load_markdown_docs(docs_dir: Path) -> list[dict]:
    docs = []
    for p in sorted(docs_dir.glob("*.md")):
        raw = p.read_text(encoding="utf-8")
        docs.append({
            "doc_id": p.stem,
            "title": p.stem,
            "content": clean_text(raw),
            "source_path": str(p.relative_to(docs_dir.parent)),
        })
    return docs


# ============ 切分 ============

def split_by_headers(content: str) -> list[tuple[str, str]]:
    """按 Markdown 标题切，返回 [(章节路径, 正文)]。"""
    sections: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []

    def flush():
        if buf:
            path = " > ".join(t for _, t in stack)
            body = "\n".join(buf).strip()
            if body:
                sections.append((path, body))
            buf.clear()

    for line in content.split("\n"):
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush()
            level, title = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        else:
            buf.append(line)
    flush()
    return sections


def split_long(text: str, size: int, overlap: int) -> list[str]:
    """按字符切长段落，优先在句号/换行处断开。"""
    if len(text) <= size:
        return [text]

    seps = ["\n\n", "\n", "。", "；", "，", " "]
    out, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            best = -1
            for sep in seps:
                pos = text.rfind(sep, start + size // 2, end)
                if pos > best:
                    best = pos
            if best > 0:
                end = best + 1
        piece = text[start:end].strip()
        if piece:
            out.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return out


def build_chunks(docs: list[dict]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in docs:
        for path, body in split_by_headers(doc["content"]):
            prefix = f"【文档】{doc['title']}"
            if path:
                prefix += f"【章节】{path}"

            for piece in split_long(body, CHUNK_SIZE, CHUNK_OVERLAP):
                if len(piece) < MIN_CHUNK_LEN:
                    continue
                cid = hashlib.md5(
                    f"{doc['doc_id']}|{path}|{piece}".encode()
                ).hexdigest()[:16]
                chunks.append(Chunk(
                    chunk_id=cid,
                    doc_id=doc["doc_id"],
                    title=doc["title"],
                    section=path,
                    content=f"{prefix}\n\n{piece}",     # 带元数据前缀，提升召回
                    raw=piece,
                    source_path=doc["source_path"],
                ))
    return chunks


# ============ 索引 ============

def build_index(docs_dir: Path) -> Store:
    docs = load_markdown_docs(docs_dir)
    print(f"  加载文档 {len(docs)} 篇")

    chunks = build_chunks(docs)
    print(f"  切分片段 {len(chunks)} 个（平均 {sum(c.chars for c in chunks) // max(len(chunks), 1)} 字）")

    print("  正在向量化…")
    vectors = _embedder.embed_documents([c.content for c in chunks])
    print(f"  向量维度 {vectors.shape}")

    store = Store(chunks=chunks, vectors=vectors)
    save_index(store)
    return store


def save_index(store: Store) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "wb") as f:
        pickle.dump(store, f)
    meta = {
        "chunks": len(store.chunks),
        "dims": int(store.vectors.shape[1]) if store.vectors is not None else 0,
        "embed_provider": EMBED_PROVIDER,
        "embed_model": EMBED_MODEL,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
    }
    (INDEX_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_index() -> Store:
    if not INDEX_FILE.exists():
        raise SystemExit(
            "索引不存在，请先运行：\n    python 04_rag/build_index.py"
        )
    with open(INDEX_FILE, "rb") as f:
        return pickle.load(f)


# ============ 检索 ============

def vector_search(store: Store, query: str, k: int = VECTOR_TOP_K) -> list[tuple[int, int]]:
    """返回 [(chunk_index, rank)]，rank 从 1 开始。"""
    qv = _embedder.embed_query(query)
    # 向量已归一化，点积 = 余弦相似度
    scores = store.vectors @ qv
    order = np.argsort(-scores)[:k]
    return [(int(i), r + 1) for r, i in enumerate(order)]


def keyword_search(store: Store, query: str, k: int = KEYWORD_TOP_K) -> list[tuple[int, int]]:
    """简易关键词检索：按查询词的覆盖度打分。

    生产上应该用 pgvector + to_tsvector('zh', ...) 或 ES。
    """
    terms = [t for t in re.split(r"[\s，。？！、；：]+", query) if len(t) >= 2]
    if not terms:
        terms = list(query)

    scored = []
    for i, c in enumerate(store.chunks):
        hits = sum(1 for t in terms if t in c.raw)
        if hits:
            scored.append((hits, i))
    scored.sort(reverse=True)

    return [(i, r + 1) for r, (_, i) in enumerate(scored[:k])]


def rrf_fuse(lists: list[list[tuple[int, int]]], k: int = RRF_K) -> list[int]:
    scores: dict[int, float] = {}
    for ranked in lists:
        for idx, rank in ranked:
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)


# ============ 重排 ============

_reranker = None


def _load_reranker():
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder

            print("  [加载重排模型] BAAI/bge-reranker-v2-m3 …")
            _reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)
        except Exception as e:
            print(f"  [警告] 重排模型不可用（{type(e).__name__}），改用向量分数")
            _reranker = False
    return _reranker


def rerank(store: Store, query: str, indices: list[int], top_n: int = RERANK_TOP_N) -> list[dict]:
    if not indices:
        return []

    model = _load_reranker()
    if model:
        pairs = [(query, store.chunks[i].raw) for i in indices]
        scores = model.predict(pairs)
    else:
        # 退化：用向量相似度
        qv = _embedder.embed_query(query)
        scores = [float(store.vectors[i] @ qv) for i in indices]

    ranked = sorted(zip(indices, scores), key=lambda x: -float(x[1]))[:top_n]

    out = []
    for i, s in ranked:
        c = store.chunks[i]
        out.append({
            "chunk_id": c.chunk_id,
            "title": c.title,
            "section": c.section,
            "content": c.raw,
            "source": c.source_path,
            "score": float(s),
        })
    return out


# ============ 对外接口 ============

def retrieve(store: Store, query: str, top_n: int = RERANK_TOP_N,
             use_hybrid: bool = True, use_rerank: bool = True) -> list[dict]:
    vec = vector_search(store, query)
    if use_hybrid:
        kw = keyword_search(store, query)
        fused = rrf_fuse([vec, kw])
        # RRF 只给顺序，这里再按向量分数保留一个好用的分数
        qv = _embedder.embed_query(query)
        indices = sorted(fused, key=lambda i: -float(store.vectors[i] @ qv))
    else:
        indices = [i for i, _ in vec]

    if use_rerank:
        return rerank(store, query, indices, top_n)

    out = []
    for i in indices[:top_n]:
        c = store.chunks[i]
        out.append({"chunk_id": c.chunk_id, "title": c.title, "section": c.section,
                    "content": c.raw, "source": c.source_path,
                    "score": float(store.vectors[i] @ _embedder.embed_query(query))})
    return out


def is_relevant(docs: list[dict], threshold: float = MIN_RELEVANCE) -> bool:
    """相关性判定：决定「回答」还是「说不知道」。"""
    if not docs:
        return False
    scores = [d["score"] for d in docs]

    # 有 rerank 分数时直接用；退化模式下向量余弦通常更小
    if _reranker:
        return max(scores) >= threshold

    # 没有 rerank 时退回向量余弦阈值
    # （余弦阈值和重排分数不是一个量纲，所以两条路要分别校准）
    return max(scores) >= 0.45


def format_docs(docs: list[dict]) -> str:
    lines = []
    for i, d in enumerate(docs, 1):
        loc = f"《{d['title']}》"
        if d["section"]:
            loc += f" — {d['section']}"
        lines.append(f"[{i}] {loc}\n{d['content']}")
    return "\n\n---\n\n".join(lines)


__all__ = [
    "Chunk", "Store", "build_index", "load_index", "save_index",
    "retrieve", "is_relevant", "format_docs", "get_embedder",
    "split_by_headers", "build_chunks", "clean_text", "load_markdown_docs",
    "vector_search", "keyword_search", "rrf_fuse", "rerank",
]
