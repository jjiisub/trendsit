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
    max_refs_per_point: int = Field(ge=1, le=5)
    video_relevance_high: float = Field(gt=0, le=1)


class AliasesCfg(_Strict):
    auto_approve: list[Literal["case", "space", "hyphen", "dot"]]
    fuzz_min_score: float = Field(ge=50, le=100)


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
    embed_text: Literal["card", "body"]
    reviewed_suspicious: list[str] = []
    linkage: Literal["average"]
    max_cluster_size: int = Field(ge=2)
    decide: DecideCfg
    past: PastCfg


class TopicsCfg(_Strict):
    min: int = Field(ge=1)
    max: int = Field(ge=1)


class SelectCfg(_Strict):
    max_candidates: int = Field(ge=1)
    topics: TopicsCfg
    lead: Literal[1]
    featured_repos_max: int = Field(ge=0)


class HighlightsCfg(_Strict):
    summary: int
    overview: int
    per_point: int
    page: tuple[int, int]


class DiagramsCfg(_Strict):
    numbers_groups_max: int
    events_groups_max: int
    per_point_max: int


class WriteCfg(_Strict):
    points: dict[Literal["single_source", "multi_source"], tuple[int, int]]
    overview_sentences: tuple[int, int]
    summary_sentences: tuple[int, int]
    highlights: HighlightsCfg
    diagrams: DiagramsCfg
    concepts_max: int


class ReviewCfg(_Strict):
    max_rounds: int = Field(ge=1, le=3)
    same_issue_repeat_to_check: int = Field(ge=1)
    duplicate_point_similarity: float = Field(gt=0, le=1)


class RuntimeCfg(_Strict):
    weekly_target_minutes: int


class BriefConfig(_Strict):
    evidence: EvidenceCfg
    aliases: AliasesCfg
    cluster: ClusterCfg
    select: SelectCfg
    write: WriteCfg
    review: ReviewCfg
    runtime: RuntimeCfg
