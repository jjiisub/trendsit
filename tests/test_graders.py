import pytest

from eval import graders


def grade(oneliner, attention=False, expect=None):
    out = {"oneliner": oneliner, "log": "README 근거", "attention": attention}
    return graders.code_grade("repo_oneliner", {}, out, None, expect or {"max_len": 60})


@pytest.mark.parametrize("line,ok", [
    ("로컬에서 오픈웨이트 LLM을 내려받아 실행하는 런타임", True),
    ("Python용 HTTP 클라이언트 라이브러리", True),
    ("로컬에서 LLM을 실행한다.", False),
    ("LLM을 실행할 수 있어요", False),
    ("혁신적인 AI 도구", False),
    ("강력한 HTTP 클라이언트", False),
    ("HTTP 클라이언트 라이브러리.", False),
])
def test_code_grade_oneliner(line, ok):
    assert grade(line)["passed"] is ok


def test_length_and_keyword_and_attention():
    assert not grade("가" * 61)["passed"]
    assert not grade("HTTP 라이브러리", expect={"must_include_any": ["형태소"]})["passed"]
    assert grade("한국어 형태소 분석기", expect={"must_include_any": ["형태소"]})["passed"]
    assert not grade("이미지 수집 스크립트", expect={"attention": True})["passed"]
    assert grade("이미지 수집 스크립트", attention=True, expect={"attention": True})["passed"]


def test_style_check_catches_haeyo_in_log():
    out = {"oneliner": "HTTP 클라이언트", "log": "README를 보고 썼어요", "attention": False}
    r = graders.code_grade("repo_oneliner", {}, out, None, {})
    assert not r["passed"] and any("해요체" in f for f in r["failed"])


def test_schema_failure_is_code_failure():
    r = graders.code_grade("repo_oneliner", {}, None, "RoleFailed", {})
    assert not r["passed"] and r["checks"][0]["name"] == "스키마"


def test_rubric_criteria():
    assert graders.rubric_criteria("repo_oneliner") == ["정확성", "구체성", "표현"]


def _res(scores, code=True):
    return {"code": {"passed": code},
            "llm": {"scores": {c: {"score": s, "reason": ""} for c, s in zip(["정확성", "구체성", "표현"], scores,
                                                                              strict=True)}} if code else None}


def test_summarize_thresholds():
    good = [_res((5, 4, 4))] * 9 + [_res((4, 4, 4))]
    assert graders.summarize("repo_oneliner", good)["passed"]
    one = [_res((5, 5, 5))] * 9 + [_res((1, 5, 5))]
    s = graders.summarize("repo_oneliner", one)
    assert not s["passed"] and any("1점" in r for r in s["fail_reasons"])
    low = [_res((5, 5, 5))] * 9 + [_res((5, 2, 5))]
    assert any("3점 미만" in r for r in graders.summarize("repo_oneliner", low)["fail_reasons"])
    code_fail = [_res((5, 5, 5))] * 9 + [_res((), code=False)]
    assert any("코드 채점" in r for r in graders.summarize("repo_oneliner", code_fail)["fail_reasons"])


def test_missing_criterion_fails():
    rows = [_res((5, 5, 5))] * 10
    rows[0] = {"code": {"passed": True}, "llm": {"scores": {"구체성": {"score": 5, "reason": ""},
                                                            "표현": {"score": 5, "reason": ""}},
                                               "missing": ["정확성"]}}
    s = graders.summarize("repo_oneliner", rows)
    assert not s["passed"] and any("누락" in r for r in s["fail_reasons"])
