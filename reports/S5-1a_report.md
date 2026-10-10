# S5-1a 리포트: 고침·정리 (동작 버그, 효과 없는 설정, 죽은 코드)

기준 main `a259b99`, 브랜치 `s5-1a-fix`. 명세 `docs/handoff/S5-1a_TASK.md`.

## 1. 한 줄 요약
프롬프트·코드 검사 결과·CLI `--help`는 한 바이트도 바꾸지 않고(A15~A17), 예산 초과 멈춤·`read_more` 열쇠·실행 요약 상태 같은 동작 버그를 고치고, 효과 없는 설정 키와 호출되지 않는 코드를 지웠다. LLM·임베딩 호출 0회.

## 진행 체크리스트
- [x] S-1 측정 도구 2개 + "전" 스냅숏(main `a259b99` 코드 기준) + `--fast`, A15~A17
- [x] S-2 동작 고침 F-1·F-7·F-27, F-2·F-20(공통 코어 별도 커밋), F-17·F-32·F-33 (A19~A21)
- [x] S-3 설정 키(5.7), 죽은 코드·방어 코드(5.8), verify 헬퍼(5.10) (A18, A22, A23)
- [x] S-4 리포트·README·COMMON.md 6.1-1 동기화 (A24)

## 2. 관문 A 결과
전체 `bash scripts/verify_s5.sh`(A1 포함) 종료 코드 0, A1~A24 전부 PASS(A1 PASS 73개, pytest 544 passed, 건너뜀 0). 런 중 게이트는 `--fast`(A1만 건너뜀).

## 3. 관문 B
없음(프롬프트 불변, 명세 7장).

## 4. 결정한 것
- `--help` 전체 스냅숏은 `scripts/verify_s5.sh`의 `help_all`이 만든다(하위 명령 목록은 도움말에서 읽음, `COLUMNS=100`).
- `--older-than` 기본값은 `video.yaml retention_days`(argparse default는 None, `--help` 문구는 C-4로 그대로라 "기본 7"이 설정과 어긋날 수 있음).
- 멈춘 run은 `weeks`를 건드리지 않고(행이 없으면 `open`으로만 생성) 브리핑 읽기본도 쓰지 않는다. weekly 중간의 `weeks.status` clustered/selected 쓰기는 없앴다.
- 요약 `status` 어휘 `ok` → `done`, `weeks.status`는 요약 상태에서 파생(partial → written).
- 선별에서도 `PriceUnknown`을 멈춤 사유로 잡는다.
- `device_flips`·`score_band`는 `cmd_filter_fixtures` 안으로 넣고 `tests/test_s2a.py`는 같은 규칙을 테스트 안에 정의해 맞춤. 지우는 기능을 검사하던 `test_missing_spec_modules_are_skipped`는 함께 삭제.
- `tools/web.py` fetch_page 깊이는 `hasattr` 방어만 제거(`execute_tool`에서 값을 넘기는 경로가 없음).
- verify 중첩 실행 제거는 `verify_s5`가 s1~s4를 `--reuse <폴더>`로 불러 이미 나온 s0~s1 출력과 종료 코드를 쓰게 함(환경변수·SKIP 없음, PASS 줄 그대로). 단독 실행 판정은 그대로.

## 5. 스펙과 다르게 한 것
- 복잡도 예산: 변경 파일이 40을 넘을 것으로 보여 멈추고 보고했고, 사용자가 상한을 60으로 올림(명세 개정 `e17bea8`).
- 위 `device_flips`, fetch_page 깊이 재호출.

## 6. 남은 문제, 다음 스펙 제안
- 규칙 정리·중복 제거·md 정리는 S5-1b.

## 7. 사용액
$0 (LLM·임베딩 호출 없음).

## 7-1. README 갱신 내역
"현재 상태"에 S5-1a 정리 반영 문장 추가. 위키 메모: 명세 변경 파일 상한 40은 명세 자신의 작업량(약 56)과 어긋났음.

## 8. impl-workflow SUMMARY 요약
- 런 `001-s5-1a`: 구현 1(예산 멈춤 후 재개) → 리뷰 A1(open 6) → 수정(5 fixed, 1 거부) → 리뷰 A2(open 1) → 수정 → 최종 리뷰 C1(Critical·High 0). QA 대상 AC 없음(Phase B 생략)
- 복잡도 예산: 변경 56/60 파일(handoff 문서·스냅숏 제외), 새 파일 4/4, 삭제 1, `trendsit/` +146/−245, 새 의존성·옵션·환경변수·예외 클래스 0
- 잔여 open: 런 종료 시 1건(Low, A19 선별 경우 테스트가 `PriceUnknown`만 던짐) → PR 리뷰 반영에서 해결
- 거부: `tools/web.py` fetch_page 깊이 재계산(F-19) 유지 — 값을 넘기려면 `ToolOutput`/`AgentState` 필드 추가가 필요해 3.4 금지 구조. `resolve`는 읽기 전용이라 결과 같음(리뷰 3회 제기)
- optional(구현 안 함, 사용자 판단):
  - 예산 중단 run도 묶기 리포트와 `eval/labels` decide·aliases csv를 씀(사람 라벨 덮어쓸 수 있음)
  - 토픽 전부 실패(`LLMError` 등) run도 `current_run_id`가 되어 직전 정상판을 밀어냄
  - `test_s2a`가 `device_flips` 복사본만 검사(제품 규칙 미검증)
  - 골든이 변하는 실DB(W41 진행 중)에 기대 코드 변경 없이 A16이 깨질 수 있음
  - 0토픽 run이 `failed`·현재판, weekly 중간 `weeks.status`(clustered/selected) 기록 없어짐, `--older-than` 도움말 "기본 7" 고정, 코드가 안 읽는 스키마 키 `note`
  - 골든의 `write_topic` 입력 조립 복사, 남은 방어 코드(`plan` None, 루프 안 `decider` None, `github.py` `getattr(state,"extras")`)·설정 복사 기본값(`translit`, `broad`) → S5-1b 후보
  - 그 밖 품질 Low(docstring "추세", 빈 줄, 함수 안 import, A20·A21 `-k` 전체 수집, F-4·F-8·F-24 설정 읽기 테스트 없음)

### 8-1. PR 리뷰 1차 반영 (기획 세션, C-19 사용자 확정, 커밋 `867e034`)
워크플로우 밖에서 손으로 고쳤으므로 `code-reviewer`를 1회 돌렸다(정확성·명세위반 0건, `.workflow/001-s5-1a/R1-review.md`).
- R1: 요약 `status == "failed"`(전부 실패, 토픽 0개 포함)면 `weeks.status`·`current_run_id`를 바꾸지 않는다. `cmd_weekly`는 읽기본을 쓰지 않고 stderr 한 줄을 내며 종료 코드 1이다(명세 5.12 "그 밖 0"에서 바뀐 부분). `until`(select/write) 단계 명령은 전과 같다. `test_summary_status_failed`는 이제 `weeks` 행이 바뀌지 않았는지 확인한다
- R2: `ctx.stopped`면 라벨 시트(`write_label_sheets`)를 쓰지 않는다. `pipeline.run_weekly` 묶기 단계와 `cmd_cluster` 둘 다 해당한다. 묶기 리포트는 전처럼 쓴다. `test_budget_stop_cluster`는 labels가 생기지 않았는지 확인한다
- 사소: A19 선별 경우를 `BudgetExceeded`·`PriceUnknown` 둘로 매개변수화했고, `select.py` docstring에서 "추세"를 지웠다
- 전체 `verify_s5.sh`: 종료 코드 0, A1~A24 PASS, pytest 545 passed, 건너뜀 0, 2분 50초. A15~A17은 불변이다
- 반영 리뷰의 optional(구현 안 함):
  - R1의 CLI 경로(종료 코드·stderr·읽기본 생략), 0토픽, until 예외를 `run_cmd`로 검증하는 테스트가 없음. R2의 `cmd_cluster` 경로 테스트도 없음
  - 현재판 미갱신 판정이 `pipeline._close`와 `cmd_weekly` 두 곳에 있음
  - until 단계에서 전부 실패하면 그 run이 현재판이 되고 종료 코드는 0(리뷰 R1이 정한 그대로)
  - `--topic` 실행에서 시작하지 않은 토픽은 실패로 세지 않음
  - 선별 중 예산이 초과되어도 대체 계획을 계산한 뒤 버림
  - `path`가 조건부로만 할당됨(실제로는 안전)

## 9. verify_s5 실행 시간 전후
| | 전체 `verify_s5.sh` | `--fast` |
|---|---|---|
| 전(명세 13장, `10abef6`) | 36분 6초(real 2166s) | 없음 |
| 후(`s5-1a-fix`, 런 뒤 1회) | **2분 51초**(real 171s) | 약 36~54초 |
| 후(리뷰 반영 `867e034`) | 2분 50초(real 170s) | |

줄어든 것은 s2~s4가 s0·s1을 다시 부르던 중첩 실행(F-23)이다. 판정 결과는 전후 같음(A1 PASS 73개).
