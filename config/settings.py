"""全局配置 —— 通过 pydantic-settings 从 .env 加载"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，自动从 .env 文件和环境变量加载"""

    # ========== DeepSeek API ==========
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_temperature: float = 0.1
    deepseek_max_tokens: int = 4096

    # ========== 评分阈值 ==========
    pass_threshold: float = 70.0
    review_threshold: float = 50.0
    hard_requirement_penalty: float = 15.0

    # ========== 维度权重（必须合计为 1.0）==========
    weight_skills: float = 0.35
    weight_experience: float = 0.30
    weight_background: float = 0.20
    weight_intention: float = 0.15

    # ========== Pipeline ==========
    max_retries: int = 2
    retry_delay_seconds: float = 2.0

    # ========== 路径 ==========
    template_dir: str = "data/templates"
    upload_dir: str = "data/uploads"
    report_dir: str = "data/reports"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow",
    }


# 全局单例
settings = Settings()
