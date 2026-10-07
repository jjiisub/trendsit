# S1 리뷰 반영 (S2~S3 0단계와 S4 시작 조건)

> 작성: 2026-10-08. S1 PR #3은 설계 세션 리뷰 후 병합됐다(리뷰 코멘트는 PR #3). 아래는 리뷰 지적 중 다음 스펙에서 처리할 것이다. 어느 묶음이 맡는지 항목마다 적었다.
> 묶음 A = S2~S3(`docs/handoff/S2S3_TASK.md`), 묶음 B = S4(`docs/handoff/S4_TASK.md`).

## 1. 고칠 것

### M1 마이그레이션을 번호 키 등록 방식으로 (중간, 묶음 A 0단계)
- 지금 `core/db.py`는 목록 순서 방식(`MIGRATIONS[version:]`, `PRAGMA user_version`)이다. 두 브랜치가 각자 목록 끝에 추가하면 두 번째 병합 때 번호가 겹친다
- 바꾸는 것
  - `trendsit/core/migrations.py` 새 파일: `MIGRATIONS: dict[int, str]`(번호 → SQL). 기존 두 개는 1, 2번 그대로 옮김
  - 적용 기록 테이블 `schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT)`
  - 처음 실행 때 `schema_migrations`가 비어 있고 `user_version`이 N이면 1..N을 적용된 것으로 기록(기존 DB 보존, 다시 실행하지 않음)
  - 적용: 등록된 번호 중 기록에 없는 것을 번호 오름차순으로 하나씩. 지금의 `executescript`는 먼저 커밋해 버려 트랜잭션이 되지 않으므로, 연결을 `isolation_level=None`으로 두고 `BEGIN` → 문장을 하나씩 실행 → `schema_migrations` 기록 → `COMMIT`(실패하면 `ROLLBACK`). 빈 번호 허용. `user_version`은 적용된 최대 번호로 맞춰 두되 판단에는 쓰지 않음
  - 번호 대역(COMMON 9장): S2~S3 = 10~19, S4 = 20~29. 다른 대역끼리는 서로 의존하지 않는다(어느 쪽이 먼저 적용돼도 같은 결과)
- 테스트: (1) user_version 2인 기존 DB → 다시 적용 없음, 기록 1·2 생김 (2) 10번과 20번을 어느 순서로 등록해도 둘 다 적용 (3) 20번이 이미 적용된 DB에 나중에 10번이 추가돼도 10번 적용 (4) 실패한 마이그레이션은 기록되지 않고 다음 실행 때 다시 시도
- 같은 PR에서 병행 충돌을 줄이는 자리도 만든다: `pyproject.toml`에 빈 `[project.optional-dependencies]` 표, `core/artifacts.py`의 INPUTS·OUTPUTS를 스펙별 모듈에서 합치는 줄(`# S2~S3`, `# S4` 표시), `cli.py`에 스펙별 `register(sub)`을 부르는 자리(S4 몫은 모듈이 없으면 건너뜀)
- 이 작업과 M2의 훅은 **작은 별도 PR(`s2-0-base`)로 먼저 병합**한다. 묶음 B는 DB 없는 부분을 먼저 하다가 이 PR이 병합되면 main을 받아 20번대를 추가한다

### M2 코드 규칙 훅과 repo_oneliner attention (중간, 묶음 A 0단계)
- repo_oneliner 관문 B가 코드 9/10으로 미달: README가 한 줄뿐인 Images360에서 attention이 흔들림. 판단 기준이 모델에게만 있었다. 지켜야 할 것은 코드
- 공통 코어 수정(별도 커밋, PR 설명 맨 위에 "공통 코어 수정"):
  - `RoleOutput.enforce(self, inp, ctx) -> Self` 기본 구현은 그대로 반환. `run_role`/`run_agent`가 스키마 검증 뒤, 저장 전에 호출
  - enforce가 칸을 바꾸면 step detail에 `enforced: [{field, before, after, rule}]`를 남긴다. 평가(`eval`)의 코드 채점은 **enforce 전 원래 출력**과 **enforce 후 출력**을 둘 다 기록하고, 통과 판정은 원래 출력 기준(모델 품질을 숨기지 않게)
  - 이후 역할의 코드 규칙(인용이 본문에 있는지, confirmed에 인용이 있는지, 과열 규칙 등)은 모두 이 훅으로
- repo_oneliner: 정리한 README 본문(`readme_head.text`)이 200자 미만이면 `attention=true`로 고정. 기준 숫자는 상수 이름으로 두고 리포트에 적음
- 그다음 repo_oneliner 관문 B 재실행(캐시로 대부분 0원) → `eval --agreement`(사용자 라벨 10행, 이 묶음과 함께 채워 둠)

### M3 DNS 재바인딩 틈 막기 (낮음, 묶음 A 3단계 도구 전에)
- safe_fetch는 검사 때 푼 주소와 실제 연결 때 푼 주소가 다를 수 있다
- 검사에서 통과한 IP로 연결을 고정한다(호스트 헤더와 TLS SNI는 원래 호스트 이름 유지). httpx 전송 계층에서 연결 주소만 바꾸는 방식이면 된다. 리다이렉트마다 다시 풀고 다시 고정
- 테스트: 검사 뒤 다른 주소를 돌려주는 가짜 리졸버로 연결 주소가 검사한 IP인지 확인

### M4 도구 인자 거부 메시지에 필드 경로 (낮음, 묶음 A 3단계)
- 6주차 모델 비교에서 작은 모델의 도구 호출 실패 원인이 중첩 인자 형식이었다. 거부 메시지에 pydantic 오류의 필드 경로(`origin.kind: 허용 값 아님`)를 넣는다. 공통 코어 `agent.py` 수정이므로 0단계 PR에 함께 넣어도 된다

### M5 키워드 조정 (낮음, 설계 세션)
- 사용자가 수집 샘플(`reports/S1_collection.md` 5장)을 표시한 결과로 설계 세션이 `config/keywords.yaml`을 고쳐 main에 넣는다. 코드 세션은 keywords.yaml을 고치지 않는다
- 방향(2026-10-08 사용자): AI 시장 경향과 개발 실무·경험 글도 관심 범위. 키워드는 넓은 1차 그물로 두고, 정밀한 판단은 S2 임베딩 필터와 글 1차 요약의 관련성으로 한다
- 묶음 A는 S2 2a에서 바뀐 keywords.yaml로 `collect`의 키워드 판정을 다시 계산하는 명령을 만든다(수집을 다시 하지 않고 저장된 본문으로, `rematch`)

### M6 낡은 문구 (낮음, 묶음 A 아무 커밋)
- `collect/sites/geeknews.py` 설명의 "메인(점수순)" → 실제 방식(`past?day=` 날짜당 1페이지)
- `collect/report.py` 19행의 계획 표기 "RSS + list_pages ?page" → 실제 방식

## 2. 유지할 것 (S1에서 정한 것)
- GeekNews는 `past?day=` 목록 페이지만(날짜당 1페이지, 점수·댓글 수 저장, 자기 글 제외). RSS, 상세, 메인은 쓰지 않음. 봇 방어(Turnstile)를 우회하지 않음
- 녹화 HTTP 픽스처로 오프라인 재현(녹화에 없는 URL은 차단). 새 네트워크 코드도 같은 방식
- 걸러진 항목도 지우지 않고 이유와 함께 저장
- 단계 사용액은 max(키 기준, 실행 기록 합). 같은 키의 다른 사용(수업 실습 등)도 키 기준에 잡히므로 단계 상한 쪽은 보수적으로 움직임. 정상

## 3. 리포트 질문에 대한 답 (S1 리포트 6장)
| 질문 | 답 |
|---|---|
| Images360 attention | M2 코드 규칙 |
| GeekNews `pages_per_day` | 1 유지. 하루 신규 건수 표를 보고 사용자가 조정 |
| 키워드 오탐 | M5 |
| DNS 재바인딩 | M3 |

## 4. 관문 A 추가 (verify_s2.sh. M3만 verify_s3.sh)
| # | 항목 | 확인 방법 |
|---|---|---|
| M1 | 마이그레이션 등록 | 1장 M1 테스트 4종 |
| M2 | enforce 훅 | 훅이 칸을 바꾸면 step detail 기록, eval이 전·후를 모두 기록, repo_oneliner 200자 규칙 테스트 |
| M4 | 거부 메시지 경로 | 중첩 인자 오류에 필드 경로 포함(테스트) |
| M6 | 낡은 문구 | `grep`으로 두 문구가 없음 |
