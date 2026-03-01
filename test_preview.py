"""
テスト: プレビューレンダリング（Pillow）
2025年度第1回のデータを使ってポスターPNGを出力する。
実行: python test_preview.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from poster.models import PosterData, Section, ContentItem, PersonInfo
from poster.preview_renderer import render_poster

# ─── テストデータ（2025年度第1回を模倣） ────────────────────────────────

data = PosterData(
    year=2025,
    session_num=1,
    theme_key="spring_sakura",
    event_date="2025年 5月23日(金)",
    time_range="19:00 - 20:30",
    venue_room="5F 小会議室1",
    venue_building="じゅうろくプラザ",
    venue_address="〒500-8856 岐阜県岐阜市橋本町1丁目10-11",
    registration_url="https://example.zoom.us/meeting/register/test",
    zoom_note="&zoomミーティング",
    mc=PersonInfo(
        affiliation="岐阜大学医学部附属病院 小児科",
        name="山田 太郎"
    ),
    chair=None,
    audience=["学生", "初期研修医", "後期研修医", "小児科医"],
    sections=[
        Section(
            label="第1部",
            time_start="19:00",
            time_end="19:20",
            contents=[
                ContentItem(
                    badge_label="症例報告1（10分）",
                    title="発熱と皮疹を主訴に来院した2歳児の一例",
                    affiliation="岐阜大学医学部附属病院 小児科",
                    presenter_name="田中 花子",
                ),
                ContentItem(
                    badge_label="症例報告2（10分）",
                    title="反復する腹痛を訴える学童期の男児",
                    affiliation="岐阜市民病院 小児科",
                    presenter_name="佐藤 次郎",
                ),
            ],
        ),
        Section(
            label="第2部",
            time_start="19:20",
            time_end="19:40",
            contents=[
                ContentItem(
                    badge_label="国内留学日誌（15分）",
                    title="東京大学小児科での研修を終えて",
                    affiliation="岐阜大学医学部附属病院 小児科",
                    presenter_name="鈴木 三郎",
                ),
            ],
        ),
        Section(
            label="第3部（特別企画）",
            time_start="19:40",
            time_end="20:30",
            contents=[
                ContentItem(
                    badge_label="特別講演（50分）",
                    title="小児の発熱性疾患における最新の治療戦略と今後の展望について",
                    affiliation="名古屋大学医学部附属病院 小児科学教室",
                    presenter_name="中村 四郎",
                ),
            ],
        ),
    ],
    contact_email="gpi.office.med@gmail.com",
    bg_opacity=0.30,
)

# ─── レンダリング ────────────────────────────────────────────────────────

print("フォントを準備中...")
from utils.font_manager import ensure_fonts
ensure_fonts()

print("ポスターを生成中...")
img = render_poster(data, scale=1.0)

output_path = Path(__file__).parent / "test_output_preview.png"
img.save(str(output_path), format="PNG")
print(f"✅ 保存完了: {output_path}")
print(f"   サイズ: {img.size[0]} x {img.size[1]} px")

# macOS で自動的に開く
import subprocess
subprocess.run(["open", str(output_path)], check=False)
