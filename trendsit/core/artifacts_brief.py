"""S5 주간 브리핑 역할의 입력·출력 스키마(COMMON 9장: 스펙별 파일). 무거운 의존성을 가져오지 않는다.

역할 다섯: decide(묶기 판단), editor_select(편집장 선별), writer(작성자), writer_revise(작성자 수정), critic(검수자).
코드가 값을 정하는 칸은 처음부터 ClassVar ENFORCED_FIELDS로 선언한다(S5 5.1-4).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self

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
    confidence: float = Field(ge=0, le=1, description="0~1. 낮으면 코드가 same과 관계없이 묶지 않음")

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


# ---------- writer (작성자, v2: 절 구조, D-27·S6-1 5.3) ----------
VisualType = Literal["none", "bars", "table", "tiles", "events"]


def _num_text(v: float) -> str:
    """부동소수점 값을 원래 자릿수로(007-A2-2): f'{v:g}'의 유효숫자 6자리 잘림·지수 표기(1.62e+06)를 피한다."""
    return str(int(v)) if v == int(v) else f"{v:.10f}".rstrip("0")


class Tile(_Strict):
    value: str
    label: str
    note: str = ""
    refs: list[str] = Field(min_length=1, max_length=3)


class Para(_Strict):
    text: str
    refs: list[str] = Field(min_length=1, max_length=4)


class NumberItem(_Strict):
    label: str
    # 숫자도 받는다: 문자열만 허용하면 모델이 숫자를 쓰려다 구조화 출력 문법에 막혀 공백만 반복하다 잘렸다(W40 7건).
    # 받은 숫자는 문자열로 바꿔 저장(근거 표기와의 대조는 코드 검사가 값으로 한다)
    value: str | float = Field(description="근거 표기 그대로(예: '77.9%'). 숫자만이면 숫자로 써도 됨")

    @field_validator("value", mode="after")
    @classmethod
    def _as_text(cls, v: str | float) -> str:
        return _num_text(v) if isinstance(v, float) else v
    ref: str
    baseline: bool = Field(default=False, description="전후 비교의 이전 값")
    emphasis: bool = False


class BarGroup(_Strict):
    title: str
    context: str = ""
    unit: str
    items: list[NumberItem] = Field(min_length=2, max_length=6)


class Table(_Strict):
    title: str
    note: str = ""
    columns: list[str] = Field(min_length=2, max_length=4)
    rows: list[list[str | float]] = Field(min_length=2, max_length=6,
                                          description="행마다 columns와 같은 길이, 첫 열은 행 머리. 숫자 셀도 받음(NumberItem과 같은 이유)")
    refs: list[str] = Field(min_length=1, max_length=4)

    @field_validator("rows", mode="after")
    @classmethod
    def _rows_as_text(cls, v: list[list[str | float]]) -> list[list[str]]:
        return [[_num_text(c) if isinstance(c, float) else c for c in row] for row in v]


class EventItem(_Strict):
    date: str = Field(description="YYYY-MM-DD(근거에 있는 날짜)")
    text: str
    ref: str | None = Field(default=None, description="근거 id. 지난 토픽이면 null")
    topic_id: str | None = Field(default=None, description="지난 토픽 id. 근거 id가 있으면 null")


class EventGroup(_Strict):
    title: str
    context: str = ""
    flow_is_point: bool = False
    items: list[EventItem] = Field(min_length=2, max_length=6)


class Section(_Strict):
    heading: str
    paragraphs: list[Para] = Field(min_length=1, max_length=2)
    visual: VisualType
    bars: BarGroup | None = None
    table: Table | None = None
    tiles: list[Tile] = Field(default_factory=list, description="visual=tiles일 때 2~3개, 아니면 []")
    events: EventGroup | None = None
    slide: str | None = Field(default=None, description="slide_candidates 중 하나의 sl: id. 코드가 채울 수도 있음")
    slide_caption: str = ""
    video_secs: list[int] = Field(default_factory=list, max_length=3, description="입력 타임라인의 sec")
    check: bool = Field(default=False, description="코드가 정함(같은 이슈가 두 번 남으면 true). 작성자 출력은 false")


class PlanBrief(_Strict):
    rank: int
    angle: str
    relation: Relation


class PreviousTopic(_Strict):
    topic_id: str
    title: str
    summary: str
    headings: list[str] = Field(description="v2: 지난 토픽 sections[].heading(5.3 하위 호환 없음, D-31)")


class AliasLine(_Strict):
    canonical: str
    aliases: list[str]


class WriterLimits(_Strict):
    sections: tuple[int, int] = Field(description="이 토픽의 근거 소스 수로 고른 sections 개수 범위")
    paragraphs_per_section: tuple[int, int]
    paragraph_sentences_max: int
    paragraph_chars_max: int
    summary_sentences: tuple[int, int]
    summary_chars_max: int
    heading_chars_max: int
    head_tiles_max: int
    tiles_per_section: tuple[int, int]
    visuals_max: int
    bars_items: tuple[int, int]
    table_rows: tuple[int, int]
    table_cols: tuple[int, int]
    slides_max: int
    video_secs_max: int
    max_refs_per_paragraph: int


class WriterInput(RoleInput):
    plan: PlanBrief
    evidence: list[Document] = Field(description="이 토픽의 근거 목록. id가 근거 id")
    previous: PreviousTopic | None
    aliases: list[AliasLine]
    limits: WriterLimits
    slide_candidates: list[str] = Field(default_factory=list, max_length=2, description="sl: id, 0~2")
    no_visuals: bool = Field(default=False, description="true면 모든 절의 visual을 none, head_tiles만")


class TopicPage(RoleOutput):
    head_tiles: list[Tile] = Field(default_factory=list, max_length=4)
    sections: list[Section]
    summary: str = Field(description="1~2문장(사건+쟁점), 150자 안팎")
    title: str = Field(description="명사구 30자 안팎")

    def enforce(self, inp: Any, ctx: Ctx | None) -> Self:
        """sections[].check는 코드가 정하는 값(같은 이슈 두 번 → true). 작성자 출력의 check는 false로."""
        if any(s.check for s in self.sections):
            return self.fix("sections", [s.model_copy(update={"check": False}) for s in self.sections],
                            "check는 코드 소유(작성자 출력은 false)", owned=True)
        return self


def loc_lines(page: TopicPage) -> list[str]:
    """위치 이름이 붙은 줄(번호 0부터, 5.3). 검수자·수정이 위치를 1부터 세던 문제를 입력에서 막는다."""
    out = [f"title: {page.title}", f"summary: {page.summary}"]
    out += [f"head_tiles[{i}]: {t.value} / {t.label} ({t.note}) (refs {', '.join(t.refs)})" for i, t in enumerate(page.head_tiles)]
    for i, s in enumerate(page.sections):
        out.append(f"sections[{i}].heading: {s.heading}" + (" [확인 필요]" if s.check else ""))
        out += [f"sections[{i}].paragraphs[{j}]: {p.text} (refs {', '.join(p.refs)})" for j, p in enumerate(s.paragraphs)]
        if s.bars is not None:
            g = s.bars
            out.append(f"sections[{i}].bars (단위 {g.unit}): {g.title} / context: {g.context}")
            out += [f"sections[{i}].bars.items[{k}]: {it.label} = {it.value} ({it.ref})" + (" [기준]" if it.baseline else "")
                    + (" [강조]" if it.emphasis else "") for k, it in enumerate(g.items)]
        if s.table is not None:
            t = s.table
            out.append(f"sections[{i}].table ({'/'.join(t.columns)}): {t.title} / note: {t.note}")
            out += [f"sections[{i}].table.rows[{k}]: {' | '.join(row)}" for k, row in enumerate(t.rows)]
        if s.visual == "tiles":
            out += [f"sections[{i}].tiles[{k}]: {t.value} / {t.label} ({t.note})" for k, t in enumerate(s.tiles)]
        if s.events is not None:
            g = s.events
            out.append(f"sections[{i}].events{' (흐름이 핵심)' if g.flow_is_point else ''}: {g.title} / context: {g.context}")
            out += [f"sections[{i}].events.items[{k}]: {it.date} {it.text} ({'ref ' + it.ref if it.ref else 'topic ' + it.topic_id if it.topic_id else '근거 없음'})"
                    for k, it in enumerate(g.items)]
        if s.slide:
            out.append(f"sections[{i}].slide: {s.slide} ({s.slide_caption})")
        if s.video_secs:
            out.append(f"sections[{i}].video_secs: {s.video_secs}")
    return out


# ---------- writer_revise (작성자 수정: 고친 칸만, v2 위치 문법) ----------
# 검수자 이슈 7종 + format(코드 검사 반려: 분량, 필수 칸, 금지 표현, 시각 요소 칸 규칙)
IssueType = Literal["unsupported", "number_mismatch", "overclaim", "wrong_ref", "missing_key", "overuse",
                    "missing_diagram", "format"]


class Issue(_Strict):
    loc: str = Field(description="위치(예: sections[1].paragraphs[0], sections[0].bars.items[1], summary)")
    type: IssueType
    evidence_id: str | None
    comment: str
    hint: str


class IndexedIssue(Issue):
    idx: int


class WriterReviseInput(RoleInput):
    RENDER_LINES: ClassVar[tuple[str, ...]] = ("loc_lines",)
    RENDER_SKIP: ClassVar[tuple[str, ...]] = ("previous",)  # loc_lines와 같은 내용이라 렌더하지 않음(코드는 객체를 씀)

    loc_lines: list[str] = Field(default_factory=list, description="previous 페이지의 모든 칸을 위치 이름(loc)이 붙은 줄로 펼친 것")
    previous: TopicPage
    issues: list[IndexedIssue]
    evidence: list[Document] = Field(description="지적된 칸의 근거 원문만")
    aliases: list[AliasLine]


class Change(_Strict):
    issue_idx: int
    loc: str
    action: Literal["edit", "delete", "add"]
    value: str | Para | Tile | BarGroup | Table | EventGroup | NumberItem | EventItem | Section | list[str] | list[int] | None = Field(
        description="그 위치의 새 값(writer와 같은 칸 형식, 하위 위치면 그 항목·글자). delete면 null. "
                     "sections 전체 add/delete 허용(sections[i]), sections 전체 삭제는 거부")


class TopicPageRevision(RoleOutput):
    changed: list[Change]


# ---------- critic (검수자) ----------
class CriticInput(RoleInput):
    RENDER_LINES: ClassVar[tuple[str, ...]] = ("loc_lines",)
    RENDER_SKIP: ClassVar[tuple[str, ...]] = ("page",)  # loc_lines와 같은 내용이라 렌더하지 않음(코드는 객체를 씀)

    loc_lines: list[str] = Field(default_factory=list, description="page의 모든 칸을 위치 이름(loc)이 붙은 줄로 펼친 것. 이슈 loc은 이 이름 그대로")
    page: TopicPage
    evidence: list[Document] = Field(description="이 토픽의 근거 원문(refs가 가리키는 것 먼저, 카드 요약 id 제외)")
    angle: str
    previous: PreviousTopic | None = Field(default=None, description="후속 토픽이면 지난 토픽(요약·절 제목). 지난 토픽을 말하는 문장은 이것과 대조")
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
