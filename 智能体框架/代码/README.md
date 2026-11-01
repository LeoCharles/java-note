# 智能体框架 · 配套代码

这里是与 `智能体框架/` 下 13 篇文档一一对应的**可运行代码**。
每篇文档都有对应目录，跑一遍代码，再回头看文档，理解会快得多。

---

## 一、快速开始

### 1. 环境准备

```bash
cd 智能体框架/代码

# 推荐用 uv（更快）；没装的话用 pip 也一样
pip install -r requirements.txt

# 或者
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
```

> 需要 Python **3.10+**（LangChain 1.x 要求）。

### 2. 配置模型

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

**最小配置（OpenAI 兼容接口）**：

```ini
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

**用国内兼容网关**（DeepSeek / 通义 / 智谱 / 本地 vLLM 都可以）：

```ini
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

> ⚠️ **不支持 Function Calling 的模型跑不了 03 之后的例子**。选模型时确认它支持 tools。

### 3. 跑第一个例子

```bash
python 01_basics/hello_llm.py
```

---

## 二、目录结构

| 目录 | 对应文档 | 内容 |
| :--- | :--- | :--- |
| `01_basics/` | 01 大模型应用开发基础 | 裸调 API、token、参数 |
| `02_langchain/` | 02 LangChain 快速上手 | invoke/stream/batch、LCEL、结构化输出 |
| `03_tools/` | 03 工具调用与结构化输出 | `@tool`、手写循环、安全 |
| `04_rag/` | 04 RAG 检索增强生成 | 建索引、检索、回答、评测 |
| `05_memory/` | 05 记忆与会话管理 | 裁剪、摘要、长期记忆 |
| `06_agent/` | 06 第一个 Agent 与 ReAct | `create_agent`、中间件、流式 |
| `07_langgraph/` | 07 LangGraph 状态图 | State/Node/Edge、reducer、Send |
| `08_persistence/` | 08 持久化与人工介入 | checkpointer、`interrupt`、恢复 |
| `09_multi_agent/` | 09 多 Agent 协作 | 工具即子 Agent、Supervisor、Handoff |
| `10_production/` | 10 工程化与生产落地 | 日志、评测、降级、成本 |
| `11_kb_agent/` | 11 实战：知识库问答 | 完整可运行的小型知识库 Agent |
| `12_cs_agent/` | 12 实战：客服工单 Agent | 订单查询 + 退款审批 + 转人工 |

---

## 三、按顺序跑

```bash
# 01 基础
python 01_basics/hello_llm.py
python 01_basics/token_cost.py
python 01_basics/params_demo.py

# 02 LangChain
python 02_langchain/basic_call.py
python 02_langchain/streaming.py
python 02_langchain/structured_output.py
python 02_langchain/lcel_chain.py

# 03 工具
python 03_tools/tools_basic.py
python 03_tools/handwritten_loop.py
python 03_tools/secure_tools.py

# 04 RAG（首次会下载嵌入模型，约 2GB）
python 04_rag/build_index.py
python 04_rag/rag_qa.py "年假有几天"
python 04_rag/eval_retrieval.py

# 05 记忆
python 05_memory/session_manager.py

# 06 Agent
python 06_agent/first_agent.py
python 06_agent/with_middleware.py
python 06_agent/stream_events.py

# 07 状态图
python 07_langgraph/basic_graph.py
python 07_langgraph/reducers.py
python 07_langgraph/parallel_send.py

# 08 持久化
python 08_persistence/checkpoint_demo.py
python 08_persistence/interrupt_demo.py
python 08_persistence/time_travel.py

# 09 多 Agent
python 09_multi_agent/tool_subagent.py
python 09_multi_agent/supervisor.py
python 09_multi_agent/handoff.py

# 10 工程化
python 10_production/logging_demo.py
python 10_production/eval_demo.py
python 10_production/fallback_demo.py

# 11 知识库 Agent（完整小项目）
python 11_kb_agent/build_index.py
python 11_kb_agent/chat.py
python 11_kb_agent/chat.py --acl-demo      # 权限对比：普通员工 vs HR

# 12 客服 Agent（完整小项目）
python 12_cs_agent/demo.py                 # 命令行跑完整场景（含审批、转人工）
python 12_cs_agent/demo.py --guard         # 只看出站质检规则
python 12_cs_agent/app.py                  # 起 HTTP 服务
# 然后 curl 或浏览器访问 http://localhost:8000/docs
```

---

## 三之二、11 / 12 两个小项目的文件构成

这两个目录不是「示例堆」，是能照抄结构的小项目。

### `11_kb_agent/` —— 知识库问答

| 文件 | 作用 |
| :--- | :--- |
| `docs/*.md` | 语料。文件头用 `<!-- acl: ... -->` 标权限，用 `<!-- updated: ... -->` 标更新时间 |
| `kb_core.py` | 加载 + 切分 + 带 ACL 的检索（复用 `04_rag` 的切分器和嵌入器） |
| `build_index.py` | 建索引，落盘到 `.index/kb.pkl` |
| `chat.py` | 问答：相关性判定 → 拒答 / 生成 → 引用校验 → 时效提示 |

**重点看 `retrieve_with_acl`**：ACL 过滤发生在**检索之前**（先缩小候选集再打向量），
而不是查完再筛。顺序错了会出现「结果数量不足、排序失真、日志泄露」三个问题。

### `12_cs_agent/` —— 客服工单

| 文件 | 作用 |
| :--- | :--- |
| `domain.py` | 模拟业务系统：订单 / 退款 / 工单状态机 / 审计。函数返回 `(status_code, payload)`，和真 HTTP 客户端同形 |
| `tools.py` | 工具层。四条铁律都在这里：身份从 `config` 取、没有金额参数、幂等键、错误分类带 `hint` |
| `routing.py` | 意图路由：规则先行，模型兜底 |
| `guard.py` | 出站质检：正则拦承诺/内部信息/责任判定/语气 + 数字一致性核对 |
| `graph.py` | 主图：triage → 子 Agent → 审批（`interrupt`）→ 执行 → 转人工 |
| `demo.py` | 命令行演示 11 个场景（质检、状态机、只读、小额/大额退款、驳回、转人工、越权、多轮、审计） |
| `app.py` | FastAPI：SSE 流式对话、审批接口、人工工作台 |

**重点看两处**：

1. `tools.py` 里 `AFTER_SALE_TOOLS = [get_order_detail, get_refund_status]` ——
   售后子 Agent **拿不到** `apply_refund`。写操作只由主图在审批之后执行。
   工具级隔离是物理的，提示词里写「不要退款」不算隔离。
2. `graph.py` 的 `approval_node` —— `interrupt()` 之前只有只读操作，
   真正的写在 `execute_node`，且带 `Idempotency-Key`。

---

## 四、常见问题

### 报错 `openai.AuthenticationError`

`.env` 里的 `OPENAI_API_KEY` 没填或不对。检查 `OPENAI_BASE_URL` 和 key 是否匹配（别把阿里云的 key 配到 OpenAI 的域名上）。

### 报错 `model does not support tools`

换一个支持 Function Calling 的模型。`gpt-4o-mini` / `deepseek-chat` / `qwen-plus` 都支持。

### RAG 例子下载模型很慢 / 连不上 huggingface

`04_rag` 和 `11_kb_agent` 默认用 `BAAI/bge-m3`（约 2GB）。两个办法：

```ini
# ① 换小模型（约 100MB），在 .env 里改
EMBED_MODEL=BAAI/bge-small-zh-v1.5
```

```bash
# ② 用镜像站
export HF_ENDPOINT=https://hf-mirror.com
# Windows PowerShell: $env:HF_ENDPOINT="https://hf-mirror.com"
```

也可以换成 API 调用（完全不下载模型）：

```ini
# .env
EMBED_PROVIDER=openai
EMBED_MODEL=text-embedding-3-small
```

> ⚠️ **换了嵌入模型必须重建索引**（`python 04_rag/build_index.py` / `python 11_kb_agent/build_index.py`）。
> 索引是拿模型输出算的，模型一换，向量空间就变了，旧索引查出来全是噪声。

### 没有 PostgreSQL

`08_persistence` 和 `12_cs_agent` 用到了 Postgres。**先用 `InMemorySaver` 跑通逻辑**，代码里都留了注释开关。
真要用 Postgres 的话：

```bash
docker run -d --name pg -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=agent \
  pgvector/pgvector:pg16
```

### 中文乱码（Windows）

```bash
chcp 65001
set PYTHONIOENCODING=utf-8
```

---

## 五、这些代码的定位

| | 说明 |
| :--- | :--- |
| ✅ 是 | 每个概念的**最小可运行示例**，能直接跑、能改 |
| ✅ 是 | 11/12 两个目录是**可以照着搭真实项目**的骨架 |
| ❌ 不是 | 生产级代码（缺少完整鉴权、完整的测试、完整的错误处理） |
| ❌ 不是 | 需要照抄的"标准答案"——**重点是看懂为什么这么写** |

> 💡 **建议的用法**：先跑通，再**故意改坏**（改 Prompt、删掉幂等键、把校验注释掉），
> 观察会发生什么。**知道它怎么坏，才知道怎么防。**

---

## 六、版本

| 依赖 | 版本 |
| :--- | :--- |
| Python | ≥ 3.10 |
| langchain | ≥ 1.0 |
| langgraph | ≥ 1.0 |
| pydantic | ≥ 2.7 |

> ⚠️ LangChain / LangGraph 迭代快，**部分 API 在小版本间有差异**。
> 遇到 `ImportError` 或参数不认，先做：
> ```python
> import inspect
> print(inspect.signature(...))
> ```
> 或者看对应文档里的"版本提示"章节。
