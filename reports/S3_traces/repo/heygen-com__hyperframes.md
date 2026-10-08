# heygen-com/hyperframes

- 큐 이유: 트렌딩 이번 주 별 3908, 키워드 agent, mcp-tools, ai-general / max_depth 2
- 트렌딩: 순위 3, 전체 별 58678, 이번 주 별 3908, 포크 5220, 언어 TypeScript
- 과열 규칙(코드): {'flags': [], 'force_check': False, 'commits_7d': 100, 'contributors': 85, 'note': '7일 별 +3908, 커밋 100'}
- 한 줄 설명(repo_oneliner): HTML과 CSS, 미디어를 MP4 영상으로 렌더링하는 오픈소스 프레임워크

## 도구 호출 경로

| # | 도구 | 인자 | 결과 |
|---|---|---|---|
| 1 | github_repo | name=heygen-com/hyperframes | ok |
| 2 | releases | name=heygen-com/hyperframes | ok |
| 3 | search_items | query=hyperframes | ok |
| 4 | recent_commits | name=heygen-com/hyperframes, days=7 | ok |
| 5 | finish | 최종 답 제출 | ok |

## 출력 카드

```json
{
 "log": "heygen-com/hyperframes: v0.8.141 릴리스, 7일 릴리스 5개, 커밋 100+, 관련",
 "attention": false,
 "evidence": [
  {
   "fact": "README: HTML, CSS, media, seekable animations을 결정적 MP4로 렌더링하는 오픈소스 프레임워크. AI 코딩 에이전트(Claude Code 플러그인, skills)로 사용 가능",
   "tool": "github_repo"
  },
  {
   "fact": "토픽: ai, mcp, framework, rendering, typescript, video",
   "tool": "github_repo"
  },
  {
   "fact": "v0.8.141 2026-10-08 릴리스 (Google font axis fallback, Studio preview decode)",
   "tool": "releases"
  },
  {
   "fact": "최근 7일 릴리스 5개 (v0.8.137~v0.8.141, 2026-10-06~08)",
   "tool": "releases"
  },
  {
   "fact": "최근 7일 커밋 100+, 작성자 9명, 마지막 커밋 2026-10-08",
   "tool": "recent_commits"
  },
  {
   "fact": "이번 주 글에 hyperframes 언급 없음",
   "tool": "search_items"
  }
 ],
 "relevant_reason": "AI 코딩 에이전트용 렌더링 도구로 MCP 토픽, 에이전트 플러그인·skills 지원 — 에이전트/도구 호출 키워드와 직접 관련",
 "relevant": true,
 "why_trending": "이번 주 릴리스 5개(v0.8.137~141)와 7일 커밋 100+로 개발이 활발",
 "hype_flags": [],
 "release": {
  "tag": "v0.8.141",
  "date": "2026-10-08",
  "line": "Google font axis fallback, Studio preview decode 개선"
 },
 "related_item_ids": [],
 "signal_reason": "이번 주 릴리스 5개, 7일 커밋 100+로 개발이 이어지는 릴리스 주도 트렌딩",
 "signal": "release",
 "oneliner": "HTML과 CSS, 미디어를 MP4 영상으로 렌더링하는 오픈소스 프레임워크"
}
```

재현: `uv run python -m trendsit repo-analyze --week 2026-W41`
