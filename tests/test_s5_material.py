"""S5 1단계 재료 개선(P4-1): 판독 수치 kind, 표·대시보드 낮은 순위, 잘못 들은 수치 교정 후보."""

from __future__ import annotations

from trendsit.core.artifacts_video import Frame, SlideNumber, SlideReading
from trendsit.video.align import DENSE_FRAME, align, spoken_variant


def _frame(t: float, spoken: str = "") -> Frame:
    return Frame(t=t, path=f"frames/r/frame_{int(t):04d}.jpg", reason="scene-change", segment_index=None,
                 spoken_text=spoken)


def _reading(*nums: tuple[str, str, str, str]) -> SlideReading:
    return SlideReading(frame_kind="slide", ocr_text=" ".join(n[0] for n in nums),
                        numbers=[SlideNumber(confidence="high", value=v, unit=u, what=w, kind=k) for v, u, w, k in nums],
                        table=None, title="", log="판독", attention=False)


def test_only_claims_become_slide_only():
    r = _reading(("80.3%", "%", "SWE-Bench Pro", "claim"), ("512", "MB", "memory setting", "ui"),
                 ("42", "", "example input", "example"), ("100", "", "y axis", "axis"))
    res = align([(_frame(10), r)], [], item_id=7)
    assert [f.value for f in res.slide_only] == ["80.3%"]
    assert sorted(x["why"] for x in res.excluded) == ["kind=axis", "kind=example", "kind=ui"]


def test_old_readings_without_kind_are_claims():
    n = SlideNumber.model_validate({"confidence": "high", "value": "35%", "unit": "%", "what": "x"})
    assert n.kind == "claim"


def test_dense_frame_facts_go_last():
    dense = _reading(*[(f"{i}.5%", "%", f"row {i}", "claim") for i in range(DENSE_FRAME)])
    normal = _reading(("61%", "%", "pass rate", "claim"))
    res = align([(_frame(5), dense), (_frame(60), normal)], [], item_id=7)
    assert res.slide_only[0].value == "61%" and not res.slide_only[0].dense
    assert all(f.dense for f in res.slide_only[1:]) and len(res.slide_only) == DENSE_FRAME + 1


def test_misheard_value_is_recorded_as_correction():
    spoken = "and on Sweebench Pro we got 88% which is a big jump"
    res = align([(_frame(30, spoken), _reading(("80.3%", "%", "SWE-Bench Pro", "claim")))], [], item_id=7)
    assert len(res.slide_only) == 1 and res.slide_only[0].spoken_value == "88%"


def test_no_correction_for_unrelated_numbers():
    assert spoken_variant("SWE-Bench Pro", "80.3%", "%", "latency dropped 40% this quarter") == ""
    assert spoken_variant("SWE-Bench Pro", "80.3%", "%", "SWE-Bench Pro 80.3%") == ""  # 같은 값
    assert spoken_variant("users", "1.2M", "", "users grew to 2 million") == ""  # 단위 종류 없음


def test_evidence_cap_is_code_owned_not_a_failure():
    """P4-6: 포인트 근거가 상한을 넘어도 통과 판정 실패가 아니다(enforce가 자르고 모델 일치율로 기록)."""
    from eval import graders
    from tests.test_s4_roles import summary, summary_input

    s = summary(key_points=[{"text": "리뷰 시간 중앙값", "evidence": ["vd:905@95", "vd:905@97", "vd:905@100",
                                                                "vd:905@101", "vd:905@102"]}])
    out = s.enforce(summary_input(), None)
    cap = [e for e in out.enforced if e["rule"].startswith("포인트 근거")]
    assert cap and cap[0]["owned"] is True
    inp = summary_input().model_dump()
    failed = graders.code_grade("video_summary", inp, s.model_dump(), None, {})["failed"]
    assert not any("근거" in f for f in failed)
    assert graders.model_agreement([{"output": s.model_dump(), "enforced": out.enforced}],
                                   ("name_pairs",))["key_points"] == "0/1"
