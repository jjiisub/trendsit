"""수집 실행: 소스마다 격리해서 돌리고, fetch_log와 실행 기록(runs, steps kind='code')을 남긴다."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ..core import config
from ..core.db import DB, KST
from ..core.trace import Tracer
from .fetch import Fetcher
from .github import GithubCollector, GithubStats
from .text import SourceFailed, SourceStats, TextCollector
from .youtube import YoutubeCollector, YtDlp, run_ytdlp


@dataclass
class CollectResult:
    run_id: str
    since: str
    until: str
    sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    failed: list[str] = field(default_factory=list)
    robots_blocked: list[str] = field(default_factory=list)
    requests: int = 0


def sync_sources(db: DB, src: config.SourcesConfig) -> None:
    for t in src.text:
        db.upsert_source(t.id, "text", t.kind, t.name, t.feed, t.model_dump())
    for v in src.video:
        db.upsert_source(v.id, "video", "video", v.name, v.feed, v.model_dump())
    db.upsert_source("github_trending", "github", "trending", "GitHub Trending", src.github.trending.url,
                     src.github.trending.model_dump())
    db.upsert_source("github_releases", "github", "release", "추적 레포 릴리스", None,
                     [t.model_dump() for t in src.github.tracked])


def collect(since: date, until: date, *, only: str | None = None, no_body: bool = False,
            data_dir: Path | None = None, config_dir: Path | None = None, use_http_cache: bool = True,
            fetcher: Fetcher | None = None, ytdlp: YtDlp = run_ytdlp, max_items: int | None = None,
            spec: str | None = None, today: date | None = None) -> CollectResult:
    data_dir = data_dir or config.ROOT / "data"
    sources = config.load("sources.yaml", config_dir)
    keywords = config.load("keywords.yaml", config_dir)
    kinds = config.load("link_kinds.yaml", config_dir)
    ids = [s.id for s in sources.text] + [s.id for s in sources.video] + ["github_trending", "github_releases"]
    if only and only not in ids:  # 실행 기록을 만들기 전에 거른다
        raise config.ConfigError("sources.yaml", "", f"없는 소스 '{only}' (있는 소스: {', '.join(ids)})")
    db = DB(data_dir / "trendsit.db")
    sync_sources(db, sources)
    own_fetcher = fetcher is None
    fetcher = fetcher or Fetcher(data_dir / "http_cache", use_cache=use_http_cache)
    tracer = Tracer(db, "collect", config.current_spec(spec), note=f"collect {since}~{until}" + (f" {only}" if only else ""))
    result = CollectResult(tracer.run_id, since.isoformat(), until.isoformat())
    day = datetime.now(KST).date().isoformat()
    period = {"since": since.isoformat(), "until": until.isoformat()}

    def run_one(sid: str, fn: Any) -> None:
        if only and sid != only:
            return
        try:
            st = fn()
        except SourceFailed as e:
            st, err = None, str(e)
        except Exception as e:  # noqa: BLE001 - 한 소스의 예상 밖 오류도 다른 소스를 멈추지 않는다(오류는 기록)
            st, err = None, f"{type(e).__name__}: {e}"
        if st is None:
            result.failed.append(sid)
            result.sources[sid] = {"status": "failed", "error": err}
            db.log_fetch(tracer.run_id, sid, day, "failed", error=err, detail=period)
            tracer.step(kind="code", role="collect", text=f"{sid}: 수집 실패", attention=True, error=err)
            return
        detail = asdict(st) | period
        partial = bool(getattr(st, "errors", None)) or not getattr(st, "covered", True)
        status = "partial" if partial else "ok"
        result.sources[sid] = {"status": status} | detail
        if isinstance(st, SourceStats):
            db.log_fetch(tracer.run_id, sid, day, status, n_new=st.n_new, n_backfilled=st.n_backfilled,
                         n_seen=st.n_seen, error="; ".join(st.errors)[:1000] or None, detail=detail)
            text = st.summary_text()
        else:
            db.log_fetch(tracer.run_id, sid, day, status, n_new=detail.get("trending", 0) + detail.get("releases_new", 0),
                         error="; ".join(detail.get("errors") or [])[:1000] or None, detail=detail)
            text = _github_text(sid, st)
        tracer.step(kind="code", role="collect", text=text, attention=partial, detail=detail,
                    error="; ".join(detail.get("errors") or [])[:500] or None)

    text_c = TextCollector(db, fetcher, keywords, kinds, run_id=tracer.run_id, no_body=no_body, max_items=max_items,
                           today=today)
    for s in sources.text:
        run_one(s.id, lambda s=s: text_c.collect(s, since, until))
    yt = YoutubeCollector(db, fetcher, keywords, kinds, run_id=tracer.run_id, ytdlp=ytdlp, max_items=max_items)
    for v in sources.video:
        run_one(v.id, lambda v=v: yt.collect(v, since, until))
    gh = GithubCollector(db, fetcher, sources.github, keywords, kinds, run_id=tracer.run_id)

    def trending() -> GithubStats:
        st = GithubStats()
        gh.trending(st)
        return st

    def releases() -> GithubStats:
        st = GithubStats()
        gh.releases(since, until, st)
        return st

    run_one("github_trending", trending)
    run_one("github_releases", releases)
    result.robots_blocked = list(fetcher.blocked_by_robots)
    result.requests = fetcher.requests
    if result.robots_blocked:
        tracer.step(kind="code", role="collect", text=f"robots.txt로 건너뜀 {len(result.robots_blocked)}건",
                    attention=True, detail={"urls": result.robots_blocked[:50],
                                            "robots_unavailable": fetcher.robots_unavailable})
    tracer.finish("partial" if result.failed else "ok")
    if own_fetcher:
        fetcher.close()
    db.close()
    return result


def _github_text(sid: str, st: GithubStats) -> str:
    if sid == "github_trending":
        return (f"github_trending: 페이지 {st.page_rows}개 중 {st.trending}개 저장, 키워드 통과 {st.trending_pass}개, "
                f"README {st.readmes}건")
    return f"github_releases: 기간 안 릴리스 {st.releases}건(신규 {st.releases_new}), README {st.readmes}건"
