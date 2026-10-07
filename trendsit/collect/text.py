"""글 수집: RSS → (부족하면 백필) → 기간 필터 → 본문 추출 → 링크 판별 → 키워드 매칭 → 칠판 저장."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

import feedparser
import trafilatura

from ..core.config import KeywordsConfig, LinkKindsConfig, TextSource
from ..core.db import DB
from .fetch import Fetcher, FetchResult
from .keywords import KeywordMatcher
from .links import classify, extract_links, url_id
from .sites import aitimes, anthropic, geeknews, simonw
from .sites.common import KST, block_text, doc

MIN_BODY = 300  # 이보다 짧으면 body_status=short
TEXT_TTL = timedelta(weeks=8)  # 본문 보관 기간(저작권). 이후 본문만 지움
MONTHS = [calendar.month_abbr[i] for i in range(13)]  # Jan, Feb, ...


class SourceFailed(Exception):
    """소스 전체를 가져오지 못함(피드 실패 등). 다른 소스는 계속한다."""


@dataclass
class Candidate:
    url: str
    title: str | None = None
    published: datetime | None = None
    published_estimated: bool = False
    summary: str | None = None
    content_html: str | None = None  # feed_full 본문
    via: str = "rss"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceStats:
    source_id: str
    n_in_range: int = 0  # 기간 안 후보(개발용 상한 적용 전)
    n_seen: int = 0  # 이번에 처리한 후보
    n_new: int = 0
    n_backfilled: int = 0  # 새 항목 중 백필로 얻은 것
    n_skipped: int = 0  # 이미 있음
    n_out_of_range: int = 0  # 글 페이지에서 얻은 게시 시각이 기간 밖이라 저장하지 않음
    backfill_pages: int = 0
    rss_oldest: str | None = None
    covered: bool = True
    body: dict[str, int] = field(default_factory=dict)  # body_status별 건수
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    fetch_errors: dict[str, int] = field(default_factory=dict)  # 본문 가져오기 실패 이유별 건수

    def summary_text(self) -> str:
        parts = [f"{self.source_id}: 신규 {self.n_new}건"]
        if self.backfill_pages:
            parts.append(f"백필 {self.backfill_pages}페이지({self.n_backfilled}건)")
        bad = self.body.get("failed", 0) + self.body.get("short", 0)
        if bad:
            parts.append(f"본문 실패·짧음 {bad}건")
        if self.fetch_errors:
            top = sorted(self.fetch_errors.items(), key=lambda kv: -kv[1])[:2]
            parts.append("실패 이유 " + ", ".join(f"{k} {v}건" for k, v in top))
        if self.n_skipped:
            parts.append(f"기존 {self.n_skipped}건 건너뜀")
        if self.n_out_of_range:
            parts.append(f"기간 밖 {self.n_out_of_range}건 제외")
        if not self.covered:
            parts.append("기간 부족")
        if self.errors:
            parts.append(f"오류 {len(self.errors)}건")
        return ", ".join(parts)


def to_kst(dt: datetime | None) -> datetime | None:
    return dt.astimezone(KST) if dt else None


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _struct_dt(t: Any) -> datetime | None:
    return datetime(*t[:6], tzinfo=UTC) if t else None


def parse_feed(text: str) -> list[Candidate]:
    feed = feedparser.parse(text)
    if feed.bozo and not feed.entries:
        raise SourceFailed(f"피드 해석 실패: {feed.get('bozo_exception')}")
    out = []
    for e in feed.entries:
        link = e.get("link")
        if not link:
            continue
        published = _struct_dt(e.get("published_parsed") or e.get("updated_parsed"))
        content = (e.get("content") or [{}])[0].get("value")
        out.append(Candidate(url=link, title=e.get("title"), published=published, published_estimated=published is None,
                             summary=_html_text(e.get("summary") or ""), content_html=content))
    return out


def _html_text(fragment: str) -> str:
    if not fragment or "<" not in fragment:
        return fragment
    try:
        return block_text(doc(f"<div>{fragment}</div>"))
    except Exception:  # noqa: BLE001 - 깨진 조각은 원문 그대로
        return fragment


def _render(template: str, *, page: int | None = None, day: date | None = None, since: date | None = None,
            until: date | None = None) -> str:
    values: dict[str, Any] = {}
    if page is not None:
        values["page"] = page
    if day is not None:
        values.update(date=day.isoformat(), yyyy=day.year, Mon=MONTHS[day.month], d=day.day)
    if since is not None:
        values["since"] = since.isoformat()
    if until is not None:
        values["until"] = until.isoformat()
    return template.format(**values)


class TextCollector:
    def __init__(self, db: DB, fetcher: Fetcher, keywords: KeywordsConfig, link_kinds: LinkKindsConfig, *,
                 run_id: str, no_body: bool = False, max_items: int | None = None):
        self.db, self.fetcher = db, fetcher
        self.matcher = KeywordMatcher(keywords)
        self.link_kinds = link_kinds
        self.run_id = run_id
        self.no_body = no_body
        self.max_items = max_items  # 개발용 작은 샘플
        self._last_error: str | None = None
        self.gn_blocked = False  # GeekNews가 브라우저 확인을 요구하면 이 실행에서는 토픽 페이지를 더 요청하지 않음
        self.origin_bodies = 0
        self._gn_days: dict[date, dict[str, Candidate]] = {}  # 막혔을 때 원문 링크를 찾는 날짜별 목록
        self._range: tuple[date, date] = (date.min, date.max)
        self._src: TextSource | None = None

    # ---------- 소스 하나 ----------
    def collect(self, src: TextSource, since: date, until: date) -> SourceStats:
        st = SourceStats(src.id)
        self._range, self._src = (since, until), src
        res = self.fetcher.fetch(src.feed, kind="feed")
        if not res.ok:
            raise SourceFailed(f"피드 실패: {res.error}")
        entries = parse_feed(res.text or "")
        dated = [to_kst(c.published) for c in entries if c.published]
        oldest = min(dated).date() if dated else None
        st.rss_oldest = oldest.isoformat() if oldest else None

        backfilled: list[Candidate] = []
        # RSS의 가장 오래된 날은 그날을 일부만 담을 수 있으므로, 시작일이 그날과 같아도 백필한다
        if oldest is None or since <= oldest:
            if src.backfill.method == "rss_only":
                st.covered = False
                st.notes.append(f"RSS 가장 오래된 항목 {oldest}, 요청 시작 {since}: 백필 방법 없음(rss_only)")
            else:
                backfilled = self._backfill(src, since, until, oldest, st)

        merged: dict[str, Candidate] = {}
        for c in [*entries, *backfilled]:  # RSS 항목이 먼저(피드 요약, 본문 보존). 백필에만 있는 정보는 합친다
            kept = merged.setdefault(url_id(c.url), c)
            if kept is not c:
                kept.extra = c.extra | kept.extra
                kept.published = kept.published or c.published
                kept.summary = kept.summary or c.summary
        in_range = [c for c in merged.values() if c.published is None or since <= to_kst(c.published).date() <= until]
        st.n_in_range = len(in_range)
        if self.max_items:
            in_range = in_range[: self.max_items]
        before = self.origin_bodies
        for c in in_range:
            self._save(src, c, st)
        if src.id == "geeknews" and self.gn_blocked:
            st.errors.append(f"GeekNews가 브라우저 확인을 요구해 토픽 페이지 요청을 멈춤(우회 안 함). "
                            f"원문 글을 본문으로 {self.origin_bodies - before}건")
        return st

    # ---------- 백필 ----------
    def _backfill(self, src: TextSource, since: date, until: date, oldest: date | None,
                  st: SourceStats) -> list[Candidate]:
        bf = src.backfill
        out: list[Candidate] = []
        if bf.method == "day_archive":
            last = min(until, oldest) if oldest else until  # RSS가 덮는 날은 건너뛰되, 가장 오래된 날은 다시 본다
            day = since - timedelta(days=1)  # 아카이브가 UTC 날짜면 한국 시간 시작일 0~9시 글이 전날 아카이브에 있다
            while day <= last:
                out += self._archive_day(src, day, st)
                day += timedelta(days=1)
        elif bf.method == "list_pages":
            out += self._list_pages(src, since, until, st)
        for c in out:
            c.via = "backfill"
        return out

    def _archive_day(self, src: TextSource, day: date, st: SourceStats) -> list[Candidate]:
        template = src.backfill.url_template or ""
        pages = range(1, src.backfill.max_pages + 1) if "{page}" in template else [None]
        out: list[Candidate] = []
        for page in pages:
            url = _render(template, page=page, day=day)
            res = self.fetcher.fetch(url, kind="page")
            st.backfill_pages += 1
            if not res.ok:
                if res.status == 404 and page in (None, 1):  # 그날 글이 없는 아카이브
                    st.notes.append(f"아카이브 없음(404): {day}")
                    break
                if res.status == 404:  # 페이지 끝
                    break
                st.errors.append(f"백필 {url}: {res.error}")
                st.covered = False
                break
            rows = self._parse_archive(src, res.text or "", day)
            out += rows
            if not rows or page is None or len(rows) < 20:  # 빈 페이지나 마지막 페이지
                break
        return out

    def _parse_archive(self, src: TextSource, text: str, day: date) -> list[Candidate]:
        if src.id == "geeknews":
            rows = geeknews.parse_list(text)
            return [Candidate(url=r["url"], title=r["title"], published=r["published"], summary=r.get("desc"),
                              extra={"origin_url": r["origin_url"]}) for r in rows]
        if src.id == "simonw":
            return [Candidate(url=r["url"], title=r["title"], published=r["published"] or
                              datetime(day.year, day.month, day.day, tzinfo=UTC),
                              published_estimated=r["published_estimated"], content_html=r["content_html"])
                    for r in simonw.parse_day(text, day)]
        raise SourceFailed(f"{src.id}: day_archive 파서 없음")

    def _list_pages(self, src: TextSource, since: date, until: date, st: SourceStats) -> list[Candidate]:
        bf = src.backfill
        out: list[Candidate] = []
        first_url = _render(bf.url_template or "", page=1, since=since, until=until)
        reached = False  # --since보다 앞선 항목까지 닿았거나, 목록 끝(빈 페이지)까지 읽음
        for page in range(1, bf.max_pages + 1):
            template = bf.url_template if page == 1 or not bf.page_template else bf.page_template
            if page > 1 and "{page}" not in (template or ""):
                break  # 페이지 넘김이 없는 목록
            url = _render(template or "", page=page, since=since, until=until)
            # 2페이지부터(더보기 AJAX 등)는 브라우저처럼 1페이지를 Referer로 보낸다
            headers = {"Referer": first_url, "X-Requested-With": "XMLHttpRequest"} if page > 1 else None
            rows = None
            for attempt in range(2):  # 목록 응답 해석 실패(일시적 거부 등)는 3초 뒤 한 번 더
                res = self.fetcher.fetch(url, kind="page", headers=headers)
                st.backfill_pages += 1
                if not res.ok:
                    st.errors.append(f"백필 {url}: {res.error}")
                    break
                try:
                    rows = self._parse_list(src, res.text or "", page, since, until)
                    break
                except ValueError as e:
                    if attempt == 1:
                        st.errors.append(f"백필 {url}: {e}")
                    else:
                        self.fetcher.sleep(3.0)
            if rows is None:  # 이 백필만 멈추고 기록
                break
            out += rows
            dated = [to_kst(c.published).date() for c in rows if c.published]
            if not rows or (dated and min(dated) < since):
                reached = True
                break
        if not reached:
            st.covered = False
            st.notes.append(f"목록 백필이 {since}까지 닿지 못함(페이지 {st.backfill_pages}, 상한 {bf.max_pages} 또는 오류)")
        return out

    def _parse_list(self, src: TextSource, text: str, page: int, since: date, until: date) -> list[Candidate]:
        if src.id == "aitimes":
            rows = aitimes.parse_list_html(text, since, until) if page == 1 else aitimes.parse_ajax(text)
        elif src.id == "anthropic":
            rows = anthropic.parse_list(text)
        else:
            raise SourceFailed(f"{src.id}: list_pages 파서 없음")
        return [Candidate(url=r["url"], title=r["title"], published=r["published"],
                          published_estimated=r.get("published_estimated", False)) for r in rows]

    # ---------- 항목 하나 ----------
    def _save(self, src: TextSource, c: Candidate, st: SourceStats) -> None:
        ext = url_id(c.url)
        existing = self.db.item_by_external(src.id, ext)
        # 이미 있으면 건너뛴다. 본문이 비었던 항목(failed, 또는 --no-body로 건너뛴 항목)만 다시 시도
        retry = existing is not None and (existing["body_status"] == "failed" or (
            existing["body_status"] == "skipped" and not self.no_body))
        if existing is not None and not retry:
            st.n_skipped += 1
            return
        st.n_seen += 1
        self._last_error = None
        body, status, links, origin_summary, published = self._body(src, c)
        if status == "failed":
            reason = (self._last_error or "본문 추출 실패")[:80]
            st.fetch_errors[reason] = st.fetch_errors.get(reason, 0) + 1
        if c.published is None and published is not None:
            c.published = published
            c.published_estimated = published.hour == 0 and published.minute == 0  # 메타데이터가 날짜만 줌
        when = to_kst(c.published) or datetime.now(KST)
        estimated = c.published is None or c.published_estimated
        since, until = self._range
        if not since <= when.date() <= until:  # 글 페이지에서 얻은 날짜(또는 수집 시각)가 기간 밖
            st.n_out_of_range += 1
            return
        m = self.matcher.match(c.title, c.summary, body)
        item = {
            "source_id": src.id, "channel": "text", "kind": src.kind, "external_id": ext, "url": c.url,
            "title": c.title, "published_at": when.isoformat(timespec="seconds"), "published_estimated": estimated,
            "day": when.date().isoformat(), "week": iso_week(when.date()), "summary_feed": c.summary,
            "body_status": status, "filter_status": m.filter_status, "filter_reason": m.filter_reason,
            "score": m.score, "run_id": self.run_id, "via": c.via,
        }
        for x in links:
            x["kind"] = classify(x["url"], self.link_kinds)
        self.db.save_item(item, text=body, origin_summary=origin_summary,
                          expires_at=(datetime.now(KST) + TEXT_TTL).isoformat(timespec="seconds") if body else None,
                          links=links, keywords=m.keywords, replace_id=existing["id"] if existing else None)
        if existing is None:
            st.n_new += 1
            st.n_backfilled += int(c.via == "backfill")
        st.body[status] = st.body.get(status, 0) + 1

    def _body(self, src: TextSource, c: Candidate
              ) -> tuple[str | None, str, list[dict[str, Any]], str | None, datetime | None]:
        """(본문, body_status, 링크, GeekNews 요약, 페이지에서 찾은 게시 시각)."""
        if self.no_body:
            return None, "skipped", [], None, None
        if src.fetch == "feed_full" and c.content_html:
            text = _html_text(c.content_html)
            links = [x | {"role": "body"} for x in extract_links(c.content_html, c.url)]
            return text, ("ok" if len(text) >= MIN_BODY else "short"), links, None, None

        if src.id == "geeknews" and self.gn_blocked:
            return self._origin_body(c)
        res: FetchResult = self.fetcher.fetch(c.url, kind="page")
        if not res.ok or not res.text:
            self._last_error = res.error or "본문 없음"
            return None, "failed", [], None, None
        if src.id == "geeknews" and geeknews.is_browser_check(res.final_url, res.text):
            self.gn_blocked = True  # 우회하지 않는다. 남은 항목은 원문 글로
            return self._origin_body(c)
        if src.id == "geeknews":
            t = geeknews.parse_topic(res.text)
            text = t["summary_text"]
            links = [x | {"role": "body"} for x in extract_links(t["summary_html"], c.url)]
            origin = t["origin_url"] or c.extra.get("origin_url")
            if origin:
                links = [x for x in links if x["url"] != origin]
                links.insert(0, {"url": origin, "anchor": t["title"] or c.title or "", "role": "origin_candidate"})
            status = "ok" if len(text) >= MIN_BODY else ("short" if text else "failed")
            return text or None, status, links, text or None, t["published"]

        return self._extract(res)

    def _origin_body(self, c: Candidate
                     ) -> tuple[str | None, str, list[dict[str, Any]], str | None, datetime | None]:
        """GeekNews 토픽 페이지를 못 받을 때: 목록에서 얻은 원문 링크의 글을 본문으로(요약 대신 원문)."""
        origin = c.extra.get("origin_url") or self._gn_origin_from_list(c)
        if not origin:
            self._last_error = "GeekNews 브라우저 확인 요구 + 원문 링크 없음"
            return None, "failed", [], None, None
        res = self.fetcher.fetch(origin, kind="page")
        head = [{"url": origin, "anchor": c.title or "", "role": "origin_candidate"}]
        if not res.ok or not res.text:
            self._last_error = f"원문 {res.error or '본문 없음'}"
            return None, "failed", head, None, None
        text, status, links, _, _ = self._extract(res)
        links = head + [x for x in links if x["url"] != origin]
        self.origin_bodies += 1
        return text, status, links, None, None  # 게시 시각은 GeekNews 목록의 것을 쓴다

    def _gn_origin_from_list(self, c: Candidate) -> str | None:
        """RSS로만 얻은 GeekNews 글: 그날의 날짜별 아카이브(목록 페이지는 브라우저 확인 대상이 아님)에서 원문 링크를 찾는다."""
        if self._src is None or c.published is None or not self._src.backfill.url_template:
            return None
        day = to_kst(c.published).date()
        if day not in self._gn_days:
            rows: dict[str, Candidate] = {}
            dummy = SourceStats(self._src.id)
            for r in self._archive_day(self._src, day, dummy):
                rows[url_id(r.url)] = r
            self._gn_days[day] = rows
        hit = self._gn_days[day].get(url_id(c.url))
        if hit is None:
            return None
        c.summary = c.summary or hit.summary
        return hit.extra.get("origin_url")

    def _extract(self, res: FetchResult
                 ) -> tuple[str | None, str, list[dict[str, Any]], str | None, datetime | None]:
        xml = trafilatura.extract(res.text, url=res.final_url, output_format="xml", include_links=True,
                                  include_comments=False, favor_recall=True)
        text = trafilatura.extract(res.text, url=res.final_url, include_comments=False, favor_recall=True) or ""
        meta = trafilatura.extract_metadata(res.text)
        published = None
        if meta is not None and meta.date:
            try:
                published = datetime.fromisoformat(meta.date).replace(tzinfo=KST)
            except ValueError:
                published = None
        links = [x | {"role": "body"} for x in extract_links(xml or "", res.final_url, xml_refs=True)]
        if not text:
            return None, "failed", links, None, published
        return text, ("ok" if len(text) >= MIN_BODY else "short"), links, None, published
