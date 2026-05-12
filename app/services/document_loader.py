"""
文档加载与格式转换。

支持格式：.md, .pdf, .docx, .pptx, .html, .epub, .txt
PDF 文件通过增强型 pdf_parser 处理（字体层级检测 / Q&A 识别 / OCR 回退），
其他格式仍使用 MarkItDown。
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def scan_books_dir(book_dir: str) -> List[str]:
    """递归扫描 books 目录，返回文件列表。"""
    if not os.path.exists(book_dir):
        logger.warning(f"Books dir not found: {book_dir}")
        return []

    supported_ext = {
        ".md", ".markdown",
        ".pdf", ".docx", ".pptx", ".html", ".htm",
        ".epub", ".txt",
    }

    files = []
    for root, _, filenames in os.walk(book_dir):
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in supported_ext:
                files.append(os.path.join(root, fname))

    logger.info(f"Scanned {len(files)} files in {book_dir}")
    return files


def _convert_with_markitdown(file_path: str) -> str:
    """使用 MarkItDown 将非 PDF 文件转为 Markdown。"""
    try:
        from markitdown import MarkItDown

        md = MarkItDown()
        result = md.convert(file_path)
        return result.text_content
    except Exception as e:
        logger.error(f"MarkItDown convert failed for {file_path}: {e}")
        return ""


def _convert_pdf(file_path: str) -> Optional[Dict[str, Any]]:
    """使用增强型 PDF 解析器处理 PDF 文件。"""
    from app.services.pdf_parser import parse_pdf

    result = parse_pdf(file_path)
    if result is None:
        # PDF 解析器失败，回退到 MarkItDown
        logger.warning(f"Enhanced PDF parser failed for {file_path}, falling back to MarkItDown")
        content = _convert_with_markitdown(file_path)
        if not content:
            return None
        return {
            "content": content,
            "file_type": "pdf",
            "source": file_path,
            "strategy": "markitdown_fallback",
        }
    return result


def convert_to_markdown(file_path: str) -> Optional[Dict[str, Any]]:
    """转换单个文件为 Markdown 文本。PDF 走增强解析管线。"""
    ext = Path(file_path).suffix.lower()

    try:
        if ext in (".md", ".markdown"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {
                "content": content,
                "file_type": "md",
                "source": file_path,
            }

        elif ext == ".pdf":
            return _convert_pdf(file_path)

        elif ext in (".docx", ".pptx", ".html", ".htm", ".epub"):
            content = _convert_with_markitdown(file_path)
            if not content:
                return None
            return {
                "content": content,
                "file_type": ext.lstrip("."),
                "source": file_path,
            }

        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return {
                "content": content,
                "file_type": "txt",
                "source": file_path,
            }

        else:
            logger.warning(f"Unsupported file type: {ext}")
            return None

    except Exception as e:
        logger.error(f"Failed to convert {file_path}: {e}")
        return None


async def batch_convert(file_paths: List[str]) -> List[Dict[str, Any]]:
    """批量转换文件。"""
    results = []
    for fp in file_paths:
        logger.info(f"Converting: {fp}")
        result = convert_to_markdown(fp)
        if result:
            results.append(result)
    return results
