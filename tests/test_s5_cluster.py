"""S5 3단계 묶기(관문 A7): 채널 넘는 묶음 조건, confidence 미달 미병합, 평균 연결(사슬), 레포만 묶음, 1개짜리 묶음."""

from __future__ import annotations

import pytest

from trendsit.brief.aliases import AliasTable
from trendsit.brief.cluster import agglomerate, build_pairs, finalize, run_decides
from trendsit.brief.evidence import EvidenceItem, Member
from trendsit.core import config
from trendsit.core.artifacts_brief import DecideAnswer

CFG = config.load("brief.yaml")  # 임시 문턱값 auto 0.80 / border 0.65


def m(key: str, channel: str = "text", entities=(), keywords=(), relevance: str = "high") -> Member:
    it = EvidenceItem(f"{key}#q1" if key.startswith("it:") else key, key, channel, "quote", "x", {})
    return Member(key, channel, key, "", "", relevance, list(entities), list(keywords), {}, [it])


def run(members: list[Member], sims: dict[tuple[str, str], float], answers: dict[tuple[str, str], tuple[bool, float]] | None = None):
    ms = {x.key: x for x in members}
    keys = sorted(ms)
    # 2차원 벡터로는 임의 유사도를 못 만들어 build_pairs의 sims를 바꿔 넣는다
    vecs = {k: [1.0, 0.0] for k in keys}
    pairs, all_sims = build_pairs(ms, vecs, AliasTable([]), CFG)
    for p in pairs:
        p.sim = sims.get((p.a, p.b), sims.get((p.b, p.a), 0.1))
        all_sims[(p.a, p.b)] = all_sims[(p.b, p.a)] = p.sim
        th = CFG.cluster.thresholds
        if p.cross:
            p.route = "decide" if (p.shared_kw or p.shared_names) and p.sim >= th.border else "none"
        else:
            p.route = "auto" if p.sim >= th.auto else "decide" if p.sim >= th.border else "none"
    asked = []

    def decider(inp):
        asked.append((inp.a.id, inp.b.id))
        same, conf = (answers or {}).get((inp.a.id, inp.b.id), (False, 0.9))
        return DecideAnswer(reason="r", same=same, confidence=conf, log="l"), None

    run_decides(pairs, ms, decider, 60)
    clusters, blocked = agglomerate(ms, pairs, all_sims, CFG)
    return finalize(clusters, ms, AliasTable([])), asked, blocked


def groups(clusters) -> list[list[str]]:
    return sorted(sorted(c.members) for c in clusters)


def test_cross_channel_needs_shared_keyword_or_name():
    a, v = m("it:1", entities=["Gemini 4"], keywords=["ai-general"]), m("vd:A", "video", entities=["Gemini 4"])
    b, w = m("it:2", keywords=["ai-general"]), m("vd:B", "video", keywords=["ai-general"])
    cl, asked, _ = run([a, v, b, w], {("it:1", "vd:A"): 0.7, ("it:2", "vd:B"): 0.9},
                       {("it:1", "vd:A"): (True, 0.9)})
    assert ("it:1", "vd:A") in asked and ("it:2", "vd:B") not in asked  # 넓은 키워드(ai-general)만 공유하면 후보 아님
    assert ["it:1", "vd:A"] in groups(cl) and ["vd:B"] in groups(cl)


def test_cross_channel_is_never_automatic():
    cl, asked, _ = run([m("it:1", entities=["X"]), m("vd:A", "video", entities=["X"])], {("it:1", "vd:A"): 0.95},
                       {("it:1", "vd:A"): (False, 0.9)})
    assert asked and groups(cl) == [["it:1"], ["vd:A"]]


def test_low_confidence_same_is_not_merged():
    cl, asked, _ = run([m("it:1"), m("it:2")], {("it:1", "it:2"): 0.7}, {("it:1", "it:2"): (True, 0.5)})
    assert asked and groups(cl) == [["it:1"], ["it:2"]]


def test_average_linkage_blocks_chain():
    sims = {("it:1", "it:2"): 0.9, ("it:2", "it:3"): 0.85, ("it:1", "it:3"): 0.3}
    cl, _, _ = run([m("it:1"), m("it:2"), m("it:3")], sims)
    assert groups(cl) == [["it:1", "it:2"], ["it:3"]]


def test_repo_only_cluster_is_not_candidate_but_single_text_is():
    cl, _, _ = run([m("rp:a/b", "github"), m("rp:c/d", "github"), m("it:1")], {("rp:a/b", "rp:c/d"): 0.9})
    repos = [c for c in cl if c.members[0].startswith("rp:")]
    single = next(c for c in cl if c.members == ["it:1"])
    assert len(repos) == 2 and all(c.repo_only for c in repos)  # 레포끼리는 묶이지도 않음
    assert not single.repo_only


def test_decided_different_pair_is_cannot_link():
    sims = {("it:1", "it:2"): 0.9, ("it:2", "it:3"): 0.75, ("it:1", "it:3"): 0.85}
    cl, _, _ = run([m("it:1"), m("it:2"), m("it:3")], sims, {("it:2", "it:3"): (False, 0.9)})
    assert not any({"it:2", "it:3"} <= set(c.members) for c in cl)


def test_size_cap_blocks_and_reports(monkeypatch):
    small = CFG.model_copy(deep=True)
    small.cluster.max_cluster_size = 2
    monkeypatch.setattr("tests.test_s5_cluster.CFG", small)
    sims = {(f"it:{i}", f"it:{j}"): 0.95 for i in range(3) for j in range(3) if i < j}
    cl, _, blocked = run([m(f"it:{i}") for i in range(3)], sims)
    assert max(len(c.members) for c in cl) == 2 and blocked


@pytest.mark.parametrize("rel", ["high", "low"])
def test_score_is_relevance_first(rel):
    """근거 1건짜리 high 글이 영상 3편짜리 mid 묶음보다 앞(채널·근거 수는 같은 관련성 안 순서만)."""
    hi = m("it:hi", relevance="high")
    vids = [m(f"vd:{i}", "video", relevance="mid") for i in range(3)]
    sims = {(a.key, b.key): 0.9 for a in vids for b in vids if a.key < b.key}
    cl, _, _ = run([hi, *vids, m("it:lo", relevance=rel)], sims)
    assert cl[0].members == ["it:hi"]
    vid = next(c for c in cl if len(c.members) == 3)
    assert cl.index(vid) > 0 and vid.score < cl[0].score


def test_stage_cluster_saves_rows_and_report(tmp_path, monkeypatch):
    """cluster 단계 끝까지(모의 임베더, 모의 decide): run_id로 쌓고 weeks.current_run_id, 리포트 절이 모두 있음."""
    import json

    from tests.conftest import FakeTransport, make_ctx, response
    from trendsit.brief import report as rp
    from trendsit.brief.weekly import stage_cluster
    from trendsit.filter.embed import HashEmbedder

    answer = json.dumps({"reason": "같은 발표", "same": True, "confidence": 0.9, "log": "같음", "attention": False})
    ctx = make_ctx(tmp_path, FakeTransport([response(answer) for _ in range(80)]), spec_cap=1.0)
    ctx.budget.cfg.specs["S0"] = 1.0
    c = ctx.db.conn
    c.execute("INSERT INTO sources(id, channel, name) VALUES ('openai','text','OpenAI')")
    card = {"quotes": [{"n": 1, "text": "Gemini 4 Argon launches"}], "numbers": [], "claims": [],
            "summary": "Gemini 4 Argon 출시다.", "entities": ["Gemini 4 Argon"], "keywords": ["frontier-release"],
            "relevance": "high"}
    for i in (1, 2, 3):
        c.execute("INSERT INTO items(id, source_id, channel, external_id, title, url, day, week) VALUES (?,?,?,?,?,?,?,?)",
                  (i, "openai", "text", f"e{i}", "Gemini 4 Argon launches today" if i < 3 else "다른 글", f"u{i}",
                   "2026-10-06", "2026-W41"))
        c.execute("INSERT INTO item_cards(item_id, version, card_json) VALUES (?, 1, ?)", (i, json.dumps(card)))
    c.commit()
    monkeypatch.setattr(rp, "OUT", tmp_path / "brief")
    stage = stage_cluster("2026-W41", ctx, embedder=HashEmbedder())
    path = rp.write_cluster_report(stage, CFG)
    run_id = stage.run_id
    assert c.execute("SELECT current_run_id, status FROM weeks").fetchone()[:] == (run_id, "clustered")
    assert c.execute("SELECT COUNT(*) FROM cluster_items ci JOIN clusters k ON k.id=ci.cluster_id WHERE k.run_id=?",
                     (run_id,)).fetchone()[0] == 3
    text = path.read_text()
    for head in ("## 1. 요약", "## 2. 유사도 분포", "## 3. 묶음 목록", "## 4. decide 판정", "## 5. 경계 근처",
                 "## 6. 의심 병합", "## 7. 과거 대조", "## 8. 별칭 표", "## 9. 편집장 입력"):
        assert head in text
    assert (tmp_path / "brief" / "cluster_pairs_2026-W41.csv").exists()
    # 다시 돌리면 새 run_id, 이전 행은 남고 current_run_id만 바뀜
    ctx.tracer = __import__("trendsit.core.trace", fromlist=["Tracer"]).Tracer(ctx.db, "weekly", "S0")
    stage2 = stage_cluster("2026-W41", ctx, embedder=HashEmbedder())
    assert c.execute("SELECT COUNT(DISTINCT run_id) FROM clusters").fetchone()[0] == 2
    assert c.execute("SELECT current_run_id FROM weeks").fetchone()[0] == stage2.run_id


def test_label_sheets_keep_filled_labels(tmp_path, monkeypatch):
    import csv

    from trendsit.brief import report as rp
    from trendsit.brief.aliases import AliasRow, AliasTable
    from trendsit.brief.cluster import ClusterResult, Pair
    from trendsit.brief.weekly import ClusterStage

    monkeypatch.setattr(rp, "LABELS", tmp_path)
    ms = {"it:1": m("it:1"), "it:2": m("it:2")}
    p = Pair("it:1", "it:2", 0.7, False, route="decide", decided=True, same=True, confidence=0.9, reason="같음")
    res = ClusterResult("2026-W41", [], [p], {}, [], 1, 0, 0, ms)
    stage = ClusterStage("r", None, AliasTable([AliasRow("Claude", "클로드", "candidate", "x")]), res, {}, [])  # type: ignore[arg-type]
    rp.write_label_sheets(stage)
    rows = list(csv.DictReader((tmp_path / "decide.csv").open()))
    rows[0]["label"], rows[0]["labeler"] = "same", "opus-5.5"
    with (tmp_path / "decide.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    rp.write_label_sheets(stage)
    again = list(csv.DictReader((tmp_path / "decide.csv").open()))
    assert (again[0]["label"], again[0]["labeler"]) == ("same", "opus-5.5")
    assert list(csv.DictReader((tmp_path / "aliases.csv").open()))[0]["alias"] == "클로드"


def test_two_repos_never_merge():
    cl, asked, _ = run([m("rp:a/x", "github"), m("rp:b/y", "github")], {("rp:a/x", "rp:b/y"): 0.95})
    assert groups(cl) == [["rp:a/x"], ["rp:b/y"]] and not asked


def test_cross_channel_member_cannot_join_through_same_channel_link():
    """리뷰 지적 6: it:1 ↔ vd:A가 decide same이어도, it:2가 it:1과 자동으로 붙으면 it:2 ↔ vd:A는 decide 없이 묶이면 안 됨."""
    a, b, v = m("it:1", entities=["X"]), m("it:2"), m("vd:A", "video", entities=["X"])
    cl, asked, _ = run([a, b, v], {("it:1", "vd:A"): 0.9, ("it:1", "it:2"): 0.95, ("it:2", "vd:A"): 0.7},
                       {("it:1", "vd:A"): (True, 0.9)})
    assert not any({"it:2", "vd:A"} <= set(c.members) for c in cl)


def test_cluster_ids_are_not_in_score_order():
    """리뷰 지적 7: 저장(= cluster_id) 순서는 점수가 아니라 첫 구성원 키."""
    hi, lo = m("it:9", relevance="high"), m("it:1", relevance="low")
    cl, _, _ = run([hi, lo], {})
    assert [c.members[0] for c in cl] == ["it:1", "it:9"]


def test_build_pairs_real_routes_including_name_path():
    """리뷰 지적 10: 테스트 안에서 경로를 다시 만들지 않고 실제 build_pairs로(이름 경로 포함)."""
    import math

    from trendsit.brief.cluster import build_pairs

    def vec(cos: float) -> list[float]:
        return [cos, math.sqrt(1 - cos * cos)]

    ms = {k: x for k, x in {
        "it:1": m("it:1", entities=["Gemini 4 Argon", "OpenAI"]), "it:2": m("it:2", entities=["Gemini 4 Argon"]),
        "it:3": m("it:3", entities=["OpenAI"]), "vd:A": m("vd:A", "video", entities=["Gemini 4 Argon"]),
        "it:4": m("it:4")}.items()}
    vecs = {"it:1": [1.0, 0.0], "it:2": vec(0.60), "it:3": vec(0.60), "vd:A": vec(0.58), "it:4": vec(0.85)}
    pairs, _ = build_pairs(ms, vecs, AliasTable([]), CFG)
    route = {(p.a, p.b): (p.route, p.via) for p in pairs}
    assert route[("it:1", "it:2")] == ("decide", "name")  # 구체 이름 공유 + 0.55 이상
    assert route[("it:1", "it:3")][0] == "none"  # 회사 이름(OpenAI)만 공유는 generic, 이름 공유 없음
    assert route[("it:1", "vd:A")] == ("decide", "name")  # 채널 넘음도 이름 경로
    assert route[("it:1", "it:4")][0] == "auto"


def test_label_sheet_keeps_other_weeks_rows(tmp_path):
    """W40·W41을 차례로 돌려도 앞 주 decide 라벨이 지워지지 않는다(PR #9 리뷰 반영 재실행)."""
    import csv

    from trendsit.brief.report import _merge_csv

    p = tmp_path / "decide.csv"
    cols = ["week", "a", "b", "answer", "label", "critique", "labeler"]
    keep = ("label", "critique", "labeler")
    _merge_csv(p, ("week", "a", "b"), cols, [{"week": "W41", "a": "x", "b": "y", "answer": "same"}], keep, "W41")
    rows = list(csv.DictReader(p.open()))
    rows[0]["label"] = "same"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    _merge_csv(p, ("week", "a", "b"), cols, [{"week": "W40", "a": "m", "b": "n", "answer": "diff"}], keep, "W40")
    got = {(r["week"], r["a"], r["label"]) for r in csv.DictReader(p.open())}
    assert got == {("W41", "x", "same"), ("W40", "m", "")}


def test_merge_csv_never_drops_same_week_rows_missing_from_a_regen(tmp_path):
    """R2-10(5.15-4): 재생성이 같은 주에 더 적은 쌍을 내도(묶기 결과가 달라짐) 기존에 사람이 라벨을 채운 행을
    지우지 않는다(58→36으로 줄던 버그)."""
    import csv

    from trendsit.brief.report import _merge_csv

    p = tmp_path / "decide.csv"
    cols = ["week", "a", "b", "answer", "label", "critique", "labeler"]
    keep = ("label", "critique", "labeler")
    _merge_csv(p, ("week", "a", "b"), cols,
              [{"week": "W41", "a": "x", "b": "y", "answer": "same"}, {"week": "W41", "a": "p", "b": "q", "answer": "diff"}],
              keep, "W41")
    rows = list(csv.DictReader(p.open()))
    for r in rows:
        r["label"], r["labeler"] = "same", "opus-5.5"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    _merge_csv(p, ("week", "a", "b"), cols, [{"week": "W41", "a": "x", "b": "y", "answer": "same"}], keep, "W41")
    got = {(r["week"], r["a"], r["label"]) for r in csv.DictReader(p.open())}
    assert got == {("W41", "x", "same"), ("W41", "p", "same")}  # p-q는 재생성에 없어도 지워지지 않음
