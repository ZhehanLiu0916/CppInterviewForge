import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def _parse_detailed_answer(raw: str) -> Dict:
    """解析LLM生成的详细回答，提取4段结构。兼容emoji标记和纯文本标题。"""
    sections = {
        "knowledge_positioning": "",
        "core_principle": "",
        "common_exams": "",
        "pitfalls": "",
    }

    # 每段的关键文本标识（不含emoji），按原文预期顺序
    markers = [
        ("knowledge_positioning", "知识点定位"),
        ("core_principle", "核心原理拆解"),
        ("common_exams", "常见考法说明"),
        ("pitfalls", "易错点提示"),
    ]

    # 找到各段落标题在原文中的位置
    # 匹配: [可选emoji+空格+加粗标记] + 标题文本 + [可选冒号]
    positions = []
    for key, marker_text in markers:
        pattern = r"(?:[📍🔍📝⚠️]\s*)?(?:\*\*)?\s*" + re.escape(marker_text) + r"\s*(?:\*\*)?\s*[：:]?"
        for m in re.finditer(pattern, raw):
            positions.append((m.start(), m.end(), key))

    positions.sort()

    if not positions:
        logger.warning("Failed to parse detailed answer, using raw content")
        sections["knowledge_positioning"] = raw[:500]
        return sections

    # 按位置截取各段落内容
    for i, (start, end, key) in enumerate(positions):
        if i + 1 < len(positions):
            content_end = positions[i + 1][0]
        else:
            content_end = len(raw)
        content = raw[end:content_end].strip()
        # 去掉开头的换行和多余空白
        content = re.sub(r"^[\s\n]+", "", content)
        sections[key] = content

    return sections


def _build_metadata(state: Dict) -> Dict:
    """构建知识库元数据（仅知识库来源时）。"""
    metadata = state.get("knowledge_base_metadata", {})
    if not metadata:
        return {}

    return {
        "category": metadata.get("category"),
        "sub_category": metadata.get("sub_category"),
        "difficulty": metadata.get("difficulty"),
    }


async def format_node(state: Dict) -> Dict:
    """格式化输出，解析详细回答并组装来源信息。"""
    answer_type = state.get("answer_type", "both")
    result = {"question": state.get("question", "")}

    # 简要回答
    if answer_type in ("short", "both"):
        result["short_answer"] = {
            "content": state.get("short_answer", ""),
            "word_count": state.get("short_answer_word_count", 0),
        }

    # 详细回答
    if answer_type in ("detailed", "both"):
        raw = state.get("detailed_answer_raw", "")
        result["detailed_answer"] = _parse_detailed_answer(raw)

    # 来源信息
    result["source"] = state.get("source_info", {"type": "ai_generated"})

    # 知识库元数据（仅知识库来源时）
    if result["source"].get("type") == "knowledge_base":
        result["metadata"] = _build_metadata(state)
    else:
        result["metadata"] = None

    logger.debug(f"Format node: source={result['source']['type']}")
    return result
