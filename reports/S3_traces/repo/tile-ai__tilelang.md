# tile-ai/tilelang

- 큐 이유: 트렌딩 이번 주 별 639, 키워드 ai-industry, ai-general / max_depth 2
- 트렌딩: 순위 10, 전체 별 8493, 이번 주 별 639, 포크 857, 언어 Python
- 과열 규칙(코드): {'flags': [], 'force_check': False, 'commits_7d': None, 'contributors': 100, 'note': ''}
- 한 줄 설명(repo_oneliner): GPU/CPU/NPU 커널 개발을 위한 도메인 특화 언어

## 도구 호출 경로

| # | 도구 | 인자 | 결과 |
|---|---|---|---|
| 1 | github_repo | name=tile-ai/tilelang | ok |
| 2 | releases | name=tile-ai/tilelang | ok |
| 3 | search_items | query=tilelang | ok |
| 4 | recent_commits | name=tile-ai/tilelang, days=7 | ok |
| 5 | contributors | name=tile-ai/tilelang | ok |
| 6 | finish | 최종 답 제출 | ok |

## 출력 카드

```json
{
 "log": "tile-ai/tilelang: v0.1.15 릴리스(Ascend 950 NPU), 커밋 14, 관련",
 "attention": false,
 "evidence": [
  {
   "fact": "README: TVM 기반 GPU/CPU/NPU 커널(GEMM, FlashAttention) 개발용 DSL, 2026-09-30 Ascend 950 NPU 백엔드 지원 추가",
   "tool": "github_repo"
  },
  {
   "fact": "v0.1.15 2026-09-30 릴리스: Huawei Ascend 950 네이티브 NPU 백엔드, CUDA warp specialization",
   "tool": "releases"
  },
  {
   "fact": "최근 7일 커밋 14, 작성자 13, 마지막 커밋 2026-10-08",
   "tool": "recent_commits"
  },
  {
   "fact": "기여자 100+, 상위 LeiWang1999 827커밋",
   "tool": "contributors"
  },
  {
   "fact": "이번 주 글에 tilelang 언급 없음",
   "tool": "search_items"
  }
 ],
 "relevant_reason": "GPU/NPU 커널 개발 DSL로 AI 모델 성능 최적화 도구, AI 산업·개발 실무 키워드와 관련",
 "relevant": true,
 "why_trending": "v0.1.15 릴리스(2026-09-30, Ascend 950 NPU 네이티브 지원), 최근 7일 커밋 14",
 "hype_flags": [],
 "release": {
  "tag": "v0.1.15",
  "date": "2026-09-30",
  "line": "Huawei Ascend 950 NPU 네이티브 백엔드, CUDA warp specialization 추가"
 },
 "related_item_ids": [],
 "signal_reason": "v0.1.15 릴리스(Ascend 950 NPU 지원)가 뜨는 이유, 7일 커밋 14·기여자 100+로 개발 지속",
 "signal": "release",
 "oneliner": "GPU/CPU/NPU 커널 개발을 위한 도메인 특화 언어"
}
```

재현: `uv run python -m trendsit repo-analyze --week 2026-W41`
