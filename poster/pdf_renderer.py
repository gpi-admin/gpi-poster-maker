"""
ReportLab ベクターPDF ポスター生成エンジン
- テキスト・図形がベクターとして出力される
- Adobe Illustrator で個別要素を編集可能
"""

import io
from pathlib import Path
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4

from poster.models import PosterData
from poster.layout import (
    LayoutEngine, Block,
    PDF_W, PDF_H,
    HEADER_H, FOOTER_H,
    LEFT_COL_X, LEFT_COL_W, DIVIDER_X, DIVIDER_W, RIGHT_COL_X,
    LC_MARGIN_X, LC_W,
    RC_MARGIN_X, RC_W,
    MARGIN_TOP, MARGIN_BOTTOM,
    TITLE_STRIP_X, TITLE_STRIP_W,
    DATE_AREA_Y, DATE_AREA_H,
    PROGRAM_TOP, PROGRAM_BOT,
    BASHO_BADGE_R,
    BADGE_LG_W, BADGE_LG_H, BADGE_SM_W, BADGE_SM_H,
    FS_HEADER, FS_DATE, FS_TIME, FS_TITLE,
    FS_BADGE_LG, FS_BADGE_SM, FS_SECTION_H, FS_PRESENTER,
    FS_VENUE, FS_AUDIENCE, FS_FOOTER, FS_MC,
)
from poster.elements_pdf import (
    pdf_header_bar, pdf_footer_bar, pdf_center_divider,
    pdf_basho_badge, pdf_venue_info, pdf_zoom_section,
    pdf_qr, pdf_audience_section,
    pdf_vertical_title, pdf_date_time,
    pdf_section_badge, pdf_sub_badge,
    pdf_content_title, pdf_presenter, pdf_mc_row,
    pdf_background_image, pdf_illustration,
)
from poster.qr_generator import generate_qr
from themes.color_themes import get_theme, LIGHT_CREAM_BG
from utils.font_manager import ensure_fonts, register_fonts_for_reportlab

ASSETS_DIR = Path(__file__).parent.parent / "assets"


def render_poster_pdf(data: PosterData) -> bytes:
    """
    ポスターを ReportLab でレンダリングし、PDF バイト列を返す。
    テキスト・楕円バッジはベクター → Illustrator で個別編集可能。
    """
    ensure_fonts()
    register_fonts_for_reportlab()
    theme = get_theme(data.theme_key, data.custom_accent_color, data.custom_accent_light)

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"GPI {data.year}年度 第{data.session_num}回ポスター")

    # ─── ポイント変換ヘルパー ──────────────────────────────────────────────
    def pt(n, axis="h"):
        return n * (PDF_H if axis == "h" else PDF_W)

    def rl_y(top_n):
        """上端正規化Y → ReportLab 下端基準 Y (pt)"""
        return PDF_H - top_n * PDF_H

    # ─── 背景 ─────────────────────────────────────────────────────────────
    # ポスター地色
    from reportlab.lib.colors import Color
    bg_color = Color(LIGHT_CREAM_BG[0]/255, LIGHT_CREAM_BG[1]/255, LIGHT_CREAM_BG[2]/255)
    c.setFillColor(bg_color)
    c.rect(0, 0, PDF_W, PDF_H, fill=1, stroke=0)

    # 背景イラスト
    bg_path = data.background_image_path
    if bg_path is None:
        bg_file = theme.get("bg_image")
        if bg_file:
            candidate = ASSETS_DIR / "illustrations" / "backgrounds" / bg_file
            if candidate.exists():
                bg_path = str(candidate)

    if bg_path and Path(bg_path).exists():
        pdf_background_image(c, bg_path, opacity=data.bg_opacity)

    # ─── ヘッダー ─────────────────────────────────────────────────────────
    header_h_pt = pt(HEADER_H)
    pdf_header_bar(c, header_h_pt, theme)

    # ─── フッター ─────────────────────────────────────────────────────────
    footer_h_pt = pt(FOOTER_H)
    pdf_footer_bar(c, footer_h_pt, data.contact_email)

    # ─── 中央縦バー ───────────────────────────────────────────────────────
    div_x_pt = pt(DIVIDER_X, "w")
    div_w_pt = max(2.5, pt(DIVIDER_W, "w"))
    header_rl_y = PDF_H - header_h_pt
    footer_rl_y = footer_h_pt
    pdf_center_divider(c, div_x_pt, header_rl_y, footer_rl_y, div_w_pt, theme)

    # ─── 左カラム ─────────────────────────────────────────────────────────
    lc_x = pt(LC_MARGIN_X, "w")
    lc_w = pt(LC_W, "w")

    # 場所バッジ
    badge_r = pt(BASHO_BADGE_R)
    badge_cx = lc_x + lc_w / 2
    badge_cy_top = HEADER_H + 0.018 + BASHO_BADGE_R * 2 + 0.008
    badge_cy_rl = PDF_H - (HEADER_H + 0.018 + BASHO_BADGE_R) * PDF_H
    pdf_basho_badge(c, badge_cx, badge_cy_rl, badge_r)

    cur_top_n = HEADER_H + 0.018 + BASHO_BADGE_R * 2 + 0.015

    # 会場情報
    venue_h = pdf_venue_info(
        c, lc_x, rl_y(cur_top_n), lc_w,
        data.venue_building, data.venue_room, data.venue_address,
        pt(FS_VENUE)
    )
    cur_top_n += venue_h / PDF_H + 0.022

    # Zoom セクション
    zoom_h = pdf_zoom_section(
        c, lc_x, rl_y(cur_top_n), lc_w,
        data.zoom_note, pt(FS_VENUE), theme
    )
    cur_top_n += zoom_h / PDF_H + 0.022

    # QR コード
    qr_size_pt = min(lc_w, pt(0.13))
    qr_x = lc_x + (lc_w - qr_size_pt) / 2
    qr_img = generate_qr(data.registration_url, size_px=200)
    pdf_qr(c, qr_img, qr_x, rl_y(cur_top_n), qr_size_pt)
    cur_top_n += qr_size_pt / PDF_H + 0.018

    # 対象
    pdf_audience_section(
        c, lc_x, rl_y(cur_top_n), lc_w,
        data.audience, pt(FS_AUDIENCE), theme
    )

    # ─── 右カラム ─────────────────────────────────────────────────────────
    rc_x = pt(RIGHT_COL_X, "w") + pt(RC_MARGIN_X, "w")
    rc_w = pt(RC_W, "w") - pt(TITLE_STRIP_W, "w")

    # 縦書きタイトル
    title_x = pt(TITLE_STRIP_X, "w")
    title_w = pt(TITLE_STRIP_W, "w")
    pdf_vertical_title(
        c,
        f"{data.year}年度",
        f"第{data.session_num}回岐阜県小児科研修セミナー",
        title_x,
        PDF_H - header_h_pt - pt(0.008),
        footer_h_pt + pt(0.008),
        title_w,
        pt(FS_TITLE)
    )

    # 日時エリア
    date_y = rl_y(HEADER_H + 0.018)
    pdf_date_time(
        c, rc_x, date_y, rc_w,
        data.event_date, data.time_range,
        pt(FS_DATE), pt(FS_TIME)
    )

    # ─── プログラムセクション ─────────────────────────────────────────────
    layout = LayoutEngine(data).compute()

    bw_lg = pt(BADGE_LG_W, "w")
    bh_lg = pt(BADGE_LG_H)
    bw_sm = pt(BADGE_SM_W, "w")
    bh_sm = pt(BADGE_SM_H)

    for block in layout:
        by_rl = rl_y(block.y)
        bh_pt = block.h * PDF_H
        sc = block.data.get("scale", 1.0)

        if block.kind == "section_badge":
            pdf_section_badge(c, rc_x, by_rl,
                               bw_lg * sc, bh_lg * sc,
                               block.data["label"], theme)

        elif block.kind == "sub_badge":
            pdf_sub_badge(c, rc_x, by_rl,
                           bw_sm * sc, bh_sm * sc,
                           block.data["label"], theme)

        elif block.kind == "title":
            pdf_content_title(c, rc_x, by_rl, rc_w,
                               block.data["text"],
                               pt(FS_SECTION_H) * sc)

        elif block.kind == "presenter":
            pdf_presenter(c, rc_x, by_rl, rc_w,
                           block.data["affiliation"],
                           block.data["name"],
                           pt(FS_PRESENTER) * sc)

        elif block.kind == "mc":
            pdf_mc_row(c, rc_x, by_rl, rc_w,
                        bw_lg * 0.75 * sc, bh_lg * sc,
                        block.data["label"], block.data["person"],
                        pt(FS_MC) * sc, theme)

    # ─── 装飾イラスト ─────────────────────────────────────────────────────
    lc_w_pt = pt(LC_W, "w")
    illust_positions = [
        (lc_x + lc_w_pt * 0.1, rl_y(0.68), lc_w_pt * 0.6),
        (lc_x + lc_w_pt * 0.4, rl_y(0.78), lc_w_pt * 0.5),
    ]
    for i, img_path in enumerate(data.decorative_images[:2]):
        if Path(img_path).exists() and i < len(illust_positions):
            px_, py_, sz_ = illust_positions[i]
            pdf_illustration(c, img_path, px_, py_, sz_)

    c.save()
    return buf.getvalue()
