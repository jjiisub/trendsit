"""S7a 실행 기록: export(run 선택·분류·상세 칸, A2·A3), publish --site-only(A1), 화면 파싱(A4·A5). 임시 DB·픽스처만 쓴다."""

from __future__ import annotations

import json

import pytest

from tests.test_export import make_db
from trendsit import ops
from trendsit.core.db import DB
from trendsit.export import build

N0 = "2026-10-13T02:00:06+09:00"


def run(c, id_, kind, started, finished=None, status="ok", spec="S5", note=None, week=None, cost=0.0, summary=None):
    c.execute("INSERT INTO runs(id, kind, spec, started_at, finished_at, status, cost_usd, note, week, summary_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
              (id_, kind, spec, started, finished, status, cost, note, week, json.dumps(summary, ensure_ascii=False) if summary is not None else None))


def step(c, run_id, seq, role, kind, text, t="2026-10-13T02:00:10+09:00", attention=0, detail=None, model=None, tin=None, tout=None, cost=None, output=None):
    c.execute("INSERT INTO steps(run_id, seq, t, role, kind, text, attention, detail, model, tokens_in, tokens_out, cost_usd, output) "
              "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (run_id, seq, t, role, kind, text, attention, json.dumps(detail, ensure_ascii=False) if detail is not None else None, model, tin, tout, cost,
               json.dumps(output, ensure_ascii=False) if output is not None else None))


def selection_db(tmp_path):
    """make_db(W41 발행·W40 done) 위에 run 선택 경계를 얹는다: auto·manual nightly, full·partial·topic·week NULL·running weekly, ③ 묶음, 개발용, 진행 주(W42)."""
    db = make_db(tmp_path)
    c = db.conn
    c.execute("UPDATE runs SET note='weekly 2026-W41 from cluster' WHERE id='r41'")  # 현재판 full
    run(c, "w-part", "weekly", "2026-10-09T10:00:00+09:00", "2026-10-09T10:05:00+09:00", note="weekly 2026-W41 from select", week="2026-W41")
    run(c, "w-topic", "weekly", "2026-10-09T11:00:00+09:00", "2026-10-09T11:01:00+09:00", "partial", "S6-1", "weekly 2026-W41 from write topic w41-a", "2026-W41", 0.01)
    run(c, "w-auto", "weekly", "2026-10-12T07:00:00+09:00", "2026-10-12T07:20:00+09:00", spec="RUN-2026-W41", note="weekly 2026-W41 from cluster", week="2026-W41")
    run(c, "w-null", "weekly", "2026-10-09T09:00:00+09:00", "2026-10-09T09:01:00+09:00", note="cluster embed compare 2026-W41")
    run(c, "w-run", "weekly", "2026-10-09T12:00:00+09:00", None, "running", note="weekly 2026-W41 from write (중단: 다시 실행)", week="2026-W41")
    run(c, "n-man", "nightly", "2026-10-09T08:00:00+09:00", "2026-10-09T08:10:00+09:00", spec="RUN-2026-W41",
        summary={"days": ["2026-10-08", "2026-10-09"], "steps": [{"name": "collect", "day": None, "exit": 0, "sec": 5.0}], "cost_usd": 0.2, "manual": True})
    run(c, "n-new", "nightly", "2026-10-13T02:00:00+09:00", "2026-10-13T02:10:00+09:00", spec="RUN-2026-W42",
        summary={"days": ["2026-10-12"], "steps": [{"name": "collect", "day": None, "exit": 0, "sec": 5.0}], "cost_usd": 0.1})
    for d in ("2026-10-07", "2026-10-08"):  # 수동 단계별 run 2날
        run(c, f"c-{d}", "collect", f"{d}T10:00:00+09:00", f"{d}T10:01:00+09:00", spec="S1", cost=0.5)
    run(c, "f-1007", "filter", "2026-10-07T11:00:00+09:00", "2026-10-07T11:01:00+09:00", "failed", "S2", cost=0.25)
    run(c, "x-role", "role", "2026-10-09T10:00:00+09:00", "2026-10-09T10:00:01+09:00")  # 개발용: 안 냄
    run(c, "x-eval", "eval", "2026-10-09T10:00:00+09:00", "2026-10-09T10:00:01+09:00")
    run(c, "x-sub", "plan", N0, N0, spec="RUN-2026-W42")  # nightly 하위(spec RUN-): ③에 안 들어감
    c.commit()
    return db


def by_id(site):
    return {r["id"]: r for r in site["runs"]}


# ---------- A2 run 선택·분류 ----------
def test_a2_selection_and_classification(tmp_path):
    site = build(selection_db(tmp_path))
    runs = by_id(site)
    # C-2: nightly는 steps≠[]만(n-skip·n-w42 제외), weekly는 week 있는 것 전부(w-null 제외), 개발용·nightly 하위 0
    assert set(runs) == {"n1", "r40", "r41", "w-part", "w-topic", "w-auto", "w-run", "n-man", "n-new", "steps-2026-10-07", "steps-2026-10-08"}
    assert {r["kind"] for r in site["runs"]} == {"nightly", "weekly", "steps"}
    # C-1: runs[].week ⊆ run_weeks[].week, 발행 주 + run이 있는 비발행 주(W40 done, W42 open)
    assert {r["week"] for r in site["runs"]} <= {rw["week"] for rw in site["run_weeks"]}
    assert [(rw["week"], rw["status"]) for rw in site["run_weeks"]] == [("2026-w42", "open"), ("2026-w41", "published"), ("2026-w40", "done")]
    assert [r["at"] for r in site["runs"]] == sorted((r["at"] for r in site["runs"]), reverse=True)
    # C-9: mode == auto ⇔ (nightly ∧ manual ∉ summary) ∨ (weekly ∧ spec RUN-%)
    assert {i: r["mode"] for i, r in runs.items()} == {"n1": "auto", "r40": "manual", "r41": "manual", "w-part": "manual", "w-topic": "manual",
        "w-auto": "auto", "w-run": "manual", "n-man": "manual", "n-new": "auto", "steps-2026-10-07": "manual", "steps-2026-10-08": "manual"}
    # label·sub·topic_id·current·result
    assert (runs["r41"]["label"], runs["r41"]["sub"], runs["r41"]["current"], runs["w-auto"]["current"]) == ("from cluster", False, True, False)
    assert (runs["w-part"]["label"], runs["w-part"]["sub"], runs["w-part"]["topic_id"]) == ("from select", True, None)
    assert (runs["w-topic"]["label"], runs["w-topic"]["sub"], runs["w-topic"]["topic_id"], runs["w-topic"]["result"]) == (
        "from write topic w41-a", True, "w41-a", {"topics": 1, "steps": 0})
    assert runs["w-topic"]["summary"] is None  # 주 누적치라 run 수치로 쓰지 않는다(NG-6)
    assert (runs["w-run"]["label"], runs["w-run"]["status"], runs["w-run"]["end"], runs["w-run"]["duration_sec"]) == ("from write", "running", None, None)
    assert runs["n-man"]["label"] == "nightly 10.8~10.9" and runs["n-man"]["week"] == "2026-w41" and runs["n-man"]["cost_usd"] == 0.2
    assert runs["n-new"]["week"] == "2026-w42" and runs["n-new"]["day"] == "2026-10-13" and runs["n-new"]["label"] == "nightly 10.12"
    assert runs["n-new"]["result"] == {"steps": 1, "failed": 0} and runs["n1"]["result"] == {"steps": 2, "failed": 1}
    # ③ 묶음: 날마다 한 줄, kind별 status별 수, 전부 ok면 ok 아니면 partial, 비용은 runs.cost_usd 합
    s7, s8 = runs["steps-2026-10-07"], runs["steps-2026-10-08"]
    assert (s7["status"], s7["cost_usd"], s7["result"], s7["steps"], s7["summary"], s7["label"]) == (
        "partial", 0.75, {"kinds": {"collect": {"ok": 1}, "filter": {"failed": 1}}}, [], None, "steps")
    assert (s8["status"], s8["week"], s8["at"]) == ("ok", "2026-w41", "2026-10-08T10:00:00+09:00")
    # run_weeks 새 칸, 옛 칸 0
    rw = {r["week"]: r for r in site["run_weeks"]}
    assert rw["2026-w41"]["weekly"] == {"total": 5, "full": 2, "partial": 2, "topic": 1}  # full r41·w-auto / 단계부터 w-part·w-run / 토픽 w-topic
    assert rw["2026-w41"]["nightly_days"] == 3 and rw["2026-w42"]["nightly_days"] == 1
    assert rw["2026-w42"] == {"week": "2026-w42", "label": "10월 3주차", "range": "10.12 ~ 10.18", "status": "open", "nightly_days": 1,
                              "weekly": {"total": 0, "full": 0, "partial": 0, "topic": 0}, "published_at": None, "current_run_id": None}
    assert rw["2026-w41"]["current_run_id"] == "r41" and rw["2026-w41"]["published_at"] == "2026-10-12T07:10:00+09:00"
    assert not {"nightly", "nightly_failed", "collected", "candidates", "published", "rejected", "needs_check"} & set(rw["2026-w41"])
    for r in site["runs"]:
        assert list(r)[:14] == ["id", "kind", "at", "end", "duration_sec", "day", "week", "mode", "status", "cost_usd", "current", "label", "sub", "topic_id"]
        assert not [k for k in r if k.startswith("_")]


def test_a2_legacy_end_timestamp_without_offset(tmp_path):
    """실DB에 시간대 없는 끝 시각('2026-10-14 06:59:08')이 있다: KST ISO로 맞춰 낸다."""
    db = selection_db(tmp_path)
    db.conn.execute("UPDATE runs SET finished_at='2026-10-09 10:05:30' WHERE id='w-part'")
    db.conn.commit()
    r = by_id(build(db))["w-part"]
    assert r["end"] == "2026-10-09T10:05:30+09:00" and r["duration_sec"] == 330


# ---------- A3 run 1건 상세 칸 ----------
def detail_db(tmp_path):
    db = selection_db(tmp_path)
    c = db.conn
    c.executescript("""
    INSERT INTO sources(id, channel, kind, name, feed, enabled, config_json) VALUES ('aitimes','text','news','AI타임스','https://x.example/rss',1,'{}');
    INSERT INTO items(id, source_id, channel, external_id, url, title, day, week, filter_status, filter_reason) VALUES
      (11,'aitimes','text','n1','https://a.example/1','밤 글 하나','2026-10-12','2026-W42','pass','keyword_pass'),
      (12,'aitimes','text','n2','https://a.example/2','밤 글 둘','2026-10-12','2026-W42','pass','keyword_pass'),
      (13,'aitimes','text','n3','https://a.example/3','밤 글 셋','2026-10-12','2026-W42','filtered','excluded:스포츠'),
      (14,'aitimes','video','n4','https://y.example/4','밤 영상','2026-10-12','2026-W42','pass','keyword_pass');
    INSERT INTO videos(item_id, video_id, duration_sec) VALUES (14,'VID14',900);
    INSERT INTO video_frames(video_id, t, reason) VALUES ('VID14', 10.0, 's'), ('VID14', 20.0, 's');
    """)
    # --- weekly 전체 run wf: 6단계 ---
    long = "가" * 400
    run(c, "wf", "weekly", "2026-10-11T23:42:00+09:00", "2026-10-11T23:57:00+09:00", note="weekly 2026-W41 from cluster", week="2026-W41", cost=0.1,
        summary={"cluster": {"clusters": 5, "past": {"new": 2, "follow_up": 1, "duplicate": 0}}, "select": {"candidates": 3, "selected": 2},
                 "write": {"topics": 2}, "review": {"rounds": {"1": 1, "2": 1, "3": 0}, "code_rejects": 1, "critic_rejects": 0, "check_topics": 1},
                 "cost_usd": {"decide": 0.01, "editor_select": 0.02, "writer": 0.03, "writer_revise": 0.0, "critic": 0.04, "total": 0.1},
                 "duration_sec": {"evidence": 1.0, "cluster": 30.4, "select": 20.0, "write_review": 600.0, "total": 651.4}})
    T = "2026-10-11T23:4{}:00+09:00"
    step(c, "wf", 1, "evidence", "code", "근거 자격 글 3, 영상 1", T.format(2), detail={"counts": {"text": 3, "video": 1}, "excluded": {"no_card": 2}})
    step(c, "wf", 2, "normalize", "code", "별칭 자동 승인 2", T.format(2), detail={"counts": {"auto_approved": 2}})
    step(c, "wf", 3, "evidence", "code", "영상 관련성 점수: high 1, mid 0", T.format(2), detail={"vd:VID14": 0.6})
    for i in range(3):
        step(c, "wf", 4 + i, "decide", "llm", "판정", T.format(3), attention=int(i == 2), model="qwen/qwen3.8-27b", tin=100, tout=10)
    step(c, "wf", 7, "cluster", "code", "묶음 5개", T.format(3), detail={"clusters": 5, "candidates": 3, "decide_calls": 3})
    step(c, "wf", 8, "weekly", "code", "2026-W41 weekly 시작: cluster부터", T.format(3), detail={"from_step": "cluster"})
    step(c, "wf", 9, "editor_select", "llm", "첫 시도", T.format(5), model="qwen/qwen3.8-27b")
    step(c, "wf", 10, "editor_select", "llm", "후보 3개 중 2개 선정", T.format(5), model="qwen/qwen3.8-27b")
    step(c, "wf", 11, "editor_select", "code", "후보 3개 중 2개 선정", T.format(5), detail={"source": "model", "reconciled": ["c3 select → drop(other)"]})
    # 토픽 A: 반려 1회 + 수정 + 비평 통과, 토픽 B: 한 번에 통과(checked), 그 사이 예산 중단 기록(topic_id 없음)
    step(c, "wf", 12, "writer", "llm", "절 3개, 단락 4개", T.format(6), model="qwen/qwen3.8-27b", tin=1000, tout=200, cost=0.01)
    step(c, "wf", 13, "writer_revise", "llm", "이슈 2개 중 수정 1", T.format(6), model="qwen/qwen3.8-27b", tin=500, tout=100, cost=0.005,
         output={"changed": [{"issue_idx": 0, "loc": "points[0]", "action": "edit", "value": {}}]})
    step(c, "wf", 14, "critic", "llm", "원자 사실 9개 모두 지지", T.format(7), model="qwen/qwen3.8-27b", tin=700, tout=300, cost=0.02)
    rounds_a = [{"round": 1, "checker": "code", "status": "reject", "issues": [
        {"loc": "points[0]", "type": "format", "comment": long, "hint": "h"}, {"loc": "overview", "type": "format", "comment": "금지 표현", "hint": "h"}]},
        {"round": 2, "checker": "critic", "status": "pass", "issues": []}]
    step(c, "wf", 15, "writer", "code", "w41-a: passed, 2라운드", T.format(7), detail={"topic_id": "w41-a", "rounds": rounds_a, "checks": []})
    step(c, "wf", 16, "writer", "llm", "절 2개", T.format(8), model="qwen/qwen3.8-27b", tin=200, tout=50, cost=0.002)
    step(c, "wf", 17, "critic", "code", "LLMError로 중단", T.format(8), attention=1)  # 오류 원문은 내지 않고 `code 중단`만
    step(c, "wf", 18, "critic", "llm", "원자 사실 4개 모두 지지", T.format(8), model="qwen/qwen3.8-27b", tin=300, tout=60, cost=0.003)
    step(c, "wf", 19, "writer", "code", "w41-b: checked, 1라운드", T.format(9), attention=1,
         detail={"topic_id": "w41-b", "rounds": [{"round": 1, "checker": "code", "status": "pass", "issues": []}], "checks": ["concepts[0]"]})
    step(c, "wf", 20, "weekly", "code", "2026-W41 weekly 끝: 토픽 2개", T.format(9), detail={"duration_sec": {"total": 651.4}, "stopped": None})
    for tid, rank, st, cid in (("w41-a", 1, "passed", [1]), ("w41-b", 2, "checked", [2])):
        c.execute("INSERT INTO topics(run_id, topic_id, week, cluster_ids_json, rank, lead, status, final_round, title) VALUES (?,?,?,?,?,?,?,?,?)",
                  ("wf", tid, "2026-W41", json.dumps(cid), rank, 0, st, 2 if tid == "w41-a" else 1, f"토픽 {tid}"))
    c.executescript("""
    INSERT INTO cluster_items(cluster_id, member, channel, joined_by) VALUES (1,'it:1','text','seed'), (2,'it:2','text','seed'), (3,'vd:VID14','video','seed');
    INSERT INTO aliases(canonical, alias, reason, origin, status, run_id) VALUES
      ('Claude Haiku 5.5','클로드 하이쿠 5.5','음차','normalizer','approved','wf'), ('Gemini','제미나이',NULL,'normalizer','approved','wf'),
      ('X','x','r','normalizer','rejected','wf'), ('Y','y','r','editor','approved','wf');
    INSERT INTO cluster_pairs(run_id, a, b, sim, cross_channel, decided, answer, confidence, reason) VALUES
      ('wf','it:1','it:2',0.7,0,1,1,0.95,'같은 발표'), ('wf','it:1','vd:VID14',0.6,1,1,0,0.8,'다른 대상'),
      ('wf','it:2','it:999',0.6,0,1,0,0.9,'참조 없음'), ('wf','it:1','it:11',0.5,0,0,NULL,NULL,NULL);
    """)
    c.execute("INSERT INTO briefing_plans(run_id, week, source, plan_json) VALUES ('wf','2026-W41','model',?)", (json.dumps({"decisions": [
        {"cluster_id": 2, "reason": "선정 2", "action": "select", "drop_reason": None}, {"cluster_id": 1, "reason": "선정 1", "action": "select", "drop_reason": None},
        {"cluster_id": 3, "reason": "분량 부족", "action": "drop", "drop_reason": "thin"}]}, ensure_ascii=False),))
    # --- nightly nf: 8단계(7 + export + build) ---
    run(c, "nf", "nightly", N0, "2026-10-13T02:13:55+09:00", spec="RUN-2026-W42", note="nightly",
        summary={"days": ["2026-10-12"], "cost_usd": 0.13, "site": {"exit": 0, "sec": 3.2}, "steps": [
            {"name": "collect", "day": None, "exit": 0, "sec": 93.0}, {"name": "filter", "day": None, "exit": 0, "sec": 24.2},
            {"name": "summarize", "day": None, "exit": 0, "sec": 234.0}, {"name": "plan", "day": "2026-10-12", "exit": 0, "sec": 29.3},
            {"name": "deep_text", "day": "2026-10-12", "exit": 0, "sec": 148.5}, {"name": "video", "day": "2026-10-12", "exit": 1, "sec": 181.7,
                                                                                    "error": "HTTP 429 Provider returned error /Users/x/secret"},
            {"name": "repo_analyze", "day": "2026-10-12", "exit": 0, "sec": 117.7}]})
    subs = [("collect", "02:00:06", "02:01:38", 0.0, "collect"), ("filter", "02:01:39", "02:02:02", 0.0, "filter"),
            ("summarize", "02:02:03", "02:05:57", 0.05, "summarize"), ("plan", "02:05:57", "02:06:26", 0.004, "plan 2026-10-12"),
            ("deep-text", "02:06:26", "02:08:54", 0.04, "deep text 2026-10-12"), ("video", "02:08:55", "02:11:05", 0.006, "video VID14"),
            ("repo-analyze", "02:11:57", "02:13:55", 0.027, "repo-analyze 2026-W42")]
    for kind, a, b, cost, note in subs:
        run(c, f"nf-{kind}", kind, f"2026-10-13T{a}+09:00", f"2026-10-13T{b}+09:00", spec="RUN-2026-W42", note=note, cost=cost)
    c.executescript("""
    INSERT INTO fetch_log(run_id, source_id, day, status, n_new, error, t) VALUES
      ('nf-collect','aitimes','2026-10-13','ok',28,NULL,'t'), ('nf-collect','geeknews','2026-10-13','partial',8,'오류 원문 /Users/x','t'),
      ('nf-collect','github_trending','2026-10-13','ok',0,NULL,'t'), ('nf-collect','github_releases','2026-10-13','ok',0,NULL,'t');
    INSERT INTO plans(day, run_id, source, plan_json) VALUES ('2026-10-12','nf-plan','fallback',
      '{"log":"큐 정리","attention":true,"text_queue":[{"item_id":11,"reason":"근거 직접","max_depth":2},{"item_id":999,"reason":"없음","max_depth":1}],
        "video_queue":[{"video_id":"VID14","reason":"자막만","mode":"whisper"}],"repo_queue":[{"full_name":"o/r","reason":"릴리스","max_depth":2}]}');
    """)
    step(c, "nf-filter", 1, "filter", "code", "4건 keep 2 drop 1", "2026-10-13T02:02:02+09:00", 1)
    for i in range(2):
        step(c, "nf-summarize", i + 1, "item_card", "llm", "카드", "2026-10-13T02:02:10+09:00", int(i == 0), model="qwen/qwen3.8-27b", tin=100, tout=20, cost=0.01)
    step(c, "nf-plan", 1, "editor_plan", "llm", "계획", "2026-10-13T02:06:00+09:00", model="qwen/qwen3.8-27b")
    c.execute("INSERT INTO item_cards(item_id, version, card_json, run_id) VALUES (11,2,?,'nf-deep-text'), (12,2,?,'nf-deep-text')",
              (json.dumps({"log": "일치 3", "trail": [{"url": "https://www.github.com/a/b", "depth": 1}, {"url": "https://github.com/a/c", "depth": 2},
                                                       {"url": "https://arxiv.org/abs/1", "depth": 2}]}), json.dumps({"log": "못 찾음", "trail": []})))
    for i in range(3):
        step(c, "nf-deep-text", i + 1, "text_analyst", "tool", "도구", "2026-10-13T02:06:30+09:00")
    step(c, "nf-deep-text", 4, "text_analyst", "llm", "호출", "2026-10-13T02:06:30+09:00", model="qwen/qwen3.8-27b")
    c.execute("INSERT INTO video_digests(video_id, item_id, digest_json, run_id, created_at) VALUES ('VID14',14,?,'nf-video','t')",
              (json.dumps({"mode": "whisper", "span": {"start": 0.0, "end": 900.0}, "segments_count": 80, "transcript_quality": "ok"}),))
    c.execute("INSERT INTO repo_cards(week, full_name, card_json, run_id) VALUES ('2026-W42','o/r',?,'nf-repo-analyze'), ('2026-W42','o/s',?,'nf-repo-analyze')",
              (json.dumps({"log": "o/r: 릴리스 v1, 커밋 5"}), json.dumps({"summary": "요약만 있음"})))
    for i in range(2):
        step(c, "nf-repo-analyze", i + 1, "repo_analyst", "tool", "도구", "2026-10-13T02:12:00+09:00")
    c.commit()
    return db


def names(r):
    return [s["name"] for s in r["steps"]]


def test_a3_weekly_full_run_steps(tmp_path):
    r = by_id(build(detail_db(tmp_path)))["wf"]
    assert names(r) == ["evidence", "normalize", "cluster + decide", "editor_select", "writer ⇄ critic", "weekly 끝"]
    ev, nm, cl, sel, wr, end = r["steps"]
    assert ev["line"] == "근거 자격 글 3, 영상 1" and [b["items"] for b in ev["detail"]] == [
        [["counts", "text 3 / video 1"], ["excluded", "no_card 2"], ["영상 관련성", "high 1, mid 0"]]]
    assert (ev["t"], ev["duration_sec"], ev["who"]) == ("23:42", 1, [{"kind": "code", "role": None, "model": None, "n": None}])
    assert nm["detail"][1]["items"] == ["클로드 하이쿠 5.5 → Claude Haiku 5.5 / 음차", "제미나이 → Gemini"]  # normalizer·approved만
    # cluster + decide: decide 행 수, attention 한 건 이상이면 line 끝에 attention n, 판정 표는 decided=1 전부
    assert cl["who"][1] == {"kind": "llm", "role": "decide", "model": "qwen3.8-27b", "n": 3} and cl["line"].endswith(" / attention 1") and cl["attention"]
    table = cl["detail"][1]
    assert table["head"] == ["a", "b", "판정", "이유", "확신도"] and len(table["rows"]) == 3
    assert table["rows"][0] == ["글 하나 (GeekNews)", "글 둘 (GeekNews)", "같음", "같은 발표", "0.95"]
    assert table["rows"][1][1] == "밤 영상 (AI타임스)" and table["rows"][1][2:] == ["다름", "다른 대상", "0.80"]  # vd: 구성원
    assert table["rows"][2][1] == "item 999"  # 참조 행 없음: 근거 id 모양(it:999)을 피한다
    assert (cl["duration_sec"], cl["cost_usd"]) == (30, 0.01)
    # editor_select: 선정은 topics 순위 순, 제외는 뒤에, 후보 이름은 선정이면 topics.title, 아니면 첫 구성원 제목
    assert sel["line"] == "후보 3개 중 2개 선정" and sel["who"] == [{"kind": "llm", "role": "editor_select", "model": "qwen3.8-27b", "n": None}]
    assert sel["detail"][1]["rows"] == [["1", "토픽 w41-a", "select", "선정 1"], ["2", "토픽 w41-b", "select", "선정 2"], ["-", "밤 영상 (AI타임스)", "drop(thin)", "분량 부족"]]
    assert dict(sel["detail"][0]["items"]) == {"source": "model", "reconciled": "c3 select → drop(other)", "past": "new 2 / follow_up 1 / duplicate 0"}
    # writer ⇄ critic: 토픽 경계는 writer code 행. 반려 표·체인·수정·글자 300자 자름
    assert wr["line"] == "topics 2 / rounds 1 ×1, 2 ×1 / code_rejects 1 / critic_rejects 0 / check_topics 1"
    assert [w["role"] for w in wr["who"]] == ["writer", "critic", "writer_revise"] and wr["who"][0]["n"] == 2 and wr["attention"]
    a, b = wr["detail"][0]["items"]
    assert a["topic_id"] == "w41-a" and (a["rank"], a["title"], a["status"], a["final_round"]) == (1, "토픽 w41-a", "passed", 2)
    assert (a["tokens_in"], a["tokens_out"], a["cost_usd"]) == (2200, 600, 0.035)
    assert a["chain"] == [["writer", "절 3개, 단락 4개"], ["code", "반려 2"], ["writer_revise", "이슈 2개 중 수정 1"], ["critic", "원자 사실 9개 모두 지지"], ["code", "passed"]]
    assert a["issues"] == [["points[0]", "format", "가" * 300, "edit"], ["overview", "format", "금지 표현", "-"]]  # 수정이 없는 지적은 `-`
    assert b["chain"] == [["writer", "절 2개"], ["code", "중단"], ["critic", "원자 사실 4개 모두 지지"], ["code", "checked 1"]] and b["issues"] == []
    assert end["line"] == "2026-W41 weekly 끝: 토픽 2개" and end["duration_sec"] == 651 and end["cost_usd"] == 0.1
    assert r["summary"] == {"clusters": 5, "candidates": 3, "selected": 2, "topics": 2, "published": None, "rounds": {"1": 1, "2": 1, "3": 0},
                            "code_rejects": 1, "critic_rejects": 0, "check_topics": 1}
    assert "LLMError" not in json.dumps(r, ensure_ascii=False)


def test_a3_nightly_run_steps_and_summary(tmp_path):
    r = by_id(build(detail_db(tmp_path)))["nf"]
    assert names(r) == ["collect", "filter", "summarize", "plan", "deep_text", "video", "repo_analyze", "export + build"]
    col, fil, summ, plan, deep, vid, repo, site = r["steps"]
    assert col["line"] == "new 36 / sources 4 / failed 1" and col["detail"][0]["items"] == ["aitimes 28", "geeknews 8 (partial)", "github_releases, github_trending 0"]
    assert (col["t"], col["duration_sec"]) == ("02:00", 93)
    assert fil["line"] == "4건 keep 2 drop 1" and dict(fil["detail"][0]["items"]) == {
        "filter_status": "pass 3 / filtered 1", "filter_reason": "keyword_pass 3 / excluded:스포츠 1"}  # 그날(days) items만
    assert summ["who"] == [{"kind": "llm", "role": "item_card", "model": "qwen3.8-27b", "n": 2}] and summ["line"] == "item_card 2 / attention 1" and summ["cost_usd"] == 0.05
    assert plan["line"] == "text_queue 2 / video_queue 1 / repo_queue 1 / fallback" and plan["attention"]  # 대체 계획: line에 fallback
    assert plan["detail"][0]["items"] == ["text_queue / 밤 글 하나 (AI타임스) / 근거 직접 / depth 2", "text_queue / item 999 / 없음 / depth 1",
                                          "video_queue / 밤 영상 (AI타임스) / 자막만 / whisper", "repo_queue / o/r / 릴리스"]
    assert dict(plan["detail"][1]["items"]) == {"log": "큐 정리"}
    assert deep["who"] == [{"kind": "agent", "role": "text_analyst", "model": "qwen3.8-27b", "n": 2}] and deep["line"] == "items 2 / tool 3"
    assert deep["detail"][0]["rows"] == [["밤 글 하나", "github.com → arxiv.org", "2", "일치 3"], ["밤 글 둘", "-", "-", "못 찾음"]]  # 도메인만, www. 뺌
    assert vid["detail"][0]["items"] == ["밤 영상 / mode whisper / span 0.0~900.0 / segments 80 / quality ok / frames 2"]
    assert vid["attention"] and vid["line"].endswith(" / exit 1") and "HTTP 429" not in json.dumps(r, ensure_ascii=False)  # 오류 원문은 종료 코드만
    assert repo["detail"][0]["items"] == ["o/r: 릴리스 v1, 커밋 5", "o/s / 요약만 있음"] and repo["line"] == "repos 2 / tool 2"
    assert (site["line"], site["duration_sec"], site["who"][0]["kind"]) == ("exit 0", 3, "code")
    assert r["summary"] == {"collected": 36, "filter_keep": 3, "cards": 2, "deep_text": 2, "video": 1, "repo": 1, "exit_nonzero": 1}
    assert r["mode"] == "auto" and r["result"] == {"steps": 7, "failed": 1}


def test_a3_missing_sources_make_line_only_steps_and_no_error_text(tmp_path):
    """원천 행이 없는 단계는 line만(예외 아님). 이 스펙 전 nightly(summary.site 없음)는 export + build 단계를 생략한다."""
    r = by_id(build(selection_db(tmp_path)))["n-new"]
    assert [(s["name"], s["line"], s["detail"]) for s in r["steps"]] == [("collect", "exit 0", [])] and r["summary"]["collected"] == 0
    assert by_id(build(selection_db(tmp_path / "again")))["w-auto"]["steps"] == []


def test_a3_text_cells_are_capped_at_300(tmp_path):
    for r in build(detail_db(tmp_path))["runs"]:
        def walk(x):
            if isinstance(x, str):
                assert len(x) <= 300
            elif isinstance(x, (list, tuple)):
                [walk(v) for v in x]
            elif isinstance(x, dict):
                [walk(v) for v in x.values()]
        walk(r["steps"])


def test_a3_multi_day_nightly_pairs_sub_runs_by_day(tmp_path):
    """하루치 단계(plan·deep_text·...)가 여러 날이면 plan 하위 run의 날짜(노트)를 기준으로 짝짓는다."""
    db = DB(tmp_path / "t.db")
    c = db.conn
    run(c, "n2", "nightly", "2026-10-13T02:00:00+09:00", "2026-10-13T03:00:00+09:00", spec="RUN-2026-W42", summary={
        "days": ["2026-10-11", "2026-10-12"], "steps": [{"name": "plan", "day": d, "exit": 0, "sec": 1.0} for d in ("2026-10-11", "2026-10-12")]
        + [{"name": "repo_analyze", "day": d, "exit": 0, "sec": 1.0} for d in ("2026-10-11", "2026-10-12")]})
    for d, mm in (("2026-10-11", "10"), ("2026-10-12", "30")):
        run(c, f"p{d}", "plan", f"2026-10-13T02:{mm}:00+09:00", spec="RUN-2026-W42", note=f"plan {d}")
        run(c, f"r{d}", "repo-analyze", f"2026-10-13T02:{mm}:30+09:00", spec="RUN-2026-W42", note="repo-analyze 2026-W42")
        c.execute("INSERT INTO repo_cards(week, full_name, card_json, run_id) VALUES ('2026-W42',?,?,?)", (f"o/{d[-2:]}", json.dumps({"log": f"o/{d[-2:]} 카드"}), f"r{d}"))
    c.commit()
    from trendsit.export_runs import _nightly, _nightly_detail

    row = c.execute("SELECT * FROM runs WHERE id='n2'").fetchone()
    d = _nightly(row, json.loads(row["summary_json"]))
    d["_row"] = row
    _, steps = _nightly_detail(db, d)
    assert [s["name"] for s in steps] == ["plan 10.11", "plan 10.12", "repo_analyze 10.11", "repo_analyze 10.12"]
    assert [s["detail"][0]["items"] for s in steps[2:]] == [["o/11 카드"], ["o/12 카드"]]


# ---------- A1 publish --site-only ----------
def test_a1_publish_site_only_exit_codes_and_weeks_unchanged(tmp_path, monkeypatch, capsys):
    """CLI 끝까지: 실제 export + 가짜 빌드 명령(python -c)으로 0 / 빌드 실패 1 / --week와 같이 쓰면 2. weeks 행은 그대로."""
    import sys

    from trendsit import cli

    db = make_db(tmp_path)
    monkeypatch.setattr("trendsit.core.db.open_db", lambda *a, **k: db)
    before = [tuple(r) for r in db.conn.execute("SELECT * FROM weeks ORDER BY week")]
    monkeypatch.setattr(ops, "BUILD_CMD", [sys.executable, "-c", "pass"])  # 뒤에 --data <임시 파일>이 붙는다
    assert cli.main(["publish", "--site-only"]) == 0
    site = json.loads((tmp_path / "site.json").read_text())
    assert site["run_weeks"] and not (tmp_path / "site.json.new").exists()
    assert [tuple(r) for r in db.conn.execute("SELECT * FROM weeks ORDER BY week")] == before  # status·published_at·current_run_id 불변
    monkeypatch.setattr(ops, "BUILD_CMD", [sys.executable, "-c", "import sys; sys.stderr.write('빌드 오류\\n'); sys.exit(1)"])
    old = (tmp_path / "site.json").read_text()
    assert cli.main(["publish", "--site-only"]) == 1 and (tmp_path / "site.json").read_text() == old
    assert "사이트 재생성 실패: 빌드 종료 코드 1: 빌드 오류" in capsys.readouterr().err
    assert cli.main(["publish", "--site-only", "--week", "2026-W41"]) == 2 and "둘 중 하나만" in capsys.readouterr().err
    assert cli.main(["publish"]) == 2  # 둘 다 없으면 인자 오류
    assert [tuple(r) for r in db.conn.execute("SELECT * FROM weeks ORDER BY week")] == before


def test_a1_export_without_published_week_still_fails(tmp_path):
    from trendsit.export import ExportError

    with pytest.raises(ExportError):
        build(make_db(tmp_path, published=()))  # 진행 주만으로는 사이트를 안 만든다(5.7)


# ---------- 픽스처가 새 계약(5.2)을 따르고 5.5의 경계를 담는다 ----------
RUN_KEYS = ["id", "kind", "at", "end", "duration_sec", "day", "week", "mode", "status", "cost_usd", "current", "label", "sub", "topic_id", "result", "summary", "steps"]
STEP_KEYS = ["t", "name", "who", "line", "duration_sec", "cost_usd", "attention", "detail"]
FIXTURES = ["tests/fixtures/site/site.json", "tests/fixtures/s6_1/site_v2.json"]


def texts(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from texts(v)
    elif isinstance(x, dict):
        for v in x.values():
            yield from texts(v)


@pytest.mark.parametrize("path", FIXTURES)
def test_fixture_runs_follow_contract(path):
    from pathlib import Path

    d = json.loads((Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8"))
    rw = {r["week"]: r for r in d["run_weeks"]}
    published = {w["id"] for w in d["weeks"]}
    assert set(published) <= set(rw) and {r["week"] for r in d["runs"]} <= set(rw)  # C-1
    assert list(rw) == sorted(rw, reverse=True)
    for r in d["run_weeks"]:
        assert list(r) == ["week", "label", "range", "status", "nightly_days", "weekly", "published_at", "current_run_id"]
        assert (r["status"] == "published") == (r["week"] in published) and (r["published_at"] is None) == (r["week"] not in published)
        assert list(r["weekly"]) == ["total", "full", "partial", "topic"]
    for r in d["runs"]:
        assert list(r) == RUN_KEYS and r["kind"] in ("nightly", "weekly", "steps")  # C-2
        assert r["status"] in ("ok", "partial", "failed", "running", "stopped") and r["mode"] in ("auto", "manual")
        assert (r["kind"] == "steps") == (r["steps"] == [] and r["summary"] is None and r["id"].startswith("steps-")) or r["kind"] != "steps"
        assert r["sub"] == (r["kind"] == "weekly" and not r["label"].startswith(("from cluster", "cluster")))
        assert (r["topic_id"] is not None) == (r["kind"] == "weekly" and "topic" in r["label"]) and r["day"] == r["at"][:10]
        for s in r["steps"]:
            assert list(s) == STEP_KEYS and all(set(w) == {"kind", "role", "model", "n"} for w in s["who"])
            assert all(b["type"] in ("kv", "list", "table", "topics") for b in s["detail"])
        assert all(len(t) <= 300 for t in texts([s["detail"] for s in r["steps"]]))  # C-5
    assert sum(r["current"] for r in d["runs"] if r["week"] in published) == len([w for w in rw.values() if w["current_run_id"]])


def test_fixture_site_covers_the_boundaries_of_5_5():
    from pathlib import Path

    d = json.loads((Path(__file__).resolve().parents[1] / FIXTURES[0]).read_text(encoding="utf-8"))
    runs = d["runs"]
    open_week = [w for w in d["run_weeks"] if w["status"] == "open"]
    assert len(open_week) == 1 and open_week[0]["nightly_days"] == 1 and open_week[0]["weekly"]["total"] == 0  # 진행 주
    assert {r["mode"] for r in runs if r["kind"] == "nightly"} == {"auto", "manual"}
    weekly = [r for r in runs if r["kind"] == "weekly"]
    assert any(r["current"] and not r["sub"] and r["label"] == "from cluster" for r in weekly) and any(r["sub"] and not r["topic_id"] for r in weekly) and any(r["topic_id"] for r in weekly)
    assert any(r["kind"] == "steps" and r["status"] == "partial" for r in runs) and any(r["status"] == "running" for r in runs)
    assert any(s["attention"] for r in runs for s in r["steps"])
    blocks = [b for r in weekly for s in r["steps"] for b in s["detail"] if b["type"] == "topics"]
    topics_ = [t for b in blocks for t in b["items"]]
    assert any(t["status"] == "checked" and t["issues"] for t in topics_) and len({t["topic_id"] for t in topics_}) >= 2
    nightly = [r for r in runs if r["kind"] == "nightly"]
    assert any(s["name"] == "export + build" for r in nightly for s in r["steps"]) and any(r["steps"] and s["name"].startswith("plan 10.") for r in nightly for s in r["steps"])
    assert any(w["published_at"] for w in d["run_weeks"])
