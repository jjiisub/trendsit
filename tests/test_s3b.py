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
    assert m["근거 없는 판정(enforce 전)"] == 1 and not reasons and m["깊이 분포"] == "2:2"
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
