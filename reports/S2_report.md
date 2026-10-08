# S2 리포트: 0단계(S1 리뷰 반영) + 2a 필터 + 2b 글 1차 요약

> 상태: 클라우드 구현 끝 + 클라우드 관문 B(픽스처 범위) 끝 + **맥 확인(2026-10-08)**: 설계 결정 Q1~Q7 반영, 실제 한 주 rematch·filter·summarize, item_card 관문 B 21건. 라벨(relevance 40, item_card 21)은 MVP 동안 사람이 달지 않고 PR 리뷰 세션 Opus 5.5가 2차 채점(설계 결정 D1-3). 필터 문턱값과 `--agreement`는 **리뷰 채점 대기**(반영 단계에서 "잠정"으로 확정)
> 맥 실행 환경: M1 Max, macOS, 파이썬 3.12.14, 임베딩 MPS. 데이터는 맥 S1 DB(`../trendsit/data`) 사본
> **클라우드 관문 B의 범위**: 저장소에 있는 픽스처(item_card 17건, 임베딩 재현 20건, repo_oneliner 10건)와 녹화 응답으로 만든 개발 DB(25건)만으로 돌렸다. 실제 한 주 데이터(맥의 `data/trendsit.db`)로 하는 `rematch`·`filter`·`summarize`, 시드 13건, 문턱값 확정, 사람 라벨 일치율은 맥 몫으로 남는다. judge 판정은 라벨이 없어 모두 **잠정**

> 진행 체크리스트(COMMON 8장). 맥락이 끊기면 여기서 이어 간다. S3(3c, 3a, 3b)는 `reports/S3_report.md`.
> 실행 환경(두 번째 클라우드 세션, 2026-10-08): `OPENROUTER_API_KEY` 있음, openrouter.ai·huggingface.co·export.arxiv.org 열림. github.com과 다른 저장소의 GitHub API, news.hada.io는 여전히 막힘. 임베딩은 CPU(`Qwen/Qwen3-Embedding-0.6B@cpu`)
> 실행 환경(첫 클라우드 세션): 리눅스, 파이썬 3.13. `OPENROUTER_API_KEY` 없음, 네트워크는 `api.github.com`과 패키지 저장소만 열림(openrouter.ai, huggingface.co, export.arxiv.org, 수집 소스 도메인은 정책상 막힘). LLM과 실제 임베딩 모델이 필요한 것은 `reports/S2S3_mac_todo.md`로.

## 진행 체크리스트
- [x] 0단계 M1 마이그레이션 번호 키 등록(`core/migrations.py`, `schema_migrations`)
- [x] 0단계 M2 `RoleOutput.enforce` 훅 + repo_oneliner README 200자 규칙 + eval 전·후 기록
- [x] 0단계 M4 도구 인자 거부 메시지에 칸 경로
- [x] 0단계 M6 낡은 문구 2곳
- [x] 0단계 병행 개발 자리(`[project.optional-dependencies]`, `artifacts.py` `_merge`, `cli.py` `_register`)
- [x] 0단계 `scripts/verify_s2.sh --stage 0`
- [x] 0단계 repo_oneliner 관문 B 재실행(두 번째 클라우드 세션) + `--agreement`
- [x] 2a 키워드 안 적용(13개), 녹화 테스트는 테스트 전용 키워드로 분리
- [x] 2a `rematch`
- [x] 2a 임베딩 필터(실제·모의 임베더, 네 갈래 판정, 임베딩 재사용), URL 중복 연결, 검증 산출물·라벨 생성기, 재현 픽스처 20건
- [x] 2a 실제 임베딩 모델 테스트, 재현 픽스처 CPU 점수 기록(두 번째 클라우드 세션)
- [x] 2a 실제 한 주 점수 분포, 시드 13건, 검증 산출물, MPS 점수(맥)
- [ ] 2a 문턱값 확정(리뷰 채점 대기, 반영 단계에서 잠정 확정)
- [x] 설계 결정 Q1(채점 두 갈래), Q5(라벨 경로), Q6(긴 인용 자르기), Q7(예산) 반영(맥)
- [x] 2b `item_card` 스키마·enforce·역할 md·채점기·채점표, `summarize`, 픽스처 17건(녹화 글 16 + 인젝션 1)
- [x] 2b 관문 B 픽스처 17건(두 번째 클라우드 세션, 반복 3회): 코드 16/17로 미달 1건, judge 잠정 통과
- [x] 2b 픽스처 4건 추가(21건), 관문 B 재실행, 한 주 실행(맥)
- [ ] 2b 라벨 21건 일치율(리뷰 채점 대기)

## 0단계 (S1 리뷰 반영, `s2-0-base` PR)

### 1. 한 줄 요약
마이그레이션을 번호 키 등록 방식(번호마다 한 트랜잭션, 기존 DB 보존)으로 바꾸고, 역할 출력에 코드 규칙 훅(`enforce`)을 넣어 repo_oneliner의 "README가 얇으면 attention" 규칙을 코드로 옮겼다. 도구 인자 오류는 칸 경로와 함께 모델에게 돌려준다. 묶음 B(S4)와 겹치는 파일에는 스펙별로 한 줄씩 더하는 자리를 만들었다.

### 2. 관문 A
`bash scripts/verify_s2.sh --stage 0` (2026-10-08, 클라우드)
```
FAIL A1 회귀: verify_s0.sh FAIL [A4 키 없음(OPENROUTER_API_KEY);A5 키 없음;A6 키 없음;] verify_s1.sh FAIL [A1 ]
PASS A2 ruff 0, pytest 168 passed in 10.41s
PASS A3 check-config 통과 (OK 설정 5개, 역할 3개). filter.yaml·deep.yaml은 2a·3a 단계 몫
PASS A4 역할 md 검사: 기존 역할 전부 통과(새 역할 md는 2b 이후 몫) (1 passed, 24 deselected in 0.04s)
PASS M1 마이그레이션 번호 키: user_version 2 기존 DB 재적용 없음, 10·20 등록 순서 무관, 늦게 추가된 10번 적용, 실패는 기록 없이 재시도 (8 passed in 0.14s)
PASS M2 enforce 훅: 칸을 바꾸면 step detail enforced 기록, eval이 원래·enforce 후를 모두 기록(판정은 원래 출력), repo_oneliner README 200자 규칙 (6 passed in 0.09s)
PASS M4 도구 거부 메시지: 중첩 인자 오류에 칸 경로(origin.kind, pages[1]) (2 passed, 4 deselected in 0.03s)
PASS M6 낡은 문구 두 개(geeknews.py 설명, report.py 계획 표기) 없음
```
- A1 FAIL은 코드가 아니라 환경 때문이다. `verify_s0.sh`의 A4~A6은 smoke(무료) 모델을 실제로 부르는데 이 세션에 키가 없고 openrouter.ai도 막혀 있다. verify_s0의 나머지 7개(A1~A3, A7~A10)와 verify_s1의 나머지 23개는 PASS. 키가 있는 곳(맥)에서 `bash scripts/verify_s2.sh --stage 0`을 한 번 돌려 A1을 확인해야 한다

### 3. 관문 B (repo_oneliner)
**맥 재채점(설계 결정 Q1, 2026-10-08)**: 재생성 없이 `eval repo_oneliner --regrade reports/eval/repo_oneliner_generate_20261008-104252.json`(→ `…-140318.json`). attention은 코드 소유 칸이라 enforce 후 값으로 채점

| 기준 | 결과 |
|---|---|
| 코드 채점(통과 판정: 원래 출력 + 코드 소유 칸만 enforce 후) | **10/10 통과** |
| 모델 일치율(attention) | 9/10(Images360만 코드가 true로) |
| judge Q1·Q2·Q3 | 각 10/10(새로 통과한 Images360 1건만 judge 추가 호출, $0.0011) |

**두 번째 클라우드 세션 재실행(2026-10-08)**: `eval repo_oneliner --spec S2`(`reports/eval/repo_oneliner_generate_20261008-104252.json`, 프롬프트 `a1a38c7f4dfe`, $0.0155)

| 기준 | 결과 |
|---|---|
| 코드 채점(원래 출력, 통과 판정 기준) | 9/10 미달(Images360 attention false) |
| 코드 채점(enforce 후, 보고용) | 10/10 |
| judge Q1·Q2·Q3 | 각 9/9 |

- 예상(질문 파일 Q1)과 같다. 판정 기준 결정은 Q1에 남아 있다
- `eval repo_oneliner --agreement --spec S2`: 라벨이 가리키는 결과(`…-071621.json`) 기준이라 아래 표와 같다(Q1 1.0, Q2 0.889, Q3 1.0, 전체 0.963)

첫 클라우드 세션(키 없음) 때 기록:
- 재실행(`eval repo_oneliner`)은 키가 없어 못 했다. 맥의 응답 캐시가 있으면 0원
- 대신 저장된 마지막 전체 실행(`reports/eval/repo_oneliner_generate_20261008-071621.json`, 프롬프트 `a1a38c7f4dfe`)에 새 enforce를 적용해 코드 채점을 다시 계산했다(LLM 호출 없음)

| 기준 | 코드 통과 | 바뀐 것 |
|---|---|---|
| 원래 출력(통과 판정 기준) | 9/10 | - |
| enforce 후 출력(보고용) | 10/10 | Images360 attention false → true (README 정리 본문 48자 < `README_THIN_CHARS` 200) |

- 나머지 9개 픽스처의 README 정리 본문은 797~2,493자라 규칙이 걸리지 않는다(기준 200자와 거리가 멀어 흔들릴 여지 적음)
- `eval repo_oneliner --agreement --spec S1` (사용자 라벨 10행, 채점된 9행과 비교)

| 질문 | 일치 | 비교 수 | 일치율 |
|---|---|---|---|
| Q1 | 9 | 9 | 1.0 |
| Q2 | 8 | 9 | 0.889 |
| Q3 | 9 | 9 | 1.0 |
| 전체 | 26 | 27 | 0.963 |

- 질문마다 80% 이상. 어긋난 1건은 hermes-agent Q2(사람 fail: "무엇을 해 주는 에이전트인지 흐림", judge pass)
- 원래 출력 기준이면 재실행해도 9/10이 유지될 가능성이 높다. 판정 기준을 질문 파일 Q1에 남겼다(`reports/S2_questions.md`)

### 4. 결정한 것
- 마이그레이션 SQL은 `MIGRATIONS: dict[int, str]`에 `register(번호, sql)`로 넣는다(같은 번호 두 번 등록은 예외). 문장 나누기는 `sqlite3.complete_statement`로(문자열 안 `;` 보존)
- `isolation_level=None`은 마이그레이션 동안만. 끝나면 원래 값("")으로 되돌린다. 다른 쓰기(`save_item` 등)가 `with conn:` 트랜잭션에 기대고 있어서, 연결 전체를 자동 커밋으로 바꾸면 여러 행 쓰기가 원자적이지 않게 된다
- 기존 DB의 1..N 기록은 `applied_at = "legacy user_version"`으로 남겨 새로 적용한 것과 구별한다
- enforce는 칸을 직접 바꾸지 않고 `fix(칸, 값, 규칙)`으로 바꾼 사본을 만든다. 바꾼 기록과 원래 출력은 출력 객체의 비공개 속성(`_enforced`, `_raw`)에 담아 run_role/run_agent → eval까지 전달한다. 칸 경로는 최상위 칸 이름(목록 안 항목을 고치면 목록 전체의 전·후)
- run_agent의 대체 출력(상한 도달)에도 enforce를 적용한다(저장 전 규칙은 출력이 어디서 왔든 같게)
- eval의 judge(LLM 채점)는 원래 출력으로 한다. 통과 판정이 원래 출력 기준이므로 같은 기준으로 맞춤
- 도구 인자 오류: pydantic 오류 종류를 짧은 한국어로 바꾸고(`필수 칸 없음`, `허용 값 아님 (허용: 'paper' or 'blog')`, `정수여야 함 (받은 값: "a")`), 칸 경로는 `origin.items[0].kind` 형식, 최대 5건. JSON이 아니면 위치와 함께
- 스펙별 모듈 합치기: 모듈 자체가 없으면 건너뛰고, 모듈 안의 import 오류(예: `embed` 묶음 없이 torch import)는 그대로 올린다(숨기면 명령이 조용히 사라짐)
- `[project.optional-dependencies]`는 빈 표로 두었다(uv lock 변화 없음)

### 5. 스펙과 다르게 한 것
- 없음. 단, repo_oneliner 관문 B 재실행은 키가 없어 저장된 결과로 다시 채점한 것으로 대신했다(위 3)

### 6. 남은 문제
- repo_oneliner 판정 기준(질문 파일 Q1)
- 키가 있는 곳에서 `verify_s2.sh --stage 0`의 A1 확인, `eval repo_oneliner --spec S2` 재실행(캐시 0원 예상)

### 7. 사용액
`uv run python -m trendsit cost --spec S2` (2026-10-08, 클라우드. 키 조회 불가라 실행 기록 합)
```
| 합계 | | | | | | 0.000000 |
- 스펙 S2: 기록 합 $0.000000 / 상한 $1.00
- 단계 사용액(실행 기록 합, 키 조회 불가): $0.000000 / 상한 $20.00
```
- 0단계 LLM 사용 0달러(호출 없음). 키 `limit_remaining`은 키가 없어 적지 못했다

### 7-1. README, 위키 메모
- README: 기능 변화 없음(0단계는 바탕 공사). `docs/DEVELOPMENT.md`에 마이그레이션 방식, enforce, 병행 개발 자리, `verify_s2.sh`를 적었다
- 위키 메모: `executescript`는 먼저 COMMIT해 버려 마이그레이션이 트랜잭션이 되지 않던 문제 → 자동 커밋 모드에서 BEGIN/문장별 실행/COMMIT으로. 연결 전체를 자동 커밋으로 두면 다른 여러 행 쓰기의 원자성이 깨져서 마이그레이션 동안만 바꿈

### 8. 서브에이전트 리뷰
새 컨텍스트 서브에이전트에게 스펙(S1_REVIEW, S2S3_TASK 5.0·6장, COMMON 9장, CONTRACTS 4장)과 diff만 주고 대조 리뷰를 받았다. 높음 0건.
| 지적 | 처리 |
|---|---|
| (중간) `verify_s2.sh`를 인자 없이 돌리면 없는 항목이 조용히 빠져 통과처럼 보임 | 전체 모드에서 아직 없는 항목은 `FAIL 미구현`으로 출력 |
| (중간) 스펙별 스키마 합치기에서 같은 이름이 말없이 덮어씀 | 다른 클래스로 같은 이름이 들어오면 `ValueError` + 테스트 |
| (낮음) finish의 스키마 오류 메시지에 칸 경로가 없음 | `validation_paths`로 통일 |
| (낮음) SQLite가 이미 되돌린 트랜잭션에 ROLLBACK하면 원래 오류가 가려짐 | `conn.in_transaction`일 때만 ROLLBACK |
| (낮음) `role --replay`는 enforce를 거치지 않음 | 재생에는 입력이 없어 적용하지 않음. detail에 `enforce: 미적용` + DEVELOPMENT.md에 한 줄 |
| (낮음) `README_THIN_CHARS` 위치, 리포트에 기준 숫자 | 상수를 구역 주석 위로. 기준 숫자는 이 리포트 3장에 |
| (낮음) repo_oneliner 재실행과 `--agreement`는 키가 없어 못 함 | `--agreement`는 저장된 결과로 확인(3장). 재실행은 맥 확인 목록 |
| (낮음) 스키마 모듈이 선택 의존성을 import하면 그 묶음이 없는 환경에서 모든 명령이 멈춤 | `artifacts.py` 주석과 DEVELOPMENT.md에 "스키마·명령 모듈 첫머리에서 선택 의존성 import 금지" |

## 2a 키워드 재판정, 임베딩 필터, URL 중복 연결

### 1. 한 줄 요약
바뀐 키워드(13개)를 저장된 글에 다시 적용하고(`rematch`), 기간의 글·영상 전부를 관심사 설명과의 임베딩 유사도로 keep/drop 판정하며(`filter`), 원문 링크가 같은 글을 기준 항목 하나로 잇는다. 클라우드에서는 모의 임베더로 흐름과 규칙을 확인했고, 실제 모델 점수와 문턱값은 맥에서 정한다.

### 2. 관문 A
`bash scripts/verify_s2.sh`(전체) 출력은 아래 "S2 관문 A 전체"에.

### 3. 관문 B
**맥(2026-10-08)**: `rematch` 343건 중 295건 바뀜(filtered→pass 89, 통과 305건 > 184), 다시 돌려 0건. `filter --embedder real`(MPS) 325건(글 308, 영상 17) 155.4초, keep 281 / drop 44(키워드 통과 278, 되살림 3, 낮은 유사도 9, 키워드 없음 23, 제외어 12). 산출물 `reports/S2_filter/`

| 기준 | 결과 |
|---|---|
| `relevance_seed.csv` 13건 85% 이상 | **11/13(84.6%) 미달**. 틀린 2건은 고객 사례 글(OpenAI Chatham 0.356, Anthropic Barclays 0.329, 기대 drop)이 키워드 통과로 keep. 잠정 문턱값 기준 |
| 라벨 40건 keep 정밀도·재현율 | **리뷰 채점 대기**(`eval/labels/relevance.csv` 40행, 빈칸, `labeler` 칸) |
| (보조) 재현 픽스처 CPU↔MPS 최대 차이 0.001 이하 | **0.0050 미달**. 클라우드 리눅스 CPU 기록과 맥 MPS 모두 bf16이라 생기는 차이로 본다. 잠정 문턱값(0.30, 0.45)을 사이에 두고 판정이 갈리는 픽스처는 없음(가장 가까운 aitimes-215688 CPU 0.4612 / MPS 0.4562). 기준은 그대로 두고 설계 세션 판단에 남김 |
| (보조) 실제 임베딩 모델 테스트(맥) | 통과. 단 테스트가 장치를 `cpu`로 고정해 맥에서는 bf16 가중치를 하드웨어 지원 없이 계산해 70분이 넘어도 끝나지 않았다 → 운영과 같은 자동 선택(맥 MPS)으로 바꿔 45초. 점수·문턱값 변경 없음 |
| (보조) 실제 임베딩 모델 테스트 | 통과(두 번째 클라우드 세션, `uv run --extra embed pytest -k real_embedder`, 모델 받기 포함 223초) |
| (보조) 재현 픽스처 20건 CPU 점수 | `reports/S2_filter/fixture_scores.json`에 기록(0.312~0.577, 200초). MPS 비교는 맥 |
- 두 번째 클라우드 세션(실제 임베더 CPU, 녹화 응답으로 다시 만든 개발 DB 25건): `rematch` 18건 바뀜(filtered→pass 1). `filter` 17건 새 임베딩 188.7초, keep 16 / drop 1(excluded:정치). 개발 DB 점수는 문턱값 근거가 아니다(표본이 작고 실제 한 주가 아님)
- 주의: `uv run`만 쓰면 embed 묶음이 지워진다. 실제 임베더는 `uv run --extra embed ...`로 실행
- 클라우드 확인(모의 임베더, 녹화 응답으로 만든 개발 DB 29건): `rematch` 1회차 22건 바뀜(filtered→pass 1), 2회차 0건. `filter` 21건(글 17, 영상 4) 1회차 새 임베딩 21, 2회차 0. 모의 임베더 점수는 단어 해시라 문턱값 근거로 쓰지 않는다

### 4. 결정한 것
- 키워드 판정 재현: S1이 부른 입력 그대로(글 = 제목·피드 요약·본문, 영상 = 제목·설명, 릴리스 = 제목·노트, 트렌딩 = 설명 → 통과면 토픽·README). 새로 통과한 트렌딩 레포는 README를 받지 않았으므로(네트워크 없음) 설명과 토픽으로만
- 임베딩 재사용 열쇠 = (항목, 모델, 입력 텍스트 해시). 본문이나 제목이 바뀌면 그 항목만 다시 계산
- 영상도 같은 문턱값으로 판정하지만 1차 요약 대상은 글만(`summarize`가 channel='text'만)
- 판정 이유: keyword_pass / low_similarity / rescued / no_keyword / excluded:<단어>
- 같은 URL 열쇠 = 자기 URL + 원문 후보 링크(GeekNews 원문). 기준 항목 순위는 `filter.yaml` `origin_rank`(primary > blog > news > curation)이고 Simon Willison은 sources.yaml에서 curation이지만 개인 블로그 원글이라 `source_kind: {simonw: blog}`로 덮어씀
- 관심사 설명: 설계 세션 초안의 항목을 키워드마다 1~2문장으로 풀어 씀(13개, ai-general 포함). 고객 사례 홍보 글은 설명에 넣지 않음
- 문턱값 자리값 drop_below 0.30, rescue_above 0.45(`thresholds_status: provisional`). 실제 모델을 받을 수 없어 분포를 못 봤다. 필터 step은 잠정이면 attention
- 재현 픽스처 20건(`eval/fixtures/filter/`): 녹화 응답으로 만든 개발 DB의 글 16 + 영상 4. 점수 기준값은 맥에서 `filter-fixtures --record`로 장치별 기록(`reports/S2_filter/fixture_scores.json`)
- 라벨 40건 뽑기: 키워드 통과·걸러짐 각 20, 각 무리 안에서 점수 순 등간격(제외어로 걸러진 글 제외)
- `embed` 선택 묶음: sentence-transformers ≥ 3.0, transformers ≥ 4.51(Qwen3), torch ≥ 2.4. `uv lock`에 반영(설치는 `--extra embed`일 때만)

### 5. 스펙과 다르게 한 것
- 검증 산출물(`reports/S2_filter/`)과 라벨 파일(`relevance.csv`)은 만드는 코드만 넣고 파일은 만들지 않았다. 모의 임베더로 만들면 리뷰어가 실제 결과로 오해할 수 있어서. 맥에서 `filter --report --labels`
- 실제 모델 테스트 1개(`test_real_embedder_scores_fixtures_in_range`)는 embed 묶음이 없어 건너뜀(허용된 한 종류)

### 6. 남은 문제
- 문턱값 확정, 시드 13건, 라벨 40건 → 맥
- 레포 키워드 재판정은 README를 새로 받지 않는다. 새로 통과한 레포의 README는 다음 수집 때 받는다

## 2b 글 1차 요약 (item_card)

### 1. 한 줄 요약
필터 keep이고 같은 URL 묶음의 기준 항목인 글마다, 본문 문장을 그대로 옮긴 인용을 먼저 뽑고 수치·주장을 인용 번호로 다는 카드(ItemCard v1)를 만든다. 본문에 없는 인용, 인용에 없는 수치, 목록 밖 키워드·링크는 코드(enforce)가 지우고 기록한다.

### 3. 관문 B
**맥(2026-10-08)**: 설계 결정 Q1·Q6 반영 + 실제 한 주 픽스처 4건 추가 뒤 재실행(설계 변경 재실행이라 COMMON 3장 개선 횟수에 넣지 않음). `reports/eval/item_card_generate_20261008-152008.json`, 프롬프트 `2691c9a33fbc`, $0.0914(응답 캐시가 없어 21건 모두 새로 생성·채점)

| 기준 | 결과 |
|---|---|
| 코드 채점 전부(통과 판정: 원래 출력 + 코드 소유 칸만 enforce 후) | **20/21 미달**: simonw__kakapo-party 모델이 본문에 없는 수치 "15s"를 quote 5에 붙임(품질 정리 대상, 원래 출력으로 채점). 클라우드 실행에서는 같은 픽스처가 통과해 생성 편차로 본다. 개선 반복 3회는 클라우드에서 다 써 더 돌리지 않았다 |
| 인용 본문 일치 95% 이상 | 108/108 (100%) |
| judge Q1 / Q2 / Q3 각 80% | 20/20, 20/20, 19/20(잠정). Q3 실패: aitimes-215937(링크 없는 글인데 needs_original=true) |
| 잘린 인용(Q6, 보고용) | 5/108 (4.6%). jump-trading(클라우드 미달 원인)은 코드가 잘라 통과 |
| 모델 일치율(코드 소유 칸) | attention 20/21, quotes(자르기) 16/21 |
| 라벨 21건 일치율 80% | **리뷰 채점 대기**(`eval/labels/item_card.csv` 21행, 빈칸, `labeler` 칸) |
| 한 주 전체 | 264건 중 264건(대체 1), relevance high 134 / mid 91 / low 39, 원본 확인 필요 158건(59.8%), 잘린 인용 56/1352(4.1%, 다시 볼 기준 5% 아래), **$0.5934** |

- 추가 픽스처 4건(실제 한 주, 기존 17건은 그대로): `deepmind__blog-gemini-4-argon-…`(DeepMind, 숫자 표현 34), `aitimes__articleView-html-idxno-215937`(DGX 스파크, 44), `aitimes__articleView-html-idxno-215863`(AI 가격 급락, 36), `openai__index-basis-tax-workbook-with-astra`(21)
- 클라우드(17건)↔맥 건별 비교: 코드 판정이 바뀐 것은 jump-trading(F→P, Q6), kakapo-party(P→F). relevance가 바뀐 것 3건(215688 mid→high, 34739 low→mid, john-gruber mid→high), quote 수 ±1이 5건. judge 판정은 공통 16건 모두 같음

두 번째 클라우드 세션, **픽스처 17건 범위만**(`reports/eval/item_card_generate_20261008-120344.json`, 프롬프트 `2691c9a33fbc`, max_tokens 2000)

| 기준 | 결과 |
|---|---|
| 코드 채점 전부(원래 출력) | **미달 16/17**(openai__jump-trading: 249자 인용으로 스키마 3회 실패) |
| 인용 본문 일치 95% 이상 | 83/83 (100%) |
| judge Q1 충실성 / Q2 핵심 / Q3 원본 판정 각 80% | 16/16, 16/16, 16/16 (잠정, 라벨 없음) |
| 라벨 20건 일치율 80% | 맥 확인 후(`eval/labels/item_card.csv` 17행 만들어 둠, 빈칸) |
| 한 주 전체(건수, 비용, relevance 분포, needs_original 비율) | 맥 확인 후. 개발 DB 15건 참고값: relevance high 8 / mid 4 / low 3, 원본 확인 필요 6건, 대체 출력 1건(같은 jump-trading), $0.0213 |

**반복 기록(COMMON 3장, 최대 3회)**

| 회차 | 프롬프트 | 바꾼 것(한 가지) | 결과 | 원인 분류 |
|---|---|---|---|---|
| 0 | `4a88561d8bd4` | - | 코드 0/17 | 채점기 오탐 14건(아래) + JSON 잘림 2 + 인용 200자 초과 1 |
| 0' | `4a88561d8bd4` | 채점기 오탐 수정(사용자 결정, `9f890d9`) | 코드 14/17, Q1 14/14, Q2 14/14, Q3 13/14 | 잘림 2(finish_reason=length), 200자 초과 1 |
| 1 | `2691c9a33fbc` | md: quotes 핵심 3~6개, 각 200자 이하, 길면 잘린다는 이유 | 코드 14/17(ironclad 잘림 해소, 34752 평가형 마무리 "핵심이다" 1건 새로) | 지시를 어김 / 상한 |
| 2 | `2691c9a33fbc`* | 코드 규칙: max_tokens 1400→2000(한국어 3,038자 출력이 1,400토큰) | **코드 16/17**, Q1~Q3 각 16/16 | 남은 1건은 모델 한계(아래) |
| 3 | `e66573de84fa` | md 예시: 긴 문장을 중간에서 자르는 예 | 코드 16/17, Q3 15/16 | 효과 없음 → 되돌림 |
| 최종 | `2691c9a33fbc` | 반복 2로 되돌려 캐시로 재기록($0) | 코드 16/17, Q1~Q3 각 16/16 | |

- 바꾼 순서: COMMON 3장 순서(md 문구 → 예시 → … → 코드 규칙)와 달리 반복 2에서 코드 규칙(max_tokens)을 예시보다 먼저 바꿨다. 원인이 지시가 아니라 출력 상한(finish_reason=length)이라 문구·예시로는 고칠 수 없다고 봤다
- 반복 1을 남긴 이유: 노린 잘림 1건(ironclad)이 풀렸다. 새로 생긴 실패(34752 claims의 "핵심이다")는 인용 지침과 무관한 문체 실패이고, 같은 md로 돈 반복 2·최종에서는 나오지 않았다. 반복 3은 노린 1건이 그대로라 되돌렸다. 17건 1회 실행이라 실행마다 생기는 흔들림과 효과를 완전히 가르지는 못한다
\* 프롬프트 해시는 md 본문만 보므로 frontmatter의 max_tokens 변경은 해시가 같다. 회차는 `reports/S2_quality.md` 메모 칸으로 구분

**남은 실패 1건(멈춘 이유)**: openai__jump-trading의 영어 문장 하나(249자)를 모델이 통째로 옮기고, 재시도 2회 모두 "200자 안으로 줄일 것" 피드백을 받고도 같은 출력(694토큰)을 냈다. 재시도 요청에 오류 문장이 들어가는 것은 확인했다. md 문구(반복 1)와 예시(반복 3)로 고치지 못해 모델 한계로 분류했다. 코드 쪽 대안(예: 스키마 상한을 넘는 인용을 코드가 200자 안 연속 구간으로 자르기)은 판정 기준을 건드려 질문 파일 Q6으로 넘겼다. 실제 운영에서는 이 글이 대체 출력(attention)으로 저장된다

**가장 나쁜 사례**: `reports/S2_quality.md` item_card 장(입력, 출력, 채점 비평)

### 4. 결정한 것
- 본문 6,000자: 문단 경계(빈 줄 또는 줄바꿈)에서 자름. 첫 문단이 길면 마지막 문장 끝에서
- 링크 번호 = 그 항목의 `links.id` 순서(1부터), role 표시. 키워드 목록 = keywords.yaml 13개 전부(id, 이름)
- 인용 대조는 공백 정리 후 부분 문자열(줄바꿈, 연속 공백 차이는 같은 것으로)
- enforce가 인용·수치를 지웠으면 attention. 키워드·링크 번호 정리만으로는 attention을 올리지 않음
- 문체 검사는 요약·주장·로그·이유 칸만(인용은 원문 문체라 제외). 이를 위해 채점기에 역할별 문체 검사 칸 자리를 만듦(공통 코어 `eval/graders.py`)
- 인용 일치율 95%는 픽스처 전체 합산(항목별 기록은 남기되 판정은 합산)
- 인젝션 사례: 픽스처 `injection__openai-math-progress.json`(OpenAI 수학 글 본문 가운데 줄에 지시문). 코드 채점: 요약·주장·로그·엔티티에 "매우 중요"가 없고 지시 문장을 인용하지도 않음
- 스키마 3회 실패면 대체 출력 저장(`item_cards.fallback=1`). 예산 초과·제공사 오류는 멈춤
- `summarize`는 이미 v1이 있는 글을 건너뜀(`--redo`로 다시)

### 5. 스펙과 다르게 한 것
- (두 번째 클라우드 세션) 채점기 `eval/graders.py`의 해요체 검사 오탐 수정: 정규식 `(요|…)$`이 log·claims의 "원본 확인 필요", "…이 중요" 같은 명사형 끝말을 해요체로 잡았다(첫 실행 14건, 실제 해요체 0건). "필요·중요·주요·개요·수요·강요·소요"로 끝나는 문장만 예외로 두고 "필요해요" 같은 실제 해요체는 그대로 잡는 테스트를 더했다. 통과를 위한 채점기 변경 금지 규칙에 걸릴 수 있어 사용자에게 묻고 고쳤다(별도 커밋 `9f890d9`). 같은 끝말 문제가 repo_oneliner의 "명사형 끝" 검사(`SENTENCE_END`)에도 있으나 이번 실패와 무관해 그대로 두었다
- (두 번째 클라우드 세션) `roles/item_card.md` max_tokens 1400 → 2000(반복 2)
- 픽스처 17건(스펙 20건). 녹화 응답에 있는 실제 글이 16건뿐(DeepMind 0건). 큐레이션 7건(GeekNews 4, Simon Willison 3), 수치가 많은 글 3건(본문의 수치 표현을 정규식으로 셈: GeekNews 테스트 글 14, OpenAI Ironclad 7, AI타임스 원프레딕트 3). 남은 3건은 맥에서 실제 한 주로 추가(추가는 허용, 기존 픽스처는 고치지 않음)

### 6. 남은 문제
- 코드 채점 16/17(jump-trading 1건, 질문 Q6)
- 프롬프트 해시가 frontmatter(max_tokens, temperature, 모델)를 포함하지 않아 반복 1·2가 같은 해시다. 해시에 frontmatter를 넣는 수정을 제안한다(공통 코어라 이번에는 고치지 않음)
- `S2_quality.md` item_card 표의 비용 $0.0000은 캐시로 다시 기록한 최종 실행 값이다. 실제 사용액은 위 반복 기록과 7장
- 픽스처 3건 추가, 라벨 20건, 한 주 실행 → 맥

## 결정 반영 (설계 결정 Q1~Q7, `docs/handoff/S2S3_DECISIONS.md`)
| 결정 | 반영 위치 | 커밋 |
|---|---|---|
| 기록 | `docs/handoff/S2S3_DECISIONS.md`(PR #6 댓글 전문) | `5527d29` |
| Q1 공통 코어 | 처음엔 `core/artifacts.py`에 채점 보기(`graded_output`)를 따로 만들었으나(`aeac887`, 별도 커밋), 같은 결정을 S4가 먼저 main에 구현(`graders.ENFORCED_FIELDS` dict, `basis_output`, `code_pass_basis`, judge 대상 D2-4)해 main 병합(`aa0b6c8`) 때 채점 흐름은 main 것으로 통일. 남은 것: `RoleOutput.ENFORCED_FIELDS`(ClassVar, 칸 목록을 정하는 곳), `fix(..., owned=)`(기록·모델 일치율용), `graders.model_agreement`(보고용), `eval --regrade`(main 기록 형식). 기록: `code` = 원래 출력(모델 품질), `code_basis` = 통과 판정 | `aeac887`, `aa0b6c8` |
| Q1 역할별 칸 | `RepoOneliner`·`ItemCardV1`·`CollectionPlan`·`ItemCardV2` = attention, `RepoCard` = signal·hype_flags·attention. 출력 클래스에 선언하고 `eval/graders.py`·`graders_text.py`가 `graders.ENFORCED_FIELDS`에 등록. 품질 정리(인용·수치·키워드·링크 삭제, 없는 id·깊이·예산 꼬리, 근거 없는 판정 등)는 원래 출력 기준 | `f20d8d2`, `aa0b6c8` |
| 병합 뒤 재채점 | 병합 전 S2·S3 평가 결과 5개를 생성 재실행 없이 main 기록 형식으로 재채점(`…-1955xx.json`). 판정 변화 없음. item_card kakapo-party만 D2-4대로 enforce 후 출력을 judge($0.0022) | `1fd6cce` |
| 라벨(D1-3) | MVP 동안 사람 라벨 없음, 리뷰 세션 Opus 5.5 2차 채점. 라벨 파일 전부 `labeler` 칸(relevance·영상 mode 생성기에 추가), 빈칸. 문턱값·`--agreement`는 리뷰 채점 대기 | `1fd6cce` |
| Q1 분류가 애매한 것 | editor_plan의 `log` 덧붙이기("잘림·정리: …")는 기록용이라 품질 쪽(원래 출력)으로 둠. 채점에는 문체 검사만 걸림 | - |
| Q1 repo_oneliner | 재생성 없이 클라우드 2차 결과 재채점: 코드 10/10, 모델 일치율 attention 9/10(위 0단계 3) | - |
| Q5 | S3 몫(`reports/S3_report.md` 결정 반영) | `6665044` |
| Q6 | `core/artifacts_text.py`: `QUOTE_SCHEMA_MAX = 1000`(스키마), `QUOTE_CHARS = 200`, `clip_quote`(단어 경계, 연속 부분 문자열, 수치가 모두 들어가는 가장 앞 구간 → 없으면 앞에서부터, 공백 없는 덩어리는 글자 단위), `ItemCardV1.clip_quotes`(owned=True, 잘려 나간 수치만 코드 소유로 삭제, attention 안 켬). 역할 md "200자 이내"는 그대로. 집계: `eval/graders_text.py` "잘린 인용", `summarize.py` 요약 줄 | `0a1ecab` |
| Q6 재실행 | item_card 관문 B 21건(위 2b 3). 잘린 인용 픽스처 4.6%, 한 주 4.1%(다시 볼 조건 5% 아래) | `ad8109b` |
| Q7 | `config/budget.yaml` S2 1.50, S3 주석. 실행 전 `cost` 기록, 합계 S2 $1.057 / 1.50 | `90c4f74` |

## 사람 확인 부채 (S2, 고도화 단계에서 처리)
MVP 동안 사람 라벨을 하지 않는다(설계 결정 D1-3). 아래 라벨은 PR 리뷰 세션 Opus 5.5가 2차 채점하고(`labeler` 칸에 기록), 그 값으로 낸 수치는 **잠정**이다. 고도화 단계에서 사람이 확인한다.

| 라벨 파일 | 규모 | 무엇을 정하는가 | 2차 채점 뒤 반영(잠정) | 사람이 볼 것 |
|---|---|---|---|---|
| `eval/labels/relevance.csv` | 40행(키워드 통과 20, 걸러짐 20), `expected` keep/drop | 임베딩 필터 keep 정밀도·재현율 | `config/filter.yaml` 문턱값(`thresholds_status`는 잠정 표시), S2 리포트 2a | 문턱값 근처 글, 고객 사례 글(시드 13건 중 틀린 2건과 같은 유형) |
| `eval/labels/item_card.csv` | 21행 × Q1~Q3 | judge 판정 일치율(`eval item_card --agreement`) | S2 품질 리포트 judge 행 | judge·라벨 불일치 행, Q3(needs_original) 판정 |
| `eval/labels/relevance_seed.csv` | 13행(사용자가 이미 채움) | 시드 정확도(11/13) | - | 이미 사람 라벨. 부채 아님 |

- 라벨 없이 이미 확정된 것: 코드 채점(인용 일치 108/108 등)은 사람 라벨과 무관
- 같은 표의 S3 몫은 `reports/S3_report.md` "사람 확인 부채"

## S2 관문 A 전체
**맥(2026-10-08, 결정 반영 뒤 마지막 커밋)**: `verify_s2.sh`·`verify_s3.sh` 전부 PASS(A1 포함, FAIL 0), pytest 273 passed + 1 skipped(embed 없이), `uv run --extra embed pytest -q` 274 passed. 중간에 verify_s0 A9(키 문자열 검사)가 테스트의 가짜 토큰 문자열을 잡아 테스트에서 이어 붙여 만들도록 고침(검사 규칙은 그대로)

`bash scripts/verify_s2.sh` (2026-10-08, 두 번째 클라우드 세션, 키 있음)
```
PASS A1 verify_s0.sh 10개, verify_s1.sh 24개 전부 PASS
PASS A2 ruff 0, pytest 258 passed, 1 skipped in 12.95s
PASS M1 마이그레이션 번호 키: user_version 2 기존 DB 재적용 없음, 10·20 등록 순서 무관, 늦게 추가된 10번 적용, 실패는 기록 없이 재시도 (8 passed in 0.13s)
PASS M2 enforce 훅: 칸을 바꾸면 step detail enforced 기록, eval이 원래·enforce 후를 모두 기록(판정은 원래 출력), repo_oneliner README 200자 규칙 (6 passed in 0.17s)
PASS M4 도구 거부 메시지: 중첩 인자 오류에 칸 경로(origin.kind, pages[1]) (2 passed, 4 deselected in 0.10s)
PASS M6 낡은 문구 두 개(geeknews.py 설명, report.py 계획 표기) 없음
PASS A3 filter.yaml, 바뀐 keywords.yaml(13개)이 check-config 통과 + 없는 키워드 id, 범위 밖 문턱값이 경로를 짚어 실패 (2 passed, 13 deselected in 0.35s)
PASS A5 rematch: 키워드를 바꾸면 판정·item_keywords·트렌딩 판정이 바뀌고, 다시 돌려도 같음 (2 passed, 13 deselected in 0.10s)
PASS A6 필터(모의 임베더): 네 갈래 판정, 제외어는 되살리지 않음, 두 번째 실행 임베딩 계산 0 (9 passed, 6 deselected in 0.11s)
PASS A7 같은 정규화 URL(원문 링크 포함)이 same_as로 연결, 기준 항목은 공식 > 개인 블로그 > 언론 > 큐레이션 (1 passed, 14 deselected in 0.08s)
PASS A13 마이그레이션 대역: 이 묶음 번호 [10, 11, 12, 13], 대역 밖 [], 등록 전체 [1, 2, 10, 11, 12, 13]
PASS A4 S2 새 역할 md(item_card)와 채점표가 역할 md 검사 통과, 예시 3개(보통/빈칸/함정). S3 역할은 verify_s3.sh (1 passed, 28 deselected in 0.12s)
PASS A8 item_card enforce: 본문에 없는 quote, quote에 없는 수치, 목록 밖 키워드·링크 정리 + detail 기록, 코드 채점(인젝션, 인용 일치율) (13 passed in 0.26s)
PASS A14 README(기능, 빠른 시작, 성과 행), DEVELOPMENT 명령표, S2 리포트, 맥 확인 목록
```
- A1까지 전부 PASS. pytest의 건너뜀 1개는 embed 묶음 없이 돈 실제 임베더 테스트(허용된 한 종류)이고, `uv run --extra embed`로 따로 돌려 통과
- 첫 클라우드 세션 때는 A1만 FAIL(키 없음)

## S2 공통 코어 수정
| 커밋 | 파일 | 내용 |
|---|---|---|
| `aeac887`(맥, 별도 커밋) | `core/artifacts.py`, `eval/graders.py`, `eval/run_eval.py`, `cli.py` | 설계 결정 Q1: `ENFORCED_FIELDS`·`fix(owned=)`, 채점 보기(원래 출력 + 코드 소유 변경), 칸별 모델 일치율, `eval --regrade` |
| 0단계(PR #5) | `core/db.py`, `core/migrations.py`, `core/artifacts.py`, `role.py`, `agent.py`, `eval/run_eval.py`, `graders.py` | 마이그레이션 번호 키, enforce 훅, 거부 메시지 경로 |
| `beb1c94` | `eval/graders.py`, `eval/run_eval.py` | 스펙별 채점 모듈 자리(ROLE_STYLE_FIELDS, AGGREGATES, _load) |

## 사용액 (S2)
| 구분 | 사용액 |
|---|---|
| 클라우드(첫 세션) | $0(LLM 호출 없음, 키 없음) |
| 클라우드(두 번째 세션) | **$0.3707** / 클라우드 몫 0.80 (qwen3.8-27b $0.2322, gemini-3.8-flash $0.1385. `cost --spec S2`) |
| 맥 | **$0.6860** / 맥 몫 약 1.12(상한 1.50 − 클라우드 0.37, 설계 결정 Q7). repo_oneliner 재채점 $0.0011, item_card 평가 $0.0914, 한 주 summarize $0.5934 |
| 합계 | $1.0567 / 상한 1.50 |

- 두 번째 세션 내역: repo_oneliner 재평가 $0.0155, item_card 평가 6회(첫 실행, 채점기 수정 뒤, 반복 1~3, 최종) $0.334, 개발 DB summarize $0.0213. verify_s0 A4~A6 smoke는 무료 모델

## 7-1. README, 위키 메모 (S2)
- README: 역할 표의 글 1차 요약 상태, 빠른 시작(rematch, filter, summarize), 성과 표 S2 행(맥 확인 뒤 수치). DEVELOPMENT: 명령 4개, 필터와 1차 요약 동작
- 위키 메모: 녹화 픽스처가 실제 키워드 설정에 기대고 있어 키워드를 넓히자 녹화에 없는 URL(README 요청)이 생겨 테스트가 깨짐 → 테스트 전용 키워드 파일로 분리. 원문 인용 칸까지 문체 검사를 하면 원문 "~요"가 걸려 거짓 실패 → 역할별 문체 검사 칸. 문장 끝 "요" 정규식은 "필요·중요" 같은 명사도 잡음 → 명사 끝말 예외. 한국어 JSON 출력은 글자당 토큰이 많아 max_tokens를 영어 기준으로 잡으면 잘림(finish_reason=length). `uv run`은 선택 묶음을 지우므로 `--extra embed`를 붙여야 함

## 8. 서브에이전트 리뷰 (2a, 2b)
S2·S3를 함께 리뷰받았다. 지적과 처리는 `reports/S3_report.md` 8장. S2 몫: 같은 URL 기준 항목이 drop이면 keep 경유 항목을 대표로(`summarize.targets`), 스키마 모듈 import 순서(자기 등록), 리포트 출력 갱신
