# AI 简历筛选系统

基于 DeepSeek 大模型的智能简历筛选工具，采用 Agent 思路拆解筛选流程：**岗位画像 → 简历解析 → 标签匹配 → 自动化串联**，全程可复用、可迭代。

## 核心思路

不是简单关键词匹配，而是让 AI 像真正的 HR 一样理解岗位需求、解析简历、多维匹配打分。

### 四个 Agent

1. **岗位画像 Agent** — 将 JD 拆解为结构化模板：硬条件 + 核心技能 + 项目经验 + 行业背景
2. **简历解析 Agent** — 自动提取简历中的学历、年限、技能、项目、公司、薪资、到岗时间
3. **标签匹配 Agent** — 多维打分（技能/经验/背景/意向）+ 标签 + 可解释评语
4. **Pipeline 编排器** — 串联三个 Agent，批量跑简历，自动输出通过/待定/淘汰

### 评分规则

| 分数 | 决策 | 含义 |
|------|------|------|
| ≥ 70 | ✅ 通过 | 进入面试池 |
| 50-69 | ⚠️ 待定 | 人工复核 |
| < 50 | ❌ 淘汰 | 直接过滤 |

硬性要求未满足 → 自动降级；3+ 项未满足 → 强制淘汰。

## 快速开始

### 1. 环境要求

- Python 3.11+
- DeepSeek API Key（[获取地址](https://platform.deepseek.com)）

### 2. 安装

```bash
# 克隆或下载项目
cd D:\project1

# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置

复制 `.env.example` 为 `.env`，填入你的 DeepSeek API Key：

```bash
copy .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY=sk-your-key
```

### 4. 启动

```bash
cd D:\project1
streamlit run ui/app.py
```

浏览器打开 http://localhost:8501 即可使用。

### 5. 使用流程

1. **系统设置** → 配置 API Key
2. **岗位画像** → 粘贴 JD → AI 生成结构化画像 → 可编辑调整 → 保存模板
3. **简历筛选** → 选择画像模板 → 上传 PDF/Word 简历 → 开始筛选
4. **筛选结果** → 查看评分/标签/详情 → 人工反馈 → 导出 Excel 报告

## 项目结构

```
D:\project1\
├── ui/app.py              # Streamlit 主入口
├── ui/pages/              # 5 个页面
│   ├── dashboard.py       # 首页仪表盘
│   ├── job_profile.py     # 岗位画像管理
│   ├── resume_upload.py   # 简历上传与筛选
│   ├── results.py         # 筛选结果与反馈
│   └── settings.py        # 系统设置
├── ui/components/         # 可复用组件
│   ├── score_card.py      # 分数仪表盘
│   └── candidate_detail.py # 候选人详情面板
├── agents/                # 三个 AI Agent
│   ├── base.py            # Agent 基类（DeepSeek 客户端）
│   ├── job_profile_agent.py
│   ├── resume_parsing_agent.py
│   └── tag_matching_agent.py
├── pipeline/              # Pipeline 编排
│   ├── orchestrator.py    # 单简历处理链
│   ├── batch_processor.py # 批量处理
│   └── exceptions.py      # 自定义异常
├── models/                # Pydantic 数据模型
│   ├── job_profile.py
│   ├── resume.py
│   └── match_result.py
├── services/              # 服务层
│   ├── document_parser.py # PDF/DOCX 文本提取
│   ├── template_manager.py # 画像模板 CRUD
│   └── report_generator.py # Excel 报告生成
├── config/                # 配置
│   ├── settings.py        # pydantic-settings
│   └── constants.py       # 常量定义
└── data/                  # 数据目录
    ├── templates/         # 保存的画像模板
    ├── reports/           # 生成的 Excel 报告
    └── uploads/           # 上传的简历暂存
```

## 可配置项

所有阈值和权重均可在「系统设置」页面调整：

- API 配置（Key / Model / Temperature）
- 通过/待定阈值
- 硬性要求扣分力度
- 四维度权重（技能/经验/背景/意向）

## 迭代优化

系统支持人工反馈闭环：

1. 在「筛选结果」页标记误判（实际合格/实际不合格）
2. 积累反馈数据后调优：
   - 调整阈值和权重
   - 优化 Agent 提示词
   - 补充岗位画像模板

## 扩展方向

- [ ] OCR 支持（扫描件 PDF 识别）
- [ ] 多岗位并行筛选
- [ ] 邮件自动通知候选人
- [ ] 面试安排对接
- [ ] 数据看板与分析
