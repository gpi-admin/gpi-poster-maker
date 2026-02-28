"""
ポスターレイアウト定数と動的配置エンジン

座標系: 正規化座標 (0.0 〜 1.0)
- (0, 0) = 左上
- (1, 1) = 右下

Pillow プレビュー: 794 x 1123 px
ReportLab PDF:    595.27 x 841.89 pt
"""

from dataclasses import dataclass, field
from typing import List

# ─── キャンバスサイズ ─────────────────────────────────────────────────────

PREVIEW_W = 794
PREVIEW_H = 1123

PDF_W = 595.27
PDF_H = 841.89

HIRES_W = 2480
HIRES_H = 3508

# ─── ヘッダー・フッター ──────────────────────────────────────────────────

HEADER_TOP = 0.010  # ヘッダー帯の上余白（背景が見える部分）
HEADER_H = 0.030   # 上部バー高さ
FOOTER_H = 0.034   # 下部バー高さ

# ─── カラム構成 (0.0 = 左端, 1.0 = 右端) ────────────────────────────────
#
# 左→右の順:
#   左カラム  (0〜37%)  : 場所・日時・司会・対象・QR
#   タイトル帯(37〜50%) : 縦書き「第N回岐阜県小児科研修セミナー」（中央より少し左）
#   右ストリップ(50〜54%): 「2025年度」縦書き + 第N部ラベルボックス
#   プログラム(54〜100%): 参加費無料 + 各セクション内容
#
# ※ 縦バーは廃止。タイトル帯がその役割を担う。

# 左カラム: 場所・日時・司会・QR
LEFT_W  = 0.395   # 左カラム幅

# 縦書きメインタイトル帯（「第N回岐阜県小児科研修セミナー」）
# ポスター中央（50%）より少し左 39.5〜50% に配置
TITLE_X = 0.395   # メインタイトル帯左端 X（= 左カラム右端）
TITLE_W = 0.105   # メインタイトル帯幅

# 右ストリップ（「2025年度」+ 第N部ラベルボックス）
SECT_X  = TITLE_X + TITLE_W   # = 0.500（ポスター中央）
SECT_W  = 0.050              # ≈ 5%（細いストリップ）

# プログラムエリア（ポスター右側 55〜100%）
PROG_X  = SECT_X + SECT_W    # = 0.550
PROG_W  = 1.0 - PROG_X       # = 0.460

# ─── 左カラム内部マージン ────────────────────────────────────────────────

LC_PAD_L = 0.030   # 左パディング (canvas_width 比)
LC_PAD_R = 0.012   # 右パディング

# ─── プログラムエリア内部マージン ────────────────────────────────────────

PROG_PAD_L = 0.011
PROG_PAD_R = 0.020

# ─── プログラムエリア縦範囲 ──────────────────────────────────────────────

PROG_TOP = 0.215   # 動的レイアウト開始 Y (年度テキスト下に余白)
PROG_BOT = 1.0 - FOOTER_H - 0.008
PROG_H   = PROG_BOT - PROG_TOP

# ─── フォントサイズ定数 (正規化高さ; × PREVIEW_H で px 変換) ────────────

FS_HEADER      = 0.018   # ヘッダーバー文字
FS_VENUE_BIG   = 0.025   # 会場名（建物）
FS_VENUE_SM    = 0.013   # 部屋・住所
FS_DATE_LBL    = 0.032   # "2025年" 小ラベル
FS_DATE_BIG    = 0.063   # "5月23日(金)" 超大文字
FS_TIME_LC     = 0.029   # 左カラム時刻
FS_MC_BADGE    = 0.015   # 司会バッジ文字
FS_MC_AFF      = 0.014   # 司会所属
FS_MC_NAME     = 0.021   # 司会氏名
FS_AUD         = 0.016   # 対象
FS_QR_CAP      = 0.013   # QRキャプション
FS_FOOTER      = 0.016   # フッター文字

FS_PROG_TIME   = 0.021   # プログラム時刻 ("19:00 - 19:20")
FS_PROG_BADGE  = 0.017   # 小バッジ文字
FS_PROG_TITLE  = 0.024   # 発表タイトル
FS_PRESENTER   = 0.018   # 所属
FS_PRES_NAME   = 0.021   # 発表者氏名
FS_SANSHUUHI   = 0.030   # 参加費無料

FS_V_TITLE     = 0.090   # 縦書きタイトル文字 (正規化高さ)
FS_V_YEAR      = 0.022   # 縦書き年度文字

# ─── セクション別コンテンツスケール ──────────────────────────────────────
# 第1部・第2部: 0.90（やや小さく）, 第3部: 1.10（やや大きく）
SECTION_CONTENT_SCALES = [0.90, 0.90, 1.10]

# タイトルブロック高さ乗数（フォントが小さいほど行間余白が詰まるため補正）
# cs=0.90 のとき 1.35、cs=1.10 のとき 1.20 で視覚的な余白を統一
SECTION_TITLE_MULTIPLIERS = [1.20, 1.20, 1.03]

# ─── バッジサイズ (normalized) ───────────────────────────────────────────

BASHO_BW    = 0.080   # 場所バッジ幅 (canvas width 比)
BASHO_BH    = 0.038   # 場所バッジ高さ (canvas height 比)
BADGE_SM_H  = 0.025   # 小バッジ高さ
BADGE_MC_H  = 0.024   # 司会バッジ高さ
BADGE_AUD_H = 0.022   # 対象バッジ高さ

# ─── LayoutEngine ────────────────────────────────────────────────────────


@dataclass
class Block:
    """配置済みブロック（正規化座標）"""
    kind: str   # "section_time"|"sub_badge"|"title"|"affiliation"|"name"|"gap"
    y: float    # トップ Y (正規化)
    h: float    # 高さ (正規化)
    data: dict = field(default_factory=dict)


class LayoutEngine:
    """
    プログラムセクションを動的にレイアウトする。
    フォントスケールを 1.0 → 0.70 まで下げながら利用可能エリアに収める。
    MC/座長は含まない（左カラムで描画）。
    """

    def __init__(self, poster_data):
        self.data = poster_data

    def compute(self) -> List[Block]:
        for scale in [1.0, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70]:
            blocks = self._build_blocks(scale)
            total = sum(b.h for b in blocks)
            if total <= PROG_H:
                return self._assign_y(blocks)
        return self._assign_y(self._build_blocks(0.70))

    def _build_blocks(self, scale: float) -> List[Block]:
        blocks = []
        for si, sec in enumerate(self.data.sections):
            if si > 0:
                blocks.append(Block("gap", 0, 0.014 * scale, {"scale": scale}))

            # セクション別コンテンツスケール（タイトル・所属・氏名のみ適用）
            cs = SECTION_CONTENT_SCALES[si] if si < len(SECTION_CONTENT_SCALES) else 1.0
            tm = SECTION_TITLE_MULTIPLIERS[si] if si < len(SECTION_TITLE_MULTIPLIERS) else 1.2

            # 時刻ヘッダー
            if sec.time_start and sec.time_end:
                blocks.append(Block("section_time", 0, FS_PROG_TIME * scale * 1.3, {
                    "text": f"{sec.time_start}  -  {sec.time_end}",
                    "part_label": sec.label,
                    "part_idx": si,
                    "scale": scale,
                }))

            for ci, item in enumerate(sec.contents):
                if ci > 0:
                    blocks.append(Block("gap", 0, 0.007 * scale, {"scale": scale}))

                # 小バッジ
                blocks.append(Block("sub_badge", 0, (BADGE_SM_H + 0.013) * scale, {
                    "label": item.badge_label,
                    "scale": scale,
                }))

                # タイトル行数推定（cs が大きいほど1行の文字数が減る）
                chars_per_line = max(8, int(13 / cs))
                title_lines = max(1, len(item.title) // chars_per_line + 1)
                blocks.append(Block("title", 0, FS_PROG_TITLE * scale * tm * title_lines * cs, {
                    "text": item.title,
                    "scale": scale,
                    "content_scale": cs,
                    "lines": title_lines,
                }))

                # 所属（手動改行を考慮）
                aff_text = item.affiliation
                manual_lines = aff_text.count("\n") + 1
                aff_chars_per_line = max(10, int(20 / cs))
                auto_lines = max(1, len(aff_text.replace("\n", "")) // aff_chars_per_line + 1)
                aff_lines = max(manual_lines, auto_lines)
                blocks.append(Block("affiliation", 0, FS_PRESENTER * scale * 1.35 * aff_lines * cs, {
                    "text": item.affiliation,
                    "scale": scale,
                    "content_scale": cs,
                }))

                # 氏名
                blocks.append(Block("name", 0, FS_PRES_NAME * scale * 1.5 * cs, {
                    "text": item.presenter_name,
                    "scale": scale,
                    "content_scale": cs,
                }))

        return blocks

    def _assign_y(self, blocks: List[Block]) -> List[Block]:
        """Y座標を順番に割り当てる"""
        y = PROG_TOP
        for b in blocks:
            b.y = y
            y += b.h
        return blocks


# ─── pdf_renderer.py 後方互換エイリアス ──────────────────────────────────

LEFT_COL_X    = 0.0
LEFT_COL_W    = LEFT_W
DIVIDER_X     = TITLE_X
DIVIDER_W     = TITLE_W
RIGHT_COL_X   = PROG_X

LC_MARGIN_X   = LC_PAD_L
LC_W          = LEFT_W - LC_PAD_L - LC_PAD_R

RC_MARGIN_X   = PROG_PAD_L
RC_W          = PROG_W - PROG_PAD_L - PROG_PAD_R

MARGIN_TOP    = HEADER_TOP + HEADER_H
MARGIN_BOTTOM = FOOTER_H

TITLE_STRIP_X = TITLE_X
TITLE_STRIP_W = TITLE_W

DATE_AREA_Y   = HEADER_TOP + HEADER_H + 0.020
DATE_AREA_H   = 0.150

PROGRAM_TOP   = PROG_TOP
PROGRAM_BOT   = PROG_BOT

BASHO_BADGE_R = BASHO_BH / 2.0   # 正規化半径

BADGE_LG_W    = BASHO_BW
BADGE_LG_H    = BASHO_BH
BADGE_SM_W    = 0.250

FS_DATE       = FS_DATE_BIG
FS_TIME       = FS_TIME_LC
FS_TITLE      = FS_V_TITLE
FS_BADGE_LG   = FS_MC_BADGE
FS_BADGE_SM   = FS_PROG_BADGE
FS_SECTION_H  = FS_PROG_TITLE
FS_VENUE      = FS_VENUE_BIG
FS_AUDIENCE   = FS_AUD
FS_MC         = FS_MC_NAME

# ─── ヘルパー変換 ────────────────────────────────────────────────────────

def n_to_px(value: float, axis: str = "h") -> int:
    """正規化サイズ → プレビューピクセル数"""
    return int(value * (PREVIEW_H if axis == "h" else PREVIEW_W))


def n_to_pt(value: float, axis: str = "h") -> float:
    """正規化サイズ → PDFポイント数"""
    return value * (PDF_H if axis == "h" else PDF_W)
