"""S5 주간 브리핑 역할의 입력·출력 스키마(COMMON 9장: 스펙별 파일). 무거운 의존성을 가져오지 않는다.

역할 다섯: decide(묶기 판단), editor_select(편집장 선별), writer(작성자), writer_revise(작성자 수정), critic(검수자).
코드가 값을 정하는 칸은 처음부터 ClassVar ENFORCED_FIELDS로 선언한다(S5 5.1-4).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    video_relevance_min: float = Field(default=0.0, description="영상 자리(C-20): 이 관련성 이상 영상 묶음이 있으면 영상 토픽 1개 이상")


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


# ---------- writer (작성자) ----------
class Point(_Strict):
    text: str = Field(description="명사형 1~2문장, 80자 안팎")
    refs: list[str] = Field(description="근거 id 1~3개")
    check: bool = Field(default=False, description="코드가 정함: 같은 이슈가 두 번 남으면 true(확인 필요)")


class NumberItem(_Strict):
    label: str
    # 숫자도 받는다: 문자열만 허용하면 모델이 숫자를 쓰려다 구조화 출력 문법에 막혀 공백만 반복하다 잘렸다(W40 7건).
    # 받은 숫자는 문자열로 바꿔 저장(근거 표기와의 대조는 코드 검사가 값으로 한다)
    value: str | float = Field(description="근거 표기 그대로(예: '77.9%'). 숫자만이면 숫자로 써도 됨")

    @field_validator("value", mode="after")
    @classmethod
    def _as_text(cls, v: str | float) -> str:
        if isinstance(v, float):
            return f"{v:g}" if abs(v) < 1e15 else str(v)
        return v
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

    def enforce(self, inp: Any, ctx: Ctx | None) -> Self:
        """points[].check는 코드가 정하는 값(같은 이슈 두 번 → true). 작성자 출력의 check는 false로."""
        if any(p.check for p in self.points):
            return self.fix("points", [p.model_copy(update={"check": False}) for p in self.points],
                            "check는 코드 소유(작성자 출력은 false)", owned=True)
        return self


def loc_lines(page: TopicPage) -> list[str]:
    """위치 이름이 붙은 줄(번호 0부터). 검수자·수정이 위치를 1부터 세던 문제(W40·W41 평가 13/13)를 입력에서 막는다."""
    out = [f"title: {page.title}", f"summary: {page.summary}", f"overview: {page.overview}"]
    out += [f"points[{i}]: {p.text} (refs {', '.join(p.refs)})" for i, p in enumerate(page.points)]
    for i, g in enumerate(page.numbers):
        out.append(f"numbers[{i}] (anchor {g.anchor}): {g.title} / context: {g.context}")
        out += [f"numbers[{i}].items[{j}]: {it.label} = {it.value} ({it.ref})" for j, it in enumerate(g.items)]
    for i, g in enumerate(page.events):
        out.append(f"events[{i}] (anchor {g.anchor}): {g.title} / context: {g.context}")
        out += [f"events[{i}].items[{j}]: {it.date} {it.text} ({it.ref or it.topic_id})" for j, it in enumerate(g.items)]
    out += [f"contributions[{i}]: [{c.channel}] {c.text}" for i, c in enumerate(page.contributions)]
    out += [f"concepts[{i}]: {c.term} - {c.desc}" for i, c in enumerate(page.concepts)]
    return out


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
    loc_lines: list[str] = Field(default=[], description="previous를 위치 이름(loc)이 붙은 줄로 펼친 것")
    previous: TopicPage
    issues: list[IndexedIssue]
    evidence: list[Document] = Field(description="지적된 칸의 근거 원문만")
    aliases: list[AliasLine]


class Change(_Strict):
    issue_idx: int
    loc: str
    action: Literal["edit", "delete", "add"]
    value: str | Point | NumberGroup | EventGroup | Contribution | Concept | NumberItem | EventItem | None = Field(
        description="그 위치의 새 값(writer와 같은 칸 형식, 하위 위치면 그 항목·글자). delete면 null")


class TopicPageRevision(RoleOutput):
    changed: list[Change]


# ---------- critic (검수자) ----------
class CriticInput(RoleInput):
    loc_lines: list[str] = Field(default=[], description="page를 위치 이름(loc)이 붙은 줄로 펼친 것. 이슈 loc은 이 이름 그대로")
    page: TopicPage
    evidence: list[Document] = Field(description="이 토픽의 근거 원문(refs가 가리키는 것 먼저, 카드 요약 id 제외)")
    angle: str
    previous: PreviousTopic | None = Field(default=None, description="후속 토픽이면 지난 토픽(요약·포인트). 지난 토픽을 말하는 문장은 이것과 대조")
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
    ENFORCED_FIELDS = ("fact_support", "status", "attention")  # atoms에서 다시 셈, 이슈가 있으면 reject, reject면 attention

    atoms: list[Atom] = Field(description="모든 원자 사실. 가장 먼저 채움")
    fact_support: FactSupport
    issues: list[Issue]
    status: Literal["pass", "reject"]

    def enforce(self, inp: CriticInput, ctx: Ctx | None) -> Self:
        support = FactSupport(total=len(self.atoms), supported=sum(a.supported for a in self.atoms))
        out = self.fix("fact_support", support, "원자 사실 수를 atoms에서 다시 셈")
        if out.issues and out.status == "pass":
            out = out.fix("status", "reject", "이슈가 있으면 reject", owned=True)
        if out.status == "reject" and not out.attention:
            out = out.fix("attention", True, "반려는 attention")
        return out


# ---------- 관문 B: 근거 충실성 judge(원자 사실, eval/judge_facts.md) ----------
class FactCheck(RoleOutput):
    """judge가 출력의 모든 문장을 원자 사실로 쪼개 근거 문서와 대조한 결과. 지지율은 코드가 센다."""

    atoms: list[Atom] = Field(description="출력의 모든 원자 사실. 칸 순서대로")


INPUTS = (DecideInput, EditorSelectInput, WriterInput, WriterReviseInput, CriticInput)
OUTPUTS = (DecideAnswer, BriefingPlan, TopicPage, TopicPageRevision, ReviewVerdict, FactCheck)
register_schemas("artifacts_brief", INPUTS, OUTPUTS)
