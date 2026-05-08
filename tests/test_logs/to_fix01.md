# 测试失败分析与待修复清单（test01.log）

> 生成时间：2026-05-06
> 来源：`tests/test_logs/test01.log`
> 总测试数：28 | 失败：26 | 成功：2

---

## 一、代码层错误（需修代码）

### 1. `test_question_state` — `AssertionError: assert 'question' in {}`

**文件：** `tests/test_basic.py:26`
**原因：** `QuestionState` 继承自 `dict`，但初始化为空 dict，`"question"` 键不存在。
**当前代码：**
```python
state = QuestionState()
assert "question" in state
```
**待修复：** 改为检验 `QuestionState` 的类型或默认属性，而非检查空 dict 的 key。
**优先级：** 高

---

### 2. `test_answer_type` — `ImportError: cannot import name 'AnswerType' from 'app.models.schemas'`

**文件：** `tests/test_basic.py:32`
**原因：** `app/models/schemas.py` 中根本没有定义 `AnswerType`，测试却在导入它。
**当前代码：**
```python
from app.models.schemas import AnswerType
assert AnswerType.SHORT.value == "short"
```
**待修复：** 在 `app/models/schemas.py` 中定义 `AnswerType` 枚举，或在测试中移除对它的引用。
**优先级：** 高

---

### 3. `test_health_check` — `KeyError: 'code'`

**文件：** `tests/test_integration.py:24`
**原因：** `/api/v1/health` 接口返回格式**没有 `code` 字段**，只有 `status`/`version`/`components`。
**当前代码：**
```python
response = client.get("/api/v1/health")
assert response.status_code == 200
data = response.json()
assert data["code"] == 0  # ← 这里报错
```
**待修复：** 修改测试，改为 `assert data["status"] == "healthy"`，或确认接口是否需要返回 `code` 字段。
**优先级：** 高

---

### 4. `test_ask_question_short` — `KeyError: 'detailed_answer'`

**文件：** `tests/test_integration.py:75`
**原因：** 请求 `answer_type="short"` 时，响应数据中**不返回 `detailed_answer`**，但测试在断言它。
**当前代码：**
```python
assert data["data"]["short_answer"] is not None
assert data["data"]["detailed_answer"] is None  # ← 这里报错
```
**待修复：** `answer_type="short"` 时，`detailed_answer` 字段可能根本不存在于响应中，应改为：
```python
assert "detailed_answer" not in data["data"] or data["data"]["detailed_answer"] is None
```
**优先级：** 中

---

### 5. `test_ask_question_detailed` — `KeyError: 'detailed_answer'`

**文件：** `tests/test_integration.py:85`
**原因：** 同上，请求 `answer_type="detailed"` 时，响应中 `detailed_answer` 字段不存在或结构不对。
**待修复：** 对照 `app/api/routes.py` 中 `/ask` 接口的实际返回结构，修正测试的断言。
**优先级：** 中

---

## 二、测试框架/环境层错误（需修测试或环境）

### 6-12. `TypeError: object Response can't be used in 'await' expression`

**涉及测试：**
- `test_ask_empty_question`（`tests/test_exceptions.py:29`）
- `test_ask_too_long_question`（`tests/test_exceptions.py:40`）
- `test_review_too_short_transcript`（`tests/test_exceptions.py:50`）
- `test_review_too_long_transcript`（`tests/test_exceptions.py:63`）
- `test_review_no_questions`（`tests/test_exceptions.py:73`）
- `test_review_partial_failure`（`tests/test_exceptions.py:136`）

**原因：** `pytest-httpx` 的 `client` fixture 是 **同步的 `httpx.Client`**，但测试函数加了 `@pytest.mark.asyncio` 并用了 `await client.post(...)`。
**当前代码：**
```python
@pytest.mark.asyncio
async def test_ask_empty_question(client: httpx.Client):
    resp = await client.post(...)  # ← httpx.Client 不能 await
```
**待修复：** 去掉 `@pytest.mark.asyncio`，直接用同步调用 `client.post(...)`；或者改用 `httpx.AsyncClient` 并配合 async 测试。
**优先级：** 高

---

### 13-22. `httpcore.ReadTimeout: timed out`

**涉及测试：**
- `test_ask_non_cpp_question`
- `test_ask_too_long_question`
- `test_llm_api_error`
- `test_chroma_error`
- `test_timeout_handling`
- `test_ask_question_both`
- `test_ask_question_short`
- `test_ask_question_detailed`
- `test_review_basic`
- `test_ask_invalid_question`

**原因：** 这些测试需要**真实运行中的服务**（`localhost:8000`），但测试执行时：
1. 服务未启动（tmux 中没有 cif 会话）
2. 或者服务的知识库/API 响应超时（硅基流动 API 在测试环境不可达）
3. `pytest-httpx` 的 mock 没有正确拦截 `httpx` 的异步请求

**待修复：**
- 方案 A（推荐）：使用 `pytest-httpx` 的 mock 功能，拦截对 `http://api.siliconflow.cn` 和 `http://api.tavily.com` 的请求，返回预设 JSON，不依赖真实服务。
- 方案 B：在测试前启动服务（fixture 中启动 uvicorn），测试后关闭。
**优先级：** 中

---

### 23. `test_ask_non_cpp_question` — 非 C++ 问题校验

**文件：** `tests/test_exceptions.py:17`
**原因：** 同上的 `TypeError` + `ReadTimeout`，但本质上该测试检查非 C++ 问题返回错误码 `1001`。
**待修复：** 先修 `TypeError`（去掉 `await`），再修超时问题（mock API 或直接跑服务）。
**优先级：** 中

---

### 24. `test_concurrency_10qps` — `FAILED`

**文件：** `tests/test_perf.py`
**原因：** 性能测试需要真实服务运行，且对硅基流动 API 发起大量并发请求，导致超时或限流。
**待修复：** 用 mock 或确保服务在测试时可达；降低并发数或增加超时时间。
**优先级：** 低

---

## 三、已通过的测试 ✅

| 测试 | 文件 | 状态 |
|------|------|------|
| `test_import_app` | `tests/test_basic.py:9` | ✅ PASSED |
| `test_import_question_graph` | `tests/test_basic.py:15` | ✅ PASSED |
| `test_count_chinese_words` | `tests/test_basic.py:38` | ✅ PASSED |
| `test_truncate_to_word_limit` | `tests/test_basic.py:50` | ✅ PASSED |
| `test_prompts_exist` | `tests/test_basic.py:64` | ✅ PASSED |
| `test_settings` | `tests/test_basic.py:74` | ✅ PASSED |

---

## 四、修复优先级总览

| 优先级 | 编号 | 问题 | 文件 |
|--------|------|------|------|
| 🔴 高 | 1 | `QuestionState` 断言错误 | `tests/test_basic.py` |
| 🔴 高 | 2 | `AnswerType` 未定义 | `app/models/schemas.py` + `tests/test_basic.py` |
| 🔴 高 | 3 | `/health` 返回格式不匹配 | `tests/test_integration.py` |
| 🔴 高 | 6-12 | `await client.post()` TypeError | 所有 `test_exceptions.py` |
| 🟡 中 | 4-5 | `detailed_answer` KeyError | `tests/test_integration.py` |
| 🟡 中 | 13-22 | `ReadTimeout` | 所有集成/性能测试 |
| ⚪ 低 | 24 | 并发性能测试 | `tests/test_perf.py` |

---

## 五、快速修复路径建议

### 路径 A — 先修测试框架（让 26 个测试能跑完不报错）
1. 修 `test_question_state`：改断言方式
2. 修 `test_answer_type`：加 `AnswerType` 枚举 或 删测试
3. 修所有 `test_exceptions.py`：去掉 `@pytest.mark.asyncio` + 去掉 `await`
4. 修 `test_health_check`：改断言字段
5. 修 `test_integration.py`：mock API 或确保服务运行

### 路径 B — 先跑通服务再测集成
1. 确保 `tmux new-session -s cif` 服务在跑
2. 修 `test_exceptions.py` 中的 `TypeError`
3. 再次运行 `pytest tests/ -v`
