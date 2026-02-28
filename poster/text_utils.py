"""
日本語テキスト処理ユーティリティ
- 楕円バッジ内のフォントサイズ自動フィッティング
- 日本語テキストの文字単位折り返し
- テキスト寸法の計算
"""

from PIL import Image, ImageDraw, ImageFont
from utils.font_manager import get_pillow_font


def get_text_size(draw: ImageDraw.ImageDraw, text: str,
                  font: ImageFont.FreeTypeFont) -> tuple:
    """テキストの (幅, 高さ) をピクセル単位で返す"""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def fit_font_in_box(draw: ImageDraw.ImageDraw, text: str,
                    weight: str, max_w: int, max_h: int,
                    max_size: int = 80, min_size: int = 10) -> ImageFont.FreeTypeFont:
    """
    テキストが (max_w, max_h) に収まる最大フォントサイズを二分探索で求める。
    """
    lo, hi = min_size, max_size
    best = get_pillow_font(weight, min_size)
    while lo <= hi:
        mid = (lo + hi) // 2
        font = get_pillow_font(weight, mid)
        tw, th = get_text_size(draw, text, font)
        if tw <= max_w and th <= max_h:
            best = font
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def fit_font_in_ellipse(draw: ImageDraw.ImageDraw, text: str,
                         weight: str, ellipse_w: int, ellipse_h: int,
                         max_size: int = 80, min_size: int = 10) -> ImageFont.FreeTypeFont:
    """
    楕円の内接矩形（幅×0.80, 高さ×0.80）に収まる最大フォントサイズを求める。
    """
    return fit_font_in_box(
        draw, text, weight,
        int(ellipse_w * 0.80), int(ellipse_h * 0.80),
        max_size=max_size, min_size=min_size
    )


def wrap_text_jp(draw: ImageDraw.ImageDraw, text: str,
                  font: ImageFont.FreeTypeFont, max_w: int) -> list:
    """
    日本語テキストを max_w 以内に収まるよう文字単位で折り返す。
    改行コード (\n) も考慮する。
    戻り値: 行のリスト
    """
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            test = current + char
            tw, _ = get_text_size(draw, test, font)
            if tw > max_w and current:
                lines.append(current)
                current = char
            else:
                current = test
        if current:
            lines.append(current)
    return lines


def draw_text_multiline(draw: ImageDraw.ImageDraw, lines: list,
                         font: ImageFont.FreeTypeFont,
                         x: int, y: int, fill: tuple,
                         line_spacing: float = 1.3,
                         align: str = "left",
                         max_w: int = None) -> int:
    """
    複数行テキストを描画し、合計高さ（px）を返す。
    align: "left" | "center" | "right"
    max_w: center/right揃えのとき使用
    """
    _, ch = get_text_size(draw, "あ", font)
    line_h = int(ch * line_spacing)
    cur_y = y
    for line in lines:
        lw, _ = get_text_size(draw, line, font)
        if align == "center" and max_w:
            lx = x + (max_w - lw) // 2
        elif align == "right" and max_w:
            lx = x + max_w - lw
        else:
            lx = x
        draw.text((lx, cur_y), line, fill=fill, font=font)
        cur_y += line_h
    return cur_y - y  # 合計高さ


def draw_centered_text(draw: ImageDraw.ImageDraw, text: str,
                        font: ImageFont.FreeTypeFont,
                        cx: int, cy: int, fill: tuple):
    """中心座標を指定してテキストを描画"""
    draw.text((cx, cy), text, fill=fill, font=font, anchor="mm")


def measure_multiline_height(draw: ImageDraw.ImageDraw, lines: list,
                              font: ImageFont.FreeTypeFont,
                              line_spacing: float = 1.3) -> int:
    """複数行テキストの合計高さを推定する"""
    if not lines:
        return 0
    _, ch = get_text_size(draw, "あ", font)
    line_h = int(ch * line_spacing)
    return line_h * len(lines)
