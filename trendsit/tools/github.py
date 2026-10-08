"""GitHub 도구(레포 분석가, 글 분석가). GitHub API를 safe_fetch로만 부른다. 결과는 모델에게 줄 짧은 사실 묶음.

자원: state.ctx.resources["fetcher"](없으면 만들어 넣음), ["github_headers"](토큰), ["today"](날짜 고정, 테스트용).
API 재시도: Fetcher가 429·5xx를 지수 백오프로 3회.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..core.textclean import clean_markdown
from .registry import ToolOutput, ToolRejected, tool

API = "https://api.github.com"
README_CHARS = 1500
NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def valid_name(name: str) -> bool:
    """owner/name. 경로 이동(., ..)은 거부(토큰을 붙인 채 다른 API 경로로 가지 않게)."""
    return bool(NAME.match(name)) and not any(p in (".", "..") for p in name.split("/"))


def resources(state: Any) -> dict[str, Any]:
    ctx = getattr(state, "ctx", None)
    res = ctx.resources if ctx is not None else getattr(state, "extras", {})
    if "fetcher" not in res:
        from ..collect.fetch import Fetcher

        res["fetcher"] = Fetcher(None, use_cache=False)
    if "github_headers" not in res:
        from ..core.config import get_secret

        token = get_secret("GITHUB_TOKEN")
        res["github_headers"] = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                                 **({"Authorization": f"Bearer {token}"} if token else {})}
    return res


def today(state: Any) -> date:
    return resources(state).get("today") or datetime.now(UTC).date()


def api_get(state: Any, path: str, *, raw: bool = False) -> tuple[int | None, Any]:
    res = resources(state)
    headers = dict(res["github_headers"])
    if raw:
        headers["Accept"] = "application/vnd.github.raw"
    r = res["fetcher"].fetch(f"{API}{path}", kind="api", headers=headers)
    if r.status == 404:
        return 404, None
    if not r.ok:
        raise ToolRejected(f"GitHub API 실패({path}): {r.error}")
    return r.status, (r.text if raw else json.loads(r.text or "null"))


class RepoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(description="owner/name 형식. 예: ollama/ollama")

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip().removeprefix("https://github.com/").strip("/")
        if not valid_name(v):
            raise ValueError("owner/name 형식이어야 함(., .. 불가)")
        return v


class CommitsArgs(RepoArgs):
    days: int = Field(default=7, ge=1, le=30, description="최근 며칠의 커밋을 셀지. 보통 7")


@tool(RepoArgs)
def github_repo(args: RepoArgs, state: Any) -> ToolOutput:
    """레포 기본 정보: 설명, 토픽, 별, 포크, 생성일, 마지막 push, 라이선스, README 앞부분(기호 정리).
    언제 쓰나: 레포가 무엇이고 관심사와 관련 있는지 처음 확인할 때. 한 레포에 한 번이면 충분하다.
    언제 쓰지 않나: 이미 같은 레포로 부른 뒤.
    인자 예: {"name": "ollama/ollama"}"""
    status, data = api_get(state, f"/repos/{args.name}")
    if status == 404 or not data:
        raise ToolRejected(f"없는 레포: {args.name}")
    _, readme = api_get(state, f"/repos/{args.name}/readme", raw=True)
    lic = (data.get("license") or {}).get("spdx_id")
    if readme:  # 글 분석가가 README 문장을 인용할 수 있게(enforce 대조 대상)
        res = getattr(getattr(state, "ctx", None), "resources", None)
        if res is not None and "fetched_pages" in res:
            from ..core.artifacts_text import page_key

            res["fetched_pages"][page_key(f"https://github.com/{args.name}")] = clean_markdown(readme)
    return ToolOutput(content={
        "full_name": data.get("full_name"), "description": data.get("description"), "topics": data.get("topics") or [],
        "stars": data.get("stargazers_count"), "forks": data.get("forks_count"), "language": data.get("language"),
        "created_at": data.get("created_at"), "pushed_at": data.get("pushed_at"), "license": lic,
        "archived": data.get("archived"), "is_template": data.get("is_template"), "fork": data.get("fork"),
        "readme_head": clean_markdown(readme or "")[:README_CHARS] or None})


@tool(CommitsArgs)
def recent_commits(args: CommitsArgs, state: Any) -> ToolOutput:
    """최근 며칠의 커밋 수, 작성자 수, 마지막 커밋(날짜, 메시지 첫 줄). 100개까지 센다.
    언제 쓰나: 별이 급증했는데 실제로 개발이 이어지는지(과열인지) 확인할 때.
    언제 쓰지 않나: README로 관심사와 관련이 낮다고 이미 판단했을 때.
    인자 예: {"name": "ollama/ollama", "days": 7}"""
    since = (datetime.combine(today(state), datetime.min.time(), UTC) - timedelta(days=args.days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    _, data = api_get(state, f"/repos/{args.name}/commits?since={since}&per_page=100")
    data = data or []
    authors = {((c.get("author") or {}).get("login") or (c.get("commit") or {}).get("author", {}).get("name"))
               for c in data}
    last = data[0] if data else None
    return ToolOutput(content={
        "days": args.days, "since": since, "commits": len(data) if len(data) < 100 else "100+",
        "authors": len(authors - {None}),
        "last_commit": None if last is None else {
            "date": ((last.get("commit") or {}).get("author") or {}).get("date"),
            "message": ((last.get("commit") or {}).get("message") or "").splitlines()[0][:120]}})


@tool(RepoArgs)
def contributors(args: RepoArgs, state: Any) -> ToolOutput:
    """기여자 수(100명까지 셈)와 상위 5명(이름, 커밋 수).
    언제 쓰나: 한 사람이 올린 레포인지, 여러 사람이 만드는지 확인할 때(과열 신호).
    언제 쓰지 않나: 관련성이 낮은 레포, 이미 recent_commits로 판단이 끝났을 때.
    인자 예: {"name": "ollama/ollama"}"""
    _, data = api_get(state, f"/repos/{args.name}/contributors?per_page=100&anon=1")
    data = data or []
    top = [{"name": c.get("login") or c.get("name") or "익명", "contributions": c.get("contributions")} for c in data[:5]]
    return ToolOutput(content={"total": len(data) if len(data) < 100 else "100+", "top": top})


@tool(RepoArgs)
def releases(args: RepoArgs, state: Any) -> ToolOutput:
    """최근 릴리스 5개: 태그, 날짜, 이름, 노트 앞 300자.
    언제 쓰나: 이번 주에 새 버전이 나와서 뜨는 것인지 확인할 때.
    언제 쓰지 않나: 관련성이 낮은 레포.
    인자 예: {"name": "ollama/ollama"}"""
    _, data = api_get(state, f"/repos/{args.name}/releases?per_page=5")
    out = [{"tag": r.get("tag_name"), "date": (r.get("published_at") or "")[:10], "name": r.get("name"),
            "notes_head": clean_markdown(r.get("body") or "")[:300]} for r in (data or [])]
    return ToolOutput(content={"releases": out} if out else {"releases": [], "note": "릴리스 없음"})
