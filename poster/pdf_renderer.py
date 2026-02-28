"""
ポスター PDF 生成エンジン

Pillow の高解像度レンダリング（300 DPI 相当）を A4 PDF に埋め込む方式。
プレビューと完全に同じレイアウト・見た目で出力される。
"""

import io
from pathlib import Path
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

from poster.models import PosterData
from poster.preview_renderer import render_poster
from poster.layout import PDF_W, PDF_H


def render_poster_pdf(data: PosterData) -> bytes:
    """
    ポスターを PDF バイト列として返す。
    Pillow で 300 DPI 相当（scale=3.125）の高解像度画像を生成し、
    A4 PDF に全面埋め込む。プレビューと完全に同じ見た目になる。
    """
    # 300 DPI 相当: PREVIEW(96DPI) × 3.125 = 2481 × 3509 px
    hires_img = render_poster(data, scale=3.125)

    # PIL Image → BytesIO
    img_buf = io.BytesIO()
    hires_img.save(img_buf, format="PNG", dpi=(300, 300))
    img_buf.seek(0)

    # ReportLab で A4 PDF に埋め込み
    pdf_buf = io.BytesIO()
    c = rl_canvas.Canvas(pdf_buf, pagesize=A4)
    c.setTitle(f"GPI {data.year}年度 第{data.session_num}回ポスター")

    # A4 全面に画像を配置（ReportLab 座標は左下原点）
    c.drawImage(ImageReader(img_buf), 0, 0, width=PDF_W, height=PDF_H)

    c.save()
    return pdf_buf.getvalue()
