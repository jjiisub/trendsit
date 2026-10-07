"""GeekNews(news.hada.io) 목록 페이지: 메인(점수순), 날짜별 목록(past?day=).

상세 페이지(topic?id=)는 요청하지 않는다(설계 결정 S1 Q1). 목록에서 제목, 원문 링크, 요약 앞부분, 점수, 댓글 수를 얻는다.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlsplit

from .common import doc, parse_iso, text_of

BASE = "https://news.hada.io/"


def is_own(url: str | None) -> bool:
    """원문 링크가 GeekNews 자신(Show GN, Ask GN 등 자기 글): 상대 주소이거나 호스트가 news.hada.io(하위 도메인 포함)."""
    if not url:
        return True
    host = (urlsplit(url).hostname or "").lower()
    return host == "" or host == "news.hada.io" or host.endswith(".news.hada.io")


def _int(text: str | None) -> int | None:
    m = re.search(r"\d+", text or "")
    return int(m.group()) if m else None


def parse_list(html: str) -> list[dict[str, Any]]:
    """목록의 토픽 행: topic_id, 토픽 URL, 제목, 원문 링크(자기 글이면 None), 요약 앞부분, 게시 시각, 점수, 댓글 수."""
    out = []
    for row in doc(html).xpath("//div[contains(@class,'topic_row')]"):
        tid = row.get("data-topic-state-id")
        a = next(iter(row.xpath(".//a[contains(@class,'topic-title-link')]")), None)
        if not tid or a is None:
            continue
        t = row.xpath(".//time/@datetime")
        desc = next(iter(row.xpath(".//div[contains(@class,'topicdesc')]")), None)
        points = next(iter(row.xpath(f".//span[@id='tp{tid}']")), None)
        comments = row.xpath(".//a[@data-topic-comment-count]/@data-topic-comment-count")
        origin = a.get("href")
        out.append({"topic_id": tid, "url": urljoin(BASE, f"topic?id={tid}"), "title": text_of(a),
                    "origin_url": None if is_own(origin) else urljoin(BASE, origin),
                    "published": parse_iso(t[0]) if t else None,
                    "desc": text_of(desc).rstrip(".…") or None,  # 요약 앞부분(약 100자, 잘림)
                    "points": _int(text_of(points)) if points is not None else None,
                    "comments": int(comments[0]) if comments else None})
    return out
