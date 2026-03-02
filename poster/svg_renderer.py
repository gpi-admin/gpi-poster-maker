"""
ポスター SVG 生成エンジン（Illustrator 編集対応）

- テキストは SVG <text> 要素として出力 → Illustrator でフォント・文言が編集可能
- 矩形・線はネイティブ SVG 要素（ベクター）
- 画像（QR・背景・装飾）は base64 埋め込みラスター
- フォント: "BIZ UDGothic" / "BIZ UDMincho"（~/Library/Fonts にインストール済みであること）

座標系: ページ左上原点・Y 軸下向き（PDF renderer の layout 座標と同じ）
PDF renderer との違い: PDF の「底辺原点 Y フリップ」が不要なため座標変換がシンプル。
"""

import base64
import io
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import poster.layout as _layout
from poster.layout import (
    LayoutEngine,
    PDF_H,
    PDF_W,
    PREVIEW_H,
    PREVIEW_W,
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

# ReportLab 登録名（メトリクス計算用）
_RL_GOTHIC = "BIZUDGothic-Regular"
_RL_GOTHIC_BOLD = "BIZUDGothic-Bold"
_RL_MINCHO = "BIZUDMincho-Regular"

# SVG font-family 名（デフォルト: macOS システムフォント ヒラギノ）
# render_poster_svg() の font_key 引数でフォントを選択できる
_SVG_GOTHIC = "Hiragino Sans"
_SVG_MINCHO = "Hiragino Mincho ProN"

# ---------------------------------------------------------------------------
# フォント設定（SVG 埋め込みフォント対応）
# ---------------------------------------------------------------------------

@dataclass
class SVGFontConfig:
    key: str
    gothic_family: str          # @font-face 名（埋め込み用）
    mincho_family: str
    gothic_regular_path: Path | None = None
    gothic_bold_path: Path | None = None
    mincho_regular_path: Path | None = None
    # fontconfig/システムフォント名（embed_fonts=False 時に使用）
    # 空文字のときは gothic_family / mincho_family をそのまま使用
    system_gothic_family: str = ""
    system_mincho_family: str = ""
    # True = Bold Mincho あり（Hiragino Mincho ProN W6 等）
    # False = Bold Mincho なし → font-weight を 400 に抑制（BIZ UDMincho 等）
    mincho_has_bold: bool = True


# 起動時に BIZ UD フォントを base64 でプリロード（@font-face 埋め込み用）
_FONT_B64: dict[str, str] = {}

def _preload_font_b64() -> None:
    for key, fname in [
        ("gothic_regular", "BIZUDGothic-Regular.ttf"),
        ("gothic_bold",    "BIZUDGothic-Bold.ttf"),
        ("mincho_regular", "BIZUDMincho-Regular.ttf"),
    ]:
        p = _BIZ_FONT_DIR / fname
        if p.exists():
            _FONT_B64[key] = base64.b64encode(p.read_bytes()).decode()

_preload_font_b64()


SVG_FONT_PRESETS: dict[str, SVGFontConfig] = {
    "hiragino": SVGFontConfig(
        key="hiragino",
        gothic_family="Hiragino Sans",
        mincho_family="Hiragino Mincho ProN",
        # cairosvg は "Hiragino Sans" + font-weight を太字として解決しないため、
        # システムフォント名で W6 を明示する（embed_fonts=False 時に使用）。
        system_gothic_family="Hiragino Sans W6",
        system_mincho_family="Hiragino Mincho ProN W6",
    ),
    "biz_ud": SVGFontConfig(
        key="biz_ud",
        gothic_family="BIZ UDGothic",       # フォント内部名と一致させること（cairosvg が @font-face を正しく解決するため）
        mincho_family="BIZ UDMincho",
        gothic_regular_path=_BIZ_FONT_DIR / "BIZUDGothic-Regular.ttf",
        gothic_bold_path=_BIZ_FONT_DIR / "BIZUDGothic-Bold.ttf",
        mincho_regular_path=_BIZ_FONT_DIR / "BIZUDMincho-Regular.ttf",
        system_gothic_family="BIZ UDGothic",
        system_mincho_family="BIZ UDMincho",
        mincho_has_bold=False,  # BIZ UDMincho Bold が存在しないため
    ),
}
SVG_FONT_DEFAULT = "hiragino"

W = PDF_W
H = PDF_H


# ---------------------------------------------------------------------------
# フォント登録（メトリクス計算用）
# ---------------------------------------------------------------------------

_svg_fonts_registered = False


def _ensure_svg_fonts():
    global _svg_fonts_registered
    if _svg_fonts_registered:
        return
    for name, fname in [
        (_RL_GOTHIC,      "BIZUDGothic-Regular.ttf"),
        (_RL_GOTHIC_BOLD, "BIZUDGothic-Bold.ttf"),
        (_RL_MINCHO,      "BIZUDMincho-Regular.ttf"),
    ]:
        path = _BIZ_FONT_DIR / fname
        if path.exists():
            try:
                pdfmetrics.getFont(name)
            except Exception:
                try:
                    pdfmetrics.registerFont(TTFont(name, str(path)))
                except Exception:
                    pass
    _svg_fonts_registered = True


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def _hex(c: tuple) -> str:
    return "#{:02X}{:02X}{:02X}".format(int(c[0]), int(c[1]), int(c[2]))


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def _tw(text: str, rl_font: str, size: float) -> float:
    """ReportLab フォントでテキスト幅を計算（SVG レイアウト用）。"""
    return pdfmetrics.stringWidth(text, rl_font, size)


def _fm(rl_font: str, size: float) -> tuple[float, float, float]:
    asc, desc = pdfmetrics.getAscentDescent(rl_font, size)
    return asc, desc, asc - desc


def _wrap_jp(text: str, rl_font: str, size: float, max_w: float) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            test = cur + ch
            if _tw(test, rl_font, size) > max_w and cur:
                lines.append(cur)
                cur = ch
            else:
                cur = test
        if cur:
            lines.append(cur)
    return lines


def _fit_font_size(
    text: str, rl_font: str, max_w: float, max_size: float, min_size: float
) -> float:
    size = max_size
    while size > min_size and _tw(text, rl_font, size) > max_w:
        size -= 0.5
    return max(min_size, size)


# ---------------------------------------------------------------------------
# SVG キャンバス
# ---------------------------------------------------------------------------

class SVGCanvas:
    """
    軽量 SVG キャンバス。
    座標はすべてページ左上原点・Y 軸下向き（PDF renderer の layout 座標と同じ）。
    """

    def __init__(self, width: float, height: float, font_config: SVGFontConfig | None = None):
        self.W = width
        self.H = height
        self._parts: list[str] = []
        fc = font_config or SVG_FONT_PRESETS[SVG_FONT_DEFAULT]
        self.gothic = fc.gothic_family
        self.mincho = fc.mincho_family
        self._mincho_has_bold = fc.mincho_has_bold
        self._font_config = fc

    def rect(
        self,
        x: float,
        y_top: float,
        w: float,
        h: float,
        rx: float = 0,
        fill: tuple | None = None,
        stroke_color: tuple | None = None,
        stroke_width: float = 1.0,
    ):
        attrs = f'x="{x:.3f}" y="{y_top:.3f}" width="{w:.3f}" height="{h:.3f}"'
        if rx > 0:
            attrs += f' rx="{rx:.3f}" ry="{rx:.3f}"'
        attrs += f' fill="{_hex(fill)}"' if fill else ' fill="none"'
        if stroke_color:
            attrs += f' stroke="{_hex(stroke_color)}" stroke-width="{stroke_width:.2f}"'
        else:
            attrs += ' stroke="none"'
        self._parts.append(f'<rect {attrs}/>')

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: tuple,
        width: float = 1.0,
    ):
        self._parts.append(
            f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="{_hex(color)}" stroke-width="{width:.2f}"/>'
        )

    def text(
        self,
        content: str,
        x: float,
        baseline_y: float,
        svg_font: str,
        size: float,
        color: tuple,
        transform: str = "",
        font_weight: str = "",
        text_anchor: str = "",
    ):
        if not content:
            return
        # font_weight 未指定時:
        # ゴシック → W6(600)
        # 明朝 → Bold が存在するフォント(Hiragino等)なら 600、なければ 400
        # BIZ UDMincho は Bold バリアントが存在しないため 600 を要求すると
        # macOS CoreText が別フォント（Hiragino Mincho等）にフォールバックして
        # Linux/FreeType と異なる表示になる。
        if not font_weight:
            if svg_font == self.mincho and not self._mincho_has_bold:
                font_weight = "400"
            else:
                font_weight = "600"
        attrs = (
            f'x="{x:.3f}" y="{baseline_y:.3f}" '
            f'font-family="{_esc(svg_font)}" font-size="{size:.3f}" '
            f'font-weight="{font_weight}" '
            f'fill="{_hex(color)}" '
            f'xml:space="preserve"'
        )
        if text_anchor:
            attrs += f' text-anchor="{text_anchor}"'
        if transform:
            attrs += f' transform="{transform}"'
        self._parts.append(f'<text {attrs}>{_esc(content)}</text>')

    def image(
        self,
        img_bytes: bytes,
        x: float,
        y_top: float,
        w: float,
        h: float,
        transform: str = "",
    ):
        b64 = base64.b64encode(img_bytes).decode("ascii")
        attrs = (
            f'x="{x:.3f}" y="{y_top:.3f}" width="{w:.3f}" height="{h:.3f}" '
            f'xlink:href="data:image/png;base64,{b64}"'
        )
        if transform:
            attrs += f' transform="{transform}"'
        self._parts.append(
            f"<image {attrs}/>"
        )

    def to_svg(self) -> str:
        # @font-face 埋め込み（埋め込みフォントが指定されている場合のみ）
        fc = self._font_config
        face_rules: list[str] = []
        if fc.gothic_regular_path:
            for family, weight, b64key in [
                (fc.gothic_family, "400", "gothic_regular"),
                (fc.gothic_family, "700", "gothic_bold"),
                (fc.mincho_family, "400", "mincho_regular"),
            ]:
                b64 = _FONT_B64.get(b64key, "")
                if b64:
                    face_rules.append(
                        f"@font-face{{font-family:'{family}';font-weight:{weight};"
                        f"src:url('data:font/truetype;base64,{b64}') format('truetype');}}"
                    )

        header = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{self.W:.3f}pt" height="{self.H:.3f}pt" '
            f'viewBox="0 0 {self.W:.3f} {self.H:.3f}">\n'
        )
        if face_rules:
            header += "<defs><style>" + "".join(face_rules) + "</style></defs>\n"
        body = "\n".join(self._parts)
        return header + body + "\n</svg>"


# ---------------------------------------------------------------------------
# 描画ヘルパー
# ---------------------------------------------------------------------------

def _draw_text(
    c: SVGCanvas,
    text: str,
    x: float,
    y_top: float,
    rl_font: str,
    svg_font: str,
    size: float,
    color: tuple,
):
    """y_top はテキスト上端からの距離（レイアウト座標）。baseline に変換して描画。"""
    asc, _, _ = _fm(rl_font, size)
    baseline = y_top + asc
    c.text(text, x, baseline, svg_font, size, color)


def _draw_text_at_baseline(
    c: SVGCanvas,
    text: str,
    x: float,
    baseline: float,
    svg_font: str,
    size: float,
    color: tuple,
    transform: str = "",
):
    """baseline はページ上端からベースラインまでの距離。"""
    c.text(text, x, baseline, svg_font, size, color, transform=transform)


def _draw_multiline(
    c: SVGCanvas,
    lines: list[str],
    x: float,
    y_top: float,
    rl_font: str,
    svg_font: str,
    size: float,
    color: tuple,
    line_spacing: float,
    align: str = "left",
    max_w: float | None = None,
) -> float:
    if not lines:
        return 0.0
    asc, _, ch = _fm(rl_font, size)
    line_h = ch * line_spacing
    cur_top = y_top
    for line in lines:
        lw = _tw(line, rl_font, size)
        if align == "center" and max_w:
            lx = x + (max_w - lw) / 2
        elif align == "right" and max_w:
            lx = x + max_w - lw
        else:
            lx = x
        baseline = cur_top + asc
        c.text(line, lx, baseline, svg_font, size, color)
        cur_top += line_h
    return line_h * len(lines)


def _draw_centered_in_box(
    c: SVGCanvas,
    text: str,
    x: float,
    y_top: float,
    w: float,
    h: float,
    rl_font: str,
    svg_font: str,
    size: float,
    color: tuple,
    y_offset: float = 0.0,
):
    asc, _, ch = _fm(rl_font, size)
    tx = x + (w - _tw(text, rl_font, size)) / 2
    ty = y_top + (h - ch) / 2 + y_offset
    baseline = ty + asc
    c.text(text, tx, baseline, svg_font, size, color)


def _draw_spaced_text(
    c: SVGCanvas,
    text: str,
    x: float,
    y_top: float,
    box_h: float,
    total_w: float,
    rl_font: str,
    svg_font: str,
    size: float,
    color: tuple,
):
    chars = list(text)
    if not chars:
        return
    widths = [_tw(ch, rl_font, size) for ch in chars]
    chars_w = sum(widths)
    gap = 0.0 if len(chars) <= 1 else (total_w - chars_w) / (len(chars) - 1)
    asc, _, ch = _fm(rl_font, size)
    ty = y_top + (box_h - ch) / 2
    baseline = ty + asc
    cx = x
    for chv, wv in zip(chars, widths):
        c.text(chv, cx, baseline, svg_font, size, color)
        cx += wv + gap


def _draw_pill(
    c: SVGCanvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    fill: tuple,
):
    c.rect(x, y_top, w, h, rx=max(2, h / 3), fill=fill)


def _draw_vertical_stack(
    c: SVGCanvas,
    text: str,
    x: float,
    y_top: float,
    y_bot: float,
    strip_w: float,
    rl_font: str,
    svg_font: str,
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
    asc, desc, ch = _fm(rl_font, size)
    gap = max(2.0, ch * gap_ratio)
    step = ch + gap
    if step * num > avail_h:
        ratio = avail_h / (step * num)
        size = max(8.0, size * ratio)
        asc, desc, ch = _fm(rl_font, size)
        gap = max(2.0, ch * gap_ratio)
        step = ch + gap
    cur_top = y_top + (avail_h - step * num) / 2

    for chv in text:
        lw = _tw(chv, rl_font, size)
        cx = x + (strip_w - lw) / 2
        char_top = cur_top + (step - ch) / 2
        if chv in _VERTICAL_ROTATE_CHARS:
            # 長音符を +90° 回転して縦書き表現
            # SVG は Y 軸下向きなので正回転が時計回り（PDF の -90 と逆）
            center_x = x + strip_w / 2
            center_y = char_top + ch / 2
            rot = f"rotate(90, {center_x:.3f}, {center_y:.3f})"
            baseline = char_top + asc
            c.text(chv, cx, baseline, svg_font, size, color, transform=rot)
        else:
            baseline = char_top + asc
            c.text(chv, cx, baseline, svg_font, size, color)
        cur_top += step


def _embed_image_opaque(img: Image.Image) -> bytes:
    """RGBA 画像を白背景に合成して PNG バイト列で返す（透明度排除）。"""
    if img.mode == "RGBA":
        white = Image.new("RGB", img.size, (255, 255, 255))
        white.paste(img, mask=img.split()[3])
        img = white
    else:
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _embed_image_alpha(img: Image.Image) -> bytes:
    """RGBA 画像の透明度を維持した PNG バイト列を返す。"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# メイン描画関数
# ---------------------------------------------------------------------------

def render_poster_svg(
    data: PosterData,
    font_key: str = SVG_FONT_DEFAULT,
    embed_fonts: bool = True,
) -> str:
    """
    Illustrator 編集可能な SVG を生成する。

    Args:
        data: ポスターデータ
        font_key: フォントプリセットキー（SVG_FONT_PRESETS のキー）
                  "hiragino" (デフォルト・macOS のみ) / "biz_ud" (全環境・埋め込み)
        embed_fonts: True=@font-face でフォントを SVG 内に埋め込む（ダウンロード用）
                     False=埋め込みなし（システムフォントに頼る・cairosvg 用）
    """
    _ensure_svg_fonts()
    fc = SVG_FONT_PRESETS.get(font_key, SVG_FONT_PRESETS[SVG_FONT_DEFAULT])
    theme = get_theme(data.theme_key, data.custom_accent_color, data.custom_accent_light)

    def pw(n: float) -> float:
        return n * W

    def ph(n: float) -> float:
        return n * H

    # embed_fonts=False のときは @font-face 埋め込みを無効化し、システムフォント名を使用
    if not embed_fonts:
        from dataclasses import replace as _dc_replace
        fc = _dc_replace(
            fc,
            gothic_family=fc.system_gothic_family or fc.gothic_family,
            mincho_family=fc.system_mincho_family or fc.mincho_family,
            gothic_regular_path=None,
            gothic_bold_path=None,
            mincho_regular_path=None,
        )
    c = SVGCanvas(W, H, font_config=fc)
    # モジュールレベルの _SVG_GOTHIC/_SVG_MINCHO をローカル変数でシャドウ
    # → 以降の描画コードはすべてこのフォント名を使用する
    _SVG_GOTHIC = c.gothic  # noqa: F841
    _SVG_MINCHO = c.mincho  # noqa: F841

    # 白背景
    c.rect(0, 0, W, H, fill=(255, 255, 255))

    # 背景画像
    bg_path = getattr(data, "background_image_path", None)
    if bg_path and Path(bg_path).exists():
        try:
            layer = make_background_layer(str(bg_path), PREVIEW_W, PREVIEW_H, opacity=data.bg_opacity)
            c.image(_embed_image_opaque(layer), 0, 0, W, H)
        except Exception as e:
            print(f"背景画像SVG埋め込みエラー: {e}")

    # ヘッダー・フッター
    header_top = ph(HEADER_TOP)
    header_h = ph(HEADER_H)
    header_bottom = header_top + header_h
    footer_h = ph(FOOTER_H)
    footer_top = H - footer_h

    title_bar_color = theme.get("title_bar", DARK_BROWN)
    c.rect(0, header_top, W, header_h, fill=title_bar_color)
    c.rect(0, footer_top, W, footer_h, fill=title_bar_color)

    # ヘッダーテキスト（均等割り付け）
    header_font_size = max(8.0, header_h * 0.52)
    header_pad = max(8.0, W * 0.03)
    _draw_spaced_text(
        c,
        "Gifu Pediatric-residency Intensives",
        header_pad, header_top, header_h,
        W - header_pad * 2,
        _RL_GOTHIC, _SVG_GOTHIC,
        header_font_size, WHITE,
    )

    # フッターテキスト（「岐阜県小児科研修支援グループ」のみ少し大きく）
    footer_font_size = max(6.0, footer_h * 0.40)
    footer_fs_large = footer_font_size * FOOTER_GROUP_SCALE
    before = "お問い合わせ先  "
    group = "岐阜県小児科研修支援グループ"
    after = f"  Mail ▶  {data.contact_email}"
    w1 = _tw(before, _RL_GOTHIC, footer_font_size)
    w2 = _tw(group, _RL_GOTHIC, footer_fs_large)
    w3 = _tw(after, _RL_GOTHIC, footer_font_size)
    footer_w = w1 + w2 + w3
    footer_asc, _, footer_ch = _fm(_RL_GOTHIC, footer_font_size)
    footer_baseline = footer_top + (footer_h - footer_ch) / 2 + footer_asc
    footer_x = (W - footer_w) / 2
    _draw_text_at_baseline(c, before, footer_x, footer_baseline, _SVG_GOTHIC, footer_font_size, WHITE)
    _draw_text_at_baseline(c, group, footer_x + w1, footer_baseline, _SVG_GOTHIC, footer_fs_large, WHITE)
    _draw_text_at_baseline(c, after, footer_x + w1 + w2, footer_baseline, _SVG_GOTHIC, footer_font_size, WHITE)

    # 各カラム基本位置
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
        title_x, header_bottom, footer_top, title_w,
        _RL_MINCHO, _SVG_MINCHO,
        ph(FS_V_TITLE), DARK_BROWN,
        top_pad=max(10.0, (footer_top - header_bottom) / 80.0),
        bot_pad=max(12.0, (footer_top - header_bottom) / 65.0),
        gap_ratio=0.08,
    )

    # 右ストリップ上部: 年度（縦書き）
    prog_top_y = ph(PROG_TOP)
    v_pad = max(12.0, (footer_top - header_bottom) / 65.0)
    year_text = f"{data.year}年度"
    if year_text:
        step = max(1.0, (prog_top_y - ph(0.005) - (header_bottom + v_pad)) / len(year_text))
        fs_year = max(8.0, min(sect_w, step * 1.10))
        cur_top = header_bottom + v_pad
        for chv in year_text:
            asc, _, ch_h = _fm(_RL_MINCHO, fs_year)
            lw = _tw(chv, _RL_MINCHO, fs_year)
            cx = sect_x + (sect_w - lw) / 2
            char_top = cur_top + max(0.0, (step - ch_h) / 2)
            baseline = char_top + asc
            _draw_text_at_baseline(c, chv, cx, baseline, _SVG_MINCHO, fs_year, DARK_BROWN)
            cur_top += step

    # 左カラム
    cur_y = header_bottom + ph(0.026)

    # 場所バッジ + 会場
    badge_w = pw(BASHO_BW)
    badge_h = ph(BASHO_BH)
    _draw_pill(c, lc_x, cur_y, badge_w, badge_h, (90, 60, 35))
    basho_fs = _fit_font_size("場所", _RL_GOTHIC, badge_w * 0.78, badge_h * 0.75, 8.0)
    _draw_centered_in_box(
        c, "場所", lc_x, cur_y, badge_w, badge_h,
        _RL_GOTHIC, _SVG_GOTHIC, basho_fs, WHITE, y_offset=basho_fs * 0.08
    )

    venue_x = lc_x + badge_w + pw(0.009)
    venue_w = pw(LEFT_W) - venue_x - pw(LC_PAD_R)
    venue_fs_big = ph(FS_VENUE_BIG)
    venue_fs_sm = ph(FS_VENUE_SM)

    if "\n" in data.venue_building:
        b_lines = data.venue_building.split("\n")
        venue_h = _draw_multiline(
            c, b_lines, venue_x, cur_y, _RL_GOTHIC, _SVG_GOTHIC, venue_fs_big, DARK_BROWN, 1.25
        )
    else:
        b_size = _fit_font_size(data.venue_building, _RL_GOTHIC, venue_w, venue_fs_big, 8.0)
        asc, _, ch_h = _fm(_RL_GOTHIC, b_size)
        baseline = cur_y + asc
        _draw_text_at_baseline(c, data.venue_building, venue_x, baseline, _SVG_GOTHIC, b_size, DARK_BROWN)
        venue_h = ch_h * 1.25

    if data.venue_room:
        room_fs = max(8.0, venue_fs_sm * 1.4)
        r_lines = _wrap_jp(data.venue_room, _RL_GOTHIC, room_fs, venue_w)
        venue_h += _draw_multiline(
            c, r_lines, venue_x, cur_y + venue_h, _RL_GOTHIC, _SVG_GOTHIC,
            room_fs, DARK_BROWN, 1.2, align="right", max_w=venue_w
        )
    cur_y += max(badge_h, venue_h) + ph(0.005)

    # 住所
    addr_fs = ph(FS_VENUE_SM)
    addr_lines = _wrap_jp(data.venue_address, _RL_GOTHIC, addr_fs, venue_w + max(2.0, addr_fs / 3))
    addr_h = _draw_multiline(c, addr_lines, venue_x, cur_y, _RL_GOTHIC, _SVG_GOTHIC, addr_fs, DARK_BROWN, 1.2)
    line_y = cur_y + addr_h + max(3.0, addr_fs * 0.4)
    c.line(venue_x, line_y, venue_x + venue_w, line_y, DARK_BROWN, 1.0)
    cur_y += (line_y + 2.0 - cur_y) + ph(0.018)

    # ハイブリッド開催（左寄せ気味） + テーマ連動 Zoom アイコン
    zoom_fs = max(10.0, ph(FS_VENUE_SM) * 1.8)
    zoom_text = "ハイブリッド開催"
    zoom_asc, _, zoom_ch = _fm(_RL_GOTHIC, zoom_fs)
    zoom_tw = _tw(zoom_text, _RL_GOTHIC, zoom_fs)

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
    zoom_baseline = text_top + zoom_asc
    c.text(zoom_text, text_x, zoom_baseline, _SVG_GOTHIC, zoom_fs, DARK_BROWN)

    zoom_line_y = text_top + zoom_ch + 2.0
    c.line(text_x, zoom_line_y, text_x + zoom_tw, zoom_line_y, DARK_BROWN, 2.0)
    try:
        icon_color = theme.get("accent_light", theme["accent"])
        icon_img = build_zoom_icon(
            max(32, int(icon_size * 3)),
            icon_color,
            logo_scale=ZOOM_ICON_LOGO_SCALE,
        )
        cx = icon_x + icon_size / 2
        cy = icon_y + icon_size / 2
        rot = f"rotate({-ZOOM_ICON_ROTATE_DEG:.3f}, {cx:.3f}, {cy:.3f})"
        c.image(_embed_image_alpha(icon_img), icon_x, icon_y, icon_size, icon_size, transform=rot)
    except Exception as e:
        print(f"ZoomアイコンSVG描画エラー: {e}")
    cur_y += (zoom_line_y + 2.0 - cur_y) + ph(0.022)

    # 日付・時刻
    event_date = data.event_date or ""
    if "年 " in event_date:
        p0, p1 = event_date.split("年 ", 1)
        year_label, date_main = p0 + "年", p1
    elif "年" in event_date:
        idx = event_date.index("年")
        year_label, date_main = event_date[: idx + 1], event_date[idx + 1:].strip()
    else:
        year_label, date_main = "", event_date

    yr_indent = max(3.0, ph(FS_DATE_LBL) * 0.3)
    if year_label:
        yr_fs = ph(FS_DATE_LBL)
        yr_asc, _, yr_h = _fm(_RL_GOTHIC, yr_fs)
        yr_baseline = cur_y + yr_asc
        _draw_text_at_baseline(c, year_label, lc_x + yr_indent, yr_baseline, _SVG_GOTHIC, yr_fs, DARK_BROWN)
        cur_y += yr_h + yr_fs * 0.2

    segs: list[tuple[str, bool]] = []
    if date_main:
        cur_s, cur_is_num = "", None
        for chv in date_main:
            is_num = chv.isdigit()
            if cur_is_num is None:
                cur_is_num = is_num
            if is_num != cur_is_num:
                segs.append((cur_s, bool(cur_is_num)))
                cur_s, cur_is_num = chv, is_num
            else:
                cur_s += chv
        if cur_s:
            segs.append((cur_s, bool(cur_is_num)))

    fs_num = max(10.0, ph(FS_DATE_BIG) * 0.75)
    fs_kana = max(8.0, ph(FS_DATE_BIG) * 0.50)
    # セグメント間（数字↔漢字）に挿入するスペース
    seg_gap = max(2.0, ph(FS_DATE_BIG) * 0.22)
    n_gaps = max(0, len(segs) - 1)
    seg_info = []
    total_sw = 0.0
    max_h = 0.0
    for txt, is_num in segs:
        size = fs_num if is_num else fs_kana
        asc, _, h = _fm(_RL_GOTHIC, size)
        w_seg = _tw(txt, _RL_GOTHIC, size)
        seg_info.append((txt, is_num, size, asc, h, w_seg))
        total_sw += w_seg
        max_h = max(max_h, h)
    total_sw += seg_gap * n_gaps
    if total_sw > lc_w and total_sw > 0:
        ratio = lc_w / total_sw
        fs_num = max(8.0, fs_num * ratio)
        fs_kana = max(6.0, fs_kana * ratio)
        seg_gap = max(1.0, seg_gap * ratio)
        seg_info = []
        total_sw = 0.0
        max_h = 0.0
        for txt, is_num in segs:
            size = fs_num if is_num else fs_kana
            asc, _, h = _fm(_RL_GOTHIC, size)
            w_seg = _tw(txt, _RL_GOTHIC, size)
            seg_info.append((txt, is_num, size, asc, h, w_seg))
            total_sw += w_seg
            max_h = max(max_h, h)

    cur_x = lc_x
    for i, (txt, _is_num, size, asc, h, w_seg) in enumerate(seg_info):
        top = cur_y + (max_h - h)
        baseline = top + asc
        _draw_text_at_baseline(c, txt, cur_x, baseline, _SVG_GOTHIC, size, DARK_BROWN)
        cur_x += w_seg + (seg_gap if i < len(seg_info) - 1 else 0.0)
    cur_y += max_h + ph(FS_DATE_BIG) * 0.18

    time_fs = ph(FS_TIME_LC)
    time_lines = _wrap_jp(data.time_range, _RL_GOTHIC, time_fs, lc_w - yr_indent)
    time_h = _draw_multiline(
        c, time_lines, lc_x + yr_indent, cur_y, _RL_GOTHIC, _SVG_GOTHIC, time_fs, DARK_BROWN, 1.2
    )
    cur_y += time_h + ph(0.018)

    # 司会/座長
    mc_cs = SECTION_CONTENT_SCALES[0]
    fs_mc_aff = ph(FS_PRESENTER * mc_cs)
    fs_mc_name = ph(FS_PRES_NAME * mc_cs)

    def draw_person_row(label: str, person):
        nonlocal cur_y
        badge_h2 = ph(FS_MC_BADGE) * 2.0
        badge_font = _fit_font_size(label, _RL_GOTHIC, lc_w * 0.75, ph(FS_MC_BADGE) + 2, 8.0)
        badge_w2 = min(_tw(label, _RL_GOTHIC, badge_font) + ph(FS_MC_BADGE) * 2.0, lc_w)
        _draw_pill(c, lc_x, cur_y, badge_w2, badge_h2, theme["accent"])
        _draw_centered_in_box(
            c, label, lc_x, cur_y, badge_w2, badge_h2,
            _RL_GOTHIC, _SVG_GOTHIC, badge_font, WHITE, y_offset=badge_font * 0.08
        )
        cur_y += badge_h2 + ph(FS_MC_BADGE) * 0.7

        aff_lines = _wrap_jp(person.affiliation, _RL_GOTHIC, fs_mc_aff, lc_w)
        aff_h = _draw_multiline(
            c, aff_lines, lc_x, cur_y, _RL_GOTHIC, _SVG_GOTHIC, fs_mc_aff, DARK_BROWN, 1.2
        )
        cur_y += aff_h + fs_mc_aff * 0.5

        fs_sensei = max(8.0, fs_mc_name * 0.85)
        nm_w = _tw(person.name, _RL_GOTHIC, fs_mc_name)
        ss_w = _tw(" 先生", _RL_GOTHIC, fs_sensei)
        nm_asc, _, nm_h = _fm(_RL_GOTHIC, fs_mc_name)
        ss_asc, _, ss_h = _fm(_RL_GOTHIC, fs_sensei)
        line_h = max(nm_h, ss_h)
        right_margin = fs_mc_name * 1.0
        right_edge = lc_x + lc_w - right_margin
        name_top = cur_y + (line_h - nm_h)
        ss_top = cur_y + (line_h - ss_h)
        _draw_text_at_baseline(c, person.name, right_edge - nm_w - ss_w, name_top + nm_asc, _SVG_GOTHIC, fs_mc_name, DARK_BROWN)
        _draw_text_at_baseline(c, " 先生", right_edge - ss_w, ss_top + ss_asc, _SVG_GOTHIC, fs_sensei, DARK_BROWN)
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
    aud_label_fs = _fit_font_size("対象", _RL_GOTHIC, lc_w * 0.45, aud_fs + 2, 8.0)
    aud_badge_w = min(_tw("対象", _RL_GOTHIC, aud_label_fs) + aud_fs * 2.0, lc_w)
    _draw_pill(c, lc_x, cur_y, aud_badge_w, aud_badge_h, theme["accent"])
    _draw_centered_in_box(
        c, "対象", lc_x, cur_y, aud_badge_w, aud_badge_h,
        _RL_GOTHIC, _SVG_GOTHIC, aud_label_fs, WHITE, y_offset=aud_label_fs * 0.08
    )
    cur_y += aud_badge_h + aud_fs * 0.7

    col_w = lc_w / 2.0 - 4.0
    col_items = [data.audience[i: i + 2] for i in range(0, len(data.audience), 2)]
    for pair in col_items:
        row_h = 0.0
        for ci, item in enumerate(pair):
            txt = "・" + item
            lines = _wrap_jp(txt, _RL_GOTHIC, aud_fs, col_w)
            h = _draw_multiline(
                c, lines, lc_x + ci * (col_w + 8.0), cur_y,
                _RL_GOTHIC, _SVG_GOTHIC, aud_fs, DARK_BROWN, 1.2
            )
            row_h = max(row_h, h)
        cur_y += row_h + aud_fs * 0.1
    cur_y += ph(0.010)

    # QR コード
    cap_fs = ph(FS_QR_CAP)
    cap2_fs = max(cap_fs + 1.0, cap_fs * 1.25)
    _, _, cap_h = _fm(_RL_GOTHIC, cap_fs)
    _, _, cap2_h = _fm(_RL_GOTHIC, cap2_fs)
    cap_gap = cap_h * 0.3
    total_cap_h = cap_h + cap2_h + cap_gap
    qr_bottom = footer_top - ph(0.020) - total_cap_h - ph(0.006)
    max_qr = qr_bottom - cur_y - ph(0.005)
    qr_size = max(ph(0.08), min(lc_w, max_qr))
    if qr_size > ph(0.06):
        qr_img = generate_qr(data.registration_url or "", size_px=max(100, int(qr_size)))
        qr_x = lc_x + (lc_w - qr_size) / 2
        c.image(_embed_image_opaque(qr_img), qr_x, qr_bottom - qr_size, qr_size, qr_size)

        cap1 = "事前登録はこちらから"
        cap2 = "※現地参加の方も登録してください"
        cap_y = qr_bottom + ph(0.003)
        cap1_w = _tw(cap1, _RL_GOTHIC, cap_fs)
        cap1_asc, _, _ = _fm(_RL_GOTHIC, cap_fs)
        _draw_text_at_baseline(
            c, cap1, lc_x + (lc_w - cap1_w) / 2, cap_y + cap1_asc, _SVG_GOTHIC, cap_fs, DARK_BROWN
        )
        cap2_w = _tw(cap2, _RL_GOTHIC, cap2_fs)
        cap2_asc, _, _ = _fm(_RL_GOTHIC, cap2_fs)
        _draw_text_at_baseline(
            c, cap2, lc_x + (lc_w - cap2_w) / 2,
            cap_y + cap_h + cap_gap + cap2_asc, _SVG_GOTHIC, cap2_fs, DARK_BROWN
        )

    # 参加費無料（sect ストリップの右横・年度テキスト中央の高さ）
    free_fs = ph(FS_SANSHUUHI)
    free_text = "参加費無料"
    free_asc, _, free_ch = _fm(_RL_GOTHIC, free_fs)
    year_mid_y = header_bottom + v_pad + (prog_top_y - header_bottom - v_pad) / 2
    free_baseline = year_mid_y - free_ch / 2 + free_asc
    free_x = sect_x + sect_w + pw(0.012)
    _draw_text_at_baseline(c, free_text, free_x, free_baseline, _SVG_GOTHIC, free_fs, (220, 30, 30))

    # プログラムレイアウト
    layout = LayoutEngine(data, use_reportlab=True).compute()
    section_positions: list[dict] = []

    for block in layout:
        by = ph(block.y)
        sc = block.data.get("scale", 1.0)
        cs = block.data.get("content_scale", 1.0)

        if block.kind == "section_time":
            fs = ph(FS_PROG_TIME) * sc
            asc, _, _ = _fm(_RL_GOTHIC, fs)
            _draw_text_at_baseline(
                c, block.data.get("text", ""), prog_x, by + asc, _SVG_GOTHIC, fs, DARK_BROWN
            )
            section_positions.append({"label": block.data.get("part_label", ""), "y_start": by})

        elif block.kind == "sub_badge":
            bh = ph(BADGE_SM_H) * sc
            max_bw = prog_w * 0.75
            fs = max(7.0, bh * 0.78)
            label = block.data.get("label", "")
            while fs > 7.0 and _tw(label, _RL_GOTHIC, fs) > max_bw * 0.92:
                fs -= 0.5
            badge_w = min(_tw(label, _RL_GOTHIC, fs) + bh * 1.8, max_bw)
            _draw_pill(c, prog_x, by, badge_w, bh, theme["accent"])
            _draw_centered_in_box(
                c, label, prog_x, by, badge_w, bh,
                _RL_GOTHIC, _SVG_GOTHIC, fs, WHITE, y_offset=fs * 0.08
            )

        elif block.kind == "title":
            fs = ph(FS_PROG_TITLE) * sc * cs
            lines = block.data.get("lines") or _wrap_jp(block.data.get("text", ""), _RL_GOTHIC, fs, prog_w)
            _draw_multiline(c, lines, prog_x, by, _RL_GOTHIC, _SVG_GOTHIC, fs, DARK_BROWN, 1.35)

        elif block.kind == "affiliation":
            fs = ph(FS_PRESENTER) * sc * cs
            lines = block.data.get("lines") or _wrap_jp(block.data.get("text", ""), _RL_GOTHIC, fs, prog_w)
            _draw_multiline(c, lines, prog_x, by, _RL_GOTHIC, _SVG_GOTHIC, fs, DARK_BROWN, 1.25)

        elif block.kind == "name":
            name = block.data.get("text", "")
            fs_name = ph(FS_PRES_NAME) * sc * cs
            fs_sensei = max(8.0, fs_name * 0.85)
            nm_w = _tw(name, _RL_GOTHIC, fs_name)
            ss_w = _tw(" 先生", _RL_GOTHIC, fs_sensei)
            nm_asc, _, nm_h = _fm(_RL_GOTHIC, fs_name)
            ss_asc, _, ss_h = _fm(_RL_GOTHIC, fs_sensei)
            line_h = max(nm_h, ss_h)
            right_edge = prog_x + prog_w
            name_top = by + (line_h - nm_h)
            ss_top = by + (line_h - ss_h)
            _draw_text_at_baseline(
                c, name, right_edge - nm_w - ss_w, name_top + nm_asc, _SVG_GOTHIC, fs_name, DARK_BROWN
            )
            _draw_text_at_baseline(
                c, " 先生", right_edge - ss_w, ss_top + ss_asc, _SVG_GOTHIC, fs_sensei, DARK_BROWN
            )

    # 右ストリップ: 第N部ラベルボックス
    for i, pos in enumerate(section_positions):
        y_start = pos["y_start"]
        y_end = section_positions[i + 1]["y_start"] if i + 1 < len(section_positions) else footer_top - ph(0.008)
        pad = max(2.0, sect_w * 0.23)
        box_h = y_end - y_start - pad * 2
        if box_h < 20:
            continue
        bx = sect_x + pad
        by2 = y_start + pad
        bw = sect_w - pad * 2
        color = theme.get("accent_light", theme["accent"])
        c.rect(bx, by2, bw, box_h, rx=max(4.0, bw / 4), fill=color)

        label = pos.get("label", "")
        display = label[: label.index("部") + 1] if "部" in label else label
        fs = max(11.0, bw * 0.62)
        asc, _, ch = _fm(_RL_GOTHIC, fs)
        step = ch + 2.0
        start_top = by2 + max(4.0, (box_h - step * len(display)) / 2)
        cur_top = start_top
        cx = bx + bw / 2  # ボックス中央（text-anchor="middle" で正確に中央揃え）
        for chv in display:
            if cur_top + ch <= by2 + box_h:
                c.text(chv, cx, cur_top + asc, _SVG_GOTHIC, fs, DARK_BROWN, text_anchor="middle")
            cur_top += step

    # 装飾イラスト（参加費無料の右側〜ページ右端まで右寄せ配置）
    deco_imgs = getattr(data, "decorative_images", [])
    if deco_imgs:
        deco_area_h = prog_top_y - header_bottom - ph(0.015)
        deco_margin = pw(0.010)
        # 参加費無料テキスト右端を起点に、ページ右端まで使って右寄せ
        free_right = free_x + _tw(free_text, _RL_GOTHIC, free_fs)
        avail_w = W - free_right - deco_margin * 2
        illust_size = min(deco_area_h * 0.88, max(0.0, avail_w))
        total_deco_w = illust_size
        deco_start_x = W - illust_size - deco_margin
        deco_y = header_bottom + (deco_area_h - illust_size) / 2 + ph(0.008)
        for i, img_path in enumerate(deco_imgs[:1]):
            try:
                p = Path(img_path)
                if not p.exists():
                    continue
                img = Image.open(p).convert("RGBA")
                iw, ih = img.size
                aspect = iw / ih
                dw = illust_size if aspect >= 1 else illust_size * aspect
                dh = illust_size / aspect if aspect >= 1 else illust_size
                img.thumbnail((int(dw * 5), int(dh * 5)), Image.LANCZOS)
                dx = deco_start_x
                dy = deco_y + (illust_size - dh) / 2
                c.image(_embed_image_alpha(img), dx, dy, dw, dh)
            except Exception as e:
                print(f"装飾画像SVG埋め込みエラー: {e}")

    return c.to_svg()
