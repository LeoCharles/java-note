"""04 | RAG 配置。

所有可调参数集中在这里，方便对照文档调整。
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import settings

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
INDEX_DIR = BASE_DIR / ".index"

# ---------- 嵌入 ----------
EMBED_PROVIDER = settings.embed_provider          # local | openai
EMBED_MODEL = settings.embed_model

# 中文嵌入模型的查询前缀（BGE 系列需要）
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："

# ---------- 切分 ----------
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
MIN_CHUNK_LEN = 30

# ---------- 检索 ----------
VECTOR_TOP_K = 20          # 向量召回数
KEYWORD_TOP_K = 20         # 关键词召回数
RERANK_TOP_N = 4           # 重排后保留数
RRF_K = 60                 # RRF 平滑参数

# 相关性阈值：低于此值判定为「没找到」
# ⚠️ 这个值必须用你自己的语料实测校准，默认值只是起点
MIN_RELEVANCE = 0.35

# ---------- 生成 ----------
MAX_ANSWER_CHARS = 300
