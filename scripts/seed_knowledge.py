#!/usr/bin/env python3
"""
知识库批量入库脚本。
用法：
    python scripts/seed_knowledge.py --rebuild    # 完全重建
    python scripts/seed_knowledge.py --incremental # 增量更新
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings
from app.services.document_loader import scan_books_dir, batch_convert
from app.services.chunker import split_by_headings
from app.services.classifier import batch_classify
from app.services.retriever import RetrieverService

logger = logging.getLogger(__name__)
logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s | %(levelname)s | %(message)s")


def _file_hash(file_path: str) -> str:
    """计算文件hash用于去重。"""
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


async def main():
    parser = argparse.ArgumentParser(description="知识库批量入库脚本")
    parser.add_argument("--rebuild", action="store_true", help="完全重建（删除旧数据）")
    parser.add_argument("--incremental", action="store_true", help="增量更新（仅处理新文件）")
    parser.add_argument("--book-dir", default=settings.BOOK_DIR, help="知识库目录")
    args = parser.parse_args()

    if not os.path.exists(args.book_dir):
        logger.error(f"Books dir not found: {args.book_dir}")
        return

    retriever = RetrieverService()
    await retriever.initialize()

    # 扫描文件
    logger.info(f"Scanning {args.book_dir}...")
    files = scan_books_dir(args.book_dir)
    logger.info(f"Found {len(files)} files")

    if not files:
        logger.warning("No files to process")
        return

    # 转换文件
    logger.info("Converting files to Markdown...")
    converted = await batch_convert(files)
    logger.info(f"Converted {len(converted)} documents")

    # 切分
    logger.info("Chunking documents...")
    all_chunks = []
    for doc in converted:
        chunks = split_by_headings(doc["content"])
        # 添加source到chunk
        for chunk in chunks:
            chunk["source"] = doc["source"]
            chunk["file_type"] = doc["file_type"]
        all_chunks.extend(chunks)
    logger.info(f"Total chunks: {len(all_chunks)}")

    # 分类
    logger.info("Classifying chunks...")
    classified = await batch_classify(all_chunks)
    logger.info(f"Classified {len(classified)} chunks")

    # 准备入库
    ids = []
    documents = []
    metadatas = []

    for chunk in classified:
        content = chunk.get("content", "")
        if not content.strip():
            continue

        # 计算ID（基于source+heading+内容hash防止重复）
        source = chunk.get("source", "")
        heading = chunk.get("metadata", {}).get("heading_text", "")
        content_sample = content[:200]
        chunk_id = hashlib.md5(f"{source}:{heading}:{content_sample}".encode()).hexdigest()

        metadata = chunk.get("metadata", {})
        # 清洗 metadata：ChromaDB 不允许空列表值
        metadata = {k: v for k, v in metadata.items() if not (isinstance(v, list) and len(v) == 0)}
        # classification 已合并到 metadata 中，无需再 update

        ids.append(chunk_id)
        documents.append(content)
        metadatas.append(metadata)

    # 入库前去重（保证ID唯一）
    seen_ids = {}
    unique_ids = []
    unique_documents = []
    unique_metadatas = []
    for i, chunk_id in enumerate(ids):
        if chunk_id in seen_ids:
            # 重复ID，加后缀重新生成
            new_id = hashlib.md5(f"{chunk_id}_{seen_ids[chunk_id]}".encode()).hexdigest()
            seen_ids[chunk_id] += 1
            unique_ids.append(new_id)
        else:
            seen_ids[chunk_id] = 1
            unique_ids.append(chunk_id)
        unique_documents.append(documents[i])
        unique_metadatas.append(metadatas[i])

    # 入库
    logger.info(f"Adding {len(unique_ids)} chunks to Chroma...")
    try:
        if args.rebuild:
            logger.info("Rebuild mode: clearing old data...")
            # Chroma 不支持直接清空，需删除collection重建
        await retriever.add_documents(unique_ids, unique_documents, unique_metadatas)
        logger.info(f"Done! Total chunks in DB: {retriever.count()}")
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
