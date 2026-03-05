"""
GPI Poster Maker - Streamlit Web アプリ
7ステップのフォームでポスター情報を入力し、
プレビューと PDF/PNG ダウンロードを提供する。
"""

import streamlit as st
import io
import json
import sys
import tempfile
import uuid
import hmac
import os
from pathlib import Path
from datetime import date

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from poster.models import PosterData, Section, ContentItem, PersonInfo
from poster.email_text import build_announcement_email_text
from themes.color_themes import THEMES, get_theme, rgb_to_hex, hex_to_rgb
from utils.font_manager import ensure_fonts

# ─── ページ設定 ───────────────────────────────────────────────────────────

st.set_page_config(
    page_title="GPI Poster Maker",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _resolve_configured_password() -> str:
    """secrets からパスワードを解決（複数のキー/階層に対応）。"""
    password_keys = {
        "password", "passcode", "app_password", "gpi_password",
        "PASSWORD", "PASSCODE", "APP_PASSWORD", "GPI_PASSWORD",
    }
    candidates = []
    for key in password_keys:
        try:
            candidates.append(st.secrets.get(key))
        except Exception:
            continue

    def _collect_passwords(node):
        if not hasattr(node, "items"):
            return
        for k, v in node.items():
            if str(k) in password_keys and isinstance(v, str):
                candidates.append(v)
            if hasattr(v, "items"):
                _collect_passwords(v)

    try:
        _collect_passwords(st.secrets)
    except Exception:
        pass

    for value in candidates:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
    return ""


def _password_fingerprint(password: str) -> str:
    """パスワード比較用の固定フィンガープリントを返す。"""
    return hmac.new(b"gpi_poster_auth", password.encode("utf-8"), "sha256").hexdigest()


def _check_password() -> None:
    """パスワードが設定されている場合のみ、ログインを必須化する。"""
    configured_password = _resolve_configured_password()
    if not configured_password:
        # 明示的に環境変数で許可した場合のみロックを無効化
        if os.getenv("GPI_ALLOW_UNLOCKED", "").strip() == "1":
            return
        st.error("🔒 パスワードが未設定のため起動を停止しました。")
        st.caption("管理者は Streamlit Secrets に `password`（または `passcode`）を設定してください。")
        st.stop()
    current_fingerprint = _password_fingerprint(configured_password)

    if (
        st.session_state.get("_authenticated") is True
        and st.session_state.get("_authenticated_password_fp") == current_fingerprint
    ):
        return

    st.session_state["_authenticated"] = False
    st.markdown("### 🔒 ログイン")
    pwd = st.text_input("パスワードを入力してください", type="password", key="_pwd_input")
    if pwd and hmac.compare_digest(pwd.strip(), configured_password):
        st.session_state["_authenticated"] = True
        st.session_state["_authenticated_password_fp"] = current_fingerprint
        st.rerun()
    if pwd:
        st.error("パスワードが違います")
    st.stop()


_check_password()

# ─── フォント初期化（初回のみDL） ─────────────────────────────────────────

@st.cache_resource
def init_fonts():
    msgs = []
    ensure_fonts(progress_callback=lambda m: msgs.append(m))
    return msgs


def _hiragino_available() -> bool:
    return Path("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc").exists()




with st.spinner("フォントを確認中..."):
    font_msgs = init_fonts()
# トーストはセッション内で1度だけ表示（ステップ切り替え時に再表示しない）
if font_msgs and not st.session_state.get("_font_msgs_shown"):
    for m in font_msgs:
        st.toast(m, icon="📥")
    st.session_state["_font_msgs_shown"] = True

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

# ─── セーブ / ロード ヘルパー（サイドバーより前に定義が必要）────────────────

_SAVE_KEYS = [
    "year", "session_num", "theme_key", "custom_accent", "svg_font_key",
    "event_date", "event_date_iso", "time_range",
    "venue_room", "venue_building", "venue_address",
    "registration_url", "zoom_note",
    "has_mc", "mc_affiliation", "mc_name",
    "has_chair", "chair_label", "chair_affiliation", "chair_name",
    "audience", "extra_audience",
    "num_sections", "sections",
    "bg_opacity", "selected_bg", "selected_decos",
    "bg_custom_enabled", "deco_custom_enabled",
    "use_custom_bg", "use_custom_decos",
    "contact_email",
]


def _export_state() -> bytes:
    """セッションステートを JSON バイト列にシリアライズ"""
    payload = {"_version": "1.1"}
    for k in _SAVE_KEYS:
        payload[k] = st.session_state.get(k)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _import_state(data: bytes):
    """JSON バイト列をセッションステートに反映（不明キーは無視）"""
    try:
        payload = json.loads(data.decode("utf-8"))
    except Exception as e:
        st.sidebar.error(f"読み込みエラー: {e}")
        return
    from themes.color_themes import THEMES, _THEME_ALIASES
    for k in _SAVE_KEYS:
        if k not in payload:
            continue
        val = payload[k]
        if k == "theme_key":
            val = _THEME_ALIASES.get(val, val)
            if val not in THEMES:
                val = "spring_sakura"
        st.session_state[k] = val
    # 旧キー互換
    if "bg_custom_enabled" not in payload and "use_custom_bg" in payload:
        st.session_state["bg_custom_enabled"] = bool(payload.get("use_custom_bg"))
    if "deco_custom_enabled" not in payload and "use_custom_decos" in payload:
        st.session_state["deco_custom_enabled"] = bool(payload.get("use_custom_decos"))
    # event_date_iso から date ウィジェット用の raw 値を復元
    iso = st.session_state.get("event_date_iso", "")
    if iso:
        try:
            st.session_state["_event_date_raw"] = date.fromisoformat(iso)
        except Exception:
            pass


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

    # ─── セーブ / ロード ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("##### 💾 データの保存 / 読み込み")

    year_val = st.session_state.get("year", date.today().year)
    num_val  = st.session_state.get("session_num", 1)
    save_name = f"GPI_{year_val}_{num_val:02d}.json"
    st.download_button(
        label="📥 現在のデータを保存",
        data=_export_state(),
        file_name=save_name,
        mime="application/json",
        use_container_width=True,
        help="入力内容を JSON ファイルとして保存します",
    )

    _lc = st.session_state.get("_load_counter", 0)
    uploaded_json = st.file_uploader(
        "保存済みデータを読み込む",
        type=["json"],
        key=f"load_json_{_lc}",
        help="以前保存した JSON ファイルを選択するとフォームに反映されます",
    )
    if uploaded_json is not None:
        _import_state(uploaded_json.read())
        st.session_state["_load_counter"] = _lc + 1  # キーを変えてアップローダーをリセット
        st.success("✅ 読み込み完了！")
        st.rerun()

# ─── セッションステート 初期化 ────────────────────────────────────────────

def init_state():
    defaults = {
        "year": date.today().year,
        "session_num": 1,
        "theme_key": "spring_sakura",
        "custom_accent": "#D26E96",
        "svg_font_key": "hiragino",
        "event_date": "",
        "event_date_iso": "",
        "_event_date_raw": date.today(),
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
        "bg_custom_enabled": False,
        "deco_custom_enabled": False,
        "use_custom_bg": False,
        "use_custom_decos": False,
        "contact_email": "gpi.office.med@gmail.com",
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

def _get_session_upload_dir() -> Path:
    """ユーザーセッションごとの一時アップロードディレクトリを返す（複数ユーザー競合防止）。"""
    if "_session_upload_dir" not in st.session_state:
        d = Path(tempfile.gettempdir()) / "gpi_poster" / str(uuid.uuid4())
        d.mkdir(parents=True, exist_ok=True)
        st.session_state["_session_upload_dir"] = str(d)
    return Path(st.session_state["_session_upload_dir"])


def _build_poster_data(uploaded_bg=None, uploaded_decos_files=None) -> PosterData:
    ss = st.session_state
    bg_custom_enabled = ss.get("bg_custom_enabled", ss.get("use_custom_bg", False))
    deco_custom_enabled = ss.get("deco_custom_enabled", ss.get("use_custom_decos", False))

    # カスタムカラー
    custom_accent = None
    if ss["theme_key"] == "custom":
        custom_accent = hex_to_rgb(ss["custom_accent"])

    # 背景パス
    bg_path = None
    if uploaded_bg is not None:
        tmp_path = _get_session_upload_dir() / "bg_upload.png"
        tmp_path.write_bytes(uploaded_bg.getvalue())
        bg_path = str(tmp_path)
    elif bg_custom_enabled and ss.get("_uploaded_bg_path") and Path(ss["_uploaded_bg_path"]).exists():
        bg_path = ss["_uploaded_bg_path"]
    elif ss.get("selected_bg") and ss["selected_bg"] != "（背景なし）":
        candidate = BG_DIR / ss["selected_bg"]
        if candidate.exists():
            bg_path = str(candidate)

    # 装飾イラスト（背景と同様に: テンプレート or カスタムアップロード）
    deco_paths = []
    if deco_custom_enabled:
        if uploaded_decos_files:
            upload_dir = _get_session_upload_dir()
            f = uploaded_decos_files[0]
            p = upload_dir / "deco_0.png"
            p.write_bytes(f.getvalue())
            deco_paths.append(str(p))
        elif ss.get("_uploaded_deco_paths"):
            path = ss["_uploaded_deco_paths"][0]
            if Path(path).exists():
                deco_paths.append(path)
    else:
        for d in ss.get("selected_decos", [])[:1]:
            p = DECO_DIR / d
            if p.exists():
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
        theme_keys = list(theme_options.keys())
        current_key = st.session_state["theme_key"]
        # 旧キー（エイリアス）は THEMES に存在しないのでフォールバック
        if current_key not in theme_keys:
            current_key = "spring_sakura"
            st.session_state["theme_key"] = current_key
        st.session_state["theme_key"] = st.selectbox(
            "カラーテーマ",
            options=theme_keys,
            format_func=lambda k: theme_options[k],
            index=theme_keys.index(current_key),
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
        date_val = st.date_input(
            "開催日",
            value=st.session_state.get("_event_date_raw", date.today()),
        )
        st.session_state["_event_date_raw"] = date_val
        # 曜日を日本語で生成
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        wd = weekdays[date_val.weekday()]
        auto_date = f"{date_val.year}年 {date_val.month}月{date_val.day}日({wd})"
        st.caption(f"ポスター表示形式: **{auto_date}**")
        st.session_state["event_date"] = auto_date
        st.session_state["event_date_iso"] = date_val.isoformat()

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
    uploaded_bg = None
    uploaded_decos_files = None

    with col_left:
        st.subheader("背景イラスト")

        # カスタムアップロード:
        # ウィジェット用キーと永続キーを分離し、ステップ切替後も状態を保持する。
        prev_use_custom_bg = st.session_state.get(
            "bg_custom_enabled",
            st.session_state.get("use_custom_bg", False),
        )
        if "_ui_use_custom_bg" not in st.session_state:
            st.session_state["_ui_use_custom_bg"] = prev_use_custom_bg
        use_custom_bg = st.checkbox(
            "カスタム画像をアップロードする",
            key="_ui_use_custom_bg",
        )
        st.session_state["bg_custom_enabled"] = use_custom_bg
        st.session_state["use_custom_bg"] = use_custom_bg

        # 背景なし / プリセット / カスタム
        # カスタムON時は「プリセットより優先」の意図どおりプリセット選択UIを非表示にする。
        preset_bgs = list_assets(BG_DIR)
        if not use_custom_bg:
            if preset_bgs:
                opts = ["（背景なし）"] + preset_bgs
                cur = st.session_state.get("selected_bg", "（背景なし）")
                cur_idx = opts.index(cur) if cur in opts else 0
                st.session_state["selected_bg"] = st.selectbox(
                    "プリセット背景を選択",
                    options=opts,
                    index=cur_idx,
                )
            else:
                st.info("assets/illustrations/backgrounds/ に画像を追加してください")
                st.session_state["selected_bg"] = ""

        if prev_use_custom_bg and not use_custom_bg:
            # ユーザーが明示的にチェックを外した時のみ保存済みパスをクリア
            st.session_state.pop("_uploaded_bg_path", None)
            st.session_state.pop("_uploaded_bg_name", None)
        if use_custom_bg:
            uploaded_bg = st.file_uploader(
                "背景画像 (PNG / JPG)", type=["png", "jpg", "jpeg"],
                key="bg_upload",
            )
            if uploaded_bg is not None:
                # アップロード直後にテンポラリファイルへ書き出してパスを保存
                tmp = _get_session_upload_dir() / "bg_upload.png"
                tmp.write_bytes(uploaded_bg.getvalue())
                st.session_state["_uploaded_bg_path"] = str(tmp)
                st.session_state["_uploaded_bg_name"] = uploaded_bg.name
        saved_path = st.session_state.get("_uploaded_bg_path", "")
        if use_custom_bg and saved_path and Path(saved_path).exists():
            st.caption(f"選択済み: {st.session_state.get('_uploaded_bg_name', '画像')}")

        st.session_state["bg_opacity"] = st.slider(
            "背景の不透明度 (%)", min_value=10, max_value=70,
            value=st.session_state["bg_opacity"], step=5
        )

        st.subheader("装飾イラスト")
        prev_use_custom_decos = st.session_state.get(
            "deco_custom_enabled",
            st.session_state.get(
                "use_custom_decos",
                bool(st.session_state.get("_uploaded_deco_paths")),
            ),
        )
        if "_ui_use_custom_decos" not in st.session_state:
            st.session_state["_ui_use_custom_decos"] = prev_use_custom_decos
        use_custom_decos = st.checkbox(
            "装飾画像をアップロードする",
            key="_ui_use_custom_decos",
        )
        st.session_state["deco_custom_enabled"] = use_custom_decos
        st.session_state["use_custom_decos"] = use_custom_decos

        preset_decos = list_assets(DECO_DIR)
        if not use_custom_decos:
            if preset_decos:
                opts = ["（装飾なし）"] + preset_decos
                current = st.session_state.get("selected_decos", [])
                current_one = current[0] if current and current[0] in preset_decos else "（装飾なし）"
                selected_deco = st.selectbox(
                    "テンプレート装飾を選択",
                    options=opts,
                    index=opts.index(current_one),
                )
                st.session_state["selected_decos"] = [] if selected_deco == "（装飾なし）" else [selected_deco]
            else:
                st.info("assets/illustrations/decorative/ にテンプレート画像を追加してください")
                st.session_state["selected_decos"] = []

        if prev_use_custom_decos and not use_custom_decos:
            st.session_state.pop("_uploaded_deco_paths", None)
            st.session_state.pop("_uploaded_deco_names", None)
        if use_custom_decos:
            uploaded_deco = st.file_uploader(
                "画像をアップロード (PNG推奨, 透過対応)",
                type=["png", "jpg", "jpeg"],
                accept_multiple_files=False,
                key="deco_upload",
            )
            if uploaded_deco:
                # アップロード直後にテンポラリファイルへ書き出してパスを保存
                upload_dir = _get_session_upload_dir()
                p = upload_dir / "deco_0.png"
                p.write_bytes(uploaded_deco.getvalue())
                st.session_state["_uploaded_deco_paths"] = [str(p)]
                st.session_state["_uploaded_deco_names"] = [uploaded_deco.name]
                uploaded_decos_files = [uploaded_deco]
        saved_deco_paths = st.session_state.get("_uploaded_deco_paths", [])
        if use_custom_decos and saved_deco_paths and any(Path(p).exists() for p in saved_deco_paths):
            names = st.session_state.get("_uploaded_deco_names", [])
            st.caption(f"選択済み: {', '.join(names)}")

        st.subheader("SVGフォント")
        from poster.svg_renderer import SVG_FONT_PRESETS, SVG_FONT_DEFAULT
        _FONT_LABELS = {
            "hiragino": "ヒラギノ（macOS 専用）",
            "biz_ud":   "BIZ UDGothic（全環境対応・クラウド推奨）",
        }
        font_keys = list(SVG_FONT_PRESETS.keys())
        current_font = st.session_state.get("svg_font_key", SVG_FONT_DEFAULT)
        if current_font not in font_keys:
            current_font = SVG_FONT_DEFAULT
        st.session_state["svg_font_key"] = st.selectbox(
            "フォント",
            options=font_keys,
            format_func=lambda k: _FONT_LABELS.get(k, k),
            index=font_keys.index(current_font),
            help="Streamlit Cloud など macOS 以外の環境では「BIZ UDGothic」を選択してください",
        )
        if not _hiragino_available() and st.session_state.get("svg_font_key") == "hiragino":
            st.info("⚠️ この環境ではヒラギノが使用できないため、プレビュー・PNG・PDF の出力には BIZ UD フォント（ゴシック/明朝）が使用されます。SVG ダウンロードはヒラギノ指定のままになります。")

    with col_right:
        st.subheader("プレビュー & ダウンロード")

        generate_btn = st.button("🎨 ポスターを生成する", type="primary", use_container_width=True)

        if generate_btn:
            poster_data = _build_poster_data(uploaded_bg, uploaded_decos_files)
            with st.spinner("ポスターを生成中（Pillow / ReportLab）..."):
                try:
                    import importlib
                    from poster.preview_renderer import render_poster
                    from poster.pdf_renderer import render_poster_pdf
                    svg_mod = importlib.import_module("poster.svg_renderer")
                    svg_mod = importlib.reload(svg_mod)
                    user_font_key = st.session_state.get("svg_font_key", "hiragino")
                    # SVGダウンロード用（ユーザー選択フォント）
                    svg_str = svg_mod.render_poster_svg(
                        poster_data,
                        font_key=user_font_key,
                    )

                    # プレビューPNG（Pillow）
                    preview_img = render_poster(poster_data, scale=1.0)
                    preview_buf = io.BytesIO()
                    preview_img.save(preview_buf, format="PNG")
                    preview_png = preview_buf.getvalue()

                    # ダウンロード用高解像度PNG（約300dpi相当）
                    export_img = render_poster(poster_data, scale=3.0)
                    export_buf = io.BytesIO()
                    export_img.save(export_buf, format="PNG")
                    export_png = export_buf.getvalue()

                    # 印刷用PDF（ReportLab）
                    export_pdf = render_poster_pdf(poster_data)

                    st.session_state["preview_png"] = preview_png
                    st.session_state["export_png_bytes"] = export_png
                    st.session_state["export_pdf_bytes"] = export_pdf
                    st.session_state["svg_str"] = svg_str
                    st.session_state["poster_data"] = poster_data
                    st.session_state["email_text"] = build_announcement_email_text(poster_data)
                    st.success("生成完了！")
                except Exception as e:
                    st.error(f"生成エラー: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        if "preview_png" in st.session_state:
            st.image(st.session_state["preview_png"], use_column_width=True)

            year = st.session_state["year"]
            num = st.session_state["session_num"]
            dl_col1, dl_col2, dl_col3 = st.columns(3)
            with dl_col1:
                st.download_button(
                    label="📥 PNG",
                    data=st.session_state.get("export_png_bytes", b""),
                    file_name=f"GPI_{year}_{num:02d}.png",
                    mime="image/png",
                    use_container_width=True,
                )
            with dl_col2:
                st.download_button(
                    label="📥 PDF (印刷用)",
                    data=st.session_state.get("export_pdf_bytes", b""),
                    file_name=f"GPI_{year}_{num:02d}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            with dl_col3:
                st.download_button(
                    label="📥 SVG (Illustrator編集用)",
                    data=st.session_state.get("svg_str", "").encode("utf-8"),
                    file_name=f"GPI_{year}_{num:02d}.svg",
                    mime="image/svg+xml",
                    use_container_width=True,
                )

            email_text = st.session_state.get("email_text")
            if not email_text and st.session_state.get("poster_data"):
                email_text = build_announcement_email_text(st.session_state["poster_data"])
                st.session_state["email_text"] = email_text
            if email_text:
                st.markdown("---")
                st.subheader("メール周知文（下書き）")
                st.text_area(
                    "メール本文",
                    value=email_text,
                    height=420,
                )
                st.download_button(
                    label="📥 メール本文TXT",
                    data=email_text.encode("utf-8"),
                    file_name=f"GPI_{year}_{num:02d}_mail.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
