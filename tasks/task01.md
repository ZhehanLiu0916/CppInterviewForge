# M1 任务清单 (1/2): 基础设施 + 配置 + 核心 Node

> 里程碑：M1 - 基础设施 + 单问题解答MVP
> 周期：Week 1-2
> 任务范围：M1-T1 ~ M1-T10

---

## M1-T1: 初始化项目骨架

**描述与关键实现要点：**
创建项目目录结构，确保模块化清晰、便于后续扩展。
- 创建 `app/` 主应用目录
- 创建子目录：`api/`（路由）、`core/`（配置/日志/Prompt）、`graphs/`（LangGraph图）、`nodes/`（LangGraph节点）、`models/`（数据模型）、`services/`（服务层）、`utils/`（工具函数）
- 创建 `scripts/`（脚本）、`tests/`（测试）、`data/`（数据目录）
- 创建空的 `__init__.py` 文件确保Python包结构
- 创建 `.env.example` 模板文件

**输入/前置依赖：**
- 无

**产出物：**
- `app/__init__.py`
- `app/api/__init__.py`
- `app/core/__init__.py`
- `app/graphs/__init__.py`
- `app/graphs/question/__init__.py`
- `app/graphs/review/__init__.py`
- `app/nodes/__init__.py`
- `app/models/__init__.py`
- `app/services/__init__.py`
- `app/utils/__init__.py`
- `scripts/__init__.py`
- `tests/__init__.py`
- `data/` 目录
- `.env.example`

**验收标准：**
- `source CIFenv/bin/activate && python -c "import app"` 无报错

---

## M1-T2: 配置管理模块

**描述与关键实现要点：**
实现统一配置管理，从 `.env` 文件加载所有配置项，支持环境变量覆盖。
- 使用 `python-dotenv` 加载 `.env`
- 定义 `Settings` 类，包含所有配置项属性
- 支持的配置项：
  - LLM配置：`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL_NAME`, `LLM_BASE_URL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`
  - 备选模型：`OPENAI_API_KEY`, `OPENAI_MODEL_NAME`, `QWEN_API_KEY`, `QWEN_MODEL_NAME`
  - Chroma配置：`CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION_NAME`
  - Embedding配置：`EMBEDDING_MODEL`, `EMBEDDING_DEVICE`
  - 检索配置：`RETRIEVAL_THRESHOLD`, `RETRIEVAL_TOP_K`
  - 在线搜索配置：`SEARCH_ENGINE`, `TAVILY_API_KEY`, `SEARCH_MAX_RESULTS`, `SEARCH_CONTENT_LIMIT`, `SEARCH_TIMEOUT`
  - 知识库路径：`BOOK_DIR`
  - 服务配置：`API_HOST`, `API_PORT`, `API_WORKERS`
  - 日志配置：`LOG_LEVEL`, `LOG_DIR`

**输入/前置依赖：**
- M1-T1（项目骨架）
- `.env.example` 已存在

**产出物：**
- `app/core/config.py`

**验收标准：**
- 配置可正确加载：`from app.core.config import settings; print(settings.LLM_PROVIDER)`
- 修改 `.env` 后重启服务能读取新配置

---

## M1-T3: 多模型适配层

**描述与关键实现要点：**
实现对多种LLM Provider的统一调用接口，便于通过 `.env` 切换模型。
- 使用 LangChain 的 `ChatOpenAI` 作为统一接口
- 支持三种Provider：
  - `deepseek`: 使用 `LLM_API_KEY` + `LLM_BASE_URL`（默认 https://api.deepseek.com/v1）
  - `openai`: 使用 `OPENAI_API_KEY`
  - `qwen`: 使用 `QWEN_API_KEY` + 阿里云 DashScope endpoint
- 实现 `get_llm(temperature, max_tokens)` 函数，返回统一接口
- 实现 `get_validator_llm()` 函数，返回低成本模型用于校验

**输入/前置依赖：**
- M1-T2（配置管理）
- `langchain-openai`, `langchain-community` 已安装

**产出物：**
- `app/services/llm.py`

**验收标准：**
- 三种Provider分别测试：`get_llm().ainvoke("hello")` 返回有效响应
- 切换 `LLM_PROVIDER=openai/qwen/deepseek` 后调用对应的API

---

## M1-T4: LangGraph QuestionGraph 骨架

**描述与关键实现要点：**
定义单问题解答的LangGraph状态图骨架，包含所有节点和边的定义。
- 定义 `QuestionState` TypedDict，包含：
  - `question`, `rewritten_query`, `keywords`
  - `retrieval_results`, `max_similarity`, `use_knowledge_base`
  - `validation_passed`, `knowledge_base_content`, `knowledge_base_metadata`
  - `online_search_results`, `online_search_urls`
  - `short_answer`, `detailed_answer`, `source_info`, `error`
- 创建 `StateGraph` 实例
- 添加节点：`rewrite`, `retrieve`, `validate`, `web_search`, `generate`, `format`
- 定义条件边：
  - `retrieve` → `validate`（当 `use_knowledge_base=True`）
  - `retrieve` → `web_search`（当 `use_knowledge_base=False`）
  - `validate` → `generate`（校验通过或不通过都走向generate）
- 设置入口点和终点

**输入/前置依赖：**
- M1-T1（项目骨架）

**产出物：**
- `app/models/state.py`（QuestionState定义）
- `app/graphs/question/graph.py`（图定义和编译函数）

**验收标准：**
- `graph.compile()` 无报错
- 可导出mermaid图：`graph.get_graph().draw_mermaid()`

---

## M1-T5: rewrite 节点实现

**描述与关键实现要点：**
对用户口语化提问进行语义理解，提取关键词并改写为标准查询。
- 输入：`state["question"]`
- 调用LLM执行改写Prompt（在 `prompts.py` 中定义）
- 输出JSON格式：`{"keywords": [...], "rewritten_query": "..."}`
- 异常处理：LLM调用失败时返回原始问题和空关键词列表

**输入/前置依赖：**
- M1-T3（多模型适配层）
- M1-T4（QuestionGraph骨架）
- `app/core/prompts.py`（REENGITE_PROMPT）

**产出物：**
- `app/nodes/rewrite.py`

**验收标准：**
- 输入"虚函数表存哪" → 输出keywords含"虚函数表"/"vtable"/"存储位置"
- LLM返回格式错误时降级处理，不抛异常

---

## M1-T6: Chroma + Embedding 初始化

**描述与关键实现要点：**
实现向量数据库客户端和嵌入函数封装，支持持久化和多路检索。
- 使用 `chromadb.PersistentClient`
- 使用 `SentenceTransformerEmbeddingFunction` 加载 `text2vec-large-chinese`
- 创建或获取集合（collection）
- 实现方法：
  - `initialize()`: 初始化客户端和集合
  - `search(query, top_k)`: 语义向量检索
  - `search_by_keywords(keywords, top_k)`: 关键词检索（使用Chroma的where过滤）
  - `multi_route_search(query, keywords)`: 合并两种检索结果
- 合并结果时按相似度排序，去重

**输入/前置依赖：**
- M1-T2（配置管理，获取CHROMA_PERSIST_DIR等）
- `chromadb`, `sentence-transformers` 已安装

**产出物：**
- `app/services/retriever.py`

**验收标准：**
- 空库时 `search()` 返回 `[]`
- 插入1条文档后检索能命中
- 合并检索结果正确排序和去重

---

## M1-T7: retrieve 节点实现

**描述与关键实现要点：**
执行多路检索并判断是否使用知识库回答。
- 输入：`state["rewritten_query"]`, `state["keywords"]`
- 调用 `retriever.multi_route_search()`
- 计算最大相似度 `max_similarity`
- 与阈值比较（默认0.8），设置 `use_knowledge_base`
- 异常处理：检索服务不可用时返回空结果和 `use_knowledge_base=False`

**输入/前置依赖：**
- M1-T6（Retriever服务）
- M1-T5（rewrite节点提供keywords）
- M1-T4（QuestionGraph骨架）

**产出物：**
- `app/nodes/retrieve.py`

**验收标准：**
- 相似度≥0.8时 `use_knowledge_base=True`
- 相似度<0.8时 `use_knowledge_base=False`
- 检索失败时降级处理

---

## M1-T8: validate 节点实现

**描述与关键实现要点：**
对知识库检索结果进行双重校验（准确性+时效性）。
- 输入：`state["retrieval_results"]`（取Top-1）
- 时效性校验：
  - 检查 `metadata["last_verified"]` 是否在6个月内
  - 超期则标记 `validation_passed=False`
- 准确性校验：
  - 调用低成本LLM执行校验Prompt
  - Prompt要求判断知识点描述是否准确（是/否+原因）
  - 不准确则标记 `validation_passed=False`
- 通过校验则设置 `knowledge_base_content` 和 `knowledge_base_metadata`
- 异常处理：校验LLM调用失败时默认通过

**输入/前置依赖：**
- M1-T3（多模型适配层，get_validator_llm）
- M1-T7（retrieve节点提供检索结果）
- `app/core/prompts.py`（VALIDATE_ACCURACY_PROMPT）

**产出物：**
- `app/nodes/validate.py`

**验收标准：**
- 明显错误的知识点被校验为不通过
- 6个月前的内容被标记超期
- 校验失败时 `validation_passed=False`

---

## M1-T9: web_search 节点实现

**描述与关键实现要点：**
当知识库未命中时，通过在线搜索获取补充信息。
- 输入：`state["rewritten_query"]`, `state["keywords"]`
- 优先使用Tavily Search API，备选SearXNG自建实例
- 搜索参数：
  - `max_results`: 5
  - `search_depth`: "basic"
  - 5秒超时
- 抓取Top-3结果正文，每条≤2000字符
- 合并为 `online_search_results`（≤4000字符）
- 记录来源URL到 `online_search_urls`
- 异常处理：超时或失败时返回空结果

**输入/前置依赖：**
- M1-T2（配置管理，TAVILY_API_KEY）
- `tavily-python` 已安装
- `app/services/web_search.py`（Tavily客户端封装）

**产出物：**
- `app/services/web_search.py`
- `app/nodes/web_search.py`

**验收标准：**
- 知识库未命中时搜索成功，`online_search_results` 非空
- 搜索超时时5秒内返回，不影响主流程
- 返回的URL列表有效

---

## M1-T10: generate 节点实现

**描述与关键实现要点：**
调用LLM生成简要回答和详细回答，注入知识库/搜索结果作为上下文。
- 输入：`state["question"]`, `state["knowledge_base_content"]`, `state["online_search_results"]`
- 根据来源决定上下文注入：
  - 知识库命中+校验通过：注入 `knowledge_base_content`
  - 在线搜索命中：注入 `online_search_results`
  - 均未命中：无上下文
- 调用LLM生成：
  - 简答：使用 `SHORT_ANSWER_PROMPT`
  - 详答：使用 `DETAILED_ANSWER_PROMPT`
- 统计简答字数（中文字符+英文单词）
- 设置来源标记：`knowledge_base`/`online_search`/`ai_generated`

**输入/前置依赖：**
- M1-T3（多模型适配层）
- M1-T8/M1-T9（校验或搜索结果）
- `app/core/prompts.py`（SHORT_ANSWER_PROMPT, DETAILED_ANSWER_PROMPT）
- `app/utils/text.py`（字数统计函数）

**产出物：**
- `app/nodes/generate.py`
- `app/utils/text.py`

**验收标准：**
- 简答≤200字
- 详答包含📍🔍📝⚠️四段emoji标题
- 来源标记正确
