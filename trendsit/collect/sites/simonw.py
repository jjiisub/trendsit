"""Simon Willison 날짜별 아카이브(/{yyyy}/{Mon}/{d}/): 글, 링크 글, 인용, 노트 조각."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urljoin

from lxml import etree

from .common import doc, text_of

BASE = "https://simonwillison.net"
_TIME = re.compile(r"(\d{1,2}):(\d{2})\s*(am|pm)", re.I)


def parse_day(html: str, day: date) -> list[dict[str, Any]]:
    """고유 주소(rel=bookmark)가 있는 조각만. 시각은 사이트 표기(UTC로 둠, 피드와 같은 기준)."""
    out = []
    for seg in doc(html).xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' segment ')]"):
        link = next(iter(seg.xpath(".//a[@rel='bookmark']/@href")), None)
        if not link:
            continue
        url = urljoin(BASE, link)
        title_el = next(iter(seg.xpath(".//h3//a | .//h2//a | .//p[contains(@class,'cite')]//a")), None)
        title = text_of(title_el) or url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
        times = [t for t in (text_of(a) for a in seg.xpath(".//p[contains(@class,'date-and-tags')]//a")) if _TIME.search(t)]
        published = None
        if times:
            h, m, ap = _TIME.search(times[0]).groups()
            hour = int(h) % 12 + (12 if ap.lower() == "pm" else 0)
            published = datetime(day.year, day.month, day.day, hour, int(m), tzinfo=UTC)
        out.append({"url": url, "title": title, "published": published,
                    "published_estimated": published is None,
                    "content_html": etree.tostring(seg, encoding="unicode")})
    return out
