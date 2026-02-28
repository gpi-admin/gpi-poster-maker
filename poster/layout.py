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

HEADER_H = 0.030   # 上部バー高さ
FOOTER_H = 0.034   # 下部バー高さ

# ─── カラム構成 (0.0 = 左端, 1.0 = 右端) ────────────────────────────────

# 左カラム: 場所・日時・司会・QR
LEFT_W  = 0.370   # 左カラム幅

# 中央縦バー
DIV_X   = 0.370   # 縦バー左端 X
DIV_W   = 0.022   # 縦バー幅

# プログラムエリア（縦バー右〜メインタイトル左）
PROG_X  = DIV_X + DIV_W   # = 0.392
TITLE_X = 0.608            # 縦書きメインタイトル帯左端 X
PROG_W  = TITLE_X - PROG_X  # ≈ 0.216

# 縦書きメインタイトル帯（「第N回岐阜県小児科研修セミナー」）
TITLE_W = 0.157            # メインタイトル帯幅

# 右ストリップ（「2025年度」+ 第N部ラベルボックス）
SECT_X  = TITLE_X + TITLE_W   # = 0.765
SECT_W  = 1.0 - SECT_X        # ≈ 0.235

# ─── 左カラム内部マージン ────────────────────────────────────────────────

LC_PAD_L = 0.016   # 左パディング (canvas_width 比)
LC_PAD_R = 0.012   # 右パディング

# ─── プログラムエリア内部マージン ────────────────────────────────────────

PROG_PAD_L = 0.011
PROG_PAD_R = 0.008

# ─── プログラムエリア縦範囲 ──────────────────────────────────────────────

PROG_TOP = 0.180   # 動的レイアウト開始 Y (年度テキスト下に余白)
PROG_BOT = 1.0 - FOOTER_H - 0.008
PROG_H   = PROG_BOT - PROG_TOP   # ≈ 0.778

# ─── フォントサイズ定数 (正規化高さ; × PREVIEW_H で px 変換) ────────────

FS_HEADER      = 0.018   # ヘッダーバー文字
FS_VENUE_BIG   = 0.025   # 会場名（建物）
FS_VENUE_SM    = 0.016   # 部屋・住所
FS_DATE_LBL    = 0.021   # "2025年" 小ラベル
FS_DATE_BIG    = 0.063   # "5月23日(金)" 超大文字
FS_TIME_LC     = 0.033   # 左カラム時刻
FS_MC_BADGE    = 0.015   # 司会バッジ文字
FS_MC_AFF      = 0.014   # 司会所属
FS_MC_NAME     = 0.021   # 司会氏名
FS_AUD         = 0.016   # 対象
FS_QR_CAP      = 0.013   # QRキャプション
FS_FOOTER      = 0.016   # フッター文字

FS_PROG_TIME   = 0.021   # プログラム時刻 ("19:00 - 19:20")
FS_PROG_BADGE  = 0.017   # 小バッジ文字
FS_PROG_TITLE  = 0.024   # 発表タイトル
FS_PRESENTER   = 0.015   # 所属
FS_PRES_NAME   = 0.021   # 発表者氏名
FS_SANSHUUHI   = 0.030   # 参加費無料

FS_V_TITLE     = 0.075   # 縦書きタイトル文字 (正規化高さ)
FS_V_YEAR      = 0.022   # 縦書き年度文字

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

            # 時刻ヘッダー
            if sec.time_start and sec.time_end:
                blocks.append(Block("section_time", 0, FS_PROG_TIME * scale * 1.7, {
                    "text": f"{sec.time_start}  -  {sec.time_end}",
                    "part_label": sec.label,
                    "part_idx": si,
                    "scale": scale,
                }))

            for ci, item in enumerate(sec.contents):
                if ci > 0:
                    blocks.append(Block("gap", 0, 0.007 * scale, {"scale": scale}))

                # 小バッジ
                blocks.append(Block("sub_badge", 0, (BADGE_SM_H + 0.007) * scale, {
                    "label": item.badge_label,
                    "scale": scale,
                }))

                # タイトル（行数推定）
                title_lines = max(1, len(item.title) // 18 + 1)
                blocks.append(Block("title", 0, FS_PROG_TITLE * scale * 1.4 * title_lines, {
                    "text": item.title,
                    "scale": scale,
                    "lines": title_lines,
                }))

                # 所属
                aff_lines = max(1, len(item.affiliation) // 20 + 1)
                blocks.append(Block("affiliation", 0, FS_PRESENTER * scale * 1.35 * aff_lines, {
                    "text": item.affiliation,
                    "scale": scale,
                }))

                # 氏名
                blocks.append(Block("name", 0, FS_PRES_NAME * scale * 1.5, {
                    "text": item.presenter_name,
                    "scale": scale,
                }))

        return blocks

    def _assign_y(self, blocks: List[Block]) -> List[Block]:
        """Y座標を順番に割り当てる"""
        y = PROG_TOP
        for b in blocks:
            b.y = y
            y += b.h
        return blocks


# ─── ヘルパー変換 ────────────────────────────────────────────────────────

def n_to_px(value: float, axis: str = "h") -> int:
    """正規化サイズ → プレビューピクセル数"""
    return int(value * (PREVIEW_H if axis == "h" else PREVIEW_W))


def n_to_pt(value: float, axis: str = "h") -> float:
    """正規化サイズ → PDFポイント数"""
    return value * (PDF_H if axis == "h" else PDF_W)
