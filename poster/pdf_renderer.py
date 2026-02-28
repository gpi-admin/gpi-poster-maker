"""
ポスター PDF 生成エンジン

Pillow の高解像度レンダリング（300 DPI 相当）を A4 PDF に埋め込む方式。
プレビューと完全に同じレイアウト・見た目で出力される。
"""

import io
from PIL import Image
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

from poster.models import PosterData
from poster.preview_renderer import render_poster
from poster.layout import PDF_W, PDF_H, HIRES_W, HIRES_H
from utils.font_manager import force_bold_fonts


def render_poster_pdf(data: PosterData) -> bytes:
    """
    ポスターを PDF バイト列として返す。
    Pillow でプレビュー基準画像を生成し、300 DPI 相当に拡大して
    A4 PDF に全面埋め込む。PDF 側は全テキストを太字寄りに描画する。
    """
    # PNG と改行結果を一致させるため、まずプレビュー基準で描画し
    # 300DPI 相当に拡大して PDF に埋め込む。PDF では文字を太字寄りに強制する。
    with force_bold_fonts(True):
        base_img = render_poster(data, scale=1.0, transparent_bg=True)
    hires_img = base_img.resize((HIRES_W, HIRES_H), Image.Resampling.LANCZOS)

    # PIL Image → BytesIO
    img_buf = io.BytesIO()
    hires_img.save(img_buf, format="PNG", dpi=(300, 300))
    img_buf.seek(0)

    # ReportLab で A4 PDF に埋め込み
    pdf_buf = io.BytesIO()
    c = rl_canvas.Canvas(pdf_buf, pagesize=A4)
    c.setTitle(f"GPI {data.year}年度 第{data.session_num}回ポスター")

    # A4 全面に画像を配置（ReportLab 座標は左下原点）
    c.drawImage(ImageReader(img_buf), 0, 0, width=PDF_W, height=PDF_H, mask="auto")

    c.save()
    return pdf_buf.getvalue()
