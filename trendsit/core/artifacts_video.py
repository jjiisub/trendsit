"""S4 영상 분석가의 입력·출력 스키마. 영상 처리 지시(CONTRACTS 1장)와 1차 처리 결과(MediaResult).

core/artifacts.py에는 등록(INPUTS, OUTPUTS)만 둔다(COMMON 9장).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .artifacts import RoleOutput

VIDEO_ID = r"^[A-Za-z0-9_-]{11}$"
Mode = Literal["skip", "captions", "whisper", "whisper+slides"]
TranscriptQuality = Literal["ok", "suspect_hallucination", "empty"]
# 프레임을 고른 이유. 판독 우선순위 순서(V6): 발화 신호 → 화면 변화 → 첫 화면 → 균등 보완
FrameReason = Literal["transcript-cue", "scene-change", "first-frame", "uniform"]
FRAME_PRIORITY: dict[str, int] = {"transcript-cue": 0, "scene-change": 1, "first-frame": 2, "uniform": 3}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- 영상 처리 지시 (CONTRACTS 1장. S3 CollectionPlan.video_queue[]와 같은 JSON) ----------
class VideoQueueItem(_Strict):
    video_id: str = Field(pattern=VIDEO_ID, description="S1 videos.video_id")
    mode: Mode
    start_sec: int | None = Field(default=None, ge=0)
    end_sec: int | None = Field(default=None, gt=0)
    reason: str = Field(description="왜 이 깊이인지 한 줄. 영상 분석가 log에 그대로 이어 씀")

    @field_validator("reason")
    @classmethod
    def _one_line(cls, v: str) -> str:
        v = v.strip()
        if not v or "\n" in v:
            raise ValueError("reason은 빈칸이 아닌 한 줄")
        return v

    @model_validator(mode="after")
    def _span(self) -> VideoQueueItem:
        if self.start_sec is not None and self.end_sec is not None and self.end_sec <= self.start_sec:
            raise ValueError("end_sec는 start_sec보다 커야 함")
        return self


# ---------- 1차 처리 결과 (V1, V12) ----------
class Segment(_Strict):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str


class Frame(_Strict):
    t: float = Field(ge=0, description="실측 프레임 시각(초, 절대시각)")
    path: str = Field(description="작업 폴더 기준 상대 경로")
    reason: FrameReason
    segment_index: int | None = Field(description="그 시각의 발화 segment. 2초 안에 발화가 없으면 null")
    spoken_text: str = Field(description="segments[segment_index].text. segment_index가 null이면 빈 문자열")


class FramesMeta(_Strict):
    tier: Literal["auto", "full"]
    engine: Literal["keyframe", "scene-change", "uniform"]
    candidates: int = Field(ge=0, description="후보 수(중복 제거 전)")
    deduped: int = Field(ge=0, description="중복 제거 뒤 남은 후보 수")
    distinct_ratio: float | None
    selected: int = Field(ge=0)
    cue_selected: int = Field(ge=0, description="발화 신호로 고른 프레임 수")
    cap: int = Field(ge=1, description="이번 영상의 프레임 예산")
    resolution: int = Field(description="실제 출력 가로 픽셀")
    fallback: bool = Field(description="후보가 모자라 균등 추출로 바꿨는지")


class Span(_Strict):
    start: float = Field(ge=0)
    end: float = Field(gt=0)


class MediaEnv(_Strict):
    """검증 산출물용 실행 환경(COMMON 10장)."""

    device: str
    whisper_model: str | None = None
    versions: dict[str, str] = {}
    timings_sec: dict[str, float] = {}


class MediaResult(_Strict):
    video_id: str = Field(pattern=VIDEO_ID)
    mode: Literal["captions", "whisper", "whisper+slides"]
    title: str
    duration_sec: int = Field(gt=0)
    span: Span = Field(description="처리 구간. 구간 지정이 없으면 0~길이(60분 상한 적용)")
    language: str
    transcript_source: Literal["whisper", "manual"]
    transcript_quality: TranscriptQuality
    quality_signals: dict[str, Any] = Field(default={}, description="품질 판정 근거 수치")
    segments: list[Segment]
    frames: list[Frame] = []
    frames_meta: FramesMeta | None = None
    frames_error: str | None = None
    warnings: list[str] = []
    work_dir: str
    env: MediaEnv
    truncated_segments: bool = Field(default=False, description="픽스처에서 segments를 앞부분만 남겼으면 true")

    def text(self) -> str:
        return " ".join(s.text for s in self.segments if s.text).strip()


# ---------- 슬라이드 판독 (video_slide 출력) ----------
class SlideNumber(_Strict):
    confidence: Literal["high", "low", "check"] = Field(
        description="high: 또렷함 / low: 읽었지만 흐림 / check: 숫자를 확신할 수 없어 사람 확인 필요(값 추측 금지)")
    value: str = Field(description="ocr_text 안의 문자열 그대로(예: '1.2M', '35%'). check면 보이는 만큼만")
    unit: str = Field(description="단위나 기호(%, ms, 배, $ 등). 없으면 빈 문자열")
    what: str = Field(description="무엇의 수치인지 화면 표현 그대로 짧게(예: 'p95 latency')")


class SlideReading(RoleOutput):
    frame_kind: Literal["slide", "demo", "speaker", "other"]
    ocr_text: str = Field(description="화면 글자 그대로(하드 자막 줄 제외). slide가 아니면 빈 문자열")
    numbers: list[SlideNumber] = Field(description="slide의 수치. 없거나 slide가 아니면 빈 목록")
    table: list[list[str]] | None = Field(description="화면의 표를 행 목록으로. 표가 없으면 null")
    title: str = Field(description="슬라이드 제목 그대로. 없으면 빈 문자열")


# ---------- 대조 결과 (코드, V8) ----------
class SlideOnlyFact(_Strict):
    fact: str = Field(description="무엇의 수치인지(판독의 what)")
    value: str
    unit: str
    sec: int
    evidence: str = Field(description="근거 id vd:{item_id}@{sec}")
    confidence: Literal["high", "low"]


class CheckNumber(_Strict):
    """확신도 check 판독. slide_only_facts에 넣지 않고 사람 확인 목록으로."""

    sec: int
    value: str
    unit: str
    what: str
    frame: str = Field(description="프레임 경로(작업 폴더 기준)")
