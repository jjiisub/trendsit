# mvschwarz/openrig

- 큐 이유: 트렌딩 이번 주 별 2912, 키워드 agent, coding-agent, frontier-release, ai-general / max_depth 2
- 트렌딩: 순위 1, 전체 별 5860, 이번 주 별 2912, 포크 433, 언어 TypeScript
- 과열 규칙(코드): {'flags': [], 'force_check': False, 'commits_7d': 100, 'contributors': 50, 'note': '7일 별 +2912, 커밋 100'}
- 한 줄 설명(repo_oneliner): Claude Code, Codex 에이전트를 팀으로 구성해 실행하는 오픈소스 CLI

## 도구 호출 경로

| # | 도구 | 인자 | 결과 |
|---|---|---|---|
| 1 | github_repo | name=mvschwarz/openrig | ok |
| 2 | releases | name=mvschwarz/openrig | ok |
| 3 | search_items | query=openrig | ok |
| 4 | recent_commits | name=mvschwarz/openrig, days=7 | ok |
| 5 | contributors | name=mvschwarz/openrig | ok |
| 6 | finish | 최종 답 제출 | ok |

## 출력 카드

```json
{
 "log": "mvschwarz/openrig: v0.6.6 릴리스, 7일 커밋 100+, 관련",
 "attention": false,
 "evidence": [
  {
   "fact": "README: A rig wraps your harnesses. Define your agent team in YAML, boot it with one command. Claude Code and Codex in the same rig",
   "tool": "github_repo"
  },
  {
   "fact": "토픽: agent-orchestration, multi-agent, ai-coding, claude-code, codex-cli",
   "tool": "github_repo"
  },
  {
   "fact": "v0.6.6 2026-10-07 릴리스, 설치 후 operator가 팀을 제안해 즉시 실행하는 개선",
   "tool": "releases"
  },
  {
   "fact": "v0.6.5 2026-10-04, v0.6.4 2026-10-02 릴리스",
   "tool": "releases"
  },
  {
   "fact": "최근 7일 커밋 100+, 작성자 8명, 마지막 커밋 2026-10-08",
   "tool": "recent_commits"
  },
  {
   "fact": "기여자 50명, 상위 mvschwarz 1839, v-openrig-build 1304",
   "tool": "contributors"
  },
  {
   "fact": "이번 주 글에 openrig 언급 없음",
   "tool": "search_items"
  }
 ],
 "relevant_reason": "Claude Code·Codex 코딩 에이전트를 팀으로 오케스트레이션하는 멀티에이전트 도구(코딩 에이전트, AI 에이전트 키워드)",
 "relevant": true,
 "why_trending": "v0.6.6 릴리스(2026-10-07), 7일 커밋 100+로 개발 활발",
 "hype_flags": [],
 "release": {
  "tag": "v0.6.6",
  "date": "2026-10-07",
  "line": "설치 후 operator가 팀을 제안해 즉시 실행, 팀을 GitHub 폴더 링크로 공유·설치"
 },
 "related_item_ids": [],
 "signal_reason": "이번 주 릴리스 v0.6.6이 뜨는 이유, 7일 커밋 100+로 개발 이어짐",
 "signal": "release",
 "oneliner": "Claude Code, Codex 에이전트를 팀으로 구성해 실행하는 오픈소스 CLI"
}
```

재현: `uv run python -m trendsit repo-analyze --week 2026-W41`
