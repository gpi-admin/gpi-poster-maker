"""
GPI Poster Maker - Streamlit Web アプリ
7ステップのフォームでポスター情報を入力し、
プレビューと PDF/PNG ダウンロードを提供する。
"""

import streamlit as st
import io
import sys
from pathlib import Path
from datetime import date

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from poster.models import PosterData, Section, ContentItem, PersonInfo
from themes.color_themes import THEMES, get_theme, rgb_to_hex, hex_to_rgb
from utils.font_manager import ensure_fonts

# ─── ページ設定 ───────────────────────────────────────────────────────────

st.set_page_config(
    page_title="GPI Poster Maker",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── フォント初期化（初回のみDL） ─────────────────────────────────────────

@st.cache_resource
def init_fonts():
    msgs = []
    ensure_fonts(progress_callback=lambda m: msgs.append(m))
    return msgs


with st.spinner("フォントを確認中..."):
    font_msgs = init_fonts()
if font_msgs:
    for m in font_msgs:
        st.toast(m, icon="📥")

# ─── アセットパス ─────────────────────────────────────────────────────────

ASSETS_DIR = Path(__file__).parent / "assets"
BG_DIR = ASSETS_DIR / "illustrations" / "backgrounds"
DECO_DIR = ASSETS_DIR / "illustrations" / "decorative"

def list_assets(directory: Path, exts=(".png", ".jpg", ".jpeg")) -> list:
    if not directory.exists():
        return []
    return sorted([f.name for f in directory.iterdir() if f.suffix.lower() in exts])

# ─── ヘッダー ─────────────────────────────────────────────────────────────

st.title("🏥 GPI Poster Maker")
st.caption("岐阜県小児科研修セミナー ポスター自動生成システム")
st.markdown("---")

# ─── サイドバー：ステップナビゲーション ──────────────────────────────────

with st.sidebar:
    st.markdown("### 入力ステップ")
    step = st.radio(
        "ステップを選択",
        options=[
            "1. 基本情報・テーマ",
            "2. 開催日時・会場",
            "3. Zoom / QR コード",
            "4. 司会・座長",
            "5. 対象",
            "6. プログラム",
            "7. イラスト & 出力",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("過去ポスターを参考に必要事項を入力してください。")

# ─── セッションステート 初期化 ────────────────────────────────────────────

def init_state():
    defaults = {
        "year": date.today().year,
        "session_num": 1,
        "theme_key": "spring_pink",
        "custom_accent": "#D26E96",
        "event_date": "",
        "time_range": "19:00 - 20:30",
        "venue_room": "5F 小会議室1",
        "venue_building": "じゅうろくプラザ",
        "venue_address": "〒500-8856\n岐阜県岐阜市橋本町1丁目10-11",
        "venue_custom": False,
        "registration_url": "",
        "zoom_note": "&zoomミーティング",
        "has_mc": True,
        "mc_affiliation": "岐阜大学医学部附属病院 小児科",
        "mc_name": "",
        "has_chair": False,
        "chair_label": "特別講演 座長",
        "chair_affiliation": "",
        "chair_name": "",
        "audience": ["学生", "初期研修医", "後期研修医", "小児科医"],
        "extra_audience": "",
        "num_sections": 3,
        "sections": [],
        "bg_opacity": 35,
        "selected_bg": "",
        "selected_decos": [],
        "contact_email": "gpi.jimu@gmail.com",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # sections 初期化
    if not st.session_state["sections"]:
        st.session_state["sections"] = _default_sections()


def _default_sections():
    return [
        {
            "label": "第1部",
            "time_start": "19:00",
            "time_end": "19:20",
            "contents": [
                {"badge": "症例報告1（10分）", "title": "", "affiliation": "", "name": ""},
                {"badge": "症例報告2（10分）", "title": "", "affiliation": "", "name": ""},
            ],
        },
        {
            "label": "第2部",
            "time_start": "19:20",
            "time_end": "19:40",
            "contents": [
                {"badge": "国内留学日誌（15分）", "title": "", "affiliation": "", "name": ""},
            ],
        },
        {
            "label": "第3部（特別企画）",
            "time_start": "19:40",
            "time_end": "20:30",
            "contents": [
                {"badge": "特別講演（50分）", "title": "", "affiliation": "", "name": ""},
            ],
        },
    ]


init_state()


# ─── PosterData 構築ヘルパー ──────────────────────────────────────────────

def _build_poster_data(uploaded_bg=None, uploaded_decos_files=None) -> PosterData:
    ss = st.session_state

    # カスタムカラー
    custom_accent = None
    if ss["theme_key"] == "custom":
        custom_accent = hex_to_rgb(ss["custom_accent"])

    # 背景パス
    bg_path = None
    if uploaded_bg is not None:
        # 一時ファイルに保存
        tmp_path = ASSETS_DIR / "uploaded" / "bg_upload.png"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(uploaded_bg.read())
        bg_path = str(tmp_path)
    elif ss.get("selected_bg") and ss["selected_bg"] != "（テーマデフォルト）":
        bg_path = str(BG_DIR / ss["selected_bg"])

    # 装飾イラスト
    deco_paths = []
    for d in ss.get("selected_decos", [])[:2]:
        p = DECO_DIR / d
        if p.exists():
            deco_paths.append(str(p))
    if uploaded_decos_files:
        upload_dir = ASSETS_DIR / "uploaded"
        upload_dir.mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(uploaded_decos_files[:2]):
            p = upload_dir / f"deco_{i}.png"
            with open(p, "wb") as out:
                out.write(f.read())
            deco_paths.append(str(p))

    # 司会・座長
    mc = None
    if ss["has_mc"] and ss["mc_name"]:
        mc = PersonInfo(ss["mc_affiliation"], ss["mc_name"])
    chair = None
    if ss["has_chair"] and ss["chair_name"]:
        chair = PersonInfo(ss["chair_affiliation"], ss["chair_name"])

    # プログラムセクション
    sections = []
    for sec_data in ss["sections"][:ss["num_sections"]]:
        contents = []
        for item in sec_data["contents"]:
            if item.get("title") or item.get("name"):
                contents.append(ContentItem(
                    badge_label=item.get("badge", ""),
                    title=item.get("title", ""),
                    affiliation=item.get("affiliation", ""),
                    presenter_name=item.get("name", ""),
                ))
        sections.append(Section(
            label=sec_data["label"],
            time_start=sec_data["time_start"],
            time_end=sec_data["time_end"],
            contents=contents,
        ))

    return PosterData(
        year=ss["year"],
        session_num=ss["session_num"],
        theme_key=ss["theme_key"],
        event_date=ss["event_date"] or "未設定",
        time_range=ss["time_range"],
        venue_room=ss["venue_room"],
        venue_building=ss["venue_building"],
        venue_address=ss["venue_address"],
        registration_url=ss["registration_url"],
        zoom_note=ss["zoom_note"],
        mc=mc,
        chair=chair,
        chair_label=ss.get("chair_label", "特別講演 座長"),
        audience=ss["audience"],
        sections=sections,
        contact_email=ss["contact_email"],
        bg_opacity=ss["bg_opacity"] / 100.0,
        background_image_path=bg_path,
        decorative_images=deco_paths,
        custom_accent_color=custom_accent,
    )


# ─── ステップ 1: 基本情報・テーマ ────────────────────────────────────────

if step == "1. 基本情報・テーマ":
    st.header("Step 1　基本情報・テーマ")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state["year"] = st.number_input(
            "年度", min_value=2020, max_value=2040,
            value=st.session_state["year"]
        )
        st.session_state["session_num"] = st.number_input(
            "第○回", min_value=1, max_value=10,
            value=st.session_state["session_num"]
        )
        st.session_state["contact_email"] = st.text_input(
            "連絡先メールアドレス",
            value=st.session_state["contact_email"]
        )

    with col2:
        theme_options = {k: v["name"] for k, v in THEMES.items()}
        st.session_state["theme_key"] = st.selectbox(
            "カラーテーマ",
            options=list(theme_options.keys()),
            format_func=lambda k: theme_options[k],
            index=list(theme_options.keys()).index(st.session_state["theme_key"]),
        )
        if st.session_state["theme_key"] != "custom":
            theme = THEMES[st.session_state["theme_key"]]
            st.info(f"推奨開催時期: {theme['month_hint']}")
        else:
            st.session_state["custom_accent"] = st.color_picker(
                "アクセントカラーを選択",
                value=st.session_state["custom_accent"]
            )

    st.markdown("---")
    st.subheader("現在の設定")
    st.write(f"**{st.session_state['year']}年度　第{st.session_state['session_num']}回**　岐阜県小児科研修セミナー")

# ─── ステップ 2: 開催日時・会場 ──────────────────────────────────────────

elif step == "2. 開催日時・会場":
    st.header("Step 2　開催日時・会場")

    col1, col2 = st.columns(2)
    with col1:
        date_val = st.date_input("開催日", value=date.today())
        # 曜日を日本語で生成
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        wd = weekdays[date_val.weekday()]
        auto_date = f"{date_val.year}年 {date_val.month}月{date_val.day}日({wd})"
        st.caption(f"ポスター表示形式: **{auto_date}**")
        st.session_state["event_date"] = auto_date

        st.session_state["time_range"] = st.text_input(
            "時間帯",
            value=st.session_state["time_range"],
            help="例: 19:00 - 20:30"
        )

    with col2:
        st.subheader("会場")
        st.session_state["venue_building"] = st.text_input(
            "建物名", value=st.session_state["venue_building"]
        )
        st.session_state["venue_address"] = st.text_area(
            "住所", value=st.session_state["venue_address"],
            height=70, help="改行したい場合はEnterを押してください"
        )
        st.session_state["venue_room"] = st.text_input(
            "部屋", value=st.session_state["venue_room"],
            help="例: 5F 小会議室1"
        )

# ─── ステップ 3: Zoom / QR ───────────────────────────────────────────────

elif step == "3. Zoom / QR コード":
    st.header("Step 3　Zoom / QR コード")

    st.session_state["registration_url"] = st.text_input(
        "事前登録URL（QRコードが自動生成されます）",
        value=st.session_state["registration_url"],
        placeholder="https://us02web.zoom.us/meeting/register/..."
    )

    st.session_state["zoom_note"] = st.text_input(
        "Zoom 補足テキスト",
        value=st.session_state["zoom_note"],
        help="例: &zoomミーティング（ハンズオンもzoom配信します）"
    )

    if st.session_state["registration_url"]:
        st.subheader("QRコードプレビュー")
        from poster.qr_generator import generate_qr
        qr_img = generate_qr(st.session_state["registration_url"], size_px=200)
        st.image(qr_img, width=200, caption="登録用 QR コード")

# ─── ステップ 4: 司会・座長 ───────────────────────────────────────────────

elif step == "4. 司会・座長":
    st.header("Step 4　総合司会・座長")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("総合司会")
        st.session_state["has_mc"] = st.checkbox(
            "総合司会あり", value=st.session_state["has_mc"]
        )
        if st.session_state["has_mc"]:
            st.session_state["mc_affiliation"] = st.text_input(
                "所属", value=st.session_state["mc_affiliation"],
                key="mc_aff"
            )
            st.session_state["mc_name"] = st.text_input(
                "氏名", value=st.session_state["mc_name"],
                key="mc_nm"
            )

    with col2:
        st.subheader("座長")
        st.session_state["has_chair"] = st.checkbox(
            "座長あり", value=st.session_state["has_chair"]
        )
        if st.session_state["has_chair"]:
            st.session_state["chair_label"] = st.text_input(
                "バッジラベル", value=st.session_state["chair_label"],
                key="ch_lbl"
            )
            st.session_state["chair_affiliation"] = st.text_input(
                "所属", value=st.session_state["chair_affiliation"],
                key="ch_aff"
            )
            st.session_state["chair_name"] = st.text_input(
                "氏名", value=st.session_state["chair_name"],
                key="ch_nm"
            )

# ─── ステップ 5: 対象 ─────────────────────────────────────────────────────

elif step == "5. 対象":
    st.header("Step 5　対象")

    st.subheader("標準対象（チェックして選択）")
    default_items = ["学生", "初期研修医", "後期研修医", "小児科医",
                     "眼科医", "耳鼻科医", "産科医", "看護師", "薬剤師"]

    selected = []
    cols = st.columns(3)
    for i, item in enumerate(default_items):
        col = cols[i % 3]
        checked = item in st.session_state["audience"]
        if col.checkbox(item, value=checked, key=f"aud_{item}"):
            selected.append(item)

    st.subheader("追加対象（自由入力）")
    extra = st.text_input(
        "追加（カンマ区切り）",
        value=st.session_state["extra_audience"],
        placeholder="例: 小児外科医, 研修医"
    )
    st.session_state["extra_audience"] = extra
    if extra:
        for item in [s.strip() for s in extra.split(",") if s.strip()]:
            if item not in selected:
                selected.append(item)

    st.session_state["audience"] = selected if selected else ["学生", "初期研修医", "後期研修医", "小児科医"]
    st.info(f"対象: {' / '.join(st.session_state['audience'])}")

# ─── ステップ 6: プログラム ───────────────────────────────────────────────

elif step == "6. プログラム":
    st.header("Step 6　プログラム")

    num_sec = st.number_input(
        "部の数", min_value=1, max_value=4,
        value=st.session_state["num_sections"]
    )
    st.session_state["num_sections"] = num_sec

    # sections リストを num_sec に合わせる
    while len(st.session_state["sections"]) < num_sec:
        st.session_state["sections"].append({
            "label": f"第{len(st.session_state['sections']) + 1}部",
            "time_start": "19:00",
            "time_end": "19:30",
            "contents": [{"badge": "発表1", "title": "", "affiliation": "", "name": ""}],
        })

    for i in range(num_sec):
        sec = st.session_state["sections"][i]
        with st.expander(f"■ {sec['label']}", expanded=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                sec["label"] = st.text_input(
                    "部のラベル（バッジ表示）",
                    value=sec["label"],
                    key=f"sec_lbl_{i}",
                    help="例: 第1部 / 第3部（特別企画）"
                )
            with col2:
                sec["time_start"] = st.text_input(
                    "開始", value=sec["time_start"], key=f"ts_{i}"
                )
            with col3:
                sec["time_end"] = st.text_input(
                    "終了", value=sec["time_end"], key=f"te_{i}"
                )

            num_items = st.number_input(
                "発表数", min_value=1, max_value=5,
                value=len(sec["contents"]), key=f"ni_{i}"
            )
            while len(sec["contents"]) < num_items:
                sec["contents"].append({"badge": "発表", "title": "", "affiliation": "", "name": ""})

            for j in range(num_items):
                item = sec["contents"][j]
                st.markdown(f"**発表 {j + 1}**")
                c1, c2 = st.columns([1, 2])
                with c1:
                    item["badge"] = st.text_input(
                        "バッジラベル",
                        value=item["badge"],
                        key=f"badge_{i}_{j}",
                        help="例: 症例報告1（10分）/ 特別講演（50分）"
                    )
                with c2:
                    item["title"] = st.text_area(
                        "タイトル", value=item["title"],
                        key=f"title_{i}_{j}", height=70
                    )
                c3, c4 = st.columns(2)
                with c3:
                    item["affiliation"] = st.text_area(
                        "所属", value=item["affiliation"], key=f"aff_{i}_{j}",
                        height=70, help="改行したい場合はEnterを押してください"
                    )
                with c4:
                    item["name"] = st.text_input(
                        "発表者名", value=item["name"], key=f"name_{i}_{j}"
                    )
                st.markdown("---")

        st.session_state["sections"][i] = sec

# ─── ステップ 7: イラスト & 出力 ─────────────────────────────────────────

elif step == "7. イラスト & 出力":
    st.header("Step 7　イラスト & ポスター出力")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("背景イラスト")

        # テーマデフォルト vs カスタム
        preset_bgs = list_assets(BG_DIR)
        use_custom_bg = st.checkbox("カスタム背景画像をアップロードする")
        uploaded_bg = None
        if use_custom_bg:
            uploaded_bg = st.file_uploader(
                "背景画像 (PNG / JPG)", type=["png", "jpg", "jpeg"],
                key="bg_upload"
            )
        else:
            if preset_bgs:
                st.session_state["selected_bg"] = st.selectbox(
                    "プリセット背景を選択",
                    options=["（テーマデフォルト）"] + preset_bgs,
                    index=0,
                )
            else:
                st.info("assets/illustrations/backgrounds/ に画像を追加してください")
                st.session_state["selected_bg"] = ""

        st.session_state["bg_opacity"] = st.slider(
            "背景の不透明度 (%)", min_value=10, max_value=70,
            value=st.session_state["bg_opacity"], step=5
        )

        st.subheader("装飾イラスト（最大2つ）")
        preset_decos = list_assets(DECO_DIR)
        uploaded_decos = []
        if preset_decos:
            st.session_state["selected_decos"] = st.multiselect(
                "プリセットから選択",
                options=preset_decos,
                default=[d for d in st.session_state["selected_decos"] if d in preset_decos],
                max_selections=2,
            )
        else:
            st.info("assets/illustrations/decorative/ に画像を追加してください")

        uploaded_decos_files = st.file_uploader(
            "または画像をアップロード (PNG推奨, 透過対応)",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="deco_upload"
        )

    with col_right:
        st.subheader("プレビュー & ダウンロード")

        generate_btn = st.button("🎨 ポスターを生成する", type="primary", use_container_width=True)

        if generate_btn:
            poster_data = _build_poster_data(
                uploaded_bg, uploaded_decos_files
            )
            with st.spinner("ポスターを生成中..."):
                try:
                    from poster.preview_renderer import render_poster
                    img = render_poster(poster_data, scale=1.0)
                    st.session_state["preview_img"] = img
                    st.session_state["poster_data"] = poster_data
                    st.success("生成完了！")
                except Exception as e:
                    st.error(f"生成エラー: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        if "preview_img" in st.session_state:
            st.image(st.session_state["preview_img"], use_column_width=True)

            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                # PNG ダウンロード
                img_buf = io.BytesIO()
                st.session_state["preview_img"].save(img_buf, format="PNG")
                img_buf.seek(0)
                year = st.session_state["year"]
                num = st.session_state["session_num"]
                st.download_button(
                    label="📥 PNG をダウンロード",
                    data=img_buf,
                    file_name=f"GPI_{year}_{num:02d}.png",
                    mime="image/png",
                    use_container_width=True,
                )

            with dl_col2:
                # PDF ダウンロード（ベクター・Illustrator 編集可）
                if st.button("📄 PDF を生成 (Illustrator編集可)", use_container_width=True):
                    with st.spinner("ベクターPDFを生成中..."):
                        try:
                            from poster.pdf_renderer import render_poster_pdf
                            pdf_bytes = render_poster_pdf(st.session_state["poster_data"])
                            st.download_button(
                                label="📥 PDF をダウンロード",
                                data=pdf_bytes,
                                file_name=f"GPI_{year}_{num:02d}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )
                        except Exception as e:
                            st.error(f"PDF生成エラー: {e}")
                            import traceback
                            st.code(traceback.format_exc())
