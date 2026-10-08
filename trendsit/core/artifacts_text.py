"""S2~S3 글 쪽 스키마: 글 1차 요약(ItemCard v1), 이후 단계의 ItemCard v2, 편집장 계획(CollectionPlan, 영상 처리 지시).

COMMON 9장: 스펙별 파일. core/artifacts.py는 끝의 _merge 줄로 INPUTS, OUTPUTS만 합친다.
첫머리에서 선택 의존성(numpy, torch 등)을 import하지 않는다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Self

from pydantic import BaseModel, ConfigDict, Field

from .artifacts import Document, RoleInput, RoleOutput

if TYPE_CHECKING:
    from .context import Ctx


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def squash(text: str) -> str:
    """공백 정리(줄바꿈, 연속 공백을 한 칸으로). 인용 대조의 기준."""
    return " ".join((text or "").split())


# ---------- 글 1차 요약 (item_card, S2 2b) ----------
class LinkRef(Strict):
    n: int = Field(description="링크 번호(1부터). origin_candidates에 이 번호를 쓴다")
    url: str
    kind: str | None = Field(default=None, description="코드가 판별한 링크 종류(논문, 레포, 공식 블로그 등)")
    anchor: str | None = None
    role: Literal["body", "origin_candidate"] = Field(
        default="body", description="origin_candidate: 수집 단계에서 원문으로 알려진 링크(GeekNews 원문 등)")


class KeywordRef(Strict):
    id: str
    name: str


class ItemCardInput(RoleInput):
    item_id: int
    title: str
    source_name: str
    source_kind: str = Field(description="primary(공식) / news(언론) / curation(큐레이션, 개인 블로그 포함)")
    url: str | None = None
    body: Document  # id = it:{item_id}. 6,000자 상한(문단 경계에서 자름)
    links: list[LinkRef] = []
    keywords: list[KeywordRef] = []


class Quote(Strict):
    n: int = Field(ge=1, description="인용 번호(1부터). 근거 id는 it:{item_id}#q{n}")
    text: str = Field(max_length=200, description="본문 문장을 한 글자도 바꾸지 않고 그대로. 200자 이내")


class NumberFact(Strict):
    quote_n: int = Field(description="이 수치가 들어 있는 quote 번호")
    value: str = Field(description="quote 안에 있는 문자열 그대로(예: '35%', '1.2억 달러')")
    unit: str = Field(description="단위. 값에 포함됐으면 빈 문자열")
    what: str = Field(description="무엇의 수치인지 짧게(명사형)")


class Claim(Strict):
    quote_ns: list[int] = Field(min_length=1, description="이 주장을 뒷받침하는 quote 번호")
    text: str = Field(description="핵심 주장 한 줄(명사형)")


Relevance = Literal["high", "mid", "low"]


class ItemCardV1(RoleOutput):
    quotes: list[Quote] = Field(max_length=8, description="본문에서 그대로 옮긴 핵심 문장. 가장 먼저 채움")
    numbers: list[NumberFact] = Field(description="quote에 있는 수치만. 없으면 빈 목록")
    claims: list[Claim] = Field(description="핵심 주장. 각 주장은 quote 번호로 뒷받침")
    summary: str = Field(max_length=300, description="2~3문장, '~다' 평서체. quotes와 claims에 있는 내용만")
    entities: list[str] = Field(description="제품, 회사, 모델 이름(원문 표기)")
    keywords: list[str] = Field(description="입력 keywords 목록의 id 중 이 글에 해당하는 것만")
    is_curation: bool = Field(description="다른 글을 소개·요약하는 글이면 true(GeekNews, 뉴스레터, 링크 모음)")
    origin_candidates: list[int] = Field(description="원본(1차 자료)일 가능성이 있는 링크 번호")
    relevance_reason: str = Field(description="관련성 판단 이유 한 줄")
    relevance: Relevance
    needs_original_reason: str = Field(description="원본 확인 필요 판단 이유 한 줄")
    needs_original: bool = Field(description="수치·주장의 출처가 본문 밖 링크(원본)에 있어 원본을 봐야 하면 true")

    @classmethod
    def fallback(cls, reason: str, inp: ItemCardInput) -> Self:
        return cls(quotes=[], numbers=[], claims=[], summary="", entities=[], keywords=[], is_curation=False,
                   origin_candidates=[], relevance_reason=f"대체 출력: {reason}", relevance="low",
                   needs_original_reason="", needs_original=False, log=f"{inp.title[:40]}: 제목만 남김 ({reason})",
                   attention=True)

    def enforce(self, inp: ItemCardInput, ctx: Ctx | None) -> Self:
        """인용이 본문에 있는지, 수치가 인용에 있는지, 목록 밖 키워드·링크 번호를 코드가 정리한다(S2S3_TASK 5.2)."""
        body = squash(inp.body.text)
        out = self
        kept = [q for q in self.quotes if squash(q.text) and squash(q.text) in body]
        if len(kept) != len(self.quotes):
            out = out.fix("quotes", kept, "본문에 없는 인용 삭제")
        ok_n = {q.n: squash(q.text) for q in kept}
        nums = [x for x in self.numbers if x.quote_n in ok_n and squash(x.value) and squash(x.value) in ok_n[x.quote_n]]
        if len(nums) != len(self.numbers):
            out = out.fix("numbers", nums, "인용에 없는 수치 삭제")
        claims = []
        for c in self.claims:
            ns = [n for n in c.quote_ns if n in ok_n]
            if ns:
                claims.append(c if ns == c.quote_ns else c.model_copy(update={"quote_ns": ns}))
        if claims != self.claims:
            out = out.fix("claims", claims, "없는 인용 번호를 가리키는 주장 정리")
        allowed = {k.id for k in inp.keywords}
        kws = [k for k in self.keywords if k in allowed]
        if kws != self.keywords:
            out = out.fix("keywords", kws, "입력 목록 밖 키워드 삭제")
        link_ns = {x.n for x in inp.links}
        origins = [n for n in self.origin_candidates if n in link_ns]
        if origins != self.origin_candidates:
            out = out.fix("origin_candidates", origins, "없는 링크 번호 삭제")
        if len(kept) != len(self.quotes) or len(nums) != len(self.numbers):
            out = out.fix("attention", True, "인용·수치 정리가 있어 사람 확인")
        return out


# ---------- 편집장 계획 (editor_plan, S3 3a) ----------
VideoMode = Literal["skip", "captions", "whisper", "whisper+slides"]


class VideoQueueItem(Strict):
    """영상 처리 지시(CONTRACTS 1장). S4 core/artifacts_video.py와 같은 모양(같은 JSON 픽스처로 테스트)."""

    reason: str = Field(description="왜 이 깊이인지 한 줄. 결정보다 먼저")
    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    mode: VideoMode
    start_sec: int | None = Field(default=None, ge=0, description="60분 넘는 영상의 처리 구간 시작. null이면 처음부터")
    end_sec: int | None = Field(default=None, ge=0, description="null이면 최대 60분")


class TextQueueItem(Strict):
    reason: str = Field(description="왜 원본을 추적하는지, 왜 이 깊이인지 한 줄")
    item_id: int
    max_depth: int = Field(ge=1, le=4)


class RepoQueueItem(Strict):
    reason: str
    full_name: str
    max_depth: int = Field(ge=1, le=3)


class VideoCandidate(Strict):
    video_id: str
    item_id: int
    title: str
    duration_min: float | None = None
    manual_sub_langs: list[str] = []
    has_auto_sub: bool | None = None
    description_head: str = ""
    published: str | None = None
    chapters: int = 0


class RepoCandidate(Strict):
    full_name: str
    stars_this_week: int | None = None
    stars_total: int | None = None
    language: str | None = None
    description: str | None = None
    tracked_release: str | None = Field(default=None, description="추적 레포 릴리스 제목(있으면)")
    hype_flags: list[str] = []
    force_check: bool = False


class TextCandidate(Strict):
    item_id: int
    title: str
    source: str
    relevance: Relevance
    needs_original_reason: str
    origin_link_kinds: list[str] = Field(description="원본 후보 링크 종류(논문, 공식 블로그, 레포 등)")


class PlanBudget(Strict):
    video_minutes: int
    slide_videos: int
    vlm_frames: int
    frames_per_slide_video: int
    text_items: int
    text_tool_calls_per_item: int
    repo_items: int
    default_text_depth: int
    max_text_depth: int
    plan_share: float
    video_max_minutes: int


class PlanInput(RoleInput):
    day: str
    new_videos: list[VideoCandidate]
    repo_candidates: list[RepoCandidate]
    text_candidates: list[TextCandidate]
    keywords: list[str]
    budget: PlanBudget
    recent_topics: list[str] = []


class CollectionPlan(RoleOutput):
    text_queue: list[TextQueueItem] = Field(description="원본을 추적할 글, 우선순위 순서")
    video_queue: list[VideoQueueItem] = Field(description="영상 처리 지시, 우선순위 순서")
    repo_queue: list[RepoQueueItem] = Field(description="깊게 볼 레포, 우선순위 순서")

    @classmethod
    def fallback(cls, reason: str, inp: PlanInput) -> Self:
        from ..deep.plan import fallback_plan

        return fallback_plan(inp, reason)

    def enforce(self, inp: PlanInput, ctx: Ctx | None) -> Self:
        from ..deep.plan import validate_plan

        return validate_plan(self, inp)


INPUTS = (ItemCardInput, PlanInput)
OUTPUTS = (ItemCardV1, CollectionPlan)
