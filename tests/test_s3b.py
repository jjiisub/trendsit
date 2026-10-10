"""S3 3b 글 분석가: 녹화 HTTP 픽스처(S1 window의 GeekNews 원문 페이지)로 오프라인 루프(A9), 깊이·도구 상한(A10), enforce.

원래 글 = GeekNews 토픽(깊이 1, 이미 읽음), 원문 = danbom425.tistory.com/113(깊이 2, 녹화). LLM은 모의 전송.
"""

import json

import pytest

from tests.conftest import FakeTransport, make_ctx, response
from tests.test_s1b import FixtureTransport, fetcher_for
from trendsit.core.artifacts import apply_enforce
from trendsit.core.artifacts_text import ItemCardV1, ItemCardV2, TextAnalystInput
from trendsit.core.role import load_role
from trendsit.deep.text_agent import build_input, checks_from_v1, run_text_analysis, write_traces
from trendsit.summarize import load_card

TOPIC = "https://news.hada.io/topic?id=34873"
ORIGIN = "https://danbom425.tistory.com/113"
SENT = "Defects4J v3.0의 실제 결함 233건, 함수 318개를 놓고"

V1 = {"quotes": [{"n": 1, "text": "실제 결함 233건과 함수 318개로 모델 11개를 시험함"}],
      "numbers": [{"quote_n": 1, "value": "233건", "unit": "", "what": "실제 결함 수"}],
      "claims": [{"quote_ns": [1], "text": "에이전트 테스트가 버그를 정답으로 박제"}],
      "summary": "버그 있는 코드로 만든 테스트가 버그를 정답으로 박제한다는 연구를 소개했다.", "entities": [],
      "keywords": ["coding-agent"], "is_curation": True, "origin_candidates": [1], "relevance_reason": "x",
      "relevance": "high", "needs_original_reason": "수치 출처가 원문", "needs_original": True, "log": "x",
      "attention": False}


def call(tool_name, **args):
    return response(tool_calls=[(f"c-{tool_name}-{json.dumps(args, sort_keys=True)}", tool_name, args)])


def v2(**kw):
    base = {"trail": [{"url": ORIGIN, "depth": 2, "reason": "GeekNews → 원문 블로그"}],
            "quotes": [{"n": 1, "url": ORIGIN, "text": SENT}],
            "verified": [{"check_n": 1, "quote_n": 1, "status": "confirmed"}, {"check_n": 2, "quote_n": None,
                                                                                "status": "not_found"}],
            "differences": [], "origin": {"url": ORIGIN, "kind": "other", "title": "에이전트가 쓴 테스트", "date": "2026-09-22"},
            "numbers": [{"quote_n": 1, "value": "233건", "unit": "", "what": "실제 결함 수"}],
            "claims": [{"quote_ns": [1], "text": "실제 결함 233건으로 시험"}], "summary": "원문 기준 요약이다.",
            "log": "GeekNews → 원문(깊이 2), 수치 1개 일치", "attention": False}
    return base | kw


@pytest.fixture
def make(tmp_path):
    def build(llm):
        c = make_ctx(tmp_path, FakeTransport(llm), spec_cap=1.0)
        c.resources.update(fetcher=fetcher_for(FixtureTransport("window")))
        db = c.db
        db.conn.execute("INSERT INTO sources(id, channel, kind, name) VALUES ('geeknews', 'text', 'curation', 'GeekNews')")
        db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, url, title, day) "
                        "VALUES (6, 'geeknews', 'text', 'topic:34873', ?, '에이전트가 쓴 테스트는 무엇을 증명하나', '2026-10-06')",
                        (TOPIC,))
        db.conn.execute("INSERT INTO links(item_id, url, kind, anchor, role) VALUES (6, ?, 'other', '원문', 'origin_candidate')",
                        (ORIGIN,))
        db.conn.execute("INSERT INTO item_cards(item_id, version, card_json) VALUES (6, 1, ?)", (json.dumps(V1),))
        db.conn.commit()
        return c
    return build


def tool_steps(c):
    return [s for s in c.db.steps_of(c.tracer.run_id) if s["kind"] == "tool"]


def test_checks_and_input():
    checks = checks_from_v1(ItemCardV1.model_validate(V1))
    assert [(c.n, c.kind) for c in checks] == [(1, "number"), (2, "claim")] and "233건" in checks[0].text


def test_finds_origin_at_depth2_offline(make, tmp_path):
    c = make([call("fetch_page", url=ORIGIN, parent=TOPIC), call("finish", **v2())])
    res = run_text_analysis(c, [(6, 2)])
    steps = tool_steps(c)
    assert not steps[0]["error"] and json.loads(steps[0]["detail"])["depth"] == 2
    assert res.origin_found == 1 and res.depths == {2: 1} and res.statuses == {"confirmed": 1, "not_found": 1}
    card = load_card(c.db, 6, 2)
    assert card["verified"][0]["status"] == "confirmed" and card["origin"]["url"] == ORIGIN
    assert load_card(c.db, 6, 1)["summary"] == V1["summary"]  # v1은 덮지 않음
    tool_msg = [m for m in c.llm.transport.bodies[-1]["messages"] if m["role"] == "tool"][0]["content"]
    assert "토론토대 연구진" in tool_msg and "[남은 도구 호출 5회]" in tool_msg
    (p,) = write_traces(res.traces, tmp_path / "tr", "cmd")
    text = p.read_text(encoding="utf-8")
    assert "| 1 | fetch_page |" in text and "| 2 |" in text and "confirmed" in text


def test_not_found_is_normal_when_depth_limit_blocks(make):
    fb = v2(trail=[], quotes=[], origin=None, numbers=[], claims=[], summary=V1["summary"], log="원본 찾지 못함",
            verified=[{"check_n": 1, "quote_n": None, "status": "not_found"}, {"check_n": 2, "quote_n": None,
                                                                              "status": "not_found"}])
    c = make([call("fetch_page", url=ORIGIN, parent=TOPIC), call("finish", **fb)])
    res = run_text_analysis(c, [(6, 1)])  # 계획이 깊이 1을 주면 원문(깊이 2)도 못 연다
    assert "깊이 상한 초과" in tool_steps(c)[0]["error"]
    assert res.origin_found == 0 and load_card(c.db, 6, 2)["attention"] is False


def test_trap_reading_unlinked_doc_without_parent(make):
    c = make([call("fetch_page", url="https://danbom425.tistory.com/999", parent=None),
              call("fetch_page", url="https://danbom425.tistory.com/999", parent=ORIGIN),
              call("finish", **v2(trail=[], quotes=[], origin=None, numbers=[], claims=[],
                                  verified=[{"check_n": 1, "quote_n": None, "status": "not_found"}]))])
    run_text_analysis(c, [(6, 3)])
    errs = [s["error"] for s in tool_steps(c)[:2]]
    assert "시작 문서가 아님" in errs[0] and "아직 읽지 않음" in errs[1]


def test_confirmed_without_fetched_quote_becomes_not_found(make):
    # 페이지를 열지 않고 confirmed를 냄 → enforce가 not_found로, origin도 trail에 없으면 지움
    c = make([call("finish", **v2(trail=[]))])
    run_text_analysis(c, [(6, 2)])
    card = load_card(c.db, 6, 2)
    assert card["quotes"] == [] and card["verified"][0] == {"check_n": 1, "quote_n": None, "status": "not_found"}
    assert card["origin"] is None and card["numbers"] == [] and card["claims"] == []
    detail = json.loads([s for s in c.db.steps_of(c.tracer.run_id) if s["kind"] == "code"][-1]["detail"])
    rules = {e["rule"] for e in detail["enforced"]}
    assert "가져온 페이지에 없는 인용 삭제" in rules and "origin.url을 이번 실행에서 열지 않음" in rules


def test_differs_sets_attention():
    inp = TextAnalystInput.model_validate({"item_id": 6, "title": "t", "source_name": "GeekNews", "url": TOPIC,
                                           "max_depth": 2, "card_v1": V1, "links": [], "checks": []})

    class Ctx:
        resources = {"fetched_pages": {ORIGIN: f"앞 문장. {SENT} 뒤 문장."}}

    out = apply_enforce(ItemCardV2.model_validate(v2(verified=[{"check_n": 1, "quote_n": 1, "status": "differs"}],
                                                     differences=["요약 '233건', 원본 '233건 중 일부'"])), inp, Ctx())
    assert out.attention is True and out.verified[0].status == "differs"


def test_tool_cap_and_role_settings(make, models):
    role = load_role("text_analyst", models)
    assert role.spec.max_tool_calls == 6 and set(role.spec.tools) == {"fetch_page", "read_more", "arxiv", "github_repo"}
    calls = [call("read_more", doc=ORIGIN, part=i + 2) for i in range(7)]
    c = make([*calls, call("finish", **v2(trail=[], quotes=[], origin=None, numbers=[], claims=[],
                                          verified=[{"check_n": 1, "quote_n": None, "status": "not_found"}]))])
    run_text_analysis(c, [(6, 2)])
    steps = tool_steps(c)
    assert sum(1 for s in steps if s["text"].endswith("상한으로 거부")) == 1  # 7번째는 실행하지 않음


@pytest.mark.parametrize("url", ["https://github.com/Foo/Bar", "http://example.com/a", "https://arxiv.org/pdf/2401.01234v2"])
def test_read_more_page_key(url):
    """C-7: fetch_page(u) 뒤 read_more(doc=u)가 거부되지 않는다(github 대문자, http, arxiv pdf). 네트워크 없이 fetcher 대역."""
    from types import SimpleNamespace

    from trendsit.core.agent import DepthTracker
    from trendsit.tools.web import FetchArgs, ReadMoreArgs, fetch_page, read_more

    class Fetched:
        ok, text, content_type, error = True, "가" * 3500, "text/plain", None
        final_url = url

    class FakeFetcher:
        def fetch(self, u, kind):
            return Fetched()

    state = SimpleNamespace(extras={"fetcher": FakeFetcher(), "link_kinds": object()}, depth=DepthTracker(None))
    args = FetchArgs(url=url, parent=None)
    state.depth.roots.add(args.url)
    assert fetch_page(args, state).content["parts"] == 2
    out = read_more(ReadMoreArgs(doc=url, part=2), state)
    assert out.content["part"] == 2 and out.content["text"] == "가" * 500


def test_github_and_web_tools_keep_their_own_fetcher():
    """github 도구는 캐시 없는 fetcher, 웹 도구는 HTTP 캐시 fetcher. 어느 쪽을 먼저 불러도 서로 덮지 않는다."""
    from types import SimpleNamespace

    from trendsit.tools import github, web

    for first, second in ((github, web), (web, github)):
        state = SimpleNamespace(extras={})
        first.resources(state)
        second.resources(state)
        assert not state.extras["github_fetcher"].use_cache and state.extras["fetcher"].use_cache


def test_read_more_and_fallback(make):
    c = make([call("fetch_page", url=ORIGIN, parent=TOPIC), call("read_more", doc=ORIGIN, part=2),
              call("read_more", doc=ORIGIN, part=9), call("finish", **v2())])
    run_text_analysis(c, [(6, 2)])
    steps = tool_steps(c)
    assert not steps[1]["error"] and "조각은 2개까지" in steps[2]["error"]
    inp = build_input(c.db, 6, 2)
    fb = ItemCardV2.fallback("x", inp)
    assert fb.summary == V1["summary"] and fb.attention is False and {v.status for v in fb.verified} == {"not_found"}
    assert inp.depth_seed()[0][0] == TOPIC and inp.depth_limit(4) == 2


def test_text_analyst_graders():
    from eval import graders
    from eval.graders_text import aggregate_text_analyst

    inp = {"checks": [{"n": 1, "kind": "number", "text": "x", "quote": "q"}]}
    good = v2(verified=[{"check_n": 1, "quote_n": 1, "status": "confirmed"}])
    assert graders.code_grade("text_analyst", inp, good, None, {})["passed"]
    bad = v2(verified=[{"check_n": 1, "quote_n": 7, "status": "differs"}], origin={**v2()["origin"], "url": "https://x"})
    failed = " ".join(graders.code_grade("text_analyst", inp, bad, None, {})["failed"])
    assert "인용 번호" in failed and "origin이 trail 안" in failed and "differences" in failed
    changed = {"field": "verified", "before": [{"check_n": 1, "quote_n": 1, "status": "confirmed"}],
               "after": [{"check_n": 1, "quote_n": None, "status": "not_found"}], "rule": "x"}
    rec = {"output": good, "enforced": [changed]}
    m, reasons = aggregate_text_analyst([rec, {"output": good}])
    assert m["근거 없는 판정(enforce 전, 부분 확인 포함)"] == 1 and not reasons and m["깊이 분포"] == "2:2"
    _, reasons = aggregate_text_analyst([rec, rec])
    assert reasons


def test_trail_and_depth_come_from_actual_fetches(make):
    # 모델이 깊이를 1로, 열지 않은 페이지를 trail에 적음 → 코드가 연 페이지만 남기고 깊이 2로
    fake = v2(trail=[{"url": ORIGIN, "depth": 1, "reason": "원문"},
                     {"url": "https://never-opened.example/x", "depth": 2, "reason": "지어냄"}])
    c = make([call("fetch_page", url=ORIGIN, parent=TOPIC), call("finish", **fake)])
    res = run_text_analysis(c, [(6, 2)])
    card = load_card(c.db, 6, 2)
    assert card["trail"] == [{"url": ORIGIN, "depth": 2, "reason": "원문"}] and res.depths == {2: 1}


def test_page_keys_for_github_and_arxiv():
    from trendsit.core.artifacts_text import page_key

    assert page_key("https://github.com/NousResearch/hermes-agent/") == page_key("https://github.com/nousresearch/hermes-agent")
    assert page_key("http://arxiv.org/abs/2501.01234v2") == "https://arxiv.org/abs/2501.01234"


def test_same_host_links_are_followable():
    from trendsit.tools.web import page_links

    xml = ('<doc><ref target="/research/paper-x">논문</ref><ref target="https://other.example/a">외부</ref>'
           '<ref target="#top">위로</ref><ref target="mailto:a@b">메일</ref></doc>')
    links = page_links(xml, "https://www.anthropic.com/news/post")
    assert [x["url"] for x in links] == ["https://www.anthropic.com/research/paper-x", "https://other.example/a"]


def test_github_name_rejects_path_traversal():
    from trendsit.tools.github import RepoArgs

    for bad in ("../user", "a/..", "./x"):
        with pytest.raises(ValueError):
            RepoArgs(name=bad)


def test_eval_registers_github_readme_as_fetched_page(tmp_path, monkeypatch):
    """평가 경로도 운영과 같이 항목마다 fetched_pages를 새로 만든다. github_repo가 첫 호출이어도 README 인용이 남는다."""
    from eval import graders, run_eval
    from trendsit.core.textclean import clean_markdown

    repo = "https://github.com/NVIDIA/OpenShell"
    fx = json.loads((run_eval.ROOT / "eval" / "fixtures" / "text_analyst" / "dev-it5.json").read_text())
    fx["input"]["links"] = [{"n": 1, "url": repo, "kind": "레포", "anchor": None, "candidate": True}]
    readme = FixtureTransport("repo_tools").index["https://api.github.com/repos/NVIDIA/OpenShell/readme"]
    sent = next(s.strip() for s in clean_markdown(__import__("gzip").decompress(readme[0].read_bytes()).decode())
                .split("\n") if len(s.strip()) > 40)
    checks = [c["n"] for c in fx["input"]["checks"]]
    out = v2(trail=[{"url": repo, "depth": 2, "reason": "원문 → 레포"}], quotes=[{"n": 1, "url": repo, "text": sent}],
             verified=[{"check_n": checks[0], "quote_n": 1, "status": "confirmed"}]
             + [{"check_n": n, "quote_n": None, "status": "not_found"} for n in checks[1:]],
             origin={"url": repo, "kind": "repo", "title": "OpenShell", "date": None}, numbers=[],
             claims=[{"quote_ns": [1], "text": "에이전트 런타임"}])
    fx_dir = tmp_path / "fixtures" / "text_analyst"
    fx_dir.mkdir(parents=True)
    (fx_dir / "it5.json").write_text(json.dumps(fx, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(run_eval, "FIXTURES", tmp_path / "fixtures")
    monkeypatch.setattr(run_eval, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(run_eval, "ROOT", tmp_path)
    monkeypatch.setattr(graders, "llm_grade", lambda *a: {"verdicts": {}, "scores": {}, "missing": []})
    c = make_ctx(tmp_path, FakeTransport([call("github_repo", name="NVIDIA/OpenShell"), call("finish", **out)]),
                 spec_cap=1.0)
    c.resources.update(github_fetcher=fetcher_for(FixtureTransport("repo_tools")), github_headers={})
    c.resources["fetched_pages"] = {"stale": "이전 픽스처"}  # 이전 픽스처의 기록은 지워져야 함
    rec = run_eval._evaluate(c, "text_analyst", None, None, "t")["results"][0]
    assert not any(e["field"] in ("quotes", "verified") for e in rec.get("enforced") or [])
    assert rec["output"]["verified"][0]["status"] == "confirmed"
    assert "stale" not in c.resources["fetched_pages"]


def test_r3_partial_confirmation_demoted():
    """PR #6 리뷰 R3: confirmed인데 check 수치가 인용에 없으면 not_found. 모델·버전 이름, 한국어 큰 단위, 작은 개수는 대조 안 함."""
    from trendsit.core.artifacts_text import PARTIAL_RULE, figures

    assert figures("GPT-6 아스트라, 2억8000만개, 6개 작업, 8.9% 증가, 2.62배, 1,300개, 2026년") == ["8.9", "2.62", "1300"]
    inp = TextAnalystInput.model_validate({"item_id": 6, "title": "t", "source_name": "GeekNews", "url": TOPIC,
                                           "max_depth": 2, "card_v1": V1, "links": [], "checks": [
                                               {"n": 1, "kind": "number", "text": "결함 233건", "quote": "q"},
                                               {"n": 2, "kind": "claim", "text": "속도 2.62배 향상", "quote": "q"}]})
    out = ItemCardV2.model_validate(v2(verified=[{"check_n": 1, "quote_n": 1, "status": "confirmed"},
                                                 {"check_n": 2, "quote_n": 1, "status": "confirmed"}]))
    got = out.demote_partial(inp)
    assert [v.status for v in got.verified] == ["confirmed", "not_found"]  # 233은 인용에 있음, 2.62는 없음
    assert got.enforced[-1]["rule"] == PARTIAL_RULE


def test_r3_n2_regrade_saved_text_analyst():
    """저장된 맥 평가에 R3을 이어 적용: it201·it933·it997이 내려가고, S5부터 근거 없는 판정 문턱값에 들어감(P4-7)."""
    from pathlib import Path

    from eval.graders_text import aggregate_text_analyst, reenforce_text_analyst

    rep = Path(__file__).parents[1] / "reports" / "eval" / "text_analyst_generate_20261008-195542.json"
    results = json.loads(rep.read_text())["results"]
    changed = []
    for x in results:
        enforced, out = reenforce_text_analyst(x)
        if any(e["rule"] == "부분 확인: check 수치가 인용에 없음 → not_found" for e in enforced):
            changed.append(x["id"])
        x["enforced"], x["enforced_output"] = enforced, out
    assert changed == ["it201", "it933", "it997"]
    metrics, reasons = aggregate_text_analyst(results)
    # S5 P4-7: 부분 확인 내림도 근거 없는 판정 문턱값(0~1건)에 들어가 이 저장 평가는 미달이 된다
    assert metrics["그중 부분 확인 내림"] == 5 and metrics["근거 없는 판정(enforce 전, 부분 확인 포함)"] == 5
    assert reasons and "부분 확인 내림 5" in reasons[0]


def test_r3_differs_kept():
    """differs는 부분 확인 내림 대상이 아니다(요약 수치와 원본이 다르다는 판정이라 check 수치가 인용에 없는 것이 정상)."""
    inp = TextAnalystInput.model_validate({"item_id": 6, "title": "t", "source_name": "GeekNews", "url": TOPIC,
                                           "max_depth": 2, "card_v1": V1, "links": [], "checks": [
                                               {"n": 1, "kind": "number", "text": "속도 2.62배 향상", "quote": "q"}]})
    out = ItemCardV2.model_validate(v2(verified=[{"check_n": 1, "quote_n": 1, "status": "differs"}],
                                       differences=["요약 '2.62배', 원본에는 다른 수치"]))
    got = out.demote_partial(inp)
    assert got is out and got.verified[0].status == "differs" and got.enforced == []
