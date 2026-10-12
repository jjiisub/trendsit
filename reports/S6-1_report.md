# S6-1 리포트

## 1. 한 줄 요약
토픽 상세가 "포인트 목록"에서 절 구조의 "한 페이지 보고서"(요약 → 핵심 수치 타일 → 절(단락·표·막대·사건 흐름·슬라이드·영상 구간) → 출처)로 바뀌었고, 작성자가 카드 인용 대신 원문 문장을 직접 근거로 1단 작성한다. 작은 보완 9건(홈 탭, 키워드 캡, 실행 1건 메타, 출처 단일 목록, 레포 메타, 실행 래퍼 fetch+reset, 대체 계획 표시, `trendsit backup`)도 함께 들어갔다.

## 2. 관문 A 결과
`bash scripts/verify_s6-1.sh` 전 항목 PASS(A0~A13), 면제·재시도 분기 없음. A10·A11의 미니 바 측정 깜빡임(A1 라운드)은 A2 라운드에서 원인을 고쳐 더는 필요 없다(6장).

(A1 라운드 실행 결과 원문은 구현 세션 보고서 `.workflow/006-s6-1/A1-impl.md`, A2 라운드는 `A2-impl.md`에 남긴다.)

## 3. 관문 B 결과
런 뒤(7장) W40·W41 재생성 뒤 리뷰 세션이 라벨로 판정(D-28). 이 보고서 작성 시점에는 아직 없음.

## 4. 결정한 것 (9장 "구현 시점 기본값" + 추가)
- 문장 나누기(`fulltext.sentences`): 줄바꿈 우선 분리 + 줄 안에서 `.!?` 뒤 공백(다음 글자가 영문/숫자/한글/따옴표/괄호)으로. 소수점·약어는 공백이 없어 안 쪼개짐(완벽한 처리는 아님)
- 전사 묶음 경계: `video_segments.start // 25 * 25`(25초 단위 내림)
- 표 셀 수치 정규화: 기존 `number_values`/`same()` 그대로(통화 기호 등은 거기서 처리)
- 타일 `note` 비었을 때: 빈 문자열 그대로 둠(화면에서 빈 `<span class="tile-s">`)
- 슬라이드 캡션에 title이 빈 경우: 화면은 `m:ss`와 `caption`만 이어 보여줌(title이 없으면 그 부분만 생략)
- `.vgo` 라벨이 긴 경우: 줄바꿈 처리를 따로 하지 않음(기존 `word-break:keep-all` 토큰 규칙에 맡김)
- `counts.written` 0일 때: 화면은 "이 실행이 쓴 토픽 0개"를 그대로 보여줌(숨기지 않음)
- 백업 파일명 시각 형식: `%Y%m%d-%H%M`(KST)
- ffmpeg 입력 파일 확장자 탐색: `data/media/<video_id>/media.*` 글롭에서 첫 번째 일치 파일
- TopicPage v2의 `visual` 칸(export): `briefing._visual_of`가 비어 있을 때도 항상 `{"type":"none"}`을 낸다(`null`이 아님, A1-impl 라운드의 서술이 틀렸음 — A3 라운드에서 정정, 007-A2-22)
- `og:`·슬라이드 판독(`sl:`) 등 여러 접두어 근거가 같은 member를 공유할 때 WriterInput 문서는 member 하나당 하나(COMMON 6.1-4 그대로, 세부 id는 줄마다 태그)
- `tests/fixtures/s6_1/digest_llamaindex.json`(A2 라운드에서 추가, 실DB `video_digests`의 `S-bRN-avZ4Q` digest `slides[]`를 읽기 전용으로 그대로 옮긴 20장 사본)

## 5. 스펙과 다르게 한 것과 이유
- `scripts/s5_1_golden.py`는 3.4 "변경하는 기존 파일" 목록에 없었지만 5.11의 B1 요구(실DB 전후 비교 → v2 픽스처 완전 일치)를 구현하려면 반드시 고쳐야 해서 수정함(건드리지 않으면 B1이 깨진 v1 API를 그대로 불러 크래시)
- **새 파일 수(007-A1-2/A2-22 정정)**: 3.4 목록(≤11)에 없는 파일이 더 있어 실제는 17개(png 제외) — `tests/fixtures/s6_1/site_v2.json`(5.9가 요구하지만 3.4 목록엔 없음), 슬라이드 픽스처 jpg 3장(`tests/fixtures/s6_1/slides/S-bRN-avZ4Q_{208,422}.jpg`, `tests/fixtures/site/slides/V1xxxxxxxxx_920.jpg`), `eval/fixtures/{writer,critic,writer_revise}/.gitkeep` 3개. jpg·gitkeep은 테스트가 실행 중에 만들 수도 있었으나(A7 ffmpeg 생성 방식) 이미 커밋됐고, 넘긴 시점에 handoff를 하지 않아 사실과 다른 "11개(≤11)"로 적혔던 것을 바로잡음
- `og:` 원본 문서: 5.2 표는 별도 `og:{item_id}` Document를 요구하지만, `evidence_docs`는 member 단위로 묶어 og 줄이 `it:{item_id}` 문서 안에 섞여 들어간다(007-A1-9/A2-11)
- `site_src/check.py`의 `a[href*="&t="]` 검사는 전체 페이지가 아니라 `.vgo`·`.vtl`·`.simg` 안으로 좁힘(글 출처 URL에 우연히 `&t=`가 있을 때 오탐 방지, 007-A2-12)
- `no_visuals=true`일 때 `<data>`에 5.2가 적은 "모든 절의 visual을 none, head_tiles만" 문장이 그대로 렌더되지 않는다. 3.4가 `core/render.py` 변경을 "수용 안 함"으로 막아 범용 bool 렌더(`no_visuals: true`)로 대체했다(의미는 `roles/writer.md` 입력 절 정적 설명으로 보완, 007-A2-9)
- `.cmpt td.em`(5.8 CSS 목록) 정의는 추가했지만, Table에 셀 단위 강조(emphasis) 데이터가 없어 `build.py`가 그 클래스를 실제로 내는 곳은 없다(007-A1-11/A2-24). 데이터 원천을 정하는 건 설계 결정이라 이번 범위에서는 CSS만

## 6. 남은 문제 (미해결)
- **verify_s5.sh B5·A23("순 감소 아님")**: S5-1 리팩터 전용 불변식으로, 이 브랜치 시작 커밋(5cca090, S6a·S6b 병합 직후)부터 이미 깨져 있었다(`git diff --stat bed7887 5cca090 -- trendsit roles skills`로 확인: 1534줄 추가 > 784줄 삭제). `reports/S6b_report.md`도 같은 이유로 verify_s5.sh 전체를 자기 게이트에서 뺐다. S6-1이 기능 스펙이라 net 코드가 느는 것은 불가피하므로, `verify_s6-1.sh`의 A11은 이 두 항목만 예외로 두고 넘어간다(값·채점표는 바꾸지 않음). 다음 사이클에서 B5·A23을 "S5-1 기준"이 아니라 "직전 스펙 기준"으로 바꾸거나 삭제하는 것을 설계 세션에 제안
- 5.7 "repos 원천 문장 정정"(F74·C-32): A1 라운드 리포트가 "미구현"이라고 적었던 것은 오류였다. `export.py`의 `_repos`는 이미 그 주 모든 `repo_trending` 행과 토픽 근거 레포를 합쳐 돌며(`[*rows, *topic_of]`), 토픽 근거가 아닌 레포만 relevant·설명 기준으로 거른다 — 정정 문장과 같은 동작이다(A2 라운드에서 확인, 006-A1-19 dup)
- `scripts/s5_eval_fixtures.py`는 v2로 포팅했으나 실DB(실제 weekly 실행 결과)가 없어 끝까지 실행해 보지 못함(런 뒤 ⑥에서 처음 실행됨)
- (A1 라운드) A10·A11의 미니 바 측정 가끔 깜빡임 — A2 라운드에서 원인을 찾아 고침(gate.js의 미니 바 측정을 `behavior()`가 쓰던 같은 페이지·컨텍스트가 아니라 독립된 새 컨텍스트에서 재도록 분리. 탭 스크롤 측정을 분리했을 때와 같은 이유). 고치기 전 바닐라 코드로도 2/4회 재현됐고, 고친 뒤 10/10회 통과(검증 방법은 A2-impl.md)

## 7. 사용액 표
`bash scripts/s6_1_regen.sh`(③ weekly W40·W41) 실행 전이라 아직 0건. **런 뒤 채움.**

## 7-1. README 갱신 내역
- 현재 상태 줄에 S6-1 한 줄 추가
- "사이트" 절에 `trendsit backup`, 슬라이드 설명 한 단락 추가
- 로드맵에 S6-1 체크 추가

## 8. impl-workflow SUMMARY 요약
(콜드 리뷰·QA 라운드 전이라 비어 있음. 리뷰 세션이 `.workflow/006-s6-1/SUMMARY.md` 생성 뒤 이 자리에 요약을 옮긴다.)
