"""video.yaml(S4 소유) 스키마. mode(편집장 계획의 처리 깊이, CONTRACTS 1장) → 1차 처리 설정.

core/config.py를 가져오지 않는다(config.py가 이 파일을 등록할 수 있게 순환 가져오기를 피함).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# 영상당 프레임 상한(예산, agents_spec 4장). 설정으로도 넘을 수 없다
FRAME_CAP_MAX = 20
# 세로 상한(이미지 입력 제약)과 업스케일 없는 가로 범위
FRAME_RES_RANGE = (256, 1998)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ModeSettings(_Strict):
    transcript: Literal["whisper", "manual"]
    frames: Literal["off", "auto", "full"]
    frames_res: int = Field(default=768, ge=FRAME_RES_RANGE[0], le=FRAME_RES_RANGE[1])
    frames_cap: int = Field(default=FRAME_CAP_MAX, ge=1, le=FRAME_CAP_MAX)


class Modes(_Strict):
    """skip은 설정이 없다(큐에서 건너뜀). 나머지 세 mode는 모두 있어야 한다."""

    captions: ModeSettings
    whisper: ModeSettings
    whisper_slides: ModeSettings = Field(alias="whisper+slides")

    @model_validator(mode="after")
    def _depth(self) -> Modes:
        # mode 이름과 설정이 어긋나면 편집장이 정한 깊이와 실제 처리가 달라진다
        if self.captions.transcript != "manual" or self.captions.frames != "off":
            raise ValueError("captions는 transcript: manual, frames: off만 허용")
        if self.whisper.transcript != "whisper" or self.whisper.frames != "off":
            raise ValueError("whisper는 transcript: whisper, frames: off만 허용")
        if self.whisper_slides.transcript != "whisper" or self.whisper_slides.frames == "off":
            raise ValueError("whisper+slides는 transcript: whisper, frames: auto 또는 full만 허용")
        return self

    def get(self, mode: str) -> ModeSettings:
        return {"captions": self.captions, "whisper": self.whisper, "whisper+slides": self.whisper_slides}[mode]


class VideoConfig(_Strict):
    whisper_model: Literal["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"]
    max_span_sec: int = Field(ge=60, le=4 * 3600)
    download_max_height: Literal[360, 480, 720, 1080]
    caption_langs: list[str] = Field(min_length=1)
    retention_days: int = Field(ge=1, le=90)
    segment_ttl_weeks: int = Field(ge=1, le=52)
    align_window_sec: int = Field(ge=0, le=300)
    modes: Modes
