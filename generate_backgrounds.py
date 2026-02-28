#!/usr/bin/env python3
"""
季節背景画像生成スクリプト

使い方:
  python generate_backgrounds.py              # グラデーション背景を生成（オフライン）
  python generate_backgrounds.py --unsplash   # Unsplash API で写真を取得
  python generate_backgrounds.py --theme spring_sakura  # 指定テーマのみ再生成

Unsplash API を使う場合は環境変数を設定してください:
  export UNSPLASH_ACCESS_KEY="your_access_key_here"
  # https://unsplash.com/developers でアカウント登録・アプリ作成後に取得
"""

import argparse
import os
import io
import sys
import time
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageDraw

# ─── 出力ディレクトリ ──────────────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).parent / "assets" / "illustrations" / "backgrounds"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── 背景サイズ（ポスタープレビューと同解像度）─────────────────────────────

BG_W, BG_H = 1588, 2246   # 2× プレビューサイズ（794×1123の2倍）

# ─── Unsplash 検索クエリ ───────────────────────────────────────────────────

UNSPLASH_QUERIES = {
    "spring_sakura":         "cherry blossom sakura japan spring pink",
    "spring_fresh":          "spring new green leaves sunlight japan",
    "early_summer_wisteria": "wisteria purple flower japan",
    "summer_hydrangea":      "hydrangea blue purple flower rainy season",
    "summer_ocean":          "summer ocean sea japan turquoise",
    "summer_night":          "milky way galaxy night sky stars japan",
    "early_autumn_cosmos":   "cosmos flower pink autumn japan field",
    "autumn_leaves":         "autumn red orange maple leaves japan momiji",
    "autumn_ginkgo":         "ginkgo yellow autumn japan street",
    "winter_snow":           "winter snow landscape japan serene",
    "winter_christmas":      "christmas pine tree snow winter festive",
    "new_year_sunrise":      "sunrise dawn japan new year golden sky",
}

# ─── グラデーション定義 ────────────────────────────────────────────────────
# 各テーマのグラデーション: [(y比率 0.0-1.0, RGB色), ...]

GRADIENT_STOPS = {
    "spring_sakura": [
        (0.0,  (255, 235, 245)),   # 上: 淡いピンク
        (0.4,  (250, 218, 235)),   # 中: 桜色
        (1.0,  (245, 240, 252)),   # 下: 薄紫がかった白
    ],
    "spring_fresh": [
        (0.0,  (215, 240, 215)),   # 上: 淡い新緑
        (0.5,  (200, 235, 205)),   # 中: 若草色
        (1.0,  (240, 250, 240)),   # 下: 薄いクリーム緑
    ],
    "early_summer_wisteria": [
        (0.0,  (235, 220, 250)),   # 上: 薄紫
        (0.4,  (220, 200, 245)),   # 中: 藤色
        (1.0,  (245, 240, 252)),   # 下: 白に近い薄紫
    ],
    "summer_hydrangea": [
        (0.0,  (210, 225, 250)),   # 上: 空色
        (0.4,  (200, 215, 245)),   # 中: 紫陽花ブルー
        (1.0,  (235, 242, 252)),   # 下: 白に近い青
    ],
    "summer_ocean": [
        (0.0,  (185, 225, 240)),   # 上: 空
        (0.35, (150, 210, 230)),   # 上中: 水平線
        (0.6,  (120, 195, 220)),   # 中: 海面
        (1.0,  (200, 235, 245)),   # 下: 砂浜の淡い色
    ],
    "summer_night": [
        (0.0,  (10,  20,  55)),    # 上: 深夜空
        (0.3,  (25,  40,  90)),    # 上中: 濃紺
        (0.7,  (40,  60,  120)),   # 中: 夜明け前
        (1.0,  (70,  90,  150)),   # 下: 地平線近く
    ],
    "early_autumn_cosmos": [
        (0.0,  (255, 235, 245)),   # 上: 薄いピンク
        (0.4,  (248, 225, 238)),   # 中: コスモス色
        (1.0,  (248, 245, 240)),   # 下: クリーム
    ],
    "autumn_leaves": [
        (0.0,  (255, 235, 205)),   # 上: 淡い橙
        (0.4,  (245, 215, 175)),   # 中: 暖かいオレンジ
        (1.0,  (250, 240, 225)),   # 下: 薄いクリーム
    ],
    "autumn_ginkgo": [
        (0.0,  (255, 248, 210)),   # 上: 淡い黄
        (0.4,  (248, 235, 170)),   # 中: 銀杏の金色
        (1.0,  (252, 248, 230)),   # 下: クリーム
    ],
    "winter_snow": [
        (0.0,  (220, 233, 248)),   # 上: 冬空の青
        (0.3,  (235, 242, 252)),   # 上中: 薄い空色
        (1.0,  (248, 250, 255)),   # 下: 雪原の白
    ],
    "winter_christmas": [
        (0.0,  (15,  65,  40)),    # 上: 深い緑
        (0.4,  (30,  90,  60)),    # 中: モミの木
        (0.75, (45,  110, 75)),    # 下中: 明るい緑
        (1.0,  (60,  130, 85)),    # 下: やや明るい
    ],
    "new_year_sunrise": [
        (0.0,  (40,  25,  70)),    # 上: 夜の紫
        (0.3,  (100, 60,  110)),   # 上中: 夜明け前の紫
        (0.6,  (220, 130, 60)),    # 中下: 朝焼けオレンジ
        (1.0,  (255, 200, 80)),    # 下: 初日の出の金
    ],
}


# ─── グラデーション描画 ───────────────────────────────────────────────────

def _interpolate_color(stops, t):
    """0〜1の位置 t に対応する補間色を返す"""
    if t <= stops[0][0]:
        return stops[0][1]
    if t >= stops[-1][0]:
        return stops[-1][1]
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(int(c0[j] * (1 - f) + c1[j] * f) for j in range(3))
    return stops[-1][1]


def make_gradient_background(theme_key: str, w: int = BG_W, h: int = BG_H) -> Image.Image:
    """グラデーション背景画像を生成する"""
    stops = GRADIENT_STOPS.get(theme_key, GRADIENT_STOPS["spring_sakura"])

    # ピクセル配列を作成
    arr = np.zeros((h, w, 3), dtype=np.float32)
    for y in range(h):
        t = y / max(h - 1, 1)
        color = _interpolate_color(stops, t)
        arr[y, :] = color

    # ソフトノイズを加えて質感を出す（振幅は小さく）
    noise = np.random.normal(0, 2.5, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    # 軽くぼかして滑らかに
    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))

    # テーマ固有の追加描画
    _add_theme_details(img, theme_key)

    return img


def _add_theme_details(img: Image.Image, theme_key: str):
    """テーマ固有の装飾を画像に追加する"""
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size

    if theme_key == "summer_night":
        # 星を散りばめる
        rng = random.Random(42)
        for _ in range(350):
            x = rng.randint(0, w)
            y = rng.randint(0, int(h * 0.75))
            brightness = rng.randint(140, 255)
            r = rng.choice([1, 1, 1, 2])
            alpha = rng.randint(100, 220)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(brightness, brightness, brightness, alpha))

    elif theme_key == "winter_snow":
        # 雪の結晶（シンプルな点）を散りばめる
        rng = random.Random(99)
        for _ in range(200):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            r = rng.choice([2, 2, 3, 4])
            alpha = rng.randint(80, 180)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 255, alpha))

    elif theme_key == "winter_christmas":
        # 雪の点を散りばめる
        rng = random.Random(77)
        for _ in range(150):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            r = rng.choice([2, 3, 3])
            alpha = rng.randint(60, 150)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 255, alpha))

    elif theme_key == "new_year_sunrise":
        # 光の放射線（初日の出）
        cx, cy = w // 2, int(h * 0.62)
        rng = random.Random(55)
        for i in range(16):
            angle = i * (360 / 16)
            import math
            rad = math.radians(angle)
            length = rng.randint(int(h * 0.3), int(h * 0.5))
            ex = int(cx + math.cos(rad) * length)
            ey = int(cy + math.sin(rad) * length)
            draw.line([cx, cy, ex, ey], fill=(255, 220, 100, 15), width=rng.randint(2, 8))

    elif theme_key in ("spring_sakura", "early_autumn_cosmos"):
        # ぼんやりした丸（花びら的な光の点）
        rng = random.Random(33 if theme_key == "spring_sakura" else 66)
        base_color = (255, 200, 220) if theme_key == "spring_sakura" else (255, 200, 210)
        for _ in range(30):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            r = rng.randint(20, 80)
            alpha = rng.randint(15, 40)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(*base_color, alpha))


# ─── Unsplash API ─────────────────────────────────────────────────────────

def download_unsplash(theme_key: str, access_key: str, w: int = BG_W, h: int = BG_H) -> Image.Image | None:
    """Unsplash API から写真をダウンロードして返す。失敗時は None"""
    try:
        import urllib.request
        import json

        query = UNSPLASH_QUERIES.get(theme_key, "nature japan")
        url = (
            f"https://api.unsplash.com/photos/random"
            f"?query={urllib.parse.quote(query)}"
            f"&orientation=portrait"
            f"&client_id={access_key}"
        )

        import urllib.parse
        req = urllib.request.Request(url, headers={"Accept-Version": "v1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        photo_url = data["urls"]["regular"]   # 1080px幅
        print(f"  → Unsplash: {data['links']['html']}")

        with urllib.request.urlopen(photo_url, timeout=30) as resp:
            img_data = resp.read()

        img = Image.open(io.BytesIO(img_data)).convert("RGB")

        # ポスター縦比にリサイズ（中央クロップ）
        target_ratio = h / w
        src_ratio = img.height / img.width
        if src_ratio > target_ratio:
            new_w = img.width
            new_h = int(new_w * target_ratio)
            top = (img.height - new_h) // 2
            img = img.crop((0, top, new_w, top + new_h))
        else:
            new_h = img.height
            new_w = int(new_h / target_ratio)
            left = (img.width - new_w) // 2
            img = img.crop((left, 0, left + new_w, new_h))

        img = img.resize((w, h), Image.LANCZOS)
        return img

    except Exception as e:
        print(f"  ✗ Unsplash 取得失敗: {e}")
        return None


# ─── メイン処理 ───────────────────────────────────────────────────────────

def generate_all(use_unsplash: bool = False, themes_filter: list = None):
    from themes.color_themes import THEMES

    target_themes = [k for k in THEMES if k != "custom"]
    if themes_filter:
        target_themes = [k for k in target_themes if k in themes_filter]

    access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "") if use_unsplash else ""

    print(f"背景画像を生成します → {OUTPUT_DIR}")
    print(f"モード: {'Unsplash API + グラデーション fallback' if use_unsplash else 'グラデーション（オフライン）'}")
    print()

    generated = []
    for theme_key in target_themes:
        theme = THEMES[theme_key]
        out_path = OUTPUT_DIR / theme["bg_image"]

        if out_path.exists():
            print(f"[skip]  {theme_key:30s} → {out_path.name} (既存)")
            generated.append(out_path)
            continue

        print(f"[生成]  {theme['name']}")
        img = None

        if use_unsplash and access_key:
            print(f"  Unsplash 検索: {UNSPLASH_QUERIES.get(theme_key, '')}")
            img = download_unsplash(theme_key, access_key)
            time.sleep(0.5)   # Rate limit 対策

        if img is None:
            print(f"  グラデーション生成中...")
            img = make_gradient_background(theme_key)

        img.save(out_path, format="PNG", optimize=True)
        print(f"  保存: {out_path.name}  ({img.width}×{img.height}px)")
        generated.append(out_path)

    print()
    print(f"完了: {len(generated)} 件")
    return generated


def main():
    parser = argparse.ArgumentParser(description="GPI Poster 季節背景画像生成")
    parser.add_argument("--unsplash", action="store_true",
                        help="Unsplash API を使って写真を取得する（UNSPLASH_ACCESS_KEY 環境変数が必要）")
    parser.add_argument("--theme", nargs="+", metavar="THEME_KEY",
                        help="生成するテーマキーを指定（省略時は全テーマ）")
    parser.add_argument("--force", action="store_true",
                        help="既存ファイルを上書き再生成する")
    args = parser.parse_args()

    if args.force:
        for f in OUTPUT_DIR.glob("*.png"):
            f.unlink()
            print(f"削除: {f.name}")

    generate_all(use_unsplash=args.unsplash, themes_filter=args.theme)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
