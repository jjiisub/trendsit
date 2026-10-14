"""S6a export(DB → site.json), 주차 표기, W40 월간 근사 목록(A1, A2, A11). 임시 DB만 쓴다(실제 data/trendsit.db는 열지 않음)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from trendsit.core.artifacts_brief import (
    BarGroup,
    EventGroup,
    EventItem,
    NumberItem,
    Para,
    Section,
    TopicPage,
)
from trendsit.core.db import DB
from trendsit.export import ExportError, build, export, stars_text, week_label

ROOT = Path(__file__).resolve().parents[1]


def _spec(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def page(title: str, n_points: int = 3, check_first: bool = False) -> str:
    paras = [Para(text=f"문장 {i}", refs=r)
             for i, r in enumerate([["it:1#q1"], ["it:2#q1"], ["it:1#q2", "rp:a/b"]][:n_points])]
    sections = [Section(heading="절 하나", paragraphs=paras[:2] or [paras[0]], visual="bars", check=check_first,
                        bars=BarGroup(title="수치", context="맥락", unit="%",
                                     items=[NumberItem(label="가", value="10%", ref="it:1#q1", emphasis=True),
                                            NumberItem(label="나", value=5, ref="it:2#q1", baseline=True)]))]
    if len(paras) > 2:
        sections.append(Section(heading="절 둘", paragraphs=[paras[2]], visual="events",
                                events=EventGroup(title="흐름", context="맥락", items=[
                                    EventItem(date="2026-10-06", text="사건", ref="it:1#q1", topic_id=None),
                                    EventItem(date="2026-09-29", text="지난 사건", ref=None, topic_id="w40-x")])))
    return TopicPage(log="x", head_tiles=[], sections=sections, title=title, summary="요약이다. 쟁점이다.").model_dump_json()


def make_db(tmp_path: Path, published: tuple[str, ...] = ("2026-W41",)) -> DB:
    """W40(토픽 1)·W41(토픽 2, 하나는 W40 토픽의 후속) 모양의 행. published에 든 주만 published, 나머지는 done."""
    db = DB(tmp_path / "t.db")
    c = db.conn
    c.executescript("""
    INSERT INTO sources(id, channel, kind, name, feed, enabled, config_json) VALUES
      ('geeknews','text','curation','GeekNews','https://news.hada.io/rss','1','{"note":"큐레이션"}'),
      ('github_trending','github','trending','GitHub Trending','https://github.com/trending?since=weekly','1','{"url":"https://github.com/trending"}');
    INSERT INTO sources(id, channel, kind, name, feed, enabled, config_json) VALUES
      ('ghost','text','curation','yaml에 없는 소스','https://ghost.example/rss','1','{}');
    INSERT INTO items(id, source_id, channel, external_id, url, title, day, week) VALUES
      (1,'geeknews','text','e1','https://example.com/1','글 하나','2026-10-06','2026-W41'),
      (2,'geeknews','text','e2','https://example.com/2','글 둘','2026-10-07','2026-W41'),
      (3,'geeknews','text','e3','https://example.com/3','글 셋','2026-09-29','2026-W40');
    INSERT INTO item_keywords(item_id, keyword_id) VALUES (1,'agent'), (3,'agent');
    INSERT INTO fetch_log(run_id, source_id, day, status, n_new, error, t) VALUES
      ('x','geeknews','2026-10-06','ok',3,NULL,'2026-10-06T02:00:00+09:00'),
      ('x','geeknews','2026-10-07','failed',0,'시간 초과','2026-10-07T02:00:00+09:00');
    INSERT INTO repos(full_name, description) VALUES ('a/b','desc');
    INSERT INTO repo_trending(week, full_name, rank, stars_this_week, run_id, filter_status) VALUES ('2026-W41','a/b',1,1600,'x','pass');
    INSERT INTO repo_oneliners VALUES ('a/b','h','{"oneliner":"에이비 도구"}','m','2026-10-11');
    INSERT INTO repo_cards(week, full_name, card_json) VALUES
      ('2026-W41','a/b','{"relevant":true,"signal":"release","why_trending":"","release":null}');
    """)
    for i in (1, 2, 3):
        card = json.dumps({"summary": f"요약 {i}.", "relevance": "high", "entities": [], "keywords": [],
                           "quotes": [{"n": 1, "text": f"인용 {i}-1"}, {"n": 2, "text": f"인용 {i}-2"}]}, ensure_ascii=False)
        c.execute("INSERT INTO item_cards(item_id, version, card_json) VALUES (?,1,?)", (i, card))
    for wk, run, status in (("2026-W40", "r40", "done"), ("2026-W41", "r41", "done")):
        st = "published" if wk in published else status
        c.execute("INSERT INTO weeks(week, start_day, end_day, status, current_run_id, published_at) VALUES (?,?,?,?,?,?)",
                  (wk, "2026-09-28" if wk == "2026-W40" else "2026-10-05", "2026-10-04" if wk == "2026-W40" else "2026-10-11", st, run,
                   "2026-10-12T07:10:00+09:00" if st == "published" else None))
        summary = {"select": {"candidates": 9, "selected": 2}, "cluster": {"past": {"new": 1, "follow_up": 1, "duplicate": 0}},
                   "review": {"rounds": {"1": 1, "2": 1}, "code_rejects": 1, "critic_rejects": 0, "check_points": 1}}
        c.execute("INSERT INTO runs(id, kind, spec, started_at, finished_at, status, cost_usd, week, summary_json) VALUES (?,?,?,?,?,?,?,?,?)",
                  (run, "weekly", "S5", "2026-10-12T07:00:00+09:00", "2026-10-12T07:18:00+09:00", "ok", 0.05, wk, json.dumps(summary)))
        c.execute("INSERT INTO steps(run_id, seq, t, role, kind, text, attention, detail) VALUES (?,?,?,?,?,?,?,?)",
                  (run, 1, "2026-10-12T07:02:00+09:00", "writer", "llm", "포인트 3개", 0, None))
        c.execute("INSERT INTO steps(run_id, seq, t, role, kind, text, attention, detail) VALUES (?,?,?,?,?,?,?,?)",
                  (run, 2, "2026-10-12T07:11:00+09:00", "critic", "llm", "1차 반려", 1,
                   json.dumps({"draft": "초안", "evidence": "근거", "fixed": "수정"}, ensure_ascii=False)))
    c.execute("INSERT INTO runs(id, kind, spec, started_at, finished_at, status, summary_json) VALUES "
              "('n-skip','nightly','RUN-2026-W41','2026-10-08T02:00:00+09:00','2026-10-08T02:00:01+09:00','skipped',?)",
              (json.dumps({"days": [], "steps": [], "cost_usd": 0.0}),))
    c.execute("INSERT INTO runs(id, kind, spec, started_at, finished_at, status, summary_json) VALUES "
              "('n-w42','nightly','RUN-2026-W42','2026-10-14T02:00:00+09:00','2026-10-14T02:06:00+09:00','ok',?)",
              (json.dumps({"days": ["2026-10-13"], "steps": [], "cost_usd": 0.0}),))  # 발행 안 된 주의 nightly
    c.execute("INSERT INTO runs(id, kind, spec, started_at, finished_at, status, summary_json) VALUES "
              "('n1','nightly','RUN-2026-W41','2026-10-07T02:00:00+09:00','2026-10-07T02:06:00+09:00','partial',?)",
              (json.dumps({"days": ["2026-10-06"], "cost_usd": 0.1, "steps": [
                  {"name": "collect", "day": None, "exit": 0, "sec": 3.2},
                  {"name": "plan", "day": "2026-10-06", "exit": 1, "sec": 1.0, "error": "계획 실패"}]}),))

    def topic(run, tid, week, rank, title, rel_type="new", rel_topic=None, checks="[]", **kw):
        c.execute("INSERT INTO topics(run_id, topic_id, week, cluster_ids_json, rank, lead, relation_type, relation_topic_id, status, "
                  "final_round, title, summary, checks_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (run, tid, week, "[]", rank, rank == 1, rel_type, rel_topic, "checked", 2, title, "요약", checks))
        c.execute("INSERT INTO topic_pages(run_id, topic_id, round, page_json) VALUES (?,?,?,?)", (run, tid, 1, page(title, **kw)))
        for eid, member, field in (("it:1#q1", "it:1", "point"), ("it:2#q1", "it:2", "point"), ("it:1#q2", "it:1", "point"),
                                   ("rp:a/b", "rp:a/b", "point")):
            c.execute("INSERT INTO topic_evidence(run_id, topic_id, evidence_id, member, field, idx) VALUES (?,?,?,?,?,0)",
                      (run, tid, eid, member, field))

    topic("r40", "w40-x", "2026-W40", 1, "W40 토픽", n_points=2)
    topic("r41", "w41-a", "2026-W41", 1, "첫 토픽")
    topic("r41", "w41-b", "2026-W41", 2, "둘째 토픽", "follow_up", "w40-x", '["sections[0]"]', check_first=True)
    c.commit()
    return db


# ---------- A1 ----------
def test_a1_structure_and_only_published(tmp_path):
    site = build(make_db(tmp_path))
    assert list(site) == ["meta", "weeks", "topics", "repos", "sources", "keywords", "runs", "run_weeks"]
    assert not {"example", "notice", "markup"} & set(site["meta"])
    assert set(site["meta"]) == {"product", "generated_at", "signal_labels", "channel_labels", "channel_labels_topic"}
    # C-1: 발행 주(W41)만. W40 주·토픽·레포·실행은 없음
    assert [w["id"] for w in site["weeks"]] == ["2026-w41"]
    assert {t["week"] for t in site["topics"]} == {"2026-w41"} and {r["week"] for r in site["repos"]} == {"2026-w41"}
    # D-12: steps가 빈 nightly(n-skip 건너뜀, n-w42 범위 없음)는 안 낸다. 발행 안 된 W40은 run(r40)이 있어 진행 주로 run_weeks에 든다(5.2-1)
    assert {r["id"] for r in site["runs"]} == {"n1", "r40", "r41"}
    w = site["weeks"][0]
    assert w == {"id": "2026-w41", "label": "10월 2주차", "range": "10.5 ~ 10.11",
                 "published_at": "2026-10-12T07:10:00+09:00", "collected": {"text": 2, "video": 0, "github": 0},
                 "topic_ids": ["w41-a", "w41-b"], "topic_count": 2, "source_count": 3, "trending_approx": False}
    t = {x["id"]: x for x in site["topics"]}
    assert t["w41-b"]["relation"] == {"type": "follow_up", "topic_id": "w40-x"} and t["w41-b"]["has_check"]
    assert "cross_checked" not in t["w41-a"]
    for x in site["topics"]:  # C-2
        ids = {s["id"] for s in x["sources"]}
        for sec in x["sections"]:
            assert all(p["refs"] and set(p["refs"]) <= ids for p in sec["paragraphs"])
    assert [(r["name"], r["stars_7d"], r["signal"], r["what"], r["topic_id"]) for r in site["repos"]] == [
        ("a/b", "+1.6k", "release", "에이비 도구", "w41-a")]
    assert "ghost" not in {s["id"] for s in site["sources"]}  # sources.yaml에 없는 소스는 제외
    gk = next(s for s in site["sources"] if s["id"] == "geeknews")
    assert gk["daily"] == {"2026-w41": [0, 1, 1, 0, 0, 0, 0]}  # 10.6(화), 10.7(수)
    assert gk["weeks"] == {"2026-w41": {"collected": 2, "failed_days": 1, "used_in_topics": 2}}
    assert gk["last"] == {"at": "2026-10-07T02:00:00+09:00", "count": 0, "status": "failed"} and gk["last_error"] == "시간 초과"
    assert gk["note"] == "큐레이션" and gk["enabled"] is True
    assert next(s for s in site["sources"] if s["id"] == "github_trending")["url"] == "https://github.com/trending?since=weekly"
    kw = site["keywords"]
    assert kw["weeks"] == ["2026-w41"] and next(i for i in kw["items"] if i["id"] == "agent")["mentions"] == [1]
    assert next(i for i in kw["items"] if i["id"] == "agent")["topics"] == ["w41-a", "w41-b"]
    run = next(r for r in site["runs"] if r["id"] == "r41")
    assert (run["kind"], run["week"], run["mode"], run["current"], run["label"], run["sub"], run["topic_id"]) == ("weekly", "2026-w41", "manual", True, "", True, None)
    assert run["result"] == {"clusters": None, "candidates": 9, "selected": 2, "topics": None, "code_rejects": 1, "check_topics": None}
    assert run["summary"] == {"clusters": None, "candidates": 9, "selected": 2, "topics": None, "published": 2, "rounds": {"1": 1, "2": 1},
                              "code_rejects": 1, "critic_rejects": 0, "check_topics": None}  # published = 현재판이면 사이트에 실리는 토픽 수
    assert [(s["name"], s["t"], s["attention"]) for s in run["steps"]] == [("writer ⇄ critic", "07:02", True)]  # steps 두 행(writer, critic llm)이 한 단계
    night = next(r for r in site["runs"] if r["id"] == "n1")
    assert (night["label"], night["mode"], night["week"], night["status"], night["cost_usd"], night["result"]) == (
        "nightly 10.6", "auto", "2026-w41", "partial", 0.1, {"steps": 2, "failed": 1})  # 비용은 summary_json 값
    assert [(s["name"], s["line"], s["attention"], s["detail"]) for s in night["steps"]] == [
        ("collect", "exit 0", False, []), ("plan", "exit 1", True, [])]  # 하위 run이 없으면 line만(오류 원문은 내지 않음)
    assert [rw["week"] for rw in site["run_weeks"]] == ["2026-w41", "2026-w40"]
    assert site["run_weeks"][0] == {"week": "2026-w41", "label": "10월 2주차", "range": "10.5 ~ 10.11", "status": "published", "nightly_days": 1,
                                    "weekly": {"total": 1, "full": 0, "partial": 1, "topic": 0}, "published_at": "2026-10-12T07:10:00+09:00",
                                    "current_run_id": "r41"}
    assert site["run_weeks"][1]["status"] == "done" and site["run_weeks"][1]["published_at"] is None


def test_a1_with_week_includes_unpublished_week_and_export_failures_keep_file(tmp_path):
    db = make_db(tmp_path)
    out = tmp_path / "site.json"
    export(db, out, with_week="2026-W40")
    assert [w["id"] for w in json.loads(out.read_text())["weeks"]] == ["2026-w41", "2026-w40"]
    assert [rw["status"] for rw in json.loads(out.read_text())["run_weeks"]] == ["published", "published"]  # with_week의 주도 발행 주로 센다
    before = out.read_text()
    # C-2 위반: 포인트 refs가 비면 실패하고 기존 파일은 그대로
    db.conn.execute("UPDATE topic_evidence SET evidence_id='zz' WHERE run_id='r41' AND topic_id='w41-a' AND evidence_id='it:2#q1'")
    db.conn.commit()
    with pytest.raises(ExportError, match="C-2"):
        export(db, out)
    assert out.read_text() == before
    # published 주가 없으면 실패
    (tmp_path / "x").mkdir()
    with pytest.raises(ExportError):
        export(make_db(tmp_path / "x", published=()), out)
    assert out.read_text() == before


def test_topic_ref_slots_covers_tiles_table_events_not_just_paragraphs():
    """006-A1-15: C-2가 단락 refs만 보지 않고 head_tiles·table·tiles·events도 봄."""
    from trendsit.export import _topic_ref_slots

    t = {"head_tiles": [{"value": "1", "refs": ["s1"]}],
         "sections": [{"paragraphs": [{"refs": ["s1"]}],
                       "visual": {"type": "tiles", "items": [{"value": "1", "refs": ["s1", "zz"]}]}},
                      {"paragraphs": [{"refs": ["s1"]}], "visual": {"type": "table", "refs": ["s1", "zz"]}},
                      {"paragraphs": [{"refs": ["s1"]}],
                       "visual": {"type": "events", "items": [{"ref": "zz"}, {"ref": None}]}}]}
    slots = dict(_topic_ref_slots(t))
    assert slots["sections[0].tiles[0]"] == ["s1", "zz"]
    assert slots["sections[1].table"] == ["s1", "zz"]
    assert slots["sections[2].events.items[0]"] == ["zz"]
    assert "sections[2].events.items[1]" not in slots  # ref 없는 사건은 topic_id로 받침, C-2 대상 아님


def test_a1_cli_exit_codes(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from trendsit.cli_ops import cmd_export

    monkeypatch.setattr("trendsit.core.db.open_db", lambda *a, **k: make_db(tmp_path))
    out = tmp_path / "o" / "site.json"
    assert cmd_export(SimpleNamespace(out=str(out))) == 0 and out.exists()
    (tmp_path / "e").mkdir()
    monkeypatch.setattr("trendsit.core.db.open_db", lambda *a, **k: DB(tmp_path / "e" / "empty.db"))
    out2 = tmp_path / "o2.json"
    assert cmd_export(SimpleNamespace(out=str(out2))) == 1 and not out2.exists()


# ---------- A2 ----------
@pytest.mark.parametrize("week,label,rng", [
    ("2026-W39", "9월 4주차", "9.21 ~ 9.27"),
    ("2026-W40", "10월 1주차", "9.28 ~ 10.4"),
    ("2026-W41", "10월 2주차", "10.5 ~ 10.11"),
    ("2026-W42", "10월 3주차", "10.12 ~ 10.18"),
    ("2026-W53", "12월 5주차", "12.28 ~ 1.3"),  # 목요일이 12/31
    ("2027-W01", "1월 1주차", "1.4 ~ 1.10"),
])
def test_a2_week_label(week, label, rng):
    assert week_label(week)[:2] == (label, rng)


def test_a2_stars_text():
    assert [stars_text(n) for n in (None, 950, 1000, 1600, 21365)] == [None, "+950", "+1.0k", "+1.6k", "+21.4k"]


def test_f69_github_collected_counts_repo_trending(tmp_path):
    site = build(make_db(tmp_path))
    gh = next(s for s in site["sources"] if s["id"] == "github_trending")
    assert gh["weeks"]["2026-w41"]["collected"] == 1  # items에는 없고 repo_trending 행(그 주)만 있음
    assert "daily" not in gh  # 요일별 원천이 없으니 [0]*7로 collected와 어긋나지 않게 칸을 두지 않음


# ---------- A11 ----------
def monthly():
    from trendsit.collect.github import parse_trending

    html = (ROOT / "tests/fixtures/site/trending_monthly.html").read_text(encoding="utf-8")  # 실제 월간 페이지에서 저장한 앞 13행
    return html, [r["full_name"] for r in parse_trending(html)]


def counts(db):
    return [db.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("runs", "repo_trending", "repos", "repo_oneliners")]


def test_a11_trending_monthly_approx(tmp_path):
    tm = _spec("scripts/trending_monthly.py", "trending_monthly")
    html, names13 = monthly()
    assert len(names13) == 13
    db = make_db(tmp_path, published=("2026-W40", "2026-W41"))
    # 대상 주(W40) 뒤의 주(W41)에 이미 있는 두 레포는 뺀다. 앞선 주(W39)에 있는 레포는 빼지 않는다
    for name in (names13[1], names13[4]):
        db.conn.execute("INSERT INTO repo_trending(week, full_name, rank, run_id) VALUES ('2026-W41',?,9,'x')", (name,))
    db.conn.execute("INSERT INTO repo_trending(week, full_name, rank, run_id) VALUES ('2026-W39',?,9,'x')", (names13[0],))
    db.conn.commit()
    calls = []

    def fetch(url):
        calls.append(url)
        return html, None

    code, todo = tm.run(db, "2026-W40", fetch)
    rows = db.conn.execute("SELECT * FROM repo_trending WHERE week='2026-W40' ORDER BY rank").fetchall()
    want = [n for i, n in enumerate(names13) if i not in (1, 4)][:10]
    assert code == 0 and len(calls) == 1 and calls[0].endswith("since=monthly")
    assert len(rows) == 10 and [r["rank"] for r in rows] == list(range(1, 11))
    assert [r["full_name"] for r in rows] == todo == want and want[0] == names13[0]
    assert all(r["stars_this_week"] is None for r in rows) and rows[0]["stars_total"] > 0
    note = db.conn.execute("SELECT kind, note FROM runs WHERE id=?", (rows[0]["run_id"],)).fetchone()
    assert tuple(note) == ("collect", "trending monthly approx")
    # 두 번 실행해도 행 수 같음(받지도 않음). oneliner가 없는 레포는 계속 돌려준다
    before = counts(db)
    assert tm.run(db, "2026-W40", fetch) == (0, want) and len(calls) == 1 and counts(db) == before
    # 일부만 oneliner가 채워진 뒤 다시 돌리면 나머지만 돌려줌(중간 실패 복구)
    for name in want[:3]:
        db.conn.execute("INSERT INTO repo_oneliners VALUES (?,?,?,?,?)", (name, "h", json.dumps({"oneliner": f"{name} 설명"}), "m", "2026-10-11"))
    db.conn.commit()
    assert tm.run(db, "2026-W40", fetch) == (0, want[3:])
    # export: trending_approx, 별 없이(stars_7d null), 한 줄 설명이 있는 레포만
    site = build(db)
    w40 = next(w for w in site["weeks"] if w["id"] == "2026-w40")
    assert w40["trending_approx"] is True and not next(w for w in site["weeks"] if w["id"] == "2026-w41")["trending_approx"]
    r40 = [r for r in site["repos"] if r["week"] == "2026-w40" and not r["topic_id"]]  # 토픽 근거 레포(a/b)는 따로 포함
    assert [(r["name"], r["stars_7d"]) for r in r40] == [(n, None) for n in want[:3]]


def test_a11_failure_leaves_db_unchanged(tmp_path, monkeypatch):
    tm = _spec("scripts/trending_monthly.py", "trending_monthly2")
    db = make_db(tmp_path)
    before = counts(db) + [db.conn.execute("SELECT COUNT(*) FROM runs WHERE kind='role'").fetchone()[0]]

    def snap():
        return counts(db) + [db.conn.execute("SELECT COUNT(*) FROM runs WHERE kind='role'").fetchone()[0]]

    for result in ((None, "HTTP 500"), ("<html>빈 페이지</html>", None)):
        assert tm.run(db, "2026-W40", lambda url, r=result: r) == (1, [])
        assert snap() == before
        # main()도: 받기 실패면 LLM 실행 기록(runs 행)을 만들지 않고 종료 1
        monkeypatch.setattr("trendsit.core.db.open_db", lambda *a, **k: db)
        monkeypatch.setattr("trendsit.core.context.open_ctx", lambda *a, **k: pytest.fail("open_ctx를 부르면 안 됨"))
        assert tm.main(["--week", "2026-W40"], fetch=lambda url, r=result: r) == 1
        assert snap() == before
    # 월간 목록이 전부 그 뒤 주 레포면 고를 게 없음: DB 변경 없이 1
    html, names13 = monthly()
    for name in names13:
        db.conn.execute("INSERT OR IGNORE INTO repo_trending(week, full_name, rank, run_id) VALUES ('2026-W41',?,9,'x')", (name,))
    db.conn.commit()
    before_all = snap()
    assert tm.run(db, "2026-W40", lambda url: (html, None)) == (1, []) and snap() == before_all
    db.conn.execute("DELETE FROM repo_trending WHERE week='2026-W41' AND rank=9")
    db.conn.commit()
    # 저장 도중 실패하면 runs 행도 남지 않음(한 트랜잭션)
    db.conn.execute("CREATE TRIGGER boom BEFORE INSERT ON repo_trending BEGIN SELECT RAISE(ABORT, 'x'); END")
    with pytest.raises(Exception, match="x"):
        tm.run(db, "2026-W40", lambda url: (html, None))
    assert snap() == before


def test_f33_keywords_and_used_members_only_for_exported_topics(tmp_path):
    db = make_db(tmp_path)
    db.conn.execute("DELETE FROM topic_pages WHERE topic_id='w41-b'")  # 작성 실패(페이지 없음): 사이트에서 빠진다
    db.conn.execute("INSERT INTO topic_evidence(run_id, topic_id, evidence_id, member, field, idx) VALUES ('r41','w41-b','it:3#q1','it:3','point',0)")
    db.conn.execute("UPDATE items SET week='2026-W41' WHERE id=3")  # 빠진 토픽만 쓰는 글(키워드 agent도 가짐)
    db.conn.commit()
    site = build(db)
    assert [t["id"] for t in site["topics"]] == ["w41-a"]
    assert next(i for i in site["keywords"]["items"] if i["id"] == "agent")["topics"] == ["w41-a"]  # w41-b는 없음
    assert next(s for s in site["sources"] if s["id"] == "geeknews")["weeks"]["2026-w41"]["used_in_topics"] == 2  # it:3은 빠진 토픽만 씀
