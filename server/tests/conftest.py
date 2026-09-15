"""测试基础设施：FakeChatModel 工厂与样例数据 fixture。

FakeStructuredChatModel：链调用 `llm.with_structured_output(Schema)` 时返回
一个按队列弹出预设结果（Pydantic 实例或异常）的 Runnable，可离线模拟
结构化输出成功 / 解析失败 / 校验失败→重试→降级→回退 全部路径。
"""

from typing import Any, Iterator

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda

from app.schemas.quiz import (
    ErrorAnalysis,
    KnowledgeExtraction,
    KnowledgePoint,
    Question,
    QuestionType,
    QuizSet,
    ReportContent,
)
from app.stores import memory_store

# ---------- 样例材料（Redis 缓存，对齐原型示例） ----------

SAMPLE_MATERIAL = """\
Redis 缓存是后端系统性能优化的核心手段，常见三大问题包括缓存穿透、缓存击穿与缓存雪崩。
缓存穿透是指查询一个数据库中根本不存在的数据，缓存和数据库都miss，恶意请求可能利用这一点压垮数据库。
解决方案是使用布隆过滤器拦截非法key，或对空结果进行短时间的空值缓存。
缓存击穿是指某个热点key在过期失效的瞬间，大量并发请求同时打到数据库，造成数据库压力骤增。
常见方案是使用互斥锁（分布式锁）保证只有一个线程回源，或者对热点数据设置逻辑过期时间永不过期。
缓存雪崩是指大量key在同一时间段集中过期，或者Redis实例宕机，导致请求全部涌向数据库。
解决方案包括给过期时间加随机值打散、构建高可用Redis集群、以及服务降级与熔断。
此外，Redis常用数据结构包括String、Hash、List、Set和ZSet，ZSet底层使用跳表实现有序集合。
""" * 3  # 充实长度


@pytest.fixture
def sample_material() -> str:
    return SAMPLE_MATERIAL


@pytest.fixture
def sample_extraction() -> KnowledgeExtraction:
    return KnowledgeExtraction(
        topic="Redis 缓存机制",
        summary="Redis 缓存三大问题及解决方案与常用数据结构",
        knowledge_points=[
            KnowledgePoint(name="缓存穿透", definition="查询不存在的数据导致缓存与数据库均miss", importance=5, confusion_with=["缓存击穿"]),
            KnowledgePoint(name="缓存击穿", definition="热点key失效瞬间大量请求打到数据库", importance=5, confusion_with=["缓存穿透", "缓存雪崩"]),
            KnowledgePoint(name="缓存雪崩", definition="大量key同时过期或Redis宕机", importance=4, confusion_with=["缓存击穿"]),
            KnowledgePoint(name="布隆过滤器", definition="用于拦截非法key的概率型数据结构", importance=3, confusion_with=[]),
        ],
    )


def make_question(
    qtype: QuestionType,
    stem: str,
    options: list[str],
    answer: int,
    kp: str,
    difficulty: int,
    excerpt: str,
) -> Question:
    return Question(
        type=qtype,
        stem=stem,
        options=options,
        correct_answer=answer,
        explanation=f"{stem} 的解析。",
        knowledge_point=kp,
        difficulty=difficulty,
        source_excerpt=excerpt,
    )


@pytest.fixture
def sample_quiz_set() -> QuizSet:
    """5 题 = 单选3 + 判断1 + 场景1，全部通过 Validator。"""
    return QuizSet(
        title="Redis 缓存闯关",
        questions=[
            make_question(
                QuestionType.SINGLE_CHOICE, "缓存穿透指的是以下哪种情况？",
                ["查询数据库中根本不存在的数据，缓存和数据库都miss", "热点key过期瞬间大量请求打到数据库",
                 "大量key在同一时间过期", "Redis主从切换导致数据丢失"], 0, "缓存穿透", 2,
                "缓存穿透是指查询一个数据库中根本不存在的数据，缓存和数据库都miss"),
            make_question(
                QuestionType.SINGLE_CHOICE, "应对缓存击穿的常见方案是什么？",
                ["给过期时间加随机值", "使用互斥锁保证只有一个线程回源",
                 "使用布隆过滤器", "清空全部缓存"], 1, "缓存击穿", 3,
                "缓存击穿是指某个热点key在过期失效的瞬间，大量并发请求同时打到数据库"),
            make_question(
                QuestionType.SINGLE_CHOICE, "ZSet 底层使用什么数据结构实现有序集合？",
                ["跳表", "红黑树", "B+树", "哈希表"], 0, "布隆过滤器", 4,
                "ZSet底层使用跳表实现有序集合"),
            make_question(
                QuestionType.TRUE_FALSE, "布隆过滤器可以用于拦截缓存穿透中的非法key。",
                ["正确", "错误"], 0, "布隆过滤器", 1,
                "解决方案是使用布隆过滤器拦截非法key"),
            make_question(
                QuestionType.SCENARIO,
                "某电商系统秒杀开始后数据库CPU飙升，排查发现某个爆款商品缓存刚好到期，上万请求同时回源。这是哪类问题，首选方案是？",
                ["缓存雪崩，给过期时间加随机值", "缓存击穿，使用互斥锁控制回源",
                 "缓存穿透，使用布隆过滤器", "缓存雪崩，清空缓存重建"], 1, "缓存击穿", 4,
                "缓存击穿是指某个热点key在过期失效的瞬间，大量并发请求同时打到数据库"),
        ],
    )


@pytest.fixture
def sample_report_content() -> ReportContent:
    return ReportContent(
        performance_summary="本次闯关对缓存三大问题掌握较好，但击穿的解决方案仍需巩固。",
        error_analyses=[
            ErrorAnalysis(question_index=1, error_type="概念混淆", analysis="将缓存击穿与缓存雪崩的解决方案混淆。")
        ],
        confusion_pairs=["缓存击穿 vs 缓存雪崩：前者是单个热点key失效，后者是大量key集中失效"],
        suggestions=["重点复习缓存三大问题对比", "动手实现互斥锁回源", "了解布隆过滤器原理"],
    )


# ---------- FakeStructuredChatModel ----------


class FakeStructuredChatModel(GenericFakeChatModel):
    """结构化输出 Fake：with_structured_output 返回按队列弹出预设结果的 Runnable。

    outcomes: 列表，元素为 Pydantic 实例（成功）或 Exception 实例（抛出）。
    每次结构化调用弹出一个；队列耗尽后重复最后一个（便于断言重试次数）。
    """

    outcomes: list[Any]
    call_count: int = 0

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None, **kwargs: Any) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="fake"))])

    def with_structured_output(self, schema: Any = None, **kwargs: Any) -> Runnable:
        outcomes = self.outcomes
        counter = self

        def _next(_input: Any) -> Any:
            idx = min(counter.call_count, len(outcomes) - 1)
            counter.call_count += 1
            outcome = outcomes[idx]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        return RunnableLambda(_next)


@pytest.fixture
def fake_llm_factory():
    def _make(outcomes: list[Any]) -> FakeStructuredChatModel:
        return FakeStructuredChatModel(messages=iter([]), outcomes=outcomes)

    return _make


@pytest.fixture(autouse=True)
def clean_store():
    memory_store.configure()
    memory_store.clear_all()
    yield
    memory_store.clear_all()
