from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ContentItem:
    """各発表の情報"""
    badge_label: str       # バッジ表示テキスト e.g. "症例報告1（10分）"
    title: str             # 発表タイトル
    affiliation: str       # 所属機関
    presenter_name: str    # 発表者名


@dataclass
class Section:
    """第N部の情報"""
    label: str             # バッジラベル e.g. "第1部", "第3部（特別企画）"
    time_start: str        # 開始時刻 e.g. "19:00"
    time_end: str          # 終了時刻 e.g. "19:30"
    contents: List[ContentItem] = field(default_factory=list)


@dataclass
class PersonInfo:
    """司会・座長の情報"""
    affiliation: str
    name: str


@dataclass
class PosterData:
    """ポスター全体のデータモデル"""
    # 基本情報
    year: int                          # 年度 e.g. 2026
    session_num: int                   # 回数 e.g. 1
    theme_key: str                     # テーマキー e.g. "spring_pink"

    # 開催情報
    event_date: str                    # 開催日 e.g. "2026年 5月23日(土)"
    time_range: str = "19:00 - 20:30"

    # 会場情報
    venue_room: str = "5F 小会議室1"
    venue_building: str = "じゅうろくプラザ"
    venue_address: str = "〒500-8856 岐阜県岐阜市橋本町1丁目10-11"

    # Zoom / QR
    registration_url: str = ""
    zoom_note: str = "&zoomミーティング"

    # 司会・座長
    mc: Optional[PersonInfo] = None
    chair: Optional[PersonInfo] = None        # 座長（任意）
    chair_label: str = "特別講演 座長"          # バッジラベル（ユーザー編集可）

    # 対象
    audience: List[str] = field(default_factory=lambda: [
        "学生", "初期研修医", "後期研修医", "小児科医"
    ])

    # プログラム
    sections: List[Section] = field(default_factory=list)

    # 連絡先
    contact_email: str = "gpi.jimu@gmail.com"

    # ビジュアル設定
    bg_opacity: float = 0.35
    background_image_path: Optional[str] = None  # None = テーマデフォルト
    decorative_images: List[str] = field(default_factory=list)  # ファイルパスのリスト

    # カスタムカラー（theme_key="custom"時）
    custom_accent_color: Optional[tuple] = None    # (R, G, B)
    custom_accent_light: Optional[tuple] = None    # (R, G, B)
