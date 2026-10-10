"""웹 도구(글 분석가): fetch_page, read_more. URL은 safe_fetch로만(SSRF 방어, robots, 도메인 간격, HTTP 캐시).

자원: state.ctx.resources["fetcher"], ["link_kinds"], ["fetched_pages"](url → 본문 전체. read_more와 enforce가 씀).
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..collect.links import normalize_url as norm_url  # artifacts_text를 여기서 import하면 합치기 순서가 꼬임
from .registry import ToolOutput, ToolRejected, tool

HEAD_CHARS = 3000
MAX_LINKS = 40
_HEAD = re.compile(r"<head[^>]*>(.*?)</head>", re.S)


def resources(state: Any) -> dict[str, Any]:
    ctx = getattr(state, "ctx", None)
    res = ctx.resources if ctx is not None else state.extras
    if "fetcher" not in res:
        from ..collect.fetch import Fetcher
        from ..core.config import ROOT

        res["fetcher"] = Fetcher(ROOT / "data" / "http_cache")
    if "link_kinds" not in res:
        from ..core import config

        res["link_kinds"] = config.load("link_kinds.yaml")
    res.setdefault("fetched_pages", {})
    return res


def remember(state: Any, url: str, text: str, depth: int | None = None) -> None:
    """가져온 문서 본문(enforce가 인용 대조에 씀)과 코드가 센 깊이."""
    from ..core.artifacts_text import page_key

    res = resources(state)
    res["fetched_pages"][page_key(url)] = text
    if depth is not None:
        res.setdefault("page_depth", {})[page_key(url)] = depth


_REF = re.compile(r'<ref target="([^"]+)">(.*?)</ref>', re.S)


def page_links(xml: str, base: str) -> list[dict[str, str]]:
    """본문 링크 전부(같은 사이트 포함: 공식 블로그 → 같은 도메인 논문·문서). http/https만, 자기 자신·조각 제외."""
    from urllib.parse import urljoin, urlsplit

    out, seen = [], {norm_url(base)}
    for href, anchor in _REF.findall(xml):
        url = urljoin(base, href.strip())
        if urlsplit(url).scheme not in ("http", "https"):
            continue
        key = norm_url(url)
        if key in seen:
            continue
        seen.add(key)
        out.append({"url": url, "anchor": re.sub(r"<[^>]+>", "", anchor).strip()})
    return out


class FetchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(description="열 페이지 URL(지금까지 읽은 문서의 링크 목록에 있던 것)")
    parent: str | None = Field(description="이 URL이 링크로 나온 문서의 URL. 원래 글의 링크면 원래 글 URL")

    @field_validator("url", "parent")
    @classmethod
    def _norm(cls, v: str | None) -> str | None:
        return norm_url(v) if v else v


class ReadMoreArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doc: str = Field(description="이미 fetch_page로 연 문서 URL")
    part: int = Field(ge=2, description="몇 번째 조각(3,000자 단위, 첫 조각은 fetch_page 결과)")


def extract(html: str, url: str) -> tuple[str, str | None, str | None, list[str], list[dict[str, str]]]:
    """(본문, 제목, 날짜, 소제목, 링크[url, anchor]). trafilatura로 본문, XML에서 링크와 소제목."""
    import trafilatura

    xml = trafilatura.extract(html, url=url, output_format="xml", include_links=True, include_comments=False,
                              favor_recall=True) or ""
    text = trafilatura.extract(html, url=url, include_comments=False, favor_recall=True) or ""
    meta = trafilatura.extract_metadata(html)
    heads = [re.sub(r"<[^>]+>", "", h).strip() for h in _HEAD.findall(xml)]
    links = page_links(xml, url)
    return text, (meta.title if meta else None), (meta.date if meta else None), [h for h in heads if h][:20], links


@tool(FetchArgs, depth_target="url")
def fetch_page(args: FetchArgs, state: Any) -> ToolOutput:
    """웹 페이지를 열어 최종 URL, 제목, 날짜, 본문 앞 3,000자, 소제목, 종류가 표시된 링크 목록을 돌려준다.
    언제 쓰나: 원래 글이나 이미 연 페이지의 링크 중 원본(논문, 공식 문서·블로그, 보도자료)일 가능성이 높은 것을 열 때.
    언제 쓰지 않나: 링크 목록에 없던 URL을 추측해서(parent 없이는 원래 글 외에 열 수 없음), 같은 페이지를 다시.
    인자 예: {"url": "https://openai.com/index/...", "parent": "https://news.hada.io/topic?id=123"}"""
    from ..collect.links import classify

    res = resources(state)
    r = res["fetcher"].fetch(args.url, kind="page")
    if not r.ok or not r.text:
        raise ToolRejected(f"페이지를 열지 못함: {r.error or '본문 없음'}")
    if (r.content_type or "").startswith(("application/json", "text/plain")):
        text, title, when, heads, links = r.text, None, None, [], []
    else:
        text, title, when, heads, links = extract(r.text, r.final_url)
    if not text:
        raise ToolRejected("본문을 추출하지 못함(JS 페이지일 수 있음)")
    depth = state.depth.resolve(args.url, args.parent)  # execute_tool이 이미 통과시킨 검사, 값만
    remember(state, args.url, text, depth)
    if norm_url(r.final_url) != args.url:
        remember(state, r.final_url, text, depth)
    kinds = res["link_kinds"]
    shown = [{"url": x["url"], "kind": classify(x["url"], kinds), "anchor": (x.get("anchor") or "")[:60]}
             for x in links[:MAX_LINKS]]
    parts = (len(text) - 1) // HEAD_CHARS + 1
    return ToolOutput(content={"final_url": r.final_url, "title": title, "date": when, "headings": heads,
                               "text": text[:HEAD_CHARS], "parts": parts,
                               "more": f"read_more(doc, part=2..{parts})" if parts > 1 else None, "links": shown},
                      links=[norm_url(x["url"]) for x in links])


@tool(ReadMoreArgs)
def read_more(args: ReadMoreArgs, state: Any) -> ToolOutput:
    """이미 연 문서의 다음 조각(3,000자 단위). 깊이를 늘리지 않는다.
    언제 쓰나: 확인할 수치가 첫 조각에 없고 소제목으로 보아 뒤에 있을 것 같을 때.
    언제 쓰지 않나: 아직 fetch_page로 열지 않은 문서, 없는 조각 번호.
    인자 예: {"doc": "https://openai.com/index/...", "part": 2}"""
    from ..core.artifacts_text import page_key

    text = resources(state)["fetched_pages"].get(page_key(args.doc))
    if text is None:
        raise ToolRejected("아직 fetch_page로 열지 않은 문서")
    parts = (len(text) - 1) // HEAD_CHARS + 1
    if args.part > parts:
        raise ToolRejected(f"조각은 {parts}개까지")
    a = (args.part - 1) * HEAD_CHARS
    return ToolOutput(content={"doc": args.doc, "part": args.part, "parts": parts, "text": text[a:a + HEAD_CHARS]})
