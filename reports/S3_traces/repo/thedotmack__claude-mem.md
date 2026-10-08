# thedotmack/claude-mem

- 큐 이유: 트렌딩 이번 주 별 2607, 키워드 agent, coding-agent, rag-search, frontier-release, ai-industry, ai-general / max_depth 2
- 트렌딩: 순위 7, 전체 별 97865, 이번 주 별 2607, 포크 8609, 언어 TypeScript
- 과열 규칙(코드): {'flags': [], 'force_check': False, 'commits_7d': 100, 'contributors': 100, 'note': '7일 별 +2607, 커밋 100'}
- 한 줄 설명(repo_oneliner): Claude Code용 세션 기억 압축 및 재주입 시스템

## 도구 호출 경로

| # | 도구 | 인자 | 결과 |
|---|---|---|---|
| 1 | github_repo | name=thedotmack/claude-mem | ok |
| 2 | releases | name=thedotmack/claude-mem | ok |
| 3 | search_items | query=claude-mem | ok |
| 4 | recent_commits | name=thedotmack/claude-mem, days=7 | ok |
| 5 | contributors | name=thedotmack/claude-mem | ok |
| 6 | finish | 최종 답 제출 | ok |

## 출력 카드

```json
{
 "log": "thedotmack/claude-mem: v13.34.2 릴리스, 커밋 100+, 관련",
 "attention": false,
 "evidence": [
  {
   "fact": "README: Persistent memory compression system built for Claude Code, captures tool usage observations, generates semantic summaries, makes them available to future sessions",
   "tool": "github_repo"
  },
  {
   "fact": "토픽: ai-agents, ai-memory, rag, embeddings, long-term-memory, claude-code-plugin",
   "tool": "github_repo"
  },
  {
   "fact": "v13.34.2 2026-10-06 릴리스, observer 세션 prompt-cache 회귀 수정",
   "tool": "releases"
  },
  {
   "fact": "v13.34.0 2026-10-06 릴리스, Pi와 DeepSeek Harness 통합 추가",
   "tool": "releases"
  },
  {
   "fact": "7일 커밋 100+, 작성자 7명, 마지막 커밋 2026-10-06",
   "tool": "recent_commits"
  },
  {
   "fact": "기여자 100+, 상위 thedotmack 2365커밋",
   "tool": "contributors"
  },
  {
   "fact": "이번 주 글에 claude-mem 언급 없음",
   "tool": "search_items"
  }
 ],
 "relevant_reason": "코딩 에이전트(Claude Code 등)용 세션 기억·RAG 재주입 도구로 에이전트, RAG 키워드 직접 해당",
 "relevant": true,
 "why_trending": "v13.34.0~v13.34.2 릴리스(2026-10-06), 7일 커밋 100+",
 "hype_flags": [],
 "release": {
  "tag": "v13.34.2",
  "date": "2026-10-06",
  "line": "Pi·DeepSeek Harness 통합 추가, observer prompt-cache 회귀 수정"
 },
 "related_item_ids": [],
 "signal_reason": "이번 주 릴리스(v13.34.0~v13.34.2)가 뜨는 이유, 7일 커밋 100+로 개발 지속",
 "signal": "release",
 "oneliner": "Claude Code용 세션 기억 압축 및 재주입 시스템"
}
```

재현: `uv run python -m trendsit repo-analyze --week 2026-W41`
