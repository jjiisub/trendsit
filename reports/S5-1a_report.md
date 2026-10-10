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
`bash scripts/verify_s5.sh --fast` 출력은 `.workflow/001-s5-1a/artifacts/gate-final.txt`. 전체(`--fast` 없이) 결과는 런 뒤 기입.

## 3. 관문 B
없음(프롬프트 불변, 명세 7장).

## 4. 결정한 것
- `--help` 전체 스냅숏은 `s5_1_prompts.py --help-all`(새 파일 예산 절약).
- `--older-than` 기본값은 `video.yaml retention_days`(argparse default는 None, `--help` 문구는 C-4로 그대로라 "기본 7"이 설정과 어긋날 수 있음).
- 멈춘 run은 `weeks`를 건드리지 않고(행이 없으면 `open`으로만 생성) 브리핑 읽기본도 쓰지 않는다. weekly 중간의 `weeks.status` clustered/selected 쓰기는 없앴다.
- 요약 `status` 어휘 `ok` → `done`, `weeks.status`는 요약 상태에서 파생(partial → written).
- 선별에서도 `PriceUnknown`을 멈춤 사유로 잡는다.
- `device_flips`는 `tests/test_s2a.py`가 import하므로 남기고 `score_band`만 안으로 넣음. 지우는 기능을 검사하던 `test_missing_spec_modules_are_skipped`는 함께 삭제.
- `tools/web.py` fetch_page 깊이는 `hasattr` 방어만 제거(`execute_tool`에서 값을 넘기는 경로가 없음).
- verify 중첩 실행 제거는 환경변수 `VERIFY_NESTED`(verify 스크립트 안에서만)로 s1~s4의 A1 회귀 재실행을 건너뜀. 각 verify 단독 판정은 그대로.

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
런 뒤 기입 (리뷰 라운드, 잔여 open, optional 목록, 거부 근거, 복잡도 예산 사용량).

## 9. verify_s5 실행 시간 전후
전: 전체 36분 6초(명세 13장). 후: 구현 세션 측정 전체 2분 45초(`--fast` 36초). 런 뒤 최종 재측정 기입.
