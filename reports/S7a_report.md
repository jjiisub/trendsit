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
- 토픽 블록 체인 글자: writer·writer_revise·critic은 steps `text` 그대로(`writer 절 5개, …`), 코드 검사는 `code 반려 n`(그 revise에 해당하는 반려 라운드가 code일 때 그 이슈 수), 중간 중단 기록은 `code 중단`, 끝은 `code <status>`(확인 필요 수가 있으면 뒤에 숫자). 반려 표 "수정" 열은 writer_revise `changed`의 같은 loc `action`(edit·delete·add), 없으면 `-`
- `item_cards v2`·`repo_cards` 한 줄: `log` → `summary` → 첫 글자 칸 순. 실측 repo_cards는 `log`(풀네임으로 시작해서 풀네임이 겹치면 붙이지 않음), item_cards v2는 `log`
- 시각 열이 없는 nightly 단계의 `t`: 하위 run 시작 시각, 하위 run이 없으면 nightly 시작 시각. 여러 날 nightly의 날 단위 단계 이름은 `plan 10.10`처럼 날을 붙인다(하위 run 짝짓기는 plan run 노트의 날짜를 기준점으로 그 뒤 시작한 deep-text·video·repo-analyze run을 그날에)
- nightly label 여러 날: `nightly 10.10~10.11`
- 목록 모바일 두 줄 grid: 1줄 시각 / 자동·수동 / run / 시간·비용 / 상태, 2줄 결과(FINAL의 5열 순서 그대로, 시간·비용을 1줄로)
- plan 단계 상세: `list` 블록(제목 칸이 계약에 없어) 항목 앞에 `text_queue / `·`video_queue / `·`repo_queue / `를 붙여 구분
- 토픽 1개 재실행 run은 `summary` null: summary_json이 주 누적치라(NG-6) 레일에 누적 수치가 나오면 오해를 부른다. 화면은 `topics 1 / steps n`만
- weekly `summary.published`는 `weeks` 행 기준 현재판 run이고 그 주가 이번 export에 담길 때만(= 사이트에 실리는 토픽 수 = `weeks[].topic_count`), 아니면 null
- 라벨의 괄호 꼬리("(중단: C-21 …)")는 뗀다(note가 서술형이라 D-11)
- 검수 지적 등 자유 글에 섞인 근거 id(`it:8#q5`, `[og:982#q4]`)는 export에서 `it 8`·`og 982` 꼴로 바꾼다. 실DB에서 check M-2가 걸려 발견(스펙 5.7의 `item <n>` 규칙을 지적·이유 글에도 확장)
- 시간대 없는 끝 시각(실DB 1건 `2026-10-14 06:59:08`)은 KST로 보고 `+09:00`을 붙인다
- nightly 끝 재생성은 `finally` 안이 아니라 그 뒤(정상 종료 경로)에서 부른다. SIGTERM·예외로 나가는 경로에서 사이트를 만들지 않으려고. 호출은 `nightly()`가 넘기는 `rebuild=True`일 때만이라 `ops weekly`의 따라잡기 nightly는 안 부른다(5.1-1: weekly는 publish가 빌드)
- `rebuild_site(db, runner, with_week)`: publish가 공유하려고 `with_week` 인자를 더했다. 오류 메시지는 둘 다 `사이트 재생성 실패: …` 한 형식(기존 publish의 `export 실패`·`사이트 빌드 실패` 문구는 없어짐, 테스트는 종료 코드만 봄)
- `trendsit publish`는 `--week`와 `--site-only` 중 하나가 없으면 종료 2

## 5. 스펙과 다르게 한 것과 이유
- gate.js 1280 셀 줄바꿈 측정에서 ③ steps 줄(`tr.tr-steps`)의 결과 칸은 뺐다. `collect ×7 / filter ×4 (ok 3, partial 1) / …`는 실데이터에서 길이가 정해지지 않아 한 줄을 보장할 수 없고 FINAL 캡처도 줄바꿈한다. 나머지 `.rt` 셀(nightly·weekly·publish 줄)은 줄바꿈 0을 요구한다
- 이 nightly 자신의 `export + build` 단계는 그 nightly의 export 시점에 `summary_json.site`가 아직 없어 그 run 쪽 화면에는 다음 재생성(다음 nightly 또는 `publish --site-only`) 때부터 나온다(5.1-1 "결과는 summary_json.site로만 남긴다"와 export가 먼저 도는 순서의 귀결)
- check.py 금칙 문자열 검사는 `runs/`·`sources/`·`keywords/` 화면만 본다(토픽 본문은 기사 내용이라 `data/` 같은 낱말이 정당하게 나올 수 있음). C-4의 "생성 HTML 전체"보다 좁다
- 목록의 publish 줄 자동/수동 칸은 `-`(어느 쪽인지 기록이 없음)
- 지금 DB에서 weekly run 100건 중 W40·W41 외 `week` 없는 것 1건은 안 나온다(5.2 대로)

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
