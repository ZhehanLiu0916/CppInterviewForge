"""
知识块噪声过滤器。

解决 PDF 附件页（网址目录、广告、版权声明等）混入知识库的问题。
提供规则过滤 + 可扩展的二分类器接口。

规则覆盖：
- URL 密度过高
- 已知垃圾域名
- 常见垃圾短语（"版权所有""网址导航"等）
- 过短或特殊字符比例过高
- 纯目录/索引行
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


# ── 噪声规则定义 ────────────────────────────────────────────────

# 已知垃圾域名（附在 PDF 末尾的网址推广页）
JUNK_DOMAINS = [
    "linuxidc.com",
    "baidu.com/s/",  # 网盘搜索链接
    "pan.baidu.com",  # 网盘分享链接（通常不是知识内容）
    "java1234.com",
    "down.chinaz.com",
    "greenxf.com",
    "jqhtml.com",
    "downcc.com",
    "pc6.com",
    "cr173.com",
    "onlinedown.net",
    "newasp.net",
    "xdowns.com",
]

# 常见垃圾短语关键词
JUNK_PHRASES = [
    "版权所有",
    "网址导航",
    "免责声明",
    "本站所有资源",
    "资源来源于网络",
    "侵权请联系",
    "请及时联系",
    "收集整理",
    "仅用于学习交流",
    "禁止商业用途",
    "微信公众号",
    "扫码关注",
    "加微信",
    "QQ群",
    "QQ交流群",
    "点击下载",
    "免费下载",
    "下载地址",
    "关注公众号",
    "博主微信",
    "个人微信",
    "技术交流群",
    "加群",
]

# URL 正则
URL_PATTERN = re.compile(r"https?://[^\s]{4,}|www\.[^\s]{4,}|ftp://[^\s]{3,}")

# 目录/索引行模式
INDEX_PATTERNS = [
    re.compile(r"^(\d+[\.、\)]\s*){2,}"),  # 多级编号如 "1.2.3 xxx"
    re.compile(r"^[\.\s]*\.{4,}"),          # 点状引导符 "......."
    re.compile(r"^[IVX]+[\.、]\s"),         # 罗马数字编号
]

# 纯非中英文特殊字符比例阈值
SPECIAL_CHAR_THRESHOLD = 0.5

# 最小有效内容长度
MIN_CONTENT_LENGTH = 30


# ── 过滤函数 ────────────────────────────────────────────────────

def filter_noise_chunks(
    chunks: List[Dict[str, Any]],
    aggressive: bool = False,
) -> List[Dict[str, Any]]:
    """
    过滤噪声 chunk。

    Args:
        chunks: 分块列表，每个元素含 content 和 metadata
        aggressive: 是否启用激进过滤（丢弃更多边界块）

    Returns:
        过滤后的 chunk 列表
    """
    kept = []
    stats = {"total": len(chunks), "url_spam": 0, "junk_phrase": 0,
             "too_short": 0, "high_special": 0, "pure_index": 0, "kept": 0}

    for chunk in chunks:
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})

        # 0. 预处理：清洗页眉页脚重复行
        content = _strip_headers_footers(content)

        # 1. 长度检查
        if len(content.strip()) < MIN_CONTENT_LENGTH:
            stats["too_short"] += 1
            logger.debug(f"Discarded too-short chunk: {content[:50]}...")
            continue

        # 2. URL 密度检查
        url_count = len(URL_PATTERN.findall(content))
        text_length = max(len(content), 1)
        url_density = url_count / (text_length / 500)  # 每500字的URL数
        if url_density > 1.5 or (url_count >= 3 and text_length < 600):
            stats["url_spam"] += 1
            logger.debug(f"Discarded URL-spam chunk (density={url_density:.2f})")
            continue

        # 3. 已知垃圾域名检查
        if _contains_junk_domain(content):
            stats["junk_phrase"] += 1
            logger.debug("Discarded chunk with known junk domain")
            continue

        # 4. 垃圾短语检查
        junk_score = _junk_phrase_score(content)
        if junk_score >= 2 or (junk_score >= 1 and len(content) < 200):
            stats["junk_phrase"] += 1
            logger.debug(f"Discarded junk-phrase chunk (score={junk_score})")
            continue

        # 5. 特殊字符比例
        if _special_char_ratio(content) > SPECIAL_CHAR_THRESHOLD:
            stats["high_special"] += 1
            continue

        # 6. 纯目录/索引检测
        if aggressive and _is_pure_index(content):
            stats["pure_index"] += 1
            continue

        # 更新 chunk 内容（可能被 _strip_headers_footers 修改）
        chunk["content"] = content
        kept.append(chunk)

    stats["kept"] = len(kept)
    removed = stats["total"] - stats["kept"]
    if removed > 0:
        logger.info(
            f"Noise filter: removed {removed}/{stats['total']} chunks "
            f"(url={stats['url_spam']}, junk={stats['junk_phrase']}, "
            f"short={stats['too_short']}, special={stats['high_special']})"
        )

    return kept


def _strip_headers_footers(text: str) -> str:
    """删除常见的页眉页脚重复行和水印行。"""
    lines = text.split("\n")
    if len(lines) <= 3:
        return text

    # 扩展的水印/广告行模式
    _WATERMARK_PATTERNS = re.compile(
        r"^.{0,20}("
        r"linuxidc\.com|Linux公社|linuxidc|java1234\.com|down\.chinaz|greenxf\.com"
        r")",
        re.IGNORECASE,
    )

    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append(line)
            continue

        # 纯网址行
        if URL_PATTERN.match(stripped) and len(stripped) <= 80:
            continue
        # 包含网址的短行（水印）
        if URL_PATTERN.search(stripped) and len(stripped) <= 60:
            continue
        # 仅有数字（页码）
        if re.match(r"^\d{1,4}$", stripped):
            continue
        # 微信/公众号推广行
        if re.match(r"^(微信|公众号|关注).{0,20}$", stripped):
            continue
        # 已知水印行
        if _WATERMARK_PATTERNS.match(stripped):
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def _contains_junk_domain(text: str) -> bool:
    """检查文本是否包含已知垃圾域名。"""
    for domain in JUNK_DOMAINS:
        if domain.lower() in text.lower():
            return True
    return False


def _junk_phrase_score(text: str) -> int:
    """计算文本中垃圾短语的出现次数。"""
    score = 0
    for phrase in JUNK_PHRASES:
        if phrase in text:
            score += 1
    return score


def _special_char_ratio(text: str) -> float:
    """计算非中英文特殊字符的比例。"""
    if not text:
        return 1.0
    normal = len(re.findall(r"[一-鿿　-〿＀-￯a-zA-Z0-9\s]", text))
    return 1.0 - (normal / len(text))


def _is_pure_index(content: str) -> bool:
    """判断是否为纯目录/索引页。"""
    lines = content.strip().split("\n")
    if len(lines) < 3:
        return False

    index_line_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for pat in INDEX_PATTERNS:
            if pat.search(stripped):
                index_line_count += 1
                break

    # 如果超过 60% 的行匹配目录模式，则判定为目录
    return index_line_count >= len(lines) * 0.6


# ── 可扩展的二分类器接口 ──────────────────────────────────────────

class NoiseClassifier:
    """
    基于 LLM 的噪声/正文二分类器（可选增强）。

    用法：
        classifier = NoiseClassifier()
        classifier.fit(labeled_samples)   # 可选：few-shot 标注
        result = await classifier.predict(chunk_text)
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self._examples: List[Dict[str, str]] = []

    def add_example(self, text: str, label: str):
        """添加标注样本 (label: 'knowledge' | 'noise')。"""
        self._examples.append({"text": text[:500], "label": label})

    async def predict(self, text: str) -> Dict[str, Any]:
        """
        使用 LLM 判断文本是否为噪声。
        仅在规则过滤器不确定时作为补充。
        """
        if not self._examples:
            # 无样本时的零样本判断
            return {"label": "knowledge", "confidence": 0.0}

        from app.services.llm import get_llm
        from langchain_core.messages import HumanMessage

        llm = get_llm(temperature=0.0, max_tokens=64)

        examples_text = "\n".join(
            f"- [{e['label']}] {e['text'][:200]}" for e in self._examples[:5]
        )

        prompt = (
            "判断以下文本片段是「knowledge」(知识内容) 还是「noise」(广告/噪声)。\n\n"
            f"标注示例:\n{examples_text}\n\n"
            f"待判断文本:\n{text[:500]}\n\n"
            "只回复一个词: knowledge 或 noise"
        )

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            label = "knowledge" if "knowledge" in response.content.lower() else "noise"
            return {"label": label, "confidence": 0.7}
        except Exception as e:
            logger.warning(f"Noise classifier LLM call failed: {e}")
            return {"label": "knowledge", "confidence": 0.0}
