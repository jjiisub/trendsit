# S6b 자동 실행: 매일 밤 분석, 월요일 브리핑·발행, main 전용 실행 폴더

> 기획 세션 작성 2026-10-11(spec-planner, 원장 저장소 `.workflow/planning/s6b/ledger.md`). 기준 커밋 main `ab82389`(S5-1b 병합 `7ea92ca` + budget specs.RUN).
> 원본은 기획 폴더 `trendsit-design/claude/87_S6b_handoff.md`. budget.yaml `specs.RUN: 1.50`은 main `ab82389`에 커밋됨.
> S6의 둘째 스펙이지만 먼저 한다(S6a 사이트와 파일이 겹치지 않음). 공통 규칙은 `docs/handoff/COMMON.md`(특히 12장), 이 문서가 우선한다. 구현 세션은 `/impl-workflow docs/handoff/S6b_TASK.md .`로 돌린다.

## 0. 이 스펙이 끝나면 되는 것

| 항목 | 값 |
|---|---|
| slug | `s6b` |
| 버전 / 작성일 | v1 / 2026-10-11 |
| 문서 상태 | **확정(투입 가능)**. 시작 조건 충족(main `ab82389`) |
| 미해결 `Q-*` | 0건 |
| 선행 런 | 없음 |
| 브랜치 | `s6b-ops`, 첫 커밋 = 이 문서 |

**한 줄 목표**: 사람이 명령을 치지 않아도 매일 밤 그날 모인 글·영상·레포가 분석되고, 월요일 아침 지난주 브리핑이 만들어져 사이트에 발행된다. 개발 중인 브랜치 코드는 자동 실행에 섞이지 않는다.

- 사용자 체감 결과: launchd 두 개(`com.trendsit.nightly` 매일 02:00, `com.trendsit.weekly` 월 07:00)가 `~/Claude/projects/trendsit-run`(main)에서 돈다. 10/19(월) 07:00에 W42 브리핑이 자동으로 발행된다. 맥이 꺼졌던 날은 다음 실행이 메운다
- 발행 = 로컬 `site/` 파일 다시 만들기(웹 서버 `com.jiseop.trendsit-web`은 `site/`를 그대로 서빙하고 DB를 읽지 않음). 사이트 내용이 실제 데이터로 바뀌는 것은 S6a. 이 스펙의 발행은 지금의 `site_src/build.py`를 부르기만 한다

## 1. 맥락

- 21(CONTEXT 89~90행)의 설계: nightly = 얕게 훑기 → 편집장 계획 → 깊게(글·영상·레포), weekly = 선별·작성·검수 → 발행. 지금은 P1 임시 예약(`com.trendsit.collect-temp`, 수집만)뿐이고 분석·브리핑은 손으로 돌렸다
- 명령 단위가 제각각이다(실측): collect·filter·summarize `--since/--until`, plan·deep text `--day`, repo-analyze·weekly `--week`, video `--queue`(`plan show --day D --video-queue`)
- 결정(원장 번호)

| ID | 결정 | 근거 |
|---|---|---|
| D-1 | S6을 S6a(사이트)·S6b(자동 실행)로 나누고 S6b 먼저 | 사용자 2026-10-11 |
| D-2 | weeks.status `published`, published 주 weekly 재실행은 `--force`로만 | 64 C-8, B-2 |
| D-3 | 임시 수집 예약 제거 | 64 C-7 |
| D-4 | 잠금 파일, 멱등 재실행 | 63 4.4 |
| D-5 | 매일 02:00 수집 → 필터 → 글 요약 → 편집장 계획 → 글 분석 → 영상 분석 → 레포 분석. 월요일 주간 브리핑 | 사용자, 21 |
| D-6 | 실패 알림은 로그 + runs 표만 | 사용자 |
| D-7 | 브리핑 성공 시 자동 발행, 실패한 주는 발행 안 함 | 사용자 |
| D-8 | 자동 실행 비용 주당 $1.50(추정 $0.6~0.9) | 사용자, runs.cost_usd 실측 |
| D-9 | main 전용 실행 폴더(git worktree), data/·site/는 작업 폴더 것을 링크로 공유, 실행 전 `git pull --ff-only` | 사용자. 작업 폴더는 구현 세션이 브랜치를 바꿈 |
| D-10~D-15 | 시각, 따라잡기 범위, 잠금 대기, 부분 실패, launchd 등록은 사용자 몫, 비용 꼬리표 | 사용자위임(원장) |

## 2. 준비물 (환경 전제·검증 명령·유료 상한)

| 항목 | 값 |
|---|---|
| 실행 경로 | 개발: `~/Claude/projects/trendsit`(작업 폴더). 자동 실행: `~/Claude/projects/trendsit-run`(main worktree) |
| 런타임 | Python·uv는 기존과 같음(`pyproject.toml`). 영상 단계는 `uv run --extra video`. 새 의존성 없음 |
| 외부 도구 | `git`(worktree), `launchctl`, `plutil`(macOS 기본) |
| 환경변수 | 기존 `.env`(`OPENROUTER_API_KEY`, `GITHUB_TOKEN`) 그대로. 새 변수 없음 |
| **검증 명령(게이트)** | `bash scripts/verify_s6b.sh`(0원, 5분 이내 목표): ruff + `pytest -q tests/test_ops*.py tests/test_migration_40.py` + `plutil -lint ops/launchd/*.plist` + 6장 스크립트 확인. 실패 시 종료 코드 ≠ 0 |
| **유료 호출 상한** | 워크플로우 안 **$0**(테스트는 가짜 실행기). 런 뒤 실제 따라잡기 1회(7장)는 `RUN-2026-W42` 꼬리표, 상한 $1.50(D-8) |
| launchd 등록 | 자동 모드가 막는다. 구현은 plist·설치 명령만 만들고, 등록·해제는 사용자가 README 명령으로(D-14) |

## 3. 범위

### 3.1 한다
1. `trendsit ops nightly`: 따라잡기 범위의 날마다 5장 단계를 순서대로 실행, runs에 `kind='nightly'` 기록
2. `trendsit ops weekly`: 지난 ISO 주차 weekly → 성공하면 `publish`
3. `trendsit publish --week W`: 사이트 빌드 → weeks.status `published`, `published_at`
4. `weekly`에 published 거부와 `--force`
5. 마이그레이션 40(weeks에 `published`, `published_at`)
6. 비용 꼬리표 `RUN-<ISO 주차>`와 주당 상한(`budget.yaml specs.RUN`을 꼬리표마다 따로 적용)
7. 편집장 계획 후보에서 이미 처리한 영상·레포 빼기(C-7)
8. 실행 폴더 준비 스크립트, 실행 래퍼, launchd plist 2개, 임시 예약 파일 제거, README "자동 실행" 절, 리포트

### 3.2 비목표
| # | 하지 않는 것 | 이유 | 나중 |
|---|---|---|---|
| NG-1 | 사이트 내용(export, 디자인) | S6a | S6a |
| NG-2 | 외부 알림(맥 알림, 폰, 메일) | D-6 | 사용자가 요청하면 |
| NG-3 | 실패 단계 자동 재시도(다음 밤에 같은 날 다시) | 무한 반복 위험. 수집만 하루 겹쳐 받음(5.2) | 운영 뒤 판단 |
| NG-4 | P4 4·5(편집장 계획 reason·mode, 원본 추적) | S6-1 | S6-1 |
| NG-5 | launchd 등록·해제 실행, 원격 브랜치 삭제 | 자동 모드 차단 | 사용자 |
| NG-6 | Cloudflare 캐시 비우기 | 공개 사이트 갱신 지연(최대 4시간)은 허용 | 지연이 문제가 되면 |
| NG-7 | 로컬 모델 전환, 실행 시간 최적화 | MVP 뒤(63 4.2) | 9주차 |

### 3.3 건드리지 않을 것
- `site_src/`, `site/`(빌드 스크립트를 부르기만 함), `roles/*.md`, `skills/*.md`, `eval/`, `config/models.yaml`, `config/keywords.yaml`, `config/budget.yaml`(기획 세션 소유), `trendsit/brief/`의 묶기·선별·작성·검수 로직(`weekly` 진입부의 거부 검사만 허용)
- 영역: 역할 입력·출력 스키마, 기존 마이그레이션 1~39의 내용

### 3.4 복잡도 예산
| 항목 | 값 |
|---|---|
| 변경하는 기존 파일 | ≤ 8 (`cli.py` 등록 한 줄, `cli_brief.py`, `core/budget.py`, `core/migrations.py`, `deep/plan.py`, `README.md`, 그 밖 2) |
| 새 파일 | ≤ 12 (`trendsit/ops.py`, `trendsit/cli_ops.py`, `config/ops.yaml`, `ops/launchd/` plist 2, `scripts/run_ops.sh`, `scripts/setup_run_worktree.sh`, `scripts/verify_s6b.sh`, 테스트 2~3, `reports/S6b_report.md`) |
| 새 의존성 | 금지 |
| 금지 구조 | 작업 큐·스케줄러 라이브러리, 단계 플러그인·레지스트리, 단계마다 클래스, 재시도 프레임워크. 단계 목록은 함수 안 목록 하나 |
| 품질 수준 | 프로덕션(무인 실행) |
| 공통 코어 수정 | `core/budget.py`(RUN 꼬리표)만. 작은 별도 커밋, PR 설명 맨 위 "공통 코어 수정" |

## 4. 폴더

```
trendsit/                       (작업 폴더, 기존)
  trendsit/ops.py               nightly·weekly·publish 흐름, 잠금, 따라잡기 범위
  trendsit/cli_ops.py           register(sub): ops nightly|weekly, publish
  config/ops.yaml               start_day, max_catchup_days, weekly_lock_wait_min
  ops/launchd/com.trendsit.nightly.plist
  ops/launchd/com.trendsit.weekly.plist
  scripts/run_ops.sh            launchd가 부르는 래퍼(실행 폴더 기준)
  scripts/setup_run_worktree.sh 실행 폴더 만들기(멱등)
  scripts/verify_s6b.sh
trendsit-run/                   (실행 폴더, git worktree, main)
  data -> ../trendsit/data      링크
  site -> ../trendsit/site      링크
```
- 로그: `data/logs/ops/<YYYY-MM-DD>-<nightly|weekly>.log`, 잠금: `data/locks/ops.lock`

## 5. 상세

### 5.1 설정 `config/ops.yaml`(S6b 소유)
```yaml
start_day: 2026-10-12        # 따라잡기의 가장 이른 날(W42 시작). 이전 날은 손으로 돌렸음
max_catchup_days: 7
weekly_lock_wait_min: 240    # 주간 실행이 밤 실행 끝을 기다리는 최대 시간
```
`check-config`가 이 파일을 검증한다(필수 칸, 날짜 형식, 양수).

### 5.2 `trendsit ops nightly [--day D]`
- 입력: `--day` 없으면 따라잡기 범위, 있으면 그날 하나(손 실행용, 범위 계산 생략)
- 따라잡기 범위: `last` = runs에서 `kind='nightly'`인 행의 `summary_json.days` 중 가장 늦은 날(없으면 `start_day - 1일`). 범위 = `max(last + 1일, start_day)` ~ `어제(KST)`, 앞에서부터 최대 `max_catchup_days`일. 범위가 비면 아무것도 하지 않고 종료 코드 0(runs 행은 남김, days `[]`)
- 단계(범위 전체에 한 번): ① `collect --since <첫날 - 1일> --until <오늘>`(하루 겹쳐 받아 늦게 올라온 글 보완, 중복은 기존 코드가 제거) ② `filter --since <첫날> --until <어제>` ③ `summarize --since <첫날> --until <어제>`
- 단계(날 D마다, 날짜 순): ④ `plan run --day D` ⑤ `deep text --day D` ⑥ `plan show --day D --video-queue` → 큐 파일 → `video run --queue <파일>`(`--extra video`, 큐가 비면 건너뜀 = ok) ⑦ `repo-analyze --week <D의 ISO 주차>`
- 실행 방식: 단계마다 하위 프로세스 `uv run [--extra video] python -m trendsit <명령> ... --spec RUN-<D의 ISO 주차>`(①~③은 범위 마지막 날 기준 주차). 단계 표준 출력·오류는 로그 파일에
- 단계 실패(종료 코드 ≠ 0)는 기록하고 **다음 단계를 계속**한다(C-6). 단 ①이 실패해도 ②~⑦은 돈다(이미 받은 항목 처리)
- runs 행: `kind='nightly'`, `spec='RUN-<주차>'`, `status` = 모든 단계 0이면 `ok`, 아니면 `partial`, `summary_json`:
```json
{"days": ["2026-10-12", "2026-10-13"],
 "steps": [{"name": "collect", "day": null, "exit": 0, "sec": 41.2},
           {"name": "plan", "day": "2026-10-12", "exit": 0, "sec": 12.8},
           {"name": "video", "day": "2026-10-12", "exit": 1, "sec": 903.0, "error": "마지막 오류 줄 200자"}],
 "cost_usd": 0.21}
```
- 이상 예시: 잠금을 못 얻음 → 단계 실행 없음, runs 행 `status='skipped'`, `note='잠금: 다른 ops 실행 중'`, 종료 코드 3. days는 `[]`(다음 밤이 그 날들을 다시 범위에 넣음)
- `days`에 들어간 날은 단계 일부가 실패했어도 "시도함"이다. 다음 밤 범위에 다시 넣지 않는다(NG-3). 실패한 날은 사람이 `ops nightly --day D`로 다시 돌린다

### 5.3 `trendsit ops weekly [--week W]`
- 기본 `W` = 실행 시각(KST) 기준 **지난** ISO 주차(월 07:00 실행 → 막 끝난 주)
- 잠금을 `weekly_lock_wait_min`분까지 기다린다. 못 얻으면 종료 코드 3, runs 기록만
- `weekly --week W --spec RUN-W` 실행 → 0이면 `publish --week W`, 아니면 발행하지 않고 종료 코드 1
- 이미 published면 아무것도 하지 않고 종료 코드 0(로그 "이미 발행"). `--force`는 받지 않는다(무인 실행이 발행본을 덮지 않게)

### 5.4 `trendsit publish --week W`
- 조건: `weeks.status in ('done', 'published')`. 아니면 종료 코드 2, 변경 없음
- `python3 site_src/build.py`를 하위 프로세스로 실행 → 0이면 `status='published'`, `published_at=지금(KST ISO)`. 0이 아니면 상태를 바꾸지 않고 종료 코드 1
- 이미 published인 주를 다시 publish하면 빌드하고 `published_at`만 갱신(사람이 고친 뒤 다시 올릴 때)

### 5.5 `weekly`의 published 거부
- `weekly --week W`(및 `--from-step`)에서 W가 published면 종료 코드 2, 메시지 "발행된 주: --force로 다시 실행", runs 행·DB 변경 없음
- `--force`면 그대로 실행하고, 끝나면 status는 기존 흐름대로(`done`/`failed`). 다시 발행은 `publish`로(자동 아님)

### 5.6 마이그레이션 40(S6 대역 40~49)
- weeks의 CHECK에 `published` 추가, `published_at TEXT NULL` 열. SQLite라 표 재생성(새 표 → 복사 → 이름 바꿈) 한 트랜잭션. 기존 행·`current_run_id` 보존

### 5.7 비용 꼬리표
- `--spec`이 `RUN-YYYY-Www` 형식이면 상한 = `budget.yaml`의 `specs.RUN`(1.50), 사용액은 그 꼬리표(`RUN-2026-W42` 등) 기준. 주차 꼬리표 자체는 `specs`에 없어도 허용. 그 밖의 없는 스펙은 지금처럼 거부. `BudgetConfig` 스키마는 바꾸지 않는다
- 단계 상한(`phase_total_usd`)은 그대로 함께 적용
- 넘으면 기존 `BudgetExceeded`로 그 단계가 실패 → 5.2 부분 실패 규칙(다음 단계도 같은 꼬리표라 곧 같은 이유로 실패, 기록됨)

### 5.8 이미 처리한 항목 빼기(`deep/plan.py`)
- 영상 후보: `video_digests`에 digest가 있는 `video_id`는 후보에서 뺀다(지금은 빼지 않음, 45행). 글 후보는 이미 v2 제외(65행, 유지). 레포 후보: 그 주 `repo_cards`가 있는 레포는 뺀다
- 이유: 편집장 계획은 최근 7일(`lookback_days`)을 본다. 매일 돌리면 같은 영상·레포가 매일 큐에 올라 예산 칸을 차지한다

### 5.9 실행 폴더와 래퍼
- `scripts/setup_run_worktree.sh [작업 폴더] [실행 폴더]`(기본 `~/Claude/projects/trendsit`, `~/Claude/projects/trendsit-run`): 없으면 `git worktree add <실행 폴더> main`, `data`·`site` 링크, `uv sync --extra video`. 이미 있으면 링크만 확인. 두 번 돌려도 결과가 같다
- `scripts/run_ops.sh <nightly|weekly>`: 실행 폴더로 이동 → `git pull --ff-only origin main`(실패하면 로그에 남기고 기존 코드로 계속) → `uv sync --extra video` → `uv run python -m trendsit ops <job>`. 종료 코드는 ops의 것을 그대로
- 실행 폴더에서 main이 아닌 브랜치가 체크아웃돼 있으면 실행하지 않고 종료 코드 3(로그 "실행 폴더가 main 아님")
- plist: `com.trendsit.nightly`(StartCalendarInterval 02:00), `com.trendsit.weekly`(Weekday 1, 07:00). ProgramArguments는 `/bin/bash <실행 폴더>/scripts/run_ops.sh <job>`, 로그는 `data/logs/ops/launchd.log`. 잠든 사이 놓친 실행은 깨어날 때 한 번 돈다(launchd 기본 동작)

### 5.10 불변식
| ID | 불변식 | 적용 | 위반 시 |
|---|---|---|---|
| C-1 | nightly `days`는 연속된 날짜이고 `days[0] ≥ start_day`, `days[-1] ≤ 어제(KST)`, `len(days) ≤ max_catchup_days`, 이전 nightly 행의 days와 겹치지 않음(`--day` 손 실행 제외) | ops.py | 테스트 실패 |
| C-2 | 같은 시각에 ops 실행(nightly·weekly·publish를 ops가 부른 것)은 1개 이하(잠금) | ops.py | 테스트 실패 |
| C-3 | `status='published'` ⇔ `published_at IS NOT NULL`, 그리고 그 시각 빌드 종료 코드 0 | publish | 테스트 실패 |
| C-4 | published 주의 `weekly`(--force 없음)는 종료 코드 2이고 runs·weeks·topics 행 수가 그대로 | cli_brief | 테스트 실패 |
| C-5 | `RUN-<W>` 꼬리표 사용액 ≤ `specs.RUN`(호출 전 추정 검사, 기존 장치) | budget.py | BudgetExceeded |
| C-6 | nightly에서 한 단계 실패가 이후 단계 실행을 막지 않음. 종료 코드 0 ⇔ 모든 단계 0 | ops.py | 테스트 실패 |
| C-7 | 계획 영상 큐에 digest가 있는 video_id 0개, 레포 큐에 그 주 repo_card가 있는 레포 0개 | plan.py | 테스트 실패 |
| C-8 | ops weekly는 `--force`를 쓰지 않는다(발행본을 무인으로 덮지 않음) | ops.py | 테스트 실패 |

### 5.11 실패 동작
| 종료 코드 | 조건 | 재시도 |
|---|---|---|
| 0 | 모든 단계 성공, 범위 빔, 이미 발행(ops weekly) | — |
| 1 | 단계 하나 이상 실패(nightly), weekly 실패(ops weekly, 발행 안 함), 빌드 실패(publish) | 사람이 원인 확인 뒤 손 실행 |
| 2 | 거부: published 주에 weekly(--force 없음), publish 대상이 done/published 아님 | — |
| 3 | 잠금 못 얻음, 실행 폴더가 main 아님 | 다음 예약이 다시 시도 |
- 오류 메시지는 한 줄 한국어, 로그 파일에 단계 출력 전체
- 비용 초과는 단계 실패(1)로 기록하고 `summary_json.steps[].error`에 BudgetExceeded 메시지

## 6. 관문 A (`scripts/verify_s6b.sh`, 모두 판정 수단 `스크립트`)

테스트는 가짜 실행기(단계 명령을 기록하고 정해진 종료 코드를 돌려주는 함수)와 임시 DB를 쓴다. 네트워크·LLM 호출 0.

| ID | 검증 내용 | PASS 기준 | 관련 |
|---|---|---|---|
| B1 | 따라잡기 범위 | 이전 행 없음 / last=10-13 / 10일 밀림 / 범위 빔 / `--day` 다섯 경우에서 days가 C-1을 만족하고 기대값과 같음 | C-1, 5.2 |
| B2 | 단계 순서·인자 | 2일 범위에서 기록된 명령 목록이 5.2 순서·인자(--since/--until/--day/--week/--spec RUN-주차, video만 --extra video)와 같음. 빈 영상 큐면 video 명령 없음 | 5.2 |
| B3 | 부분 실패 | collect·video가 1을 돌려도 나머지 단계가 모두 실행되고 종료 코드 1, runs status partial, summary_json 스키마(5.2 예시 칸) 일치 | C-6, 5.11 |
| B4 | 잠금 | 잠금이 잡힌 상태에서 nightly는 즉시 종료 코드 3·runs skipped·days [], weekly는 대기 상한(테스트는 1초)을 넘으면 3 | C-2 |
| B5 | 이미 처리한 항목 | digest가 있는 영상, 그 주 repo_card가 있는 레포가 계획 후보에 없음. 없는 것은 있음 | C-7, 5.8 |
| B6 | 비용 꼬리표 | `RUN-2026-W42` 사용액이 상한에 닿으면 다음 호출이 BudgetExceeded, `RUN-x` 같은 틀린 형식과 목록에 없는 스펙은 지금처럼 거부 | C-5, 5.7 |
| B7 | 마이그레이션 40 | 39까지 적용된 DB(W40·W41 행 포함)에 40 적용 → 행·current_run_id 보존, `published` 저장 가능, 다른 값은 CHECK 실패 | 5.6 |
| B8 | publish | done 주: 빌드 0 → published·published_at, 빌드 1 → 상태 그대로·종료 1. open 주 → 종료 2 | C-3, 5.4 |
| B9 | weekly 거부 | published 주 weekly → 종료 2·행 수 그대로, `--force` → 실행됨 | C-4, 5.5 |
| B10 | ops weekly | 월 07:00 기준 지난 주 계산(연말 주 포함 3경우), weekly 실패 → publish 호출 없음·종료 1, 이미 published → 0·weekly 호출 없음, 명령에 --force 없음 | C-8, 5.3 |
| B11 | 실행 폴더·래퍼·plist | 임시 저장소에서 setup 두 번 → worktree 1개, data·site가 링크. run_ops.sh는 pull 실패에도 ops 실행, main 아니면 3. plist `plutil -lint` 통과, 경로가 trendsit-run, 시각 02:00 / 월 07:00 | 5.9 |
| B12 | 정리·문서 | `scripts/collect_temp.sh`·`scripts/com.trendsit.collect-temp.plist` 없음. README에 "자동 실행" 절(setup, launchctl bootstrap 2줄, 임시 예약 bootout 1줄, 로그 위치). `check-config`가 ops.yaml 검증. `reports/S6b_report.md` 8장까지 있음 | D-3, D-14 |

## 7. 관문 B와 QA

- 관문 B 없음(LLM 역할 변경 없음). QA 대상 AC 없음(모두 스크립트)
- **런 뒤 실제 1회(워크플로우 밖, 구현 세션)**: 작업 폴더의 PR 브랜치에서 `uv run python -m trendsit ops nightly`를 1회 실행해 10/12~어제를 따라잡는다. W42 브리핑 재료를 미리 만드는 실제 작업이고 `RUN-2026-W42` 상한 $1.50 안이다. 이 실행의 runs 행이 남으므로 병합 뒤 첫 무인 실행은 그다음 날부터 이어 간다(C-1). 결과는 리포트 7장에 적는다: 날마다 단계 종료 코드·시간, 사용액, 영상 처리 수, 실패 단계 원인. 실패 단계가 코드 문제면 이 PR에서 고친다(C-19)
- launchd 등록과 첫 무인 실행 확인은 병합 뒤 사용자가 README대로(D-14). 리뷰 세션은 병합 뒤 다음 날 로그 확인을 사용자에게 안내

## 8. 단계 (커밋 단위)

| ID | 단계 | 완료 AC | 산출물 |
|---|---|---|---|
| S-1 | 마이그레이션 40, publish, weekly 거부, 비용 꼬리표(공통 코어 커밋 분리) | B6~B9 | migrations.py, cli_ops.py(publish), cli_brief.py, budget.py |
| S-2 | ops nightly·weekly, ops.yaml, 계획 후보 제외 | B1~B5, B10 | ops.py, cli_ops.py, config/ops.yaml, deep/plan.py |
| S-3 | 실행 폴더·래퍼·plist, 임시 예약 제거, README, 리포트 | B11, B12 | scripts/, ops/launchd/, README.md, reports/S6b_report.md |

## 9. 넘길 것과 미확정

- 미해결 `Q-*`: 0건
- 구현 시점 기본값(보고서 "결정한 것"에 적기): 잠금 구현(fcntl flock), 로그 회전 없음(파일 날짜별), 큐 임시 파일 위치(`data/tmp/`), `plan show` 출력이 빈 배열일 때 판정
- 병합 뒤 사용자: `bash scripts/setup_run_worktree.sh`, `launchctl bootstrap gui/$(id -u) ...` 2줄, `launchctl bootout gui/$(id -u)/com.trendsit.collect-temp`, 원격 브랜치 삭제
- 병합 뒤 기획 세션: 19·63·64 부록 C 갱신, S6a는 publish가 부르는 `site_src/build.py`를 실제 데이터로 바꾼다(발행 경로는 이 스펙 그대로)

## 13. 실측 반영 이력
| 날짜 | 런 | 발견 | 근거 | 변경한 § |
|---|---|---|---|---|
