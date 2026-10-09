"""S5 주간 브리핑 역할의 입력·출력 스키마(COMMON 9장: 스펙별 파일). 무거운 의존성을 가져오지 않는다.

역할 다섯: decide(묶기 판단), editor_select(편집장 선별), writer(작성자), writer_revise(작성자 수정), critic(검수자).
코드가 값을 정하는 칸은 처음부터 ClassVar ENFORCED_FIELDS로 선언한다(S5 5.1-4).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Self

from pydantic import BaseModel, ConfigDict, Field

from .artifacts import Document, RoleInput, RoleOutput, register_schemas

if TYPE_CHECKING:
    from .context import Ctx

Channel = Literal["text", "video", "github"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- decide (묶기 판단, 쌍 하나) ----------
class PairShared(_Strict):
    keywords: list[str] = Field(description="두 항목이 공유하는 키워드 id")
    aliases: list[str] = Field(description="두 항목이 공유하는 이름(정본 표기)")
    similarity: float = Field(description="임베딩 유사도(참고용)")


class DecideInput(RoleInput):
    a: Document = Field(description="항목 a. id는 근거 키(it:/vd:/rp:)")
    b: Document
    shared: PairShared


class DecideAnswer(RoleOutput):
    reason: str = Field(description="두 항목이 가리키는 대상을 각각 이름으로 적고 같은지 다른지 한 줄")
    same: bool
    confidence: float = Field(ge=0, le=1, description="0~1. 코드는 0.6 미만이면 묶지 않음")

    @classmethod
    def fallback(cls, reason: str, inp: DecideInput) -> Self:
        """실패하면 묶지 않는다(s5_role_notes 0.4)."""
        return cls(reason=f"대체 출력: {reason}", same=False, confidence=0.0, log=f"묶기 판단 실패({reason})",
                   attention=True)


# ---------- editor_select (편집장 선별) ----------
class CandidateItem(_Strict):
    member: str = Field(description="근거 키 it:/vd:/rp:")
    channel: Channel
    title: str
    line: str = Field(description="한 줄 요약")
    relevance: str = Field(description="high/mid/low. 레포는 relevant이면 high")


class PastCandidate(_Strict):
    topic_id: str
    title: str
    similarity: float


class RecentTopic(_Strict):
    topic_id: str
    week: str
    title: str
    summary: str


class KeywordTrend(_Strict):
    keyword: str
    this_week: int
    last_week: int


class RepoLine(_Strict):
    full_name: str
    oneliner: str
    signal: str
    stars_this_week: int | None


class SelectLimits(_Strict):
    min_topics: int
    max_topics: int
    lead: int = 1


class EditorSelectInput(RoleInput):
    candidates: list[Document] = Field(description="후보 묶음. id c{cluster_id}, cluster_id 순서 고정")
    recent_topics: list[RecentTopic]
    keyword_trend: list[KeywordTrend]
    repo_cards: list[RepoLine]
    limits: SelectLimits
    previous_errors: list[str] = Field(default=[], description="직전 출력이 코드 검증에서 거부된 이유(재시도 때만)")


class Decision(_Strict):
    cluster_id: int
    reason: str = Field(description="입력 값만 인용한 한 줄")
    action: Literal["select", "drop"]
    drop_reason: Literal["duplicate", "low_relevance", "thin", "other"] | None = Field(
        description="drop일 때만. select면 null")


class Split(_Strict):
    cluster_id: int
    groups: list[list[str]] = Field(description="근거 키 목록의 목록(그 후보의 항목 안에서만)")
    reason: str


class Relation(_Strict):
    type: Literal["new", "follow_up"]
    topic_id: str | None = Field(description="follow_up이면 과거 대조 후보의 지난 토픽 id, new면 null")


class PlannedTopic(_Strict):
    cluster_ids: list[int] = Field(min_length=1)
    rank: int = Field(ge=1)
    lead: bool
    relation: Relation
    relation_reason: str
    angle: str = Field(description="다룰 축 한 줄(사실 주장·수치 없이)")
    slug_hint: str = Field(description="영문 소문자 2~3단어, 하이픈")


class BriefingPlan(RoleOutput):
    decisions: list[Decision] = Field(description="모든 후보마다 하나. 가장 먼저 채움")
    splits: list[Split]
    topics: list[PlannedTopic]
    featured_repos: list[str] = Field(description="홈에 올릴 레포 이름(최대 5)")

    @classmethod
    def fallback(cls, reason: str, inp: EditorSelectInput) -> Self:
        """코드 대체(점수 순 상위 N)는 brief/select.py가 만든다. 여기서는 빈 계획 + attention."""
        return cls(decisions=[], splits=[], topics=[], featured_repos=[], log=f"편집장 선별 실패({reason})",
                   attention=True)


# ---------- writer (작성자) ----------
class Point(_Strict):
    text: str = Field(description="명사형 1~2문장, 80자 안팎")
    refs: list[str] = Field(description="근거 id 1~3개")
    check: bool = Field(default=False, description="코드가 정함: 같은 이슈가 두 번 남으면 true(확인 필요)")


class NumberItem(_Strict):
    label: str
    value: str = Field(description="근거 표기 그대로")
    ref: str
    baseline: bool = Field(default=False, description="전후 비교의 이전 값")
    emphasis: bool = False


class NumberGroup(_Strict):
    anchor: int = Field(ge=1, description="붙는 포인트 번호(1부터)")
    group: str
    title: str = Field(description="발견을 말하는 제목")
    context: str = Field(description="무엇을 어떤 조건에서 비교했는지 1~2문장, 근거 id 포함")
    unit: str
    items: list[NumberItem]


class EventItem(_Strict):
    date: str = Field(description="YYYY-MM-DD(근거에 있는 날짜)")
    text: str
    ref: str | None = Field(description="근거 id. 지난 토픽이면 null")
    topic_id: str | None = Field(description="지난 토픽 id. 근거 id가 있으면 null")


class EventGroup(_Strict):
    anchor: int = Field(ge=1)
    title: str
    context: str
    flow_is_point: bool = False
    items: list[EventItem]


class Contribution(_Strict):
    channel: Channel
    text: str
    refs: list[str]


class Concept(_Strict):
    term: str
    desc: str


class PlanBrief(_Strict):
    rank: int
    angle: str
    relation: Relation


class PreviousTopic(_Strict):
    topic_id: str
    title: str
    summary: str
    points: list[str]


class AliasLine(_Strict):
    canonical: str
    aliases: list[str]


class WriterInput(RoleInput):
    plan: PlanBrief
    evidence: list[Document] = Field(description="이 토픽의 근거 목록. id가 근거 id")
    previous: PreviousTopic | None
    aliases: list[AliasLine]


class TopicPage(RoleOutput):
    points: list[Point]
    numbers: list[NumberGroup]
    events: list[EventGroup]
    contributions: list[Contribution]
    concepts: list[Concept]
    overview: str = Field(description="1문단 2~4문장, '~다'")
    summary: str = Field(description="1~2문장(최대 3), 첫 문장이 결론")
    title: str = Field(description="명사구 30자 안팎")

    @classmethod
    def fallback(cls, reason: str, inp: WriterInput) -> Self:
        return cls(points=[], numbers=[], events=[], contributions=[], concepts=[], overview="", summary="", title="",
                   log=f"작성 실패({reason})", attention=True)


# ---------- writer_revise (작성자 수정: 고친 칸만) ----------
# 검수자 이슈 7종 + format(코드 검사 반려: 분량, 필수 칸, 금지 표현, 도식 칸 규칙)
IssueType = Literal["unsupported", "number_mismatch", "overclaim", "wrong_ref", "missing_key", "overuse",
                    "missing_diagram", "format"]


class Issue(_Strict):
    loc: str = Field(description="위치(예: points[2], numbers[0].items[1], summary)")
    type: IssueType
    evidence_id: str | None
    comment: str
    hint: str


class IndexedIssue(Issue):
    idx: int


class WriterReviseInput(RoleInput):
    previous: TopicPage
    issues: list[IndexedIssue]
    evidence: list[Document] = Field(description="지적된 칸의 근거 원문만")
    aliases: list[AliasLine]


class Change(_Strict):
    issue_idx: int
    loc: str
    action: Literal["edit", "delete", "add"]
    value: str | Point | NumberGroup | EventGroup | Contribution | Concept | None = Field(
        description="그 위치의 새 값(writer와 같은 칸 형식). delete면 null")


class TopicPageRevision(RoleOutput):
    changed: list[Change]

    @classmethod
    def fallback(cls, reason: str, inp: WriterReviseInput) -> Self:
        return cls(changed=[], log=f"수정 실패({reason})", attention=True)


# ---------- critic (검수자) ----------
class CriticInput(RoleInput):
    page: TopicPage
    evidence: list[Document] = Field(description="page의 refs가 가리키는 근거 원문만")
    angle: str
    code_warnings: list[str]
    round: int = Field(ge=1, le=3)


class Atom(_Strict):
    loc: str
    fact: str
    evidence_id: str | None
    supported: bool


class FactSupport(_Strict):
    total: int
    supported: int


class ReviewVerdict(RoleOutput):
    ENFORCED_FIELDS = ("fact_support",)  # atoms에서 코드가 다시 셈

    atoms: list[Atom] = Field(description="모든 원자 사실. 가장 먼저 채움")
    fact_support: FactSupport
    issues: list[Issue]
    status: Literal["pass", "reject"]

    @classmethod
    def fallback(cls, reason: str, inp: CriticInput) -> Self:
        return cls(atoms=[], fact_support=FactSupport(total=0, supported=0), issues=[], status="pass",
                   log=f"검수 실패({reason})", attention=True)

    def enforce(self, inp: CriticInput, ctx: Ctx | None) -> Self:
        support = FactSupport(total=len(self.atoms), supported=sum(a.supported for a in self.atoms))
        out = self.fix("fact_support", support, "원자 사실 수를 atoms에서 다시 셈")
        if out.issues and out.status == "pass":
            out = out.fix("status", "reject", "이슈가 있으면 reject", owned=True)
        if out.status == "reject" and not out.attention:
            out = out.fix("attention", True, "반려는 attention")
        return out


INPUTS = (DecideInput, EditorSelectInput, WriterInput, WriterReviseInput, CriticInput)
OUTPUTS = (DecideAnswer, BriefingPlan, TopicPage, TopicPageRevision, ReviewVerdict)
register_schemas("artifacts_brief", INPUTS, OUTPUTS)
