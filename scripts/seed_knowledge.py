#!/usr/bin/env python3
"""
知识库批量入库脚本。

用法：
    python scripts/seed_knowledge.py --rebuild       # 完全重建
    python scripts/seed_knowledge.py --incremental    # 增量更新
    python scripts/seed_knowledge.py --rebuild --noise-strict  # 重建+激进噪声过滤

流水线：
    扫描 → 转换（PDF走增强解析） → 分块 → 噪声过滤 → 分类 → 去重入库
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

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings
from app.services.document_loader import scan_books_dir, batch_convert
from app.services.chunker import split_by_headings
from app.services.classifier import batch_classify
from app.services.retriever import RetrieverService
from app.services.noise_filter import filter_noise_chunks

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def _file_hash(file_path: str) -> str:
    """计算文件 hash 用于增量去重。"""
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _make_chunk_id(source: str, heading: str, content: str) -> str:
    """生成稳定的 chunk ID。"""
    content_sample = content[:200]
    return hashlib.md5(f"{source}:{heading}:{content_sample}".encode()).hexdigest()


async def main():
    parser = argparse.ArgumentParser(description="知识库批量入库脚本")
    parser.add_argument("--rebuild", action="store_true", help="完全重建（删除旧数据）")
    parser.add_argument("--incremental", action="store_true", help="增量更新（仅处理新文件）")
    parser.add_argument("--noise-strict", action="store_true",
                        help="启用激进噪声过滤（额外丢弃目录/索引页）")
    parser.add_argument("--book-dir", default=settings.BOOK_DIR, help="知识库目录")
    args = parser.parse_args()

    if not os.path.exists(args.book_dir):
        logger.error(f"Books dir not found: {args.book_dir}")
        return

    retriever = RetrieverService()
    await retriever.initialize()

    # ── 阶段 1：扫描文件 ──
    logger.info(f"Scanning {args.book_dir}...")
    files = scan_books_dir(args.book_dir)
    logger.info(f"Found {len(files)} files")

    if not files:
        logger.warning("No files to process")
        return

    # ── 阶段 2：转换文件 ──
    logger.info("Converting files to Markdown...")
    converted = await batch_convert(files)
    logger.info(f"Converted {len(converted)} documents")

    # 统计解析策略分布
    strategy_counts = {}
    for doc in converted:
        strategy = doc.get("strategy", "standard")
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
    if strategy_counts:
        logger.info(f"Parse strategies: {strategy_counts}")

    # ── 阶段 3：分块 ──
    logger.info("Chunking documents...")
    all_chunks = []
    for doc in converted:
        chunks = split_by_headings(doc["content"])
        for chunk in chunks:
            chunk["source"] = doc["source"]
            chunk["file_type"] = doc["file_type"]
            # 保留解析策略到 metadata
            if "strategy" in doc:
                chunk.setdefault("metadata", {})
                chunk["metadata"]["parse_strategy"] = doc["strategy"]
        all_chunks.extend(chunks)
    logger.info(f"Total chunks before filtering: {len(all_chunks)}")

    # ── 阶段 4：噪声过滤 ──
    logger.info("Filtering noise chunks...")
    filtered = filter_noise_chunks(all_chunks, aggressive=args.noise_strict)
    logger.info(f"Chunks after noise filter: {len(filtered)} "
                f"(removed {len(all_chunks) - len(filtered)})")

    # ── 阶段 5：分类 ──
    logger.info("Classifying chunks...")
    classified = await batch_classify(filtered)
    logger.info(f"Classified {len(classified)} chunks")

    # ── 阶段 6：准备入库 ──
    ids = []
    documents = []
    metadatas = []

    for chunk in classified:
        content = chunk.get("content", "")
        if not content.strip():
            continue

        source = chunk.get("source", "")
        heading = chunk.get("metadata", {}).get("heading_text", "")

        chunk_id = _make_chunk_id(source, heading, content)

        metadata = chunk.get("metadata", {})
        # ChromaDB 不允许空列表值
        metadata = {k: v for k, v in metadata.items()
                    if not (isinstance(v, list) and len(v) == 0)}

        # 确保来源文件名在 metadata 中（便于检索时同文档多块召回）
        if "source" not in metadata:
            metadata["source"] = os.path.basename(source)

        ids.append(chunk_id)
        documents.append(content)
        metadatas.append(metadata)

    # 去重
    seen_ids = {}
    unique_ids = []
    unique_documents = []
    unique_metadatas = []
    for i, chunk_id in enumerate(ids):
        if chunk_id in seen_ids:
            new_id = hashlib.md5(
                f"{chunk_id}_{seen_ids[chunk_id]}".encode()
            ).hexdigest()
            seen_ids[chunk_id] += 1
            unique_ids.append(new_id)
        else:
            seen_ids[chunk_id] = 1
            unique_ids.append(chunk_id)
        unique_documents.append(documents[i])
        unique_metadatas.append(metadatas[i])

    # ── 阶段 7：入库 ──
    logger.info(f"Adding {len(unique_ids)} unique chunks to Chroma...")
    try:
        if args.rebuild:
            logger.info("Rebuild mode: overwriting collection...")
        await retriever.add_documents(unique_ids, unique_documents, unique_metadatas)
        logger.info(f"Done! Total chunks in DB: {retriever.count()}")
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
