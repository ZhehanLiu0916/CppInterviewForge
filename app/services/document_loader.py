import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def scan_books_dir(book_dir: str) -> List[str]:
    """递归扫描books目录，返回文件列表。"""
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
    """使用MarkItDown转换文件为Markdown。"""
    try:
        from markitdown import MarkItDown

        md = MarkItDown()
        result = md.convert(file_path)
        return result.text_content
    except Exception as e:
        logger.error(f"MarkItDown convert failed for {file_path}: {e}")
        return ""


def convert_to_markdown(file_path: str) -> Optional[Dict[str, Any]]:
    """转换单个文件为Markdown文本。"""
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

        elif ext in (".pdf", ".docx", ".pptx", ".html", ".htm", ".epub"):
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
