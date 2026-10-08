# S3 리포트: 깊게 보기 (3c 레포 분석가 → 3a 편집장 계획 → 3b 글 분석가)

> 진행 체크리스트(COMMON 8장). 상태: 클라우드 구현 끝, 맥 확인 대기(`reports/S2S3_mac_todo.md`). 관문 B 수치는 맥 확인 뒤 채운다.
> 실행 환경: 클라우드(리눅스, 파이썬 3.13), `OPENROUTER_API_KEY` 없음. GitHub API는 이 저장소만, github.com·export.arxiv.org·원문 사이트는 막힘.

## 진행 체크리스트
- [x] M3 safe_fetch 연결 주소 고정(DNS 재바인딩)
- [x] 공통 코어: 입력별 허용 도구·깊이 상한, 항목당 도구 호출 상한, 도구 자원, 시작 문서 지정
- [x] 3c `repo_analyst`: 스키마·enforce, GitHub 도구 4개 + search_items, 과열 규칙, 규칙 기반 큐, `repo-analyze`, 채점(도구 효율)
- [x] 3a `editor_plan`: 스키마(CONTRACTS 1장), validate_plan, 대체 계획, `plan run/show/agreement`, 산출물·라벨 생성기, 채점
- [x] 3b `text_analyst`: 스키마·enforce, fetch_page·read_more·arxiv, 원본 추적 지침, `deep text`, 채점
- [x] `scripts/verify_s3.sh`
- [ ] 관문 B 3개 역할, 검증 산출물(`S3_traces/`, `S3_plan.md`), 라벨(맥)

## 1. 한 줄 요약
편집장이 세 채널 후보와 예산으로 계획을 세우면(모델 실패 시 규칙 기반 계획), 코드가 예산·깊이·id를 검증해 자르고, 레포 분석가가 GitHub 도구로 관련성·뜨는 이유·과열을, 글 분석가가 원문 링크를 따라 원본을 찾아 수치를 대조한다. 도구 사용 범위와 횟수, 문서 깊이, 근거 없는 판정은 코드가 막는다.

## 2. 관문 A
`bash scripts/verify_s3.sh` (2026-10-08, 클라우드)
```
FAIL A1 회귀: verify_s0.sh FAIL [A4 키 없음(OPENROUTER_API_KEY);A5 키 없음;A6 키 없음;] verify_s1.sh FAIL [A1 ]
PASS A2 ruff 0, pytest 253 passed, 1 skipped in 14.09s
PASS A3 deep.yaml이 check-config 통과 + 잘못된 값(깊이 순서, 범위)이 경로를 짚어 실패 (1 passed in 0.19s)
PASS A4 S3 역할 md 3개(repo_analyst, editor_plan, text_analyst)와 채점표, 원본 추적 지침이 역할 md 검사 통과, 예시 3개 (1 passed, 28 deselected in 0.12s)
PASS M3 safe_fetch 연결 주소 고정: 검사한 IP로만 연결(Host는 원래 이름), 리다이렉트마다 다시 고정, 검사 안 한 이름은 거부 (5 passed in 0.21s)
PASS A9 에이전트 오프라인: 녹화 픽스처로 3c(GitHub 응답), 3b(GeekNews 원문 페이지) 루프가 끝까지(모의 LLM) (4 passed, 20 deselected in 0.61s)
PASS A10 깊이·도구 상한: max_depth별 허용 도구(3c), 깊이 상한 밖·parent 없는 읽기 거부(3b), 도구 호출 6회 상한 (7 passed, 21 deselected in 0.74s)
PASS A11 계획 검증: 예산 초과 꼬리 자르기, max_depth 자르기, 없는 id 제거, 대체 계획 (7 passed, 7 deselected in 0.32s)
PASS A12 계약: video_queue.json이 VideoQueueItem으로 읽히고 plan show --video-queue 출력이 같은 모양 (2 passed, 12 deselected in 0.28s)
PASS A13 마이그레이션 대역: 이 묶음 번호 [10, 11, 12, 13], 대역 밖 [], 등록 전체 [1, 2, 10, 11, 12, 13]
PASS A14 README(빠른 시작, 성과 행), DEVELOPMENT 명령표, S3 리포트, 맥 확인 목록
```
- A1 FAIL은 키가 없어 verify_s0 A4~A6(smoke 모델 실제 호출)이 FAIL인 것뿐. 맥에서 확인

## 3. 관문 B (맥 확인 후)
| 역할 | 통과 기준 | 결과 |
|---|---|---|
| repo_analyst | judge Q1~Q3 각 80% + 관련 낮은 레포 80% 이상 커밋 도구 없이 finish + 평균 도구 호출 4회 이하 | 맥 확인 후 |
| editor_plan | 코드 채점 전부 + judge Q1~Q2 80% + 영상 mode 동의율 80% | 맥 확인 후 |
| text_analyst | enforce 전 근거 없는 confirmed/differs 0~1건 + judge Q1~Q3 각 80% | 맥 확인 후 |

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

## 4. 공통 코어 수정
| 커밋 | 파일 | 내용 |
|---|---|---|
| `3838b77` | `core/agent.py`, `role.py`, `artifacts.py`, `context.py` | 입력별 허용 도구·깊이(`RoleInput.tool_names/depth_limit`), `max_tool_calls`, `AgentState.ctx·inp·extras`, `Ctx.resources` |
| `42e68d0` | `core/artifacts.py`, `agent.py` | 시작 문서 지정(`RoleInput.depth_seed`) |
| `c72908a`(3c 커밋 안) | `eval/run_eval.py` | 도구 에이전트의 픽스처별 도구 호출 경로 기록 |
| `23cfb17`(3b 커밋 안) | `core/artifacts.py`, `eval/run_eval.py` | 반쯤 읽힌 스키마 모듈을 오류로, 픽스처마다 연 페이지 기록 비움 |
| 리뷰 반영 커밋 | `core/artifacts.py`, `agent.py` | 스펙별 스키마 자기 등록(`register_schemas`), 입력별 도구 호출 상한(`tool_call_limit`) |
- `c72908a`, `23cfb17`은 기능 커밋 안에 섞였다(COMMON 9장은 별도 커밋). 다음부터 분리

## 5. 마이그레이션
| 번호 | 단계 | 테이블 |
|---|---|---|
| 10 | 2a | item_embeddings, item_relevance, item_same_as |
| 11 | 2b | item_cards(version 1·2) |
| 12 | 3c | repo_cards, repo_oneliners |
| 13 | 3a | plans |

## 6. 남은 문제, 다음 스펙 제안
- 관문 B 3개 역할, 라벨, 산출물 → 맥
- 다음 스펙(S5) 제안: 유사 쌍 상위 30(맥 실행 뒤 `reports/S2_filter/README.md`)으로 묶기 기준, ItemCard 중 묶기에 쓸 칸(entities, keywords, claims), 원본 깊이 분포로 기본 깊이 결정
- 슬라이드 예산만 넘는 영상을 빼지 않고 whisper로 낮출지(S4 결과 보고)

## 7. 사용액
| 구분 | S3 사용액 |
|---|---|
| 클라우드 | $0(LLM 호출 없음, 키 없음) |
| 맥 | 맥 확인 후 |

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
