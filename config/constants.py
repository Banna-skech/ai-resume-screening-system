"""全局常量定义"""

# 支持的简历文件格式
SUPPORTED_RESUME_FORMATS = [".pdf", ".docx"]

# Excel 报告配置
EXCEL_FILENAME_PREFIX = "简历筛选报告"
EXCEL_SHEET_SUMMARY = "汇总表"
EXCEL_SHEET_DETAIL = "详细评分"
EXCEL_SHEET_SKILLS = "技能矩阵"

# 反馈文件
FEEDBACK_FILE = "data/feedback.json"

# 决策值
DECISION_PASS = "pass"
DECISION_REVIEW = "review"
DECISION_REJECT = "reject"

DECISION_LABELS = {
    DECISION_PASS: "✅ 通过",
    DECISION_REVIEW: "⚠️ 待定",
    DECISION_REJECT: "❌ 淘汰",
}

# 评分维度
DIMENSION_SKILLS = "skills"
DIMENSION_EXPERIENCE = "experience"
DIMENSION_BACKGROUND = "background"
DIMENSION_INTENTION = "intention"

DIMENSION_LABELS = {
    DIMENSION_SKILLS: "技能匹配",
    DIMENSION_EXPERIENCE: "经验匹配",
    DIMENSION_BACKGROUND: "背景匹配",
    DIMENSION_INTENTION: "意向匹配",
}

# 技能熟练度等级
PROFICIENCY_LEVELS = ["了解", "熟悉", "掌握", "精通"]

# 学历等级
DEGREE_LEVELS = ["大专", "本科", "硕士", "博士", "其他"]
