"""S3 3c 레포 분석가: 오프라인 에이전트 루프(A9), 깊이별 허용 도구·도구 상한(A10), 과열 규칙, 규칙 기반 큐, enforce.

GitHub 응답은 tests/fixtures/http/repo_tools(레포 정보·README는 S1 녹화, ollama·hermes 커밋·기여자·릴리스는 합성, 실제 녹화 3개 레포 추가), LLM은 모의 전송.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from tests.conftest import FakeTransport, make_ctx, response
from tests.test_s1b import FixtureTransport, fetcher_for
from trendsit.core import config
from trendsit.core.artifacts import apply_enforce
from trendsit.core.artifacts_repo import HypeCheck, ItemTitle, RepoAnalystInput, RepoCard
from trendsit.core.role import load_role
from trendsit.deep.repo_agent import (
    HYPE_STARS_WEEK,
    QueueItem,
    build_input,
    hype_check,
    rule_queue,
    run_repo_analysis,
)

WEEK = "2026-W41"


def call(tool_name, **args):
    return response(tool_calls=[(f"c-{tool_name}-{json.dumps(args, sort_keys=True)}", tool_name, args)])


def card(**kw):
    base = dict(evidence=[{"fact": "README: run LLMs locally", "tool": "github_repo"}],
                relevant_reason="로컬 LLM", relevant=True, why_trending="v0.12.3 릴리스", hype_flags=[],
                release={"tag": "v0.12.3", "date": "2026-10-02", "line": "새 모델 지원"},
                related_item_ids=["it:1"], signal_reason="릴리스", signal="release", log="ollama: 릴리스", attention=False)
    return base | kw


ONELINER = response(json.dumps({"basis": "x", "oneliner": "로컬 LLM 실행 도구", "log": "README", "attention": False},
                               ensure_ascii=False))


@pytest.fixture
def ctx(tmp_path):
    def make(llm_responses):
        c = make_ctx(tmp_path, FakeTransport(llm_responses), spec_cap=1.0)
        c.resources.update(fetcher=fetcher_for(FixtureTransport("repo_tools")), today=date(2026, 10, 8),
                           github_headers={})
        db = c.db
        for name, stars, kws, status in (("ollama/ollama", 300, {"open-weight": "title"}, "pass"),
                                         ("NousResearch/hermes-agent", HYPE_STARS_WEEK + 500, {"agent": "title"}, "pass"),
                                         ("someone/recipes", 5000, {}, "filtered")):
            db.conn.execute("INSERT INTO repos(full_name, description, readme_head) VALUES (?, ?, ?)",
                            (name, f"{name} desc", "Get up and running with large language models."))
            db.conn.execute("INSERT INTO repo_trending(week, full_name, rank, stars_total, stars_this_week, forks, "
                            "filter_status, keywords) VALUES (?,?,?,?,?,?,?,?)",
                            (WEEK, name, 1, 100000, stars, 10, status, json.dumps(kws)))
        db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, title, week) "
                        "VALUES (1, 'geeknews', 'text', 'e1', 'Ollama 0.12 출시', ?)", (WEEK,))
        db.conn.execute("INSERT INTO item_cards(item_id, version, card_json) VALUES (1, 1, ?)",
                        (json.dumps({"summary": "ollama 새 버전", "entities": ["Ollama"], "relevance": "high"}),))
        db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, title, week, published_at) "
                        "VALUES (2, 'github_releases', 'github', 'e2', 'openai/codex rust-v0.9', ?, '2026-10-06')", (WEEK,))
        db.conn.commit()
        return c
    return make


def tool_steps(c):
    return [s for s in c.db.steps_of(c.tracer.run_id) if s["kind"] == "tool"]


def test_rule_queue_keyword_trending_then_tracked_releases(ctx):
    c = ctx([])
    q = rule_queue(c.db, WEEK, 10)
    assert [x.full_name for x in q] == ["NousResearch/hermes-agent", "ollama/ollama", "openai/codex"]
    assert "추적 레포 릴리스" in q[2].reason and rule_queue(c.db, WEEK, 1)[0].max_depth == 2


def test_hype_rules_from_api(ctx):
    c = ctx([])
    from trendsit.deep.repo_agent import trending_stats

    h = hype_check(c, "NousResearch/hermes-agent", trending_stats(c.db, WEEK, "NousResearch/hermes-agent"), "agent")
    assert h.flags == ["no_commits", "single_contributor"] and h.force_check and h.commits_7d == 0
    h = hype_check(c, "ollama/ollama", trending_stats(c.db, WEEK, "ollama/ollama"), "x")
    assert h.flags == [] and h.commits_7d is None and h.contributors == 3  # 급증 아님: 커밋은 세지 않음
    h = hype_check(c, "sindresorhus/awesome-ollama", None, None)
    assert "awesome_list" in h.flags and "API 실패" in h.note  # 녹화에 없는 레포: 규칙 미적용 + 이유


def test_agent_loop_offline_depth2(ctx):
    c = ctx([ONELINER, call("github_repo", name="ollama/ollama"), call("releases", name="ollama/ollama"),
             call("search_items", query="ollama"), call("finish", **card())])
    kw = config.load("keywords.yaml")
    res = run_repo_analysis(c, [QueueItem("ollama/ollama", 2, "트렌딩")], WEEK, kw)
    assert res.done == 1 and res.fallback == 0 and res.tool_calls == [3] and res.signals == {"release": 1}
    steps = tool_steps(c)
    assert [s["text"].split(":")[0] for s in steps] == ["github_repo", "releases", "search_items", "finish"]
    assert all(not s["error"] for s in steps)
    saved = json.loads(c.db.conn.execute("SELECT card_json FROM repo_cards").fetchone()[0])
    assert saved["oneliner"] == "로컬 LLM 실행 도구" and saved["related_item_ids"] == ["it:1"]
    # 도구 결과 내용: 릴리스와 칠판 검색이 실제 녹화/DB에서 왔는지
    tool_msgs = [m["content"] for m in c.llm.transport.bodies[-1]["messages"] if m["role"] == "tool"]
    assert "Get up and running" in tool_msgs[0] and tool_msgs[0].endswith("[남은 도구 호출 5회]")
    assert "v0.12.3" in tool_msgs[1] and "it:1" in tool_msgs[2]


def test_depth1_allows_only_repo_and_search(ctx):
    c = ctx([ONELINER, call("recent_commits", name="ollama/ollama", days=7),
             call("finish", **card(release=None, signal="trending"))])
    run_repo_analysis(c, [QueueItem("ollama/ollama", 1, "얕게")], WEEK, config.load("keywords.yaml"))
    steps = tool_steps(c)
    assert "허용되지 않은 도구 'recent_commits'" in steps[0]["error"]
    inp = RepoAnalystInput.model_validate({**_inp(), "max_depth": 1})
    assert inp.tool_names(load_role("repo_analyst", c.models).spec.tools) == ["github_repo", "search_items"]


def test_hype_force_check_is_enforced(ctx):
    c = ctx([ONELINER, call("github_repo", name="NousResearch/hermes-agent"),
             call("finish", **card(signal="trending", why_trending="", release=None, related_item_ids=["it:99"]))])
    res = run_repo_analysis(c, [QueueItem("NousResearch/hermes-agent", 2, "급증")], WEEK, config.load("keywords.yaml"))
    saved = json.loads(c.db.conn.execute("SELECT card_json FROM repo_cards").fetchone()[0])
    assert res.signals == {"check": 1}
    assert saved["signal"] == "check" and saved["attention"] is True
    assert saved["hype_flags"] == ["no_commits", "single_contributor"] and saved["related_item_ids"] == []
    detail = json.loads([s for s in c.db.steps_of(c.tracer.run_id) if s["kind"] == "code"][-1]["detail"])
    assert {e["rule"] for e in detail["enforced"]} >= {"7일 별 급증 + 커밋 0이면 check(코드)", "입력에 없는 글 id 삭제"}


def _inp(**kw):
    base = {"full_name": "a/b", "max_depth": 2, "reason": "r", "oneliner": "x", "keywords": ["에이전트"],
            "week_items": [{"id": "it:1", "title": "t"}],
            "hype": {"flags": [], "force_check": False}}
    return base | kw


def test_enforce_attention_when_why_without_evidence():
    out = apply_enforce(RepoCard.model_validate(card(evidence=[], signal="trending")),
                        RepoAnalystInput.model_validate(_inp()), None)
    assert out.attention is True and out.enforced[-1]["rule"] == "근거(evidence) 없이 why_trending을 씀"


def test_fallback_uses_number_rule():
    inp = RepoAnalystInput.model_validate(_inp(hype=HypeCheck(flags=["no_commits"], force_check=True).model_dump()))
    fb = RepoCard.fallback("걸음 상한", inp)
    assert fb.signal == "check" and fb.attention and fb.hype_flags == ["no_commits"]


def test_build_input_and_role_limits(ctx):
    c = ctx([ONELINER])
    inp = build_input(c, QueueItem("ollama/ollama", 2, "r"), WEEK, config.load("keywords.yaml"))
    assert inp.trending.stars_this_week == 300 and inp.oneliner == "로컬 LLM 실행 도구"
    assert inp.week_items == [ItemTitle(id="it:1", title="Ollama 0.12 출시")]
    role = load_role("repo_analyst", c.models)
    assert role.spec.max_tool_calls == 6
    # 같은 입력이면 한 줄 설명을 다시 부르지 않음(모의 전송에 남은 응답이 없어도 통과)
    assert build_input(c, QueueItem("ollama/ollama", 2, "r"), WEEK, config.load("keywords.yaml")).oneliner


def test_traces_written(ctx, tmp_path):
    from trendsit.deep.repo_agent import write_traces

    c = ctx([ONELINER, call("github_repo", name="ollama/ollama"), call("finish", **card())])
    res = run_repo_analysis(c, [QueueItem("ollama/ollama", 2, "트렌딩")], WEEK, config.load("keywords.yaml"))
    (p,) = write_traces(res.traces, tmp_path / "traces", "cmd")
    text = p.read_text(encoding="utf-8")
    assert p.name == "ollama__ollama.md" and "| 1 | github_repo | name=ollama/ollama | ok |" in text
    assert "이번 주 별 300" in text and '"oneliner": "로컬 LLM 실행 도구"' in text


def test_commits_404_does_not_count_as_zero(tmp_path):
    from trendsit.core.artifacts_repo import TrendingStats

    url = "https://api.github.com/repos/gone/repo/commits?since=2026-10-01T00:00:00Z&per_page=100"
    extra = {url: (404, "application/json", '{"message": "Not Found"}'),
             "https://api.github.com/repos/gone/repo/contributors?per_page=100&anon=1":
                 (404, "application/json", '{"message": "Not Found"}')}
    c = make_ctx(tmp_path, FakeTransport([]))
    c.resources.update(fetcher=fetcher_for(FixtureTransport("repo_tools", extra=extra)), today=date(2026, 10, 8),
                       github_headers={})
    h = hype_check(c, "gone/repo", TrendingStats(week=WEEK, stars_this_week=HYPE_STARS_WEEK + 1), None)
    assert h.flags == [] and not h.force_check and "404" in h.note
    assert hype_check(c, "../user", None, None).note.startswith("레포 이름 형식 오류")


def test_tool_call_limit_from_deep_yaml(ctx):
    c = ctx([ONELINER])
    inp = build_input(c, QueueItem("ollama/ollama", 2, "r"), WEEK, config.load("keywords.yaml"), tool_calls=2)
    assert inp.tool_call_limit(6) == 2
    inp = build_input(c, QueueItem("ollama/ollama", 2, "r"), WEEK, config.load("keywords.yaml"))
    assert inp.tool_calls == config.load("deep.yaml").repo_tool_calls_per_item


# ---------- 설계 결정 Q3: 실제 GitHub 녹화(recorded) 정상 경로 ----------
REAL = {"active": "NVIDIA/OpenShell", "release": "tile-ai/tilelang", "small": "pablostanley/yoinks"}


def real_state():
    from types import SimpleNamespace

    return SimpleNamespace(extras={"fetcher": fetcher_for(FixtureTransport("repo_tools")), "github_headers": {},
                                   "today": date(2026, 10, 8)})


def test_recorded_github_responses_normal_path():
    from trendsit.tools.github import (
        CommitsArgs,
        RepoArgs,
        contributors,
        github_repo,
        recent_commits,
        releases,
    )

    st = real_state()
    info = github_repo(RepoArgs(name=REAL["active"]), st).content
    assert info["full_name"] == REAL["active"] and info["stars"] > 10000 and info["readme_head"]
    active = recent_commits(CommitsArgs(name=REAL["active"]), st).content
    assert active["commits"] > 20 and active["authors"] > 5 and active["last_commit"]["date"].startswith("2026-10")
    assert contributors(RepoArgs(name=REAL["active"]), st).content["total"] == "100+"
    rel = releases(RepoArgs(name=REAL["active"]), st).content["releases"]
    assert rel[0]["tag"] == "dev" and rel[0]["prerelease"] is True and rel[1]["prerelease"] is False
    tl = releases(RepoArgs(name=REAL["release"]), st).content["releases"]
    assert tl[0]["date"] >= "2026-09-28" and tl[0]["prerelease"] is False
    small = recent_commits(CommitsArgs(name=REAL["small"]), st).content
    assert small == {"days": 7, "since": "2026-10-01T00:00:00Z", "commits": 0, "authors": 0, "last_commit": None}
    assert contributors(RepoArgs(name=REAL["small"]), st).content["total"] == 1
    assert releases(RepoArgs(name=REAL["small"]), st).content == {"releases": [], "note": "릴리스 없음"}


def test_recorded_fixtures_have_no_secrets_and_keep_synthetic():
    import gzip

    fix = Path(__file__).parent / "fixtures" / "http" / "repo_tools"
    idx = json.loads((fix / "index.json").read_text())
    assert sum(1 for m in idx.values() if m.get("synthetic")) == 5  # 합성(경계 사례) 유지
    assert sum(1 for u, m in idx.items() if m.get("recorded") and any(r in u for r in REAL.values())) == 15
    for m in idx.values():
        body = gzip.decompress((fix / m["file"]).read_bytes())
        assert not any(p in body for p in (b"ghp_", b"github_pat_", b"gho_", b"sk-or-"))


def test_github_token_not_persisted_or_sent_to_llm(ctx):
    """토큰은 GitHub 요청 헤더에만. 실행 기록 DB(steps, llm_calls, fetch_log 등)와 LLM 요청 본문에 남지 않는다."""
    fake = "github_pat_" + "FAKE" * 8  # 이어 붙여 만든다(verify_s0 A9 키 문자열 검사에 걸리지 않게)
    c = ctx([ONELINER, call("github_repo", name="ollama/ollama"), call("releases", name="ollama/ollama"),
             call("finish", **card())])
    c.resources["github_headers"] = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {fake}"}
    run_repo_analysis(c, [QueueItem("ollama/ollama", 2, "트렌딩")], WEEK, config.load("keywords.yaml"))
    assert len(tool_steps(c)) == 3
    dump = "\n".join(c.db.conn.iterdump())
    assert fake not in dump and "Authorization" not in dump
    assert fake not in json.dumps(c.llm.transport.bodies, ensure_ascii=False)


def test_agent_records_tool_results_per_run(ctx):
    """run_agent가 이번 실행의 도구 결과(이름, 성공 여부)를 ctx.resources에 남긴다(R1 enforce 근거)."""
    c = ctx([ONELINER, call("github_repo", name="ollama/ollama"), call("contributors", name="nobody/missing"),
             call("finish", **card(release=None, signal="trending"))])
    run_repo_analysis(c, [QueueItem("ollama/ollama", 2, "트렌딩")], WEEK, config.load("keywords.yaml"))
    assert c.resources["tool_results"] == [{"name": "github_repo", "ok": True}, {"name": "contributors", "ok": False}]


# ---------- PR #6 리뷰 R1, R4, 설계 결정 N1 ----------
def test_r1_all_github_tools_fail_403(ctx):
    """GitHub API 403(비인증 한도) 녹화: 실패한 도구를 출처로 쓴 evidence 삭제, attention·why_trending·signal 코드 규칙."""
    c = ctx([ONELINER, call("github_repo", name="ollama/ollama"), call("releases", name="ollama/ollama"),
             call("search_items", query="ollama"),
             call("finish", **card(evidence=[{"fact": "github_repo, releases 모두 HTTP 403으로 실패", "tool": "github_repo"},
                                             {"fact": "이번 주 글 it:1에서 언급", "tool": "search_items"}],
                                   why_trending="이번 주 릴리스", signal="release", attention=False))])
    deny = {u: 403 for u in FixtureTransport("repo_tools").index if "ollama/ollama" in u}
    c.resources["fetcher"] = fetcher_for(FixtureTransport("repo_tools", override=deny))
    run_repo_analysis(c, [QueueItem("ollama/ollama", 2, "트렌딩")], WEEK, config.load("keywords.yaml"))
    assert [r["ok"] for r in c.resources["tool_results"]] == [False, False, True]
    saved = json.loads(c.db.conn.execute("SELECT card_json FROM repo_cards").fetchone()[0])
    assert [e["tool"] for e in saved["evidence"]] == ["search_items"]
    assert saved["attention"] is True and saved["why_trending"] == "" and saved["signal"] == "trending"


def test_r1_tool_check_and_r4_raw_why_trending():
    from eval import graders

    out = card(evidence=[{"fact": "403", "tool": "github_repo"}]) | {"why_trending": "릴리스"}
    calls = [{"text": "github_repo: name=x", "error": "HTTP 403", "detail": None}, {"text": "finish: 최종 답 제출", "error": None}]
    got = graders.code_grade("repo_analyst", _inp(), out, None, {}, calls)
    assert "evidence 출처가 성공한 도구: github_repo" in got["failed"]
    no_ev = card(evidence=[], why_trending="근거 없는 이유", attention=True)  # attention이 true여도(코드 소유) 품질 실패
    assert any(f.startswith("evidence 없이 why_trending을 쓰지 않음") for f in
               graders.code_grade("repo_analyst", _inp(), no_ev, None, {}, [])["failed"])


def test_n1_invalid_run_by_github_tool_errors():
    """설계 결정 N1: 무효 실행(…-165334)은 '도구 오류로 무효', 정상 실행(…-182928)은 판정 불변."""
    from eval.graders_text import aggregate_repo_analyst

    rep = Path(__file__).parents[1] / "reports" / "eval"
    bad = json.loads((rep / "repo_analyst_generate_20261008-165334.json").read_text())["results"]
    good = json.loads((rep / "repo_analyst_generate_20261008-182928.json").read_text())["results"]
    metrics, reasons = aggregate_repo_analyst(bad)
    assert any(r.startswith("도구 오류로 무효") for r in reasons) and metrics["GitHub 도구 성공 0 항목"] == 10
    metrics, reasons = aggregate_repo_analyst(good)
    assert reasons == [] and metrics["GitHub 도구 오류율"] == 0.0
