import pytest

from eval import graders

README = "# B\nPython HTTP client library with sync and async APIs."


def grade(oneliner, attention=False, expect=None, basis="Python HTTP client library", readme=README):
    out = {"basis": basis, "oneliner": oneliner, "log": "README 근거", "attention": attention}
    return graders.code_grade("repo_oneliner", {"readme_head": readme}, out, None, expect or {"max_len": 60})


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


def test_basis_must_be_in_readme():
    assert grade("HTTP 클라이언트", basis="Python  HTTP\nclient library")["passed"]  # 공백 정규화
    r = grade("HTTP 클라이언트", basis="the fastest HTTP client")
    assert not r["passed"] and any("basis" in f for f in r["failed"])
    assert not grade("HTTP 클라이언트", basis="")["passed"]  # 문장이 있으면 근거도 있어야


def test_empty_oneliner_needs_attention():
    assert grade("", basis="", attention=True)["passed"]
    assert not grade("", basis="", attention=False)["passed"]


def test_style_check_catches_haeyo_in_log():
    out = {"basis": "", "oneliner": "", "log": "README를 보고 썼어요", "attention": True}
    r = graders.code_grade("repo_oneliner", {"readme_head": README}, out, None, {})
    assert not r["passed"] and any("해요체" in f for f in r["failed"])


def test_schema_failure_is_code_failure():
    r = graders.code_grade("repo_oneliner", {}, None, "RoleFailed", {})
    assert not r["passed"] and r["checks"][0]["name"] == "스키마"


def test_rubric_parsing():
    assert list(graders.rubric_questions("repo_oneliner")) == ["Q1", "Q2", "Q3"]
    assert graders.rubric_criteria("repo_oneliner") == ["정확성", "구체성", "표현"]


def _res(v=("pass", "pass", "pass"), code=True, missing=()):
    if not code:
        return {"code": {"passed": False}}
    verdicts = {q: {"verdict": x, "critique": ""} for q, x in zip(["Q1", "Q2", "Q3"], v, strict=True) if q not in missing}
    return {"code": {"passed": True}, "llm": {"verdicts": verdicts, "scores": {}, "missing": list(missing)}}


def test_summarize_thresholds():
    assert graders.summarize("repo_oneliner", [_res()] * 10)["passed"]
    one_q2 = [_res()] * 9 + [_res(("pass", "fail", "pass"))]
    assert graders.summarize("repo_oneliner", one_q2)["passed"]  # Q2 9/10은 통과
    one_q1 = [_res()] * 9 + [_res(("fail", "pass", "pass"))]
    s = graders.summarize("repo_oneliner", one_q1)
    assert not s["passed"] and any(r.startswith("Q1") for r in s["fail_reasons"])
    two_q3 = [_res()] * 8 + [_res(("pass", "pass", "fail"))] * 2
    assert any(r.startswith("Q3") for r in graders.summarize("repo_oneliner", two_q3)["fail_reasons"])
    code_fail = [_res()] * 9 + [_res(code=False)]
    assert any("코드 채점" in r for r in graders.summarize("repo_oneliner", code_fail)["fail_reasons"])


def test_missing_question_fails():
    rows = [_res()] * 9 + [_res(missing=("Q1",))]
    s = graders.summarize("repo_oneliner", rows)
    assert not s["passed"] and any("누락" in r for r in s["fail_reasons"])
