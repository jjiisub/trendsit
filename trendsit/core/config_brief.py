"""brief.yaml(S5 소유) 스키마. 토픽 수, 문턱값, 상한, 라운드 같은 조정값은 모두 여기(S5_TASK 5.11).

core/config.py를 가져오지 않는다(config.py가 이 파일을 등록할 수 있게 순환 가져오기를 피함).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceCfg(_Strict):
    max_tokens_per_topic: int = Field(ge=1000)
    max_refs_per_paragraph: int = Field(ge=1, le=6)
    video_relevance_high: float = Field(gt=0, le=1)


class AliasesCfg(_Strict):
    fuzz_min_score: float = Field(ge=50, le=100)
    transliteration: dict[str, str] = {}  # 영문 낱말 → 한글 음차(작성자 출력·묶기 이름 신호의 표기 맞춤, 리뷰 R11)


class Thresholds(_Strict):
    auto: float = Field(gt=0, le=1)
    border: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def _order(self) -> Thresholds:
        if self.border >= self.auto:
            raise ValueError("border는 auto보다 작아야 함")
        return self


class DecideCfg(_Strict):
    max_calls_per_week: int = Field(ge=0)
    min_confidence: float = Field(ge=0, le=1)


class PastCfg(_Strict):
    top_k: int = Field(ge=1)
    weeks_back: int = Field(ge=1)


class ClusterCfg(_Strict):
    thresholds: Thresholds
    name_border: float = Field(gt=0, le=1)
    generic_names: list[str]
    broad_keywords: list[str]
    alias_decide_max: int = Field(ge=0)
    embed_text: Literal["card", "body"]
    reviewed_suspicious: list[str] = []
    max_cluster_size: int = Field(ge=2)
    decide: DecideCfg
    past: PastCfg


class TopicsCfg(_Strict):
    min: int = Field(ge=1)
    max: int = Field(ge=1)


class VideoSlotCfg(_Strict):
    min: int = Field(ge=0)
    relevance_min: float = Field(ge=0, le=1)


class SelectCfg(_Strict):
    max_candidates: int = Field(ge=1)
    topics: TopicsCfg
    video_slot: VideoSlotCfg
    lead: Literal[1]
    featured_repos_max: int = Field(ge=0)


class HighlightsCfg(_Strict):
    summary: int
    per_paragraph: int
    page: tuple[int, int]


class WriteInputCfg(_Strict):
    text_chars: int = Field(ge=100)
    transcript_chars: int = Field(ge=100)


class SummaryCfg(_Strict):
    sentences: tuple[int, int]
    chars_max: int


class SectionsCfg(_Strict):
    single_source: tuple[int, int]
    multi_source: tuple[int, int]


class ParagraphsCfg(_Strict):
    per_section: tuple[int, int]
    sentences_max: int
    chars_max: int


class TableCfg(_Strict):
    rows: tuple[int, int]
    cols: tuple[int, int]


class RetryFailedCfg(_Strict):
    rounds: int = Field(ge=0)
    wait_sec: int = Field(ge=0)


class WriteCfg(_Strict):
    input: WriteInputCfg
    summary: SummaryCfg
    sections: SectionsCfg
    paragraphs: ParagraphsCfg
    heading_chars_max: int
    head_tiles_max: int
    tiles_per_section: tuple[int, int]
    visuals_max: int
    visuals_target: tuple[int, int]
    bars_items: tuple[int, int]
    table: TableCfg
    slides_max: int
    video_secs_max: int
    highlights: HighlightsCfg
    retry_failed: RetryFailedCfg  # S9(015 흡수): weekly 작성 단계 뒤 LLMError failed 토픽 재시도

    def sections_for(self, n_sources: int) -> tuple[int, int]:
        """작성자 sections 개수 범위: 근거 소스가 둘 이상이면 multi_source."""
        return self.sections.multi_source if n_sources > 1 else self.sections.single_source


class ReviewCfg(_Strict):
    max_rounds: int = Field(ge=1, le=3)
    same_issue_repeat_to_check: int = Field(ge=1)
    duplicate_point_similarity: float = Field(gt=0, le=1)


class BriefConfig(_Strict):
    evidence: EvidenceCfg
    aliases: AliasesCfg
    cluster: ClusterCfg
    select: SelectCfg
    write: WriteCfg
    review: ReviewCfg
