"""Agent 1: 岗位画像 Agent —— 将 JD 转化为结构化岗位画像"""

import json
import uuid
from agents.base import BaseAgent, LLMJSONError
from models.job_profile import JobProfile, HardRequirement

JOB_PROFILE_SYSTEM_PROMPT = """你是一位专业的HR岗位分析师。你的任务是将岗位描述(JD)转化为结构化的岗位画像模板。

请严格按照以下 JSON Schema 输出：

{
    "job_title": "岗位名称",
    "hard_requirements": [
        {
            "category": "education | years_of_experience | certification | other",
            "requirement": "具体要求描述",
            "is_mandatory": true
        }
    ],
    "core_skills": [
        {
            "name": "技能名称",
            "proficiency": "了解 | 熟悉 | 掌握 | 精通",
            "weight": 1.0
        }
    ],
    "project_experience": [
        {
            "domain": "项目领域/方向",
            "description": "项目经验要求描述",
            "required_skills": ["技能1", "技能2"]
        }
    ],
    "industry_background": {
        "industry": "所属行业",
        "preferred_subfields": ["细分领域1", "细分领域2"],
        "importance": "required | preferred | nice_to_have"
    }
}

输出要求：
1. hard_requirements 必须至少包含 education（学历要求）和 years_of_experience（工作年限）两个维度
2. core_skills 中 weight 取值范围 1.0~3.0，越核心的技能权重越高：
   - 3.0 = 该岗位最核心的必备技能
   - 2.0 = 重要的辅助技能
   - 1.0 = 加分项/锦上添花的技能
3. 对于 JD 中模糊的描述，根据你的专业知识补充合理的具体要求
4. proficiency 必须从 ["了解", "熟悉", "掌握", "精通"] 中选择
5. 如果 JD 中没有明确提及行业背景，industry_background 的 importance 设为 "nice_to_have"
6. 必须输出合法 JSON，只输出 JSON，不要包含 markdown 标记或额外说明文字
7. 所有字段使用中文"""


class JobProfileAgent(BaseAgent):
    """岗位画像生成 Agent

    输入原始 JD 文本，输出结构化的 JobProfile 对象。
    """

    SYSTEM_PROMPT = JOB_PROFILE_SYSTEM_PROMPT

    def generate(self, jd_text: str) -> JobProfile:
        """根据 JD 文本生成岗位画像

        Args:
            jd_text: 原始岗位描述文本

        Returns:
            JobProfile 实例

        Raises:
            LLMJSONError: LLM 返回数据格式不正确
        """
        user_prompt = f"请分析以下岗位描述，输出结构化的岗位画像：\n\n岗位描述：\n{jd_text}"

        try:
            profile = self._call_llm_with_schema(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model_class=JobProfile,
            )
        except LLMJSONError:
            # 重试一次，带上更严格的格式要求
            retry_prompt = user_prompt + "\n\n⚠️ 上次输出的 JSON 格式不正确。请确保只输出合法的 JSON，不要包含任何额外文字或 markdown 标记。"
            profile = self._call_llm_with_schema(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=retry_prompt,
                model_class=JobProfile,
            )

        # 后处理：补充原始 JD 和自动生成 ID
        profile.original_jd = jd_text
        if not profile.id:
            profile.id = f"job_{uuid.uuid4().hex[:8]}"

        # 确保 hard_requirements 包含教育和工作年限
        categories = {hr.category for hr in profile.hard_requirements}
        if "education" not in categories:
            profile.hard_requirements.append(
                HardRequirement(
                    category="education",
                    requirement="本科及以上学历",
                    is_mandatory=True,
                )
            )
        if "years_of_experience" not in categories:
            profile.hard_requirements.append(
                HardRequirement(
                    category="years_of_experience",
                    requirement="3年以上相关工作经验",
                    is_mandatory=True,
                )
            )

        return profile
