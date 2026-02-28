"""
ReportLab ベクターPDF 用の個別要素描画関数
- テキスト → PDF テキスト演算子（Illustrator で編集可能）
- 楕円・矩形 → PDF パス演算子（Illustrator で編集可能）
- 画像 → 埋め込みラスター（Illustrator でアクセス可能）

ReportLab 座標系: (0,0) = 左下、Y は上方向が正
引数 y はすべて「上端からの距離」で受け取り、内部で変換する。
"""

import io
import tempfile
from pathlib import Path
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics

from themes.color_themes import DARK_BROWN, DARK_BROWN_CIRCLE, WHITE, LIGHT_CREAM_BG
from poster.layout import PDF_W, PDF_H


def _rgb(t: tuple) -> Color:
    """(R,G,B) tuple → ReportLab Color"""
    return Color(t[0] / 255, t[1] / 255, t[2] / 255)


def _y(top_y: float) -> float:
    """上端Y（正規化）→ ReportLab 下端基準 Y（pt）"""
    return PDF_H - top_y * PDF_H


def _pt(n: float, axis: str = "h") -> float:
    """正規化値 → ポイント数"""
    return n * (PDF_H if axis == "h" else PDF_W)


def _font(weight: str = "Regular") -> str:
    """
    ReportLab で使用するフォント名を返す。
    HeiseiKakuGo-W5 は ReportLab 組み込みの日本語 CIDFont。
    Bold/Black も同一フォント（ウェイト区別なし）。
    Illustrator で開くとテキストとして編集可能。
    """
    return "HeiseiKakuGo-W5"


def _text_width(c: rl_canvas.Canvas, text: str, font: str, size: float) -> float:
    """テキスト幅をポイントで返す"""
    c.setFont(font, size)
    return pdfmetrics.stringWidth(text, font, size)


# ─── ヘッダーバー ──────────────────────────────────────────────────────────

def pdf_header_bar(c: rl_canvas.Canvas, h_pt: float, theme: dict):
    c.setFillColor(_rgb(DARK_BROWN))
    c.rect(0, PDF_H - h_pt, PDF_W, h_pt, fill=1, stroke=0)

    text = "Gifu  Pediatric-residency  Intensives"
    font_size = max(6, int(h_pt * 0.52))
    c.setFillColor(_rgb(WHITE))
    c.setFont(_font("Regular"), font_size)
    tw = pdfmetrics.stringWidth(text, _font("Regular"), font_size)
    c.drawString((PDF_W - tw) / 2, PDF_H - h_pt + (h_pt - font_size) * 0.3, text)


# ─── フッターバー ──────────────────────────────────────────────────────────

def pdf_footer_bar(c: rl_canvas.Canvas, h_pt: float, email: str):
    c.setFillColor(_rgb(DARK_BROWN))
    c.rect(0, 0, PDF_W, h_pt, fill=1, stroke=0)

    text = f"お問い合わせ先  岐阜県小児科研修支援グループ  Mail ＞  {email}"
    font_size = max(5, int(h_pt * 0.40))
    c.setFillColor(_rgb(WHITE))
    c.setFont(_font("Regular"), font_size)
    tw = pdfmetrics.stringWidth(text, _font("Regular"), font_size)
    c.drawString((PDF_W - tw) / 2, (h_pt - font_size) * 0.35, text)


# ─── 中央縦バー ────────────────────────────────────────────────────────────

def pdf_center_divider(c: rl_canvas.Canvas,
                        x_pt: float, y_top_pt: float, y_bot_pt: float,
                        w_pt: float, theme: dict):
    c.setFillColor(_rgb(theme["title_bar"]))
    c.rect(x_pt, y_bot_pt, w_pt, y_top_pt - y_bot_pt, fill=1, stroke=0)


# ─── 楕円バッジ（大・小共通） ─────────────────────────────────────────────

def _draw_ellipse_badge(c: rl_canvas.Canvas,
                         x_pt: float, y_top_pt: float,
                         bw_pt: float, bh_pt: float,
                         label: str, fill_color: tuple, text_color: tuple,
                         font_weight: str = "Bold"):
    """楕円バッジを描画してラベルを中央配置"""
    rl_y = y_top_pt - bh_pt  # ReportLab 下端Y

    c.setFillColor(_rgb(fill_color))
    c.ellipse(x_pt, rl_y, x_pt + bw_pt, rl_y + bh_pt, fill=1, stroke=0)

    # テキストサイズをフィッティング
    font = _font(font_weight)
    max_w = bw_pt * 0.80
    max_h = bh_pt * 0.75
    size = max_h
    tw = pdfmetrics.stringWidth(label, font, size)
    if tw > max_w:
        size = size * max_w / tw
    size = max(4, size)

    c.setFillColor(_rgb(text_color))
    c.setFont(font, size)
    tw2 = pdfmetrics.stringWidth(label, font, size)
    c.drawString(x_pt + (bw_pt - tw2) / 2,
                  rl_y + (bh_pt - size) / 2 + size * 0.15,
                  label)


def pdf_section_badge(c: rl_canvas.Canvas,
                       x_pt: float, y_top_pt: float,
                       bw_pt: float, bh_pt: float,
                       label: str, theme: dict):
    _draw_ellipse_badge(c, x_pt, y_top_pt, bw_pt, bh_pt,
                         label, theme["accent"], WHITE, "Bold")


def pdf_sub_badge(c: rl_canvas.Canvas,
                   x_pt: float, y_top_pt: float,
                   bw_pt: float, bh_pt: float,
                   label: str, theme: dict):
    _draw_ellipse_badge(c, x_pt, y_top_pt, bw_pt, bh_pt,
                         label, theme["accent_light"], DARK_BROWN, "Regular")


# ─── 場所バッジ ────────────────────────────────────────────────────────────

def pdf_basho_badge(c: rl_canvas.Canvas,
                     cx_pt: float, cy_top_pt: float, r_pt: float):
    """濃いブラウンの円に「場所」"""
    rl_cy = cy_top_pt  # ReportLab のY = PDF_H - top_y
    c.setFillColor(_rgb(DARK_BROWN_CIRCLE))
    c.circle(cx_pt, rl_cy, r_pt, fill=1, stroke=0)

    font = _font("Bold")
    size = r_pt * 0.75
    tw = pdfmetrics.stringWidth("場所", font, size)
    c.setFillColor(_rgb(WHITE))
    c.setFont(font, size)
    c.drawString(cx_pt - tw / 2, rl_cy - size * 0.35, "場所")


# ─── テキスト描画ヘルパー ─────────────────────────────────────────────────

def _wrap_jp(text: str, font: str, size: float, max_w: float) -> list:
    """文字単位の折り返し"""
    lines = []
    for para in text.split("\n"):
        current = ""
        for ch in para:
            test = current + ch
            tw = pdfmetrics.stringWidth(test, font, size)
            if tw > max_w and current:
                lines.append(current)
                current = ch
            else:
                current = test
        if current:
            lines.append(current)
    return lines


def _draw_text_block(c: rl_canvas.Canvas,
                      text: str, font_weight: str, size: float,
                      x_pt: float, y_top_pt: float, max_w: float,
                      color: tuple, line_spacing: float = 1.35) -> float:
    """
    テキストを折り返しながら描画。
    戻り値: 消費した高さ（pt）
    """
    font = _font(font_weight)
    c.setFont(font, size)
    lines = _wrap_jp(text, font, size, max_w)
    line_h = size * line_spacing
    c.setFillColor(_rgb(color))
    cur_rl_y = y_top_pt - size
    for line in lines:
        c.drawString(x_pt, cur_rl_y, line)
        cur_rl_y -= line_h
    return line_h * len(lines)


# ─── 会場情報 ──────────────────────────────────────────────────────────────

def pdf_venue_info(c: rl_canvas.Canvas,
                    x_pt: float, y_top_pt: float, max_w: float,
                    building: str, room: str, address: str,
                    font_size: float) -> float:
    """戻り値: 消費した高さ（pt）"""
    cur_top = y_top_pt
    cur_top -= _draw_text_block(c, building, "Bold", font_size,
                                  x_pt, cur_top, max_w, DARK_BROWN)
    cur_top -= font_size * 0.2
    cur_top -= _draw_text_block(c, room, "Regular", font_size * 0.85,
                                  x_pt, cur_top, max_w, DARK_BROWN)
    cur_top -= font_size * 0.1
    cur_top -= _draw_text_block(c, address, "Regular", font_size * 0.80,
                                  x_pt, cur_top, max_w, DARK_BROWN)
    return y_top_pt - cur_top


# ─── Zoom セクション ───────────────────────────────────────────────────────

def pdf_zoom_section(c: rl_canvas.Canvas,
                      x_pt: float, y_top_pt: float, max_w: float,
                      note: str, font_size: float, theme: dict) -> float:
    icon_sz = font_size * 1.6
    r = icon_sz * 0.18
    color = theme["zoom_color"]

    rl_y = y_top_pt - icon_sz
    c.setFillColor(_rgb(color))
    c.roundRect(x_pt, rl_y, icon_sz, icon_sz, radius=r, fill=1, stroke=0)

    # "Z"
    c.setFillColor(_rgb(WHITE))
    c.setFont(_font("Black"), icon_sz * 0.6)
    zw = pdfmetrics.stringWidth("Z", _font("Black"), icon_sz * 0.6)
    c.drawString(x_pt + (icon_sz - zw) / 2, rl_y + icon_sz * 0.2, "Z")

    # テキスト
    tx = x_pt + icon_sz + font_size * 0.4
    avail = max_w - icon_sz - font_size * 0.4
    _draw_text_block(c, note, "Regular", font_size, tx,
                      y_top_pt - (icon_sz - font_size) / 2,
                      avail, DARK_BROWN)

    return icon_sz + font_size * 0.3


# ─── QR コード ─────────────────────────────────────────────────────────────

def pdf_qr(c: rl_canvas.Canvas, qr_pil_img,
            x_pt: float, y_top_pt: float, size_pt: float):
    """QR PIL Image → PDF 埋め込み"""
    from reportlab.lib.utils import ImageReader
    buf = io.BytesIO()
    qr_pil_img.save(buf, format="PNG")
    buf.seek(0)
    c.drawImage(
        ImageReader(buf), x_pt, y_top_pt - size_pt, size_pt, size_pt,
        preserveAspectRatio=True, mask="auto"
    )


# ─── 対象 ──────────────────────────────────────────────────────────────────

def pdf_audience_section(c: rl_canvas.Canvas,
                          x_pt: float, y_top_pt: float, max_w: float,
                          audience: list, font_size: float, theme: dict) -> float:
    label = "（対象）"
    bh = font_size * 1.5
    bw = max_w

    # バッジ
    rl_y = y_top_pt - bh
    c.setFillColor(_rgb(theme["accent"]))
    c.roundRect(x_pt, rl_y, bw, bh, radius=bh * 0.4, fill=1, stroke=0)
    font = _font("Bold")
    size = min(font_size * 1.1, bh * 0.65)
    tw = pdfmetrics.stringWidth(label, font, size)
    c.setFillColor(_rgb(WHITE))
    c.setFont(font, size)
    c.drawString(x_pt + (bw - tw) / 2, rl_y + (bh - size) * 0.4, label)

    cur_top = y_top_pt - bh - font_size * 0.3
    for item in audience:
        bullet = "◆ " + item
        cur_top -= _draw_text_block(c, bullet, "Regular", font_size,
                                     x_pt, cur_top, max_w, DARK_BROWN,
                                     line_spacing=1.25)
        cur_top -= font_size * 0.1
    return y_top_pt - cur_top


# ─── セミナータイトル（縦書き） ────────────────────────────────────────────

def pdf_vertical_title(c: rl_canvas.Canvas,
                         line1: str, line2: str,
                         x_pt: float, y_top_pt: float, y_bot_pt: float,
                         w_pt: float, font_size: float):
    """
    ReportLab の rotate() を使って縦書きタイトルを描画。
    """
    avail_h = y_top_pt - y_bot_pt  # pt高さ

    # line1: 年度
    c.saveState()
    c.translate(x_pt + w_pt / 2, y_bot_pt + avail_h * 0.70)
    c.rotate(90)
    size1 = font_size * 0.65
    c.setFont(_font("Bold"), size1)
    tw1 = pdfmetrics.stringWidth(line1, _font("Bold"), size1)
    c.setFillColor(_rgb(DARK_BROWN))
    c.drawString(-tw1 / 2, -size1 * 0.35, line1)
    c.restoreState()

    # line2: 回数+セミナー名
    c.saveState()
    c.translate(x_pt + w_pt / 2, y_bot_pt + avail_h * 0.35)
    c.rotate(90)
    size2 = font_size
    avail_w2 = avail_h * 0.65
    # テキストが収まるようにフォントサイズ調整
    tw2 = pdfmetrics.stringWidth(line2, _font("Black"), size2)
    if tw2 > avail_w2:
        size2 = size2 * avail_w2 / tw2
    c.setFont(_font("Black"), size2)
    tw2 = pdfmetrics.stringWidth(line2, _font("Black"), size2)
    c.setFillColor(_rgb(DARK_BROWN))
    c.drawString(-tw2 / 2, -size2 * 0.35, line2)
    c.restoreState()


# ─── 日時 ─────────────────────────────────────────────────────────────────

def pdf_date_time(c: rl_canvas.Canvas,
                   x_pt: float, y_top_pt: float, max_w: float,
                   event_date: str, time_range: str,
                   size_date: float, size_time: float) -> float:
    cur_top = y_top_pt
    cur_top -= _draw_text_block(c, event_date, "Black", size_date,
                                  x_pt, cur_top, max_w, DARK_BROWN)
    cur_top -= size_date * 0.1
    cur_top -= _draw_text_block(c, time_range, "Bold", size_time,
                                  x_pt, cur_top, max_w, DARK_BROWN)
    return y_top_pt - cur_top


# ─── 発表タイトル ──────────────────────────────────────────────────────────

def pdf_content_title(c: rl_canvas.Canvas,
                       x_pt: float, y_top_pt: float, max_w: float,
                       title: str, font_size: float) -> float:
    return _draw_text_block(c, title, "Bold", font_size, x_pt, y_top_pt,
                             max_w, DARK_BROWN, line_spacing=1.35)


# ─── 発表者情報 ────────────────────────────────────────────────────────────

def pdf_presenter(c: rl_canvas.Canvas,
                   x_pt: float, y_top_pt: float, max_w: float,
                   affiliation: str, name: str, font_size: float) -> float:
    cur_top = y_top_pt
    cur_top -= _draw_text_block(c, affiliation, "Regular", font_size,
                                  x_pt, cur_top, max_w, DARK_BROWN, line_spacing=1.2)
    cur_top -= _draw_text_block(c, name, "Bold", font_size * 1.05,
                                  x_pt, cur_top, max_w, DARK_BROWN, line_spacing=1.2)
    return y_top_pt - cur_top


# ─── 司会・座長 ────────────────────────────────────────────────────────────

def pdf_mc_row(c: rl_canvas.Canvas,
                x_pt: float, y_top_pt: float, max_w: float,
                bw_pt: float, bh_pt: float,
                label: str, person, font_size: float, theme: dict) -> float:
    # バッジ
    pdf_section_badge(c, x_pt, y_top_pt, bw_pt, bh_pt, label, theme)
    # テキスト
    tx = x_pt + bw_pt + font_size * 0.4
    avail = max_w - bw_pt - font_size * 0.4
    cur_top = y_top_pt
    cur_top -= _draw_text_block(c, person.affiliation, "Regular", font_size,
                                  tx, cur_top, avail, DARK_BROWN, line_spacing=1.2)
    cur_top -= _draw_text_block(c, person.name, "Bold", font_size,
                                  tx, cur_top, avail, DARK_BROWN, line_spacing=1.2)
    consumed = y_top_pt - cur_top
    return max(bh_pt, consumed)


# ─── 背景画像 ──────────────────────────────────────────────────────────────

def pdf_background_image(c: rl_canvas.Canvas, img_path: str, opacity: float = 0.35):
    """
    背景画像を A4 全面に透明度をかけて描画する。
    ReportLab はネイティブに透明度を画像に持たないため、
    Pillow で白と合成してから埋め込む。
    """
    try:
        from PIL import Image as PILImage
        from utils.image_utils import resize_cover
        import io as _io

        img = PILImage.open(img_path).convert("RGBA")
        # A4相当のピクセルサイズに変換（150DPI）
        target_w, target_h = int(PDF_W * 150 / 72), int(PDF_H * 150 / 72)
        img = resize_cover(img, target_w, target_h)

        white = PILImage.new("RGBA", img.size, (255, 255, 255, 255))
        r, g, b, a = img.split()
        a = a.point(lambda x: int(x * opacity))
        img = PILImage.merge("RGBA", (r, g, b, a))
        composited = PILImage.alpha_composite(white, img).convert("RGB")

        from reportlab.lib.utils import ImageReader as _IR
        buf = _io.BytesIO()
        composited.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(_IR(buf), 0, 0, PDF_W, PDF_H, preserveAspectRatio=False)
    except Exception as e:
        print(f"背景画像PDF埋め込みエラー: {e}")


# ─── 装飾イラスト ──────────────────────────────────────────────────────────

def pdf_illustration(c: rl_canvas.Canvas, img_path: str,
                      x_pt: float, y_top_pt: float, size_pt: float):
    """装飾イラスト（PNG透過対応）を埋め込む"""
    try:
        buf = io.BytesIO()
        from PIL import Image as PILImage
        img = PILImage.open(img_path).convert("RGBA")
        img.thumbnail((int(size_pt * 5), int(size_pt * 5)), PILImage.LANCZOS)
        iw, ih = img.size
        aspect = iw / ih
        if aspect >= 1:
            draw_w = size_pt
            draw_h = size_pt / aspect
        else:
            draw_h = size_pt
            draw_w = size_pt * aspect
        from reportlab.lib.utils import ImageReader as _IR2
        img.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(_IR2(buf), x_pt, y_top_pt - draw_h, draw_w, draw_h,
                     preserveAspectRatio=True, mask="auto")
    except Exception as e:
        print(f"イラストPDF埋め込みエラー: {e}")
