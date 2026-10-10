# S5-1a 고침·정리: 동작 버그, 효과 없는 설정, 죽은 코드

> 기획 세션 작성 2026-10-10(spec-planner, 원장 `.workflow/planning/s5-1/ledger.md`). 기준 커밋 **main `a259b99`**(S5 병합).
> S5-1(단계 R)을 런 2개로 나눈 것의 첫째. 둘째는 `docs/handoff/S5-1b_TASK.md`(규칙 정리·중복 제거·md 정리). **이 스펙이 병합된 뒤 S5-1b를 시작한다.**
> 공통 규칙은 `docs/handoff/COMMON.md`(특히 12장), 이 문서가 우선한다. 구현 세션은 `/impl-workflow docs/handoff/S5-1a_TASK.md .`로 돌린다.

## 0. 이 스펙이 끝나면 되는 것

| 항목 | 값 |
|---|---|
| slug | `s5-1a` |
| 버전 / 작성일 | v1 / 2026-10-10 |
| 문서 상태 | **확정(투입 가능)** |
| 미해결 `Q-*` | 0건 |
| 선행 런 | 없음(S5는 워크플로우 밖에서 구현) |
| 브랜치 | `s5-1a-fix`, 첫 커밋 = 이 문서 + 저장소 `CLAUDE.md` 진행 상태 블록(미커밋분) |

**한 줄 목표**: 프롬프트와 코드 검사 결과는 한 바이트도 바꾸지 않고, 리뷰가 실행으로 재현한 동작 버그를 고치고, 효과 없는 설정 키·호출되지 않는 코드·방어 코드를 지운다.

- 사용자 체감 결과: 주간 실행이 예산 상한에 걸리면 **멈추고 종료 코드 1**, 직전 현재판은 그대로. 글 분석가가 github 대문자·http·arxiv pdf 문서의 다음 조각을 읽음. 설정 키를 바꾸면 동작이 바뀜(효과 없는 키는 없음)
- 프롬프트가 그대로이므로 관문 B·캐시에 영향 없음. LLM 호출 0회

## 1. 맥락

- S5 리뷰를 네 번 돌면서 사례별 규칙과 예외 덧대기가 쌓였다(기획 문서 84). S6 전에 구조를 단순화하고, **S5 MVP를 문제없이 정리**하는 것이 S5-1의 목적이다
- 재료: 전체 코드 콜드 리뷰 35건(code-reviewer, 2026-10-10)과 규칙 발동 실측(근거 A). 이 스펙에는 그중 **프롬프트를 바꾸지 않는 것**만 담았다. 나머지(규칙 정리, 중복 합치기, md 정리)는 S5-1b
- 결정(원장 D-n, 64 부록 C와 별개 번호. 64에는 기획 세션이 C-26으로 묶어 기록)

| ID | 결정 | 근거 |
|---|---|---|
| D-9 | 목표는 구조 단순화 + S5 MVP를 문제없이 정리. 사실이 틀린 정보는 불허, 덜 좋은 표현 정도의 트레이드오프는 허용(S5-1b에 해당) | 사용자 2026-10-10 |
| D-12 | 리뷰가 찾은 실제 문제(정확성·명세위반)는 이번에 모두 해결. 품질 개선(S5 남은 ⚠ 토픽)은 MVP 뒤 | 사용자 |
| D-13 | 지운 코드와 짝인 설정 키는 이 PR에서 `config/*.yaml`까지 함께 지운다(COMMON 9장 "설정은 기획 세션 소유"의 **이 PR 한정 예외**) | 사용자. 스키마가 `extra="forbid"`라 따로 지울 수 없음 |
| D-20 | 예산 초과 동작은 기존 관례를 따른다: `ctx.stopped` 설정 → 남은 작업 중단 → run `stopped` → 종료 코드 1 | `cli.py:76-80, 162`, `core/context.py:28`(근거 A) |
| D-21 | decide 중 예산 초과: 이미 받은 판정은 유지·저장, 남은 쌍은 판정 없음(묶지 않음) | D-20과 같은 관례 |
| D-22 | 같은 상한이 두 설정에 있으면 실행 쪽(`video.yaml`)이 정본 | 실제로 자르는 값이 실행 쪽 |
| D-23 | github·web 도구의 fetcher는 리소스 키를 나눈다(github = 캐시 없음, web = HTTP 캐시, 지금 의도 그대로) | `tools/github.py:29-42`, `tools/web.py:21-34` |

## 2. 준비물 (환경 전제·검증 명령·유료 상한)

| 항목 | 값 |
|---|---|
| 작업 디렉터리 | `~/Claude/projects/trendsit`(맥), main `a259b99`에서 브랜치 |
| 런타임 | `uv`, Python은 `pyproject.toml` 그대로, `--extra video --extra embed`(pytest 건너뜀 0 조건) |
| 데이터 | `data/trendsit.db`(W40·W41 현재판 run `20261010-144517-weekly-67f5`, `20261010-124834-weekly-75b1`). **읽기만** |
| 비밀 | `~/.config/trendsit/.env`(이름만: `OPENROUTER_API_KEY`, `GITHUB_TOKEN`). 이 스펙은 쓰지 않음 |
| **검증 명령(게이트)** | `.workflow/gate.sh` = `bash scripts/verify_s5.sh --fast`. `--fast`는 A1(s0~s4 회귀 재실행)만 건너뛰고 A2~ 전부 실행(A2가 전체 pytest라 s0~s4 테스트는 포함됨). 실패 시 종료 코드 ≠ 0. 이 스펙의 AC는 같은 스크립트에 `A15~` 행으로 추가 |
| 전체 검증 | `bash scripts/verify_s5.sh`(옵션 없음, A1 포함)를 **런 뒤 1회** + PR 전. 전체 PASS가 병합 조건 |
| 게이트 시간 | `--fast` 15분 이내(훅 타임아웃 900초). 전체는 지금 36분(13장) → 시간 상한 없음, 결과로만 기록 |
| **유료 호출 상한** | **$0**. LLM·임베딩 API 호출 없음. 실데이터 재실행 없음 |

## 3. 범위

### 3.1 한다(리뷰 번호 F-n은 `.workflow/planning/s5-1/review-0.md`. 필요한 내용은 5장에 옮겨 둠)
- 고침: F-1 예산 초과 멈춤, F-2 `read_more` 조회 열쇠, F-4 `retention_days`, F-7 decide 중 예산 초과, F-8 중복 상한, F-17 선별 대체 이유, F-20(fetcher 공유만), F-24 검수자 근거 창, F-27 실행 요약 상태, F-32 verify A3 문구, F-33 제목 없는 근거
- 지움: F-5·F-29 효과 없는 설정 키, F-9 호출 안 되는 `fallback()` 7개, F-10 `collect/video/settings.py`, F-18 안 쓰는 매개변수·반환값·함수, F-19 일어날 수 없는 방어 코드, F-25 한 번 쓰는 얇은 헬퍼, F-31 설정값을 복사한 함수 기본값, F-23 verify 헬퍼 복사·회귀 중첩 실행
- 측정 도구: 골든 회귀 스크립트, 프롬프트 스냅숏 스크립트(5.1). S5-1b도 이 둘을 쓴다

### 3.2 비목표
| # | 하지 않는 것 | 이유 |
|---|---|---|
| NG-1 | `brief/checks.py`의 규칙 추가·삭제·변경 | S5-1b. 이 스펙에서 골든 회귀는 "완전 동일"이어야 한다 |
| NG-2 | `roles/*.md`, `skills/*.md`, `eval/judge*.md` 변경, 출력 스키마 칸 추가·삭제·순서 변경 | 프롬프트 불변(C-2). md 정리는 S5-1b, 칸 순서(F-16)는 MVP 뒤 |
| NG-3 | 같은 일을 하는 코드 합치기(F-11, F-20의 fetcher 외 항목, F-21, F-22), 테스트 정리(F-28), 함수 쪼개기, 500줄 파일 분할 | S5-1b |
| NG-4 | 새 기능, 새 CLI 명령·옵션, 새 설정 키 | 단순화 스펙 |
| NG-5 | 실행 시간 단축 목표 | 결과로만 잰다(목표로 두면 최적화 코드가 들어옴) |
| NG-6 | Whisper 모델 id 설정 이동(F-30), 출력 스키마 칸 순서(F-16) | MVP 뒤 |
| NG-7 | S6 범위(export, 사이트, launchd), 관문 B 실행 | S6 / 프롬프트 불변이라 불필요 |

### 3.3 건드리지 않을 것
- 파일: `roles/`, `skills/`, `eval/`(픽스처·채점기·채점표·라벨·judge md), `data/`, `docs/handoff/CONTRACTS.md`, `trendsit/core/migrations.py`(번호·내용), `config/budget.yaml`, `config/models.yaml`, `config/keywords.yaml`, `reports/eval/`, `reports/S5_brief/`
- 영역: 역할 호출 메시지와 출력 스키마(C-2), 코드 검사 결과(C-3), CLI 명령·옵션 이름과 `--help` 출력(C-4), DB 스키마

### 3.4 복잡도 예산
| 항목 | 값 |
|---|---|
| 변경 파일 수 | ≤ 60(삭제 포함, 테스트·verify 스크립트 포함) |
| 새 파일 | ≤ 4: `scripts/s5_1_golden.py`, `scripts/s5_1_prompts.py`, `scripts/verify_common.sh`(F-23 공용 헬퍼), `reports/S5-1a_report.md`. 스냅숏 파일(`reports/S5-1/*.json`)은 세지 않음 |
| 지우는 파일 | `trendsit/collect/video/settings.py` |
| 순 줄 수 | `trendsit/` 순 감소(음수). 고침으로 늘어나는 줄 포함 |
| 새 의존성 | 금지 |
| 금지 구조 | 새 추상 계층·레지스트리·설정 옵션·환경변수, 새 예외 클래스(기존 `BudgetExceeded`·`PriceUnknown`·`LLMError`만), 일어날 수 없는 상황의 방어 코드 |
| 품질 수준 | 프로덕션 |

구현이 예산을 넘길 것 같으면 멈추고 보고한다. "제대로 하려면 새 모듈이 필요하다"는 멈춤 신호다.

## 4. 폴더

```
scripts/s5_1_golden.py          (새) 골든 회귀: 저장된 판에 check·autofix·warnings → JSON
scripts/s5_1_prompts.py         (새) 프롬프트 스냅숏: 역할별 initial_messages·출력 스키마 → JSON(sha256)
scripts/verify_common.sh        (새) pass/fail/pt 공용 헬퍼(F-23)
scripts/verify_s0~s5.sh         (수정) 헬퍼 source, verify_s5는 s0~s4를 한 번씩만(F-23), A15~ 추가
reports/S5-1/golden_before.json, prompts_before.json, help_before.txt   (새, 첫 코드 커밋)
reports/S5-1a_report.md         (새)
trendsit/brief/{write,pipeline,weekly,select,briefing,cluster,aliases}.py, trendsit/cli*.py,
trendsit/core/{artifacts,artifacts_brief,artifacts_text,artifacts_video,config,config_brief,config_video}.py,
trendsit/deep/plan.py, trendsit/tools/{web,github}.py, trendsit/collect/video/{settings(삭제),ff,workspace}.py,
trendsit/summarize.py, config/{brief,deep,sources,link_kinds}.yaml, tests/
```

## 5. 상세

### 5.1 측정 도구(S-1, 다른 변경보다 먼저)

**골든 회귀 `scripts/s5_1_golden.py`**
- 입력: `--out <path>`, `--db <path>`(기본 `data/trendsit.db`, **읽기 전용 연결** `mode=ro`)
- 대상: W40·W41 현재판 run(`weeks.current_run_id`)의 모든 토픽 × `topic_pages`의 모든 라운드
- 근거 pack 재구성: `week_evidence(db, week)` → 토픽 `cluster_ids_json`의 `cluster_items.member`(rowid 순, 중복 제거) → `cap_pack(members, cfg.evidence.max_tokens_per_topic)` → `pack_index`. `n_sources` = pack의 구성원 수. canon·translit은 `write_topic`과 같은 방식으로
- 각 판에 대해 `checks.autofix(raw 판 또는 저장 판)`, `checks.check`, `checks.warnings(…, angle=topics.angle)` 결과를 기록
- 출력 스키마(정렬된 키, `ensure_ascii=False`, 들여쓰기 1):
```json
{"runs": {"2026-W40": "20261010-144517-weekly-67f5", "2026-W41": "20261010-124834-weekly-75b1"},
 "pages": [{"topic_id": "w40-gpt-6-1-sol", "round": 1,
            "issues": [{"loc": "points[4]", "type": "number_mismatch", "comment": "points[4]의 '2'가 it:8#q5에 없음. 근거의 가까운 값은 0.1, 6, 6.1"}],
            "autofix": [{"loc": "concepts", "rule": "…"}],
            "warnings": ["누락 의심: …"]}]}
```
- 정상 예: 위. 이상 예: DB에 해당 run이 없으면 `stderr`에 `run 없음: 2026-W40`, 종료 코드 2
- 기준 실측(기획 세션 2026-10-10, 같은 방법): 20토픽, 현재 코드 반려 이슈 합계 약 40건(라운드 합), 경고 약 21건. 이 스펙의 기대값은 숫자가 아니라 **전후 동일**

**프롬프트 스냅숏 `scripts/s5_1_prompts.py`**
- 역할: `roles/*.md` 전부 + `eval/judge*.md`
- 역할마다: `load_role` 후 system 문자열, `role.output_cls.model_json_schema()`(정렬 직렬화), 그리고 `eval/fixtures/<역할>/` 픽스처 입력 각각의 `initial_messages(role, inp)`. 픽스처가 없는 역할은 system·스키마만
- 출력: `{역할: {"system": sha256, "schema": sha256, "fixtures": {파일명: sha256}}}`. 차이가 나면 `--diff <before>`로 첫 차이 위치를 출력
- 이상 예: 픽스처 입력이 역할 입력 스키마에 맞지 않으면 그 파일만 `"invalid"`로 기록하고 계속(전후 동일 비교 대상)

**스냅숏 만들기(첫 코드 커밋)**
- "전" 스냅숏은 **main `a259b99` 코드로** 만든다: `git worktree add /tmp/s5-1-base a259b99` → 그 폴더에서 두 스크립트(새 파일이라 복사해서)와 각 CLI `--help`를 실행 → `reports/S5-1/golden_before.json`, `prompts_before.json`, `help_before.txt` → worktree 제거. 커밋 메시지에 기준 커밋 해시
- `--help` 대상: `uv run python -m trendsit --help`와 모든 하위 명령(하위 파서 목록을 코드에서 읽어 순회)

### 5.2 F-1 · 작성·검수 중 예산 초과
- 현재: `brief/write.py:288-296 _call`이 `(RoleFailed, LLMError)`만 잡음 → `BudgetExceeded`·`PriceUnknown`이 `pipeline.py:117-120`의 `except Exception`에서 토픽 failed로 바뀌고 다음 토픽 진행 → 끝에서 `weeks.current_run_id`를 이 run으로 갱신, `cmd_weekly` 종료 코드 0(리뷰어 실행 재현)
- 고친 뒤 계약:
  - `BudgetExceeded`·`PriceUnknown`이 작성·검수·수정 중 나면 `ctx.stopped = "<예외 이름>: <메시지>"`, 그 토픽은 `failed`(attention에 이유), **남은 토픽은 시작하지 않음**
  - run: `runs.status = "stopped"`, 실행 요약 `status = "stopped"`
  - `weeks.status`·`weeks.current_run_id`는 **바꾸지 않는다**(직전 현재판 유지)
  - `cmd_weekly` 종료 코드 1, stderr에 `ctx.stopped`
  - 묶기·선별 단계의 예산 초과도 같은 규칙(현재판 미갱신, 종료 코드 1)
- 예시(정상): 예산 안 → 지금과 같음(`status` done/written, 종료 코드 0). 예시(이상): 토픽 2번째 작성 중 `BudgetExceeded` → 토픽 1 passed, 토픽 2 failed, 토픽 3~ 없음, run `stopped`, `weeks.current_run_id` 그대로, 종료 코드 1

### 5.3 F-27 · 실행 요약 상태
- 현재 `pipeline.py:241-243`은 토픽이 있고 전부 실패해도 `partial`. `pipeline.py:135-140`의 `weeks.status` 계산과 어휘가 두 벌
- 고친 뒤: 실행 요약 `status` ∈ {`done`, `partial`, `failed`, `stopped`}. 전부 실패면 `failed`, 일부 실패면 `partial`, 예산 중단이면 `stopped`. `weeks.status` 계산과 같은 판정 함수 하나를 쓴다(두 계산 중 하나를 지우고 다른 쪽이 그 결과를 씀)

### 5.4 F-7 · 묶기 decide 중 예산 초과
- 현재 `brief/weekly.py:94-97`: `decide_aliases` 도중 초과 시 `alias_dec=[]`로 덮지만 이미 바뀐 `r.status`는 저장됨. `:112-116`: `cluster_week` 도중 초과 시 `decider=None`으로 처음부터 다시 돌려 이미 받은 판정이 사라짐
- 고친 뒤: 이미 받은 decide 판정은 결과·기록 모두 유지. 초과 시점 이후 쌍은 판정하지 않음(decide 미달 쌍과 같이 묶지 않음). `ctx.stopped` 설정 → 5.2 규칙으로 run 중단. `cluster_week` 재실행 경로(`decider=None` 재시도)는 지운다

### 5.5 F-2 · `read_more` 조회 열쇠
- `tools/web.py:135`의 `norm_url(args.doc)`를 저장과 같은 `page_key(args.doc)`로
- 예시: `fetch_page("https://github.com/Foo/Bar")` 후 `read_more(doc="https://github.com/Foo/Bar", part=2)` → 거부되지 않음. `http://example.com/a`, `https://arxiv.org/pdf/2401.01234v2`도 같음

### 5.6 F-20(일부) · fetcher 공유 키
- `tools/github.py resources`는 `res["github_fetcher"]`(캐시 없음), `tools/web.py resources`는 `res["fetcher"]`(HTTP 캐시). 호출 순서와 무관하게 각 도구가 자기 fetcher를 씀

### 5.7 설정 키(F-4, F-5, F-8, F-24, F-29, F-31)
| 키 | 처리 |
|---|---|
| `brief.yaml aliases.auto_approve`, `cluster.linkage`, `write.diagrams.per_point_max`, `runtime`(블록 전체) | 스키마(`core/config_brief.py`)와 yaml에서 삭제. 주석으로 남기지 않음 |
| `sources.yaml text[].lang`, `video[].lang`, `video[].channel_handle`, `github.tracked[].why`, `link_kinds.yaml kinds.*.paths` | 스키마에서 삭제. yaml 값은 **주석으로 옮김**(사람이 읽는 메모) |
| `video.yaml retention_days`(F-4) | 유지. `cli_video.py`의 `--older-than` 기본값을 이 키에서 읽음(하드코드 7 삭제). `--help` 문구가 바뀌면 안 됨(C-4) |
| `deep.yaml video_max_minutes`, `frames_per_slide_video`(F-8) | 설정 키 삭제(`core/config.py` 스키마 259·267행 + yaml). `deep/plan.py`는 `video.yaml max_span_sec // 60`·`frames_cap`을 읽음. **편집장 계획 입력(`core/artifacts_text.py:308, 315`)의 칸 이름·값은 그대로**(값 출처만 video.yaml, 60·20으로 같음 → C-2 유지). `config_video.py FRAME_CAP_MAX`(검증 상한 20)는 그대로 |
| 검수자 근거 "앞뒤 30초"(F-24, `brief/write.py:145, 152-155`) | `video.yaml align_window_sec`를 읽음 |
| 함수 기본값이 설정을 복사(F-31): `aliases.build(fuzz_min=90)`, `weekly.decide_aliases(limit=10)`, `select.recent_topics(weeks_back=4)` | 기본값 삭제(필수 인자). 호출처는 이미 설정값을 넘김 |

### 5.8 죽은 코드·방어 코드(F-9, F-10, F-18, F-19, F-25)
- F-9: `fallback()` 삭제 — `core/artifacts_brief.py` BriefingPlan·TopicPage·TopicPageRevision·ReviewVerdict·FactCheck, `core/artifacts_video.py` SlideReading, `core/artifacts_text.py` CollectionPlan. 출력 스키마는 바뀌지 않아야 함(C-2)
- F-10: `collect/video/settings.py` 삭제, 호출처(`cli_video`, scripts 3개, tests)는 `config.load("video.yaml")`와 `config.check_all()`
- F-18: `cluster.score(trend=)`(docstring의 "키워드 추세"도), `cluster.save(truncated=)`, `briefing.sources_index` 두 번째 반환값, `aliases.as_dicts`, `collect/video/ff.have_tools`
- F-19: `write.py:360 hasattr(page,"raw_dump")`, `write.py:415-421 except ValueError`(apply_revision이 이미 처리), `briefing.py:74 "checks_json" in t.keys()`, `cli._register`·`core/artifacts._merge`의 `ModuleNotFoundError` 무시, `pipeline.py:132`의 중복 `src` 조건, `summarize.py:79 hasattr(card,"model_dump")`, `tools/web.py:115` 깊이 재계산, `cli_brief.py:49-50` step 재계산, 낡은 docstring(`cli_brief.py:1`, `weekly.py:1`)
- F-25: `select.week_num`, `evidence.item_tokens`, `pipeline._summary_src`, `agent.nullable_fields`, `write.ref_channel`, `agent._args_summary`를 호출처에 인라인. `cli_text.score_band`·`device_flips`는 `cmd_filter_fixtures` 안으로

### 5.9 그 밖의 고침(F-17, F-32, F-33)
- F-17 `select.py:374-390`: 대체 계획 이유는 **마지막 시도**가 예외면 `"호출 실패"`, 검증 실패면 `"검증 실패"`
- F-32 `verify_s5.sh` A3: 역할 md 5개(decide, editor_select, writer, writer_revise, critic) 파일 존재를 실제로 확인(`[ -f roles/$r.md ]`)
- F-33 `briefing.py:126`: 제목이 None인 근거는 `'?'`

### 5.10 verify 스크립트(F-23)
- `scripts/verify_common.sh`에 `pass/fail/pt` 한 벌. `verify_s1~s5.sh`는 source
- `verify_s5.sh` 한 번에 s0~s4가 **각각 한 번만** 실행됨(지금은 s2·s3·s4가 s0·s1을 다시 불러 전체 pytest가 약 16회). 방법은 구현 시점 기본값(verify 스크립트 안에서만, 제품 코드·CLI에 옵션 추가 금지). 각 verify를 단독으로 돌렸을 때의 판정은 지금과 같아야 함
- 판정 결과(PASS/FAIL 항목과 개수)는 전후 같아야 함. 줄어드는 것은 중복 실행 시간뿐

### 5.11 불변식
| ID | 불변식 | 판정 |
|---|---|---|
| C-1 | `bash scripts/verify_s5.sh` 종료 코드 0, pytest 건너뜀 0 | 게이트 |
| C-2 | `scripts/s5_1_prompts.py` 출력 == `reports/S5-1/prompts_before.json`(모든 역할의 system·schema·픽스처 메시지 sha256 동일) | A15 |
| C-3 | `scripts/s5_1_golden.py` 출력 == `reports/S5-1/golden_before.json`(모든 판의 issues·autofix·warnings 동일) | A16 |
| C-4 | 모든 CLI `--help` 출력 == `reports/S5-1/help_before.txt` | A17 |
| C-5 | `check-config` 통과, 스키마에 있는 키 ⊆ 코드가 읽는 키(5.7 표의 삭제 키가 스키마·yaml에 0) | A18 |
| C-6 | 작성 중 `BudgetExceeded` → `weeks.current_run_id` 불변 ∧ `runs.status == "stopped"` ∧ 종료 코드 1 ∧ 남은 토픽 시작 0 | A19 |
| C-7 | `fetch_page(u)` 뒤 `read_more(doc=u)`가 u ∈ {github 대문자, http, arxiv pdf}에서 거부되지 않음 | A20 |

### 5.12 실패 동작
- 에러 형식은 지금 그대로(`ctx.stopped` 문자열, attention, stderr 한 줄). 새 예외 클래스 없음
- 종료 코드: `weekly`(및 하위 `cluster`·`select`·`write`·`review`) 예산 중단 1, 인자 오류 2(지금 그대로), 그 밖 0
- 부분 실패: 토픽 하나의 예상 밖 오류(`except Exception`)는 지금처럼 그 토픽만 `failed`, 계속. **예산 초과만** 전체 중단
- 측정 스크립트: DB·run 없음 2, 비교 차이 1, 같음 0

## 6. 관문 A (`scripts/verify_s5.sh`에 A15~ 추가, 모두 판정 수단 `스크립트`)

| ID | 검증 | 판정 방법 | PASS 기준 | 관련 |
|---|---|---|---|---|
| A1~A14 | S5 관문 A 그대로(A3은 5.9로 강화) | 기존 | 전부 PASS | C-1 |
| A15 | 프롬프트 불변 | `uv run python scripts/s5_1_prompts.py --diff reports/S5-1/prompts_before.json` | 종료 코드 0(차이 0) | C-2 |
| A16 | 코드 검사 결과 불변 | `uv run python scripts/s5_1_golden.py --out $TMP/g.json && diff -q $TMP/g.json reports/S5-1/golden_before.json` | 차이 0 | C-3 |
| A17 | CLI 도움말 불변 | `--help` 전부 → `diff` | 차이 0 | C-4 |
| A18 | 효과 없는 설정 키 0 | 5.7 표의 키를 `config/*.yaml`(주석 제외)·`trendsit/core/config*.py`에서 grep | 0건, check-config OK | C-5 |
| A19 | 예산 초과 시 멈춤 | `pytest tests/test_s5_weekly.py -k budget_stop`(write·select·cluster 도중 각각 `BudgetExceeded`) | 3경우 모두 C-6 성립 | C-6, F-1·F-7 |
| A20 | 실행 요약 상태 | `pytest -k summary_status`: 전부 실패 → failed, 일부 → partial, 예산 → stopped | 3경우 일치 | F-27 |
| A21 | read_more 열쇠 | `pytest -k read_more_page_key`(URL 3종) | 3종 모두 읽힘 | C-7 |
| A22 | 지운 코드가 없음 | grep: `def fallback`가 5.8의 7개 클래스에 0, `collect/video/settings.py` 없음, 5.8 F-18 이름 0 | 0건 | F-9·F-10·F-18 |
| A23 | 순 줄 수 감소 | `git diff --shortstat a259b99 -- trendsit/` | 삭제 줄 > 추가 줄 | 3.4 |
| A24 | 리포트·README | `reports/S5-1a_report.md`에 8장 체크리스트 전부 `[x]`, README "현재 상태" 줄에 S5-1a | grep | - |

AC 10개(A15~A24) + 기존 A1~A14.

## 7. 관문 B와 QA

- **관문 B: 이 스펙은 실행하지 않는다.** 프롬프트(C-2)와 코드 검사 결과(C-3)가 불변이므로 LLM 출력이 바뀔 경로가 없다. S5-1b 런 뒤 1회 실행한다(COMMON 3장)
- QA 대상 AC: **없음**(전부 스크립트). 실데이터 재실행 없음
- 적대적 차원: 예산 초과(A19)만. 그 밖 차원은 고르지 않는다(단순화 스펙에 적대 테스트를 넣으면 방어 코드가 들어온다)

## 8. 단계 (커밋 단위, 진행 블록 E11)

| ID | 단계 | 완료 AC | 산출물 |
|---|---|---|---|
| S-1 | 첫 커밋(handoff + CLAUDE.md 진행 상태 블록) → `verify_s5.sh --fast`(verify 스크립트 안의 인자, A1만 건너뜀) → 측정 스크립트 2개 + "전" 스냅숏 3개(5.1, main 코드 기준) | A15~A17 PASS(변경 전이라 자명) | `scripts/s5_1_*.py`, `reports/S5-1/*` |
| S-2 | 동작 고침: F-1·F-7·F-27(한 커밋), F-2·F-20(한 커밋), F-17·F-32·F-33(한 커밋). **공통 코어(`tools/`) 수정은 별도 커밋**(COMMON 9장) | A19~A21 | 테스트 3묶음 |
| S-3 | 설정 키(5.7) → 죽은 코드·방어 코드(5.8) → verify 헬퍼(5.10). 묶음당 커밋 하나 | A15~A18, A22, A23 | |
| S-4 | 리포트·README | A24 | `reports/S5-1a_report.md` |

리포트 8장 = SUMMARY 요약(라운드, 잔여 open, optional 목록, 거부 근거, 복잡도 예산 사용량), 9장 = verify_s5 실행 시간 전후(측정만).

## 9. 넘길 것과 미확정

- 미해결 `Q-*`: **0건**
- 구현 시점 기본값(묻지 않음, 리포트 "결정한 것"에 기록): 이름 바꾸기, import 정리, 주석, 함수 순서, 타입 표기, 테스트 함수 이름, 커밋 메시지 문구
- PR 설명: 맨 위 "공통 코어 수정"(tools/, core/) 표시, optional finding 목록, S5-1b로 넘긴 리뷰 번호
- 런 뒤 워크플로우 밖: 관문 B 없음 → 리포트 → README → 커밋·푸시·PR. 손으로 고친 것이 있으면 `code-reviewer` 1회
- 문서 동기화(기획 세션 요청, 이 PR의 docs 커밋 하나): `docs/handoff/COMMON.md` 6.1-1의 "`<example>` 3개"를 "`<example>` 3~5개(기본 3개: 보통 / 빈칸이 맞는 경우 / 함정. check-config lint가 3~5로 검사)"로. 결정 출처 64 C-26
- S5-1b가 쓰는 것: `scripts/s5_1_golden.py`, `scripts/s5_1_prompts.py`(이 스펙 병합본 기준으로 "전" 스냅숏을 다시 만듦)

## 13. 실측 반영 이력
| 날짜 | 발견 | 근거 | 반영 |
|---|---|---|---|
| 2026-10-10 | W41 현재판 run에 옛 코드 판정 토픽이 carry_over로 섞여, weekly 재실행은 리팩터 전에도 판정이 달라짐 → 동일성 검증은 저장 판 재검사(골든)로 | 기획 세션 재실행 스크립트 | 5.1 |
| 2026-10-10 | 전체 주 재실행 W41 17.3분·$0.111, W40 15.9분·$0.081 | `runs`·`steps` | S5-1b 7장 |
| 2026-10-10 | `bash scripts/verify_s5.sh` 전체 **36분 6초**(real 2166s), 전부 PASS. A1(s0~s4, s2~s4가 다시 s0·s1을 부름, 리뷰 F-23)이 대부분이고 A2 전체 pytest 533개 3분 12초. A1 제외 추정 약 5분 → 게이트는 `--fast`, 전체는 런 뒤 1회 | 기획 세션 `time` 측정(`10abef6` = main 내용) | 2장, 5.10 |
| 2026-10-10 | 명세가 지시한 범위(호출처·테스트·verify 스크립트 포함)만으로 약 56개라 상한 40을 지킬 수 없음 → 사용자 결정으로 60 | A1-impl.md 미해결 1 | 3.4 |
