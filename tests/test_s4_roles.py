"""S4 역할: 이미지 입력(공통 코어, A10)과 판독·요약의 코드 규칙(enforce, A9). LLM은 모의 전송."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.conftest import FakeTransport, make_ctx, response
from trendsit.core import images
from trendsit.core.artifacts import Document
from trendsit.core.artifacts_video import (
    NO_CONTENT,
    SlideInput,
    SlideOnlyFact,
    SlideReading,
    VideoSummary,
    VideoSummaryInput,
)
from trendsit.core.cache import cache_key
from trendsit.core.role import initial_messages, load_role, run_role

ROOT = Path(__file__).resolve().parents[1]
THUMBS = sorted((ROOT / "tests/fixtures/video").rglob("*.jpg"))


def slide_json(**over) -> str:
    out = {"frame_kind": "slide", "ocr_text": "Review time\nmedian 58 min\np95 6.5 h",
           "numbers": [{"confidence": "high", "value": "58", "unit": "min", "what": "median"},
                       {"confidence": "high", "value": "6.5", "unit": "h", "what": "p95"}],
           "table": None, "title": "Review time", "log": "슬라이드, 수치 2개", "attention": False}
    return json.dumps(out | over, ensure_ascii=False)


def slide_input(path: Path) -> SlideInput:
    return SlideInput(image={"path": str(path)}, sec=97, spoken_text="our median review now takes about an hour")


# ---------- A10 이미지 입력 ----------
def test_message_shape_data_then_image_then_task(models):
    role = load_role("video_slide", models)
    msgs = initial_messages(role, slide_input(THUMBS[0]))
    parts = msgs[1]["content"]
    assert [p["type"] for p in parts] == ["text", "image_url", "text"]
    assert parts[0]["text"].startswith("<data>") and "spoken_text: our median" in parts[0]["text"]
    assert "image" not in parts[0]["text"].split("</data>")[0].replace("image_url", "")  # 이미지 칸은 자료에 없음
    assert parts[1]["image_url"]["url"] == images.SCHEME + images.digest(THUMBS[0])
    assert parts[2]["text"].startswith(role.spec.task)
    assert msgs[0]["content"] == role.system_prompt  # system에는 입력 없음


def test_transport_gets_data_uri_but_records_and_cache_do_not(tmp_path, models):
    tr = FakeTransport([response(slide_json())])
    ctx = make_ctx(tmp_path, tr)
    role = load_role("video_slide", models)
    out = run_role(role, slide_input(THUMBS[0]), ctx)
    assert out.title == "Review time"
    sent = tr.bodies[0]["messages"][1]["content"][1]["image_url"]
    assert sent["url"].startswith("data:image/jpeg;base64,") and "path" not in sent
    call = ctx.db.llm_call(ctx.last_step_id)
    recorded = json.dumps(call["request"], ensure_ascii=False)
    assert "base64" not in recorded and images.SCHEME in recorded and str(THUMBS[0]) in recorded
    cached = json.dumps([json.loads(p.read_text()) for p in (tmp_path / "cache").rglob("*.json")])
    assert "base64" not in cached
    # 같은 입력 다시: 캐시 적중(네트워크 0)
    run_role(role, slide_input(THUMBS[0]), ctx)
    assert tr.calls == 1


def test_cache_key_follows_image_bytes_not_path(tmp_path, models):
    role = load_role("video_slide", models)
    copy = tmp_path / "elsewhere.jpg"
    shutil.copy(THUMBS[0], copy)

    def key(p: Path) -> str:
        return cache_key({"model": "m", "messages": initial_messages(role, slide_input(p))})

    assert key(THUMBS[0]) == key(copy)
    assert key(THUMBS[0]) != key(THUMBS[1])


def test_estimate_includes_image_tokens(tmp_path, models):
    seen = []
    tr = FakeTransport([response(slide_json()), response(slide_json())])
    ctx = make_ctx(tmp_path, tr)
    ctx.budget.check = lambda est, what: seen.append(est)
    body = ctx.llm.build_body("generate", initial_messages(load_role("video_slide", models), slide_input(THUMBS[0])),
                              max_tokens=10)
    ctx.llm.send("generate", body, no_cache=True)
    no_image = json.loads(json.dumps(body))
    no_image["messages"][1]["content"].pop(1)
    ctx.llm.send("generate", no_image, no_cache=True)
    pin = ctx.budget.prices.price(ctx.models.models["generate"], ctx.models.base_url("generate"))[0]
    # 차이 = 장당 추정 토큰 + 자리표시 문자열 자체(수십 토큰)
    assert images.IMAGE_TOKENS_EST * pin <= seen[0] - seen[1] <= (images.IMAGE_TOKENS_EST + 200) * pin


def test_changed_image_file_is_not_sent(tmp_path, models):
    img = tmp_path / "f.jpg"
    shutil.copy(THUMBS[0], img)
    body = {"messages": initial_messages(load_role("video_slide", models), slide_input(img))}
    img.write_bytes(THUMBS[1].read_bytes())
    with pytest.raises(images.ImageError):
        images.materialize(body)


# ---------- A9 판독 enforce ----------
def test_slide_numbers_must_be_in_ocr_text(tmp_path, models):
    bad = slide_json(numbers=[{"confidence": "high", "value": "58", "unit": "min", "what": "median"},
                              {"confidence": "high", "value": "6.0", "unit": "h", "what": "p95(지어냄)"}])
    ctx = make_ctx(tmp_path, FakeTransport([response(bad)]))
    out = run_role(load_role("video_slide", models), slide_input(THUMBS[0]), ctx)
    assert [n.value for n in out.numbers] == ["58"] and out.attention
    assert out.raw_dump()["numbers"][1]["value"] == "6.0"  # 원래 출력은 평가용으로 보관
    detail = ctx.db.step(ctx.last_step_id)["detail"]
    assert "ocr_text에 없는 수치" in json.dumps(detail, ensure_ascii=False)


def test_non_slide_numbers_cleared():
    r = SlideReading.model_validate_json(slide_json(frame_kind="speaker"))
    out = r.enforce(slide_input(THUMBS[0]), None)
    assert out.numbers == [] and out.enforced


# ---------- A9 요약 enforce ----------
def summary_input(quality="ok", slides=True, transcript="[95] our median review takes about an hour\n"
                  "[240] we call it lama three point one based reviewer") -> VideoSummaryInput:
    docs = [Document(id="vd:905@97", source="슬라이드 판독", title="Review time", text="Review time\nmedian 58 min"),
            Document(id="vd:905@241", source="슬라이드 판독", text="Llama 3.1 reviewer")] if slides else []
    return VideoSummaryInput(
        item_id=905, transcript=Document(id="vd:905@0", source="전사(whisper)",
                                         text=transcript if quality == "ok" else ""),
        transcript_quality=quality, slides=docs,
        slide_only_facts=[SlideOnlyFact(fact="median", value="58", unit="min", sec=97, evidence="vd:905@97",
                                        confidence="high")],
        title="리뷰 시간", duration_sec=600, span_start=0, span_end=600, chapters=[], mode="whisper+slides")


def summary(**over) -> VideoSummary:
    base = {"name_pairs": [{"spoken": "lama three point one", "screen": "Llama 3.1", "sec": 241},
                           {"spoken": "엘엘엠", "screen": "LLM", "sec": 10}],
            "key_points": [{"text": "리뷰 시간 중앙값 약 1시간(슬라이드 58분)", "evidence": ["vd:905@95", "vd:905@97"]},
                           {"text": "구간 밖 근거", "evidence": ["vd:905@900"]},
                           {"text": "다른 영상 근거", "evidence": ["vd:111@95"]}],
            "timeline": [{"sec": 95, "label": "리뷰 시간", "slide": True}, {"sec": 700, "label": "밖", "slide": False}],
            "chapters": [{"sec": 0, "title": "인트로"}, {"sec": 9999, "title": "밖"}],
            "summary": "리뷰 시간 사례 발표다.", "log": "요약", "attention": False}
    return VideoSummary.model_validate(base | over)


def test_summary_enforce_pairs_evidence_seconds():
    out = summary().enforce(summary_input(), None)
    assert [(p.spoken, p.screen) for p in out.name_pairs] == [("lama three point one", "Llama 3.1")]
    assert [k.text for k in out.key_points] == ["리뷰 시간 중앙값 약 1시간(슬라이드 58분)"]
    assert [t.sec for t in out.timeline] == [95] and [c.sec for c in out.chapters] == [0]
    assert not out.attention


@pytest.mark.parametrize("quality", ["suspect_hallucination", "empty"])
def test_summary_bad_transcript_keeps_only_slide_evidence(quality):
    """A7: 전사를 쓸 수 없는 품질이면 전사만 근거인 포인트는 지움(판독 근거는 남김)."""
    s = summary(key_points=[{"text": "전사만 근거", "evidence": ["vd:905@95"]},
                            {"text": "슬라이드 근거", "evidence": ["vd:905@95", "vd:905@97"]}])
    out = s.enforce(summary_input(quality), None)
    assert [(k.text, k.evidence) for k in out.key_points] == [("슬라이드 근거", ["vd:905@97"])]
    assert out.name_pairs == [] and out.attention  # 전사 표기는 쓸 수 없음


def test_summary_no_sources_is_no_content():
    """A7: 전사도 판독도 없으면 내용 없음 + attention(모델이 지어내도 코드가 비움)."""
    out = summary().enforce(summary_input("suspect_hallucination", slides=False), None)
    assert out.summary == NO_CONTENT and out.key_points == [] and out.timeline == [] and out.attention
