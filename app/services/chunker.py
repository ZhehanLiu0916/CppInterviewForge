import re
import logging
from typing import List, Dict, Any


logger = logging.getLogger(__name__)


def split_by_headings(
    md_text: str,
    max_tokens: int = 800,
    min_tokens: int = 50,
) -> List[Dict[str, Any]]:
    """按Markdown标题层级切分，无标题时按字数切分。"""
    lines = md_text.split("\n")
    chunks = []
    current_chunk = {"content": "", "heading_level": 0, "heading_text": "", "parent_heading": ""}
    parent_h2 = ""
    has_headings = any(re.match(r"^(#{1,6})\s+(.+)$", line) for line in lines)

    if not has_headings:
        # 无标题结构，按字数切分
        return _split_by_token_limit(md_text, max_tokens, min_tokens)

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()

            # 保存当前chunk
            if current_chunk["content"].strip():
                result = _finalize_chunk(current_chunk, max_tokens, min_tokens)
                if result is not None:
                    chunks.append(result)

            # 更新chunk信息
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
                # h1, h4, h5, h6 作为普通内容
                current_chunk["content"] += line + "\n"
        else:
            current_chunk["content"] += line + "\n"

    # 保存最后一个chunk
    if current_chunk["content"].strip():
        result = _finalize_chunk(current_chunk, max_tokens, min_tokens)
        if result is not None:
            chunks.append(result)

    logger.info(f"Split into {len(chunks)} chunks")
    return chunks


def _finalize_chunk(
    chunk_info: Dict[str, Any], max_tokens: int, min_tokens: int
) -> Dict[str, Any]:
    """完成chunk的最终处理。"""
    content = chunk_info["content"].strip()
    token_count = _estimate_tokens(content)

    # 超长二次切分
    if token_count > max_tokens:
        content = _split_long_chunk(content, max_tokens)
        token_count = _estimate_tokens(content)

    # 过短合并（暂留，由调用方处理）
    if token_count < min_tokens:
        return None

    return {
        "content": content,
        "metadata": {
            "heading_level": chunk_info["heading_level"],
            "heading_text": chunk_info["heading_text"],
            "parent_heading": chunk_info["parent_heading"],
        },
        "token_count": token_count,
    }


def _split_by_token_limit(
    text: str,
    max_tokens: int = 800,
    min_tokens: int = 50,
) -> List[Dict[str, Any]]:
    """无标题时按字数切分为知识块。"""
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    current_tokens = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_tokens = _estimate_tokens(para)
        if current_tokens + para_tokens > max_tokens and current_tokens >= min_tokens:
            chunks.append({
                "content": current.strip(),
                "heading_level": 0,
                "heading_text": "",
                "parent_heading": "",
            })
            current = para + "\n\n"
            current_tokens = para_tokens
        else:
            current += para + "\n\n"
            current_tokens += para_tokens

    if current.strip():
        chunks.append({
            "content": current.strip(),
            "heading_level": 0,
            "heading_text": "",
            "parent_heading": "",
        })

    return chunks


def _estimate_tokens(text: str) -> int:
    """估算token数（中文字符=1token，英文单词=1token）。"""
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    english = len(re.findall(r"[a-zA-Z]+", text))
    return chinese + english


def _split_long_chunk(text: str, max_tokens: int) -> str:
    """按段落换行二次切分超长chunk。"""
    paragraphs = text.split("\n\n")
    result = ""
    current_count = 0

    for para in paragraphs:
        para_count = _estimate_tokens(para)
        if current_count + para_count > max_tokens and result:
            break
        result += para + "\n\n"
        current_count += para_count

    return result.strip() if result else text[:max_tokens * 3]  # 简单截断
