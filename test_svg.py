"""
テスト: SVG レンダリング（アプリが実際に使う出力経路）
発表者名（敬称込み自由入力・改行で複数名）、サブタイトル、ユーザー文字サイズ倍率を確認する。
実行: .venv/bin/python test_svg.py  → test_output_svg.png を生成（目視確認）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cairosvg  # noqa: E402

from poster.layout import (  # noqa: E402
    FS_PRES_NAME,
    NAME_FIT_MIN,
    PDF_H,
    PDF_W,
    PROG_PAD_L,
    PROG_PAD_R,
    PROG_W,
    LayoutEngine,
    clamp_user_scale,
    rl_name_metrics,
)
from poster.models import ContentItem, PersonInfo, PosterData, Section  # noqa: E402
from poster.name_utils import split_honorific_segments, split_name_lines  # noqa: E402
from poster.svg_renderer import _ensure_svg_fonts, render_poster_svg  # noqa: E402

# ─── name_utils の単体確認 ──────────────────────────────────────────────

assert split_name_lines(None) == []
assert split_name_lines("") == []
assert split_name_lines(" 山田 太郎 先生 \n\n  鈴木 花子 様\n") == ["山田 太郎 先生", "鈴木 花子 様"]

assert split_honorific_segments("山田 太郎 先生") == [("山田 太郎", False), (" 先生", True)]
assert split_honorific_segments("山田 太郎 様") == [("山田 太郎", False), (" 様", True)]
assert split_honorific_segments("山田 太郎") == [("山田 太郎", False)]
assert split_honorific_segments("山田太郎先生") == [("山田太郎先生", False)]
assert split_honorific_segments("山田 太郎 先生、鈴木 花子 先生") == [
    ("山田 太郎", False), (" 先生", True), ("、鈴木 花子", False), (" 先生", True),
]
assert split_honorific_segments("山田 太郎　　先生") == [("山田 太郎", False), (" 先生", True)]
assert split_honorific_segments("山田 さんま") == [("山田 さんま", False)]

assert clamp_user_scale(None) == 1.0
assert clamp_user_scale(9) == 1.5
assert clamp_user_scale(0.1) == 0.5

# ─── テストデータ ─────────────────────────────────────────────────────

# 1行に2名で幅を超える（fit が NAME_FIT_MIN〜1.0 の間で効き、領域内に収まる）
LONG_NAME = "長谷川 小百合子 先生、勅使河原 宏 先生"

data = PosterData(
    year=2026, session_num=2, theme_key="spring_sakura",
    event_date="2026年 6月12日(金)", time_range="19:00 - 20:30",
    venue_room="5F 小会議室1", venue_building="じゅうろくプラザ",
    venue_address="〒500-8856 岐阜県岐阜市橋本町1丁目10-11",
    registration_url="https://example.zoom.us/meeting/register/test",
    mc=PersonInfo("岐阜大学医学部附属病院 小児科", "山田 太郎 先生\n佐藤 花子 先生", name_scale=0.9),
    chair=PersonInfo("岐阜県総合医療センター\n小児科", "高橋 五郎 様"),
    sections=[
        Section("第1部", "19:00", "19:20", [
            ContentItem("症例報告1（10分）", "発熱と皮疹を主訴に来院した2歳児の一例",
                        "岐阜大学医学部附属病院 小児科",
                        "田中 花子 先生\n伊藤 一郎 先生",
                        title_scale=0.85),
            ContentItem("症例報告2（10分）", "反復する腹痛を訴える学童期の男児",
                        "岐阜市民病院 小児科", "佐藤 次郎 様",
                        name_scale=1.2),
        ]),
        Section("第2部", "19:20", "19:40", [
            ContentItem("国内留学日誌（15分）", "東京大学小児科での研修を終えて",
                        "岐阜大学医学部附属病院 小児科", "鈴木 三郎 先生、渡辺 四郎 先生"),
            ContentItem("ミニレクチャー（5分）", "外来で役立つ小児の皮膚診察",
                        "岐阜赤十字病院 小児科", "加藤 美咲"),
        ]),
        Section("第3部（特別企画）", "19:40", "20:30", [
            ContentItem("特別講演（50分）",
                        "小児の発熱性疾患における最新の治療戦略と今後の展望について",
                        "名古屋大学医学部附属病院 小児科学教室", LONG_NAME,
                        subtitle="〜エビデンスと臨床現場のギャップを埋めるために〜",
                        title_scale=1.2, subtitle_scale=1.0),
        ]),
    ],
    bg_opacity=0.30,
)

# ─── レイアウト契約の確認 ──────────────────────────────────────────────

_ensure_svg_fonts()  # LayoutEngine(use_reportlab=True) は ReportLab フォント登録済みが前提
blocks = LayoutEngine(data, use_reportlab=True).compute()
kinds = [b.kind for b in blocks]
assert kinds.count("subtitle") == 5, kinds
for b in blocks:
    if b.kind == "subtitle" and not b.data["text"]:
        assert b.h == 0.0
name_blocks = [b for b in blocks if b.kind == "name"]
assert [len(b.data["lines"]) for b in name_blocks] == [2, 1, 1, 1, 1]
assert name_blocks[0].data["lines"][0] == [("田中 花子", False), (" 先生", True)]
assert name_blocks[2].data["lines"][0] == [
    ("鈴木 三郎", False), (" 先生", True), ("、渡辺 四郎", False), (" 先生", True),
]
assert name_blocks[3].data["lines"] == [[("加藤 美咲", False)]]
nb = name_blocks[4]
assert NAME_FIT_MIN < nb.data["fit"] < 1.0, "長い氏名で fit が効いていない／下限に張り付いている"
_m = rl_name_metrics(
    nb.data["lines"],
    FS_PRES_NAME * PDF_H * nb.data["scale"] * nb.data["content_scale"] * nb.data["user_scale"],
    nb.data["fit"],
)
assert max(_m.line_widths) <= (PROG_W - PROG_PAD_L - PROG_PAD_R) * PDF_W + 1e-6, "長い氏名がはみ出している"
assert all(b.data["fit"] == 1.0 for b in name_blocks[:4])
# ブロックは重ならず順に並ぶ
for a, b in zip(blocks, blocks[1:]):
    assert abs((a.y + a.h) - b.y) < 1e-9
print("fit (long name):", round(name_blocks[4].data["fit"], 3))

# Pillow 計測経路も同じ契約で動くこと
pil_blocks = LayoutEngine(data, use_reportlab=False).compute()
assert [b.kind for b in pil_blocks] == kinds
assert all("lines" in b.data and "fit" in b.data for b in pil_blocks if b.kind == "name")

# ─── 描画 ─────────────────────────────────────────────────────────────

svg = render_poster_svg(data, font_key="biz_ud", embed_fonts=False)
assert "田中 花子" in svg and "伊藤 一郎" in svg
assert "加藤 美咲 先生" not in svg
assert svg.count(">加藤 美咲<") == 1

out = Path(__file__).parent / "test_output_svg.png"
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out), scale=2)
print(f"OK: {out}")
