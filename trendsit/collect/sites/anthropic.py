"""Anthropic 뉴스 목록(www.anthropic.com/news): 공식 RSS가 없고 커뮤니티 피드가 멈췄을 때만 쓰는 대체 수단."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

BASE = "https://www.anthropic.com"


def parse_list(html: str) -> list[dict[str, Any]]:
    """글 주소만(날짜는 글 페이지의 메타데이터에서). 목록은 최신 10건 안팎이고 페이지 넘김이 없다."""
    seen: dict[str, None] = {}
    for path in re.findall(r'href="(/news/[a-z0-9][a-z0-9-]*)"', html):
        seen.setdefault(urljoin(BASE, path), None)
    return [{"url": u, "title": None, "published": None} for u in seen]
