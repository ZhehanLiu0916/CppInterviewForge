"""
增强型 PDF 解析器。

解决 MarkItDown 在以下三类 PDF 上的失效问题：
1. 表格/脑图式速查手册 → 基于字体/粗体/坐标重建层级标题
2. Q&A 平铺式面试题 → 正则识别问句边界，自动生成 ### 标题
3. 扫描版 PDF → OCR 引擎回退

所有解析结果均补全 Markdown 标题标记，以复用现有 split_by_headings()。
"""

import logging
import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


# ── 公共接口 ────────────────────────────────────────────────────

def parse_pdf(file_path: str) -> Optional[Dict[str, Any]]:
    """
    解析 PDF 文件，返回带 Markdown 标题的结构化文本。

    Returns:
        dict with keys: content, file_type, source, strategy, page_count
        或 None（解析失败时）
    """
    try:
        import fitz
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed")
        return None

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.error(f"Failed to open PDF: {file_path}, {e}")
        return None

    page_count = doc.page_count
    strategy = _detect_strategy(doc)

    logger.info(f"PDF [{os.path.basename(file_path)}]: {page_count} pages, strategy={strategy}")

    if strategy == "scanned":
        content = _parse_scanned(doc, file_path)
    elif strategy == "qa_flat":
        content = _parse_qa_flat(doc)
    elif strategy == "mindmap":
        content = _parse_mindmap(doc)
    else:
        content = _parse_structured(doc)

    doc.close()

    if not content or len(content.strip()) < 50:
        logger.warning(f"PDF parser produced near-empty output for {file_path}")
        return None

    return {
        "content": content,
        "file_type": "pdf",
        "source": file_path,
        "strategy": strategy,
        "page_count": page_count,
    }


# ── 策略检测 ─────────────────────────────────────────────────────

def _detect_strategy(doc) -> str:
    """根据 PDF 特征自动选择解析策略。"""
    total_text = 0
    font_sizes = []
    bold_count = 0
    regular_count = 0
    BOLD_FLAG = 16
    question_mark_count = 0
    blocks_count = 0

    # 前几页分析（用于扫描/脑图检测）
    for i in range(min(5, doc.page_count)):
        page = doc[i]
        text = page.get_text().strip()
        total_text += len(text)
        blocks = page.get_text("dict")["blocks"]
        blocks_count += len(blocks)
        for b in blocks:
            if b["type"] == 0:
                for line in b["lines"]:
                    for span in line["spans"]:
                        txt = span["text"].strip()
                        if txt:
                            font_sizes.append(span["size"])
                            if span["flags"] & BOLD_FLAG:
                                bold_count += 1
                            else:
                                regular_count += 1

    # 扫描版：几乎无文字
    if total_text < 200:
        return "scanned"

    # 速查手册/脑图：单页或少页 + 海量文本块
    # C++知识点全概括.pdf: 1 page, 980 blocks
    if doc.page_count <= 3 and blocks_count > 100:
        return "mindmap"

    # ── Q&A 检测：采样第 3-10 页（跳过封面和目录）──
    qa_pages_start = min(3, doc.page_count - 1)
    qa_pages_end = min(10, doc.page_count)
    qa_font_sizes = []
    qa_bold = 0
    qa_regular = 0
    qa_qmarks = 0

    for i in range(qa_pages_start, qa_pages_end):
        page = doc[i]
        text = page.get_text().strip()
        qa_qmarks += len(re.findall(r"[？?]", text))
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b["type"] == 0:
                for line in b["lines"]:
                    for span in line["spans"]:
                        txt = span["text"].strip()
                        if txt:
                            qa_font_sizes.append(span["size"])
                            if span["flags"] & BOLD_FLAG:
                                qa_bold += 1
                            else:
                                qa_regular += 1

    qa_size_range = 0
    if len(qa_font_sizes) >= 5:
        unique = sorted(set(qa_font_sizes))
        if len(unique) >= 2:
            qa_size_range = max(unique) - min(unique)

    # Q&A 平铺型：问号多 + 字号统一 + 正文主导
    qa_score = 0
    if doc.page_count >= 5:
        qa_score += 1
    if qa_qmarks >= 3:
        qa_score += 2
    if qa_size_range < 2.5:
        qa_score += 2
    qa_total = qa_bold + qa_regular
    if qa_total > 0 and (qa_bold / qa_total) < 0.3:
        qa_score += 1

    if qa_score >= 4:
        return "qa_flat"

    return "structured"


# ── 标题有效性验证 ───────────────────────────────────────────────

# 明显的非标题模式
_NOT_A_HEADING_RE = re.compile(
    r"^[{}()\[\];,，。！？、；：\"'`\\/*\-+=<>%^&|~@#$!]+$"  # 纯符号
    r"|^\d{1,2}$"                                              # 单个数字
    r"|^[。！，；：、]$"                                        # 单个中文标点
    r"|^[a-zA-Z_]\w*$"                                         # 单个标识符
    r"|^[（(][^）)]*[）)]$"                                    # 纯括号内容
)

# 句子模式（不应作为标题的完整句子）
_SENTENCE_END_RE = re.compile(r"[。！]")

# 表格/目录行模式（面试题名称、题目数量等重复出现的表头）
_TABLE_HEADER_RE = re.compile(
    r"^(面试题名称|题目数量|字数统计|序号|页码|目录|索引|"
    r"名称|数量|描述|备注|说明|作者|日期|版本)$"
)


def _is_valid_heading(text: str) -> bool:
    """检查文本是否适合作为标题（非代码、非完整句子、非符号）。"""
    if len(text) < 2:
        return False
    if len(text) > 60:
        return False
    # 纯符号/单个标识符/单个数字
    if _NOT_A_HEADING_RE.match(text):
        return False
    # 以句号/感叹号结尾 = 完整句子，不是标题
    if _SENTENCE_END_RE.search(text[-3:]):
        return False
    # 表格/目录行
    if _TABLE_HEADER_RE.match(text):
        return False
    # 包含 >2 个 URL
    if text.count("http") > 2:
        return False
    return True


# ── 结构化解析（字号/粗体驱动的层级检测）──────────────────────────

def _parse_structured(doc) -> str:
    """
    基于字体属性重建 Markdown 层级。

    核心逻辑：
    - 粗体短文本 → 潜在标题
    - 大字号短文本 → 潜在标题
    - 编号模式（第X章、X.、X、）→ 标题
    - 代码行 → 自动包裹代码块
    """
    all_lines = _extract_all_lines(doc)

    if not all_lines:
        return ""

    # 统计字号分布，找正文字号
    size_counts = {}
    for ln in all_lines:
        sz = ln["size"]
        size_counts[sz] = size_counts.get(sz, 0) + 1
    sorted_sizes = sorted(size_counts.items(), key=lambda x: -x[1])
    body_size = sorted_sizes[0][0] if sorted_sizes else 10.0

    BOLD_FLAG = 16
    result_lines = []
    prev_page = -1
    prev_y = -1
    in_code_block = False

    for ln in all_lines:
        text = ln["text"]
        size = ln["size"]
        flags = ln["flags"]
        page_num = ln["page"]
        x0 = ln["bbox"][0]
        y0 = ln["bbox"][1]
        y1 = ln["bbox"][3]

        is_bold = bool(flags & BOLD_FLAG)
        # 是否比正文显著大
        is_large = size >= body_size + 1.5

        # 页面分隔
        if page_num != prev_page:
            result_lines.append("")
            prev_page = page_num
            prev_y = -1

        # 段落间距检测（y 坐标跳变 > 25pt）
        if prev_y >= 0 and (y0 - prev_y) > 25:
            result_lines.append("")
        prev_y = y1

        # 代码块检测
        if re.match(r"^\s*(#include|using namespace|int main|class |struct |template<|return |cout |cin |if \(|for \(|while \(|//|/\*)", text):
            if not in_code_block:
                result_lines.append("```cpp")
                in_code_block = True
            result_lines.append(text)
            continue
        elif in_code_block:
            # 判断是否还在代码块中
            if re.match(r"^[a-zA-Z_\{}\[\];\s=\+\-\*/><&|!~%^]+$", text) and len(text) < 80:
                result_lines.append(text)
                continue
            elif re.match(r"^\s*(public|private|protected|virtual|static|const|void|int |char |bool |double |float |long )", text):
                result_lines.append(text)
                continue
            else:
                result_lines.append("```")
                in_code_block = False

        # ── 标题判定 ──

        is_heading = False
        heading_level = 0

        # 规则1：章节编号模式（最可靠）
        chapter_match = re.match(r"^(第[一二三四五六七八九十\d]+[章节篇])\s*(.*)", text)
        section_match = re.match(r"^(\d+[\.、)\s]+)\s*(\S.*)$", text)

        if chapter_match and (is_large or is_bold or len(text) <= 30):
            is_heading = True
            heading_level = 2
        elif section_match and (is_large or is_bold) and _is_valid_heading(text):
            is_heading = True
            heading_level = 3

        # 规则2：粗体且短文本（≤30字符）
        elif is_bold and len(text) <= 30 and _is_valid_heading(text):
            if not re.match(r"^\s*(#include|using|int |char |void |bool |double |float |long |auto |return|if\(|for\(|while\()", text):
                is_heading = True
                heading_level = 2 if (is_large or len(text) <= 12) else 3

        # 规则3：大字号短文本
        elif is_large and len(text) <= 25 and _is_valid_heading(text):
            is_heading = True
            heading_level = 2

        # 规则4：简短左对齐粗体/大字文本 + 内容检查
        elif (is_bold or is_large) and len(text) <= 40 and x0 < 120 and _is_valid_heading(text):
            is_heading = True
            heading_level = 3

        if is_heading:
            prefix = "#" * heading_level
            result_lines.append(f"{prefix} {text}")
        else:
            result_lines.append(text)

    if in_code_block:
        result_lines.append("```")

    return "\n".join(result_lines)


def _extract_all_lines(doc) -> List[Dict[str, Any]]:
    """从 PDF 提取所有带样式的行，自动跳过广告页。"""
    all_lines = []
    for page_num in range(doc.page_count):
        page = doc[page_num]
        text = page.get_text().strip()
        if _is_ad_page(text):
            continue
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b["type"] != 0:
                continue
            for line in b["lines"]:
                spans = line["spans"]
                if not spans:
                    continue
                text_line = "".join(s["text"] for s in spans).strip()
                if not text_line:
                    continue
                first_span = spans[0]
                all_lines.append({
                    "text": text_line,
                    "size": round(first_span["size"], 1),
                    "font": first_span["font"],
                    "flags": first_span["flags"],
                    "bbox": line["bbox"],
                    "page": page_num,
                })
    return all_lines


_AD_KEYWORDS = [
    "linuxidc", "Linux公社", "www.linuxidc", "linuxidc.com",
    "java1234", "down.chinaz", "greenxf",
    "资源来源于网络", "仅用于学习交流", "侵权请联系删除",
]


def _is_ad_page(page_text: str) -> bool:
    """判断是否为广告/赞助商插入页。"""
    if not page_text:
        return False
    lines = [l for l in page_text.split("\n") if l.strip()]
    if not lines:
        return False
    ad_hits = sum(1 for l in lines
                  if any(kw.lower() in l.lower() for kw in _AD_KEYWORDS))
    return ad_hits / len(lines) > 0.5


def _get_page_texts(doc, skip_ads: bool = True) -> List[str]:
    """获取所有非广告页的文本。"""
    texts = []
    for page in doc:
        text = page.get_text().strip()
        if skip_ads and _is_ad_page(text):
            continue
        texts.append(text)
    return texts


# ── Q&A 平铺型解析 ──────────────────────────────────────────────

def _parse_qa_flat(doc) -> str:
    """从无标题的 Q&A 平铺文档中识别问答对并生成 ### 标题。"""
    page_texts = _get_page_texts(doc, skip_ads=True)
    full_text = "\n".join(page_texts)

    lines = full_text.split("\n")

    # 章节标题模式
    section_pattern = re.compile(
        r"^(C\+\+.*|STL.*|内存管理.*|新特性.*|面向对象.*|基础.*|数据结构.*|算法.*|操作系统.*|网络.*|数据库.*)"
        r"$"
    )
    # Q&A 问题边界模式
    question_boundary = re.compile(
        r"[？?]$"  # 以问号结尾
    )
    # 短标题模式（可能是问题的开头）
    short_title = re.compile(
        r"^.{2,60}[：:]$"  # 以冒号结尾的短行
    )
    # 排除可能是代码/关键词/注释的冒号行
    _NOT_A_QUESTION_COLON = re.compile(
        r"^\s*(public|private|protected|virtual|static|const|default|case|class|struct|enum)\s*:$"
        r"|^\s*(运行结果|输出结果|示例代码|参考代码|注意事项|补充说明|注意\s*\w*)\s*[：:]$"
        r"|^\s*(举例|例如|比如|示例|如下图|如下|代码如下)\s*[：:]$"
    )
    # 编号问题模式
    numbered_q = re.compile(
        r"^(\d+)[\.、\)]\s*"  # 数字序号开头
    )

    result = []
    current_section = ""
    in_intro = True
    intro_line_count = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped:
            result.append("")
            continue

        # 章节标题检测
        if section_pattern.match(stripped) and len(stripped) <= 25:
            current_section = stripped
            result.append(f"\n## {stripped}")
            in_intro = False
            continue

        # 跳过介绍部分（前 100 行内且无问号/冒号标题）
        if in_intro:
            intro_line_count += 1
            is_content_start = (
                question_boundary.search(stripped) or
                (short_title.match(stripped) and not _NOT_A_QUESTION_COLON.match(stripped) and
                 not re.search(r"[好大但这那它我你他她]", stripped[:5])) or
                (numbered_q.match(stripped) and question_boundary.search(stripped))
            )
            if is_content_start or intro_line_count > 100:
                in_intro = False
            else:
                # 保留介绍文字但不生成标题
                result.append(stripped)
                continue

        # 检测问题行
        is_question = False
        question_text = stripped

        # 模式A：以问号结尾 → 明确的问题
        if question_boundary.search(stripped):
            is_question = True
        # 模式B：编号 + 短行（可能是问题描述的开头）
        elif numbered_q.match(stripped) and len(stripped) <= 100:
            # 检查后续行是否有问号
            for j in range(i + 1, min(i + 5, len(lines))):
                if question_boundary.search(lines[j]):
                    is_question = True
                    break
        # 模式C：短行以冒号结尾 + 不是代码/关键词
        elif short_title.match(stripped) and len(stripped) <= 80:
            if not _NOT_A_QUESTION_COLON.match(stripped) and \
               not re.match(r"^\s*(#include|using|int |char |void |bool |double |float )", stripped):
                is_question = True

        if is_question:
            # 收集问题和答案直到下一个问题/章节
            qa_lines = [stripped]
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    qa_lines.append("")
                    j += 1
                    continue
                # 遇到下一个章节
                if section_pattern.match(next_line) and len(next_line) <= 25:
                    break
                # 遇到下一个问题
                if question_boundary.search(next_line):
                    break
                if short_title.match(next_line) and len(next_line) <= 80:
                    if not _NOT_A_QUESTION_COLON.match(next_line) and \
                       not re.match(r"^\s*(#include|using|int |char |void |bool )", next_line):
                        break
                qa_lines.append(next_line)
                j += 1

            answer_text = "\n".join(qa_lines).strip()

            # 生成标题：清理问题文本
            clean_q = re.sub(r"[？?]$", "", question_text)
            clean_q = re.sub(r"^\d+[\.、\)]\s*", "", clean_q)
            clean_q = clean_q.rstrip("：:").strip()
            if len(clean_q) > 60:
                clean_q = clean_q[:57] + "..."

            prefix = f"{current_section} - " if current_section else ""
            result.append(f"### {prefix}{clean_q}")
            result.append(answer_text)
            result.append("")

            i = j - 1  # -1 因为 for 循环会 +1
        else:
            result.append(stripped)

    return "\n".join(result)


# ── 脑图/表格速查类型解析 ───────────────────────────────────────

def _parse_mindmap(doc) -> str:
    """
    解析单页/少页的脑图或表格型速查 PDF。

    在脑图 PDF 中，"标题"往往是粗体小字（如 9pt Bold），
    而正文是常规字号（如 10.5pt Regular）。因此以粗体为首要信号。
    """
    all_spans = []

    for page_num in range(doc.page_count):
        page = doc[page_num]
        if _is_ad_page(page.get_text().strip()):
            continue
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b["type"] != 0:
                continue
            for line in b["lines"]:
                for span in line["spans"]:
                    txt = span["text"].strip()
                    if not txt:
                        continue
                    all_spans.append({
                        "text": txt,
                        "size": round(span["size"], 1),
                        "font": span["font"],
                        "flags": span["flags"],
                        "bbox": list(span["bbox"]),
                        "page": page_num,
                    })

    if not all_spans:
        return ""

    BOLD_FLAG = 16

    # 统计字号和粗体分布
    bold_texts = [s for s in all_spans if s["flags"] & BOLD_FLAG]
    regular_texts = [s for s in all_spans if not (s["flags"] & BOLD_FLAG)]

    # 找出 "Bold" 字体的主体字号（标题字号）
    if bold_texts:
        bold_sizes = {}
        for s in bold_texts:
            bold_sizes[s["size"]] = bold_sizes.get(s["size"], 0) + 1
        heading_size = sorted(bold_sizes.items(), key=lambda x: -x[1])[0][0]
    else:
        heading_size = 12

    # 找出 Regular 字体的主体字号（正文字号）
    if regular_texts:
        reg_sizes = {}
        for s in regular_texts:
            reg_sizes[s["size"]] = reg_sizes.get(s["size"], 0) + 1
        body_size = sorted(reg_sizes.items(), key=lambda x: -x[1])[0][0]
    else:
        body_size = 10

    result_lines = []
    prev_page = -1
    last_x0 = 0
    prev_span = None

    for s in all_spans:
        text = s["text"]
        size = s["size"]
        flags = s["flags"]
        is_bold = bool(flags & BOLD_FLAG)
        page_num = s["page"]
        x0, y0, x1, y1 = s["bbox"]

        if page_num != prev_page:
            prev_page = page_num
            result_lines.append("")
            prev_span = None

        # 垂直间距
        if prev_span:
            y_gap = y0 - prev_span["bbox"][3]
            if y_gap > 40:
                result_lines.append("")
            elif y_gap > 12 and abs(x0 - prev_span["bbox"][0]) < 10:
                result_lines.append("")

        # 标题判定（在脑图中，粗体 = 标题标记，但要排除代码片段）
        is_heading = False
        heading_level = 0

        # 排除代码类文本
        _CODE_PATTERN = re.compile(
            r"^[{}()\[\];,.<>=+\-*/%&|^!~]+$"  # 纯符号/运算符
            r"|^\s*(#include|using|int |char |void |bool |double |float |long |auto |return|if\(|for\(|while\()"
            r"|^\s*(public|private|protected|virtual|static|const)\s"
            r"|^[a-zA-Z_]\w*\s*[=;{}()]$"  # 单个标识符+符号
            r"|^\w+\s*\(\s*[^)]*\s*\)\s*[;/{]*\s*$"  # 函数调用/定义
            r"|^\w+\s*\(\s*[^)]*\s*\)\s*//.*$"  # 函数调用+注释
            r"|^throw\s*\([^)]*\)\s*;?\s*$"  # throw语句
            r"|^catch\s*\([^)]*\)\s*$"  # catch块
            r"|^[a-zA-Z_]+\s*::\s*[a-zA-Z_]+\s*$"  # 命名空间限定
        )
        looks_like_code = bool(_CODE_PATTERN.match(text))

        if is_bold and len(text) >= 2 and len(text) <= 30 and _is_valid_heading(text) and not looks_like_code:
            is_heading = True
            heading_level = 2 if len(text) <= 12 else 3
        elif size >= heading_size + 1 and len(text) <= 25 and _is_valid_heading(text):
            is_heading = True
            heading_level = 2

        if is_heading:
            prefix = "#" * heading_level
            result_lines.append(f"{prefix} {text}")
        else:
            result_lines.append(text)

        last_x0 = x0
        prev_span = s

    return "\n".join(result_lines)


# ── 扫描版 OCR 解析 ──────────────────────────────────────────────

def _parse_scanned(doc, file_path: str) -> str:
    """
    OCR 回退：将扫描页渲染为图片后 OCR。

    支持的后端（按优先级）：
    1. PaddleOCR（中文识别最佳）
    2. Tesseract（需安装 tesseract-ocr + chi_sim 语言包）
    3. easyocr
    """
    ocr_backend = None
    ocr = None

    # 检测可用的 OCR 引擎
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)
        ocr_backend = "paddleocr"
        logger.info("Using PaddleOCR for scanned PDF")
    except ImportError:
        pass

    if not ocr_backend:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            ocr_backend = "tesseract"
            logger.info("Using Tesseract for scanned PDF")
        except Exception:
            pass

    if not ocr_backend:
        try:
            import easyocr
            ocr_backend = "easyocr"
            logger.info("Using EasyOCR for scanned PDF")
        except ImportError:
            pass

    if not ocr_backend:
        logger.error(
            "No OCR engine available. Install one of: paddleocr, tesseract, easyocr. "
            "Skipping OCR for scanned PDF."
        )
        return ""

    output_parts = []

    for page_num in range(doc.page_count):
        page = doc[page_num]
        if _is_ad_page(page.get_text().strip()):
            continue
        mat = page.get_pixmap(dpi=300)
        img_bytes = mat.tobytes("png")

        if ocr_backend == "paddleocr":
            from paddleocr import PaddleOCR
            if ocr is None:
                ocr = PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)
            import numpy as np
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(img_bytes))
            img_np = np.array(img)
            result = ocr.ocr(img_np, cls=True)
            if result and result[0]:
                lines = [line[1][0] for line in result[0]]
                page_text = "\n".join(lines)
            else:
                page_text = ""

        elif ocr_backend == "tesseract":
            import pytesseract
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(img_bytes))
            page_text = pytesseract.image_to_string(img, lang="chi_sim+eng")

        elif ocr_backend == "easyocr":
            import easyocr
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(img_bytes))
            import numpy as np
            img_np = np.array(img)
            if ocr is None:
                ocr = easyocr.Reader(["ch_sim", "en"])
            result = ocr.readtext(img_np)
            page_text = "\n".join([r[1] for r in result])

        output_parts.append(page_text)

        if (page_num + 1) % 10 == 0:
            logger.info(f"OCR progress: {page_num + 1}/{doc.page_count} pages")

    full_text = "\n\n".join(output_parts)
    return _postprocess_ocr_text(full_text)


def _postprocess_ocr_text(text: str) -> str:
    """对 OCR 文本做后处理：检测章节标记并补上 Markdown 标题。"""
    lines = text.split("\n")
    result = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append("")
            continue

        if re.match(r"^第[一二三四五六七八九十\d]+[章节]", stripped):
            result.append(f"## {stripped}")
        elif re.match(r"^\d+[\.、]\s*\S", stripped) and len(stripped) <= 60:
            result.append(f"### {stripped}")
        else:
            result.append(stripped)

    return "\n".join(result)
