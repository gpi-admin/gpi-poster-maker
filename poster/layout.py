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

from poster.name_utils import parse_name_block
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
FS_PROG_SUBTITLE = 0.019 # 発表サブタイトル（タイトルの約 0.8 倍）

# ─── ユーザー指定の文字サイズ倍率・氏名描画 ──────────────────────────────

USER_FONT_SCALE_MIN = 0.5    # ユーザー指定倍率の下限（50%）
USER_FONT_SCALE_MAX = 1.5    # ユーザー指定倍率の上限（150%）
HONORIFIC_SCALE     = 0.85   # 敬称（先生・様など）の氏名本体に対するサイズ比
NAME_FIT_MIN        = 0.6    # 氏名が幅に収まらない場合の自動縮小の下限倍率


def clamp_user_scale(value) -> float:
    """ユーザー指定の文字サイズ倍率を有効範囲に丸める。不正値・None は 1.0。"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 1.0
    if v != v:  # NaN
        return 1.0
    return max(USER_FONT_SCALE_MIN, min(USER_FONT_SCALE_MAX, v))


HONORIFIC_MIN_SIZE      = 8.0    # 敬称フォントサイズの下限（pt / px）
NAME_LINE_ADVANCE_PROG  = 1.25   # プログラム発表者名の行送り（行高 = max(氏名高, 敬称高) × この値）
NAME_LINE_ADVANCE_MC    = 1.2    # 左カラム（総合司会・座長）氏名の行送り
NAME_MC_RIGHT_MARGIN    = 1.0    # 左カラム氏名の右マージン（fit 前の氏名サイズ × この値）
PROG_SUBTITLE_SPACING   = 1.35   # サブタイトルの行間
FS_SANSHUUHI   = 0.030   # 参加費無料

FS_V_TITLE     = 0.090   # 縦書きタイトル文字 (正規化高さ)
FS_V_YEAR      = 0.022   # 縦書き年度文字

# ─── Zoomセクション（左カラム内） ───────────────────────────────────────

ZOOM_TEXT_SHIFT_RATIO   = 0.060   # 中央配置から左へ寄せる量（左カラム幅比）
ZOOM_ICON_SIZE_SCALE    = 1.45    # アイコンサイズ倍率（zoomテキスト高さ比）
ZOOM_ICON_RIGHT_PAD     = 0.040   # アイコン右余白（左カラム幅比）
ZOOM_TEXT_ICON_GAP      = 0.040   # テキストとアイコンの最小間隔（左カラム幅比）
ZOOM_ICON_LOGO_SCALE    = 0.80    # アイコン内ロゴのサイズ倍率
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
    kind: str   # "section_time"|"sub_badge"|"title"|"subtitle"|"affiliation"|"name"|"gap"
    y: float    # トップ Y (正規化)
    h: float    # 高さ (正規化)
    data: dict = field(default_factory=dict)


# ─── 氏名ブロックの計測（ReportLab メトリクス） ─────────────────────────────
# LayoutEngine(use_reportlab=True) の高さ計測と svg_renderer の描画が
# 同じ関数を通ることで、数式のズレを防ぐ。

_RL_NAME_FONT = "BIZUDGothic-Bold"     # 氏名本体（計測用）
_RL_HONORIFIC_FONT = "BIZUDGothic-Regular"  # 敬称（計測用）


@dataclass
class NameBlockMetrics:
    """氏名ブロックの描画寸法（ReportLab 単位）。"""
    lines: list          # [[(text, is_honorific), ...], ...]
    fit: float           # 幅超過時の一律縮小率（収まれば 1.0）
    name_size: float     # 氏名本体のフォントサイズ（fit 適用後）
    hon_size: float      # 敬称のフォントサイズ（fit 適用後）
    name_asc: float
    name_h: float        # 氏名本体の文字高（ascent - descent）
    hon_asc: float
    hon_h: float
    line_h: float        # 1行の文字高 = max(name_h, hon_h)（行送りはこれ × advance）
    seg_widths: list     # [[w, ...], ...]  各セグメント幅
    line_widths: list    # [w, ...]          各行の合計幅


def honorific_size(name_size: float) -> float:
    """氏名本体サイズ → 敬称サイズ。"""
    return max(HONORIFIC_MIN_SIZE, name_size * HONORIFIC_SCALE)


def _rl_seg_widths(lines, name_size: float, hon_size: float) -> list:
    return [
        [
            pdfmetrics.stringWidth(
                text,
                _RL_HONORIFIC_FONT if is_hon else _RL_NAME_FONT,
                hon_size if is_hon else name_size,
            )
            for text, is_hon in line
        ]
        for line in lines
    ]


def rl_name_fit(lines, base_size: float, max_w: float) -> float:
    """最も幅の広い行が max_w を超える場合の一律縮小率（NAME_FIT_MIN 以上）。収まれば 1.0。"""
    if not lines:
        return 1.0
    widths = _rl_seg_widths(lines, base_size, honorific_size(base_size))
    widest = max(sum(ws) for ws in widths)
    if widest <= max_w or widest <= 0:
        return 1.0
    return max(NAME_FIT_MIN, max_w / widest)


def rl_name_metrics(lines, base_size: float, fit: float) -> NameBlockMetrics:
    """氏名ブロックの寸法を計算する（base_size は fit 適用前の氏名サイズ）。"""
    name_size = base_size * fit
    hon_size = honorific_size(name_size)
    n_asc, n_desc = pdfmetrics.getAscentDescent(_RL_NAME_FONT, name_size)
    h_asc, h_desc = pdfmetrics.getAscentDescent(_RL_HONORIFIC_FONT, hon_size)
    name_h = n_asc - n_desc
    hon_h = h_asc - h_desc
    seg_widths = _rl_seg_widths(lines, name_size, hon_size)
    return NameBlockMetrics(
        lines=lines,
        fit=fit,
        name_size=name_size,
        hon_size=hon_size,
        name_asc=n_asc,
        name_h=name_h,
        hon_asc=h_asc,
        hon_h=hon_h,
        line_h=max(name_h, hon_h),
        seg_widths=seg_widths,
        line_widths=[sum(ws) for ws in seg_widths],
    )


def rl_name_block_height(metrics: NameBlockMetrics, advance: float) -> float:
    """氏名ブロック全体の高さ（ReportLab 単位）。空なら 0。"""
    if not metrics.lines:
        return 0.0
    return len(metrics.lines) * (metrics.line_h * advance)


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

                # ユーザー指定倍率（旧データにも耐えるよう getattr。ここが唯一のクランプ箇所）
                us_title = clamp_user_scale(getattr(item, "title_scale", 1.0))
                us_sub = clamp_user_scale(getattr(item, "subtitle_scale", 1.0))
                us_aff = clamp_user_scale(getattr(item, "affiliation_scale", 1.0))
                us_name = clamp_user_scale(getattr(item, "name_scale", 1.0))

                # タイトル（実測行高）
                title_lines, title_h = self._measure_wrapped_block(
                    text=item.title or "",
                    weight="Bold",
                    fs_norm=FS_PROG_TITLE,
                    scale=scale,
                    content_scale=cs,
                    line_spacing=1.35,
                    user_scale=us_title,
                )
                blocks.append(Block("title", 0, title_h, {
                    "text": item.title,
                    "scale": scale,
                    "content_scale": cs,
                    "user_scale": us_title,
                    "lines": title_lines,
                }))

                # サブタイトル（任意。空なら高さ 0）
                subtitle = getattr(item, "subtitle", "") or ""
                sub_lines, sub_h = self._measure_wrapped_block(
                    text=subtitle,
                    weight="Regular",
                    fs_norm=FS_PROG_SUBTITLE,
                    scale=scale,
                    content_scale=cs,
                    line_spacing=PROG_SUBTITLE_SPACING,
                    user_scale=us_sub,
                )
                blocks.append(Block("subtitle", 0, sub_h, {
                    "text": subtitle,
                    "scale": scale,
                    "content_scale": cs,
                    "user_scale": us_sub,
                    "lines": sub_lines,
                }))

                # 所属（実測行高）
                aff_lines, aff_h = self._measure_wrapped_block(
                    text=item.affiliation or "",
                    weight="Regular",
                    fs_norm=FS_PRESENTER,
                    scale=scale,
                    content_scale=cs,
                    line_spacing=1.25,
                    user_scale=us_aff,
                )
                blocks.append(Block("affiliation", 0, aff_h, {
                    "text": item.affiliation,
                    "scale": scale,
                    "content_scale": cs,
                    "user_scale": us_aff,
                    "lines": aff_lines,
                }))

                # 氏名（入力どおり。改行で複数名・敬称は小さめ・幅超過時は一律縮小）
                name_lines = parse_name_block(item.presenter_name)
                name_h, fit = self._measure_name_block(
                    lines=name_lines,
                    scale=scale,
                    content_scale=cs,
                    user_scale=us_name,
                )
                blocks.append(Block("name", 0, name_h, {
                    "text": item.presenter_name,
                    "scale": scale,
                    "content_scale": cs,
                    "user_scale": us_name,
                    "lines": name_lines,
                    "fit": fit,
                }))

        return blocks

    def _font_px(
        self, fs_norm: float, scale: float, content_scale: float = 1.0, user_scale: float = 1.0
    ) -> int:
        return max(1, int(fs_norm * self.canvas_h * scale * content_scale * user_scale))

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
        user_scale: float = 1.0,
    ) -> tuple[list[str], float]:
        if not text:
            return [], 0.0
        if self.use_reportlab:
            return self._rl_measure_wrapped_block(
                text, weight, fs_norm, scale, content_scale, line_spacing, user_scale
            )
        font = get_pillow_font(weight, self._font_px(fs_norm, scale, content_scale, user_scale))
        lines = wrap_text_jp(self._measure_draw, text, font, self.prog_w_px)
        h_px = self._measure_multiline_height(font, lines, line_spacing)
        return lines, (h_px / self.canvas_h)

    def _measure_name_block(
        self, lines: list, scale: float, content_scale: float, user_scale: float = 1.0
    ) -> tuple[float, float]:
        """氏名ブロックの (正規化高さ, fit) を返す。lines は parse_name_block() の結果。"""
        if not lines:
            return 0.0, 1.0
        if self.use_reportlab:
            return self._rl_measure_name_block(lines, scale, content_scale, user_scale)

        # Pillow 計測（旧プレビュー用。ReportLab 経路と同じ規則を Pillow メトリクスで適用）
        draw = self._measure_draw
        base_px = FS_PRES_NAME * self.canvas_h * scale * content_scale * user_scale

        def fonts(px: float):
            fs_n = max(1, int(px))
            fs_h = max(int(HONORIFIC_MIN_SIZE), int(fs_n * HONORIFIC_SCALE))
            return get_pillow_font("Bold", fs_n), get_pillow_font("Regular", fs_h)

        font_n, font_h = fonts(base_px)
        widest = max(
            sum(get_text_size(draw, t, font_h if hon else font_n)[0] for t, hon in line)
            for line in lines
        )
        fit = 1.0
        if widest > self.prog_w_px and widest > 0:
            fit = max(NAME_FIT_MIN, self.prog_w_px / widest)
            font_n, font_h = fonts(base_px * fit)
        _, nm_h = get_text_size(draw, "あ", font_n)
        _, ss_h = get_text_size(draw, " 先生", font_h)
        line_px = int(max(nm_h, ss_h) * NAME_LINE_ADVANCE_PROG)
        return (line_px * len(lines)) / self.canvas_h, fit

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
        user_scale: float = 1.0,
    ) -> tuple[list[str], float]:
        size = fs_norm * self.canvas_h * scale * content_scale * user_scale
        rl_font = self._RL_GOTHIC_BOLD if weight in ("Bold", "Black") else self._RL_GOTHIC
        lines = self._rl_wrap(text, rl_font, size, self.prog_w_pt)
        if not lines:
            return [], 0.0
        ch = self._rl_ch(rl_font, size)
        h = ch * line_spacing * len(lines)
        return lines, h / self.canvas_h

    def _rl_measure_name_block(
        self, lines: list, scale: float, content_scale: float, user_scale: float = 1.0
    ) -> tuple[float, float]:
        if not lines:
            return 0.0, 1.0
        base = FS_PRES_NAME * self.canvas_h * scale * content_scale * user_scale
        fit = rl_name_fit(lines, base, self.prog_w_pt)
        metrics = rl_name_metrics(lines, base, fit)
        return rl_name_block_height(metrics, NAME_LINE_ADVANCE_PROG) / self.canvas_h, fit

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
