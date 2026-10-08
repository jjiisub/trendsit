# S2 리포트: 0단계(S1 리뷰 반영) + 2a 필터 + 2b 글 1차 요약

> 진행 체크리스트(COMMON 8장). 맥락이 끊기면 여기서 이어 간다. S3(3c, 3a, 3b)는 `reports/S3_report.md`.
> 실행 환경: 클라우드 Claude Code 세션(리눅스, 파이썬 3.13). `OPENROUTER_API_KEY` 없음, 네트워크는 `api.github.com`과 패키지 저장소만 열림(openrouter.ai, huggingface.co, export.arxiv.org, 수집 소스 도메인은 정책상 막힘). LLM과 실제 임베딩 모델이 필요한 것은 `reports/S2S3_mac_todo.md`로.

## 진행 체크리스트
- [x] 0단계 M1 마이그레이션 번호 키 등록(`core/migrations.py`, `schema_migrations`)
- [x] 0단계 M2 `RoleOutput.enforce` 훅 + repo_oneliner README 200자 규칙 + eval 전·후 기록
- [x] 0단계 M4 도구 인자 거부 메시지에 칸 경로
- [x] 0단계 M6 낡은 문구 2곳
- [x] 0단계 병행 개발 자리(`[project.optional-dependencies]`, `artifacts.py` `_merge`, `cli.py` `_register`)
- [x] 0단계 `scripts/verify_s2.sh --stage 0`
- [ ] 0단계 repo_oneliner 관문 B 재실행(키 필요) → `--agreement`는 저장된 결과로 확인함(아래)
- [ ] 2a rematch, 임베딩 필터, URL 중복 연결
- [ ] 2b item_card

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
