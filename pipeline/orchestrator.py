"""Pipeline 编排器 —— 串联画像解析→简历解析→标签匹配的完整处理链"""

import logging
from pathlib import Path

from config.settings import settings
from config.constants import (
    DECISION_PASS,
    DECISION_REVIEW,
    DECISION_REJECT,
    DIMENSION_SKILLS,
    DIMENSION_EXPERIENCE,
    DIMENSION_BACKGROUND,
    DIMENSION_INTENTION,
)

from models.job_profile import JobProfile
from models.resume import ParsedResume
from models.match_result import MatchResult, DimensionScore

from agents.job_profile_agent import JobProfileAgent
from agents.resume_parsing_agent import ResumeParsingAgent
from agents.tag_matching_agent import TagMatchingAgent

from services.document_parser import parse_resume
from pipeline.exceptions import SkipResumeError

logger = logging.getLogger(__name__)

# 维度权重映射
DEFAULT_WEIGHTS = {
    DIMENSION_SKILLS: settings.weight_skills,
    DIMENSION_EXPERIENCE: settings.weight_experience,
    DIMENSION_BACKGROUND: settings.weight_background,
    DIMENSION_INTENTION: settings.weight_intention,
}


class PipelineOrchestrator:
    """简历筛选流水线编排器

    负责串联完整的处理流程：
    1. 文档解析（PDF/DOCX → 文本）
    2. 简历解析（文本 → ParsedResume）
    3. 标签匹配（画像 + 简历 → MatchResult）
    4. 分数重算与决策修正
    """

    def __init__(
        self,
        job_profile_agent: JobProfileAgent | None = None,
        resume_agent: ResumeParsingAgent | None = None,
        match_agent: TagMatchingAgent | None = None,
        dimension_weights: dict[str, float] | None = None,
    ):
        """
        Args:
            job_profile_agent: 岗位画像 Agent（可选，用于动态创建画像）
            resume_agent: 简历解析 Agent
            match_agent: 标签匹配 Agent
            dimension_weights: 自定义维度权重
        """
        self.job_profile_agent = job_profile_agent
        self.resume_agent = resume_agent
        self.match_agent = match_agent
        self.dimension_weights = dimension_weights or DEFAULT_WEIGHTS

    def _recalculate_score(self, result: MatchResult) -> MatchResult:
        """根据维度分数和权重重新计算综合分，防止 LLM 计算错误

        Args:
            result: LLM 返回的匹配结果

        Returns:
            修正后的匹配结果
        """
        total = 0.0
        weight_sum = 0.0

        for ds in result.dimension_scores:
            weight = self.dimension_weights.get(ds.dimension, ds.weight)
            total += ds.score * weight
            weight_sum += weight
            ds.weight = weight  # 统一权重

        if weight_sum > 0:
            result.overall_score = round(total / weight_sum, 1)
        else:
            result.overall_score = 50.0

        return result

    def _apply_hard_requirement_rules(self, result: MatchResult) -> MatchResult:
        """应用硬性要求规则

        - 任一硬性要求未满足 → 最高 review
        - 3+ 项硬性要求未满足 → 强制 reject
        - 每项未满足扣分

        Args:
            result: 匹配结果

        Returns:
            修正后的匹配结果
        """
        # 统计硬性要求未满足数
        failed_hard = [
            t for t in result.tags
            if t.category in ("education", "experience", "certification")
            and not t.match
        ]
        failed_count = len(failed_hard)

        # 硬性要求扣分
        penalty = failed_count * settings.hard_requirement_penalty
        if penalty > 0:
            result.overall_score = max(0.0, result.overall_score - penalty)

        # 修正决策
        recalculated_decision = result.decision

        if failed_count >= 3:
            recalculated_decision = DECISION_REJECT
        elif failed_count >= 1 and result.decision == DECISION_PASS:
            recalculated_decision = DECISION_REVIEW

        if recalculated_decision != result.decision:
            result.decision_reason = (
                f"[修正] {result.decision_reason}；"
                f"硬性要求未满足 {failed_count} 项，"
                f"决策由 {result.decision} 调整为 {recalculated_decision}"
            )
            result.decision = recalculated_decision

        return result

    def process_one(self, file_path: Path, job_profile: JobProfile) -> MatchResult:
        """处理单份简历的完整流程

        Args:
            file_path: 简历文件路径
            job_profile: 岗位画像

        Returns:
            匹配结果

        Raises:
            SkipResumeError: 处理失败，应跳过
        """
        # Step 1: 文档解析
        try:
            raw_text = parse_resume(file_path)
        except Exception as e:
            raise SkipResumeError(f"文档解析失败: {e}")

        if not raw_text or len(raw_text.strip()) < 50:
            raise SkipResumeError("简历文本内容过短（可能为空白或扫描件），无法解析")

        # Step 2: 简历解析
        try:
            parsed_resume = self.resume_agent.parse(raw_text)
            parsed_resume.raw_text = raw_text
        except Exception as e:
            raise SkipResumeError(f"简历解析失败: {e}")

        # Step 3: 标签匹配
        try:
            result = self.match_agent.match(job_profile, parsed_resume)
        except Exception as e:
            raise SkipResumeError(f"标签匹配失败: {e}")

        # Step 4: 分数重算 + 硬性要求规则
        result.resume_file = file_path.name
        result.candidate_name = parsed_resume.candidate_name

        result = self._recalculate_score(result)
        result = self._apply_hard_requirement_rules(result)

        return result

    def create_job_profile(self, jd_text: str) -> JobProfile:
        """从 JD 文本创建岗位画像

        Args:
            jd_text: 原始岗位描述

        Returns:
            JobProfile 实例
        """
        if not self.job_profile_agent:
            raise ValueError("JobProfileAgent 未初始化")
        return self.job_profile_agent.generate(jd_text)
