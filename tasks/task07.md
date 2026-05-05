# M4.5 任务清单: 前端演示页面

> 里程碑：M4.5 - 前端演示页面（可选）
> 周期：Week 11（可选，可与M4并行）
> 任务范围：M4.5-T1 ~ M4.5-T8

---

## M4.5-T1: FastAPI 自动文档配置

**描述与关键实现要点：**
配置FastAPI的Swagger UI和ReDoc自动文档，支持API在线调试。
- 更新 `app/main.py`
- 配置FastAPI元数据：
  ```python
  app = FastAPI(
      title="C++面试Agent API",
      description="帮助校招应届生系统性掌握C++面试知识点",
      version="1.0.0",
      docs_url="/docs",      # Swagger UI
      redoc_url="/redoc",    # ReDoc
  )
  ```
- 确保所有路由有正确的Pydantic模型注解
- 配置OAuth2/API Key认证提示（如有）
- 验证Swagger UI可在线调试接口

**输入/前置依赖：**
- M1-T14（FastAPI主应用）
- M1-T13, M3-T11（/ask和/review接口）

**产出物：**
- 更新 `app/main.py`

**验收标准：**
- 访问 `http://localhost:8000/docs` 显示完整API文档
- 可在Swagger UI中直接调试API

---

## M4.5-T2: 静态文件路由

**描述与关键实现要点：**
配置FastAPI静态文件服务，用于托管前端演示页面。
- 创建 `static/` 目录
- 更新 `app/main.py`：
  ```python
  from fastapi.staticfiles import StaticFiles
  app.mount("/static", StaticFiles(directory="static"), name="static")
  ```
- 添加根路径重定向（可选）：
  ```python
  @app.get("/", include_in_schema=False)
  async def root():
      from fastapi.responses import RedirectResponse
      return RedirectResponse(url="/static/demo.html")
  ```
- 测试静态文件访问

**输入/前置依赖：**
- M1-T14（FastAPI主应用）

**产出物：**
- 创建 `static/` 目录
- 更新 `app/main.py`

**验收标准：**
- `GET /static/demo.html` 返回HTML文件
- 根路径重定向正确

---

## M4.5-T3: 演示页面 HTML 结构

**描述与关键实现要点：**
创建演示页面的基础HTML结构，包含两个功能区。
- 创建 `static/demo.html`
- 页面结构：
  ```html
  <!DOCTYPE html>
  <html lang="zh-CN">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>C++面试Agent</title>
    <style>/* 内联CSS */</style>
  </head>
  <body>
    <header>...</header>
    <main>
      <!-- 提问区 -->
      <section id="ask-section">...</section>
      <!-- 复盘区 -->
      <section id="review-section">...</section>
      <!-- API状态显示区 -->
      <section id="status-section">...</section>
    </main>
    <footer>...</footer>
    <script>/* 内联JS */</script>
  </body>
  </html>
  ```
- 提问区元素：
  - 问题输入 `<textarea>`
  - 回答类型选择 `<select>`
  - 提交按钮 `<button>`
  - 结果展示区 `<div id="ask-result">`
- 复盘区元素：
  - 转写文本输入 `<textarea>`
  - 提交按钮 `<button>`
  - 报告展示区 `<div id="review-result">`
- API状态区：
  - 连接状态指示
  - 错误消息显示

**输入/前置依赖：**
- M4.5-T2（静态文件路由）

**产出物：**
- `static/demo.html`

**验收标准：**
- 页面加载无JS错误
- 布局清晰，结构分明
- 移动端访问正常

---

## M4.5-T4: 提问区实现

**描述与关键实现要点：**
实现提问区的交互逻辑，调用 `/ask` API 并展示结果。
- 功能实现：
  1. 获取输入问题
  2. 获取选择的回答类型
  3. 发送请求到 `/api/v1/ask`
  4. 解析响应，展示结果
- 请求示例：
  ```javascript
  async function submitQuestion() {
    const question = document.getElementById('question-input').value;
    const answerType = document.getElementById('answer-type').value;
    
    const response = await fetch(`${BASE_URL}/api/v1/ask`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question, answer_type: answerType})
    });
    
    const data = await response.json();
    displayAskResult(data);
  }
  ```
- 结果展示：
  - 简要回答区域
  - 详细回答区域（4段可折叠）
  - 来源标记显示
- 加载状态：提交后显示loading动画
- 错误处理：显示API返回的错误信息

**输入/前置依赖：**
- M4.5-T3（HTML结构）
- M1-T13（/ask接口可用）

**产出物：**
- 更新 `static/demo.html`（JS部分）

**验收标准：**
- 输入问题点击提交 → 调用 `/ask` API
- 正确展示简答、详答、来源标记
- 错误场景显示提示信息

---

## M4.5-T5: 复盘区实现

**描述与关键实现要点：**
实现复盘区的交互逻辑，调用 `/review` API 并分模块展示报告。
- 功能实现：
  1. 获取转写文本输入
  2. 发送请求到 `/api/v1/review`
  3. 解析响应，分模块展示报告
- 请求示例：
  ```javascript
  async function submitReview() {
    const transcript = document.getElementById('transcript-input').value;
    
    const response = await fetch(`${BASE_URL}/api/v1/review`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({transcript})
    });
    
    const data = await response.json();
    displayReviewResult(data);
  }
  ```
- 报告展示（5模块）：
  1. 面试问题汇总（可折叠列表）
  2. 各问题参考答案（可折叠详情）
  3. 各问题回答评估（表格展示）
  4. 整体面试表现总结
  5. 提升建议
- 使用 `<details><summary>` 实现折叠
- 加载状态：显示进度条或文字提示
- 错误处理：显示API返回的错误信息

**输入/前置依赖：**
- M4.5-T3（HTML结构）
- M3-T11（/review接口可用）

**产出物：**
- 更新 `static/demo.html`（JS部分）

**验收标准：**
- 输入转写文本点击提交 → 调用 `/review` API
- 正确分模块展示5大报告模块
- 每个模块可展开/收起

---

## M4.5-T6: 内联 CSS 样式

**描述与关键实现要点：**
编写极简内联CSS样式，确保页面美观、响应式。
- 样式设计：
  - 布局：CSS Grid/Flexbox
  - 配色：简洁专业（主色#2196F3或类似）
  - 字体：系统默认，无需加载外部字体
  - 响应式：支持移动端和桌面端
- 关键样式：
  ```css
  /* 主布局 */
  body { font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
  
  /* 卡片 */
  .card { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 20px 0; }
  
  /* 结果区域 */
  .result-section { margin-top: 20px; }
  
  /* 加载状态 */
  .loading { opacity: 0.6; pointer-events: none; }
  
  /* 折叠面板 */
  details { border: 1px solid #eee; padding: 10px; margin: 10px 0; }
  summary { cursor: pointer; font-weight: bold; }
  
  /* 响应式 */
  @media (max-width: 768px) { ... }
  ```
- 动画：
  - 加载旋转动画
  - 展开/收起过渡动画
- 总CSS大小≤50KB

**输入/前置依赖：**
- M4.5-T3（HTML结构）

**产出物：**
- 更新 `static/demo.html`（CSS部分）

**验收标准：**
- 移动端和桌面端适配良好
- UI简洁清晰
- 总文件大小≤200KB

---

## M4.5-T7: 错误处理

**描述与关键实现要点：**
实现前端错误处理，提升用户体验。
- 错误场景：
  1. **输入验证**
     - 问题为空：提示"请输入面试问题"
     - 转写文本过短：提示"转写文本至少50字"
  2. **API错误**
     - 显示错误码和错误信息
     - 网络错误：提示"网络连接失败，请重试"
  3. **超时处理**
     - 设置请求超时（如60秒）
     - 超时提示"请求超时，请稍后重试"
  4. **服务器错误**
     - 5xx错误：提示"服务器异常，请稍后重试"
- 实现方式：
  ```javascript
  function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => errorDiv.style.display = 'none', 5000);
  }
  ```
- 禁用重复提交：请求进行中禁用按钮

**输入/前置依赖：**
- M4.5-T4, M4.5-T5（提问区和复盘区实现）

**产出物：**
- 更新 `static/demo.html`

**验收标准：**
- 输入空值时显示错误提示
- API错误显示message内容
- 超时正确提示

---

## M4.5-T8: Docker 集成

**描述与关键实现要点：**
将前端静态文件打包进Docker镜像，支持通过容器访问演示页面。
- 更新 `Dockerfile`：
  ```dockerfile
  COPY static/ ./static/
  ```
- 更新 `docker-compose.yml`（可选卷挂载）：
  ```yaml
  volumes:
    - ./static:/app/static:ro  # 便于开发时热更新
  ```
- 验证容器内访问：
  - 访问 `http://localhost:8000/` 显示演示页面
  - 访问 `http://localhost:8000/static/demo.html` 正常
- 可选：配置nginx处理静态文件（生产环境优化）

**输入/前置依赖：**
- M4-T1, M4-T2（Docker配置）
- M4.5-T2（静态文件路由）

**产出物：**
- 更新 `Dockerfile`
- 更新 `docker-compose.yml`

**验收标准：**
- Docker容器启动后访问根路径可看到前端入口
- `/static/demo.html` 正常加载
- 前端可正常调用后端API
