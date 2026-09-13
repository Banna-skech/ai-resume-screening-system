"""岗位画像数据模型"""

from datetime import datetime
from pydantic import BaseModel, Field


class HardRequirement(BaseModel):
    """硬性要求：教育、年限、证书等必须满足的条件"""
    category: str = Field(description="类别：education / years_of_experience / certification / other")
    requirement: str = Field(description="具体要求描述")
    is_mandatory: bool = Field(default=True, description="是否为必须满足的硬性条件")


class CoreSkill(BaseModel):
    """核心技能要求及期望熟练度"""
    name: str = Field(description="技能名称")
    proficiency: str = Field(description="期望水平：了解 / 熟悉 / 掌握 / 精通")
    weight: float = Field(default=1.0, ge=0.0, le=3.0, description="重要性权重，1.0~3.0")


class ProjectExperience(BaseModel):
    """项目经验要求"""
    domain: str = Field(description="项目领域/方向")
    description: str = Field(description="项目描述")
    required_skills: list[str] = Field(default_factory=list, description="项目所需的技能")


class IndustryBackground(BaseModel):
    """行业背景偏好"""
    industry: str = Field(description="所属行业")
    preferred_subfields: list[str] = Field(default_factory=list, description="偏好的细分领域")
    importance: str = Field(default="preferred", description="required / preferred / nice_to_have")


class JobProfile(BaseModel):
    """完整的岗位画像模板"""
    id: str = Field(default="", description="模板 ID，保存时自动生成")
    job_title: str = Field(description="岗位名称")
    original_jd: str = Field(default="", description="原始 JD 文本，由后处理自动填充")
    hard_requirements: list[HardRequirement] = Field(default_factory=list)
    core_skills: list[CoreSkill] = Field(default_factory=list)
    project_experience: list[ProjectExperience] = Field(default_factory=list)
    industry_background: IndustryBackground | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: int = Field(default=1)

    model_config = {"extra": "allow"}
