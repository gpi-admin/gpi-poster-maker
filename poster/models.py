from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ContentItem:
    """各発表の情報"""
    badge_label: str       # バッジ表示テキスト e.g. "症例報告1（10分）"
    title: str             # 発表タイトル（改行可）
    affiliation: str       # 所属機関（改行可）
    presenter_name: str    # 発表者名。敬称込みで入力されたまま描画する（自動で「先生」は付けない）。
                           # 改行で複数名を入力可（1行 = 1名）。
    subtitle: str = ""     # サブタイトル（任意・改行可）。タイトル直下に小さめで描画
    # ユーザー指定の文字サイズ倍率（1.0 = 100%）。
    # 有効範囲は layout.py の USER_FONT_SCALE_MIN / MAX でクランプされる。
    title_scale: float = 1.0
    subtitle_scale: float = 1.0        # 基準サイズ FS_PROG_SUBTITLE に対する倍率
    affiliation_scale: float = 1.0
    name_scale: float = 1.0


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
    affiliation: str       # 所属（改行可）
    name: str              # 氏名。敬称込みで入力されたまま描画（改行で複数名可）
    affiliation_scale: float = 1.0     # ユーザー指定の文字サイズ倍率（1.0 = 100%）
    name_scale: float = 1.0


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
    contact_email: str = "gpi.office.med@gmail.com"

    # ビジュアル設定
    bg_opacity: float = 0.35
    background_image_path: Optional[str] = None  # None = 背景なし
    decorative_images: List[str] = field(default_factory=list)  # ファイルパスのリスト

    # カスタムカラー（theme_key="custom"時）
    custom_accent_color: Optional[tuple] = None    # (R, G, B)
    custom_accent_light: Optional[tuple] = None    # (R, G, B)
