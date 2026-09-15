"""API 层共享依赖：链注册表、资源归属校验。"""

from dataclasses import dataclass

from fastapi import Request
from langchain_core.runnables import Runnable

from app.schemas.api import ApiError
from app.schemas.quiz import Material, Quiz
from app.stores import memory_store


@dataclass
class ChainRegistry:
    """三条 LCEL 链（应用启动时构建一次，全局复用）。"""

    extraction_chain: Runnable
    quiz_chain: Runnable
    report_chain: Runnable


def get_chains(request: Request) -> ChainRegistry:
    return request.app.state.chains


def get_owned_material(material_id: str, client_id: str) -> Material:
    material = memory_store.get_material(material_id)
    if material is None or material.client_id != client_id:
        raise ApiError(
            code="MATERIAL_NOT_FOUND",
            message="学习材料不存在或已过期，请重新提交",
            status_code=404,
        )
    return material


def get_owned_quiz(quiz_id: str, client_id: str) -> Quiz:
    quiz = memory_store.get_quiz(quiz_id)
    if quiz is None or quiz.client_id != client_id:
        raise ApiError(
            code="SESSION_EXPIRED",
            message="会话已过期，请重新生成闯关",
            status_code=404,
        )
    return quiz
