"""레포 도구(github_repo, recent_commits, contributors, releases) 실제 GitHub API 응답 녹화(설계 결정 Q3).

사용: uv run python scripts/record_repo_tools.py owner/name [owner/name ...] [--today YYYY-MM-DD]
결과: tests/fixtures/http/repo_tools/index.json에 recorded: true로 **추가**(이미 있는 URL은 건너뜀, 합성 응답 유지) + 본문 gzip
- 도구 함수를 그대로 불러 도구가 실제로 보내는 URL(commits?since=…)을 녹화한다. today는 테스트와 같은 날짜로 고정
- GITHUB_TOKEN이 있으면 붙여 부른다(한도). 요청 헤더는 저장하지 않고, 본문·location의 비밀 값은 redact_secrets로 지운다
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import httpx

from trendsit.collect.fetch import Fetcher
from trendsit.core.config import get_secret, redact_secrets
from trendsit.tools.github import CommitsArgs, RepoArgs, contributors, github_repo, recent_commits, releases

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "http" / "repo_tools"


class Recorder(httpx.BaseTransport):
    def __init__(self) -> None:
        self.inner = httpx.HTTPTransport()
        self.records: list[dict] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        resp = self.inner.handle_request(request)
        body = resp.read()
        self.records.append({"url": str(request.url), "status": resp.status_code,
                             "content_type": resp.headers.get("content-type", ""),
                             "location": resp.headers.get("location"), "body": body})
        headers = [(k, v) for k, v in resp.headers.items()
                   if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")]
        return httpx.Response(resp.status_code, headers=headers, content=body, request=request)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repos", nargs="+")
    ap.add_argument("--today", default="2026-10-08")
    a = ap.parse_args()
    rec = Recorder()
    token = get_secret("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
               **({"Authorization": f"Bearer {token}"} if token else {})}
    state = SimpleNamespace(extras={"fetcher": Fetcher(None, use_cache=False, transport=rec),
                                    "github_headers": headers, "today": date.fromisoformat(a.today)})
    for name in a.repos:
        for fn, args in ((github_repo, RepoArgs(name=name)), (recent_commits, CommitsArgs(name=name, days=7)),
                         (contributors, RepoArgs(name=name)), (releases, RepoArgs(name=name))):
            try:
                out = fn(args, state)
                print(f"{name} {fn.__name__}: {json.dumps(out.content, ensure_ascii=False)[:160]}")
            except Exception as e:  # 형식 차이(빈 레포 409 등)는 녹화해 두고 리포트에
                print(f"{name} {fn.__name__}: 오류 {type(e).__name__}: {e}")
    idx_path = OUT / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8"))
    for r in rec.records:
        if r["url"] in index:
            print(f"건너뜀(이미 있음): {r['url']}")
            continue
        fname = hashlib.sha1(r["url"].encode()).hexdigest()[:20] + ".gz"
        (OUT / fname).write_bytes(gzip.compress(redact_secrets(r["body"]), mtime=0))
        loc = r["location"] and redact_secrets(r["location"].encode()).decode()
        index[r["url"]] = {"file": fname, "status": r["status"], "content_type": r["content_type"],
                           "location": loc, "recorded": True}
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
