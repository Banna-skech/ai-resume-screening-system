# AI 简历筛选系统 — 实现详解

> 一份给 HR 和技术同学看的完整实现文档，解释这个系统怎么建、为什么这么建、每一层做了什么。

---

## 目录

1. [为什么要用 Agent 思路](#1-为什么要用-agent-思路)
2. [系统架构总览](#2-系统架构总览)
3. [三个 Agent 怎么工作的](#3-三个-agent-怎么工作的)
   - [Agent ① 岗位画像 Agent](#agent--岗位画像-agent)
   - [Agent ② 简历解析 Agent](#agent--简历解析-agent)
   - [Agent ③ 标签匹配 Agent](#agent--标签匹配-agent)
4. [Pipeline 编排层 —— 为什么做双保险](#4-pipeline-编排层--为什么做双保险)
5. [评分算法详解](#5-评分算法详解)
6. [数据模型设计](#6-数据模型设计)
7. [Streamlit 界面设计](#7-streamlit-界面设计)
8. [部署与运行](#8-部署与运行)
9. [如何迭代优化](#9-如何迭代优化)

---

## 1. 为什么要用 Agent 思路

### 传统关键词筛选的问题

大多数简历筛选工具做的事是关键词匹配：JD 里写"Python"，就在简历里搜"Python"，匹配到了加分，没匹配到扣分。这让 HR 很痛苦：

- **只看字面不看语义**：简历里写"Django/Flask"但没写"Python"，关键词匹配会判定"不匹配 Python"
- **不能理解程度**：简历写"熟悉 Python"和"精通 Python"，关键词匹配看成同一回事
- **没有全局判断**：学历不达标但技能突出的候选人，关键词工具一刀切干掉，HR 根本看不到
- **无法解释为什么**：给你一个分数但不说为什么，HR 没办法判断这个分数可不可信

### Agent 思路怎么解决问题

这个系统把筛选拆成三个各司其职的 Agent，每个 Agent 对应一个 HR 真实的思维步骤：

```
传统 HR 筛简历的思维过程：
  "这个岗位到底要什么人？" → Agent ① 岗位画像
  "这份简历写了什么？"     → Agent ② 简历解析
  "这人跟岗位匹不匹配？"   → Agent ③ 标签匹配

传统工具：
  搜关键词 → 给分数 → 排序 → 没了
```

**关键区别**：Agent 不是让模型"给简历打分"，而是让模型扮演 HR 角色，经历"理解岗位 → 读懂简历 → 多维评估"的完整思维链。每一步都有结构化输出，每一步都留下可审计的中间产物。

---

## 2. 系统架构总览

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Web UI                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 首页看板  │ │ 岗位画像  │ │ 简历筛选  │ │ 筛选结果  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
├─────────────────────────────────────────────────────────┤
│                  Pipeline 编排层                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  BatchProcessor (批量)                               │ │
│  │    └→ PipelineOrchestrator.process_one() (单份)      │ │
│  │         ├─ Step1: 文档解析 (PDF/Word → 文本)         │ │
│  │         ├─ Step2: Agent② 简历解析 (文本 → 结构化)    │ │
│  │         ├─ Step3: Agent③ 标签匹配 (画像+简历 → 分数) │ │
│  │         └─ Step4: 分数重算 + 硬性要求兜底             │ │
│  └────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                   三个 AI Agent                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ Agent①       │ │ Agent②       │ │ Agent③       │    │
│  │ 岗位画像      │ │ 简历解析      │ │ 标签匹配      │    │
│  │ JD→结构化模板 │ │ 文本→标准字段 │ │ 多维打分+标签 │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
├─────────────────────────────────────────────────────────┤
│                    基础设施层                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │文档解析   │ │模板管理   │ │报告导出   │ │配置中心   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

| 层 | 技术 | 为什么选它 |
|---|------|----------|
| 大模型 | DeepSeek (via OpenAI SDK) | 性价比高，中文能力强，JSON 模式稳定 |
| 前端 | Streamlit | 纯 Python 写 Web，零前端代码，HR 友好 |
| 数据模型 | Pydantic v2 | LLM 输出 JSON → 自动验证 → Python 对象，一步到位 |
| 文档解析 | pdfminer.six + python-docx | 覆盖 PDF 和 Word 两种最常用格式 |
| 报告 | openpyxl → Excel | HR 标准工具，多 Sheet 汇总/明细/技能矩阵 |
| 重试 | tenacity | LLM 偶尔返回异常 JSON，自动重试保底 |

### 数据怎么流转

```
一份简历的完整旅程：

上传 PDF
  │
  ▼
services/document_parser.py
  提取文本："张三，男，28岁，北京大学硕士..."
  │
  ▼
Agent② ResumeParsingAgent
  LLM 解析 → ParsedResume {
    candidate_name: "张三",
    education: [{degree: "硕士", school: "北京大学", ...}],
    skills: ["Python", "PyTorch", "SQL", ...],
    total_years_experience: 5.0,
    ...
  }
  │
  ▼
Agent③ TagMatchingAgent
  LLM 匹配 → MatchResult {
    dimension_scores: [
      {dimension: "skills", score: 85, details: [{reason: "精通Python", impact: "positive"}, ...]},
      {dimension: "experience", score: 72, details: [...]},
      ...
    ],
    tags: [{tag: "985硕士", match: true}, {tag: "Python精通", match: true}, ...],
    overall_score: 78.5,
    decision: "pass",
    llm_explanation: "候选人综合素质优秀..."
  }
  │
  ▼
PipelineOrchestrator 后处理
  - 代码重算 overall_score（防止 LLM 算错加权）
  - 应用硬性要求惩罚规则
  - 输出最终决策
  │
  ▼
Excel 报告 + UI 展示
```

---

## 3. 三个 Agent 怎么工作的

### Agent 的设计原则

三个 Agent 共用一个基类 `BaseAgent`（`agents/base.py`），这个基类封装了：

1. **DeepSeek API 客户端**：通过 OpenAI SDK 调用（DeepSeek 兼容 OpenAI 接口格式）
2. **JSON 模式强制输出**：调用时设置 `response_format={"type": "json_object"}`，确保 LLM 返回合法 JSON
3. **重试机制**：如果 JSON 解析失败，自动重试（最多 3 次，指数退避：2s → 4s → 10s）
4. **Pydantic 验证**：`_call_llm_with_schema()` 方法直接把 LLM 输出的 JSON 注入 Pydantic 模型——字段类型不对、缺少必填字段都会抛异常，不会让脏数据流到下游
5. **自我修复**：如果 JSON 被 ```json ``` 包裹，自动剥离后再解析

```python
# agents/base.py 核心调用链 (简化示意)

class BaseAgent:
    def _call_llm(self, system_prompt, user_prompt) -> dict:
        # 1. 调用 DeepSeek API，response_format={"type": "json_object"}
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            temperature=0.1,           # 低温度保证稳定输出
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        # 2. 解析 JSON
        return json.loads(response.choices[0].message.content)

    def _call_llm_with_schema(self, system_prompt, user_prompt, model_class):
        # 3. 用 Pydantic 模型验证
        data = self._call_llm(system_prompt, user_prompt)
        return model_class(**data)  # 类型不匹配/缺字段 → 抛异常 → 自动重试
```

---

### Agent ① 岗位画像 Agent

**文件**: `agents/job_profile_agent.py`

**它做什么**：把 HR 粘贴的岗位描述（JD）变成一份结构化的"岗位画像模板"。

**为什么这么做**：

JD 都是自由文本，同一个要求有无数种写法："要会 Python" = "精通 Python 编程" = "具备 Python 开发能力"。如果不先结构化，后面的匹配 Agent 就无从下手。这个 Agent 相当于给每个岗位配一个"小助手"，把模糊的 JD 翻译成机器可理解的规格书。

**输入**：原始 JD 文本
```
岗位名称：高级 Python 开发工程师
岗位职责：
1. 负责后端微服务架构设计与开发
2. 参与数据中台建设
任职要求：
1. 本科及以上学历，计算机相关专业
2. 5年以上 Python 开发经验
3. 精通 Django/FastAPI 等主流框架
4. 熟悉 MySQL、Redis、Elasticsearch
...
```

**输出**：结构化 JobProfile
```json
{
  "job_title": "高级 Python 开发工程师",
  "hard_requirements": [
    {"category": "education", "requirement": "本科及以上学历，计算机相关专业", "is_mandatory": true},
    {"category": "years_of_experience", "requirement": "5年以上 Python 开发经验", "is_mandatory": true}
  ],
  "core_skills": [
    {"name": "Python", "proficiency": "精通", "weight": 3.0},
    {"name": "Django/FastAPI", "proficiency": "精通", "weight": 2.5},
    {"name": "MySQL", "proficiency": "熟悉", "weight": 1.5},
    {"name": "Redis", "proficiency": "熟悉", "weight": 1.5},
    {"name": "微服务架构", "proficiency": "掌握", "weight": 2.0},
    {"name": "Elasticsearch", "proficiency": "了解", "weight": 1.0}
  ],
  "project_experience": [
    {"domain": "后端微服务", "description": "有微服务架构设计与开发经验", "required_skills": ["Python", "FastAPI", "Docker"]},
    {"domain": "数据中台", "description": "参与过数据平台/中台建设项目", "required_skills": ["SQL", "ETL"]}
  ],
  "industry_background": {
    "industry": "互联网/软件",
    "preferred_subfields": ["企业服务", "数据平台"],
    "importance": "nice_to_have"
  }
}
```

**Prompt 设计思路**：

- 角色设定为"专业的 HR 岗位分析师"，而非通用的"AI 助手"
- JSON Schema 内嵌在 prompt 里，每个字段都有中文注释和例值
- `weight` 权重有明确的语义锚点：3.0 = 必备核心技能，2.0 = 重要辅助，1.0 = 加分项。不是让模型瞎猜，而是给它一个可参照的标尺
- `proficiency` 限定为四个选项：了解/熟悉/掌握/精通——这样后面的匹配 Agent 在做技能对比时有统一的语言

**后处理**：

```python
# 代码兜底：确保 hard_requirements 至少包含 education 和 years_of_experience
# 即使 LLM 漏掉了，代码也会补上默认值
categories = {hr.category for hr in profile.hard_requirements}
if "education" not in categories:
    profile.hard_requirements.append(HardRequirement(
        category="education",
        requirement="本科及以上学历",
        is_mandatory=True,
    ))
```

---

### Agent ② 简历解析 Agent

**文件**: `agents/resume_parsing_agent.py`

**它做什么**：把 PDF/Word 提取出的纯文本，变成结构化的标准字段。

**为什么这么做**：

简历格式千差万别——有人把技能写在一个表格里，有人散落在项目描述中，有人把教育经历放在最前面，有人放在最后。HR 手动看一份要 3-5 分钟，100 份就是 5-8 小时。这个 Agent 相当于替 HR 做了"逐行读简历并填表"的工作，3 秒钟一份。

**输入**：从 PDF/Word 提取的纯文本
```
张三
手机：138xxxx | 邮箱：zhangsan@email.com

教育经历
2018-2021 北京大学 计算机科学 硕士
2014-2018 武汉大学 软件工程 本科

工作经历
2021-至今 字节跳动 高级后端开发工程师
- 负责用户画像服务架构设计，日均处理 10 亿+ 请求
- 使用 Python + Go 开发微服务，MySQL + Redis 存储
...

技能
Python, Go, Django, FastAPI, MySQL, Redis, Kafka, Docker, K8s
```

**输出**：结构化 ParsedResume
```json
{
  "candidate_name": "张三",
  "phone": "138xxxx",
  "email": "zhangsan@email.com",
  "education": [
    {"degree": "硕士", "school": "北京大学", "major": "计算机科学", "graduation_year": 2021},
    {"degree": "本科", "school": "武汉大学", "major": "软件工程", "graduation_year": 2018}
  ],
  "total_years_experience": 5.0,
  "skills": ["Python", "Go", "Django", "FastAPI", "MySQL", "Redis", "Kafka", "Docker", "K8s"],
  "projects": [...],
  "work_experiences": [
    {"company": "字节跳动", "title": "高级后端开发工程师", "start_date": "2021-07", "end_date": "至今", ...}
  ],
  "current_company": "字节跳动",
  "current_title": "高级后端开发工程师",
  "salary_expectation": null,
  "availability": null
}
```

**Prompt 设计要点**：

- 技能提取有两个来源：明确的"技能"章节 + 项目描述中的技术名词（"使用 Python + Go 开发微服务"）
- `total_years_experience` 要求 LLM 优先取简历中明确标注的年限，其次从工作经历推算——给 LLM 一个明确的优先级
- 输入长度限制在 8000 字符——防止超长简历撑爆 token 限制，超出的部分截断

**后处理**：保存原始文本 `raw_text` 到结果中——万一后面发现解析有问题，可以回溯原始文本做审计。

---

### Agent ③ 标签匹配 Agent

**文件**: `agents/tag_matching_agent.py`

**它做什么**：对比岗位画像和候选人简历，从四个维度打分，打标签，写评语，给出通过/待定/淘汰的建议。

**为什么这么做**：

这是整个系统最核心的 Agent，也是最体现"Agent 思路"的地方。它不是简单地计算技能重合度，而是像一个有经验的 HR 一样做多维评估：

- 技能不只看有没有，还看程度（"熟悉 Python" vs "精通 Python"）
- 经验不只看年限，还看相关性和公司质量（5 年外包 ≠ 5 年大厂）
- 背景看学历层次 + 学校层次 + 行业匹配
- 意向看薪资期望和到岗时间是否合理

而且每一项判断都要求 LLM 给出 reason（为什么这么评），不是黑盒打分。

**四个维度及权重**：

| 维度 | 权重 | 评估内容 |
|------|------|---------|
| 技能匹配 skills | 35% | 技能覆盖度 + 熟练度匹配 + 缺核心技能扣15-25分/项 + 额外技能加3-5分/项 |
| 经验匹配 experience | 30% | 年限达标 + 项目领域相关性 + 职位级别 + 头部公司加分 |
| 背景匹配 background | 20% | 学历 + 学校层次(985/211/海归) + 行业 + 公司知名度 |
| 意向匹配 intention | 15% | 薪资在合理范围 + 到岗时间 + 职业方向 |

**为什么权重这样分配**：

技能是决定候选人能不能干活的核心，占最高权重 35%。经验是证明候选人干过什么的依据，占 30%。背景代表候选人的基本素质和学习能力，占 20%。意向关系到候选人来了能不能留下，占 15%——权重最低因为薪资和到岗时间通常有弹性空间。

**Prompt 的关键设计**：

```python
# 系统 prompt 里嵌入评分标准，让 LLM 的角色从"打分工具"变成"评估专家"

"""你是一位资深的招聘评估专家，拥有15年HR经验。"""

# 每个维度有具体的加减分规则，不是让 LLM 自由发挥
"""
【维度一：技能匹配 skills】(权重 35%)
- 缺少核心技能扣分（每项缺核心技能扣 15-25 分）
- 有额外相关技能加分（每项 +3-5 分）
"""

# 硬性要求的兜底规则也写在 prompt 里
"""
- 任何硬性要求明确不满足时，decision 最高只能到 "review"
- 三个及以上硬性要求不满足时，decision 必须为 "reject"
"""
```

**输出的 explainable items** 是整个系统最有价值的部分：

```json
{
  "dimension": "skills",
  "score": 85,
  "details": [
    {"reason": "精通 Python，完全匹配核心技能要求", "impact": "positive"},
    {"reason": "缺少 NLP 项目经验（岗位核心要求）", "impact": "negative"},
    {"reason": "有 Spark 大数据处理技能，为加分项", "impact": "positive"},
    {"reason": "MySQL 熟练度 '熟悉' 未达到 '精通' 要求", "impact": "negative"}
  ]
}
```

每个分数下面挂着具体的加扣分项，HR 一眼就能看到："哦，这人 Python 很强，但 NLP 方向缺经验，所以技能只有 85 不是 95"。这个可解释性才是 HR 敢用 AI 筛选的前提。

**输入构造**：

Agent 里有两个格式化方法，把岗位画像和简历转成结构清晰的文本：

```
【岗位画像】
岗位名称：高级 Python 开发工程师

【硬性要求】
  - [education] 本科及以上学历，计算机相关专业 （必须满足）
  - [years_of_experience] 5年以上 Python 开发经验 （必须满足）

【核心技能】
  - Python（精通，权重 3.0）
  - Django/FastAPI（精通，权重 2.5）
  - MySQL（熟悉，权重 1.5）
  ...

====================================

【候选人简历】
候选人姓名：张三
学历：硕士 / 北京大学 / 计算机科学 / 2021; 本科 / 武汉大学 / 软件工程 / 2018
工作年限：5.0年
技能：Python, Go, Django, FastAPI, ...
工作经历：
  - 高级后端开发工程师 @ 字节跳动（2021-07 ~ 至今）
  ...
```

把两边都用结构化文本呈现出来，LLM 的匹配质量比丢两坨 JSON 过去高得多——等于替 LLM 做好了对比前的整理工作。

---

## 4. Pipeline 编排层 —— 为什么做双保险

**文件**: `pipeline/orchestrator.py`

这是整个系统最关键的工程决策：**不让 LLM 的分数直接成为最终分数**。

### 问题：LLM 不擅长精确算术

LLM 按加权公式 `overall_score = Σ(维度分 × 权重)` 算出来的分数经常有偏差——可能在 1-3 分左右。一个人 85 分和 82 分对 HR 来说差别不大，但如果是 72 分（通过）和 68 分（待定），差 2 分就改变决策了。

### 方案：LLM 打分 + 代码重算

```
LLM 做的事情（在 prompt 里）：
  ✓ 四维度分别打分（技能 85、经验 72、背景 88、意向 70）
  ✓ 打标签（16 个标签，每个标注 match/不 match）
  ✓ 写理由（每个维度的 explainable items）
  ✓ 写评语（llm_explanation 供 HR 阅读）
  ✓ 给出建议 decision

代码做的事情（在 orchestrator 里）：
  ✓ 用 LLM 给的四个维度分数，按权重重新计算综合分
  ✓ 统计硬性要求不满足的数量
  ✓ 硬性要求惩罚扣分
  ✓ 应用决策兜底规则
  ✓ 如果修正了 LLM 的决策，在 decision_reason 里标注 [修正]
```

### 代码重算的核心逻辑

```python
def _recalculate_score(self, result):
    """用代码重新算：overall = Σ(维度分 × 权重)"""
    total = 0.0
    for ds in result.dimension_scores:
        weight = self.dimension_weights.get(ds.dimension, ds.weight)
        total += ds.score * weight
    result.overall_score = round(total, 1)  # 精确到小数点后 1 位
    return result

def _apply_hard_requirement_rules(self, result):
    """硬性要求的规则引擎"""
    # 统计硬性要求未满足数（从 tags 中判断）
    failed_hard = [t for t in result.tags
                   if t.category in ("education", "experience", "certification")
                   and not t.match]

    # 规则 1: 每项未满足扣 15 分（可在设置页调整）
    penalty = len(failed_hard) * 15
    result.overall_score = max(0, result.overall_score - penalty)

    # 规则 2: 3+ 项不满足 → 强制淘汰
    if len(failed_hard) >= 3:
        result.decision = "reject"

    # 规则 3: 1+ 项不满足 + LLM 判了通过 → 降为待定
    elif len(failed_hard) >= 1 and result.decision == "pass":
        result.decision = "review"
        result.decision_reason = f"[修正] ...决策由 pass 调整为 review"

    return result
```

### 为什么这个设计很重要

1. **确定性**：同样的维度分，永远是同样的综合分——不会因为 LLM 偶尔算错而变
2. **可解释性**：HR 看到 `[修正]` 标记就知道代码做了什么调整
3. **可配置**：扣分力度、阈值全在设置页可调，不用改 prompt
4. **安全网**：即使 LLM 误判，硬性要求的规则引擎会兜底

---

## 5. 评分算法详解

### 完整评分流程

```
一份简历经过以下 4 层计算，最终得到决策：

第 1 层：LLM 多维度打分
  ├─ 技能维度 (0-100)
  ├─ 经验维度 (0-100)
  ├─ 背景维度 (0-100)
  └─ 意向维度 (0-100)
      ↓
第 2 层：代码重算综合分
  overall = 技能分 × 0.35 + 经验分 × 0.30 + 背景分 × 0.20 + 意向分 × 0.15
      ↓
第 3 层：硬性要求惩罚
  每项不满足扣 15 分
      ↓
第 4 层：决策映射
  ≥ 70 → ✅ 通过（进入面试池）
  50-69 → ⚠️ 待定（人工复核）
  < 50  → ❌ 淘汰（直接过滤）
  任一硬性不满足 → 最高 ⚠️ 待定
  3+ 项硬性不满足 → 强制 ❌ 淘汰
```

### 举个完整例子

**场景**：某 Python 开发岗位要求本科学历 + 3 年经验 + 精通 Python + 熟悉 MySQL。候选人 A：大专学历, 2 年经验, 精通 Python, 熟悉 MySQL。

```
第 1 层：LLM 评估
  技能分 = 92（Python 精通 + MySQL 熟悉，完全达标）
  经验分 = 55（2 年经验 vs 要求 3 年，有差距）
  背景分 = 40（大专 vs 要求本科，明显差距）
  意向分 = 75（期望薪资合理，到岗时间 2 周）

第 2 层：代码重算
  overall = 92 × 0.35 + 55 × 0.30 + 40 × 0.20 + 75 × 0.15
         = 32.2 + 16.5 + 8.0 + 11.25
         = 67.95 → 68.0

第 3 层：硬性要求惩罚
  不满足项：学历(大专 vs 本科)、年限(2年 vs 3年) → 2 项
  扣分：2 × 15 = 30
  修正后：68.0 - 30 = 38.0

第 4 层：决策
  38.0 < 50 → ❌ 淘汰
  且有硬性要求未满足，强制淘汰
```

这个例子说明了硬性要求惩罚的作用：技能再强，学历和年限这两个硬门槛没到，分数会被大幅拉低。

---

## 6. 数据模型设计

三组 Pydantic 模型，对应系统里的三种核心数据结构：

### 6.1 岗位画像模型 (`models/job_profile.py`)

```python
class HardRequirement(BaseModel):
    category: str          # education / years_of_experience / certification / other
    requirement: str       # "本科及以上学历，计算机相关专业"
    is_mandatory: bool     # True=硬性门槛, False=加分项

class CoreSkill(BaseModel):
    name: str              # "Python"
    proficiency: str       # "精通"
    weight: float          # 1.0~3.0, 越重要越高

class ProjectExperience(BaseModel):
    domain: str            # "后端微服务"
    description: str       # "有微服务架构设计经验"
    required_skills: list[str]  # ["Python", "Docker"]

class IndustryBackground(BaseModel):
    industry: str          # "互联网/软件"
    preferred_subfields: list[str]
    importance: str        # required / preferred / nice_to_have

class JobProfile(BaseModel):
    id: str                # "job_a1b2c3d4"
    job_title: str         # "高级 Python 开发工程师"
    original_jd: str       # 原始 JD 全文（留存备查）
    hard_requirements: list[HardRequirement]
    core_skills: list[CoreSkill]
    project_experience: list[ProjectExperience]
    industry_background: IndustryBackground | None
    created_at: str        # ISO 时间戳
    version: int           # 每次保存 +1，追溯修改历史
```

### 6.2 简历模型 (`models/resume.py`)

```python
class Education(BaseModel):
    degree: str            # 博士 / 硕士 / 本科 / 大专 / 其他
    school: str            # "北京大学"
    major: str             # "计算机科学"
    graduation_year: int | None  # 2021

class WorkExperience(BaseModel):
    company: str           # "字节跳动"
    title: str             # "高级后端开发工程师"
    start_date: str        # "2021-07"
    end_date: str          # "至今"
    duration_months: int | None
    description: str       # 工作职责简述

class Project(BaseModel):
    name: str
    role: str              # "核心开发"
    description: str
    skills_used: list[str] # ["Python", "Go", "Redis"]
    duration_months: int | None

class ParsedResume(BaseModel):
    candidate_name: str
    phone: str | None
    email: str | None
    education: list[Education]
    total_years_experience: float | None  # 5.0
    skills: list[str]
    projects: list[Project]
    work_experiences: list[WorkExperience]
    current_company: str | None
    current_title: str | None
    salary_expectation: str | None  # "30k-40k"
    availability: str | None        # "2周内"
    raw_text: str                   # 原始文本（审计用，不参与匹配）
```

### 6.3 匹配结果模型 (`models/match_result.py`)

```python
class ExplainableItem(BaseModel):
    reason: str     # "精通 Python，完全匹配核心要求"
    impact: str     # positive / negative / neutral

class DimensionScore(BaseModel):
    dimension: str  # skills / experience / background / intention
    score: float    # 0-100
    weight: float   # 0.35 / 0.30 / 0.20 / 0.15
    details: list[ExplainableItem]  # 为什么打这个分

class TagItem(BaseModel):
    tag: str        # "985硕士"
    category: str   # education / skill / experience / intention
    match: bool     # True=符合要求 / False=不符合
    detail: str     # "满足学历硬性要求"

class MatchResult(BaseModel):
    job_profile_id: str
    resume_file: str             # "张三简历.pdf"
    candidate_name: str
    overall_score: float         # 78.5
    dimension_scores: list[DimensionScore]
    tags: list[TagItem]
    decision: str                # pass / review / reject
    decision_reason: str         # 为什么做这个决策
    llm_explanation: str         # LLM 给 HR 看的完整评语
    raw_response: str            # LLM 原始 JSON（审计用）
```

---

## 7. Streamlit 界面设计

### 页面导航

```
侧边栏
├── 🏠 首页         — 统计看板 + 最近活动
├── 📝 岗位画像      — 创建/编辑/保存/加载画像模板
├── 📤 简历筛选      — 选画像 → 上传文件 → 批量跑
├── 📊 筛选结果      — 过滤/排序/详情/反馈/导出
└── ⚙️ 系统设置      — API配置/阈值/权重
```

### 各页面说明

**首页**：三个指标卡片（已处理简历数、通过率、待审数）+ 决策分布柱状图 + 最近处理时间线。HR 一打开就知道整体情况。

**岗位画像**：双 Tab 设计。Tab1 粘贴 JD 一键生成画像，生成后可逐项编辑（硬性要求/技能/项目/行业每个字段都能改）。Tab2 浏览已保存的模板，加载/删除/设为当前使用。

**简历筛选**：三步流程。Step1 选画像模板。Step2 多文件上传（支持拖拽 PDF/Word）。Step3 开始筛选——带实时进度条，每份处理完显示"✅ 张三 — 78.5 分 (通过)"或"❌ 李四 — 解析失败"。

**筛选结果**：顶部过滤栏（决策/最低分/排序/搜索）。每个候选人展示缩略信息（姓名、综合分、四个维度分、前 3 个标签），点开展示完整详情（分数仪表盘 + 四维度进度条 + 带颜色的评分理由 + 标签云 + LLM 评语 + 原始 JSON）。每个人旁边有"实际合格"和"实际不合格"反馈按钮——HR 点一下就能标记误判，为后续迭代积累数据。

**系统设置**：四个配置区。API 配置（Key/URL/Model/Temperature 含测试连接按钮）。评分阈值（通过线/待定线/硬性扣分力度，三个滑块）。维度权重（四个百分比滑块，联动校验总和 100%）。数据管理（清空会话/查看目录路径）。

---

## 8. 部署与运行

### 环境要求

- **Python**: 3.11 以上
- **系统**: Windows / macOS / Linux 均可
- **API**: DeepSeek API Key（在 https://platform.deepseek.com 注册获取）
- **可选**: Tesseract OCR（用于扫描件 PDF，非必需）

### 安装步骤

```bash
# 1. 进入项目目录
cd D:\project1

# 2. (推荐) 创建虚拟环境
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
copy .env.example .env
# 用记事本打开 .env，修改这行：
# DEEPSEEK_API_KEY=sk-你的真实 key
```

### 启动

```bash
streamlit run ui/app.py
```

浏览器访问 http://localhost:8501

### 首次使用流程

1. 打开 **系统设置** → 填入 DeepSeek API Key → 点测试连接确认
2. 打开 **岗位画像** → 粘贴一个 JD → 点"生成岗位画像" → 检查调整 → 点"保存模板"
3. 打开 **简历筛选** → 选择刚保存的模板 → 上传几份简历 PDF → 点"开始 AI 筛选"
4. 打开 **筛选结果** → 查看每个人的评分和标签 → 导出 Excel 报告

---

## 9. 如何迭代优化

这个系统设计之初就考虑了迭代闭环。随着使用，你可以从以下几个方向让它越来越准：

### 9.1 调整阈值和权重

在「系统设置」页面直接拖滑块：

- **通过率太高**（比如 80% 的人都通过了）→ 提高通过阈值到 75 或 80
- **技能要求特别高的岗位** → 调高技能维度权重到 40%
- **对学历要求不高的岗位** → 降低背景维度权重到 10%

### 9.2 优化 Agent 提示词

如果你发现某个 Agent 的某个行为不符合预期，可以直接改对应的 prompt 文件：

| 问题 | 改哪里 |
|------|--------|
| 岗位画像漏掉了重要的硬性要求 | `agents/job_profile_agent.py` 里的 `JOB_PROFILE_SYSTEM_PROMPT` |
| 简历解析把"项目经理"误识别为技术岗 | `agents/resume_parsing_agent.py` 里的 `RESUME_PARSER_SYSTEM_PROMPT` |
| 匹配 Agent 对薪资判断太严格 | `agents/tag_matching_agent.py` 里的 `TAG_MATCHING_SYSTEM_PROMPT` |

修改 prompt 后不需要重新训练，重启 Streamlit 即可生效。

### 9.3 利用人工反馈

这是最核心的迭代手段：

1. 在「筛选结果」页面，HR 对每个候选人点"实际合格"或"实际不合格"
2. 系统把反馈保存到 `data/feedback.json`
3. 积累一定量后分析：
   - **假阴性多**（系统判淘汰但实际合格）→ 降低淘汰阈值，或减小硬性要求扣分力度
   - **假阳性多**（系统判通过但实际不合格）→ 提高通过阈值，或给某个维度加权重

### 9.4 扩充岗位画像模板库

每次筛选完一个岗位，把画像模板保存下来。下次招同类岗位时直接加载，修改少量差异即可复用。模板库积累到 10-20 个时，80% 的新岗位都可以从模板出发微调，而不是从零写 JD。

### 9.5 扩展方向

- **OCR 支持**：安装 `pdf2image + pytesseract` 后，系统可识别扫描件 PDF
- **多岗位并行**：同一批简历对多个岗位画像跑匹配
- **面试对接**：通过的人自动生成面试问题清单
- **数据分析**：统计哪些学校/公司/技能的人通过率最高

---

## 附录：关键文件速查

| 你想... | 看这个文件 |
|---------|----------|
| 修改 Agent 的提示词 | `agents/job_profile_agent.py` (line 8) / `resume_parsing_agent.py` (line 6) / `tag_matching_agent.py` (line 9) |
| 调整评分权重默认值 | `config/settings.py` |
| 修改硬性要求惩罚规则 | `pipeline/orchestrator.py` → `_apply_hard_requirement_rules()` |
| 修改通过/淘汰阈值默认值 | `config/settings.py` / Streamlit 设置页 |
| 添加新的简历格式支持 | `services/document_parser.py` → `parse_resume()` |
| 修改 Excel 报告格式 | `services/report_generator.py` |
| 看数据模型定义 | `models/job_profile.py` / `models/resume.py` / `models/match_result.py` |
| 看 LLM 调用怎么封装的 | `agents/base.py` |
