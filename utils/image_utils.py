"""
画像ユーティリティ (リサイズ・透過合成など)
"""

from PIL import Image
import numpy as np


def composite_alpha(base: Image.Image, overlay: Image.Image,
                    position: tuple = (0, 0), opacity: float = 1.0) -> Image.Image:
    """
    base に overlay を opacity で合成する（RGBA対応）。
    position: (x, y) 左上座標
    """
    base = base.convert("RGBA")
    overlay = overlay.convert("RGBA")

    if opacity < 1.0:
        r, g, b, a = overlay.split()
        a = a.point(lambda x: int(x * opacity))
        overlay = Image.merge("RGBA", (r, g, b, a))

    tmp = Image.new("RGBA", base.size, (0, 0, 0, 0))
    tmp.paste(overlay, position)
    return Image.alpha_composite(base, tmp)


def resize_contain(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """アスペクト比を保ちつつ max_w x max_h 内に収まるようリサイズ"""
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def resize_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """アスペクト比を保ちつつ target_w x target_h をカバーするようリサイズしてクロップ"""
    iw, ih = img.size
    scale = max(target_w / iw, target_h / ih)
    new_w = int(iw * scale)
    new_h = int(ih * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def make_background_layer(img_path: str, canvas_w: int, canvas_h: int,
                           opacity: float = 0.35) -> Image.Image:
    """
    背景イラストを読み込み、キャンバスサイズにフィットさせ、
    指定の透明度（opacity）で白と合成した RGBA 画像を返す。
    """
    bg = Image.open(img_path).convert("RGBA")
    bg = resize_cover(bg, canvas_w, canvas_h)

    # 白ベースに alpha blend
    white = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
    r, g, b, a = bg.split()
    a = a.point(lambda x: int(x * opacity))
    bg = Image.merge("RGBA", (r, g, b, a))
    result = Image.alpha_composite(white, bg)
    return result.convert("RGB")


def add_rounded_rect(draw, x0, y0, x1, y1, radius: int, fill, outline=None):
    """
    PIL Draw に角丸矩形を描画する（Pillow 9.2+ の rounded_rectangle を使用）
    """
    try:
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius,
                                fill=fill, outline=outline)
    except AttributeError:
        # 古い Pillow へのフォールバック
        draw.rectangle([x0, y0, x1, y1], fill=fill, outline=outline)
