"""
Pillow による各ポスター要素の描画関数
実際のピクセル座標を受け取る（呼び出し元が正規化座標から変換済み）。
"""

from PIL import Image, ImageDraw, ImageFont
from poster.text_utils import (
    fit_font_in_ellipse, fit_font_in_box,
    wrap_text_jp, draw_text_multiline, draw_centered_text, get_text_size
)
from utils.font_manager import get_pillow_font, get_pillow_font_mincho
from themes.color_themes import DARK_BROWN, WHITE, LIGHT_CREAM_BG

# ─── 共通ユーティリティ ────────────────────────────────────────────────────

def _draw_pill(draw: ImageDraw.ImageDraw,
               x: int, y: int, w: int, h: int,
               fill: tuple, text: str = "", font=None,
               text_color: tuple = WHITE):
    """角丸長方形（ピル型）バッジを描画し、テキストを中央に配置する"""
    r = max(3, h // 3)
    try:
        draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill)
    except AttributeError:
        draw.rectangle([x, y, x + w, y + h], fill=fill)
    if text and font:
        draw_centered_text(draw, text, font, x + w // 2, y + h // 2, text_color)


# ─── ヘッダーバー ──────────────────────────────────────────────────────────

def _draw_text_spaced(draw: ImageDraw.ImageDraw, x: int, y: int,
                      text: str, font, fill, total_w: int):
    """テキストを指定幅いっぱいに文字間隔を均等調整して描画する。"""
    chars = list(text)
    # 各文字の幅を計測
    widths = [get_text_size(draw, ch, font)[0] for ch in chars]
    chars_w = sum(widths)
    if len(chars) <= 1:
        draw.text((x, y), text, fill=fill, font=font)
        return
    gap = (total_w - chars_w) / (len(chars) - 1)
    cx = x
    for ch, cw in zip(chars, widths):
        draw.text((int(cx), y), ch, fill=fill, font=font)
        cx += cw + gap


def draw_header_bar(canvas: Image.Image, draw: ImageDraw.ImageDraw,
                    h: int, theme: dict, y_top: int = 0):
    """上部 "Gifu Pediatric-residency Intensives" バー（テーマカラー背景）"""
    W = canvas.width
    bar_color = theme.get("title_bar", DARK_BROWN)
    draw.rectangle([0, y_top, W, y_top + h], fill=bar_color)
    font = get_pillow_font("Regular", max(10, int(h * 0.52)))
    text = "Gifu Pediatric-residency Intensives"
    pad = max(10, int(W * 0.03))
    _, th = get_text_size(draw, text, font)
    _draw_text_spaced(draw, pad, y_top + (h - th) // 2, text, font, WHITE, W - pad * 2)


# ─── フッターバー ──────────────────────────────────────────────────────────

def draw_footer_bar(canvas: Image.Image, draw: ImageDraw.ImageDraw,
                    y: int, h: int, email: str, theme: dict = None):
    """下部お問い合わせ先フッター（テーマカラー背景）"""
    W = canvas.width
    bar_color = theme.get("title_bar", DARK_BROWN) if theme else DARK_BROWN
    draw.rectangle([0, y, W, y + h], fill=bar_color)
    font = get_pillow_font("Regular", max(8, int(h * 0.40)))
    text = f"お問い合わせ先  岐阜県小児科研修支援グループ  Mail ▶  {email}"
    tw, th = get_text_size(draw, text, font)
    draw.text(((W - tw) // 2, y + (h - th) // 2), text, fill=WHITE, font=font)


# ─── 中央縦バー ────────────────────────────────────────────────────────────

def draw_center_divider(draw: ImageDraw.ImageDraw,
                         x: int, y_top: int, y_bot: int, w: int, theme: dict):
    """テーマカラーの縦バーを描画（第N部ラベルなし）"""
    draw.rectangle([x, y_top, x + w, y_bot], fill=theme["title_bar"])


def draw_part_label_on_divider(canvas: Image.Image,
                                div_x: int, div_w: int,
                                y_center: int, label: str, theme: dict):
    """
    縦バーに「第N部」を縦書きで描画。
    label 例: "第1部", "第2部（特別企画）"→ 最初の3〜4文字を表示
    """
    display = label[:4] if len(label) > 3 else label  # "第1部" 程度に収める
    font_size = max(8, div_w - 4)
    font = get_pillow_font("Bold", font_size)

    # 各文字を縦に積む
    char_h = font_size + 2
    total_h = char_h * len(display)
    start_y = y_center - total_h // 2

    for i, ch in enumerate(display):
        cy = start_y + i * char_h
        if cy < 0:
            continue
        tw, th = get_text_size(ImageDraw.Draw(canvas), ch, font)
        cx = div_x + (div_w - tw) // 2
        ImageDraw.Draw(canvas).text((cx, cy), ch, fill=WHITE, font=font)


# ─── 場所バッジ（角丸長方形） ──────────────────────────────────────────────

def draw_basho_badge(draw: ImageDraw.ImageDraw,
                      x: int, y: int, w: int, h: int):
    """
    「場所」と書かれたピル型バッジを描画する（ダークブラウン角丸長方形）。
    """
    BASHO_COLOR = (90, 60, 35)
    font = fit_font_in_box(draw, "場所", "Bold", int(w * 0.78), int(h * 0.78),
                            max_size=int(h * 0.75), min_size=8)
    _draw_pill(draw, x, y, w, h, BASHO_COLOR, "場所", font, WHITE)


# ─── 会場情報 ──────────────────────────────────────────────────────────────

def draw_venue_info(draw: ImageDraw.ImageDraw,
                    x: int, y: int, w: int,
                    building: str, room: str, address: str,
                    fs_big: int, fs_sm: int) -> int:
    """
    会場名・部屋・住所を描画。
    返値: 使用した高さ（px）
    building は建物名（大きめ）、room は部屋名、address は住所（小さめ）。
    """
    font_r = get_pillow_font("Regular", fs_sm)
    cur_y = y

    # 建物名（太字）- 手動改行なければ1行に収まるようフォントサイズ自動調整
    if "\n" in building:
        font_b = get_pillow_font("Bold", fs_big)
        lines = building.split("\n")
        h1 = draw_text_multiline(draw, lines, font_b, x, cur_y, DARK_BROWN, 1.25)
    else:
        font_b = fit_font_in_box(draw, building, "Bold", w, fs_big * 3,
                                  max_size=fs_big, min_size=8)
        _, bh = get_text_size(draw, building, font_b)
        draw.text((x, cur_y), building, fill=DARK_BROWN, font=font_b)
        h1 = int(bh * 1.25)
    cur_y += h1

    # 部屋名（右寄せ・やや大きめ）
    if room:
        font_room = get_pillow_font("Regular", max(8, int(fs_sm * 1.4)))
        lines = wrap_text_jp(draw, room, font_room, w)
        h2 = draw_text_multiline(draw, lines, font_room, x, cur_y, DARK_BROWN, 1.2,
                                  align="right", max_w=w)
        cur_y += h2

    return cur_y - y


def draw_address(draw: ImageDraw.ImageDraw,
                 x: int, y: int, w: int,
                 address: str, fs: int) -> int:
    """住所を描画。住所エリア下に区切り線を引く。返値: 使用した高さ"""
    font = get_pillow_font("Regular", fs)
    # 高解像度時のフォントヒンティング差を吸収するため判定幅を気持ち広めにする
    lines = wrap_text_jp(draw, address, font, w + max(2, fs // 3))
    h = draw_text_multiline(draw, lines, font, x, y, DARK_BROWN, 1.2)
    # 住所エリア下に横線（区切り線）
    line_y = y + h + max(3, int(fs * 0.4))
    draw.line([(x, line_y), (x + w, line_y)], fill=DARK_BROWN, width=1)
    return line_y + 2 - y


# ─── Zoom セクション ───────────────────────────────────────────────────────

def draw_zoom_section(draw: ImageDraw.ImageDraw,
                       x: int, y: int, w: int,
                       fs: int, zoom_note: str, theme: dict) -> int:
    """
    「ハイブリッド配信あり」を下線付きで描画。
    返値: 使用した高さ（px）
    """
    text = "ハイブリッド開催"
    font_size = max(10, int(fs * 1.8))
    font = get_pillow_font("Bold", font_size)
    indent = max(5, int(font_size * 0.6))
    tw, th = get_text_size(draw, text, font)
    draw.text((x + indent, y), text, fill=DARK_BROWN, font=font)
    # 下線
    line_y = y + th + 2
    draw.line([(x + indent, line_y), (x + indent + tw, line_y)], fill=DARK_BROWN, width=2)
    return line_y + 2 - y


# ─── 左カラム: 日付・時刻 ─────────────────────────────────────────────────

def _draw_date_oneline(draw: ImageDraw.ImageDraw,
                        x: int, y: int, w: int,
                        date_str: str, fs_big: int, fill: tuple) -> int:
    """
    "5月23日(金)" を1行で混合サイズ描画（折り返しなし）。
    数字: fs_big × 0.75（やや小さく）
    月・日・曜日カッコ: fs_big × 0.40（だいぶ小さく）
    各セグメントをベースライン下揃えで描画する。
    返値: 使用した高さ（px）
    """
    fs_num  = max(10, int(fs_big * 0.75))
    fs_kana = max(8,  int(fs_big * 0.50))
    font_num  = get_pillow_font("Black", fs_num)
    font_kana = get_pillow_font("Bold",  fs_kana)

    # 文字列をセグメントに分割（数字 vs 非数字）
    segments = []
    current = ""
    current_is_num = None
    for ch in date_str:
        is_num = ch.isdigit()
        if current_is_num is None:
            current_is_num = is_num
        if is_num != current_is_num:
            segments.append((current, current_is_num))
            current = ch
            current_is_num = is_num
        else:
            current += ch
    if current:
        segments.append((current, current_is_num))

    # 総幅・最大高さを計算（幅超過時はスケールダウン）
    def _measure(segs, fn, fk):
        tw = sum(get_text_size(draw, t, fn if n else fk)[0] for t, n in segs)
        th = max(get_text_size(draw, t, fn if n else fk)[1] for t, n in segs)
        return tw, th

    total_w, max_h = _measure(segments, font_num, font_kana)
    if total_w > w:
        ratio = w / total_w
        fs_num  = max(8, int(fs_num  * ratio))
        fs_kana = max(6, int(fs_kana * ratio))
        font_num  = get_pillow_font("Black", fs_num)
        font_kana = get_pillow_font("Bold",  fs_kana)
        total_w, max_h = _measure(segments, font_num, font_kana)

    # ベースライン下揃えで描画
    baseline = y + max_h
    cur_x = x
    for text, is_num in segments:
        font = font_num if is_num else font_kana
        tw, th = get_text_size(draw, text, font)
        draw.text((cur_x, baseline - th), text, fill=fill, font=font)
        cur_x += tw

    return max_h


def draw_date_time_left(draw: ImageDraw.ImageDraw,
                         x: int, y: int, w: int,
                         event_date: str,
                         time_range: str,
                         fs_lbl: int, fs_big: int, fs_time: int,
                         theme: dict) -> int:
    """
    左カラムの日付・時刻エリアを描画。
    "2025年 5月23日(金)" を「小ラベル + 大きな日付」に分けて描画する。
    返値: 使用した高さ
    """
    cur_y = y

    # event_date を "年" で分割: ["2025", "5月23日(金)"]
    if "年 " in event_date:
        parts = event_date.split("年 ", 1)
        year_label = parts[0] + "年"
        date_main  = parts[1]
    elif "年" in event_date:
        idx = event_date.index("年")
        year_label = event_date[:idx + 1]
        date_main  = event_date[idx + 1:].strip()
    else:
        year_label = ""
        date_main  = event_date

    # 年ラベル（Bold・やや大きめ）
    yr_indent = max(3, int(fs_lbl * 0.3))
    if year_label:
        font_yr = get_pillow_font("Bold", fs_lbl)
        draw.text((x + yr_indent, cur_y), year_label, fill=DARK_BROWN, font=font_yr)
        _, yr_h = get_text_size(draw, year_label, font_yr)
        cur_y += yr_h + int(fs_lbl * 0.2)

    # 大きな日付（数字大・月日曜小・1行）
    h_date = _draw_date_oneline(draw, x, cur_y, w, date_main, fs_big, DARK_BROWN)
    cur_y += h_date + int(fs_big * 0.18)

    # 時刻
    font_time = get_pillow_font("Bold", fs_time)
    lines = wrap_text_jp(draw, time_range, font_time, w - yr_indent)
    h_time = draw_text_multiline(draw, lines, font_time, x + yr_indent, cur_y, DARK_BROWN, 1.2)
    cur_y += h_time

    return cur_y - y


# ─── 左カラム: 司会・座長 ─────────────────────────────────────────────────

def draw_mc_section(draw: ImageDraw.ImageDraw,
                     x: int, y: int, w: int,
                     badge_label: str, person,
                     theme: dict,
                     fs_badge: int, fs_aff: int, fs_name: int) -> int:
    """
    司会/座長セクションを描画。
      [バッジ]
      所属
      氏名 先生
    返値: 使用した高さ
    """
    cur_y = y

    # バッジ（ピル型）
    badge_h = int(fs_badge * 2.0)
    # テキストに合わせた幅
    font_b = fit_font_in_box(draw, badge_label, "Regular",
                              int(w * 0.75), badge_h - 4,
                              max_size=fs_badge + 2, min_size=8)
    tw, _ = get_text_size(draw, badge_label, font_b)
    badge_w = tw + int(fs_badge * 2.0)
    badge_w = min(badge_w, w)
    _draw_pill(draw, x, cur_y, badge_w, badge_h, theme["accent"], badge_label, font_b, WHITE)
    cur_y += badge_h + int(fs_badge * 0.7)

    # 所属
    font_aff = get_pillow_font("Regular", fs_aff)
    lines = wrap_text_jp(draw, person.affiliation, font_aff, w)
    h_aff = draw_text_multiline(draw, lines, font_aff, x, cur_y, DARK_BROWN, 1.2)
    cur_y += h_aff + int(fs_aff * 0.5)

    # 氏名（太字）+ 先生（レギュラー・小さめ）を右寄せで組み合わせ描画
    font_nm = get_pillow_font("Bold", fs_name)
    fs_sensei = max(8, int(fs_name * 0.85))
    font_sensei = get_pillow_font("Regular", fs_sensei)
    right_margin = int(fs_name * 1.0)
    right_edge = x + w - right_margin
    nm_w, nm_h = get_text_size(draw, person.name, font_nm)
    ss_w, ss_h = get_text_size(draw, " 先生", font_sensei)
    line_h = max(nm_h, ss_h)
    draw.text((right_edge - nm_w - ss_w, cur_y + (line_h - nm_h)),
              person.name, fill=DARK_BROWN, font=font_nm)
    draw.text((right_edge - ss_w, cur_y + (line_h - ss_h)),
              " 先生", fill=DARK_BROWN, font=font_sensei)
    h_nm = int(line_h * 1.2)
    cur_y += h_nm

    return cur_y - y


# ─── 左カラム: 対象 ───────────────────────────────────────────────────────

def draw_audience_section(draw: ImageDraw.ImageDraw,
                           x: int, y: int, w: int,
                           audience: list, fs: int, theme: dict) -> int:
    """
    「対象」バッジ + 2カラム箇条書きを描画。
    返値: 使用した高さ
    """
    cur_y = y

    # 「対象」バッジ
    badge_h = int(fs * 1.9)
    font_lbl = fit_font_in_box(draw, "対象", "Regular",
                                int(w * 0.45), badge_h - 4,
                                max_size=fs + 2, min_size=8)
    tw, _ = get_text_size(draw, "対象", font_lbl)
    badge_w = tw + int(fs * 2.0)
    badge_w = min(badge_w, w)
    _draw_pill(draw, x, cur_y, badge_w, badge_h,
               theme["accent"], "対象", font_lbl, WHITE)
    cur_y += badge_h + int(fs * 0.7)

    # 箇条書き（2カラム）
    font_item = get_pillow_font("Regular", fs)
    col_w = w // 2 - 4
    col_items = [audience[i:i + 2] for i in range(0, len(audience), 2)]
    for pair in col_items:
        row_h = 0
        for ci, item in enumerate(pair):
            txt = "・" + item
            lines = wrap_text_jp(draw, txt, font_item, col_w)
            h = draw_text_multiline(draw, lines, font_item,
                                     x + ci * (col_w + 8), cur_y,
                                     DARK_BROWN, 1.2)
            row_h = max(row_h, h)
        cur_y += row_h + int(fs * 0.1)

    return cur_y - y


# ─── QR コード ─────────────────────────────────────────────────────────────

def draw_qr(canvas: Image.Image, qr_img: Image.Image,
             x: int, y: int, size: int):
    """QRコード画像をキャンバスに貼り付け"""
    qr_resized = qr_img.resize((size, size), Image.LANCZOS)
    canvas.paste(qr_resized, (x, y))


# ─── 縦書きタイトル帯 ──────────────────────────────────────────────────────

# 縦書き時に90°回転が必要な文字（長音符など）
_VERTICAL_ROTATE_CHARS = frozenset("ーｰ")


def _paste_rotated_char(canvas: Image.Image, char: str, font,
                         x: int, y: int, strip_w: int, ch_ref: int):
    """文字を90°時計回りに回転してキャンバスに貼り付ける（ー用）。
    anchor="mm" で正方形中心に文字を正確に中央配置してから回転する。
    """
    sq = max(strip_w, ch_ref) + 8
    tmp = Image.new("RGBA", (sq, sq), (0, 0, 0, 0))
    tmp_d = ImageDraw.Draw(tmp)
    # anchor="mm" = 水平・垂直ともに中央寄せ → フォントメトリクスに依存せず正確
    # stroke_width=1 で明朝体を程よく太く見せる
    tmp_d.text((sq // 2, sq // 2), char, fill=(*DARK_BROWN, 255),
               font=font, anchor="mm", stroke_width=1, stroke_fill=(*DARK_BROWN, 255))
    # 90°時計回りに回転（正方形なのでサイズ不変）
    tmp_rot = tmp.rotate(-90, expand=False)
    # strip と文字セル内で中央配置
    px = x + (strip_w - sq) // 2
    py = y + (ch_ref - sq) // 2
    base = canvas.convert("RGBA")
    base.paste(tmp_rot, (px, py), tmp_rot)
    if canvas.mode == "RGBA":
        canvas.paste(base)
    else:
        canvas.paste(base.convert("RGB"))


def draw_vertical_title(canvas: Image.Image,
                          main_title: str,
                          x: int, y_top: int, y_bot: int,
                          strip_w: int, fs_main: int):
    """
    縦書きメインタイトルを文字積み方式で描画する。
    各文字を縦幅いっぱいに均等配置し、帯内で横中央寄せ。
    「ー」などの長音符は90°時計回りに回転して縦書き表記に合わせる。
    """
    draw = ImageDraw.Draw(canvas)
    num_chars = len(main_title)
    avail_h = y_bot - y_top

    # 上下余白（上は小さめ、下は通常）
    v_pad_top = max(4, avail_h // 120)
    v_pad_bot = max(12, avail_h // 65)
    y_top  = y_top + v_pad_top
    avail_h = avail_h - v_pad_top - v_pad_bot

    # フォントサイズ: 帯幅の 88% を上限（従来65%から拡大）
    # 明朝体（ヒラギノ明朝）を使用
    font_size = min(fs_main, max(10, int(strip_w * 0.88)))
    font = get_pillow_font_mincho("Bold", font_size)
    _, ch = get_text_size(draw, "あ", font)

    # 文字間隔: 文字高さ + 8%（tight spacing）
    char_gap = max(2, int(ch * 0.08))
    char_step = ch + char_gap

    # 縦幅に収まらない場合は比例縮小
    if char_step * num_chars > avail_h:
        scale = avail_h / (char_step * num_chars)
        font_size = max(8, int(font_size * scale))
        font = get_pillow_font_mincho("Bold", font_size)
        _, ch = get_text_size(draw, "あ", font)
        char_gap = max(2, int(ch * 0.08))
        char_step = ch + char_gap

    # 縦中央に配置
    total_title_h = char_step * num_chars
    cur_y = y_top + (avail_h - total_title_h) // 2

    for char in main_title:
        if char in _VERTICAL_ROTATE_CHARS:
            # 「ー」は90°時計回りに回転して縦棒として描画
            _paste_rotated_char(canvas, char, font, x, cur_y, strip_w, char_step)
            draw = ImageDraw.Draw(canvas)   # canvas更新後にdrawを再取得
        else:
            cw, _ = get_text_size(draw, char, font)
            cx = x + (strip_w - cw) // 2
            # 文字セル内の縦中央に描画、stroke_width=1 で程よく太く
            char_y = cur_y + (char_step - ch) // 2
            draw.text((cx, char_y), char, fill=DARK_BROWN, font=font,
                      stroke_width=1, stroke_fill=DARK_BROWN)
        cur_y += char_step


# ─── 右ストリップ: 年度テキスト ────────────────────────────────────────────

def draw_year_label_strip(draw: ImageDraw.ImageDraw,
                            year_text: str,
                            x: int, y_top: int, y_bot: int,
                            strip_w: int):
    """
    右ストリップ上部に年度テキスト（例: "2025年度"）を文字積みで縦書き描画。
    y_top〜y_bot の範囲に文字を等間隔に配置する。
    """
    num_chars = max(1, len(year_text))
    avail_h = y_bot - y_top
    # 1文字あたりの均等ステップ
    char_step = avail_h // num_chars
    # フォントサイズ: ステップの 1.1 倍まで許容（文字間隔が狭くなるのは可）
    # strip_w を上限として strip に収める
    font_size = max(8, min(strip_w, int(char_step * 1.10)))
    font = get_pillow_font_mincho("Bold", font_size)
    _, ch = get_text_size(draw, "あ", font)

    cur_y = y_top
    for char in year_text:
        cw, _ = get_text_size(draw, char, font)
        cx = x + (strip_w - cw) // 2
        # char_step が ch より小さい場合は y_top 基準のまま（わずかな重なりを許容）
        char_y = cur_y + max(0, (char_step - ch) // 2)
        draw.text((cx, char_y), char, fill=DARK_BROWN, font=font,
                  stroke_width=1, stroke_fill=DARK_BROWN)
        cur_y += char_step


# ─── 右ストリップ: 第N部ラベルボックス ─────────────────────────────────────

def draw_section_label_box(canvas: Image.Image,
                             x: int, y_start: int, y_end: int,
                             strip_w: int, label: str, theme: dict,
                             pad: int = None):
    """
    角丸長方形の第N部ラベルボックスを右ストリップに描画。
    ラベル文字を縦積みで中央配置する。
    label が長い場合は "第X部" 部分のみ抽出して表示する。
    """
    # pad を strip_w に比例させて解像度に依存しないようにする（約23%）
    if pad is None:
        pad = max(2, int(strip_w * 0.23))
    box_h = y_end - y_start - pad * 2
    if box_h < 20:
        return

    draw = ImageDraw.Draw(canvas)
    bx = x + pad
    by = y_start + pad
    bw = strip_w - pad * 2

    color = theme.get("accent_light", theme["accent"])   # 薄い色
    r = max(4, bw // 4)
    try:
        draw.rounded_rectangle([bx, by, bx + bw, by + box_h], radius=r, fill=color)
    except AttributeError:
        draw.rectangle([bx, by, bx + bw, by + box_h], fill=color)

    # "第X部" 部分のみ抽出（長いラベルを短縮）
    display = label
    if "部" in label:
        idx = label.index("部")
        display = label[:idx + 1]

    # bw が小さくてもボックス内で読める最低限のサイズを確保
    fs = max(11, int(bw * 0.62))
    font = get_pillow_font("Bold", fs)
    _, ch = get_text_size(draw, "あ", font)
    char_step = ch + 2
    total_text_h = char_step * len(display)
    start_ty = by + max(4, (box_h - total_text_h) // 2)

    for char in display:
        cw, _ = get_text_size(draw, char, font)
        cx = bx + (bw - cw) // 2
        if start_ty + ch <= by + box_h:
            draw.text((cx, start_ty), char, fill=DARK_BROWN, font=font)   # 黒文字
        start_ty += char_step


# ─── プログラムエリア: 時刻ヘッダー ──────────────────────────────────────

def draw_section_time(draw: ImageDraw.ImageDraw,
                       x: int, y: int, time_text: str, fs: int):
    """セクション時刻（"19:00  -  19:20" など）を描画"""
    font = get_pillow_font("Bold", fs)
    draw.text((x, y), time_text, fill=DARK_BROWN, font=font)


# ─── プログラムエリア: 小バッジ ──────────────────────────────────────────

def draw_sub_badge(draw: ImageDraw.ImageDraw,
                    x: int, y: int, max_w: int, h: int,
                    label: str, theme: dict) -> int:
    """
    ピル型の小バッジ（症例報告N など）を描画。
    返値: 消費高さ
    """
    color = theme["accent"]   # 濃い色
    font = fit_font_in_box(draw, label, "Regular",
                            int(max_w * 0.92), int(h * 0.82),
                            max_size=int(h * 0.78), min_size=7)
    tw, _ = get_text_size(draw, label, font)
    badge_w = min(tw + int(h * 1.8), max_w)
    _draw_pill(draw, x, y, badge_w, h, color, label, font, WHITE)   # 白文字
    return h


# ─── プログラムエリア: タイトル ───────────────────────────────────────────

def draw_content_title(draw: ImageDraw.ImageDraw,
                        x: int, y: int, w: int,
                        title: str, fs: int) -> int:
    """発表タイトルを描画。返値: 消費高さ"""
    font = get_pillow_font("Bold", fs)
    lines = wrap_text_jp(draw, title, font, w)
    return draw_text_multiline(draw, lines, font, x, y, DARK_BROWN, 1.35)


# ─── プログラムエリア: 発表者 ────────────────────────────────────────────

def draw_presenter(draw: ImageDraw.ImageDraw,
                    x: int, y: int, w: int,
                    affiliation: str, name: str,
                    fs_aff: int, fs_name: int) -> int:
    """所属・氏名（氏名 先生）を描画。返値: 消費高さ"""
    font_a = get_pillow_font("Regular", fs_aff)
    font_n = get_pillow_font("Bold", fs_name)
    cur_y = y

    lines = wrap_text_jp(draw, affiliation, font_a, w)
    h1 = draw_text_multiline(draw, lines, font_a, x, cur_y, DARK_BROWN, 1.25,
                              align="right", max_w=w)
    cur_y += h1

    # 氏名（太字）+ 先生（レギュラー・小さめ）を右寄せで組み合わせ描画
    if name and not name.endswith("先生"):
        fs_sensei = max(8, int(fs_name * 0.85))
        font_sensei = get_pillow_font("Regular", fs_sensei)
        nm_w, nm_h = get_text_size(draw, name, font_n)
        ss_w, ss_h = get_text_size(draw, " 先生", font_sensei)
        line_h = max(nm_h, ss_h)
        draw.text((x + w - nm_w - ss_w, cur_y + (line_h - nm_h)),
                  name, fill=DARK_BROWN, font=font_n)
        draw.text((x + w - ss_w, cur_y + (line_h - ss_h)),
                  " 先生", fill=DARK_BROWN, font=font_sensei)
        h2 = int(line_h * 1.25)
    else:
        lines = wrap_text_jp(draw, name, font_n, w)
        h2 = draw_text_multiline(draw, lines, font_n, x, cur_y, DARK_BROWN, 1.25,
                                  align="right", max_w=w)
    cur_y += h2

    return cur_y - y


# ─── 装飾イラスト ──────────────────────────────────────────────────────────

def paste_illustration(canvas: Image.Image, img_path: str,
                         x: int, y: int, max_size: int):
    """装飾イラスト（PNG透過対応）をキャンバスに貼り付け"""
    try:
        illust = Image.open(img_path).convert("RGBA")
        illust.thumbnail((max_size, max_size), Image.LANCZOS)
        base = canvas.convert("RGBA")
        tmp = Image.new("RGBA", base.size, (0, 0, 0, 0))
        tmp.paste(illust, (x, y), illust)
        result = Image.alpha_composite(base, tmp)
        if canvas.mode == "RGBA":
            canvas.paste(result)
        else:
            canvas.paste(result.convert("RGB"))
    except Exception as e:
        print(f"イラスト読み込みエラー: {img_path} - {e}")
