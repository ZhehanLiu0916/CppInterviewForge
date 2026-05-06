import json
import logging
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.services.llm import get_llm
from app.core.prompts import CLASSIFY_PROMPT

logger = logging.getLogger(__name__)


async def classify_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """对单个知识块进行分类标注。"""
    content = chunk.get("content", "")
    heading_text = chunk.get("heading_text", "")
    parent_heading = chunk.get("parent_heading", "")

    llm = get_llm(temperature=0.0, max_tokens=256)
    prompt = CLASSIFY_PROMPT.format(
        content=content[:1000],  # 限制输入长度
        heading_text=heading_text,
        parent_heading=parent_heading,
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = json.loads(response.content)
        return {
            "category": result.get("category", "C++核心语法"),
            "sub_category": result.get("sub_category", ""),
            "difficulty": result.get("difficulty", "中等"),
            "tags": result.get("tags", []),
        }
    except json.JSONDecodeError as e:
        logger.warning(f"Classifier JSON parse failed: {e}")
        return _fallback_classify(content)
    except Exception as e:
        logger.error(f"Classifier failed: {e}")
        return _fallback_classify(content)


def _fallback_classify(content: str) -> Dict[str, Any]:
    """基于关键词的降级分类。"""
    content_lower = content.lower()
    
    if any(kw in content_lower for kw in ["vector", "map", "set", "list", "deque", "queue", "stack"]):
        category = "STL标准库"
    elif any(kw in content_lower for kw in ["process", "thread", "mutex", "deadlock", "scheduling", "memory"]):
        category = "操作系统"
    elif any(kw in content_lower for kw in ["tcp", "udp", "http", "socket", "ip", "dns"]):
        category = "计算机网络"
    elif any(kw in content_lower for kw in ["sql", "transaction", "acid", "redis", "mysql"]):
        category = "数据库"
    elif any(kw in content_lower for kw in ["singleton", "factory", "observer", "strategy"]):
        category = "设计模式"
    else:
        category = "C++核心语法"

    return {
        "category": category,
        "sub_category": "",
        "difficulty": "中等",
        "tags": [],
    }


async def batch_classify(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量分类知识块。"""
    results = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Classifying chunk {i+1}/{len(chunks)}")
        classification = await classify_chunk(chunk)
        chunk_with_meta = {**chunk}
        chunk_with_meta["metadata"] = {**chunk.get("metadata", {}), **classification}
        results.append(chunk_with_meta)
    return results
