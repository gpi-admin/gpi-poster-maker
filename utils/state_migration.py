"""
保存データ（JSON）の旧バージョン互換処理。

streamlit に依存しない純 Python モジュール。

バージョン履歴:
- 1.1 以前: 描画時に氏名へ自動で「先生」を付けていた。
- 1.2 以降: 氏名は敬称込みの自由入力（自動付与なし）。
"""

import copy

CURRENT_VERSION = "1.2"
_SUFFIX = "先生"


def _version_tuple(value):
    """バージョン値を (major, minor) に変換。壊れた値・None は None（旧扱い）。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        parts = str(value).strip().split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 and parts[1] != "" else 0
        return (major, minor)
    except Exception:
        return None


def _is_legacy(payload: dict) -> bool:
    if "_version" not in payload:
        return True
    ver = _version_tuple(payload.get("_version"))
    if ver is None:
        return True
    return ver < _version_tuple(CURRENT_VERSION)


def _add_sensei(text):
    """複数行の氏名の各非空行に、末尾が「先生」でなければ " 先生" を付ける。"""
    if not isinstance(text, str) or not text:
        return text
    out = []
    for line in text.split("\n"):
        stripped = line.rstrip()
        if stripped.strip() and not stripped.endswith(_SUFFIX):
            out.append(f"{stripped} {_SUFFIX}")
        else:
            out.append(line)
    return "\n".join(out)


def migrate_saved_state(payload: dict) -> dict:
    """旧バージョンの保存データを現行仕様に変換して返す（入力は変更しない）。

    _version が無い / 1.2 未満 / 壊れている場合のみ、司会・座長・各発表の氏名に
    「 先生」を付与する（旧版は描画時に自動付与していたため、同じ見た目を保つ）。
    1.2 以上はそのままコピーを返す。
    """
    if not isinstance(payload, dict):
        return payload
    result = copy.deepcopy(payload)
    if not _is_legacy(result):
        return result

    for key in ("mc_name", "chair_name"):
        if key in result:
            result[key] = _add_sensei(result[key])

    sections = result.get("sections")
    if isinstance(sections, list):
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            contents = sec.get("contents")
            if not isinstance(contents, list):
                continue
            for item in contents:
                if isinstance(item, dict) and "name" in item:
                    item["name"] = _add_sensei(item["name"])
    return result
