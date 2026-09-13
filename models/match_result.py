"""匹配结果数据模型"""

from pydantic import BaseModel, Field


class ExplainableItem(BaseModel):
    """可解释的评分明细项"""
    reason: str = Field(description="评分理由")
    impact: str = Field(description="positive / negative / neutral")


class DimensionScore(BaseModel):
    """单个维度的评分"""
    dimension: str = Field(description="维度标识：skills / experience / background / intention")
    score: float = Field(ge=0.0, le=100.0, description="该维度分数 0-100")
    weight: float = Field(ge=0.0, le=1.0, description="该维度权重")
    details: list[ExplainableItem] = Field(default_factory=list, description="评分明细（可解释性）")


class TagItem(BaseModel):
    """匹配标签"""
    tag: str = Field(description="标签名称")
    category: str = Field(description="标签类别：education / skill / experience / intention / other")
    match: bool = Field(description="是否匹配")
    detail: str = Field(default="", description="标签说明")


class MatchResult(BaseModel):
    """完整的匹配评估结果"""
    job_profile_id: str = Field(default="", description="对应的岗位画像 ID，由后处理自动填充")
    resume_file: str = Field(default="", description="原始简历文件名")
    candidate_name: str = Field(default="", description="候选人姓名")
    overall_score: float = Field(ge=0.0, le=100.0, description="综合评分 0-100")
    dimension_scores: list[DimensionScore] = Field(default_factory=list, description="四维度评分")
    tags: list[TagItem] = Field(default_factory=list, description="匹配标签列表")
    decision: str = Field(default="review", description="pass / review / reject")
    decision_reason: str = Field(default="", description="决策说明")
    llm_explanation: str = Field(default="", description="LLM 的完整评语")
    raw_response: str = Field(default="", description="LLM 原始 JSON，用于审计")
