# S6a 사이트: DB → 화면 JSON(export), 디자인 시스템 v1 적용, 발행 연결

> 기획 세션 작성 2026-10-11(spec-planner, 원장 저장소 `.workflow/planning/s6a/ledger.md`). 기준 커밋 main `3967cd4`(S6b PR #12 병합). v2: 리뷰 세션 handoff 003 반영(data/ 추적 파일 이동, verify_s5 B7, S6b 실제 publish 구조).
> 구현 세션 시작 절차: `git fetch origin && git switch -c s6a-site origin/main`(작업 폴더에서 `git switch main` 불가, 실행 폴더가 main 체크아웃) → 이 문서를 `docs/handoff/S6a_TASK.md`로, `~/Claude/projects/trendsit-design/claude/s6_design/repo_reference/s6_design/`를 `docs/reference/s6_design/`로 복사 → 첫 커밋 → `/impl-workflow docs/handoff/S6a_TASK.md .`. (S6b 구현 중에 같은 폴더에 untracked로 두지 않으려고 기획 폴더에 둠)
> S6의 첫째 스펙이지만 S6b 다음에 한다(같은 작업 폴더라 순차, `publish`가 S6b에 있음). 공통 규칙은 `docs/handoff/COMMON.md`(특히 12장), 이 문서가 우선한다. 구현 세션은 `/impl-workflow docs/handoff/S6a_TASK.md .`로 돌린다.

## 0. 이 스펙이 끝나면 되는 것

| 항목 | 값 |
|---|---|
| slug | `s6a` |
| 버전 / 작성일 | v2 / 2026-10-11(v1 같은 날) |
| 문서 상태 | **확정(투입 가능)**. 시작 조건 충족(S6b 병합 `3967cd4`) |
| 미해결 `Q-*` | 0건 |
| 선행 런 | 없음(S6b 런과 별개) |
| 브랜치 | `s6a-site`, 첫 커밋 = 이 문서 + `docs/reference/s6_design/`(머리말의 복사 절차) |

**한 줄 목표**: 발행된 주의 실제 브리핑이 디자인 시스템 v1(x04)의 모양으로 trendsit.jiseop.com에 나오고, 관리 화면 3종(소스·키워드·실행 기록)이 실제 기록을 보여 준다. 월요일 자동 발행(S6b)이 이 사이트를 다시 만든다.

- 사용자 체감 결과: `trendsit publish --week W`가 export → 빌드를 하고, `site/`에 홈·주차·토픽·관리 화면이 새 디자인으로 생긴다. 예시 데이터 흔적이 없다. 아이폰 Safari(WebKit)와 크롬에서 관문 9를 통과한다
- 공개 범위: 지금처럼 로그인 없이 공개(D-3)

## 1. 맥락

- 지금 `site_src/build.py`(1050줄, 표준 라이브러리만)는 `data/trendsit-example.json`(디자인용 예시)을 읽어 옛 디자인(IBM Plex, 소스 연결도, 관리 화면 버튼)으로 만든다. S5는 DB에 실제 브리핑을 저장하고 `brief/briefing.py`의 `export_topic()`이 토픽 하나를 예시 JSON 토픽 모양으로 꺼낸다(실측)
- 디자인은 6단계까지 확정(기획 문서 78~82). 기준 페이지 x04 = `docs/reference/s6_design/showcase/pages/*.html`, 규칙 = `docs/reference/s6_design/DESIGN.md`, CSS = `tokens.css`·`trendsit.css`, 생성 규칙(형광·토큰 묶기·포인트 끝 어절 + 인용 묶기) = `docs/reference/s6_design/drafts/common.py`, 관문 9 측정 = `drafts/shoot.py`의 `GATE_JS`
- 결정(원장 번호)

| ID | 결정 | 근거 |
|---|---|---|
| D-1 | S6a(사이트)·S6b(자동 실행)로 나눔 | 사용자 2026-10-11 |
| D-2 | P4 4·5는 S6-1 | 사용자 |
| D-3 | 공개 유지(Access 안 함) | 사용자 |
| D-4 | 관문 9를 WebKit에서도 통과. 툴팁·미니 바 미지원이면 대체 동작 확인 | 사용자. 디자인 검증은 Chromium만이었음 |
| D-5 | 예시 흔적 제거 | 사용자 |
| D-6 | 없는 주차·없는 지난 토픽은 링크를 그리지 않음 | 사용자 |
| D-7 | 다크 모드·글꼴 서브셋은 MVP 뒤. CSS는 외부 파일 + 내용 해시 | 사용자 |
| D-9 | ⚠(확인 필요) 표기: 작은 회색 글자(5.5) | 사용자 |
| D-10 | W40 트렌딩: 월간 목록 근사, 별 없이, 한국어 한 줄, 안내 한 줄 | 사용자. stargazers API 404(2026-10-11 재확인) |
| D-11 | export 스키마 = `trendsit-example.json` 구조(AGENTS.md "최종 출력 형식은 예시 JSON과 같아야 함"). 못 만드는 칸은 화면에서 뺀다(63 4.0 3번) | 사용자위임, AGENTS.md |
| D-12 | 관리 화면의 S5 새 데이터는 예시 JSON 칸까지만: 실행 1건 = 단계 레일(steps의 역할 문장) + 반려 비교(steps.detail의 draft/evidence) + counts. 3라운드 초안 전문·decide 쌍 표는 넣지 않음 | 사용자위임. 예시 runs·steps가 S5 steps 표와 대응하게 설계됨(64 5.9) |
| D-13 | 사이트에는 published 주만 나온다 | 사용자위임. S6b 자동 발행과 일관 |
| D-19 | `data/` 아래 추적 파일 2개(`trendsit-example.json`, `make_data.py`)를 `site_src/example/`로 옮기고 `.gitignore`가 `data`·`site` 링크도 무시하게. 병합 직후 실행 폴더를 한 번 `fetch` + `reset --hard origin/main` | 실측(임시 저장소 재현 2026-10-11): 실행 폴더는 data/가 링크라 그 파일을 바꾸거나 옮기는 커밋이 오면 `pull --ff-only`가 Aborting. 옮긴 뒤 한 번 reset하면 이후 pull 정상, 링크·DB 보존. skip-worktree는 효과 없음. 리뷰 handoff 003-2 |
| D-20 | verify_s5 B7·A17을 "스냅숏의 명령·옵션이 하나도 사라지지 않음(추가 허용)"으로 | 원래 목적은 S5-1 리팩터가 기능을 빼지 않았다는 보장. S6b가 ops·publish·`--force`를 더해 완전 일치가 깨짐(handoff 003-3) |
| D-14 | 브라우저 측정은 전역 playwright-core(Node, `@playwright/cli`에 포함)로. 새 의존성 없음 | 실측: WebKit 26.5·Chromium 실행 확인(2026-10-11) |

## 2. 준비물 (환경 전제·검증 명령·유료 상한)

| 항목 | 값 |
|---|---|
| 실행 경로 | `~/Claude/projects/trendsit`(작업 폴더, PR 브랜치) |
| 런타임 | Python·uv 기존. `site_src/build.py`는 표준 라이브러리만(지금 규칙 유지) |
| 브라우저 측정 | Node 24(`/Users/jiseop/.nvm/versions/node/v24.18.0/bin/node`), playwright-core 1.62(`$(npm root -g)/@playwright/cli/node_modules/playwright-core`), 브라우저 캐시 `~/Library/Caches/ms-playwright`(chromium-1234, webkit-2359). 경로는 스크립트가 찾고, 없으면 브라우저 AC를 실패로(건너뛰지 않음) |
| 환경변수 | 기존. 새 변수 없음 |
| **검증 명령(게이트)** | `bash scripts/verify_s6a.sh`(0원, 15분 이내): ruff + `pytest -q tests/test_export*.py tests/test_site*.py` + 픽스처 사이트 빌드 + `python3 site_src/check.py --fixture`(정적 검사 + 관문 9 Chromium·WebKit + 동작). 실패 시 종료 코드 ≠ 0 |
| **유료 호출 상한** | 워크플로우 안 $0. 런 뒤 W40 근사 목록 repo_oneliner(10개 약 $0.01)만, 스펙 꼬리표 `S6a`, 상한 $0.10(기획 세션이 budget.yaml `specs.S6a: 0.10` 커밋) |

## 3. 범위

### 3.1 한다
0. (첫 단계) `git mv data/trendsit-example.json data/make_data.py site_src/example/`, `.gitignore`의 두 예외 줄 삭제와 `/data`·`/site`(끝 슬래시 없이, 링크도 무시) 추가, 이 두 파일을 읽던 코드(`site_src/build.py`, `site_src/check.py`)는 이 스펙에서 어차피 다시 쓰므로 예시 파일을 읽지 않게 됨(D-19). 자동 모드가 `git mv`를 막으면 `mkdir -p site_src/example && mv … && git add -A data site_src/example`로 같은 결과(내용 불변 이동)
1. `trendsit export`: DB → `data/site.json`(예시 JSON 구조, published 주만)
2. `site_src/build.py`: `data/site.json` → 디자인 시스템 v1 마크업. 홈, 주차, 토픽, 소스, 키워드, 실행 기록(주차별 / 이번 주차 / 1건)
3. 글꼴·CSS: Pretendard 400·500 직접 호스팅, tokens.css + trendsit.css를 해시 붙은 외부 파일 하나로
4. `publish`(S6b, `trendsit/ops.py`의 `publish(db, week, runner)`·`BUILD_CMD`)가 export → build 순서로 부름. 실행기 주입(runner) 구조는 그대로 쓰고 테스트도 가짜 실행기로
5. W40 트렌딩 근사 목록 스크립트(5.7)
6. `site_src/check.py` 다시 쓰기: 정적 검사 + 관문 9(Chromium·WebKit) + 동작 검사, 픽스처 모드
7. 테스트 픽스처(5.8), verify, README, 리포트
8. `scripts/verify_s5.sh` B7·A17 판정 기준 변경(D-20, 5.11)

### 3.2 비목표
| # | 하지 않는 것 | 이유 | 나중 |
|---|---|---|---|
| NG-1 | 다크 모드, 글꼴 서브셋 | D-7 | MVP 뒤 |
| NG-2 | 관리 화면 조작(승인, 켜기/끄기, 설정 변경) | 디자인 결정(보여 주기만) | 13주차 FastAPI |
| NG-3 | 3라운드 초안 전문, decide 쌍 표, 묶기 리포트 화면 | D-12 | 사용자가 요청하면 |
| NG-4 | Access·로그인, Cloudflare 캐시 비우기 | D-3, S6b NG-6 | 공개 범위 결정 때 |
| NG-5 | 출처 → 인용 백링크, 소스 연결도 | 디자인에서 뺌(81) | 없음 |
| NG-6 | 브리핑 내용(작성자 규칙, 형광 개수) 변경 | 디자인 범위 밖(00 사전결정) | S6-1 이후 |
| NG-7 | 예시 사이트 보존 | 실제 데이터로 교체 | 없음 |

### 3.3 건드리지 않을 것
- `trendsit/brief/`(`briefing.export_topic` 재사용만, 고치지 않음), `trendsit/collect/`(파서 재사용만. 월간 페이지 형식 차이로 고쳐야 하면 `parse_trending`에 인자 하나까지), `roles/`, `skills/`, `eval/`, `config/*.yaml`(기획 세션 소유), S6b의 nightly·weekly 흐름(`ops.py`의 publish 함수만)
- `scripts/run_ops.sh`, `scripts/setup_run_worktree.sh`, `ops/launchd/`(S6b. 실행 폴더 1회 정리는 코드가 아니라 병합 절차, 7장)
- 영역: DB 스키마(마이그레이션 없음), 역할 입력·출력, 디자인 토큰 값(`tokens.css`는 그대로 복사. 바꿔야 하면 멈추고 handoff)

### 3.4 복잡도 예산
| 항목 | 값 |
|---|---|
| 변경하는 기존 파일 | ≤ 8 (`site_src/build.py`, `site_src/check.py`, `trendsit/ops.py`, `trendsit/cli_ops.py`, `README.md`, `.gitignore`, `scripts/verify_s5.sh`, `site_src/style.css` 삭제). 옮기는 파일 2개(`git mv`, 내용 불변)는 따로 센다 |
| 새 파일 | ≤ 14 (`trendsit/export.py`, `site_src/tokens.css`, `site_src/trendsit.css`, `site_src/static/fonts/` woff2 2 + OFL.txt, `site_src/gate.js`, `scripts/trending_monthly.py`, `scripts/verify_s6a.sh`, 테스트 2, 픽스처 1~2, `reports/S6a_report.md`) |
| 새 의존성 | 금지(Python·npm 모두). 전역 playwright-core 사용 |
| 금지 구조 | 템플릿 엔진, 컴포넌트 클래스 계층, 페이지 레지스트리, JS(사이트에는 JS 0. 측정용 gate.js는 사이트에 안 나감) |
| 줄 수 | `build.py`는 지금(1050줄)보다 길어지지 않는다. 500줄 넘는 새 파일 없음 |
| 품질 수준 | 프로덕션(공개 사이트) |

## 4. 폴더

```
trendsit/export.py            DB → site.json
site_src/build.py             site.json → site/ (표준 라이브러리만)
site_src/tokens.css, trendsit.css   docs/reference/s6_design에서 복사(값 그대로)
site_src/static/fonts/        Pretendard-Regular.woff2, Pretendard-Medium.woff2, OFL.txt
site_src/check.py             정적 검사 + 브라우저 측정 호출, --fixture
site_src/gate.js              GATE_JS + 동작 검사(Node, playwright-core)
tests/fixtures/site/          export 결과 모양의 site.json 픽스처(경계 경우 포함)
scripts/trending_monthly.py   W40 근사 목록
data/site.json                export 결과(git 제외)
site/assets/trendsit.<hash>.css, site/assets/fonts/
```

## 5. 상세

### 5.1 `trendsit export [--out data/site.json]`
- 입력: DB. 대상 주 = `weeks.status='published'`, 주의 현재판 = `current_run_id`
- 출력: 예시 JSON(`data/trendsit-example.json`)과 같은 최상위 칸 `meta, weeks, topics, repos, sources, keywords, runs, run_weeks`. 칸별 원천과 빼는 칸:

| 칸 | 원천 | 비고 |
|---|---|---|
| meta | product, generated_at, signal_labels, channel_labels, channel_labels_topic | `example`, `notice`, `markup` 칸 없음(D-5) |
| weeks[] | weeks + runs | id `2026-w42`(소문자), label·range(5.2), published_at, collected(채널별 그 주 항목 수), topic_ids(rank 순), topic_count, source_count, `trending_approx`(bool, 5.7). `next_run` 없음 |
| topics[] | `briefing.export_topic()` 그대로 | 5.3의 화면 계산만 build가 함. `cross_checked` 없음 |
| repos[] | repo_trending(그 주 마지막 수집 run) + repo_oneliners + topic_evidence | name, stars_7d(`+1.6k` 표기, 없으면 null), signal, what(oneliner), topic_id(그 레포를 근거로 쓴 토픽, 없으면 null), url. 토픽 근거로 쓴 레포는 트렌딩에 없어도 포함(디자인 78) |
| sources[] | sources.yaml + items + fetch_log + topic_evidence | id, name, type, channel, url, enabled, weeks{collected, failed_days, used_in_topics}, last{at, count, status}, last_error. `daily`·`note`·`added_at`은 원천이 있으면, 없으면 칸 없음 |
| keywords | keywords.yaml + item_keywords + topics | weeks(발행 주 최근 4개), items[{id, name, aliases, mentions[주별], topics}] |
| runs[] | runs: `kind='nightly'` 전부 + 발행 주의 `current_run_id` weekly | id, kind, at, duration_min, status, summary(한 줄), counts(5.6), steps[{role, text, t, attention, detail?}] |
| run_weeks[] | 발행 주별 집계 | week, label, range, nightly, nightly_failed, collected, candidates, published, rejected, needs_check |

- 불변식은 5.9. 실패: DB 열기 실패·published 주 0개면 종료 코드 1, 파일을 쓰지 않음(기존 site.json 유지)

### 5.2 주차 표기
- id: `2026-W42` → `2026-w42`. label: 그 ISO 주의 **목요일**이 속한 달과 그 달의 몇째 목요일인지 → "10월 3주차". range: "10.12 ~ 10.18"
- 확인 값(실측 계산): W39 → "9월 4주차", W40 → "10월 1주차", W41 → "10월 2주차", W42 → "10월 3주차", 2026-W53(목 12.31) → "12월 5주차". W40이 10월 1주차인 예시 JSON과 일치

### 5.3 토픽 화면 계산(build)
- 블록 순서·클래스는 `DESIGN.md` 4장과 `showcase/pages/topic-*.html`: 머리(제목, 요약, 채널 글자, 후속이면 "지난 흐름" 링크) → 개요 → 핵심 포인트 → 핵심 개념 → 소스별로 더한 것 → 출처(채널별, 영상은 타임라인) → 같은 주 이전·다음, 미니 바
- 출처 번호: 출처 id는 export_topic의 채널별 id(`s1`·`v1`·`g1`), 출처 목록 항목 앵커 `#src-<id>`. 화면 번호 `[n]`은 토픽 안 출처를 채널 순서(글 → 영상 → 레포)·채널 안 id 순으로 1부터. 마크업은 쇼케이스와 같게: `.cite#c-k` 안에 `a.ref[href=#src-<id>][aria-label="출처 n"][aria-describedby=tip-k]`와 `.tip#tip-k`(채널 / 사이트 / 날짜, 제목, "원문 열기", "출처 목록 [n]"). 출처 목록 안에서는 변환하지 않음. url 없는 출처는 "원문 열기" 없음
- 도식: numbers·events는 `anchor` 포인트 바로 아래, 영상 타임라인은 영상 출처를 처음 인용한 포인트 아래. 같은 포인트에 여럿이면 numbers → events → 타임라인 순. 빠진 도식은 없음
- 한국어 조판: `common.py`의 `nb_tokens()`·`rich()`·`point_html()` 규칙을 옮긴다(숫자·영문 토큰 20자 이하 `.nb`, 마지막 어절 + 인용 `.nb-end`, 한 음절이면 앞 어절까지, `==형광==` → `<mark>`, 백틱 → `code.ic`)
- 출처 목록: 출처에 `origin`(원본 URL)이 있으면 그 항목 아래 "원본" 링크 한 줄(글 v2 경유 표시, 63 4.0 5번)
- 링크(D-6): "지난 흐름"은 `relation.topic_id`가 site.json에 있을 때만, "지난 주차"는 이전 published 주가 있을 때만, 이전·다음 토픽은 같은 주 안에서만

### 5.4 홈·주차
- 홈 = 가장 최근 published 주. `week/<id>/`는 모든 published 주. 주차 머리(label 30/500, 둘째 줄 range / 토픽 n / 소스 n / 읽는 시간 약 n분(공백 제외 글자 수 ÷ 500, 올림)), 지난 주차 링크
- 탭 `.has-tabs`: 주요 토픽 n / 트렌딩 레포 n. `#repos`로 레포 탭 바로 열기(CSS `:target` + `:has`). 토픽 목록은 rank 순, 리드 구분 없음, 메타 줄 "글 3 / 영상 1 / 레포 2"(0인 채널 생략, "/ 후속"은 follow_up일 때)
- 레포: 이름, "이번 주 별 +1.6k"(stars_7d가 null이면 이 줄 없음), what, 신호 회색 글자, 관련 토픽 링크. 별만 급증 신호(`needs_check`)는 `.check`
- 레포가 0개인 주: 탭 안에 "이 주는 트렌딩 기록이 없다" 한 줄(W40은 5.7 실행 뒤 근사 목록이 들어가므로 픽스처에서만 확인)

### 5.5 ⚠ 확인 필요 표기(D-9)
- 원천: 포인트는 `points[].check`, 그 밖은 토픽 `checks`(`overview`, `summary`, `concepts[i]` 등. "빠진 도식: …"은 표시 안 함)
- 포인트: 인용 번호 바로 뒤 `<span class="chk">확인 필요</span>`(13px `--fs-xs`, `--c-muted`, 테두리 없음, 왼쪽 간격 `--sp-1`), 인용과 같은 `.nb-end` 묶음 안
- 요약·개요·개념: 그 문단 끝에 같은 표기. 홈 토픽 메타 줄 끝 `/ 확인 필요`(has_check일 때, 개수 없음)
- 새 CSS는 `.chk` 한 규칙만(토큰 변수만 사용, DESIGN.md 7장 절차). `trendsit.css`에 덧붙이지 않고 build가 내는 CSS 파일 끝에 붙인다(원본 복사본은 그대로)

### 5.6 관리 화면(`.ops`, 조작 요소 없음)
- 소스: 표(이름, 채널, 상태, 이번 주 수집, 토픽에 쓰인 수, 마지막 수집), 확인할 것 한 줄(실패 소스 수). 소스 연결도·버튼·"동작 안 함" 안내 없음
- 키워드: 표(이름, 별칭, 최근 4주 언급 수 글자, 관련 토픽 링크)
- 실행 기록: 주차별(run_weeks 표) → 이번 주차(그 주 nightly·weekly 목록) → 1건(키-값: 시각·시간·상태·비용, 단계 레일: steps의 역할 문장, 반려 비교: detail의 draft/evidence). counts: candidates, related{follow_up,new,duplicate}, selected, evidence_ids, review{passed_first, rejected, needs_check}, published(원천은 runs.summary_json과 steps. 원천이 없는 칸은 표에서 뺌)
- nightly 기록이 없는 주(W40·W41)는 "매일 실행 기록 없음(손으로 실행)" 한 줄

### 5.7 W40 트렌딩 근사(`scripts/trending_monthly.py --week 2026-W40`)
- `https://github.com/trending?since=monthly`를 safe_fetch로 1회 받음 → `parse_trending` → `repo_trending`에 이미 있는 **다른 주(W41 이후)** 레포를 뺌 → 남은 순서대로 상위 10개 → `repo_trending`(week=2026-W40, rank, stars_this_week NULL)에 저장, runs 행 `kind='collect'`, `note='trending monthly approx'` → 없는 레포는 repo_oneliner(`--spec S6a`)
- export: 그 주 repo_trending이 이 note의 run에서 왔으면 `weeks[].trending_approx=true`. 홈 레포 탭 위 안내 한 줄 "주간 기록이 없어 월간 목록으로 대신한다"
- 월간 창이 W40을 포함할 때(약 10/28까지) 실행해야 한다. 런 뒤 1회(7장)
- 실패: 받기·파싱 실패면 종료 코드 1, DB 변경 없음. 이미 근사 행이 있으면 다시 넣지 않고 0(멱등)

### 5.8 픽스처와 검사
- `tests/fixtures/site/site.json`: export 결과 모양. 두 주(첫 주는 지난 주차 없음), 경계 경우: 제목 40자 이상, 출처 12개 토픽, 출처 1개 토픽, ⚠ 포인트·⚠ 개요, follow_up(대상 있음 / 없음), 레포 0개 주, trending_approx 주, stars null 레포, numbers·events·영상 타임라인 같은 포인트에, url 없는 출처
- `check.py --fixture`: 픽스처로 임시 폴더에 빌드 → 정적 검사 → `gate.js`(로컬 http 서버) 관문 9 + 동작. 인자 없이 돌리면 `site/`(실데이터)를 같은 기준으로 검사

### 5.9 불변식
| ID | 불변식 | 위반 시 |
|---|---|---|
| C-1 | site.json의 weeks는 모두 DB에서 published이고, topics·repos·runs는 그 주들 것만 | 테스트 실패 |
| C-2 | 모든 토픽의 points[].refs가 그 토픽 sources의 id 안에 있다(빈 refs 0) | export 실패, 종료 1 |
| C-3 | 생성된 HTML의 내부 링크(`href`가 `/` 또는 상대 경로) 대상 파일·앵커가 모두 존재 | check 실패 |
| C-4 | 외부 요청 0: `<link>`·`<script>`·`@import`·`url()`에 http(s) 주소 없음(본문 `<a href>` 출처 링크는 허용). `<script>` 0개 | check 실패 |
| C-5 | 관리 화면에 `button`·`form`·`input`·`select`·`textarea` 0개, "동작 안 함"·"예시" 문자열 0회(사이트 전체) | check 실패 |
| C-6 | 계산된 글자색·배경색·선색이 모두 tokens.css 색 10개 안(관문 9-7) | check 실패 |
| C-7 | `title` 속성 0, 제목 단계 건너뜀 0(관문 9-9) | check 실패 |
| C-8 | 도식은 anchor 포인트 다음, 다음 포인트 앞에 있다 | 테스트 실패 |
| C-9 | `chk` 표기 수 = 표시 대상 check 수(포인트 + 문단), check 없는 토픽에 0 | 테스트 실패 |
| C-10 | `build.py`는 site.json이 없거나 깨지면 종료 1이고 `site/`를 건드리지 않는다(쓰기는 임시 폴더 → 성공 시 교체) | 테스트 실패 |

### 5.10 실패 동작
| 종료 코드 | 조건 |
|---|---|
| 0 | 성공 |
| 1 | export: DB 오류·published 0개·C-2 위반 / build: site.json 없음·깨짐 / trending_monthly: 받기·파싱 실패 / check: 검사 하나라도 실패(실패 목록 출력) |
- publish(S6b)는 export 또는 build가 1이면 상태를 바꾸지 않는다(S6b C-3 유지)
- build는 `site/`를 한 번에 바꾼다: 임시 폴더에 다 만든 뒤 교체. 실패하면 이전 사이트가 그대로 서빙된다

### 5.11 verify_s5 B7·A17
- 지금: `reports/S5-1/help_before.txt`(하위 명령별 `--help` 339줄)와 완전 일치
- 바꿈: 스냅숏의 하위 명령마다 ① 그 명령이 지금도 있고 ② 스냅숏 help의 옵션(`-x`/`--xxx`로 시작하는 토큰) 전부가 지금 help에도 있다. 새 명령·새 옵션·설명 문구 변경은 허용. 스냅숏 파일은 바꾸지 않는다
- 실패 메시지는 사라진 명령·옵션 목록

## 6. 관문 A (`scripts/verify_s6a.sh`)

| ID | 검증 내용 | 판정 방법 | PASS 기준 | 수단 | 관련 |
|---|---|---|---|---|---|
| A1 | export 구조 | 임시 DB(W40·W41 모양 행, 한 주만 published)로 export | 최상위 8칸, 칸별 5.1 표 이름·타입, meta에 example/notice/markup 없음, published 주만(C-1), C-2 | 스크립트 | 5.1 |
| A2 | 주차 표기 | 단위 테스트 | 5.2 확인 값 3개 + 연말(2026-W53 또는 2027-W01) 1개 | 스크립트 | 5.2 |
| A3 | 도식 배치·출처 번호 | 픽스처 빌드 → HTML 파싱 | C-8, 출처 번호 채널 순·id 순, `#src-<id>` 앵커 존재, 타임라인이 첫 영상 인용 포인트 아래 | 스크립트 | 5.3 |
| A4 | ⚠ 표기 | 픽스처 빌드 | C-9, 포인트 표기가 `.nb-end` 안, 홈 메타 `/ 확인 필요` | 스크립트 | 5.5 |
| A5 | 링크 | check 정적 | C-3, 첫 주에 지난 주차 링크 없음, 대상 없는 follow_up에 링크 없음 | 스크립트 | 5.3, D-6 |
| A6 | 외부 요청·글꼴·CSS | check 정적 | C-4, `@font-face` 400·500 둘만, CSS 파일명에 해시, Google Fonts 문자열 0 | 스크립트 | D-7 |
| A7 | 관리 화면·예시 흔적 | check 정적 | C-5, 소스·키워드·실행 기록 3단 페이지 존재 | 스크립트 | 5.6, D-5 |
| A8 | 관문 9 Chromium | gate.js, 375×812·768×1024·1280×900, 홈·토픽 3(긴 제목, 출처 12, 출처 1)·소스·키워드·실행 기록 1건 | 9항목 전부 통과(C-6, C-7 포함) | 스크립트 | D-4 |
| A9 | 관문 9 WebKit + 터치 대체 | gate.js WebKit 375×812(모바일·터치)·1280×900 | 9항목 통과. 375에서 인용 번호 누르면 `#src-<id>`(출처 목록 항목)로 이동 | 스크립트 | D-4 |
| A10 | 동작(Chromium 1280) | gate.js | 툴팁: 0.15초 뒤 표시, 벗어나도 0.6초 유지·1초 뒤 닫힘, 동시에 하나. 탭: 기본 토픽, `#repos`면 레포. 미니 바: 맨 위 숨김, 제목이 위로 빠지면 보임 | 스크립트 | 82 |
| A11 | W40 근사 | 저장한 월간 HTML 픽스처 + 임시 DB | 다른 주 레포 제외, 상위 10, stars NULL, run note, 두 번 실행해도 행 수 같음, export trending_approx, 홈 안내 한 줄·"이번 주 별" 없음 | 스크립트 | 5.7 |
| A12 | 발행 연결·원자 교체 | 임시 DB·폴더 | publish = export → build 순서, build 실패 시 `site/` 바이트 그대로·status 그대로(C-10) | 스크립트 | 5.10 |
| A14 | data/ 정리 | 정적 검사 + 임시 디렉터리 | `git ls-files data` 0줄, `site_src/example/`에 두 파일(내용 해시가 옮기기 전과 같음), `trendsit/`·`site_src/`·`scripts/`에서 `data/trendsit-example.json` 문자열 0회, 임시 폴더의 `data`·`site` **심볼릭 링크**가 `git check-ignore`로 무시됨, `verify_s5.sh` B7·A17이 현재 CLI로 PASS하고 스냅숏에서 옵션 하나를 지운 가짜 help로는 FAIL | 스크립트 | D-19, D-20 |
| A13 | 문서 | 파일 검사 | README "사이트" 절(export·publish·check 명령), `reports/S6a_report.md` 8장까지, `site_src/style.css`·옛 Google Fonts 코드 없음 | 스크립트 | — |

## 7. 관문 B와 QA

- 관문 B 없음(LLM 역할 변경 없음)
- QA(qa-verifier, 0원): **실데이터 빌드**. 작업 폴더 DB에서 W40·W41을 임시 DB 사본으로 published 처리 → export → 임시 폴더 빌드 → `check.py`를 그 폴더에 실행(A8·A9 기준). 원본 DB와 `site/`는 건드리지 않는다. 적대적 차원: 긴 제목, 출처 많은 토픽, ⚠ 많은 토픽(W40 decisions-api 등 실제 값), follow_up 대상이 미발행 주인 경우
- **병합 직후(리뷰 세션, 병합 절차의 일부, 다음 02:00 전)**: `git -C ~/Claude/projects/trendsit-run fetch && git -C ~/Claude/projects/trendsit-run reset --hard origin/main` 1회 → `git -C ~/Claude/projects/trendsit-run status -s`가 빈 출력 → `git -C … pull --ff-only` 성공 확인. 다음 nightly runs 행에 `pull_failed`가 없는지 다음 날 확인(D-19). 이 정리 없이 두면 실행 폴더가 S6b 코드에 머물고, 옛 build.py가 옮겨진 예시 파일을 못 찾아 월요일 발행이 실패한다
- **런 뒤(워크플로우 밖, 구현 세션)**: ① `scripts/trending_monthly.py --week 2026-W40`(S6a 상한 $0.10) ② `trendsit publish --week 2026-W40`, `--week 2026-W41` ③ `check.py`(실사이트) ④ trendsit.jiseop.com을 WebKit 375로 열어 홈·토픽 1개 캡처를 리포트 7장에. 공개 사이트가 바뀌는 단계이므로 ②부터는 **사용자에게 진행을 묻지 않고 하되**, 결과(바뀐 페이지 수, 캡처)를 리포트와 PR 설명 맨 위에 적는다(사용자 승인 2026-10-11: 기획부터 구현까지 확인 없이 진행)

## 8. 단계 (커밋 단위)

| ID | 단계 | 완료 AC | 산출물 |
|---|---|---|---|
| S-1 | data/ 정리(첫 커밋, 따로) → verify_s5 B7·A17 → export + 주차 표기 + W40 근사 스크립트 | A14, A1, A2, A11 | trendsit/export.py, cli_ops.py, scripts/trending_monthly.py, 테스트 |
| S-2 | build 다시 쓰기(읽기 화면 + 관리 화면), 글꼴·CSS, ⚠ | A3~A7 | site_src/build.py, css, fonts, 픽스처 |
| S-3 | check.py·gate.js, publish 연결, 원자 교체 | A8~A10, A12 | site_src/check.py, gate.js, ops.py |
| S-4 | README, 리포트, 정리 | A13 | README.md, reports/S6a_report.md |

## 9. 넘길 것과 미확정

- 미해결 `Q-*`: 0건
- 구현 시점 기본값(리포트 "결정한 것"에): 읽는 시간 계산의 글자 범위(제목·요약·개요·포인트), 실행 1건 페이지 경로(`runs/<week>/<run_id>/`), 소스 표 정렬(채널 → 이름), 키워드 언급 수 표기("0 / 2 / 9 / 11"), 미니 바 "출처 n" 숫자
- OFL.txt: Pretendard 저장소의 라이선스 원문(https://github.com/orioncactus/pretendard, OFL-1.1)을 그대로
- budget.yaml `specs.S6a: 0.10`은 기획 세션이 main에 커밋함(2026-10-11)
- 병합 뒤 기획 세션: 19·63·64 부록 C, 디자인 열린 질문(다크 모드·서브셋) 기록 유지
- S6-1로 넘긴 것(handoff 003-1·003-4): `plan run`이 BudgetExceeded를 규칙 기반 대체 계획으로 처리할 때 runs `summary_json`에 `fallback_plan` 표시, `setup_run_worktree.sh`가 `git fetch` 뒤 `origin/main`으로 실행 폴더를 만들기, 래퍼의 `pull --ff-only`를 `fetch` + `reset --hard origin/main`으로 바꿀지(실행 폴더는 배포 전용)

## 13. 실측 반영 이력
| 날짜 | 런 | 발견 | 근거 | 변경한 § |
|---|---|---|---|---|
