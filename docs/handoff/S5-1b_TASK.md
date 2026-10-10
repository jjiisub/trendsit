# S5-1b 단순화: 코드 검사 규칙 정리, 중복 제거, 역할 md 정리

> 기획 세션 작성 2026-10-10(spec-planner, 원장 `.workflow/planning/s5-1/ledger.md`). 기준 커밋 **S5-1a 병합 커밋**(main).
> S5-1(단계 R)을 런 2개로 나눈 것의 둘째. 첫째 `docs/handoff/S5-1a_TASK.md`가 병합된 뒤 시작한다. S5-1a가 만든 측정 도구(`scripts/s5_1_golden.py`, `scripts/s5_1_prompts.py`)를 쓴다.
> 공통 규칙은 `docs/handoff/COMMON.md`(특히 12장), 이 문서가 우선한다. 구현 세션은 `/impl-workflow docs/handoff/S5-1b_TASK.md .`로 돌린다.

## 0. 이 스펙이 끝나면 되는 것

| 항목 | 값 |
|---|---|
| slug | `s5-1b` |
| 버전 / 작성일 | v1 / 2026-10-10 |
| 문서 상태 | **확정(투입 가능)**. 단 시작 조건: S5-1a 병합 |
| 미해결 `Q-*` | 0건 |
| 선행 런 | `.workflow/<NNN>-s5-1a/`(같은 기획 원장) |
| 브랜치 | `s5-1b-simplify`, 첫 커밋 = 이 문서 |

**한 줄 목표**: 넓고 자주 걸리는 것만 코드 검사에 남기고, 지엽적인 규칙은 LLM 지침으로 넘기며, 같은 일을 하는 코드·md 문장을 한 벌로 줄여 S6를 가벼운 코드 위에서 시작한다.

- 사용자 체감 결과: `brief/checks.py`·`brief/write.py`가 500줄 아래, 코드 검사 규칙은 아래 5.1 표의 "남김"만, 역할 md에 같은 규칙이 두 번 나오지 않음. 브리핑의 사실 충실성은 S5 병합 시점 이상(관문 B, 7장)
- **트레이드오프 허용**: 표현이 조금 덜 다듬어지는 정도는 허용한다(D-9). 사실이 틀린 정보는 불허

## 1. 맥락

- 리뷰 네 번 동안 "실패 사례 하나 → 코드 규칙 하나"가 반복돼 `checks.py`가 368 → 507줄, `check()` 한 함수 185줄이 됐다(기획 문서 84). 기획 세션이 W40·W41 현재판 20토픽의 저장된 모든 라운드 판에 현재 검사를 다시 돌려 규칙별 발동·오탐을 실측했다(근거 A, 5.1 표의 숫자)
- 결정(원장 번호)

| ID | 결정 | 근거 |
|---|---|---|
| D-9 | 구조 단순화 우선. 사실 오류는 불허, 표현 품질 트레이드오프는 허용 | 사용자 2026-10-10 |
| D-11 | **넓고 자주 걸리는 것만 코드, 지엽적인 것은 LLM 지침(md)**. md 문구 변경 허용 | 사용자 |
| D-15 | 5.1의 규칙 분류 | 실측 + 사용자 승인 |
| D-18 | 줄 수 목표 숫자 없음: 순 감소 + 500줄 초과 파일 0 + 뺀 규칙이 코드에 0 | 사용자. 숫자 목표는 억지 압축 코드를 부름 |
| D-19 | 함수 60줄 이하는 이번에 손대는 함수만 | 사용자 |
| D-24 | 관문 B는 사실 지표만 판정(7장) | 사용자 |
| D-25 | md에 박힌 설정 숫자 제거. 작성자 입력에 `limits` 칸 추가 | 사용자. 같은 값이 brief.yaml과 md 두 곳에 있음(리뷰 F-13) |
| D-26 | 예시 개수 규칙(리뷰 F-14)은 **코드 lint(3~5개)를 기준**으로 두고 문서만 맞춘다(COMMON 6.1 문구는 기획 세션이 main에서). 측정하지 않는 S2~S4 역할의 예시는 바꾸지 않음 | 사용자위임: 재실행으로 측정되는 것은 S5 역할뿐 |
| C-25 | 새 코드 규칙은 일반성·재사용·사실 보호 셋 다일 때만(64 부록 C) | 기존 결정 |

## 2. 준비물 (환경 전제·검증 명령·유료 상한)

| 항목 | 값 |
|---|---|
| 작업 디렉터리 | `~/Claude/projects/trendsit`, S5-1a 병합된 main에서 브랜치 |
| 런타임 | S5-1a와 같음 |
| 데이터 | `data/trendsit.db`. 워크플로우 안에서는 **읽기만**. 런 뒤 재실행(7장)만 쓴다 |
| **검증 명령(게이트)** | `.workflow/gate.sh` = `bash scripts/verify_s5.sh --fast`(S5-1a가 만든 빠른 경로, 15분 이내). 이 스펙의 AC는 같은 스크립트에 `B1~` 행으로 추가 |
| 전체 검증 | `bash scripts/verify_s5.sh`(A1 포함) 런 뒤 1회 + PR 전. 전체 PASS가 병합 조건 |
| **유료 호출 상한** | 워크플로우 안 **$0**(LLM 호출 없음). 런 뒤 워크플로우 밖: W40·W41 재실행 + 관문 B judge, 합계 **$1.00 이내**(`--spec S5`, S5 키 남은 몫 약 $2.1 안). 넘으면 멈추고 보고 |

## 3. 범위

### 3.1 한다
1. 코드 검사 규칙 정리(5.1): 뺄 규칙 삭제, 그 내용이 md에 없으면 md 한 줄로
2. 중복 코드 한 벌로(5.2): 리뷰 F-11, F-20(fetcher 외), F-21, F-22, F-28
3. 역할 md 정리(5.3): 리뷰 F-3, F-6, F-12, F-13(D-25), F-15(문서만), F-26, F-34, F-35
4. 이번에 손대는 긴 함수 쪼개기(5.4): `check`, `autofix`, `warnings`, `write_topic`, `run_weekly`를 각 60줄 이하로
5. 500줄 넘는 파일 0(5.4)

### 3.2 비목표
| # | 하지 않는 것 | 이유 |
|---|---|---|
| NG-1 | 새 기능, 새 CLI 명령·옵션, `limits` 외 새 입력 칸 | 단순화 스펙 |
| NG-2 | 코드 검사 규칙 **추가**(5.1 "남김"을 손보는 것 포함) | C-25 |
| NG-3 | 관문 B 문턱값·채점표·judge md(`eval/judge*.md`)·라벨 변경 | 측정이 흔들림 |
| NG-4 | S2~S4 역할 md의 예시·지침 변경(F-12의 `<data>` 중복 문장 삭제만 예외) | 재실행으로 측정되지 않음(D-26) |
| NG-5 | 출력 스키마 칸 순서(F-16), Whisper 모델 id(F-30) | MVP 뒤 |
| NG-6 | 실행 시간 단축 목표, 성능 최적화 | 결과로만 잰다 |
| NG-7 | S5 남은 ⚠ 토픽 품질 개선(근거 충실성 2토픽, 2채널 토픽 부족, 편집장 큐 재처리, spoken_value 오탐) | MVP 뒤(D-12) |
| NG-8 | S5-1a가 다룬 항목 재작업 | 병합됨 |

### 3.3 건드리지 않을 것
- 파일: `eval/`(채점기·채점표·judge md·라벨·문턱값. **예외: `eval/fixtures/writer/*.json`은 `scripts/s5_eval_fixtures.py`로 재생성만**), `data/`(워크플로우 안), `docs/handoff/CONTRACTS.md`, `trendsit/core/migrations.py`, `config/*.yaml`, `reports/eval/`, S2~S4 역할 md(NG-4 예외 외)
- 영역: DB 스키마, CLI 명령·옵션·`--help`(S5-1a 스냅숏과 동일), 실행 요약 JSON 형식, `TopicPage` 등 **출력** 스키마

### 3.4 복잡도 예산
| 항목 | 값 |
|---|---|
| 변경 파일 수 | ≤ 35(md·테스트·verify 포함, 재생성 픽스처 20개는 세지 않음) |
| 새 파일 | ≤ 3, **500줄 넘는 파일을 쪼갤 때만**(삭제로 500 아래가 되면 0) + `reports/S5-1b_report.md` |
| 순 줄 수 | `trendsit/` 순 감소, `roles/*.md`+`skills/*.md` 순 감소 |
| 새 의존성 | 금지 |
| 금지 구조 | 규칙 레지스트리·규칙 클래스 계층·플러그인, 새 설정 키·옵션, 공통 부모 클래스 확장(`artifacts_*` 공통화는 중복 삭제 범위에서만) |
| 품질 수준 | 프로덕션 |

## 4. 폴더

```
trendsit/brief/{checks,write,pipeline,weekly,select,cluster,evidence,briefing,report}.py
trendsit/core/{artifacts_brief,agent,config,config_brief,config_video,artifacts_text,numbers}.py
trendsit/tools/{web,github}.py, trendsit/collect/links.py, trendsit/filter/embed.py, trendsit/cli*.py
roles/{writer,critic,writer_revise,decide,editor_select}.md, roles/*.md(<data> 문장만), skills/{style_ko,diagrams}.md
scripts/{s5_gate_b,s5_eval_fixtures,verify_s5}.sh|py, AGENTS.md, tests/, eval/fixtures/writer/(재생성)
reports/S5-1b_report.md, reports/S5-1/intended_removals.json
```

## 5. 상세

### 5.1 코드 검사 규칙(`brief/checks.py`)

실측: 현재 코드를 W40·W41 현재판 20토픽의 저장된 모든 라운드 판에 다시 돌린 발동 수(라운드 합/토픽). "저장"은 저장된 판정 기록 기준(옛 코드 포함).

**남김(코드)**
| 규칙 | 실측 | 이유 |
|---|---|---|
| 필수 칸·summary/overview 문장 수·points 개수·짧은 point·refs 개수·refs 실재 | 0~2 | 형식 계약, 모든 토픽 |
| 수치 대조(points, 제목·요약·개요·개념·도식·기여 칸), 도식 값 ↔ 근거 | 2/1, 2/2 | 사실, 모든 토픽 |
| 요약·개요 수치는 points·numbers 값만(4차 H1a, `with_units` 포함) | 9/2 | 사실 보호, 사용자 결정 |
| 영문 이름 뒤 숫자는 버전(수치 대조 제외) | (Haiku 5.5 오탐 반려 3회 방지) | 모델 이름 토픽 전반 |
| contributions 채널 누락 | 1/1 | 형식 |
| 도식 칸 구조(그룹 상한, anchor, title·context, 항목 2~6, 한 포인트 도식 하나), 빈 단위, 그룹 안 단위 섞임, 날짜 형식, 사건 근거, concepts 상한 | 0 | 형식, 코드 몇 줄 |
| 명사형 칸이 문장으로 끝남, 요약·개요 문장마다 "~다", 해요체, `EVAL_ENDINGS`·`EVAL_WORDS`(core.style) | 117(저장)/14, 5/2, "핵심이다" 2/2 | 자주 걸림, 공용 모듈 |
| 자동 수정: points 초과 자르기, contributions 채널 정리, 그릴 수 없는 도식 빼기, 별칭·음차 정본, 공백·문장부호, 형광 상한 | 저장 48/17 등 | 반려 없이 고침 |
| 경고: 같은 근거 문장의 같은 단위 값 3개 이상(누락 의심), events 누락, 남발, 중복 point | 9/5 등 | 검수자 입력 |

**뺌(코드에서 삭제 → 내용은 md)**
| 규칙 | 줄 | 실측 | md 처리 |
|---|---|---|---|
| `BAD_PARTICLE`(영문 이름 뒤 조사) | 40, 413-414 | 12/4, **3토픽 9건 오탐**(DeepSeek가·Work와·Instant가) | `skills/style_ko.md`에 "영문 이름 뒤 조사는 한글 발음 기준(Anthropic → 앤트로픽이)" 한 줄 |
| `CONCEPT_DESC_MIN`과 짧은 개념 자동 삭제 | 44, 144-149 | 저장 2/2, 목적 사례("Sourcegraph의 베타 출시 기능", 21자)에 무효 | writer.md "풀이가 없으면 넣지 않는다" 이미 있음 |
| `BARE_PER_TOKEN`·`PER_MILLION` | 41-42, 337-341 | 1/1 | writer.md:37 "단위와 기준('100만 토큰당')을 빠뜨리지 않는다" 이미 있음 |
| `SPECULATIVE` 반려 | 38, 402, 417-419 | "부상했다" 1/1, 나머지 7개 0 | writer.md:40·critic.md:64 이미 있음. **`scripts/s5_gate_b.py`는 같은 목록을 그 파일 안의 상수로 옮김(값 동일, 관문 B 측정 불변)** |
| 라벨 끝 괄호 단위 ≠ 그룹 단위(`LABEL_UNIT`) | 46, 356-362 | 0(지금까지 전부) | writer.md "한 그룹 한 단위" 이미 있음 |
| 근거 단위 ≠ 그룹 단위(`evidence_unit`)와 "단위 확인 필요" 경고 | 64-75, 363-367, 484-489 | 0 / 저장 4/3 | critic 대조 |
| `GENERIC_START`·감탄·질문형 끝·이모지 | 24-25, 405-412 | 0 | style_ko.md 이미 있음 |
| 금지 표현 힌트 3갈래 | 415-424 | - | 힌트 한 문장으로 |
| 경고: angle 핵심 낱말(`_PARTICLE`, `_GENERIC`, `angle_words`) | 430-452 | 3/1 | critic.md 핵심 포착 기준 이미 있음(없으면 한 줄) |
| 경고: 한 point 안 같은 단위 값 3개(`_VAL`, 474행 단위 튜플) | 43, 467-479 | 7/3 | diagrams.md 이미 있음 |
| `UNIT_KINDS`·`unit_kind` | 32-36, 49-61 | - | **남김 규칙(`with_units`)이 쓰는 만큼만 남김**. 안 쓰는 단위 종류는 삭제 |
| `scripts/s5_order_preview.py` | 96줄 | 참조 0 | - |

**의도한 제거 표 `reports/S5-1/intended_removals.json`**(B1 판정 기준): 첫 코드 커밋에서 만든다. 형식 `[{"topic_id", "round", "kind": "issue|autofix|warning", "match": "<원문 앞부분>", "rule": "<뺀 규칙 이름>"}]`. 골든 회귀 전후 차이 = 이 표, 정확히 일치해야 한다. 표에 없는 차이는 실패

### 5.2 중복 코드(한쪽을 지우고 남은 쪽을 씀)
| 리뷰 | 내용 |
|---|---|
| F-11 | topics·briefing_plans INSERT(`pipeline.py:94-102` ↔ `select.save`), 별칭 표·영상 관련성 계산(`pipeline.py:64-69` ↔ `weekly.py:91-92, 106-107`), `UPDATE runs SET week` 두 번 → 각각 한 곳 |
| F-20 | `agent._loc` ≡ `config.loc_to_path`, `web.page_links`(+`_REF`) ≈ `collect.links.extract_links`, `artifacts_text.norm_url` 래퍼, 수치 정규식 4벌(`artifacts_text._NUM`, `select._NUM`, `aliases._NUM`, `collect/github._NUM`) → `core/numbers.py`, `cluster.score_video_relevance`·`interest_similarity`가 `filter.embed.best_interest` 재구현(관심사 임베딩 한 번만), `config_brief._Strict`·`config_video._Strict` → `config.Strict`. **동작이 다르면(정규식이 미세하게 다름 등) 합치지 않고 리포트에 이유** |
| F-21 | 페이지 근거 id 칸 순회 4벌 → 1벌, `cap_pack.groups` ≡ `write.pack_index`, `select.recent_topics` ≈ `cluster.past_topics`, 주차 문자열 파싱 4곳 → `evidence.week_days` 하나, `fallback_plan`의 slug 재구현, 출력 폴더 상수 `OUT` 두 곳 → 한 곳 |
| F-22 | CLI의 spec 결정(`_spec`, `args.spec or "S2"` 등) → `config.current_spec(args.spec, 기본값)` 하나(환경변수 `TRENDSIT_SPEC` 우선은 지금 `current_spec` 동작 그대로), `cli_text._date` ≡ `cli._parse_date`, DB 열기 6곳 → 한 함수 |
| F-28 | 테스트가 경로 규칙을 다시 조립(`test_s5_common.py:79-87`) → `config.SECRET_FILE.parent` 기준, 출력 폴더 이중 monkeypatch → 하나(F-21과 함께) |

### 5.3 역할 md
| 리뷰 | 처리 |
|---|---|
| F-3 | `writer_revise.md:46`에서 "문체"와 "(이슈로 오지 않는다)" 삭제(형광만 코드가 고침) |
| F-6 | `decide.md` 입력 절을 실제 렌더(`<document id="it:1" …>`, `<document id="vd:Ab" …>`, 첫째가 a·둘째가 b)대로. 출력 예의 "a는/b는"도 같이 |
| F-12 | `<data>` 처리 문장: 모든 `roles/*.md`에서 삭제(코드 `DATA_RULE`이 system에 붙임). 문체: writer.md·video_summary.md에서 style_ko.md와 같은 문장 삭제. 도식 상한: writer.md에서 diagrams.md와 같은 문장 삭제. 근거 범위 사례 표: writer.md:36-47과 critic.md:55-70에 같은 사례가 두 벌 → **critic.md 표 하나만 남기고 writer.md는 유형 이름 한 줄씩**(새 skill 파일 만들지 않음) |
| F-13·D-25 | editor_select.md·decide.md·writer.md의 설정 숫자 삭제 → "입력 `limits`의 값". `core/artifacts_brief.py`에 `WriterLimits`(`points: tuple[int,int]`(이 토픽의 n_sources로 고른 범위), `overview_sentences`, `summary_sentences`, `highlights_page`, `numbers_groups_max`, `events_groups_max`, `concepts_max`)와 `WriterInput.limits`. 채우는 곳: `write.py`, `scripts/s5_eval_fixtures.py`, `scripts/s5_gate_b.py`. `decide.md`의 "0.6 미만" 문구와 `artifacts_brief.py:41` description의 숫자도 삭제 |
| F-15 | `AGENTS.md` "원칙" 마지막 줄을 실제 검사 범위(섹션·예시 수·굵게)로 고침. check-config에 검사 추가 안 함 |
| F-26 | `CriticInput.page`, `WriterReviseInput.previous`를 렌더에서 뺌(`loc_lines`만). 코드는 객체를 계속 씀(필드는 `exclude` 또는 렌더 제외 표시, 어느 쪽이든 새 옵션 없이) |
| F-34 | `writer_revise.md:20` `## 목표` 앞 굵은 문단 삭제 |
| F-35 | writer system 프롬프트(writer.md + include)의 굵게 1개로: `diagrams.md:5` 굵게 해제 |

- md 각 파일은 `check-config` 섹션 검사 통과
- `eval/fixtures/writer/*.json` 20개는 `uv run python scripts/s5_eval_fixtures.py`(writer 부분)로 재생성. 다른 역할 픽스처는 그대로

### 5.4 함수·파일 크기
- `check`, `autofix`, `warnings`(checks.py), `write_topic`(write.py), `run_weekly`(pipeline.py) 각 60줄 이하. 쪼갤 때 위치별(칸별) 작은 함수로, 클래스·레지스트리 금지
- 500줄 넘는 `trendsit/**/*.py` 0개. 5.1·5.2 삭제 뒤에도 넘으면 그 파일만 쪼갬(새 파일 ≤ 3)

### 5.5 계약
- CLI·DB·실행 요약·`TopicPage` 출력 스키마: S5-1a 병합 시점과 같음
- 바뀌는 계약은 **역할 입력** 두 가지뿐: `WriterInput.limits` 추가, `CriticInput`·`WriterReviseInput` 렌더에서 page 중복 제거
- `WriterInput.limits` 예시(정상): `{"points": [3, 6], "overview_sentences": [2, 4], "summary_sentences": [1, 3], "highlights_page": [3, 4], "numbers_groups_max": 2, "events_groups_max": 1, "concepts_max": 3}`(근거 소스 2개 이상). 근거 소스 1개면 `"points": [2, 3]`
- 이상 예: `limits` 없이 `WriterInput` 생성 → pydantic 검증 오류(필수 칸)

### 5.6 불변식
| ID | 불변식 | 판정 |
|---|---|---|
| C-1 | 게이트 종료 코드 0, pytest 건너뜀 0 | 게이트 |
| C-2 | 골든 회귀 전후 차이 == `intended_removals.json`(집합 일치) | B1 |
| C-3 | 5.1 "뺌" 규칙 이름(`BAD_PARTICLE`, `CONCEPT_DESC_MIN`, `BARE_PER_TOKEN`, `PER_MILLION`, `LABEL_UNIT`, `evidence_unit`, `GENERIC_START`, `EMOJI`, `angle_words`, `_GENERIC`, `_VAL`)이 `trendsit/`에 0, `SPECULATIVE`가 `trendsit/brief/`에 0 | B2 |
| C-4 | `scripts/s5_1_prompts.py` 차이가 S5 역할(writer, writer_revise, critic, decide, editor_select)과 `<data>` 문장을 지운 역할에만 있음. `eval/judge*.md`는 차이 0 | B3 |
| C-5 | `trendsit/**/*.py` 중 500줄 초과 0, 5.4 함수 5개 각 ≤ 60줄 | B4 |
| C-6 | `trendsit/` 순 줄 수 < 0, `roles/`+`skills/` 순 줄 수 < 0 | B5 |
| C-7 | `scripts/s5_gate_b.py`의 금지 표현 목록 == 현재 `checks.SPECULATIVE` 값 | B6 |
| C-8 | CLI `--help` == S5-1a 스냅숏 | B7 |

### 5.7 실패 동작
- 변경 없음(S5-1a 그대로). 예산 초과는 S5-1a의 멈춤 규칙
- 리팩터 중 동작이 달라지는 중복(5.2 굵은 글씨)은 합치지 않고 남긴다. 이건 실패가 아니라 리포트 항목

## 6. 관문 A (`scripts/verify_s5.sh`에 B1~ 추가, 모두 판정 수단 `스크립트`)

| ID | 검증 | 판정 방법 | PASS 기준 | 관련 |
|---|---|---|---|---|
| A1~A24 | S5·S5-1a 관문 그대로 | 기존(A16은 B1로 대체: 골든 기준 파일이 바뀜) | PASS | C-1 |
| B1 | 코드 검사 결과 차이가 의도한 제거와 일치 | `s5_1_golden.py` 출력 vs `golden_before.json`(S5-1a 병합본 기준 재생성) 차이 집합 == `intended_removals.json` | 정확히 일치 | C-2 |
| B2 | 뺀 규칙이 코드에 없음 | grep(C-3 이름) | 0건 | C-3 |
| B3 | 프롬프트 변경 범위 | `s5_1_prompts.py --diff` 결과의 역할 목록 ⊆ 허용 목록, judge 0 | 일치 | C-4 |
| B4 | 파일·함수 크기 | `wc -l`, `ast`로 5개 함수 길이 | C-5 | C-5 |
| B5 | 순 줄 수 | `git diff --shortstat <S5-1a 병합> -- trendsit/` 및 `-- roles/ skills/` | 둘 다 삭제 > 추가 | C-6 |
| B6 | 관문 B 정규식 목록 불변 | python 한 줄로 값 비교(S5-1a 병합본 `checks.SPECULATIVE`는 첫 커밋에서 `reports/S5-1/speculative_before.json`으로 저장) | 같음 | C-7 |
| B7 | CLI 도움말 | S5-1a A17 그대로 | 차이 0 | C-8 |
| B8 | 작성자 입력 limits | `pytest -k writer_limits`: 소스 1개 → points [2,3], 2개 이상 → [3,6], 값이 `brief.yaml`에서 옴(설정을 바꾼 임시 cfg로 확인) | PASS | D-25 |
| B9 | 렌더 중복 제거 | `pytest -k render_no_page_dup`: critic·writer_revise 렌더에 같은 point 문장이 한 번만 | PASS | F-26 |
| B10 | md 중복 | grep: `<data>` 처리 문장이 `roles/*.md`에 0, writer.md에 diagrams.md·style_ko.md 문장과 같은 줄 0, editor_select·decide·writer md에 brief.yaml 숫자(4~10, 0.55, 0.6, 2~3, 3~6, 3~4) 0 | 0건 | F-12·F-13 |
| B11 | 리포트·README | `reports/S5-1b_report.md` 체크리스트 전부 `[x]`, 8장 SUMMARY, 9장 전후 줄 수 표, 10장 관문 B 칸(런 뒤 채움 표시) | grep | - |

AC 11개(B1~B11).

## 7. 관문 B와 QA

- **QA 대상 AC: 없음**(워크플로우 안은 전부 스크립트, 0원)
- **런 뒤 워크플로우 밖(구현 세션, COMMON 3장)**:
  1. `uv run python -m trendsit weekly --week 2026-W40 --spec S5`, 이어서 `--week 2026-W41`(처음부터, 캐시 켠 채). 실측 기준 각 약 16·17분, 합계 약 $0.2. 두 run이 각 주 현재판이 됨
  2. 관문 B(S5 7장 항목, 라벨 잠정 opus-5.5)
  3. **판정(D-24)**: 근거 충실성 통과 토픽 ≥ 18/20 **그리고** 묶기 오병합 0 → 통과. 핵심 포착·군더더기·읽기 쉬움·문체·정규식은 **기록만**(S5 병합 시점 값과 나란히)
  4. 충실성이 18 미만이면: 떨어진 토픽의 원인을 5.1·5.3 변경 중 하나로 특정 → 그 변경을 고치거나 되돌림 → 해당 토픽만 재실행, **최대 3회**(E-규칙). 그래도 미달이면 멈추고 `[사용자 필요]`
  5. 사용액 합계 $1.00을 넘기면 멈춤
- 적대적 차원: 고르지 않는다(단순화 스펙)

## 8. 단계 (커밋 단위)

| ID | 단계 | 완료 AC | 산출물 |
|---|---|---|---|
| S-1 | 첫 커밋(handoff) → "전" 스냅숏 재생성(**S5-1a 병합 커밋을 `git worktree`로 꺼내 그 코드로**, S5-1a 5.1과 같은 방법: golden·prompts·speculative) → 5.1 규칙 삭제 + `intended_removals.json` + md 한 줄 이동 + gate_b 상수 이동 | B1, B2, B6 | checks.py, s5_gate_b.py, style_ko.md |
| S-2 | 5.2 중복 제거(F-11 / F-20 / F-21 / F-22·F-28, 묶음당 커밋. 공통 코어는 별도 커밋) | B5(중간), B7 | |
| S-3 | 5.3 md 정리 + `WriterInput.limits` + 픽스처 재생성 | B3, B8, B9, B10 | |
| S-4 | 5.4 함수·파일 크기 → 리포트·README | B4, B5, B11 | `reports/S5-1b_report.md` |

## 9. 넘길 것과 미확정

- 미해결 `Q-*`: **0건**
- 구현 시점 기본값: 이름, import, 주석, 함수 순서, 타입 표기, 쪼갠 함수의 경계(위치별이라는 원칙 안에서), 커밋 문구
- PR 설명: 공통 코어 수정 표시, optional finding 목록, 합치지 않은 중복과 이유(5.2), 관문 B 결과(런 뒤)
- 기획 세션이 PR 뒤 할 일: COMMON 6.1 예시 개수 문구(D-26), 64 부록 C에 C-26(S5-1 결정 요약), 19 갱신

## 13. 실측 반영 이력
| 날짜 | 발견 | 근거 | 반영 |
|---|---|---|---|
| 2026-10-10 | 규칙별 발동·오탐(5.1 표) | 기획 세션 재실행 스크립트(저장 판 20토픽 전 라운드) | 5.1 |
| 2026-10-10 | `BAD_PARTICLE` 오탐 3/4토픽 | 같음 | 5.1 |
| 2026-10-10 | `select.order` similarity 모드 코드는 이미 없음, 미리보기 스크립트만 남음 | grep | 5.1 |
