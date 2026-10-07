from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lxml import html as lxml_html

KST = timezone(timedelta(hours=9))


def doc(text: str) -> lxml_html.HtmlElement:
    return lxml_html.fromstring(text)


def text_of(el: lxml_html.HtmlElement | None) -> str:
    if el is None:
        return ""
    return " ".join(el.text_content().split())


def block_text(el: lxml_html.HtmlElement | None) -> str:
    """문단, 목록 항목을 줄로 나눠 텍스트로."""
    if el is None:
        return ""
    for br in el.iter("br"):
        br.tail = "\n" + (br.tail or "")
    lines = []
    for node in el.iter("p", "li", "h1", "h2", "h3", "h4", "blockquote", "pre"):
        t = " ".join(node.text_content().split())
        if t and (not lines or lines[-1] != t):
            lines.append(("- " if node.tag == "li" else "") + t)
    return "\n".join(lines) if lines else text_of(el)


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=KST)
