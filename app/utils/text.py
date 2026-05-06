import re


def count_chinese_words(text: str) -> int:
    """统计中文字符数（每个中文字符计1）和英文单词数。"""
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    english_words = len(re.findall(r"[a-zA-Z]+", text))
    return chinese_chars + english_words


def truncate_to_word_limit(text: str, max_words: int) -> str:
    """将文本截断到指定字数（中文字符+英文单词）。"""
    if count_chinese_words(text) <= max_words:
        return text

    result = []
    word_count = 0
    for char in text:
        if re.match(r"[\u4e00-\u9fff]", char):
            word_count += 1
            result.append(char)
        elif re.match(r"[a-zA-Z]", char):
            word_count += 1
            result.append(char)
        else:
            if result and re.match(r"[a-zA-Z]", result[-1]):
                word_count += 1
            result.append(char)
        if word_count > max_words:
            break

    return "".join(result).rstrip("，。、！？；：") + "…"
