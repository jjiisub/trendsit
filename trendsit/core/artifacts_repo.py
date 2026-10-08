"""S3 3c 레포 분석가 스키마: RepoAnalystInput, RepoCard. COMMON 9장: 스펙별 파일(artifacts.py는 합치기만)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Self

from pydantic import BaseModel, ConfigDict, Field

from .artifacts import RoleInput, RoleOutput, register_schemas

if TYPE_CHECKING:
    from .context import Ctx

# 깊이별 허용 도구(코드). 3은 MVP에서 2와 같음(연결 문서 도구는 이후)
DEPTH_TOOLS = {1: ("github_repo", "search_items"),
               2: ("github_repo", "search_items", "recent_commits", "contributors", "releases")}
DEPTH_TOOLS[3] = DEPTH_TOOLS[2]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TrendingStats(Strict):
    week: str
    rank: int | None = None
    stars_total: int | None = None
    stars_this_week: int | None = None
    forks: int | None = None
    language: str | None = None
    description: str | None = None


class HypeCheck(Strict):
    """입력 조립 때 코드가 계산한 과열 규칙 결과(enforce가 고정)."""

    flags: list[str] = Field(description="no_commits(7일 별 급증인데 커밋 0), single_contributor, awesome_list")
    force_check: bool = Field(description="true면 signal=check로 고정")
    commits_7d: int | None = None
    contributors: int | None = None
    note: str = ""


class ItemTitle(Strict):
    id: str = Field(description="it:{item_id}")
    title: str


class RepoAnalystInput(RoleInput):
    full_name: str
    max_depth: int = Field(ge=1, le=3, description="1 = 저장소 정보와 칠판 검색만 / 2 = 커밋, 기여자, 릴리스까지")
    reason: str = Field(description="이 레포를 보게 된 이유(큐)")
    trending: TrendingStats | None = None
    oneliner: str = Field(description="repo_oneliner 결과(코드가 카드에 붙임, 다시 쓰지 않음)")
    keywords: list[str] = Field(description="관심 키워드 이름")
    week_items: list[ItemTitle] = Field(description="이번 주 ItemCard 제목(최대 30)")
    hype: HypeCheck

    tool_calls: int | None = Field(default=None, ge=1, description="항목당 도구 호출 상한(deep.yaml repo_tool_calls_per_item)")

    def tool_call_limit(self, default: int | None) -> int | None:
        return self.tool_calls or default

    def tool_names(self, names: list[str]) -> list[str]:
        allowed = DEPTH_TOOLS[min(self.max_depth, 3)]
        return [n for n in names if n in allowed]


class Evidence(Strict):
    fact: str = Field(description="도구 결과에서 옮긴 사실 한 줄(수치는 결과 그대로)")
    tool: str = Field(description="그 사실이 나온 도구 이름")


class Release(Strict):
    tag: str
    date: str
    line: str = Field(description="릴리스 내용 한 줄(명사형)")


Signal = Literal["trending", "rising", "release", "check"]


class RepoCard(RoleOutput):
    evidence: list[Evidence] = Field(description="도구 결과에서 확인한 사실. 가장 먼저 채움")
    relevant_reason: str = Field(description="관심 키워드와의 관련성 판단 이유 한 줄")
    relevant: bool
    why_trending: str = Field(description="근거 있는 뜨는 이유(릴리스, 글 언급 등). 근거 없으면 빈 문자열")
    hype_flags: list[str] = Field(description="과열 신호(no_commits, single_contributor, awesome_list, template_clone)")
    release: Release | None = Field(description="이번 주 릴리스가 확인되면. 없으면 null")
    related_item_ids: list[str] = Field(description="입력 week_items의 id 중 이 레포를 다룬 글")
    signal_reason: str = Field(description="신호 판단 이유 한 줄")
    signal: Signal

    @classmethod
    def fallback(cls, reason: str, inp: RepoAnalystInput) -> Self:
        """트렌딩 설명으로 대체, signal은 숫자 규칙(과열이면 check, 이번 주 별이 있으면 trending)."""
        signal: Signal = "check" if inp.hype.force_check else "trending"
        return cls(evidence=[], relevant_reason=f"대체 출력: {reason}", relevant=False, why_trending="",
                   hype_flags=list(inp.hype.flags), release=None, related_item_ids=[],
                   signal_reason="숫자 규칙(대체 출력)", signal=signal,
                   log=f"{inp.full_name}: 대체 출력({reason})", attention=True)

    def enforce(self, inp: RepoAnalystInput, ctx: Ctx | None) -> Self:
        out = self
        allowed = {x.id for x in inp.week_items}
        rel = [i for i in self.related_item_ids if i in allowed]
        if rel != self.related_item_ids:
            out = out.fix("related_item_ids", rel, "입력에 없는 글 id 삭제")
        flags = list(dict.fromkeys([*inp.hype.flags, *out.hype_flags]))
        if flags != out.hype_flags:
            out = out.fix("hype_flags", flags, "코드 과열 규칙 플래그 고정")
        if inp.hype.force_check and out.signal != "check":
            out = out.fix("signal", "check", "7일 별 급증 + 커밋 0이면 check(코드)")
        if out.signal == "check" and not out.attention:
            out = out.fix("attention", True, "check 신호는 사람 확인")
        if not out.evidence and out.why_trending.strip() and not out.attention:
            out = out.fix("attention", True, "근거(evidence) 없이 why_trending을 씀")
        return out


INPUTS = (RepoAnalystInput,)
OUTPUTS = (RepoCard,)
register_schemas("artifacts_repo", INPUTS, OUTPUTS)
