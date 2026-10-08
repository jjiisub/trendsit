"""S4 1차 처리(DB 없는 부분): 설정, 큐 계약, 받기 규칙, 전사 정규화·품질, 프레임 예산, 화면 지시, 계약 검사, 보관.

맥 전용(ffmpeg + video 묶음) 테스트는 mac_video 표시 하나로만 건너뛴다(S4_TASK A2).
"""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

from trendsit.collect.video import contract, cues, source
from trendsit.collect.video import frames as fr
from trendsit.collect.video import transcribe as tr
from trendsit.collect.video.process import Deps, MediaSkipped, media_process, resolve_span
from trendsit.collect.video.settings import check_video_config, load_video_config
from trendsit.collect.video.workspace import Workspace, purge
from trendsit.core.artifacts_video import MediaResult, VideoQueueItem
from trendsit.core.config_video import FRAME_CAP_MAX

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "tests/fixtures/contracts/video_queue.json"
FIXTURES = ROOT / "tests/fixtures/video"

mac_video = pytest.mark.skipif(
    sys.platform != "darwin" or shutil.which("ffmpeg") is None
    or importlib.util.find_spec("mlx_whisper") is None or importlib.util.find_spec("yt_dlp") is None,
    reason="맥 + ffmpeg + video 묶음(yt-dlp, mlx-whisper)이 있어야 함")


def cfg():
    return load_video_config()


def write_video_yaml(tmp_path: Path, mutate) -> Path:
    data = yaml.safe_load((ROOT / "config/video.yaml").read_text(encoding="utf-8"))
    mutate(data)
    (tmp_path / "video.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return tmp_path


# ---------- A3 설정 ----------
def test_video_config_ok():
    assert check_video_config() == []
    c = cfg()
    assert c.modes.get("whisper+slides").frames_cap <= FRAME_CAP_MAX
    assert c.modes.get("whisper").frames == "off"


@pytest.mark.parametrize("mutate,path", [
    (lambda d: d["modes"]["whisper+slides"].update(frames_cap=30), "modes.whisper+slides.frames_cap"),
    (lambda d: d["modes"].update(deep={"transcript": "whisper", "frames": "auto"}), "modes.deep"),
    (lambda d: d["modes"]["whisper"].update(frames="auto"), "modes"),
    (lambda d: d["modes"].pop("captions"), "modes.captions"),
    (lambda d: d.update(max_span_sec=10), "max_span_sec"),
])
def test_video_config_bad_points_to_path(tmp_path, mutate, path):
    errors = check_video_config(write_video_yaml(tmp_path, mutate))
    assert errors and errors[0].file == "video.yaml"
    assert errors[0].path == path, errors[0]


# ---------- A6 큐 계약 ----------
def test_queue_fixture_parses_and_maps_to_settings():
    items = [VideoQueueItem.model_validate(x) for x in json.loads(QUEUE.read_text(encoding="utf-8"))]
    assert [i.mode for i in items] == ["whisper+slides", "whisper", "captions", "skip"]
    c = cfg()
    assert c.modes.get(items[0].mode).frames in ("auto", "full")
    assert c.modes.get(items[1].mode).frames == "off"
    assert c.modes.get(items[2].mode).transcript == "manual"
    with pytest.raises(MediaSkipped):
        media_process(items[3], c, Path("/nonexistent"), deps=Deps())


@pytest.mark.parametrize("bad", [
    {"video_id": "short", "mode": "whisper", "reason": "x"},
    {"video_id": "AAAAAAAAAAA", "mode": "deep", "reason": "x"},
    {"video_id": "AAAAAAAAAAA", "mode": "whisper", "start_sec": 100, "end_sec": 50, "reason": "x"},
    {"video_id": "AAAAAAAAAAA", "mode": "whisper", "reason": "두 줄\n이유"},
])
def test_queue_item_rejects(bad):
    with pytest.raises(ValueError):
        VideoQueueItem.model_validate(bad)


def _info(subtitles=None, auto=None):
    return {"id": "CCCCCCCCCCC", "title": "짧은 소식", "duration": 120, "subtitles": subtitles or {},
            "automatic_captions": auto or {}}


VTT = """WEBVTT

00:00:01.000 --> 00:00:04.000
<c>안녕하세요</c> 오늘 소식입니다

00:00:04.000 --> 00:00:06.500
안녕하세요 오늘 소식입니다

00:00:07.000 --> 00:00:10.000
새 모델이 1.2M 토큰 문맥을 지원합니다
"""


def test_captions_without_manual_track_skips_even_with_auto_captions(tmp_path):
    """A13: 자동 자막만 있으면 captions는 건너뜀(whisper로 올리지 않음, 자동 자막을 받지 않음)."""
    called = []
    deps = Deps(fetch_info=lambda vid: _info(auto={"ko": [{"ext": "vtt"}], "en": [{"ext": "vtt"}]}),
                download_captions=lambda *a: called.append("captions") or tmp_path / "x.vtt",
                download=lambda *a, **k: called.append("download"),
                transcribe=lambda *a, **k: called.append("whisper"))
    item = VideoQueueItem(video_id="CCCCCCCCCCC", mode="captions", reason="업로더 자막")
    with pytest.raises(MediaSkipped, match="수동 자막"):
        media_process(item, cfg(), tmp_path, deps=deps)
    assert called == []


def test_captions_with_manual_track(tmp_path):
    def download_captions(vid, lang, staging):
        assert lang == "ko"
        p = staging / "sub.ko.vtt"
        p.write_text(VTT, encoding="utf-8")
        return p

    deps = Deps(fetch_info=lambda vid: _info(subtitles={"live_chat": [], "en": [], "ko": []}),
                download_captions=download_captions)
    item = VideoQueueItem(video_id="CCCCCCCCCCC", mode="captions", reason="업로더 자막")
    r = media_process(item, cfg(), tmp_path, deps=deps)
    assert r.transcript_source == "manual" and r.language == "ko" and r.frames == []
    assert [s.text for s in r.segments] == ["안녕하세요 오늘 소식입니다", "새 모델이 1.2M 토큰 문맥을 지원합니다"]
    assert r.segments[0].end == 6.5  # 롤업 중복은 하나로
    assert contract.check(r) == []


def test_no_auto_caption_path_in_video_code():
    """A13: 영상 분석가 코드에 자동 자막을 읽거나 받는 경로가 없다."""
    for p in [*(ROOT / "trendsit/collect/video").glob("*.py"), *(ROOT / "trendsit/video").glob("*.py")]:
        text = p.read_text(encoding="utf-8")
        assert '"automatic_captions"' not in text and "'automatic_captions'" not in text, p
        assert '"writeautomaticsub": True' not in text, p


def test_manual_caption_lang_prefers_order_and_region():
    assert source.manual_caption_lang({"subtitles": {"en": [], "ko-KR": []}}, ["ko", "en"]) == "ko-KR"
    assert source.manual_caption_lang({"subtitles": {"live_chat": []}}, ["ko", "en"]) is None


# ---------- 받기 규칙 ----------
@pytest.mark.parametrize("ref,vid", [
    ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
])
def test_parse_video_ref(ref, vid):
    assert source.parse_video_ref(ref) == vid


@pytest.mark.parametrize("ref", [
    "https://www.youtube.com/playlist?list=PL123", "https://www.youtube.com/@TechBridge-KR",
    "https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv", "https://example.com/watch?v=dQw4w9WgXcQ",
])
def test_parse_video_ref_rejects_collections(ref):
    with pytest.raises(source.SourceError):
        source.parse_video_ref(ref)


def test_download_retries_once_then_fails(tmp_path):
    attempts = []

    class Boom:
        def __init__(self, opts):
            attempts.append(opts["format"])

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download):
            raise RuntimeError("HTTP Error 403")

    with pytest.raises(source.SourceError, match="2회"):
        source.download("dQw4w9WgXcQ", tmp_path, need_video=True, max_height=1080, ydl=Boom)
    assert len(attempts) == 2 and all("height<=1080" in a for a in attempts)
    assert source.format_selectors(False, 1080)[0].startswith("bestaudio")


def test_resolve_span_caps_long_videos():
    lo, hi, note = resolve_span(None, None, 95 * 60, 3600)
    assert (lo, hi) == (0, 3600) and "60분" in note
    assert resolve_span(600, 1200, 95 * 60, 3600)[:2] == (600, 1200)
    assert resolve_span(None, None, 400, 3600)[:2] == (0, 400)
    assert resolve_span(0, 9000, 400, 3600)[:2] == (0, 400)


# ---------- 전사 정규화, 품질 (V5) ----------
def test_normalize_segments_order_overlap_span():
    raw = [{"start": 10, "end": 12, "text": "c"}, {"start": 3, "end": 2, "text": "a"},
           {"start": 4, "end": 11, "text": "b"}, {"start": 60, "end": 62, "text": "out"},
           {"start": 39, "end": 39.5, "text": "  "}, {"start": 39.5, "end": 39.9, "text": "\ufffd\ufffd"},
           {"start": 38, "end": 39, "text": "red\ufffd"}]
    segs, fixes = tr.normalize_segments(raw, 100.0, 100.0, 140.0)
    assert [s["text"] for s in segs] == ["a", "b", "c", "red"]
    assert fixes == {"reversed": 1, "out_of_span": 1, "overlapped": 1, "blank": 2}
    for a, b in zip(segs, segs[1:], strict=False):
        assert a["start"] <= a["end"] <= b["start"] <= b["end"]
    assert segs[0]["start"] == 103.0  # 절대시각


def _segs(texts, length=2.0):
    return [{"start": i * length, "end": i * length + length, "text": t} for i, t in enumerate(texts)]


def test_quality_empty_suspect_ok():
    assert tr.judge_quality(tr.quality_signals([], None))[0] == "empty"
    assert tr.judge_quality(tr.quality_signals(_segs(["음"]), None))[0] == "empty"
    repeat = [{"start": i * 30.0, "end": i * 30.0 + 29.5, "text": "구독과 좋아요 부탁드립니다"} for i in range(10)]
    q, reasons = tr.judge_quality(tr.quality_signals(repeat, 0.1))
    assert q == "suspect_hallucination" and "반복" in reasons[0]
    normal = _segs([f"이번 발표에서는 {i}번째 주제인 에이전트 평가 방법을 다룬다" for i in range(20)])
    assert tr.judge_quality(tr.quality_signals(normal, 0.05))[0] == "ok"
    nospeech = [s | {"no_speech_prob": 0.9, "avg_logprob": -1.2} for s in _segs([f"말 {i} 다른 내용" for i in range(10)])]
    assert tr.judge_quality(tr.quality_signals(nospeech, 0.7))[0] == "suspect_hallucination"


def test_transcribe_with_fake_whisper(tmp_path):
    def whisper(wav, **kw):
        assert kw["language"] == "en" and kw["path_or_hf_repo"].endswith("large-v3-turbo")
        return {"language": "en", "segments": [{"start": 0, "end": 5, "text": " Hello there, this slide."},
                                                {"start": 5, "end": 9, "text": "Latency dropped to 40 ms."}]}

    out = tr.transcribe(tmp_path / "a.wav", model="large-v3-turbo", lo=600.0, hi=700.0, whisper=whisper,
                        detect=lambda *a: ("en", [{"at": 1, "lang": "en", "prob": 0.99}], []),
                        silence=lambda *a: 0.1)
    assert out["segments"][0] == {"start": 600.0, "end": 605.0, "text": "Hello there, this slide."}
    assert out["transcript_quality"] == "ok" and out["quality_signals"]["language_votes"]


# ---------- 프레임 예산, 중복 제거 ----------
def test_dedup_and_uniform_reduce():
    a, b = bytes([10] * fr.THUMB_BYTES), bytes([200] * fr.THUMB_BYTES)
    almost_a = bytes([12] * fr.THUMB_BYTES)
    assert fr.dedup_indices([a, almost_a, b, b, a]) == [0, 2, 4]
    assert fr.uniform_reduce(10, 3) == [0, 4, 9]
    assert fr.uniform_reduce(3, 5) == [0, 1, 2]
    assert fr.gap_fill_times([0, 10], 1, 0, 10) == [5.0]


@pytest.mark.parametrize("ratio,survivors,span", [(0.9, 300, 900), (0.1, 3, 60), (None, 50, 7200)])
def test_plan_budget_never_exceeds_cap(ratio, survivors, span):
    cap, target = fr.plan_budget(ratio, survivors, span, 20)
    assert cap <= 20 and target <= cap
    assert target >= min(fr.MIN_CONTEXT_FRAMES, cap)


def test_target_geometry_no_upscale_even_dims():
    assert fr.target_geometry(1920, 1080, 768) == (768, 432)
    assert fr.target_geometry(640, 360, 1024) == (640, 360)
    assert fr.target_geometry(None, None, 768) is None


# ---------- 화면 지시 프레임, spoken_text ----------
def test_select_cues_ko_en_and_interval():
    ko = [{"start": 0, "end": 2, "text": "오늘은"}, {"start": 2, "end": 4, "text": "여기 이 그래프를"},
          {"start": 4, "end": 6, "text": "보시면 지연이 줄었습니다"}, {"start": 6.5, "end": 8, "text": "다음으로"}]
    times, _ = cues.select_cues(ko, "ko", budget=5, lo=0, hi=100)
    assert times and all(0 <= t <= 100 for t in times)
    en = [{"start": 10, "end": 13, "text": "As you can see on this slide,"},
          {"start": 13, "end": 15, "text": "the chart shows latency."}]
    times_en, _ = cues.select_cues(en, "en", budget=3, lo=0, hi=100)
    assert times_en[0] == pytest.approx(11.5)
    # 최소 간격 5초
    assert all(b - a >= cues.MIN_CUE_INTERVAL for a, b in zip(times, times[1:], strict=False))
    _, warn = cues.select_cues(en, "ja", budget=3, lo=0, hi=100)
    assert warn


def test_attach_spoken_every_frame():
    segs = [{"start": 0, "end": 5, "text": "first"}, {"start": 5, "end": 9, "text": "second"},
            {"start": 30, "end": 32, "text": "far"}]
    frames = cues.attach_spoken([{"t": 6.0}, {"t": 10.5}, {"t": 20.0}], segs)
    assert [(f["segment_index"], f["spoken_text"]) for f in frames] == [(1, "second"), (1, "second"), (None, "")]
    assert cues.attach_spoken([{"t": 1.0}], [])[0] == {"t": 1.0, "segment_index": None, "spoken_text": ""}


# ---------- A5 계약 ----------
def fixture_results() -> list[Path]:
    return sorted(p for p in FIXTURES.glob("*.json") if not p.name.startswith("_"))


def test_fixtures_exist_and_pass_contract():
    paths = fixture_results()
    assert len(paths) >= 2, "실제 영상 1차 처리 픽스처 2~3편"
    for p in paths:
        assert contract.check(json.loads(p.read_text(encoding="utf-8"))) == [], p.name


def _broken(mutate):
    data = json.loads(next(p for p in fixture_results()
                           if json.loads(p.read_text(encoding="utf-8"))["frames"]).read_text(encoding="utf-8"))
    mutate(data)
    return contract.check(data)


def test_contract_rejects_broken_copies():
    def reverse_segments(d):
        d["segments"][0], d["segments"][1] = d["segments"][1], d["segments"][0]

    def reverse_frames(d):
        d["frames"][0], d["frames"][1] = d["frames"][1], d["frames"][0]

    def over_cap(d):
        d["frames"] = d["frames"] + copy.deepcopy(d["frames"][-1:]) * (FRAME_CAP_MAX + 1 - len(d["frames"]))

    def outside(d):
        d["frames"][0]["path"] = "../../etc/passwd"

    def absolute(d):
        d["frames"][0]["path"] = "/tmp/frame.jpg"

    def bad_quality(d):
        d["transcript_quality"] = "great"

    def frame_after_end(d):
        d["frames"][-1]["t"] = d["duration_sec"] + 50

    def spoken_mismatch(d):
        f = next(f for f in d["frames"] if f["segment_index"] is not None)
        f["spoken_text"] = "다른 문장"

    for mutate in (reverse_segments, reverse_frames, over_cap, outside, absolute, bad_quality, frame_after_end,
                   spoken_mismatch):
        assert _broken(mutate), mutate.__name__


# ---------- A11 보관(작업 폴더) ----------
def test_purge_only_old_workdirs(tmp_path):
    now = time.time()
    for vid, age_days in (("OLDOLDOLD01", 8), ("NEWNEWNEW01", 2)):
        ws = Workspace(tmp_path, vid)
        ws.save_meta({"committed_at": now - age_days * 86400, "last_used_at": now - age_days * 86400})
        (ws.dir / "media.mp4").write_bytes(b"x" * 10)
    res = purge(tmp_path, 7, now=now)
    assert res["removed"] == ["OLDOLDOLD01"] and res["kept"] == ["NEWNEWNEW01"]
    assert not (tmp_path / "OLDOLDOLD01").exists() and (tmp_path / "NEWNEWNEW01/media.mp4").exists()


def test_workspace_refuses_paths_outside(tmp_path):
    ws = Workspace(tmp_path / "media", "AAAAAAAAAAA")
    with pytest.raises(RuntimeError):
        ws.assert_inside(tmp_path / "elsewhere")
    with pytest.raises(ValueError):
        Workspace(tmp_path, "../x")


# ---------- 맥: 합성 영상으로 1차 처리 전체(ffmpeg 실제, 받기·전사는 가짜) ----------
def _synthetic_video(path: Path) -> None:
    # 10초마다 색이 바뀌는 40초 영상 + 소리
    colors = ["red", "blue", "green", "white"]
    inputs = []
    for c in colors:
        inputs += ["-f", "lavfi", "-i", f"color=c={c}:s=640x360:d=10:r=10"]
    concat = "".join(f"[{i}:v]" for i in range(len(colors))) + f"concat=n={len(colors)}:v=1:a=0[v]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-f", "lavfi", "-i", "sine=f=440:d=40",
                    "-filter_complex", concat, "-map", "[v]", "-map", f"{len(colors)}:a", "-c:v", "libx264",
                    "-g", "50", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)


@mac_video
def test_media_process_synthetic_end_to_end(tmp_path):
    src = tmp_path / "src.mp4"
    _synthetic_video(src)

    def download(video_id, staging, *, need_video, max_height):
        dst = staging / "dl.mp4"
        shutil.copy(src, dst)
        return {"path": dst, "title": "합성 영상", "declared_duration": 40.0}

    def transcribe(wav, *, model, lo, hi, lang):
        assert wav.is_file()
        segs = [{"start": 0.0, "end": 8.0, "text": "Welcome to the talk."},
                {"start": 12.0, "end": 18.0, "text": "As you can see on this slide, latency is 40 ms."},
                {"start": 22.0, "end": 38.0, "text": "Thanks for listening."}]
        return {"language": "en", "segments": segs, "transcript_quality": "ok", "quality_signals": {},
                "warnings": []}

    item = VideoQueueItem(video_id="SYNTHETIC01", mode="whisper+slides", reason="합성 테스트")
    r = media_process(item, cfg(), tmp_path / "media", deps=Deps(download=download, transcribe=transcribe))
    assert contract.check(r, check_files=True) == []
    assert 1 <= len(r.frames) <= FRAME_CAP_MAX and r.frames_meta and r.frames_error is None
    assert r.frames[0].reason == "first-frame"
    assert {f.reason for f in r.frames} <= {"transcript-cue", "scene-change", "first-frame", "uniform"}
    assert not (tmp_path / "media/SYNTHETIC01/audio.wav").exists()  # 전사 뒤 오디오 삭제
    assert (tmp_path / "media/SYNTHETIC01/meta.json").exists()
    # 같은 영상을 다시: 받은 파일 재사용(받기 호출 없음)
    r2 = media_process(item, cfg(), tmp_path / "media",
                       deps=Deps(download=lambda *a, **k: pytest.fail("다시 받음"), transcribe=transcribe))
    assert MediaResult.model_validate(r2.model_dump()) and contract.check(r2, check_files=True) == []
