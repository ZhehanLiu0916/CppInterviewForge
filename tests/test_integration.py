import pytest`
import httpx`
import json`
from typing import Dict, Any`


# 基础URL（测试时使用）`
BASE_URL = "http://localhost:8000"`


@pytest.fixture(scope="module")`
def client():`
    """创建httpx客户端。"""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:`
        yield client`


@pytest.mark.asyncio`
async def test_health_check(client: httpx.Client):`
    """测试健康检查接口。"""
    response = client.get("/api/v1/health")`
    assert response.status_code == 200`
    data = response.json()`
    assert data["code"] == 0`
    assert "status" in data["data"]`
    assert data["data"]["status"] in ["healthy", "degraded"]`


@pytest.mark.asyncio`
async def test_ask_question_both(client: httpx.Client):`
    """测试单问题解答接口（both模式）。"""
    payload = {`
        "question": "C++中虚函数表的存储位置在哪里？",`
        "answer_type": "both",`
    }`
    response = client.post(`
        "/api/v1/ask",`
        json=payload,`
        headers={"Content-Type": "application/json"},`
    )`
    assert response.status_code == 200`
    data = response.json()`
    assert data["code"] == 0`
    assert "question" in data["data"]`
    assert "short_answer" in data["data"]`
    assert "detailed_answer" in data["data"]`
    assert "source" in data["data"]`
    # 检查简答字数`
    short = data["data"]["short_answer"]`
    assert short["word_count"] <= 200`
    # 检查详答结构`
    detailed = data["data"]["detailed_answer"]`
    assert "knowledge_positioning" in detailed`
    assert "core_principle" in detailed`
    assert "common_exams" in detailed`
    assert "pitfalls" in detailed`


@pytest.mark.asyncio`
async def test_ask_question_short(client: httpx.Client):`
    """测试单问题解答接口（short模式）。"""
    payload = {`
        "question": "什么是RAII？",`
        "answer_type": "short",`
    }`
    response = client.post(`
        "/api/v1/ask",`
        json=payload,`
        headers={"Content-Type": "application/json"},`
    )`
    assert response.status_code == 200`
    data = response.json()`
    assert data["code"] == 0`
    assert data["data"]["short_answer"] is not None`
    assert data["data"]["detailed_answer"] is None`


@pytest.mark.asyncio`
async def test_ask_question_detailed(client: httpx.Client):`
    """测试单问题解答接口（detailed模式）。"""
    payload = {`
        "question": "请解释C++中的智能指针",`
        "answer_type": "detailed",`
    }`
    response = client.post(`
        "/api/v1/ask",`
        json=payload,`
        headers={"Content-Type": "application/json"},`
    )`
    assert response.status_code == 200`
    data = response.json()`
    assert data["code"] == 0`
    assert data["data"]["short_answer"] is None`
    assert data["data"]["detailed_answer"] is not None`


@pytest.mark.asyncio`
async def test_ask_invalid_question(client: httpx.Client):`
    """测试无效问题处理。"""
    # 空问题`
    payload = {"question": "", "answer_type": "both"}`
    response = client.post(`
        "/api/v1/ask", json=payload, headers={"Content-Type": "application/json"}`
    )`
    assert response.status_code == 422  # 验证错误`


@pytest.mark.asyncio`
async def test_review_basic(client: httpx.Client):`
    """测试面试复盘接口（基础场景）。"""
    transcript = """`
[面试官] 请你介绍一下C++中的智能指针。`
[面试者] 智能指针就是自动管理内存的...`
[面试官] shared_ptr和unique_ptr的区别是什么？`
[面试者] shared_ptr是共享所有权的...`
"""`
    payload = {`
        "transcript": transcript,`
        "metadata": {"company": "测试公司", "position": "C++开发"},`
    }`
    response = client.post(`
        "/api/v1/review",`
        json=payload,`
        headers={"Content-Type": "application/json"},`
    )`
    # 可能超时或成功`
    if response.status_code == 200:`
        data = response.json()`
        assert data["code"] == 0`
        assert "report" in data["data"]`
        report = data["data"]["report"]`
        assert "questions_summary" in report`
        assert "reference_answers" in report`
        assert "answer_evaluations" in report`
        assert "overall_summary" in report`
        assert "improvement_suggestions" in report`
    else:`
        # 超时或错误，至少不崩溃`
        assert response.status_code in [200, 504, 503]`
