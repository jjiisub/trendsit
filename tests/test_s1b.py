"""S1 1b 수집: 저장한 응답(tests/fixtures/http)만으로 재현한다. 녹화에 없는 URL은 네트워크 차단으로 실패한다."""

import gzip
import json
import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import yaml

from trendsit.collect import fetch as fetch_mod
from trendsit.collect.fetch import MAX_BYTES, FetchBlocked, Fetcher, check_address
from trendsit.collect.github import parse_trending
from trendsit.collect.keywords import KeywordMatcher
from trendsit.collect.links import classify, normalize_url, url_id
from trendsit.collect.run import collect
from trendsit.collect.text import TextCollector
from trendsit.core import config
from trendsit.core.config import ROOT
from trendsit.core.db import DB

FIX = ROOT / "tests" / "fixtures" / "http"
PUBLIC_IP = "93.184.216.34"


class FixtureTransport(httpx.BaseTransport):
    """녹화한 응답만 돌려준다. 없는 URL은 연결 실패(네트워크 차단). override로 상태를 바꿀 수 있다."""

    def __init__(self, *names: str, override: dict[str, int] | None = None, extra: dict[str, tuple] | None = None):
        self.index: dict[str, tuple[Path, dict]] = {}
        for name in names:
            idx = json.loads((FIX / name / "index.json").read_text())
            for url, meta in idx.items():
                self.index[url] = (FIX / name / meta["file"], meta)
        self.override = override or {}
        self.extra = extra or {}
        self.requested: list[str] = []
        self.blocked: list[str] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requested.append(url)
        if url in self.extra:
            status, ctype, body = self.extra[url]
            return httpx.Response(status, headers={"content-type": ctype}, content=body.encode(), request=request)
        if url in self.override:
            return httpx.Response(self.override[url], headers={"content-type": "text/html"}, content=b"err",
                                  request=request)
        if url not in self.index:
            self.blocked.append(url)
            raise httpx.ConnectError(f"네트워크 차단(픽스처에 없음): {url}", request=request)
        path, meta = self.index[url]
        headers = {"content-type": meta["content_type"]}
        if meta.get("location"):
            headers["location"] = meta["location"]
        return httpx.Response(meta["status"], headers=headers, content=gzip.decompress(path.read_bytes()),
                              request=request)


def fake_ytdlp(*names: str):
    calls = {}
    for n in names:
        p = FIX / n / "ytdlp.json"
        if p.exists():
            calls |= json.loads(p.read_text())
    return lambda args: calls.get(" ".join(args))


def fetcher_for(transport, **kw) -> Fetcher:
    return Fetcher(None, use_cache=False, transport=transport, resolver=lambda host: [PUBLIC_IP],
                   sleep=lambda s: None, **kw)


def run_window(tmp_path, transport=None, data_dir=None):
    meta = json.loads((FIX / "window" / "meta.json").read_text())
    transport = transport or FixtureTransport("window")
    res = collect(date.fromisoformat(meta["since"]), date.fromisoformat(meta["until"]), data_dir=data_dir or tmp_path,
                  fetcher=fetcher_for(transport), ytdlp=fake_ytdlp("window"), max_items=meta["max_items"])
    return res, meta, transport


def independent_in_range(transport: "FixtureTransport", day: str) -> dict[str, int]:
    """녹화한 피드를 feedparser로 직접 읽어 한국 시간 게시일이 day인 항목 수(수집 코드를 쓰지 않음)."""
    from datetime import timezone

    import feedparser

    kst = timezone(timedelta(hours=9))
    out = {}
    for src in config.load("sources.yaml").text:
        path, _ = transport.index[src.feed]
        feed = feedparser.parse(gzip.decompress(path.read_bytes()))
        n = 0
        for e in feed.entries:
            t = e.get("published_parsed") or e.get("updated_parsed")
            if t and datetime(*t[:6], tzinfo=UTC).astimezone(kst).date().isoformat() == day:
                n += 1
        out[src.id] = n
    return out


def count(db: DB, sql: str, *args) -> int:
    return db.conn.execute(sql, args).fetchone()[0]


# ---------- A3 설정 ----------
def copy_cfg(tmp_path):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    return tmp_path / "config"


def edit(path, fn):
    d = yaml.safe_load(path.read_text())
    fn(d)
    path.write_text(yaml.safe_dump(d, allow_unicode=True))


def test_new_config_files_pass():
    assert config.check_all() == []
    assert set(config.FILES) >= {"sources.yaml", "link_kinds.yaml"}


def test_bad_backfill_method_and_kind_point_to_path(tmp_path):
    cfg = copy_cfg(tmp_path)
    edit(cfg / "sources.yaml", lambda d: d["text"][3]["backfill"].__setitem__("method", "crawl_all"))
    edit(cfg / "sources.yaml", lambda d: d["text"][0].__setitem__("kind", "blog"))
    paths = {(e.file, e.path) for e in config.check_all(cfg)}
    assert ("sources.yaml", "text[3].backfill.method") in paths
    assert ("sources.yaml", "text[0].kind") in paths


def test_backfill_needs_template_and_link_kinds_validated(tmp_path):
    cfg = copy_cfg(tmp_path)
    edit(cfg / "sources.yaml", lambda d: d["text"][4]["backfill"].pop("url_template"))
    edit(cfg / "link_kinds.yaml", lambda d: d["kinds"]["paper"].__setitem__("domain", ["arxiv.org"]))
    errors = {(e.file, e.path) for e in config.check_all(cfg)}
    assert ("sources.yaml", "text[4].backfill") in errors
    assert ("link_kinds.yaml", "kinds.paper.domain") in errors


# ---------- A4 SSRF ----------
@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "::1", "192.168.1.10", "172.16.0.1",
                                "100.64.0.1", "0.0.0.0", "224.0.0.1", "fe80::1", "fc00::1", "::ffff:127.0.0.1"])
def test_private_addresses_blocked(ip):
    with pytest.raises(FetchBlocked):
        check_address(ip)
    check_address(PUBLIC_IP)


def _mock(handler):
    return Fetcher(None, use_cache=False, transport=httpx.MockTransport(handler),
                   resolver=lambda h: ["10.0.0.5"] if h == "internal.example" else [PUBLIC_IP], sleep=lambda s: None)


@pytest.mark.parametrize("url", ["http://127.0.0.1/admin", "http://10.0.0.5/", "http://169.254.169.254/latest/meta-data",
                                 "http://[::1]:8788/", "http://internal.example/", "file:///etc/passwd",
                                 "gopher://example.com/"])
def test_dangerous_urls_rejected_without_request(url):
    calls = []
    f = _mock(lambda r: calls.append(r) or httpx.Response(200, text="x"))
    res = f.fetch(url, kind="feed")
    assert res.error and res.error.startswith("차단") and calls == []


def test_redirect_to_private_ip_blocked():
    def handler(r):
        if r.url.host == "public.example":
            return httpx.Response(302, headers={"location": "http://10.0.0.5/secret"})
        raise AssertionError("사설 주소로 요청이 나감")
    res = _mock(handler).fetch("https://public.example/start", kind="feed")
    assert res.error and "공인 주소가 아님" in res.error


def test_size_and_content_type_limits():
    big = _mock(lambda r: httpx.Response(200, headers={"content-type": "text/html"}, content=b"a" * (MAX_BYTES + 10)))
    assert "크기 상한" in big.fetch("https://public.example/big", kind="feed").error
    pdf = _mock(lambda r: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF"))
    assert "허용 밖 형식" in pdf.fetch("https://public.example/a.pdf", kind="feed").error


def test_retry_on_5xx_then_success_and_domain_interval():
    waits, n = [], {"i": 0}

    def handler(r):
        n["i"] += 1
        return httpx.Response(503 if n["i"] < 3 else 200, headers={"content-type": "text/plain"}, text="ok")
    f = Fetcher(None, use_cache=False, transport=httpx.MockTransport(handler), resolver=lambda h: [PUBLIC_IP],
                sleep=waits.append, clock=lambda: 0.0)
    res = f.fetch("https://public.example/x", kind="feed")
    assert res.ok and n["i"] == 3
    assert 1.0 in waits and 2.0 in waits  # 지수 백오프(1, 2초) + 같은 도메인 1초 간격


def test_http_cache_conditional_request(tmp_path):
    seen = []

    def handler(r):
        seen.append(r.headers.get("if-none-match"))
        if r.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, headers={"content-type": "text/plain", "etag": '"v1"'}, text="body")
    f = Fetcher(tmp_path, transport=httpx.MockTransport(handler), resolver=lambda h: [PUBLIC_IP], sleep=lambda s: None)
    assert f.fetch("https://public.example/c", kind="feed").text == "body"
    again = f.fetch("https://public.example/c", kind="feed")
    assert again.from_cache and again.text == "body" and seen == [None, '"v1"']


# ---------- A11 robots ----------
def test_robots_disallow_is_respected_and_recorded():
    def handler(r):
        if r.url.path == "/robots.txt":
            return httpx.Response(200, headers={"content-type": "text/plain"},
                                  text="User-agent: *\nDisallow: /private/\n")
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>ok</p>")
    f = _mock(handler)
    assert f.fetch("https://public.example/private/page", kind="page").error == "robots.txt가 막음"
    assert f.fetch("https://public.example/open/page", kind="page").ok
    assert f.fetch("https://public.example/private/feed.xml", kind="feed").ok  # 피드는 robots 확인 생략
    assert f.blocked_by_robots == ["https://public.example/private/page"]


def test_real_robots_allow_our_agent():
    """녹화한 실제 robots.txt(GeekNews는 학습용 크롤러만 막음)에서 TrendsIT은 허용."""
    f = fetcher_for(FixtureTransport("window"))
    assert f.allowed_by_robots("https://news.hada.io/topic?id=1")


# ---------- A5, A6 오프라인 수집과 멱등 ----------
def test_offline_collect_matches_recording(tmp_path):
    res, meta, transport = run_window(tmp_path)
    assert res.failed == [] and transport.blocked == []
    db = DB(tmp_path / "trendsit.db")
    for sid, exp in meta["result"].items():
        if "n_new" in exp:
            got = count(db, "SELECT COUNT(*) FROM items WHERE source_id=?", sid)
            assert got == exp["n_new"], sid
    assert count(db, "SELECT COUNT(*) FROM repo_trending") == meta["result"]["github_trending"]["trending"]
    assert count(db, "SELECT COUNT(*) FROM items WHERE source_id='github_releases'") == \
        meta["result"]["github_releases"]["releases"]
    # 본문, 링크, 키워드가 저장됨
    assert count(db, "SELECT COUNT(*) FROM items WHERE channel='text' AND body_status='ok'") >= 8
    assert count(db, "SELECT COUNT(*) FROM item_texts WHERE length(text) > 300") >= 8
    assert count(db, "SELECT COUNT(*) FROM links") > 10
    assert count(db, "SELECT COUNT(*) FROM links WHERE role='origin_candidate'") == \
        count(db, "SELECT COUNT(*) FROM items WHERE source_id='geeknews'")
    assert count(db, "SELECT COUNT(*) FROM item_keywords") > 10
    assert count(db, "SELECT COUNT(*) FROM videos WHERE meta_status='ok'") == meta["result"]["techbridge"]["n_new"]
    # 실행 기록: runs 1행, 소스마다 step과 fetch_log
    assert count(db, "SELECT COUNT(*) FROM runs WHERE kind='collect'") == 1
    assert count(db, "SELECT COUNT(*) FROM steps WHERE kind='code' AND role='collect'") == len(meta["result"])
    assert count(db, "SELECT COUNT(*) FROM fetch_log") == len(meta["result"])
    for row in db.conn.execute("SELECT day, week, published_at FROM items WHERE source_id != 'github_releases'"):
        assert row["day"] == meta["since"] and row["week"] == "2026-W41" and row["published_at"].endswith("+09:00")
    # 기간 안 후보 수(개발용 상한 적용 전)를 녹화 결과가 아니라 피드에서 직접 센 값과 비교한다
    for sid, expect in independent_in_range(transport, meta["since"]).items():
        assert res.sources[sid]["n_in_range"] >= expect, sid  # 백필로 더해질 수 있어 하한
        if sid in ("openai", "deepmind", "anthropic"):  # RSS만으로 덮는 소스는 같아야 함
            assert res.sources[sid]["n_in_range"] == expect, sid


def test_collect_twice_is_idempotent(tmp_path):
    run_window(tmp_path)
    db = DB(tmp_path / "trendsit.db")
    before = count(db, "SELECT COUNT(*) FROM items"), count(db, "SELECT COUNT(*) FROM links")
    res, _, _ = run_window(tmp_path)
    after = count(db, "SELECT COUNT(*) FROM items"), count(db, "SELECT COUNT(*) FROM links")
    assert before == after
    assert all(d.get("n_new", 0) == 0 for k, d in res.sources.items() if k != "github_trending")
    assert count(db, "SELECT COUNT(*) FROM (SELECT source_id, external_id FROM items GROUP BY 1, 2 HAVING COUNT(*) > 1)") == 0


# ---------- A7 백필 ----------
@pytest.mark.parametrize("name,sid", [("bf_geeknews", "geeknews"), ("bf_aitimes", "aitimes"), ("bf_simonw", "simonw"),
                                      ("bf_youtube", "techbridge")])
def test_backfill_from_saved_pages(tmp_path, name, sid):
    meta = json.loads((FIX / name / "meta.json").read_text())
    res = collect(date.fromisoformat(meta["since"]), date.fromisoformat(meta["until"]), only=sid, data_dir=tmp_path,
                  fetcher=fetcher_for(FixtureTransport(name)), ytdlp=fake_ytdlp(name), max_items=meta["max_items"])
    d = res.sources[sid]
    exp = meta["result"][sid]
    assert d["status"] in ("ok", "partial") and not d.get("errors")
    assert d["backfill_pages"] == exp["backfill_pages"] >= 1
    assert d["n_backfilled"] == exp["n_backfilled"] >= 1
    db = DB(tmp_path / "trendsit.db")
    days = [r[0] for r in db.conn.execute("SELECT day FROM items WHERE source_id=?", (sid,))]
    assert days and all(meta["since"] <= x <= meta["until"] for x in days)


def test_day_archive_pages_until_short_page(tmp_path):
    """GeekNews 날짜별 아카이브: 20건 미만 페이지에서 멈추고 다음 날짜로."""
    meta = json.loads((FIX / "bf_geeknews" / "meta.json").read_text())
    t = FixtureTransport("bf_geeknews")
    collect(date.fromisoformat(meta["since"]), date.fromisoformat(meta["until"]), only="geeknews", data_dir=tmp_path,
            fetcher=fetcher_for(t), max_items=meta["max_items"])
    pages = [u for u in t.requested if "past?day=" in u]
    # 아카이브는 시작일 하루 전부터(UTC 날짜 아카이브 대응), 날마다 1페이지부터 20건 미만 페이지까지
    start = date.fromisoformat(meta["since"])
    days = sorted({u.split("day=")[1].split("&")[0] for u in pages})
    assert days[0] == (start - timedelta(days=1)).isoformat() and days[-1] == meta["since"]
    for d in days:
        nums = [int(u.rsplit("=", 1)[1]) for u in pages if f"day={d}&" in u]
        assert nums == list(range(1, len(nums) + 1))


def test_list_pages_stops_before_since(tmp_path):
    """목록 페이지에 --since보다 앞선 항목이 나오면 다음 페이지를 읽지 않는다."""
    src = next(s for s in config.load("sources.yaml").text if s.id == "aitimes")
    since, until = date(2026, 10, 3), date(2026, 10, 4)
    p1 = src.backfill.url_template.format(since=since, until=until)
    p2 = src.backfill.page_template.format(page=2, since=since, until=until)
    p3 = src.backfill.page_template.format(page=3, since=since, until=until)
    html = ('<section id="section-list"><ul><li><h2 class="altlist-subject"><a href="https://www.aitimes.com/news/'
            'articleView.html?idxno=1">A</a></h2><div class="altlist-info-item">10-04 10:00</div></li></ul></section>')
    ajax = json.dumps({"result": "success", "data": [{"idxno": "2", "title": "B", "pub_date": "2026-10-02"}]})
    t = FixtureTransport(extra={p1: (200, "text/html", html), p2: (200, "text/javascript", ajax),
                                p3: (200, "text/javascript", ajax),
                                "https://www.aitimes.com/robots.txt": (200, "text/plain", "User-agent: *\nAllow: /")})
    db = DB(tmp_path / "t.db")
    c = TextCollector(db, fetcher_for(t), config.load("keywords.yaml"), config.load("link_kinds.yaml"), run_id="r")
    from trendsit.collect.text import SourceStats
    st = SourceStats("aitimes")
    rows = c._list_pages(src, since, until, st)
    assert [r.url.rsplit("=", 1)[1] for r in rows] == ["1", "2"]
    assert p3 not in t.requested and st.backfill_pages == 2


# ---------- A8 실패 격리 ----------
def test_one_source_failing_does_not_stop_others(tmp_path):
    feed = next(s.feed for s in config.load("sources.yaml").text if s.id == "openai")
    t = FixtureTransport("window", override={feed: 500})
    res, meta, _ = run_window(tmp_path, transport=t)
    assert res.failed == ["openai"]
    db = DB(tmp_path / "trendsit.db")
    assert count(db, "SELECT COUNT(*) FROM items WHERE source_id='geeknews'") == meta["result"]["geeknews"]["n_new"]
    log = db.conn.execute("SELECT status, error FROM fetch_log WHERE source_id='openai'").fetchone()
    assert log["status"] == "failed" and "500" in log["error"]
    step = db.conn.execute("SELECT attention, text FROM steps WHERE text LIKE 'openai%'").fetchone()
    assert step["attention"] == 1
    assert db.conn.execute("SELECT status FROM runs WHERE kind='collect'").fetchone()[0] == "partial"


# ---------- A9 트렌딩 ----------
@pytest.mark.parametrize("src", ["window", "monthly"])
def test_trending_parser(src):
    if src == "window":
        t = FixtureTransport("window")
        url = config.load("sources.yaml").github.trending.url
        path, _ = t.index[url]
        html = gzip.decompress(path.read_bytes()).decode()
    else:
        html = gzip.decompress((FIX / "trending_monthly.html.gz").read_bytes()).decode()
    rows = parse_trending(html)
    assert len(rows) == html.count('<article class="Box-row') and len(rows) >= 10
    assert all(isinstance(r["stars_this_week"], int) for r in rows)
    assert all(r["full_name"].count("/") == 1 for r in rows)
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))


def test_empty_trending_page_is_failure(tmp_path):
    url = config.load("sources.yaml").github.trending.url
    t = FixtureTransport("window", extra={url: (200, "text/html", "<html><body>바뀐 페이지</body></html>")})
    res, _, _ = run_window(tmp_path, transport=t)
    assert "github_trending" in res.failed
    assert "트렌딩 0건" in res.sources["github_trending"]["error"]


# ---------- A10 키워드 ----------
def test_keyword_rules():
    m = KeywordMatcher(config.load("keywords.yaml"))
    assert m.match("New eval suite for agents").score == 3 + 3  # 제목 매칭은 3점씩
    assert m.match("We evaluate things").filter_status == "filtered"  # eval이 evaluate에 안 걸림
    assert m.match("제목", "본문에 MCP 서버").score == 1  # 본문 매칭 1점
    assert m.match("MCP 서버 소개", "MCP 이야기").keywords == {"mcp-tools": "title"}  # 같은 키워드는 한 번
    ex = m.match("회사 합병 소식", "AI 에이전트 회사가 합병")
    assert ex.filter_status == "filtered" and ex.filter_reason == "excluded:합병"
    assert m.match("AI 에이전트 회사 합병", "").filter_status == "pass"  # 제목에 포함 키워드가 있으면 유지
    assert m.match("Claude Code 2.0", "").keywords["coding-agent"] == "title"


# ---------- 링크 ----------
def test_url_normalize_and_classify():
    assert normalize_url("https://Example.com/a/?utm_source=x&id=3&ref=hn#top") == "https://example.com/a?id=3"
    assert url_id("https://example.com/a/") == url_id("https://example.com/a?utm_medium=y")
    kinds = config.load("link_kinds.yaml")
    assert classify("https://arxiv.org/abs/2501.00001", kinds) == "paper"
    assert classify("https://huggingface.co/blog/foo", kinds) == "official"
    assert classify("https://huggingface.co/Qwen/Qwen3", kinds) == "repo"
    assert classify("https://www.openai.com/index/x", kinds) == "official"
    assert classify("https://example.org/newsroom/2026", kinds) == "press"
    assert classify("https://example.org/post", kinds) == "other"


def test_fetch_module_constants():
    assert fetch_mod.USER_AGENT.startswith("TrendsIT/0.1")


# ---------- 수집 리포트 ----------
def test_collection_report(tmp_path):
    from trendsit.collect.report import build

    _, meta, _ = run_window(tmp_path)
    day = date.fromisoformat(meta["since"])
    path, verdict = build(day, day, data_dir=tmp_path, out=tmp_path / "S1_collection.md")
    text = path.read_text()
    for h in ("## 1. 소스별", "## 2. 백필 URL 확인", "## 3. GitHub", "## 4. 유튜브", "## 5. 사람 확인용 샘플",
              "## 6. 링크", "## 7. 문턱값"):
        assert h in text
    assert "- [ ] 놓침" in text and "- [ ] 잘못 통과" in text
    assert verdict["trending"] == meta["result"]["github_trending"]["trending"] and verdict["duplicates"] == 0
    assert verdict["origin_rate"] == 1.0


# ---------- GeekNews 브라우저 확인 ----------
def test_geeknews_browser_check_stops_and_uses_origin(tmp_path):
    """토픽 페이지가 브라우저 확인으로 넘어가면 더 요청하지 않고(우회 안 함) 목록의 원문 링크 글을 본문으로."""
    from trendsit.collect.text import Candidate, SourceStats

    article = "<html><body><article><h1>T</h1>" + "<p>원문 본문 문장입니다. " * 40 + "</p></article></body></html>"
    calls = []

    def handler(r):
        calls.append(str(r.url))
        if r.url.path == "/robots.txt":
            return httpx.Response(404)
        if r.url.path == "/topic":
            return httpx.Response(302, headers={"location": "/topic_browser_check?return=%2Ftopic"})
        if r.url.path == "/topic_browser_check":
            return httpx.Response(200, headers={"content-type": "text/html"},
                                  text='<form id="browser-check"></form>')
        return httpx.Response(200, headers={"content-type": "text/html"}, text=article)
    f = Fetcher(None, use_cache=False, transport=httpx.MockTransport(handler), resolver=lambda h: [PUBLIC_IP],
                sleep=lambda s: None)
    src = next(s for s in config.load("sources.yaml").text if s.id == "geeknews")
    c = TextCollector(DB(tmp_path / "t.db"), f, config.load("keywords.yaml"), config.load("link_kinds.yaml"), run_id="r")
    st = SourceStats("geeknews")
    for i in (1, 2):
        cand = Candidate(url=f"https://news.hada.io/topic?id={i}", title=f"글 {i}", published=None,
                         extra={"origin_url": f"https://blog.example.com/post{i}"})
        c._save(src, cand, st)
    assert c.gn_blocked and st.body == {"ok": 2}
    assert sum("/topic?id=" in u for u in calls) == 1  # 확인 페이지를 본 뒤로는 토픽 페이지를 다시 요청하지 않음
    db = c.db
    assert count(db, "SELECT COUNT(*) FROM links WHERE role='origin_candidate'") == 2


# ---------- 리뷰 반영 회귀 테스트 ----------
def _collector(tmp_path, handler):
    f = Fetcher(None, use_cache=False, transport=httpx.MockTransport(handler), resolver=lambda h: [PUBLIC_IP],
                sleep=lambda s: None)
    return TextCollector(DB(tmp_path / "t.db"), f, config.load("keywords.yaml"), config.load("link_kinds.yaml"), run_id="r")


ARTICLE = "<html><body><article><h1>T</h1>" + "<p>원문 본문 문장입니다. " * 40 + "</p></article></body></html>"


def test_rss_only_geeknews_finds_origin_from_archive_when_blocked(tmp_path):
    """RSS로만 얻은 GeekNews 글도 브라우저 확인이 나오면 그날 목록에서 원문 링크를 찾아 원문을 받는다."""
    from trendsit.collect.text import Candidate, SourceStats

    lst = ("<div class='topic_row' data-topic-state-id='7'><div class='topictitle'><a href='https://blog.example.com/a' "
           "class='topic-title-link'><h2>글</h2></a></div><div class='topicdesc'><a href='topic?id=7'>요약 앞부분</a></div>"
           "<div class='topicinfo'><time datetime='2026-10-06T10:00:00+09:00'>x</time></div></div>")

    def handler(r):
        if r.url.path == "/robots.txt":
            return httpx.Response(404)
        if r.url.path == "/topic":
            return httpx.Response(302, headers={"location": "/topic_browser_check?return=x"})
        if r.url.path == "/topic_browser_check":
            return httpx.Response(200, headers={"content-type": "text/html"}, text='<form id="browser-check"></form>')
        if r.url.path == "/past":
            return httpx.Response(200, headers={"content-type": "text/html"}, text=lst)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=ARTICLE)
    c = _collector(tmp_path, handler)
    src = next(s for s in config.load("sources.yaml").text if s.id == "geeknews")
    c._range, c._src = (date(2026, 10, 6), date(2026, 10, 6)), src
    st = SourceStats("geeknews")
    cand = Candidate(url="https://news.hada.io/topic?id=7", title="글",
                     published=datetime.fromisoformat("2026-10-06T10:00:00+09:00"))  # RSS 항목: 원문 링크 없음
    c._save(src, cand, st)
    assert st.body == {"ok": 1}
    assert count(c.db, "SELECT COUNT(*) FROM links WHERE role='origin_candidate' AND url='https://blog.example.com/a'") == 1


def test_out_of_range_date_from_page_is_not_saved(tmp_path):
    """목록에 날짜가 없던 후보는 글 페이지에서 얻은 날짜로 기간을 다시 보고, 밖이면 저장하지 않는다."""
    from trendsit.collect.text import Candidate, SourceStats

    old = ('<html><head><meta property="article:published_time" content="2025-01-15T09:00:00Z"></head>'
           '<body><article>' + "<p>본문입니다. " * 50 + "</p></article></body></html>")
    c = _collector(tmp_path, lambda r: httpx.Response(404) if r.url.path == "/robots.txt" else
                   httpx.Response(200, headers={"content-type": "text/html"}, text=old))
    src = next(s for s in config.load("sources.yaml").text if s.id == "anthropic")
    c._range, c._src = (date(2026, 9, 28), date(2026, 10, 4)), src
    st = SourceStats("anthropic")
    c._save(src, Candidate(url="https://www.anthropic.com/news/old", title=None, published=None), st)
    assert st.n_out_of_range == 1 and st.n_new == 0
    assert count(c.db, "SELECT COUNT(*) FROM items") == 0


def test_list_backfill_not_reaching_since_is_not_covered(tmp_path):
    """목록 백필이 --since까지 닿지 못하면(페이지 넘김 없음, 날짜 없음) 기간 덮음이 아니다."""
    from trendsit.collect.text import SourceStats

    c = _collector(tmp_path, lambda r: httpx.Response(404) if r.url.path == "/robots.txt" else
                   httpx.Response(200, headers={"content-type": "text/html"}, text='<a href="/news/a">a</a>'))
    src = next(s for s in config.load("sources.yaml").text if s.id == "anthropic")
    st = SourceStats("anthropic")
    rows = c._list_pages(src, date(2026, 9, 28), date(2026, 10, 4), st)
    assert len(rows) == 1 and st.covered is False and st.notes


def test_archive_error_marks_not_covered(tmp_path):
    from trendsit.collect.text import SourceStats

    c = _collector(tmp_path, lambda r: httpx.Response(404) if r.url.path == "/robots.txt" else httpx.Response(500))
    src = next(s for s in config.load("sources.yaml").text if s.id == "geeknews")
    st = SourceStats("geeknews")
    c._archive_day(src, date(2026, 10, 1), st)
    assert st.covered is False and st.errors


def test_robots_5xx_or_unreachable_disallows_and_is_recorded():
    def handler(r):
        if r.url.path == "/robots.txt":
            return httpx.Response(503)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="ok")
    f = _mock(handler)
    res = f.fetch("https://public.example/page", kind="page")
    assert res.error.startswith("robots.txt 확인 불가") and f.blocked_by_robots
    assert "https://public.example" in f.robots_unavailable
    n_before = len(f.blocked_by_robots)
    f.fetch("https://public.example/page2", kind="page")  # 출처마다 한 번만 확인
    assert len(f.blocked_by_robots) == n_before + 1


def test_missing_content_type_rejected():
    f = _mock(lambda r: httpx.Response(200, content=b"%PDF-1.7 binary"))
    assert f.fetch("https://public.example/x", kind="feed").error == "형식 헤더 없음"


def test_retry_after_http_date():
    from trendsit.collect.fetch import _retry_after

    assert _retry_after("7") == 7.0
    assert _retry_after("Wed, 21 Oct 2015 07:28:00 GMT") == 0.0  # 지난 시각이면 바로
    assert _retry_after("garbage") is None
