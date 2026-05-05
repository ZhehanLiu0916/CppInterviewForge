# M2 任务清单: 知识库入库管道 + 质量调优

> 里程碑：M2 - 知识库入库管道 + 质量调优
> 周期：Week 4-5
> 任务范围：M2-T1 ~ M2-T9

---

## M2-T1: MarkItDown 文件转换管道

**描述与关键实现要点：**
实现对多种文档格式的统一转换，输出Markdown文本。
- 创建 `app/services/document_loader.py`
- 支持的文件格式：
  - `.md`: 直接读取返回
  - `.pdf`, `.docx`, `.pptx`, `.html`, `.epub`: 通过MarkItDown转换
  - `.txt`: 尝试段落结构识别
- 核心方法：
  - `scan_books_dir(book_dir)`: 递归扫描目录，返回文件列表
  - `convert_to_markdown(file_path)`: 根据扩展名分派转换
  - `batch_convert(file_paths)`: 批量转换
- 转换后保留元信息：
  - `source`: 原始文件路径
  - `file_type`: 文件类型
- 异常处理：转换失败时记录日志，跳过该文件

**输入/前置依赖：**
- M1-T2（配置管理，获取BOOK_DIR）
- `markitdown` 已安装
- `./books` 目录含待处理文档

**产出物：**
- `app/services/document_loader.py`

**验收标准：**
- 对 `books/` 下所有PDF执行转换，输出md文本
- 输出md文件头部有标题标识
- 转换失败文件被跳过，不中断流程

---

## M2-T2: Markdown 标题层级切分器

**描述与关键实现要点：**
将Markdown文本按标题层级切分为知识块，保持语义完整性。
- 创建 `app/services/chunker.py`
- 切分策略：
  - 首选边界：`##` 二级标题
  - 辅助边界：`###` 三级标题
  - 不跨标题切分，保持语义完整
- Chunk参数：
  - 最大800 tokens，最小50 tokens
  - 超长chunk按段落换行二次切分
  - 过短chunk合并至上级标题chunk
- 输出chunk结构：
  ```python
  {
    "content": "知识点内容...",
    "metadata": {
      "source": "book/STL源码剖析.md",
      "heading_level": 3,
      "heading_text": "vector底层实现",
      "parent_heading": "STL容器"
    }
  }
  ```
- 保留父子标题关联，便于上下文回溯

**输入/前置依赖：**
- M2-T1（转换后的Markdown文本）
- 字数统计工具（M1-T10已实现）

**产出物：**
- `app/services/chunker.py`

**验收标准：**
- 输入md文本 → 输出chunk列表
- 每个chunk < 800 tokens
- 每个chunk包含heading_text和parent_heading元数据

---

## M2-T3: LLM 自动分类标注

**描述与关键实现要点：**
对切分后的chunk进行自动分类，推断category/sub_category/difficulty/tags。
- 创建 `app/services/classifier.py`
- 分类Prompt设计：
  - 输入：chunk内容 + 标题信息
  - 输出JSON：
    ```json
    {
      "category": "C++核心语法",
      "sub_category": "面向对象-虚函数",
      "difficulty": "中等",
      "tags": ["虚函数", "vtable", "多态"]
    }
    ```
- 分类类别：
  - `C++核心语法`, `STL标准库`, `操作系统`, `计算机网络`, `数据库`, `设计模式`
- 使用低成本LLM（DeepSeek-Chat）执行分类
- 批量分类：支持传入chunk列表，并行处理

**输入/前置依赖：**
- M2-T2（切分后的chunk列表）
- M1-T3（LLM适配层）

**产出物：**
- `app/services/classifier.py`
- 更新 `app/core/prompts.py`（添加CLASSIFY_PROMPT）

**验收标准：**
- 100个chunk抽样：category分类准确率≥85%
- 输出tags与内容相关

---

## M2-T4: 批量入库脚本

**描述与关键实现要点：**
实现知识库重建和增量更新脚本，支持一键入库。
- 创建 `scripts/seed_knowledge.py`
- 命令行参数：
  - `--rebuild`: 完全重建（删除旧数据）
  - `--incremental`: 增量更新（仅处理新文件）
  - `--book-dir`: 指定知识库目录（默认配置中的BOOK_DIR）
- 执行流程：
  1. 扫描 `./books` 目录
  2. MarkItDown转换
  3. 标题层级切分
  4. LLM自动分类
  5. Embedding向量化
  6. Chroma批量写入
  7. 去重检测（基于source+heading_text）
- 进度显示：tqdm进度条
- 结果统计：处理文件数、生成chunk数、跳过数

**输入/前置依赖：**
- M2-T1, M2-T2, M2-T3（转换、切分、分类）
- M1-T6（Retriever服务，Chroma写入能力）

**产出物：**
- `scripts/seed_knowledge.py`

**验收标准：**
- 执行后Chroma中chunk数≥200
- 重复执行不产生重复条目
- 执行时间<30分钟（books目录下全部文档）

---

## M2-T5: 全量入库执行

**描述与关键实现要点：**
执行知识库全量入库，确保chunk数和质量达标。
- 执行 `python scripts/seed_knowledge.py --rebuild`
- 监控入库过程：
  - 记录失败文件
  - 检查chunk数量
  - 抽检chunk质量
- 验证入库结果：
  - Chroma count≥650
  - 6大方向均有覆盖
- 记录入库日志和统计信息

**输入/前置依赖：**
- M2-T4（入库脚本）
- `./books` 目录含充足文档

**产出物：**
- 入库日志文件
- Chroma数据库（data/chroma/）

**验收标准：**
- Chroma中chunk数≥650
- 覆盖6大方向：C++核心语法/STL/操作系统/网络/数据库/设计模式
- 抽检5个chunk内容质量合格

---

## M2-T6: Prompt调优 - 简答

**描述与关键实现要点：**
调整 `SHORT_ANSWER_PROMPT`，提高简答质量和字数控制准确性。
- 问题诊断：
  - 收集10-20题简答测试结果
  - 分析字数超标/口语化不足的具体原因
- 调优方向：
  - 强化字数约束提示
  - 明确"核心结论+关键判定标准"结构
  - 禁止代码示例和铺垫性内容
  - 调整temperature参数
- 迭代测试：
  - 每次修改后测试50题
  - 统计合规率变化
- 记录调优过程和最终Prompt版本

**输入/前置依赖：**
- M1-T12（初始Prompt）
- 测试题目集

**产出物：**
- 更新 `app/core/prompts.py`
- 调优记录文档

**验收标准：**
- 50题测试：简答≤200字合规率≥95%
- 口语化程度适中，贴合面试场景

---

## M2-T7: Prompt调优 - 详答

**描述与关键实现要点：**
调整 `DETAILED_ANSWER_PROMPT`，提高详答结构完整度和代码示例适度性。
- 问题诊断：
  - 收集10-20题详答测试结果
  - 分析结构缺失/代码过多/深度不足的问题
- 调优方向：
  - 强化4段式结构约束
  - 控制代码示例长度（<30行）
  - 适配校招应届生知识水平
  - 调整"常见考法"和"易错点"的具体度
- 迭代测试：
  - 每次修改后测试50题
  - 人工评估结构完整度和内容质量
- 记录调优过程和最终Prompt版本

**输入/前置依赖：**
- M1-T12（初始Prompt）
- 测试题目集

**产出物：**
- 更新 `app/core/prompts.py`
- 调优记录文档

**验收标准：**
- 50题测试：详答4段完整率≥95%
- 代码示例适度，不过冗长
- 内容深度适合校招应届生

---

## M2-T8: Prompt调优 - 校验

**描述与关键实现要点：**
调整 `VALIDATE_ACCURACY_PROMPT`，减少误判率。
- 问题诊断：
  - 收集知识库正确内容被误判的案例
  - 分析误判原因（Prompt过于严格/理解偏差）
- 调优方向：
  - 放宽校验标准，减少False Positive
  - 明确"知识点核心准确性"vs"表述细节"
  - 调整校验LLM温度
- 迭代测试：
  - 测试100个知识库条目
  - 统计误判率
- 平衡：误判率vs漏检风险

**输入/前置依赖：**
- M1-T12（初始Prompt）
- 知识库样本条目

**产出物：**
- 更新 `app/core/prompts.py`

**验收标准：**
- 知识库正确内容被误判为不准确的比例≤5%
- 明显错误内容仍能被检出

---

## M2-T9: 检索结果缓存

**描述与关键实现要点：**
实现检索结果缓存，提升高频问题的响应速度。
- 创建 `app/services/cache.py`
- 缓存策略：
  - LRU缓存，最大容量1000
  - TTL=1小时
  - 缓存键：问题hash（可选用rewritten_query）
- 缓存内容：
  - 检索结果列表
  - 最大相似度分数
- 集成点：`retrieve`节点调用检索前先查缓存
- 缓存失效：
  - 知识库更新时清空缓存
  - TTL过期自动失效

**输入/前置依赖：**
- M1-T7（retrieve节点）
- M1-T6（Retriever服务）

**产出物：**
- `app/services/cache.py`
- 更新 `app/nodes/retrieve.py`

**验收标准：**
- 相同问题第二次请求响应时间减少≥50%
- 缓存命中率统计可观测
