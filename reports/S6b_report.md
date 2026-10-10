# S6b 리포트: 자동 실행 (매일 밤 분석, 월요일 브리핑·발행, main 전용 실행 폴더)

기준 main `ab82389`, 브랜치 `s6b-ops`. 명세 `docs/handoff/S6b_TASK.md`. 구현 런 `004-s6b` 1라운드(A1).

## 진행 체크리스트
- [x] S-1 마이그레이션 40, publish, weekly 거부, 비용 꼬리표(`core/budget.py`는 별도 커밋 `995d288`) (B6~B9)
- [x] S-2 ops nightly·weekly, ops.yaml, 계획 후보 제외 (B1~B5, B10)
- [x] S-3 실행 폴더·래퍼·plist, 임시 예약 제거, README, 리포트 (B11, B12)
- [ ] 런 뒤 실제 따라잡기 1회(7장). 워크플로우 밖, 이 리포트 작성 시점에는 하지 않음

## 1. 한 줄 요약
`trendsit ops nightly`(따라잡기 범위의 날마다 수집 → 필터 → 요약 → 계획 → 글·영상·레포 분석, 한 단계가 실패해도 다음 단계 계속), `ops weekly`(지난 ISO 주차 브리핑 → 성공하면 `publish`), `publish --week W`(사이트 빌드 → `weeks.status='published'`)가 동작하고, 잠금(flock)·멱등 재실행·비용 꼬리표 `RUN-<주차>`(주당 $1.50)·main 전용 실행 폴더·launchd plist 2개가 갖춰졌다. launchd 등록은 하지 않았다(README 명령으로 사용자가). 워크플로우 안 유료 호출 0회.

## 2. 관문 A 결과
`bash scripts/verify_s6b.sh`(= `.workflow/gate.sh`) 종료 코드 0, 약 11초.

```
PASS A1 ruff: All checks passed!
PASS B1 따라잡기 범위(이전 행 없음, 이어서, 10일 밀림, 범위 빔, --day, C-1) (6 passed, 17 deselected in 0.21s)
PASS B2 단계 순서·인자·--spec 주차 꼬리표·video만 --extra video·빈 큐면 video 없음 (2 passed, 21 deselected in 0.17s)
PASS B3 부분 실패: 나머지 단계 계속, 종료 코드 1, partial, summary_json 칸 (2 passed, 21 deselected in 0.19s)
PASS B4 잠금: nightly 즉시 종료 코드 3·skipped·days [], weekly 대기 상한 뒤 3 (3 passed, 20 deselected in 1.56s)
PASS B5 계획 후보에서 digest 있는 영상, 그 주 repo_card 있는 레포 제외 (2 passed, 21 deselected in 0.18s)
PASS B6 비용 꼬리표 RUN-주차 상한, 틀린 형식·없는 스펙 거부 (7 passed, 3 deselected in 0.19s)
PASS B7 마이그레이션 40: 행·current_run_id 보존, published 저장, 다른 값 CHECK 실패 (1 passed in 0.02s)
PASS B8 publish: done 주 빌드 0 → published, 빌드 1 → 상태 그대로, open 주 → 2 (1 passed, 9 deselected in 0.17s)
PASS B9 published 주 weekly 거부 2·행 수 그대로, --force는 실행 (2 passed, 8 deselected in 0.20s)
PASS B10 ops weekly: 지난 주 계산, 실패 시 발행 없음, 이미 발행이면 아무것도 안 함, --force 없음 (7 passed, 16 deselected in 0.21s)
PASS A2 ops 테스트 전체(CLI 연결 포함) (34 passed in 1.94s)
PASS B11 임시 저장소: setup 두 번에 worktree 1개·data·site 링크, 래퍼(pull 실패에도 실행·종료 코드 전달·main 아니면 3), plist lint·경로·시각
PASS B12 임시 예약 파일 없음, README 자동 실행 절, check-config의 ops.yaml 검증, 리포트 8장
```
게이트 밖에서 전체 `uv run pytest -q`: 580 passed. 이전 스펙 `verify_s0~s5.sh`는 돌리지 않았다(무겁고 명세 게이트 밖). `verify_s5.sh`의 B7 `--help` 스냅숏은 의도대로 달라진다(6장).

## 3. 관문 B 결과
해당 없음(LLM 역할 변경 없음, 명세 7장).

## 4. 결정한 것 (명세 9장 "구현 시점 기본값" 포함)
- **잠금 구현**: `fcntl.flock`(비차단) on `data/locks/ops.lock`. 프로세스가 죽으면 OS가 풀어 준다. weekly는 5초 간격으로 `weekly_lock_wait_min`분까지 재시도
- **로그**: 회전 없음, 날짜별 파일 `data/logs/ops/<YYYY-MM-DD>-<nightly|weekly>.log`(단계 명령, 표준 출력·오류 전체, 종료 코드·초). 래퍼의 pull·sync·시작·종료 줄도 같은 파일
- **큐 임시 파일**: `data/tmp/video-queue-<날짜>.json`, 지우지 않음(작음)
- **`plan show` 빈 배열 판정**: 종료 코드 0이고 표준 출력이 JSON 배열 `[]`면 video 단계를 건너뛰고 `exit 0`으로 기록. `plan show`가 실패(계획 없음 등)하거나 JSON이 아니면 video 단계 실패로 기록
- **`uv sync --extra video --extra embed`**: 명세는 `--extra video`만 적었다. `uv sync`는 정확 동기화라 `embed`를 지정하지 않으면 sentence-transformers·torch를 지워 `filter`(기본 임베더 real)와 `weekly`(묶기)가 깨진다. `uv run`은 임시 폴더 실험으로 확인한 대로 추가 묶음을 지우지 않으므로(명세대로 단계 명령은 `uv run [--extra video]`) setup과 래퍼의 sync만 두 묶음으로 했다
- **`ops weekly`의 runs 행**: `kind='ops-weekly'`(안쪽 `weekly` 명령이 만드는 `kind='weekly'` 행과 구분), spec `RUN-<주차>`, `summary_json={"week","steps":[{name,day,exit,sec,error?}]}`. 이미 발행·잠금 실패·실패·성공 모두 행을 남김(이미 발행은 status ok)
- **nightly ②③의 `--until`**: 명세는 "어제". 실제 처리하는 범위의 마지막 날(`days[-1]`)로 했다. 정상 운영에서는 어제와 같고, 7일 상한으로 잘린 따라잡기나 `--day D` 손 실행에서 범위 밖 날까지 요약하지 않는다
- **PATH**: 래퍼는 `PATH` 뒤에 `/opt/homebrew/bin:/usr/local/bin`을 붙인다(launchd 기본 PATH에 uv 없음, 이미 PATH에 있으면 그것이 먼저)
- **publish의 빌드 명령**: 명세대로 `python3 site_src/build.py`(실행 폴더 `uv run` 안이라 PATH의 `python3`는 그 환경 것)
- **`weekly` 거부 검사는 단계 명령(`select`·`write`·`review`)에도** 적용하고 같은 `--force`를 줌(내부적으로 같은 함수)
- **테스트 파일 8번째 기존 파일**: `tests/test_s2_migrations.py`의 마이그레이션 대역 검사 `n <= 39`를 `n <= 49`로(COMMON 9장이 S6에 40~49를 줌). 검사를 약하게 한 것이 아니라 새 대역을 반영

## 5. 스펙과 다르게 한 것
- 4장의 `uv sync` 묶음(video + embed)과 ②③ `--until`의 마지막 날 기준. 그 밖에는 명세대로

## 6. 남은 문제, 다음 스펙 제안
- **[결정 필요] 실행 폴더의 `git pull --ff-only`와 추적 파일 `data/make_data.py`, `data/trendsit-example.json`**: main에 `data/` 아래 추적 파일 2개가 있어, 실행 폴더에서 `data/`를 작업 폴더로 링크하면 git은 그 파일들을 "지워진 상태"로 본다. 임시 저장소 실험으로 확인: **main이 이 두 파일 중 하나를 바꾸면 pull이 "local changes would be overwritten"으로 실패**하고, 명세대로 "기존 코드로 계속"하므로 실행 폴더가 옛 코드에 머문다(로그에 `git pull 실패`). sparse-checkout, skip-worktree, assume-unchanged로 막아 봤으나 심볼릭 링크 너머에 같은 이름 파일이 실제로 있어 소용없었다. 지금은 두 파일이 거의 안 바뀌어 실사용에 영향 없음. S6a가 `data/trendsit-example.json`을 바꾸거나 없앨 때가 위험하다. 기획 세션이 정할 것: 추적 파일을 `data/` 밖으로 옮기거나 S6a에서 같이 처리
- 병합 뒤 `reports/S5-1/help_before.txt` 스냅숏과 `verify_s5.sh`의 B7(`CLI --help 전부 불변`)은 새 명령(`ops`, `publish`)과 `weekly --force` 때문에 달라진다(의도한 변경). 이 파일은 S5-1a 리팩터 불변 스냅숏이라 손대지 않았다. 갱신 여부는 리뷰·기획이 판단
- `repo-analyze --week W`는 명세대로 매일 같은 규칙 큐(상위 10개)를 다시 돌린다. 편집장 계획의 `repo_queue`를 `--queue`로 넘기거나 카드가 있는 레포를 건너뛰면 비용이 줄 텐데 명세 5.2 단계 ⑦이 아니라 제안으로만 남긴다
- `cluster --week W`는 `weeks.status`를 `clustered`로 덮으므로 발행된 주에서 실수로 돌리면 발행 상태가 풀린다(명세 5.5는 `weekly`만 거부). `weekly --force`를 끝낸 뒤 `published_at`은 그대로 남고 status만 `done`이 된다(C-3은 `publish` 쪽 불변식으로만 지킴)
- `--day D`로 손 실행한 날이 가장 늦은 날보다 뒤면 다음 밤 따라잡기 범위가 그 날 뒤로 간다(5.2의 "가장 늦은 날" 규칙 그대로). 명세가 말한 용도(실패한 옛 날 다시 돌리기)에서는 문제 없음
- 작업 중 untracked 폴더 `docs/reference/s6_design/`가 작업 폴더에서 사라졌다(01:27경). 이 런은 건드린 적 없고 `trendsit-design/claude/s6_design`에 같은 이름이 있어 기획 세션이 옮긴 것으로 보인다

## 7. 사용액과 실제 1회 따라잡기
- 워크플로우 안 유료 호출 **$0** (가짜 실행기·임시 DB만. 실제 `ops nightly`·LLM·네트워크 호출 없음)
- 런 뒤 실제 1회(`ops nightly`, `RUN-2026-W42` 상한 $1.50): **미실행** — 워크플로우 밖에서 구현 세션이 한다. 결과(날마다 단계 종료 코드·시간, 사용액, 영상 처리 수, 실패 단계 원인)는 이 장에 추가할 것

### 7-1. README 갱신, 위키 메모
- README: 현재 상태 줄, 빠른 시작에 "자동 실행 (S6b)" 절(setup, `launchctl bootstrap` 2줄, 임시 예약 `bootout` 1줄, 로그 위치, 종료 코드, 손 실행), 폴더 구조에 `ops/`, 로드맵 S6b 체크(S6a 남김)
- 위키 메모: ① `uv sync`(정확)와 `uv run`(추가 묶음 유지)의 차이 때문에 sync에 두 묶음을 모두 둔다 ② git worktree + 링크한 `data/`와 main의 추적 파일이 충돌한다(6장)

## 8. impl-workflow SUMMARY 요약
- 구현 라운드 A1: 한 번에 게이트 통과. 리뷰·QA 라운드, 잔여 open, optional, 거부 판정은 오케스트레이터 SUMMARY로 채워진다(이 시점에는 없음)
- 복잡도 예산(§3.4): 변경한 기존 파일 **8/8** (`cli.py`, `cli_brief.py`, `core/budget.py`, `core/migrations.py`, `core/config.py`, `deep/plan.py`, `README.md`, `tests/test_s2_migrations.py`; 삭제 2: `scripts/collect_temp.sh`, `scripts/com.trendsit.collect-temp.plist`), 새 파일 **12/12** (`trendsit/ops.py`, `trendsit/cli_ops.py`, `config/ops.yaml`, `ops/launchd/` plist 2, `scripts/run_ops.sh`, `scripts/setup_run_worktree.sh`, `scripts/verify_s6b.sh`, `tests/test_ops.py`, `tests/test_ops_publish.py`, `tests/test_migration_40.py`, `reports/S6b_report.md`), 새 의존성 0, 금지 구조(작업 큐·플러그인·재시도 프레임워크) 없음, 공통 코어 수정은 `core/budget.py` 한 곳을 별도 커밋(`995d288`)으로
