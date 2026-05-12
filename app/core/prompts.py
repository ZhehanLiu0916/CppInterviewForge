# Prompt模板 - 所有LLM调用的Prompt定义

# 问题改写Prompt
REWRITE_PROMPT = """你是一个C++面试问题的语义分析专家，负责将用户的面试问题转换为适合向量检索的技术查询。

你的输出将被送入向量数据库做语义搜索，因此 rewritten_query 必须是关键词密集的技术短语，而不是自然语言问句。

要求：
1. 提取核心知识点关键词（5-8个精确的技术术语，包含中英文，如"虚函数 vtable 多态 动态绑定"）
2. rewritten_query 用空格分隔的技术关键词组合，包含同义词、缩写、英文对应词，例如：
   - 用户问"C++里面多态怎么实现的" → "C++ 多态 虚函数 virtual 虚函数表 vtable 动态绑定 运行时多态 继承"
   - 用户问"堆和栈有啥区别" → "堆区 栈区 heap stack 内存管理 动态分配 自动分配 操作系统 性能差异"
   - 用户问"new和malloc区别" → "new malloc C++ 运算符 库函数 内存分配 构造函数 operator 类型安全"

用户问题：{question}

必须以纯JSON格式输出，不要添加markdown代码块标记，不要添加解释文字，直接输出JSON：
{{"keywords": ["术语1", "术语2", "术语3"], "rewritten_query": "关键词1 关键词2 同义词 英文术语 相关概念"}}"""

# 简要回答Prompt
SHORT_ANSWER_PROMPT = """你是一位C++面试辅导专家，正在帮助校招应届生准备C++面试。

请对以下面试问题给出简要回答。

要求：
- 字数严格控制在不超200字
- 仅覆盖核心结论和关键判定标准/核心特性
- 口语化表达，贴合面试场景
- 不要代码示例、不要延伸扩展、不要铺垫性介绍

{source_context}

面试问题：{question}

简要回答："""

# 详细回答Prompt
DETAILED_ANSWER_PROMPT = """你是一位C++面试辅导专家，正在帮助校招应届生系统性掌握C++面试知识点。

请对以下面试问题给出详细回答，严格采用4段式结构：

📍 知识点定位：用1-2句话定位该知识点在C++知识体系中的位置，说明"这是什么"
🔍 核心原理拆解：逐步拆解底层原理，从概念定义→机制说明→关键细节，必要时辅以代码示例（不超过30行）
📝 常见考法说明：列举2-3种面试常见问法变体及其答题要点
⚠️ 易错点提示：列出2-3个考生高频出错的点

注意：回答需匹配校招应届生的知识基础，用循序渐进的方式教学。

{source_context}

面试问题：{question}

详细回答："""

# 准确性校验Prompt
VALIDATE_ACCURACY_PROMPT = """你是一个C++技术审核专家。请判断以下C++知识点描述是否准确。

知识点描述：
{content}

请仅回答JSON格式：
{{
    "is_accurate": true/false,
    "reason": "如果不准确，说明原因"
}}"""

# 在线搜索Prompt（暂未使用，搜索结果直接注入）
# SEARCH_CONTEXT_PROMPT = """..."""

# 面试复盘相关Prompt（M3阶段使用）
EXTRACT_QUESTIONS_PROMPT = """你是面试分析专家。请从以下面试对话文本中提取面试官提出的所有问题。

要求：
1. 区分面试官和面试者的发言
2. 提取面试官提出的每个独立问题
3. 如果有追问/补充说明，合并为主问题的子问题
4. 编号输出

面试对话文本：
{transcript}

必须以纯JSON格式输出，不要添加markdown代码块，直接输出JSON，例如：
{{"questions": [
    {{
        "id": 1,
        "text": "主问题",
        "sub_questions": ["追问1", "追问2"]
    }}
]}}"""

EXTRACT_ANSWERS_PROMPT = """请从以下面试对话中，提取面试者对每个问题的实际回答。

面试问题列表：
{questions}

面试对话文本：
{transcript}

必须以纯JSON格式输出，不要添加markdown代码块，直接输出JSON，例如：
{{"answers": [
    {{
        "question_id": 1,
        "answer_text": "面试者的实际回答内容"
    }}
]}}"""

EVALUATE_ANSWER_PROMPT = """你是一位资深C++面试评估专家。请对比面试者的回答和参考答案，从以下5个维度进行评估：

1. 准确性：关键知识点是否正确
2. 完整性：是否覆盖所有要点
3. 逻辑性：回答是否有条理
4. 专业术语使用：是否使用了准确的专业术语
5. 匹配度：回答是否切题

面试问题：{question}
参考答案简述：{reference_answer}
面试者回答：{interviewee_answer}

请以JSON格式输出：
{{"accuracy": {{
        "score": 1-5,
        "issues": ["具体不足1", "具体不足2"],
        "suggestions": ["优化建议1"]
    }},
    "completeness": {{
        "score": 1-5,
        "issues": [],
        "suggestions": []
    }},
    "logic": {{
        "score": 1-5,
        "issues": [],
        "suggestions": []
    }},
    "terminology": {{
        "score": 1-5,
        "issues": [],
        "suggestions": []
    }},
    "relevance": {{
        "score": 1-5,
        "issues": [],
        "suggestions": []
    }}
}}"""

OVERALL_SUMMARY_PROMPT = """你是一位资深C++面试评估专家。请根据以下各题的评估结果，生成面试复盘总结。

各题评估结果：
{evaluations}

请生成JSON格式输出：
{{"total_score": X.X,
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["不足1", "不足2"],
    "knowledge_distribution": {{
        "C++核心语法": "正确率%",
        "STL标准库": "正确率%",
        "操作系统": "正确率%",
        "计算机网络": "正确率%",
        "数据库": "正确率%",
        "设计模式": "正确率%"
    }},
    "answer_style": "回答风格特点描述"
}}"""

IMPROVEMENT_PROMPT = """你是一位C++面试辅导专家。请根据面试评估结果，给出针对性提升建议。

面试评估结果：
{evaluations}

面试表现总结：
{summary}

请生成JSON格式输出：
{{"priority_directions": [
        {{
            "direction": "需补强的知识方向",
            "topics": ["具体知识点1", "具体知识点2"],
            "reference": "推荐学习资料"
        }}
    ],
    "technique_improvements": ["回答技巧提升建议1", "建议2"],
    "recommended_questions": ["推荐练习题1", "推荐练习题2", "推荐练习题3"],
    "learning_path": ["Step1: ...", "Step2: ...", "Step3: ..."]
}}"""

# 文本预处理Prompt
PREPROCESS_PROMPT = """你是一个面试录音转写文本的处理专家。请对以下面试录音转写文本进行预处理：

1. 口语化内容规整：去除"嗯、啊、就是、然后、那个"等语气词和口头禅
2. 噪音内容过滤：去除无关闲聊、重复内容
3. 说话人分离：标注面试官和面试者的发言

输出格式：每一行以[面试官]或[面试者]开头

原始转写文本：
{transcript}

规整后的文本："""

# 分类标注Prompt（M2阶段使用）
CLASSIFY_PROMPT = """你是一个C++知识分类专家。请对以下知识块进行分类标注。

知识块内容：
{content}

标题信息：
- heading_text: {heading_text}
- parent_heading: {parent_heading}

必须以纯JSON格式输出，不要添加markdown代码块，直接输出JSON，例如：
{{"category": "C++核心语法/STL标准库/操作系统/计算机网络/数据库/设计模式",
    "sub_category": "细分方向（如面向对象-虚函数）",
    "difficulty": "基础/中等/进阶",
    "tags": ["标签1", "标签2", "标签3"]
}}"""
