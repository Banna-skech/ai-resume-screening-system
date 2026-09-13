"""Agent 基类 —— 封装 DeepSeek API 调用、JSON 模式、重试逻辑"""

import json
import logging
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import settings
from config.constants import DECISION_REVIEW

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM 调用失败"""
    pass


class LLMJSONError(LLMError):
    """LLM 返回无效 JSON"""
    pass


class BaseAgent:
    """所有 Agent 的基类，提供 LLM 调用的通用能力"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        api_key = api_key or settings.deepseek_api_key
        if not api_key:
            raise ValueError("DeepSeek API Key 未配置，请在 .env 中设置 DEEPSEEK_API_KEY")

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or settings.deepseek_base_url,
        )
        self.model = model or settings.deepseek_model
        self.temperature = temperature if temperature is not None else settings.deepseek_temperature
        self.max_tokens = max_tokens or settings.deepseek_max_tokens

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((LLMError,)),
        reraise=True,
    )
    def _call_llm(self, system_prompt: str, user_prompt: str) -> dict:
        """调用 LLM 并返回解析后的 JSON 字典

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Returns:
            解析后的 JSON 字典

        Raises:
            LLMJSONError: LLM 返回的 JSON 无法解析
            LLMError: 其他 LLM 调用错误
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as e:
            raise LLMError(f"LLM API 调用失败: {e}") from e

        content = response.choices[0].message.content
        if content is None:
            raise LLMJSONError("LLM 返回内容为空")

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # 尝试提取 JSON 片段
            logger.warning(f"JSON 解析失败，尝试修复: {content[:200]}")
            try:
                # 有时 LLM 会包裹 ```json ``` 标记
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return json.loads(content.strip())
            except (json.JSONDecodeError, IndexError):
                raise LLMJSONError(f"LLM 返回无效 JSON: {content[:300]}") from e

    def _call_llm_with_schema(
        self, system_prompt: str, user_prompt: str, model_class: type
    ):
        """调用 LLM 并使用 Pydantic 模型验证返回结果

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            model_class: 用于验证的 Pydantic 模型类

        Returns:
            验证后的 Pydantic 模型实例

        Raises:
            LLMJSONError: 验证失败
        """
        data = self._call_llm(system_prompt, user_prompt)
        try:
            return model_class(**data)
        except Exception as e:
            raise LLMJSONError(f"LLM 返回数据不符合预期格式: {e}\n数据: {json.dumps(data, ensure_ascii=False)[:500]}") from e


def get_default_decision(overall_score: float, pass_threshold: float = 70.0, review_threshold: float = 50.0) -> str:
    """根据分数计算默认决策

    Args:
        overall_score: 综合分数
        pass_threshold: 通过阈值
        review_threshold: 待定阈值

    Returns:
        pass / review / reject
    """
    from config.constants import DECISION_PASS, DECISION_REVIEW, DECISION_REJECT

    if overall_score >= pass_threshold:
        return DECISION_PASS
    elif overall_score >= review_threshold:
        return DECISION_REVIEW
    else:
        return DECISION_REJECT
