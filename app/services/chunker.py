"""
Markdown 文档分块器。

核心策略：
1. 有标题结构 → split_by_headings() 按 ##/### 边界切分
2. 无标题结构 → _split_with_overlap() 带重叠滑动窗口切分，不再硬截断
3. 超长 chunk → _split_long_chunk() 递归切分，保证内容不丢失
4. 可选语义分块 → semantic_split() 基于 embedding 断点检测
"""

import re
import logging
from typing import List, Dict, Any, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# 中文友好的分隔符列表：优先按段落、换行、句子边界切分
CN_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", ".", "!", "?", ";", ",", " "]

# 默认分块参数
DEFAULT_CHUNK_SIZE = 2000  # 字符（中文字符 ≈ 2 token，2000 字符 ≈ 4000 token 宽松上限）
DEFAULT_OVERLAP = 200      # 重叠字符数
MIN_CHUNK_SIZE = 50        # 最小有效 chunk


def split_by_headings(
    md_text: str,
    max_tokens: int = 800,
    min_tokens: int = 50,
) -> List[Dict[str, Any]]:
    """按 Markdown 标题层级切分，无标题时改用重叠滑动窗口。"""
    lines = md_text.split("\n")
    chunks = []
    current_chunk = {"content": "", "heading_level": 0, "heading_text": "", "parent_heading": ""}
    parent_h2 = ""
    has_headings = any(re.match(r"^(#{1,6})\s+(.+)$", line) for line in lines)

    if not has_headings:
        return _split_with_overlap(md_text, max_tokens, min_tokens)

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()

            if current_chunk["content"].strip():
                results = _finalize_chunk(current_chunk, max_tokens, min_tokens)
                chunks.extend(results)

            if level == 2:
                parent_h2 = text
                current_chunk = {
                    "content": line + "\n",
                    "heading_level": 2,
                    "heading_text": text,
                    "parent_heading": "",
                }
            elif level == 3:
                current_chunk = {
                    "content": line + "\n",
                    "heading_level": 3,
                    "heading_text": text,
                    "parent_heading": parent_h2,
                }
            else:
                current_chunk["content"] += line + "\n"
        else:
            current_chunk["content"] += line + "\n"

    if current_chunk["content"].strip():
        results = _finalize_chunk(current_chunk, max_tokens, min_tokens)
        chunks.extend(results)

    logger.info(f"split_by_headings: {len(chunks)} chunks from {len(lines)} lines")
    return chunks


def _finalize_chunk(
    chunk_info: Dict[str, Any], max_tokens: int, min_tokens: int
) -> List[Dict[str, Any]]:
    """完成 chunk 的最终处理。超长时递归切分，过短时丢弃。"""
    content = chunk_info["content"].strip()
    token_count = _estimate_tokens(content)

    if token_count <= max_tokens:
        if token_count < min_tokens:
            return []
        return [{
            "content": content,
            "metadata": {
                "heading_level": chunk_info["heading_level"],
                "heading_text": chunk_info["heading_text"],
                "parent_heading": chunk_info["parent_heading"],
            },
            "token_count": token_count,
        }]

    # 超长 → 递归切分，不丢内容
    sub_chunks = _split_long_chunk(content, max_tokens)
    results = []
    for sub in sub_chunks:
        sub_tokens = _estimate_tokens(sub)
        if sub_tokens >= min_tokens:
            results.append({
                "content": sub,
                "metadata": {
                    "heading_level": chunk_info["heading_level"],
                    "heading_text": chunk_info["heading_text"],
                    "parent_heading": chunk_info["parent_heading"],
                },
                "token_count": sub_tokens,
            })
    return results


# ── 重叠滑动窗口切分（替代旧版 _split_by_token_limit）────────────

def _split_with_overlap(
    text: str,
    max_tokens: int = 800,
    min_tokens: int = 50,
) -> List[Dict[str, Any]]:
    """
    无标题结构时的回退切分策略。

    使用 RecursiveCharacterTextSplitter 带重叠切分，
    避免旧版按段落硬截断造成的内容丢失。
    """
    # 将 token 预算转为字符数（约 1 token ≈ 1 中文字符 ≈ 4 英文字符）
    char_size = int(max_tokens * 2.5)  # 宽松估计
    char_overlap = max(int(char_size * 0.1), 50)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=char_size,
        chunk_overlap=char_overlap,
        separators=CN_SEPARATORS,
        keep_separator=True,
        is_separator_regex=False,
    )

    sub_texts = splitter.split_text(text)

    chunks = []
    for sub in sub_texts:
        sub = sub.strip()
        token_count = _estimate_tokens(sub)
        if token_count < min_tokens:
            continue
        chunks.append({
            "content": sub,
            "metadata": {
                "heading_level": 0,
                "heading_text": "",
                "parent_heading": "",
            },
            "token_count": token_count,
        })

    logger.info(f"_split_with_overlap: {len(chunks)} chunks from {len(text)} chars")
    return chunks


def _split_long_chunk(text: str, max_tokens: int) -> List[str]:
    """
    对超长 chunk 进行递归切分。

    不再使用旧版的简单截断（返回前 N 个段落或硬截断至 max_tokens*3 字符），
    而是用 RecursiveCharacterTextSplitter 完整保留所有内容。
    """
    char_size = int(max_tokens * 2.5)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=char_size,
        chunk_overlap=80,
        separators=CN_SEPARATORS,
        keep_separator=True,
        is_separator_regex=False,
    )

    sub_texts = splitter.split_text(text)
    return [s.strip() for s in sub_texts if s.strip()]


# ── 语义分块（可选增强）─────────────────────────────────────────

def semantic_split(
    text: str,
    max_tokens: int = 800,
    min_tokens: int = 50,
    similarity_threshold: float = 0.75,
) -> List[Dict[str, Any]]:
    """
    基于 embedding 相似度的语义分块。

    对无结构的长文档，在相邻句子的 embedding 相似度骤降处断点。
    适合内容密集、无标题标记的文档。

    Args:
        text: 输入文本
        max_tokens: 单块 token 上限
        min_tokens: 单块 token 下限
        similarity_threshold: 低于此相似度视为语义边界
    """
    # 将文本按句子拆分
    sentences = re.split(r"(?<=[。！？；\n])(?=[^\s])", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) <= 3:
        # 文本太短，直接用滑动窗口
        return _split_with_overlap(text, max_tokens, min_tokens)

    # 获取 embedding
    try:
        embeddings = _get_sentence_embeddings(sentences)
    except Exception as e:
        logger.warning(f"Semantic embedding failed, falling back to overlap split: {e}")
        return _split_with_overlap(text, max_tokens, min_tokens)

    # 计算相邻句子相似度，找断点
    breakpoints = []
    for i in range(len(embeddings) - 1):
        sim = _cosine_sim(embeddings[i], embeddings[i + 1])
        if sim < similarity_threshold:
            breakpoints.append(i + 1)  # 在 i 之后断开

    # 按断点聚合句子为 chunk
    chunks = []
    start = 0
    current_tokens = 0
    current_texts = []

    for i, sent in enumerate(sentences):
        sent_tokens = _estimate_tokens(sent)
        is_break = i in breakpoints

        if (current_tokens + sent_tokens > max_tokens and current_tokens >= min_tokens) or \
           (is_break and current_tokens >= min_tokens):
            chunks.append({
                "content": "".join(current_texts),
                "metadata": {"heading_level": 0, "heading_text": "", "parent_heading": ""},
                "token_count": current_tokens,
            })
            current_texts = []
            current_tokens = 0

        current_texts.append(sent)
        current_tokens += sent_tokens

        # 对每个句子的超长内容做二次切分
        while current_tokens > max_tokens * 2:
            # 在中点断点处切分
            mid = len(current_texts) // 2
            first_half = "".join(current_texts[:mid])
            chunks.append({
                "content": first_half,
                "metadata": {"heading_level": 0, "heading_text": "", "parent_heading": ""},
                "token_count": _estimate_tokens(first_half),
            })
            current_texts = current_texts[mid:]
            current_tokens = _estimate_tokens("".join(current_texts))

    if current_texts and current_tokens >= min_tokens:
        chunks.append({
            "content": "".join(current_texts),
            "metadata": {"heading_level": 0, "heading_text": "", "parent_heading": ""},
            "token_count": current_tokens,
        })

    logger.info(f"semantic_split: {len(chunks)} chunks from {len(sentences)} sentences")
    return chunks


def _get_sentence_embeddings(sentences: List[str]) -> List[List[float]]:
    """获取句子 embedding 列表。复用项目已配置的 embedding 模型。"""
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    from app.core.config import settings

    ef = SentenceTransformerEmbeddingFunction(
        model_name=settings.EMBEDDING_MODEL,
        device=settings.EMBEDDING_DEVICE,
    )
    return ef(sentences)


def _cosine_sim(a: List[float], b: List[float]) -> float:
    """余弦相似度。"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── Token 估算 ─────────────────────────────────────────────────

def _estimate_tokens(text: str) -> int:
    """估算 token 数（中文字符=1 token，英文单词=1 token）。"""
    chinese = len(re.findall(r"[一-鿿]", text))
    english = len(re.findall(r"[a-zA-Z]+", text))
    return chinese + english
