"""简历结构化数据模型"""

from pydantic import BaseModel, Field


class Education(BaseModel):
    """教育经历"""
    degree: str = Field(description="学历：博士 / 硕士 / 本科 / 大专 / 其他")
    school: str = Field(description="毕业院校")
    major: str = Field(default="", description="专业")
    graduation_year: int | None = Field(default=None, description="毕业年份")


class Project(BaseModel):
    """项目经验"""
    name: str = Field(description="项目名称")
    role: str = Field(default="", description="担任角色")
    description: str = Field(default="", description="项目描述")
    skills_used: list[str] = Field(default_factory=list, description="使用的技术栈/技能")
    duration_months: int | None = Field(default=None, description="项目时长（月）")


class WorkExperience(BaseModel):
    """工作经历"""
    company: str = Field(description="公司名称")
    title: str = Field(description="职位")
    start_date: str = Field(description="开始时间")
    end_date: str = Field(description="结束时间，用'至今'表示当前")
    duration_months: int | None = Field(default=None, description="工作时长（月）")
    description: str = Field(default="", description="工作职责描述")


class ParsedResume(BaseModel):
    """解析后的简历结构化数据"""
    candidate_name: str = Field(default="未知", description="候选人姓名")
    phone: str | None = Field(default=None, description="手机号")
    email: str | None = Field(default=None, description="邮箱")
    education: list[Education] = Field(default_factory=list, description="教育经历")
    total_years_experience: float | None = Field(default=None, description="总工作年限")
    skills: list[str] = Field(default_factory=list, description="技能列表")
    projects: list[Project] = Field(default_factory=list, description="项目经验")
    work_experiences: list[WorkExperience] = Field(default_factory=list, description="工作经历")
    current_company: str | None = Field(default=None, description="当前公司")
    current_title: str | None = Field(default=None, description="当前职位")
    salary_expectation: str | None = Field(default=None, description="期望薪资")
    availability: str | None = Field(default=None, description="到岗时间")
    raw_text: str = Field(default="", description="原始提取文本，用于审计核对")

    model_config = {"extra": "allow"}
