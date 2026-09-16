"""出题服务：提取缓存 + 校验-重试-减量-回退流水线（方案 6.5）。

绝不展示不合格题目：全部降级手段用尽仍失败 → QuizGenerationFailed。
"""

import structlog
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.runnables import Runnable

from app.llm.callbacks import record_usage
from app.schemas.api import ApiError
from app.schemas.quiz import (
    KnowledgeExtraction,
    KnowledgePoint,
    QuizConfig,
    QuizSet,
    reduction_ladder,
)
from app.stores import memory_store
from app.validators.quiz_validator import validate_quiz

logger = structlog.get_logger(__name__)

# 校验失败后的服务层重试次数（每个降级档位）
# 真实模型单次调用成本远高于样例模式，默认每档只跑 1 次，失败直接进下一档
VALIDATE_RETRY_PER_STEP = 1


def worst_case_llm_calls(
    count: int,
    chain_max_attempts: int,
    has_fallback: bool,
    retry_per_step: int = VALIDATE_RETRY_PER_STEP,
) -> int:
    """单局出题的 LLM 调用次数上界（成本护栏）。

    = 降级档位数 × 每档重试次数 × 链级重试次数 × （装配回退时主/备各一次）
    """
    steps = len(reduction_ladder(count))
    per_chain = chain_max_attempts * (2 if has_fallback else 1)
    return steps * retry_per_step * per_chain


class QuizGenerationFailed(Exception):
    def __init__(self, last_errors: list[str] | None = None):
        self.last_errors = last_errors or []
        super().__init__("quiz generation failed after all degradation steps")


def expand_topic_material(topic_text: str, extraction: KnowledgeExtraction) -> str:
    """主题模式：主题本身太短，无法支撑 Grounded 校验。

    用提取结果（主题 + 摘要 + 各知识点定义）扩展为「有效材料」，
    出题与 source_excerpt 校验均针对扩展文本进行。
    """
    parts = [topic_text, extraction.summary]
    parts.extend(f"{kp.name}：{kp.definition}" for kp in extraction.knowledge_points)
    return "\n".join(p for p in parts if p.strip())


def filter_knowledge_points(
    extraction: KnowledgeExtraction, selected: list[str]
) -> KnowledgeExtraction:
    """按用户勾选过滤知识点；为空或全不命中时返回全集。"""
    if not selected:
        return extraction
    selected_norm = {s.strip() for s in selected if s.strip()}
    kept = [kp for kp in extraction.knowledge_points if kp.name in selected_norm]
    if not kept:
        return extraction
    return extraction.model_copy(update={"knowledge_points": kept})


async def extract_knowledge(
    material_id: str,
    material_text: str,
    chain: Runnable,
    session_id: str = "",
) -> KnowledgeExtraction:
    """知识点提取：按 material_id 缓存，同材料重复出题不再调用链1。"""
    cached = memory_store.get_extraction(material_id)
    if cached is not None:
        logger.info("extraction_cache_hit", material_id=material_id)
        return cached
    usage_cb = UsageMetadataCallbackHandler()
    result: KnowledgeExtraction = await chain.ainvoke(
        {"material": material_text}, config={"callbacks": [usage_cb]}
    )
    record_usage(session_id or material_id, usage_cb)
    memory_store.save_extraction(material_id, result)
    return result


async def generate_quiz(
    material_text: str,
    extraction: KnowledgeExtraction,
    config: QuizConfig,
    quiz_chain: Runnable,
    session_id: str = "",
    grounded_strict: bool = True,
    retry_per_step: int = VALIDATE_RETRY_PER_STEP,
) -> QuizSet:
    """校验-重试-减量流水线。

    链内 with_retry 处理结构化解析失败；此处循环处理 Validator 业务校验失败；
    逐级减量；链上 with_fallbacks 已自动跨模型回退。
    grounded_strict=False 时摘录未命中原文只告警不判失败。
    """
    last_errors: list[str] = []
    for count, single, judge, scenario in reduction_ladder(config.count):
        for attempt in range(retry_per_step):
            usage_cb = UsageMetadataCallbackHandler()
            try:
                quiz: QuizSet = await quiz_chain.ainvoke(
                    {
                        "knowledge_points": extraction.model_dump_json(),
                        "material": material_text,
                        "goal": config.goal.value,
                        "difficulty": config.difficulty.value,
                        "single": single,
                        "judge": judge,
                        "scenario": scenario,
                    },
                    config={"callbacks": [usage_cb]},
                )
            except Exception as exc:  # 链级重试与回退均已失败
                last_errors = [f"chain error: {type(exc).__name__}"]
                logger.warning("quiz_chain_failed", count=count, attempt=attempt, error=str(exc))
                break  # 模型层面失败直接进下一档（减量），不空转
            finally:
                record_usage(session_id, usage_cb)

            errors = validate_quiz(
                quiz,
                extraction,
                material_text,
                (count, single, judge, scenario),
                grounded_strict=grounded_strict,
            )
            if not errors:
                logger.info("quiz_generated", count=count, attempt=attempt)
                return quiz
            last_errors = errors
            logger.warning("quiz_validation_failed", count=count, attempt=attempt, errors=errors)
    raise QuizGenerationFailed(last_errors)


def quiz_generation_api_error(exc: QuizGenerationFailed) -> ApiError:
    return ApiError(
        code="QUIZ_GENERATION_FAILED",
        message="题目生成失败，建议精简内容后重试",
        status_code=200,  # SSE 内以 error 事件下发，HTTP 仍 200
        detail={"errors": exc.last_errors[:5]},
    )
