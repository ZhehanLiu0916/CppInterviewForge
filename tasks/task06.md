# M4 任务清单: Docker部署 + 测试验收

> 里程碑：M4 - Docker部署 + 测试验收
> 周期：Week 9-10
> 任务范围：M4-T1 ~ M4-T10

---

## M4-T1: Dockerfile 编写

**描述与关键实现要点：**
编写多阶段构建的Dockerfile，确保镜像精简、构建高效。
- 创建 `Dockerfile`
- 多阶段构建：
  ```dockerfile
  # 阶段1：builder
  FROM python:3.11-slim AS builder
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt
  
  # 阶段2：runtime
  FROM python:3.11-slim
  WORKDIR /app
  COPY --from=builder /app/deps /usr/local/lib/python3.11/site-packages
  COPY app/ ./app/
  COPY scripts/ ./scripts/
  COPY static/ ./static/
  
  ENV PYTHONUNBUFFERED=1
  EXPOSE 8000
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- 镜像优化：
  - 使用 `python:3.11-slim` 基础镜像
  - 不复制虚拟环境
  - 排除测试文件和开发依赖
- 预下载Embedding模型（可选，加速首次启动）

**输入/前置依赖：**
- `requirements.txt` 已存在

**产出物：**
- `Dockerfile`

**验收标准：**
- `docker build -t cpp-interview-forge .` 构建成功
- 镜像大小<2GB
- `docker run -p 8000:8000 cpp-interview-forge` 启动成功

---

## M4-T2: docker-compose.yml

**描述与关键实现要点：**
编写docker-compose配置，实现一键启动和便捷管理。
- 创建 `docker-compose.yml`
- 配置内容：
  ```yaml
  version: "3.8"
  services:
    cpp-interview-agent:
      build: .
      ports:
        - "8000:8000"
      env_file:
        - .env
      volumes:
        - ./books:/app/books:ro
        - ./data:/app/data
        - ./logs:/app/logs
      restart: unless-stopped
      healthcheck:
        test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
        interval: 30s
        timeout: 10s
        retries: 3
  ```
- 卷挂载说明：
  - `./books:ro`：知识库文档（只读）
  - `./data`：Chroma数据库持久化
  - `./logs`：日志文件
- 环境变量通过 `.env` 文件注入

**输入/前置依赖：**
- M4-T1（Dockerfile）
- `.env.example` 已存在

**产出物：**
- `docker-compose.yml`

**验收标准：**
- `docker-compose up -d` 一键启动
- 健康检查通过
- `docker-compose down` 正常停止

---

## M4-T3: .env 配置说明

**描述与关键实现要点：**
完善 `.env.example` 注释，确保新用户能快速配置启动。
- 更新 `.env.example`
- 为每个配置项添加详细注释：
  ```env
  # ===== LLM配置 =====
  # LLM提供商：deepseek / openai / qwen
  LLM_PROVIDER=deepseek
  # 对应Provider的API Key
  LLM_API_KEY=sk-xxxxxxxxxxxx
  # ...
  
  # ===== 向量数据库配置 =====
  # Chroma持久化目录
  CHROMA_PERSIST_DIR=./data/chroma
  # ...
  ```
- 添加配置项分组：
  - LLM配置
  - 备选模型配置
  - 向量数据库配置
  - Embedding配置
  - 检索配置
  - 在线搜索配置
  - 服务配置
  - 日志配置
- 添加常见问题说明

**输入/前置依赖：**
- M1-T2（配置管理定义了所有配置项）

**产出物：**
- 更新 `.env.example`

**验收标准：**
- 新用户复制 `.env.example` → `.env` 填写API Key后可启动
- 每项配置有清晰注释说明用途

---

## M4-T4: .gitignore 完善

**描述与关键实现要点：**
完善 `.gitignore`，确保敏感文件和构建产物不进入版本控制。
- 检查现有 `.gitignore`
- 确保排除：
  - `CIFenv/`、`venv/`、`env/`（虚拟环境）
  - `__pycache__/`、`*.pyc`（Python缓存）
  - `data/chroma/`（向量数据库）
  - `.env`（敏感配置）
  - `logs/`（日志文件）
  - `*.key`、`*.pem`（密钥文件）
  - `.DS_Store`、`Thumbs.db`（系统文件）
- 验证：`git status` 不显示应排除的文件

**输入/前置依赖：**
- 项目已有 `.gitignore`

**产出物：**
- 更新 `.gitignore`

**验收标准：**
- `git status` 不显示应排除文件
- 敏感信息不会被误提交

---

## M4-T5: 单元测试

**描述与关键实现要点：**
编写核心模块的单元测试，确保基础功能正确。
- 创建 `tests/test_api.py`（API接口测试）
  - 测试 `/api/v1/health`
  - 测试 `/api/v1/ask` 请求校验
  - 测试 `/api/v1/review` 请求校验
- 创建 `tests/test_nodes.py`（节点测试）
  - 测试 `rewrite_node` 输出格式
  - 测试 `format_node` 解析正确性
  - 测试 `preprocess_node` 文本清洗
- 创建 `tests/test_prompts.py`（Prompt测试）
  - 测试Prompt模板变量完整性
  - 测试输出格式可解析性
- 使用 `pytest-asyncio` 支持异步测试
- Mock外部依赖（LLM API、Chroma）

**输入/前置依赖：**
- M1 ~ M3 代码完成
- `pytest`, `pytest-asyncio` 已安装

**产出物：**
- `tests/test_api.py`
- `tests/test_nodes.py`
- `tests/test_prompts.py`
- `tests/conftest.py`（共享fixtures）

**验收标准：**
- `CIFenv/bin/pytest tests/ -v` 全部通过
- 覆盖核心功能路径

---

## M4-T6: 集成测试

**描述与关键实现要点：**
编写端到端集成测试，验证完整链路可用。
- 创建 `tests/test_integration.py`
- 测试场景：
  1. **单问题解答完整链路**
     - 输入C++面试问题
     - 验证返回简答+详答
     - 验证来源标记正确
  2. **面试复盘完整链路**
     - 输入模拟转写文本
     - 验证返回5模块报告
     - 验证每题都有参考答案
  3. **异常场景处理**
     - 非C++问题返回正确错误码
     - 空输入返回正确错误码
- 使用真实LLM API（或配置mock）
- 使用 `httpx.AsyncClient` 调用API

**输入/前置依赖：**
- M4-T5（单元测试框架）
- 服务可启动

**产出物：**
- `tests/test_integration.py`
- `tests/mock_data.py`（测试数据）

**验收标准：**
- `/ask` 返回完整回答
- `/review` 返回5模块报告
- 异常场景正确处理

---

## M4-T7: 性能测试

**描述与关键实现要点：**
验证系统性能指标达标，包括响应时间和并发能力。
- 创建 `tests/test_perf.py`
- 测试指标：
  1. **响应时间**
     - 简答P95≤5s
     - 详答P95≤15s
     - 复盘报告P95≤60s
  2. **并发能力**
     - 10 QPS持续1分钟无错误
     - 平均响应时间不劣化>20%
  3. **首token时间**
     - 流式输出首token≤2s
- 测试工具：
  - 使用 `locust` 或自定义脚本
  - 收集P50/P95/P99延迟
- 记录测试报告

**输入/前置依赖：**
- 系统已完整部署
- 测试环境配置完成

**产出物：**
- `tests/test_perf.py`
- 性能测试报告

**验收标准：**
- 所有性能指标达标
- 测试报告可追溯

---

## M4-T8: 异常场景回归测试

**描述与关键实现要点：**
验证spec.md中所有异常处理场景的正确性。
- 根据 `spec.md 2.2.3` 和 `spec.md 2.3.3` 列出全部异常场景
- 创建测试用例覆盖：
  - 功能1异常场景（7种）
  - 功能2异常场景（7种）
- 验证每种场景：
  - 返回正确的错误码
  - 返回用户友好的提示信息
  - 不影响服务稳定性
- 记录测试结果

**输入/前置依赖：**
- M4-T5, M4-T6（测试框架）
- spec.md 异常处理定义

**产出物：**
- `tests/test_exceptions.py`
- 异常场景测试报告

**验收标准：**
- 每种异常均有正确降级/提示/错误码
- 无异常导致服务崩溃

---

## M4-T9: 知识库终态确认

**描述与关键实现要点：**
确认知识库达到最终交付状态，包含足够的内容覆盖。
- 检查项：
  1. **数量达标**
     - Chroma count ≥ 650
  2. **方向覆盖**
     - C++核心语法：~200 chunk
     - STL标准库：~120 chunk
     - 操作系统：~100 chunk
     - 计算机网络：~100 chunk
     - 数据库：~80 chunk
     - 设计模式：~50 chunk
  3. **质量抽检**
     - 随机抽检20个chunk内容质量
     - 验证heading和分类正确
  4. **检索可用性**
     - 10个测试问题均能检索到相关内容
- 记录知识库统计信息

**输入/前置依赖：**
- M2-T5（全量入库完成）

**产出物：**
- 知识库统计报告
- Chroma数据库文件

**验收标准：**
- Chroma count≥650
- 6大方向均有覆盖
- 抽检质量合格

---

## M4-T10: 部署验证

**描述与关键实现要点：**
在Docker容器内执行完整功能验证，确保交付可用。
- 验证步骤：
  1. **容器启动**
     - `docker-compose up -d`
     - 健康检查通过
  2. **API功能验证**
     - `GET /api/v1/health` 返回healthy
     - `POST /api/v1/ask` 返回正确回答
     - `POST /api/v1/review` 返回完整报告
  3. **文档可访问**
     - `GET /docs` 显示Swagger UI
     - `GET /redoc` 显示ReDoc
  4. **前端演示（如有）**
     - 访问首页显示演示页面
  5. **日志正常**
     - 检查日志无异常报错
- 记录验证清单和结果

**输入/前置依赖：**
- M4-T1 ~ M4-T9（全部完成）

**产出物：**
- 部署验证清单
- 最终交付确认

**验收标准：**
- 容器内全部接口正常工作
- 无异常日志
- 可直接交付使用
