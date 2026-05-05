# CppInterviewForge 开发计划

> 基于 spec.md v1.0 | 日期：2026-05-05

---

## 1. 里程碑总览表

| 阶段 | 里程碑 | 周期 | 核心目标 | 关键交付物 |
|------|--------|------|----------|-----------|
| M1 | 基础设施 + 单问题解答MVP | Week 1-3 | 跑通"用户提问→RAG检索/在线搜索→LLM生成→格式化输出"全链路 | 可运行的 /ask 接口，输入问题返回简答+详答 |
| M2 | 知识库入库管道 + 质量调优 | Week 4-5 | ./book文档→MarkItDown→标题切分→向量化入库全流程打通；Prompt调优 | seed_knowledge.py 脚本、650+知识chunk入库、回答质量达标 |
| M3 | 面试复盘功能 | Week 6-8 | 实现 /review 接口，完成文本预处理→问题提取→逐题解答→5维评估→报告生成 | 可运行的 /review 接口，输出5模块结构化报告 |
| M4 | Docker部署 + 测试验收 | Week 9-10 | 容器化部署、性能达标、端到端测试通过 | Docker镜像、docker-compose.yml、测试报告 |

**里程碑依赖关系：**

```
M1 (MVP链路) ──→ M2 (知识库+调优) ──→ M3 (复盘功能) ──→ M4 (部署+验收)
  │                                       ↑
  └─── /ask接口 ──────────────────────────┘ (复用功能1)
```

---

## 2. 里程碑详细说明

### M1：基础设施 + 单问题解答MVP（Week 1-3）

**目标：** 用最快速度跑通核心链路——用户输入一个C++面试问题，系统返回简要回答+详细回答。此阶段知识库可为空，侧重验证 LangGraph 流程编排和多模型适配。

| # | 任务 | 具体产出 | 验收标准 | 预估工时 |
|---|------|----------|----------|---------|
| M1-1 | 初始化项目骨架 | 目录结构：`app/{api,core,graphs,nodes,models,services,utils}`、`scripts/`、`tests/`、`.env.example` | `python -c "import app"` 无报错 | 0.5天 |
| M1-2 | 配置管理 | `app/core/config.py`：从.env加载LLM_PROVIDER/API_KEY/MODEL_NAME等全部配置项 | 切换LLM_PROVIDER可正常调用不同模型API | 0.5天 |
| M1-3 | 多模型适配层 | `app/services/llm.py`：统一get_llm()接口，支持DeepSeek/OpenAI/Qwen，.env切换 | `get_llm().ainvoke("hello")` 三种Provider均返回结果 | 1天 |
| M1-4 | LangGraph QuestionGraph骨架 | `app/models/state.py`（QuestionState定义）、`app/graphs/question/graph.py`（5节点图：rewrite→retrieve→validate/web_search→generate→format） | `graph.compile()` 无报错，可绘制graph.get_graph().draw_mermaid() | 1天 |
| M1-5 | rewrite节点 | `app/nodes/rewrite.py`：输入question→输出keywords+rewritten_query | 输入"虚函数表存哪"→输出keywords=["虚函数表","vtable","存储位置"], rewritten_query="C++虚函数表vtable的存储位置" | 0.5天 |
| M1-6 | Chroma + Embedding初始化 | `app/services/retriever.py`：Chroma持久化客户端、text2vec-large-chinese嵌入函数、语义检索+关键词检索+合并排序 | 空库search返回[]；插入1条doc后search能命中 | 1天 |
| M1-7 | retrieve节点 | `app/nodes/retrieve.py`：调用retriever.multi_route_search，输出retrieval_results+max_similarity+use_knowledge_base | 阈值0.8以上标记use_knowledge_base=True，以下为False | 0.5天 |
| M1-8 | validate节点 | `app/nodes/validate.py`：准确性LLM校验+时效性规则校验 | 准确性不通过→validation_passed=False；6个月前内容→降级 | 1天 |
| M1-9 | 在线搜索节点 | `app/nodes/web_search.py`：Tavily搜索（优先）/SearXNG降级；5s超时；抓取Top-3正文≤4000字 | 知识库未命中时搜索成功→online_search_results非空；搜索超时→返回空 | 1天 |
| M1-10 | generate节点 | `app/nodes/generate.py`：简答Prompt(≤200字)+详答4段式Prompt+搜索结果/知识库内容注入 | 简答≤200字；详答含4个emoji标题段落；来源标注正确 | 1.5天 |
| M1-11 | format节点 | `app/nodes/format.py`：解析详答4段式、组装source_info+metadata | 输出符合spec.md 6.1节JSON schema | 0.5天 |
| M1-12 | Prompt工程 | `app/core/prompts.py`：REENGITE/SHORT_ANSWER/DETAILED_ANSWER/VALIDATE_ACCURACY 四组Prompt | 10题抽检：简答字数≤200合格率≥80%、详答4段完整率≥80% | 2天 |
| M1-13 | /ask接口 | `app/api/routes.py`：POST /api/v1/ask，请求校验→LangGraph调用→响应格式化+错误处理 | curl测试返回完整JSON；异常场景返回对应错误码 | 1天 |
| M1-14 | FastAPI主应用 | `app/main.py`：app实例、CORS、startup/shutdown、路由注册、loguru日志 | `uvicorn app.main:app` 启动无报错 | 0.5天 |
| M1-15 | 健康检查接口 | GET /api/v1/health：返回status/components | 返回{"status":"healthy","version":"1.0.0","components":{...}} | 0.5天 |

**M1验收标准：**
1. `POST /api/v1/ask` 输入C++面试问题，5s内返回简答、15s内返回详答
2. 简答≤200字，详答包含📍🔍📝⚠️四段结构
3. 来源标注正确：知识库命中→[来源:知识库]，搜索命中→[来源:在线搜索]，均未命中→[来源:AI生成]
4. 非C++问题返回错误码1001
5. LLM API不可用返回503

---

### M2：知识库入库管道 + 质量调优（Week 4-5）

**目标：** 将 `./books` 目录下已有PDF/MD文档全部入库；优化Prompt使回答质量达标。

| # | 任务 | 具体产出 | 验收标准 | 预估工时 |
|---|------|----------|----------|---------|
| M2-1 | MarkItDown文件转换管道 | `app/services/document_loader.py`：递归扫描./books目录→按扩展名(.pdf/.docx/.pptx/.md/.txt/.html/.epub)分派→MarkItDown转Markdown→输出统一md文本 | 对books/下所有PDF执行转换，输出md文件头部有标题标识 | 1天 |
| M2-2 | Markdown标题层级切分器 | `app/services/chunker.py`：按##/###切分→生成chunk列表(content+heading_text+parent_heading+source)→chunk_size 50-800 token范围→超长二次切分 | 输入md文本→输出chunk列表，每个chunk<800 token，包含heading_text元数据 | 1.5天 |
| M2-3 | LLM自动分类标注 | 切分后chunk经LLM推断category/sub_category/difficulty/tags→填入metadata | 100个chunk抽样：category分类准确率≥85% | 1天 |
| M2-4 | 批量入库脚本 | `scripts/seed_knowledge.py --rebuild`：扫描→转换→切分→分类→Embedding→Chroma批量写入→去重(基于source+heading) | 执行后Chroma中chunk数≥200；重复执行不产生重复条目 | 1天 |
| M2-5 | 全量入库执行 | 对books/目录下全部文档执行入库 | Chroma中chunk数≥650 | 1天 |
| M2-6 | Prompt调优-简答 | 调整SHORT_ANSWER_PROMPT：控制字数、口语化程度 | 50题测试：简答≤200字合规率≥95% | 1天 |
| M2-7 | Prompt调优-详答 | 调整DETAILED_ANSWER_PROMPT：4段结构完整度、代码示例适度 | 50题测试：详答4段完整率≥95% | 1天 |
| M2-8 | Prompt调优-校验 | 调整VALIDATE_ACCURACY_PROMPT：减少误判 | 知识库正确内容被误判为不准确的比例≤5% | 0.5天 |
| M2-9 | 检索结果缓存 | `app/services/cache.py`：LRU缓存（TTL=1h），高频问题检索结果缓存 | 重复问题第二次响应时间减少≥50% | 0.5天 |

**M2验收标准：**
1. `python scripts/seed_knowledge.py --rebuild` 可将./books全部文档向量化入库
2. Chroma中知识chunk数≥650，覆盖6大方向
3. 50题抽检：简答≤200字合规率≥95%、详答4段完整率≥95%
4. 知识库命中(simi≥0.8)场景回答来源标注为[来源:知识库]+出处
5. 重复执行seed_knowledge.py不产生重复条目

---

### M3：面试复盘功能（Week 6-8）

**目标：** 实现功能2全流程，复用M1的功能1作为子流程，输出5模块结构化复盘报告。

| # | 任务 | 具体产出 | 验收标准 | 预估工时 |
|---|------|----------|----------|---------|
| M3-1 | ReviewState定义 | `app/models/state.py`增加ReviewState：raw_transcript/cleaned_transcript/questions/interviewee_answers/reference_answers/evaluations/report | TypedDict编译无报错 | 0.5天 |
| M3-2 | 文本预处理节点 | `app/nodes/preprocess.py`：口语化规整(去"嗯啊就是")→噪音过滤→说话人分离→输出结构化对话 | 测试3份转写文本：语气词过滤率≥90%、说话人识别≥85% | 1.5天 |
| M3-3 | 问题提取节点 | `app/nodes/extract_questions.py`：从面试官发言提取独立问题→合并追问→输出问题列表 | 5份文本测试：问题召回率≥90% | 1天 |
| M3-4 | 回答提取节点 | `app/nodes/extract_answers.py`：从面试者发言提取每题回答→输出回答列表 | 5份文本测试：回答-问题对应正确率≥85% | 1天 |
| M3-5 | 逐题解答(复用QuestionGraph) | `app/graphs/review/graph.py`中answer_questions节点：遍历问题列表→调用run_question_graph→收集参考答案 | 5题测试：每题均有简答+详答，无遗漏 | 0.5天 |
| M3-6 | 5维评估Prompt | `app/core/prompts.py`增加EVALUATE_ANSWER_PROMPT：准确性/完整性/逻辑性/专业术语/匹配度，各1-5分+issues+suggestions | 10题人工对比：LLM评分与人工评分偏差≤1分 | 2天 |
| M3-7 | 逐题对比评估节点 | `app/nodes/evaluate.py`：对比面试者回答vs参考答案→5维评分→分点不足+优化建议 | 输出每题5维度评分+issues+suggestions | 1天 |
| M3-8 | 整体总结Prompt | OVERALL_SUMMARY_PROMPT+IMPROVEMENT_PROMPT：总分/strengths/weaknesses/knowledge_distribution/answer_style/优先方向/学习路径 | 总结与各题评估结果一致，不矛盾 | 1天 |
| M3-9 | 报告生成节点 | `app/nodes/generate_report.py`：组装5模块(问题汇总/参考答案/回答评估/表现总结/提升建议)→输出完整报告 | 输出严格包含5个模块，无缺失 | 1天 |
| M3-10 | ReviewGraph组装 | `app/graphs/review/graph.py`：preprocess→{extract_questions,extract_answers}→answer_questions→evaluate→generate_report→END | `graph.compile()`无报错 | 1天 |
| M3-11 | /review接口 | `app/api/routes.py`增加POST /api/v1/review：请求校验→LangGraph调用→响应格式化+错误处理 | curl测试返回完整5模块JSON | 1天 |
| M3-12 | 复盘异常处理 | 输入过短(<50字)→1003、未识别问题→1004、部分解答失败→标注继续、整体超时→截断提示 | 5种异常场景均有正确降级/提示 | 1天 |

**M3验收标准：**
1. `POST /api/v1/review` 输入转写文本，60s内返回5模块完整报告
2. 报告严格包含：问题汇总/参考答案/回答评估/表现总结/提升建议，无模块缺失
3. 每个问题均有参考答案（禁止省略），5维度评分齐全
4. 提升建议与评估结果对应，可执行
5. 6种异常场景均有正确响应

---

### M4：Docker部署 + 测试验收（Week 9-10）

**目标：** 容器化部署可一键启动，全部测试通过，性能指标达标，可交付使用。

| # | 任务 | 具体产出 | 验收标准 | 预估工时 |
|---|------|----------|----------|---------|
| M4-1 | Dockerfile编写 | 多阶段构建：builder阶段pip install→runtime阶段仅拷贝wheel+app代码 | `docker build .` 成功，镜像<2GB | 0.5天 |
| M4-2 | docker-compose.yml | 服务定义+env_file+volume挂载(./books,./data,./logs)+健康检查 | `docker-compose up -d` 一键启动，health检查通过 | 0.5天 |
| M4-3 | .env配置说明 | 完善.env.example注释，说明每项含义+可选值 | 新用户复制.env.example→.env填写API Key即可启动 | 0.5天 |
| M4-4 | .gitignore | 排除CIFenv/、__pycache__/、data/chroma/、.env、logs/ | git status不显示应排除文件 | 0.2天 |
| M4-5 | 单元测试 | tests/test_api.py + tests/test_nodes.py：核心Node/Prompt/工具函数 | `CIFenv/bin/pytest tests/ -v` 通过 | 2天 |
| M4-6 | 集成测试 | tests/test_integration.py：端到端/ask和/review测试 | /ask返回完整回答、/review返回5模块报告 | 1.5天 |
| M4-7 | 性能测试 | tests/test_perf.py：简答P95≤5s、详答P95≤15s、10 QPS无错误 | 所有性能指标达标 | 1天 |
| M4-8 | 异常场景回归测试 | 验证spec.md 2.2.3和2.3.3全部异常处理 | 每种异常均有正确降级/错误码 | 1天 |
| M4-9 | 知识库终态确认 | books/文档全部入库，chunk数≥650，6大方向覆盖 | Chroma count≥650 | 1天 |
| M4-10 | 部署验证 | Docker容器内执行完整流程：/ask + /review + /health | 容器内全部接口正常工作 | 0.5天 |

**M4验收标准：**
1. `docker-compose up -d` 一键启动，无需额外配置
2. 新用户仅需填写.env中API Key即可使用
3. 全部单元测试+集成测试通过
4. 性能指标达标：简答P95≤5s、详答P95≤15s、复盘P95≤60s、10 QPS无错误
5. spec.md中所有异常场景均有正确响应
6. 知识库chunk数≥650，覆盖6大方向

---

### M4.5：前端演示页面（可选里程碑）

**目标：** 提供一个极轻量前端展示界面，让非技术用户直观试用产品功能。核心后端接口不变，前端仅为单HTML静态页面，用内联CSS/JS调用后端API并展示结果。完全独立于后端主开发计划，可并行开发。

| # | 任务 | 具体产出 | 验收标准 | 预估工时 |
|---|------|----------|----------|---------|
| M4.5-1 | FastAPI自动文档配置 | 配置FastAPI Swagger UI `/docs` + ReDoc `/redoc`，支持API在线调试 | 访问 http://localhost:8000/docs 可看到完整API文档 | 0.2天 |
| M4.5-2 | 静态文件路由 | FastAPI添加静态文件路由 `/static` 服务前端资源 | `GET /static/demo.html` 返回HTML文件 | 0.2天 |
| M4.5-3 | 演示页面HTML结构 | `static/demo.html`：两个独立Section（提问区/复选区）+ API状态显示区 | 页面加载无JS错误，布局清晰 | 0.5天 |
| M4.5-4 | 提问区实现 | 输入框+简答/详答/Both选项+提交按钮+结果展示区（简答/详答/来源） | 输入问题点击提交→调用/ask→展示结果 | 1天 |
| M4.5-5 | 复盘区实现 | 多行文本输入框+提交按钮+报告5模块展开/收起面板 | 输入转写文本点击提交→调用/review→分模块展示报告 | 1.5天 |
| M4.5-6 | 内联CSS样式 | 极简样式：响应式布局、结果卡片、展开动画、加载状态 | 移动端/桌面端适配，UI简洁清晰 | 0.5天 |
| M4.5-7 | 错误处理 | 显示API错误信息、超时提示、格式验证 | 输入空值提示错误；API错误显示message | 0.5天 |
| M4.5-8 | Docker集成 | 前端静态文件打包进Docker镜像，nginx处理静态文件（可选） | Docker容器启动后访问根路径可看到前端入口 | 0.5天 |

**M4.5验收标准：**
1. 访问根路径 `/` 或 `/demo` 展示功能入口页面
2. 提问区：输入问题→选择回答类型→提交→显示简答/详答/来源标记
3. 复盘区：粘贴面试转写文本→提交→分模块展开报告（5大模块）
4. 纯静态无后端依赖：HTML文件可独立打开，修改`BASE_URL`变量连接不同后端
5. 手机浏览器访问正常显示

**前端技术约束：**
- 禁止引入React/Vue/Angular
- 禁止依赖npm/node
- 仅单HTML文件+内联CSS+内联JS
- UI库使用浏览器原生CSS Grid/Flex布局
- 图表展示用原生HTML `<details>` + `<summary>` 展开折叠
- 代码示例高亮用浏览器内置`<pre><code>`
- 总文件大小≤200KB

---

## 3. 关键风险与应对措施

| # | 风险 | 影响里程碑 | 概率 | 影响 | 应对措施 |
|---|------|-----------|------|------|----------|
| R1 | Prompt效果不达预期（字数超标/结构缺失） | M1、M2 | 高 | 高 | M1阶段用最简Prompt先跑通链路；M2预留3天专项调优；建立50题评估基准集，量化每次Prompt修改效果 |
| R2 | LLM API限流/不稳定 | M1、M3 | 中 | 高 | 实现请求队列+自动重试1次；.env支持多API Key轮询（LLM_API_KEYS=sk1,sk2,sk3）；降级时返回503+明确提示 |
| R3 | MarkItDown转换质量不足（PDF表格/代码块丢失） | M2 | 中 | 中 | 转换后自动校验：检测md中是否含代码块(```)/表格(|)；异常时log warning并回退为纯文本切分；对核心书籍(.md格式)优先手动校验 |
| R4 | 在线搜索不稳定 | M1 | 中 | 中 | 5s超时快速跳过；SearXNG自建实例作为Tavily降级；搜索失败不影响主链路（直接LLM生成） |
| R5 | 说话人分离准确率不足 | M3 | 中 | 中 | Prompt中强化模式匹配（"面试官"/"面试者"/"Q:"/"A:"关键字）；降级方案：提供说话人标注辅助接口，用户可手动标注 |
| R6 | 复盘报告生成超时 | M3 | 中 | 中 | 并行处理问题解答（LangGraph Send API）；单题10s上限，超时标注继续；整体60s超时返回部分报告 |
| R7 | Chroma检索质量不足（中文语义匹配差） | M1、M2 | 低 | 高 | 调整chunk策略（标题层级→段落切分）；必要时更换Embedding模型（BGE系列）；长期可升级Milvus |
| R8 | text2vec模型首次加载慢（~2GB下载） | M1 | 中 | 低 | M1阶段提前下载模型到本地；Docker镜像构建时预下载；.env可配置EMBEDDING_DEVICE=cpu |

---

## 4. 整体时间线预估

```
Week 1        Week 2        Week 3        Week 4        Week 5
┌────────────┬────────────┬────────────┬────────────┬────────────┐
│ M1-1~M1-6  │ M1-7~M1-14 │ M1-15      │ M2-1~M2-4  │ M2-5~M2-9  │
│ 骨架+底层   │ 核心节点    │ 接口+验收   │ 入库管道    │ 全量+调优   │
│ 模型适配    │ +Prompt     │            │            │            │
└────────────┴────────────┴────────────┴────────────┴────────────┘
                                  │
                    M1验收：/ask接口可用
                                              │
                                M2验收：650+chunk入库、
                                        回答质量达标

Week 6        Week 7        Week 8        Week 9        Week 10
┌────────────┬────────────┬────────────┬────────────┬────────────┐
│ M3-1~M3-5  │ M3-6~M3-9  │ M3-10~M3-12│ M4-1~M4-6  │ M4-7~M4-10 │
│ 预处理+提取  │ 评估+报告   │ 组装+接口   │ Docker+测试 │ 性能+验收   │
│ +复用解答    │ +Prompt    │ +异常处理   │            │            │
└────────────┴────────────┴────────────┴────────────┴────────────┘
                                  │                            │
                    M3验收：/review接口可用        M4验收：全部达标，可交付

可选：
Week 11 (可选里程碑)
┌────────────┐
│ M4.5       │
│ 前端演示页面│
│ (并行开发)  │
└────────────┘
```

**总工期：10周**

**关键检查点：**
- Week 3末：M1验收 → /ask接口可用，核心链路跑通
- Week 5末：M2验收 → 知识库完整入库，回答质量达标
- Week 8末：M3验收 → /review接口可用，复盘报告完整
- Week 10末：M4验收 → Docker部署通过，全部测试通过
- Week 11（可选）：M4.5验收 → 前端演示页面可用，非技术用户可直观试用

---

## 5. 极低成本约束下的具体措施

| 约束 | 具体措施 |
|------|----------|
| LLM成本 | 默认DeepSeek-Chat（最低价中文模型）；.env可切换其他Provider；校验用同一模型lowest temperature |
| 向量数据库 | Chroma免费嵌入式，零运维成本；持久化到本地文件 |
| Embedding | text2vec-large-chinese本地加载，零API成本；CPU模式运行 |
| 在线搜索 | Tavily免费额度(1000次/月)先用于开发测试；生产部署SearXNG自建零成本 |
| 部署 | Docker单容器部署，无需K8s；单机CPU即可运行 |
| 并发 | 4个uvicorn worker即可满足10 QPS；无需额外扩展 |
| 知识库运营 | 用户自行添加./books文件+运行seed脚本，零人工运营成本 |
