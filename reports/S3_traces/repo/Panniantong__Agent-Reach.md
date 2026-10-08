# Panniantong/Agent-Reach

- 큐 이유: 트렌딩 이번 주 별 6912, 키워드 agent, coding-agent, mcp-tools, frontier-release, ai-general / max_depth 2
- 트렌딩: 순위 6, 전체 별 93489, 이번 주 별 6912, 포크 8188, 언어 Python
- 과열 규칙(코드): {'flags': [], 'force_check': False, 'commits_7d': 4, 'contributors': 36, 'note': '7일 별 +6912, 커밋 4'}
- 한 줄 설명(repo_oneliner): AI 에이전트에 인터넷 검색·읽기 기능을 제공하는 CLI 도구

## 도구 호출 경로

| # | 도구 | 인자 | 결과 |
|---|---|---|---|
| 1 | github_repo | name=Panniantong/Agent-Reach | ok |
| 2 | releases | name=Panniantong/Agent-Reach | ok |
| 3 | search_items | query=Agent-Reach | ok |
| 4 | recent_commits | name=Panniantong/Agent-Reach, days=7 | ok |
| 5 | contributors | name=Panniantong/Agent-Reach | ok |
| 6 | finish | 최종 답 제출 | ok |

## 출력 카드

```json
{
 "log": "Panniantong/Agent-Reach: 별 +6912, 커밋 4, 릴리스·글 언급 없음, 관련",
 "attention": true,
 "evidence": [
  {
   "fact": "README: AI Agent에 인터넷 검색·읽기(Twitter, Reddit, YouTube, GitHub, Bilibili, XiaoHongShu)를 CLI로 제공, 토픽 ai-agent/mcp/llm-tools",
   "tool": "github_repo"
  },
  {
   "fact": "최근 릴리스 v1.5.0 2026-06-11(이번 주 아님), v1.4.2 2026-06-10",
   "tool": "releases"
  },
  {
   "fact": "이번 주 글에 Agent-Reach 언급 없음",
   "tool": "search_items"
  },
  {
   "fact": "7일 커밋 4, 작성자 1, 마지막 커밋 2026-10-07",
   "tool": "recent_commits"
  },
  {
   "fact": "기여자 36명, 상위 Panniantong 325커밋",
   "tool": "contributors"
  }
 ],
 "relevant_reason": "AI 에이전트에 인터넷 검색·읽기 도구를 MCP/CLI로 제공, 에이전트·MCP·도구 호출 키워드 직접 해당",
 "relevant": true,
 "why_trending": "도구로 확인된 릴리스·글 언급 없음, 별 급증 원인 미확인",
 "hype_flags": [],
 "release": null,
 "related_item_ids": [],
 "signal_reason": "7일 별 +6912, 커밋 4(작성자 1), 기여자 36, 이번 주 릴리스·글 언급 없음",
 "signal": "trending",
 "oneliner": "AI 에이전트에 인터넷 검색·읽기 기능을 제공하는 CLI 도구"
}
```

재현: `uv run python -m trendsit repo-analyze --week 2026-W41`
