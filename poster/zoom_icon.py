from pathlib import Path

from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).parent.parent / "assets"
_LOGO_CANDIDATES = [
    ASSETS_DIR / "illustrations" / "fixed" / "zoom_mark_white.png",
    Path(__file__).parent.parent / "zoomアイコン白のみ.png",
]


def _load_logo() -> Image.Image | None:
    for p in _LOGO_CANDIDATES:
        if p.exists():
            try:
                return Image.open(p).convert("RGBA")
            except Exception:
                continue
    return None


def build_zoom_icon(
    size_px: int,
    bg_color: tuple[int, int, int],
    logo_scale: float = 0.58,
) -> Image.Image:
    """
    テーマ色の角丸正方形 + 白ロゴで Zoom アイコン画像を生成する。
    """
    side = max(8, int(size_px))
    icon = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon, "RGBA")

    radius = max(2, int(side * 0.22))
    d.rounded_rectangle((0, 0, side, side), radius=radius, fill=(*bg_color, 255))

    logo = _load_logo()
    if logo is None:
        return icon

    mark = logo.copy()
    target = max(1, int(side * logo_scale))
    mark.thumbnail((target, target), Image.LANCZOS)
    x = (side - mark.width) // 2
    y = (side - mark.height) // 2
    icon.alpha_composite(mark, (x, y))
    return icon
