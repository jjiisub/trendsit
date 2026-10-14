# S6-1 상세 페이지 개편: 한 페이지 보고서(절 구조·시각 요소·영상 타임라인) + 작은 보완 + W40·W41 재생성

> 기획 세션 작성 2026-10-12(spec-planner, 원장 저장소 `.workflow/planning/s6-1/ledger.md` D-1~D-45, 읽기용 종합은 기획 문서 90). 기준 커밋 main `e099138`(budget `specs.S6-1: 1.50`).
> 구현 세션 시작 절차: `git fetch origin && git switch -c s6-1-detail origin/main`(작업 폴더에서 `git switch main` 불가, 실행 폴더가 main 체크아웃. 지금 작업 폴더는 병합된 `s6a-site`) → 이 문서를 `docs/handoff/S6-1_TASK.md`로 복사 → 첫 커밋 → `/impl-workflow docs/handoff/S6-1_TASK.md .`
> 공통 규칙은 `docs/handoff/COMMON.md`(특히 3·12장), 이 문서가 우선한다. 시험 실행 스크립트 `.workflow/planning/s6-1/proto/`는 **참고용**이다(입력 형식·실측 근거로만. 저장소 코드가 아니고 명세가 그 구현을 따를 의무는 없다. 근거 id 형식은 시험과 다르게 계약(5.2)대로).

## 0. 이 스펙이 끝나면 되는 것

| 항목 | 값 |
|---|---|
| slug | `s6-1` |
| 버전 / 작성일 | v1.3 / 2026-10-14(v1.3: PR #14 리뷰·관문 B 1차 반영 — 5.14 신설. v1.1: 보기 확인점 3개와 런 뒤 단일 스크립트 추가, 사용자 요청. v1.2: 런 006 C2 리뷰 반영 — 5.13 부분 실패 주 발행, C-5 상한, A3·A11 판정, 3.4 예산, 5.3 시각 칸 비우기. 13장) |
| 문서 상태 | **확정(투입 가능)** |
| 미해결 `Q-*` | 0건(Q-10 소스 페이지 영상 id 노출은 다음 사이클로 보류 → 비목표 NG-8) |
| 선행 런 | `.workflow/005-s6a/`(리뷰 모드 재료: handoff 006 F74·F10·F48·F70·F09) |
| 브랜치 | `s6-1-detail`, 첫 커밋 = 이 문서 |

**한 줄 목표**: 토픽 상세가 "포인트 목록"이 아니라 **한 페이지 보고서**로 읽힌다. 요약(리드) → 핵심 수치 타일 → 절(포인트 문장이 제목, 단락 1~2개, 필요한 절에만 시각 요소 하나) → 출처. 영상 토픽은 절마다 그 구간으로 가는 타임라인 링크와 코드가 고른 그래프 슬라이드 이미지가 붙는다. 작성자는 카드 인용이 아니라 **원문 문장**을 근거로 바로 쓴다(1단). 작은 보완 7건을 첫 단계로 끝내고, W40·W41을 새 구조로 다시 써 발행한다. 10/19(월) 07:00 W42 자동 발행이 새 작성자로 돈다.

- 사용자 체감 결과: trendsit.jiseop.com의 20토픽이 새 구조(요약·개요·포인트 1 중복 없음, 수치는 타일·표·막대로, 영상 토픽은 시점 링크). 홈 탭 두 개가 같은 높이에서 멈춤. 키워드 페이지 긴 행 없음. `trendsit backup`으로 DB 사본
- 분량 목표(D-16·D-19, 시험 실측): 요약 1~2문장 150자 안팎, 절 4~7(원문이 충분할 때), 절 안 단락 1~2개·단락 2~3문장, 본문 700~2,400자

## 1. 맥락

- 원인 실측(원장 블록 0 M-1~M-9, 문서 90 §6.2): 상세가 부실한 것은 데이터가 없어서가 아니다. 원문(글당 대개 2~6천 자)은 DB `item_texts`에 있는데 작성자는 카드 인용 3~6문장(원문의 15~25%)만 받고, 작성 상한이 "1~1.5화면"이었고, 도식 조건(같은 단위 3개 이상)이 좁았다. 요약·개요가 같은 재료를 쓰게 지시돼 중복이 났다. 영상 타임라인은 DB에 있는데 export가 안 냈다
- 두 기획 세션(A: 참고 아티클·실사이트 QA 15건, B: 시안·실제 모델 시험 4회, 누적 $0.232)의 결과는 문서 90 §9 통합 표. 시안 https://claude.ai/artifact/2ZmTrtZfwUASuy6yhWK6gD, 시험 결과 https://claude.ai/artifact/VWhh5kH3LECnBmahP5ca9D
- 결정(원장 번호 그대로. 근거 A = 이 프로젝트 실측, — = 사용자 판단)

| ID | 결정 | 근거 |
|---|---|---|
| D-1 | 홈 탭 두 개 모두 맨 위(nav 보이는 위치)로, JS 없이 | A: M-8 |
| D-2 | 영상 타임라인 export + 각 시각은 `&t=초s` 시점 링크 | A: M-6 |
| D-3·D-7 | 보고서형. 포인트 목록 없이 **포인트 문장이 절 제목**(시안 B). 개요 칸 삭제, 요약이 리드 | 사용자 |
| D-4 | 시각 요소는 따로 떼지 않고 절 안에 | 사용자 |
| D-8·D-10·D-17 | 수치 타일(배치 규칙 5.8), 비교 표, 막대는 값 2개부터 | 사용자, A: WebKit 375 실측 |
| D-11·D-30·D-34 | 슬라이드 이미지는 그래프·표·수치 몰린 슬라이드만, **코드가 후보(최대 2장)**를 고르고 작성자는 후보 안에서만 배치, 자르지 않고 전체 프레임 | A: 시험에서 작성자 단독 선택 0·0·3장 |
| D-13·D-45 | 한 스펙(작은 보완 → 구조 개편), slug s6-1 | 사용자 |
| D-15·D-25 | 코드로 막는 것은 ① 숫자 표기 보존 ③ 없는 근거 id ⑥ 잘림만. 의미 없는 타일·인과 연결·발표자 이름·요약↔단락 수치 조건은 검수자 | A: 시험 v1~v3 |
| D-16·D-19·D-20 | 절은 늘어도 절 안은 간결. 요약 2문장(사건+쟁점) 150자 안팎, 홈 목록도 같은 칸 | 사용자, A: 시안 3안 |
| D-18 | 영상 단락 방식: 단락 + 그 구간 타임라인 링크 + 코드가 고른 그래프 슬라이드 | 사용자 |
| D-21·D-22·D-24 | 홈 순위 모양 구분 없음. 수치 불일치는 코드 검사가 아니라 지침. critic 1회 흐름 그대로(작성 → 검수 → 수정), 지침만 새 구조 | 사용자 |
| D-23 | W40 + W41 둘 다 재생성·발행(토픽당 약 $0.01) | A: 시험 비용 |
| D-26 | QA-6(확인 필요 모으기·간격) QA-7(고유명사 영문) QA-8(핵심 개념 칸 삭제) QA-11(출처 채널 머리 생략) QA-14(레포 태그 메타) 포함. QA-13 제외 | A: 문서 90 §3 |
| D-27 | **1단 작성**: 작성자가 원문 문장 번호를 근거로 절+단락을 바로 씀(기존 포인트 단계 없음). 기존 요약은 입력에 안 줌 | A: out_one 5/6 성공, 포인트 범위 같거나 넓음 |
| D-28 | 관문 B: W41 10토픽 + W40 영상·표 토픽 3~4개, 리뷰 세션 라벨 | 사용자 |
| D-29·D-42 | 잘림: max_tokens 4500, run_role 재시도 1회 그대로, 그래도 잘리면 `no_visuals` 입력으로 1회 더 | A: 잘림 6/25회, 도식 없이 재시도로 회복 |
| D-31 | 옛 구조 의존물(테스트·골든·verify_s5 항목·eval 픽스처·graders)은 **새 구조로 교체**. 두 구조 공존 안 함 | A: M-12 |
| D-32 | 반려 비교 화면, P4 4·5는 비목표 | A: steps.detail에 쌍 없음 |
| D-33 | 재시도 뒤에도 실패한 토픽은 failed·제외(기존 흐름) | A: write.py |
| D-35 | `trendsit backup [--tag]` 수동 명령만 | 사용자 |
| D-36 | 재생성·발행은 구현 세션이 런 뒤 확인 없이(S6a와 같음). 관문 B는 발행 뒤 | 사용자 |
| D-37 | F48: counts 머리에 "이 주 발행 n개 / 이 실행이 쓴 토픽 m개" | A |
| D-38 | 근거 id 확장: `it:#s{n}`, `rp:#f{n}`, `sl:{item_id}@{sec}`. 영상은 계약대로 item_id | A: CONTRACTS 2장 |
| D-39 | 슬라이드 프레임은 작성 시점에 뽑아 `data/slides/`에 저장(영상 파일 7일 보관) | A: video.yaml |
| D-40·D-41 | 탭 앵커는 탭 위 0높이 요소. 시각 요소는 첫 단락 뒤. 상단 "확인 필요"는 첫 ⚠로 가는 링크 | A |
| D-43·D-44 | eval 픽스처 재생성은 0원·런 뒤, judge 실행은 범위 밖. 분량 숫자는 brief.yaml → limits, md에 숫자 없음(B10) | A: M-19 |
| D-46 | 보기 확인점 3개(샘플 사이트 → 실사이트 → 첫 무인 실행), 런 뒤 DB 쓰기 단계는 스크립트 하나로 묶어 사용자 승인 1회 | 사용자 2026-10-12, A: S6a 리포트 7장(자동 모드가 DB 쓰기를 막음) |

## 2. 준비물 (환경 전제·검증 명령·유료 상한)

| 항목 | 값 |
|---|---|
| 실행 경로 | `~/Claude/projects/trendsit`(작업 폴더, 브랜치 `s6-1-detail`) |
| 런타임 | Python 3.12 + uv 기존. `site_src/build.py`·`check.py`는 표준 라이브러리만(S6a 규칙 유지) |
| 외부 도구 | `ffmpeg`(`/opt/homebrew/bin/ffmpeg` 8.1.2, 슬라이드 프레임. 없으면 슬라이드 없이 진행 + attention, 테스트는 ffmpeg 없으면 **실패**로(건너뛰지 않음)). 브라우저 측정은 S6a와 같음(Node 24 `/Users/jiseop/.nvm/versions/node/v24.18.0/bin/node`, 전역 playwright-core, WebKit·Chromium 캐시) |
| 환경변수 | 기존. 새 변수 없음 |
| **검증 명령(게이트)** | `bash scripts/verify_s6-1.sh`(0원, LLM·네트워크 호출 없음): ruff + `pytest -q`(전체, 건너뜀 0) + `python3 site_src/check.py --fixture` + 항목별 검사(6장) + 회귀 `verify_s6a.sh`·`verify_s6b.sh`·`verify_s5.sh --fast` 종료 코드 0. 실측: pytest 전체 37초(649개), verify_s6a 51초 → 전체 6분 안(15분 상한 안). 실패 시 종료 코드 ≠ 0 |
| **유료 호출 상한** | 워크플로우 안 **$0**. 런 뒤(7장) W40·W41 재생성 `--spec S6-1`: 토픽당 작성 1 + 검수 1 + 수정 ≤2회 ≈ $0.015, 20토픽 ≈ $0.3~0.4. 스펙 상한 `specs.S6-1: 1.50`(시험 $0.232 사용, 남은 약 $1.27). 넘길 것 같으면 멈추고 보고 |

## 3. 범위

### 3.1 한다
1. **작은 보완(S-1)**: 홈 탭 맨 위(D-1·D-40), 키워드 관련 토픽 5개 + "외 n개"(F70·QA-12), 실행 1건 범위 글자(D-37), 출처 채널 머리 생략(QA-11), 레포 신호 메타 줄(QA-14), 실행 래퍼 `fetch` + `reset --hard origin/main`, `setup_run_worktree.sh` origin/main, 대체 계획 표시(C-30), `trendsit backup`(D-35)
2. **근거 공급(S-2)**: 작성자 입력을 원문 문장 번호·레포 카드 사실·영상 전사 묶음·슬라이드 판독으로(5.2). 검수자 원문도 같은 id로
3. **작성자 출력 구조(S-2)**: `TopicPage` v2(summary, head_tiles, sections[heading, paragraphs, visual, slide, video_secs]) + `WriterInput` v2 + `loc_lines`·revise 위치 문법(5.3)
4. **역할 md 3개(S-2)**: writer·critic·writer_revise 새 구조 지침 + skills/diagrams.md 개정(5.4). 코드 검사 ①③⑥ + 구조 상한(5.5). 슬라이드 후보·배치·프레임(5.6)
5. **export v2(S-3)**: 토픽 칸 교체, 영상 출처 타임라인, 슬라이드 파일 복사(5.7)
6. **build·CSS·check(S-3)**: 절 구조 화면, 타일·표·막대·슬라이드·타임라인 조각, 관문 9 확장(5.8·5.9)
7. **설정·회귀 교체(S-2·S-3)**: brief.yaml `write:`·`evidence:` 개편(5.10), verify_s5 작성 항목 판정 변경, 옛 테스트·골든·eval 픽스처 교체(5.11), CONTRACTS 2장 근거 id 행 추가, AGENTS.md 출력 형식 한 줄
8. **런 뒤(S-4, 워크플로우 밖)**: W40·W41 재생성 → 발행 → 실사이트 확인 → eval 픽스처 재생성(0원) → 리포트·README → PR(7장)

### 3.2 비목표
| # | 하지 않는 것 | 이유 | 나중 |
|---|---|---|---|
| NG-1 | 반려 비교 화면(`.cmp`, 검수 초안·근거·수정 쌍 기록) | D-32. steps.detail에 쌍이 없고 검수 단계 기록 변경이 필요 | 사용자가 원하면 |
| NG-2 | P4 4·5(편집장 reason·mode, origin_trace) | D-32. 편집장 역할 변경 = 관문 B 추가 | 시연 뒤 |
| NG-3 | 홈 목록 변경(부제 한 줄, 순위 모양 구분) | D-20·D-21 기각 | 없음 |
| NG-4 | 소스 연결도, 단계·흐름 카드(B4), 2열 비교 카드(B2) | 비교 표가 대체(D-10). 사건 흐름(events)은 기존 도식 유지 | 없음 |
| NG-5 | 다크 모드, 글꼴 서브셋, Access | S6a NG-1·NG-4 | MVP 뒤 |
| NG-6 | 자동 백업(weekly 전), 보관 개수 관리 | D-35 수동만 | 필요하면 |
| NG-7 | eval judge 실행(`trendsit eval writer|critic|writer_revise`), 관문 B 코드 채점 문턱값 | D-43. 관문 B는 D-28 라벨 채점 | 다음 사이클 |
| NG-8 | 소스 페이지 "메타데이터 실패: <영상 id>" 노출 바꾸기(QA-13, Q-10 보류) | 사용자 보류 | 다음 사이클 |
| NG-9 | 슬라이드 자르기 규칙(채널별 crop) | D-34 전체 프레임 | 필요하면 |
| NG-10 | 역할 모델 변경, 검수 라운드 수 변경(3 유지), 묶기·선별 변경 | 범위 밖. `brief.yaml`의 cluster·select는 그대로 | — |

### 3.3 건드리지 않을 것
- `trendsit/collect/`, `trendsit/filter/`, `trendsit/deep/`, `trendsit/video/`, `trendsit/summarize.py`, `trendsit/core/role.py`(D-42: 재시도 흐름은 write.py에서), `trendsit/core/llm.py`, `trendsit/core/agent.py`, `trendsit/core/numbers.py`(재사용만), `trendsit/brief/cluster.py`·`select.py`·`aliases.py`·`weekly.py`
- `roles/` 중 writer·critic·writer_revise **밖**의 md 9개, `skills/style_ko.md`(참조만), `eval/judge*.md`
- `config/budget.yaml`·`keywords.yaml`·`models.yaml`·`sources.yaml`·`ops.yaml`·`video.yaml`(기획 세션 소유. `brief.yaml`은 5.10 범위만)
- `ops/launchd/`, `trendsit/ops.py`의 nightly·weekly 흐름(publish 함수도 그대로. backup은 `cli_ops.py`에 새 하위 명령, 구현은 `trendsit/core/db.py`에 함수 하나까지)
- `site_src/tokens.css` 값(새 토큰이 필요하면 멈추고 handoff), `docs/reference/s6_design/`(참고 복사본), `site_src/example/`
- 영역: DB 스키마(마이그레이션 없음. 새 저장은 파일 `data/slides/`와 기존 칸 `topic_pages.page_json`·`topics.checks_json`), 묶기·선별 입력·출력, 공개 범위, 비용 꼬리표 규칙

### 3.4 복잡도 예산
| 항목 | 값 |
|---|---|
| 변경하는 기존 파일 | ≤ 39(v1.2: 런 006 실측으로 `scripts/s5_1_golden.py`(B1 구현에 필수)·`trendsit/core/db.py`(3.3이 허용한 backup 함수) 수용. `core/render.py`는 수용 안 함 — 되돌림). 원안 ≤ 37(`.gitignore`에 `/site.sample` 한 줄 포함). 코드 12(`core/artifacts_brief.py`, `core/config_brief.py`, `brief/evidence.py`, `brief/write.py`, `brief/checks.py`, `brief/revision.py`, `brief/briefing.py`, `brief/pipeline.py`, `export.py`, `cli_ops.py`, `site_src/build.py`, `site_src/check.py`), `site_src/gate.js`, `site_src/trendsit.css`, 역할·스킬 md 4, `config/brief.yaml`, 스크립트 5(`run_ops.sh`, `setup_run_worktree.sh`, `verify_s5.sh`, `verify_s6b.sh`, `s5_eval_fixtures.py`), `eval/graders_brief.py`, `scripts/s5_gate_b.py`, 테스트 7(`test_s5_select_checks.py`, `test_s5_weekly.py`, `test_s5_evidence.py`, `test_s5_material.py`, `test_export.py`, `test_site.py`, `test_ops.py`), 픽스처 `tests/fixtures/site/site.json`, 문서 3(`README.md`, `AGENTS.md`, `docs/handoff/CONTRACTS.md`) |
| 새 파일 | ≤ 11: `scripts/s6_1_regen.sh`(7장 ①~⑤ 한 번에), `trendsit/brief/fulltext.py`(원문 조립), `trendsit/brief/slides.py`(후보·프레임), `scripts/verify_s6-1.sh`, 테스트 2~3(`tests/test_s6_1_write.py`, `tests/test_s6_1_site.py`, 선택 `tests/test_s6_1_ops.py`), 픽스처 2(`tests/fixtures/s6_1/digest_llamaindex.json`, `tests/fixtures/s6_1/topic_v2.json`), `reports/S6-1_report.md`, `reports/S6-1/golden.json`(새 구조 코드 검사 골든, 5.11) |
| 삭제 | 옛 eval 픽스처 `eval/fixtures/writer|critic|writer_revise/*.json`(런 뒤 재생성으로 교체), `reports/S5-1/golden_before.json`은 **남김**(verify_s5 B1이 더는 읽지 않음) |
| 새 의존성 | 금지(Python·npm). ffmpeg는 외부 실행 파일(subprocess) |
| 금지 구조 | 템플릿 엔진, 컴포넌트 클래스 계층, 플러그인·레지스트리, 두 스키마 공존 어댑터(D-31), 사이트 JS(측정용 gate.js 제외), 새 설정 파일 |
| 줄 수 | `build.py` ≤ 700줄(지금 566), `write.py` ≤ 450(지금 417), `checks.py` ≤ 450(지금 440). 500줄 넘는 새 파일 없음, 함수 60줄 이하(verify_s5 B4 유지) |
| 품질 수준 | 프로덕션(공개 사이트, 무인 자동 발행) |

예산은 추정이 아니라 의도다. 넘길 것 같으면 멈추고 `handoff/NNN_impl→plan.md`.

### 3.5 구현이 추가하면 안 되는 것(기본)
명세에 없는 CLI 옵션·환경변수, 추상화 계층, 한 번 쓰는 헬퍼, 일어날 수 없는 상황의 방어 코드, 바꾸지 않은 코드의 주석·타입 표기. 프로젝트별: 역할 md에 분량 숫자(D-44), 사이트 외부 요청(이미지·글꼴 자체 호스팅), 옛 칸(points·overview·concepts·contributions·diagrams) 호환 분기.

## 4. 폴더

```
trendsit/brief/fulltext.py       원문 문장·전사 묶음·슬라이드 판독·레포 사실 → 작성자 Document (5.2)
trendsit/brief/slides.py         슬라이드 후보 휴리스틱, 배치, ffmpeg 프레임 → data/slides/<video_id>_<sec>.jpg (5.6)
trendsit/brief/write.py          1단 작성 → 코드 검사 → 검수 → 수정 (잘림 no_visuals 재시도)
trendsit/brief/checks.py         새 구조 코드 검사 (5.5)
trendsit/brief/revision.py       새 위치 문법 (5.3)
trendsit/core/artifacts_brief.py TopicPage v2, WriterInput v2, loc_lines
trendsit/export.py               토픽 v2, sources.timeline, slide 파일 확인
site_src/build.py, trendsit.css  절 구조·타일·표·막대·슬라이드·타임라인 조각, 탭 앵커
site_src/check.py, gate.js       정적 검사 + 관문 9 + 탭 높이·타일 넘침
data/slides/                     슬라이드 프레임(git 제외, data/ 아래)
site/assets/slides/              build가 복사
tests/fixtures/s6_1/             digest·토픽 v2 픽스처
scripts/verify_s6-1.sh           게이트
```

## 5. 상세

### 5.1 작은 보완(S-1, 모두 0원)
| # | 항목 | 요구 |
|---|---|---|
| 1 | 홈 탭(D-1·D-40) | `#topics`·`#repos` 앵커를 `.tabs` 바로 위 0높이 요소(`<span class="tab-anchor" id="…">`, `scroll-margin-top: var(--sticky-offset)`)에 둔다. 패널 전환은 `.has-tabs:has(#repos:target) …`로 그대로 JS 0. 두 탭을 눌렀을 때 `scrollY` 차이 ≤ 1px이고 `.nav`가 화면 안(top ≥ 0) |
| 2 | 키워드(F70·QA-12) | 관련 토픽 링크 5개까지, 넘치면 뒤에 "외 n개"(글자). 정렬은 지금 순서 |
| 3 | 실행 1건(D-37) | counts `dl` 앞에 `<p class="meta">이 주 발행 n개 / 이 실행이 쓴 토픽 m개</p>`. export `runs[].counts.written` = 그 run의 `steps(role='writer', kind='code')` 수 |
| 4 | 출처(QA-11) | 채널 머리 `h3.src-g`("글 2") 제거, 목록 하나(`ol.srcs`)에 화면 번호 순. 영상 출처 아래 타임라인(5.8) |
| 5 | 레포(QA-14) | 신호 글자를 메타 줄로: `이번 주 별 +1.6k / 트렌딩 / 관련 토픽 …`(`.meta`, `" / "` 구분, 가운뎃점 없음). `needs_check`는 `.check` 유지 |
| 6 | 실행 래퍼 | `run_ops.sh`: `git pull --ff-only origin main` → `git fetch origin main && git reset --hard origin/main`(실행 폴더는 배포 전용. data·site 링크는 ignore라 보존, S6a D-19 실측). fetch 또는 reset 실패 시 지금처럼 기존 코드로 계속 + `TRENDSIT_PULL_FAILED=1`. 로그 문구 "git pull 실패" → "git 동기화 실패" |
| 7 | setup | `setup_run_worktree.sh`: 실행 폴더를 처음 만들 때 `git fetch origin` 뒤 로컬 `main`을 `origin/main`에 맞추고(`git branch -f main origin/main`, 작업 폴더가 main이 아님은 기존 guard) worktree 생성 |
| 8 | 대체 계획(C-30) | 실행 1건 화면: nightly `plan` 단계 행에 그 날 `plans.source='fallback'`이면 텍스트 끝 " (대체 계획)", weekly 행에 `briefing_plans.source='fallback'`이면 메타 한 줄 "선별 대체 계획(점수 순)". export가 `runs[].steps[].fallback: true` / `runs[].fallback_select: true`로 냄 |
| 9 | 백업(D-35) | `trendsit backup [--tag 글자]` → `data/backup/<YYYYMMDD-HHMM>[-<tag>].db`(sqlite3 `Connection.backup`, WAL 포함 일관 사본). 성공 0 + 경로 출력, 대상 폴더 못 만들거나 실패 1. 같은 이름이 있으면 덮어쓰지 않고 1 |

### 5.2 근거 공급(작성자·검수자 입력, D-27·D-38)
작성자 입력 `WriterInput` v2 = `plan`(rank, angle, relation) + `evidence: list[Document]` + `previous` + `aliases` + `limits` + `slide_candidates: list[str]`(sl: id, 0~2) + `no_visuals: bool`(기본 false. true면 렌더에 "모든 절의 visual을 none, head_tiles만" 한 줄). 기존 요약·포인트는 주지 않는다(D-27, 시험 ⑦).

| 구성원 | Document id | 줄 형식(근거 id → 그 줄만 담는다) | 상한 |
|---|---|---|---|
| 글 `it:{item_id}` | `it:{item_id}` | `[it:{item_id}#s{n}] 원문 n번째 문장`. 문장 나누기는 `fulltext.sentences()`(마침표·물음표·느낌표·"다." 뒤 공백, 줄바꿈 단위 우선). `item_texts.text`가 없거나 만료(NULL)면 **카드 인용 `it:#q{n}`**(기존 `evidence_docs`)으로 대체하고 attention 문구 "원문 없음: it:{id}" | 글당 `write.input.text_chars`(6,000자, 문장 경계) |
| 원본 문서 v2 | `og:{item_id}` | 기존 `og:{item_id}#q{n}` 그대로(원문 전체는 저장돼 있지 않음, M-13) | 기존 |
| 레포 `rp:{owner/name}` | `rp:{owner/name}` | `[rp:{name}#f{n}] 사실`: RepoCard `evidence[].fact` 순서대로, 마지막에 `why_trending`("뜨는 이유: …"), 릴리스 한 줄. 기존 `rp:{name}`(repo_field) id는 작성자에게 주지 않음 | 카드 전체 |
| 영상 `vd:{video_id}`(member) | `vd:{item_id}` | 요약 1줄(근거 id 없음, 참고만) → 타임라인 `  {sec}초 {label}[ (슬라이드)]`(id 없음) → 슬라이드 전용 수치 `[vd:{item_id}@{sec}] 발표 슬라이드 수치: …`(기존 slide_fact) → 슬라이드 판독 `[sl:{item_id}@{sec}] 제목 | 글자(500자) | 수치 | 표 있음/없음`(frame_kind=slide만) → 전사 `[vd:{item_id}@{sec}] 25초 묶음 문장들`(`video_segments` start 기준, 묶음 시작 초) | 전사 `write.input.transcript_chars`(14,000자) |

- 토픽 전체 상한 `evidence.max_tokens_per_topic`(5.10에서 14,000으로). 넘치면 기존 `cap_pack` 방식과 같은 순서(관련성 → 채널 다양성 → 출처 균형)로 **문장 단위**로 자른다
- 검수자 원문(`raw_evidence`): `it:#s{n}` → 그 문장 ± 1문장, `vd:@sec` 전사 묶음 → 그 묶음(기존 ±30초 전사·판독 로직은 slide_fact·claim id에만), `sl:` → 판독 글자 전체, `rp:#f` → 그 사실
- 저장: `topic_evidence(evidence_id, member, field, idx)`의 `field`는 **기존 CHECK 값 재사용**(단락 → `point`, 타일·표·막대 항목 → `number`, 사건 → `event`, 표·막대 설명 글 속 id → `context`). 마이그레이션 없음(실측: CHECK는 `point·number·event·context·contribution`)
- CONTRACTS 2장에 행 3개 추가(글 원문 문장 `it:{item_id}#s{n}`, 레포 사실 `rp:{owner/name}#f{n}`, 슬라이드 판독 `sl:{item_id}@{sec}`)와 "전사 묶음은 `vd:{item_id}@{sec}`(묶음 시작 초)" 한 줄

### 5.3 작성자 출력 스키마 `TopicPage` v2 (인터페이스 계약)
칸 순서(근거가 붙은 칸 먼저, 결론 나중, log·attention 끝 — COMMON 6.1-5). pydantic `_Strict`(extra=forbid).

```
Tile        {value: str, label: str, note: str, refs: list[str] 1~3}
Para        {text: str, refs: list[str] 1~4}
BarGroup    {title, context, unit, items: list[NumberItem] 2~6}          # NumberItem 기존(label, value, ref, baseline, emphasis)
Table       {title, note, columns: list[str] 2~4, rows: list[list[str]] 2~6, refs: list[str] 1~4}  # rows[i]는 columns와 같은 길이, 첫 열은 행 머리
EventGroup  기존(title, context, flow_is_point, items 2~6) — anchor 칸 없음
Section     {heading: str, paragraphs: list[Para] 1~2, visual: "none"|"bars"|"table"|"tiles"|"events",
             bars: BarGroup|null, table: Table|null, tiles: list[Tile] (visual=tiles일 때 2~3, 아니면 []),
             events: EventGroup|null, slide: str|null (slide_candidates 중 하나의 sl: id. 코드가 채울 수도 있음),
             slide_caption: str, video_secs: list[int] 0~3 (입력 타임라인의 sec), check: bool=false (코드 소유)}
TopicPage   {head_tiles: list[Tile] 0~4, sections: list[Section], summary: str, title: str, log, attention}
```
- 도식 위치 이름(`loc_lines`, 번호 0부터): `title`, `summary`, `head_tiles[i]`, `sections[i].heading`, `sections[i].paragraphs[j]`, `sections[i].bars`, `sections[i].bars.items[k]`, `sections[i].table`, `sections[i].table.rows[k]`, `sections[i].tiles[k]`, `sections[i].events`, `sections[i].events.items[k]`, `sections[i].slide`, `sections[i].video_secs`
- revise `Change.loc`은 위 이름 그대로. `value` 형식: 문자열(title·summary·heading·paragraph text·slide_caption), `Para`, `Tile`, `BarGroup`, `Table`, `EventGroup`, `NumberItem`, `EventItem`, `list[str]`(table.rows[k])、`list[int]`(video_secs). `Section` 전체 add/delete 허용(`sections[i]`), `sections` 전체 삭제는 거부
- `check`·`slide`(코드가 채운 것)는 코드 소유: 작성자 출력의 `check=true`는 enforce가 false로
- (v1.2) 시각 요소 비우기: 위치 문법에 `visual` 칸은 없다. revise 적용 뒤 절의 visual 종류 칸(bars·table·events가 null, tiles가 [])이 비면 코드가 `visual="none"`으로 맞춘다(자동 수정, 반려 아님). 하위 경로가 붙은 loc이 위 이름에 없으면 그 변경은 버리고 note(절 전체 delete는 loc이 정확히 `sections[i]`일 때만)

**실제 예시(정상, 요지)** — Haiku 토픽(글 2), 시험 1단 결과에서:
```json
{"head_tiles":[{"value":"$0.10 / $0.50","label":"입력 / 출력, 100만 토큰당","note":"10만 토큰 이하 요청","refs":["it:812#s7"]},
               {"value":"1620점","label":"GDPval-AA","note":"GPT-6 Luna 1437점","refs":["it:812#s12"]}],
 "sections":[{"heading":"10만 토큰을 넘기면 단가가 5배가 되는 구간 가격","paragraphs":[{"text":"Anthropic은 Haiku 5.5 요청을 10만 토큰 기준으로 나눠 … 했다.","refs":["it:812#s7","it:812#s8"]}],
              "visual":"table","bars":null,"table":{"title":"구간별 100만 토큰당 가격","note":"입력 / 출력, 달러","columns":["구간","입력","출력"],"rows":[["10만 토큰 이하","$0.10","$0.50"],["10만 토큰 초과","$0.50","$2.50"]],"refs":["it:812#s7","it:812#s8"]},
              "tiles":[],"events":null,"slide":null,"slide_caption":"","video_secs":[],"check":false},
             {"heading":"남은 쟁점: 실제 워크로드 비용 절감은 근거 없음","paragraphs":[{"text":"Simon Willison은 … 지적했다.","refs":["it:815#s3"]}],"visual":"none","bars":null,"table":null,"tiles":[],"events":null,"slide":null,"slide_caption":"","video_secs":[],"check":false}],
 "summary":"Anthropic이 Haiku 5.5를 출시하고 10만 토큰 이하 요청 단가를 90% 내렸다. 쟁점은 토크나이저 변경으로 같은 프롬프트의 토큰이 1.25배 느는 것이다.",
 "title":"Claude Haiku 5.5 출시, 90% 가격 인하와 토크나이저 변경","log":"절 5개, 단락 8개, 표 1개, 타일 2개","attention":false}
```
**실제 예시(이상)** — 코드 검사가 반려해야 하는 것: `head_tiles[0].value "8192 토큰"`인데 refs 문장은 "8K context" → `number_mismatch`(8192 ≠ 8000); `sections[2].paragraphs[0].refs ["vd:1291@4000"]`가 입력에 없음 → `wrong_ref`; `sections[1].visual "bars"`인데 `bars` null → `format`; `sections[0].slide "sl:274@500"`이 `slide_candidates`에 없음 → 코드가 `slide=null`로 고치고 autofix 기록(반려 아님).

**하위 호환**: 없음(D-31). `topic_pages.page_json`의 옛 구조는 읽지 않는다. 발행 주(W40·W41)를 모두 재생성하므로 export가 보는 현재판은 전부 v2. `previous_topic()`은 v2의 `summary` + `sections[].heading`을 지난 포인트로 준다. 옛 판이 남은 run은 current가 아니라 export·화면에 안 나온다.

### 5.4 역할 md 3개 + 스킬 (38 문서 1장 7항목)
공통: COMMON 6.1 섹션 순서(목표/입력/판단 기준/출력/막혔을 때/예시 3~5개), 굵게 1개 이하, `check-config` 통과. **분량·개수 숫자는 md에 쓰지 않고 `limits` 칸 이름으로**(D-44, verify_s5 B10). 시험 지침 `proto/writer_proto_one.md`를 재료로 쓰되 숫자를 limits 참조로 바꾼다.

| 역할 | 핵심 내용 | task / core_rules(3줄) | 코드가 지킬 것 | 예시 3개 |
|---|---|---|---|---|
| `writer`(1단) | 목표: 한 페이지 보고서. 원문에서 포인트를 절로 세우고 단락으로 풀어 쓴다. 근거 범위 규칙은 기존 writer.md 그대로 + 숫자 표기 보존("8K"를 "8192"로 쓰지 않음), 두 근거 인과 연결 금지, 발표자 이름은 입력 제목·요약 표기만, 고유명사 영문 원문 표기(음차 금지, 처음 나올 때 풀이). 쓰는 방식: summary 사건+쟁점, 첫 절 이번 주 사건, 마지막 절 남은 쟁점·확인할 것, 절 안 간결, 단락끼리·summary와 반복 금지. 시각 요소: 타일은 결과·성능·가격·규모만(시간·버전·날짜·개수 세기 금지), 절마다 visual 하나까지, 절의 절반 이상은 none, bars는 비교가 요지일 때(값 2개면 비교 대상이 분명할 때), table은 행×열 정보, tiles는 독립 수치, events는 날짜 다른 사건, slide는 `slide_candidates` 중에서만, video_secs는 입력 타임라인 sec만. head_tiles 수치는 절 visual에 다시 쓰지 않음 | task "위 원문만으로 이 토픽을 절 구조의 토픽 페이지로 쓴다." / 근거 id·숫자 표기 그대로 / 절 제목은 포인트 문장(명사형) / 시각 요소는 limits 안에서 꼭 필요한 절에만 | 5.5 전부 | 보통(글 2, 표 1) / 빈칸이 맞는 경우(수치 없는 토픽: head_tiles [], 모든 visual none) / 함정(숫자 표기 변경·의미 없는 타일·타임라인 초를 전사 id로 쓴 것) |
| `critic` | 기존 절차 유지(원자 사실 대조). 추가 판정: 요약↔단락 수치 조건 불일치(`number_mismatch`), 의미 없는 타일(`overuse`), 두 근거 인과 연결(`unsupported`), 발표자 이름이 입력 표기와 다름(`unsupported`), 단락끼리·summary와 같은 사실 반복(`overuse`, comment "중복"), 영문 고유명사 음차(`format`가 아니라 지적하지 않음 — 코드 정본 치환이 함) | task 그대로 / core_rules 그대로 | loc_lines v2, 이슈 7종 유지 | 보통 / 통과 / 함정(매끄럽지만 타일이 "6개월"·"V2") |
| `writer_revise` | 기존 + 위치 문법 v2(sections[i].paragraphs[j] …), `overuse` 타일·표는 비우거나 문장으로, `format`(단락 문장 수·절 수 등)은 comment대로 | 그대로 | revision.py v2 되돌림 | 보통 / 삭제 / 함정(지적 안 된 절 고치기) |
| `skills/diagrams.md` | 표를 새 구조로: 타일(독립 수치 2~3개 → limits) / 막대(같은 단위 값 2개 이상, 비교가 요지) / 표(행×열) / 사건 흐름(기존) / 슬라이드(코드 후보). "그릴지는 코드가 정한다" 문장은 "구조 상한은 코드가 검사한다"로 | — | — | — |

입력 렌더: `evidence[]`는 `<document id="it:812" source="…" title="…">` 안에 줄마다 `[근거 id] 문장`(5.2). `slide_candidates`·`limits`·`no_visuals`는 자료 뒤 과제 앞에 한 줄씩.

### 5.5 코드 검사·라운드·잘림(write.py·checks.py)
자동 수정(반려 아님): 형광 상한(summary `highlights.summary`, 단락당 `highlights.per_paragraph`, 페이지 `highlights.page[1]`, 뒤쪽부터 제거), 공백·문장부호, 별칭·음차 → 정본(기존), `slide`가 후보 밖이면 null, `video_secs`가 타임라인에 없으면 그 값 제거, `sections` 수 초과면 뒤에서 자름(그 절의 시각 요소 포함).

반려(`format`·`number_mismatch`·`wrong_ref`, 라운드에 셈):
| 검사 | 기준(brief.yaml 5.10) |
|---|---|
| 필수 칸 | title·summary 비어 있지 않음, sections ≥ `sections` 하한, 절마다 paragraphs ≥ 1, heading 비어 있지 않음 |
| 분량 | summary 문장 수 ≤ `summary.sentences[1]`, 글자 ≤ `summary.chars_max`; 단락 문장 수 ≤ `paragraphs.sentences_max`, 글자 ≤ `paragraphs.chars_max`; heading ≤ `heading_chars_max` |
| refs | 모든 refs가 토픽 근거 목록(pack)에 있음(③). 단락 refs 1~`max_refs_per_paragraph`, 타일 refs ≥ 1 |
| 숫자 표기(①) | 단락·heading·summary·title·타일 value·표 셀·막대 value·캡션의 수치(`figures` + 단위 붙은 수)가 그 칸 refs(없는 칸은 토픽 근거 전체)의 원문에 **값으로** 있음(`number_values`·`same` 재사용, 단위 환산 없음). 표 첫 열(행 머리)은 제외 |
| 시각 요소 구조 | visual과 내용 일치(bars면 bars 있음, 나머지 null·[]), bars items 2~6·단위 하나·빈 단위 금지, table columns 2~4·rows 2~6·행 길이 일치, tiles 2~3(visual=tiles), events items 2~6·날짜 형식·ref 또는 topic_id, 페이지 visual≠none 수 ≤ `visuals_max`, head_tiles ≤ `head_tiles_max`, slide 토픽당 ≤ `slides_max` |
| 문체 | summary·단락 문장 "~다", heading 명사형(문장으로 끝나지 않음), 해요체·평가어 금지(기존 `_check_style` 재사용) |

경고(검수자 입력): 절의 절반 넘게 visual≠none, 같은 단락 문장 유사도 ≥ `review.duplicate_point_similarity`, summary 문장이 어느 단락 문장과 유사도 ≥ 0.8, head_tiles 수치가 절 visual에 다시 나옴.

라운드: 기존 3라운드 흐름 그대로(코드 반려 → 검수 안 부름, 같은 이슈 2회 → check, 마지막 라운드 남은 이슈 → check). `check` 위치는 `sections[i]` 단위(단락·타일·표 이슈는 그 절), `summary`·`title`. `topics.checks_json`에 위치 이름 그대로. 코드 확인 오류가 남은 시각 요소(단위 섞임·값 불일치)는 최종판에서 뺀다(기존 `_drop_code_bad_diagrams` 방식: visual → none, 그 절 check).

잘림(⑥, D-42): `roles/writer.md` `max_tokens: 4500`. `run_role`이 잘림 1회 재시도 뒤 `RoleFailed("출력 잘림…")`을 올리면 write.py가 **같은 입력에 `no_visuals=true`**로 `run_role` 1회 더(v1.2: 내부 재시도 포함 토픽당 최대 5회 호출 — 잘림 2 + no_visuals 쪽 스키마 재시도 포함 3. 성공한 판은 횟수 때문에 버리지 않는다). 그래도 실패면 기존대로 토픽 failed + attention "작성 실패: 잘림"(D-33). 비용 기록은 `costs["writer"]`에 합산, `steps.detail`에 `{"no_visuals": true}`.

### 5.6 슬라이드 후보·배치·프레임(slides.py, D-30·D-34·D-39)
- 후보(코드, 영상 digest `slides[]`): `frame_kind == "slide"`이고 ① 25자 이하 짧은 줄(`ocr_text` 줄 단위) 20개 이상 + `numbers` 1개 이상, 또는 ② `table`이 있음. 같은 `title`은 첫 장만. sec 오름차순 최대 `slides_max`(2). id `sl:{item_id}@{sec}`
- 작성자는 `slide_candidates` 중에서만 절에 둔다. 작성자가 안 둔 후보는 코드가 붙인다: 그 sec **직전** 타임라인 구간 시작 초를 `video_secs`에 가진 절 → 없으면 `video_secs`의 최댓값이 sec 이하인 절 중 가장 가까운 것 → 없으면 첫 영상 근거를 인용한 절. 절 하나에 슬라이드 하나. visual이 있는 절에도 붙을 수 있다(슬라이드는 visual 수에 세지 않음)
- 프레임: 최종판 저장 직전에 `data/media/<video_id>/media.*`에서 `ffmpeg -ss {sec} -i … -frames:v 1 -vf "scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:-1:-1:color=white" -q:v 4 data/slides/<video_id>_<sec>.jpg`(자르지 않음, D-34). 파일이 이미 있으면 다시 만들지 않음. 영상 파일이 없거나 ffmpeg 실패면 그 슬라이드는 `slide=null`로 두고 attention "슬라이드 프레임 없음: <video_id>@<sec>"(토픽은 계속)
- `data/slides/`는 `.gitignore`의 `/data` 아래라 자동 제외. 지우지 않는다(영상 파일은 7일 뒤 지워지지만 프레임은 남아 재발행에 쓰임)

### 5.7 export v2(`trendsit export`, `data/site.json`)
최상위 8칸·weeks·repos·sources·keywords·runs·run_weeks는 S6a 그대로(repos 원천 문장 정정: **그 주 모든 수집 run 행 중 카드 relevant 또는 설명 있는 것 + 토픽 근거 레포**, F74·C-32). 바뀌는 것:

| 칸 | 값 |
|---|---|
| topics[] | `id, week, rank, lead, title, summary, relation, head_tiles[{value,label,note,refs[출처 번호 id]}], sections[{heading, paragraphs[{text, refs}], visual{type: none|bars|table|tiles|events, …기존 bars 모양(items·unit·title·context·ref) / table{title,note,columns,rows,refs} / tiles[] / events(기존 모양)}, slide{sec, title, caption, image: "slides/<video_id>_<sec>.jpg"}|null, video_secs[{sec,label,slide}], check}], sources[], channels, has_check, checks[]`. **없는 칸**: overview, points, diagrams, concepts, contributions |
| sources[] (영상) | 기존 칸 + `video_id`, `timeline: [{sec, label, slide}]`(digest 그대로) |
| runs[] | 기존 + `counts.written`(5.1-3), `steps[].fallback`, `fallback_select`(5.1-8) |

- refs 변환: 근거 id → 구성원 → 출처 번호 id(`s1`·`v1`·`g1`)는 기존 `export_topic` 방식. `sl:`·`vd:@`는 그 영상 출처
- `slide.image`는 `data/slides/<video_id>_<sec>.jpg`가 **있을 때만**. 없으면 `slide: null`
- `video_secs`는 타임라인에 있는 sec만(라벨 붙여서)
- C-2(모든 refs가 그 토픽 출처 안) 유지, 위반 시 ExportError·파일 미작성(기존)

### 5.8 build 화면(DESIGN.md 4.3 개정 + 새 조각)
토픽 블록 순서: 머리(뒤로 링크, 제목 26/500, 요약 `.ts`, 메타 줄: 채널 구성 / 후속 / **확인 필요(링크 `#chk-1`)** / 읽는 시간, 지난 흐름) → `head_tiles`(`.tiles.n{개수}`) → 절들(`section.dsec`: `h2.dsec-t` = heading, 첫 단락 `p.dp` + 인용 번호 → 시각 요소 `figure.dg`(bars 기존 `.bars` / table `.cmpt` 가로 스크롤 wrap / tiles `.tiles` / events 기존 `.events`) → 나머지 단락 → 슬라이드 `figure.simg`(img 960×540 `loading="lazy"`, alt "슬라이드: 제목", figcaption "슬라이드 m:ss(시점 링크) / 제목 / 캡션") → `ol.vgo`(video_secs: m:ss 링크 `{url}&t={sec}s` + 라벨, 슬라이드 구간은 500 굵기)) → 출처(`ol.srcs` 하나, 영상 항목 아래 전체 타임라인 `ol.vtl` 각 행 시점 링크) → 이전·다음(기존) → 미니 바(기존).
- 수치 타일 배치(실측): 1개 가로형 한 줄, 2·4개 2열(640px 이상 4개는 4열), 3개 모바일 가로형 3줄·640px 이상 3열, 5개 이상 없음(코드 상한)
- 인용 번호·툴팁·`.nb`·`.nb-end`·형광 규칙은 포인트 대신 **단락 끝**에 그대로(`with_end`·`cites` 재사용). ⚠ `.chk`는 그 단락(또는 요약) 끝에 `id="chk-k"`(k 1부터), 메타 "확인 필요"는 `<a href="#chk-1">`
- 읽는 시간 = 제목 + 요약 + 단락 글자(공백 제외) ÷ 500, 올림, 최소 1분
- CSS: `trendsit.css`에 조각 추가(`.tiles .tile .tile-v .tile-x .tile-l .tile-s`, `.dsec .dsec-t .dp`, `.cmpt-wrap .cmpt td.em`, `.vgo .vx`, `.simg`, `.tab-anchor`). 값은 토큰 변수만(새 토큰 금지). 시험 CSS(`proto/shell.html` 9~43행)가 출발점. 지우는 것: `.sec-ov .ov`, `.pts .pt .pt-x`, `.cc .cb`, `.src-g`(개요·포인트·개념·기여·채널 머리). `tokens.css` 불변
- 홈·주차: 토픽 목록 모양 그대로(summary 2문장, D-20·D-21). 탭 앵커 5.1-1. 레포 메타 5.1-5
- 관리 화면: 5.1-2·3·8

### 5.9 check.py·gate.js
- 정적(기존 M-1·M-2·C-3~C-7 유지) + 새 항목: 토픽 페이지에 `개요`·`핵심 포인트`·`핵심 개념`·`소스별로 더한 것` 섹션 제목 0, `h3.src-g` 0, `img`는 `/assets/slides/` 경로만이고 파일 존재, `a[href*="&t="]`는 영상 출처 URL로 시작, `.tiles` 자식 수 1~4와 `n{k}` 클래스 일치, `.chk` 수 = site.json의 check 수(C-9 개정), 메타 "확인 필요" 링크 대상 존재
- **샘플 사이트(사람이 보는 용도, 새 옵션 없음)**: `uv run python site_src/build.py --data tests/fixtures/s6_1/site_v2.json --out site.sample` → `site.sample/`(git 제외). 픽스처 `site_v2.json`은 시험 1단 결과 6토픽(`proto/out_one/*.json`)을 5.7 모양으로 옮긴 것이라 실제 글·수치·슬라이드가 들어간다. `python3 -m http.server -d site.sample 8789`로 열어 본다
- gate.js(관문 9 Chromium·WebKit, 375·768·1280) 대상 페이지 추가: 타일 1·2·3·4개 토픽, 표 있는 토픽, 슬라이드 이미지 토픽, 영상 타임라인 토픽. 측정 추가: 탭 두 개 클릭 뒤 `scrollY` 차 ≤ 1px·`.nav` top ≥ 0(D-40), `.cmpt-wrap`은 가로 스크롤이고 페이지 넘침 0, 이미지 `naturalWidth` > 0(로드됨), 375에서 타일 글자 잘림 0(`scrollWidth ≤ clientWidth`)

### 5.10 설정 `config/brief.yaml`(5.10 범위만 구현 세션이 고침, `check-config` 통과)
```yaml
evidence:
  max_tokens_per_topic: 14000      # 8000 → 14000(원문 공급, 시험 입력 최대 8.2K 토큰)
  max_refs_per_paragraph: 4        # max_refs_per_point 대체
  video_relevance_high: 0.50       # 그대로
write:
  input: {text_chars: 6000, transcript_chars: 14000}
  summary: {sentences: [1, 2], chars_max: 200}
  sections: {single_source: [3, 5], multi_source: [4, 7]}
  paragraphs: {per_section: [1, 2], sentences_max: 4, chars_max: 320}
  heading_chars_max: 70
  head_tiles_max: 4
  tiles_per_section: [2, 3]
  visuals_max: 4
  bars_items: [2, 6]
  table: {rows: [2, 6], cols: [2, 4]}
  slides_max: 2
  video_secs_max: 3
  highlights: {summary: 1, per_paragraph: 1, page: [2, 4]}
review: 그대로(max_rounds 3, same_issue_repeat_to_check 2, duplicate_point_similarity 0.8)
```
삭제: `write.points`, `overview_sentences`, `summary_sentences`(→ summary.sentences), `highlights.overview·per_point`, `diagrams`, `concepts_max`, `evidence.max_refs_per_point`. `WriteCfg`·`EvidenceCfg`(config_brief.py)도 같이. `WriterLimits`는 이 값들을 그대로 담는다(sections는 `n_sources`로 고른 범위).

### 5.11 회귀 교체(D-31)
| 대상 | 처리 |
|---|---|
| `tests/test_s5_select_checks.py`·`test_s5_weekly.py`·`test_s5_evidence.py`·`test_s5_material.py` | 옛 TopicPage 모양을 쓰는 테스트는 v2로 고치거나 지우고, 같은 보장(라운드 상한·되돌림·check·저장·요약 계산·cap)은 `tests/test_s6_1_write.py`가 v2로 보장 |
| `verify_s5.sh` A9·A10·A13·B8·B9 | `-k` 대상이 v2 테스트를 가리키게. 설명 문구에 "(S6-1 v2 기준)" |
| `verify_s5.sh` B1(골든) | `reports/S5-1/golden_before.json`과의 비교를 **`reports/S6-1/golden.json`**(v2 픽스처에 코드 검사를 돌린 결과, 이 스펙이 만듦)과의 완전 일치로 바꿈. 이후 스펙 회귀용 |
| `verify_s5.sh` B3·A15 | 그대로 통과(S5 역할 5개 안의 변경이라 허용 범위) |
| `verify_s5.sh` B10 | 그대로(새 writer.md에 숫자 패턴 0) |
| `verify_s6a.sh` | 수정 없이 통과해야 함(A14의 `3967cd4` 해시 비교 포함). `tests/test_site.py`·`test_export.py`는 v2 픽스처로 |
| `verify_s6b.sh` B11 | 래퍼 검사 문구를 fetch+reset에 맞게(“pull 실패에도 실행” → "동기화 실패에도 실행", `TRENDSIT_PULL_FAILED` 그대로) |
| `eval/graders_brief.py`, `scripts/s5_gate_b.py`, `scripts/s5_eval_fixtures.py` | v2 칸(summary·sections·tiles)으로. 채점 항목 이름은 유지, 라벨 시트 열은 `topic_id, section, type, label` |
| `eval/fixtures/writer|critic|writer_revise/` | 옛 파일 삭제. 런 뒤 재생성 재료(7장). 워크플로우 안에서는 디렉터리가 비어 있어도 테스트가 실패하지 않아야 함 |
| `trendsit/brief/briefing.py write_briefing_md` | 읽기본을 v2로(요약, 타일, 절·단락, 시각 요소 표, 슬라이드·video_secs, ⚠ 위치) |
| `AGENTS.md` | "최종 출력 형식은 예시 사이트의 `trendsit-example.json`과 같아야 함" → "최종 출력 형식은 `data/site.json`(S6a 최상위 구조 + S6-1 토픽 v2, `docs/handoff/S6-1_TASK.md` 5.7)" |

### 5.12 불변식
| ID | 불변식 | 위반 시 |
|---|---|---|
| C-1 | 최종판 TopicPage의 모든 refs(단락·타일·표·막대·사건·캡션)는 그 토픽 pack의 id 안에 있다(`set(all_refs) <= set(pack)`) | 코드 검사 반려(wrong_ref) |
| C-2 | 타일 value·표 셀(첫 열 제외)·막대 value의 모든 수치는 그 칸 refs 원문에 값으로 존재(`same()`) | 코드 검사 반려(number_mismatch) |
| C-3 | 절마다 `visual != none`인 것은 그 종류의 내용이 있고 나머지 시각 칸은 비어 있다; 페이지 `visual != none` 수 ≤ `visuals_max`; `len(head_tiles) ≤ head_tiles_max`; 슬라이드 ≤ `slides_max` | 반려(format) / 자동 수정(sections 자름) |
| C-4 | `section.slide`는 `slide_candidates`의 원소이거나 null; `video_secs ⊆ 타임라인 sec` | 자동 수정 |
| C-5 | 작성자 호출은 토픽당 최대 5회(v1.2: 기본 ≤2 + no_visuals run_role 1회 ≤3), 성공 판은 폐기하지 않음, 실패 토픽은 `status='failed'`이고 export에 없다 | 테스트 실패 |
| C-6 | `page.check`·`section.check`는 코드만 바꾼다(작성자·수정 출력의 true는 false로) | enforce |
| C-7 | site.json 토픽에 `overview`·`points`·`diagrams`·`concepts`·`contributions` 키 없음; `slide.image`가 가리키는 파일이 `data/slides/`에 존재 | export 테스트 실패 |
| C-8 | 생성 HTML: 외부 요청 0(S6a C-4) + `img src`는 `/assets/slides/*.jpg`이고 파일 존재; 사이트 JS 0 | check 실패 |
| C-9 | `.chk` 수 = 표시 대상 check 수(절 + summary), 메타 "확인 필요" 링크는 has_check일 때만, 대상 `#chk-1` 존재 | 테스트·check 실패 |
| C-10 | 홈에서 `#topics`·`#repos` 선택 시 scrollY 차 ≤ 1px, nav top ≥ 0 | gate.js 실패 |
| C-11 | `trendsit backup`은 원본 DB를 바꾸지 않고(before/after 해시 동일) 사본은 `PRAGMA integrity_check` ok | 테스트 실패 |
| C-12 | `run_ops.sh`는 동기화 실패에도 ops를 실행하고 종료 코드는 ops의 것; main 아니면 3(S6b B11 유지) | verify_s6b B11 |

### 5.13 실패 동작
| 상황 | 동작 | 종료/상태 |
|---|---|---|
| 작성자 잘림 2회(기본) + no_visuals 모두 실패 | 토픽 failed, attention, 다른 토픽 계속 | weekly 0(partial은 요약 상태로), 사이트에서 그 토픽 제외 |
| (v1.2) 토픽 일부만 failed(예산 중단 아님, 성공 토픽 ≥ 1) | runs.status·summary는 `partial` 그대로, **`weeks.status`는 `done`**(지금 코드는 `written`이라 publish가 2로 거부 → 무인 발행이 통째로 막힘). ops weekly는 그대로 publish까지 | 발행됨, 실패 토픽은 export에 없음 |
| 토픽 전부 failed 또는 예산 중단 | 기존대로 weeks 갱신 안 함·발행 안 함 | 1 |
| 원문 없음(만료) | 카드 인용으로 대체 + attention | 계속 |
| 영상 파일 없음 / ffmpeg 없음·실패 | 슬라이드 null + attention, 토픽 계속 | 계속 |
| export: C-2 위반, published 0개, DB 오류 | ExportError, 파일 미작성(기존) | 1 |
| build: site.json 없음·깨짐·`slide.image` 파일 없음 | BuildError, `site/` 불변(기존 원자 교체) | 1 |
| check: 항목 실패 | 실패 목록 출력 | 1 |
| backup: 폴더 못 만듦·같은 이름 존재·backup API 예외 | 메시지 한 줄, 원본 불변 | 1 |
| run_ops.sh: fetch/reset 실패 | 로그 + `TRENDSIT_PULL_FAILED=1` + 기존 코드로 ops 실행 | ops의 것 |
- 에러 메시지 형식: `<명령>: <원인 한 줄>`(stderr). 부분 실패 정책: 토픽 단위 격리(한 토픽 실패가 주 전체를 멈추지 않음, 예산 초과만 전체 중단 — 기존)
- 타임아웃·재시도: LLM은 run_role 기존(스키마 2회, 잘림 1회) + no_visuals 1회. ffmpeg `timeout 60초`, 실패는 재시도 없음

## 6. 관문 A (`scripts/verify_s6-1.sh`)

| ID | 검증 내용 | 판정 방법 | PASS 기준 | 수단 | 관련 | 단계 |
|---|---|---|---|---|---|---|
| A1 | 작은 보완(운영) | 임시 저장소(verify_s6b B11 방식)로 run_ops fetch+reset(원격 앞선 커밋 뒤 HEAD == origin/main, 링크 보존, 동기화 실패에도 실행, 종료 코드 전달, main 아니면 3), setup이 fetch 뒤 origin/main으로 worktree, `trendsit backup` 임시 DB(사본 integrity ok, 원본 해시 동일, 같은 이름 1, --tag) | 전부 통과, verify_s6b 전체 PASS | 스크립트 | 5.1-6·7·9, C-11·C-12 | S-1 |
| A2 | 작은 보완(화면) | 픽스처 빌드 → HTML 파싱 + gate.js | 키워드 행 링크 ≤ 5 + "외 n개", 실행 1건 "이 주 발행 n개 / 이 실행이 쓴 토픽 m개"와 export `counts.written`, 대체 계획 문구 2종, `h3.src-g` 0, 레포 메타 줄 " / " 구분, 탭 C-10 | 스크립트 | 5.1-1~5·8 | S-1 |
| A3 | 스키마·역할 md·설정 | `check-config`(역할 md 3개 lint: 섹션 순서·예시 3~5·굵게 ≤1, brief.yaml 새 칸), TopicPage v2 검증(이상 예시가 거부·enforce), WriterLimits가 brief.yaml 값, writer.md에 숫자 패턴 0(B10), writer.md에 `limits.` 참조 ≥ 1(v1.2: critic·writer_revise 입력에는 limits 칸이 없어 제외) | 통과 | 스크립트 | 5.3·5.4·5.10, D-44 | S-2 |
| A4 | 근거 공급 | 임시 DB(글 2·영상 1·레포 1): Document 줄 형식 4종 id, 글 6,000자·전사 14,000자 상한(문장 경계), 토픽 상한 문장 단위 자름, 원문 NULL → `#q` 대체 + attention, 검수자 raw_evidence 매핑(#s ±1문장, 전사 묶음, sl 판독), topic_evidence field 저장 | 통과 | 스크립트 | 5.2, C-1 | S-2 |
| A5 | 코드 검사 | 5.5 표 각 행 1건 이상(이상 예시 포함) + 자동 수정 4종 + 경고 4종 | 반려·수정·경고가 명세대로 | 스크립트 | 5.5, C-2·C-3·C-4 | S-2 |
| A6 | 라운드·수정·잘림 | 가짜 LLM: 위치 문법 v2 apply(지적 안 된 절 되돌림, sections[i] add/delete, rows[k]), 같은 이슈 2회 → section check, 잘림 → no_visuals 재호출(호출 수 ≤ 4, detail.no_visuals) → 그래도 실패면 failed·export 제외, 비용 합산, previous_topic v2, (v1.2) 하위 위치 오류 delete가 절을 지우지 않음, 시각 칸 비우면 visual none, 토픽 1개 failed인 run → weeks `done`·ops weekly publish 0·사이트에 그 토픽 없음 | 통과 | 스크립트 | 5.3·5.5, C-5·C-6 | S-2 |
| A7 | 슬라이드 | 픽스처 digest(LlamaIndex 20장 사본): 후보 = 873·900초 2장(같은 제목 첫 장, 글머리표 슬라이드 제외), 작성자 선택 후보 밖 → null, 미배치 → 직전 구간 절, ffmpeg로 합성 영상(`lavfi testsrc` 10초, 테스트가 만듦) 프레임 960×540 생성·재실행 시 재생성 안 함, 영상 없음 → null + attention | 통과(ffmpeg 없으면 FAIL) | 스크립트 | 5.6, C-4 | S-2 |
| A8 | export v2 | 임시 DB v2 페이지 → site.json: 토픽 칸 목록 일치, 옛 키 0(C-7), refs → 출처 id, 영상 sources.timeline·video_id, video_secs 라벨, slide 파일 있을 때만, C-2 위반 시 파일 유지, runs.counts.written·fallback | 통과 | 스크립트 | 5.7, C-7 | S-3 |
| A9 | build 토픽 | v2 픽스처(타일 0·1·2·3·4, 표, 막대 2개, events, 슬라이드, 영상 타임라인, ⚠ 절·요약, 절 1개 토픽, 긴 heading) → HTML 파싱 | 블록 순서 5.8, 시각 요소가 첫 단락 뒤, `.tiles.n{k}`, 슬라이드 figure·캡션 링크 `&t=`, `.vgo`·`.vtl` 링크 수 = secs 수, `.chk` id 순번·메타 링크(C-9), 읽는 시간 식, 옛 섹션 제목 0 | 스크립트 | 5.8, C-9 | S-3 |
| A10 | 관문 9 + 동작 | `check.py --fixture`(정적 + gate.js Chromium·WebKit 375/768/1280, 대상 페이지 5.9) | 9항목 전부 + 새 측정(탭 높이, 표 스크롤·넘침 0, 이미지 로드, 타일 잘림 0) 통과, 외부 요청 0(C-8) | 스크립트 | 5.9, C-8·C-10 | S-3 |
| A11 | 회귀 | `verify_s6a.sh`, `verify_s6b.sh`, `verify_s5.sh --fast`(개정 항목 포함) | 셋 다 종료 코드 0(v1.2 예외: verify_s5 B5·A23 "순 감소 아님"은 S5-1 전용 불변식으로 기준 커밋에서 이미 FAIL → 이 두 줄만 FAIL 허용, 다른 항목 FAIL은 불합격), pytest 전체 건너뜀 0, `reports/S6-1/golden.json`(6토픽)과 B1 일치 | 스크립트 | 5.11 | S-3 |
| A12 | 실측 QA(0원) | qa-verifier: `site.sample/`(5.9 명령, 시험 6토픽)을 WebKit 375×812·Chromium 1280으로 열어 캡처를 `reports/S6-1/shots/`에(홈 탭 2개, 타일 3개 토픽, 표 토픽, 슬라이드·타임라인 토픽, ⚠ 토픽, 키워드, 실행 1건). 적대적: 절 1개 토픽, 타일 1개·3개 모바일 배치, 표 4열 모바일 가로 스크롤, 슬라이드 파일 없는 토픽(null → figure 없음), 영상 없는 토픽에 `.vgo` 0, 확인 필요 0인 토픽에 메타 링크 없음 | 캡처가 5.8 배치 규칙과 일치, 가로 넘침 0, 깨진 레이아웃 0 | QA | 5.8 | S-3 |
| A13 | 문서·정리 | 파일 검사 | README "사이트" 절(새 구조·`backup`·`export` v2), README "자동 실행" 절(래퍼 fetch+reset), `AGENTS.md` 출력 형식 줄 교체, CONTRACTS 2장 근거 id 3행, `reports/S6-1_report.md` 8장까지, `reports/S6-1/shots/` png ≥ 6장, `.gitignore`에 `/site.sample`, 옛 eval 픽스처 3폴더 비어 있음, `trendsit/`에 `overview`·`concepts` 식별자 0(grep) | 스크립트 | 5.11 | S-4 |

## 7. 관문 B와 QA, 런 뒤 할 일

- **관문 B(워크플로우 밖, D-28·D-36)**: 발행 뒤 리뷰 세션이 라벨(opus-5.5, D1-3): W41 10토픽 전체 + W40 영상(LlamaIndex)·표 있는 토픽 3~4개. 기준: 근거 밖 사실·숫자 0, 표·타일 숫자 원문 일치 100%, 요약↔단락 중복 0(같은 사실 문장 반복), 의미 없는 타일 0, 발표자 이름 입력 표기와 일치. 미달이면 사용자에게(되돌림: `weeks.current_run_id`를 이전 run으로, publish 재실행). 라벨 시트는 `eval/labels/s6_1_r1/`
- **QA(qa-verifier, 0원)**: A12만. 실데이터는 LLM 없이 v2 페이지를 만들 수 없어 픽스처(시험 1단 결과 6토픽을 v2 모양으로 옮긴 `tests/fixtures/s6_1/topic_v2.json`)로 한다. 실데이터 화면 확인은 런 뒤 ③
- **보기 확인점(사용자가 페이지를 보는 자리, D-46)**
  | 확인점 | 시점 | 무엇을 보나 | 비용·막힘 |
  |---|---|---|---|
  | ① 샘플 사이트 | 런 끝(S-3 뒤, A12) | `site.sample/`(시험 6토픽, 새 구조 전부) + `reports/S6-1/shots/` 캡처. 구현 세션은 캡처를 사용자에게 보내고 로컬 서버(8789)로 열어 둔다 | $0, DB 쓰기 없음 → 막힘 없음 |
  | ② 실사이트(새 글 20토픽) | 런 뒤 ①~⑤ 뒤 | trendsit.jiseop.com | LLM 약 $0.3, DB 쓰기 → 아래 "1회 승인" |
  | ③ 첫 무인 실행 | 10/19 07:00 | W42가 새 작성자로 | 자동 |
- **런 뒤(구현 세션, 워크플로우 밖)** — ①~⑤는 **`scripts/s6_1_regen.sh` 하나**로 묶는다(순서·인자는 아래 그대로, 한 단계라도 실패하면 거기서 멈추고 종료 코드 1). S6a 실측(리포트 7장)으로 자동 모드 분류기가 실DB 쓰기(publish·backup·weekly)를 막으므로, 구현 세션은 `[사용자 필요]` 블록에 이 스크립트 한 줄을 적고 **승인 1회**를 받아 실행한다(사용자가 터미널에서 직접 돌려도 같다). 그 밖의 단계(⑥·⑦)는 승인 없이 진행(D-36)
  ① 영상 파일 확인: `data/media/S-bRN-avZ4Q/media.*`·`data/media/D7q8fa589FY/media.*`(보관 7일. 없으면 리포트에 적고 슬라이드 없이 진행)
  ② `uv run python -m trendsit backup --tag pre-s6-1`(D-35, 첫 사용)
  ③ `uv run --extra embed python -m trendsit weekly --week 2026-W40 --force --spec S6-1` → `--week 2026-W41 --force --spec S6-1`(`--force`는 발행을 풀어 done으로, C-8). 각 뒤 `trendsit cost --spec S6-1` 확인(합 ≤ 1.50, 넘으면 스크립트가 멈춤)
  ④ 읽기본(`reports/S5_brief/briefing_<week>.md` v2) 훑어 작성 실패·⚠ 수 기록
  ⑤ `trendsit publish --week 2026-W40`, `--week 2026-W41` → `python3 site_src/check.py`(실사이트) → trendsit.jiseop.com WebKit 375 홈·토픽 2개(표·슬라이드) 캡처 → `reports/S6-1/shots/`·리포트 7장
  ⑥ eval 픽스처 재생성(0원): `scripts/s5_eval_fixtures.py --weeks 2026-W40 2026-W41`(v2) → `eval/fixtures/writer|critic|writer_revise/` 커밋(judge 실행은 안 함, NG-7)
  ⑦ 손으로 고친 것이 있으면 `code-reviewer` 1회 → 리포트 8장(SUMMARY 요약) → README → 커밋·푸시·PR → `handoff/NNN_impl→review.md`
- **병합 뒤(리뷰 세션)**: 실행 폴더 `git -C ~/Claude/projects/trendsit-run fetch && git -C … reset --hard origin/main` 1회(래퍼가 이제 reset 방식이라 이후 자동), `status -s` 빈 출력. 10/13(화)부터 nightly `pull_failed` 없음 확인. **10/19(월) 07:00 W42가 새 작성자로 처음 도는 날**: 아침에 runs·사이트 확인(실패 토픽·⚠ 수·비용 RUN-2026-W42 ≤ 1.50)

## 8. 단계 (커밋 단위, 한 단계가 한 컨텍스트 안에서 끝나는 크기)

| ID | 단계 | 포함 | 완료 AC | 선행 | 산출물 |
|---|---|---|---|---|---|
| S-1 | 작은 보완 | 5.1 1~9, verify_s6b B11 개정, verify_s6-1.sh 뼈대 | A1, A2 | — | build.py·trendsit.css·export.py·cli_ops.py·run_ops.sh·setup_run_worktree.sh·verify_s6b.sh·verify_s6-1.sh·테스트 |
| S-2 | 작성·검수 v2 | 5.2~5.6, 5.10, 옛 brief 테스트 교체, 역할 md 3 + diagrams.md, 골든 생성 | A3~A7 | S-1 | artifacts_brief.py·config_brief.py·brief.yaml·fulltext.py·slides.py·write.py·checks.py·revision.py·briefing.py·roles·tests/test_s6_1_write.py·reports/S6-1/golden.json |
| S-3 | export·화면·회귀 | 5.7~5.9, 5.11(verify_s5 항목·eval graders·s5 스크립트·AGENTS·CONTRACTS), 픽스처 v2 | A8~A12 | S-2 | export.py·build.py·check.py·gate.js·trendsit.css·tests/test_s6_1_site.py·fixtures |
| S-4 | 문서·런 뒤 | README·리포트, 7장 ①~⑦ | A13 (+ 7장) | S-3 | README.md·reports/S6-1_report.md·eval/fixtures 재생성 |

## 9. 넘길 것과 미확정

- 미해결 `Q-*`: **0건**. 보류 Q-10(QA-13)은 NG-8
- 구현 시점 기본값(리포트 "결정한 것"에 적는다): 문장 나누기 정규식의 약어·소수점 처리, 전사 묶음 경계(25초 ± 문장 끝), 표 셀 수치 정규화(`$0.10` 등 통화 기호 처리는 `number_values` 그대로), 타일 `note` 비었을 때 표시, 슬라이드 캡션에 title이 빈 경우 "슬라이드 m:ss"만, `.vgo` 라벨이 긴 경우 줄바꿈, 읽기본(md) 표 모양, `counts.written` 0일 때 표시, 백업 파일명 시각 형식(`%Y%m%d-%H%M`), ffmpeg 입력 파일 확장자 탐색 순서
- 기획 세션 몫(병합 뒤): 19·63 3.3·64 부록 C(C-34: S6-1 결과), `docs/CONTEXT.md`·COMMON 8장 스펙 표 동기화, 디자인 문서(`docs/reference/s6_design/DESIGN.md` 4.3)에 새 조각 반영은 **다음 사이클**(이 스펙에서는 `trendsit.css`만. 참고 복사본은 건드리지 않음 3.3)
- 사용자 몫: 원격 브랜치 정리, 관문 B 미달 시 되돌림 결정, 예산 상향(필요 시)
- 다음 사이클(v1.2, 런 006에서 발견, 시연 뒤): ① 출처 메타(channel·title·url)를 만료되는 원문(item_texts·video_segments, 8주)에서 찾아 W40·W41은 약 11/26 이후 재발행 때 출처가 깨짐 → member 단위(items·videos)에서 찾기(006-C2-14). ② 영상 2개 이상 토픽의 `video_secs`·슬라이드 시점 링크가 첫 영상으로 감(006-C2-16, 칸에 영상 id 필요). ③ verify_s5 B5·A23을 "직전 스펙 기준"으로 바꾸거나 삭제
- 위험: 10/19 첫 무인 실행이 새 작성자 — 잘림 재시도(D-42)와 실패 격리(D-33)가 안전장치. 시험 잘림률 6/25라 토픽당 평균 호출 1.3회 가정, 주당 비용 +$0.1~0.2(RUN 1.50 안)

### 5.14 v1.3 보정(PR #14 리뷰·관문 B 1차, 사용자 결정 2026-10-13~14)
| # | 무엇 | 요구 | 근거 |
|---|---|---|---|
| 1 | 상세 절 구분 | 상세의 `.dsec` 위 테두리 제거, 절 제목 위에 회색 번호 `01`·`02`(CSS counter, `--fs-sm`·`--c-muted`), 절 사이 `--sp-10`. 목록(`.list`)은 테두리 유지 | 사용자: 목록·상세가 같은 테두리라 구분이 안 됨, 시안 B 선택(`s6_1b_시안/`) |
| 2 | 영상 구간 링크 | export가 절 `video_secs`에 그 절 단락 refs의 `vd:`·`sl:`…`@초`가 든 타임라인 구간 시작 초를 덧붙임(작성자 선택 + 근거, 타임라인에 있는 초만, 시간순, `write.video_secs_max`개) | 실측: W40·W41 영상 토픽 9절 중 1절만 링크 |
| 3 | 음차 | 작성자 출력의 사전 낱말(brief.yaml `aliases.transliteration`)을 낱말 단위로 영문으로(조사 경계 유지, "솔루션·구글링"은 안 바꿈). 사전에 Anthropic·OpenAI·Google·Microsoft·Large 추가. 정리 대상에 head_tiles·표·막대·타일·사건·슬라이드 캡션 글자 포함(refs 등 id 칸 제외) | 관문 B: 9토픽에 음차, 표 칸 '제미나이 4 아르곤' |
| 4 | 식별자 보호 | 별칭 정본 치환은 앞이 `@ / _ . -`·영숫자, 뒤가 `/ _ -`·영숫자인 자리를 바꾸지 않음 | 관문 B: `@openrig/cli` → `@OpenRig/cli` |
| 5 | 도식 양 | `write.visuals_target: [2, 3]`(새 칸, WriterLimits `visuals_target`). writer.md "절의 절반 이상 none" 삭제 → 수치 비교·구간·여러 대상·날짜 다른 사건이 있는 절은 visual, 목표 범위, 상한 visuals_max. 코드 경고 "남발 의심" 기준도 목표 상한 초과로 | 사용자: 토픽당 2~3개 목표. 실측 절 88개 중 10개 |
| 6 | 형광 | WriterLimits `highlights_page`(=highlights.page). writer.md: 페이지 전체 그 범위로 결론 구절에, 단락당 하나, summary 하나까지("쓰지 않아도 됨" 삭제) | 실측: 17토픽 중 형광 1개 |
| 7 | 되풀이 | writer.md: 첫 절은 summary 사실을 다시 쓰지 않고 세부부터, 마지막 절은 앞 절 재요약 금지, head_tiles 수치는 절 제목·visual에 다시 쓰지 않음. critic.md overuse에 같은 항목 | 관문 B: 6토픽 반복. 원인은 summary(사건+쟁점)·첫 절(사건)·마지막 절(쟁점) 배치가 겹치게 정한 명세 |
| 8 | 번역·표기 | writer.md: 기술 용어는 원어 병기 또는 원어, 뜻이 불확실하면 원어. 슬라이드·글 원문과 전사·타임라인 라벨 표기가 다르면 슬라이드·원문. critic.md: 영어 근거의 낱말 뜻 대조(오역 = unsupported), 이름 철자 다름 = unsupported | 관문 B: Coordination→조류, lifecycle→리라이프, LiteParse→LightParse |
| 9 | 검수자 | `max_tokens` 4000 → 6000(모델은 그대로 qwen, 사용자 결정) | 실측: 출력 평균 3,464·잘림 7/28 |
| 10 | 관문 9 항목 5 | "첫 절이 375 첫 화면 안" → "머리 타일 또는 첫 절이 첫 화면 안" | 실사이트 3토픽 836~902px, 요약+타일 구조상 |
| 11 | CI | `ci.yml`에 ffmpeg 설치(테스트는 ffmpeg 없으면 실패가 정상, 2장) | PR #14 CI 실패 |
| 12 | 재생성 | W41만 `weekly --from-step write --force --spec S6-1` → publish(W40은 publish 때 1·2·10만 반영). W40은 W41 결과를 보고 결정 | 사용자 2026-10-14 |
- 예산(3.4) 갱신: `checks.py` ≤ 480, `write.py` ≤ 455, 새 파일 +1(`tests/test_s6_1b.py`). 검수자 모델 변경은 하지 않음(NG-10 유지)
- 콜드 리뷰(R3, `.workflow/007-s6-1/R3-review.md`) 반영: 이름 패턴(`translit_pattern`)에도 식별자 보호(실DB `w40-deepseek-harness`에서 `@deepseek-ai/…` 훼손 2건 확인 — W40을 다시 쓰지 않으면 남음), 2글자 음차는 조사 없이 나올 때만·1글자는 낱말 단위 제외("솔로"·"라지만" 보호), 병기 중복 "X(X)" 정리, 영상 2개 이상 토픽은 근거로 채우지 않음(작성자 값만), 작성자 선택 구간이 cap에 밀리지 않음. 첫 절 지침은 "summary 사건을 다루되 문장을 되풀이하지 않고 세부를 더함"으로(검수자 절차 0과의 모순 해소)
- 3.3 갱신: `trendsit/brief/aliases.py`(음차 패턴의 정본 위치)와 `.github/workflows/ci.yml` 수정 허용

### 5.15 v1.3 추가(리뷰 세션 2026-10-14, 코드 지적 `.workflow/planning/s6-1/code-findings-2.md`. 이번 범위는 1·2·4와 R2-04, 3은 MVP 뒤)
| # | 무엇 | 요구 |
|---|---|---|
| 1 | 검수자 원문 | 5.2의 "`it:#s` → 그 문장 ± 1문장"은 유지하되 **구성원 하나에 문서 하나**: 같은 구성원의 창을 합쳐(겹치면 한 번) 문장 순서대로, 줄마다 근거 id. slide_fact는 사실 줄 + 기존 ±30초 창 |
| 2 | 검수 실패 | 검수자 LLMError → 30초 뒤 1회 재시도, 그래도 실패면 summary `check=true`(⚠) + attention "검수 실패". 5.13 표의 "critic 실패 → 코드 통과판"을 이것으로 바꿈 |
| 3 | 페이지 단위 형식 이슈 | loc `sections`(개수 상한 등)는 코드 자동 수정 또는 attention만. summary에 ⚠를 붙이지 않음 |
| 4 | 라벨 파일 | 재생성·eval 픽스처 경로는 추적 중인 `eval/labels/*.csv`를 덮어쓰지 않음 |
- 6장 A6 문구 "호출 수 ≤ 4" → "≤ 5"(C-5와 맞춤)
- 3.4 예산 이탈 수용(리뷰 세션 판정, 사용자 위임 2026-10-14): 새 파일 17/11(테스트·픽스처·jpg·.gitkeep), `tests/test_s6_1_write.py` 675줄(테스트 파일은 500줄 상한 대상에서 뺌). 코드 파일 예산은 5.14대로

## 13. 실측 반영 이력
| 날짜 | 런 | 발견 | 근거 | 변경한 § |
|---|---|---|---|---|
| 2026-10-12 | 006-s6-1 | C2 리뷰 High 3(revise 절 삭제, 복합 수치 일부만 대조, 부분 실패 주 미발행)·Medium(C-5 사후 폐기, limits 참조, B5·A23, 예산 39) | `.workflow/006-s6-1/C2-review.md`, 코드 지적 `.workflow/planning/s6-1/code-findings-1.md` | 3.4, 5.3, 5.5, 5.12 C-5, 5.13, 6장 A3·A6·A11, 9장 |
| 2026-10-14 | PR #14 리뷰 | 관문 B 1차(14토픽): ⚠ 없는 오류 4토픽(오역 2·이름 1·근거 밖 1), 반복 6, 음차 9, 식별자 변경 1, 도식 0.6/토픽, 형광 1/17, 영상 링크 1/9절, CI ffmpeg | `eval/labels/s6_1_r1/gate_b.csv` | 5.14 신설 |
