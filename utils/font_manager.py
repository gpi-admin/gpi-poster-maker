"""
フォント管理
macOS 組み込みの ヒラギノ角ゴシック を優先して使用する。
存在しない場合は Noto Sans JP をダウンロードする。
"""

import subprocess
import urllib.request
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

# プロジェクト内フォントディレクトリ（Noto DL先）
FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSansJP"

# BIZ UDGothic（リポジトリ内 TTF、Linux 含む全環境で利用可能）
_BIZ_FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts" / "BIZUDGothic"
BIZ_FONT_PATHS = {
    "Regular": _BIZ_FONT_DIR / "BIZUDGothic-Regular.ttf",
    "Bold":    _BIZ_FONT_DIR / "BIZUDGothic-Bold.ttf",
    "Black":   _BIZ_FONT_DIR / "BIZUDGothic-Bold.ttf",  # Black → Bold でフォールバック
}

# macOS ヒラギノ角ゴシック (システムフォント)
# W3 ≈ Regular, W6 ≈ Bold, W8/W9 ≈ Black
HIRAGINO_FONTS = {
    "Regular": "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "Bold":    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "Black":   "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
}
HIRAGINO_BLACK_FALLBACK = "/System/Library/Fonts/ヒラギノ角ゴシック W9.ttc"

# macOS ヒラギノ明朝 (システムフォント)
# TTC内のindex: 0 = W3(細め), 1 = W6(太め)
HIRAGINO_MINCHO_PATH = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"
HIRAGINO_MINCHO_INDEX = {"Regular": 0, "Bold": 1, "Black": 1}

# Noto Sans JP ダウンロード先（ヒラギノがない環境用）
NOTO_FONT_PATHS = {
    weight: FONT_DIR / f"NotoSansJP-{weight}.ttf"
    for weight in ["Regular", "Bold", "Black"]
}
# GitHub Releases からの直接ダウンロードURL
# (google/fonts リポジトリの最新の構造に対応)
NOTO_URLS = {
    "Regular": "https://github.com/notofonts/noto-cjk/releases/download/Sans2.004/07_NotoSansCJKjp.zip",
    # zip は大きいので個別ファイルURLを試す
}

# ダウンロード試行フラグ
_download_attempted = False
_force_bold_ctx: ContextVar[bool] = ContextVar("force_bold_fonts", default=True)


@contextmanager
def force_bold_fonts(enabled: bool = True):
    """コンテキスト内で太字モードの有効/無効を切り替える。"""
    token = _force_bold_ctx.set(bool(enabled))
    try:
        yield
    finally:
        _force_bold_ctx.reset(token)


def _resolve_weight(weight: str) -> str:
    """必要に応じてウェイトを太字側に寄せる。"""
    if _force_bold_ctx.get():
        if weight == "Regular":
            return "Bold"
        if weight == "Bold":
            return "Black"
    return weight


def _hiragino_path(weight: str) -> str | None:
    """ヒラギノフォントのパスを返す。存在しない場合はNone"""
    path = HIRAGINO_FONTS.get(weight, "")
    if Path(path).exists():
        return path
    # Black フォールバック
    if weight == "Black" and Path(HIRAGINO_BLACK_FALLBACK).exists():
        return HIRAGINO_BLACK_FALLBACK
    return None


def _is_valid_font(path: str) -> bool:
    """フォントファイルが有効かチェック"""
    p = Path(path)
    return p.exists() and p.stat().st_size > 1000


def get_font_path(weight: str = "Regular") -> str:
    """
    使用可能なフォントパスを返す。
    優先度: ヒラギノ(macOS) > ダウンロード済みNoto > デフォルト
    """
    weight = _resolve_weight(weight)

    # 1. macOS ヒラギノ
    hira = _hiragino_path(weight)
    if hira and _is_valid_font(hira):
        return hira

    # 2. ダウンロード済み Noto
    noto_path = NOTO_FONT_PATHS.get(weight)
    if noto_path and _is_valid_font(str(noto_path)):
        return str(noto_path)

    # 3. ダウンロードを試みる
    global _download_attempted
    if not _download_attempted:
        ensure_fonts()
        if noto_path and _is_valid_font(str(noto_path)):
            return str(noto_path)

    # 4. BIZ UDGothic（リポジトリ内 TTF、Linux 含む全環境で利用可能）
    biz_path = BIZ_FONT_PATHS.get(weight)
    if biz_path and _is_valid_font(str(biz_path)):
        return str(biz_path)

    # 5. weight を下げてフォールバック
    for fallback in ["Bold", "Regular"]:
        if fallback == weight:
            continue
        fb_hira = _hiragino_path(fallback)
        if fb_hira and _is_valid_font(fb_hira):
            return fb_hira

    return ""  # 最終フォールバック（Pillowのデフォルトを使用）


def ensure_fonts(progress_callback=None) -> bool:
    """
    フォントが利用可能か確認し、なければダウンロードする。
    macOS ヒラギノがあれば追加DLは不要。
    """
    global _download_attempted

    # macOS ヒラギノがすべて揃っていればOK
    if all(_hiragino_path(w) for w in ["Regular", "Bold"]):
        return True

    # Noto ダウンロード（一度だけ試みる）
    if _download_attempted:
        return False

    _download_attempted = True
    FONT_DIR.mkdir(parents=True, exist_ok=True)

    # Google Fonts の直接URLを複数試みる
    urls_to_try = [
        # GitHub経由のSubset OTF (小さい)
        ("Regular", "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/JP/NotoSansCJKjp-Regular.otf",
                    FONT_DIR / "NotoSansJP-Regular.ttf"),
        ("Bold",    "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/JP/NotoSansCJKjp-Bold.otf",
                    FONT_DIR / "NotoSansJP-Bold.ttf"),
        ("Black",   "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/JP/NotoSansCJKjp-Black.otf",
                    FONT_DIR / "NotoSansJP-Black.ttf"),
    ]

    all_ok = True
    for weight, url, dest in urls_to_try:
        if _is_valid_font(str(dest)):
            continue
        msg = f"Noto Sans JP ({weight}) をダウンロード中..."
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)
        try:
            urllib.request.urlretrieve(url, dest)
        except Exception as e:
            print(f"  DL失敗: {e}")
            if dest.exists():
                dest.unlink()
            all_ok = False

    return all_ok


_rl_fonts_registered = False


def register_fonts_for_reportlab():
    """
    ReportLab に日本語フォントを登録する。
    ReportLab 組み込みの CJK フォント (HeiseiKakuGo-W5) を優先使用。
    これにより PDF 内でテキストがベクターとして保持される。
    """
    global _rl_fonts_registered
    if _rl_fonts_registered:
        return

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        # 平成角ゴシック (ReportLab 組み込み CJK フォント)
        # Regular・Bold 相当として同一フォントを複数名で登録する
        cjk_font_name = "HeiseiKakuGo-W5"
        for alias in ["NotoSansJP", "NotoSansJP-Bold", "NotoSansJP-Black"]:
            try:
                pdfmetrics.getFont(alias)  # 登録済みならスキップ
            except Exception:
                try:
                    pdfmetrics.registerFont(UnicodeCIDFont(cjk_font_name, isVertical=False))
                    # エイリアスとして同じフォントを登録
                    pdfmetrics.registerFont(UnicodeCIDFont(cjk_font_name, isVertical=False))
                    # 直接名前をマップ
                    break
                except Exception:
                    pass

        # シンプル登録: "NotoSansJP" という名前で HeiseiKakuGo-W5 を登録
        try:
            pdfmetrics.getFont("NotoSansJP")
        except Exception:
            pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
            # 別名でも登録
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont as UCID
            for alias, cjk in [("NotoSansJP", "HeiseiKakuGo-W5"),
                                ("NotoSansJP-Bold", "HeiseiKakuGo-W5"),
                                ("NotoSansJP-Black", "HeiseiKakuGo-W5")]:
                try:
                    pdfmetrics.registerFont(UCID(cjk))
                    # RegistrationName として追加登録
                    pdfmetrics._fonts[alias] = pdfmetrics.getFont(cjk)
                except Exception:
                    pass

        _rl_fonts_registered = True
    except ImportError:
        pass


def get_pillow_font(weight: str = "Regular", size: int = 20):
    """Pillow ImageFont を返す（ゴシック体）"""
    from PIL import ImageFont
    path = get_font_path(weight)
    if path and _is_valid_font(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    # デフォルトフォント（英数字のみ）
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def get_pillow_font_mincho(weight: str = "Regular", size: int = 20):
    """Pillow ImageFont を返す（明朝体）。
    macOS ヒラギノ明朝 ProN を使用。利用不可の場合はゴシックにフォールバック。
    """
    from PIL import ImageFont
    weight = _resolve_weight(weight)
    if Path(HIRAGINO_MINCHO_PATH).exists():
        try:
            idx = HIRAGINO_MINCHO_INDEX.get(weight, 0)
            return ImageFont.truetype(HIRAGINO_MINCHO_PATH, size, index=idx)
        except Exception:
            pass
    # フォールバック: ゴシック体
    return get_pillow_font(weight, size)
