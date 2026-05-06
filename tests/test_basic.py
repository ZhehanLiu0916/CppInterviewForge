import pytest
import sys
from pathlib import Path

# 添加项目根目录到sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import_app():
    """测试可以导入app模块。"""
    import app
    assert app is not None


def test_import_question_graph():
    """测试可以导入QuestionGraph。"""
    from app.graphs.question.graph import _get_question_app
    app = _get_question_app()
    assert app is not None


def test_question_state():
    """测试QuestionState定义。"""
    from app.models.state import QuestionState
    state = QuestionState()
    assert "question" in state
    assert "answer_type" in state


def test_answer_type():
    """测试AnswerType定义。"""
    from app.models.schemas import AnswerType
    assert AnswerType.SHORT.value == "short"
    assert AnswerType.DETAILED.value == "detailed"
    assert AnswerType.BOTH.value == "both"


def test_count_chinese_words():
    """测试字数统计函数。"""
    from app.utils.text import count_chinese_words

    # 中文
    assert count_chinese_words("你好世界") == 4
    # 英文
    assert count_chinese_words("Hello World") == 2
    # 混合
    assert count_chinese_words("Hello你好") == 3


def test_truncate_to_word_limit():
    """测试字数截断函数。"""
    from app.utils.text import truncate_to_word_limit

    # 不截断
    text = "你好世界"
    assert truncate_to_word_limit(text, 4) == text

    # 截断
    text = "你好世界Hello"
    result = truncate_to_word_limit(text, 4)
    assert len(result) < len(text)


def test_prompts_exist():
    """测试Prompt模板存在。"""
    from app.core import prompts

    assert hasattr(prompts, "REWRITE_PROMPT")
    assert hasattr(prompts, "SHORT_ANSWER_PROMPT")
    assert hasattr(prompts, "DETAILED_ANSWER_PROMPT")
    assert hasattr(prompts, "VALIDATE_ACCURACY_PROMPT")


def test_settings():
    """测试配置加载。"""
    from app.core.config import settings

    assert settings.LLM_PROVIDER is not None
    assert settings.CHROMA_PERSIST_DIR is not None
    assert settings.EMBEDDING_MODEL is not None
