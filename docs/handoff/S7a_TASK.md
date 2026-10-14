# S7a 실행 기록 화면: 주차 → 날 → run 목록, run 1건 단계 상세, nightly 끝 사이트 재생성

> 기획 세션 작성 2026-10-14(spec-planner, 원장 저장소 `.workflow/planning/s7a/ledger.md` D-1~D-22). 디자인 확정본 `claude/s7a_시안/FINAL.md` + `final/*.html`(Cowork 세션, 사용자 확정 2026-10-13). 기준 커밋 = **S6-1 병합 뒤 main**(이 문서는 `s6-1-detail` 코드 기준으로 썼다).
> 구현 세션 시작 절차: S6-1 병합 확인 → `git fetch origin && git switch -c s7a-records origin/main`(작업 폴더에서 `git switch main` 불가, 85 3.1) → 이 문서를 `docs/handoff/S7a_TASK.md`로 복사 → 첫 커밋 → `/impl-workflow docs/handoff/S7a_TASK.md .`
> 공통 규칙은 `docs/handoff/COMMON.md`(3·12장), 이 문서가 우선한다. 시안 생성기(`claude/s7a_시안/final.py`, `extract_db.py`)는 **참고용**(마크업·CSS 조각·분류 규칙의 실측 근거. 저장소 코드가 아니고 그 구현을 따를 의무 없음).

## 0. 이 스펙이 끝나면 되는 것

| 항목 | 값 |
|---|---|
| slug | `s7a` |
| 버전 / 작성일 | v1 / 2026-10-14 |
| 문서 상태 | **확정(투입 가능)** |
| 미해결 `Q-*` | 0건 |
| 선행 런 | 없음(디자인 원장 D-1~D-22만) |
| 브랜치 | `s7a-records` ← main(S6-1 병합 뒤), 첫 커밋 = 이 문서 |

**한 줄 목표**: 실행 기록이 "언제·자동/수동·무엇을·결과"가 한 줄로 읽히고, run 1건을 열면 단계마다 "누가(코드 / LLM 역할·모델) 무엇을, 왜"가 접힘 없이 보인다. 매일 02:00 nightly가 끝나면 사이트의 실행 기록이 그날 것으로 갱신된다(브리핑은 발행본 그대로). 10/19(월) 07:00 W42 자동 발행이 새 화면으로 보인다.

- 사용자 체감 결과: trendsit.jiseop.com/runs/ 가 주차별 표(5열) → 주차를 누르면 그 주의 날 → run 표(모든 run, 하위 run은 `└`) → run을 누르면 단계 상세(decide 판정 전부, 선별 이유, 토픽 10개 작성⇄검수 체인·반려 표). 10/16 병합·실서버 반영 뒤 다음 날 아침 어젯밤 nightly가 보인다
- 시연(94 5장)에서 쓰는 순서: `/runs/` → 이번 주 → 오늘 02:00 nightly 1건(8단계) → 10월 2주차 → weekly from cluster 1건 → cluster + decide 표 → editor_select 표 → 토픽 1개 체인·반려 표

## 1. 맥락

- **실측된 원인(94 1.0)**: 사이트는 발행 때만 다시 만들어지고(`ops nightly`는 export·build를 안 부름), export C-1이 발행된 주의 nightly만 낸다. 10/12·10/13 02:00 자동 nightly는 DB에 있지만 실서버에 없다. 지금 화면(`/runs/weeks/` 표, `/runs/<주>/` 표 1줄, run 1건 kv + 단계 레일)은 중간평가 평가 항목 ④(출처·로그가 보이는가)를 보여 주기에 부족하다(92 1장)
- **결정 로그**: 원장 D-1~D-22(= 64 부록 C-35). 핵심 — D-1 과정 페이지 안 함 / D-4 위계 주차 → 날 → run → 단계 / D-5 과거 수동 run도 올림, 개발용 run 제외 / D-6 성능 원칙(새 기록 금지, nightly 끝 export+build 1회) / D-7 공개 금칙 / D-10·D-11 디버그용·시스템 이름·자동/수동 / D-12 돌지 않은 run 숨김 / D-14 확정 시안(쪽 구조·열·접힘 0) / D-15 주차 귀속 = run이 다루는 주 / D-16 weekly run 전부 한 줄씩 / D-17 수동 단계별 run 날마다 한 줄 / D-18 누가 = 글자 + 인라인 코드 / D-19 publish는 run 아님 / D-20 상세 표 전부 / D-21·D-22 토픽 페이지·홈 불변
- **디자인 기준**: `claude/s7a_시안/FINAL.md` 0·1·4장(쪽 구조, 열·폭, CSS 조각 이름), 캡처 `final/shots/*_1280.png`·`*_375.png`. 디자인 시스템 v1(`site_src/tokens.css` 불변, DESIGN.md 4.4·5·6장)
- 근거 실측(2026-10-13~14, 실DB 읽기): runs.kind 분포(nightly 5, weekly 85, ops-weekly 1, 개발용 role 471·eval 72·proto 12·image-check 2·rematch 4), weekly `spec`는 손 실행 전부 `S5`·ops 호출은 `RUN-<주>`(ops.py 303·320), nightly `summary_json.manual`은 `--day`일 때만(ops.py 250), nightly 하위 run은 `spec=RUN-<주>` + 시작~끝 구간으로 잇는다(ops.py 245 비용 집계와 같은 방식), `weekly` summary_json 칸(`evidence`·`aliases`·`cluster`·`select`·`write`·`review`·`cost_usd`·`duration_sec`), 토픽 1개 재실행 run의 summary_json은 주 누적치(run 자체 수치 없음), publish는 `weeks.published_at`만(재발행 시 덮임, 10.11 13:44 → 10.13 20:57), `data/site.json` 149KB, cluster_pairs decided 590행

## 2. 준비물 (환경 전제·검증 명령·유료 상한)

| 항목 | 값 |
|---|---|
| 실행 경로 | `~/Claude/projects/trendsit`(작업 폴더, 브랜치 `s7a-records`) |
| 런타임 | Python 3.12 + uv 기존. `site_src/build.py`·`build_runs.py`·`check.py`는 표준 라이브러리만(S6a 규칙). 브라우저 측정 S6a와 같음(Node 24 `/Users/jiseop/.nvm/versions/node/v24.18.0/bin/node`, 전역 playwright-core, Chromium·WebKit 캐시) |
| 환경변수 | 기존. 새 변수 없음(5.1-2) |
| 실DB | 읽기 전용 참고(`data/trendsit.db`). 테스트·게이트는 임시 DB·픽스처만 |
| **검증 명령(게이트)** | `bash scripts/verify_s7a.sh`(0원, LLM·네트워크 없음): ruff + `pytest -q`(전체, 건너뜀 0) + `python3 site_src/check.py --fixture` + 6장 항목별 검사 + 회귀 `verify_s6a.sh`·`verify_s6b.sh` 종료 코드 0. 실측(2026-10-14 00:20, s6-1-detail, 다른 작업과 병행): `verify_s6a.sh` 전체 4분 06초(19항목 PASS, check.py --fixture 포함), pytest 전체 약 40초(91) → 게이트 약 8분(check --fixture가 verify_s7a와 s6a에서 두 번 돎, 상한 15분 안. 넘기면 s6a 호출을 S-3 끝 1회로 옮긴다). `verify_s6-1.sh`(A11 안에 s6a·s6b·s5 --fast 중첩, 약 6분)는 게이트에 넣지 않고 **S-3 끝과 런 뒤 1회**(A10) |
| **유료 호출 상한** | **$0**. 이 스펙은 LLM을 부르지 않는다. 런 뒤 실서버 반영(7장)도 $0 |

## 3. 범위

### 3.1 한다
1. **ops**: nightly 끝에 사이트만 다시 만들기(export → build → `data/site.json` 교체, 주 상태·published_at 불변). 실패해도 nightly 상태·종료 코드 불변. `trendsit publish --site-only`로 같은 동작을 손으로
2. **export**: `runs`·`run_weeks`를 새 계약(5.2)으로. 발행 주 + 진행 주, nightly 전부(돌지 않은 것 제외), weekly 전부(week 있는 것), 수동 단계별 run 묶음, 자동/수동, 하위 run 분류, run 1건 상세 칸(weekly 6단계·nightly 8단계, 전부)
3. **build**: `/runs/` 주차별 표 → `/runs/<주>/` 날 → run 표 → `/runs/<주>/<run>/` 수치 레일 + 단계 목록(접힘 0). 새 파일 `site_src/build_runs.py`. CSS 조각은 FINAL 4장 이름으로 `trendsit.css`에
4. **check·gate**: 새 경로 존재, `/runs/weeks/` 없음, 금칙 문자열 0, 발췌 길이, `details` 0, site.json 크기, 관문 9에 run 목록·run 1건(weekly·nightly) 추가
5. 테스트·픽스처(`tests/fixtures/site/site.json`·`s6_1/site_v2.json`의 runs·run_weeks를 새 계약으로), verify_s6-1 A2의 옛 문구 항목 개정, README 실행 기록 절 한 단락, CLAUDE.md 진행 블록

### 3.2 비목표
| # | 하지 않는 것 | 이유 | 나중 |
|---|---|---|---|
| NG-1 | 별도 "과정" 페이지, 자동 재생, JS | D-1, 88 | 없음 |
| NG-2 | 소스·키워드 페이지 손질(94 2·3장) | D-8 → S7b | S7b |
| NG-3 | 새 기록(DB 칸·테이블·로그) 추가, LLM 호출·DB 쓰기 경로 변경. publish를 run으로 남기기 | D-6, D-19 | 사용자가 원하면 |
| NG-4 | 토픽 페이지 "검수 기록" 링크, 홈·주차 페이지 nightly 한 줄 | D-21, D-22 | 없음 |
| NG-5 | 모바일(375) 디자인 검토. 넘침 0만 보장(FINAL 0장 8) | 디버그 화면, PC 우선 | 다음 사이클 |
| NG-6 | 토픽 1개 재실행 run의 run 단위 집계를 write 단계에서 남기기(FINAL 6장 3) | NG-3. 화면은 `topics 1 / steps n` | 없음 |
| NG-7 | `running`인 채 남은 run의 stale 처리(일정 시간 뒤 failed) | 글자 그대로 보여 준다(FINAL 6장 4) | 필요하면 |
| NG-8 | 오류 원문을 사람 말로 바꾸는 사전 | 오류는 상태·종류만(D-7) | S7b 소스 상태 칸에서 |
| NG-9 | `/runs/weeks/` 경로 리다이렉트 | 외부 링크 없음, S6a 이후 2주 | 없음 |
| NG-10 | 디자인 문서(`docs/reference/s6_design/DESIGN.md`) 갱신 | 참고 복사본 불변(91 9장과 같음) | 다음 사이클 |

### 3.3 건드리지 않을 것
- `trendsit/collect/`, `filter/`, `deep/`, `video/`, `summarize.py`, `brief/`(cluster·select·write·checks·revision·briefing·pipeline·evidence·fulltext·slides), `core/`(llm·role·agent·db·config·context·numbers·artifacts), `roles/`, `skills/`, `eval/`, `config/*.yaml`(ops.yaml 포함. 새 칸 없음), `ops/launchd/`, `scripts/run_ops.sh`(5.1-2), `scripts/setup_run_worktree.sh`
- `trendsit/ops.py`의 `nightly`·`weekly`·`publish` 흐름(5.1-1의 끝 단계 호출 1곳과 `publish --site-only` 분기만), `cli_ops.py`(옵션 1개)
- `site_src/tokens.css` 값, `site_src/build.py`의 홈·주차·토픽·소스·키워드 렌더(runs 관련 함수 3개와 `build_into`의 runs 줄만 바꿈), `site_src/example/`, `docs/reference/`
- 영역: DB 스키마(마이그레이션 없음), `weeks` 상태·`published_at`(site-only는 안 바꿈), 토픽 페이지 마크업, 홈 마크업, 비용 꼬리표, 공개 범위(발행 주 토픽만)

### 3.4 복잡도 예산
| 항목 | 값 |
|---|---|
| 변경하는 기존 파일 | ≤ 18: 코드 7(`trendsit/export.py`, `trendsit/ops.py`, `trendsit/cli_ops.py`, `site_src/build.py`, `site_src/check.py`, `site_src/gate.js`, `site_src/trendsit.css`), 테스트 4(`tests/test_export.py`, `tests/test_site.py`, `tests/test_ops.py`, `tests/test_s6_1_site.py`), 픽스처 2(`tests/fixtures/site/site.json`, `tests/fixtures/s6_1/site_v2.json`), 스크립트 1(`scripts/verify_s6-1.sh` A2 문구 항목), 문서 3(`README.md`, `CLAUDE.md` 진행 블록, `AGENTS.md` 출력 형식 줄). `tests/test_ops_publish.py`가 있으면 그것도 포함(목록 안에서 교체, 상한 그대로) |
| 새 파일 | ≤ 6: `trendsit/export_runs.py`(runs·run_weeks·상세 칸), `site_src/build_runs.py`(실행 기록 3쪽), `tests/test_s7a.py`, `scripts/verify_s7a.sh`, `reports/S7a_report.md`, `reports/S7a/shots/`(캡처 폴더) |
| 삭제 | `build.py`의 `render_runs_weeks`·`render_runs_week`·`render_run`과 `.rail .kv .cmp` 중 안 쓰게 되는 CSS(쓰는 조각은 남김), `KIND_LABELS`·`STATUS_LABELS`·`STATUS_ALERT`가 runs 전용이면 build_runs.py로 이동 |
| 새 의존성 | 금지(Python·npm) |
| 금지 구조 | 템플릿 엔진, 컴포넌트 클래스 계층, 플러그인·레지스트리, 새 설정 파일·설정 칸, 새 환경 변수, 사이트 JS, `<details>`(접힘 0), 오류 원문 사전 |
| 줄 수 | `build.py` ≤ 700(runs 코드가 빠져 줄어듦), `build_runs.py` ≤ 500, `export.py` ≤ 350(지금 328, 호출만 추가), `export_runs.py` ≤ 450, `check.py` ≤ 480, 함수 ≤ 60줄(verify_s5 B4 유지) |
| 품질 수준 | 프로덕션(공개 사이트, 무인 자동 실행의 끝 단계) |

예산은 추정이 아니라 의도다. 넘길 것 같으면 멈추고 `handoff/NNN_impl→plan.md`.

### 3.5 구현이 추가하면 안 되는 것(기본)
명세에 없는 옵션·플래그·환경변수, 추상화 계층, 한 번 쓰는 헬퍼, 일어날 수 없는 상황의 방어 코드, 바꾸지 않은 코드의 주석·타입 표기. 화면에 한국어 서술 메모("첫 무인 실행", "정상" 같은 상태 번역), 배지 3종, 접이식, 가운뎃점 구분자.

## 4. 폴더

```
trendsit/export.py            build()가 export_runs를 부르고 runs·run_weeks를 채움(진행 주 포함)
trendsit/export_runs.py       (새) runs 선택·분류·상세 칸, run_weeks
trendsit/ops.py               nightly 끝 rebuild_site(), publish(site_only=True)
trendsit/cli_ops.py           publish --site-only
site_src/build.py             runs 함수 3개 제거, build_runs 호출
site_src/build_runs.py        (새) /runs/, /runs/<주>/, /runs/<주>/<run>/
site_src/trendsit.css         FINAL 4장 조각
site_src/check.py, gate.js    새 경로·금칙·크기·관문 9 대상
tests/test_s7a.py             (새) 5.1~5.4 단위 + 화면 파싱
tests/fixtures/site/site.json, tests/fixtures/s6_1/site_v2.json   runs·run_weeks 새 계약
scripts/verify_s7a.sh         (새) 게이트
reports/S7a_report.md, reports/S7a/shots/   런 뒤
```

## 5. 상세

### 5.1 ops: nightly 끝 사이트 재생성, `publish --site-only`
1. `trendsit/ops.py`에 함수 하나 `rebuild_site(db, runner=run_subprocess) -> int`: `export_site(db, tmp, None)` → `BUILD_CMD --data tmp` → 성공 시 `os.replace(tmp, data/site.json)`. `weeks` 행은 **읽기만**(status·published_at 불변). 반환 0 성공 / 1 export 또는 빌드 실패(stderr 한 줄 `사이트 재생성 실패: <원인>`). `publish()`의 임시 파일·교체 코드를 공유한다(중복 금지: publish가 rebuild 부분을 이 함수로)
   - `_nightly_locked`의 `finally`에서 `_close_run` **뒤**(status·종료 코드가 정해진 뒤), 잠금을 쥔 채로 1회 호출. 결과는 그 nightly 행의 `summary_json["site"] = {"exit": int, "sec": float}`로만 남긴다(`steps`에는 넣지 않는다 → status 계산과 `catchup_days`에 영향 0). `days`가 비어 건너뛴 nightly(`_skipped`)에서는 부르지 않는다
   - `weekly()`는 publish가 이미 빌드하므로 부르지 않는다. publish가 실패한 weekly 뒤에도 부르지 않는다(상태가 `done`인 주는 C-1대로 토픽을 안 내므로 의미 없음)
   - 시간 상한: `cfg.step_timeout_min`(기존 칸) 그대로 runner timeout. 넘기면 exit 124 기록, nightly 결과 불변
2. **자동/수동 판별(D-11, C-10)**: 새 환경 변수·note 변경 없음(handoff 009 c의 "래퍼 환경 변수"는 **쓰지 않는다** — 과거 run에 표시가 없어 이력이 틀리고, 기존 칸으로 같은 뜻을 낼 수 있음). 규칙: nightly는 `summary_json.manual` 없음 → auto, 있음 → manual. weekly는 `spec LIKE 'RUN-%'` → auto(ops가 띄운 것), 그 밖(`S5` 등) → manual. 수동 단계별 묶음(5.2-1 ③)은 항상 manual. 손으로 `trendsit ops nightly`(`--day` 없이)를 돌리면 auto로 보인다(같은 코드 경로, 허용)
3. `trendsit publish --site-only`: `--week` 없이 쓸 수 있고(같이 주면 오류 2 "둘 중 하나만"), `rebuild_site`를 부르고 그 종료 코드를 돌려준다. 기존 `publish --week W`는 불변(export with_week → build → status 변경)

### 5.2 export v3: `runs`·`run_weeks` (인터페이스 계약)
최상위 8칸 이름은 그대로(`meta, weeks, topics, repos, sources, keywords, runs, run_weeks`). `weeks`·`topics`·`repos`·`sources`·`keywords`는 S6-1 5.7 그대로(발행 주만). 바뀌는 것은 `runs`·`run_weeks`와 그 주 범위.

**1) 주 범위와 run 선택(C-1 개정, C-2)**
- 주 집합 = 발행 주(weeks 표 status published) ∪ **진행 주**(status ≠ published이고 아래 run이 1건 이상인 주, 보통 이번 주 1개). `run_weeks`는 이 집합 전부, 최근 주가 앞
- run 귀속 주(D-15): nightly = `summary_json.days[0]`의 ISO 주(비면 제외). weekly = `runs.week`(NULL이면 제외). 수동 단계별 묶음 = 실행 날짜의 ISO 주. publish 줄은 run이 아니라 `weeks.published_at`(build가 그 날짜 아래에 줄 하나)
- 내는 run: ① `kind='nightly'`이고 `summary_json.steps`가 비어 있지 않은 것(D-12: "범위 없음"·건너뜀은 제외). ② `kind='weekly'`이고 `week`가 있는 것 **전부**(D-16: 토픽 1개 재실행 포함, 중단·running 포함). ③ 수동 단계별 묶음: `kind IN ('collect','filter','summarize','plan','deep-text','video','repo-analyze')`이고 `spec NOT LIKE 'RUN-%'`(= nightly 하위가 아닌 손 실행)인 run을 **실행 날짜별로 한 줄**(D-17). `started_at >= config ops.start_day - 7일`이 아니라 **DB에 있는 것 전부**(10/7부터; 그 이전은 없음). 개발용(`role`·`eval`·`proto`·`image-check`·`rematch`·`ops-weekly`)은 안 냄
- 주 집합 밖의 run은 안 냄(귀속 주가 집합에 없으면 제외)

**2) `runs[]` 스키마**(칸 순서 고정, null 허용 표시)
```
id            str   runs.id (③은 "steps-<YYYY-MM-DD>")
kind          "nightly" | "weekly" | "steps"
at            str   ISO(+09:00) 시작. ③은 그날 첫 run 시작
end           str|null  끝. running이면 null
duration_sec  int|null
day           "YYYY-MM-DD"  실행 날짜(at 기준)
week          "2026-w41"    귀속 주 id(소문자, 기존 week_id)
mode          "auto" | "manual"  (5.1-2)
status        "ok" | "partial" | "failed" | "running" | "stopped"  runs.status 그대로(③은 전부 ok면 ok, 아니면 partial)
cost_usd      float 4자리  nightly는 summary_json.cost_usd(기존), weekly·③은 runs.cost_usd 합
current       bool  weeks.current_run_id == id (weekly만 true 가능)
label         str   run 열 글자: nightly "nightly 10.12"(처리한 날, 여러 날이면 "10.10~10.11") / weekly: note에서 "weekly <주> " 접두를 뗀 것("from cluster", "from select until select", "from write topic w41-x", 옛 "cluster 2026-W41") / ③ "steps"
sub           bool  하위 run(들여쓰기 + └): weekly에서 label이 "from cluster"도 "cluster …"도 아닌 것(단계부터·토픽 1개). nightly·③은 false
topic_id      str|null  weekly topic 재실행이면 "w41-…"
result        object  종류별(아래)
summary       object|null  run 1건 머리 수치 레일 원천(아래). ③은 null
steps         list    run 1건 단계(5.2-3). ③은 []
```
`result`:
- nightly: `{"steps": n, "failed": n}` (summary_json.steps 개수, exit≠0 개수)
- weekly 전체·단계부터(`topic_id` null): `{"clusters", "candidates", "selected", "topics", "code_rejects", "check_topics"}` — summary_json의 `cluster.clusters`, `select.candidates`, `select.selected`, `write.topics`, `review.code_rejects`, `review.check_topics`. 없는 칸은 null
- weekly topic 1개: `{"topics": 1, "steps": n}` (n = 그 run의 steps 행 수. summary_json은 주 누적치라 쓰지 않음, NG-6)
- ③: `{"kinds": {"collect": {"ok": 7, "partial": 1}, …}}` kind별 status별 수

`summary`(run 1건 머리 레일):
- nightly: `{"collected": n, "filter_keep": n, "cards": n, "deep_text": n, "video": n, "repo": n, "exit_nonzero": n}` — collect 하위 run의 fetch_log `SUM(n_new)`, filter 하위 run 뒤 `items.filter_status='pass'`인 그날 항목 수, summarize 하위 run의 `steps` role item_card llm 행 수, plans.plan_json의 `text_queue`·`video_queue`·`repo_queue` 길이, summary_json.steps exit≠0 수
- weekly: `{"clusters", "candidates", "selected", "topics", "published", "rounds": {"1": n, "2": n, "3": n}, "code_rejects", "critic_rejects", "check_topics"}` — summary_json 그대로(`published`는 weeks.current_run_id == id이면 발행 토픽 수, 아니면 null)

**3) `steps[]`(run 1건 단계)** — 칸: `t`(HH:MM), `name`, `who`(list of `{"kind": "code"|"llm"|"agent", "role": str|null, "model": str|null, "n": int|null}`), `line`(한 줄 결과, 시스템 이름·수치만), `duration_sec`, `cost_usd`, `attention`(bool), `detail`(list of 블록: `{"type": "kv", "items": [[k, v], …]}` / `{"type": "list", "items": [str]}` / `{"type": "table", "head": [..], "rows": [[..]]}` / `{"type": "topics", "items": [토픽 블록]}`). **전부 낸다(D-20)**, 자르지 않는다. 글자 칸(이유·지적·comment)은 **300자**에서 자른다(C-5).

| run | 단계(name) | who | line·detail 원천(실측 칸) |
|---|---|---|---|
| weekly | `evidence` | code | steps role evidence: text, detail `counts`·`excluded`, 둘째 행 detail(영상 관련성 점수 → high/mid 수) |
| weekly | `normalize` | code | steps role normalize: text, detail counts. list: `aliases WHERE run_id=? AND origin='normalizer' AND status='approved'`의 `alias → canonical` + reason |
| weekly | `cluster + decide` | code + llm(decide, model, n=decide 행 수) | steps role cluster: text, detail(clusters·candidates·multi_channel·decide_calls). table head `a / b / 판정 / 이유 / 확신도`: `cluster_pairs WHERE run_id=? AND decided=1` 전부, a·b는 `items.title`(id "it:<n>"; "vd:"·"rp:"는 videos.title·repos.full_name) + " (" + sources 이름 + ")", 판정 `같음`/`다름`, confidence 2자리. attention = decide steps 중 attention=1이 1건 이상 → line 끝에 `attention n` |
| weekly | `editor_select` | llm(editor_select, model) | steps editor_select llm: text. table head `순위 / 후보 / 판정 / 이유`: `briefing_plans.plan_json.decisions` 전부 — 후보 이름은 선정이면 `topics.title`(cluster_ids_json에 그 cluster_id가 있는 토픽), 아니면 그 묶음 첫 구성원 제목(`cluster_items` → items.title), 판정 `select`/`drop(<drop_reason>)`, 순위는 topics.rank. kv: steps editor_select code detail의 `reconciled`·`source`, summary_json `cluster.past` |
| weekly | `writer ⇄ critic` | llm(writer ×n)·llm(critic ×n)·llm(writer_revise ×n) | line: topics n / rounds / code_rejects / critic_rejects / check_topics(summary_json.review). detail `topics`: 토픽마다 `{"rank", "title", "topic_id", "status", "final_round", "tokens_in", "tokens_out", "cost_usd", "chain": [[이름, 글자], …], "issues": [[위치, 종류, 지적, 수정], …]}` — 토픽 경계는 steps role writer kind code의 `detail.topic_id`(그 code 행 **이전**, 직전 writer/code 행 **이후**의 llm 행들이 그 토픽). chain = 그 구간 llm·code 행을 순서대로 `writer 근거 id n / 절 n`(writer llm text), `code 반려 n`(code detail rounds[i].issues 수, status), `writer_revise k/m`(text), `critic <text>`, 끝 `code <status>`. issues = rounds[].issues의 (loc, type, comment, 수정 = writer_revise output.changed의 같은 loc action) |
| weekly | `weekly 끝` | code | steps role weekly 마지막 행 text + detail duration_sec |
| nightly | `collect` | code | collect 하위 run: fetch_log `source_id, status, n_new, n_seen`(list "소스 n_new (status)"), 실패 소스 수. **오류 원문(error) 안 냄** |
| nightly | `filter` | code | filter 하위 run의 steps text; kv: 그날(days) items `filter_status`별 수, `filter_reason` 상위 전부(excluded:·no_keyword) |
| nightly | `summarize` | llm(item_card ×n) | summarize 하위 run steps llm 행: 수, tokens_in/out 합, cost 합, attention 수 |
| nightly | `plan` | llm(editor_plan) | `plans WHERE day=?` 마지막 행 plan_json: list `text_queue`(items.title + reason + depth), `video_queue`(videos.title + reason + mode), `repo_queue`(full_name + reason); `log`; `source`가 fallback이면 line에 `fallback`; attention = plan_json.attention |
| nightly | `deep_text` | agent(text_analyst ×n) | deep-text 하위 run: table head `항목 / 원본 추적 경로 / 깊이 / 대조`: `item_cards WHERE version=2 AND run_id=?`의 card_json `trail[].url`을 **도메인만**(`github.com`) `→`로 이어 붙임, 최대 depth, `log` 300자. 도구 호출 수 = 그 run steps kind tool 행 수 |
| nightly | `video` | agent(video_analyst ×n) | video 하위 run들: `video_digests WHERE run_id IN (…)` digest_json `mode`, `span`, `segments_count`, `transcript_quality` + videos.title. 슬라이드 수는 `video_frames` 행 수(있으면) |
| nightly | `repo_analyze` | agent(repo_analyst ×n) | repo-analyze 하위 run: `repo_cards WHERE run_id=?` full_name + card_json 한 줄(`summary` 또는 첫 글자 칸 300자), 도구 호출 수 |
| nightly | `export + build` | code | summary_json.site(5.1-1): exit·sec. 없으면(이 스펙 전 run) 단계 생략 |

- 하위 run 찾기: `runs WHERE spec=? AND started_at >= nightly.started_at AND started_at <= nightly.finished_at AND kind=<단계 kind>` (spec = nightly.spec). 하루치 단계(plan·deep_text·video·repo_analyze)가 여러 날이면 `summary_json.steps[].day` 순서대로 짝짓는다. 하위 run이 없으면 그 단계는 line만(summary_json.steps의 exit·sec)
- 시각 `t` = 하위 run 또는 steps 행의 시각. 글자 칸은 시스템 이름(역할·kind·status)을 그대로, 한국어는 열 머리와 `같음/다름/선정/제외` 같은 고정 어휘만

**4) `run_weeks[]`**
```
week, label, range     기존
status                 weeks.status ("open"|…|"published")
nightly_days           int  그 주 날짜 중 nightly(auto·manual)가 처리한 날 수(summary_json.days 합집합 ∩ 주 범위)
weekly                 {"total": n, "full": n, "partial": n, "topic": n}  full = label이 "from cluster"·"cluster …", partial = 그 밖 단계부터, topic = topic_id 있음
published_at           str|null
current_run_id         str|null
```
옛 칸(`nightly`, `nightly_failed`, `collected`, `candidates`, `published`, `rejected`, `needs_check`)은 **없앤다**(A1 테스트 개정).

**실제 예시** — 정상 1(아래), 이상 1: `weekly` run인데 `week` NULL(10/9 `cluster embed compare`) → runs에 없음; nightly `steps: []` → 없음; `role` run → 없음.
```json
{"id": "20261013-020006-nightly-1b8b", "kind": "nightly", "at": "2026-10-13T02:00:06+09:00", "end": "2026-10-13T02:13:55+09:00",
 "duration_sec": 829, "day": "2026-10-13", "week": "2026-w42", "mode": "auto", "status": "ok", "cost_usd": 0.1299, "current": false,
 "label": "nightly 10.12", "sub": false, "topic_id": null,
 "result": {"steps": 7, "failed": 0},
 "summary": {"collected": 55, "filter_keep": 35, "cards": 24, "deep_text": 5, "video": 2, "repo": 8, "exit_nonzero": 0},
 "steps": [{"t": "02:00", "name": "collect", "who": [{"kind": "code", "role": null, "model": null, "n": null}], "line": "new 55 / sources 9 / failed 0",
            "duration_sec": 93, "cost_usd": null, "attention": false,
            "detail": [{"type": "list", "items": ["aitimes 28", "github_trending 11", "geeknews 8", "github_releases 6", "techbridge 2", "openai, anthropic, deepmind, simonw 0"]}]}, "…"]}
```
```json
{"week": "2026-w42", "label": "10월 3주차", "range": "10.12 ~ 10.18", "status": "open", "nightly_days": 1,
 "weekly": {"total": 0, "full": 0, "partial": 0, "topic": 0}, "published_at": null, "current_run_id": null}
```
**하위 호환**: `runs`·`run_weeks` 옛 칸을 읽는 곳은 `build.py`(교체)·테스트·픽스처뿐(grep `run_weeks`·`"steps"`·`counts` 확인). 깨지는 외부 소비자 없음.

### 5.3 build: 실행 기록 3쪽(`site_src/build_runs.py`, FINAL 1장)
공통: `ops_page` 셸(`<main class="wrap ops">`), 빵부스러기 `.crumb`(이전 단계 링크, 현재 위치 글자), 상태 글자 `ok` 회색(`.state.ok`), `partial`·`failed`는 `.check` 테두리, `running`·`stopped` 글자 그대로, 현재판 `.cur`(`current`), 자동/수동은 글자 `자동`/`수동`, 비용 `$0.012`(소수 3자리, 0이면 `$0`), 시간 `93초`/`14분`. 가운뎃점 없음(" / " 구분). `<details>`·JS 0.

| 쪽 | 경로 | 내용 |
|---|---|---|
| 주차별 표 | `/runs/` | `.ph` h1 "실행 기록" + 메타 `주차 → 날 → run / 주차를 누르면 그 주의 run 목록`. `.dtable` 5열 `주차(링크) / 기간 / nightly n/7 / weekly n (full n / partial n / topic n) / publish(published_at "10.13 20:57" 또는 "-")`. 행 = run_weeks 전부, 최근 주 위. `/runs/weeks/`는 만들지 않는다 |
| 한 주의 run 목록 | `/runs/<주>/` | `.ph.crumb` + h1 주차 라벨. 범례 한 줄 `.rt-legend`: `결과: weekly는 clusters → candidates → selected → topics / code_rejects / check, topic 1개는 topics 1 / steps, nightly는 steps / exit≠0`. **표 하나** `table.rt.v1`(`col.c-t/.c-m/.c-run/.c-x/.c-s` 폭 고정: 4.5em / 5em / 36% / 나머지 / 7.5em / 5em): 날 행 머리 `tr.rt-day`(th colspan, "10.13 화 run 8") + run 줄 `시각 / 자동·수동 / run / 결과 / 시간·비용 / 상태`. run 열 = kind 글자(제목색, run 1건 링크) + 흐린 글자 label 나머지(`from select`, `topic w41-…` 토픽 id는 본문색) + `.cur`. 하위 run(`sub`)은 `tr.tr-sub` 들여쓰기 + `└`. 결과 열: weekly 전체 `201 → 20 → 10 → 10 / 0 / 0`(clusters → candidates → selected → topics / code_rejects / check_topics, null은 `-`), topic 1개 `topics 1 / steps 7`, nightly `steps 7 / exit≠0 0`, ③ `collect ×7 / filter ×4 (ok 3, partial 1) / …`(링크 없음). publish 줄: `published_at`의 날 아래 `publish weeks.published_at / current <run id 뒤 4자> / published`(링크 없음). 날은 최근이 위, 같은 날은 시각 내림차순. 끝에 `.wk-nav` 이전·다음 주 링크(run_weeks 순서). 모바일(<1024): thead 숨김, tr을 grid 두 줄(FINAL 1장) |
| run 1건 | `/runs/<주>/<run id>/` | `.ph.rh`: 빵부스러기, h1 `weekly 2026-W41` / `nightly 10.12`, 메타 `10.10 토 23:42 / 수동 / ok`. 수치 레일 `.rails`: `summary`에서 `.rail-g`(제목 `.rail-t` + `.rail.seq`는 → 연결): weekly `cluster → select → write (순서대로 줄어듦)` = clusters → candidates → selected → topics → published, `review` = rounds("2 ×10"처럼 라운드별 수) / code_rejects / critic_rejects / check. nightly `collect → filter → summarize` = collected → filter_keep → cards, `plan이 고른 것` = deep_text / video / repo, `steps` = exit≠0. h2 `steps n` + `attention n`. `ol.steps > li.st`: 시각 `.st-t` + 본문(`.st-n` 단계 이름 15/500 + `.who`(code 회색 글자 / `code.ic` `llm / decide / qwen3.8-27b ×58`) + `.check`(attention) + 오른쪽 `.st-x` `시간 / 비용`) + `.st-l` 한 줄 + `.st-d` 상세(kv / list / table `.dtable.fixed` / 토픽 블록 `.tps > .tp`). 토픽 블록: 머리 `.tp-n` 순위 / `.tp-h` 제목 + `.tp-s` 토픽 id, `.tp-m` `rounds 2 / checked|passed / in 6.1k / out 1.1k / $0.009`, `.tp-chain`(→ 연결, 반려·확인 필요 항목은 밑줄), 반려 표(위치 / 종류 / 지적 / 수정). ③ steps 묶음은 페이지 없음 |

- 페이지 수: run_weeks 수 + runs 중 kind≠steps 수 + 1. 모든 내부 링크 유효(C-3 기존)
- `build.py`: `build_into`에서 `build_runs.render_all(C)`(또는 같은 뜻의 함수 1개) 호출, runs 함수 3개 삭제. `build_runs.py`는 `build.py`의 `page`·`esc`·`table`·`mdhm`·`SEP` 등을 import해 쓴다(순환 import 없이: build.py가 build_runs를 import하고 build_runs는 공용 헬퍼를 인자로 받거나 `from build import …`를 함수 안에서 — 구현 시점 선택, 12.1)
- CSS: FINAL 4장 조각(`.rt` 계열, `.state.ok`, `.cur`, `.crumb`, `.who`, `.rh`, `.rails`·`.rail-g`·`.rail-t`·`.rail.seq`, `.steps`·`.st-*`, `.dtable.fixed`, `.tps`·`.tp-*`, `.wk-nav`)을 `trendsit.css` 관리 화면 절에. 값은 토큰 변수만. `final.py`의 `FINAL_CSS`(125줄)를 출발점으로 쓰되 버린 안의 조각(`.v2~.v5`, `.r-from`, `col.c-from`)은 넣지 않는다

### 5.4 check.py·gate.js
- 정적(기존 유지) + 개정: A7 페이지 존재 → `runs/index.html`, `runs/<주>/index.html`(run_weeks마다), `runs/<주>/<run>/index.html`(kind≠steps마다), **`runs/weeks/` 없음**. 새 항목: 관리 화면 HTML에 `<details>` 0(C-9), 금칙 문자열 0(C-4: `Traceback`, `/Users/`, `data/`, `.py:`, `sk-`, `Bearer`, `localhost`), run 1건 글자 칸 300자 이하(table 셀·list 항목, C-5), `data/site.json`(또는 --data 파일) 크기 ≤ 3MB(C-6), 상태 글자가 `ok|partial|failed|running|stopped|published` 밖 0, "손"·"정상"·"건너뜀" 문자열 0(D-11)
- `pick_pages`: run 목록 1쪽(run이 가장 많은 주) + run 1건 weekly(`from cluster`) 1 + nightly 1 추가(픽스처에 둘 다 있어야 함). gate.js 측정은 기존 9항목 + 1280에서 `.rt` 셀 줄바꿈 0(각 `td`의 `scrollHeight ≤ 1줄 높이 × 1.5`) — 모바일은 넘침 0만(NG-5)

### 5.5 테스트·픽스처
- `tests/fixtures/site/site.json`·`tests/fixtures/s6_1/site_v2.json`: runs를 새 계약으로. 경계: 진행 주(status open, nightly 1, weekly 0) 1개 + 발행 주 1개, nightly auto·manual 각 1, weekly full(current)·partial·topic 각 1, ③ 묶음(partial 포함) 1, running 1, attention 있는 단계, 토픽 2개(하나는 checked·issues 있음), publish_at 있는 주
- `tests/test_export.py` A1 개정(run 선택·run_weeks 새 칸), `tests/test_s7a.py` 신규(5.1 rebuild·site-only·manual 규칙·하위 run 짝짓기·300자 자름·D-12 제외·③ 묶음, 5.3 화면 파싱), `tests/test_site.py`의 `f75`(옛 문구)·`f29`(옛 rail/kv) 교체, `tests/test_ops.py` nightly 끝 호출(실패 격리·summary.site·status 불변). `tests/test_s6_1_site.py`에서 runs 옛 문구를 쓰는 테스트가 있으면 교체
- `scripts/verify_s6-1.sh` A2의 "실행 1건 '이 주 발행 n개 / 이 실행이 쓴 토픽 m개'와 export counts.written" 항목 → "run 1건 머리 레일 `published`와 run_weeks current"로 문구·대상 교체(나머지 항목 불변)

### 5.6 불변식
| ID | 불변식 | 위반 시 |
|---|---|---|
| C-1 | `weeks`·`topics`·`repos`·`sources`·`keywords`는 published 주만(기존); `runs[].week` ⊆ `run_weeks[].week`; `run_weeks`의 주 = published 주 ∪ run이 있는 비발행 주 | export 테스트 실패 |
| C-2 | `runs[].kind ∈ {nightly, weekly, steps}`; nightly는 `summary_json.steps ≠ []`인 것만; weekly는 `week IS NOT NULL`인 것 전부; kind가 role·eval·proto·image-check·rematch·ops-weekly인 run 0 | export 테스트 실패 |
| C-3 | 생성 HTML: `runs/<주>/<id>/index.html` 수 = `len([r for r in runs if r.kind != "steps"])`, `runs/weeks/index.html` 없음, 모든 내부 링크 유효 | check 실패 |
| C-4 | 생성 HTML 전체에 금칙 문자열(5.4 목록) 0, `<script>`·`<details>` 0, 외부 요청 0 | check 실패 |
| C-5 | `steps[].detail` 글자 칸(table 셀·list 항목·kv 값) 길이 ≤ 300 | export 테스트·check 실패 |
| C-6 | `data/site.json` ≤ 3MB(발행 주 2 + 진행 주 1, weekly run 85 기준 실측 뒤 리포트에 적음) | check 실패 |
| C-7 | `rebuild_site` 전후 `weeks` 표 바이트 동일(status·published_at·current_run_id 불변), DB 쓰기는 그 nightly 행 `summary_json.site` 1곳뿐 | ops 테스트 실패 |
| C-8 | `rebuild_site`가 실패(예외·exit≠0·timeout)해도 nightly `runs.status`·종료 코드·`summary_json.steps` 불변, `site/`·`data/site.json` 불변(기존 원자 교체) | ops 테스트 실패 |
| C-9 | `mode == "auto"` ⇔ (nightly ∧ `manual` ∉ summary_json) ∨ (weekly ∧ spec LIKE 'RUN-%') | export 테스트 실패 |
| C-10 | 같은 site.json → 같은 HTML(빌드 결정성, 기존 C-8). 시각·정렬은 데이터에서만 | 테스트 실패 |
| C-11 | `build.py` ≤ 700, `build_runs.py` ≤ 500, `export_runs.py` ≤ 450, 함수 ≤ 60줄 | verify 실패 |

### 5.7 실패 동작
| 상황 | 동작 | 종료/상태 |
|---|---|---|
| nightly 끝 export 예외 / build exit≠0 / timeout | stderr 한 줄, `summary_json.site.exit`에 1·코드·124, 사이트·site.json 불변 | nightly 종료 코드·status 불변(C-8) |
| `publish --site-only` export·build 실패 | 기존 publish와 같은 메시지 형식(`사이트 재생성 실패: <원인 한 줄>`) | 1 |
| `publish --site-only --week W` | 인자 오류 메시지 | 2 |
| export: published 주 0개 | 기존 ExportError(진행 주만으로는 사이트를 안 만든다 — 토픽이 0이라 홈이 없음) | 1 |
| export: 하위 run·plans·cluster_pairs 등 원천 행 없음 | 그 단계는 line만, detail `[]`(예외 아님) | 계속 |
| export: 글자 칸 > 300자 | 자름(`…` 없이 300자) | 계속 |
| export: `items.title` 등 참조 행 없음 | id 글자 그대로(`it:1041`) — M-2(근거 id 노출) 검사와 충돌하므로 **`item <n>`** 형식으로 | 계속 |
| build: `runs[]`에 kind steps인데 steps 비어 있지 않음 등 계약 위반 | BuildError, `site/` 불변 | 1 |
| check: 항목 실패 | 실패 목록 출력 | 1 |
- 에러 메시지 형식: `<명령>: <원인 한 줄>`(stderr). 부분 실패 정책: 단계·run 단위 격리(한 run의 원천이 비어도 다른 run·쪽은 만든다). 타임아웃·재시도: rebuild는 `step_timeout_min` 1회, 재시도 없음

## 6. 관문 A (`scripts/verify_s7a.sh`)

| ID | 검증 내용 | 판정 방법 | PASS 기준 | 수단 | 관련 | 단계 |
|---|---|---|---|---|---|---|
| A1 | nightly 끝 사이트 재생성·site-only | 임시 DB + 가짜 runner(test_ops 방식): 정상(site.json 교체, weeks 바이트 동일, summary.site exit 0), export 예외·build 실패·timeout(site 불변, nightly status·종료 코드 불변), 건너뛴 nightly는 안 부름, `publish --site-only`(0 / 실패 1 / `--week` 동시 2), 기존 `publish --week` 불변 | 전부 통과 | 스크립트 | 5.1, C-7·C-8 | S-1 |
| A2 | run 선택·분류 | 임시 DB(nightly auto·manual·steps 빈 것, weekly full·partial·topic·week NULL·running, 수동 단계별 run 2날, role·eval run, 진행 주) → `runs`·`run_weeks` | C-1·C-2·C-9, label·sub·topic_id·current·week 귀속·③ 묶음·status·cost가 5.2대로, 옛 칸 0 | 스크립트 | 5.2-1·2·4 | S-1 |
| A3 | run 1건 상세 칸 | 임시 DB에 weekly 6단계·nightly 8단계 원천 행(cluster_pairs 3, briefing_plans decisions 3, 토픽 2 + steps 라운드, aliases, fetch_log, items, plans, item_cards v2, video_digests, repo_cards, summary.site) → `steps[]` | 5.2-3 표의 단계마다 name·who·line·detail 블록이 있고 원천 행 수와 같음(전부), 300자 자름, 원천 없는 단계는 line만, 하위 run 짝짓기(날 2개), 참조 없음 `item <n>` | 스크립트 | 5.2-3, C-5 | S-1 |
| A4 | 주차별 표·주 목록 | 픽스처 빌드 → HTML 파싱 | `/runs/` 5열·행 수 = run_weeks·링크, `/runs/<주>/` 날 행 머리 수 = 날 수, run 줄 수 = runs(그 주) + publish 1, `tr.tr-sub` = sub run 수, `.cur` 1, 결과 열 3종 형식, ③ 줄 링크 없음, 이전·다음 주 링크, `/runs/weeks/` 없음 | 스크립트 | 5.3 | S-2 |
| A5 | run 1건 | 픽스처 빌드 → HTML 파싱 | weekly·nightly 각: 빵부스러기 2링크, 레일 묶음 수(weekly 2·nightly 3)와 값, `li.st` 수 = steps 수, who 글자(`code` / `code.ic` 안 `llm / decide / … ×58`), `.check` 수 = attention 수, 토픽 블록 수 = topics 수·체인·반려 표, `<details>` 0 | 스크립트 | 5.3, C-3 | S-2 |
| A6 | 공개 금칙·크기 | `check.py --fixture` 새 항목 + 실DB export(읽기, `--out` 임시) 크기 | 금칙 0, `details` 0, 300자, 상태 어휘, "손·정상·건너뜀" 0, site.json ≤ 3MB | 스크립트 | C-4·C-5·C-6 | S-2 |
| A7 | 관문 9 + 셀 줄바꿈 | `check.py --fixture`(gate.js Chromium·WebKit 375/768/1280, 대상에 run 목록·weekly·nightly) | 9항목 전부, 1280에서 `.rt` 셀 줄바꿈 0, 375 가로 넘침 0 | 스크립트 | 5.4 | S-2 |
| A8 | 회귀 | `verify_s6a.sh`, `verify_s6b.sh`, pytest 전체(건너뜀 0), `verify_s6-1.sh`(개정 A2 포함)는 S-3 끝 1회 | 종료 코드 0(verify_s6-1은 91 A11 예외 B5·A23 그대로) | 스크립트 | 5.5 | S-3 |
| A9 | 복잡도·구조 | 줄 수·함수 길이(verify_s5 B4 방식)·grep | C-11, `build.py`에 `render_run` 식별자 0, `trendsit.css`에 `.v2`·`.c-from` 0, 새 환경 변수 0(`os.environ` 추가 없음), `<details>` 0 | 스크립트 | 3.4 | S-3 |
| A10 | 실측 QA(0원) | qa-verifier: 실DB를 **읽기 전용**으로 `trendsit export --out <임시>` → 임시 폴더 빌드 → WebKit 375·Chromium 1280 캡처 `reports/S7a/shots/`(`/runs/`, `/runs/2026-w41/`, weekly from cluster 1건, 오늘 nightly 1건). 적대적: 토픽 1개 재실행 run 페이지(상세가 토픽 1개), running run 줄, ③ 묶음 줄, 진행 주 페이지(weekly 0) | 캡처가 6.1 기준선(FINAL 캡처)과 구조 일치: 쪽 3종·열·들여쓰기·레일·단계·토픽 블록, 접힘 0, 1280 셀 줄바꿈 0, 375 넘침 0 | QA | 5.3 | S-3 |
| A11 | 문서 | 파일 검사 | README "실행 기록" 한 단락(쪽 3종·nightly 끝 재생성·`publish --site-only`), `CLAUDE.md` 진행 블록, `AGENTS.md` 출력 형식 줄(5.2 참조), `reports/S7a_report.md` 8장까지(C-6 실측 크기 포함), `reports/S7a/shots/` ≥ 4장 | 스크립트 | — | S-3 |

### 6.1 기준선 예시 (A10)
| AC | PASS 예시 | FAIL 예시(경계 근처) | 무엇이 갈랐나 |
|---|---|---|---|
| A10 주차별 표 | `claude/s7a_시안/final/shots/weeks_1280.png` | `claude/s7a_시안/out/shots/목록_02_1280.png`(세 주를 한 쪽에 쌓고 열 9개) | 쪽 분리와 5열 |
| A10 주 목록 | `final/shots/목록_1280.png`(날 행 머리, `└` 하위 run, publish 줄, 범례) | `out/shots/목록_01_1280.png`(카드 줄, "손" 배지, `펼치기` 접힘, 건너뜀 줄) / `out/shots/목록_11_1280.png`(가깝지만 하위 run 구분 없음·"손") | 표 하나·시스템 이름·하위 구분·접힘 0 |
| A10 run 1건 weekly | `final/shots/weekly_1280.png`(레일 2묶음, 단계 6, 토픽 10 블록 펼침) | `out/shots/주간_01_1280.png`(details 접힘, 배지 3종) / `out/shots/주간_11_1280.png`(펼쳐졌지만 배지·"끝" 서술) | 접힘 0·누가 글자·레일 |
| A10 run 1건 nightly | `final/shots/nightly_1280.png`(레일 3묶음, 단계 8, export + build 단계) | `out/shots/매일_03_375.png`(표형이라 모바일 가로 스크롤) | 표 아닌 단계 목록 |
| A10 모바일 | `final/shots/목록_375.png`(두 줄 접기, 넘침 0) | `out/shots/매일_01_375.png` 첫 캡처(배지 21px 넘침) | 넘침 0만 본다 |

## 7. 관문 B와 QA, 런 뒤 할 일
- **관문 B 없음**(LLM 호출 0). QA는 A10만(0원, 실DB 읽기)
- **런 뒤(구현 세션)**: ① `verify_s6-1.sh` 1회(A8) ② `reports/S7a_report.md` 8장(C-6 실측 크기, 변경 파일 수, 결정한 것) ③ README·CLAUDE.md ④ 손으로 고친 것이 있으면 `code-reviewer` 1회 ⑤ 커밋·푸시·PR → `handoff/NNN_impl→review.md`
- **병합 뒤(리뷰 세션, 10/16 목표)**: 실행 폴더 `git -C ~/Claude/projects/trendsit-run fetch && … reset --hard origin/main` → **`uv run python -m trendsit publish --site-only`**(실행 폴더, $0, 상태 불변) → `python3 site_src/check.py`(실사이트) → trendsit.jiseop.com/runs/ 확인(10/13 02:00 nightly가 보이는지). 다음 날 02:00 nightly 뒤 `/runs/`에 어젯밤 줄이 생기는지, `summary_json.site.exit` 0 확인. 19·63·64 갱신은 기획 세션
- **10/19(월) 07:00**: W42 자동 발행 뒤 `/runs/2026-w42/`에 weekly from cluster(auto) 1줄 + publish 줄

## 8. 단계 (커밋 단위)

| ID | 단계 | 포함 | 완료 AC | 선행 | 산출물 |
|---|---|---|---|---|---|
| S-1 | ops + export | 5.1, 5.2(export_runs.py), 픽스처 2개 새 계약, test_export A1 개정, test_ops, test_s7a(export 부분), verify_s7a.sh 뼈대 | A1, A2, A3 | — | ops.py·cli_ops.py·export.py·export_runs.py·fixtures·tests |
| S-2 | build + check | 5.3(build_runs.py, CSS), 5.4(check·gate), test_site f75·f29 교체, test_s7a(화면), test_s6_1_site 옛 문구 | A4~A7 | S-1 | build.py·build_runs.py·trendsit.css·check.py·gate.js·tests |
| S-3 | 회귀·QA·문서 | verify_s6-1 A2 개정, 줄 수·grep 검사, A10 캡처, README·CLAUDE.md·AGENTS.md·리포트 | A8~A11 | S-2 | verify_s6-1.sh·verify_s7a.sh·reports/S7a·README |

## 9. 넘길 것과 미확정
- 미해결 `Q-*`: **0건**
- 구현 시점 기본값(12.1, 리포트 "결정한 것"에 적는다): `build_runs.py`가 `build.py` 헬퍼를 쓰는 방식(함수 인자 전달 또는 모듈 import), 토픽 블록 체인 글자의 정확한 문구(`writer 근거 id 16 / 절 5` 등은 steps text 그대로), 반려 표 "수정" 열에 writer_revise 대응 항목이 없을 때 `-`, `item_cards v2`·`repo_cards` card_json에서 한 줄로 쓸 칸 이름(실측해 `log`·`summary`·첫 글자 칸 순), 시각 열이 없는 steps 행(nightly summary.steps)의 `t`는 하위 run 시작 시각, 날짜가 여러 날인 nightly label(`10.10~10.11`), site.json 크기 상한 3MB를 실측이 넘기면 멈추고 보고(C-6), 모바일 두 줄 grid의 열 순서(FINAL 1장 그대로)
- 기획 세션 몫(병합 뒤): 19·63 3.3·64 C-35 갱신, `docs/CONTEXT.md`·COMMON 8장 스펙 표, S7b 기획(소스·키워드, 같은 표현 원칙 D-10·D-11)
- 사용자 몫: 원격 브랜치 정리, 10/16 실서버 확인, 10/19 아침 확인
- 위험: 10/19 첫 자동 weekly 뒤 publish가 `published_at`을 덮어 10/13 재발행 시각이 사라진다(D-19 수용). S6-1 병합이 10/15를 넘기면 S7a 브랜치가 늦어진다 → 명세는 그대로, 기준 커밋만 바뀜. `verify_s6-1.sh` A2 개정으로 S6-1 게이트 문구가 바뀌므로 리뷰 세션은 "개정 항목"을 알고 본다

## 13. 실측 반영 이력
| 날짜 | 런 | 발견 | 근거 | 변경한 § |
|---|---|---|---|---|
