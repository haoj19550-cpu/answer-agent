"""LangChain 链编排层：三条 LCEL 链的构建函数（方案 6.3）。

依赖注入：接受 BaseChatModel 实例而非自行构造，测试可注入 FakeChatModel。
装配：prompt | llm.with_structured_output(Schema, method="json_schema")
      → with_fallbacks（跨模型回退）→ with_retry（链级重试）。
"""

from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.schemas.quiz import KnowledgeExtraction, QuizSet, ReportContent

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """加载版本化 Prompt 模板（启动时加载为字符串常量）。"""
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def _assemble(
    prompt: ChatPromptTemplate,
    schema: type,
    llm: BaseChatModel,
    fallback_llm: BaseChatModel | None,
    max_attempts: int,
) -> Runnable:
    chain = prompt | llm.with_structured_output(schema, method="json_schema")
    if fallback_llm is not None:
        chain = chain.with_fallbacks(
            [prompt | fallback_llm.with_structured_output(schema, method="json_schema")]
        )
    return chain.with_retry(stop_after_attempt=max_attempts)


def build_extraction_chain(
    llm: BaseChatModel,
    fallback_llm: BaseChatModel | None = None,
    max_attempts: int = 3,
) -> Runnable:
    """链1：知识点提取链。"""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("knowledge_extraction_v1.md")),
            ("human", "学习材料如下：\n<material>\n{material}\n</material>"),
        ]
    )
    return _assemble(prompt, KnowledgeExtraction, llm, fallback_llm, max_attempts)


def build_quiz_chain(
    llm: BaseChatModel,
    fallback_llm: BaseChatModel | None = None,
    max_attempts: int = 3,
) -> Runnable:
    """链2：出题生成链。"""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("quiz_gen_v1.md")),
            (
                "human",
                "知识点列表：\n{knowledge_points}\n\n"
                "学习目标：{goal}\n难度档位：{difficulty}\n\n"
                "材料原文：\n<material>\n{material}\n</material>\n\n"
                "题型配比：单选{single}道、判断{judge}道、场景{scenario}道",
            ),
        ]
    )
    return _assemble(prompt, QuizSet, llm, fallback_llm, max_attempts)


def build_report_chain(
    llm: BaseChatModel,
    fallback_llm: BaseChatModel | None = None,
    max_attempts: int = 3,
) -> Runnable:
    """链3：报告文案生成链。"""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("report_gen_v1.md")),
            (
                "human",
                "学习主题：{topic}\n"
                "已算好的统计数字：\n{stats}\n\n"
                "答题明细（含对错、用户答案、正确答案）：\n{answers_detail}\n\n"
                "材料中易混淆的概念对：\n{confusion_hints}",
            ),
        ]
    )
    return _assemble(prompt, ReportContent, llm, fallback_llm, max_attempts)
