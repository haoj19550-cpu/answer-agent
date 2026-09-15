"""输入解析层：输入源 → 统一纯文本（方案 3.5 / 5.2）。

策略接口 MaterialParser.parse() -> str，新输入源只新增实现类。
"""

import io
from typing import Protocol

from app.schemas.api import ApiError

TRUNCATION_MARK = "\n……（中段内容已省略）……\n"


def normalize_text(text: str) -> str:
    """基础去噪：统一换行、压缩连续空白行。"""
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    out: list[str] = []
    blank = 0
    for line in lines:
        if line:
            out.append(line)
            blank = 0
        else:
            blank += 1
            if blank <= 1:
                out.append("")
    return "\n".join(out).strip()


def truncate_material(text: str, max_chars: int) -> tuple[str, bool]:
    """超长截断：保留首尾（前 60% / 后 40%），中段省略。返回 (文本, 是否截断)。"""
    if len(text) <= max_chars:
        return text, False
    head = int(max_chars * 0.6)
    tail = max_chars - head - len(TRUNCATION_MARK)
    return text[:head] + TRUNCATION_MARK + text[-tail:], True


class MaterialParser(Protocol):
    def parse(self) -> str: ...


class TextMaterialParser:
    """主题/文本直传。"""

    def __init__(self, text: str, min_chars: int = 50, max_chars: int = 20000):
        self.text = text
        self.min_chars = min_chars
        self.max_chars = max_chars

    def parse(self) -> str:
        text = normalize_text(self.text)
        if len(text) < self.min_chars:
            raise ApiError(
                code="MATERIAL_TOO_SHORT",
                message="内容太少啦，再多提供一点学习材料吧",
                status_code=422,
                detail={"min_chars": self.min_chars, "actual": len(text)},
            )
        truncated, _ = truncate_material(text, self.max_chars)
        return truncated


class PdfMaterialParser:
    """文本型 PDF：pdfplumber 主，pypdf 备。扫描版/加密明确报错。"""

    def __init__(
        self,
        data: bytes,
        max_bytes: int = 10 * 1024 * 1024,
        max_pages: int = 50,
        min_chars: int = 50,
        max_chars: int = 20000,
    ):
        self.data = data
        self.max_bytes = max_bytes
        self.max_pages = max_pages
        self.min_chars = min_chars
        self.max_chars = max_chars

    def parse(self) -> str:
        if len(self.data) > self.max_bytes:
            raise ApiError(
                code="PDF_TOO_LARGE",
                message="PDF 文件超过 10MB，请压缩后重试",
                status_code=422,
                detail={"max_bytes": self.max_bytes},
            )
        text = self._extract_pdfplumber()
        if text is None:
            text = self._extract_pypdf()
        if text is None:
            raise ApiError(
                code="PDF_PARSE_FAILED",
                message="该 PDF 无法解析，可能是扫描版或加密文件",
                status_code=422,
            )
        text = normalize_text(text)
        if len(text) < self.min_chars:
            # 能打开但几乎无文本 → 扫描版
            raise ApiError(
                code="PDF_PARSE_FAILED",
                message="该 PDF 可能是扫描版（图片型），暂不支持，请提供文本型 PDF",
                status_code=422,
            )
        truncated, _ = truncate_material(text, self.max_chars)
        return truncated

    def _extract_pdfplumber(self) -> str | None:
        try:
            import pdfplumber

            parts: list[str] = []
            with pdfplumber.open(io.BytesIO(self.data)) as pdf:
                if len(pdf.pages) > self.max_pages:
                    raise ApiError(
                        code="PDF_TOO_MANY_PAGES",
                        message=f"PDF 超过 {self.max_pages} 页，请拆分后重试",
                        status_code=422,
                    )
                for page in pdf.pages:
                    parts.append(page.extract_text() or "")
            return "\n".join(parts)
        except ApiError:
            raise
        except Exception:
            return None

    def _extract_pypdf(self) -> str | None:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(self.data))
            if len(reader.pages) > self.max_pages:
                raise ApiError(
                    code="PDF_TOO_MANY_PAGES",
                    message=f"PDF 超过 {self.max_pages} 页，请拆分后重试",
                    status_code=422,
                )
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except ApiError:
            raise
        except Exception:
            return None


def parse_text_material(text: str, *, min_chars: int = 50, max_chars: int = 20000) -> str:
    return TextMaterialParser(text, min_chars=min_chars, max_chars=max_chars).parse()


def parse_pdf_material(
    data: bytes,
    *,
    max_bytes: int = 10 * 1024 * 1024,
    max_pages: int = 50,
    min_chars: int = 50,
    max_chars: int = 20000,
) -> str:
    return PdfMaterialParser(
        data, max_bytes=max_bytes, max_pages=max_pages, min_chars=min_chars, max_chars=max_chars
    ).parse()
