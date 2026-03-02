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

from PIL import Image, ImageDraw
from reportlab.pdfbase import pdfmetrics

from poster.text_utils import get_text_size, wrap_text_jp
from utils.font_manager import get_pillow_font

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
#   左カラム  (0〜41.5%)  : 場所・日時・司会・対象・QR
#   タイトル帯(41.5〜52%) : 縦書き「第N回岐阜県小児科研修セミナー」
#   右ストリップ(52〜57%)  : 「2025年度」縦書き + 第N部ラベルボックス
#   プログラム(57〜100%)  : 参加費無料 + 各セクション内容
#
# ※ 縦バーは廃止。タイトル帯がその役割を担う。

# 左カラム: 場所・日時・司会・QR
LEFT_W  = 0.415   # 左カラム幅

# 縦書きメインタイトル帯（「第N回岐阜県小児科研修セミナー」）
# ポスター 41.5〜52.0% に配置
TITLE_X = 0.415   # メインタイトル帯左端 X（= 左カラム右端）※変更禁止
TITLE_W = 0.105   # メインタイトル帯幅

# 右ストリップ（「2025年度」+ 第N部ラベルボックス）
SECT_X  = TITLE_X + TITLE_W   # = 0.520
SECT_W  = 0.050              # ≈ 5%（細いストリップ）

# プログラムエリア（ポスター右側 57〜100%）
PROG_X  = SECT_X + SECT_W    # = 0.570
PROG_W  = 1.0 - PROG_X       # = 0.430

# ─── 左カラム内部マージン ────────────────────────────────────────────────

LC_PAD_L = 0.030   # 左パディング (canvas_width 比)
LC_PAD_R = 0.012   # 右パディング

# ─── プログラムエリア内部マージン ────────────────────────────────────────

PROG_PAD_L = 0.011
PROG_PAD_R = 0.020

# ─── プログラムエリア縦範囲 ──────────────────────────────────────────────

PROG_TOP = 0.230   # 動的レイアウト開始 Y (年度テキスト下に余白)
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
FS_MC_NAME     = 0.022   # 司会氏名
FS_AUD         = 0.016   # 対象
FS_QR_CAP      = 0.013   # QRキャプション
FS_FOOTER      = 0.016   # フッター文字
FOOTER_GROUP_SCALE = 1.18   # フッター「岐阜県小児科研修支援グループ」のみ拡大（基準フォントに対する倍率）

FS_PROG_TIME   = 0.018   # プログラム時刻 ("19:00 - 19:20")
FS_PROG_BADGE  = 0.017   # 小バッジ文字
FS_PROG_TITLE  = 0.024   # 発表タイトル
FS_PRESENTER   = 0.018   # 所属
FS_PRES_NAME   = 0.022   # 発表者氏名
FS_SANSHUUHI   = 0.030   # 参加費無料

FS_V_TITLE     = 0.090   # 縦書きタイトル文字 (正規化高さ)
FS_V_YEAR      = 0.022   # 縦書き年度文字

# ─── Zoomセクション（左カラム内） ───────────────────────────────────────

ZOOM_TEXT_SHIFT_RATIO   = 0.060   # 中央配置から左へ寄せる量（左カラム幅比）
ZOOM_ICON_SIZE_SCALE    = 1.35    # アイコンサイズ倍率（zoomテキスト高さ比）
ZOOM_ICON_RIGHT_PAD     = 0.040   # アイコン右余白（左カラム幅比）
ZOOM_TEXT_ICON_GAP      = 0.040   # テキストとアイコンの最小間隔（左カラム幅比）
ZOOM_ICON_LOGO_SCALE    = 0.72    # アイコン内ロゴのサイズ倍率
ZOOM_ICON_ROTATE_DEG    = 8.0     # アイコン回転角（反時計回り）

# ─── セクション別コンテンツスケール ──────────────────────────────────────
# 第1部・第2部: 0.90（やや小さく）, 第3部: 1.10（やや大きく）
SECTION_CONTENT_SCALES = [0.90, 0.90, 1.10]

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
    use_reportlab=True にすると ReportLab BIZ UDGothic メトリクスを使用（SVG レンダラー用）。
    """

    # ReportLab フォント名（SVGレンダラーと同じ）
    _RL_GOTHIC = "BIZUDGothic-Regular"
    _RL_GOTHIC_BOLD = "BIZUDGothic-Bold"
    _RL_MINCHO = "BIZUDMincho-Regular"

    def __init__(self, poster_data, render_scale: float = 1.0, use_reportlab: bool = False):
        self.data = poster_data
        self.render_scale = render_scale
        self.use_reportlab = use_reportlab
        if use_reportlab:
            self.canvas_w = PDF_W
            self.canvas_h = PDF_H
            self.prog_w_pt = (PROG_W - PROG_PAD_L - PROG_PAD_R) * PDF_W
        else:
            self.canvas_w = max(1, int(PREVIEW_W * render_scale))
            self.canvas_h = max(1, int(PREVIEW_H * render_scale))
            self.prog_w_px = max(1, int((PROG_W - PROG_PAD_L - PROG_PAD_R) * self.canvas_w))
        self._measure_draw = ImageDraw.Draw(Image.new("RGB", (1, 1), "white"))

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

                # タイトル（実測行高）
                title_lines, title_h = self._measure_wrapped_block(
                    text=item.title,
                    weight="Bold",
                    fs_norm=FS_PROG_TITLE,
                    scale=scale,
                    content_scale=cs,
                    line_spacing=1.35,
                )
                blocks.append(Block("title", 0, title_h, {
                    "text": item.title,
                    "scale": scale,
                    "content_scale": cs,
                    "lines": title_lines,
                }))

                # 所属（実測行高）
                aff_lines, aff_h = self._measure_wrapped_block(
                    text=item.affiliation,
                    weight="Regular",
                    fs_norm=FS_PRESENTER,
                    scale=scale,
                    content_scale=cs,
                    line_spacing=1.25,
                )
                blocks.append(Block("affiliation", 0, aff_h, {
                    "text": item.affiliation,
                    "scale": scale,
                    "content_scale": cs,
                    "lines": aff_lines,
                }))

                # 氏名
                name_h = self._measure_name_block(
                    name=item.presenter_name,
                    scale=scale,
                    content_scale=cs,
                )
                blocks.append(Block("name", 0, name_h, {
                    "text": item.presenter_name,
                    "scale": scale,
                    "content_scale": cs,
                }))

        return blocks

    def _font_px(self, fs_norm: float, scale: float, content_scale: float = 1.0) -> int:
        return max(1, int(fs_norm * self.canvas_h * scale * content_scale))

    # ── Pillow 計測（プレビュー用） ──────────────────────────────────────────

    def _measure_multiline_height(self, font, lines: List[str], line_spacing: float) -> int:
        if not lines:
            return 0
        _, ch = get_text_size(self._measure_draw, "あ", font)
        line_h = max(1, int(ch * line_spacing))
        return line_h * len(lines)

    def _measure_wrapped_block(
        self,
        text: str,
        weight: str,
        fs_norm: float,
        scale: float,
        content_scale: float,
        line_spacing: float,
    ) -> tuple[list[str], float]:
        if self.use_reportlab:
            return self._rl_measure_wrapped_block(text, weight, fs_norm, scale, content_scale, line_spacing)
        font = get_pillow_font(weight, self._font_px(fs_norm, scale, content_scale))
        lines = wrap_text_jp(self._measure_draw, text, font, self.prog_w_px)
        h_px = self._measure_multiline_height(font, lines, line_spacing)
        return lines, (h_px / self.canvas_h)

    def _measure_name_block(self, name: str, scale: float, content_scale: float) -> float:
        if self.use_reportlab:
            return self._rl_measure_name_block(name, scale, content_scale)
        if not name:
            return 0.0

        fs_name = self._font_px(FS_PRES_NAME, scale, content_scale)
        font_n = get_pillow_font("Bold", fs_name)

        if not name.endswith("先生"):
            fs_sensei = max(8, int(fs_name * 0.85))
            font_sensei = get_pillow_font("Regular", fs_sensei)
            _, nm_h = get_text_size(self._measure_draw, name, font_n)
            _, ss_h = get_text_size(self._measure_draw, " 先生", font_sensei)
            return int(max(nm_h, ss_h) * 1.25) / self.canvas_h

        lines = wrap_text_jp(self._measure_draw, name, font_n, self.prog_w_px)
        h_px = self._measure_multiline_height(font_n, lines, 1.25)
        return h_px / self.canvas_h

    # ── ReportLab 計測（SVG レンダラー用） ──────────────────────────────────

    @staticmethod
    def _rl_wrap(text: str, rl_font: str, size: float, max_w: float) -> list[str]:
        """ReportLab メトリクスによる日本語テキスト折り返し。"""
        lines: list[str] = []
        for para in text.split("\n"):
            cur = ""
            for ch in para:
                test = cur + ch
                if pdfmetrics.stringWidth(test, rl_font, size) > max_w and cur:
                    lines.append(cur)
                    cur = ch
                else:
                    cur = test
            if cur:
                lines.append(cur)
        return lines

    @staticmethod
    def _rl_ch(rl_font: str, size: float) -> float:
        """ReportLab フォントの文字高さ（ascent - descent）。"""
        asc, desc = pdfmetrics.getAscentDescent(rl_font, size)
        return asc - desc

    def _rl_measure_wrapped_block(
        self,
        text: str,
        weight: str,
        fs_norm: float,
        scale: float,
        content_scale: float,
        line_spacing: float,
    ) -> tuple[list[str], float]:
        size = fs_norm * self.canvas_h * scale * content_scale
        rl_font = self._RL_GOTHIC_BOLD if weight in ("Bold", "Black") else self._RL_GOTHIC
        lines = self._rl_wrap(text, rl_font, size, self.prog_w_pt)
        if not lines:
            return [], 0.0
        ch = self._rl_ch(rl_font, size)
        h = ch * line_spacing * len(lines)
        return lines, h / self.canvas_h

    def _rl_measure_name_block(self, name: str, scale: float, content_scale: float) -> float:
        if not name:
            return 0.0
        fs_name = FS_PRES_NAME * self.canvas_h * scale * content_scale
        fs_sensei = max(8.0, fs_name * 0.85)
        nm_h = self._rl_ch(self._RL_GOTHIC_BOLD, fs_name)
        ss_h = self._rl_ch(self._RL_GOTHIC, fs_sensei)
        line_h = max(nm_h, ss_h) * 1.25
        return line_h / self.canvas_h

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
