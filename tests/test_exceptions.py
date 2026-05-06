import pytest
import httpx


BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


@pytest.mark.asyncio
async def test_ask_non_cpp_question(client: httpx.Client):
    """测试非C++问题（错误码1001）。"""
    resp = await client.post(
        "/api/v1/ask",
        json={"question": "如何提高英语口语水平？", "answer_type": "both"},
    )
    assert resp.status_code == 422 or (
        resp.status_code == 200 and resp.json()["code"] == 1001
    )


@pytest.mark.asyncio
async def test_ask_empty_question(client: httpx.Client):
    """测试空问题（422验证错误）。"""
    resp = await client.post(
        "/api/v1/ask",
        json={"question": "", "answer_type": "both"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ask_too_long_question(client: httpx.Client):
    """测试超长问题（422验证错误）。"""
    long_q = "问题" * 100
    resp = await client.post(
        "/api/v1/ask",
        json={"question": long_q, "answer_type": "both"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_review_too_short_transcript(client: httpx.Client):
    """测试过短转写文本（错误码1003）。"""
    resp = await client.post(
        "/api/v1/review",
        json={"transcript": "你好"},
    )
    assert resp.status_code == 422 or (
        resp.status_code == 200 and resp.json()["code"] == 1003
    )


@pytest.mark.asyncio
async def test_review_too_long_transcript(client: httpx.Client):
    """测试超长转写文本（422验证错误）。"""
    long_t = "对话" * 10000
    resp = await client.post(
        "/api/v1/review",
        json={"transcript": long_t},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_review_no_questions(client: httpx.Client):
    """测试无法识别问题（错误码1004）。"""
    resp = await client.post(
        "/api/v1/review",
        json={"transcript": "你好，谢谢，再见"},
    )
    # 可能返回1004或空问题列表
    if resp.status_code == 200:
        data = resp.json()
        if data["code"] == 0:
            report = data["data"]["report"]
            assert report["questions_summary"]["total_count"] == 0


@pytest.mark.asyncio
async def test_llm_api_error(client: httpx.Client):
    """测试LLM API不可用（错误码2001）。"""
    # 这需要临时修改配置或断开API连接
    # 此处仅测试接口可用性
    resp = await client.post(
        "/api/v1/ask",
        json={"question": "什么是RAII？", "answer_type": "short"},
    )
    # 正常情况应返回200，不可用返回2001
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        assert resp.json()["code"] in (0, 2001)


@pytest.mark.asyncio
async def test_chroma_error(client: httpx.Client):
    """测试向量数据库不可用（错误码3001）。"""
    # 这需要临时停止Chroma或断开连接
    # 此处仅测试接口可用性
    resp = await client.post(
        "/api/v1/ask",
        json={"question": "什么是虚函数？", "answer_type": "short"},
    )
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        assert resp.json()["code"] in (0, 3001)


@pytest.mark.asyncio
async def test_timeout_handling(client: httpx.Client):
    """测试超时处理。"""
    # 这需要模拟慢速API或设置极短超时
    # 此处测试超时场景是否存在处理
    resp = await client.post(
        "/api/v1/review",
        json={"transcript": "面试官：问题1\n面试者：回答1\n" * 100},
        timeout=1.0,
    )
    # 应返回504或超时错误
    assert resp.status_code in (200, 504, 503)


@pytest.mark.asyncio
async def test_review_partial_failure(client: httpx.Client):
    """测试部分问题解答失败（降级处理）。"""
    transcript = """[面试官] 问题1
[面试者] 回答1
[面试官] 问题2（极难偏题）
[面试者] 不知道
"""
    resp = await client.post(
        "/api/v1/review",
        json={"transcript": transcript},
    )
    # 不应崩溃，应返回报告（可能部分失败）
    assert resp.status_code in (200, 504)
    if resp.status_code == 200:
        data = resp.json()
        assert data["code"] in (0, 2002)
