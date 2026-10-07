"""repo_oneliner 픽스처 생성: GitHub API로 README를 한 번 받아 저장(이후 네트워크 없이 재현).

사용: uv run python scripts/fetch_fixtures.py   (GITHUB_TOKEN이 있으면 사용, 없으면 비인증)
이미 있는 픽스처는 덮어쓰지 않는다(--force로 덮어씀). expect와 note는 아래 표에서 온다.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import httpx

from trendsit.core.config import get_secret

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "fixtures" / "repo_oneliner"
README_HEAD = 3000

# (레포, 성격, 반드시 들어갈 핵심어 후보(하나 이상), README 빈 레포 여부)
REPOS = [
    ("ollama/ollama", "추적 레포: 로컬 LLM 실행 환경", ["LLM", "모델", "언어 모델"], False),
    ("NousResearch/hermes-agent", "추적 레포: 에이전트", ["에이전트", "agent", "Agent"], False),
    ("openai/codex", "추적 레포: 코딩 에이전트", ["코딩", "코드"], False),
    ("anthropics/claude-code", "추적 레포: 코딩 에이전트", ["코딩", "코드"], False),
    ("encode/httpx", "라이브러리", ["HTTP"], False),
    ("excalidraw/excalidraw", "앱", ["화이트보드", "다이어그램", "드로잉", "스케치", "그림"], False),
    ("punkpeye/awesome-mcp-servers", "목록류 awesome-*", ["MCP"], False),
    ("fastapi/full-stack-fastapi-template", "템플릿", ["템플릿"], False),
    ("kakao/khaiii", "한국어 README 라이브러리", ["형태소"], False),
    ("Python3WebSpider/Images360", "README가 거의 빈 레포(제목 + 한 줄)", ["이미지"], True),
]


def main() -> None:
    force = "--force" in sys.argv
    token = get_secret("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url="https://api.github.com", headers=headers, timeout=30) as gh:
        for full_name, kind, must, empty in REPOS:
            path = OUT / f"{full_name.replace('/', '__')}.json"
            if path.exists() and not force:
                print(f"건너뜀(있음): {path.name}")
                continue
            meta = gh.get(f"/repos/{full_name}").raise_for_status().json()
            r = gh.get(f"/repos/{full_name}/readme", headers={"Accept": "application/vnd.github.raw"})
            if r.status_code not in (200, 404):  # 404만 "README 없음". 한도 초과(403) 등은 멈춤
                r.raise_for_status()
            readme = r.text if r.status_code == 200 else ""
            expect = {"max_len": 60, "must_include_any": must}
            if empty:
                expect["attention"] = True
            fixture = {
                "input": {
                    "full_name": full_name,
                    "description": meta.get("description"),
                    "topics": meta.get("topics") or [],
                    "readme_head": readme[:README_HEAD],
                },
                "expect": expect,
                "note": f"{kind}. README {len(readme)}자 중 앞 {min(len(readme), README_HEAD)}자. "
                        f"수집 {date.today()}, 레포 최근 push {meta.get('pushed_at', '')[:10]}",
            }
            path.write_text(json.dumps(fixture, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"저장: {path.name} (README {len(readme)}자)")


if __name__ == "__main__":
    main()
