# CppInterviewForge 项目启动错误记录

启动时间: 2026-05-06

---

## Error 1: ImportError - 无法从 app.api 导入 router

**错误信息:**
```
ImportError: cannot import name 'router' from 'app.api' (/home/admin001/CppInterviewForge/app/api/__init__.py)
```

**原因:**
`app/api/__init__.py` 文件为空，没有从 `app/api/routes.py` 导出 `router`。而 `app/main.py` 第15行执行 `from app.api import router`，导致导入失败。

**修复:**
在 `app/api/__init__.py` 中添加：
```python
from app.api.routes import router
__all__ = ["router"]
```

---

## Error 2: SyntaxError - app/graphs/review/graph.py 每行末尾有多余反引号

**错误信息:**
```
SyntaxError: invalid syntax
```

**原因:**
`app/graphs/review/graph.py` 文件中每一行末尾都有一个多余的反引号字符 `\``，导致 Python 语法解析失败。

**修复:**
删除文件中所有行末尾的反引号字符。

---

## Error 3: ModuleNotFoundError - app/nodes 包缺少 __init__.py

**错误信息:**
```
ModuleNotFoundError: No module named 'app.nodes'
```

**原因:**
`app/nodes/` 目录下没有 `__init__.py` 文件。`app/graphs/question/graph.py` 第6行和 `app/graphs/review/graph.py` 第5行都通过 `from app.nodes import ...` 导入节点模块，但没有 `__init__.py` 使其成为 Python 包。

**修复:**
创建 `app/nodes/__init__.py`，导出所有节点模块：
```python
from app.nodes import (
    rewrite, retrieve, validate, generate, format,
    preprocess, extract_questions, extract_answers,
    evaluate, generate_report,
)
```

---

## Error 4: SyntaxError - app/nodes/format.py 多余括号

**错误信息:**
```
SyntaxError: unmatched ')'
```

**原因:**
`app/nodes/format.py` 第5行：
```python
logger = logging.getLogger(__name__))
```
末尾多了一个右括号 `)`。

**修复:**
改为：
```python
logger = logging.getLogger(__name__)
```

---

## Error 5: SyntaxError - app/nodes/extract_questions.py 行尾反引号

**错误信息:**
```
SyntaxError: invalid syntax
```

**原因:**
`app/nodes/extract_questions.py` 第2-8行末尾有多余的反引号字符。

**修复:**
删除行尾的反引号。

---

## Error 6: SyntaxError - app/nodes/extract_answers.py 行尾反引号

**错误信息:**
```
SyntaxError: invalid syntax
```

**原因:**
`app/nodes/extract_answers.py` 第1-8行末尾有多余的反引号字符。

**修复:**
删除行尾的反引号。

---

## Error 7: SyntaxError - app/nodes/evaluate.py 行尾反引号

**错误信息:**
```
SyntaxError: invalid syntax
```

**原因:**
`app/nodes/evaluate.py` 全部行末尾都有多余的反引号字符。

**修复:**
删除所有行尾的反引号。

---

## Error 8: AttributeError - loguru Logger 对象没有 _runtime 属性

**错误信息:**
```
'Logger' object has no attribute '_runtime'
```

**原因:**
`app/core/logging.py` 中 `InterceptHandler.emit` 方法使用了 loguru 已废弃的内部 API：
```python
logger_opt, logger_name, level, _, _ = logger._runtime._start, record.name, record.levelno, record.msg
logger_opt(logger_name, level, record.getMessage())
```
新版 loguru 不再有 `_runtime` 属性，导致所有通过标准 logging 输出的日志（包括 retriever 初始化日志）触发此错误。

**修复:**
替换为兼容的 loguru API：
```python
class InterceptHandler(standard_logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = standard_logging.currentframe(), 2
        while frame and frame.f_code.co_filename == standard_logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
```

---

## Error 9: NameError（潜在） - searxng_search 引用未定义变量

**错误信息:**
```
NameError: name 'max_chars_per_result' is not defined
```

**原因:**
`app/services/web_search.py` 中 `searxng_search` 函数在第69行引用了 `max_chars_per_result` 变量，但该变量是 `tavily_search` 函数的参数，不在 `searxng_search` 的作用域内。当使用 searxng 搜索引擎时将触发此错误。

**修复:**
在 `searxng_search` 函数签名中添加 `max_chars_per_result: int = 2000` 参数。

---

## Error 10: HuggingFace 网络不可达 - Embedding 模型下载失败

**错误信息:**
```
[Errno 101] Network is unreachable
Failed to initialize Chroma: Cannot send a request, as the client has been closed.
```

**原因:**
默认 embedding 模型 `text2vec-large-chinese` 需要从 huggingface.co 下载，但服务器无法访问 HuggingFace。

**修复:**
1. 在 `.env` 中设置 `HF_ENDPOINT=https://hf-mirror.com` 使用国内镜像
2. 将 `EMBEDDING_MODEL` 改为 `shibing624/text2vec-base-chinese`（镜像可用的模型）
3. 在 `app/main.py` 中将 `HF_ENDPOINT` 环境变量应用到 `os.environ`

---

## Error 11: async/await 不匹配 - RetrieverService 缓存调用

**错误信息:**
不会产生崩溃，但会导致缓存逻辑异常 — `cache.get()` 返回协程对象而非缓存数据，被错误判断为 truthy。

**原因:**
`app/services/retriever.py` 中 `LRUCache.get()` 和 `LRUCache.set()` 是 async 方法，但 `search()` 方法中调用时没有使用 `await`：
```python
cached = cache.get(query, ("semantic",))  # 缺少 await
cache.set(query, ("semantic",), items)     # 缺少 await
```

**修复:**
添加 `await`：
```python
cached = await cache.get(query, ("semantic",))
await cache.set(query, ("semantic",), items)
```

---

## 修复后结果

项目成功启动，health check 返回：
```json
{"status":"healthy","version":"1.0.0","components":{"llm":"connected","chroma":"connected","embedding":"loaded"}}
```

前端页面、Swagger文档均正常访问。
