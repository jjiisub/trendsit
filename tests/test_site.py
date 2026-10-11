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
from trendsit.export import export

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


# ---------- A3 ----------
def test_a3_diagrams_after_anchor_point_and_source_numbers(site):
    d = dom(site, "topic/w41-long")
    pts = [e["id"] for e in d.find("li", "pt")]
    assert pts == ["pt-1", "pt-2", "pt-3", "pt-4", "pt-5"]
    figs = d.find("figure")
    # C-8: 도식은 모두 anchor 포인트(2번) 안, 포인트 문장 다음에. 같은 포인트에서 수치 → 사건 → 타임라인
    assert [tuple(c for c in f["cls"] if c != "dg") for f in figs] == [("dg-bars",), ("dg-events",), ("dg-video",)]
    assert all(inside(f, id_="pt-2") for f in figs)
    p2 = [e for e in d.els if inside(e, id_="pt-2")]
    assert next(i for i, e in enumerate(p2) if "pt-x" in e["cls"]) < next(i for i, e in enumerate(p2) if e["tag"] == "figure")
    assert d.find("ol", "vtl") and inside(d.find("ol", "vtl")[0], id_="pt-2")  # 영상 v1을 처음 인용한 포인트
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
    # 도식 없는 토픽에는 도식 없음, 수치 막대는 anchor 1번 포인트 아래
    assert not dom(site, "topic/w41-one").find("figure")
    mid = dom(site, "topic/w41-mid")
    assert [inside(f, id_="pt-1") for f in mid.find("figure")] == [True]


def test_a3_topic_blocks_order_and_links(site):
    html = (site / "topic/w41-long/index.html").read_text(encoding="utf-8")
    order = [html.index(x) for x in ('id="h-ov"', 'id="h-pt"', 'id="h-cc"', 'id="h-cb"', 'id="h-src"', 'class="pn"')]
    assert order == sorted(order)
    assert html.index('class="follow"') < order[0] and "/topic/w40-base/" in html  # 대상이 있는 후속은 지난 흐름 링크
    assert 'class="follow"' not in (site / "topic/w41-one/index.html").read_text(encoding="utf-8")  # 대상 없는 후속은 링크 없음
    one = dom(site, "topic/w41-one")
    assert not one.find("nav", "pn") or all("w41-" in (e["href"] or "") for e in one.find("a", "pn-next") + one.find("a", "pn-prev"))
    assert "<script" not in html and 'title="' not in html


# ---------- A4 ----------
class ChkWalk(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.depth_end, self.chk, self.chk_in_end, self.stack = 0, 0, 0, []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "").split()
        self.stack.append((tag, "nb-end" in cls))
        if "chk" in cls:
            self.chk += 1
            self.chk_in_end += any(e for _, e in self.stack[:-1])

    def handle_endtag(self, tag):
        while self.stack and self.stack.pop()[0] != tag:
            pass


@pytest.mark.parametrize("tid,total,in_points", [("w41-long", 3, 1), ("w41-one", 0, 0), ("w41-mid", 0, 0), ("w40-base", 0, 0)])
def test_a4_check_marks(site, tid, total, in_points):
    w = ChkWalk((site / "topic" / tid / "index.html").read_text(encoding="utf-8"))
    assert w.chk == total  # C-9: 포인트 1(points[0]) + 개요 + 개념[0]. '빠진 도식'은 표시 안 함
    assert w.chk_in_end == in_points  # 포인트의 표기는 인용과 같은 .nb-end 묶음 안


def test_a4_home_meta_has_check(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    items = html.split('<li class="it">')[1:]
    assert ["확인 필요" in re.search(r'<p class="tmeta.*?</p>', i).group(0) for i in items] == [True, False, False]
    assert 'class="chk"' not in html  # 홈 메타의 표기는 .chk가 아니라 글자만


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
    del data["topics"][0]["points"]  # 렌더링 도중 실패
    half = tmp_path / "half.json"
    half.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert run_build(half, out).returncode == 1
    assert tree_hash(out) == before and not [p for p in tmp_path.iterdir() if ".tmp-" in p.name]  # 바이트 그대로, 임시 폴더 정리


def test_a12_publish_runs_export_then_build_and_failure_keeps_site(tmp_path):
    db = make_db(tmp_path, published=())
    site_dir, data = tmp_path / "site", tmp_path / "site.json"
    calls: list[str] = []
    corrupt = {"on": False}

    def runner(cmd):
        if cmd[: len(ops.EXPORT_CMD)] == ops.EXPORT_CMD:
            calls.append("export")
            export(db, data, cmd[-1])
            if corrupt["on"]:
                data.write_text("{ 깨짐", encoding="utf-8")
            return 0, "", ""
        assert cmd == ops.BUILD_CMD
        calls.append("build")
        r = run_build(data, site_dir)
        return r.returncode, r.stdout, r.stderr

    assert ops.publish(db, "2026-W41", runner) == 0
    assert calls == ["export", "build"]
    row = db.conn.execute("SELECT status, published_at FROM weeks WHERE week='2026-W41'").fetchone()
    assert row["status"] == "published" and (site_dir / "week/2026-w41/index.html").is_file()
    assert (site_dir / "topic/w41-a/index.html").is_file()
    before = tree_hash(site_dir)
    # 다음 주 발행에서 build가 실패하면: site/ 바이트 그대로, 상태 그대로(done)
    corrupt["on"] = True
    assert ops.publish(db, "2026-W40", runner) == 1
    assert tree_hash(site_dir) == before
    assert db.conn.execute("SELECT status FROM weeks WHERE week='2026-W40'").fetchone()[0] == "done"
    assert calls == ["export", "build", "export", "build"]
