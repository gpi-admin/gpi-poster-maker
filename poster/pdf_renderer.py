"""
ポスター PDF 生成エンジン（ベクター編集対応）

- テキスト・図形は ReportLab のネイティブ要素として描画
- Illustrator で文字位置や文言を個別編集可能
- 画像（QR・背景・装飾）は埋め込みラスター
"""

import io
from pathlib import Path

from PIL import Image
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas as rl_canvas

import poster.layout as _layout
from poster.layout import (
    LayoutEngine,
    PREVIEW_H,
    PREVIEW_W,
    PDF_H,
    PDF_W,
    HEADER_H,
    HEADER_TOP,
    FOOTER_H,
    FOOTER_GROUP_SCALE,
    LEFT_W,
    TITLE_X,
    TITLE_W,
    SECT_X,
    SECT_W,
    PROG_X,
    PROG_W,
    LC_PAD_L,
    LC_PAD_R,
    PROG_PAD_L,
    PROG_PAD_R,
    PROG_TOP,
    BASHO_BH,
    BASHO_BW,
    BADGE_SM_H,
    FS_VENUE_BIG,
    FS_VENUE_SM,
    FS_DATE_LBL,
    FS_DATE_BIG,
    FS_TIME_LC,
    FS_MC_BADGE,
    FS_AUD,
    FS_QR_CAP,
    FS_PROG_TIME,
    FS_PROG_TITLE,
    FS_PRESENTER,
    FS_PRES_NAME,
    FS_SANSHUUHI,
    FS_V_TITLE,
    SECTION_CONTENT_SCALES,
)
from poster.models import PosterData
from poster.qr_generator import generate_qr
from poster.zoom_icon import build_zoom_icon
from themes.color_themes import DARK_BROWN, WHITE, get_theme
from utils.image_utils import make_background_layer

# layout.py が旧版でも起動できるように既定値でフォールバック
ZOOM_TEXT_SHIFT_RATIO = getattr(_layout, "ZOOM_TEXT_SHIFT_RATIO", 0.060)
ZOOM_ICON_SIZE_SCALE = getattr(_layout, "ZOOM_ICON_SIZE_SCALE", 1.45)
ZOOM_ICON_RIGHT_PAD = getattr(_layout, "ZOOM_ICON_RIGHT_PAD", 0.040)
ZOOM_TEXT_ICON_GAP = getattr(_layout, "ZOOM_TEXT_ICON_GAP", 0.040)
ZOOM_ICON_LOGO_SCALE = getattr(_layout, "ZOOM_ICON_LOGO_SCALE", 0.80)
ZOOM_ICON_ROTATE_DEG = getattr(_layout, "ZOOM_ICON_ROTATE_DEG", 8.0)

ASSETS_DIR = Path(__file__).parent.parent / "assets"
_BIZ_FONT_DIR = ASSETS_DIR / "fonts" / "BIZUDGothic"
_VERTICAL_ROTATE_CHARS = frozenset("ーｰ")

# フォント名定数（_ensure_pdf_fonts() 呼び出し後に確定する）
_FONT_REG = "HeiseiKakuGo-W5"      # ゴシック体
_FONT_MINCHO = "HeiseiMin-W3"      # 明朝体
_FONT_BOLD = "HeiseiKakuGo-W5"     # 太字ゴシック（BIZ UDがあれば差し替え）
_USE_TTF = False                    # TrueType埋め込みが有効かどうか


def _register_biz_ud_fonts() -> bool:
    """
    BIZ UD Gothic/Mincho の TrueType フォントを ReportLab に登録する。
    assets/fonts/BIZUDGothic/ にフォントファイルが揃っている場合のみ有効。
    TrueType 埋め込みにより Illustrator でテキスト編集が可能になる。
    """
    from reportlab.pdfbase.ttfonts import TTFont

    reg_path = _BIZ_FONT_DIR / "BIZUDGothic-Regular.ttf"
    bold_path = _BIZ_FONT_DIR / "BIZUDGothic-Bold.ttf"
    mincho_path = _BIZ_FONT_DIR / "BIZUDMincho-Regular.ttf"

    # Regular と Bold の両方が揃っていることを確認
    if not (reg_path.exists() and bold_path.exists()):
        return False

    try:
        # 未登録の場合のみ登録
        try:
            pdfmetrics.getFont("BIZUDGothic-Regular")
        except Exception:
            pdfmetrics.registerFont(TTFont("BIZUDGothic-Regular", str(reg_path)))

        try:
            pdfmetrics.getFont("BIZUDGothic-Bold")
        except Exception:
            pdfmetrics.registerFont(TTFont("BIZUDGothic-Bold", str(bold_path)))

        if mincho_path.exists():
            try:
                pdfmetrics.getFont("BIZUDMincho-Regular")
            except Exception:
                pdfmetrics.registerFont(TTFont("BIZUDMincho-Regular", str(mincho_path)))

        return True
    except Exception as e:
        print(f"BIZ UD フォント登録エラー: {e}")
        return False


def _ensure_pdf_fonts():
    """
    PDF 用フォントを登録し、グローバル定数を設定する。
    BIZ UD Gothic (TrueType) が利用可能ならそちらを優先する（Illustrator でテキスト編集可能）。
    利用できない場合は CID フォント (HeiseiKakuGo-W5) にフォールバックする。
    """
    global _FONT_REG, _FONT_MINCHO, _FONT_BOLD, _USE_TTF

    if _USE_TTF:
        return  # 既に TTF 設定済み

    if _register_biz_ud_fonts():
        _FONT_REG = "BIZUDGothic-Regular"
        _FONT_BOLD = "BIZUDGothic-Bold"
        # 明朝体: BIZ UD Mincho があれば使う、なければゴシックで代替
        mincho_path = _BIZ_FONT_DIR / "BIZUDMincho-Regular.ttf"
        _FONT_MINCHO = "BIZUDMincho-Regular" if mincho_path.exists() else "BIZUDGothic-Regular"
        _USE_TTF = True
        return

    # フォールバック: ReportLab 組み込み CID フォント（非埋め込み）
    for name in {"HeiseiKakuGo-W5", "HeiseiMin-W3"}:
        try:
            pdfmetrics.getFont(name)
        except Exception:
            pdfmetrics.registerFont(UnicodeCIDFont(name))
    _FONT_REG = "HeiseiKakuGo-W5"
    _FONT_BOLD = "HeiseiKakuGo-W5"
    _FONT_MINCHO = "HeiseiMin-W3"


def _rgb(c: tuple) -> Color:
    return Color(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)


def _text_width(text: str, font: str, size: float) -> float:
    return pdfmetrics.stringWidth(text, font, size)


def _font_metrics(font: str, size: float) -> tuple[float, float, float]:
    asc, desc = pdfmetrics.getAscentDescent(font, size)
    return asc, desc, (asc - desc)


def _draw_text_raw(
    c: rl_canvas.Canvas,
    text: str,
    x: float,
    baseline_y: float,
    font: str,
    size: float,
    color: tuple,
    stroke_width: float = 0.0,
):
    c.saveState()
    txt = c.beginText()
    txt.setTextOrigin(x, baseline_y)
    txt.setFont(font, size)
    txt.setFillColor(_rgb(color))
    if stroke_width > 0:
        c.setStrokeColor(_rgb(color))
        c.setLineWidth(stroke_width)
        txt.setTextRenderMode(2)  # fill + stroke
    txt.textOut(text)
    c.drawText(txt)
    c.restoreState()


def _wrap_jp(text: str, font: str, size: float, max_w: float) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            test = cur + ch
            if _text_width(test, font, size) > max_w and cur:
                lines.append(cur)
                cur = ch
            else:
                cur = test
        if cur:
            lines.append(cur)
    return lines


def _draw_multiline(
    c: rl_canvas.Canvas,
    lines: list[str],
    x: float,
    y_top: float,
    font: str,
    size: float,
    color: tuple,
    line_spacing: float,
    align: str = "left",
    max_w: float | None = None,
) -> float:
    if not lines:
        return 0.0
    asc, desc, ch = _font_metrics(font, size)
    line_h = ch * line_spacing
    cur_top = y_top
    for line in lines:
        lw = _text_width(line, font, size)
        if align == "center" and max_w:
            lx = x + (max_w - lw) / 2
        elif align == "right" and max_w:
            lx = x + max_w - lw
        else:
            lx = x
        baseline = PDF_H - (cur_top + asc)
        _draw_text_raw(c, line, lx, baseline, font, size, color)
        cur_top += line_h
    return line_h * len(lines)


def _fit_font_size(text: str, font: str, max_w: float, max_size: float, min_size: float) -> float:
    size = max_size
    while size > min_size and _text_width(text, font, size) > max_w:
        size -= 0.5
    return max(min_size, size)


def _draw_pill(
    c: rl_canvas.Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    fill: tuple,
):
    y_bottom = PDF_H - (y_top + h)
    c.setFillColor(_rgb(fill))
    c.roundRect(x, y_bottom, w, h, radius=max(2, h / 3), fill=1, stroke=0)


def _draw_centered_in_box(
    c: rl_canvas.Canvas,
    text: str,
    x: float,
    y_top: float,
    w: float,
    h: float,
    font: str,
    size: float,
    color: tuple,
    y_offset: float = 0.0,
):
    asc, desc, ch = _font_metrics(font, size)
    tx = x + (w - _text_width(text, font, size)) / 2
    ty = y_top + (h - ch) / 2 + y_offset
    baseline = PDF_H - (ty + asc)
    _draw_text_raw(c, text, tx, baseline, font, size, color)


def _draw_spaced_text(
    c: rl_canvas.Canvas,
    text: str,
    x: float,
    y_top: float,
    box_h: float,
    total_w: float,
    font: str,
    size: float,
    color: tuple,
):
    chars = list(text)
    if not chars:
        return
    widths = [_text_width(ch, font, size) for ch in chars]
    chars_w = sum(widths)
    gap = 0.0 if len(chars) <= 1 else (total_w - chars_w) / (len(chars) - 1)
    asc, _, ch = _font_metrics(font, size)
    ty = y_top + (box_h - ch) / 2
    baseline = PDF_H - (ty + asc)
    cx = x
    for chv, wv in zip(chars, widths):
        _draw_text_raw(c, chv, cx, baseline, font, size, color)
        cx += wv + gap


def _draw_text_raw_mincho_boldish(
    c: rl_canvas.Canvas,
    text: str,
    x: float,
    baseline_y: float,
    font: str,
    size: float,
    color: tuple,
):
    """明朝体描画。
    注: stroke_width（fill+stroke = テキストレンダーモード2）は使わない。
    Illustratorはレンダーモード0（fill only）以外のテキストをアウトライン化するため。
    """
    _draw_text_raw(c, text, x, baseline_y, font, size, color)


def _draw_vertical_stack(
    c: rl_canvas.Canvas,
    text: str,
    x: float,
    y_top: float,
    y_bot: float,
    strip_w: float,
    font: str,
    base_size: float,
    color: tuple,
    top_pad: float,
    bot_pad: float,
    gap_ratio: float,
):
    if not text:
        return
    num = len(text)
    y_top += top_pad
    avail_h = max(1.0, (y_bot - y_top) - bot_pad)
    size = min(base_size, max(8.0, strip_w * 0.88))
    asc, _, ch = _font_metrics(font, size)
    gap = max(2.0, ch * gap_ratio)
    step = ch + gap
    if step * num > avail_h:
        ratio = avail_h / (step * num)
        size = max(8.0, size * ratio)
        asc, desc, ch = _font_metrics(font, size)
        gap = max(2.0, ch * gap_ratio)
        step = ch + gap
    cur_top = y_top + (avail_h - step * num) / 2

    for chv in text:
        lw = _text_width(chv, font, size)
        cx = x + (strip_w - lw) / 2
        char_top = cur_top + (step - ch) / 2
        if chv in _VERTICAL_ROTATE_CHARS:
            # 長音符だけ回転させ、縦書き表現に寄せる
            c.saveState()
            # 回転中心を少し左へ寄せて、見た目の中央を補正する
            center_x = x + strip_w / 2 - size * 0.12
            center_y = PDF_H - (char_top + ch / 2)
            c.translate(center_x, center_y)
            c.rotate(-90)
            # stroke_width は使わない（テキストレンダーモード2はIllustratorがアウトライン化するため）
            _draw_text_raw(c, chv, -lw / 2, -((asc + desc) / 2.0), font, size, color)
            c.restoreState()
        else:
            baseline = PDF_H - (char_top + asc)
            _draw_text_raw_mincho_boldish(c, chv, cx, baseline, font, size, color)
        cur_top += step


def _draw_background_image(c: rl_canvas.Canvas, data: PosterData):
    bg_path = getattr(data, "background_image_path", None)
    if not bg_path:
        return
    p = Path(bg_path)
    if not p.exists():
        return
    try:
        layer = make_background_layer(str(p), PREVIEW_W, PREVIEW_H, opacity=data.bg_opacity)
        # Illustrator互換: 透明チャンネルを白背景に合成して透明度を排除する
        # mask="auto" を使うとPDFに透明度が生じ、Illustratorがテキストをアウトライン化してしまう
        white = Image.new("RGB", (layer.width, layer.height), (255, 255, 255))
        if layer.mode == "RGBA":
            white.paste(layer, mask=layer.split()[3])
        else:
            white.paste(layer.convert("RGB"))
        buf = io.BytesIO()
        white.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, width=PDF_W, height=PDF_H)
    except Exception as e:
        print(f"背景画像PDF埋め込みエラー: {e}")


def _draw_decorative(c: rl_canvas.Canvas, img_path: str, x: float, y_top: float, size: float):
    try:
        p = Path(img_path)
        if not p.exists():
            return
        img = Image.open(p).convert("RGBA")
        img.thumbnail((int(size * 5), int(size * 5)), Image.LANCZOS)
        iw, ih = img.size
        if iw <= 0 or ih <= 0:
            return
        aspect = iw / ih
        if aspect >= 1:
            dw = size
            dh = size / aspect
        else:
            dh = size
            dw = size * aspect
        # Illustrator互換: 透明チャンネルを白背景に合成して透明度を排除する
        white = Image.new("RGB", (iw, ih), (255, 255, 255))
        white.paste(img, mask=img.split()[3])
        buf = io.BytesIO()
        white.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(ImageReader(buf), x, PDF_H - (y_top + dh), dw, dh)
    except Exception as e:
        print(f"装飾画像PDF埋め込みエラー: {e}")


def render_poster_pdf(data: PosterData) -> bytes:
    """
    Illustrator 編集可能なベクター主体 PDF を生成する。
    """
    _ensure_pdf_fonts()
    theme = get_theme(data.theme_key, data.custom_accent_color, data.custom_accent_light)

    def pw(n: float) -> float:
        return n * PDF_W

    def ph(n: float) -> float:
        return n * PDF_H

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"GPI {data.year}年度 第{data.session_num}回ポスター")

    # 背景画像（指定時のみ）
    _draw_background_image(c, data)

    # ヘッダー・フッター
    header_top = ph(HEADER_TOP)
    header_h = ph(HEADER_H)
    header_bottom = header_top + header_h
    footer_h = ph(FOOTER_H)
    footer_top = PDF_H - footer_h

    c.setFillColor(_rgb(theme.get("title_bar", DARK_BROWN)))
    c.rect(0, PDF_H - (header_top + header_h), PDF_W, header_h, fill=1, stroke=0)
    c.rect(0, 0, PDF_W, footer_h, fill=1, stroke=0)

    header_font_size = max(8.0, header_h * 0.52)
    header_pad = max(8.0, PDF_W * 0.03)
    _draw_spaced_text(
        c,
        "Gifu Pediatric-residency Intensives",
        header_pad,
        header_top,
        header_h,
        PDF_W - header_pad * 2,
        _FONT_REG,
        header_font_size,
        WHITE,
    )

    footer_font_size = max(6.0, footer_h * 0.40)
    footer_fs_large = footer_font_size * FOOTER_GROUP_SCALE
    before = "お問い合わせ先  "
    group = "岐阜県小児科研修支援グループ"
    after = f"  Mail ▶  {data.contact_email}"
    w1 = _text_width(before, _FONT_REG, footer_font_size)
    w2 = _text_width(group, _FONT_REG, footer_fs_large)
    w3 = _text_width(after, _FONT_REG, footer_font_size)
    footer_w = w1 + w2 + w3
    footer_asc, _, footer_ch = _font_metrics(_FONT_REG, footer_font_size)
    footer_baseline = PDF_H - (footer_top + (footer_h - footer_ch) / 2 + footer_asc)
    footer_x = (PDF_W - footer_w) / 2
    _draw_text_raw(c, before, footer_x, footer_baseline, _FONT_REG, footer_font_size, WHITE)
    _draw_text_raw(c, group, footer_x + w1, footer_baseline, _FONT_REG, footer_fs_large, WHITE)
    _draw_text_raw(c, after, footer_x + w1 + w2, footer_baseline, _FONT_REG, footer_font_size, WHITE)

    # 左・中央・右の基本位置
    lc_x = pw(LC_PAD_L)
    lc_w = pw(LEFT_W) - pw(LC_PAD_L) - pw(LC_PAD_R)
    title_x = pw(TITLE_X)
    title_w = pw(TITLE_W)
    sect_x = pw(SECT_X)
    sect_w = pw(SECT_W)
    prog_x = pw(PROG_X) + pw(PROG_PAD_L)
    prog_w = pw(PROG_W) - pw(PROG_PAD_L) - pw(PROG_PAD_R)

    # 縦書きメインタイトル
    _draw_vertical_stack(
        c,
        f"第{data.session_num}回岐阜県小児科研修セミナー",
        title_x,
        header_bottom,
        footer_top,
        title_w,
        _FONT_MINCHO,
        ph(FS_V_TITLE),
        DARK_BROWN,
        top_pad=max(10.0, (footer_top - header_bottom) / 80.0),
        bot_pad=max(12.0, (footer_top - header_bottom) / 65.0),
        gap_ratio=0.08,
    )

    # 右ストリップ上部: 年度
    prog_top_y = ph(PROG_TOP)
    v_pad = max(12.0, (footer_top - header_bottom) / 65.0)
    year_text = f"{data.year}年度"
    if year_text:
        step = max(1.0, (prog_top_y - ph(0.005) - (header_bottom + v_pad)) / len(year_text))
        fs_year = max(8.0, min(sect_w, step * 1.10))
        cur_top = header_bottom + v_pad
        for chv in year_text:
            asc, _, ch_h = _font_metrics(_FONT_MINCHO, fs_year)
            lw = _text_width(chv, _FONT_MINCHO, fs_year)
            cx = sect_x + (sect_w - lw) / 2
            char_top = cur_top + max(0.0, (step - ch_h) / 2)
            baseline = PDF_H - (char_top + asc)
            _draw_text_raw_mincho_boldish(c, chv, cx, baseline, _FONT_MINCHO, fs_year, DARK_BROWN)
            cur_top += step

    # 左カラム
    cur_y = header_bottom + ph(0.026)

    # 場所バッジ + 会場
    badge_w = pw(BASHO_BW)
    badge_h = ph(BASHO_BH)
    _draw_pill(c, lc_x, cur_y, badge_w, badge_h, (90, 60, 35))
    basho_fs = _fit_font_size("場所", _FONT_REG, badge_w * 0.78, badge_h * 0.75, 8.0)
    _draw_centered_in_box(
        c, "場所", lc_x, cur_y, badge_w, badge_h, _FONT_REG, basho_fs, WHITE, y_offset=basho_fs * 0.08
    )

    venue_x = lc_x + badge_w + pw(0.009)
    venue_w = pw(LEFT_W) - venue_x - pw(LC_PAD_R)
    venue_fs_big = ph(FS_VENUE_BIG)
    venue_fs_sm = ph(FS_VENUE_SM)

    if "\n" in data.venue_building:
        b_lines = data.venue_building.split("\n")
        venue_h = _draw_multiline(
            c, b_lines, venue_x, cur_y, _FONT_REG, venue_fs_big, DARK_BROWN, 1.25
        )
    else:
        b_size = _fit_font_size(data.venue_building, _FONT_REG, venue_w, venue_fs_big, 8.0)
        asc, _, ch_h = _font_metrics(_FONT_REG, b_size)
        b_base = PDF_H - (cur_y + asc)
        _draw_text_raw(c, data.venue_building, venue_x, b_base, _FONT_REG, b_size, DARK_BROWN)
        venue_h = ch_h * 1.25

    if data.venue_room:
        room_fs = max(8.0, venue_fs_sm * 1.4)
        r_lines = _wrap_jp(data.venue_room, _FONT_REG, room_fs, venue_w)
        venue_h += _draw_multiline(
            c, r_lines, venue_x, cur_y + venue_h, _FONT_REG, room_fs, DARK_BROWN, 1.2, align="right", max_w=venue_w
        )
    cur_y += max(badge_h, venue_h) + ph(0.005)

    # 住所
    addr_fs = ph(FS_VENUE_SM)
    addr_lines = _wrap_jp(data.venue_address, _FONT_REG, addr_fs, venue_w + max(2.0, addr_fs / 3))
    addr_h = _draw_multiline(c, addr_lines, venue_x, cur_y, _FONT_REG, addr_fs, DARK_BROWN, 1.2)
    line_y = cur_y + addr_h + max(3.0, addr_fs * 0.4)
    c.setStrokeColor(_rgb(DARK_BROWN))
    c.setLineWidth(1.0)
    c.line(venue_x, PDF_H - line_y, venue_x + venue_w, PDF_H - line_y)
    cur_y += (line_y + 2.0 - cur_y) + ph(0.018)

    # ハイブリッド開催（左寄せ気味） + テーマ連動 Zoom アイコン
    zoom_fs = max(10.0, ph(FS_VENUE_SM) * 1.8)
    zoom_text = "ハイブリッド開催"
    zoom_asc, _, zoom_ch = _font_metrics(_FONT_REG, zoom_fs)
    zoom_tw = _text_width(zoom_text, _FONT_REG, zoom_fs)

    icon_size = max(zoom_ch, zoom_ch * ZOOM_ICON_SIZE_SCALE)
    block_h = max(zoom_ch, icon_size)
    icon_right_pad = max(2.0, lc_w * ZOOM_ICON_RIGHT_PAD)
    icon_x = lc_x + lc_w - icon_right_pad - icon_size
    icon_y = cur_y + (block_h - icon_size) / 2

    text_x = lc_x + (lc_w - zoom_tw) / 2 - (lc_w * ZOOM_TEXT_SHIFT_RATIO)
    min_gap = max(4.0, lc_w * ZOOM_TEXT_ICON_GAP)
    if text_x + zoom_tw > icon_x - min_gap:
        text_x = icon_x - min_gap - zoom_tw
    text_x = max(lc_x + max(2.0, lc_w * 0.02), text_x)
    text_top = cur_y + (block_h - zoom_ch) / 2
    zoom_baseline = PDF_H - (text_top + zoom_asc)
    _draw_text_raw(c, zoom_text, text_x, zoom_baseline, _FONT_REG, zoom_fs, DARK_BROWN)

    zoom_line_y = text_top + zoom_ch + 2.0
    c.setStrokeColor(_rgb(DARK_BROWN))
    c.setLineWidth(2.0)
    c.line(text_x, PDF_H - zoom_line_y, text_x + zoom_tw, PDF_H - zoom_line_y)

    try:
        icon_color = theme.get("accent_light", theme["accent"])
        icon_img = build_zoom_icon(
            max(32, int(icon_size * 3)),
            icon_color,
            logo_scale=ZOOM_ICON_LOGO_SCALE,
        ).convert("RGB")
        icon_buf = io.BytesIO()
        icon_img.save(icon_buf, format="PNG")
        icon_buf.seek(0)
        icon_reader = ImageReader(icon_buf)
        cx = icon_x + icon_size / 2
        cy = PDF_H - (icon_y + icon_size / 2)
        c.saveState()
        c.translate(cx, cy)
        c.rotate(ZOOM_ICON_ROTATE_DEG)
        c.drawImage(
            icon_reader,
            -icon_size / 2,
            -icon_size / 2,
            icon_size,
            icon_size,
        )
        c.restoreState()
    except Exception as e:
        print(f"ZoomアイコンPDF描画エラー: {e}")

    cur_y += (zoom_line_y + 2.0 - cur_y) + ph(0.022)

    # 日付・時刻
    event_date = data.event_date or ""
    if "年 " in event_date:
        p0, p1 = event_date.split("年 ", 1)
        year_label, date_main = p0 + "年", p1
    elif "年" in event_date:
        idx = event_date.index("年")
        year_label, date_main = event_date[: idx + 1], event_date[idx + 1 :].strip()
    else:
        year_label, date_main = "", event_date

    yr_indent = max(3.0, ph(FS_DATE_LBL) * 0.3)
    if year_label:
        yr_fs = ph(FS_DATE_LBL)
        yr_asc, _, yr_h = _font_metrics(_FONT_REG, yr_fs)
        yr_base = PDF_H - (cur_y + yr_asc)
        _draw_text_raw(c, year_label, lc_x + yr_indent, yr_base, _FONT_REG, yr_fs, DARK_BROWN)
        cur_y += yr_h + yr_fs * 0.2

    segs: list[tuple[str, bool]] = []
    if date_main:
        cur = ""
        cur_is_num = None
        for chv in date_main:
            is_num = chv.isdigit()
            if cur_is_num is None:
                cur_is_num = is_num
            if is_num != cur_is_num:
                segs.append((cur, bool(cur_is_num)))
                cur = chv
                cur_is_num = is_num
            else:
                cur += chv
        if cur:
            segs.append((cur, bool(cur_is_num)))

    fs_num = max(10.0, ph(FS_DATE_BIG) * 0.75)
    fs_kana = max(8.0, ph(FS_DATE_BIG) * 0.50)
    seg_info = []
    total_w = 0.0
    max_h = 0.0
    for txt, is_num in segs:
        font = _FONT_REG
        size = fs_num if is_num else fs_kana
        asc, _, h = _font_metrics(font, size)
        w = _text_width(txt, font, size)
        seg_info.append((txt, is_num, size, asc, h, w))
        total_w += w
        max_h = max(max_h, h)
    if total_w > lc_w and total_w > 0:
        ratio = lc_w / total_w
        fs_num = max(8.0, fs_num * ratio)
        fs_kana = max(6.0, fs_kana * ratio)
        seg_info = []
        total_w = 0.0
        max_h = 0.0
        for txt, is_num in segs:
            size = fs_num if is_num else fs_kana
            asc, _, h = _font_metrics(_FONT_REG, size)
            w = _text_width(txt, _FONT_REG, size)
            seg_info.append((txt, is_num, size, asc, h, w))
            total_w += w
            max_h = max(max_h, h)

    cur_x = lc_x
    for txt, _is_num, size, asc, h, w in seg_info:
        top = cur_y + (max_h - h)
        baseline = PDF_H - (top + asc)
        _draw_text_raw(c, txt, cur_x, baseline, _FONT_REG, size, DARK_BROWN)
        cur_x += w
    cur_y += max_h + ph(FS_DATE_BIG) * 0.18

    time_fs = ph(FS_TIME_LC)
    time_lines = _wrap_jp(data.time_range, _FONT_REG, time_fs, lc_w - yr_indent)
    time_h = _draw_multiline(
        c,
        time_lines,
        lc_x + yr_indent,
        cur_y,
        _FONT_REG,
        time_fs,
        DARK_BROWN,
        1.2,
    )
    cur_y += time_h + ph(0.018)

    # 司会/座長
    mc_cs = SECTION_CONTENT_SCALES[0]
    fs_mc_aff = ph(FS_PRESENTER * mc_cs)
    fs_mc_name = ph(FS_PRES_NAME * mc_cs)

    def draw_person_row(label: str, person):
        nonlocal cur_y
        badge_h2 = ph(FS_MC_BADGE) * 2.0
        badge_font = _fit_font_size(label, _FONT_REG, lc_w * 0.75, ph(FS_MC_BADGE) + 2, 8.0)
        badge_w2 = min(_text_width(label, _FONT_REG, badge_font) + ph(FS_MC_BADGE) * 2.0, lc_w)
        _draw_pill(c, lc_x, cur_y, badge_w2, badge_h2, theme["accent"])
        _draw_centered_in_box(
            c, label, lc_x, cur_y, badge_w2, badge_h2, _FONT_REG, badge_font, WHITE,
            y_offset=badge_font * 0.08
        )
        cur_y += badge_h2 + ph(FS_MC_BADGE) * 0.7

        aff_lines = _wrap_jp(person.affiliation, _FONT_REG, fs_mc_aff, lc_w)
        aff_h = _draw_multiline(c, aff_lines, lc_x, cur_y, _FONT_REG, fs_mc_aff, DARK_BROWN, 1.2)
        cur_y += aff_h + fs_mc_aff * 0.5

        fs_sensei = max(8.0, fs_mc_name * 0.85)
        nm_w = _text_width(person.name, _FONT_REG, fs_mc_name)
        ss_w = _text_width(" 先生", _FONT_REG, fs_sensei)
        _, _, nm_h = _font_metrics(_FONT_REG, fs_mc_name)
        ss_asc, _, ss_h = _font_metrics(_FONT_REG, fs_sensei)
        nm_asc, _, _ = _font_metrics(_FONT_REG, fs_mc_name)
        line_h = max(nm_h, ss_h)
        right_margin = fs_mc_name * 1.0
        right_edge = lc_x + lc_w - right_margin
        name_top = cur_y + (line_h - nm_h)
        ss_top = cur_y + (line_h - ss_h)
        _draw_text_raw(
            c,
            person.name,
            right_edge - nm_w - ss_w,
            PDF_H - (name_top + nm_asc),
            _FONT_REG,
            fs_mc_name,
            DARK_BROWN,
        )
        _draw_text_raw(
            c,
            " 先生",
            right_edge - ss_w,
            PDF_H - (ss_top + ss_asc),
            _FONT_REG,
            fs_sensei,
            DARK_BROWN,
        )
        cur_y += line_h * 1.2

    if data.mc:
        draw_person_row("総合司会", data.mc)
        cur_y += ph(0.012)
    if data.chair:
        draw_person_row(data.chair_label, data.chair)
        cur_y += ph(0.012)

    # 対象
    aud_fs = ph(FS_AUD)
    aud_badge_h = aud_fs * 1.9
    aud_label_fs = _fit_font_size("対象", _FONT_REG, lc_w * 0.45, aud_fs + 2, 8.0)
    aud_badge_w = min(_text_width("対象", _FONT_REG, aud_label_fs) + aud_fs * 2.0, lc_w)
    _draw_pill(c, lc_x, cur_y, aud_badge_w, aud_badge_h, theme["accent"])
    _draw_centered_in_box(
        c, "対象", lc_x, cur_y, aud_badge_w, aud_badge_h, _FONT_REG, aud_label_fs, WHITE,
        y_offset=aud_label_fs * 0.08
    )
    cur_y += aud_badge_h + aud_fs * 0.7

    col_w = lc_w / 2.0 - 4.0
    col_items = [data.audience[i : i + 2] for i in range(0, len(data.audience), 2)]
    for pair in col_items:
        row_h = 0.0
        for ci, item in enumerate(pair):
            txt = "・" + item
            lines = _wrap_jp(txt, _FONT_REG, aud_fs, col_w)
            h = _draw_multiline(
                c,
                lines,
                lc_x + ci * (col_w + 8.0),
                cur_y,
                _FONT_REG,
                aud_fs,
                DARK_BROWN,
                1.2,
            )
            row_h = max(row_h, h)
        cur_y += row_h + aud_fs * 0.1
    cur_y += ph(0.010)

    # QR
    cap_fs = ph(FS_QR_CAP)
    cap2_fs = max(cap_fs + 1.0, cap_fs * 1.12)
    _, _, cap_h = _font_metrics(_FONT_REG, cap_fs)
    _, _, cap2_h = _font_metrics(_FONT_REG, cap2_fs)
    cap_gap = cap_h * 0.3
    total_cap_h = cap_h + cap2_h + cap_gap
    qr_bottom = footer_top - ph(0.020) - total_cap_h - ph(0.006)
    max_qr = qr_bottom - cur_y - ph(0.005)
    qr_size = max(ph(0.08), min(lc_w, max_qr))
    if qr_size > ph(0.06):
        qr_img = generate_qr(data.registration_url or "", size_px=max(100, int(qr_size)))
        qr_x = lc_x + (lc_w - qr_size) / 2
        # Illustrator互換: QRコードをRGBに変換して透明度を排除する
        qr_rgb = Image.new("RGB", qr_img.size, (255, 255, 255))
        if qr_img.mode == "RGBA":
            qr_rgb.paste(qr_img, mask=qr_img.split()[3])
        else:
            qr_rgb.paste(qr_img.convert("RGB"))
        qr_buf = io.BytesIO()
        qr_rgb.save(qr_buf, format="PNG")
        qr_buf.seek(0)
        c.drawImage(ImageReader(qr_buf), qr_x, PDF_H - qr_bottom, qr_size, qr_size)

        cap1 = "事前登録はこちらから"
        cap2 = "※現地参加の方も登録してください"
        cap_y = qr_bottom + ph(0.003)
        cap1_w = _text_width(cap1, _FONT_REG, cap_fs)
        cap1_asc, _, _ = _font_metrics(_FONT_REG, cap_fs)
        _draw_text_raw(
            c,
            cap1,
            lc_x + (lc_w - cap1_w) / 2,
            PDF_H - (cap_y + cap1_asc),
            _FONT_REG,
            cap_fs,
            DARK_BROWN,
        )
        cap2_w = _text_width(cap2, _FONT_REG, cap2_fs)
        cap2_asc, _, _ = _font_metrics(_FONT_REG, cap2_fs)
        _draw_text_raw(
            c,
            cap2,
            lc_x + (lc_w - cap2_w) / 2,
            PDF_H - (cap_y + cap_h + cap_gap + cap2_asc),
            _FONT_REG,
            cap2_fs,
            DARK_BROWN,
        )

    # プログラムエリア
    free_fs = ph(FS_SANSHUUHI)
    free_text = "参加費無料"
    free_tw = _text_width(free_text, _FONT_REG, free_fs)
    free_x = prog_x + prog_w - free_tw - pw(0.012)
    free_y = header_bottom + ph(0.018)
    free_asc, _, _ = _font_metrics(_FONT_REG, free_fs)
    _draw_text_raw(c, free_text, free_x, PDF_H - (free_y + free_asc), _FONT_REG, free_fs, (220, 30, 30))

    layout = LayoutEngine(data, render_scale=1.0).compute()
    section_positions: list[dict] = []

    for block in layout:
        by = ph(block.y)
        sc = block.data.get("scale", 1.0)
        cs = block.data.get("content_scale", 1.0)

        if block.kind == "section_time":
            fs = ph(FS_PROG_TIME) * sc
            asc, _, _ = _font_metrics(_FONT_REG, fs)
            _draw_text_raw(
                c,
                block.data.get("text", ""),
                prog_x,
                PDF_H - (by + asc),
                _FONT_REG,
                fs,
                DARK_BROWN,
            )
            section_positions.append({"label": block.data.get("part_label", ""), "y_start": by})

        elif block.kind == "sub_badge":
            bh = ph(BADGE_SM_H) * sc
            max_w = prog_w * 0.75
            fs = max(7.0, bh * 0.78)
            label = block.data.get("label", "")
            while fs > 7.0 and _text_width(label, _FONT_REG, fs) > max_w * 0.92:
                fs -= 0.5
            badge_w = min(_text_width(label, _FONT_REG, fs) + bh * 1.8, max_w)
            _draw_pill(c, prog_x, by, badge_w, bh, theme["accent"])
            _draw_centered_in_box(
                c, label, prog_x, by, badge_w, bh, _FONT_REG, fs, WHITE, y_offset=fs * 0.08
            )

        elif block.kind == "title":
            fs = ph(FS_PROG_TITLE) * sc * cs
            lines = block.data.get("lines") or _wrap_jp(block.data.get("text", ""), _FONT_REG, fs, prog_w)
            _draw_multiline(c, lines, prog_x, by, _FONT_REG, fs, DARK_BROWN, 1.35)

        elif block.kind == "affiliation":
            fs = ph(FS_PRESENTER) * sc * cs
            lines = block.data.get("lines") or _wrap_jp(block.data.get("text", ""), _FONT_REG, fs, prog_w)
            _draw_multiline(c, lines, prog_x, by, _FONT_REG, fs, DARK_BROWN, 1.25)

        elif block.kind == "name":
            name = block.data.get("text", "")
            fs_name = ph(FS_PRES_NAME) * sc * cs
            fs_sensei = max(8.0, fs_name * 0.85)
            nm_w = _text_width(name, _FONT_REG, fs_name)
            ss_w = _text_width(" 先生", _FONT_REG, fs_sensei)
            nm_asc, _, nm_h = _font_metrics(_FONT_REG, fs_name)
            ss_asc, _, ss_h = _font_metrics(_FONT_REG, fs_sensei)
            line_h = max(nm_h, ss_h)
            right_edge = prog_x + prog_w
            name_top = by + (line_h - nm_h)
            ss_top = by + (line_h - ss_h)
            _draw_text_raw(
                c,
                name,
                right_edge - nm_w - ss_w,
                PDF_H - (name_top + nm_asc),
                _FONT_REG,
                fs_name,
                DARK_BROWN,
            )
            _draw_text_raw(
                c,
                " 先生",
                right_edge - ss_w,
                PDF_H - (ss_top + ss_asc),
                _FONT_REG,
                fs_sensei,
                DARK_BROWN,
            )

    # 右ストリップ: 第N部ラベルボックス
    for i, pos in enumerate(section_positions):
        y_start = pos["y_start"]
        if i + 1 < len(section_positions):
            y_end = section_positions[i + 1]["y_start"]
        else:
            y_end = footer_top - ph(0.008)

        pad = max(2.0, sect_w * 0.23)
        box_h = y_end - y_start - pad * 2
        if box_h < 20:
            continue
        bx = sect_x + pad
        by = y_start + pad
        bw = sect_w - pad * 2
        color = theme.get("accent_light", theme["accent"])

        c.setFillColor(_rgb(color))
        c.roundRect(
            bx,
            PDF_H - (by + box_h),
            bw,
            box_h,
            radius=max(4.0, bw / 4),
            fill=1,
            stroke=0,
        )

        label = pos.get("label", "")
        display = label
        if "部" in label:
            display = label[: label.index("部") + 1]
        fs = max(11.0, bw * 0.62)
        asc, _, ch = _font_metrics(_FONT_REG, fs)
        step = ch + 2.0
        start_top = by + max(4.0, (box_h - step * len(display)) / 2)
        cur_top = start_top
        for chv in display:
            lw = _text_width(chv, _FONT_REG, fs)
            cx = bx + (bw - lw) / 2
            if cur_top + ch <= by + box_h:
                _draw_text_raw(c, chv, cx, PDF_H - (cur_top + asc), _FONT_REG, fs, DARK_BROWN)
            cur_top += step

    # 装飾イラスト
    deco_imgs = getattr(data, "decorative_images", [])
    if deco_imgs:
        illust_size = lc_w * 0.65
        positions = [
            (lc_x + lc_w * 0.0, PDF_H * 0.60),
            (lc_x + lc_w * 0.35, PDF_H * 0.68),
        ]
        for i, img_path in enumerate(deco_imgs[:2]):
            if i < len(positions):
                px, py = positions[i]
                _draw_decorative(c, img_path, px, py, illust_size)

    c.save()
    return buf.getvalue()
