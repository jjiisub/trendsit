# NVIDIA/OpenShell

- 큐 이유: 트렌딩 이번 주 별 3690, 키워드 agent, ai-industry, ai-general / max_depth 2
- 트렌딩: 순위 5, 전체 별 15340, 이번 주 별 3690, 포크 1729, 언어 Rust
- 과열 규칙(코드): {'flags': [], 'force_check': False, 'commits_7d': 86, 'contributors': 100, 'note': '7일 별 +3690, 커밋 86'}
- 한 줄 설명(repo_oneliner): 자율 AI 에이전트용 안전하고 격리된 런타임

## 도구 호출 경로

| # | 도구 | 인자 | 결과 |
|---|---|---|---|
| 1 | github_repo | name=NVIDIA/OpenShell | ok |
| 2 | releases | name=NVIDIA/OpenShell | ok |
| 3 | search_items | query=OpenShell | ok |
| 4 | recent_commits | name=NVIDIA/OpenShell, days=7 | ok |
| 5 | contributors | name=NVIDIA/OpenShell | ok |
| 6 | finish | 최종 답 제출 | ok |

## 출력 카드

```json
{
 "log": "NVIDIA/OpenShell: 에이전트 격리 런타임, 7일 커밋 86, 기여자 100+, 관련",
 "attention": false,
 "evidence": [
  {
   "fact": "README: OpenShell is the safe, private runtime for fleets of autonomous AI agents; kernel-level enforcement, formally verified policy changes",
   "tool": "github_repo"
  },
  {
   "fact": "v0.1.2 2026-09-28 릴리스 (docs: clarify sandbox-local loopback access 등)",
   "tool": "releases"
  },
  {
   "fact": "이번 주 글에 OpenShell 언급 없음",
   "tool": "search_items"
  },
  {
   "fact": "7일 커밋 86, 작성자 24, 마지막 커밋 2026-10-08",
   "tool": "recent_commits"
  },
  {
   "fact": "기여자 100+, 상위 drew 344, johntmyers 199, pimlock 143",
   "tool": "contributors"
  }
 ],
 "relevant_reason": "자율 AI 에이전트 격리·보안 런타임(AI 에이전트, AI 보안 키워드)",
 "relevant": true,
 "why_trending": "7일 커밋 86·작성자 24로 개발 지속, v0.1.2(09-28) 이후 안정 릴리스 주기 운영",
 "hype_flags": [],
 "release": {
  "tag": "v0.1.2",
  "date": "2026-09-28",
  "line": "sandbox-local loopback 접근 문서 정리 등"
 },
 "related_item_ids": [],
 "signal_reason": "7일 별 +3690, 커밋 86·기여자 100+로 개발 지속, 이번 주 릴리스 없음",
 "signal": "trending",
 "oneliner": "자율 AI 에이전트용 안전하고 격리된 런타임"
}
```

재현: `uv run python -m trendsit repo-analyze --week 2026-W41`
