"""材料提交 / PDF 上传（方案 5.2 / 8）。"""

from uuid import uuid4

from fastapi import APIRouter, Request, UploadFile
from fastapi.params import File, Form

from app.parsers.material_parser import parse_pdf_material, parse_text_material
from app.schemas.api import ApiError, MaterialCreateRequest, MaterialResponse
from app.schemas.quiz import Material
from app.stores import memory_store

router = APIRouter(tags=["materials"])


def _derive_title(text: str, fallback: str = "") -> str:
    first = text.strip().split("\n")[0].strip()
    return (first[:30] or fallback or "学习材料").strip()


@router.post("/materials", status_code=201, response_model=MaterialResponse)
async def create_material(req: MaterialCreateRequest, request: Request):
    settings = request.app.state.settings
    # 主题模式允许短输入（AI 基于主题扩展）；文本模式要求足够材料量
    min_chars = 4 if req.source_type == "topic" else settings.material_min_chars
    text = parse_text_material(req.text, min_chars=min_chars, max_chars=settings.material_max_chars)
    title = req.title.strip() or _derive_title(text)
    material = Material(
        id=f"mat_{uuid4().hex[:12]}",
        client_id=req.client_id,
        source_type=req.source_type,
        title=title,
        text=text,
        char_count=len(text),
    )
    memory_store.save_material(material)
    return MaterialResponse(material_id=material.id, title=title, char_count=len(text))


@router.post("/materials/upload", status_code=201, response_model=MaterialResponse)
async def upload_material(request: Request, client_id: str = Form(...), file: UploadFile = File(...)):
    settings = request.app.state.settings
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise ApiError(
            code="UNSUPPORTED_FILE_TYPE",
            message="目前仅支持 PDF 文件",
            status_code=422,
            detail={"filename": filename},
        )
    data = await file.read()
    text = parse_pdf_material(
        data,
        max_bytes=settings.pdf_max_bytes,
        max_pages=settings.pdf_max_pages,
        min_chars=settings.material_min_chars,
        max_chars=settings.material_max_chars,
    )
    title = filename.rsplit(".", 1)[0][:30] or "PDF 学习材料"
    material = Material(
        id=f"mat_{uuid4().hex[:12]}",
        client_id=client_id,
        source_type="pdf",
        title=title,
        text=text,
        char_count=len(text),
    )
    memory_store.save_material(material)
    return MaterialResponse(material_id=material.id, title=title, char_count=len(text))
