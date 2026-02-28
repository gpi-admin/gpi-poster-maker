"""
季節・テーマ別カラーパレット定義（12テーマ）
"""

# 固定色（テーマに依らず不変）
DARK_BROWN = (80, 50, 30)          # メインテキスト・場所バッジ
DARK_BROWN_CIRCLE = (100, 65, 40)  # 場所バッジ円
WHITE = (255, 255, 255)
LIGHT_CREAM_BG = (245, 241, 234)   # ポスター地色

THEMES = {
    # ─── 春 ────────────────────────────────────────────────────────────────
    "spring_sakura": {
        "name": "春・桜 (3〜4月)",
        "month_hint": "3〜4月",
        "accent": (210, 110, 150),       # 濃いピンク（バッジ背景）
        "accent_light": (235, 170, 195), # 薄いピンク（第N部背景）
        "title_bar": (220, 130, 165),    # ヘッダー・フッター帯
        "zoom_color": (210, 110, 150),
        "bg_image": "spring_sakura.png",
        "suggested_decoratives": [],
    },
    "spring_fresh": {
        "name": "春・新緑 (4〜5月)",
        "month_hint": "4〜5月",
        "accent": (90, 165, 90),
        "accent_light": (150, 205, 150),
        "title_bar": (100, 175, 100),
        "zoom_color": (90, 165, 90),
        "bg_image": "spring_fresh.png",
        "suggested_decoratives": [],
    },

    # ─── 初夏〜梅雨 ─────────────────────────────────────────────────────────
    "early_summer_wisteria": {
        "name": "初夏・藤 (5月)",
        "month_hint": "5月",
        "accent": (140, 90, 185),
        "accent_light": (190, 155, 220),
        "title_bar": (150, 100, 195),
        "zoom_color": (140, 90, 185),
        "bg_image": "early_summer_wisteria.png",
        "suggested_decoratives": [],
    },
    "summer_hydrangea": {
        "name": "梅雨・紫陽花 (6月)",
        "month_hint": "6月",
        "accent": (75, 130, 200),
        "accent_light": (140, 180, 225),
        "title_bar": (85, 140, 210),
        "zoom_color": (75, 130, 200),
        "bg_image": "summer_hydrangea.png",
        "suggested_decoratives": [],
    },

    # ─── 夏 ────────────────────────────────────────────────────────────────
    "summer_ocean": {
        "name": "夏・海 (7〜8月)",
        "month_hint": "7〜8月",
        "accent": (30, 155, 180),
        "accent_light": (105, 200, 220),
        "title_bar": (40, 165, 190),
        "zoom_color": (30, 155, 180),
        "bg_image": "summer_ocean.png",
        "suggested_decoratives": [],
    },
    "summer_night": {
        "name": "夏夜・銀河 (8月)",
        "month_hint": "8月",
        "accent": (80, 165, 210),        # 現行 summer_blue 互換
        "accent_light": (140, 205, 235),
        "title_bar": (90, 180, 220),
        "zoom_color": (80, 165, 210),
        "bg_image": "summer_night.png",
        "suggested_decoratives": [],
    },

    # ─── 初秋 ───────────────────────────────────────────────────────────────
    "early_autumn_cosmos": {
        "name": "初秋・コスモス (9月)",
        "month_hint": "9月",
        "accent": (200, 110, 155),
        "accent_light": (225, 165, 195),
        "title_bar": (210, 120, 165),
        "zoom_color": (200, 110, 155),
        "bg_image": "early_autumn_cosmos.png",
        "suggested_decoratives": [],
    },

    # ─── 秋 ────────────────────────────────────────────────────────────────
    "autumn_leaves": {
        "name": "秋・紅葉 (10〜11月)",
        "month_hint": "10〜11月",
        "accent": (210, 110, 50),
        "accent_light": (235, 170, 120),
        "title_bar": (220, 125, 65),
        "zoom_color": (210, 110, 50),
        "bg_image": "autumn_leaves.png",
        "suggested_decoratives": [],
    },
    "autumn_ginkgo": {
        "name": "秋・銀杏 (11月)",
        "month_hint": "11月",
        "accent": (195, 165, 30),
        "accent_light": (225, 205, 100),
        "title_bar": (205, 175, 40),
        "zoom_color": (195, 165, 30),
        "bg_image": "autumn_ginkgo.png",
        "suggested_decoratives": [],
    },

    # ─── 冬 ────────────────────────────────────────────────────────────────
    "winter_snow": {
        "name": "冬・雪景色 (12〜1月)",
        "month_hint": "12〜1月",
        "accent": (80, 145, 195),
        "accent_light": (140, 185, 220),
        "title_bar": (90, 155, 205),
        "zoom_color": (80, 145, 195),
        "bg_image": "winter_snow.png",
        "suggested_decoratives": [],
    },
    "winter_christmas": {
        "name": "冬・クリスマス (12月)",
        "month_hint": "12月",
        "accent": (75, 155, 75),
        "accent_light": (130, 195, 130),
        "title_bar": (90, 170, 90),
        "zoom_color": (75, 155, 75),
        "bg_image": "winter_christmas.png",
        "suggested_decoratives": [],
    },

    # ─── 新春 ───────────────────────────────────────────────────────────────
    "new_year_sunrise": {
        "name": "新春・初日の出 (1〜2月)",
        "month_hint": "1〜2月",
        "accent": (210, 145, 50),
        "accent_light": (235, 195, 120),
        "title_bar": (220, 155, 60),
        "zoom_color": (210, 145, 50),
        "bg_image": "new_year_sunrise.png",
        "suggested_decoratives": [],
    },

    # ─── カスタム ────────────────────────────────────────────────────────────
    "custom": {
        "name": "カスタム",
        "month_hint": "任意",
        "accent": (100, 150, 200),
        "accent_light": (160, 200, 230),
        "title_bar": (110, 160, 210),
        "zoom_color": (100, 150, 200),
        "bg_image": None,
        "suggested_decoratives": [],
    },
}

# 旧テーマキーの後方互換エイリアス（PosterDataに保存済みのデータが壊れないように）
_THEME_ALIASES = {
    "spring_pink":          "spring_sakura",
    "early_summer_green":   "early_summer_wisteria",
    "summer_blue":          "summer_night",
    "autumn_orange":        "autumn_leaves",
}


def get_theme(key: str, custom_accent=None, custom_accent_light=None) -> dict:
    """テーマ辞書を取得。カスタムカラーがあれば上書きして返す"""
    # エイリアス解決
    key = _THEME_ALIASES.get(key, key)
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
