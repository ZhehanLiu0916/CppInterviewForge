# C++ 面试 Agent

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Status](https://img.shields.io/badge/status-开发中-orange)

基于 FastAPI + LangGraph 的 C++ 面试辅导系统，帮助校招应届生系统性掌握 C++ 面试知识点。

## 📋 目录

- [项目亮点](#-项目亮点)
- [项目简介](#项目简介)
- [快速开始](#快速开始)
- [项目架构](#项目架构)
- [API 接口说明](#api-接口说明)
- [目录结构说明](#目录结构说明)
- [开发指南](#开发指南)
- [使用示例](#使用示例)
- [常见问题 (FAQ)](#常见问题-faq)
- [性能基准](#性能基准)
- [相关文档](#相关文档)
- [支持与反馈](#支持与反馈)
- [许可证](#许可证)

---

## 🎯 项目亮点

- **智能问答**：支持单题解答，提供简要回答（≤200字）和详细回答（4段式结构化输出）
- **面试复盘**：上传面试录音转写文本，自动生成5维度评估报告
- **知识库增强**：基于 Chroma 向量数据库 + RAG 检索，优先从知识库返回权威答案
- **多源回答**：知识库未命中时自动切换在线搜索或 AI 生成，确保回答可用性
- **低成本架构**：支持 DeepSeek/OpenAI/Qwen 等多模型，默认使用低成本方案

## 项目简介

### 产品定位
**系统性掌握知识点** —— 帮助校招应届生从零构建 C++ 面试知识体系，通过"知识点定位→核心原理拆解→常见考法说明→易错点提示"的引导式学习路径，实现从"背答案"到"理解原理"的转变。

### 适用人群
- 计算机相关专业的本科/硕士应届生
- 正在准备 C++ 技术岗面试的求职者
- 对 C++ 底层原理理解不扎实，需要系统性梳理的开发者

### 核心功能
| 功能 | 说明 |
|------|------|
| **单题解答** | 输入 C++ 面试问题，返回 ≤200 字简要回答 + 结构化详细回答（4 段式） |
| **面试复盘** | 上传面试录音转写文本，自动提取问题、评估回答、生成结构化复盘报告 |
| **多源回答** | 优先从知识库检索，未命中时自动切换在线搜索或 AI 生成 |
| **5 维评估** | 准确性、完整性、逻辑性、专业术语使用、匹配度 |

### 知识覆盖范围
| 方向 | 内容示例 |
|------|----------|
| **C++核心语法** | 指针与引用、const、static、模板、右值引用、移动语义、RAII、虚函数、智能指针 |
| **STL标准库** | vector/map底层原理、迭代器失效、allocator、各类容器性能对比 |
| **操作系统** | 进程线程、虚拟内存、死锁、IO多路复用、内存管理 |
| **计算机网络** | TCP/UDP、HTTP/HTTPS、三次握手/四次挥手、拥塞控制、Socket编程 |
| **数据库** | 索引原理、事务ACID、MVCC、SQL优化、Redis数据结构 |
| **设计模式** | 单例、工厂、观察者、策略、模板方法等常见模式 |

---

## 快速开始

### 前置要求
- Docker 20.10+ 及 Docker Compose
- Python 3.11+（非 Docker 部署时）

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆仓库
git clone <repo-url>
cd CppInterviewForge

# 2. 复制并配置环境变量
cp .env.example .env

# 3. 编辑 .env，填写至少一项 LLM API Key
# LLM_PROVIDER=deepseek
# LLM_API_KEY=sk-xxxxxxxx
# LLM_MODEL_NAME=deepseek-chat
# LLM_BASE_URL=https://api.siliconflow.cn/v1/

# 4. 启动服务
docker-compose up -d

# 5. 验证服务健康
curl http://localhost:8000/api/v1/health
# 预期返回：{"status":"healthy","version":"1.0.0","components":{...}}
```

### 方式二：本地虚拟环境部署

```bash
# 1. 创建并激活虚拟环境
python -m venv CIFenv
source CIFenv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填写 API Key

# 4. 设置 HuggingFace 镜像（国内网络环境）
echo 'HF_ENDPOINT=https://hf-mirror.com' >> .env

# 5. 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `deepseek` | LLM 提供商：`deepseek`/`openai`/`qwen` |
| `LLM_API_KEY` | - | LLM API 密钥（**必填**） |
| `LLM_MODEL_NAME` | `deepseek-chat` | 模型名称 |
| `LLM_BASE_URL` | `https://api.siliconflow.cn/v1/` | API 地址（硅基流动等第三方） |
| `LLM_TEMPERATURE` | `0.3` | 生成温度（0-1，越低越确定性） |
| `EMBEDDING_MODEL` | `text2vec-large-chinese` | Embedding 模型 |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | Chroma 向量库存储路径 |
| `RETRIEVAL_THRESHOLD` | `0.8` | 知识库检索相似度阈值 |
| `TAVILY_API_KEY` | - | Tavily 在线搜索 API Key（可选） |
| `HF_ENDPOINT` | - | HuggingFace 镜像地址（国内填 `https://hf-mirror.com`） |

---

## 项目架构

### 技术栈
| 组件 | 技术 | 用途 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | HTTP 服务、路由管理 |
| 流程编排 | LangGraph | 多步骤 AI 流程的状态图编排 |
| 向量数据库 | ChromaDB | 知识库语义检索 |
| Embedding | sentence-transformers | 文本向量化 |
| LLM 适配 | LangChain | 统一多模型接口（DeepSeek/OpenAI/Qwen） |
| 在线搜索 | Tavily / SearXNG | 知识库未命中时的降级方案 |
| 日志 | Loguru | 结构化日志输出 |

### 架构流程

**单题解答流程：**
```
用户输入问题
    ↓
[改写节点] → 提取关键词 + 问题改写
    ↓
[检索节点] → 多路检索（语义 + 关键词）
    ↓
{相似度 ≥ 0.8?}
   ├─ YES → [校验节点] → 准确性 + 时效性校验
   └─ NO  → [在线搜索节点]
    ↓
[生成节点] → 调用 LLM 生成简答 + 详答
    ↓
[格式化节点] → 解析详答、组装来源信息
    ↓
返回结果（简答 + 详答 + 来源）
```

**面试复盘流程：**
```
上传面试转写文本
    ↓
[预处理节点] → 去噪 + 说话人分离
    ↓
[问题提取] + [回答提取]（并行）
    ↓
[逐题解答] → 复用单题解答流程
    ↓
[评估节点] → 5 维对比评估
    ↓
[报告生成] → 5 模块结构化报告
    ↓
返回复盘报告
```

---

## API 接口说明

服务启动后访问 `http://localhost:8000/docs` 查看完整 Swagger 文档。

### 健康检查
```bash
GET /api/v1/health
curl http://localhost:8000/api/v1/health
```

### 单题解答
```bash
POST /api/v1/ask
Content-Type: application/json

{
  "question": "C++ 中虚函数的底层实现原理是什么？",
  "answer_type": "both"
}

# answer_type: "short"（简答）/ "detailed"（详答）/ "both"（两者）
```

**响应示例：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "question": "C++ 中虚函数的底层实现原理是什么？",
    "short_answer": {
      "content": "虚函数通过虚函数表（vtable）实现...",
      "word_count": 180
    },
    "detailed_answer": {
      "knowledge_positioning": "📍 知识点定位：...",
      "core_principle": "🔍 核心原理拆解：...",
      "common_exams": "📝 常见考法说明：...",
      "pitfalls": "⚠️ 易错点提示：..."
    },
    "source": {
      "type": "knowledge_base",
      "reference": "xxx.md",
      "similarity_score": 0.92
    }
  }
}
```

### 面试复盘
```bash
POST /api/v1/review
Content-Type: application/json

{
  "transcript": "面试官：说说虚函数的作用...\n面试者：虚函数可以实现多态...",
  "metadata": {"candidate": "张三"}
}
```

---

## 目录结构说明

```
CppInterviewForge/
├── app/
│   ├── api/              # FastAPI 路由
│   │   └── routes.py     # /ask、/review、/health 接口
│   ├── core/             # 核心配置
│   │   ├── config.py     # 环境变量加载
│   │   ├── logging.py    # 日志配置
│   │   └── prompts.py   # 所有 LLM Prompt 模板
│   ├── graphs/           # LangGraph 流程定义
│   │   ├── question/     # 单题解答图
│   │   └── review/       # 面试复盘图
│   ├── models/           # 数据模型
│   │   ├── schemas.py    # Pydantic 请求/响应模型
│   │   └── state.py     # LangGraph 状态定义
│   ├── nodes/            # LangGraph 节点实现
│   │   ├── rewrite.py    # 问题改写
│   │   ├── retrieve.py   # 知识库检索
│   │   ├── validate.py   # 内容校验
│   │   ├── web_search.py # 在线搜索
│   │   ├── generate.py   # 回答生成
│   │   ├── format.py     # 输出格式化
│   │   ├── preprocess.py # 文本预处理
│   │   ├── extract_questions.py
│   │   ├── extract_answers.py
│   │   ├── evaluate.py   # 回答评估
│   │   └── generate_report.py
│   ├── services/         # 业务服务层
│   │   ├── llm.py       # LLM 多模型适配
│   │   ├── retriever.py  # Chroma 向量检索
│   │   ├── cache.py     # LRU 缓存
│   │   ├── web_search.py # Tavily/SearXNG 搜索
│   │   ├── chunker.py   # Markdown 文档切分
│   │   ├── classifier.py # LLM 自动分类标注
│   │   └── document_loader.py  # 多格式文档加载
│   ├── utils/           # 工具函数
│   │   └── text.py      # 字频统计、截断等
│   └── main.py          # FastAPI 应用入口
├── books/               # 知识库原始文档（PDF/MD/DOCX等）
├── scripts/
│   └── seed_knowledge.py  # 知识库入库脚本
├── tests/               # 测试用例
├── static/              # 前端演示页面
├── data/chroma/         # Chroma 向量数据库存储
├── logs/                # 运行日志
├── docker-compose.yml   # Docker Compose 配置
├── Dockerfile           # Docker 镜像构建
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量模板
├── spec.md              # 产品技术规格文档
├── plan.md              # 开发计划
└── README.md            # 本文件
```

---

## 开发指南

### 扩展知识库

将 C++ 相关 PDF/MD/DOCX 文档放入 `books/` 目录，然后运行入库脚本：

```bash
# 激活虚拟环境
source CIFenv/bin/activate

# 全量重建知识库（首次或文档有更新时）
python scripts/seed_knowledge.py --rebuild

# 增量更新（仅处理新增文档）
python scripts/seed_knowledge.py
```

入库流程：`books/` → MarkItDown 转 Markdown → 按标题切分 → LLM 自动分类 → 向量化写入 Chroma

### 运行测试

```bash
# 激活虚拟环境
source CIFenv/bin/activate

# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_basic.py -v

# 带覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

### 修改 Prompt

所有 LLM Prompt 模板集中在 `app/core/prompts.py` 中，修改后重启服务生效：

| Prompt 变量 | 用途 |
|-------------|------|
| `REWRITE_PROMPT` | 问题改写和关键词提取 |
| `SHORT_ANSWER_PROMPT` | 简要回答生成（≤200 字） |
| `DETAILED_ANSWER_PROMPT` | 详细回答生成（4 段式） |
| `VALIDATE_ACCURACY_PROMPT` | 知识库内容准确性校验 |
| `EXTRACT_QUESTIONS_PROMPT` | 面试文本问题提取 |
| `EXTRACT_ANSWERS_PROMPT` | 面试者回答提取 |
| `EVALUATE_ANSWER_PROMPT` | 5 维回答评估 |
| `OVERALL_SUMMARY_PROMPT` | 复盘整体总结 |
| `IMPROVEMENT_PROMPT` | 提升建议生成 |

### 添加新节点

1. 在 `app/nodes/` 下创建新节点文件，定义 `async def xxx_node(state: dict) -> dict`
2. 在 `app/nodes/__init__.py` 中导出新节点
3. 在对应的 `app/graphs/*/graph.py` 中添加节点并连接边

---

## 使用示例

### 单题解答示例

```bash
# 使用 curl 测试
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "C++ 中虚函数的底层实现原理是什么？",
    "answer_type": "both"
  }'
```

**简答输出示例：**
> 虚函数通过虚函数表（vtable）实现。每个包含虚函数的类都有对应的 vtable，存储虚函数指针；对象实例通过隐含的 vptr 指针指向所属类的 vtable，调用时通过 vptr 找到 vtable 再找到目标函数地址。

**详答结构示例：**
```
📍 知识点定位：属于 C++ 面向对象多态机制的底层实现细节...
🔍 核心原理拆解：1. 编译器为每个含虚函数的类生成 vtable... 2. vptr 初始化时机...
📝 常见考法说明：① 手写验证 vtable 存在 ② vtable 在菱形继承中的布局...
⚠️ 易错点提示：① 误认为 vtable 存储在堆上 ② 混淆 vtable 和 vptr...
```

### 面试复盘示例

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "面试官：说说智能指针的作用。\n面试者：智能指针可以自动管理内存..."
  }'
```

---

## 常见问题 (FAQ)

**Q: 知识库如何更新？**
> 将 C++ 相关文档（PDF/MD/DOCX等）放入 `books/` 目录，然后运行 `python scripts/seed_knowledge.py --rebuild` 即可重建索引。

**Q: 支持哪些 LLM 模型？**
> 目前支持 DeepSeek（默认）、OpenAI、Qwen。在 `.env` 文件中配置 `LLM_PROVIDER` 和 `LLM_API_KEY` 即可切换。

**Q: 回答质量如何保证？**
> 知识库命中时经过准确性校验和时效性校验双重验证；知识库未命中时结合在线搜索结果生成回答；所有回答均标注来源。

**Q: 如何处理非 C++ 问题？**
> 系统会识别问题是否属于 C++ 面试范围，非 C++ 问题将返回错误提示（错误码 1001）。

**Q: Docker 部署失败怎么办？**
> 1. 确认 Docker 和 Docker Compose 已正确安装（`docker --version`）
> 2. 检查 `.env` 文件是否配置了有效的 API Key
> 3. 查看日志 `docker-compose logs -f` 排查具体错误

---

## 性能基准

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 简答响应时间 (P95) | ≤ 5s | 仅返回简要回答时 |
| 详答响应时间 (P95) | ≤ 15s | 返回完整详细回答时 |
| 复盘报告时间 (P95) | ≤ 60s | 5个问题场景下 |
| 并发能力 | ≥ 10 QPS | 单节点 uvicorn 部署 |

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [spec.md](spec.md) | 产品技术规格文档（完整功能设计） |
| [plan.md](plan.md) | 开发计划（里程碑、任务分解） |
| [log/errors.md](log/errors.md) | 项目启动错误记录与修复历史 |
| [tasks/](tasks/) | 各任务详细记录 |

---

## 支持与反馈

- **问题反馈**：请在 GitHub Issues 提交问题
- **功能建议**：欢迎提交 Pull Request 或开启 Discussion
- **技术交流**：欢迎通过 Issue 进行技术讨论

---

## 许可证

MIT License

Copyright (c) 2026 CppInterviewForge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
