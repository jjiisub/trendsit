"""AI타임스: 기간으로 거른 목록. 1페이지는 HTML(articleList.html), 2페이지부터는 AJAX JSON(ajaxArticlePaging.php)."""

from __future__ import annotations

import html as html_lib
import json
import re
from datetime import date, datetime
from typing import Any

from .common import KST, doc, text_of

ARTICLE = "https://www.aitimes.com/news/articleView.html?idxno={idxno}"
_MD_HM = re.compile(r"(\d{2})-(\d{2})\s+(\d{2}):(\d{2})")


def _from_md(text: str, since: date, until: date) -> datetime | None:
    """목록의 'MM-DD HH:MM'(연도 없음). 기간의 연도로 붙이고, 연말·연초에 걸치면 맞는 쪽을 고른다."""
    m = _MD_HM.search(text)
    if not m:
        return None
    mo, d, h, mi = map(int, m.groups())
    for year in sorted({since.year, until.year}, reverse=True):
        try:
            dt = datetime(year, mo, d, h, mi, tzinfo=KST)
        except ValueError:
            continue
        if since <= dt.date() <= until or year == since.year:
            return dt
    return None


def parse_list_html(text: str, since: date, until: date) -> list[dict[str, Any]]:
    out = []
    for li in doc(text).xpath("//section[@id='section-list']//li | //*[@id='section-list']//li"):
        a = next(iter(li.xpath(".//*[contains(@class,'altlist-subject')]//a | .//h2//a | .//h4//a")), None)
        if a is None or "idxno=" not in (a.get("href") or ""):
            continue
        idx = re.search(r"idxno=(\d+)", a.get("href")).group(1)
        info = " ".join(text_of(x) for x in li.xpath(".//*[contains(@class,'altlist-info-item')]"))
        out.append({"url": ARTICLE.format(idxno=idx), "title": text_of(a), "published": _from_md(info, since, until),
                    "published_estimated": False})
    return out


def parse_ajax(text: str) -> list[dict[str, Any]]:
    """2페이지부터. pub_date는 날짜만 있어 시각은 0시(추정 표시)."""
    data = json.loads(text)
    if data.get("result") != "success":
        raise ValueError(f"AJAX 응답 실패: {data.get('msg') or data.get('result')}")
    out = []
    for x in data.get("data") or []:
        pub = x.get("pub_date")
        published = datetime.fromisoformat(pub).replace(tzinfo=KST) if pub else None
        out.append({"url": ARTICLE.format(idxno=x["idxno"]), "title": html_lib.unescape(x.get("title") or ""),
                    "published": published, "published_estimated": True})
    return out
