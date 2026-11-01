# 02 - LangChain 快速上手

> 上一篇讲清了"模型是个什么东西"，这篇开始写代码。
> 目标：**用最少的概念跑通一个能用的对话程序**——接模型、发消息、拿回复、做流式、要结构化结果、处理多轮对话。
> 本篇只讲 LangChain 的**模型调用层**（`langchain-core` + `langchain-openai`），不涉及 Agent 和 RAG，那些后面几篇再说。

---

## 📖 目录

1. [LangChain 到底帮你做了什么](#一langchain-到底帮你做了什么)
2. [装环境与第一个调用](#二装环境与第一个调用)
3. [模型抽象：ChatModel 的三种用法](#三模型抽象chatmodel-的三种用法)
4. [消息体系（Messages）⭐](#四消息体系messages-)
5. [PromptTemplate：把变量安全地拼进去](#五prompttemplate把变量安全地拼进去)
6. [LCEL：用管道组合步骤](#六lcel用管道组合步骤)
7. [流式输出（Streaming）⭐](#七流式输出streaming-)
8. [结构化输出 ⭐](#八结构化输出-)
9. [多轮对话的最小实现](#九多轮对话的最小实现)
10. [错误处理、超时与重试](#十错误处理超时与重试)
11. [缓存：省钱的第一手段](#十一缓存省钱的第一手段)
12. [和 Java 的对照表](#十二和-java-的对照表)
13. [本章小结与练习](#本章小结与练习)

---

## 一、LangChain 到底帮你做了什么

### 1.1 没有框架时你要处理的事

直接调 HTTP 你会遇到这些琐碎问题：

| 问题 | 具体表现 |
| :--- | :--- |
| 多厂商协议差异 | 有的用 `tools`，有的用 `functions`；流式格式各不相同 |
| 消息格式转换 | 你存的是字符串，接口要的是 `[{role, content}]` |
| 流式解析 | SSE 分块、拼接、最后一个包没有换行 |
| 工具调用解析 | `tool_calls` 的 arguments 是 JSON 字符串，可能不合法 |
| 重试与超时 | 每个厂商的异常类型不一样 |
| 结构化输出 | 要自己拼 JSON schema、校验、失败重试 |
| 多模型切换 | 换个模型要改一堆代码 |

**LangChain 的核心价值就是：把这些差异统一成一套抽象。**

### 1.2 分层结构

```text
langchain-core         ← 抽象层：BaseChatModel、BaseMessage、Runnable、Tool、Callback
   ↑
langchain-openai       ← 具体模型的实现（ChatOpenAI）
langchain-anthropic
langchain-ollama
   ↑
langchain              ← 高层：create_agent、中间件、RAG 工具
langgraph              ← 编排：状态图、持久化、人工介入
```

**记住一点就够了**：你要用的模型类，来自 `langchain_<厂商>` 包；**通用抽象**（消息、工具、Runnable）来自 `langchain_core`。

### 1.3 什么时候不该用 LangChain

- 项目只用**一个模型、一个调用**，没有工具和 RAG → 直接调 SDK 更简单
- 团队对"额外一层抽象"极度敏感，且需要极致控制 → 直调 SDK
- 需要能力超出框架、频繁改框架源码 → 直调 SDK

> 💡 **LangChain 是加速器，不是必需品**。但当你要接工具、做 RAG、上 Agent 时，它省下的工作量非常可观。

---

## 二、装环境与第一个调用

### 2.1 安装

```bash
# 核心 + OpenAI 兼容实现
pip install -U langchain langchain-openai

# 如果你用 LangGraph（后面几篇要用）
pip install -U langgraph

# 环境变量管理
pip install -U python-dotenv
```

`requirements.txt`：

```text
langchain>=1.0
langchain-openai>=1.0
langgraph>=1.0
python-dotenv>=1.0
pydantic>=2.0
```

> ⚠️ **Pydantic 版本**：LangChain 1.x 要求 **Pydantic v2**。如果你的项目还在 v1，会报 `PydanticImportError`，需要升级。

### 2.2 `.env` 配置

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_xxx
LANGSMITH_PROJECT=lc-learning
```

```python
from dotenv import load_dotenv
load_dotenv()
```

### 2.3 第一个调用（三种写法都可以，选一种）

**写法 A：直接用 `ChatOpenAI`（最直观）**

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
resp = model.invoke("用一句话解释什么是 RESTful API")
print(resp.content)
```

**写法 B：`init_chat_model` 统一入口（推荐，换模型不改代码）**

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-4o-mini", model_provider="openai", temperature=0)
resp = model.invoke("用一句话解释什么是 RESTful API")
print(resp.content)
```

**写法 C：从配置文件/字符串读取（多模型共存时最灵活）**

```python
import os
from langchain.chat_models import init_chat_model

model = init_chat_model(os.getenv("MODEL_NAME", "gpt-4o-mini"))
```

> 💡 **为什么推荐 B**：
> ```python
> model = init_chat_model("deepseek-chat", model_provider="openai",
>                         base_url="https://api.deepseek.com/v1")
> ```
> 只改一行就能换到另一个兼容 OpenAI 协议的服务，业务代码不用动。

### 2.4 返回的不是字符串

```python
resp = model.invoke("你好")
print(type(resp))          # <class 'langchain_core.messages.ai.AIMessage'>
print(resp.content)        # 文本内容
print(resp.response_metadata)   # finish_reason、模型名、token 用量等
print(resp.usage_metadata)      # input_tokens / output_tokens / total_tokens
```

> ⚠️ **`resp.content` 不一定是字符串**。某些模型（尤其是带推理过程的）返回的是**内容块列表**，如 `[{"type": "text", "text": "..."}]`。取值前先判断类型，或使用框架提供的文本提取辅助方法。

---

## 三、模型抽象：ChatModel 的三种用法

LangChain 所有"可执行组件"都实现了 `Runnable` 接口，有三个核心方法：

| 方法 | 返回 | 用途 |
| :--- | :--- | :--- |
| `invoke(input)` | 完整结果 | 最简单，同步 |
| `stream(input)` | 生成器，逐块产出 | 流式输出（用户体验） |
| `batch([inputs])` | 结果列表 | 批量并发调用 |

```python
# invoke
print(model.invoke("你好").content)

# stream
for chunk in model.stream("写一首关于 Java 的短诗"):
    print(chunk.content, end="", flush=True)

# batch（并发执行，比 for 循环快得多）
results = model.batch(["问题1", "问题2", "问题3"])
for r in results:
    print(r.content)
```

**异步版本**：

```python
import asyncio

async def main():
    resp = await model.ainvoke("你好")
    print(resp.content)

    async for chunk in model.astream("讲个笑话"):
        print(chunk.content, end="", flush=True)

    results = await model.abatch(["问题1", "问题2"])

asyncio.run(main())
```

> ⚠️ **`batch` 是并发，会同时占用配额**。批量 100 条可能直接触发限流，实际使用要配合 `max_concurrency` 或自己分批：
> ```python
> results = model.batch(inputs, config={"max_concurrency": 5})
> ```

### 3.1 常用参数

```python
model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,          # 确定性
    max_tokens=800,         # 输出上限（必须设！）
    timeout=30,             # 单次请求超时（秒）
    max_retries=2,          # 自动重试
    streaming=False,        # 默认；用 .stream() 时会自动开
)
```

> ⚠️ **一定要设 `max_tokens` 和 `timeout`**。不设的话，模型可能生成几千 token（烧钱 + 慢），网络问题可能挂几分钟。

---

## 四、消息体系（Messages）⭐

### 4.1 四种消息类型

```python
from langchain_core.messages import (
    SystemMessage,      # 系统指令
    HumanMessage,       # 用户输入
    AIMessage,          # 模型回复
    ToolMessage,        # 工具执行结果
)
```

```python
from langchain_core.messages import SystemMessage, HumanMessage

messages = [
    SystemMessage("你是一个简洁的技术顾问，回答不超过 80 字。"),
    HumanMessage("什么是幂等？"),
]
resp = model.invoke(messages)
print(resp.content)
```

**也可以用简写元组**（框架会自动转换）：

```python
messages = [
    ("system", "你是一个简洁的技术顾问"),
    ("user", "什么是幂等？"),
]
resp = model.invoke(messages)
```

### 4.2 消息上还带了什么

除了 `content`，消息还有：

| 字段 | 说明 |
| :--- | :--- |
| `content` | 文本（或内容块列表） |
| `additional_kwargs` | 厂商特有字段（如 `tool_calls` 的原始结构） |
| `response_metadata` | 模型名、finish_reason、token 用量的原始结构 |
| `usage_metadata` | 规范化的 token 统计 |
| `id` | 消息 ID（可用于去重/追踪） |
| `name` | 发送者名字（多 Agent 场景有用） |

```python
ai_msg = model.invoke(messages)
print(ai_msg.usage_metadata)
# {'input_tokens': 32, 'output_tokens': 58, 'total_tokens': 90}
```

> 💡 **`usage_metadata` 是核算成本的关键**。生产上建议在每次调用后累加记录，按用户/会话/trace_id 汇总。

### 4.3 消息在 Agent 中的形态

一旦接入工具调用，消息序列会变成：

```text
SystemMessage      你是一个订单助手……
HumanMessage       帮我查一下订单 12345
AIMessage          tool_calls=[{name: "get_order", args: {"order_no": "12345"}}]
ToolMessage        {"status": "已发货", "items": [...]}
AIMessage          您的订单已发货……
```

消息序列就是 Agent 的"完整思维记录"。**排查问题时，把整个消息列表打印出来，比读日志有用。**

### 4.4 消息的增删改

消息是 **Pydantic 对象**（不可变风格），修改要重建：

```python
from langchain_core.messages import AIMessage

new_msg = ai_msg.model_copy(update={"content": "被修改的内容"})
```

**常见操作**：

```python
# 只保留最近 10 条（简单截断）
recent = messages[-10:]

# 去掉所有工具消息
no_tools = [m for m in messages if not isinstance(m, ToolMessage)]

# 合并两条连续的用户消息
# （有些模型要求 user/assistant 交替）
```

> ⚠️ **不要直接 `messages.append(ai_msg)` 后无限循环**——这就是"上下文无限增长"的根源。第 05 篇会讲裁剪策略。

---

## 五、PromptTemplate：把变量安全地拼进去

### 5.1 为什么不用 f-string

```python
# ❌ 危险：用户输入含 { } 会炸；也无法复用
prompt = f"请总结以下内容：{user_text}"

# ✅ 用模板
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是资深 {role}，请用专业但简洁的语言回答。"),
    ("user", "请总结以下内容：\n{document}"),
])
```

### 5.2 使用

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 {role}，回答不超过 {limit} 字。"),
    ("user", "{question}"),
])

messages = prompt.invoke({
    "role": "Java 架构师",
    "limit": "100",
    "question": "什么是 DDD？",
})
print(messages.to_messages())     # 得到消息列表

resp = model.invoke(messages)
```

**也可以用管道**（下一节）：

```python
chain = prompt | model
resp = chain.invoke({"role": "Java 架构师", "limit": "100", "question": "什么是 DDD？"})
```

### 5.3 常用变体

```python
from langchain_core.prompts import (
    ChatPromptTemplate,
    PromptTemplate,
    FewShotChatMessagePromptTemplate,
)

# 1. 单字符串模板
PromptTemplate.from_template("把以下英文翻译成中文：{text}")

# 2. 带示例（Few-shot）
examples = [
    {"input": "我忘了密码", "output": "重置密码"},
    {"input": "我想换个手机号", "output": "修改手机号"},
]
example_prompt = ChatPromptTemplate.from_messages([
    ("human", "{input}"),
    ("ai", "{output}"),
])
few_shot = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt, examples=examples,
)
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是工单分类器，只输出类别名。"),
    few_shot,
    ("human", "{input}"),
])
```

### 5.4 部分填充（partial）

```python
partial_prompt = prompt.partial(role="Java 架构师")
# 调用时只传剩余变量
partial_prompt.invoke({"limit": "100", "question": "什么是 DDD？"})
```

> 💡 **实际用途**：把"版本号、当前日期、租户名称"这类固定信息用 `partial` 一次性填好，业务调用处更干净。

### 5.5 模板与注入

**Prompt 注入的雏形**：如果用户输入被直接拼进 `system`，用户就能改写系统指令。

```python
# ❌ 把用户输入拼进 system
("system", f"你是客服。用户资料：{user_input}")

# ✅ 用户输入永远放 user，资料用分隔符隔离
("system", "你是客服。参考资料见 <docs> 标签内。"),
("user", "<docs>{docs}</docs>\n\n问题：{question}"),
```

> ⚠️ **没有任何 Prompt 写法能 100% 防注入**。真正的防护在代码层（权限校验、工具白名单），第 10 篇展开。

---

## 六、LCEL：用管道组合步骤

### 6.1 什么是 LCEL

**LCEL（LangChain Expression Language）** 用 `|` 把组件串成链：

```python
chain = prompt | model | parser
result = chain.invoke({"question": "什么是 CAP 理论？"})
```

**读法**：把左边输出的结果，作为右边输入的参数。

```python
prompt  : dict            → ChatPromptValue
model   : ChatPromptValue → AIMessage
parser  : AIMessage       → str
```

### 6.2 常用组合

```python
from langchain_core.output_parsers import StrOutputParser

chain = prompt | model | StrOutputParser()
print(chain.invoke({"question": "..."}))    # 直接得到字符串
```

```python
# 并行：同一输入走两条链，结果合并成 dict
from langchain_core.runnables import RunnableParallel

chain = RunnableParallel(
    summary=summary_prompt | model | StrOutputParser(),
    keywords=keyword_prompt | model | StrOutputParser(),
)
result = chain.invoke({"text": "..."})
# {"summary": "...", "keywords": "..."}
```

```python
# 顺序传递
chain = prompt1 | model | prompt2 | model | StrOutputParser()
```

```python
# 透传原始输入（用 lambda 或 RunnablePassthrough）
from langchain_core.runnables import RunnablePassthrough

chain = {
    "question": RunnablePassthrough(),
    "context": retriever,           # 用同一个问题去检索
} | prompt | model | StrOutputParser()
```

### 6.3 在链上配置

```python
chain = prompt | model

# 运行时参数（超时、并发、标签、回调）
chain.invoke(
    {"question": "..."},
    config={
        "run_name": "qa_chain",
        "tags": ["qa", "prod"],
        "metadata": {"user_id": "u_1001"},
        "max_concurrency": 5,
        "recursion_limit": 25,
    },
)
```

> 💡 **`metadata` 里的字段会出现在追踪系统里**，是排查"这个用户为什么答错了"的关键。建议至少带上 `user_id`、`session_id`、`trace_id`。

### 6.4 LCEL 的边界

LCEL 适合**线性、并行**的流程。一旦需要：

- 循环（Agent 的 while 循环）
- 条件分支（根据结果走不同路径）
- 中断恢复（人工审批）
- 状态在多步之间共享

**就不要硬用 LCEL 了**，那正是 LangGraph 的领域（第 07 篇）。

> ⚠️ **LangChain 1.x 用中间件（middleware）替代了部分旧链式 API**。旧的 `LLMChain`、`SimpleSequentialChain` 已经移到 `langchain-classic`，**新代码不要再写**。

---

## 七、流式输出（Streaming）⭐

### 7.1 为什么必须做

不流式：用户盯着空白页 **10–30 秒**，大概率直接关掉。
流式：**0.5 秒**内出现第一个字，用户知道系统在干活。

这是 AI 产品体验的分水岭，**没有流式的长回答产品基本没法用**。

### 7.2 最简写法

```python
for chunk in model.stream("介绍一下 Spring Boot 自动配置原理"):
    print(chunk.content, end="", flush=True)
```

```python
# 在链上流式（只要最后一步支持流式，整条链就能流）
chain = prompt | model | StrOutputParser()
for token in chain.stream({"question": "..."}):
    print(token, end="", flush=True)
```

### 7.3 流式的两种粒度

| 粒度 | 产出 | 用途 |
| :--- | :--- | :--- |
| `stream` | **token 级** | 聊天界面逐字打印 |
| `astream_events` | **事件级**（节点开始/结束、工具调用、模型输出） | 前端要展示"正在检索…""正在调用工具…" |

```python
async for event in chain.astream_events({"question": "..."}, version="v2"):
    kind = event["event"]
    if kind == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="", flush=True)
    elif kind == "on_tool_start":
        print(f"\n[调用工具: {event['name']}]")
    elif kind == "on_tool_end":
        print(f"[工具结果: {event['data']['output']}]")
```

> 💡 **`astream_events` 是构建"AI 应用界面"的关键**。用户能看到 Agent 在做什么，焦虑感大幅降低——这也是 Agent 产品好用与否的重要因素。

### 7.4 后端怎么吐给前端

**SSE（Server-Sent Events）** 是标准做法：

```python
# FastAPI
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def gen():
        async for chunk in chain.astream({"question": req.question}):
            if chunk:
                # SSE 格式：data: xxx\n\n
                yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")
```

**要点**：

1. 响应头 `Content-Type: text/event-stream`
2. 每个事件以 `data: ` 开头、`\n\n` 结尾
3. 客户端要处理断线重连
4. **反向代理要关掉缓冲**（Nginx `proxy_buffering off;`），否则流式会被攒成一坨

> ⚠️ **最常见的坑：本地流式正常，上了 Nginx 就变成"等半天一次性出来"**。检查 `proxy_buffering`、`proxy_cache`、`gzip`（对 SSE 关闭 gzip）。

### 7.5 流式与结构化输出的冲突

流式拿到的 JSON 是**不完整的片段**，不能直接 `json.loads`。

**解决**：

- 用支持**增量解析**的解析器（LangChain 的 `JsonOutputParser` 支持 partial）
- 或者：**普通字段流式，结构化字段最后一次性返回**
- 或者：让模型先流式输出自然语言，后台再异步生成结构化数据

```python
from langchain_core.output_parsers import JsonOutputParser

parser = JsonOutputParser()
for partial in parser.transform(stream_iter):
    print(partial)      # 逐步得到部分填充的 dict
```

---

## 八、结构化输出 ⭐

### 8.1 为什么需要

后端不想要一段散文，想要一个对象：

```python
# 想要的
{"name": "张三", "age": 28, "skills": ["Java", "Spring"]}

# 实际可能得到
"好的，根据您提供的信息，这位候选人叫张三，今年28岁，掌握的技能有 Java 和 Spring。"
```

### 8.2 三种实现方式

**方式 1：`with_structured_output`（最推荐）**

```python
from pydantic import BaseModel, Field
from typing import Literal

class Person(BaseModel):
    """从文本中提取的人物信息"""
    name: str = Field(description="姓名")
    age: int = Field(description="年龄，未知填 -1")
    skills: list[str] = Field(default_factory=list, description="技能列表")
    level: Literal["初级", "中级", "高级"] = Field(description="技术水平")

extractor = model.with_structured_output(Person)
result = extractor.invoke("候选人张三，28岁，5年 Java 经验，精通 Spring，水平算高级。")
print(result)          # Person(name='张三', age=28, skills=['Java', 'Spring'], level='高级')
print(type(result))    # 直接是 Pydantic 对象，不是字符串
```

> ⚠️ **`with_structured_output` 底层是用工具调用或 JSON Schema 约束实现的**，所以**要求模型支持工具调用**。小模型/老模型可能不支持。

**方式 2：`JsonOutputParser` + Prompt 里放 schema**

```python
from langchain_core.output_parsers import JsonOutputParser

parser = JsonOutputParser(pydantic_object=Person)
prompt = ChatPromptTemplate.from_messages([
    ("system", "从用户输入中提取人物信息。\n{format_instructions}"),
    ("human", "{text}"),
]).partial(format_instructions=parser.get_format_instructions())

chain = prompt | model | parser
result = chain.invoke({"text": "..."})    # 得到 dict
```

**方式 3：模型原生 JSON 模式**

```python
model = ChatOpenAI(model="gpt-4o-mini", model_kwargs={"response_format": {"type": "json_object"}})
```

> ⚠️ JSON 模式**只保证是合法 JSON，不保证字段符合你的 schema**。还需要自己校验。

### 8.3 三者对比

| 方式 | 可靠性 | 兼容性 | 是否返回对象 |
| :--- | :--- | :--- | :--- |
| `with_structured_output` | **高** | 需要工具调用 | ✅ Pydantic |
| `JsonOutputParser` | 中 | **好**（纯 Prompt） | dict |
| JSON Mode | 中 | 需要模型支持 | dict（需自己校验） |

### 8.4 结构化输出的实战要点

1. **字段描述（`description`）非常重要**——模型靠它理解字段含义
2. **用 `Literal` / 枚举约束取值范围**，比事后校验有效
3. **必填 vs 可选**：不确定的字段给默认值，别让它"必须编一个"
4. **加校验 + 重试**：

```python
from pydantic import ValidationError

def extract_with_retry(text, retries=2):
    for i in range(retries):
        try:
            return model.with_structured_output(Person).invoke(text)
        except ValidationError as e:
            text += f"\n\n上次输出不符合要求：{e}\n请严格按照 schema 重新输出。"
    raise ValueError("结构化提取失败")

# 或者用框架内置的重试
from langchain.output_parsers import RetryOutputParser
```

5. **`include_raw=True` 拿到原始消息**（排查"为什么解析失败"时必备）：

```python
extractor = model.with_structured_output(Person, include_raw=True)
res = extractor.invoke("...")
print(res["raw"])       # 原始 AIMessage
print(res["parsed"])    # 解析结果（可能为 None）
print(res["parsing_error"])
```

---

## 九、多轮对话的最小实现

### 9.1 模型无状态，历史要自己带

```python
history = [SystemMessage("你是 Java 技术助手，回答简洁。")]

def chat(user_input: str) -> str:
    history.append(HumanMessage(user_input))
    ai_msg = model.invoke(history)
    history.append(ai_msg)
    return ai_msg.content

print(chat("我在用 Spring Boot 3"))
print(chat("那它和 Java 17 兼容吗？"))   # 能理解"它"
```

**执行过程**：

```text
第 1 轮：system + [user1]                        → 模型
第 2 轮：system + [user1, ai1, user2]            → 模型（能看到第 1 轮）
```

> ⚠️ **每轮都会重发全部历史**，所以：**token 消耗随轮次平方增长，延迟也在增加**。这是"多轮对话"最容易被忽略的成本问题。

### 9.2 最简单的历史裁剪

```python
MAX_TURNS = 10

def chat(user_input: str) -> str:
    history.append(HumanMessage(user_input))
    # 保留 system + 最近 N 轮（每轮 2 条消息）
    trimmed = [history[0]] + history[1:][-MAX_TURNS * 2:]
    ai_msg = model.invoke(trimmed)
    history.append(ai_msg)
    return ai_msg.content
```

### 9.3 按 token 数裁剪（更准确）

```python
def trim_by_tokens(msgs, max_tokens=3000, keep_system=True):
    system = [m for m in msgs if isinstance(m, SystemMessage)] if keep_system else []
    rest = [m for m in msgs if not isinstance(m, SystemMessage)]

    total = sum(model.get_num_tokens_from_messages(system))
    kept = []
    for m in reversed(rest):                    # 从最新往前保留
        n = model.get_num_tokens_from_messages([m])
        if total + n > max_tokens:
            break
        kept.insert(0, m)
        total += n
    return system + kept
```

> 💡 **第 05 篇会把这个做成可复用的记忆管理模块**（滑动窗口 / 摘要 / 混合）。这里先有个印象。

### 9.4 在 LangChain 里的"标准做法"

LangChain 1.x 提供了 `ShortTermMemory` / middleware 形式的记忆管理，并且和 LangGraph 的 checkpointer 深度集成：

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model=model,
    tools=[],
    checkpointer=InMemorySaver(),      # 由 checkpointer 自动管理历史
)

config = {"configurable": {"thread_id": "user_1001_session_1"}}
agent.invoke({"messages": [("user", "我叫张三")]}, config)
resp = agent.invoke({"messages": [("user", "我叫什么？")]}, config)
print(resp["messages"][-1].content)    # 知道"张三"
```

> 💡 **这是第 05、08 篇的主题**。现在只需理解：**记忆 = 把历史存到某个地方，下次取出来拼进消息**。

---

## 十、错误处理、超时与重试

### 10.1 会遇到的异常

| 异常 | 触发 | 处理 |
| :--- | :--- | :--- |
| `AuthenticationError` | key 错/过期 | 检查配置，不重试 |
| `RateLimitError` (429) | 超出配额 | **指数退避重试** |
| `APITimeoutError` | 超时 | 重试，或缩短输入 |
| `APIConnectionError` | 网络问题 | 重试 |
| `BadRequestError` (400) | 参数错/超长 | 不重试，修代码 |
| `InternalServerError` (500) | 服务端问题 | 重试 1–2 次 |

```python
from openai import RateLimitError, APITimeoutError, APIConnectionError
import time

def invoke_with_retry(chain, inputs, retries=3):
    for i in range(retries):
        try:
            return chain.invoke(inputs)
        except (RateLimitError, APITimeoutError, APIConnectionError):
            if i == retries - 1:
                raise
            time.sleep(2 ** i)          # 1s, 2s, 4s
```

### 10.2 框架内置的重试

```python
model = ChatOpenAI(model="gpt-4o-mini", max_retries=3, timeout=30)
```

> ⚠️ **`max_retries` 只重试网络类错误，不重试 400**。业务层的失败（比如工具执行失败、输出格式不对）要自己写重试。

### 10.3 幂等与重复调用

**模型调用本身要按幂等来设计**：

- 重试会**重复计费**（看不出来但确实花钱）
- 如果调用链里有副作用（写库、发消息），重试会**重复执行**

> 💡 **原则**：**有副作用的操作不要放在"可能被重试"的链路里**，而是拆成"模型决策 → 业务执行（带幂等键）"两步。

### 10.4 降级

```python
def robust_invoke(messages):
    try:
        return primary_model.invoke(messages, config={"timeout": 20})
    except Exception:
        logger.warning("主模型失败，降级到备用模型")
        try:
            return backup_model.invoke(messages, config={"timeout": 20})
        except Exception:
            return AIMessage(content="服务繁忙，请稍后重试。")   # 兜底话术
```

---

## 十一、缓存：省钱的第一手段

### 11.1 精确缓存（相同输入）

```python
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache

set_llm_cache(InMemoryCache())        # 进程内，重启失效
```

```python
from langchain_community.cache import SQLiteCache
set_llm_cache(SQLiteCache(database_path=".langchain_cache.db"))
```

**适用**：测试、固定问答（FAQ）、Prompt 调试期间反复跑同样的 case。

> ⚠️ **注意时效性**：缓存了"今天天气"，明天还返回旧值就错了。**带实时性的调用不要缓存**。

### 11.2 语义缓存（相似问题）

用户问"怎么重置密码"和"密码忘了怎么办"，字面不同但意思一样。

```python
# 伪代码：用 embedding 判断语义相似
query_vec = embed(question)
cached = vector_store.search(query_vec, threshold=0.95)
if cached:
    return cached.answer
answer = model.invoke(...)
vector_store.save(query_vec, answer)
```

**风险**：阈值没调好会返回**近似但不正确**的答案（"怎么取消订单"匹配到"怎么修改订单"）。

> 💡 **生产上语义缓存要谨慎**：加"置信度阈值 + 命中后仍做一次轻量校验"，或者只对**无副作用、高重复率**的问答开启。

### 11.3 服务商侧的 Prompt 缓存

很多服务商对**相同前缀**的输入提供折扣（例如长系统提示 + 固定文档）。设计时：

- 把**固定不变的部分放在最前面**（系统提示、工具定义、固定知识）
- 把**变化的部分放在后面**（用户问题）

> 💡 **这是一条几乎零成本的优化**：调整消息顺序就能省钱，而且不改变任何业务逻辑。

---

## 十二、和 Java 的对照表

| LangChain / Python | Spring / Java 对应 | 说明 |
| :--- | :--- | :--- |
| `ChatOpenAI` / `init_chat_model` | `RestTemplate` / `WebClient` | 远程调用客户端 |
| `BaseMessage` 系列 | DTO | 请求/响应对象 |
| `ChatPromptTemplate` | `String.format` + 模板引擎 | 参数化文本 |
| LCEL `a \| b \| c` | 方法链 / `Stream` 流水线 | 组合执行 |
| `Runnable.invoke` | 同步方法调用 | — |
| `Runnable.stream` | `Flux<String>`（WebFlux） | 流式 |
| `Runnable.batch` | `CompletableFuture.allOf` | 并发 |
| `with_structured_output` | `Jackson` 反序列化 + `@Valid` | 结构化 |
| `config` 里的 `metadata` | MDC / TraceId | 链路追踪 |
| `InMemorySaver` / checkpointer | `Session` / Redis 存储 | 状态保存 |
| `create_agent` | 一个带循环的 Service | — |
| LangGraph `StateGraph` | 状态机 / 工作流引擎 | 编排 |

> 💡 **如果你在用 Java**：`LangChain4j` 的 `ChatLanguageModel`、`AiServices` 与这里的概念一一对应；`Spring AI` 的 `ChatClient` 也是同样的思路。**概念是跨语言的，API 只是写法差异。**

---

## 十三、本章小结与练习

### 核心结论

1. **LangChain 的核心价值是抽象统一**：多模型、消息协议、流式、工具调用、结构化输出。
2. **模型调用有三种形态**：`invoke`（同步）、`stream`（流式）、`batch`（并发）。
3. **消息序列就是上下文**，`usage_metadata` 是成本核算的依据。
4. **LCEL 用 `|` 组合线性流程**；有分支/循环/中断的需求要交给 LangGraph。
5. **流式输出是体验底线**，SSE 是标准实现；注意反向代理的缓冲配置。
6. **结构化输出优先用 `with_structured_output`**，字段描述写清楚，加校验重试。
7. **多轮对话 = 每次重发历史**，token 成本随轮次增长，必须做裁剪。
8. **重试要区分错误类型**，有副作用的操作要幂等或拆出重试链路。
9. **缓存与消息顺序**是最容易拿到收益的成本优化。

### 动手练习

1. 用 `init_chat_model` 接入两个不同厂商的模型，写一个函数用一行配置切换。
2. 写一个"代码审查"链：输入一段 Java 代码，输出结构化结果（`issues: [{line, severity, message}]`），并用 `with_structured_output` 保证类型。
3. 给练习 2 加流式输出，用 FastAPI + SSE 暴露成接口，用 `curl -N` 观察逐段返回。
4. 实现一个多轮对话，并打印每一轮的 `usage_metadata.total_tokens`，观察增长曲线。
5. 故意传一个超长文本，观察 400 错误，然后加上"按 token 裁剪"逻辑修复。
6. 用 `InMemoryCache` 缓存练习 2 的**相同输入**，验证第二次调用不产生 token 消耗。

### 下一篇

[03 - 工具调用与结构化输出](03-工具调用与结构化输出.md) —— 让模型从"只会说"变成"能办事"。这是 Agent 的前置条件，也是绝大多数业务系统接入模型的第一个真实需求。
