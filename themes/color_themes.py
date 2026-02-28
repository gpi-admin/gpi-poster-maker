"""
季節・テーマ別カラーパレット定義
"""

# 固定色（テーマに依らず不変）
DARK_BROWN = (80, 50, 30)          # メインテキスト・場所バッジ
DARK_BROWN_CIRCLE = (100, 65, 40)  # 場所バッジ円
WHITE = (255, 255, 255)
LIGHT_CREAM_BG = (245, 241, 234)   # ポスター地色

THEMES = {
    "spring_pink": {
        "name": "春 (ピンク・桜)",
        "month_hint": "3〜5月",
        "accent": (210, 110, 150),       # メインアクセント（大バッジ）
        "accent_light": (235, 170, 195), # サブバッジ
        "title_bar": (220, 130, 165),    # 中央縦バー
        "zoom_color": (210, 110, 150),   # Zoomアイコン配色
        "bg_image": "spring_sakura.png",
        "suggested_decoratives": [],
    },
    "early_summer_green": {
        "name": "初夏 (緑・山)",
        "month_hint": "5〜6月",
        "accent": (75, 155, 75),
        "accent_light": (130, 195, 130),
        "title_bar": (90, 170, 90),
        "zoom_color": (75, 155, 75),
        "bg_image": "mountain_green.png",
        "suggested_decoratives": ["beer_mugs.png"],
    },
    "summer_blue": {
        "name": "夏 (青・銀河)",
        "month_hint": "7〜8月",
        "accent": (80, 165, 210),
        "accent_light": (140, 205, 235),
        "title_bar": (90, 180, 220),
        "zoom_color": (80, 165, 210),
        "bg_image": "summer_galaxy.png",
        "suggested_decoratives": ["beer_mugs.png"],
    },
    "autumn_orange": {
        "name": "秋 (橙・紅葉)",
        "month_hint": "9〜11月",
        "accent": (210, 110, 50),
        "accent_light": (235, 170, 120),
        "title_bar": (220, 125, 65),
        "zoom_color": (210, 110, 50),
        "bg_image": "autumn_leaves.png",
        "suggested_decoratives": [],
    },
    "winter_christmas": {
        "name": "冬 (緑・クリスマス)",
        "month_hint": "12〜2月",
        "accent": (75, 155, 75),
        "accent_light": (130, 195, 130),
        "title_bar": (90, 170, 90),
        "zoom_color": (75, 155, 75),
        "bg_image": "winter_snow.png",
        "suggested_decoratives": [],
    },
    "custom": {
        "name": "カスタム",
        "month_hint": "任意",
        "accent": (100, 150, 200),       # アプリ側で上書き
        "accent_light": (160, 200, 230),
        "title_bar": (110, 160, 210),
        "zoom_color": (100, 150, 200),
        "bg_image": None,
        "suggested_decoratives": [],
    },
}


def get_theme(key: str, custom_accent=None, custom_accent_light=None) -> dict:
    """テーマ辞書を取得。カスタムカラーがあれば上書きして返す"""
    theme = dict(THEMES.get(key, THEMES["custom"]))
    if key == "custom" and custom_accent:
        theme["accent"] = custom_accent
        r, g, b = custom_accent
        light = (min(255, r + 60), min(255, g + 60), min(255, b + 60))
        theme["accent_light"] = custom_accent_light or light
        theme["title_bar"] = custom_accent
        theme["zoom_color"] = custom_accent
    return theme


def rgb_to_hex(rgb: tuple) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def hex_to_rgb(hex_str: str) -> tuple:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
