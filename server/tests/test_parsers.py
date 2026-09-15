"""输入解析层测试：文本/PDF 解析、截断、扫描版报错。"""

import io

import pytest

from app.parsers.material_parser import (
    normalize_text,
    parse_pdf_material,
    parse_text_material,
    truncate_material,
)
from app.schemas.api import ApiError


def _make_text_pdf(pages: list[str]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for text in pages:
        y = 800
        for line in text.split("\n"):
            c.drawString(50, y, line)
            y -= 16
        c.showPage()
    c.save()
    return buf.getvalue()


def _make_blank_pdf() -> bytes:
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    return buf.getvalue()


# ---------- normalize / truncate ----------


def test_normalize_collapses_blank_lines():
    assert normalize_text("a\r\n\r\n\r\nb\r") == "a\n\nb"


def test_truncate_short_text_unchanged():
    text, truncated = truncate_material("短文本", 100)
    assert text == "短文本"
    assert truncated is False


def test_truncate_keeps_head_and_tail():
    body = "段" * 1000
    text, truncated = truncate_material(body, 200)
    assert truncated is True
    assert len(text) <= 210
    assert text.startswith("段" * 50)
    assert "中段内容已省略" in text
    assert text.endswith("段" * 20)


# ---------- 文本材料 ----------


def test_text_material_ok():
    text = parse_text_material("Redis 缓存相关内容" * 10, min_chars=50)
    assert len(text) >= 50


def test_text_material_too_short():
    with pytest.raises(ApiError) as exc:
        parse_text_material("太短", min_chars=50)
    assert exc.value.code == "MATERIAL_TOO_SHORT"
    assert exc.value.status_code == 422


def test_text_material_over_max_truncated():
    text = parse_text_material("字" * 30000, max_chars=20000)
    assert len(text) <= 20010


# ---------- PDF 材料 ----------


def test_pdf_text_extracted():
    line = "Redis cache penetration breakdown avalanche " * 3
    data = _make_text_pdf([line])
    text = parse_pdf_material(data, min_chars=50)
    assert "Redis cache" in text


def test_pdf_blank_scanned_rejected():
    data = _make_blank_pdf()
    with pytest.raises(ApiError) as exc:
        parse_pdf_material(data, min_chars=50)
    assert exc.value.code == "PDF_PARSE_FAILED"


def test_pdf_too_large_rejected():
    with pytest.raises(ApiError) as exc:
        parse_pdf_material(b"x" * (11 * 1024 * 1024), max_bytes=10 * 1024 * 1024)
    assert exc.value.code == "PDF_TOO_LARGE"


def test_pdf_too_many_pages_rejected():
    data = _make_text_pdf(["page content line " * 5] * 51)
    with pytest.raises(ApiError) as exc:
        parse_pdf_material(data, max_pages=50)
    assert exc.value.code == "PDF_TOO_MANY_PAGES"


def test_pdf_corrupted_rejected():
    with pytest.raises(ApiError) as exc:
        parse_pdf_material(b"not a pdf at all" * 100, min_chars=50)
    assert exc.value.code == "PDF_PARSE_FAILED"
