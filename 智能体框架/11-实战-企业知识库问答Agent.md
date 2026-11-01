# 11 - 实战：企业知识库问答 Agent

> 前面十篇把零件都造齐了。这一篇开始**装配**。
> 目标是做一个**真能在公司里跑起来**的知识库问答：员工问"年假怎么算"，它去公司文档里找，回答并给出来源；实习生问"报销流程"，它不仅能答，还能帮人发起流程。
> 这个项目我们**从需求分析做到上线**，每一步都给完整代码。

---

## 📖 目录

1. [需求分析：先想清楚要解决什么](#一需求分析先想清楚要解决什么)
2. [技术方案设计 ⭐](#二技术方案设计-)
3. [项目骨架](#三项目骨架)
4. [数据接入：文档从哪来 ⭐](#四数据接入文档从哪来-)
5. [切分与索引：让文档变得可检索 ⭐⭐](#五切分与索引让文档变得可检索-)
6. [检索层：混合检索 + 重排 ⭐⭐](#六检索层混合检索--重排-)
7. [回答层：引用、拒答、追问 ⭐⭐](#七回答层引用拒答追问-)
8. [Agent 化：从问答升级到办事 ⭐⭐](#八agent-化从问答升级到办事-)
9. [权限：不同人能看不同文档 ⭐⭐](#九权限不同人能看不同文档-)
10. [会话与追问](#十会话与追问)
11. [增量同步与文档治理](#十一增量同步与文档治理)
12. [评测：怎么知道它到底准不准](#十二评测怎么知道它到底准不准)
13. [接口与前端](#十三接口与前端)
14. [部署与运维](#十四部署与运维)
15. [上线后的真实问题](#十五上线后的真实问题)
16. [本章小结与练习](#本章小结与练习)

---

## 一、需求分析：先想清楚要解决什么

### 1.1 场景

**某公司 800 人，制度、流程、产品文档散落在 Confluence、飞书、共享盘、邮件里。**

员工找信息的方式是：

- 在群里问 HR / IT / 行政，平均等 20 分钟
- 自己搜，搜不到就放弃
- 找到的是三年前的旧版本

**HR 和 IT 每月重复回答同样的问题上百次。**

### 1.2 目标

> **让员工用自然语言，在 10 秒内找到有出处的答案。**

**可量化的目标**：

| 指标 | 现状 | 目标 |
| :--- | :--- | :--- |
| 平均找信息耗时 | 20 分钟 | < 30 秒 |
| HR/IT 重复问题量 | 300 次/月 | 降 60% |
| 答案准确率 | — | > 85% |
| 有出处比例 | — | 100% |

### 1.3 范围（很重要）

| 做 | 不做 |
| :--- | :--- |
| 制度、流程、产品说明的问答 | 八卦、闲聊 |
| 给出原文出处链接 | 替人做决策（"我该不该辞职"） |
| 引导到发起流程 | 直接代办审批 |
| 覆盖 3 个主要系统 | 接入全部 20 个系统 |

> ⚠️ **第一版范围一定要窄**。**"什么都能问"是最常见的失败起点**——覆盖太广会导致召回率极低，用户体验差。

### 1.4 关键约束

| 约束 | 影响 |
| :--- | :--- |
| 数据不能出内网 | 用私有化模型或内网网关 |
| 文档有权限分级 | 检索必须带权限过滤 |
| 文档会更新 | 需要增量同步 |
| 老文档要淘汰 | 需要"时效性"判断 |
| 用户不会看长答案 | 回答要短，细节给出处 |

---

## 二、技术方案设计 ⭐

### 2.1 整体架构

```text
【离线】
 数据源 ──► 加载 ──► 清洗 ──► 切分 ──► 向量化 ──► PostgreSQL(pgvector)
  Confluence   │        │        │                    +
  飞书         │        │        └─ 元数据（权限、来源、版本）
  共享盘       │        └─ 去噪、去页眉页脚
  上传         └─ 增量识别（content_hash）

【在线】
 用户问题
   │
   ▼
 意图分类 ──► 闲聊/闲聊外 ──► 礼貌拒绝
   │
   ▼ 知识问答
 查询改写（可选）
   │
   ▼
 混合检索（向量 + 关键词）──► 权限过滤
   │
   ▼
 重排（rerank）
   │
   ▼
 相关性判定 ──► 不足 ──► 明确"没找到" + 建议
   │
   ▼ 充足
 生成回答（带引用）
   │
   ▼
 引用校验 ──► 输出
```

### 2.2 技术选型

| 组件 | 选择 | 理由 |
| :--- | :--- | :--- |
| 编排 | LangGraph | 要分支、要权限、要可观测 |
| 模型 | GPT-4o-mini / 内网通义千问 | 成本与质量平衡 |
| 嵌入 | BGE-M3（中文强） | 中英文混合、支持长文本 |
| 向量库 | PostgreSQL + pgvector | 已有 PG，少一个组件；支持元数据过滤 |
| 重排 | bge-reranker-v2-m3 | 本地部署，效果好 |
| 关键词 | PG 全文索引（zhparser） | 与向量库同库，易做混合 |
| 缓存 | Redis | 查询结果、embedding |
| 服务 | FastAPI | 异步、生态好 |

> 💡 **不要一上来就上 Milvus/ES**。**pgvector 在百万级文档下完全够用**，且能和业务数据同库做联表过滤，运维成本低得多。

### 2.3 为什么不用纯向量检索

| 问题 | 纯向量 | 混合 |
| :--- | :--- | :--- |
| "OA 系统 V2.3 版本" 精确匹配 | 差 | 关键词能中 |
| 专有名词/缩写 | 差 | 好 |
| 语义改写（"怎么请假"→"休假制度"） | 好 | 好 |
| 数字、编号 | 差 | 好 |

**结论**：**必须混合检索。** 向量管语义，关键词管精确。

### 2.4 为什么需要重排

**向量检索的 top-20 里，真正相关的可能只有 3 条，而且排序不对。**
**重排模型（cross-encoder）把 query 和 doc 一起输入，精度高得多。**

```text
向量检索 top 20（快、粗） → rerank → top 4（准）
```

### 2.5 版本规划

| 版本 | 内容 | 周期 |
| :--- | :--- | :--- |
| V1 | 单轮问答 + 引用 + 权限 | 3 周 |
| V1.5 | 多轮 + 增量同步 + 评测 | 2 周 |
| V2 | 办事能力（发起流程） | 3 周 |
| V2.5 | 反馈闭环 + 文档治理 | 持续 |

---

## 三、项目骨架

```text
kb-agent/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── chat.py
│   │   └── admin.py
│   ├── ingest/
│   │   ├── loaders.py         # 各数据源加载
│   │   ├── cleaner.py         # 清洗
│   │   ├── splitter.py        # 切分
│   │   └── indexer.py         # 入库
│   ├── rag/
│   │   ├── retrieve.py        # 混合检索
│   │   ├── rerank.py
│   │   └── generate.py        # 回答生成
│   ├── graph/
│   │   ├── qa_graph.py        # LangGraph 主图
│   │   └── state.py
│   ├── tools/
│   │   ├── kb_tools.py
│   │   └── hr_tools.py        # 发起流程
│   ├── security/
│   │   └── acl.py             # 权限
│   └── obs/
│       └── logging.py
├── scripts/
│   ├── build_index.py
│   └── sync_docs.py
├── eval/
│   ├── cases.json
│   └── run_eval.py
└── pyproject.toml
```

---

## 四、数据接入：文档从哪来 ⭐

### 4.1 数据源盘点

| 源 | 格式 | 量 | 更新 |
| :--- | :--- | :--- | :--- |
| Confluence | HTML / API | 1200 页 | 不定 |
| 飞书文档 | API | 400 篇 | 不定 |
| 共享盘 | PDF / DOCX | 300 个 | 季度 |
| 上传 | PDF / DOCX / MD | — | 随时 |

### 4.2 统一文档模型

**所有源都转成同一个结构**，后续流程就不用管来源：

```python
from pydantic import BaseModel, Field
from datetime import datetime

class RawDoc(BaseModel):
    doc_id: str                      # 全局唯一，如 "confluence:12345"
    source: str                      # confluence | feishu | share | upload
    title: str
    content: str                     # 纯文本
    url: str | None = None           # 原文链接
    updated_at: datetime | None = None
    acl: list[str] = Field(default_factory=list)   # 可见的部门/角色
    tags: list[str] = Field(default_factory=list)
    version: str | None = None
    content_hash: str = ""           # 用于增量识别
```

### 4.3 Confluence 加载

```python
# app/ingest/loaders.py
import httpx, hashlib, re
from bs4 import BeautifulSoup

def load_confluence(base: str, token: str, space: str) -> list[RawDoc]:
    docs = []
    start = 0
    while True:
        r = httpx.get(
            f"{base}/rest/api/content",
            params={"spaceKey": space, "expand": "body.storage,version,metadata.labels",
                    "limit": 50, "start": start},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        data = r.json()
        for page in data.get("results", []):
            raw_md = html_to_markdown(page["body"]["storage"]["value"])
            md = clean_text(raw_md)
            docs.append(RawDoc(
                doc_id=f"confluence:{page['id']}",
                source="confluence",
                title=page["title"],
                content=md,
                url=f"{base}/pages/viewpage.action?pageId={page['id']}",
                updated_at=datetime.fromisoformat(page["version"]["when"]),
                acl=extract_acl_from_labels(page.get("metadata", {}).get("labels", {})),
                tags=[l["name"] for l in page.get("metadata", {}).get("labels", {}).get("results", [])],
                version=str(page["version"]["number"]),
                content_hash=hashlib.sha256(md.encode()).hexdigest(),
            ))
        if "next" not in data.get("_links", {}):
            break
        start += 50
    return docs


def html_to_markdown(html: str) -> str:
    """HTML 转 Markdown，保留标题层级，这是切分的依据。"""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "nav", "footer"]):
        t.decompose()

    out = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "table", "pre"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        if el.name.startswith("h"):
            out.append("#" * int(el.name[1]) + " " + text)
        elif el.name == "li":
            out.append("- " + text)
        elif el.name == "pre":
            out.append("```\n" + text + "\n```")
        else:
            out.append(text)
    return "\n\n".join(out)
```

### 4.4 清洗

**这一步的收益常被低估。脏数据会让检索质量直接腰斩。**

```python
import re

NOISE_PATTERNS = [
    r"^\s*第\s*\d+\s*页\s*共\s*\d+\s*页\s*$",
    r"^\s*Copyright\s*©.*$",
    r"^\s*内部资料.*严禁外传.*$",
    r"^\s*\d{4}-\d{2}-\d{2}\s*$",          # 孤立日期行
    r"^\s*[-_=]{5,}\s*$",                   # 分隔线
]

def clean_text(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            lines.append("")
            continue
        if any(re.match(p, s, re.I) for p in NOISE_PATTERNS):
            continue
        lines.append(s)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)          # 多余空行
    text = re.sub(r"[ \t]{2,}", " ", text)          # 多余空格
    text = re.sub(r"(\n\s*){3,}", "\n\n", text)
    return text.strip()
```

> 💡 **页眉页脚、版权声明、页码是 RAG 效果的最大杀手之一**。它们会在每个 chunk 里出现，导致所有 chunk 都"相似"。上线前**抽样看 20 个 chunk**，脏了就回去改清洗。

### 4.5 PDF 加载的坑

```python
from langchain_community.document_loaders import PyPDFLoader

def load_pdf(path: str) -> str:
    loader = PyPDFLoader(path)
    pages = loader.load()
    text = "\n\n".join(p.page_content for p in pages)

    # 中文 PDF 常见问题：字间多空格
    cjk_space = len(re.findall(r"[一-鿿]\s[一-鿿]", text))
    if cjk_space > len(text) * 0.05:
        text = re.sub(r"(?<=[一-鿿])\s+(?=[一-鿿])", "", text)
    return text
```

| PDF 问题 | 表现 | 处理 |
| :--- | :--- | :--- |
| 扫描件 | 提取出空内容 | OCR（PaddleOCR） |
| 双栏排版 | 文字顺序错乱 | 用 `unstructured` 或版面分析 |
| 表格 | 变成一堆数字 | 单独抽表 + LLM 转 Markdown |
| 字间空格 | "员 工 手 册" | 上面的正则修复 |
| 页眉页脚 | 每页重复 | 跨页去重 |

> ⚠️ **扫描件占比超过 5% 就要上 OCR**，否则会有一批文档"检索不到但你也查不出原因"。

### 4.6 元数据增强

**在切分之前，给每一段补上"它属于什么"**。这能显著提升召回：

```python
def enrich_title(doc: RawDoc) -> str:
    """把文档标题和路径拼到正文开头，让每个 chunk 自带上下文。"""
    return f"# {doc.title}\n\n{doc.content}"
```

> 💡 **这是"Contextual Retrieval"的简化版**。完整版是用 LLM 给每个 chunk 生成一句"这段在讲什么"，但成本高。**标题前缀性价比最高。**

---

## 五、切分与索引：让文档变得可检索 ⭐⭐

### 5.1 切分策略

```python
# app/ingest/splitter.py
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter,
)

MD_HEADERS = [
    ("#", "h1"), ("##", "h2"), ("###", "h3"),
]

def split_doc(doc: RawDoc) -> list[dict]:
    """按 Markdown 标题切 -> 超长再按字符切 -> 附完整元数据。"""
    # ① 按标题切，保留层级
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=MD_HEADERS, strip_headers=False,
    )
    sections = header_splitter.split_text(doc.content)

    # ② 超长的再按字符切
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=["\n\n", "\n", "。", "；", "，", " ", ""],
        length_function=len,
    )

    chunks = []
    for sec in sections:
        path = " > ".join(
            v for k, v in sec.metadata.items() if k in ("h1", "h2", "h3") and v
        )
        prefix = f"【文档】{doc.title}"
        if path:
            prefix += f"【章节】{path}"

        for i, piece in enumerate(text_splitter.split_text(sec.page_content)):
            if len(piece.strip()) < 30:            # 太短，丢弃
                continue
            chunks.append({
                "chunk_id": f"{doc.doc_id}#{len(chunks)}",
                "doc_id": doc.doc_id,
                "title": doc.title,
                "section": path,
                "content": f"{prefix}\n\n{piece}",
                "raw_content": piece,
                "url": doc.url,
                "updated_at": doc.updated_at,
                "acl": doc.acl,
                "source": doc.source,
                "tags": doc.tags,
                "content_hash": doc.content_hash,
            })
    return chunks
```

### 5.2 参数怎么定

| 文档类型 | chunk_size | overlap |
| :--- | :--- | :--- |
| 制度条款（条目式） | 300–500 | 50 |
| 操作手册（步骤式） | 500–800 | 100 |
| 产品说明（叙述式） | 400–600 | 80 |
| FAQ | 按问答对切，不切 | 0 |

> 💡 **不要迷信固定值**。**先跑 20 个真实问题，看检索出来的 chunk 是否"完整表达了意思"**——如果 chunk 被切断在半句话，就调大 overlap 或用语义切分。

### 5.3 建库

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE kb_chunks (
    chunk_id     TEXT PRIMARY KEY,
    doc_id       TEXT NOT NULL,
    title        TEXT NOT NULL,
    section      TEXT,
    content      TEXT NOT NULL,
    raw_content  TEXT NOT NULL,
    url          TEXT,
    source       TEXT,
    tags         TEXT[],
    acl          TEXT[] NOT NULL DEFAULT '{}',
    updated_at   TIMESTAMPTZ,
    content_hash TEXT,
    tsv          tsvector,
    embedding    vector(1024)
);

CREATE INDEX idx_chunks_embedding ON kb_chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);
CREATE INDEX idx_chunks_tsv ON kb_chunks USING gin (tsv);
CREATE INDEX idx_chunks_acl ON kb_chunks USING gin (acl);
CREATE INDEX idx_chunks_doc ON kb_chunks (doc_id);
```

```python
# scripts/build_index.py
import psycopg
from pgvector.psycopg import register_vector
from langchain_huggingface import HuggingFaceEmbeddings

embedder = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
)


def index_chunks(chunks: list[dict], conn):
    register_vector(conn)
    texts = [c["content"] for c in chunks]
    vectors = embedder.embed_documents(texts)

    with conn.cursor() as cur:
        for c, v in zip(chunks, vectors):
            cur.execute("""
                INSERT INTO kb_chunks
                    (chunk_id, doc_id, title, section, content, raw_content,
                     url, source, tags, acl, updated_at, content_hash, tsv, embedding)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        to_tsvector('simple', %s), %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    raw_content = EXCLUDED.raw_content,
                    tsv = EXCLUDED.tsv,
                    embedding = EXCLUDED.embedding,
                    updated_at = EXCLUDED.updated_at,
                    content_hash = EXCLUDED.content_hash
            """, (c["chunk_id"], c["doc_id"], c["title"], c["section"], c["content"],
                  c["raw_content"], c["url"], c["source"], c["tags"], c["acl"],
                  c["updated_at"], c["content_hash"], c["raw_content"], v))
    conn.commit()
```

> ⚠️ **`to_tsvector('simple', ...)` 对中文是"按字切"**，效果一般。生产上装 `zhparser` 或 `pg_jieba` 扩展做中文分词，效果提升明显。
> ```sql
> CREATE TEXT SEARCH CONFIGURATION zh (PARSER = zhparser);
> ALTER TEXT SEARCH CONFIGURATION zh ADD MAPPING FOR n,v,a,i,e,l WITH simple;
> -- 建索引时用 to_tsvector('zh', ...)
> ```

### 5.4 嵌入模型选择

| 模型 | 维度 | 中文 | 说明 |
| :--- | :--- | :--- | :--- |
| `BAAI/bge-m3` | 1024 | ⭐⭐⭐ | **推荐**，多语言、支持长文本 |
| `BAAI/bge-large-zh-v1.5` | 1024 | ⭐⭐⭐ | 中文专用，快 |
| `text-embedding-3-small` | 1536 | ⭐⭐ | OpenAI，需外网 |
| `m3e-base` | 768 | ⭐⭐ | 轻量 |

**BGE 系列有查询指令要求**：

```python
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："
query_vec = embedder.embed_query(QUERY_INSTRUCTION + user_query)
```

> ⚠️ **建库和查询必须用同一个模型**。换模型 = 重建索引。**把模型名和维度写进表结构或配置，避免混用。**

---

## 六、检索层：混合检索 + 重排 ⭐⭐

### 6.1 混合检索实现

```python
# app/rag/retrieve.py
import asyncio, psycopg
from pgvector.psycopg import register_vector

RRF_K = 60


def vector_search(conn, query_vec, user_acls: list[str], k=30) -> list[tuple[str, int]]:
    """返回 [(chunk_id, rank), ...]，rank 从 1 开始。"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT chunk_id
            FROM kb_chunks
            WHERE acl && %s                       -- 数组重叠：有交集即可见
            ORDER BY embedding <=> %s
            LIMIT %s
        """, (user_acls, query_vec, k))
        return [(r[0], i + 1) for i, r in enumerate(cur.fetchall())]


def keyword_search(conn, query: str, user_acls: list[str], k=30) -> list[tuple[str, int]]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT chunk_id
            FROM kb_chunks
            WHERE acl && %s
              AND tsv @@ plainto_tsquery('simple', %s)
            ORDER BY ts_rank(tsv, plainto_tsquery('simple', %s)) DESC
            LIMIT %s
        """, (user_acls, query, query, k))
        return [(r[0], i + 1) for i, r in enumerate(cur.fetchall())]


def rrf_fuse(*ranked_lists, k=RRF_K) -> list[str]:
    """Reciprocal Rank Fusion：把多路结果的排名融合。"""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for cid, rank in ranked:
            scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)


async def hybrid_retrieve(conn, embedder, query: str, user_acls: list[str],
                          top_k=40) -> list[dict]:
    qv = embedder.embed_query(QUERY_INSTRUCTION + query)

    vec_ranked, kw_ranked = await asyncio.gather(
        asyncio.to_thread(vector_search, conn, qv, user_acls, top_k),
        asyncio.to_thread(keyword_search, conn, query, user_acls, top_k),
    )

    fused = rrf_fuse(vec_ranked, kw_ranked)[:top_k]

    with conn.cursor() as cur:
        cur.execute("""
            SELECT chunk_id, doc_id, title, section, raw_content, url, updated_at
            FROM kb_chunks WHERE chunk_id = ANY(%s)
        """, (fused,))
        rows = {r[0]: r for r in cur.fetchall()}

    return [
        {"chunk_id": cid, "doc_id": rows[cid][1], "title": rows[cid][2],
         "section": rows[cid][3], "content": rows[cid][4], "url": rows[cid][5],
         "updated_at": rows[cid][6]}
        for cid in fused if cid in rows
    ]
```

### 6.2 RRF 为什么有效

```text
向量检索：  A B C D E
关键词检索：C A F G B
─────────────────────
RRF 融合：  C A B D E F G
```

**它不关心分数绝对值，只看排名**。所以两路完全不同的打分体系也能融合。

### 6.2.5 查询改写：中文 RAG 里性价比最高的一步

**用户说的话和文档里写的字，经常一个都对不上。**

| 用户说 | 文档里写 |
| :--- | :--- |
| 「出差住酒店能报多少」 | 「住宿标准」「住宿费按职级…」 |
| 「P7 的薪资范围」 | 「薪酬带宽（月度）」 |
| 「年休假怎么算」 | 「年假」 |
| 「这个能退吗」 | 「七天无理由退货」 |

**三种做法，成本从低到高**：

| 做法 | 成本 | 效果 | 适用 |
| :--- | :--- | :--- | :--- |
| **同义词表**（`str.replace`） | 0 | 中文场景里意外地管用 | 冷启动必做 |
| **query 改写模型**（小模型扩写/同义改写） | 1 次小模型调用 | 好，但会增加延迟和不确定性 | 有数据后 |
| **嵌入模型微调 / 领域模型** | 高 | 最好 | 语料规模大且稳定 |

**从同义词表开始**，成本几乎为零，先把明显的问题消掉：

```python
# app/rag/rewrite.py
SYNONYMS = [
    ("薪资", "薪酬"), ("工资", "薪酬"),
    ("酒店", "住宿"), ("能报", "报销"), ("报多少", "报销"),
    ("年休假", "年假"),
]

def normalize_query(q: str) -> str:
    for a, b in SYNONYMS:
        q = q.replace(a, b)
    return q
```

**这张表从哪来**：从**真实搜不到的日志**里挖。跑一周，把「用户问了、但判成拒答」的 query 捞出来，
人工看 100 条，能总结出十几条同义关系。**补一次表，比换一个更大的嵌入模型见效快。**

> 💡 **同义词表要同时作用于向量检索和关键词检索**，否则两路召回的候选集不一致，RRF 融合会偏向一路。

### 6.3 重排

```python
# app/rag/rerank.py
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)

def rerank(query: str, docs: list[dict], top_n: int = 5) -> list[dict]:
    if not docs:
        return []
    pairs = [(query, d["content"]) for d in docs]
    scores = reranker.predict(pairs)
    for d, s in zip(docs, scores):
        d["rerank_score"] = float(s)
    ranked = sorted(docs, key=lambda d: d["rerank_score"], reverse=True)
    return ranked[:top_n]
```

> ⚠️ **CrossEncoder 很慢**（GPU 上 40 条约 200–500ms）。**先用向量检索把 40 条压到 40，再重排到 5**，不要直接对全库重排。

### 6.4 相关性阈值：拒答的依据

```python
MIN_RERANK_SCORE = 0.3      # 需要按你的模型和语料实测校准

def is_relevant(docs: list[dict]) -> bool:
    if not docs:
        return False
    return docs[0]["rerank_score"] >= MIN_RERANK_SCORE
```

**怎么定这个阈值**：

```text
1. 准备 100 个问题：50 个"文档里有答案"，50 个"文档里没有"
2. 对每题取 top1 的 rerank_score
3. 画分布，找分开两组的阈值
4. 用"宁可拒答，不要瞎答"的原则偏保守
```

> 💡 **这个阈值是知识库 Agent 最重要的一个数字**。它决定了"该说不知道的时候说不说"。
> **没有阈值 = 100% 会瞎答。**

### 6.5 检索的完整链路

```python
async def retrieve(conn, embedder, query, user_acls,
                   top_k=40, top_n=5) -> tuple[list[dict], bool]:
    q = normalize_query(query)                       # ① 查询改写（同义词）
    docs = await hybrid_retrieve(conn, embedder, q, user_acls, top_k)  # ② 混合召回（ACL 在 SQL 里）
    docs = rerank(q, docs, top_n)                    # ③ 重排
    relevant = is_relevant(docs)                     # ④ 阈值判定
    return docs, relevant
```

**一句话记住顺序**：**改写 → 召回 → 重排 → 判定**。前一步错了，后面全都白搭；
判定放在最后，因为只有排过序的分数才有可比性。

---

## 七、回答层：引用、拒答、追问 ⭐⭐

### 7.1 Prompt 设计

```python
# app/rag/generate.py
from langchain_core.prompts import ChatPromptTemplate

SYSTEM = """你是公司内部知识库助手，帮员工查制度、流程、产品信息。

【回答规则】
1. 只依据提供的【资料】回答，不使用资料外的知识。
2. 每个结论后用 [编号] 标注来源，如"年假 5 天[1]"。
3. 资料不足以回答时，明确说"知识库里没有找到相关信息"，并建议咨询哪个部门。
4. 回答控制在 200 字以内；用户要求详细时可展开。
5. 涉及金额、日期、比例，必须原样引用，不要换算或推断。
6. 如果资料相互矛盾，指出矛盾并建议确认最新版本。
7. 不要提及"资料""文档片段"等内部词汇，直接回答问题。

【资料】
{docs}
"""

USER = "{question}"


def format_docs(docs: list[dict]) -> str:
    lines = []
    for i, d in enumerate(docs, 1):
        updated = d["updated_at"].strftime("%Y-%m-%d") if d["updated_at"] else "未知"
        lines.append(
            f"[{i}] 《{d['title']}》— {d['section'] or '正文'}（更新于 {updated}）\n"
            f"{d['content']}"
        )
    return "\n\n---\n\n".join(lines)


prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", USER)])
```

### 7.2 引用校验

**模型会编造引用编号。必须在代码里校验。**

```python
import re

CITE_RE = re.compile(r"\[(\d+)\]")

def validate_citations(answer: str, docs: list[dict]) -> tuple[str, list[dict]]:
    """校验并修正引用；返回 (修正后回答, 实际用到的来源)。"""
    valid = {str(i) for i in range(1, len(docs) + 1)}
    used: set[str] = set()

    def fix(m):
        n = m.group(1)
        if n in valid:
            used.add(n)
            return m.group(0)
        return ""                       # 无效引用直接删掉

    cleaned = CITE_RE.sub(fix, answer)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    sources = [docs[int(n) - 1] for n in sorted(used, key=int)]
    return cleaned, sources
```

> ⚠️ **模型引用编号出错非常常见**（尤其是资料多时）。**不校验的引用比没有引用更危险**——用户会点开一个不相关的链接，然后不再信任系统。

### 7.3 拒答

```python
NO_ANSWER = """知识库里没有找到与「{q}」直接相关的内容。

建议：
- 换个说法再问一次（例如用制度名称、流程名称）
- 咨询 {dept}
- 如果这份文档应该有，请联系知识库管理员补充"""

DEPT_ROUTING = [
    (("请假", "年假", "考勤", "入职", "离职", "社保", "薪酬"), "HR"),
    (("报销", "发票", "付款", "预算", "财务"), "财务部"),
    (("VPN", "账号", "电脑", "网络", "系统", "权限"), "IT 支持"),
    (("合同", "法务", "合规"), "法务部"),
]


def suggest_dept(q: str) -> str:
    for kws, dept in DEPT_ROUTING:
        if any(k in q for k in kws):
            return dept
    return "相关部门"
```

### 7.4 生成 + 校验的完整流程

```python
async def answer(question: str, docs: list[dict], model) -> dict:
    chain = prompt | model
    resp = await chain.ainvoke({
        "docs": format_docs(docs),
        "question": question,
    })
    text, sources = validate_citations(resp.content, docs)

    if not sources and docs:
        # 模型没引用任何资料 —— 可能没用资料，标记出来
        text = f"{text}\n\n（注：本条回答未引用知识库原文，建议核实）"

    return {
        "answer": text,
        "sources": [
            {"title": s["title"], "section": s["section"], "url": s["url"],
             "updated_at": s["updated_at"].isoformat() if s["updated_at"] else None}
            for s in sources
        ],
        "tokens": resp.usage_metadata,
    }
```

### 7.5 时效性提示

```python
from datetime import datetime, timedelta

def freshness_note(docs: list[dict]) -> str | None:
    oldest = min((d["updated_at"] for d in docs if d["updated_at"]), default=None)
    if not oldest:
        return None
    if datetime.now(oldest.tzinfo) - oldest > timedelta(days=365):
        return f"⚠️ 引用内容最早更新于 {oldest:%Y-%m-%d}，可能已过时，建议确认。"
    return None
```

> 💡 **企业知识库最大的信任问题是"过期文档"**。**主动标注时效比事后解释有用得多。**

---

## 八、Agent 化：从问答升级到办事 ⭐⭐

### 8.1 为什么要 Agent 化

**纯 RAG 只能回答"怎么做"，不能帮人"真的做"。**

```text
用户：我要请三天年假，怎么操作？
V1：年假请假流程是：登录 OA → 请假申请 → 选择年假 → 提交直属主管审批… [1]
V2：年假请假流程是…[1]
    需要我帮你打开请假页吗？（点这里）
```

### 8.2 加两个工具

```python
# app/tools/hr_tools.py
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
import httpx

@tool
async def get_leave_balance(config: RunnableConfig) -> dict:
    """查询当前用户的年假余额、已用天数、剩余天数。

    用户询问"我还有几天年假""年假还剩多少"时使用。
    """
    uid = config["configurable"]["user_id"]
    async with httpx.AsyncClient(timeout=8) as c:
        r = await c.get(f"{HR_API}/leave/balance", headers={"X-User-Id": uid})
    if r.status_code != 200:
        return {"success": False, "error": "HR 系统暂时不可用"}
    d = r.json()
    return {"success": True, "annual_total": d["annual"],
            "annual_used": d["used"], "annual_left": d["left"]}


@tool
async def get_leave_policy(leave_type: str = "年假") -> str:
    """查询请假政策原文（天数规则、审批要求）。"""
    docs = await retrieve_sync(leave_type + " 请假 政策", top_n=3)
    return format_docs(docs)


@tool
def open_leave_form() -> str:
    """生成请假页面链接，引导用户去 OA 提交申请（不会自动提交）。"""
    return ("请假申请入口：https://oa.example.com/leave/new\n"
            "（请自行填写并提交，提交后会发送给直属主管审批）")
```

> ⚠️ **第一版不要让 Agent"代提交请假"**。**只生成链接、只做查询，不做写操作**——写操作要么需要审批（第 08 篇），要么先不做。

### 8.3 主图

```python
# app/graph/qa_graph.py
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from langchain_core.messages import AnyMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    query: str
    rewritten_query: str
    docs: list[dict]
    relevant: bool
    answer: str
    sources: list[dict]
    mode: str                       # chat | kb | action


class Intent(BaseModel):
    mode: Literal["chat", "kb", "action"] = Field(
        description="chat=闲聊问候, kb=知识问答, action=需要查询或操作业务系统"
    )


# ---------- 节点 ----------

async def classify(state: State) -> dict:
    q = state["messages"][-1].content
    r = await small_model.with_structured_output(Intent).ainvoke(
        f"判断用户意图。\n"
        f"- chat：打招呼、感谢、与公司业务无关的闲聊\n"
        f"- kb：询问制度、流程、产品说明等文档内容\n"
        f"- action：需要查询个人数据（如年假余额、订单状态）或引导操作\n"
        f"用户消息：{q}"
    )
    return {"mode": r.mode, "query": q}


def route_intent(state: State) -> Literal["chat", "kb", "action"]:
    return state["mode"]


async def chat_node(state: State) -> dict:
    r = await small_model.ainvoke(state["messages"])
    return {"answer": r.content, "sources": []}


async def rewrite(state: State) -> dict:
    """多轮指代消解：'那病假呢' -> '病假有多少天'。"""
    if len(state["messages"]) <= 1:
        return {"rewritten_query": state["query"]}

    history = "\n".join(
        f"{m.type}: {m.content}" for m in state["messages"][-5:] if m.content
    )
    r = await small_model.ainvoke(
        f"根据对话历史，把用户最后一个问题改写成一个独立的、完整的问题。"
        f"只输出改写后的问题，不要解释。\n\n历史：\n{history}\n\n最后一个问题：{state['query']}"
    )
    return {"rewritten_query": r.content.strip()}


async def retrieve_node(state: State, config) -> dict:
    acls = config["configurable"]["acls"]
    docs, relevant = await retrieve(
        conn, embedder, state["rewritten_query"], acls, top_k=40, top_n=5
    )
    return {"docs": docs, "relevant": relevant}


def route_relevance(state: State) -> Literal["generate", "no_answer"]:
    return "generate" if state["relevant"] else "no_answer"


async def generate_node(state: State) -> dict:
    res = await answer(state["query"], state["docs"], model)
    return {"answer": res["answer"], "sources": res["sources"],
            "messages": [AIMessage(res["answer"])]}


def no_answer_node(state: State) -> dict:
    q = state["query"]
    msg = NO_ANSWER.format(q=q, dept=suggest_dept(q))
    return {"answer": msg, "sources": [], "messages": [AIMessage(msg)]}


async def action_node(state: State, config) -> dict:
    agent = kb_action_agent          # create_agent，tools=[get_leave_balance, get_leave_policy, open_leave_form]
    r = await agent.ainvoke(
        {"messages": state["messages"]},
        config={"configurable": {"user_id": config["configurable"]["user_id"]}},
    )
    last = r["messages"][-1]
    return {"answer": last.content, "messages": [last]}


# ---------- 组图 ----------

def build(saver):
    b = StateGraph(State)
    b.add_node("classify", classify)
    b.add_node("chat", chat_node)
    b.add_node("rewrite", rewrite)
    b.add_node("retrieve", retrieve_node)
    b.add_node("generate", generate_node)
    b.add_node("no_answer", no_answer_node)
    b.add_node("action", action_node)

    b.add_edge(START, "classify")
    b.add_conditional_edges("classify", route_intent,
                            {"chat": "chat", "kb": "rewrite", "action": "action"})
    b.add_edge("chat", END)
    b.add_edge("rewrite", "retrieve")
    b.add_conditional_edges("retrieve", route_relevance,
                            {"generate": "generate", "no_answer": "no_answer"})
    b.add_edge("generate", END)
    b.add_edge("no_answer", END)
    b.add_edge("action", END)
    return b.compile(checkpointer=saver)
```

### 8.4 图长什么样

```text
START → classify ─┬─ chat → END
                  ├─ action → END
                  └─ rewrite → retrieve ─┬─ generate → END
                                         └─ no_answer → END
```

> 💡 **注意这个图里"没有 Agent 循环"**（除了 action 分支）。**这是有意的**——知识问答路径越确定，越稳定、越便宜、越可测。

---

## 九、权限：不同人能看不同文档 ⭐⭐

### 9.1 问题

**工资制度、组织架构、高管会议纪要不能全员可见。**

如果检索时不过滤，模型可能把不该看的内容说出来。**这是企业知识库最容易出的事故。**

### 9.2 设计

**① 文档打标签**（建索引时）：

```python
ACL_PUBLIC = "all"
ACL_HR = "dept:HR"
ACL_FINANCE = "dept:FINANCE"
ACL_MGMT = "level:manager"
```

```python
# 从 Confluence 标签映射
LABEL_TO_ACL = {
    "hr-only": ["dept:HR", "level:hr"],
    "finance-only": ["dept:FINANCE"],
    "management": ["level:manager"],
    "public": ["all"],
}

def extract_acl_from_labels(labels: dict) -> list[str]:
    acls = set()
    for l in labels.get("results", []):
        acls.update(LABEL_TO_ACL.get(l["name"], []))
    return list(acls) or ["all"]
```

**② 用户算 ACL**（请求时）：

```python
# app/security/acl.py
def user_acls(user: dict) -> list[str]:
    acls = ["all"]
    for d in user.get("departments", []):
        acls.append(f"dept:{d}")
    if user.get("level") in ("manager", "director"):
        acls.append("level:manager")
    if user.get("dept") == "HR":
        acls.append("level:hr")
    return acls
```

**③ 检索时过滤**（SQL 层）：

```sql
WHERE acl && %s        -- 数组重叠
```

> ⚠️ **必须在 SQL 层过滤，不能在应用层"取回再筛"**。后者会导致：结果数量不足、排序失真，甚至日志泄露。

### 9.3 三道防线

| 层 | 做法 |
| :--- | :--- |
| **检索层** | SQL `WHERE acl && user_acls` |
| **生成层** | Prompt 声明"只回答资料中内容" |
| **输出层** | 检测回答里是否出现受限关键词（兜底） |

```python
RESTRICTED_KEYWORDS = ["薪资表", "组织架构图", "董事会"]

def output_guard(answer: str, user: dict) -> str:
    if "level:manager" in user_acls(user):
        return answer
    for k in RESTRICTED_KEYWORDS:
        if k in answer:
            return "抱歉，该问题涉及受限信息，请咨询对应部门。"
    return answer
```

### 9.4 验证方法

**必须有自动化测试**：

```python
@pytest.mark.asyncio
async def test_employee_cannot_see_salary_doc():
    # 用普通员工身份问薪资相关
    r = await graph.ainvoke(
        {"messages": [("user", "P7 的薪资范围是多少")]},
        {"configurable": {"thread_id": "t-acl-1", "user_id": "emp001",
                          "acls": ["all", "dept:RD"]}},
    )
    assert "薪资" not in r["sources"] or not r["sources"]
    assert "没有找到" in r["answer"] or "受限" in r["answer"]

@pytest.mark.asyncio
async def test_hr_can_see_salary_doc():
    r = await graph.ainvoke(
        {"messages": [("user", "P7 的薪资范围是多少")]},
        {"configurable": {"thread_id": "t-acl-2", "user_id": "hr001",
                          "acls": ["all", "dept:HR", "level:hr"]}},
    )
    assert r["sources"]           # 有引用
```

> 💡 **权限测试用例要放进 CI**。权限回退是最严重的事故类型，不能靠人工回归。

---

## 十、会话与追问

### 10.1 多轮指代

```text
用户：年假有多少天？
助手：入职满 1 年 5 天…[1]
用户：那病假呢？        ← 需要改写为"病假有多少天"
助手：…
```

**改写节点（第七节 `rewrite`）解决这个问题。**

**代价**：多一次模型调用（约 300 token、0.5s）。
**优化**：只在"有历史 且 问题很短（< 15 字）或含指代词"时改写。

```python
PRONOUNS = ("那", "这个", "它", "呢", "还有", "另外", "同样")

def need_rewrite(history_len: int, q: str) -> bool:
    if history_len <= 1:
        return False
    if len(q) <= 15:
        return True
    return any(p in q for p in PRONOUNS)
```

### 10.2 上下文管理

**知识问答不需要携带全部历史**，只需要最近 3 轮 + 上一轮的检索主题。

```python
def build_rewrite_context(messages, n=3):
    return messages[-n * 2:] if len(messages) > n * 2 else messages
```

### 10.3 话题切换

```python
async def is_topic_switch(prev_q: str, cur_q: str) -> bool:
    r = await small_model.with_structured_output(SwitchCheck).ainvoke(
        f"上一个问题：{prev_q}\n当前问题：{cur_q}\n"
        f"当前问题是否在延续上一个话题（追问细节、换角度问同一主题）？"
    )
    return not r.follow_up
```

**话题切换时清空 `rewrite` 的上下文**，避免"那病假呢"被错误地结合到无关话题。

---

## 十一、增量同步与文档治理

### 11.1 增量同步

```python
# scripts/sync_docs.py
async def sync(conn):
    docs = load_all_sources()                  # 所有源
    stats = {"new": 0, "updated": 0, "deleted": 0, "skipped": 0}

    seen_ids = set()
    for doc in docs:
        seen_ids.add(doc.doc_id)

        with conn.cursor() as cur:
            cur.execute("SELECT content_hash FROM kb_docs WHERE doc_id=%s", (doc.doc_id,))
            row = cur.fetchone()

        if row and row[0] == doc.content_hash:
            stats["skipped"] += 1
            continue

        chunks = split_doc(doc)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM kb_chunks WHERE doc_id=%s", (doc.doc_id,))
            cur.execute("""
                INSERT INTO kb_docs (doc_id, title, url, content_hash, updated_at)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    title=EXCLUDED.title, url=EXCLUDED.url,
                    content_hash=EXCLUDED.content_hash, updated_at=EXCLUDED.updated_at
            """, (doc.doc_id, doc.title, doc.url, doc.content_hash, doc.updated_at))
        index_chunks(chunks, conn)

        stats["updated" if row else "new"] += 1

    # 删除已消失的文档
    with conn.cursor() as cur:
        cur.execute("SELECT doc_id FROM kb_docs")
        for (did,) in cur.fetchall():
            if did not in seen_ids:
                cur.execute("DELETE FROM kb_chunks WHERE doc_id=%s", (did,))
                cur.execute("DELETE FROM kb_docs WHERE doc_id=%s", (did,))
                stats["deleted"] += 1
    conn.commit()
    return stats
```

### 11.2 索引重建的平滑切换

**重建整个索引时，不能停服务。**

```python
async def rebuild_safely():
    """建到新表 -> 验证 -> 原子切换视图。"""
    # 1. 建新表 kb_chunks_new
    # 2. 全量导入
    # 3. 抽样验证（跑 20 个评测题，对比通过率）
    # 4. ALTER VIEW kb_chunks_current AS SELECT * FROM kb_chunks_new
    # 5. 旧表保留 7 天后删除
```

> 💡 **生产上建议用"读视图 + 物理表名带版本"**，切换时只改视图定义，秒级完成。

### 11.3 文档治理

**RAG 系统最大的长期问题是"文档质量"，不是模型。**

| 问题 | 检测 | 处理 |
| :--- | :--- | :--- |
| 过期文档 | `updated_at` > 1 年 | 标注、提醒 owner |
| 重复文档 | 相似度聚类 | 合并 |
| 无结构文档 | 无标题、单段超长 | 提示整改 |
| 从未被检索 | 统计 chunk 命中次数 | 评估是否保留 |
| 高频检索但低分 | 检索命中但 rerank 分低 | 内容可能没答到点上 |

```sql
-- 高频问题，但没有好答案 → 说明缺文档
SELECT query, COUNT(*) AS asks, AVG(top1_score) AS avg_score
FROM qa_logs
WHERE created_at > now() - interval '30 days'
GROUP BY query
HAVING COUNT(*) > 5 AND AVG(top1_score) < 0.4
ORDER BY asks DESC;
```

> 💡 **这张表是"该写什么文档"的最佳来源**——用户反复问但答不好的，就是要补的。

### 11.4 反馈闭环

```python
@app.post("/feedback")
def feedback(body: FeedbackReq, user=Depends(current_user)):
    db.insert("qa_feedback", {
        "trace_id": body.trace_id, "user_id": user.id,
        "helpful": body.helpful, "comment": body.comment,
    })
    # 不帮且有问题 → 进待改进队列
    if not body.helpful:
        db.insert("qa_improve_queue", {"trace_id": body.trace_id, "status": "open"})
```

**每周看两件事**：

1. 踩数最高的问题 → 加评测用例 + 补文档
2. 点踩的具体回答 → 看是检索问题还是生成问题

---

## 十二、评测：怎么知道它到底准不准

### 12.1 三层指标

| 层 | 指标 | 目标 |
| :--- | :--- | :--- |
| **检索** | Recall@5、MRR | Recall@5 > 0.85 |
| **生成** | 忠实度（faithfulness）、相关性 | 忠实度 > 0.9 |
| **端到端** | 答案正确率、拒答正确率 | 正确率 > 0.85 |

### 12.2 评测集

```json
[
  {
    "id": "hr_001",
    "question": "入职满一年有几天年假？",
    "expected_answer_contains": ["5 天"],
    "expected_sources": ["员工手册"],
    "must_have_citation": true
  },
  {
    "id": "hr_002",
    "question": "年假可以累积到下一年吗？",
    "expected_answer_contains": ["可以", "不超过", "结转"],
    "expected_sources": ["员工手册"]
  },
  {
    "id": "neg_001",
    "question": "公司有食堂吗？",
    "answerable": false,
    "expected_answer_contains": ["没有找到"]
  }
]
```

> 💡 **必须有 20–30% 的"不可回答"用例**。否则你永远测不出拒答能力，上线后会被瞎答坑。

### 12.3 检索评测

```python
def eval_retrieval(cases, retriever):
    recalls, mrrs = [], []
    for c in cases:
        if not c.get("expected_sources"):
            continue
        docs = retriever(c["question"], top_n=5)
        hit_ranks = [i + 1 for i, d in enumerate(docs)
                     if d["title"] in c["expected_sources"]]
        recalls.append(1.0 if hit_ranks else 0.0)
        mrrs.append(1.0 / hit_ranks[0] if hit_ranks else 0.0)
    return {"recall@5": sum(recalls) / len(recalls),
            "mrr": sum(mrrs) / len(mrrs)}
```

### 12.4 生成评测

**忠实度（faithfulness）**：回答是否有资料支撑，有没有编造。

```python
class Faithfulness(BaseModel):
    score: int = Field(ge=1, le=5)
    unsupported_claims: list[str]

FAITH_PROMPT = """判断回答中的每一项陈述是否能在【资料】中找到依据。

【资料】
{docs}

【回答】
{answer}

输出：score（5=全部有依据，1=大量编造），以及无法找到依据的陈述列表。
"""

def eval_faithfulness(answer, docs) -> Faithfulness:
    return judge_model.with_structured_output(Faithfulness).invoke(
        FAITH_PROMPT.format(docs=format_docs(docs), answer=answer)
    )
```

### 12.5 拒答评测

```python
def eval_refusal(cases, graph):
    tp = fp = fn = tn = 0
    for c in cases:
        r = graph.invoke(...)
        refused = "没有找到" in r["answer"] or "受限" in r["answer"]
        answerable = c.get("answerable", True)

        if answerable and not refused: tp += 1
        elif answerable and refused:   fn += 1     # 该答没答
        elif not answerable and refused: tn += 1
        else: fp += 1                              # 不该答却答了（最严重）

    return {"答案覆盖率": tp / (tp + fn), "拒答准确率": tn / (tn + fp),
            "误拒率": fn / (tp + fn), "瞎答率": fp / (tn + fp)}
```

> ⚠️ **"瞎答率"（不该答却答了）是最关键的指标**。企业场景里，错误的权威回答比"不知道"危险得多。**目标是瞎答率 < 5%，宁可误拒。**

### 12.6 基线对比表

| 版本 | 改动 | Recall@5 | 正确率 | 瞎答率 | 平均延迟 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| v1.0 | 纯向量，chunk 800 | 0.71 | 68% | 18% | 2.1s |
| v1.1 | + 关键词混合 | 0.83 | 79% | 12% | 2.3s |
| v1.2 | + rerank | **0.89** | **86%** | **7%** | 2.8s |
| v1.3 | + 标题前缀 | 0.91 | 88% | 5% | 2.8s |
| v1.4 | chunk 500 + 清洗 | 0.93 | 90% | 4% | 2.7s |

**这张表就是项目汇报最有力的材料。** 每一行改动都有数字支撑。

---

## 十三、接口与前端

### 13.1 流式接口

```python
# app/api/chat.py
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

app = FastAPI()

class ChatReq(BaseModel):
    message: str
    thread_id: str | None = None


@app.post("/chat/stream")
async def chat_stream(req: ChatReq, user=Depends(current_user)):
    thread_id = req.thread_id or f"{user['tenant']}:{user['id']}:web:{uuid4().hex}"
    cfg = {"configurable": {
        "thread_id": thread_id,
        "user_id": user["id"],
        "acls": user_acls(user),
    }, "recursion_limit": 10}

    async def gen():
        yield sse({"type": "meta", "thread_id": thread_id})
        try:
            async for ev in graph.astream_events(
                {"messages": [("user", req.message)]}, cfg, version="v2"
            ):
                k = ev["event"]
                if k == "on_chat_model_stream":
                    chunk = ev["data"]["chunk"].content
                    if chunk:
                        yield sse({"type": "token", "text": chunk})
                elif k == "on_chain_end" and ev["name"] in ("generate", "no_answer"):
                    out = ev["data"]["output"]
                    if isinstance(out, dict) and "sources" in out:
                        yield sse({"type": "sources", "sources": out["sources"]})
            yield sse({"type": "done"})
        except Exception as e:
            logger.exception("chat failed")
            yield sse({"type": "error", "message": "服务暂时不可用，请稍后重试"})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


def sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"
```

### 13.2 消息协议

```text
data: {"type":"meta","thread_id":"t1:u1:web:abc"}
data: {"type":"token","text":"入职满"}
data: {"type":"token","text":"一年有 5 天年假"}
data: {"type":"token","text":"[1]。"}
data: {"type":"sources","sources":[{"title":"员工手册","section":"假期 > 年假","url":"...","updated_at":"2026-03-01"}]}
data: {"type":"done"}
```

> 💡 **`sources` 单独一个事件**，前端可以在回答下方渲染"参考资料"卡片，比塞在文本里好。

### 13.3 前端要点

```text
① 首字要快：先显示"正在检索知识库…"
② 引用要可点击：点击跳到原文位置
③ 要显示更新日期：让用户判断时效
④ 要有点踩：收集反馈
⑤ 要能开新会话：避免上下文混乱
⑥ 拒答要有"下一步"：给出部门/联系方式
```

### 13.4 与 IM 集成

```python
# 企业微信/飞书机器人 webhook
@app.post("/im/webhook")
async def im_webhook(body: dict):
    question = body["text"]["content"]
    user_id = body["user_id"]

    r = await graph.ainvoke(
        {"messages": [("user", question)]},
        {"configurable": {"thread_id": f"im:{user_id}", "user_id": user_id,
                          "acls": user_acls(load_user(user_id))}},
    )

    # IM 里没有 Markdown 链接渲染，用纯文本 + 链接行
    text = r["answer"]
    if r["sources"]:
        text += "\n\n参考：\n" + "\n".join(
            f"· {s['title']} {s['url'] or ''}" for s in r["sources"][:3]
        )
    return {"msgtype": "text", "text": {"content": text}}
```

---

## 十四、部署与运维

### 14.1 部署拓扑

```text
              ┌──────────────┐
   用户 ─────►│  Nginx/ALB   │
              └──────┬───────┘
                     ▼
           ┌──────────────────┐
           │  kb-agent (x3)   │  FastAPI + uvicorn
           └────┬────────┬────┘
                │        │
      ┌─────────▼──┐  ┌──▼─────────┐
      │ PostgreSQL │  │ Redis      │
      │ + pgvector │  │ 缓存/限流   │
      └────────────┘  └────────────┘
                │
      ┌─────────▼─────────────┐
      │ 嵌入/重排服务 (GPU)    │
      │ 独立部署, HTTP 调用    │
      └───────────────────────┘
```

### 14.2 为什么嵌入/重排要独立部署

| 理由 | 说明 |
| :--- | :--- |
| GPU 资源贵 | 只给需要的服务用 |
| 内存占用大 | 模型加载占 2–4GB |
| 独立扩容 | 检索量和大模型调用量不成比例 |
| 复用 | 其他系统也能用 |

```python
# 通过 HTTP 调用嵌入服务
async def embed(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{EMBED_URL}/embed", json={"texts": texts})
    return r.json()["embeddings"]
```

### 14.3 Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir uv && uv pip install --system -r pyproject.toml

COPY app ./app
COPY prompts ./prompts

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 14.4 索引更新任务

```bash
# 每天凌晨增量同步
0 2 * * * cd /app && python scripts/sync_docs.py >> /var/log/kb-sync.log 2>&1
```

**同步任务要有的保护**：

- 加锁（避免并发跑两份）
- 超时（避免挂死）
- 失败告警
- 统计输出（新增/更新/删除数）

### 14.5 监控

| 指标 | 告警阈值 |
| :--- | :--- |
| 拒答率 | > 40% 持续 1 小时（文档或检索出问题） |
| P95 延迟 | > 8s |
| 检索命中为空 | > 30% |
| 索引文档数 | 环比下降 > 10%（同步任务出错） |
| 点踩率 | > 20% |

> 💡 **"拒答率突增"是知识库系统最有价值的告警**——它通常意味着**索引被清空、同步失败、或权限配置出错**。

---

## 十五、上线后的真实问题

### 15.1 六个真实问题

| 问题 | 原因 | 处理 |
| :--- | :--- | :--- |
| "为什么搜不到我刚写的文档？" | 同步是 T+1 | 提供"立即同步"按钮 + 说明延迟 |
| "它说是 5 天，但制度改成了 7 天" | 文档没更新 | 时效提示 + 文档 owner 提醒 |
| "它答的是别的部门的规定" | 部门文档混在一起 | ACL 细化 + 标题带部门 |
| "回答太长了，我只要一句话" | Prompt 没限制长度 | 改 Prompt + 前端可折叠详情 |
| "它说不知道，但明明有" | 用词差异 / 切分切断 | 补同义词 + 调 chunk 参数 |
| "引用点开是首页" | URL 没带锚点 | 用标题锚点或章节级链接 |

### 15.2 冷启动方法

```text
① 先只接 1 个源（如 HR 制度，约 100 篇）
② 找 20 个真实的高频问题
③ 跑通 → 找 10 个种子用户试用 2 周
④ 收集问题 → 补文档、调检索
⑤ 准确率 > 80% 再扩大范围
```

> ⚠️ **不要一开始就接 5 个系统 3000 篇文档**。**"小而准"建立信任，"大而糊"直接失去用户。**

### 15.3 用户预期管理

```text
✅ 首屏说明：「我是知识库助手，可以帮你查制度、流程、产品说明。回答会附原文出处，请以原文为准。」
✅ 拒答时给下一步：「没有找到，建议咨询 HR / 提交工单」
✅ 回答下方：「最后更新 2026-03-01，如有疑问请以最新制度为准」
```

### 15.4 项目汇报怎么写

**用数字，不用形容词。**

```text
❌ "上线了智能知识库问答，大幅提升了效率"
✅ "覆盖 HR/IT/财务 3 类 1200 篇文档，上线 2 个月：
    - 日均 340 次提问
    - 平均响应 2.8 秒（原人工平均 20 分钟）
    - 答案准确率 88%（人工抽检 200 条）
    - HR/IT 重复问题工单下降 52%
    - 单次问答成本 0.008 元"
```

---

## 十六、本章小结与练习

### 核心结论

1. **范围要窄**：先做 3 个系统、1000 篇文档，不要贪多。
2. **混合检索是必选项**：向量管语义，关键词管精确名词和编号。
3. **rerank 是性价比最高的一步**：精度提升明显，成本可控。
4. **相关性阈值决定了会不会瞎答**，必须用真实数据校准，且必须设。
5. **引用要校验**：模型编造引用编号非常常见。
6. **拒答要给出路**：告诉用户找谁，而不是只说"不知道"。
7. **权限过滤在 SQL 层**，三道防线，且必须有自动化测试。
8. **Agent 化要克制**：先只做查询和引导，写操作往后放。
9. **评测必须有"不可回答"用例**，盯住"瞎答率"。
10. **文档治理是长期工程**：用"高频低分问题"反推该写什么文档。

### 动手练习

1. 用 20 篇 Markdown 文档搭一个最小索引，跑通"加载→切分→向量化→检索→回答"。
2. 只用向量检索 vs 向量+关键词+rerank，各跑 30 个问题，对比 Recall@5。
3. 造 20 个"文档里没有答案"的问题，测你的系统瞎答率；然后调阈值降到 10% 以下。
4. 故意让模型引用一个不存在的编号，验证你的校验逻辑能删掉它。
5. 建一个 `dept:FINANCE` 的受限文档，用普通员工身份检索，验证 SQL 过滤生效。
6. 实现增量同步：改一篇文档的 content_hash，验证只重建这一篇。
7. 写 30 条评测用例（含 8 条不可回答），跑出基线表，然后做一次优化对比。
8. 用 `astream_events` 做一个带"正在检索…"和"参考资料卡片"的流式前端。

### 下一篇

[12 - 实战：智能客服工单 Agent](12-实战-智能客服工单Agent.md) —— 从"回答问题"到"处理问题"，涉及工具写操作、审批、多 Agent 和工单闭环。
