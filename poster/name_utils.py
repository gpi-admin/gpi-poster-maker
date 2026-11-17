"""
氏名文字列の解析ユーティリティ（純 Python。PIL / reportlab に依存しない）

- 氏名は敬称込みの自由入力。自動で「先生」は付けない。
- 改行で複数名を入力できる（1行 = 1名）。
- 敬称（先生・様・氏・さん）は描画時に小さめのサイズで描くため、セグメントに分ける。
"""

import re

HONORIFICS = ("先生", "様", "氏", "さん")

# 敬称と認識する条件:
#   直前に半角/全角スペースが1つ以上あり、直後が行末・スペース・区切り文字のもの。
#   （「山田太郎先生」のようにスペースなしで続く場合は敬称扱いしない）
_HONORIFIC_DELIMS = " 　、,，・/／）)"
_HONORIFIC_RE = re.compile(
    r"[ 　]+(" + "|".join(re.escape(h) for h in HONORIFICS) + r")"
    r"(?=$|[" + re.escape(_HONORIFIC_DELIMS) + r"])"
)


def split_name_lines(name) -> list[str]:
    """氏名文字列を改行で分割し、各行を strip して空行を除いたリストを返す。"""
    if not name:
        return []
    lines = []
    for raw in str(name).splitlines():
        line = raw.strip()
        if line:
            lines.append(line)
    return lines


def split_honorific_segments(line: str) -> list[tuple[str, bool]]:
    """1行の氏名を (テキスト, 敬称か) のセグメント列に分ける。

    敬称セグメントのテキストは直前の空白を半角スペース1個に正規化した " 先生" の形。
    例: "山田 太郎 先生、鈴木 花子 先生"
        → [("山田 太郎", False), (" 先生", True), ("、鈴木 花子", False), (" 先生", True)]
    """
    if not line:
        return []
    segments: list[tuple[str, bool]] = []
    pos = 0
    for m in _HONORIFIC_RE.finditer(line):
        body = line[pos:m.start()]
        if body:
            segments.append((body, False))
        segments.append((" " + m.group(1), True))
        pos = m.end()
    rest = line[pos:]
    if rest:
        segments.append((rest, False))
    return segments


def parse_name_block(name) -> list[list[tuple[str, bool]]]:
    """氏名文字列 → 行ごとのセグメント列のリスト。"""
    return [split_honorific_segments(line) for line in split_name_lines(name)]
