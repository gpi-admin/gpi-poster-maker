"""
Pillow ベースのポスタープレビュー描画エンジン

レイアウト構成（左→右）:
  左カラム   (0〜37%)  : 場所・日時・司会・対象・QR
  タイトル帯 (37〜50%) : 縦書き「第N回岐阜県小児科研修セミナー」（中央より少し左）
  右ストリップ(50〜62%): 「20XX年度」縦書き + 第N部ラベルボックス（動的高さ）
  プログラム (62〜100%): 参加費無料 + 各セクション内容
"""

from PIL import Image, ImageDraw
from pathlib import Path

from poster.models import PosterData
from poster.layout import (
    LayoutEngine,
    PREVIEW_W, PREVIEW_H,
    HEADER_TOP, HEADER_H, FOOTER_H,
    LEFT_W, PROG_X, PROG_W, TITLE_X, TITLE_W, SECT_X, SECT_W,
    LC_PAD_L, LC_PAD_R,
    PROG_PAD_L, PROG_PAD_R,
    PROG_TOP,
    BASHO_BW, BASHO_BH, BADGE_SM_H,
    FS_HEADER, FS_VENUE_BIG, FS_VENUE_SM,
    FS_DATE_LBL, FS_DATE_BIG, FS_TIME_LC,
    FS_MC_BADGE, FS_MC_AFF, FS_MC_NAME,
    FS_AUD, FS_QR_CAP, FS_FOOTER,
    FS_PROG_TIME, FS_PROG_BADGE, FS_PROG_TITLE,
    FS_PRESENTER, FS_PRES_NAME, FS_SANSHUUHI,
    FS_V_TITLE,
    SECTION_CONTENT_SCALES,
)
from poster.elements_pillow import (
    draw_header_bar, draw_footer_bar,
    draw_basho_badge, draw_venue_info, draw_address,
    draw_zoom_section, draw_date_time_left,
    draw_mc_section, draw_audience_section,
    draw_qr, draw_vertical_title,
    draw_year_label_strip, draw_section_label_box,
    draw_section_time, draw_sub_badge,
    draw_presenter,
    paste_illustration,
)
from poster.qr_generator import generate_qr
from themes.color_themes import get_theme, LIGHT_CREAM_BG
from utils.image_utils import make_background_layer
from utils.font_manager import ensure_fonts, get_pillow_font
from poster.text_utils import get_text_size, wrap_text_jp, draw_text_multiline

ASSETS_DIR = Path(__file__).parent.parent / "assets"


def render_poster(data: PosterData, scale: float = 1.0, transparent_bg: bool = False) -> Image.Image:
    """
    ポスターを PIL Image としてレンダリングして返す。
    scale=1.0: PREVIEW_W × PREVIEW_H  (794 × 1123 px)
    scale=0.5: 半分サイズ（高速プレビュー用）
    transparent_bg=True: ベース背景を透明で開始する（書き出し用）
    """
    ensure_fonts()
    theme = get_theme(data.theme_key,
                      getattr(data, "custom_accent_color", None),
                      getattr(data, "custom_accent_light", None))

    W = int(PREVIEW_W * scale)
    H = int(PREVIEW_H * scale)

    def pw(n):  return max(1, int(n * W))   # 正規化幅 → px
    def ph(n):  return max(1, int(n * H))   # 正規化高さ → px

    # ─── ベースキャンバス ────────────────────────────────────────────────
    if transparent_bg:
        canvas = Image.new("RGBA", (W, H), color=(0, 0, 0, 0))
    else:
        canvas = Image.new("RGB", (W, H), color=LIGHT_CREAM_BG)

    # ─── 背景イラスト（明示指定時のみ）───────────────────────────────────
    bg_path = getattr(data, "background_image_path", None)

    if bg_path and Path(bg_path).exists():
        try:
            bg_layer = make_background_layer(bg_path, W, H,
                                             opacity=getattr(data, "bg_opacity", 0.30))
            canvas.paste(bg_layer)
        except Exception as e:
            print(f"背景画像エラー: {e}")

    draw = ImageDraw.Draw(canvas)

    # ─── ヘッダー・フッター ──────────────────────────────────────────────
    header_top = ph(HEADER_TOP)   # 帯の上余白（背景が見える）
    header_h = ph(HEADER_H)
    header_bottom = header_top + header_h   # コンテンツ開始基準
    footer_h = ph(FOOTER_H)
    footer_y = H - footer_h

    draw_header_bar(canvas, draw, header_h, theme, y_top=header_top)
    draw_footer_bar(canvas, draw, footer_y, footer_h, data.contact_email, theme)

    # ─── 縦書きタイトル帯 ────────────────────────────────────────────────
    title_x  = pw(TITLE_X)
    title_w  = pw(TITLE_W)
    sect_x   = pw(SECT_X)
    sect_w   = pw(SECT_W)

    draw_vertical_title(
        canvas,
        f"第{data.session_num}回岐阜県小児科研修セミナー",
        title_x, header_bottom, footer_y, title_w,
        ph(FS_V_TITLE)
    )

    # ─── 右ストリップ: 年度テキスト（固定位置） ──────────────────────────
    prog_top_y = ph(PROG_TOP)
    _v_pad = max(12, (footer_y - header_bottom) // 65)
    draw_year_label_strip(
        draw,
        f"{data.year}年度",
        sect_x, header_bottom + _v_pad, prog_top_y - ph(0.005),
        sect_w
    )

    # ─── 左カラム ────────────────────────────────────────────────────────
    lc_x  = pw(LC_PAD_L)
    lc_w  = pw(LEFT_W) - pw(LC_PAD_L) - pw(LC_PAD_R)
    cur_y = header_bottom + ph(0.026)

    # 場所バッジ + 会場名（横並び）
    badge_w = pw(BASHO_BW)
    badge_h = ph(BASHO_BH)
    draw_basho_badge(draw, lc_x, cur_y, badge_w, badge_h)

    venue_x = lc_x + badge_w + pw(0.009)
    venue_w = pw(LEFT_W) - venue_x - pw(LC_PAD_R)
    venue_h = draw_venue_info(
        draw, venue_x, cur_y, venue_w,
        data.venue_building, data.venue_room,
        "", ph(FS_VENUE_BIG), ph(FS_VENUE_SM)
    )
    cur_y += max(badge_h, venue_h) + ph(0.005)

    # 住所（建物名と左端を揃える）
    addr_h = draw_address(draw, venue_x, cur_y, venue_w,
                           data.venue_address, ph(FS_VENUE_SM))
    cur_y += addr_h + ph(0.018)

    # Zoom セクション
    zoom_h = draw_zoom_section(
        canvas, draw, lc_x, cur_y, lc_w,
        ph(FS_VENUE_SM), data.zoom_note, theme
    )
    cur_y += zoom_h + ph(0.022)

    # 日付・時刻（大）
    date_h = draw_date_time_left(
        draw, lc_x, cur_y, lc_w,
        data.event_date, data.time_range,
        ph(FS_DATE_LBL), ph(FS_DATE_BIG), ph(FS_TIME_LC),
        theme
    )
    cur_y += date_h + ph(0.018)

    # 第1部・第2部と同じコンテンツスケールを司会・座長にも適用
    _mc_cs = SECTION_CONTENT_SCALES[0]
    _fs_mc_aff  = ph(FS_PRESENTER * _mc_cs)
    _fs_mc_name = ph(FS_PRES_NAME * _mc_cs)

    # 総合司会
    if data.mc:
        mc_h = draw_mc_section(
            draw, lc_x, cur_y, lc_w,
            "総合司会", data.mc, theme,
            ph(FS_MC_BADGE), _fs_mc_aff, _fs_mc_name
        )
        cur_y += mc_h + ph(0.012)

    # 特別講演座長
    if data.chair:
        chair_h = draw_mc_section(
            draw, lc_x, cur_y, lc_w,
            data.chair_label, data.chair, theme,
            ph(FS_MC_BADGE), _fs_mc_aff, _fs_mc_name
        )
        cur_y += chair_h + ph(0.012)

    # 対象
    aud_h = draw_audience_section(
        draw, lc_x, cur_y, lc_w,
        data.audience, ph(FS_AUD), theme
    )
    cur_y += aud_h + ph(0.010)

    # QR コード（左カラム下部）
    qr_caption1 = "事前登録はこちらから"
    qr_caption2 = "※現地参加の方も登録してください"
    font_cap = get_pillow_font("Regular", ph(FS_QR_CAP))
    fs_cap_bold = max(ph(FS_QR_CAP) + 1, int(ph(FS_QR_CAP) * 1.12))
    font_cap_bold = get_pillow_font("Bold", fs_cap_bold)
    _, cap_h = get_text_size(draw, "あ", font_cap)
    _, cap2_h = get_text_size(draw, "あ", font_cap_bold)
    cap_line_gap = int(cap_h * 0.3)
    total_cap_h = cap_h + cap2_h + cap_line_gap

    qr_bottom = footer_y - ph(0.020) - total_cap_h - ph(0.006)
    max_qr = qr_bottom - cur_y - ph(0.005)
    qr_size = max(ph(0.08), min(lc_w, max_qr))

    if qr_size > ph(0.06):
        qr_img = generate_qr(data.registration_url or "", size_px=qr_size)
        qr_x = lc_x + (lc_w - qr_size) // 2
        draw_qr(canvas, qr_img, qr_x, qr_bottom - qr_size, qr_size)
        # キャプション1行目
        cap_y = qr_bottom + ph(0.003)
        cap1_w, _ = get_text_size(draw, qr_caption1, font_cap)
        draw.text((lc_x + (lc_w - cap1_w) // 2, cap_y),
                   qr_caption1, fill=DARK_BROWN, font=font_cap)
        # キャプション2行目（太字）
        cap2_w, _ = get_text_size(draw, qr_caption2, font_cap_bold)
        draw.text((lc_x + (lc_w - cap2_w) // 2, cap_y + cap_h + cap_line_gap),
                   qr_caption2, fill=DARK_BROWN, font=font_cap_bold)

    # ─── プログラムエリア ─────────────────────────────────────────────────
    prog_x = pw(PROG_X) + pw(PROG_PAD_L)
    prog_w = pw(PROG_W) - pw(PROG_PAD_L) - pw(PROG_PAD_R)

    # 参加費無料（上部右寄せ、赤）
    font_free = get_pillow_font("Black", ph(FS_SANSHUUHI))
    free_tw, free_th = get_text_size(draw, "参加費無料", font_free)
    free_x = prog_x + prog_w - free_tw - pw(0.012)
    free_y = header_bottom + ph(0.018)
    draw.text((free_x, free_y), "参加費無料", fill=(220, 30, 30), font=font_free)

    # 動的レイアウト
    layout = LayoutEngine(data, render_scale=scale).compute()

    section_positions = []   # [(part_label, y_px)] for divider labels

    for block in layout:
        by = ph(block.y)
        sc = block.data.get("scale", 1.0)
        cs = block.data.get("content_scale", 1.0)   # セクション別スケール

        if block.kind == "section_time":
            draw_section_time(draw, prog_x, by,
                               block.data["text"],
                               int(ph(FS_PROG_TIME) * sc))
            # 第N部 ラベル位置を記録（次のコンテンツ群の中央 Y として後で設定）
            section_positions.append({
                "label": block.data.get("part_label", ""),
                "y_start": by,
            })

        elif block.kind == "sub_badge":
            bh = int(ph(BADGE_SM_H) * sc)
            draw_sub_badge(draw, prog_x, by, int(prog_w * 0.75), bh,
                            block.data["label"], theme)

        elif block.kind == "title":
            font_t = get_pillow_font("Bold", int(ph(FS_PROG_TITLE) * sc * cs))
            lines = block.data.get("lines") or wrap_text_jp(
                draw, block.data["text"], font_t, prog_w
            )
            draw_text_multiline(draw, lines, font_t, prog_x, by, DARK_BROWN, 1.35)

        elif block.kind == "affiliation":
            font_a = get_pillow_font("Regular", int(ph(FS_PRESENTER) * sc * cs))
            lines = block.data.get("lines") or wrap_text_jp(
                draw, block.data["text"], font_a, prog_w
            )
            draw_text_multiline(draw, lines, font_a, prog_x, by, DARK_BROWN, 1.25)

        elif block.kind == "name":
            draw_presenter(draw, prog_x, by, prog_w,
                            "", block.data["text"],
                            int(ph(FS_PRESENTER) * sc * cs),
                            int(ph(FS_PRES_NAME) * sc * cs))

    # ─── 右ストリップ: 第N部ラベルボックス ──────────────────────────────
    for i, pos in enumerate(section_positions):
        if i + 1 < len(section_positions):
            y_end = section_positions[i + 1]["y_start"]
        else:
            y_end = footer_y - ph(0.008)
        draw_section_label_box(
            canvas, sect_x, pos["y_start"], y_end,
            sect_w, pos["label"], theme
        )

    # ─── 装飾イラスト ────────────────────────────────────────────────────
    deco_imgs = getattr(data, "decorative_images", [])
    if deco_imgs:
        illust_size = int(lc_w * 0.65)
        positions = [
            (lc_x + int(lc_w * 0.0), int(H * 0.60)),
            (lc_x + int(lc_w * 0.35), int(H * 0.68)),
        ]
        for i, img_path in enumerate(deco_imgs[:2]):
            if Path(img_path).exists():
                px_pos = positions[i]
                paste_illustration(canvas, img_path,
                                    px_pos[0], px_pos[1], illust_size)

    return canvas


# ─── DARK_BROWN インポート ────────────────────────────────────────────────
from themes.color_themes import DARK_BROWN
