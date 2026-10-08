"""S3 3a 편집장 계획: validate_plan(A11: 예산 꼬리 자르기, 깊이, 없는 id), 대체 계획, 계약(A12), 저장·보기, 코드 채점."""

import json
from datetime import date

import pytest

from eval import graders
from tests.conftest import FakeTransport, make_ctx, response
from trendsit.core import config
from trendsit.core.artifacts import apply_enforce
from trendsit.core.artifacts_text import CollectionPlan, PlanInput, VideoQueueItem
from trendsit.core.config import ROOT
from trendsit.core.role import load_role, run_role
from trendsit.deep.plan import (
    build_plan_input,
    fallback_plan,
    latest_plan,
    make_mode_labels,
    mode_agreement,
    save_plan,
    usage,
    validate_plan,
    video_queue_json,
)

CONTRACT = ROOT / "tests" / "fixtures" / "contracts" / "video_queue.json"


def budget(**kw):
    b = dict(video_minutes=90, slide_videos=1, vlm_frames=40, frames_per_slide_video=20, text_items=2,
             text_tool_calls_per_item=6, repo_items=2, default_text_depth=2, max_text_depth=3, plan_share=0.8,
             video_max_minutes=60)
    return b | kw


def vid(i, minutes, subs=()):
    return {"video_id": f"VIDEO{i:06d}", "item_id": 100 + i, "title": f"영상 {i}", "duration_min": minutes,
            "manual_sub_langs": list(subs), "has_auto_sub": True}


def plan_input(**kw):
    base = {"day": "2026-10-06",
            "new_videos": [vid(1, 30), vid(2, 50, ["ko"]), vid(3, 140), vid(4, 20)],
            "repo_candidates": [{"full_name": f"o/r{i}", "stars_this_week": 100 * i} for i in range(1, 5)],
            "text_candidates": [{"item_id": i, "title": f"글 {i}", "source": "geeknews", "relevance": r,
                                 "needs_original_reason": "x", "origin_link_kinds": ["공식 블로그"]}
                                for i, r in ((1, "high"), (2, "high"), (3, "mid"), (4, "high"))],
            "keywords": ["에이전트"], "budget": budget()}
    return PlanInput.model_validate(base | kw)


def plan(**kw):
    base = {"text_queue": [], "video_queue": [], "repo_queue": [], "log": "계획", "attention": False}
    return CollectionPlan.model_validate(base | kw)


def v(i, mode="whisper", **kw):
    return {"reason": "r", "video_id": f"VIDEO{i:06d}", "mode": mode} | kw


# ---------- A11 ----------
def test_cuts_budget_tail_in_priority_order():
    p = plan(video_queue=[v(1, "whisper+slides"), v(2, "captions"), v(4), v(3)],  # 30 + 50 = 80, 20 넘침
             text_queue=[{"reason": "r", "item_id": i, "max_depth": 2} for i in (1, 2, 4)],
             repo_queue=[{"reason": "r", "full_name": f"o/r{i}", "max_depth": 2} for i in (1, 2, 3)])
    out = validate_plan(p, plan_input())
    assert [x.video_id for x in out.video_queue] == ["VIDEO000001", "VIDEO000002"]  # 뒤의 4, 3이 잘림
    assert [t.item_id for t in out.text_queue] == [1, 2] and [r.full_name for r in out.repo_queue] == ["o/r1", "o/r2"]
    assert "VIDEO000004" in out.log and "글 4 예산 초과로 잘림" in out.log and "레포 o/r3" in out.log
    assert all(u <= t for u, t in usage(out, plan_input()).values())
    assert out.attention is True  # 80% 넘음(영상 80/90 등)


def test_slide_budget_and_long_video_window():
    p = plan(video_queue=[v(1, "whisper+slides"), v(4, "whisper+slides"), v(3, start_sec=0, end_sec=1800)])
    out = validate_plan(p, plan_input())
    # 슬라이드 영상 상한 1 → 4는 잘림, 140분 영상은 구간 30분만 계산
    assert [x.video_id for x in out.video_queue] == ["VIDEO000001", "VIDEO000003"]
    assert usage(out, plan_input())["영상 분"][0] == 60
    long_default = validate_plan(plan(video_queue=[v(3)]), plan_input())  # 구간 없으면 최대 60분으로 셈
    assert usage(long_default, plan_input())["영상 분"][0] == 60


def test_depth_clip_unknown_ids_and_duplicates():
    p = plan(text_queue=[{"reason": "r", "item_id": 1, "max_depth": 4}, {"reason": "r", "item_id": 99, "max_depth": 2},
                         {"reason": "r", "item_id": 1, "max_depth": 2}],
             video_queue=[v(77)], repo_queue=[{"reason": "r", "full_name": "x/y", "max_depth": 1}])
    out = validate_plan(p, plan_input())
    assert [(t.item_id, t.max_depth) for t in out.text_queue] == [(1, 3)]  # max_text_depth 3
    assert out.video_queue == [] and out.repo_queue == []
    assert "없는 글 99" in out.log and "중복 글 1" in out.log and "깊이 4→3" in out.log
    assert {e["rule"] for e in out.enforced} >= {"validate_plan: 글 큐", "validate_plan: 영상 큐"}


def test_within_80_percent_keeps_attention_false():
    out = validate_plan(plan(video_queue=[v(1)], text_queue=[{"reason": "r", "item_id": 1, "max_depth": 2}]),
                        plan_input())
    assert out.attention is False and out.enforced == []


def test_fallback_plan_rules():
    out = fallback_plan(plan_input(), "모델 실패")
    modes = {x.video_id: x.mode for x in out.video_queue}
    assert modes["VIDEO000002"] == "captions" and "whisper+slides" not in modes.values()
    assert [t.item_id for t in out.text_queue] == [1, 2]  # high만, text_items 2로 잘림
    assert all(t.max_depth == 2 for t in out.text_queue)
    assert [r.full_name for r in out.repo_queue] == ["o/r4", "o/r3"]  # 별 상위, repo_items 2
    assert out.attention and out.log.startswith("규칙 기반 대체 계획")


def test_run_role_enforces_plan(tmp_path, models):
    role = load_role("editor_plan", models)
    raw = plan(text_queue=[{"reason": "r", "item_id": 1, "max_depth": 4}]).model_dump()
    ctx = make_ctx(tmp_path, FakeTransport([response(json.dumps(raw, ensure_ascii=False))]), spec_cap=1.0)
    out = run_role(role, plan_input(), ctx)
    assert out.text_queue[0].max_depth == 3
    assert json.loads(ctx.db.step(ctx.last_step_id)["detail"])["enforced"]


# ---------- A12 계약 ----------
def test_contract_fixture_reads_as_video_queue_item():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    items = [VideoQueueItem.model_validate(x) for x in data]
    assert [i.mode for i in items] == ["whisper+slides", "whisper", "captions", "skip"]


def test_plan_show_video_queue_has_contract_shape(tmp_path):
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    ctx = make_ctx(tmp_path, FakeTransport([]))
    p = plan(video_queue=data)
    save_plan(ctx.db, "2026-10-06", p, "model", "r1")
    shown = video_queue_json(latest_plan(ctx.db, "2026-10-06"))
    assert [set(x) for x in shown] == [set(x) for x in data] and shown == data
    assert [list(x) for x in shown] == [["video_id", "mode", "start_sec", "end_sec", "reason"]] * 4


# ---------- 입력 조립, 라벨, 채점 ----------
def test_build_plan_input_from_db(tmp_path):
    ctx = make_ctx(tmp_path, FakeTransport([]))
    db = ctx.db
    db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, title, day, week, published_at) "
                    "VALUES (1, 'techbridge', 'video', 'v1', '발표', '2026-10-05', '2026-W41', '2026-10-05T10:00:00+09:00')")
    db.conn.execute("INSERT INTO videos(item_id, video_id, duration_sec, manual_sub_langs, has_auto_sub, chapters_json) "
                    "VALUES (1, 'VIDEO000001', 1800, '[\"ko\"]', 1, '[{\"start\": 0}]')")
    db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, title, day) "
                    "VALUES (2, 'geeknews', 'text', 't2', '큐레이션 글', '2026-10-04')")
    db.conn.execute("INSERT INTO links(item_id, url, kind, role) VALUES (2, 'https://a', '공식 블로그', 'origin_candidate')")
    db.conn.execute("INSERT INTO item_cards(item_id, version, card_json) VALUES (2, 1, ?)", (json.dumps(
        {"needs_original": True, "relevance": "high", "needs_original_reason": "수치 출처", "origin_candidates": [1]}),))
    db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, title, day) "
                    "VALUES (3, 'openai', 'text', 't3', '공식', '2026-10-04')")
    db.conn.execute("INSERT INTO item_cards(item_id, version, card_json) VALUES (3, 1, ?)",
                    (json.dumps({"needs_original": False}),))
    db.conn.commit()
    inp = build_plan_input(ctx, date(2026, 10, 6), config.load("deep.yaml"), config.load("keywords.yaml"), hype=False)
    assert [x.video_id for x in inp.new_videos] == ["VIDEO000001"] and inp.new_videos[0].duration_min == 30
    assert inp.new_videos[0].manual_sub_langs == ["ko"] and inp.new_videos[0].chapters == 1
    assert [(t.item_id, t.origin_link_kinds) for t in inp.text_candidates] == [(2, ["공식 블로그"])]
    assert inp.budget.video_minutes == 90 and inp.recent_topics == []


def test_mode_labels_and_agreement(tmp_path):
    path = tmp_path / "editor_plan_mode.csv"
    p = plan(video_queue=[v(1), v(2, "captions")]).model_dump()
    assert make_mode_labels(plan_input(), p, path) == 4
    import csv

    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows[0]["agree"], rows[1]["agree"] = "y", "n"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    assert mode_agreement(path) == {"n": 2, "agree": 1, "rate": 0.5}
    make_mode_labels(plan_input(), p, path)  # 다시 만들어도 채운 칸 보존
    assert mode_agreement(path)["n"] == 2


def test_code_grade_editor_plan():
    inp = plan_input().model_dump()
    good = validate_plan(plan(video_queue=[v(1)]), plan_input()).model_dump()
    assert graders.code_grade("editor_plan", inp, good, None, {})["passed"]
    bad = plan(video_queue=[v(1), v(2), v(3)], text_queue=[{"reason": " ", "item_id": 99, "max_depth": 4}]).model_dump()
    failed = " ".join(graders.code_grade("editor_plan", inp, bad, None, {})["failed"])
    assert "예산 초과 0" in failed and "모든 결정에 reason" in failed and "id가 입력 후보 안" in failed


@pytest.mark.parametrize("bad", ["short", "AAAAAAAAAAAA"])
def test_video_id_format(bad):
    with pytest.raises(ValueError):
        VideoQueueItem(reason="r", video_id=bad, mode="whisper")


def test_apply_enforce_on_fallback_is_idempotent():
    fb = fallback_plan(plan_input(), "x")
    again = apply_enforce(fb, plan_input(), None)
    assert again.enforced == fb.enforced and again.model_dump() == fb.model_dump()  # 두 번째 검증은 바꾸는 것 없음


def test_mode_labels_and_judge_labels_are_separate_files():
    """설계 결정 Q5: 영상 mode 동의 라벨과 judge 라벨이 서로 덮어쓰지 않는다."""
    from eval.run_eval import LABELS
    from trendsit.cli_text import PLAN_LABELS

    assert PLAN_LABELS.name == "editor_plan_mode.csv" and PLAN_LABELS != LABELS / "editor_plan.csv"
