"""S5 5.1 공통 수정(관문 A4): 명사 예외, ImageError 계열, 중첩 ImageFile 거부, ClassVar 선언, 예산 기준값 위치, 수치 모듈."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from eval import graders
from eval.run_eval import NESTED_BRIEF, _brief
from trendsit.core import config, context
from trendsit.core.artifacts import RoleInput
from trendsit.core.artifacts_video import VideoSummary
from trendsit.core.errors import LLMError
from trendsit.core.images import ImageError, ImageFile
from trendsit.core.numbers import number_values, same
from trendsit.core.role import nested_image_fields
from trendsit.core.style import ends_as_sentence, is_haeyo


@pytest.mark.parametrize("text", ["원본 확인 필요", "발표 개요", "GPU 수요", "처리 시간 소요", "주요"])
def test_noun_yo_is_not_a_sentence_end(text):
    assert not ends_as_sentence(text) and not is_haeyo(text)


@pytest.mark.parametrize("text", ["확인이 필요해요", "중요해요.", "발표했다", "무엇일까", "끝났습니다."])
def test_real_sentence_ends_still_caught(text):
    assert ends_as_sentence(text)


def test_video_grader_uses_common_rule():
    import eval.graders_video as gv

    assert not hasattr(gv, "SENTENCE_END")  # 자체 정규식 없음
    assert graders.ENFORCED_FIELDS["video_summary"] == VideoSummary.ENFORCED_FIELDS == ("name_pairs",)


def test_enforced_fields_are_classvars():
    assert "ENFORCED_FIELDS" not in VideoSummary.model_fields
    assert "ENFORCED_FIELDS" in VideoSummary.__class_vars__


def test_image_error_is_llm_error():
    assert issubclass(ImageError, LLMError)
    from trendsit.core.llm import LLMError as FromLLM

    assert FromLLM is LLMError


class _Inner(BaseModel):
    image: ImageFile


class _TopOnly(RoleInput):
    image: ImageFile
    note: str


class _Nested(RoleInput):
    frames: list[ImageFile]
    inner: _Inner


def test_nested_image_fields_rejected():
    assert nested_image_fields(_TopOnly) == []
    assert sorted(nested_image_fields(_Nested)) == ["frames", "inner.image"]


def test_quality_report_brief_cuts_nested_input():
    big = [{"id": i, "text": "가" * 50} for i in range(40)]
    out = _brief(big)
    assert isinstance(out, str) and len(out) == NESTED_BRIEF + 1 and out.endswith("…")
    small = {"a": 1}
    assert _brief(small) == small and len(json.dumps(small)) < NESTED_BRIEF


def test_budget_state_moves_to_shared_place(tmp_path, monkeypatch):
    root, home = tmp_path / "repo", tmp_path / "home" / ".config" / "trendsit"
    (root / "data").mkdir(parents=True)
    old = {"phase": "mvp", "phase_baseline_usd": 0.48331, "recorded_at": "2026-10-07T15:33:03+09:00"}
    (root / "data" / "budget_state.json").write_text(json.dumps(old))
    monkeypatch.setattr(config, "ROOT", root)
    monkeypatch.setattr(config, "SECRET_FILE", home / ".env")
    p = context.budget_state_path(None)
    assert p == home / "budget_state.json" and json.loads(p.read_text()) == old  # 10/7 기준값 유지
    assert context.budget_state_path(tmp_path / "x") == tmp_path / "x" / "budget_state.json"


def test_numbers_module_shared():
    assert any(same(v, 1.2e6) for v in number_values("one point two million"))
    assert any(same(v, 1.2e6) for v in number_values("1.2M"))
    assert any(same(v, 3e8) for v in number_values("3억"))


def test_truncated_output_is_detected_and_retried_once(tmp_path):
    """COMMON 6.1-9: max_tokens에 닿아 잘린 출력은 '출력 잘림'으로 기록하고 한 번만 더(같은 길이면 또 잘림)."""
    from tests.conftest import FakeTransport, make_ctx, response
    from tests.test_role import INPUT
    from trendsit.core.role import RoleFailed, load_role, run_role

    models = config.load("models.yaml")
    role = load_role("repo_oneliner", models)
    cut = response('{"basis": "A tool', tokens=(100, role.spec.max_tokens))
    t = FakeTransport([cut, cut, cut])
    ctx = make_ctx(tmp_path, t)
    with pytest.raises(RoleFailed, match="출력 잘림"):
        run_role(role, INPUT, ctx)
    assert t.calls == 2
    assert "더 짧은 JSON" in t.bodies[1]["messages"][-1]["content"]
    steps = ctx.db.steps_of(ctx.tracer.run_id)
    assert all(s["text"].startswith("출력 잘림") for s in steps)


def test_r9_clear_trending_keeps_repos_with_cards(tmp_path):
    """그 주 마지막 수집에서 빠진 레포라도 카드가 있으면 이전 수집판 행(별 수)을 남긴다(PR #9 리뷰 R9)."""
    from trendsit.core.db import DB

    db = DB(tmp_path / "t.db")
    for name, stars in (("a/carded", 3690), ("b/plain", 10)):
        db.save_trending("2026-W41", {"full_name": name, "rank": 1, "stars_this_week": stars}, "r1")
    db.conn.execute("INSERT INTO repo_cards(week, full_name, card_json) VALUES ('2026-W41', 'a/carded', '{}')")
    db.conn.commit()
    db.clear_trending("2026-W41")
    left = db.conn.execute("SELECT full_name, stars_this_week FROM repo_trending").fetchall()
    assert [tuple(r) for r in left] == [("a/carded", 3690)]
