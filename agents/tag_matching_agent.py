"""Agent 3: 标签匹配 Agent —— 多维匹配打分 + 标签 + 决策建议"""

import json
from agents.base import BaseAgent, LLMJSONError
from models.job_profile import JobProfile
from models.resume import ParsedResume
from models.match_result import MatchResult

TAG_MATCHING_SYSTEM_PROMPT = """你是一位资深的招聘评估专家，拥有15年HR经验。请对候选人简历与岗位画像进行多维度匹配分析。

你需要从以下4个维度进行评估，每个维度给出0-100的分数：

【维度一：技能匹配 skills】(权重 35%)
- 对比候选人的技能列表与岗位核心技能
- 考虑技能熟练度要求（了解/熟悉/掌握/精通）
- 缺少核心技能扣分（每项缺核心技能扣15-25分）
- 有额外相关技能加分（每项+3-5分）
- 技能熟练度不足酌情扣分

【维度二：经验匹配 experience】(权重 30%)
- 工作年限是否满足硬性要求
- 项目经验领域是否与岗位要求相关
- 过往职位级别与岗位要求是否匹配
- 是否有同行业头部公司经验（加分项）

【维度三：背景匹配 background】(权重 20%)
- 学历是否满足要求（博士/硕士/本科/大专）
- 学校层次（985/211/海外名校/普通院校）
- 行业背景是否符合要求
- 过往公司规模与知名度

【维度四：意向匹配 intention】(权重 15%)
- 薪资期望是否在合理范围（无法判断时给中位分70-80）
- 到岗时间是否满足要求
- 职业发展方向是否与岗位匹配

请按以下 JSON Schema 输出：

{
    "dimension_scores": [
        {
            "dimension": "skills",
            "score": 75,
            "weight": 0.35,
            "details": [
                {"reason": "精通Python，完全匹配核心要求", "impact": "positive"},
                {"reason": "缺少NLP项目经验", "impact": "negative"},
                {"reason": "有Spark技能，为加分项", "impact": "positive"}
            ]
        },
        {
            "dimension": "experience",
            "score": 60,
            "weight": 0.30,
            "details": []
        },
        {
            "dimension": "background",
            "score": 85,
            "weight": 0.20,
            "details": []
        },
        {
            "dimension": "intention",
            "score": 70,
            "weight": 0.15,
            "details": []
        }
    ],
    "tags": [
        {"tag": "985硕士", "category": "education", "match": true, "detail": "满足学历硬性要求"},
        {"tag": "Python精通", "category": "skill", "match": true, "detail": "核心技能"},
        {"tag": "5年经验", "category": "experience", "match": false, "detail": "要求3年以上，符合"},
        {"tag": "期望薪资30k", "category": "intention", "match": true, "detail": "在预算范围内"}
    ],
    "overall_score": 72.5,
    "decision": "review",
    "decision_reason": "技能匹配度高但项目经验方向稍有偏差，建议进入待定池人工复核",
    "llm_explanation": "候选人整体素质优秀，Python技能突出，985硕士背景加分。但项目经验偏向数据分析而非机器学习，与岗位要求的NLP方向有偏差。建议HR进一步面试确认其NLP相关能力和转型意愿。"
}

评分标准（非常重要）：
- overall_score = (技能分 × 0.35) + (经验分 × 0.30) + (背景分 × 0.20) + (意向分 × 0.15)
- overall_score >= 70 → decision: "pass"
- overall_score 50-69 → decision: "review"
- overall_score < 50 → decision: "reject"
- 任何硬性要求明确不满足时，decision 最高只能到 "review"
- 三个及以上硬性要求不满足时，decision 必须为 "reject"

注意事项：
1. 每个维度至少列出 2 个 details（正面或负面均可），说明评分理由
2. tags 至少包含 6 个标签，覆盖 education / skill / experience / intention 等不同类别
3. match 字段 true 表示该项符合要求，false 表示不符合或存在风险
4. llm_explanation 应该是一段完整的评语，HR 可直接阅读
5. decision_reason 要简洁明了，解释为什么做出此决策
6. 必须输出合法 JSON，只输出 JSON，不要包含 markdown 标记或额外说明文字"""


class TagMatchingAgent(BaseAgent):
    """标签匹配 Agent

    对比岗位画像与候选人简历，输出多维匹配分数、标签和决策建议。
    """

    SYSTEM_PROMPT = TAG_MATCHING_SYSTEM_PROMPT

    def _format_profile(self, profile: JobProfile) -> str:
        """将岗位画像格式化为 prompt 文本"""
        lines = [
            f"岗位名称：{profile.job_title}",
            "",
            "【硬性要求】",
        ]
        for hr in profile.hard_requirements:
            mandatory = "（必须满足）" if hr.is_mandatory else "（加分项）"
            lines.append(f"  - [{hr.category}] {hr.requirement} {mandatory}")

        lines.append("")
        lines.append("【核心技能】")
        for sk in profile.core_skills:
            lines.append(f"  - {sk.name}（{sk.proficiency}，权重 {sk.weight}）")

        lines.append("")
        lines.append("【项目经验要求】")
        for pe in profile.project_experience:
            lines.append(f"  - {pe.domain}: {pe.description}")
            if pe.required_skills:
                lines.append(f"    所需技能: {', '.join(pe.required_skills)}")

        if profile.industry_background:
            ib = profile.industry_background
            lines.append("")
            lines.append(f"【行业背景】{ib.industry}（{ib.importance}）")
            if ib.preferred_subfields:
                lines.append(f"  偏好领域: {', '.join(ib.preferred_subfields)}")

        return "\n".join(lines)

    def _format_resume(self, resume: ParsedResume) -> str:
        """将简历格式化为 prompt 文本"""
        lines = [
            f"候选人姓名：{resume.candidate_name}",
        ]

        if resume.education:
            edu_texts = []
            for edu in resume.education:
                parts = [edu.degree, edu.school]
                if edu.major:
                    parts.append(edu.major)
                if edu.graduation_year:
                    parts.append(str(edu.graduation_year))
                edu_texts.append(" / ".join(parts))
            lines.append(f"学历：{'; '.join(edu_texts)}")

        lines.append(f"工作年限：{resume.total_years_experience}年" if resume.total_years_experience else "工作年限：未标注")

        if resume.skills:
            lines.append(f"技能：{', '.join(resume.skills)}")

        if resume.work_experiences:
            lines.append("工作经历：")
            for exp in resume.work_experiences:
                lines.append(f"  - {exp.title} @ {exp.company}（{exp.start_date} ~ {exp.end_date}）")
                if exp.description:
                    lines.append(f"    {exp.description[:150]}")

        if resume.projects:
            lines.append("项目经验：")
            for proj in resume.projects:
                lines.append(f"  - {proj.name}（{proj.role}）")
                if proj.description:
                    lines.append(f"    {proj.description[:150]}")
                if proj.skills_used:
                    lines.append(f"    使用技能: {', '.join(proj.skills_used)}")

        if resume.salary_expectation:
            lines.append(f"期望薪资：{resume.salary_expectation}")
        if resume.availability:
            lines.append(f"到岗时间：{resume.availability}")

        return "\n".join(lines)

    def match(self, job_profile: JobProfile, resume: ParsedResume) -> MatchResult:
        """对一份简历进行匹配评估

        Args:
            job_profile: 岗位画像
            resume: 解析后的简历

        Returns:
            MatchResult 实例

        Raises:
            LLMJSONError: LLM 返回数据格式不正确
        """
        profile_text = self._format_profile(job_profile)
        resume_text = self._format_resume(resume)

        user_prompt = f"""【岗位画像】
{profile_text}

====================================

【候选人简历】
{resume_text}

====================================

请输出多维度的匹配评估结果（JSON格式）。"""

        try:
            result = self._call_llm_with_schema(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model_class=MatchResult,
            )
        except LLMJSONError as e:
            # 重试，带上更严格的格式要求
            retry_prompt = user_prompt + "\n\n⚠️ 上次输出格式不正确。请确保严格按照 JSON Schema 输出，所有数字字段必须是数字类型。"
            result = self._call_llm_with_schema(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=retry_prompt,
                model_class=MatchResult,
            )

        # 后处理：填充关联信息
        result.job_profile_id = job_profile.id
        result.raw_response = json.dumps(
            {"dimension_scores": [d.model_dump() for d in result.dimension_scores],
             "tags": [t.model_dump() for t in result.tags],
             "overall_score": result.overall_score,
             "decision": result.decision,
             "llm_explanation": result.llm_explanation},
            ensure_ascii=False,
        )

        return result
