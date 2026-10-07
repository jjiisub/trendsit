"""safe_fetch: 수집 URL은 모두 이 함수로만 가져온다.

- SSRF 방어: http/https만, 호스트를 DNS로 풀어 공인 주소가 아니면 거부(사설, 루프백, 링크로컬, 멀티캐스트, 예약,
  IPv4/IPv6 모두). 리다이렉트는 직접 따라가며 매번 다시 검사(최대 5회)
- 예의: User-Agent, 같은 도메인은 1초에 1번, robots.txt(목록, 아카이브, 글 페이지), 429/5xx는 지수 백오프 3회
- 제한: 연결 5초, 읽기 15초, 크기 5MB, 허용 콘텐츠 형식
- HTTP 캐시(data/http_cache/): ETag/Last-Modified 조건부 요청
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from ..core.db import now_kst

USER_AGENT = "TrendsIT/0.1 (+https://trendsit.jiseop.com)"
ROBOTS_AGENT = "TrendsIT"
MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5
RETRIES = 3
DOMAIN_INTERVAL_S = 1.0
ALLOWED_TYPES = ("text/html", "application/xhtml+xml", "application/xml", "text/xml", "application/rss+xml",
                 "application/atom+xml", "application/json", "text/plain",
                 "text/javascript", "application/javascript",  # AI타임스 AJAX(JSON을 이 형식으로 보냄)
                 "application/vnd.github")  # GitHub API raw README
TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)

# feed: 피드(기계용, robots 확인 생략) / page: 목록, 아카이브, 글 페이지(robots 확인) / api: 공개 API(robots 생략)
Kind = Literal["feed", "page", "api"]


class FetchBlocked(Exception):
    """SSRF 방어나 형식 제한으로 가져오지 않음."""


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int | None
    content_type: str | None
    text: str | None
    fetched_at: str
    from_cache: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status is not None and 200 <= self.status < 300


def _resolve(host: str) -> list[str]:
    return sorted({info[4][0] for info in socket.getaddrinfo(host, None)})


SITE_LOCAL_V6 = ipaddress.ip_network("fec0::/10")  # 폐지된 site-local. is_global이 참으로 나와 따로 막는다


def check_address(ip_text: str) -> None:
    ip = ipaddress.ip_address(ip_text.split("%")[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    bad = (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
           or ip.is_unspecified or not ip.is_global
           or (isinstance(ip, ipaddress.IPv6Address) and ip in SITE_LOCAL_V6))
    if bad:
        raise FetchBlocked(f"공인 주소가 아님: {ip}")


class Fetcher:
    def __init__(self, cache_dir: Path | None, *, use_cache: bool = True,
                 transport: httpx.BaseTransport | None = None,
                 resolver: Callable[[str], list[str]] = _resolve,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):
        self.cache_dir = cache_dir
        self.use_cache = use_cache and cache_dir is not None
        self.resolver = resolver
        self.sleep = sleep
        self.clock = clock
        self.client = httpx.Client(transport=transport, timeout=TIMEOUT, follow_redirects=False,
                                   headers={"User-Agent": USER_AGENT})
        self.last_hit: dict[str, float] = {}
        self.intervals: dict[str, float] = {}  # 도메인별 요청 간격(기본 DOMAIN_INTERVAL_S)
        self.robots: dict[str, RobotFileParser | str | None] = {}  # None=제한 없음, str=확인 불가(이유)
        self.blocked_by_robots: list[str] = []
        self.robots_unavailable: dict[str, str] = {}
        self.requests = 0

    # ---------- 공개 함수 ----------
    def fetch(self, url: str, *, kind: Kind = "page", headers: dict[str, str] | None = None) -> FetchResult:
        """오류는 예외가 아니라 FetchResult.error로 돌려준다(수집기가 소스 단위로 격리)."""
        try:
            self._check_url(url)
            if kind == "page" and not self.allowed_by_robots(url):
                self.blocked_by_robots.append(url)
                origin = self._origin(url)
                why = self.robots_unavailable.get(origin)
                return FetchResult(url, url, None, None, None, now_kst(),
                                   error=f"robots.txt 확인 불가로 건너뜀({why})" if why else "robots.txt가 막음")
            return self._fetch(url, headers or {})
        except FetchBlocked as e:
            return FetchResult(url, url, None, None, None, now_kst(), error=f"차단: {e}")
        except httpx.HTTPError as e:
            return FetchResult(url, url, None, None, None, now_kst(), error=f"{type(e).__name__}: {e}")

    @staticmethod
    def _origin(url: str) -> str:
        parts = urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}"

    def allowed_by_robots(self, url: str) -> bool:
        """RFC 9309: 4xx는 제한 없음, 5xx나 연결 실패는 전부 막힌 것으로 본다(출처마다 한 번 확인하고 기억)."""
        origin = self._origin(url)
        if origin not in self.robots:
            entry: RobotFileParser | str | None
            try:
                res = self._fetch(f"{origin}/robots.txt", {}, allow_types=None)
            except (httpx.HTTPError, FetchBlocked) as e:
                res = FetchResult(origin, origin, None, None, None, now_kst(), error=f"{type(e).__name__}: {e}")
            if res.ok and res.text is not None:
                entry = RobotFileParser()
                entry.parse(res.text.splitlines())
            elif res.status is not None and 400 <= res.status < 500:
                entry = None  # robots.txt 없음 = 제한 없음
            else:
                entry = res.error or f"HTTP {res.status}"
                self.robots_unavailable[origin] = entry
            self.robots[origin] = entry
        entry = self.robots[origin]
        if entry is None:
            return True
        if isinstance(entry, str):
            return False
        return entry.can_fetch(ROBOTS_AGENT, url)

    # ---------- 내부 ----------
    def _check_url(self, url: str) -> None:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            raise FetchBlocked(f"허용하지 않는 scheme: {parts.scheme or '(없음)'}")
        host = parts.hostname
        if not host:
            raise FetchBlocked("호스트 없음")
        try:
            ipaddress.ip_address(host)
            addrs = [host]  # IP 리터럴
        except ValueError:
            try:
                addrs = self.resolver(host)
            except OSError as e:
                raise FetchBlocked(f"DNS 실패: {host} ({e})") from e
        if not addrs:
            raise FetchBlocked(f"DNS 결과 없음: {host}")
        for a in addrs:
            check_address(a)

    def set_interval(self, host: str, seconds: float) -> None:
        """이 도메인은 seconds초에 1번(설정의 request_interval_s)."""
        self.intervals[host.removeprefix("www.")] = max(seconds, DOMAIN_INTERVAL_S)

    def _wait_turn(self, host: str) -> None:
        host = host.removeprefix("www.")  # 같은 도메인(www 유무 무관)은 정한 간격에 1번(기본 1초)
        interval = self.intervals.get(host, DOMAIN_INTERVAL_S)
        last = self.last_hit.get(host)
        if last is not None:
            gap = self.clock() - last
            if gap < interval:
                self.sleep(interval - gap)
        self.last_hit[host] = self.clock()

    def _cache_path(self, url: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.json"

    def _fetch(self, url: str, headers: dict[str, str], allow_types: tuple[str, ...] | None = ALLOWED_TYPES
               ) -> FetchResult:
        cached = None
        cpath = self._cache_path(url) if self.use_cache else None
        if cpath and cpath.exists():
            cached = json.loads(cpath.read_text(encoding="utf-8"))
            if cached.get("etag"):
                headers = {**headers, "If-None-Match": cached["etag"]}
            if cached.get("last_modified"):
                headers = {**headers, "If-Modified-Since": cached["last_modified"]}

        current = url
        for _ in range(MAX_REDIRECTS + 1):
            self._check_url(current)
            resp, body = self._request(current, headers)
            if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("location"):
                current = urljoin(current, resp.headers["location"])
                headers = {k: v for k, v in headers.items() if k not in ("If-None-Match", "If-Modified-Since")}
                continue
            break
        else:
            return FetchResult(url, current, None, None, None, now_kst(), error=f"리다이렉트 {MAX_REDIRECTS}회 초과")

        if resp.status_code == 304 and cached is not None:
            return FetchResult(url, cached["final_url"], cached["status"], cached["content_type"], cached["text"],
                               now_kst(), from_cache=True)
        ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        if resp.status_code >= 400:
            return FetchResult(url, current, resp.status_code, ctype, None, now_kst(), error=f"HTTP {resp.status_code}")
        if allow_types is not None and not ctype:
            return FetchResult(url, current, resp.status_code, None, None, now_kst(), error="형식 헤더 없음")
        if allow_types is not None and not ctype.startswith(allow_types):
            return FetchResult(url, current, resp.status_code, ctype, None, now_kst(),
                               error=f"허용 밖 형식: {ctype}")
        text = body.decode(resp.encoding or "utf-8", errors="replace")
        result = FetchResult(url, current, resp.status_code, ctype, text, now_kst())
        if cpath is not None and result.ok:
            cpath.parent.mkdir(parents=True, exist_ok=True)
            data = asdict(result) | {"etag": resp.headers.get("etag"),
                                     "last_modified": resp.headers.get("last-modified")}
            cpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return result

    def _request(self, url: str, headers: dict[str, str]) -> tuple[httpx.Response, bytes]:
        host = urlsplit(url).hostname or ""
        for attempt in range(RETRIES + 1):
            self._wait_turn(host)
            self.requests += 1
            with self.client.stream("GET", url, headers=headers) as resp:
                size = int(resp.headers.get("content-length") or 0)
                if size > MAX_BYTES:
                    raise FetchBlocked(f"크기 상한 초과: {size}바이트")
                chunks, total = [], 0
                for chunk in resp.iter_bytes():
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise FetchBlocked(f"크기 상한 초과: {MAX_BYTES}바이트 넘음")
                    chunks.append(chunk)
            body = b"".join(chunks)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == RETRIES:
                    return resp, body
                wait = min(_retry_after(resp.headers.get("retry-after")) or 2.0 ** attempt, 30.0)
                self.sleep(wait)
                continue
            return resp, body
        raise AssertionError("unreachable")

    def close(self) -> None:
        self.client.close()


def _retry_after(value: str | None) -> float | None:
    """Retry-After: 초 또는 HTTP 날짜."""
    if not value:
        return None
    if value.strip().isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max((when - datetime.now(when.tzinfo or UTC)).total_seconds(), 0.0)
