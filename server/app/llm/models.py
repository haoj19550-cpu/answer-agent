"""模型抽象层：BaseChatModel 实例工厂（方案 6.2）。

换模型只动这一层；未配置 fallback 密钥则不装配回退。
"""

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Settings


def get_primary_llm(settings: Settings) -> BaseChatModel:
    from langchain_deepseek import ChatDeepSeek

    return ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        temperature=0.3,  # 出题求稳，低温
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )


def get_fallback_llm(settings: Settings) -> BaseChatModel | None:
    """备用模型（通义，OpenAI 兼容端点）；未配置密钥则不装配回退。"""
    if not settings.fallback_api_key:
        return None
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.fallback_model,
        api_key=settings.fallback_api_key,
        base_url=settings.fallback_base_url,
        temperature=0.3,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )
