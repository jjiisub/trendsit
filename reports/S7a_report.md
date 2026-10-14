# S7a 리포트

## 1. 한 줄 요약
`/runs/`가 주차별 표(5열) → 주차를 누르면 날 → run 표(자동/수동·결과·시간/비용·상태, 하위 run은 `└`) → run 1건(수치 레일 + 접힘 없는 단계 목록: 누가, 한 줄 결과, decide 판정·선별 이유·토픽별 작성⇄검수 체인과 반려 표)으로 바뀌었고, 매일 02:00 `ops nightly`가 끝나면 사이트만 다시 만들어(`rebuild_site`, `publish --site-only`와 같은 코드) 실행 기록이 그날 것으로 갱신된다. 새 기록(DB 칸·테이블·로그)과 LLM 호출은 없다.

## 2. 관문 A 결과
`bash scripts/verify_s7a.sh`(A0~A11, 0원) 전 항목 PASS는 구현 세션 마지막 실행 기준(원문은 `.workflow/009-s7a/A1-impl.md`). 게이트 전체 소요 시간은 그 보고서에 적는다. 항목별 수단:
- A1~A3(S-1): `tests/test_ops.py`·`tests/test_s7a.py`·`tests/test_export.py`. A4~A5(S-2): `tests/test_s7a.py` 화면 파싱. A6·A7: `site_src/check.py --fixture`(27항목, Chromium·WebKit 375·768·1280) + 실DB 사본 export·build·check(A6b)
- A8: pytest 전체(건너뜀 0), `verify_s6a.sh`, `verify_s6b.sh`. `verify_s6-1.sh`(개정 A2 포함)는 게이트 밖에서 S-3 끝 1회: 아래 6장 "verify_s6-1 결과"
- A9: build.py 601줄(≤700), build_runs.py 234(≤500), export.py 221(≤350), export_runs.py 449(≤450), check.py 468(≤480), 함수 ≤60줄, `render_run` 0, 버린 CSS 조각 0, `<details>` 0, 새 환경 변수 0
- A10(실측 QA)은 qa-verifier 몫. `reports/S7a/shots/`에는 구현 세션이 픽스처 빌드를 Chromium 1280/375로 찍은 5장(`fixture_*.png`)만 있다(A11의 4장 조건용). QA가 실DB 캡처로 채운다
- A11: README 단락, `CLAUDE.md` 진행 블록 줄, `AGENTS.md` 출력 형식 줄, 이 리포트 8장

## 3. 관문 B 결과
없음(LLM 호출 0, 사용액 $0).

## 4. 결정한 것 (9장 "구현 시점 기본값" + 추가)
- `build_runs.py`가 `build.py` 도구를 쓰는 방식: `render_all(b)`에 build 모듈을 인자로 넘긴다(`sys.modules[__name__]`). `build.py`는 `python site_src/build.py`로도 실행돼 `from build import …`를 하면 두 번째 모듈이 생겨 `C`가 갈라지므로
- 토픽 블록 체인 글자: writer·writer_revise·critic은 steps `text` 그대로(`writer 절 5개, …`), 코드 검사는 `code 반려 n`(그 revise에 해당하는 반려 라운드가 code일 때 그 이슈 수), 중간 중단 기록은 `code stopped`(코드 행에 상태가 없어 runs 상태 어휘로), 끝은 `code <status>`(확인 필요 수가 있으면 뒤에 숫자). 반려 표 "수정" 열은 writer_revise `changed`의 같은 loc `action`(edit·delete·add), 없으면 `-`
- `item_cards v2`·`repo_cards` 한 줄: `log` → `summary` → 첫 글자 칸 순. 실측 repo_cards는 `log`(풀네임으로 시작해서 풀네임이 겹치면 붙이지 않음), item_cards v2는 `log`
- 시각 열이 없는 nightly 단계의 `t`: 하위 run 시작 시각, 하위 run이 없으면 nightly 시작 시각. 여러 날 nightly의 날 단위 단계 이름은 `plan 10.10`처럼 날을 붙인다(하위 run 짝짓기는 plan run 노트의 날짜를 기준점으로 그 뒤 시작한 deep-text·video·repo-analyze run을 그날에)
- nightly label 여러 날: `nightly 10.10~10.11`
- 목록 모바일 두 줄 grid: 1줄 시각 / 자동·수동 / run / 상태, 2줄 결과(왼쪽)·시간/비용(오른쪽). FINAL 375 캡처 배치. 처음에 시간·비용을 1줄에 뒀다가 WebKit 375에서 하위 run 줄과 글자가 겹쳐 2줄로 옮겼다(009-B1-01)
- plan 단계 상세: `list` 블록(제목 칸이 계약에 없어) 항목 앞에 `text_queue / `·`video_queue / `·`repo_queue / `를 붙여 구분
- 사용자 결정: 토픽 1개 재실행 run 쪽은 그 run 것만(누적치 안 씀, NG-6). 결과 칸은 `topics 1 / steps n`, `writer ⇄ critic` 단계 line은 그 run의 토픽 블록에서(`topics 1 / rounds <final_round> / code_rejects <반려 수> / critic_rejects <비평 반려 수> / check_topics <0|1>`), `summary`는 `published`만(현재판이면 발행 토픽 수, 아니면 null이고 둘 다 null이면 레일 없음)
- weekly `summary.published`는 `weeks` 행 기준 현재판 run이고 그 주가 이번 export에 담길 때만(= 사이트에 실리는 토픽 수 = `weeks[].topic_count`), 아니면 null
- 라벨의 괄호 꼬리("(중단: C-21 …)")는 뗀다(note가 서술형이라 D-11)
- 검수 지적 등 자유 글에 섞인 근거 id(`it:8#q5`, `[og:982#q4]`)는 export에서 `it 8`·`og 982` 꼴로 바꾼다. 실DB에서 check M-2가 걸려 발견(스펙 5.7의 `item <n>` 규칙을 지적·이유 글에도 확장)
- 시간대 없는 끝 시각(실DB 1건 `2026-10-14 06:59:08`)은 KST로 보고 `+09:00`을 붙인다
- nightly 끝 재생성은 `finally` 안이 아니라 그 뒤(정상 종료 경로)에서 부른다(리뷰 009-A1-09 거부). `finally`에 넣으면 SIGTERM(launchd 종료)으로 `SystemExit`가 올라오는 경로에서도 재생성(하위 프로세스, 최대 step_timeout_min)이 돌아 종료가 launchd의 강제 종료 대기시간을 넘기고 중간에 SIGKILL로 끊긴다. 일반 예외 경로는 이미 `failed`로 마감된 run이라 재생성할 이유도 없다. 호출은 `nightly()`가 넘기는 `rebuild=True`일 때만이라 `ops weekly`의 따라잡기 nightly는 안 부른다(5.1-1: weekly는 publish가 빌드)
- `rebuild_site(db, runner, with_week)`: publish가 공유하려고 `with_week` 인자를 더했다. 오류 메시지는 둘 다 `사이트 재생성 실패: …` 한 형식(기존 publish의 `export 실패`·`사이트 빌드 실패` 문구는 없어짐, 테스트는 종료 코드만 봄)
- `trendsit publish`는 `--week`와 `--site-only` 중 하나가 없으면 종료 2. `--site-only`는 `step_timeout_min`을 timeout으로 넘기고 임시 파일은 `site.json.<pid>.new`(잠금 없이 이름만 고유)
- run 단위 격리: 한 run의 상세 계산이 예외면 그 run은 `summary` null·`steps` []로 내고 stderr 한 줄, 모르는 nightly 단계 이름은 line만(`exit n`)

## 5. 스펙과 다르게 한 것과 이유
- gate.js 1280 셀 줄바꿈 측정에서 ③ steps 줄(`tr.tr-steps`)은 뺐다. 먼저 예외 없이 가는 길을 시도했으나(③ 글자 줄이기) 실DB 사본 실측(1280, 결과 칸 폭 약 263px)에서 10.9 ③ 줄의 결과 칸이 129자라 4줄, 10.8이 92자라 3줄로 나온다(`collect ×7 (ok 3, partial 4) / deep-text ×1 / filter ×4 / plan ×1 / summarize ×3 (ok 2, running 1) / video ×25 (ok 24, running 1)` 꼴). kind 7종 × 상태 수라 한 줄에 넣을 길이가 아니고 FINAL 캡처도 같다. 같은 사본에서 ③ 줄을 뺀 나머지 `.rt` 셀(nightly·weekly·publish 줄)은 줄바꿈 0이다. 그래서 예외를 유지한다(셀 높이 실측: 4.0줄·3.0줄)
- 이 nightly 자신의 `export + build` 단계는 그 nightly의 export 시점에 `summary_json.site`가 아직 없어 그 run 쪽 화면에는 다음 재생성(다음 nightly 또는 `publish --site-only`) 때부터 나온다(5.1-1 "결과는 summary_json.site로만 남긴다"와 export가 먼저 도는 순서의 귀결)
- C-4 금칙 문자열 검사는 생성 HTML 전체를 본다(`sk-`는 키 모양 `sk-` + 영숫자 8자 이상만). 실DB 사본의 토픽 페이지 포함 129쪽에서 오탐 0
- 목록의 publish 줄 자동/수동 칸은 `-`(어느 쪽인지 기록이 없음)
- 지금 DB에서 weekly run 100건 중 W40·W41 외 `week` 없는 것 1건은 안 나온다(5.2 대로)
- 5.2-3 하위 run 끝 경계 ≤ → <(사용자 결정 10/14, 연속 nightly 중복 합산). 시작 경계는 `>=` 그대로, 비교는 `_iso(finished_at)` 거침
- nightly 끝 재생성 호출 위치: 명세는 `finally` 안이었으나 그 뒤 정상 종료 경로에서 부른다(근거는 4장: `finally`에 넣으면 SIGTERM의 `SystemExit` 경로에서도 최대 step_timeout_min짜리 하위 프로세스가 돌아 launchd 강제 종료에 끊긴다. 009-A1-09 거부, 009-C1-04)
- gate.js에 375 `.rt` 셀 겹침 측정을 더했다(명세는 375 넘침 0만). B1 QA High(목록 시간·비용이 하위 run 줄과 겹침) 회귀 방지로 오케스트레이터가 지시(009-C1-12)
- export_runs.py 줄 예산 450→470(사용자 결정 10/14, 사유: run 단위 격리 + 토픽 run 자기 수치, 461줄)

## 6. 남은 문제 (미해결)
- A10(실DB 읽기 전용 캡처 QA)은 qa-verifier 몫: 토픽 1개 재실행 run, running run 줄, ③ 묶음 줄(줄바꿈 허용), 진행 주 페이지(weekly 0)를 적대적으로 볼 것
- `running`인 채 남은 run(10.9 weekly 2건, 10.7 collect 2건 등)은 글자 그대로 `running`(NG-7)
- `reports/S7a/shots/`의 `fixture_*.png`는 QA 캡처가 들어오면 지워도 된다
- 실DB export에서 일부 `cluster_pairs.reason`이 `대체 출력: LLMError`(디코드 실패 대체값)로 나온다. 오류 원문은 아니고 DB 값 그대로(D-7: 종류만). 거슬리면 S7b에서 사전으로

verify_s6-1 결과(S-3 끝 1회, A2 개정 포함): `PASS A0 … A13` 전 항목 PASS, 종료 코드 0(A2 "run 1건 머리 레일 published와 run_weeks current" 6 passed, A10 check.py --fixture 27/27, A11 verify_s6a·s6b·s5 --fast 0). B5·A23 예외 그대로.

## 7. 사용액 표
| 항목 | 값 |
|---|---|
| LLM·네트워크 호출 | 0 |
| 사용액 | $0 |

C-6 실측(실DB `data/trendsit.db`를 `sqlite3 backup`으로 읽어 만든 사본, 2026-10-14 16:3x): export 1,138,552바이트(약 1.1MB) / 상한 3MB. 발행 주 2(W40, W41) + 진행 주 1(W42), runs 108건(weekly 100 중 week 있는 것 + nightly 5 중 steps 있는 것 + ③ 묶음 날 4), export 0.5초. 실DB 사본으로 `build.py` 129쪽, `check.py --site` 26/26 PASS(관문 9 포함).

변경 파일: 기존 17(상한 18) — `trendsit/{export,ops,cli_ops}.py`, `site_src/{build.py,check.py,gate.js,trendsit.css}`, `tests/{test_export,test_site,test_ops,test_s6_1_site}.py`, `tests/fixtures/{site/site.json,s6_1/site_v2.json}`, `scripts/verify_s6-1.sh`, `README.md`, `CLAUDE.md`, `AGENTS.md`. 새 파일 6(상한 6) — `trendsit/export_runs.py`, `site_src/build_runs.py`, `tests/test_s7a.py`, `scripts/verify_s7a.sh`, `reports/S7a_report.md`, `reports/S7a/shots/`. 의존성 추가 0.

## 8. impl-workflow SUMMARY 요약
(구현 라운드 A1 기준. 리뷰·QA 라운드 결과는 `.workflow/009-s7a/SUMMARY.md`로 오케스트레이터가 이어 적는다.)
- S-1 `c1f7b87`: `rebuild_site`·nightly 끝 호출·`publish --site-only`, `export_runs.py`, 픽스처 2개 새 계약, 테스트
- S-2 `13a1486`: `build_runs.py`, CSS, check·gate 개정, 옛 문구 테스트 교체
- S-3: 회귀·구조 검사·문서·shots·이 리포트
