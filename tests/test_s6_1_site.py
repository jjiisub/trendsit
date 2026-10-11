"""S6-1 작은 보완(S-1): 홈 탭 앵커, 키워드 캡, 실행 1건 메타, 출처 단일 목록, 레포 메타, 대체 계획 표시, backup.
새 토픽 v2 화면(절 구조·타일·표·슬라이드)은 tests/test_s6_1_write.py(작성 로직) + S-3에서 이 파일에 더한다.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_export import make_db
from trendsit.core.db import DB
from trendsit.export import build as export_build

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "site_src" / "build.py"
FIXTURE = ROOT / "tests" / "fixtures" / "site" / "site.json"
V2_FIXTURE = ROOT / "tests" / "fixtures" / "s6_1" / "site_v2.json"


def run_build(data: Path, out: Path):
    return subprocess.run([sys.executable, str(BUILD), "--data", str(data), "--out", str(out)], capture_output=True, text=True)


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("s6_1_fx") / "site"
    r = run_build(FIXTURE, out)
    assert r.returncode == 0, r.stderr
    return out


def home_html(site: Path) -> str:
    return (site / "index.html").read_text(encoding="utf-8")


# ---------- 5.1-1 홈 탭 앵커 ----------
def test_tab_anchor_spans_above_tabs_nav(site):
    html = home_html(site)
    anchor_idx = [m.start() for m in re.finditer(r'<span class="tab-anchor" id="(topics|repos)">', html)]
    tabs_idx = html.index('<nav class="tabs"')
    assert len(anchor_idx) == 2 and all(i < tabs_idx for i in anchor_idx)
    # 패널은 panel-topics / panel-repos로, #topics·#repos는 앵커 전용(id 중복 없음)
    ids = re.findall(r' id="([^"]+)"', html)
    assert ids.count("topics") == 1 and ids.count("repos") == 1
    assert 'id="panel-topics"' in html and 'id="panel-repos"' in html
    assert '<a class="tb-t" href="#topics">' in html and '<a class="tb-r" href="#repos">' in html


# ---------- 5.1-2 키워드 ----------
def test_keyword_topic_links_capped_at_5_with_overflow_count(site):
    html = (site / "keywords/index.html").read_text(encoding="utf-8")
    # 픽스처는 토픽 링크가 5개 미만이라 "외 n개"가 없음을 먼저 확인하고, 6개짜리를 따로 만들어 캡을 확인
    assert "외" not in html or "개</td>" not in html
    sys.path.insert(0, str(ROOT / "site_src"))
    import build as b

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    topic_ids = [t["id"] for t in data["topics"]]
    many = (topic_ids * 3)[:7]
    data["keywords"]["items"].append({"id": "many", "name": "많은 키워드", "aliases": [], "mentions": [0, 0, 0], "topics": many})
    b.load(data)
    b.C.css_name = "x.css"
    out = b.render_keywords()
    assert out.count('<a href="/topic/') >= 5
    assert ", 외 2개" in out


# ---------- 5.1-3 실행 1건 ----------
def test_run_meta_line_published_and_written_counts(tmp_path):
    db = make_db(tmp_path, published=("2026-W41",))
    db.conn.execute("INSERT INTO steps(run_id, seq, t, role, kind, text, attention) VALUES ('r41', 100, "
                    "'2026-10-12T07:12:00+09:00', 'writer', 'code', 'w41-a: passed, 1라운드', 0)")
    db.conn.execute("INSERT INTO steps(run_id, seq, t, role, kind, text, attention) VALUES ('r41', 101, "
                    "'2026-10-12T07:13:00+09:00', 'writer', 'code', 'w41-b: checked, 2라운드', 0)")
    db.conn.commit()
    site = export_build(db)
    run = next(r for r in site["runs"] if r["id"] == "r41")
    assert run["counts"]["written"] == 2
    sys.path.insert(0, str(ROOT / "site_src"))
    import build as b

    b.load(site)
    b.C.css_name = "x.css"
    html = b.render_run(run)
    assert '<p class="meta">이 주 발행 2개 / 이 실행이 쓴 토픽 2개</p>' in html


# ---------- 5.1-4 출처: 채널 머리 제거, 단일 목록 ----------
def test_source_list_is_single_list_without_channel_headers(site):
    html = (site / f"topic/{json.loads(FIXTURE.read_text(encoding='utf-8'))['topics'][0]['id']}/index.html").read_text(encoding="utf-8")
    assert "<h3" not in html and 'class="src-g"' not in html
    assert html.count('<ol class="srcs">') == 1


# ---------- 5.1-5 레포 메타 줄 ----------
def test_repo_meta_line_uses_slash_separator_not_middle_dot(site):
    html = (site / "week/2026-w40/index.html").read_text(encoding="utf-8")
    m = re.search(r'<p class="rp-m meta">([^<]*(?:<[^>]+>[^<]*)*)</p>', html)
    assert m
    assert "·" not in re.sub(r"<[^>]+>", "", m.group(0))
    assert " / " in m.group(0) or "class=\"check\"" in m.group(0)


# ---------- 5.1-8 대체 계획 표시 ----------
def test_fallback_select_shows_meta_line_and_plan_step_shows_suffix(tmp_path):
    db = make_db(tmp_path, published=("2026-W41",))
    db.conn.execute("INSERT INTO briefing_plans(run_id, week, source, plan_json) VALUES ('r41','2026-W41','fallback','{}')")
    db.conn.execute("INSERT INTO plans(day, run_id, source, plan_json) VALUES ('2026-10-06','n1','fallback','{}')")
    db.conn.commit()
    site = export_build(db)
    run = next(r for r in site["runs"] if r["id"] == "r41")
    assert run.get("fallback_select") is True
    night = next(r for r in site["runs"] if r["id"] == "n1")
    assert any(s.get("fallback") for s in night["steps"])
    sys.path.insert(0, str(ROOT / "site_src"))
    import build as b

    b.load(site)
    b.C.css_name = "x.css"
    assert "선별 대체 계획(점수 순)" in b.render_run(run)
    assert "(대체 계획)" in b.render_run(night)


# ---------- 5.1-9 backup ----------
def test_backup_creates_consistent_copy_without_touching_original(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db = DB(data_dir / "trendsit.db")
    db.conn.execute("INSERT INTO runs(id, kind, started_at) VALUES ('x','nightly','2026-10-12T00:00:00+09:00')")
    db.conn.commit()
    before = (data_dir / "trendsit.db").read_bytes()
    dest = tmp_path / "backup" / "20261012-0000-pre.db"
    db.backup(dest)
    assert dest.is_file()
    after = (data_dir / "trendsit.db").read_bytes()
    assert before == after
    copy = DB(dest)
    assert copy.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert copy.conn.execute("SELECT id FROM runs").fetchone()[0] == "x"


def test_backup_cli_rejects_existing_name(tmp_path, monkeypatch):
    from trendsit import cli_ops
    from trendsit.core import config as cfgmod

    monkeypatch.setattr(cfgmod, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    DB(tmp_path / "data" / "trendsit.db").conn.close()
    dest_dir = tmp_path / "data" / "backup"
    dest_dir.mkdir(parents=True)
    import datetime

    now = datetime.datetime.now(__import__("trendsit.core.db", fromlist=["KST"]).KST)
    existing = dest_dir / f"{now.strftime('%Y%m%d-%H%M')}-dup.db"
    existing.write_bytes(b"x")

    class Args:
        tag = "dup"

    assert cli_ops.cmd_backup(Args()) == 1


def test_backup_cli_rejects_bad_tag_and_missing_db(tmp_path, monkeypatch):
    """006-A1-37: --tag에 경로 문자가 있거나 원본 DB가 없으면 1(빈 DB를 새로 만들어 백업하지 않음)."""
    from trendsit import cli_ops
    from trendsit.core import config as cfgmod

    monkeypatch.setattr(cfgmod, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()

    class Args:
        tag = "../x"

    assert cli_ops.cmd_backup(Args()) == 1
    assert not (tmp_path / "data" / "trendsit.db").exists()  # 검증만 하고 DB를 만들지 않음

    class Args2:
        tag = None

    assert cli_ops.cmd_backup(Args2()) == 1
    assert not (tmp_path / "data" / "trendsit.db").exists()  # 원본 없음 → open_db()로 새로 만들지 않고 거부


# ---------- A9: build 토픽(v2 픽스처, 5.8) ----------
@pytest.fixture(scope="module")
def site_v2(tmp_path_factory):
    # llamaindex 토픽의 슬라이드 이미지는 data/slides/에서 build가 복사한다(5.6). 실제 data/slides/를 건드리지
    # 않게(006-A1-17) 임시 루트에서 build.ROOT를 바꿔 in-process로 빌드한다(subprocess면 ROOT를 못 바꿈)
    sys.path.insert(0, str(ROOT / "site_src"))
    import build as b

    tmp_root = tmp_path_factory.mktemp("s6_1_v2_root")
    names = ["S-bRN-avZ4Q_208.jpg", "S-bRN-avZ4Q_422.jpg"]
    slides_dir = tmp_root / "data" / "slides"
    slides_dir.mkdir(parents=True)
    for n in names:
        (slides_dir / n).write_bytes(b"\xff\xd8\xff\xdb" + b"\x00" * 16)
    old_root = b.ROOT
    b.ROOT = tmp_root
    try:
        out = tmp_path_factory.mktemp("s6_1_v2") / "site"
        n = b.build(str(V2_FIXTURE), str(out))
        assert n > 0
        yield out
    finally:
        b.ROOT = old_root


def _topic_html(site_v2, tid):
    return (site_v2 / "topic" / tid / "index.html").read_text(encoding="utf-8")


def test_a9_head_tiles_counts_0_to_4(site_v2):
    assert '<div class="tiles-wrap">' not in _topic_html(site_v2, "w41-agent-slop-state-machine")  # 0개
    assert 'class="tiles n4"' in _topic_html(site_v2, "w41-embedding-gemma-2")
    assert 'class="tiles n1"' in _topic_html(site_v2, "w41-openrig-multi-agent")
    assert 'class="tiles n2"' in _topic_html(site_v2, "w41-claude-haiku-5-5")
    assert 'class="tiles n3"' in _topic_html(site_v2, "w41-mistral-large-4")


def test_a9_table_bars_events_present(site_v2):
    assert "dg-table" in _topic_html(site_v2, "w41-claude-haiku-5-5")
    assert "dg-bars" in _topic_html(site_v2, "w41-embedding-gemma-2")
    assert "dg-events" in _topic_html(site_v2, "w41-openrig-multi-agent")


def test_a9_slide_and_video_timeline(site_v2):
    html = _topic_html(site_v2, "w40-llamaindex-context-layer")
    assert html.count('class="simg"') == 2
    assert 'loading="lazy"' in html and "&t=" in html
    assert 'class="vtl"' in html


def test_a9_check_marks_section_and_summary(site_v2):
    html = _topic_html(site_v2, "w41-claude-haiku-5-5")
    assert html.count('class="chk"') == 2
    assert '<a class="fu" href="#chk-1">확인 필요</a>' in html


def test_a9_single_section_topic_and_long_heading(site_v2):
    html = _topic_html(site_v2, "w41-agent-slop-state-machine")
    assert html.count('class="dsec"') == 1
    long_html = _topic_html(site_v2, "w41-mistral-large-4")
    assert "세부 조건과 비교 대상을 함께 담아 평소보다 길게 쓴 절 제목" in long_html


def test_a9_no_broken_markup_across_all_topics(site_v2):
    sys.path.insert(0, str(ROOT / "site_src"))
    import check

    for f in sorted(site_v2.rglob("*.html")):
        p = check.parse(f)
        assert not p.mismatch and not p.open, f
