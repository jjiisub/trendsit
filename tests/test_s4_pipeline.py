"""S4 파이프라인: 실제 영상 1차 처리 픽스처 + 모의 LLM으로 판독 이후 단계(어디서나, CI 포함).

A7 품질 분기, 대체 동작(판독 전부 실패 → 전사만, 받기 실패 → fetch_log), 저장(video_* 표), A11 보관, A12 마이그레이션 대역.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tests.conftest import FakeTransport, make_ctx, response
from trendsit.collect.video.process import Deps, MediaFailed
from trendsit.collect.video.settings import load_video_config
from trendsit.core import migrations
from trendsit.core.artifacts_video import NO_CONTENT, MediaResult, VideoQueueItem
from trendsit.core.db import KST
from trendsit.video import store
from trendsit.video.pipeline import analyze

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests/fixtures/video"
ITEM_ID = 905


def load_media(video_id: str, **update) -> MediaResult:
    data = json.loads((FIX / f"{video_id}.json").read_text(encoding="utf-8"))
    data["work_dir"] = str(ROOT / data["work_dir"])
    return MediaResult.model_validate(data | update)


def add_video(db, video_id: str, duration: int = 1200) -> None:
    with db.conn:
        db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, title) VALUES (?,?,?,?,?)",
                        (ITEM_ID, "techbridge", "video", video_id, "테스트 영상"))
        db.conn.execute("INSERT INTO videos(item_id, video_id, duration_sec, chapters_json, meta_status) "
                        "VALUES (?,?,?,?,?)", (ITEM_ID, video_id, duration,
                                               json.dumps([{"start": 0, "title": "Intro"}]), "ok"))


def slide_resp(n: int) -> dict:
    ocr = f"Adoption {n}\n{40 + n}% of teams\n{n}.5x faster"
    return response(json.dumps({
        "frame_kind": "slide", "ocr_text": ocr,
        "numbers": [{"confidence": "high", "value": f"{40 + n}%", "unit": "%", "what": "of teams"},
                    {"confidence": "check" if n == 0 else "high", "value": f"{n}.5x", "unit": "x", "what": "faster"}],
        "table": None, "title": f"Adoption {n}", "log": "슬라이드, 수치 2개", "attention": n == 0}, ensure_ascii=False))


def summary_resp(media: MediaResult, evidence: list[str]) -> dict:
    return response(json.dumps({
        "name_pairs": [], "key_points": [{"text": "에이전트 도입 현황", "evidence": evidence}],
        "timeline": [{"sec": round(media.span.start), "label": "시작", "slide": False}], "chapters": [],
        "summary": "에이전트 도입 사례 발표다.", "log": "요약", "attention": False}, ensure_ascii=False))


def thumbs_count(media: MediaResult) -> int:
    return sum(1 for f in media.frames if (Path(media.work_dir) / f.path).is_file())


def run(tmp_path, transport, item, media, **kw):
    ctx = make_ctx(tmp_path, transport)
    add_video(ctx.db, item.video_id, media.duration_sec if media else 1200)
    return ctx, analyze(item, ctx, load_video_config(), tmp_path / "media", media=media, **kw)


def test_slides_pipeline_saves_digest(tmp_path):
    media = load_media("xRZHLI5SPWo")
    n = thumbs_count(media)
    assert n == 5
    first_seg = round(media.segments[0].start)
    tr = FakeTransport([slide_resp(i) for i in range(n)] + [summary_resp(media, [f"vd:{ITEM_ID}@{first_seg}"])])
    item = VideoQueueItem(video_id=media.video_id, mode="whisper+slides", reason="컨퍼런스 발표, 수치 많음")
    ctx, out = run(tmp_path, tr, item, media)
    assert out.status == "ok" and tr.calls == n + 1
    d = store.digest(ctx.db, media.video_id)
    assert d.frames_read == n and d.frames_total == len(media.frames)
    assert d.log.startswith("컨퍼런스 발표, 수치 많음")  # reason을 log에 이어 씀
    assert d.slide_only_facts and all(re.match(rf"^vd:{ITEM_ID}@\d+$", f.evidence) for f in d.slide_only_facts)
    assert d.check_numbers and d.attention  # check 판독은 따로 + attention
    assert d.key_points[0].evidence == [f"vd:{ITEM_ID}@{first_seg}"]
    # 판독 순서: 우선순위 높은 프레임부터
    sent_secs = [int(re.search(r"sec: (\d+)", b["messages"][1]["content"][0]["text"]).group(1)) for b in tr.bodies[:n]]
    assert len(sent_secs) == n
    # 저장: 실행 기록 run 1개에 단계별 step, video_* 표
    kinds = [(s["kind"], s["role"]) for s in ctx.db.steps_of(ctx.tracer.run_id)]
    assert ("llm", "video_slide") in kinds and ("llm", "video_summary") in kinds and ("code", "video_analyst") in kinds
    db = ctx.db.conn
    assert db.execute("SELECT COUNT(*) FROM video_segments WHERE video_id=?", (media.video_id,)).fetchone()[0] == len(media.segments)
    assert db.execute("SELECT COUNT(*) FROM video_frames WHERE reading_json IS NOT NULL").fetchone()[0] == n
    row = db.execute("SELECT status, transcript_quality, item_id FROM video_runs").fetchone()
    assert tuple(row) == ("ok", "ok", ITEM_ID)
    # 요약 입력: 전사는 [초] 줄, 판독은 vd: 문서
    summary_text = tr.bodies[-1]["messages"][1]["content"]
    assert f'<document id="vd:{ITEM_ID}@' in summary_text and f"[{first_seg}] " in summary_text


@pytest.mark.parametrize("quality", ["suspect_hallucination", "empty"])
def test_bad_transcript_without_frames_is_no_content_without_llm(tmp_path, quality):
    """A7: 전사를 쓸 수 없고 판독도 없으면 LLM을 부르지 않고 내용 없음 + attention."""
    media = load_media("5wDzydCqkV8", transcript_quality=quality)
    tr = FakeTransport([])
    item = VideoQueueItem(video_id=media.video_id, mode="whisper", reason="대담")
    ctx, out = run(tmp_path, tr, item, media)
    assert tr.calls == 0 and out.digest.summary == NO_CONTENT and out.digest.attention
    assert out.digest.key_points == [] and out.digest.transcript_quality == quality


@pytest.mark.parametrize("quality", ["suspect_hallucination", "empty"])
def test_bad_transcript_with_slides_uses_slides_only(tmp_path, quality):
    """A7: 전사를 근거로 쓰지 않음(요약 입력의 전사는 빈 문서, 전사 근거 포인트는 코드가 지움)."""
    media = load_media("xRZHLI5SPWo", transcript_quality=quality)
    n = thumbs_count(media)
    seg_sec = round(media.segments[3].start)
    tr = FakeTransport([slide_resp(i) for i in range(n)] + [summary_resp(media, [f"vd:{ITEM_ID}@{seg_sec}"])])
    item = VideoQueueItem(video_id=media.video_id, mode="whisper+slides", reason="발표")
    _ctx, out = run(tmp_path, tr, item, media)
    summary_text = tr.bodies[-1]["messages"][1]["content"]
    assert media.segments[3].text not in summary_text  # 전사 문장이 요약 입력에 없음
    assert out.digest.key_points == [] and out.digest.attention
    # 발화 대조도 하지 않음: 판독 수치는 전부 슬라이드 전용(확인 필요 제외)
    assert out.aligned.matched == []


def test_all_slide_readings_fail_falls_back_to_transcript(tmp_path):
    media = load_media("xRZHLI5SPWo")
    n = thumbs_count(media)
    bad = [response("{not json") for _ in range(n * 3)]  # 역할마다 재시도 2회 → 3번 실패
    first_seg = round(media.segments[0].start)
    tr = FakeTransport(bad + [summary_resp(media, [f"vd:{ITEM_ID}@{first_seg}"])])
    item = VideoQueueItem(video_id=media.video_id, mode="whisper+slides", reason="발표")
    ctx, out = run(tmp_path, tr, item, media)
    assert out.status == "partial" and "전사 결과만" in out.digest.log and out.digest.attention
    assert out.digest.frames_read == 0 and out.digest.key_points
    assert ctx.db.conn.execute("SELECT status FROM video_runs").fetchone()[0] == "partial"


def test_captions_without_manual_track_is_skipped_and_recorded(tmp_path):
    deps = Deps(fetch_info=lambda vid: {"title": "x", "duration": 100, "subtitles": {},
                                        "automatic_captions": {"ko": []}})
    item = VideoQueueItem(video_id="CCCCCCCCCCC", mode="captions", reason="업로더 자막")
    ctx, out = run(tmp_path, FakeTransport([]), item, None, deps=deps)
    assert out.status == "skipped" and "수동 자막" in out.note
    assert ctx.db.conn.execute("SELECT status, mode FROM video_runs").fetchone()[:] == ("skipped", "captions")


def test_media_failure_logs_fetch_failure(tmp_path):
    def boom(*a, **k):
        raise MediaFailed("받기 실패(2회): HTTP Error 403")

    item = VideoQueueItem(video_id="AAAAAAAAAAA", mode="whisper", reason="발표")
    ctx, out = run(tmp_path, FakeTransport([]), item, None, deps=Deps(download=boom))
    assert out.status == "failed"
    row = ctx.db.conn.execute("SELECT source_id, status, error FROM fetch_log").fetchone()
    assert row["source_id"] == "techbridge" and row["status"] == "failed" and "403" in row["error"]
    assert any(s["attention"] for s in ctx.db.steps_of(ctx.tracer.run_id))


def test_unknown_video_and_skip_mode(tmp_path):
    ctx = make_ctx(tmp_path, FakeTransport([]))
    cfg = load_video_config()
    out = analyze(VideoQueueItem(video_id="ZZZZZZZZZZZ", mode="whisper", reason="x"), ctx, cfg, tmp_path)
    assert out.status == "failed" and "collect" in out.note
    add_video(ctx.db, "DDDDDDDDDDD")
    out = analyze(VideoQueueItem(video_id="DDDDDDDDDDD", mode="skip", reason="행사 안내"), ctx, cfg, tmp_path)
    assert out.status == "skipped"


# ---------- A11 보관(DB) ----------
def test_segment_text_expires_but_digest_stays(tmp_path):
    media = load_media("5wDzydCqkV8")
    tr = FakeTransport([summary_resp(media, [f"vd:{ITEM_ID}@{round(media.segments[0].start)}"])])
    ctx, _ = run(tmp_path, tr, VideoQueueItem(video_id=media.video_id, mode="whisper", reason="대담"), media)
    later = datetime.now(KST) + timedelta(weeks=9)
    assert store.expire_segment_text(ctx.db, now=later) == len(media.segments)
    db = ctx.db.conn
    assert db.execute("SELECT COUNT(*) FROM video_segments WHERE text IS NOT NULL").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM video_segments").fetchone()[0] == len(media.segments)  # 시각은 남음
    assert store.digest(ctx.db, media.video_id) is not None
    assert store.expire_segment_text(ctx.db) == 0  # 기한 전이면 그대로


# ---------- A12 마이그레이션 대역 ----------
def test_s4_migrations_in_band_and_only_video_tables():
    s4 = {n: sql for n, sql in migrations.MIGRATIONS.items() if 20 <= n <= 29}  # S5부터 30~39 대역이 뒤에 붙음
    assert s4 and all(20 <= n <= 29 for n in s4)
    for n, sql in migrations.MIGRATIONS.items():
        made = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", sql)
        if 20 <= n <= 29:
            assert made and all(t.startswith("video_") for t in made), n
            assert not re.search(r"ALTER TABLE (?!video_)", sql)
        else:
            assert not any(t.startswith("video_") for t in made), n


def test_video_migration_applies_in_either_order(tmp_path):
    """A12: S2~S3 대역과 서로 의존하지 않음(20번을 먼저 적용해도, 나중에 적용해도 같은 표)."""
    from trendsit.core.db import DB

    fake_s2 = "CREATE TABLE IF NOT EXISTS s2_dummy (x INTEGER);"
    base = {n: s for n, s in migrations.MIGRATIONS.items() if n < 10}
    a = DB(tmp_path / "a.db", migrations=base | {20: migrations.MIGRATIONS[20]})
    a.migrate(base | {20: migrations.MIGRATIONS[20], 10: fake_s2})
    b = DB(tmp_path / "b.db", migrations=base | {10: fake_s2, 20: migrations.MIGRATIONS[20]})

    def tables(db):
        return sorted(r[0] for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'"))

    assert tables(a) == tables(b) and "video_digests" in tables(a)


def test_saved_media_with_other_mode_is_refused(tmp_path):
    """저장한 1차 처리 결과로 mode를 올리지 않는다(whisper 지시에 whisper+slides 결과 → 판독 없이 실패 기록)."""
    media = load_media("xRZHLI5SPWo")
    tr = FakeTransport([])
    _ctx, out = run(tmp_path, tr, VideoQueueItem(video_id=media.video_id, mode="whisper", reason="대담"), media)
    assert out.status == "failed" and "mode" in out.note and tr.calls == 0


def test_captions_failure_goes_to_fetch_log(tmp_path):
    def boom(vid):
        raise RuntimeError("ERROR: Video unavailable")

    item = VideoQueueItem(video_id="CCCCCCCCCCC", mode="captions", reason="업로더 자막")
    ctx, out = run(tmp_path, FakeTransport([]), item, None, deps=Deps(fetch_info=boom))
    assert out.status == "failed"
    assert ctx.db.conn.execute("SELECT status FROM fetch_log").fetchone()[0] == "failed"


def test_cli_queue_continues_after_unexpected_error(tmp_path, monkeypatch, capsys):
    """한 영상의 예상 밖 오류는 기록하고 다음 영상으로(큐 전체가 멈추지 않음)."""
    from trendsit import cli_video
    from trendsit.core import context
    from trendsit.video import pipeline

    ctx = make_ctx(tmp_path, FakeTransport([]))
    monkeypatch.setattr(context, "open_ctx", lambda *a, **k: ctx)
    seen = []

    def fake_analyze(item, *a, **k):
        seen.append(item.video_id)
        if item.video_id == "AAAAAAAAAAA":
            raise KeyError("boom")
        return pipeline.VideoOutcome(item.video_id, "skipped", "테스트")

    monkeypatch.setattr(pipeline, "analyze", fake_analyze)
    q = tmp_path / "q.json"
    q.write_text(json.dumps([{"video_id": "AAAAAAAAAAA", "mode": "whisper", "reason": "a"},
                             {"video_id": "BBBBBBBBBBB", "mode": "whisper", "reason": "b"}]), encoding="utf-8")
    args = cli_video.argparse.Namespace(queue=str(q), video_id=None, mode=None, start=None, end=None, reason="",
                                        frames=None, res=None, lang=None, from_json=None, reuse_media=False,
                                        model=None, no_cache=False, spec="S0")
    assert cli_video.cmd_run(args) == 1
    assert seen == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert ctx.db.conn.execute("SELECT video_id, status FROM video_runs").fetchone()[:] == ("AAAAAAAAAAA", "failed")


def test_duplicate_frame_times_keep_reading(tmp_path):
    """같은 시각 프레임이 둘이면 판독이 있는 쪽 하나만 저장하고 빠진 수를 돌려준다(조용히 덮어쓰지 않음)."""
    from trendsit.core.artifacts_video import Frame, SlideReading

    ctx = make_ctx(tmp_path, FakeTransport([]))
    f = Frame(t=5.0, path="frames/a.jpg", reason="uniform", segment_index=None, spoken_text="")
    reading = SlideReading(frame_kind="other", ocr_text="", numbers=[], table=None, title="", log="x")
    assert store.save_frames(ctx.db, "XXXXXXXXXXX", [(f, None), (f, reading)]) == 1
    assert ctx.db.conn.execute("SELECT reading_json IS NOT NULL FROM video_frames").fetchone()[0] == 1
