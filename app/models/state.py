from typing import Optional
from typing import List, Dict, Any


class QuestionState(dict):
    """单问题解答LangGraph状态定义。"""

    question: str
    answer_type: str = "both"

    # rewrite节点输出
    rewritten_query: str = ""
    keywords: List[str] = []

    # retrieve节点输出
    retrieval_results: List[Dict] = []
    max_similarity: float = 0.0
    use_knowledge_base: bool = False

    # validate节点输出
    validation_passed: bool = False
    knowledge_base_content: Optional[str] = None
    knowledge_base_metadata: Optional[Dict] = None

    # web_search节点输出
    online_search_results: Optional[str] = None
    online_search_urls: List[str] = []

    # generate节点输出
    short_answer: str = ""
    short_answer_word_count: int = 0
    detailed_answer_raw: str = ""
    detailed_answer: Dict = {}
    source_info: Dict = {}

    # format节点输出
    source: Dict = {}
    metadata: Optional[Dict] = None

    # error记录
    error: Optional[str] = None


class ReviewState(dict):
    """面试复盘LangGraph状态定义。"""

    raw_transcript: str = ""
    metadata: Optional[Dict] = None

    # preprocess节点输出
    cleaned_transcript: str = ""

    # extract节点输出
    questions: List[Dict] = []
    interviewee_answers: List[Dict] = []

    # answer_questions节点输出
    reference_answers: List[Dict] = []

    # evaluate节点输出
    evaluations: List[Dict] = []

    # report节点输出
    report: Dict = {}

    # error记录
    error: Optional[str] = None
