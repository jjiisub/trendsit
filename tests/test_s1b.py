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
# 녹화 픽스처는 S1 키워드로 만들었다. 실제 config/keywords.yaml이 넓어져도 녹화가 깨지지 않게 분리(S1 리뷰 M5)
TEST_KEYWORDS = config.KeywordsConfig.model_validate(
    yaml.safe_load((ROOT / "tests" / "fixtures" / "keywords_test.yaml").read_text(encoding="utf-8")))
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
                  fetcher=fetcher_for(transport), ytdlp=fake_ytdlp("window"), max_items=meta["max_items"],
                  today=date.fromisoformat(meta["today"]), keywords=TEST_KEYWORDS)
    return res, meta, transport


def independent_in_range(transport: "FixtureTransport", day: str) -> dict[str, int]:
    """녹화한 피드를 feedparser로 직접 읽어 한국 시간 게시일이 day인 항목 수(수집 코드를 쓰지 않음)."""
    from datetime import timezone

    import feedparser

    kst = timezone(timedelta(hours=9))
    out = {}
    for src in config.load("sources.yaml").text:
        if src.feed is None:  # 목록으로 받는 소스(GeekNews)
            continue
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
                  fetcher=fetcher_for(FixtureTransport(name)), ytdlp=fake_ytdlp(name), max_items=meta["max_items"],
                  today=date.fromisoformat(meta["today"]))
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
            fetcher=fetcher_for(t), max_items=meta["max_items"], today=date.fromisoformat(meta["today"]))
    pages = [u for u in t.requested if "past?day=" in u]
    # GeekNews 날짜별 목록은 한국 시간 날짜라 요청 기간의 날짜만, 날마다 1페이지부터 20건 미만 페이지까지
    days = sorted({u.split("day=")[1].split("&")[0] for u in pages})
    assert days == [meta["since"]]
    assert not any("topic?id=" in u for u in t.requested)  # 상세 페이지는 요청하지 않음(설계 결정 Q1)
    for d in days:
        nums = [int(u.rsplit("=", 1)[1]) for u in pages if f"day={d}&" in u]
        assert nums == list(range(1, len(nums) + 1))


def test_list_pages_stops_before_since(tmp_path):
    """날짜순 목록: --since보다 앞선 항목이 나오면 다음 페이지를 읽지 않는다."""
    from trendsit.collect.text import SourceStats
    from trendsit.core.config import TextSource

    src = TextSource(id="aitimes", name="t", kind="news", feed="https://www.aitimes.com/rss.xml",
                     fetch="feed_summary", backfill={"method": "list_pages",
                                                     "url_template": "https://www.aitimes.com/list?p=1",
                                                     "page_template": "https://www.aitimes.com/ajax?page={page}"})
    html = ('<section id="section-list"><ul><li><h2 class="altlist-subject"><a href="https://www.aitimes.com/news/'
            'articleView.html?idxno=1">A</a></h2><div class="altlist-info-item">10-04 10:00</div></li></ul></section>')
    ajax = json.dumps({"result": "success", "data": [{"idxno": "2", "title": "B", "pub_date": "2026-10-02"}]})
    p1, p2, p3 = "https://www.aitimes.com/list?p=1", "https://www.aitimes.com/ajax?page=2", "https://www.aitimes.com/ajax?page=3"
    t = FixtureTransport(extra={p1: (200, "text/html", html), p2: (200, "text/javascript", ajax),
                                p3: (200, "text/javascript", ajax),
                                "https://www.aitimes.com/robots.txt": (200, "text/plain", "User-agent: *\nAllow: /")})
    c = TextCollector(DB(tmp_path / "t.db"), fetcher_for(t), TEST_KEYWORDS,
                      config.load("link_kinds.yaml"), run_id="r")
    st = SourceStats("aitimes")
    rows = c._list_pages(src, date(2026, 10, 3), date(2026, 10, 4), st)
    assert [r.url.rsplit("=", 1)[1] for r in rows] == ["1", "2"]
    assert p3 not in t.requested and st.backfill_pages == 2 and st.covered


def test_date_filtered_list_reads_until_empty_page(tmp_path):
    """기간으로 거른 목록({since})은 기간 안에 수정된 예전 글이 섞여도 빈 페이지까지 읽는다(AI타임스 실측)."""
    from trendsit.collect.text import SourceStats

    src = next(s for s in config.load("sources.yaml").text if s.id == "aitimes")
    since, until = date(2026, 10, 3), date(2026, 10, 4)
    p1 = src.backfill.url_template.format(since=since, until=until)
    pages = {i: src.backfill.page_template.format(page=i, since=since, until=until) for i in (2, 3, 4)}
    html = ('<section id="section-list"><ul><li><h2 class="altlist-subject"><a href="https://www.aitimes.com/news/'
            'articleView.html?idxno=1">A</a></h2><div class="altlist-info-item">10-04 10:00</div></li></ul></section>')
    old = json.dumps({"result": "success", "data": [{"idxno": "2", "title": "B", "pub_date": "2026-09-23"},
                                                    {"idxno": "3", "title": "C", "pub_date": "2026-10-03"}]})
    empty = json.dumps({"result": "success", "data": []})
    t = FixtureTransport(extra={p1: (200, "text/html", html), pages[2]: (200, "text/javascript", old),
                                pages[3]: (200, "text/javascript", old), pages[4]: (200, "text/javascript", empty),
                                "https://www.aitimes.com/robots.txt": (200, "text/plain", "User-agent: *\nAllow: /")})
    c = TextCollector(DB(tmp_path / "t.db"), fetcher_for(t), TEST_KEYWORDS,
                      config.load("link_kinds.yaml"), run_id="r")
    st = SourceStats("aitimes")
    c._list_pages(src, since, until, st)
    assert pages[4] in t.requested and st.backfill_pages == 4 and st.covered


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
    m = KeywordMatcher(TEST_KEYWORDS)
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
    assert verdict["origin_rate"] == 1.0 and verdict["trending_page_rows"] == verdict["trending"]
    assert "### 하루 신규 건수" in text


# ---------- 리뷰 반영 회귀 테스트 ----------
def _collector(tmp_path, handler):
    f = Fetcher(None, use_cache=False, transport=httpx.MockTransport(handler), resolver=lambda h: [PUBLIC_IP],
                sleep=lambda s: None)
    return TextCollector(DB(tmp_path / "t.db"), f, TEST_KEYWORDS, config.load("link_kinds.yaml"), run_id="r")


ARTICLE = "<html><body><article><h1>T</h1>" + "<p>원문 본문 문장입니다. " * 40 + "</p></article></body></html>"


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


# ---------- 설계 결정 반영(S1 Q1, Q2) ----------
def test_geeknews_list_parser_points_comments_self_posts():
    from trendsit.collect.sites import geeknews

    html = gzip.decompress(next(p for u, (p, _) in FixtureTransport("bf_geeknews").index.items()
                                if "past?day=" in u).read_bytes()).decode()
    rows = geeknews.parse_list(html)
    assert rows and all(r["topic_id"].isdigit() and isinstance(r["points"], int) and isinstance(r["comments"], int)
                        for r in rows)
    assert all(r["origin_url"] is None or "news.hada.io" not in r["origin_url"] for r in rows)
    own = ("<div class='topic_row' data-topic-state-id='9'><div class='topictitle'><a href='topic?id=9' "
           "class='topic-title-link'><h2>Show GN: 내 앱</h2></a></div><div class='topicinfo'><span id='tp9'>3</span>"
           "<a data-topic-comment-count='2'>x</a></div></div>")
    r = geeknews.parse_list(own)[0]
    assert r["origin_url"] is None and r["points"] == 3 and r["comments"] == 2


def test_geeknews_collects_from_lists_only(tmp_path):
    """RSS와 상세 페이지를 요청하지 않고, topic id로 중복 제거, 자기 글은 빼고 세고, 점수·댓글 수를 저장."""
    meta = json.loads((FIX / "bf_geeknews" / "meta.json").read_text())
    t = FixtureTransport("bf_geeknews")
    res = collect(date.fromisoformat(meta["since"]), date.fromisoformat(meta["until"]), only="geeknews",
                  data_dir=tmp_path, fetcher=fetcher_for(t), today=date.fromisoformat(meta["today"]), no_body=True)
    assert not any("topic?id=" in u or "/rss/" in u for u in t.requested)
    d = res.sources["geeknews"]
    db = DB(tmp_path / "trendsit.db")
    n = count(db, "SELECT COUNT(*) FROM items WHERE source_id='geeknews'")
    assert n == d["n_in_range"]
    # 자기 글 제외 건수를 픽스처 목록에서 직접 센 값과 비교(T1)
    from trendsit.collect.sites import geeknews

    own = set()
    for u, (pth, _) in t.index.items():
        if "past?day=" in u:
            for r in geeknews.parse_list(gzip.decompress(pth.read_bytes()).decode()):
                if r["origin_url"] is None and r["published"] and r["published"].date().isoformat() == meta["since"]:
                    own.add(r["topic_id"])
    assert d["n_self_excluded"] == len(own) > 0
    assert count(db, "SELECT COUNT(*) FROM items WHERE source_id='geeknews' AND external_id LIKE 'topic:%'") == n
    row = db.conn.execute("SELECT meta_json FROM items WHERE source_id='geeknews' LIMIT 1").fetchone()
    m = json.loads(row["meta_json"])
    assert m["topic_id"].isdigit() and isinstance(m["points"], int) and isinstance(m["comments"], int)
    assert count(db, "SELECT COUNT(*) FROM links WHERE role='origin_candidate'") == n


def test_geeknews_self_posts_excluded_and_counted(tmp_path):

    page = ("<div class='topic_row' data-topic-state-id='{i}'><div class='topictitle'><a href='{href}' "
            "class='topic-title-link'><h2>{title}</h2></a></div><div class='topicdesc'><a>요약</a></div>"
            "<div class='topicinfo'><span id='tp{i}'>1</span><time datetime='2026-10-03T10:00:00+09:00'>x</time>"
            "<a data-topic-comment-count='0'>c</a></div></div>")
    html = (page.format(i=1, href="https://blog.example.com/a", title="글 A")
            + page.format(i=1, href="https://blog.example.com/a", title="글 A")  # 같은 topic id 두 번
            + page.format(i=2, href="topic?id=2", title="Show GN: 내 앱"))

    def handler(r):
        if r.url.path == "/robots.txt":
            return httpx.Response(404)
        if r.url.path == "/past":
            return httpx.Response(200, headers={"content-type": "text/html"},
                                  text=html if "page=1" in str(r.url) else "")
        return httpx.Response(200, headers={"content-type": "text/html"}, text=ARTICLE)
    c = _collector(tmp_path, handler)
    c.today = date(2026, 10, 7)
    src = next(s for s in config.load("sources.yaml").text if s.id == "geeknews")
    st = c.collect(src, date(2026, 10, 3), date(2026, 10, 3))
    assert st.n_self_excluded == 1 and st.n_new == 1 and st.body == {"ok": 1}


def test_intentional_skips_are_separate_from_failures(tmp_path):
    from trendsit.collect.text import Candidate, SourceStats

    def handler(r):
        if r.url.path == "/robots.txt":
            return httpx.Response(200, headers={"content-type": "text/plain"}, text="User-agent: *\nDisallow: /private")
        if r.url.path.endswith(".pdf"):
            return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")
        if r.url.path == "/forbidden":
            return httpx.Response(403)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=ARTICLE)
    c = _collector(tmp_path, handler)
    src = next(s for s in config.load("sources.yaml").text if s.id == "geeknews")
    c._range = (date(2026, 10, 3), date(2026, 10, 3))
    st = SourceStats("geeknews")
    when = datetime.fromisoformat("2026-10-03T10:00:00+09:00")
    for i, origin in enumerate(["https://a.example/private/x", "https://a.example/r.pdf", "https://youtu.be/abc",
                                "https://a.example/forbidden", "https://a.example/ok"]):
        c._save(src, Candidate(url=f"https://news.hada.io/topic?id={i}", title=f"t{i}", published=when,
                               extra={"origin_url": origin, "external_id": f"topic:{i}"}), st)
    assert st.body == {"skip_robots": 1, "skip_type": 1, "skip_video": 1, "failed": 1, "ok": 1}


def test_trending_verdict_requires_all_page_rows(tmp_path):
    """트렌딩 기준(Q2): 페이지에 보인 수와 저장한 수가 같고 누락 0이면 통과(개수 하한 없음)."""
    from trendsit.collect.report import build

    _, meta, _ = run_window(tmp_path)
    day = date.fromisoformat(meta["since"])
    path, verdict = build(day, day, data_dir=tmp_path, out=tmp_path / "r.md")
    assert verdict["trending"] == verdict["trending_page_rows"] > 0
    assert "| 트렌딩 |" in path.read_text() and "| 통과 |" in path.read_text().split("| 트렌딩 |")[1].split("\n")[0]


# ---------- 2차 리뷰 반영 ----------
def _gn_page(rows: list[tuple[int, str, str]]) -> str:
    tpl = ("<div class='topic_row' data-topic-state-id='{i}'><div class='topictitle'><a href='{href}' "
           "class='topic-title-link'><h2>t{i}</h2></a></div><div class='topicinfo'><span id='tp{i}'>1</span>"
           "<time datetime='{when}'>x</time><a data-topic-comment-count='0'>c</a></div></div>")
    return "".join(tpl.format(i=i, href=h, when=w) for i, h, w in rows)


def test_geeknews_days_pages_per_day_and_interval(tmp_path):
    """매일 수집과 백필 모두 날짜별 목록만(메인 화면 없음, S1 Q5). 오늘은 읽지 않고, 날짜당 pages_per_day페이지.
    목록 요청은 request_interval_s 간격."""
    waits, seen = [], []
    full = _gn_page([(i, f"https://a.example/{i}", "2026-10-05T10:00:00+09:00") for i in range(1, 21)])  # 20행

    def handler(r):
        seen.append(str(r.url))
        if r.url.path == "/robots.txt":
            return httpx.Response(404)
        if r.url.host == "news.hada.io":
            return httpx.Response(200, headers={"content-type": "text/html"}, text=full)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=ARTICLE)
    f = Fetcher(None, use_cache=False, transport=httpx.MockTransport(handler), resolver=lambda h: [PUBLIC_IP],
                sleep=waits.append, clock=lambda: 0.0)
    c = TextCollector(DB(tmp_path / "t.db"), f, TEST_KEYWORDS, config.load("link_kinds.yaml"),
                      run_id="r", today=date(2026, 10, 7), no_body=True)
    src = next(s for s in config.load("sources.yaml").text if s.id == "geeknews")
    assert src.backfill.pages_per_day == 1
    st = c.collect(src, date(2026, 10, 5), date(2026, 10, 7))
    hada = [u for u in seen if "news.hada.io" in u and "robots" not in u]
    assert hada == ["https://news.hada.io/past?day=2026-10-05&page=1", "https://news.hada.io/past?day=2026-10-06&page=1"]
    assert st.notes and "오늘" in st.notes[0]
    assert waits.count(5.0) >= len(hada) - 1  # 목록 요청 사이 5초
    # 날짜당 2페이지로 바꾸면 20행 페이지 다음 페이지까지 읽는다
    src2 = src.model_copy(update={"backfill": src.backfill.model_copy(update={"pages_per_day": 2})})
    seen.clear()
    c.collect(src2, date(2026, 10, 5), date(2026, 10, 5))
    assert [u for u in seen if "past?day=" in u] == ["https://news.hada.io/past?day=2026-10-05&page=1",
                                                     "https://news.hada.io/past?day=2026-10-05&page=2"]


def test_empty_list_page_is_error(tmp_path):
    def handler(r):
        if r.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>바뀐 화면</html>")
    c = _collector(tmp_path, handler)
    c.today = date(2026, 10, 7)
    src = next(s for s in config.load("sources.yaml").text if s.id == "geeknews")
    st = c.collect(src, date(2026, 10, 3), date(2026, 10, 7))
    assert st.covered is False and any("0행" in e for e in st.errors)


def test_robots_unavailable_counts_as_failure(tmp_path):
    """robots.txt를 못 읽은 것(5xx, 타임아웃)은 의도적 건너뜀이 아니라 실패(T4)."""
    from trendsit.collect.text import Candidate, SourceStats

    def handler(r):
        if r.url.path == "/robots.txt":
            return httpx.Response(503)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=ARTICLE)
    c = _collector(tmp_path, handler)
    src = next(s for s in config.load("sources.yaml").text if s.id == "geeknews")
    c._range = (date(2026, 10, 3), date(2026, 10, 3))
    st = SourceStats("geeknews")
    c._save(src, Candidate(url="https://news.hada.io/topic?id=1", title="t",
                           published=datetime.fromisoformat("2026-10-03T10:00:00+09:00"),
                           extra={"origin_url": "https://down.example/x", "external_id": "topic:1"}), st)
    assert st.body == {"failed": 1} and not st.skip_reasons


def test_self_post_detection_by_host():
    from trendsit.collect.sites.geeknews import is_own

    assert is_own("topic?id=1") and is_own("https://news.hada.io/topic?id=1") and is_own(None)
    assert not is_own("https://blog.example.com/post?ref=news.hada.io")


def test_trending_verdict_fails_when_a_row_is_dropped(tmp_path):
    """페이지에 보인 행보다 저장한 행이 적으면(파서가 거른 행) 트렌딩 기준 미달(T2)."""
    from trendsit.collect.report import build

    url = config.load("sources.yaml").github.trending.url
    page = ('<article class="Box-row"><h2><a href="/a/b">a/b</a></h2><span>12 stars this week</span></article>'
            '<article class="Box-row"><h2><a href="/broken">x</a></h2></article>')
    t = FixtureTransport("window", extra={url: (200, "text/html", page)})
    _, meta, _ = run_window(tmp_path, transport=t)
    day = date.fromisoformat(meta["since"])
    path, verdict = build(day, day, data_dir=tmp_path, out=tmp_path / "r.md")
    assert verdict["trending_page_rows"] == 2 and verdict["trending"] == 1
    assert "| 미달 |" in path.read_text().split("| 트렌딩 |")[1].split("\n")[0]
