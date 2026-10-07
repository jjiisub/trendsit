"""GeekNews(news.hada.io): 토픽 페이지(한국어 요약 + 원문 링크), 날짜별 아카이브(past?day=)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from lxml import etree

from .common import block_text, doc, parse_iso, text_of

BASE = "https://news.hada.io/"


def is_browser_check(final_url: str, html: str | None) -> bool:
    """토픽 페이지 대신 브라우저 확인(Cloudflare Turnstile)이 나옴. 우회하지 않고 멈출 신호."""
    return "/topic_browser_check" in final_url or (html is not None and "id=\"browser-check\"" in html)


def is_own(url: str | None) -> bool:
    return not url or url.startswith(BASE) or url.startswith("topic?") or "news.hada.io" in url


def parse_topic(html: str) -> dict[str, Any]:
    """요약 본문(section#topic_contents), 원문 링크(제목 링크), 게시 시각. 댓글은 넣지 않는다."""
    d = doc(html)
    section = next(iter(d.xpath("//section[@id='topic_contents']")), None)
    title_a = next(iter(d.xpath("//div[contains(@class,'topictitle')]//a[contains(@class,'topic-title-link')]")), None)
    origin = title_a.get("href") if title_a is not None else None
    times = d.xpath("//div[contains(@class,'topicinfo')]//time/@datetime")
    return {
        "summary_text": block_text(section),
        "summary_html": etree.tostring(section, encoding="unicode") if section is not None else "",
        "origin_url": None if is_own(origin) else origin,
        "title": text_of(title_a),
        "published": parse_iso(times[0]) if times else None,
    }


def parse_list(html: str) -> list[dict[str, Any]]:
    """목록(past?day=, new)의 토픽 행: 토픽 URL, 제목, 원문 링크, 게시 시각."""
    out = []
    for row in doc(html).xpath("//div[contains(@class,'topic_row')]"):
        tid = row.get("data-topic-state-id")
        a = next(iter(row.xpath(".//a[contains(@class,'topic-title-link')]")), None)
        t = row.xpath(".//time/@datetime")
        desc = next(iter(row.xpath(".//div[contains(@class,'topicdesc')]")), None)
        if not tid or a is None:
            continue
        origin = a.get("href")
        out.append({"url": urljoin(BASE, f"topic?id={tid}"), "title": text_of(a),
                    "origin_url": None if is_own(origin) else origin,
                    "published": parse_iso(t[0]) if t else None,
                    "desc": text_of(desc).rstrip(".…") or None})  # 요약 앞부분(약 100자, 잘림)
    return out
