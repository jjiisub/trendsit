# S5-1b 리포트: 단순화 (코드 검사 규칙 정리, 중복 제거, 역할 md 정리)

기준 main S5-1a 병합 커밋 `bed7887`, 브랜치 `s5-1b-simplify`. 명세 `docs/handoff/S5-1b_TASK.md`.

## 1. 한 줄 요약
코드 검사에서 지엽 규칙(영문 이름 뒤 조사, 짧은 개념 삭제, 토큰당, 전망형 반려, 라벨·근거 단위, 일반론·감탄·이모지, angle 경고, point 안 단위 3개 경고)을 걷어내고 그 내용은 md로 넘겼으며, 같은 일을 하던 코드·md 문장을 한 벌로 줄이고, 작성자 입력에 `limits`를 넣었고, `check`·`autofix`·`write_topic`·`run_weekly`를 칸별·단계별 함수로 쪼갰다. 코드 검사 전후 차이는 의도한 제거 표 26건과 정확히 같다(B1). LLM·임베딩 유료 호출 0회.

## 진행 체크리스트
- [x] S-1 "전" 스냅숏을 `bed7887` worktree에서 재생성(golden·prompts는 기존 파일과 바이트 동일, speculative 신규), 5.1 규칙 삭제, `intended_removals.json`, md 한 줄 이동, gate_b 상수 이동 (B1, B2, B6)
- [x] S-2 5.2 중복 제거: F-11 / F-20(공통 코어는 별도 커밋) / F-21 / F-22·F-28 (B5 중간, B7)
- [x] S-3 5.3 md 정리, `WriterInput.limits`, writer 픽스처 재생성 (B3, B8, B9, B10)
- [x] S-4 5.4 함수·파일 크기, 리포트·README (B4, B5, B11)

## 2. 관문 A 결과
런 중 게이트 `bash scripts/verify_s5.sh --fast` 종료 코드 0. A2 pytest 543 passed(건너뜀 0), A3 check-config OK, A4~A24와 B1~B10 PASS. 전체 `verify_s5.sh`(A1 포함)는 런 뒤 1회 돌린다(이 리포트 작성 시점에는 미실행).

| ID | 결과 |
|---|---|
| B1 | 골든 전후 차이 == `reports/S5-1/intended_removals.json` 26건 |
| B2 | 뺀 규칙 이름 11개 + `SPECULATIVE`(trendsit/brief/) 0건 |
| B3 | 프롬프트 변경 역할 = S5 역할 5개 + `<data>` 문장만 지운 역할, `eval/judge*.md` 차이 0 |
| B4 | 500줄 넘는 `trendsit/**/*.py` 0개, 5개 함수 모두 60줄 이하(9장) |
| B5 | `bed7887` 기준 `trendsit/` +699/−717, `roles/ skills/` +61/−74 |
| B6 | `scripts/s5_gate_b.py` 금지 표현 8개 == `reports/S5-1/speculative_before.json` |
| B7 | CLI `--help` 전부 불변 |
| B8 | `pytest -k writer_limits`(소스 1개 [2,3], 2개 이상 [3,6], 값은 brief.yaml, `limits` 없으면 검증 오류) |
| B9 | `pytest -k render_no_page_dup`(검수자·수정 입력에 같은 포인트 문장 한 번) |
| B10 | `<data>` 문장 0, writer.md와 diagrams·style_ko 같은 줄 0, editor_select·decide·writer의 설정 숫자 0 |
| B11 | 이 리포트 |

### 2-1. 의도한 제거 표 26건(규칙별)
| 규칙 | 건수 | 차이 |
|---|---|---|
| `BAD_PARTICLE` | 12 | Work와(gpt-6-1-sol 2), DeepSeek가(deepseek-harness 6), Instant가(gpt6-intelligent-ui 1), Anthropic가(claude-haiku-5-5 3), summary·overview·points 위치별. "summary 금지 표현: 핵심이다, 조사 ..." 는 낱말마다 한 건으로 세어 조사 쪽만 사라지고 "핵심이다"는 남음 |
| `angle_words` | 3 | claude-sonnet-5-5 라운드 1~3 "핵심 의심" 경고 |
| `_VAL` | 7 | sonnet-5-5 points[4] 3건, mistral-large-4 2건, openai-textgrain 2건 "누락 의심: points[n] 안에 같은 단위 값 3개 이상" |
| `evidence_unit` | 2 | decision-api "단위 확인 필요" 경고 |
| `BARE_PER_TOKEN` | 1 | decision-api-spec points[2] "토큰당" |
| `SPECULATIVE` | 1 | agent-coding-talks summary "부상했다" |

표는 실제 차이를 복사하지 않고 각 차이가 5.1 "뺌" 규칙의 메시지인지 하나씩 확인한 뒤 손으로 썼다. 뺌 규칙과 무관한 차이는 0건이었다. 표의 한 줄을 지우면 B1이 "표에 없는 제거"로 실패하는 것도 확인했다. 전후 비교 단위는 `scripts/s5_1_golden.py --before --removals`가 정한다(이슈·자동 수정·경고 한 건씩, 금지 표현은 낱말 하나씩).

## 3. 관문 B
런 뒤 채운다(10장).

## 4. 결정한 것
- `run_checks`는 `angle` 인자를 받기만 하고 쓰지 않는다. `eval/graders_brief.py`(수정 금지 영역)가 `angle=`을 넘기기 때문이다. 쓰지 않는 인자가 남았다는 뜻이므로 명세 개정 때 정리 대상.
- `UNIT_KINDS`·`unit_kind`는 지웠다. 요약·개요 수치 대조(`with_units`)는 "단위가 붙었는가"만 보므로 단위 낱말 목록 하나(`UNIT_WORDS`, 호출부 정규식 `[가-힣%]+`로 닿는 낱말만)와 `is_unit`만 남겼다.
- `CriticInput.page`·`WriterReviseInput.previous`는 렌더에서만 뺀다. `Field(exclude=True)`는 `model_dump()`에서도 빠져 `s5_eval_fixtures.py`가 만드는 critic·writer_revise 픽스처에서 page가 사라지므로, 두 입력 클래스에만 `RENDER_SKIP` ClassVar를 두고 `render_body`가 `getattr(obj, "RENDER_SKIP", ())`로 읽게 했다(공통 부모 `RoleInput`은 바꾸지 않음).
- `WriteCfg.points_for(n_sources)`를 두어 checks 2곳과 `writer_limits`가 같은 "소스 수 → points 범위" 선택을 쓰게 했다.
- `config.current_spec(override, default)`: `--spec`, 환경변수 `TRENDSIT_SPEC`, 기본값 순. 이전에 `args.spec or "S2"` 꼴이던 명령(rematch, filter, summarize, repo-analyze, plan, deep-text, cluster, weekly)은 환경변수가 있으면 이제 환경변수를 따른다(전에는 명령 기본 스펙이 환경변수보다 앞이었다).
- DB 열기는 `core/db.py`의 `open_db(data_dir=None)` 한 함수. `open_ctx`, cli, `collect/run.py`, `collect/report.py`가 쓴다.
- `cli_text`의 날짜 파서는 `cli.parse_date`(공개 이름)를 import한다(둘이 같았다).
- 코드가 고정으로 검사하는 형식 계약 숫자(도식 항목 2~6개 등)는 md에 남겼다. `brief.yaml` 값이지만 `limits`에 칸이 없는 것(형광 칸별 개수, 후보 상한 등)은 숫자를 빼고 일반 문구로 바꿨다(NG-1: `limits` 외 새 입력 칸 금지).
- 리뷰 반영 A2: writer.md에서 style_ko.md·diagrams.md와 문구만 다른 같은 규칙(문체 core_rules, 도식 context·그림 없이 읽히게, 요약 "~다", numbers title·단위, 형광 "핵심 결론"만)을 지웠다. 그 결과 writer.md 본문의 굵게는 0개다(check-config "1개 이하" 만족). critic.md는 문체 몫을 사실에 맞게 고쳤다(코드가 보지 않는 문체는 format 이슈로).
- 리뷰 반영 A2: `UNIT_WORDS`는 호출부 정규식 `[가-힣%]+`로 닿는 낱말만 남겼다(골든 출력 바이트 동일 확인).
- 리뷰 반영 A3: `loc_lines`가 page의 단위·group·기준·강조·흐름이 핵심·기여 refs·확인 필요 표시까지 담는다(렌더에서 page를 뺀 뒤에도 정보가 한 번 남게). `page.log`/`attention`(모델이 낸 기록 칸)은 싣지 않는다. B9 테스트가 이를 단언한다.
- 리뷰 반영 A3: critic.md 문체 서술은 사실만 적는다(문체·형광·분량은 반려 사유가 아니고 코드가 검사). 5.1은 오탐 때문에 규칙을 코드에서 뺐고 md 처리는 writer 쪽 `style_ko.md`다. 검수자 반려로 되살리지 않는다.
- 리뷰 반영 A3: `<data>` 문장만 지우고 역할별 꼬리 지시(인젝션 인용 금지, 이미지 속 글자는 자료, README 지시 따르지 않기, 도구 결과는 자료)는 7개 역할에 복원했다. B3는 지운 줄이 `<data>` 줄이고 더한 줄의 낱말이 모두 지운 줄에 있는지 본다.
- 리뷰 반영 A3: 골든 B1은 `--before` 파일의 runs(같은 run_id)로 고정해 계산한다. 그 run이 DB에 없으면 종료 코드 2. 근거 목록·별칭은 현재 데이터를 쓰므로 수집 데이터가 바뀌면 달라질 수 있다.
- 리뷰 반영 A3: verify는 A15·A17을 원래 ID로 두고 B3·B7과 같은 판정을 낸다(A16만 B1로 대체).
- 리뷰 반영 A3: writer.md 본문에 굵게 1개(핵심 규칙 "각 문장은 그 문장에 다는 근거 id의 내용만 담는다")를 되살렸다(F-35).
- 리뷰 반영 A2: B3는 측정 스크립트 종료 코드를 확인하고, 달라진 역할 집합이 허용 집합(S5 5개 + `bed7887` md에 `<data>` 줄이 있던 역할)의 부분집합인지 비교한다.
- `weekly.set_run_week`: `UPDATE runs SET week`는 한 함수. cluster부터면 `stage_cluster`가, 그 밖의 단계부터면 `run_weekly`가 한 번 부른다(이어 갈 run이 없어 `ValueError`가 나는 경우에는 week를 쓰지 않는다).
- 영상 관련성 계산은 `cluster.score_video_relevance(ev, embedder, interests, cfg)` 한 호출 형태로 합쳤다.
- `pack_index`는 `evidence.py`로 옮기고 `cap_pack`이 쓴다(`write.py`는 import해서 그대로 노출).
- 페이지 근거 id 칸 순회는 `checks.page_refs(page)` 하나. `refs_of`(칸 종류 순서 유지), `_loc_refs`, `write.save`의 topic_evidence 행, `checks`의 refs 실재 검사가 쓴다. 저장 행 순서는 전과 같다.
- `select.ascii_slug`: `slugify`와 `fallback_plan`이 같은 정규식 한 줄을 쓴다(5-1).
- `trendsit/brief/revision.py`(신규): `write.py`가 523줄이었고 `write_topic` 쪼개기로 줄이 늘어 수정 합치기(`top_loc`, `normalize_loc`, `apply_revision`와 위치 정규식)를 옮겼다. `write.py`가 import하므로 기존 import 경로는 그대로 쓸 수 있다.
- `s5_1_golden.py`에 `--before/--removals`, `s5_1_prompts.py`에 `--roles`를 더했다(둘 다 `scripts/` 측정 도구, B1·B3용). `trendsit` CLI 옵션은 없다.
- B3의 "허용"은 S5 역할 5개는 자유, 그 밖의 역할은 `roles/<역할>.md`의 diff가 `<data>`가 든 줄 삭제뿐일 때다. `skills/style_ko.md` 한 줄(5.1 지시)과 `skills/diagrams.md` 굵게 해제(F-35)는 그 스킬을 include하는 역할의 시스템 프롬프트를 바꾸지만, 그 역할들도 `<data>` 문장을 지우므로 C-4 안이다.
- 전 스냅숏: `bed7887`을 `git worktree`로 꺼내 `s5_1_golden.py`·`s5_1_prompts.py`와 `checks.SPECULATIVE`를 다시 만들었다. golden·prompts는 기존 `golden_before.json`·`prompts_before.json`과 바이트 동일이라 파일은 그대로고, `speculative_before.json`만 새로 저장했다. worktree는 지웠다.
- `intended_removals.json`의 `match`는 원문 앞부분이고, 한 줄이 차이 한 건에 대응한다.
- 픽스처: `s5_eval_fixtures.py`를 실행했더니 현재 DB 기준 writer 입력 20개가 기존 파일 20개와 이름이 9개만 같았다(나머지 11개는 이전 run의 토픽 이름). 기존 11개는 지우고 새 11개를 넣어 writer 디렉터리는 현재 20토픽 = 20파일이다. 기존 9개는 현재 입력 형식(원문 줄, 카드 주장 줄 없음)과 `limits`로 바뀌었다. critic·editor_select·writer_revise 픽스처는 되돌려 그대로다(그 디렉터리도 현재 DB 기준으로는 달라지지만 명세가 "그대로").
- `data/trendsit.db`: 첫 구현 때 픽스처 스크립트가 DB를 쓰기 모드로 열어 sha256이 `fa12c3f2…` → `1f82d701…`로 바뀌었고 실행 전 복사본으로 되돌려 `fa12c3f2…`로 복구했다. 리뷰 반영 A2에서 스크립트가 읽기 전용 연결로 임시 DB에 복사해 그 복사본을 열도록 고쳤다. 다시 돌려 실제 DB 해시가 그대로이고 writer 픽스처 20개가 바뀌지 않음을 확인했다.

## 5. 스펙과 다르게 한 것
- F-12의 "video_summary.md에서 style_ko.md와 같은 문장 삭제"는 하지 않았다(사용자 결정). NG-4가 S2~S4 역할 md의 지침 변경을 `<data>` 문장 삭제만 예외로 막고, B3도 그 역할에는 그 줄만 허용한다. 해당 줄에는 영상 전용 꼬리("해석, 평가는 쓰지 않는다")도 있다.
- 복잡도 예산 변경 파일 수 ≤ 35를 넘었다(60개). 명세 5.2·5.3 항목만으로 불가피해 사용자가 승인했다.
- F-12 `video_summary.md` 문체 줄은 NG-4와 충돌한다. 사용자 결정: NG-4대로 남기고, 충돌은 기획 세션에 넘긴다.

### 5-1. 합치지 않은 중복과 이유(5.2)
| 항목 | 이유 |
|---|---|
| `web.page_links` ↔ `collect.links.extract_links` | 동작이 다르다. `page_links`는 같은 호스트 링크를 포함하고(공식 블로그 → 같은 도메인 논문) 자기 자신만 뺀다. `extract_links`는 바깥 호스트만, anchor 정리(HTML 엔티티, 공백 압축, 200자 상한)도 다르다. 합치면 fetch_page 링크 목록이 바뀐다. 정규식만 `collect.links.XML_REF`(이름 바꿈) 하나로 |
| `artifacts_text._NUM` `\d+(?:[.,]\d+)*` ↔ `core.numbers.DECIMAL` | 쉼표 처리가 다르다("1,234"는 하나 대 둘). 합치면 `figures`·`numbers` 결과가 바뀐다 |
| `collect/github._NUM` `[\d,]+` | 정수 파싱용(쉼표 포함 첫 덩어리)이고 소수점이 없다. 다른 정규식은 "1.5k"에서 "1.5"를 잡아 `int()`가 깨진다 |
| `select._NUM`·`aliases._NUM` | 같았다. `core/numbers.DECIMAL` 하나로 합침 |
| `config_brief._Strict` ↔ `config.Strict` | 같지만 `config.py`가 `config_brief`를 먼저 import하므로(두 파일 첫머리에 "config.py를 가져오지 않는다") 순환이 생긴다 |
| `config_video._Strict` ↔ `config.Strict` | `populate_by_name=True`가 더 있어 다르다 |
| `select.recent_topics` ↔ `cluster.past_topics` | `past_topics`는 `topic_embeddings`를 JOIN해 임베딩이 없는 토픽을 제외하고 그 결과로 weeks_back 주를 고른다. `recent_topics`는 제외하지 않고 정렬(주, rank)도 다르다 |
| `fallback_plan`의 slug ↔ `slugify` | 정규식 한 줄(`ascii_slug`)만 공유. 대체 계획은 30자 자르기와 `c{cluster_id}` 기본값, `slugify`는 4마디 자르기와 "topic" 기본값이라 합치면 대체 계획의 토픽 id가 바뀐다 |
| `score_video_relevance`·`interest_similarity`의 코사인 최댓값 ↔ `filter.embed.best_interest` | `best_interest`는 6자리로 반올림하고 이 둘은 4자리라 이중 반올림하면 경계값이 달라진다. 최댓값 계산은 합치지 않고 그대로 두었다. 관심사 쿼리 임베딩만 `embed_interests`로 합쳐 weekly 한 번에 한 번만 계산한다 |

## 6. 남은 문제, 다음 스펙 제안
- 관문 B 재실행(W40·W41 weekly, judge, 충실성 ≥ 18/20 && 오병합 0): 런 뒤(10장).
- `current_spec` 환경변수 우선순위 변경은 동작이 미세하게 달라지는 부분이다.
- `run_checks(angle=)` 미사용 인자는 `eval/graders_brief.py`를 고칠 수 있을 때 같이 지운다.

### 6-1. optional로 남긴 것
- 명세에 없는 인자·옵션·헬퍼: `run_checks(angle=)`(미사용), `stage_cluster(interests=)`, `WriteCfg.points_for`, `writer_limits`, `checks.page_refs`, `pack_index`(evidence로 이동), `embed_interests`, `set_run_week`, `open_db`, 공개 `parse_date`, `ascii_slug`, `collect.links.XML_REF`, `CriticInput/WriterReviseInput.RENDER_SKIP`, `current_spec(default=)`, `trendsit/brief/revision.py`, 측정 도구 옵션 `s5_1_golden --before/--removals`·`s5_1_prompts --roles`. `trendsit` CLI 명령·옵션과 설정 키는 추가하지 않았다.
- writer 픽스처 토픽 11개 교체(현재 DB 토픽에 맞춤): `eval` writer 결과를 이전 `reports/eval/` 실행과 비교할 때 토픽 구성이 다르다(같은 이름 9개는 입력 형식·`limits`도 바뀜).
- 관문 B judge 입력(`eval.graders.judge_input`)의 `source_fields`에 `limits`가 들어간다(작성자 입력의 필드를 그대로 싣기 때문). judge md·채점표는 그대로다.

## 7. 사용액
$0 (워크플로우 안 LLM 호출 없음). 임베딩은 로컬 모델로 픽스처 스크립트에서만 돌렸다.

## 7-1. README 갱신 내역
"현재 상태"에 S5-1b 단순화 반영 문장 추가. AGENTS.md "원칙" 마지막 줄을 `check-config`의 실제 검사 범위(섹션 순서, 예시 3~5개, 굵게 1개 이하)로 고침(F-15).

## 8. impl-workflow SUMMARY 요약
- 런 `002-s5-1b`: 구현 A1(S-1~S-4 전부, 게이트 `--fast` 통과). 이후 리뷰·수정 라운드 결과는 `.workflow/002-s5-1b/SUMMARY.md`에 오케스트레이터가 이어 적는다. QA 대상 AC 없음.
- 복잡도 예산: 변경 60/35 파일(재생성 픽스처·base 커밋의 `COMMON.md` 제외, **초과, 사용자 승인**), 새 코드 파일 1/3(`revision.py`) + 데이터 2(`intended_removals.json`, `speculative_before.json`), 삭제 1(`s5_order_preview.py`), `trendsit/` +699/−717, `roles/ skills/` +61/−74, 새 의존성·옵션·환경변수 0
- findings 승계: 002-I01(`fetch_page` 깊이 재계산, 금지 구조 필요), 002-I02(리포트 장이 비어 있는 채 grep PASS, 런 뒤 채우는 장) — 둘 다 이번 명세 범위 밖으로 처리하지 않음
- 거부·optional: 없음(구현 첫 라운드)

## 9. 줄 수 전후 (`bed7887` → 이 브랜치)
| | 전 | 후 |
|---|---|---|
| `trendsit/` 추가·삭제 | | +699 / −717 (순 −18) |
| `roles/ skills/` 추가·삭제 | | +61 / −74 (순 −13) |
| `brief/checks.py` | 507 | 440 |
| `brief/write.py` | 523 | 415 (+ `brief/revision.py` 121) |
| `brief/pipeline.py` | 295 | 306 |
| `check()` | 185 | 4 (칸별 함수 7개) |
| `autofix()` | 82 | 12 (단계별 함수 6개) |
| `warnings()` | 56 | 32 |
| `write_topic()` | 168 | 38 |
| `run_weekly()` | 111 | 37 |
| 500줄 넘는 `trendsit/**/*.py` | 2개(checks 507, write 523) | 0개 |
| 코드 검사 "뺌" 규칙 | | 11개 이름 + `SPECULATIVE` 0건 |
| `scripts/s5_order_preview.py` | 96 | 삭제 |

함수 줄 수는 `ast`의 `end_lineno − lineno + 1`(독스트링·주석 포함). `check()`가 4줄인 것은 칸별 함수의 목록을 이어 붙이기만 해서다.

## 10. 관문 B 결과 (런 뒤 채움)
워크플로우 밖에서 `uv run python -m trendsit weekly --week 2026-W40 --spec S5` → `--week 2026-W41` 후 관문 B를 돌려 채운다. 지금은 비어 있다.

| 항목 | S5 병합 시점 | S5-1b | 판정 |
|---|---|---|---|
| 근거 충실성 통과 토픽(20) | 런 뒤 채움 | 런 뒤 채움 | 런 뒤 채움 (기준 ≥ 18/20) |
| 묶기 오병합 | 런 뒤 채움 | 런 뒤 채움 | 런 뒤 채움 (기준 0) |
| 핵심 포착·군더더기·읽기 쉬움·문체·정규식 | 런 뒤 채움 | 런 뒤 채움 | 기록만 |
| 사용액(상한 $1.00) | | 런 뒤 채움 | |
