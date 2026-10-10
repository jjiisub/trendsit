# 2026-W40 트렌딩 재구성: 접음 (2026-10-09 16:20)

멈춤 지점 결정 8의 접는 조건대로 W40은 레포 없이 진행한다. 반나절이 걸려서가 아니라, 별을 받은 시각(starred_at)을 읽을 방법이 없어서다.

## 시도한 것
- 후보: 트렌딩 월별 + 주별 목록 33개(`scripts/reconstruct_trending.py`, run `collect` note "trending reconstructed")
- REST `GET /repos/{owner}/{repo}/stargazers`(`Accept: application/vnd.github.star+json`)
  - `.env`의 fine-grained 토큰(읽기 전용): 403 "Resource not accessible by personal access token" 18건
  - gh 토큰(classic, repo 범위): 1쪽부터 404 Not Found(ollama/ollama 포함)
  - 토큰 없음: 401 Requires authentication
  - 별 4만 개가 넘는 15개는 REST 400쪽 제한으로 처음부터 셀 수 없음
- GraphQL `repository { stargazers(last: N) { edges { starredAt } } }`(400쪽 제한 없음)
  - fine-grained 토큰: FORBIDDEN
  - gh 토큰: `stargazerCount`는 5,498이 오지만 `edges`는 빈 목록
- 결론: 지금 GitHub API는 공개 레포의 stargazer 목록과 시각을 주지 않는다. 그래서 W40 주에 받은 별 수를 셀 수 없다

## 결과
- repo_trending 2026-W40: 0행(저장하지 않음)
- W40 weekly: 레포 근거 없이 글·영상만. 홈 레포 목록 비어 있음
- 다른 근사(커밋 수, 릴리스, OSS Insight)는 "그 주 별 수"가 아니라 이번에는 쓰지 않았다. 필요하면 S6 제안으로
