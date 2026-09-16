"""模型抽象层：BaseChatModel 实例工厂（方案 6.2）。

换模型只动这一层；未配置 fallback 密钥则不装配回退。
真实模式缺 Key 时抛 LLMConfigurationError，由启动装配转成可读提示。
"""

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Settings


class LLMConfigurationError(RuntimeError):
    """LLM 配置缺失/非法（缺 API Key 等），属于可自助修复的启动期错误。"""


def get_primary_llm(settings: Settings) -> BaseChatModel:
    """主模型：DeepSeek（langchain-deepseek 官方集成包）。"""
    if not settings.deepseek_api_key:
        raise LLMConfigurationError(
            "未配置 DEEPSEEK_API_KEY：请在 server/.env 中填入 DeepSeek API Key，"
            "或设置 FAKE_LLM=1 使用内置样例模式"
        )
    from langchain_deepseek import ChatDeepSeek

    return ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        api_base=settings.deepseek_base_url,
        temperature=0.3,  # 出题求稳，低温
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
        # 出题/报告走结构化输出，显式关闭思考模式（v4 系列默认可能开启）
        extra_body={"thinking": {"type": "disabled"}}
        if settings.deepseek_disable_thinking
        else None,
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
