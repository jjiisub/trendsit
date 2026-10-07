# S0 리포트: 레포 골격 + LLM 실행 기반 + 평가 틀

## 1. 한 줄 요약
`roles/<이름>.md`로 정의한 역할을 `models.yaml`의 모델로 실행하면, 스키마 검증(실패 시 재시도), 실행 기록(비용 포함), 응답 캐시(재실행 0원), 예산 상한이 함께 동작한다. `eval` 명령 하나로 코드 채점 → LLM 채점 → 품질 리포트가 나온다. `repo_oneliner`(실제 기능)와 `lookup_agent`(도구 루프 검증용)가 이 위에서 돈다.

## 2. 관문 A 결과
`bash scripts/verify_s0.sh` (2026-10-07, 종료 코드 0)
```
PASS A1 uv sync 성공, ruff 오류 0
PASS A2 pytest 56 passed in 2.49s
PASS A3 정상 통과 / FAIL roles/repo_oneliner.md: model: models.yaml에 없는 별칭 'genrate' / FAIL keywords.yaml: keywords[4].aliases: Input should be a valid list / FAIL budget.yaml: specs.S0: Input should be greater than or equal to 0
PASS A4 "Python용 동기·비동기 API와 HTTP/2 지원, 내장 CLI를 갖춘 HTTP 클라이언트 라이브러리" / step 241 hash=c03ec9c6dcee model=nvidia/nemotron-3-super-120b-a12b:free tokens=2302/56 latency=549ms (스키마 재시도 1회 기록)
PASS A5 step 243 cache_hit=1 cost=0, 모의 클라이언트 네트워크 0회(1 passed, 12 deselected in 0.30s)
PASS A6 step 241 재생(캐시 없이 재전송) → 새 step 244, 요청 본문 동일
PASS A7 BudgetExceeded로 호출 전 중단, /key 모의로 단계 사용액과 limit_remaining 검사 (5 passed, 8 deselected in 0.45s)
PASS A8 max_steps 대체 출력, 깊이 4 거부, 허용 밖 도구 거부, 도구 호출 kind='tool' 기록 (8 passed in 0.71s)
PASS A9 키 문자열 없음, .env와 data/가 .gitignore에 있음
PASS A10 README에 설치와 명령, reports/S0_report.md 있음
```

## 3. 관문 B 결과 (요약, 상세는 `reports/S0_quality.md`)
| 모델 | 코드 채점 | 정확성 평균(1점 수) | 구체성 | 표현 | 3점 미만 | 문턱값 | 비용 |
|---|---|---|---|---|---|---|---|
| generate `qwen/qwen3.8-27b` | 10/10 | 4.8 (0) | 4.9 | 5.0 | 0 | 통과 | $0.0096 (채점만, 생성은 캐시) |
| judge `google/gemini-3.8-flash` (상한선) | 10/10 | 5.0 (0) | 5.0 | 5.0 | 0 | 통과 | $0.0098 (채점만) |
| lookup_agent / smoke (도구 루프) | 5/5 | - | - | - | - | 통과 | $0 |

- 1회차(역할 md 초안)에 문턱값 통과(정확성 4.9, 구체성 5.0, 표현 5.0). 리뷰 반영으로 채점표에서 스펙 밖 문장을 뺀 뒤 같은 출력을 다시 채점한 2회차도 통과(위 표). 역할 md 개선 반복은 하지 않음
- 가장 낮은 사례: awesome-mcp-servers 정확성 3점("MCP 서버 구현체와 클라이언트를 주제별로 정리한 목록": README는 서버 목록이고 클라이언트는 별도 저장소). hermes-agent 구체성 4점(세부 기능 압축)
- 상한선 행은 생성과 채점이 같은 모델(gemini-3.8-flash)이라 자기 출력 채점 편향 가능성이 있음
- lookup_agent 실제 실행: 깊이 1~3의 답 3건은 맞힘, 깊이 4에만 답이 있는 2건은 a4, c4 읽기가 코드에서 "깊이 상한 초과"로 거부되고 걸음 상한에서 대체 출력(attention=true)으로 끝남

## 4. 결정한 것 (스펙에 없어서 정한 것)
| 결정 | 이유 |
|---|---|
| 기존 로컬 저장소(`~/Claude/projects/trendsit`, 예시 사이트 포함) 위에 handoff를 얹어 GitHub 비공개 `jjiisub/trendsit`로 올림 | S7에서 쓸 `site_src/`, 출력 계약 `data/trendsit-example.json`, `docs/02_DESIGN.md`를 그대로 이어 쓰기 위해(사용자 확인) |
| `CLAUDE.md`는 handoff 판(`@AGENTS.md`)으로 교체, 예전 `docs/01_CONTEXT.md` 삭제(`docs/CONTEXT.md`가 10/7판), 예시 사이트 빌드·서빙 명령은 README로 이동 | 맥락 문서를 하나로 |
| `.gitignore`: `data/*` + 예외 `data/trendsit-example.json`, `data/make_data.py` | 스펙은 `data/` 제외인데, 출력 계약 파일이 이미 `data/`에 있어 추적 유지 |
| 역할 md 앞부분에 `input:`(입력 클래스 이름) 추가 | CLI `--input` JSON을 검증할 입력 모델이 필요. 스펙 예시에는 `output`만 있음 |
| 에이전트의 최종 답은 자동으로 붙는 `finish` 도구(인자 = 출력 스키마)로 제출 | 도구 호출과 구조화 출력(response_format)을 함께 쓰면 제공사마다 지원이 갈림. 도구 하나로 통일. 텍스트로 JSON을 내면 그것도 받음 |
| 걸음(`max_steps`) = 모델 호출 1회. 도구 호출은 각각 `kind='tool'` 한 걸음으로 기록, 최종 출력은 `kind='code'` 걸음(text=log, attention) | 실행 기록 화면에서 판단(LLM), 행동(도구), 결과를 나눠 보기 위해 |
| **깊이는 모델이 준 `parent`만 믿지 않음.** 시작 문서(도구가 알려 준 roots) = 1, 이미 읽은 문서가 실제로 링크한 문서만 출발 문서 + 1. 시작 문서가 아닌데 parent가 없거나, 읽지 않은 parent, 링크에 없는 대상은 거부 | `parent=null`로 깊은 문서를 바로 읽는 우회를 막기 위해(테스트 `test_depth_cannot_be_bypassed_without_parent`). S3 원본 추적이 그대로 씀 |
| 깊이 초과는 실행 종료가 아니라 "거부 + 오류를 결과로 돌려줌". 종료는 finish / max_steps / 예산 | 다른 갈래에 답이 있을 수 있어 모델이 계속 볼 수 있게. 결국 못 찾으면 max_steps에서 대체 출력 |
| 출력 스키마의 길이 조건(60자)은 pydantic 검증(코드)이 지키고, strict JSON 스키마에서는 maxLength 등을 뺌 | 제공사마다 strict 스키마 키워드 지원이 다름. 어기면 검증 실패 → 오류를 알려 주고 재시도(실제로 Qwen 1건, smoke 여러 건에서 동작) |
| strict 스키마에서 `log`, `attention`을 맨 뒤로 | 모델이 본 출력(oneliner 등)을 먼저 쓰고 기록을 나중에 쓰게 |
| `--no-cache`는 캐시 읽기만 끄고 새 응답은 저장 | 관문 A4(실제 호출) 다음 A5(캐시 적중)를 한 흐름으로 확인하기 위해 |
| 예상 비용의 단가는 OpenRouter 공개 `/models/{id}/endpoints`에서 고정 제공사(태그) 단가를 읽어 `data/prices.json`에 하루 캐시. 못 찾으면 가장 비싼 단가. 입력 토큰은 2글자당 1토큰으로 보수 추정 | 단가를 설정 파일에 박으면 낡음. 조회 실패 + 저장값 없음이면 `PriceUnknown`으로 멈춤 |
| 단계 사용액 = max(키 usage − 기준값, 실행 기록 합) | 키 usage는 몇 분 늦게 반영됨(실측: 기록 $0.0326일 때 키 $0.0179, 몇 분 뒤 $0.0326으로 일치). 늦은 값으로 예산을 적게 보지 않게 |
| 비밀은 환경 변수 → `~/.config/trendsit/.env` 순서로 읽음 | CONTEXT 14장의 비밀 위치와 맞춤 |
| 채점자도 역할 md 하나(`eval/judge.md`, model: judge). 채점표 md를 `includes`로 시스템 프롬프트에 그대로 붙임 | 채점도 같은 run_role 경로(캐시, 예산, 실행 기록, 프롬프트 해시)를 탐. 채점표가 바뀌면 해시도 바뀜 |
| 관문 B 통과 조건에 "코드 채점 10/10"도 포함 | 코드 채점에서 떨어진 항목은 LLM 채점을 받지 않아 평균에서 빠지므로 |
| `eval --note`로 반복 기록에 "이번 수정의 이유"를 남김 | 공통 규칙 3장의 "원인 한 줄"을 품질 리포트에 남기기 위해 |
| 픽스처 6개: encode/httpx(라이브러리), excalidraw/excalidraw(앱), punkpeye/awesome-mcp-servers(목록), fastapi/full-stack-fastapi-template(템플릿), kakao/khaiii(한국어 README), Python3WebSpider/Images360(README = 제목 + 한 줄). 수집 스크립트 `scripts/fetch_fixtures.py` | 성격을 고르게. README가 완전히 빈 인기 레포는 찾기 어려워 "제목 + 한 줄"을 씀 |
| 역할 md의 좋은 예, 나쁜 예는 픽스처가 아닌 레포(llama.cpp, sindresorhus/awesome)로 | 스펙 예시("로컬에서 오픈웨이트 LLM을 내려받아 실행하는 런타임")는 픽스처 ollama의 기대 답에 가까워, 그대로 넣으면 기대 출력을 프롬프트에 박는 셈 |
| lookup_agent `max_steps: 12`, model: smoke | 이 문서 구조에서 넓게 따라가 깊이 3까지 읽고 finish하려면 8은 빠듯함(실측: 8에서 a3를 읽은 직후 상한) |
| `ruff`에서 E501(줄 길이) 끔 | 한글을 폭 2로 세어 거의 모든 한국어 설명 줄이 걸림 |
| `budget.yaml`에 상한이 없는 스펙(오타 포함)이면 실행 시작 전에 실패 | 스펙 상한 검사가 조용히 빠지지 않게(리뷰 2) |
| 실행 상태: 성공일 때만 `ok`, 예산 초과는 `stopped`, 그 밖의 예외는 `failed`. 에이전트가 예산 초과로 대체 출력을 내도 실행은 `stopped`, 종료 코드 1 | 스펙 5.5(대체 출력 반환)와 공통 규칙 3장(상한에 걸리면 멈추고 보고)을 함께 지키기 위해(리뷰 3, 6) |
| `steps`에 `reasoning_tokens`, `cached_tokens` 칸 추가(기존 DB는 자동으로 칸 추가) | 5.2 "함께 기록"을 집계 가능하게(리뷰 9). 스펙의 칸은 그대로 |
| 품질 리포트의 "모델별 최신 결과"는 픽스처 전체를 돈 실행만. `--limit` 부분 실행은 반복 기록에 "(부분 실행)"으로만 | 1건짜리 배관 확인이 최신 결과로 보이지 않게(리뷰 5) |

## 5. 스펙과 다르게 한 것
| 스펙 | 실제 | 이유 |
|---|---|---|
| smoke = `google/gemma-4-26b-a4b-it:free` | `nvidia/nemotron-3-super-120b-a12b:free` | gemma 무료는 OpenRouter에서 구조화 출력 미지원 + 업스트림 429(2026-10-07). 스펙이 허용한 교체 |
| judge `reasoning: {effort: low, max_tokens: 800}` | `reasoning: {max_tokens: 800}` | OpenRouter가 둘을 함께 받지 않음(HTTP 400 실측). 설정 검증에 "둘 중 하나만" 추가 |
| judge 제공사: "flex를 고를 수 있으면 사용, 방법은 확인 후 리포트" | `provider.order: [google-ai-studio/flex]`, `allow_fallbacks: false` | OpenRouter 제공사 목록에 flex가 별도 태그로 있음($0.375 / $1.875, standard의 절반). 실제 청구액이 flex 단가와 일치함을 확인 |
| A4 "steps 1행" | "성공 step 1행 + 필수 칸 채워짐"으로 검사, 스키마 재시도로 생긴 실패 step 수는 따로 표시 | 무료 모델 출력이 매번 달라 60자를 넘기면 재시도(5.5)가 정상 동작하며 실패 step이 하나 더 남음. 재시도를 끄는 것은 스펙(5.5)과 충돌 |
| 폴더 구조 | `trendsit/core/context.py`(실행 맥락 묶음), `eval/judge.md`, `scripts/fetch_fixtures.py`, `trendsit/tools/lookup_docs.json`(가짜 문서) 추가 | 이름은 스펙 그대로, 파일만 추가 |
| `eval/fixtures/lookup_agent/` 3~5개 | 5개 | 깊이 1, 2, 3에 답 / 깊이 4에만 답 2갈래 |
| 단계 상한 2달러, 키 공통 한도 5달러 | `phase_total_usd: 20.00`, 키 전체 크레딧 50달러. `AGENTS.md`, `COMMON.md` 4장, `CONTEXT.md` 13장·결정 기록도 고침. 스펙별 상한(S0 0.15달러)과 COMMON 4장의 배분 비율(생성 1.1 / 채점 0.4 / …)은 2달러 기준 원안 그대로 | 사용자 정정(2026-10-07): "전체 키 크레딧은 50달러, 이번 작업 제한은 20달러". `S0_TASK.md`는 원문 보존 |
| 채점표 = 스펙 7장 표 그대로 | 표 위에 "대상: oneliner, 근거는 README 앞부분, 설명, 토픽" 한 줄. 채점자 지침(`eval/judge.md`)에 "5와 3 사이면 4, 3과 1 사이면 2", "입력에 없는 내용이면 정확성 감점"(1점 기준의 재진술) | 채점 대상 필드와 1/3/5 사이 점수의 처리를 정하기 위해. 처음에 넣었던 "README가 거의 빈 레포는 …" 문장은 기준을 바꾸는 추가라 리뷰 후 제거하고 다시 채점 |
| "4xx는 재시도하지 않음" | openai SDK 기본 재시도(`max_retries=3`): 429, 5xx, 연결 오류, 타임아웃(120초) + 408, 409 | SDK 재시도를 쓰라는 스펙(1장)을 따름. 408, 409도 SDK가 재시도함. 타임아웃 재시도는 제공사가 이미 처리한 요청을 한 번 더 보낼 수 있음(예산 검사는 첫 전송 전 1회). S1에서 재시도를 직접 제어할지 결정 |
| A9 "`sk-or-` 등 grep" | `sk-or-v1-` + 16진수 20자 이상, `ghp_`, `github_pat_` | README와 `.env.example`의 자리표시자(`sk-or-v1-...`)가 걸리지 않게 |
| A3 예산 음수 경로 | `specs.S0`까지 짚음 | 리뷰 10 반영(처음엔 `specs`에서 멈추고 S0는 이유 문구에만 있었음) |

## 6. 남은 문제, 다음 스펙 제안
- **채점 변별력이 낮음.** 20건 중 19건이 세 항목 모두 5점. 지금 채점표(1/3/5 기준 문장)로는 좋은 출력 사이의 차이를 못 가름. 로컬 모델 비교(9주차) 전에 사람 라벨 몇 건과 채점 결과를 맞춰 보거나, 채점표에 4점 기준 문장을 넣는 것을 검토(채점표 수정은 설계 세션 결정 사항)
- 상한선 출력에 "다양한", "협업 도구"처럼 군더더기나 README에서 약하게만 뒷받침되는 표현이 있었는데 5점을 받음(자기 출력 채점 편향 가능성)
- 무료 smoke 모델이 nullable 도구 인자에 문자열 `"None"`을 넣는 실수를 자주 함(lookup_agent 실행 5건에서 14회 거부). 로컬 소형 모델로 바꾸면 같은 문제가 예상됨. 다음 스펙에서 nullable 인자의 `"None"`, `"null"`, `""`를 null로 정규화할지 결정 필요
- `max_steps`는 모델 호출 수 기준. 에이전트 명세의 "항목당 도구 호출 6번"은 S3/S4에서 별도 상한(도구 호출 수)으로 추가 필요(`AgentState.tool_calls`는 이미 셈)
- **예산 정정 반영 후 설계 세션이 정할 것:** 20달러 기준 배분 비율(COMMON 4장은 2달러 원안), 스펙별 상한(S1부터 `budget.yaml`의 `specs`에 넣어야 실행됨)
- 한 번의 모델 응답에 담긴 도구 호출 수 상한 없음(리뷰 14). S3에서 실제 fetch 도구를 붙이기 전에 "항목당 도구 호출 수" 상한과 함께 넣을 것
- OpenRouter 문서상 `usage: {include: true}`는 이제 효과가 없고 비용 칸이 기본으로 옴(리뷰 확인). 스펙대로 계속 보냄(해 없음)
- README 원문은 배지, HTML이 많아 앞 3,000자 중 실제 설명이 적은 레포가 있음(awesome-mcp-servers는 언어 배지가 앞부분을 차지). S4 레포 분석가에서 README 정리(배지, HTML 제거) 여부 결정
- 다음 스펙(S1 수집기) 제안: safe_fetch(SSRF 방어)를 S1 첫 작업으로, 수집 결과도 `steps`(kind='code')에 남겨 실행 기록 화면의 수집 단계 원천으로

## 7. 사용액
`uv run python -m trendsit cost --spec S0` (기준값 $0.483310, 2026-10-07 15:33 첫 실행 때 키 usage)
```
| 스펙 | 모델 | 호출 | 캐시 적중 | 입력 토큰 | 출력 토큰 | 사용액(달러) |
|---|---|---|---|---|---|---|
| S0 | google/gemini-3.8-flash | 61 | 11 | 108673 | 9293 | 0.047921 |
| S0 | qwen/qwen3.8-27b | 26 | 15 | 54628 | 1339 | 0.004083 |
| S0 | nvidia/nemotron-3-super-120b-a12b:free | 84 | 29 | 145974 | 5615 | 0.000000 |
| 합계 | | | | | | 0.052004 |

- 스펙 S0: 기록 합 $0.052004 / 상한 $0.15
- 단계(mvp) 사용액: $0.052004 / 상한 $20.00, 남은 예산 $19.947996
  - 키 기준(현재 usage − 기준값 $0.483310): $0.052004, 실행 기록 합: $0.052004 (키 반영이 늦으면 큰 쪽 사용)
- 키 limit_remaining: 49.464686312
```
- 키 기준 사용액은 몇 분 늦게 반영됨: 1회차 직후 키 $0.0179 / 기록 $0.0326 → 몇 분 뒤 둘 다 $0.0326. `usage.cost` 기록이 실제 청구액과 일치함을 확인

## 8. 서브에이전트 리뷰 지적과 처리
새 컨텍스트의 서브에이전트(code-reviewer)에게 `S0_TASK.md`, `COMMON.md`, diff, 이 리포트만 주고 대조 리뷰를 받음. A1~A10 구현과 테스트는 실제로 있음, 픽스처별 분기·기대 출력 박기·약한 테스트 없음, `usage.cost` 실측 기록 확인.

| # | 지적 | 심각도 | 처리 |
|---|---|---|---|
| 1 | strict 스키마 변환이 `title`, `format` 같은 **필드 이름**까지 키워드로 보고 지움(실행 확인) | high | 고침. 키워드 필터는 스키마 노드에만, `properties`의 키는 보존. 회귀 테스트 추가 |
| 2 | `budget.yaml`에 없는 스펙이면 스펙 상한 검사가 빠짐(`--spec s0`, `S1`) | medium | 고침. 상한 없는 스펙은 시작 전 실패. 테스트 추가 |
| 3 | 잡히지 않은 예외로 끝난 `role` 실행이 `ok`로 기록, `eval`은 일부 예외에서 `running`으로 남음 | medium | 고침. 기본 `failed`, 성공일 때만 `ok`. eval은 try/finally |
| 4 | 채점자가 항목을 빠뜨려도 관문 B 통과(1건 평균으로 판정 가능) | medium | 고침. 누락 1건이라도 미달. 테스트 추가 |
| 5 | 품질 리포트 "최신 결과"에 `--limit` 부분 실행이 섞임 | low/medium | 고침. 전체 실행만 |
| 6 | 에이전트 예산 초과가 대체 출력으로 삼켜져 실행이 `ok` | low | 고침. 대체 출력은 그대로 반환하고 실행은 `stopped`, eval 중단 |
| 7 | SDK 재시도 범위가 스펙보다 넓음(408, 409, 타임아웃) | low | 반영 안 함. SDK 재시도를 쓰라는 스펙(1장)과 맞물림. 5장 표에 편차로 기록, S1에서 결정 |
| 8 | 네트워크 호출 뒤 실패(오류 응답)면 비용, step이 남지 않음 | low | 고침. 오류 응답의 청구액도 예산에 더하고, run_role, run_agent에서 실패를 `code` step(error)으로 기록 |
| 9 | `cached_tokens`, `reasoning_tokens`가 steps 칸에 없음 | low | 고침. 칸 추가 + 기존 DB 자동 확장 |
| 10 | 예산 음수 경로가 `specs`에서 멈춤 | low | 고침. `specs.S0`, A3 검사도 이 경로로 |
| 11 | 채점표, 채점자 지침에 스펙 밖 문장 | low | 기준을 바꾸는 문장("README가 거의 빈 레포는 …")은 빼고 다시 채점. 나머지(대상 줄, 4·2점 보간)는 5장 표에 편차로 기록 |
| 12 | A6 재생이 캐시 적중으로 끝나 실제 재전송 미확인 | low | 고침. `--no-cache`로 재전송, 새 step `cache_hit=0` 확인 |
| 13 | 픽스처 스크립트가 403도 빈 README로 저장, note의 "수집일"이 실제로는 레포 push 날짜 | low | 고침. 404만 빈 README, 그 밖은 멈춤. note는 "수집 2026-10-07, 레포 최근 push …"로 바로잡음(채점에 안 쓰는 메타데이터) |
| 14 | 한 응답의 도구 호출 수 상한 없음 | low | S3로 넘김(6장) |
