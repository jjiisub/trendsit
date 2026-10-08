# cursor/plugins

- 큐 이유: 트렌딩 이번 주 별 1109, 키워드 agent, coding-agent, dev-practice, ai-general / max_depth 2
- 트렌딩: 순위 4, 전체 별 10281, 이번 주 별 1109, 포크 977, 언어 TypeScript
- 과열 규칙(코드): {'flags': [], 'force_check': False, 'commits_7d': 26, 'contributors': 23, 'note': '7일 별 +1109, 커밋 26'}
- 한 줄 설명(repo_oneliner): Cursor 공식 플러그인을 모아둔 저장소

## 도구 호출 경로

| # | 도구 | 인자 | 결과 |
|---|---|---|---|
| 1 | github_repo | name=cursor/plugins | ok |
| 2 | releases | name=cursor/plugins | ok |
| 3 | search_items | query=cursor plugins | ok |
| 4 | recent_commits | name=cursor/plugins, days=7 | ok |
| 5 | contributors | name=cursor/plugins | ok |
| 6 | finish | 최종 답 제출 | ok |

## 출력 카드

```json
{
 "log": "cursor/plugins: 7일 커밋 26, 기여자 8, 관련",
 "attention": false,
 "evidence": [
  {
   "fact": "README: Official Cursor plugins for popular developer tools, frameworks, and SaaS products",
   "tool": "github_repo"
  },
  {
   "fact": "릴리스 없음",
   "tool": "releases"
  },
  {
   "fact": "이번 주 글에 'cursor plugins' 언급 없음",
   "tool": "search_items"
  },
  {
   "fact": "7일 커밋 26, 작성자 8, 마지막 커밋 2026-10-08",
   "tool": "recent_commits"
  },
  {
   "fact": "기여자 23명, 상위 poteto 103, cursoragent 86",
   "tool": "contributors"
  }
 ],
 "relevant_reason": "Cursor 공식 코딩 에이전트 플러그인 저장소(코딩 에이전트, 개발 실무 키워드)",
 "relevant": true,
 "why_trending": "7일 커밋 26, 기여자 8명으로 개발이 이어짐. 릴리스와 글 언급은 확인되지 않음",
 "hype_flags": [],
 "release": null,
 "related_item_ids": [],
 "signal_reason": "트렌딩 4위, 7일 별 +1109, 커밋 26·기여자 8명으로 개발 지속 확인. 릴리스·글 언급 근거 없음",
 "signal": "trending",
 "oneliner": "Cursor 공식 플러그인을 모아둔 저장소"
}
```

재현: `uv run python -m trendsit repo-analyze --week 2026-W41`
