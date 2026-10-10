"""S2~S3 글 쪽 스키마: 글 1차 요약(ItemCard v1), 이후 단계의 ItemCard v2, 편집장 계획(CollectionPlan, 영상 처리 지시).

COMMON 9장: 스펙별 파일. core/artifacts.py는 끝의 _merge 줄로 INPUTS, OUTPUTS만 합친다.
첫머리에서 선택 의존성(numpy, torch 등)을 import하지 않는다.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal, Self

from pydantic import BaseModel, ConfigDict, Field

from .artifacts import Document, RoleInput, RoleOutput, register_schemas

if TYPE_CHECKING:
    from .context import Ctx


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def squash(text: str) -> str:
    """공백 정리(줄바꿈, 연속 공백을 한 칸으로). 인용 대조의 기준."""
    return " ".join((text or "").split())


_NUM = re.compile(r"\d+(?:[.,]\d+)*")
_NUM_WORDS = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight",
              "9": "nine", "10": "ten"}


def number_in(n: str, text: str, words: bool = False) -> bool:
    """숫자 n(쉼표 없음)이 text에 독립된 수로 있는지. words면 영어 수 단어 one~ten도 같은 것으로."""
    if re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", (text or "").replace(",", "")):
        return True
    w = _NUM_WORDS.get(n) if words else None
    return bool(w and re.search(rf"\b{w}\b", text or "", re.I))


def scaled_in(n: str, text: str, src: str) -> bool:
    """한국어 큰 단위가 붙은 수('100만')를 값으로 비교: 인용이 'per million'이면 같은 수(S5 1단계 오탐 수정)."""
    from .numbers import number_values, same

    m = re.search(rf"(?<![\d.]){re.escape(n)}(?=\s*(천만|백만|천억|[천만억조]))", (text or "").replace(",", ""))
    if not m:
        return False
    vals = [v for v in number_values(m.group() + m.group(1)) if v != float(n)]
    return any(same(v, w) for v in vals for w in number_values(src))


def numbers(text: str) -> list[str]:
    """글 속 숫자 전부(쉼표 없앰). item_card 요약·주장 대조(PR #6 리뷰 R2)."""
    return [m.group().replace(",", "") for m in _NUM.finditer(text or "")]


def figures(text: str) -> list[str]:
    """대조할 수치만: %·배·x가 붙은 수, 소수, 네 자리 이상 정수(연도 제외).
    모델·버전 이름(GPT-6, v1.1), 한국어 큰 단위(2억8000만), 작은 개수(6개)는 표기가 달라 대조하지 않는다(리뷰 R3)."""
    out = []
    for m in _NUM.finditer(text or ""):
        n, before, after = m.group().replace(",", ""), text[m.start() - 1:m.start()], text[m.end():m.end() + 1]
        if before.isalpha() or before in ("-", "_") or after in ("만", "억", "천", "조"):
            continue
        if after in ("%", "배", "x", "×") or "." in n or (len(n) >= 4 and not re.fullmatch(r"(19|20)\d\d", n)):
            out.append(n)
    return out


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


QUOTE_CHARS = 200  # 인용 길이(역할 md 지시, enforce가 자름). 설계 결정 Q6
QUOTE_SCHEMA_MAX = 1000  # 모델용 스키마 안전 상한. 이보다 짧으면 스키마 오류로 다시 묻지 않는다
QUOTE_CLIP_RULE = f"{QUOTE_CHARS}자 넘는 인용을 본문 연속 구간으로 자름"


def clipped_quotes(enforced: list[dict]) -> int:
    """enforce 기록에서 긴 인용 자르기로 바뀐 인용 수."""
    return sum(1 for e in enforced if e["rule"] == QUOTE_CLIP_RULE
               for b, a in zip(e["before"], e["after"], strict=False) if b["text"] != a["text"])


class Quote(Strict):
    n: int = Field(ge=1, description="인용 번호(1부터). 근거 id는 it:{item_id}#q{n}")
    text: str = Field(max_length=QUOTE_SCHEMA_MAX, description="본문 문장을 한 글자도 바꾸지 않고 그대로. 200자 이내")


def clip_quote(text: str, values: list[str], limit: int = QUOTE_CHARS) -> str:
    """limit자를 넘는 인용을 연속 부분 문자열로 자른다(설계 결정 Q6). 공백에서 자르고 말줄임 기호는 붙이지 않는다.

    values(이 인용을 가리키는 수치)가 모두 들어가는 구간 중 가장 앞의 것, 없으면 앞에서부터.
    공백 없이 limit자를 넘는 한 덩어리뿐이면 글자 단위로 앞에서 자른다.
    """
    text = squash(text)
    if len(text) <= limit:
        return text
    words = text.split(" ")
    starts = [0]
    for w in words[:-1]:
        starts.append(starts[-1] + len(w) + 1)
    windows = []
    for i in range(len(words)):
        j = i
        while j + 1 < len(words) and starts[j + 1] + len(words[j + 1]) - starts[i] <= limit:
            j += 1
        if starts[j] + len(words[j]) - starts[i] <= limit:
            windows.append(text[starts[i]:starts[j] + len(words[j])])
    need = [squash(v) for v in values if squash(v)]
    for w in windows:
        if all(v in w for v in need):
            return w
    return windows[0] if windows else text[:limit]


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
    # 설계 결정 Q1. 칸 단위 코드 소유는 attention뿐. 긴 인용 자르기(Q6)도 코드 소유지만 quotes 칸 전체를 코드 소유로 둘 수
    # 없어(본문에 없는 인용 삭제는 품질 정리) fix(owned=True)로만 표시한다. 통과 판정 보기(graders.basis_output)는 quotes를
    # 원래 출력으로 보는데, 채점기에 인용 길이 검사가 없어 결과는 결정과 같다(PR #6 리뷰 R5)
    ENFORCED_FIELDS = ("attention",)
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
        out = self.clip_quotes(body)
        kept = [q for q in out.quotes if squash(q.text) and squash(q.text) in body]
        if len(kept) != len(out.quotes):
            out = out.fix("quotes", kept, "본문에 없는 인용 삭제")
        ok_n = {q.n: squash(q.text) for q in kept}
        before_nums = out.numbers
        nums = [x for x in before_nums if x.quote_n in ok_n and squash(x.value) and squash(x.value) in ok_n[x.quote_n]]
        if len(nums) != len(before_nums):
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
        if len(kept) != len(self.quotes) or len(nums) != len(before_nums):
            out = out.fix("attention", True, "인용·수치 정리가 있어 사람 확인")
        if out.numbers_outside_quotes(inp.title):
            out = out.fix("attention", True, "요약·주장의 숫자가 인용(제목)에 없음")
        return out

    def numbers_outside_quotes(self, title: str = "") -> list[str]:
        """summary·claims의 숫자 중 quotes와 제목에 없는 것(영어 수 단어 one~ten 허용). PR #6 리뷰 R2."""
        src = " ".join([title, *(q.text for q in self.quotes)])
        return [n for t in [self.summary, *(c.text for c in self.claims)] for n in numbers(t)
                if not number_in(n, src, words=True) and not scaled_in(n, t, src)]

    def clip_quotes(self, body: str) -> Self:
        """본문에 있는 QUOTE_CHARS자 초과 인용을 자르고, 잘려 나간 수치를 지운다(설계 결정 Q6, 코드 소유. attention 없음)."""
        quotes, cut = [], {}  # cut: 인용 번호 → (원래, 자른 것)
        for q in self.quotes:
            t = squash(q.text)
            if len(t) > QUOTE_CHARS and t in body:
                short = clip_quote(t, [x.value for x in self.numbers if x.quote_n == q.n])
                quotes.append(q.model_copy(update={"text": short}))
                cut[q.n] = (t, short)
            else:
                quotes.append(q)
        if not cut:
            return self
        out = self.fix("quotes", quotes, QUOTE_CLIP_RULE, owned=True)

        def lost(x: NumberFact) -> bool:  # 원래 인용에는 있었는데 잘려 나간 수치만(모델이 틀린 수치는 품질 정리로)
            v = squash(x.value)
            return x.quote_n in cut and bool(v) and v in cut[x.quote_n][0] and v not in cut[x.quote_n][1]

        nums = [x for x in self.numbers if not lost(x)]
        if len(nums) != len(self.numbers):
            out = out.fix("numbers", nums, "자른 인용 밖으로 나간 수치 삭제", owned=True)
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
    rank: int | None = None
    stars_this_week: int | None = None
    stars_total: int | None = None
    forks: int | None = None
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
    ENFORCED_FIELDS = ("attention",)  # 설계 결정 Q1. 없는 id·중복, 깊이, 예산 꼬리 자르기는 품질 정리
    text_queue: list[TextQueueItem] = Field(description="원본을 추적할 글, 우선순위 순서")
    video_queue: list[VideoQueueItem] = Field(description="영상 처리 지시, 우선순위 순서")
    repo_queue: list[RepoQueueItem] = Field(description="깊게 볼 레포, 우선순위 순서")

    def enforce(self, inp: PlanInput, ctx: Ctx | None) -> Self:
        from ..deep.plan import validate_plan

        return validate_plan(self, inp)


# ---------- 글 분석가 (text_analyst, S3 3b) ----------
def norm_url(url: str) -> str:
    """깊이 추적과 대조의 문서 id(추적 파라미터, 조각, 끝 슬래시 정리)."""
    from ..collect.links import normalize_url

    return normalize_url(url)


def page_key(url: str) -> str:
    """가져온 문서 대조 열쇠: 정규화 URL + github.com은 소문자, arxiv는 https·버전 없는 abs 주소."""
    import re

    u = norm_url(url).replace("http://", "https://", 1)
    if u.startswith("https://github.com/"):
        return u.lower()
    m = re.match(r"https://(?:export\.)?arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(v\d+)?", u)
    return f"https://arxiv.org/abs/{m.group(1)}" if m else u


class CheckItem(Strict):
    n: int = Field(description="확인할 것 번호(verified의 check_n)")
    kind: Literal["number", "claim"]
    text: str = Field(description="요약 글의 수치·주장")
    quote: str = Field(description="요약 글에서 그 수치·주장이 나온 문장")


class ArticleLink(Strict):
    n: int
    url: str
    kind: str | None = None
    anchor: str | None = None
    candidate: bool = Field(description="1차 요약이 원본 후보로 고른 링크")


class TextAnalystInput(RoleInput):
    item_id: int
    title: str
    source_name: str
    url: str = Field(description="원래 글 URL(이미 읽음, 깊이 1)")
    max_depth: int = Field(ge=1, le=4, description="편집장 계획의 항목별 깊이 상한")
    card_v1: ItemCardV1
    links: list[ArticleLink] = Field(description="원래 글의 링크(종류 표시). 원본 후보는 candidate=true")
    checks: list[CheckItem] = Field(description="원본과 대조할 수치·주장(코드가 v1에서 뽑음)")

    tool_calls: int | None = Field(default=None, ge=1, description="항목당 도구 호출 상한(deep.yaml text_tool_calls_per_item)")

    def tool_call_limit(self, default: int | None) -> int | None:
        return self.tool_calls or default

    def depth_limit(self, default: int | None) -> int | None:
        from .config import MAX_DEPTH_ALL

        return min(self.max_depth, default or MAX_DEPTH_ALL, MAX_DEPTH_ALL)

    def depth_seed(self) -> list[tuple[str, list[str]]]:
        return [(norm_url(self.url), [norm_url(x.url) for x in self.links])]


class TrailStep(Strict):
    url: str
    depth: int = Field(ge=1)
    reason: str = Field(description="왜 이 페이지로 갔는지 한 줄(예: 'GeekNews → 공식 블로그: 수치 출처')")


class OriginQuote(Strict):
    n: int = Field(ge=1, description="근거 id og:{item_id}#q{n}")
    url: str = Field(description="이 문장을 가져온 페이지 URL(fetch_page·arxiv·github_repo로 연 것)")
    text: str = Field(max_length=300, description="원본 문장을 한 글자도 바꾸지 않고 그대로")


class Verified(Strict):
    check_n: int
    quote_n: int | None = Field(description="대조에 쓴 원본 quote 번호. 못 찾았으면 null")
    status: Literal["confirmed", "differs", "not_found"]


class Origin(Strict):
    url: str
    kind: Literal["paper", "official_doc", "official_blog", "press", "repo", "news", "curation", "other"]
    title: str
    date: str | None = None


PARTIAL_RULE = "부분 확인: check 수치가 인용에 없음 → not_found"


class ItemCardV2(RoleOutput):
    ENFORCED_FIELDS = ("attention",)  # 설계 결정 Q1. 근거 없는 판정, 연 적 없는 페이지 인용, trail 밖 origin은 품질 정리
    trail: list[TrailStep] = Field(description="거쳐 간 페이지(순서대로)")
    quotes: list[OriginQuote] = Field(max_length=8, description="원본에서 옮긴 문장. 결론보다 먼저")
    verified: list[Verified] = Field(description="checks마다 confirmed / differs / not_found")
    differences: list[str] = Field(description="요약 글과 원본이 다른 점(예: 요약 '10배', 원본 '최대 10배')")
    origin: Origin | None = Field(description="찾은 1차 자료. 못 찾았으면 null")
    numbers: list[NumberFact] = Field(description="원본 quote에 있는 수치만")
    claims: list[Claim]
    summary: str = Field(max_length=400, description="원본 기준 2~3문장. 원본을 못 찾았으면 v1 요약 그대로")

    @classmethod
    def fallback(cls, reason: str, inp: TextAnalystInput) -> Self:
        """v1 유지 + "원본 찾지 못함"(attention 아님)."""
        v1 = inp.card_v1
        return cls(trail=[], quotes=[], verified=[Verified(check_n=c.n, quote_n=None, status="not_found")
                                                  for c in inp.checks],
                   differences=[], origin=None, numbers=[], claims=[], summary=v1.summary,
                   log=f"원본 찾지 못함({reason})", attention=False)

    def enforce(self, inp: TextAnalystInput, ctx: Ctx | None) -> Self:
        """이번 실행에서 실제로 가져온 페이지 본문에 있는 인용만 근거로 인정(S2S3_TASK 5.5)."""
        res = ctx.resources if ctx is not None else {}
        pages: dict[str, str] = res.get("fetched_pages") or {}
        depths: dict[str, int] = res.get("page_depth") or {}
        bodies = {page_key(u): squash(t) for u, t in pages.items()}
        out = self
        # trail은 실제로 연 문서만, 깊이는 코드가 센 값으로(모델이 쓴 값을 믿지 않음)
        trail = [t.model_copy(update={"depth": depths.get(page_key(t.url), t.depth)}) for t in self.trail
                 if page_key(t.url) in bodies]
        if trail != self.trail:
            out = out.fix("trail", trail, "연 적 없는 문서 삭제, 깊이는 코드가 센 값")
        kept = [q for q in self.quotes
                if squash(q.text) and squash(q.text) in bodies.get(page_key(q.url), "")]
        if len(kept) != len(self.quotes):
            out = out.fix("quotes", kept, "가져온 페이지에 없는 인용 삭제")
        ok = {q.n for q in kept}
        ver = [v if v.status == "not_found" or (v.quote_n is not None and v.quote_n in ok)
               else v.model_copy(update={"status": "not_found", "quote_n": None}) for v in self.verified]
        if ver != self.verified:
            out = out.fix("verified", ver, "confirmed/differs인데 근거 인용이 없거나 가져온 페이지에 없음 → not_found")
        nums = [x for x in self.numbers if x.quote_n in ok]
        if nums != self.numbers:
            out = out.fix("numbers", nums, "없는 인용을 가리키는 수치 삭제")
        claims = [c.model_copy(update={"quote_ns": [n for n in c.quote_ns if n in ok]}) for c in self.claims
                  if any(n in ok for n in c.quote_ns)]
        if claims != self.claims:
            out = out.fix("claims", claims, "없는 인용을 가리키는 주장 정리")
        if self.origin is not None and page_key(self.origin.url) not in bodies:
            out = out.fix("origin", None, "origin.url을 이번 실행에서 열지 않음")
        out = out.demote_partial(inp)
        if any(v.status == "differs" for v in out.verified) and not out.attention:
            out = out.fix("attention", True, "원본과 다른 점(differs)이 있어 사람 확인")
        return out

    def demote_partial(self, inp: TextAnalystInput) -> Self:
        """confirmed인데 check 문장의 수치가 인용에 없으면 부분 확인으로 보고 not_found(PR #6 리뷰 R3).
        differs는 그대로 둔다(요약과 원본 수치가 다르다는 판정이라 check 수치가 인용에 없는 것이 정상).
        가져온 페이지 없이 출력과 입력만 보므로 eval --regrade가 저장된 출력에 다시 적용할 수 있다."""
        checks = {c.n: c.text for c in inp.checks}
        quoted = " ".join(q.text for q in self.quotes)
        ver = [v if v.status != "confirmed" or all(number_in(n, quoted) for n in figures(checks.get(v.check_n, "")))
               else v.model_copy(update={"status": "not_found", "quote_n": None}) for v in self.verified]
        return self.fix("verified", ver, PARTIAL_RULE) if ver != self.verified else self


INPUTS = (ItemCardInput, PlanInput, TextAnalystInput)
OUTPUTS = (ItemCardV1, CollectionPlan, ItemCardV2)
register_schemas("artifacts_text", INPUTS, OUTPUTS)
