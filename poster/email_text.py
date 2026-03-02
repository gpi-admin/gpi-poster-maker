"""
メール周知文生成ユーティリティ
ポスター入力データ（PosterData）から、案内メール本文の下書きを生成する。
"""

from poster.models import PosterData, PersonInfo, ContentItem


def _clean_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _with_sensei(name: str) -> str:
    n = _clean_text(name)
    if not n:
        return ""
    if n.endswith("先生"):
        return n
    return f"{n} 先生"


def _format_person(person: PersonInfo | None) -> str:
    if person is None:
        return ""
    aff = _clean_text(person.affiliation)
    name = _with_sensei(person.name)
    if aff and name:
        return f"{aff}　{name}"
    return aff or name


def build_announcement_email_text(data: PosterData) -> str:
    """ポスター情報をもとに、メール配信用の周知文テキストを生成する。"""
    lines: list[str] = []
    lines.append("岐阜県内で小児科プログラム研修に参加頂いている先生方（卒業生も含み、お送りしています）")
    lines.append("")
    lines.append("お世話になっております。")
    lines.append(
        f"{data.year}年度 第{data.session_num}回岐阜県小児科研修セミナー"
        "・事前参加登録のご案内です。"
    )
    if data.registration_url:
        lines.append("ご参加頂ける方は、以下より事前参加登録をお願いします。")
        lines.append("")
        lines.append(data.registration_url)
        lines.append("")
    else:
        lines.append("参加登録URLが確定次第、改めてご案内します。")
        lines.append("")

    lines.append(f"{data.year}年度第{data.session_num}回岐阜県小児科研修セミナー")
    lines.append(f"日時：{data.event_date}　{data.time_range}")
    lines.append(f"場所：{_clean_text(data.venue_building)} {_clean_text(data.venue_room)}")
    lines.append(_clean_text(data.venue_address))
    lines.append("")

    if data.mc:
        lines.append(f"総合司会　{_format_person(data.mc)}")

    if data.chair:
        chair_label = _clean_text(data.chair_label) or "座長"
        lines.append(f"{chair_label}　{_format_person(data.chair)}")
    if data.mc or data.chair:
        lines.append("")

    for section in data.sections:
        label = _clean_text(section.label)
        lines.append(f"{label}　{_clean_text(section.time_start)} - {_clean_text(section.time_end)}")
        for item in section.contents:
            badge = _clean_text(item.badge_label)
            title = _clean_text(item.title)
            if badge:
                lines.append(badge)
            if title:
                lines.append(f"　{title}")
            if not badge and not title:
                lines.append("発表")
            presenter_line = _format_person(
                PersonInfo(
                    affiliation=item.affiliation,
                    name=item.presenter_name,
                )
            )
            if presenter_line:
                lines.append(f"　{presenter_line}")
        lines.append("")

    if data.registration_url:
        lines.append("＊（オンライン・現地問わず）参加希望の方は、以下より事前登録してください。")
        lines.append(data.registration_url)
        lines.append("")
        lines.append("また懇親会の参加登録もこちらからしていますので、現地参加の方も事前参加登録をお願いします。")
        lines.append("")
    lines.append("皆様のご参加をお待ちしています。")
    if data.contact_email:
        lines.append(f"お問い合わせ先：{_clean_text(data.contact_email)}")

    return "\n".join(lines).strip() + "\n"
