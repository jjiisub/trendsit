"""S6a 사이트: 도식 배치·출처 번호(A3), 확인 필요 표기(A4), 정적 검사 실패 감지(A5~A7), 발행 연결·원자 교체(A12, C-10). 임시 폴더만 쓴다."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tests.test_export import make_db
from trendsit import ops

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "site_src" / "build.py"
FIXTURE = ROOT / "tests" / "fixtures" / "site" / "site.json"


def run_build(data: Path, out: Path):
    return subprocess.run([sys.executable, str(BUILD), "--data", str(data), "--out", str(out)], capture_output=True, text=True)


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("fx") / "site"
    r = run_build(FIXTURE, out)
    assert r.returncode == 0, r.stderr
    return out


def tree_hash(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


class Dom(HTMLParser):
    """요소 스택을 따라가며 (태그, 클래스, 부모 체인)을 모은다."""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, list[str], str | None]] = []
        self.els: list[dict] = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        el = {"tag": tag, "cls": a.get("class", "").split(), "id": a.get("id"), "href": a.get("href"), "chain": list(self.stack), "text": ""}
        self.els.append(el)
        if tag not in ("br", "link", "meta", "img", "input"):
            self.stack.append((tag, el["cls"], a.get("id")))

    def handle_endtag(self, tag):
        while self.stack and self.stack[-1][0] != tag:
            self.stack.pop()
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.els:
            self.els[-1]["text"] += data

    def find(self, tag=None, cls=None):
        return [e for e in self.els if (tag is None or e["tag"] == tag) and (cls is None or cls in e["cls"])]


def dom(site: Path, rel: str) -> Dom:
    return Dom((site / rel / "index.html").read_text(encoding="utf-8"))


def inside(el, cls=None, id_=None) -> bool:
    return any((cls and cls in c) or (id_ and i == id_) for _, c, i in el["chain"])


# ---------- A3(v2 5.8) ----------
def test_a3_sections_order_visual_after_first_paragraph_and_source_numbers(site):
    d = dom(site, "topic/w41-long")
    secs = [e["id"] for e in d.find("section", "dsec")]
    assert secs == ["sec-0", "sec-1", "sec-2", "sec-3", "sec-4"]
    figs = d.find("figure")
    assert [tuple(c for c in f["cls"] if c != "dg") for f in figs] == [("dg-bars",), ("dg-events",)]
    assert inside(figs[0], id_="sec-1") and inside(figs[1], id_="sec-2")
    p1 = [e for e in d.els if inside(e, id_="sec-1")]
    assert next(i for i, e in enumerate(p1) if "dp" in e["cls"]) < next(i for i, e in enumerate(p1) if e["tag"] == "figure")
    assert d.find("ol", "vgo") and inside(d.find("ol", "vgo")[0], id_="sec-4")  # 영상 구간이 있는 절 아래
    # 출처 번호: 채널 순(글 → 영상 → 레포), 채널 안 id 순
    refs = {e["href"]: e["text"] for e in d.find("a", "ref")}
    assert [refs[f"#src-{i}"] for i in ("s1", "s6", "v1", "v2", "g1", "g4")] == ["[1]", "[6]", "[7]", "[8]", "[9]", "[12]"]
    src_ids = {e["id"]: e for e in d.find("li", "src")}
    assert set(src_ids) == {f"src-{i}" for i in ["s1", "s2", "s3", "s4", "s5", "s6", "v1", "v2", "g1", "g2", "g3", "g4"]}
    assert all(h[1:] in src_ids for h in refs)
    # 인용마다 툴팁, aria 연결, url 없는 출처(v2)는 원문 열기 없음, 원본(origin) 링크 한 줄
    assert len(d.find("span", "tip")) == len(d.find("a", "ref")) == len(d.find("span", "cite"))
    html = (site / "topic/w41-long/index.html").read_text(encoding="utf-8")
    tip_v2 = re.search(r'<span class="tip"[^>]*>(?:(?!</span></span></span>).)*출처 목록 \[8\]', html).group(0)
    assert "원문 열기" not in tip_v2 and html.count("원본 <a href=") == 1
    # 영상 출처 아래 전체 타임라인
    assert d.find("ol", "vtl")
    # 도식 없는 토픽에는 도식 없음, 수치 막대는 그 절 안
    assert not dom(site, "topic/w41-one").find("figure")
    mid = dom(site, "topic/w41-mid")
    assert [inside(f, id_="sec-0") for f in mid.find("figure")] == [True]


def test_a3_topic_blocks_order_and_links(site):
    html = (site / "topic/w41-long/index.html").read_text(encoding="utf-8")
    order = [html.index(x) for x in ('id="sec-0"', 'id="sec-4"', 'id="h-src"', 'class="pn"')]
    assert order == sorted(order)
    assert html.index('class="follow"') < order[0] and "/topic/w40-base/" in html  # 대상이 있는 후속은 지난 흐름 링크
    assert "개요" not in html and "핵심 포인트" not in html and "핵심 개념" not in html  # 옛 섹션 제목 없음
    assert 'class="follow"' not in (site / "topic/w41-one/index.html").read_text(encoding="utf-8")  # 대상 없는 후속은 링크 없음
    one = dom(site, "topic/w41-one")
    assert not one.find("nav", "pn") or all("w41-" in (e["href"] or "") for e in one.find("a", "pn-next") + one.find("a", "pn-prev"))
    assert "<script" not in html and 'title="' not in html


def test_a3_head_tiles_class_matches_count(site):
    d = dom(site, "topic/w41-long")
    wrap = d.find("div", "tiles")
    assert wrap and f"n{len(d.find('div', 'tile'))}" in wrap[0]["cls"]


def test_a3_video_secs_links(site):
    html = (site / "topic/w41-long/index.html").read_text(encoding="utf-8")
    assert "&t=920s" in html and "&t=110s" in html


# ---------- A4(v2 C-9) ----------
class ChkWalk(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.chk, self.stack = 0, []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "").split()
        self.stack.append(tag)
        if "chk" in cls:
            self.chk += 1

    def handle_endtag(self, tag):
        while self.stack and self.stack.pop() != tag:
            pass


@pytest.mark.parametrize("tid,total", [("w41-long", 1), ("w41-one", 0), ("w41-mid", 0), ("w40-base", 0)])
def test_a4_check_marks(site, tid, total):
    w = ChkWalk((site / "topic" / tid / "index.html").read_text(encoding="utf-8"))
    assert w.chk == total  # C-9: 절 하나(sections[0])만 확인 필요. '빠진 시각 요소'는 표시 안 함


def test_a4_check_mark_target_matches_meta_link(site):
    html = (site / "topic/w41-long/index.html").read_text(encoding="utf-8")
    assert '<a class="fu" href="#chk-1">확인 필요</a>' in html and 'id="chk-1"' in html


def test_a4_home_meta_has_check(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    items = html.split('<li class="it">')[1:]
    assert ["확인 필요" in re.search(r'<p class="tmeta.*?</p>', i).group(0) for i in items] == [True, False, False]
    assert 'class="chk"' not in html  # 홈 메타의 표기는 .chk가 아니라 글자만
    assert '<a class="fu" href="#chk-1">' not in html  # 홈에서는 그 토픽 페이지 안의 앵커로 가지 않음(링크 없는 글자)


# ---------- A5~A7: 정적 검사가 실제로 잡아내는가 ----------
def test_a5_to_a7_checker_catches_violations(site, tmp_path):
    import shutil

    sys.path.insert(0, str(ROOT / "site_src"))
    import check

    bad = tmp_path / "site"
    shutil.copytree(site, bad)
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def run():
        check.results.clear()
        pages = {f: check.parse(f) for f in sorted(bad.rglob("*.html"))}
        import contextlib
        import io

        with contextlib.redirect_stdout(io.StringIO()):
            check.static_checks(bad, data, pages)
        return {n.split()[0] + " " + n.split()[1] for n, ok, _ in check.results if not ok}

    assert run() == set()
    css = next((bad / "assets").glob("*.css"))
    (bad / "sources/index.html").write_text((bad / "sources/index.html").read_text(encoding="utf-8").replace("</main>", "<button>x</button><p>예시 사이트</p></main>"), encoding="utf-8")
    css.write_text(css.read_text(encoding="utf-8") + '@import url("https://fonts.googleapis.com/css2?family=X");', encoding="utf-8")
    (bad / "index.html").write_text((bad / "index.html").read_text(encoding="utf-8").replace("<body>", '<body><a href="/week/none/">깨진 링크</a><script></script>'), encoding="utf-8")
    failed = run()
    assert failed == {"C-3 내부", "C-4 외부", "C-5 button·form·input·select·textarea", "A7 '동작", "A6 @font-face"}


# ---------- A12, C-10 ----------
def test_c10_bad_input_keeps_site_untouched(site, tmp_path):
    out = tmp_path / "site"
    assert run_build(FIXTURE, out).returncode == 0
    before = tree_hash(out)
    assert run_build(tmp_path / "none.json", out).returncode == 1  # 없음
    broken = tmp_path / "broken.json"
    broken.write_text("{ 깨짐", encoding="utf-8")
    assert run_build(broken, out).returncode == 1
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del data["topics"][0]["sections"]  # 렌더링 도중 실패
    half = tmp_path / "half.json"
    half.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert run_build(half, out).returncode == 1
    assert tree_hash(out) == before and not [p for p in tmp_path.iterdir() if ".tmp-" in p.name]  # 바이트 그대로, 임시 폴더 정리


def test_a12_publish_runs_export_then_build_and_failure_keeps_site(tmp_path):
    db = make_db(tmp_path, published=())
    site_dir, data = tmp_path / "site", tmp_path / "site.json"  # data = DB와 같은 폴더의 site.json(= publish가 쓰는 위치)
    calls: list[str] = []
    corrupt = {"on": False}

    def runner(cmd):
        assert cmd[: len(ops.BUILD_CMD)] == ops.BUILD_CMD and cmd[-2] == "--data"
        calls.append("build:" + Path(cmd[-1]).name)
        assert Path(cmd[-1]).is_file()  # export가 먼저 끝나 있음
        if corrupt["on"]:
            Path(cmd[-1]).write_text("{ 깨짐", encoding="utf-8")
        r = run_build(Path(cmd[-1]), site_dir)
        return r.returncode, r.stdout, r.stderr

    assert ops.publish(db, "2026-W41", runner) == 0
    assert calls == ["build:site.json.new"] and ops.BUILD_CMD[0] == sys.executable  # 시스템 python3가 아니라 trendsit을 부른 python
    row = db.conn.execute("SELECT status, published_at FROM weeks WHERE week='2026-W41'").fetchone()
    assert row["status"] == "published" and (site_dir / "week/2026-w41/index.html").is_file()
    assert (site_dir / "topic/w41-a/index.html").is_file()
    assert [w["id"] for w in json.loads(data.read_text(encoding="utf-8"))["weeks"]] == ["2026-w41"] and not (tmp_path / "site.json.new").exists()
    before, data_before = tree_hash(site_dir), data.read_bytes()
    # 다음 주 발행에서 build가 실패하면: site/ 바이트 그대로, 상태 그대로(done), data/site.json에 미발행 주가 남지 않음
    corrupt["on"] = True
    assert ops.publish(db, "2026-W40", runner) == 1
    assert tree_hash(site_dir) == before and data.read_bytes() == data_before and not (tmp_path / "site.json.new").exists()
    assert db.conn.execute("SELECT status FROM weeks WHERE week='2026-W40'").fetchone()[0] == "done"
    assert calls == ["build:site.json.new"] * 2


def test_f75_approx_week_home_note_and_no_week_stars_and_empty_notes(site):
    w39 = (site / "week/2026-w39/index.html").read_text(encoding="utf-8")
    assert w39.count("주간 기록이 없어 월간 목록으로 대신한다") == 1 and "monthly-a" in w39
    assert 'class="rp-s"' not in w39  # 별 수가 없는 레포에는 "이번 주 별" 줄이 없음
    assert "이 주는 트렌딩 기록이 없다" in (site / "week/2026-w41/index.html").read_text(encoding="utf-8")  # 레포 0개 주
    assert "매일 실행 기록 없음(손으로 실행)" in (site / "runs/2026-w41/index.html").read_text(encoding="utf-8")  # nightly 0개 주


def test_f79_site_old_not_restored_when_input_invalid(tmp_path):
    b = load_build()
    b.build(FIXTURE, tmp_path / "site")
    (tmp_path / "site").rename(tmp_path / "site.old")
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(b.BuildError):
        b.build(bad, tmp_path / "site")
    assert not (tmp_path / "site").exists() and (tmp_path / "site.old").is_dir()  # C-10: 깨진 입력이면 건드리지 않음


def test_f53_publish_export_exception_returns_1_and_keeps_state(tmp_path, monkeypatch, capsys):
    db = make_db(tmp_path, published=())

    def boom(*a, **k):
        raise KeyError("rank")

    monkeypatch.setattr(ops, "export_site", boom)
    assert ops.publish(db, "2026-W41", lambda cmd: pytest.fail("빌드까지 가면 안 됨")) == 1
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1 and "KeyError" in err[0]
    assert db.conn.execute("SELECT status FROM weeks WHERE week='2026-W41'").fetchone()[0] == "done"
    assert not (tmp_path / "site.json").exists() and not (tmp_path / "site.json.new").exists()


# ---------- F01 끝 어절 묶기: 원문 어절 단위 ----------
def load_build():
    sys.path.insert(0, str(ROOT / "site_src"))
    import build as b

    return b


@pytest.mark.parametrize("raw,expect", [
    ("AAII 벤치마크 43점", '<span class="nb">AAII</span> 벤치마크 <span class="nb-end"><span class="nb">43</span>점&nbsp;T</span>'),
    ("설치는 `uv`로", '설치는 <span class="nb-end"><code class="ic">uv</code>로&nbsp;T</span>'),
    ("처리량이 ==2배 늘어==됨", '처리량이 <span class="nb-end"><mark class="hl">2배 늘어</mark>됨&nbsp;T</span>'),
    ("정확도 ==93.5%==가", '정확도 <span class="nb-end"><mark class="hl"><span class="nb">93.5%</span></mark>가&nbsp;T</span>'),
    ("성능이 더 큼", '성능이 <span class="nb-end">더 큼&nbsp;T</span>'),  # 한 음절이면 앞 어절까지
    ("한 단어", '한 <span class="nb-end">단어&nbsp;T</span>'),
    ("==아주 긴 형광 구절이 끝까지 이어지는 문장 끝부분==", '<mark class="hl">아주 긴 형광 구절이 끝까지 이어지는 문장 끝부분</mark><span class="nb-end">&nbsp;T</span>'),  # 24자 넘으면 인용만
])
def test_f01_with_end_uses_raw_words(raw, expect):
    assert load_build().with_end(raw, "T") == expect


def test_f01_no_broken_markup_in_real_shaped_points(site):
    html = (site / "topic/w41-mid/index.html").read_text(encoding="utf-8")
    assert not re.search(r"<\w+ <", html) and 'class="nb">' not in re.sub(r"<[^>]+>", "", html)
    assert ChkWalk(html).stack == []  # 태그가 어긋나면 스택이 비지 않음
    assert '<span class="nb-end"><span class="nb">43</span>점.&nbsp;' in html


def test_f01_checker_catches_broken_markup(site, tmp_path):
    import contextlib
    import io
    import shutil

    sys.path.insert(0, str(ROOT / "site_src"))
    import check

    bad = tmp_path / "site"
    shutil.copytree(site, bad)
    f = bad / "topic/w41-mid/index.html"
    f.write_text(f.read_text(encoding="utf-8").replace('<span class="nb-end"><span class="nb">43</span>', '<span <span class="nb-end">class="nb">43</span>'), encoding="utf-8")  # 옛 with_end가 만들던 깨진 모양
    check.results.clear()
    pages = {p: check.parse(p) for p in sorted(bad.rglob("*.html"))}
    with contextlib.redirect_stdout(io.StringIO()):
        check.static_checks(bad, json.loads(FIXTURE.read_text(encoding="utf-8")), pages)
    assert [n.split()[0] for n, ok, _ in check.results if not ok] == ["M-1"]


# ---------- F12 두 번째 rename 실패 시 이전 사이트 복구 ----------
def test_f12_second_rename_failure_restores_old_site(tmp_path, monkeypatch):
    b = load_build()
    out = tmp_path / "site"
    assert b.build(FIXTURE, out) > 0
    before = tree_hash(out)
    real = Path.rename
    calls = {"n": 0}

    def flaky(self, target):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("두 번째 rename 실패")
        return real(self, target)

    monkeypatch.setattr(Path, "rename", flaky)
    with pytest.raises(OSError):
        b.build(FIXTURE, out)
    monkeypatch.undo()
    assert tree_hash(out) == before and [p.name for p in tmp_path.iterdir()] == ["site"]


# ---------- F25 엔티티 ----------
def test_f25_entities_survive_token_wrapping(site):
    b = load_build()
    out = b.rich('He said "hi" & it\'s <b> 43점')
    assert "&quot;" in out and "&amp;" in out and "&#x27;" in out and "&lt;b&gt;" in out
    assert not re.search(r'&#?<span|&[a-z]*<span class="nb">(?:quot|amp|lt|gt|x27)', out)
    html = (site / "topic/w41-mid/index.html").read_text(encoding="utf-8")
    visible = Dom(html)
    assert not any(re.search(r"&#\w+;|&(?:quot|amp|lt|gt);", e["text"]) for e in visible.els)  # 파싱한 글자에 엔티티가 그대로 보이면 안 됨


def test_f25_checker_flags_exposed_entity(site, tmp_path):
    import contextlib
    import io
    import shutil

    sys.path.insert(0, str(ROOT / "site_src"))
    import check

    bad = tmp_path / "site"
    shutil.copytree(site, bad)
    f = bad / "topic/w41-mid/index.html"
    f.write_text(f.read_text(encoding="utf-8").replace("it</span>&#x27;s", 'it</span>&#<span class="nb">x27</span>;s'), encoding="utf-8")
    check.results.clear()
    pages = {p: check.parse(p) for p in sorted(bad.rglob("*.html"))}
    with contextlib.redirect_stdout(io.StringIO()):
        check.static_checks(bad, json.loads(FIXTURE.read_text(encoding="utf-8")), pages)
    assert "M-1" in [n.split()[0] for n, ok, _ in check.results if not ok]


# ---------- F50 데이터 원문 글자 보존, F68 내부 근거 id ----------
def test_f50_literal_markup_text_in_data_is_kept_and_passes_m1(site, tmp_path):
    import contextlib
    import io

    sys.path.insert(0, str(ROOT / "site_src"))
    import check

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    t = next(t for t in data["topics"] if t["id"] == "w41-one")
    t["sections"][0]["paragraphs"][0]["text"] = 'HTML 태그 `<span class="x">`를 쓰고 &amp; 문제 &#x27; 확인'
    p = tmp_path / "s.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "site"
    assert run_build(p, out).returncode == 0
    html = (out / "topic/w41-one/index.html").read_text(encoding="utf-8")
    shown = re.sub(r"\s+", " ", "".join(Dom(html).els[i]["text"] for i in range(len(Dom(html).els))))
    assert '<span class="x">' in shown and "&amp; 문제 &#x27; 확인" in shown  # 파싱한 화면 글자가 원문 그대로
    check.results.clear()
    pages = {f: check.parse(f) for f in sorted(out.rglob("*.html"))}
    with contextlib.redirect_stdout(io.StringIO()):
        check.static_checks(out, data, pages)
    assert not [n for n, ok, _ in check.results if n.startswith("M-1") and not ok]


def test_f68_evidence_ids_stripped_from_diagram_context(site, tmp_path):
    import contextlib
    import io
    import shutil

    sys.path.insert(0, str(ROOT / "site_src"))
    import check

    pages_html = "".join(f.read_text(encoding="utf-8") for f in site.rglob("*.html"))
    assert not re.search(r"\[it:|#q\d", pages_html) and "같은 조건." in pages_html  # 설명 글은 남고 id만 빠짐
    bad = tmp_path / "site"
    shutil.copytree(site, bad)
    f = bad / "topic/w41-mid/index.html"
    f.write_text(f.read_text(encoding="utf-8").replace("</main>", "<p>[it:8#q2]</p></main>", 1), encoding="utf-8")
    check.results.clear()
    pages = {p: check.parse(p) for p in sorted(bad.rglob("*.html"))}
    with contextlib.redirect_stdout(io.StringIO()):
        check.static_checks(bad, json.loads(FIXTURE.read_text(encoding="utf-8")), pages)
    assert "M-2" in [n.split()[0] for n, ok, _ in check.results if not ok]


# ---------- F59 site/ 없이 site.old만 남은 경우 복구 ----------
def test_f59_build_restores_old_site_when_site_missing(tmp_path):
    b = load_build()
    out = tmp_path / "site"
    b.build(FIXTURE, out)
    out.rename(tmp_path / "site.old")  # 두 rename 사이에 죽은 상태
    b.build(FIXTURE, out)  # 입력이 정상이면 시작할 때 복구한 뒤 새로 교체
    assert (out / "index.html").is_file() and not (tmp_path / "site.old").exists()


# ---------- F39 수집 URL 스킴 ----------
def test_f39_only_http_urls_become_links(tmp_path):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    t = next(t for t in data["topics"] if t["id"] == "w41-one")
    t["sources"][0]["url"] = "javascript:alert(1)"
    t["sources"][0]["origin"] = "data:text/html,x"
    data["repos"][0]["url"] = "javascript:void(0)"
    data["sources"][0]["url"] = "vbscript:x"
    p = tmp_path / "s.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "site"
    assert run_build(p, out).returncode == 0
    pages = "".join(f.read_text(encoding="utf-8") for f in out.rglob("*.html"))
    assert not re.search(r'href="(?:javascript|data|vbscript):', pages)
    html = (out / "topic/w41-one/index.html").read_text(encoding="utf-8")
    assert "새 설정 방식 소개" in html and "원문 열기" not in html  # 글자는 남고 링크만 빠짐
    assert 'href="https://' in (out / "topic/w41-mid/index.html").read_text(encoding="utf-8")


# ---------- F29 실행 1건: 레일 = steps의 역할 문장, counts = 키-값 ----------
def test_f29_run_page_rail_is_steps_and_counts_are_kv(site):
    d = dom(site, "runs/2026-w41/r41")
    rail = d.find("ol", "rail")
    assert len(rail) == 1 and len([e for e in d.find("li") if inside(e, cls="rail")]) == 3  # 픽스처 steps 3개
    html = (site / "runs/2026-w41/r41/index.html").read_text(encoding="utf-8")
    assert "1차 반려: 수치가 근거와 단위가 달라 수정 요청" in html and html.count('class="check">확인 필요') == 1
    kv = html[html.index('<dl class="kv">', html.index("요약")):]
    assert all(x in kv for x in ("<dt>후보</dt><dd>9</dd>", "<dt>선정</dt><dd>3</dd>", "<dt>근거 id</dt><dd>41</dd>", "<dt>1차 통과</dt><dd>2</dd>",
                                 "<dt>반려</dt><dd>1</dd>", "<dt>확인 필요</dt><dd>3</dd>", "<dt>발행</dt><dd>3</dd>"))
    assert html.count("<h2>반려 비교</h2>") == 1 and "<h3>초안</h3>" in html
