"""본문 속 링크 추출, URL 정규화, 링크 종류 판별(config/link_kinds.yaml)."""

from __future__ import annotations

import hashlib
import re
from html import unescape
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from ..core.config import LinkKindsConfig

TRACKING_PARAMS = re.compile(r"^(utm_.*|ref|ref_src|fbclid|gclid|mc_cid|mc_eid|igshid)$", re.I)


def normalize_url(url: str) -> str:
    """추적 파라미터(utm_*, ref 등) 제거, 호스트 소문자, 조각(#) 제거, 끝 슬래시 통일."""
    parts = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                       if not TRACKING_PARAMS.match(k)])
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def url_id(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()[:16]


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


_A = re.compile(r"<a\s[^>]*?href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
XML_REF = re.compile(r"<ref target=\"([^\"]+)\">(.*?)</ref>", re.S)
_TAG = re.compile(r"<[^>]+>")


def extract_links(html: str, base_url: str, *, xml_refs: bool = False) -> list[dict[str, str]]:
    """바깥 링크(다른 호스트, http/https)만. xml_refs=True면 trafilatura XML의 <ref target>에서."""
    pattern = XML_REF if xml_refs else _A
    own = host_of(base_url)
    out: dict[str, dict[str, str]] = {}
    for href, inner in pattern.findall(html or ""):
        url = urljoin(base_url, unescape(href).strip())
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            continue
        if host_of(url) == own:
            continue
        anchor = " ".join(unescape(_TAG.sub(" ", inner)).split())[:200]
        out.setdefault(normalize_url(url), {"url": url, "anchor": anchor})
    return list(out.values())


def classify(url: str, cfg: LinkKindsConfig) -> str:
    """위에서부터 먼저 맞는 종류. 도메인은 호스트가 같거나 하위 도메인, 경로가 붙은 도메인(huggingface.co/blog)은 앞부분 일치."""
    parts = urlsplit(url)
    host = host_of(url)
    hostpath = f"{host}{parts.path}"
    for kind, rule in cfg.kinds.items():
        for d in rule.domains:
            d = d.lower().removeprefix("www.")
            if "/" in d:
                if hostpath.startswith(d):
                    return kind
            elif host == d or host.endswith("." + d):
                return kind
        if any(p in parts.path for p in rule.path_contains):
            return kind
    return cfg.default
