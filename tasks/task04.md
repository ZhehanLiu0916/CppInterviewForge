# M3 任务清单 (1/2): 面试复盘功能 - 预处理与提取

> 里程碑：M3 - 面试复盘功能
> 周期：Week 6-7
> 任务范围：M3-T1 ~ M3-T10

---

## M3-T1: ReviewState 定义

**描述与关键实现要点：**
定义面试复盘的LangGraph状态结构，包含所有流程节点间传递的数据。
- 在 `app/models/state.py` 中增加 `ReviewState` TypedDict
- 状态字段：
  ```python
  class ReviewState(TypedDict, total=False):
      raw_transcript: str                    # 原始转写文本
      metadata: dict | None                  # 面试元数据
      cleaned_transcript: str                # 预处理后的文本
      questions: list[dict]                  # 提取的问题列表
      interviewee_answers: list[dict]        # 面试者回答列表
      reference_answers: list[dict]          # 参考答案列表
      evaluations: list[dict]                # 评估结果列表
      report: dict                           # 最终报告
      error: str | None                      # 错误信息
  ```
- questions结构：
  ```python
  {"id": 1, "text": "问题文本", "sub_questions": ["追问1", "追问2"]}
  ```
- interviewee_answers结构：
  ```python
  {"question_id": 1, "answer_text": "面试者回答"}
  ```

**输入/前置依赖：**
- M1-T4（LangGraph使用经验）

**产出物：**
- 更新 `app/models/state.py`

**验收标准：**
- TypedDict编译无报错
- 可正确创建和传递状态

---

## M3-T2: 文本预处理节点

**描述与关键实现要点：**
对面试录音转写文本进行清洗和结构化处理。
- 创建 `app/nodes/preprocess.py`
- 处理步骤：
  1. 口语化规整：去除"嗯/啊/就是/然后/那个"等语气词
  2. 噪音过滤：去除无关闲聊、重复内容
  3. 说话人分离：区分面试官/面试者发言
- 实现方式：
  - 使用规则+LLM结合
  - 正则匹配常见语气词模式
  - LLM识别说话人和内容边界
- 输出格式：
  ```
  [面试官] 请介绍一下C++中的智能指针
  [面试者] 智能指针就是自动管理内存的...
  [面试官] shared_ptr和unique_ptr的区别？
  ...
  ```
- 异常处理：分离失败时返回原始文本

**输入/前置依赖：**
- M1-T3（LLM适配层）
- `app/core/prompts.py`（PREPROCESS_PROMPT）

**产出物：**
- `app/nodes/preprocess.py`
- 更新 `app/core/prompts.py`

**验收标准：**
- 测试3份转写文本：语气词过滤率≥90%
- 说话人识别准确率≥85%
- 输出为结构化对话格式

---

## M3-T3: 问题提取节点

**描述与关键实现要点：**
从面试官发言中提取所有独立面试问题。
- 创建 `app/nodes/extract_questions.py`
- 提取逻辑：
  - 遍历面试官发言行
  - 识别提问句式（以"？"结尾、"请问"、"介绍一下"等）
  - 合并追问/补充说明为主问题的sub_questions
  - 自动编号
- LLM辅助：
  - 使用LLM识别问题边界和追问关系
  - Prompt输入：预处理后的结构化对话
  - Prompt输出：JSON格式问题列表
- 异常处理：
  - 未识别到问题时返回空列表和错误标记
  - 部分识别成功时继续处理已识别问题

**输入/前置依赖：**
- M3-T2（预处理后的文本）
- M1-T3（LLM适配层）
- `app/core/prompts.py`（EXTRACT_QUESTIONS_PROMPT）

**产出物：**
- `app/nodes/extract_questions.py`
- 更新 `app/core/prompts.py`

**验收标准：**
- 5份文本测试：问题召回率≥90%
- 追问正确合并到主问题
- 输出问题列表格式正确

---

## M3-T4: 回答提取节点

**描述与关键实现要点：**
从面试者发言中提取每个问题的实际回答。
- 创建 `app/nodes/extract_answers.py`
- 提取逻辑：
  - 根据问题列表定位面试者对应回答
  - 匹配规则：问题后的面试者连续发言
  - 使用LLM辅助关联问题-回答对
- LLM辅助：
  - Prompt输入：问题列表 + 面试者发言
  - Prompt输出：JSON格式回答列表
- 特殊情况处理：
  - 面试者未回答某问题：标记为"[未回答]"
  - 回答跨多个发言片段：合并

**输入/前置依赖：**
- M3-T2（预处理后的文本）
- M3-T3（提取的问题列表）
- M1-T3（LLM适配层）
- `app/core/prompts.py`（EXTRACT_ANSWERS_PROMPT）

**产出物：**
- `app/nodes/extract_answers.py`
- 更新 `app/core/prompts.py`

**验收标准：**
- 5份文本测试：回答-问题对应正确率≥85%
- 未回答问题正确标记

---

## M3-T5: 逐题解答节点

**描述与关键实现要点：**
复用M1的单问题解答功能，为每个问题生成参考答案。
- 在 `app/graphs/review/graph.py` 中实现 `answer_questions` 节点逻辑
- 实现方式：
  - 遍历 `state["questions"]` 列表
  - 对每个问题调用 `run_question_graph(question_text)`
  - 收集返回的参考答案
  - 组装 `reference_answers` 列表
- 并行优化：
  - 使用 `asyncio.gather` 并行调用
  - 单题解答上限10秒，超时标记继续
- 输出结构：
  ```python
  {
    "question_id": 1,
    "question_text": "...",
    "short_answer": {...},
    "detailed_answer": {...},
    "source": {...}
  }
  ```

**输入/前置依赖：**
- M3-T3（问题列表）
- M1-T13（/ask接口，run_question_graph函数）

**产出物：**
- 更新 `app/graphs/review/graph.py`

**验收标准：**
- 5题测试：每题均有简答+详答，无遗漏
- 解答失败问题正确标记，不影响其他问题

---

## M3-T6: 5维评估 Prompt

**描述与关键实现要点：**
设计5维度评估Prompt，用于对比面试者回答和参考答案。
- 更新 `app/core/prompts.py`
- 评估维度：
  1. **准确性**：关键知识点是否正确（1-5分）
  2. **完整性**：是否覆盖所有要点（1-5分）
  3. **逻辑性**：回答是否有条理（1-5分）
  4. **专业术语使用**：是否使用准确术语（1-5分）
  5. **匹配度**：回答是否切题（1-5分）
- 每维度包含：
  - 评分（1-5）
  - 具体不足之处（分点）
  - 针对性优化建议
- Prompt输出格式：
  ```json
  {
    "accuracy": {"score": 3, "issues": [...], "suggestions": [...]},
    "completeness": {"score": 4, "issues": [...], "suggestions": [...]},
    "logic": {"score": 5, "issues": [], "suggestions": []},
    "terminology": {"score": 2, "issues": [...], "suggestions": [...]},
    "relevance": {"score": 4, "issues": [...], "suggestions": [...]}
  }
  ```

**输入/前置依赖：**
- 无（可并行开发）

**产出物：**
- 更新 `app/core/prompts.py`（EVALUATE_ANSWER_PROMPT）

**验收标准：**
- 10题人工对比：LLM评分与人工评分偏差≤1分
- 输出格式稳定可解析

---

## M3-T7: 逐题对比评估节点

**描述与关键实现要点：**
对比面试者回答和参考答案，输出5维评估结果。
- 创建 `app/nodes/evaluate.py`
- 实现逻辑：
  - 遍历问题和对应的参考答案/面试者回答
  - 调用LLM执行评估Prompt
  - 解析评估结果
  - 计算综合评分（5维度平均）
- 并行处理：
  - 使用 `asyncio.gather` 并行评估多题
- 异常处理：
  - 评估失败时标记默认分数，记录错误
- 输出结构：
  ```python
  {
    "question_id": 1,
    "question_text": "...",
    "interviewee_summary": "面试者回答摘要",
    "scores": {
      "accuracy": {"score": 3, "issues": [...], "suggestions": [...]},
      ...
    },
    "overall_score": 3.4
  }
  ```

**输入/前置依赖：**
- M3-T5（参考答案列表）
- M3-T4（面试者回答列表）
- M3-T6（评估Prompt）

**产出物：**
- `app/nodes/evaluate.py`

**验收标准：**
- 输出每题5维度评分+issues+suggestions
- 综合评分计算正确
- 评估失败时有降级处理

---

## M3-T8: 整体总结 Prompt

**描述与关键实现要点：**
设计整体面试表现总结和提升建议的Prompt。
- 更新 `app/core/prompts.py`
- 包含两个Prompt：
  1. `OVERALL_SUMMARY_PROMPT`：生成整体表现总结
     - 输入：各题评估结果
     - 输出：
       ```json
       {
         "total_score": 3.2,
         "strengths": ["优势1", "优势2"],
         "weaknesses": ["不足1", "不足2"],
         "knowledge_distribution": {
           "C++核心语法": "60%",
           "STL标准库": "40%",
           ...
         },
         "answer_style": "回答风格特点描述"
       }
       ```
  2. `IMPROVEMENT_PROMPT`：生成提升建议
     - 输入：评估结果 + 整体总结
     - 输出：
       ```json
       {
         "priority_directions": [
           {"direction": "方向", "topics": [...], "reference": "..."}
         ],
         "technique_improvements": ["建议1", "建议2"],
         "recommended_questions": ["推荐题1", ...],
         "learning_path": ["Step1: ...", "Step2: ..."]
       }
       „`

**输入/前置依赖：**
- 无（可并行开发）

**产出物：**
- 更新 `app/core/prompts.py`

**验收标准：**
- 总结与各题评估结果一致，不矛盾
- 提升建议可执行、有针对性

---

## M3-T9: 报告生成节点

**描述与关键实现要点：**
组装完整的5模块复盘报告。
- 创建 `app/nodes/generate_report.py`
- 5大模块组装：
  1. **面试问题汇总**：问题列表+追问
  2. **各问题参考答案**：每题简答+详答
  3. **各问题回答评估**：5维度评分+不足+建议
  4. **整体面试表现总结**：调用OVERALL_SUMMARY_PROMPT
  5. **提升建议**：调用IMPROVEMENT_PROMPT
- 组装逻辑：
  - 前3个模块直接使用已有数据
  - 后2个模块调用LLM生成
- 输出完整report结构：
  ```python
  {
    "questions_summary": {...},
    "reference_answers": [...],
    "answer_evaluations": [...],
    "overall_summary": {...},
    "improvement_suggestions": {...}
  }
  ```

**输入/前置依赖：**
- M3-T5（参考答案）
- M3-T7（评估结果）
- M3-T8（总结和建议Prompt）

**产出物：**
- `app/nodes/generate_report.py`

**验收标准：**
- 输出严格包含5个模块，无缺失
- 各模块数据格式符合spec.md定义

---

## M3-T10: ReviewGraph 组装

**描述与关键实现要点：**
将所有复盘功能节点组装为完整的LangGraph图。
- 完善 `app/graphs/review/graph.py`
- 节点顺序：
  ```
  preprocess 
    → {extract_questions, extract_answers}(并行)
    → answer_questions 
    → evaluate 
    → generate_report 
    → END
  ```
- 使用LangGraph的并行节点API：
  - `preprocess` 后同时启动问题提取和回答提取
  - `extract_questions` 完成后启动 `answer_questions`
  - 两个提取分支汇合后进行评估
- 条件边：
  - `extract_questions` 返回空列表时直接结束（未识别到问题）
- 实现 `run_review_graph(transcript, metadata)` 入口函数

**输入/前置依赖：**
- M3-T2 ~ M3-T9（所有节点实现）

**产出物：**
- 完整 `app/graphs/review/graph.py`

**验收标准：**
- `graph.compile()` 无报错
- 可绘制mermaid流程图
- 入口函数可正常调用
