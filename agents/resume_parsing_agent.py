"""Agent 2: 简历解析 Agent —— 将简历文本转化为结构化数据"""

from agents.base import BaseAgent, LLMJSONError
from models.resume import ParsedResume

RESUME_PARSER_SYSTEM_PROMPT = """你是一位专业的简历解析专家。请从简历文本中提取结构化信息。

严格按照以下 JSON Schema 输出：

{
    "candidate_name": "姓名，如果无法识别填'未知'",
    "phone": "手机号或null",
    "email": "邮箱或null",
    "education": [
        {
            "degree": "博士 | 硕士 | 本科 | 大专 | 其他",
            "school": "学校名称",
            "major": "专业名称",
            "graduation_year": 2020
        }
    ],
    "total_years_experience": 5.0,
    "skills": ["技能名称1", "技能名称2"],
    "projects": [
        {
            "name": "项目名称",
            "role": "担任角色",
            "description": "项目简要描述",
            "skills_used": ["使用的技术或技能"],
            "duration_months": 12
        }
    ],
    "work_experiences": [
        {
            "company": "公司名称",
            "title": "职位名称",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM 或 '至今'",
            "duration_months": 24,
            "description": "主要职责和业绩简述"
        }
    ],
    "current_company": "当前所在公司或null",
    "current_title": "当前职位或null",
    "salary_expectation": "期望薪资或null",
    "availability": "到岗时间或null"
}

提取注意事项：
1. 工作年限：优先使用简历中明确标注的年限，否则从最早的工作经历/教育结束时间推算
2. 技能提取：从"技能"章节提取，同时从项目描述和工作经历中补充识别
3. 学历：education 按时间倒序排列（最近的放在最前面）
4. 薪资和到岗时间：如果简历中没有明确提及，填 null
5. total_years_experience 为数字类型（浮点数），若无信息填 null
6. 姓名如果无法从简历中识别，candidate_name 填 "未知"
7. 确保所有字段都存在，即使为空列表或 null
8. 必须输出合法 JSON，只输出 JSON，不要包含 markdown 标记或额外说明文字"""


class ResumeParsingAgent(BaseAgent):
    """简历解析 Agent

    输入清洗后的简历纯文本，输出结构化的 ParsedResume 对象。
    """

    SYSTEM_PROMPT = RESUME_PARSER_SYSTEM_PROMPT

    def parse(self, resume_text: str) -> ParsedResume:
        """解析简历文本为结构化数据

        Args:
            resume_text: 清洗后的简历纯文本

        Returns:
            ParsedResume 实例

        Raises:
            LLMJSONError: LLM 返回数据格式不正确
        """
        # 限制输入长度避免超 token 限制
        max_input_chars = 8000
        trimmed_text = resume_text if len(resume_text) <= max_input_chars else resume_text[:max_input_chars]

        user_prompt = f"请解析以下简历文本：\n\n{trimmed_text}"

        try:
            parsed = self._call_llm_with_schema(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model_class=ParsedResume,
            )
        except LLMJSONError:
            retry_prompt = user_prompt + "\n\n⚠️ 请确保只输出合法 JSON，所有字段都存在，不要遗漏任何字段。"
            parsed = self._call_llm_with_schema(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=retry_prompt,
                model_class=ParsedResume,
            )

        # 后处理：保存原始文本用于审计
        parsed.raw_text = resume_text

        return parsed
