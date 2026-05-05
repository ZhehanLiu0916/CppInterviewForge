# M1 任务清单 (2/2): Prompt工程 + API + 主应用

> 里程碑：M1 - 基础设施 + 单问题解答MVP
> 周期：Week 2-3
> 任务范围：M1-T11 ~ M1-T15

---

## M1-T11: format 节点实现

**描述与关键实现要点：**
解析LLM生成的详细回答，组装最终输出格式。
- 输入：`state["short_answer"]`, `state["detailed_answer_raw"]`
- 解析详答的4段结构：
  - 使用正则提取 `📍 知识点定位:` 后的内容
  - 提取 `🔍 核心原理拆解:` 后的内容
  - 提取 `📝 常见考法说明:` 后的内容
  - 提取 `⚠️ 易错点提示:` 后的内容
- 如果解析失败，将原始内容放入 `knowledge_positioning`
- 组装 `source_info`：
  - `type`: `knowledge_base`/`online_search`/`ai_generated`
  - `reference`: 知识库文档来源或搜索URL
  - `similarity_score`: 检索相似度（仅知识库来源）
- 组装 `metadata`（仅知识库来源时）：
  - `category`, `sub_category`, `difficulty`
- 返回符合spec.md 6.1节JSON schema的结构

**输入/前置依赖：**
- M1-T10（generate节点产出）
- M1-T7/M1-T8（检索结果和元数据）

**产出物：**
- `app/nodes/format.py`

**验收标准：**
- 输出JSON符合spec.md 6.1节定义的schema
- 4段解析正确率≥95%
- 来源和元数据完整

---

## M1-T12: Prompt工程

**描述与关键实现要点：**
编写和优化所有核心Prompt模板，确保输出质量。
- 创建 `app/core/prompts.py`
- 编写以下Prompt：
  1. `REENGITE_PROMPT`: 问题改写和关键词提取
     - 输入：用户原始问题
     - 输出JSON：`{"keywords": [...], "rewritten_query": "..."}`
  2. `SHORT_ANSWER_PROMPT`: 简要回答生成
     - 约束：≤200字，核心结论+关键判定标准，口语化
     - 可注入：知识库内容/搜索结果
  3. `DETAILED_ANSWER_PROMPT`: 详细回答生成
     - 严格4段式结构，emoji标题
     - 适配校招应届生知识水平
     - 可注入：知识库内容/搜索结果
  4. `VALIDATE_ACCURACY_PROMPT`: 知识点准确性校验
     - 输入：知识库内容
     - 输出JSON：`{"is_accurate": true/false, "reason": "..."}`
- Prompt中预留 `{question}`, `{source_context}` 等变量占位符
- 设计few-shot示例提高输出稳定性

**输入/前置依赖：**
- 无（可并行开发）

**产出物：**
- `app/core/prompts.py`

**验收标准：**
- 10题抽检：简答字数≤200合格率≥80%
- 10题抽检：详答4段完整率≥80%
- JSON输出格式稳定可解析

---

## M1-T13: /ask API 接口

**描述与关键实现要点：**
实现单问题解答的HTTP接口，处理请求、调用LangGraph、返回响应。
- 路由：`POST /api/v1/ask`
- 请求体：
  ```json
  {
    "question": "C++面试问题",
    "answer_type": "both"  // "short"|"detailed"|"both"
  }
  ```
- 响应体：符合spec.md 6.1节定义
- 请求校验：
  - `question` 长度1-500字
  - `answer_type` 枚举值校验
- 调用 `run_question_graph(question, answer_type)`
- 错误处理：
  - 非C++问题 → code: 1001
  - 问题模糊 → code: 1002
  - LLM调用失败 → code: 2001
  - 生成超时 → code: 2002
  - 安全审核拦截 → code: 2003
  - 向量库不可用 → code: 3001
- 支持流式输出（可选，后续M1优化）

**输入/前置依赖：**
- M1-T4（QuestionGraph可运行）
- `app/models/schemas.py`（Pydantic请求/响应模型）

**产出物：**
- `app/api/routes.py`
- `app/models/schemas.py`

**验收标准：**
- `curl -X POST http://localhost:8000/api/v1/ask -H "Content-Type: application/json" -d '{"question":"虚函数表存哪"}'` 返回完整JSON
- 异常场景返回对应错误码和message

---

## M1-T14: FastAPI 主应用

**描述与关键实现要点：**
创建FastAPI应用实例，配置中间件、路由、生命周期事件。
- 创建 `app/main.py`
- 配置CORS中间件（允许所有来源）
- 注册路由：`/api/v1/*`
- 启动事件：
  - 初始化Retriever服务（预热Chroma和Embedding）
- 关闭事件：清理资源
- 集成loguru日志
- 配置FastAPI元数据：title, description, version
- 自动生成OpenAPI文档（`/docs`, `/redoc`）

**输入/前置依赖：**
- M1-T13（routes定义）
- M1-T6（Retriever服务）
- `app/core/logging.py`（loguru配置）

**产出物：**
- `app/main.py`
- `app/core/logging.py`

**验收标准：**
- `uvicorn app.main:app --host 0.0.0.0 --port 8000` 启动无报错
- 访问 `http://localhost:8000/docs` 显示Swagger UI
- 启动日志输出组件初始化状态

---

## M1-T15: 健康检查接口

**描述与关键实现要点：**
实现服务健康检查接口，用于监控和负载均衡健康探测。
- 路由：`GET /api/v1/health`
- 检查组件状态：
  - `llm`: LLM API连接状态（简单ping或返回"connected"）
  - `chroma`: 向量数据库连接状态
  - `embedding`: Embedding模型加载状态
- 响应体：
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "components": {
      "llm": "connected",
      "chroma": "connected", 
      "embedding": "loaded"
    }
  }
  ```
- 任一组件不可用时 `status: "degraded"`

**输入/前置依赖：**
- M1-T14（FastAPI应用）
- M1-T6（Retriever服务状态）

**产出物：**
- 更新 `app/api/routes.py`

**验收标准：**
- `curl http://localhost:8000/api/v1/health` 返回预期JSON
- 无报错时status为healthy
