"""FAKE_LLM 模式：无 API Key 时用内置样例数据装配三条链，供前后端联调/演示。

链为 RunnableLambda，直接返回确定性 Pydantic 结果；quiz 链按入参配比裁题。
"""

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

SAMPLE_EXTRACTION = KnowledgeExtraction(
    topic="Redis 缓存机制",
    summary="Redis 缓存三大问题（穿透/击穿/雪崩）及解决方案，常用数据结构。",
    # 定义文本覆盖全部样例题的 source_excerpt，保证主题模式下 Grounded 校验可通过
    knowledge_points=[
        KnowledgePoint(
            name="缓存穿透",
            definition="缓存穿透是指查询一个数据库中根本不存在的数据，缓存和数据库都miss。解决方案是使用布隆过滤器拦截非法key，或对空结果进行短时间的空值缓存",
            importance=5, confusion_with=["缓存击穿"],
        ),
        KnowledgePoint(
            name="缓存击穿",
            definition="缓存击穿是指某个热点key在过期失效的瞬间，大量并发请求同时打到数据库。常见方案是使用互斥锁（分布式锁）保证只有一个线程回源，或者对热点数据设置逻辑过期时间永不过期",
            importance=5, confusion_with=["缓存穿透", "缓存雪崩"],
        ),
        KnowledgePoint(
            name="缓存雪崩",
            definition="缓存雪崩是指大量key在同一时间段集中过期，或者Redis实例宕机，导致请求全部涌向数据库。解决方案包括给过期时间加随机值打散、构建高可用Redis集群、以及服务降级与熔断",
            importance=4, confusion_with=["缓存击穿"],
        ),
        KnowledgePoint(
            name="布隆过滤器",
            definition="拦截非法key的概率型数据结构，用于缓存穿透防护",
            importance=3, confusion_with=[],
        ),
        KnowledgePoint(
            name="ZSet 与跳表",
            definition="ZSet底层使用跳表实现有序集合",
            importance=3, confusion_with=[],
        ),
    ],
)

_POOL = [
    Question(
        type=QuestionType.SINGLE_CHOICE,
        stem="缓存穿透指的是以下哪种情况？",
        options=[
            "查询数据库中根本不存在的数据，缓存和数据库都miss",
            "热点key过期瞬间大量请求打到数据库",
            "大量key在同一时间过期",
            "Redis主从切换导致数据丢失",
        ],
        correct_answer=0,
        explanation="缓存穿透查询的是数据库中根本不存在的数据，缓存与库都挡不住。",
        knowledge_point="缓存穿透",
        difficulty=2,
        source_excerpt="缓存穿透是指查询一个数据库中根本不存在的数据，缓存和数据库都miss",
    ),
    Question(
        type=QuestionType.SINGLE_CHOICE,
        stem="应对缓存击穿的常见方案是什么？",
        options=["给过期时间加随机值", "使用互斥锁保证只有一个线程回源", "使用布隆过滤器", "清空全部缓存"],
        correct_answer=1,
        explanation="互斥锁把重建缓存串行化，只放一个请求回源，是击穿场景最快的止血动作。",
        knowledge_point="缓存击穿",
        difficulty=3,
        source_excerpt="缓存击穿是指某个热点key在过期失效的瞬间，大量并发请求同时打到数据库",
    ),
    Question(
        type=QuestionType.SINGLE_CHOICE,
        stem="ZSet 底层使用什么数据结构实现有序集合？",
        options=["跳表", "红黑树", "B+树", "哈希表"],
        correct_answer=0,
        explanation="ZSet 底层使用跳表（skiplist）实现有序集合。",
        knowledge_point="ZSet 与跳表",
        difficulty=4,
        source_excerpt="ZSet底层使用跳表实现有序集合",
    ),
    Question(
        type=QuestionType.SINGLE_CHOICE,
        stem="缓解缓存雪崩的有效手段不包括以下哪项？",
        options=["过期时间加随机值打散", "构建高可用 Redis 集群", "服务降级与熔断", "对所有 key 设置相同的过期时间"],
        correct_answer=3,
        explanation="相同过期时间会加剧同时失效，正是雪崩诱因。",
        knowledge_point="缓存雪崩",
        difficulty=3,
        source_excerpt="缓存雪崩是指大量key在同一时间段集中过期，或者Redis实例宕机",
    ),
    Question(
        type=QuestionType.SINGLE_CHOICE,
        stem="布隆过滤器在缓存穿透防护中的作用是什么？",
        options=["拦截数据库中一定不存在的非法key", "给热点key续期", "压缩缓存占用内存", "加速回源查询"],
        correct_answer=0,
        explanation="布隆过滤器在缓存前拦截一定不存在的 key，避免请求打到数据库。",
        knowledge_point="布隆过滤器",
        difficulty=2,
        source_excerpt="解决方案是使用布隆过滤器拦截非法key",
    ),
    Question(
        type=QuestionType.SINGLE_CHOICE,
        stem="对空结果进行短时间缓存主要用来缓解什么问题？",
        options=["缓存穿透", "缓存击穿", "缓存雪崩", "主从延迟"],
        correct_answer=0,
        explanation="空值缓存让不存在的数据也能命中缓存，挡住穿透流量。",
        knowledge_point="缓存穿透",
        difficulty=2,
        source_excerpt="或对空结果进行短时间的空值缓存",
    ),
    Question(
        type=QuestionType.TRUE_FALSE,
        stem="布隆过滤器可以用于拦截缓存穿透中的非法key。",
        options=["正确", "错误"],
        correct_answer=0,
        explanation="布隆过滤器可拦截一定不存在的 key，是穿透防护的常见手段。",
        knowledge_point="布隆过滤器",
        difficulty=1,
        source_excerpt="解决方案是使用布隆过滤器拦截非法key",
    ),
    Question(
        type=QuestionType.TRUE_FALSE,
        stem="给热点 key 设置永不过期，就能彻底避免缓存击穿。",
        options=["正确", "错误"],
        correct_answer=1,
        explanation="「彻底」过于绝对：逻辑过期也需要异步重建，且永不过期有数据一致性代价。",
        knowledge_point="缓存击穿",
        difficulty=2,
        source_excerpt="或者对热点数据设置逻辑过期时间永不过期",
    ),
    Question(
        type=QuestionType.SCENARIO,
        stem="秒杀活动开始前一秒，商品详情 key 恰好过期，8 万 QPS 全部落到 MySQL，数据库 CPU 打满。你第一步应该做什么？",
        options=[
            "立即扩容 MySQL 只读从库，把读流量分摊出去",
            "用分布式互斥锁只放一个请求重建缓存，其余请求短暂等待",
            "把商品详情改为永不过期，避免再次失效",
            "给所有 key 的过期时间加上随机值",
        ],
        correct_answer=1,
        explanation="热点 key 失效瞬间被并发打穿是典型击穿，互斥锁重建是最快止血动作。",
        knowledge_point="缓存击穿",
        difficulty=4,
        source_excerpt="缓存击穿是指某个热点key在过期失效的瞬间，大量并发请求同时打到数据库",
    ),
    Question(
        type=QuestionType.SCENARIO,
        stem="凌晨批量任务结束后，监控发现数据库 QPS 突增 10 倍，大量缓存 key 恰好在同一分钟过期。这最可能是哪类问题，应优先采取什么措施？",
        options=[
            "缓存穿透，上布隆过滤器",
            "缓存雪崩，给过期时间加随机值并评估集群高可用",
            "缓存击穿，加互斥锁",
            "主从切换，重建哨兵",
        ],
        correct_answer=1,
        explanation="大量 key 同时过期是雪崩特征，打散过期时间 + 高可用是正解。",
        knowledge_point="缓存雪崩",
        difficulty=4,
        source_excerpt="缓存雪崩是指大量key在同一时间段集中过期",
    ),
]

SAMPLE_REPORT = ReportContent(
    performance_summary="本次闯关对缓存三大问题的整体掌握不错，但击穿与雪崩的触发条件还需要进一步区分。",
    error_analyses=[
        ErrorAnalysis(question_index=1, error_type="概念混淆", analysis="把缓存击穿与缓存雪崩的触发条件混淆：击穿是单个热点 key 失效瞬间被并发打穿，雪崩是大批 key 同时过期。"),
    ],
    confusion_pairs=["缓存击穿 vs 缓存雪崩：前者是单个热点 key 失效，后者是大量 key 集中失效或实例宕机"],
    suggestions=[
        "把穿透、击穿、雪崩的触发条件和解法做成一张对照表，各记一句话",
        "针对缓存击穿单独练 3 道场景题，重点是互斥锁重建与逻辑过期的取舍",
        "明天这个时间回来复习薄弱点，5 题即可",
    ],
)


def _fake_quiz(inputs: dict) -> QuizSet:
    single = int(inputs.get("single", 3))
    judge = int(inputs.get("judge", 1))
    scenario = int(inputs.get("scenario", 1))
    picked: list[Question] = []
    for qtype, need in (
        (QuestionType.SINGLE_CHOICE, single),
        (QuestionType.TRUE_FALSE, judge),
        (QuestionType.SCENARIO, scenario),
    ):
        pool = [q for q in _POOL if q.type == qtype]
        picked.extend(pool[:need])
    return QuizSet(title="Redis 缓存闯关", questions=picked)


def make_fake_chains():
    """返回 (extraction_chain, quiz_chain, report_chain) 三个 Runnable。"""
    return (
        RunnableLambda(lambda _inputs: SAMPLE_EXTRACTION),
        RunnableLambda(_fake_quiz),
        RunnableLambda(lambda _inputs: SAMPLE_REPORT),
    )
