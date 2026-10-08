# S3 리포트: 깊게 보기 (3c 레포 분석가 → 3a 편집장 계획 → 3b 글 분석가)

> 진행 체크리스트(COMMON 8장). 상태: 클라우드 구현 끝 + 클라우드 관문 B(픽스처 범위) 끝 + **맥 확인(2026-10-08)**: 실제 GitHub(토큰), 실제 한 주(2026-W41, 2026-10-04 계획)로 관문 B 세 역할 통과(judge 잠정). 라벨은 리뷰 세션 독립 채점 + 사용자 불일치 판정 방식으로 바뀌어 파일만 만들어 둠.
> 맥 실행 환경: M1 Max, 파이썬 3.12.14, `GITHUB_TOKEN`(fine-grained, 공개 저장소 읽기 전용, `~/.config/trendsit/.env`). 토큰 값이 저장소·data·로그에 없음을 값 대조로 확인
> **클라우드 관문 B의 범위**: editor_plan 2건, text_analyst 6건의 픽스처를 녹화 응답으로 만든 개발 DB(글 15건 1차 요약, 영상 1편, 트렌딩 11행)에서 뽑아 돌렸다. 스펙 수(영상 10편 계획, 글 10건)에 못 미치고 실제 한 주가 아니다. repo_analyst는 GitHub API가 이 저장소 밖으로 막혀 돌리지 않았다. 실제 한 주 픽스처, 검증 산출물(`S3_traces/`, `S3_plan.md`), 사람 라벨은 맥 몫. judge 판정은 모두 **잠정**
> 실행 환경(두 번째 클라우드 세션): 키 있음, openrouter.ai·export.arxiv.org·일반 원문 사이트 열림. github.com(레포 페이지), 이 저장소 밖 GitHub API, news.hada.io는 막힘
> 실행 환경(첫 클라우드 세션): 클라우드(리눅스, 파이썬 3.13), `OPENROUTER_API_KEY` 없음. GitHub API는 이 저장소만, github.com·export.arxiv.org·원문 사이트는 막힘.

## 진행 체크리스트
- [x] M3 safe_fetch 연결 주소 고정(DNS 재바인딩)
- [x] 공통 코어: 입력별 허용 도구·깊이 상한, 항목당 도구 호출 상한, 도구 자원, 시작 문서 지정
- [x] 3c `repo_analyst`: 스키마·enforce, GitHub 도구 4개 + search_items, 과열 규칙, 규칙 기반 큐, `repo-analyze`, 채점(도구 효율)
- [x] 3a `editor_plan`: 스키마(CONTRACTS 1장), validate_plan, 대체 계획, `plan run/show/agreement`, 산출물·라벨 생성기, 채점
- [x] 3b `text_analyst`: 스키마·enforce, fetch_page·read_more·arxiv, 원본 추적 지침, `deep text`, 채점
- [x] `scripts/verify_s3.sh`
- [x] 관문 B editor_plan(픽스처 2건), text_analyst(픽스처 6건): 두 번째 클라우드 세션, 잠정 통과
- [x] 관문 B repo_analyst(맥, 반복 1), editor_plan·text_analyst 실제 한 주 픽스처(맥), 검증 산출물(`S3_traces/`, `S3_plan.md`), 라벨 파일(맥)
- [x] 설계 결정 Q3(실제 녹화), Q4(픽스처), Q5(라벨 경로) 반영(맥)
- [ ] 라벨 일치율(리뷰 세션 독립 채점 + 사용자 불일치 판정, 영상 mode는 사용자)

## 1. 한 줄 요약
편집장이 세 채널 후보와 예산으로 계획을 세우면(모델 실패 시 규칙 기반 계획), 코드가 예산·깊이·id를 검증해 자르고, 레포 분석가가 GitHub 도구로 관련성·뜨는 이유·과열을, 글 분석가가 원문 링크를 따라 원본을 찾아 수치를 대조한다. 도구 사용 범위와 횟수, 문서 깊이, 근거 없는 판정은 코드가 막는다.

## 2. 관문 A
**맥(2026-10-08, 결정 반영 뒤 마지막 커밋)**: `verify_s2.sh`·`verify_s3.sh` 전부 PASS(A1 포함, FAIL 0), pytest 273 passed + 1 skipped(embed 없이), `uv run --extra embed pytest -q` 274 passed. 중간에 verify_s0 A9(키 문자열 검사)가 테스트의 가짜 토큰 문자열을 잡아 테스트에서 이어 붙여 만들도록 고침(검사 규칙은 그대로)

`bash scripts/verify_s3.sh` (2026-10-08, 두 번째 클라우드 세션, 키 있음)
```
PASS A1 verify_s0.sh 10개, verify_s1.sh 24개 전부 PASS
PASS A2 ruff 0, pytest 258 passed, 1 skipped in 13.33s
PASS A3 deep.yaml이 check-config 통과 + 잘못된 값(깊이 순서, 범위)이 경로를 짚어 실패 (1 passed in 0.16s)
PASS A4 S3 역할 md 3개(repo_analyst, editor_plan, text_analyst)와 채점표, 원본 추적 지침이 역할 md 검사 통과, 예시 3개 (1 passed, 28 deselected in 0.11s)
PASS M3 safe_fetch 연결 주소 고정: 검사한 IP로만 연결(Host는 원래 이름), 리다이렉트마다 다시 고정, 검사 안 한 이름은 거부 (5 passed in 0.21s)
PASS A9 에이전트 오프라인: 녹화 픽스처로 3c(GitHub 응답), 3b(GeekNews 원문 페이지) 루프가 끝까지(모의 LLM) (4 passed, 20 deselected in 0.49s)
PASS A10 깊이·도구 상한: max_depth별 허용 도구(3c), 깊이 상한 밖·parent 없는 읽기 거부(3b), 도구 호출 6회 상한 (7 passed, 21 deselected in 0.62s)
PASS A11 계획 검증: 예산 초과 꼬리 자르기, max_depth 자르기, 없는 id 제거, 대체 계획 (7 passed, 7 deselected in 0.27s)
PASS A12 계약: video_queue.json이 VideoQueueItem으로 읽히고 plan show --video-queue 출력이 같은 모양 (2 passed, 12 deselected in 0.28s)
PASS A13 마이그레이션 대역: 이 묶음 번호 [10, 11, 12, 13], 대역 밖 [], 등록 전체 [1, 2, 10, 11, 12, 13]
PASS A14 README(빠른 시작, 성과 행), DEVELOPMENT 명령표, S3 리포트, 맥 확인 목록
```
- A1까지 전부 PASS(첫 클라우드 세션 때는 키가 없어 A1만 FAIL)

## 3. 관문 B
**맥(2026-10-08)**: 응답 캐시가 없어 클라우드 `dev-` 픽스처도 새로 생성·채점. judge는 모두 **잠정**(라벨 대기)

| 역할 | 통과 기준 | 맥 결과 |
|---|---|---|
| repo_analyst | judge Q1~Q3 각 80% + 관련 낮은 레포 80% 이상 커밋 도구 없이 finish + 평균 도구 호출 4회 이하 | **통과(반복 1)**: 2026-W41 트렌딩 10개(키워드 통과 5, 걸러짐 4 + 경계 tilelang). 코드 10/10, Q1~Q3 각 10/10, 평균 도구 호출 3.4, 관련 낮음 4/5 얕게 끝냄, 도구 오류 0. `reports/eval/repo_analyst_generate_20261008-182928.json`, $0.0350 |
| editor_plan | 코드 채점 전부 + judge Q1~Q2 80% + 영상 mode 동의율 80% | **통과(반복 없음)**: 픽스처 3건(실제 2026-10-04: 영상 17, 글 158, 레포 4 + dev 2). 코드 3/3, Q1·Q2 각 3/3, 모델 일치율 attention 2/3(dev-10-06 레포 10/10이 80% 초과). 실제 계획: 영상 5편 whisper(84분), 글 5, 레포 4. mode 동의율은 사용자 라벨 대기(`editor_plan_mode.csv` 17행) |
| text_analyst | enforce 전 근거 없는 confirmed/differs 0~1건 + judge Q1~Q3 각 80% | **통과(반복 1)**: 픽스처 16건(실제 한 주 10 + dev 6). 근거 없는 판정 0, 코드 16/16, Q1~Q3 각 16/16, 원본 확보 14/16(깊이 2: 13, 3: 1. 못 찾음: it240 X 트윗 robots 차단, it959). dev-it5·it21은 github.com이 열려 원본 문장 대조 6/6(클라우드 4/6). `…-191228.json`, $0.1511 |

**repo_analyst 반복 기록**

| 회차 | 실행 | 바꾼 것 | 결과 | 원인 |
|---|---|---|---|---|
| 0 | `…-164718` | - | 코드 4/10 | evidence의 tool 칸에 입력 칸 이름(trending, hype)을 적음 6건(지시를 어김) |
| (무효) | `…-165334` | md 문구 | 코드 10/10, Q 10/10이지만 **무효** | GitHub 비인증 한도 소진으로 도구 41회 중 33회 HTTP 403(아래 6장 사례). 반복 횟수에 넣지 않음 |
| 1 | `…-182928` | md 문구: tool 칸은 도구 이름만, 입력 수치는 signal_reason에 | **통과** | 토큰으로 같은 md 재실행 |

**text_analyst 반복 기록**

| 회차 | 실행 | 바꾼 것 | 결과 | 원인 |
|---|---|---|---|---|
| 0 | `…-185127` | - | 근거 없는 판정 7 | 5건(dev-it5)은 평가 버그: `run_eval`이 `fetched_pages`를 지우기만 해 github_repo가 첫 호출이면 README가 가져온 페이지로 등록되지 않음 → 공통 코어 수정(`b09261f`, 개선 횟수 아님) |
| 0' | `…-185514` | 평가 버그 수정 | 근거 없는 판정 2(it201) | 모델이 Nature 본문의 `AF3’s`(U+2019)를 `AF3's`로 옮겨 인용 대조 실패(지시를 어김/모델 한계) |
| 1 | `…-191228` | md 문구: 따옴표·대시 모양까지 그대로 | **통과**(0건) | |

- 이전 클라우드 세션 기록(픽스처 범위)은 아래에 그대로 둔다

### 클라우드 기록 (픽스처 범위만)
| 역할 | 통과 기준 | 결과 |
|---|---|---|
| repo_analyst | judge Q1~Q3 각 80% + 관련 낮은 레포 80% 이상 커밋 도구 없이 finish + 평균 도구 호출 4회 이하 | **실행 안 함**: 도구(커밋·기여자·릴리스·README)가 GitHub API를 부르는데 이 클라우드는 이 저장소 밖이 403. 녹화는 2개 레포뿐이고 커밋 등은 합성. 맥 확인 후 |
| editor_plan | 코드 채점 전부 + judge Q1~Q2 80% + 영상 mode 동의율 80% | 픽스처 2건(개발 DB 2026-10-04, 10-06): 코드 2/2, Q1 2/2, Q2 2/2 **잠정 통과**($0.0083, 재기록 $0, `reports/eval/editor_plan_generate_20261008-122719.json`). 영상 1편뿐이라 mode 동의율은 맥 |
| text_analyst | enforce 전 근거 없는 confirmed/differs 0~1건 + judge Q1~Q3 각 80% | 픽스처 6건: 근거 없는 판정 0건, 코드 6/6, Q1~Q3 각 6/6 **잠정 통과**($0.0499 + 재기록 $0.0043, `reports/eval/text_analyst_generate_20261008-122802.json`). `원본 확보` 집계는 6/6이지만 it5·it21은 github.com 403으로 공식 사이트·문서를 대신 열어 인용 0, 판정 전부 not_found다. 원본 문장과 실제로 대조한 것은 **4/6**. 깊이 2에서 6건 |

**두 번째 클라우드 세션 픽스처(새로 추가, 기존 없음)**
- 개발 DB: S1 녹화 응답 5묶음(window, bf_aitimes, bf_geeknews, bf_simonw, bf_youtube)을 테스트와 같은 재생 방식으로 `data/`에 수집 → `rematch` → `filter --embedder real` → `summarize`(15건, $0.0213). 실제 한 주가 아니다
- `eval/fixtures/editor_plan/dev-2026-10-04.json`(영상 1, 글 3, 레포 0), `dev-2026-10-06.json`(영상 1, 글 5, 레포 11). `plan run --fixture … --no-hype`(과열 검사는 GitHub API라 끔). 10-07도 만들었으나 10-06과 날짜 말고 같아 지움
- `eval/fixtures/text_analyst/dev-it{5,6,20,21,22,23}.json`: 개발 DB에서 needs_original=true인 6건 전부, `deep text --item N --fixtures`. 원본 후보 접속: it5·it21은 github.com이 403이라 공식 사이트·문서로 대신 확인(not_found 처리), it20은 원본 블로그 열림, it6은 블로그 + arxiv 초록
- 반복 개선 없음(두 역할 모두 첫 실행에서 문턱값 통과). 첫 실행 원자료 JSON(`…-120942`, `…-121347`)은 픽스처 이름을 `dev-`로 바꾼 뒤 다시 기록하면서 지웠다(커밋 전). 다시 기록한 결과는 같고, 첫 실행 비용 $0.0083, $0.0499는 `cost --spec S3` 실행 기록 기준. `S3_quality.md`의 비용 칸($0, $0.0043)은 다시 기록한 실행 값이다
- `S3_quality.md`는 자동 생성이라 범위 문구가 없다. 거기의 "문턱값: 통과"는 개발 DB 픽스처 2건·6건(스펙 각 10건) 기준이다. editor_plan 장의 "`editor_plan.csv`를 채우면 일치율을 잰다" 안내는 질문 Q5 때문에 지금은 맞지 않는다 라벨 `eval/labels/text_analyst.csv` 6행 만들어 둠(빈칸)
- `eval editor_plan --label`은 judge 라벨을 `eval/labels/editor_plan.csv`에 쓰는데, 같은 경로를 `plan --labels`(영상 mode 동의 라벨, 스펙 지정)도 쓴다. 서로 덮어써서 judge 라벨은 만들지 않았다(질문 파일 Q5)

## 3c 레포 분석가

### 결정한 것
- 과열 규칙 상수(`deep/repo_agent.py`): `HYPE_STARS_WEEK = 1000`(7일 별 증가가 이 이상이면 커밋 수를 셈), `HYPE_COMMITS_7D = 0`(그 이하면 no_commits + signal check 고정), `SINGLE_CONTRIBUTOR = 1`, awesome 목록은 이름이나 README 앞 300자로. 커밋은 급증일 때만 세고(API 1회), 기여자는 항상 셈(API 1회). API 실패는 규칙 미적용 + note
- 규칙 기반 큐(3a 전): 키워드에 걸린 트렌딩(이번 주 별 순) + 그 주 추적 레포 릴리스, 깊이 2
- 깊이 3은 2와 같은 도구(연결 문서 도구는 이후)
- 한 줄 설명은 `repo_oneliners`(입력 해시가 같으면 재사용), 없으면 repo_oneliner 실행. 카드 저장 때 코드가 붙임
- `search_items`는 입력 week_items(이번 주 v1 카드 제목 최대 30, relevance 순)와 그 카드의 요약·엔티티에서 찾음
- enforce: 입력에 없는 글 id 삭제, 코드 과열 플래그 유지, force_check면 check, check면 attention, evidence 없이 why_trending이면 attention
- 대체 출력: 관련 false, signal은 숫자 규칙(과열이면 check, 아니면 trending), attention

### 스펙과 다르게 한 것
- 오프라인 테스트의 커밋·기여자·릴리스 응답은 합성이다(`tests/fixtures/http/repo_tools/meta.json`에 표시). 클라우드의 GitHub API가 이 저장소 밖을 막아 녹화하지 못했다. 레포 정보와 README는 S1 실제 녹화를 복사

## 3a 편집장 계획

### 결정한 것
- 입력 범위: day 포함 최근 `lookback_days`(7)일의 영상과 needs_original 글(v2가 아직 없는 것), 그 주의 레포 후보(최대 20, 과열 규칙 포함)
- 예산 계산: 영상 분 = skip 0, 구간이 있으면 구간, 없으면 min(길이, 60분). 슬라이드 프레임 = 슬라이드 영상 수 × `frames_per_slide_video`(20). 글·레포는 개수
- validate_plan 순서: 없는 id·중복 제거 → 글 깊이를 min(max_text_depth, 4)로 → 큐 앞에서부터 담아 예산을 넘는 항목은 건너뜀(영상은 분·슬라이드 수·프레임을 함께 봄, 글·레포는 개수로 뒤를 자름) → 잘린 것을 log에 → 예산의 80%를 넘으면 attention
- 영상을 자를 때 mode를 낮추지 않고 빼기만 함(스펙 "꼬리를 잘라 냄"). 슬라이드 예산만 넘는 영상을 whisper로 낮추는 선택지는 S4 결과를 본 뒤 정할 일(다음 스펙 제안)
- 대체 계획도 validate_plan을 거침(예산 초과 0). log는 "규칙 기반 대체 계획(이유)", attention true
- 모델 실패(스키마 3회, 예산, 제공사 오류)면 대체 계획을 저장하고 실행 기록에 남김. 클라우드에서 개발 DB로 돌려 본 결과: 키가 없어 대체 계획(영상 4편 whisper, 레포 10개, 글 0건)

## 3b 글 분석가

### 결정한 것
- 원래 글 = 깊이 1(1차 요약 때 이미 읽음), 그 링크 = 깊이 2. 항목별 상한은 계획의 max_depth와 전체 4 중 작은 값
- 문서 id는 정규화 URL. `fetch_page`의 링크(추출한 본문 링크 전부)가 다음 깊이로 이어짐
- `arxiv`와 `github_repo`는 깊이를 세지 않는다(검색·API, 링크 추적이 아님). 대신 도구 호출 6회 상한 안
- 인용 근거 범위 = 이번 실행(항목)에서 연 페이지 본문 + arxiv 초록 + README. 항목마다, eval에서는 픽스처마다 비움
- 확인할 것 = v1의 수치(먼저) → 주장, 번호 1부터
- enforce: 연 페이지에 없는 인용 삭제 → 근거 없는 confirmed/differs는 not_found → 그 인용을 가리키는 수치·주장 정리 → trail 밖 origin 지움 → differs면 attention
- 대체 출력: v1 요약 유지, 모두 not_found, log "원본 찾지 못함", attention false
- `render_page`, `web_search`는 만들지 않음(범위 밖)

### 스펙과 다르게 한 것
- 오프라인 테스트는 S1 녹화의 GeekNews 원문 페이지(danbom425.tistory.com/113) 하나로 세 경우(깊이 2에서 찾음 / 계획 깊이 1이라 못 찾음 / parent 없이 읽기 함정)를 만들었다. 그 페이지의 본문에서 추출되는 링크가 없어 "깊이 상한 밖 문서"는 계획 깊이 1로 원문(깊이 2)을 막는 경우로, 함정은 "parent 없이 읽기"와 "아직 읽지 않은 문서를 parent로 대기" 거부로 확인했다

## 결정 반영 (설계 결정, `docs/handoff/S2S3_DECISIONS.md`)
| 결정 | 반영 위치 | 커밋 |
|---|---|---|
| Q1(S3 역할) | `RepoCard.ENFORCED_FIELDS = (signal, hype_flags, attention)`, `CollectionPlan`·`ItemCardV2` = attention. 공통 코어는 S2 리포트 결정 반영 | `f20d8d2`, `aeac887` |
| Q1 결과 | 모델 일치율: repo_analyst signal·hype_flags·attention 각 10/10, editor_plan attention 2/3, text_analyst attention 16/16 | - |
| Q2 | 코드 세션 할 일 없음(환경 설정은 설계 세션·사용자) | - |
| Q3 | `scripts/record_repo_tools.py`(새), `tests/fixtures/http/repo_tools`에 NVIDIA/OpenShell(활발)·tile-ai/tilelang(릴리스)·pablostanley/yoinks(작은 개인) 각 5개 응답 추가(`recorded: true`), 합성 5개 유지·기대값 미변경, `test_recorded_github_responses_normal_path`. 녹화에서 본 형식 차이: 매 커밋 갱신되는 `dev` 프리릴리스가 목록 맨 앞에 오고 published_at은 처음 날짜(2026-03-18) → `releases` 도구 출력에 `prerelease` 칸. 빈 레포 409 같은 오류 형식은 이번 녹화에 없었다 | `7332d72` |
| Q3 비밀 | 첫 녹화는 토큰 없이. 토큰 도입 뒤 녹화 스크립트 2개가 저장 전 비밀 값 지우기, 요청 헤더 미저장. `tests/test_secret_safety.py`(녹화에 Authorization 헤더 형태·토큰 형태·.env 값 없음, index 허용 칸만, 리다이렉트), `test_github_token_not_persisted_or_sent_to_llm`. 본문 산문의 "authorization" 단어 2곳(S1 녹화 기사, OpenShell 커밋 메시지)은 비밀이 아니라 그대로 | `e3ec37f` |
| Q4 | repo_analyst 10(2026-W41), editor_plan 1(실제 2026-10-04, 영상 17편), text_analyst 10(계획 큐 5 + 수동 5: 933, 201, 972, 959, 240). `dev-` 픽스처 그대로 | `51f5a95` 외 |
| Q5 | `cli_text.PLAN_LABELS = eval/labels/editor_plan_mode.csv`, judge 라벨은 `editor_plan.csv`. `docs/DEVELOPMENT.md`, 맥 확인 목록 명령, `test_mode_labels_and_judge_labels_are_separate_files` | `6665044` |
| Q7 | S3 상한 2.00 그대로, 주석만. 합계 $0.561 | `90c4f74` |

## 4. 공통 코어 수정
| 커밋 | 파일 | 내용 |
|---|---|---|
| `3838b77` | `core/agent.py`, `role.py`, `artifacts.py`, `context.py` | 입력별 허용 도구·깊이(`RoleInput.tool_names/depth_limit`), `max_tool_calls`, `AgentState.ctx·inp·extras`, `Ctx.resources` |
| `42e68d0` | `core/artifacts.py`, `agent.py` | 시작 문서 지정(`RoleInput.depth_seed`) |
| `c72908a`(3c 커밋 안) | `eval/run_eval.py` | 도구 에이전트의 픽스처별 도구 호출 경로 기록 |
| `23cfb17`(3b 커밋 안) | `core/artifacts.py`, `eval/run_eval.py` | 반쯤 읽힌 스키마 모듈을 오류로, 픽스처마다 연 페이지 기록 비움 |
| 리뷰 반영 커밋 | `core/artifacts.py`, `agent.py` | 스펙별 스키마 자기 등록(`register_schemas`), 입력별 도구 호출 상한(`tool_call_limit`) |
- `c72908a`, `23cfb17`은 기능 커밋 안에 섞였다(COMMON 9장은 별도 커밋). 다음부터 분리
| `aeac887`(맥, 별도) | `core/artifacts.py`, `eval/graders.py`, `eval/run_eval.py`, `cli.py` | 설계 결정 Q1 채점 두 갈래(S2 리포트 결정 반영) |
| `b09261f`(맥, 별도) | `eval/run_eval.py` | 평가도 항목마다 `fetched_pages`·`page_depth`를 새로(운영과 같게). 테스트 `test_eval_registers_github_readme_as_fetched_page` |
| `e3ec37f`(맥) | `core/config.py`, `collect/fetch.py`, 녹화 스크립트 2개 | 녹화 저장 전 비밀 값 지우기(`redact_secrets`), 다른 호스트 리다이렉트에 Authorization 안 넘김 |

## 5. 마이그레이션
| 번호 | 단계 | 테이블 |
|---|---|---|
| 10 | 2a | item_embeddings, item_relevance, item_same_as |
| 11 | 2b | item_cards(version 1·2) |
| 12 | 3c | repo_cards, repo_oneliners |
| 13 | 3a | plans |

## 6. 남은 문제, 다음 스펙 제안
- **(지적, 리뷰 때 결정) 도구가 전부 실패해도 관문 B가 통과한 사례**: repo_analyst 무효 실행(`reports/eval/repo_analyst_generate_20261008-165334.json`). GitHub 비인증 한도 소진으로 GitHub 도구 41회 중 33회가 HTTP 403(성공은 search_items 8회뿐)이었는데 **코드 10/10, judge Q1~Q3 각 10/10**으로 통과 판정이 났다. 모델은 "막혔을 때" 지시대로 10개 모두 attention=true, why_trending 빈칸, evidence에 "github_repo, releases, … 모두 HTTP 403으로 실패"를 적었고 relevant·signal은 입력(트렌딩 수치, 설명)만으로 정했다. judge는 "403이라 why_trending을 비운 처리가 규칙에 부합"으로 pass. 지금 채점은 "실패를 정직하게 적었는가"만 보고 "근거를 실제로 얻었는가"는 보지 않는다. 코드 규칙 후보(지금은 넣지 않음): 이 항목의 GitHub 도구 호출이 전부 오류면 attention 고정 + 카드 내용(relevant, signal) 무효 표시, 평가에서는 도구 오류율이 높은 실행을 무효로. 리뷰 세션 결정 대기
- 평가 실행 경로와 운영 경로의 자원 초기화가 달랐던 문제(`b09261f`로 고침)는 클라우드에서 github.com이 막혀 드러나지 않았다. 도구 결과를 근거로 등록하는 다른 경로(arxiv 등)도 평가·운영이 같은 초기화를 쓰는지 리뷰 때 함께 볼 것
- 인용 대조의 따옴표 모양: 모델이 ’를 '로 옮기는 일이 반복되면(text_analyst 반복 1로 이번에는 0건) enforce의 공백 정리에 따옴표·대시 정규화를 더할지 설계 세션 판단. 채점·enforce 규칙 변경이라 손대지 않음
- it982 원본이 공식 발표가 아니라 언론(thenewstack.io)인데 judge Q1 pass. 라벨 비교 때 확인할 것
- 라벨 일치율: 리뷰 세션 독립 채점 + 사용자 불일치 판정(item_card, repo_analyst, editor_plan judge, text_analyst), 영상 mode는 사용자
- 다음 스펙(S5) 제안: 유사 쌍 상위 30(맥 실행 뒤 `reports/S2_filter/README.md`)으로 묶기 기준, ItemCard 중 묶기에 쓸 칸(entities, keywords, claims), 원본 깊이 분포로 기본 깊이 결정
- 슬라이드 예산만 넘는 영상을 빼지 않고 whisper로 낮출지(S4 결과 보고)

## 7. 사용액
| 구분 | S3 사용액 |
|---|---|
| 클라우드(첫 세션) | $0(LLM 호출 없음, 키 없음) |
| 클라우드(두 번째 세션) | **$0.0625** / 클라우드 몫 1.60 (`cost --spec S3`. editor_plan $0.0083, text_analyst $0.0499 + 픽스처 이름 변경 뒤 재기록 $0.0043(원문 페이지를 새로 받아 캐시 일부만 맞음, 결과 같음)) |
| 맥 | **$0.4988** / 맥 몫 약 1.93(상한 2.00 − 클라우드 0.06, 설계 결정 Q7). repo_analyst 평가 3회 $0.096(첫 실행 $0.0261, 무효 $0.0348, 반복 1 $0.0350) + repo-analyze 실행·추적, editor_plan 평가 $0.0283 + 계획 실행, text_analyst 평가 3회 $0.319 + 추적 |
| 합계 | $0.5613 / 상한 2.00 |

## 7-1. README, 위키 메모
- README: 역할 표 상태, 빠른 시작(repo-analyze, plan, deep text), 성과 표 S3 행. DEVELOPMENT: 명령 5개, 깊게 보기 동작
- 위키 메모: 도구 모듈이 스키마 모듈을 먼저 import하면 스펙별 스키마 합치기가 반쯤 읽힌 모듈을 받아 역할이 "없는 출력 클래스"가 됨 → 합치기에서 오류로 잡게 함. 프록시 환경에서 전송 계층을 바꾸면 httpx가 환경 변수 프록시를 쓰지 않음 → 프록시가 있으면 주소 고정을 끔

## 8. 서브에이전트 리뷰
새 컨텍스트 서브에이전트에게 스펙(S2S3_TASK, S1_REVIEW, CONTRACTS, COMMON 9~11장)과 `s2-0-base...s2-s3` diff, 리포트만 주고 대조 리뷰를 받았다(S2·S3 함께).
| 지적 | 처리 |
|---|---|
| (높음) 스키마 모듈(`artifacts_text` 등)을 먼저 import하는 진입점에서 순환 import로 ImportError | 스펙별 모듈이 끝에서 `register_schemas`로 스스로 등록, `_merge`는 읽히는 중인 모듈을 건너뜀. 6개 모듈 단독 import 회귀 테스트 |
| (중간) 대문자 레포 README, arxiv(http·버전) 인용이 대조 열쇠가 달라 지워짐 | `page_key`(github.com 소문자, arxiv는 https·버전 없는 abs)로 넣고 찾음 + 테스트 |
| (중간) trail·origin·깊이를 모델이 쓴 값으로 믿음 | trail은 이번 실행에서 연 문서만, 깊이는 코드가 센 값(`page_depth`)으로 덮어씀, origin은 연 문서만 + 테스트 |
| (중간) fetch_page가 같은 사이트 링크를 따라갈 수 없음(공식 블로그 → 같은 도메인 논문) | 도구 쪽 링크 추출을 같은 호스트 포함으로(`page_links`) + 테스트 |
| (중간) 같은 URL 기준 항목이 drop이면 묶음 전체가 요약에서 빠짐 | 기준이 drop이면 keep 경유 항목 하나(id 최소)를 대표로 + 테스트 |
| (중간) editor_plan 함정 예시가 80% 규칙·구간과 어긋남 | 72분 안(구간 30분 + 40분)으로, reason과 구간 일치 |
| (중간) deep.yaml의 항목당 도구 호출 수가 안 쓰임 | `RoleInput.tool_call_limit`(공통 코어, 좁히기만) + 두 입력의 `tool_calls`를 deep.yaml에서 + 테스트 |
| (낮음) GitHub 이름 `../user`로 다른 API 경로 | `valid_name`(., .. 거부)을 도구 인자, `--queue` 파일, 과열 규칙에 + 테스트 |
| (낮음) 커밋 API 404를 커밋 0으로 셈, 지난 주차도 오늘 기준 | 404면 규칙 미적용 + note, 지난 주차는 그 주 일요일까지 7일 + 테스트 |
| (낮음) 계획의 레포 후보에 rank, forks 없음 | 칸 추가 |
| (낮음) 허용 밖·인자 오류 호출도 도구 호출 상한에 셈 | 의도대로 둠(헤매는 호출도 비용). 아래 "스펙과 다르게"에 적음 |
| (낮음) 리포트의 관문 A 출력이 오래됨 | 다시 붙임 |
| (낮음) 프록시 환경에서 주소 고정이 조용히 꺼짐 | 운영(맥)은 직접 연결이라 그대로 두고 아래에 적음. 맥 확인 목록에 실제 HTTPS 수집 확인 |

### 리뷰 뒤 스펙과 다르게 한 것(추가)
- 도구 호출 상한은 거부된 호출(허용 밖 도구, 인자 오류)도 센다
- safe_fetch 주소 고정은 환경 변수 프록시가 있으면 꺼진다(프록시가 이름을 풀므로). 판별에 httpx 내부 함수(`httpx._utils.get_environment_proxies`)를 쓴다

### 두 번째 클라우드 세션(관문 B) 리뷰
새 컨텍스트 서브에이전트에게 스펙(COMMON 2·3·10·11장, S2S3_TASK 7~9장), `5ce27e4..7f3d15e` diff, 리포트만 주고 대조 리뷰를 받았다. 지름길 위반, 숫자 불일치, 비밀은 없다는 결과.
| 지적 | 처리 |
|---|---|
| (중간) "원본 확보 6/6"이 좋게 읽힘(it5·it21은 대체 문서, 인용 0) | README, S3 리포트, 맥 목록에 "원본 문장 대조 4/6" 병기 |
| (중간) 맥 목록 "기존 17건은 캐시로 0원"이 틀림(캐시는 git 밖) | 다시 생성·채점, 비용 예상, 클라우드 결과와 비교하라고 고침(dev- 픽스처도) |
| (중간) 맥 S2 몫 0.20 부족 가능 | 맥 목록 머리말에 경고, 질문 Q7(몫 재배분) |
| (중간) 명령 칸에 `--extra embed` 없음 | 세 명령 고침 |
| (낮음~중간) `filter-fixtures --device cpu --record`가 클라우드 CPU 기록을 덮어씀 | 명령을 mps만으로 |
| (낮음) repo_oneliner 행만 `[x]` | 체크 칸은 맥이 채우므로 `[ ]`로 되돌림(결과 칸에 클라우드 결과) |
| (낮음) 반복 순서가 규칙과 다름, 반복 1 유지 근거 | S2 리포트 2b에 이유 적음 |
| (낮음) 프롬프트 해시가 frontmatter 미포함 | S2 리포트 남은 문제에 제안(공통 코어라 이번에 고치지 않음) |
| (낮음) 첫 실행 원자료 JSON 없음, 품질 표 비용 칸이 캐시 재기록 값 | S2·S3 리포트에 적음 |
| (낮음) 품질 리포트(자동 생성)에 범위 문구 없음, S3_quality의 editor_plan 라벨 안내가 Q5와 어긋남 | 자동 생성 파일이라 손대지 않고 S3 리포트에 적음 |
| (낮음) `SENTENCE_END`의 같은 오탐, "해 주요" 놓침 | 이번 실패와 무관해 그대로(S2 리포트 5장) |
