# M3 任务清单 (2/2): 面试复盘功能 - 接口与异常处理

> 里程碑：M3 - 面试复盘功能
> 周期：Week 7-8
> 任务范围：M3-T11 ~ M3-T12

---

## M3-T11: /review API 接口

**描述与关键实现要点：**
实现面试复盘的HTTP接口，处理请求、调用ReviewGraph、返回结构化报告。
- 路由：`POST /api/v1/review`
- 请求体：
  ```json
  {
    "transcript": "面试录音转写文本（50-50000字）",
    "metadata": {
      "company": "可选-公司名",
      "position": "可选-岗位",
      "date": "可选-面试日期"
    }
  }
  ```
- 响应体：符合spec.md 6.2节定义的5模块结构
- 请求校验：
  - `transcript` 长度50-50000字
  - `metadata` 可选
- 调用 `run_review_graph(transcript, metadata)`
- 流式输出支持：
  - 使用 `async_generator` 逐模块返回
  - 首模块到达时间≤15s
- 响应包含元信息：
  ```json
  {
    "code": 0,
    "message": "success",
    "data": {
      "report": {...},
      "metadata": {
        "company": "...",
        "position": "...",
        "question_count": 5,
        "processing_time_ms": 35000
      }
    }
  }
  ```

**输入/前置依赖：**
- M3-T10（ReviewGraph可运行）
- M1-T13（routes已有）, 更新即可

**产出物：**
- 更新 `app/api/routes.py`
- 更新 `app/models/schemas.py`（ReviewRequest, ReviewResponse模型）

**验收标准：**
- `curl -X POST http://localhost:8000/api/v1/review -H "Content-Type: application/json" -d '{"transcript":"..."}'` 返回完整5模块JSON
- 响应时间≤60s（5个问题）
- 元信息字段完整

---

## M3-T12: 复盘异常处理

**描述与关键实现要点：**
实现复盘功能所有异常场景的处理，确保用户体验和系统稳定性。
- 异常场景清单（根据spec.md 2.3.3）：
  1. **输入文本过短（<50字）**
     - 返回错误码 `1003`
     - 提示："输入文本过短，请提供完整的面试录音转写文本。"
  2. **无法识别面试官/面试者**
     - 尝试语义区分，仍失败则提示用户标注
     - 返回部分结果 + 警告标记
  3. **问题提取结果为0**
     - 返回错误码 `1004`
     - 提示："未识别到面试问题，请确认输入为面试对话文本。"
  4. **单个问题解答超时（>10s）**
     - 标注 `[生成超时]`
     - 继续处理下一题
  5. **部分问题解答失败**
     - 跳过失败问题
     - 报告中标注 `[该题解答失败]`
     - 其他问题正常输出
  6. **输入文本超过token限制**
     - 分段处理，每段≤4000 token
     - 合并结果后生成报告
  7. **整体报告生成超时（>60s）**
     - 返回已生成的部分模块
     - 添加 `[报告因超时截断，请重试获取完整报告]`
- 实现位置：
  - `app/nodes/*.py`：节点内异常捕获和降级
  - `app/graphs/review/graph.py`：条件边处理特殊情况
  - `app/api/routes.py`：统一异常响应格式

**输入/前置依赖：**
- M3-T11（/review接口）
- M3-T2 ~ M3-T10（各节点）

**产出物：**
- 更新各节点和路由的异常处理代码
- 更新 `app/models/schemas.py`（错误响应模型）

**验收标准：**
- 6种异常场景均有正确响应（降级/提示/错误码）
- 异常不影响服务稳定性（不崩溃、不内存泄漏）
- 错误信息用户友好
