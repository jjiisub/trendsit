# S0 리포트: 레포 골격 + LLM 실행 기반 + 평가 틀

## 1. 한 줄 요약
`roles/<이름>.md`로 정의한 역할을 `models.yaml`의 모델로 실행하면, 스키마 검증(실패 시 재시도), 실행 기록(비용 포함), 응답 캐시(재실행 0원), 예산 상한이 함께 동작한다. `eval` 명령 하나로 코드 채점 → LLM 채점 → 품질 리포트가 나온다. `repo_oneliner`(실제 기능)와 `lookup_agent`(도구 루프 검증용)가 이 위에서 돈다.

## 2. 관문 A 결과
`bash scripts/verify_s0.sh` (2026-10-07, 종료 코드 0)
```
(VERIFY_OUTPUT)
```

## 3. 관문 B 결과 (요약, 상세는 `reports/S0_quality.md`)
| 모델 | 코드 채점 | 정확성 평균(1점 수) | 구체성 | 표현 | 3점 미만 | 문턱값 | 비용 |
|---|---|---|---|---|---|---|---|
| generate `qwen/qwen3.8-27b` | 10/10 | 4.9 (0) | 5.0 | 5.0 | 0 | 통과 | $0.0117 |
| judge `google/gemini-3.8-flash` (상한선) | 10/10 | 5.0 (0) | 5.0 | 5.0 | 0 | 통과 | $0.0187 |
| lookup_agent / smoke (도구 루프) | 5/5 | - | - | - | - | 통과 | $0 |

- 첫 회차에 문턱값을 통과해 개선 반복은 하지 않음(반복 0회). 가장 낮은 사례는 awesome-mcp-servers 정확성 4점("클라이언트" 포함: README는 서버 목록이고 클라이언트는 별도 저장소)
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

## 5. 스펙과 다르게 한 것
| 스펙 | 실제 | 이유 |
|---|---|---|
| smoke = `google/gemma-4-26b-a4b-it:free` | `nvidia/nemotron-3-super-120b-a12b:free` | gemma 무료는 OpenRouter에서 구조화 출력 미지원 + 업스트림 429(2026-10-07). 스펙이 허용한 교체 |
| judge `reasoning: {effort: low, max_tokens: 800}` | `reasoning: {max_tokens: 800}` | OpenRouter가 둘을 함께 받지 않음(HTTP 400 실측). 설정 검증에 "둘 중 하나만" 추가 |
| judge 제공사: "flex를 고를 수 있으면 사용, 방법은 확인 후 리포트" | `provider.order: [google-ai-studio/flex]`, `allow_fallbacks: false` | OpenRouter 제공사 목록에 flex가 별도 태그로 있음($0.375 / $1.875, standard의 절반). 실제 청구액이 flex 단가와 일치함을 확인 |
| A4 "steps 1행" | "성공 step 1행 + 필수 칸 채워짐"으로 검사, 스키마 재시도로 생긴 실패 step 수는 따로 표시 | 무료 모델 출력이 매번 달라 60자를 넘기면 재시도(5.5)가 정상 동작하며 실패 step이 하나 더 남음. 재시도를 끄는 것은 스펙(5.5)과 충돌 |
| 폴더 구조 | `trendsit/core/context.py`(실행 맥락 묶음), `eval/judge.md`, `scripts/fetch_fixtures.py`, `trendsit/tools/lookup_docs.json`(가짜 문서) 추가 | 이름은 스펙 그대로, 파일만 추가 |
| `eval/fixtures/lookup_agent/` 3~5개 | 5개 | 깊이 1, 2, 3에 답 / 깊이 4에만 답 2갈래 |

## 6. 남은 문제, 다음 스펙 제안
- **채점 변별력이 낮음.** 20건 중 19건이 세 항목 모두 5점. 지금 채점표(1/3/5 기준 문장)로는 좋은 출력 사이의 차이를 못 가름. 로컬 모델 비교(9주차) 전에 사람 라벨 몇 건과 채점 결과를 맞춰 보거나, 채점표에 4점 기준 문장을 넣는 것을 검토(채점표 수정은 설계 세션 결정 사항)
- 상한선 출력에 "다양한", "협업 도구"처럼 군더더기나 README에서 약하게만 뒷받침되는 표현이 있었는데 5점을 받음(자기 출력 채점 편향 가능성)
- 무료 smoke 모델이 nullable 도구 인자에 문자열 `"None"`을 넣는 실수를 자주 함(lookup_agent 실행 5건에서 14회 거부). 로컬 소형 모델로 바꾸면 같은 문제가 예상됨. 다음 스펙에서 nullable 인자의 `"None"`, `"null"`, `""`를 null로 정규화할지 결정 필요
- `max_steps`는 모델 호출 수 기준. 에이전트 명세의 "항목당 도구 호출 6번"은 S3/S4에서 별도 상한(도구 호출 수)으로 추가 필요(`AgentState.tool_calls`는 이미 셈)
- OpenRouter 키 한도가 문서의 공통 한도 5달러가 아니라 **50달러**로 조회됨(`limit: 50`). 2달러 상한은 코드가 지키지만, 키 한도를 5달러로 둘 계획이었다면 OpenRouter 설정 확인 필요
- README 원문은 배지, HTML이 많아 앞 3,000자 중 실제 설명이 적은 레포가 있음(awesome-mcp-servers는 언어 배지가 앞부분을 차지). S4 레포 분석가에서 README 정리(배지, HTML 제거) 여부 결정
- 다음 스펙(S1 수집기) 제안: safe_fetch(SSRF 방어)를 S1 첫 작업으로, 수집 결과도 `steps`(kind='code')에 남겨 실행 기록 화면의 수집 단계 원천으로

## 7. 사용액
`uv run python -m trendsit cost --spec S0` (기준값 $0.483310, 2026-10-07 15:33 첫 실행 때 키 usage)
```
(COST_OUTPUT)
```

## 8. 서브에이전트 리뷰 지적과 처리
(REVIEW)
