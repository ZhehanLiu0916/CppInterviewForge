import pytest 
import time 
import asyncio 
from typing import List, Dict 
from concurrent.futures import ThreadPoolExecutor 
import httpx

# 基础URL（性能测试使用） 
BASE_URL = "http://localhost:8000" 


@pytest.fixture(scope="module") 
def client(): 
    """创建httpx客户端。"""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c: 
        yield c 


@pytest.mark.asyncio 
async def test_ask_short_perf(client: httpx.Client): 
    """测试简答响应时间P95≤5s。"""
    questions = [ 
        "什么是RAII？", 
        "C++中智能指针有哪些？", 
        "vector的扩容机制是什么？", 
        "TCP三次握手的过程？", 
        "map和unordered_map的区别？", 
    ] 
    times = await _run_concurrent_requests( 
        client, "/api/v1/ask", 
        [{"question": q, "answer_type": "short"} for q in questions], 
    ) 
    p50 = _percentile(times, 50) 
    p95 = _percentile(times, 95) 
    print(f"\n简答P50: {p50:.2f}s, P95: {p95:.2f}s") 
    assert p95 <= 5.0, f"简答P95={p95:.2f}s > 5s" 


@pytest.mark.asyncio 
async def test_ask_detailed_perf(client: httpx.Client): 
    """测试详答响应时间P95≤15s。"""
    questions = [ 
        "请详细解释C++中的虚函数表", 
        "shared_ptr的实现原理是什么？", 
        "解释一下C++的内存对齐", 
    ] 
    times = await _run_concurrent_requests( 
        client, "/api/v1/ask", 
        [{"question": q, "answer_type": "detailed"} for q in questions], 
    ) 
    p50 = _percentile(times, 50) 
    p95 = _percentile(times, 95) 
    print(f"\n详答P50: {p50:.2f}s, P95: {p95:.2f}s") 
    assert p95 <= 15.0, f"详答P95={p95:.2f}s > 15s" 


@pytest.mark.asyncio 
async def test_review_perf(client: httpx.Client): 
    """测试复盘报告响应时间P95≤60s。"""
    transcript = """ 
[面试官] 请你介绍一下C++中的智能指针。 
[面试者] 智能指针就是自动管理内存的... 
[面试官] shared_ptr和unique_ptr的区别？ 
[面试者] shared_ptr是共享所有权... 
""" 
    times = await _run_concurrent_requests( 
        client, "/api/v1/review", 
        [{"transcript": transcript}] * 3, 
    ) 
    p50 = _percentile(times, 50) 
    p95 = _percentile(times, 95) 
    print(f"\n复盘P50: {p50:.2f}s, P95: {p95:.2f}s") 
    assert p95 <= 60.0, f"复盘P95={p95:.2f}s > 60s" 


@pytest.mark.asyncio 
async def test_concurrency_10qps(client: httpx.Client): 
    """测试10 QPS并发能力。"""
    questions = [f"测试问题{i}" for i in range(10)] 
    payloads = [{"question": q, "answer_type": "short"} for q in questions] 

    start = time.time() 
    responses = await _run_concurrent_requests(client, "/api/v1/ask", payloads) 
    elapsed = time.time() - start 

    success_count = sum(1 for r in responses if r.status_code == 200) 
    qps = success_count / elapsed if elapsed > 0 else 0 

    print(f"\n10 QPS测试: {success_count}/10成功, QPS≈{qps:.1f}, 耗时{elapsed:.2f}s") 
    assert success_count >= 10, f"并发测试失败: {10 - success_count}个请求失败" 
    assert qps >= 5.0, f"QPS={qps:.1f} < 5（建议值）" 


async def _run_concurrent_requests( 
    client: httpx.Client, url: str, payloads: List[Dict], 
) -> List[float]: 
    """并发发送请求并收集响应时间。"""
    from asyncio import gather, create_task 
    from asyncio import Semaphore 

    sem = Semaphore(10)  # 限制并发数 

    async def _single_request(payload: Dict) -> tuple: 
        async with sem: 
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as ac: 
                start = time.time() 
                try: 
                    resp = await ac.post(url, json=payload) 
                    elapsed = time.time() - start 
                    return elapsed, resp.status_code 
                except Exception as e: 
                    return time.time() - start, 500 

    tasks = [create_task(_single_request(p)) for p in payloads] 
    results = await gather(*tasks) 

    return [r[0] for r in results] 


def _percentile(data: List[float], p: int) -> float: 
    """计算百分位数。"""
    if not data: 
        return 0.0 
    sorted_data = sorted(data) 
    k = (len(sorted_data) - 1) * p / 100 
    f = int(k) 
    c = f + 1 if f + 1 < len(sorted_data) else f 
    return sorted_data[c] 
