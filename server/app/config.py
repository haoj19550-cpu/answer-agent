from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置（pydantic-settings，环境变量 / .env）。"""

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"  # 主用模型，非推理模式
    fallback_api_key: str = ""  # 通义（百炼兼容端点）
    fallback_model: str = "qwen-plus"
    fallback_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    llm_timeout: int = 30
    llm_max_retries: int = 2  # 网络层指数退避重试（429/5xx）
    chain_max_attempts: int = 3  # 业务层链级重试

    # 材料约束
    material_max_chars: int = 20000
    material_min_chars: int = 50
    pdf_max_bytes: int = 10 * 1024 * 1024  # 10MB
    pdf_max_pages: int = 50

    # 存储 TTL（秒）
    store_ttl: int = 7200  # 材料/闯关/报告 2 小时
    gamification_ttl: int = 30 * 86400  # 游戏化状态 30 天

    # 游戏化
    monthly_quota: int = 30  # 每自然月生成额度
    exp_per_correct: int = 20
    exp_per_complete: int = 40

    # 限频
    rate_limit_per_minute: int = 10

    # FAKE_LLM=1：内置样例数据装配链（无 Key 联调/演示用）
    fake_llm: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
