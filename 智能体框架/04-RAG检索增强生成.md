# 04 - RAG 检索增强生成

> RAG（Retrieval-Augmented Generation，检索增强生成）是**企业落地占比最高的 AI 应用形态**：让模型基于"你的公司文档"回答问题。
> 它看起来很简单——"查资料再回答"——但**做好极难**。同样的模型、同样的文档，不同团队做出来的效果可能天差地别。
> 本篇从 O 到 1 搭一套可用的 RAG，重点放在**实际项目里真正影响效果的那些决策**上。

---

## 📖 目录

1. [为什么需要 RAG](#一为什么需要-rag)
2. [RAG 的完整链路](#二rag-的完整链路)
3. [文档加载与解析](#三文档加载与解析)
4. [切分（Chunking）⭐⭐](#四切分chunking-)
5. [Embedding 与向量库 ⭐](#五embedding-与向量库-)
6. [检索策略 ⭐⭐](#六检索策略-)
7. [重排（Rerank）⭐⭐](#七重排rerank-)
8. [Prompt 组装与引用溯源 ⭐](#八prompt-组装与引用溯源-)
9. [完整实现](#九完整实现)
10. [评估：怎么知道你的 RAG 好不好 ⭐⭐](#十评估怎么知道你的-rag-好不好-)
11. [进阶：查询改写与多跳检索](#十一进阶查询改写与多跳检索)
12. [进阶：GraphRAG 与结构化知识](#十二进阶graphrag-与结构化知识)
13. [成本与运维](#十三成本与运维)
14. [踩坑清单](#十四踩坑清单)
15. [本章小结与练习](#本章小结与练习)

---

## 一、为什么需要 RAG

### 1.1 模型不知道你的数据

回顾 01 篇：模型的知识来自训练数据，有截止日期，**不包含你公司的内部文档**。

你问："我们公司的年假政策是什么？"

| 方案 | 结果 |
| :--- | :--- |
| 直接问模型 | 编一个"一般公司 5–15 天"（**幻觉**） |
| 微调 | 理论上可以，但贵、慢、文档一改就过时 |
| **RAG** | 从制度文档里查到"入职满 1 年 10 天，满 3 年 15 天"，基于原文回答 |

### 1.2 RAG vs 微调

| 维度 | RAG | 微调（Fine-tuning） |
| :--- | :--- | :--- |
| 解决什么问题 | **模型不知道的事实** | **模型的表达风格 / 特定任务格式** |
| 数据更新 | **改文档即可** | 重新训练 |
| 成本 | 低（存储 + 检索 + 少量推理） | 高（训练数据、算力、运维） |
| 可溯源 | **可以给出来源** | 不能 |
| 幻觉 | 显著降低 | 不解决 |
| 适合 | 知识库问答、文档助手、客服 | 语气定制、特定领域术语、固定格式输出 |

> 💡 **绝大多数企业需求是 RAG 不是微调**。先问自己："模型是不知道这件事，还是知道了但说得不对？"——前者用 RAG，后者才考虑微调。

### 1.3 RAG 的三个层次

```text
L1 基础 RAG：切分 → 向量化 → 检索 top-k → 塞进 Prompt
L2 进阶 RAG：混合检索 + 重排 + 查询改写 + 上下文压缩
L3 复杂 RAG：多跳、Agentic RAG（模型自己决定检索什么）、GraphRAG
```

**大部分业务做到 L2 就够了。** 本篇覆盖 L1 和 L2，L3 做介绍。

---

## 二、RAG 的完整链路

### 2.1 离线：建索引

```text
原始文档（PDF/Word/网页/Confluence/数据库）
   ↓ 加载（Loader）
纯文本
   ↓ 清洗（去页眉页脚、去乱码、保留结构）
文本块
   ↓ 切分（Splitter）
Chunk 列表（每块 300–800 token）
   ↓ 向量化（Embedding）
向量
   ↓ 存储（Vector Store）
索引库
```

### 2.2 在线：查询

```text
用户问题
   ↓ （可选）查询改写
检索 query
   ↓ 向量检索 / 关键词检索 / 混合
候选文档（top 20–50）
   ↓ 重排（Rerank）
精选文档（top 3–5）
   ↓ 组装 Prompt
[系统提示] + [资料] + [问题]
   ↓ 模型生成
答案 + 引用
```

> ⚠️ **线上效果差，先查"离线索引"**。80% 的 RAG 问题出在文档解析和切分，而不是检索算法。

### 2.3 一个关键认知

**RAG 不是"接一个向量库"就完事。** 它是一条**数据处理流水线**，每一环都会损失或引入噪声：

| 环节 | 常见损失 |
| :--- | :--- |
| 解析 | PDF 表格错乱、扫描件无文字、页眉页脚混入 |
| 清洗 | 删除过多上下文、保留乱码 |
| 切分 | 一句话被切成两半、表格被拆散 |
| Embedding | 专业术语表达不佳、多语言支持差 |
| 检索 | 召回不到（同义词）、召回太多（噪声） |
| 重排 | 模型选错 |
| Prompt | 资料太长挤压指令、格式不清 |

> 💡 **调试 RAG 的正确顺序是"从后往前"**：先看最终 Prompt 里到底塞了什么，再看重排结果，再看检索结果，再看 chunk 内容，最后才回到切分和解析。**一步步向上游追，比一上来就换模型有效得多。**

---

## 三、文档加载与解析

### 3.1 用 LangChain 的 Loader

```python
from langchain_community.document_loaders import (
    TextLoader,         # .txt
    PyPDFLoader,        # .pdf
    Docx2txtLoader,     # .docx
    UnstructuredMarkdownLoader,
    CSVLoader,
    WebBaseLoader,      # 网页
    DirectoryLoader,    # 批量加载目录
)

# 单个文件
docs = PyPDFLoader("handbook.pdf").load()

# 批量加载目录（按扩展名匹配）
loader = DirectoryLoader(
    "./docs",
    glob="**/*.md",
    loader_cls=UnstructuredMarkdownLoader,
    show_progress=True,
    use_multithreading=True,
)
docs = loader.load()
```

**每个 `Document` 包含**：

```python
Document(
    page_content="文本内容...",
    metadata={
        "source": "docs/handbook.pdf",
        "page": 3,
        "title": "员工手册",
        # 自定义字段：部门、权限、更新时间……
    }
)
```

> 💡 **`metadata` 是 RAG 的灵魂**。它承载了**权限过滤、时间过滤、溯源展示**所需的全部信息。**在加载阶段就要想清楚要保留哪些字段**，后面再补很痛苦。

### 3.2 解析的坑（比想象中多）

| 文档类型 | 常见问题 | 应对 |
| :--- | :--- | :--- |
| PDF（文本型） | 双栏排版顺序错乱、页眉页脚混入、表格错行 | 用 `pdfplumber` / `PyMuPDF` 按坐标提取；后处理去页眉页脚 |
| PDF（扫描件） | **提取不到文字** | OCR（PaddleOCR / Tesseract / 云服务） |
| Word | 表格、批注、修订痕迹 | `python-docx` 保留表格结构 |
| Excel | 多 sheet、合并单元格 | 转成 Markdown 表格或按行转文本 |
| 网页 | 导航栏、广告、JS 渲染 | `trafilatura` / `readability` 提取正文；JS 页面用 Playwright |
| Confluence/Wiki | 层级和链接关系丢失 | API 拉取时保留空间/父页面信息到 metadata |
| 代码库 | 函数被切断 | 按函数/类切分（AST） |

**一个实际的清洗步骤**：

```python
import re

def clean_text(text: str) -> str:
    text = re.sub(r"第\s*\d+\s*页\s*共\s*\d+\s*页", "", text)   # 页码
    text = re.sub(r"^\s*-\s*\d+\s*-\s*$", "", text, flags=re.M)  # 页脚
    text = re.sub(r"\n{3,}", "\n\n", text)                        # 多余空行
    text = re.sub(r"[ \t]{2,}", " ", text)                        # 多余空格
    return text.strip()
```

> ⚠️ **表格是 RAG 的重灾区**。纯文本切分会把表格拆成无意义的碎片。**建议把表格转成 Markdown 格式再存**，模型对 Markdown 表格的理解很好。

### 3.3 给 Document 加元数据

```python
docs = loader.load()
for d in docs:
    d.metadata.update({
        "doc_id": hashlib.md5(d.metadata["source"].encode()).hexdigest()[:12],
        "title": extract_title(d.page_content),
        "department": infer_department(d.metadata["source"]),   # 从路径推断
        "visibility": "internal",                                # 权限等级
        "updated_at": os.path.getmtime(d.metadata["source"]),
        "version": "v2026.11",
    })
```

**至少要有**：

- `source` / `doc_id`：溯源
- `title`：给用户看"答案来自哪篇文章"
- `updated_at`：判断信息是否过时
- **权限字段**：谁能看这份文档

---

## 四、切分（Chunking）⭐⭐

**切分是 RAG 里投入产出比最高的一环。改了切分策略，效果可能提升 30%；换模型可能只提升 5%。**

### 4.1 为什么必须切分

| 原因 | 说明 |
| :--- | :--- |
| 上下文窗口有限 | 整本文档塞不进去 |
| 检索精度 | 整篇文档的向量"平均"了所有主题，检索不准 |
| 成本 | 塞得越多越贵、越慢 |
| 噪声 | 无关内容会干扰模型 |

### 4.2 四种切分策略

**策略 1：固定长度切分（最简单）**

```python
from langchain_text_splitters import CharacterTextSplitter

splitter = CharacterTextSplitter(
    separator="\n\n",
    chunk_size=500,
    chunk_overlap=50,
)
chunks = splitter.split_documents(docs)
```

**策略 2：递归字符切分（最常用）**

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,          # 每块字符数（中文约 500 token）
    chunk_overlap=100,       # 重叠，保住上下文连续性
    separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
)
chunks = splitter.split_documents(docs)
```

**递归的含义**：先按段落切，太大再按句子切，还大再按字符切。**尽量在语义边界断开。**

> 💡 **中文切分一定要自定义 `separators`**。默认是英文标点，中文长句会被硬切在句子中间。

**策略 3：按语义切分（Semantic Chunking）**

```python
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

splitter = SemanticChunker(
    OpenAIEmbeddings(),
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=95,
)
chunks = splitter.split_documents(docs)
```

**原理**：计算相邻句子的向量相似度，**在相似度骤降的地方断开**。

**优点**：语义完整
**缺点**：**很慢很贵**（要算大量 embedding），且对短文档不友好

**策略 4：按结构切分（最推荐，需要结构信息）**

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ],
    strip_headers=False,        # 保留标题在正文里，检索更准
)
chunks = splitter.split_text(markdown_text)
# 每个 chunk 的 metadata 会带上 h1/h2/h3
```

**适用**：Markdown、HTML、Word（按标题层级）、代码（按函数/类）。

> ⚠️ **按标题切分会让块大小极不均匀**（有的章节 50 字，有的 5000 字）。**建议"结构切分 + 二次长度切分"组合**：
> ```python
> for chunk in structural_chunks:
>     if len(chunk.page_content) > MAX:
>         yield from recursive_split(chunk)
>     else:
>         yield chunk
> ```

### 4.3 参数怎么定

| 参数 | 建议 | 说明 |
| :--- | :--- | :--- |
| `chunk_size` | **中文 300–800 字 / 英文 500–1200 字符** | 太小丢上下文，太大稀释语义 |
| `chunk_overlap` | **size 的 10%–20%** | 保住跨块信息 |
| `separators` | 按文档类型定制 | 中文加中文标点 |

**不同内容的推荐值**：

| 内容 | chunk_size | overlap | 备注 |
| :--- | :--- | :--- | :--- |
| FAQ / 制度条款 | 300–500 | 50 | 一条一问一答，块要小 |
| 技术文档 | 600–1000 | 100 | 保留完整段落 |
| 长文章 / 报告 | 800–1200 | 150 | 上下文更重要 |
| 代码 | 按函数 | 0 | 用 AST 切，别按字符 |
| 表格 | 整表 | — | 不要切 |

### 4.4 高级：上下文增强（Contextual Retrieval）

一个真实的问题：块被切开后，**丢失了它属于哪个章节**。

```text
原文：
## 第三章 报销制度
### 3.2 交通费
市内交通单次不超过 100 元，需提供发票。

切出的块：
"市内交通单次不超过 100 元，需提供发票。"   ← 不知道这是报销制度的哪一条
```

**解决方案：给每个块加上下文前缀**

```python
def add_context(chunk, doc_summary, section_path):
    prefix = f"【文档：{doc_summary}｜章节：{section_path}】\n"
    chunk.page_content = prefix + chunk.page_content
    return chunk
```

**效果**：

```text
【文档：员工手册｜章节：第三章 报销制度 > 3.2 交通费】
市内交通单次不超过 100 元，需提供发票。
```

> 💡 这是 Anthropic 提出的 **Contextual Retrieval** 思路，实测能显著降低检索失败率。**成本是要为每个块生成一句上下文摘要**（可以用小模型批量做）。

**更轻量的做法**：直接把标题拼进正文（`MarkdownHeaderTextSplitter(strip_headers=False)`）。

### 4.5 父文档检索（Parent Document Retriever）

**问题**：小块检索准，但上下文不足；大块上下文足，但检索不准。

**解法**：**用小块检索，返回它所属的大块**。

```python
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000)     # 大块
child_splitter = RecursiveCharacterTextSplitter(chunk_size=400)       # 小块

retriever = ParentDocumentRetriever(
    vectorstore=Chroma(embedding_function=OpenAIEmbeddings()),
    docstore=InMemoryStore(),
    child_splitter=child_splitter,
    parent_splitter=parent_splitter,
)
retriever.add_documents(docs)

# 检索时用小块的向量匹配，但返回大块内容
results = retriever.invoke("交通费报销标准")
```

> 💡 **这是工业界非常常用的技巧**，几乎"免费"提升效果。生产环境把 `docstore` 换成 Redis/PostgreSQL 即可。

---

## 五、Embedding 与向量库 ⭐

### 5.1 Embedding 模型选择

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=1024)
```

| 模型 | 维度 | 特点 |
| :--- | :--- | :--- |
| `text-embedding-3-small` | 1536（可调） | 便宜、够用 |
| `text-embedding-3-large` | 3072 | 效果更好，贵 |
| BGE-M3 / bge-large-zh | 1024 | **中文效果好，可本地部署** |
| `multilingual-e5-large` | 1024 | 多语言 |

> ⚠️ **中文场景一定要测**。很多英文模型的英文效果很好，中文 retrieval 明显退化。**BGE 系列（智源）是国内最常用的开源选择**，可以本地跑，没有数据出境问题。

**选择要点**：

| 考虑 | 说明 |
| :--- | :--- |
| 语言 | 中文优先中文优化的模型 |
| 部署 | 数据敏感 → 本地部署（BGE、m3e） |
| 成本 | 建索引时一次性，查询时每次都算 |
| 维度 | 维度高 → 存储大、检索慢；1024 通常够 |
| **一致性** | **建库和查询必须用同一个模型、同一版本** |

> ⚠️ **换 embedding 模型 = 全量重建索引**。向量空间不同，旧向量直接作废。**这是规划时必须预留的运维成本。**

### 5.2 向量库选择

| 向量库 | 部署 | 特点 | 适合 |
| :--- | :--- | :--- | :--- |
| **Chroma** | 本地/嵌入式 | 简单、零配置 | 开发、小规模 |
| **FAISS** | 本地库 | Facebook 出品、快 | 离线/单机 |
| **pgvector** | PostgreSQL 扩展 | **和业务库同库**、支持 SQL 过滤 | **已有 PG 的项目首选** |
| **Milvus** | 独立集群 | 大规模、功能全 | 千万级以上 |
| **Qdrant / Weaviate** | 独立服务 | 云原生、过滤强 | 中大规模 |
| **Elasticsearch** | 已有集群 | 向量 + 全文一体 | 已有 ES 的项目 |
| 云服务（阿里云/腾讯云） | 托管 | 免运维 | 不想自己运维 |

**给后端程序员的建议**：

```text
开发阶段      → Chroma（pip 装完就能用）
生产、有 PG   → pgvector（少一个组件，事务一致性好）
生产、大规模  → Milvus / Qdrant
已有 ES       → Elasticsearch 向量检索
```

> 💡 **pgvector 常常是被低估的选择**：你已经有 PostgreSQL，加个扩展就能存向量，还能和业务表 join、用同一个事务、复用备份和监控。**对绝大多数企业应用，这比引入 Milvus 更务实。**

```sql
-- pgvector 建表
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE doc_chunks (
    id          BIGSERIAL PRIMARY KEY,
    doc_id      VARCHAR(64)  NOT NULL,
    content     TEXT         NOT NULL,
    metadata    JSONB        DEFAULT '{}',
    embedding   vector(1024) NOT NULL,
    created_at  TIMESTAMPTZ  DEFAULT now()
);

-- 建索引（HNSW，比 IVFFlat 更适合动态数据）
CREATE INDEX ON doc_chunks USING hnsw (embedding vector_cosine_ops);

-- 查询：余弦距离，取最相近的 5 条
SELECT id, doc_id, content, 1 - (embedding <=> $1) AS score
FROM doc_chunks
WHERE metadata->>'department' = 'HR'     -- 元数据过滤
ORDER BY embedding <=> $1
LIMIT 5;
```

### 5.3 用 LangChain 操作向量库

```python
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

vectorstore = Chroma(
    collection_name="handbook",
    embedding_function=OpenAIEmbeddings(),
    persist_directory="./chroma_db",
)

vectorstore.add_documents(chunks)                    # 写入
results = vectorstore.similarity_search("报销标准", k=5)
results = vectorstore.similarity_search_with_score("报销标准", k=5)

# 带元数据过滤
results = vectorstore.similarity_search(
    "报销标准", k=5,
    filter={"department": "HR"},
)
```

### 5.4 相似度度量

| 度量 | 含义 | 适用 |
| :--- | :--- | :--- |
| 余弦相似度 | 向量夹角 | **文本检索最常用** |
| 内积（dot） | 大小 + 方向 | 向量已归一化时等同余弦 |
| 欧氏距离（L2） | 直线距离 | 图像、部分模型 |

> ⚠️ **度量方式要和 embedding 模型的训练方式匹配**。用错了会导致"看起来都差不多"。查模型文档，别猜。

### 5.5 索引类型（了解即可）

| 类型 | 特点 |
| :--- | :--- |
| **HNSW** | 图索引，查询快、召回高、内存占用大；**动态插入友好** |
| **IVF-Flat** | 聚类倒排，建索引快、内存小；需要先训练，适合静态数据 |
| 暴力（Flat） | 精确但慢；数据量 < 10 万时其实够用 |

---

## 六、检索策略 ⭐⭐

### 6.1 只用向量检索的问题

| 问题 | 例子 |
| :--- | :--- |
| 专有名词 / 编号 | "订单号 A2026110001" 向量检索可能召回无关内容 |
| 精确匹配 | 产品型号 "XR-2000" |
| 短查询 | "怎么退货" 语义信息太少 |
| 领域黑话 | 模型没见过 "打板"、"压款" |

### 6.2 混合检索（Hybrid Search）⭐⭐

**向量检索（语义）+ 关键词检索（BM25/全文）**，两路召回后融合。

```text
查询
 ├─▶ 向量检索 top 20   （语义相近）
 └─▶ BM25 检索 top 20   （关键词命中）
          ↓
      融合去重（RRF）
          ↓
      候选 30 条 → 重排
```

**RRF（Reciprocal Rank Fusion，倒数排名融合）**：

```python
def rrf_fusion(result_lists, k=60, top_n=20):
    """docs: 多个检索器返回的有序列表"""
    scores = {}
    doc_map = {}

    for results in result_lists:
        for rank, doc in enumerate(results):
            key = doc.metadata["doc_id"] + ":" + str(hash(doc.page_content))
            scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
            doc_map[key] = doc

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [doc_map[k] for k, _ in ranked[:top_n]]
```

**优点**：不需要调权重，对异构检索器天然友好。

> 💡 **混合检索几乎是"必做项"**。实测在中文企业文档上，混合检索比纯向量检索的召回率平均高 10–20 个百分点。

### 6.3 LangChain 中的实现

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

bm25 = BM25Retriever.from_documents(chunks, k=20)
bm25.k = 20

vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 20})

ensemble = EnsembleRetriever(
    retrievers=[bm25, vector_retriever],
    weights=[0.4, 0.6],       # 可调：关键词重要就提高 BM25 权重
)

docs = ensemble.invoke("XR-2000 型号的保修期")
```

> ⚠️ **BM25 需要 jieba 之类的中文分词**，默认按空格切分对中文几乎是灾难：
> ```python
> import jieba
> from langchain_community.retrievers import BM25Retriever
> BM25Retriever.from_documents(chunks, preprocess_func=jieba.lcut)
> ```

### 6.4 k 值怎么定

| 阶段 | 建议 k | 说明 |
| :--- | :--- | :--- |
| 向量召回 | 20–50 | **宁可多召回**，交给重排筛选 |
| 关键词召回 | 20–50 | 同上 |
| 融合后 | 20–30 | — |
| **重排后** | **3–8** | 真正进 Prompt 的数量 |

**为什么重排后只要 3–8？**

- 每段 500 token × 8 = 4000 token，已经不小
- 超过 8 段，模型注意力分散，反而效果下降
- 无关内容会干扰判断

> ⚠️ **"多塞点总没坏处"是错的**。研究表明，检索片段从 5 增加到 20，准确率往往**先升后降**。噪声的破坏力比想象的强。

### 6.5 元数据过滤

**检索前先按业务条件过滤**，既能提效又能防越权：

```python
retriever = vectorstore.as_retriever(
    search_kwargs={
        "k": 20,
        "filter": {
            "$and": [
                {"department": {"$in": ["HR", "ADMIN"]}},
                {"updated_at": {"$gte": "2025-01-01"}},
                {"visibility": {"$ne": "confidential"}},
            ]
        },
    }
)
```

> ⚠️ **权限过滤必须在检索层做，不能靠模型自觉**。否则用户问"薪资表在哪"，模型可能把机密内容直接念出来。**这是 RAG 最大的安全事故来源。**

### 6.6 MMR：多样性检索

```python
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5},
)
```

**问题**：相似检索会返回 5 段几乎一样的内容（都在说同一件事）。
**MMR（最大边际相关性）**：在"相关"和"不重复"之间平衡。`lambda_mult` 越小越强调多样性。

---

## 七、重排（Rerank）⭐⭐

### 7.1 为什么需要

向量检索是**双编码器（Bi-Encoder）**：问题和文档**分别**编码成向量，再算相似度。

- 优点：快（文档向量可以离线算好）
- 缺点：**问题和文档之间没有"交互"**，精度有限

**重排是交叉编码器（Cross-Encoder）**：把 (问题, 文档) **一起**输入模型，输出相关性分数。

- 优点：**精度高得多**
- 缺点：慢（每个候选都要跑一次），所以只对 top 20–50 做

```text
向量检索 top 50（快，粗排）
        ↓
重排模型打分（慢，精排）
        ↓
取 top 5 进 Prompt
```

> 💡 **重排是 L1 → L2 最大的效果提升点**，通常能提升 10–30% 的相关性准确率，成本很低。

### 7.2 用 LangChain 做重排

**方案 A：Cohere Rerank（托管）**

```python
from langchain_cohere import CohereRerank

compressor = CohereRerank(model="rerank-multilingual-v3.0", top_n=5)
retriever = vectorstore.as_retriever(search_kwargs={"k": 30})
pipeline = retriever | compressor
docs = pipeline.invoke("报销标准是什么")
```

**方案 B：本地开源模型（BGE Reranker）**

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.retrievers.document_compressors import CrossEncoderReranker

model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-v2-m3")
compressor = CrossEncoderReranker(model=model, top_n=5)

retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=ensemble,
)
docs = retriever.invoke("报销标准是什么")
```

> ⚠️ **重排很吃 CPU/GPU**。50 个候选 × 每个 500 token，本地 CPU 可能跑 1–3 秒。**生产建议 GPU 或托管服务**，或者把候选数降到 20。

### 7.3 阈值过滤

```python
docs_with_scores = [(d, score) for d, score in reranked]
relevant = [d for d, s in docs_with_scores if s >= 0.3]
```

**如果过滤后为空**，就明确告诉用户"知识库中未找到相关内容"，而不是硬用低分内容作答。**这比答错好得多。**

---

## 八、Prompt 组装与引用溯源 ⭐

### 8.1 标准结构

```python
from langchain_core.prompts import ChatPromptTemplate

SYSTEM = """你是 {company} 的内部知识助手。

规则：
1. 只依据 <context> 中的资料回答，资料中没有的内容明确说"未找到相关信息"。
2. 每个结论后用 [编号] 标注来源，如 [1]。
3. 不要编造链接、数字、人名。
4. 如果资料之间冲突，指出冲突并说明各自出处。
5. 回答使用简体中文，条理清晰，不超过 400 字。

<context>
{context}
</context>
"""

USER = "{question}"

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", USER),
])


def format_docs(docs):
    parts = []
    for i, d in enumerate(docs, 1):
        title = d.metadata.get("title", d.metadata.get("source", "未知来源"))
        parts.append(f"[{i}] 来源：{title}\n{d.page_content}")
    return "\n\n".join(parts)
```

### 8.2 引用溯源

**必须让用户能点开原文验证**——这是企业知识库的信任基础。

```python
def build_answer(retriever, question):
    docs = retriever.invoke(question)
    if not docs:
        return {"answer": "未在知识库中找到相关内容，建议联系对口同事。", "citations": []}

    resp = (prompt | model).invoke({
        "company": "XX 公司",
        "context": format_docs(docs),
        "question": question,
    })

    citations = [
        {
            "index": i,
            "title": d.metadata.get("title"),
            "source": d.metadata.get("source"),
            "url": d.metadata.get("url"),
            "snippet": d.page_content[:120],
        }
        for i, d in enumerate(docs, 1)
    ]
    return {"answer": resp.content, "citations": citations}
```

```json
{
  "answer": "根据《员工手册》，入职满 1 年享 10 天年假，满 3 年 15 天 [1]。",
  "citations": [
    {"index": 1, "title": "员工手册 v2026.11", "source": "docs/handbook.pdf", "page": 12}
  ]
}
```

> ⚠️ **模型可能编造引用编号**（引用 [4] 但只给了 3 段）。**要校验**：解析答案里的 `[n]`，确保 n 在有效范围内，否则标记为"引用异常"。

### 8.3 "没找到"要明说

```python
NO_ANSWER = "未在知识库中找到相关内容"
```

**这比幻觉好一万倍**。用户宁愿看到"不知道"，也不想被误导。

**进一步**：记录所有"未命中"的问题，**这是知识库建设的待办清单**。

### 8.4 上下文压缩

如果检索到的片段太长，可以先压缩再塞进 Prompt：

```python
from langchain.retrievers.document_compressors import LLMChainExtractor

compressor = LLMChainExtractor.from_llm(model)
compressed = compressor.compress_documents(docs, query)
```

**注意**：这多了一次 LLM 调用，**不一定划算**。更常用的做法是**用重排把 top_k 降到 3–5**。

---

## 九、完整实现

### 9.1 建索引脚本

```python
# build_index.py
import hashlib, os, re, json
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

RAW_DIR = "./docs"
DB_DIR = "./chroma_db"
EMBED_MODEL = "text-embedding-3-small"


def load_documents():
    loader = DirectoryLoader(
        RAW_DIR, glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader,
        show_progress=True,
    )
    docs = loader.load()
    for d in docs:
        src = d.metadata["source"]
        d.metadata.update({
            "doc_id": hashlib.md5(src.encode()).hexdigest()[:12],
            "title": Path(src).stem,
            "department": infer_department(src),
            "updated_at": Path(src).stat().st_mtime,
        })
    return docs


def split_documents(docs):
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,
    )
    recursive = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=120,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )

    chunks = []
    for d in docs:
        for piece in header_splitter.split_text(d.page_content):
            piece.metadata.update(d.metadata)
            # 结构切分后仍可能过大，二次切分
            if len(piece.page_content) > 1200:
                for sub in recursive.split_documents([piece]):
                    chunks.append(sub)
            else:
                chunks.append(piece)
    return chunks


def main():
    docs = load_documents()
    chunks = split_documents(docs)
    print(f"文档 {len(docs)} 篇，切出 {len(chunks)} 块")

    embeddings = OpenAIEmbeddings(model=EMBED_MODEL)
    vs = Chroma(
        collection_name="handbook",
        embedding_function=embeddings,
        persist_directory=DB_DIR,
    )
    vs.reset_collection()          # 全量重建
    vs.add_documents(chunks)
    print("索引构建完成")


if __name__ == "__main__":
    main()
```

### 9.2 检索 + 生成

```python
# rag.py
import os
from dotenv import load_dotenv
import jieba
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

model = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=800)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vs = Chroma(collection_name="handbook", embedding_function=embeddings,
            persist_directory="./chroma_db")

# 双路召回
vector_retriever = vs.as_retriever(search_kwargs={"k": 30})
all_chunks = [d for d in vs.get(include=["documents", "metadatas"]) ]
# 生产上 BM25 建议从独立的倒排索引/ES 服务取，这里用内存版示意
bm25 = BM25Retriever.from_texts(
    [d.page_content for d in vs._collection.get(include=["documents"])["documents"]]
    if False else [doc for doc in vs.get(include=["documents"])["documents"]],
    preprocess_func=jieba.lcut,
)
bm25.k = 30

ensemble = EnsembleRetriever(retrievers=[bm25, vector_retriever], weights=[0.4, 0.6])

# 重排
cross = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-v2-m3")
reranker = CrossEncoderReranker(model=cross, top_n=5)
retriever = ContextualCompressionRetriever(
    base_compressor=reranker, base_retriever=ensemble,
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是公司内部知识助手。

规则：
1. 只依据 <context> 回答，没有就说"未找到相关信息"。
2. 每个结论后用 [编号] 标注来源。
3. 不要编造数字、链接、人名。

<context>
{context}
</context>"""),
    ("human", "{question}"),
])


def format_docs(docs):
    return "\n\n".join(
        f"[{i}] {d.metadata.get('title', d.metadata.get('source'))}\n{d.page_content}"
        for i, d in enumerate(docs, 1)
    )


def ask(question: str, department: str | None = None) -> dict:
    docs = retriever.invoke(question)
    if department:
        docs = [d for d in docs if d.metadata.get("department") in (department, "PUBLIC")]

    if not docs:
        return {"answer": "未在知识库中找到相关内容。", "citations": []}

    answer = (PROMPT | model | StrOutputParser()).invoke({
        "context": format_docs(docs), "question": question,
    })

    return {
        "answer": answer,
        "citations": [
            {"index": i, "title": d.metadata.get("title"), "source": d.metadata.get("source")}
            for i, d in enumerate(docs, 1)
        ],
    }
```

> ⚠️ 上面的 BM25 初始化为了示意做了简化。**生产上 BM25/全文检索应该由独立的搜索引擎承担**（Elasticsearch / PostgreSQL 全文索引 / OpenSearch），不要在应用内存里维护，否则多实例、增量更新都会出问题。

### 9.3 用 LCEL 组装

```python
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

chain = (
    RunnableParallel(
        context=retriever | format_docs,
        question=RunnablePassthrough(),
    )
    | PROMPT
    | model
    | StrOutputParser()
)

print(chain.invoke("出差住宿标准是多少？"))
```

---

## 十、评估：怎么知道你的 RAG 好不好 ⭐⭐

**没有评估的 RAG，就是在盲调。**

### 10.1 三层评估

```text
检索层：召回的文档相关吗？          → Recall@k / Precision@k / MRR / NDCG
生成层：回答是否忠于检索内容？        → Faithfulness / Answer Relevancy
端到端：用户问题是否被解决？          → 人工评分 / LLM 评分 / 业务指标
```

### 10.2 建评测集

**最基本的形式**：问题 + 标准答案 + 应引用的文档。

```json
[
  {
    "question": "入职满 3 年年假多少天？",
    "ground_truth": "15 天",
    "relevant_docs": ["handbook.md"],
    "type": "factual"
  },
  {
    "question": "出差住宿标准？",
    "ground_truth": "一线城市 600 元/晚，其他城市 400 元/晚",
    "relevant_docs": ["expense.md"],
    "type": "factual"
  },
  {
    "question": "我可以报销健身房会员费吗？",
    "ground_truth": "知识库中未涉及，应回答无法确认",
    "relevant_docs": [],
    "type": "unanswerable"
  }
]
```

> 💡 **一定要包含"无法回答"的问题**。这是检测幻觉最有效的方式。

**建集子的方法**：

1. 从真实用户问题里采样（最有效）
2. 让模型基于文档批量生成问题（快，但要人工筛）
3. 业务专家出题（质量最高，成本最高）

**规模**：先做 **30–50 条**，覆盖主要场景和边界情况。**不要一开始就追求几百条**，关键是有。

### 10.3 检索层评估

```python
def recall_at_k(retriever, dataset, k=5):
    hits = 0
    for item in dataset:
        if not item["relevant_docs"]:
            continue
        docs = retriever.invoke(item["question"])[:k]
        retrieved = {d.metadata.get("source", "").split("/")[-1] for d in docs}
        if retrieved & set(item["relevant_docs"]):
            hits += 1
    return hits / len([x for x in dataset if x["relevant_docs"]])
```

**关键指标**：

| 指标 | 含义 | 目标 |
| :--- | :--- | :--- |
| Recall@5 | 前 5 条里有没有正确答案所在文档 | > 0.85 |
| MRR | 正确答案排多靠前 | > 0.6 |
| 无关文档占比 | 进 Prompt 的噪声比例 | < 30% |

> ⚠️ **Recall 低 → 问题在检索（切分/embedding/混合检索）。Recall 高但答案差 → 问题在生成（Prompt/模型/重排）。** 这个二分法能快速定位问题。

### 10.4 生成层评估（LLM-as-a-Judge）

```python
from pydantic import BaseModel, Field

class JudgeResult(BaseModel):
    faithful: bool = Field(description="回答是否完全基于给定资料，没有编造")
    relevant: bool = Field(description="回答是否切题")
    score: int = Field(ge=1, le=5, description="1-5 分")
    reason: str = Field(description="简短的判断理由")

judge_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
judge = judge_model.with_structured_output(JudgeResult)

JUDGE_PROMPT = """判断下面的问答质量。

【资料】
{context}

【问题】
{question}

【回答】
{answer}

判断标准：
- faithful：回答中的每个事实是否都能在资料中找到依据
- relevant：是否直接回答了问题
"""

def llm_judge(context, question, answer):
    return judge.invoke(JUDGE_PROMPT.format(
        context=context, question=question, answer=answer
    ))
```

> ⚠️ **用 LLM 当裁判要注意**：
> - **用不同的模型评判**（评判用的模型最好比被测的强）
> - **裁判自己也会出错**，要用人工标注校准一批
> - **不要只看平均分**，要看具体失败案例

### 10.5 用 LangSmith 做评估

```python
from langsmith import Client, evaluate
from langsmith.evaluation import LangChainStringEvaluator

client = Client()
dataset = client.create_dataset("rag-eval")
client.create_examples(inputs=[...], outputs=[...], dataset_id=dataset.id)

results = evaluate(
    lambda x: {"answer": ask(x["question"])["answer"]},
    data="rag-eval",
    evaluators=[
        LangChainStringEvaluator("correctness"),
        LangChainStringEvaluator("faithfulness"),
    ],
)
```

### 10.6 回归测试

**每次改切分、改 Prompt、换模型，都跑一遍评测集**，记录分数变化：

| 版本 | Recall@5 | Faithfulness | 平均分 | 备注 |
| :--- | :--- | :--- | :--- | :--- |
| v1 | 0.72 | 0.81 | 3.4 | 纯向量 |
| v2 | 0.85 | 0.83 | 3.9 | +混合检索 |
| v3 | 0.88 | 0.91 | 4.3 | +重排 |
| v4 | 0.88 | 0.90 | 4.2 | 改了 Prompt，**回退** |

> 💡 这张表就是团队里最有说服力的东西：**它让"我觉得这样更好"变成可讨论的数据**。

---

## 十一、进阶：查询改写与多跳检索

### 11.1 查询改写（Query Rewriting）

**问题**：用户的原话往往不适合检索。

| 用户说的 | 检索友好的 |
| :--- | :--- |
| "我上周买的那个键盘坏了能换吗" | "商品质量问题 换货政策 保修期限" |
| "年假" | "年假 带薪年休假 请假流程 天数" |

**实现**：

```python
REWRITE_PROMPT = """将用户问题改写成适合知识库检索的查询。

要求：
- 补全指代（"它"、"那个" → 具体名词）
- 补充同义词和领域术语
- 拆分为多个独立查询（如涉及多个方面）
- 只输出查询，每行一个

历史对话：{history}
用户问题：{question}
"""

def rewrite_query(question, history=""):
    resp = model.invoke(REWRITE_PROMPT.format(history=history, question=question))
    return [q.strip() for q in resp.content.strip().split("\n") if q.strip()]

# 多查询分别检索再合并
queries = rewrite_query("年假")
all_docs = []
for q in queries:
    all_docs.extend(retriever.invoke(q))
docs = dedupe(all_docs)
```

### 11.2 HyDE（假设性文档）

让模型**先编一个"假答案"**，再用这个假答案去检索。

**原理**：假答案的表述风格更接近真实文档，检索效果更好。

```python
HYDE_PROMPT = "请写一段话回答下面的问题（假设你知道答案）：{question}"

def hyde_search(question):
    fake_answer = model.invoke(HYDE_PROMPT.format(question=question)).content
    return retriever.invoke(fake_answer)     # 用假答案去检索
```

**适用**：短查询、专业问题。**不适合**事实性精确查询（假答案可能带偏）。

### 11.3 多跳检索（Multi-hop）

**问题**："负责 A 项目的部门，去年预算多少？"

需要：先查" A 项目 → 部门"，再查"部门 → 预算"。

```python
def multi_hop(question, max_hops=3):
    context = []
    sub_q = question
    for _ in range(max_hops):
        docs = retriever.invoke(sub_q)
        context.extend(docs)

        check = model.invoke(f"""已收集的信息：
{format_docs(context)}

原始问题：{question}

信息是否足够回答？如果足够，输出 FINISHED。
如果不够，输出下一个需要检索的查询（只输出查询本身）。
""")

        if "FINISHED" in check.content:
            break
        sub_q = check.content.strip()

    return context
```

> ⚠️ **多跳检索成本高、延迟大**，且容易跑偏。**先在评测集上验证真的需要多跳**，再上这个方案。

### 11.4 Agentic RAG

把"检索"封装成**工具**，让 Agent 自己决定**什么时候检索、检索几次、用什么查询**。

```python
@tool
def search_knowledge_base(query: str) -> str:
    """在企业知识库中检索。用于查询公司制度、流程、产品说明等内部信息。"""
    docs = retriever.invoke(query)
    return format_docs(docs) if docs else "未找到相关内容"

agent = create_agent(model=model, tools=[search_knowledge_base],
                     system_prompt="你是知识助手，需要资料时调用检索工具。")
```

**优点**：灵活，能处理复杂问题
**缺点**：**不可控**（可能不检索直接编、可能反复检索）、成本高

> 💡 **建议**：先用**固定流程 RAG**（每次必检索）。只有在评测证明"固定流程不够用"时，才升级到 Agentic RAG。

---

## 十二、进阶：GraphRAG 与结构化知识

### 12.1 普通 RAG 的盲区

- **全局性问题**："这份年报的主要风险有哪些？"——需要通读全文，不是某一处
- **关系型问题**："A 和 B 是什么关系？"——需要跨文档连接

### 12.2 GraphRAG 思路

```text
文档 → 抽取实体和关系 → 构建知识图谱 → 社区检测 → 为每个社区生成摘要
查询 → 匹配相关社区 → 用摘要回答
```

**适用**：需要"纵观全局"的分析型问题、实体关系复杂的领域。

**代价**：构建成本高（大量 LLM 调用）、维护复杂。

> ⚠️ **不要为了用 GraphRAG 而用**。**90% 的企业知识问答，混合检索 + 重排就够了。**

### 12.3 结构化数据的 RAG（Text-to-SQL）

如果知识在数据库里，RAG 应该是"生成 SQL 再执行"：

```python
@tool
def query_database(question: str) -> str:
    """将自然语言问题转为 SQL 并查询数据库（只读）。"""
    sql = model.invoke(f"""根据以下表结构生成 MySQL 查询语句。

表结构：
{schema}

问题：{question}

只输出 SQL，不要解释。
""").content

    if not is_safe_select(sql):          # 关键：只允许 SELECT
        return "只支持只读查询"
    return str(db.execute(sql).fetchall())
```

> ⚠️ **Tool/Text-to-SQL 的安全红线**：**只读账号、只允许 SELECT、限制返回行数、加超时**。让模型生成 SQL 直接执行是极高风险操作。

---

## 十三、成本与运维

### 13.1 成本构成

| 项目 | 说明 | 优化 |
| :--- | :--- | :--- |
| 建索引 | Embedding 一次性（文档量大时不小） | 增量更新，只重算变更文档 |
| 查询 embedding | 每次查询一次 | 缓存高频问题 |
| 向量检索 | 计算资源 | 索引选型、调低 k |
| 重排 | GPU 或 API | 控制候选数 |
| 生成 | **最大头** | 控制进 Prompt 的片段数和长度 |

### 13.2 增量更新

```python
def incremental_sync():
    """只重建变更过的文档"""
    for path in scan_docs("./docs"):
        doc_id = md5(path)
        new_hash = file_hash(path)
        old = collection.get(where={"doc_id": doc_id}, include=["metadatas"])

        if not old["ids"]:
            add_document(path)                        # 新增
        elif old["metadatas"][0]["content_hash"] != new_hash:
            collection.delete(where={"doc_id": doc_id})   # 先删旧块
            add_document(path)                             # 再插新块
        # 否则跳过
```

**要点**：

1. 用 `content_hash` 判断内容是否变化
2. **删除旧块再插入**，避免残留
3. 记录 `last_sync_at`，支持定时同步

> ⚠️ **文档删除要同步删除向量**。否则用户会检索到已经被删除（甚至已作废）的内容——这在制度类文档里是**严重的合规问题**。

### 13.3 监控指标

| 指标 | 说明 |
| :--- | :--- |
| 检索命中率 | 有结果返回的比例 |
| 空结果率 | **突然升高 → 索引或文档有问题** |
| 平均 top1 相关度 | 检索质量的代理指标 |
| "未找到"回答率 | 知识缺口 |
| 引用点击率 | 用户是否信任答案 |
| 端到端延迟 | P50 / P95 / P99 |
| 单次成本 | token + 检索 + 重排 |

---

## 十四、踩坑清单

| # | 坑 | 现象 | 解决 |
| :--- | :--- | :--- | :--- |
| 1 | PDF 页眉页脚混入 | 检索到无意义内容 | 清洗规则 |
| 2 | 表格被拆碎 | 数字答错 | 表格转 Markdown，整表不切 |
| 3 | 中文切分用英文标点 | 句子被硬切 | 自定义 `separators` |
| 4 | chunk 太大 | 召回不准、token 高 | 300–800 字 |
| 5 | chunk 太小 | 缺上下文 | 加 overlap 或父文档检索 |
| 6 | 建库/查询用不同 embedding 模型 | 结果完全不对 | **统一模型和版本** |
| 7 | 换 embedding 模型没重建索引 | 全乱 | 全量重建 |
| 8 | 只做向量检索 | 专有名词/编号查不到 | 加 BM25 混合 |
| 9 | BM25 没中文分词 | 关键词检索失效 | jieba |
| 10 | top_k 设太大 | 噪声多、成本高 | 召回 20–50，重排后 3–8 |
| 11 | 没有重排 | 精度上不去 | 加 Cross-Encoder |
| 12 | 元数据权限未过滤 | **数据泄露** | 检索层强制过滤 |
| 13 | 删除文档没删向量 | 检索到已作废内容 | 同步删除 |
| 14 | Prompt 没说"没有就说不知道" | 幻觉 | 明确拒答规则 |
| 15 | 引用编号不校验 | 引用错乱 | 解析 + 校验范围 |
| 16 | 没有评测集 | 改动全靠感觉 | 30–50 条起步 |
| 17 | 只用 LLM 评分不看失败案例 | 掩盖系统性问题 | 人工抽查 |
| 18 | 多实例各自维护内存 BM25 | 结果不一致 | 用独立检索引擎 |
| 19 | 检索结果不截断 | token 爆炸 | 限长 + 说明截断 |
| 20 | 问题太短没改写 | 召回差 | 查询改写/扩展 |

---

## 十五、本章小结与练习

### 核心结论

1. **RAG 解决"模型不知道你的数据"**，是幻觉问题的主要解法，也是企业落地占比最高的形态。
2. **RAG 是一条流水线**，效果由最弱的一环决定，**解析和切分是投入产出比最高的环节**。
3. **切分策略 > 模型选择**：结构化切分 + 二次长度切分 + 上下文前缀。
4. **混合检索（向量 + 关键词）几乎是必做项**，RRF 融合简单有效。
5. **重排是 L1→L2 的最大提升点**，把 top 20–50 精排到 3–8。
6. **权限过滤必须在检索层完成**，不能依赖模型。
7. **"没找到"要明说**，比编一个答案好得多。
8. **没有评测集的 RAG 优化就是盲调**；先定位是检索问题还是生成问题。
9. **增量更新和删除同步**是运维的必修课。

### 动手练习

1. 用 10 篇 Markdown 文档搭一个最小 RAG，跑通"加载 → 切分 → 入库 → 检索 → 生成"。
2. 对比 `chunk_size` = 300 / 800 / 1500 三种设置下的检索效果（人工看 top 5 是否相关）。
3. 加 BM25 混合检索，用同一个问题对比"纯向量"和"混合"的召回差异（准备一个带型号/编号的问题）。
4. 加重排，观察 top 5 的变化和端到端耗时的增加。
5. 造一个"知识库中没有答案"的问题，验证系统是否正确回答"未找到"。
6. 构造一个越权场景（不同 department 的用户查同一问题），验证元数据过滤生效。
7. 写一个 20 条的小评测集（含 3 条"无法回答"），实现 Recall@5 和 faithfulness 自动打分。
8. 实现文档增量更新：改一篇文档，重跑同步脚本，验证只有该文档的向量被重建。

### 下一篇

[05 - 记忆与会话管理](05-记忆与会话管理.md) —— 让对话"记得住"，同时把成本控制在可接受范围。
