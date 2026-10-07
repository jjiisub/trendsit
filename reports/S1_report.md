# S1 리포트: S0 보완 + 수집 (얕게 훑기의 코드 부분) + 백필

> 진행 체크리스트(COMMON 8장). 맥락이 끊기면 여기서 이어 간다.
> S0_ADDENDUM은 S0 PR(#1)에 들어가지 않았으므로 **S1의 첫 단계(1a)**로 했다.

## 1. 한 줄 요약
`trendsit collect --since 2026-09-28 --until 2026-10-04`로 글 6곳, 유튜브, GitHub 트렌딩과 추적 레포 릴리스를 한 주치 모아(AI타임스와 유튜브는 RSS가 짧아 백필, GeekNews는 설계 결정대로 목록 페이지에서 원문 링크를 받아 원문을 본문으로) 본문, 링크 종류, 키워드 매칭까지 칠판에 저장하고, 다시 돌려도 중복이 생기지 않는다. 1a로 역할 md 작성 규칙(task, core_rules, 문서 태그, 예/아니오 채점, 라벨 도구)과 S0 리뷰 반영(R1~R6)을 바탕에 넣었다.

## 2. 관문 A
`bash scripts/verify_s1.sh` (2026-10-08, 종료 코드 0, 24개 PASS)
```
PASS A1 verify_s0.sh 전부 PASS (10개)
PASS A2 ruff 0, pytest 150 passed in 32.37s
PASS A3 새 sources.yaml, link_kinds.yaml 통과 + 잘못된 backfill method, 없는 kind가 경로를 짚어 실패 (3 passed, 58 deselected in 1.24s)
PASS A4 SSRF: 127.0.0.1, 10.0.0.5, 169.254.169.254, [::1], 사설 IP로 리다이렉트, 5MB 초과, 허용 밖 형식 거부 (21 passed, 40 deselected in 0.79s)
PASS A5 오프라인 collect(녹화에 없는 URL은 차단): 소스별 기대 건수, 본문, 링크, 키워드 저장 (1 passed, 60 deselected in 4.84s)
PASS A6 같은 collect 두 번: 항목 수 그대로, 중복 0 (1 passed, 60 deselected in 5.42s)
PASS A7 백필: list_pages(AI타임스)와 day_archive(GeekNews, Simon Willison), 유튜브 채널 목록, --since 앞에서 멈춤 (6 passed, 55 deselected in 3.75s)
PASS A8 실패 격리: 한 소스 500이어도 나머지 수집, fetch_log failed + 실행 기록 attention (1 passed, 60 deselected in 3.65s)
PASS A9 트렌딩(설계 결정 Q2): 주간 페이지에 보이는 전부 저장(페이지 수 = 저장 수), stars_this_week 모두 숫자, 0개면 실패로 기록. 파서는 월간 페이지 25개로도 확인 (5 passed, 56 deselected in 9.91s)
PASS A10 키워드: 제목 매칭 3점, 단어 경계(eval ≠ evaluate), 제외어 규칙 (1 passed, 60 deselected in 0.77s)
PASS A11 robots: 막힌 경로는 가져오지 않고 기록 (4 passed, 57 deselected in 0.91s)
PASS A12 README와 DEVELOPMENT.md에 수집 명령, reports/S1_report.md
PASS P1 역할 md 검사: 전부 통과 + 섹션 누락, core_rules 4개가 경로를 짚어 실패 (4 passed, 21 deselected in 0.60s)
PASS P2 메시지 조립: system에 입력 없음, <data> → task → 핵심 규칙, 해시는 입력과 무관 (3 passed, 22 deselected in 0.37s)
PASS P3 자료 탈출 방지: </document>, </data> 등이 태그 밖으로 나가지 않음 (8 passed, 17 deselected in 0.11s)
PASS P4 스키마 순서: 모든 출력의 마지막 두 칸 log, attention, basis가 oneliner 앞 (4 passed, 21 deselected in 0.12s)
PASS P5 라벨 도구: --label CSV 생성, 모의 라벨로 --agreement 일치율 (1 passed, 24 deselected in 0.18s)
PASS P6 README 한 줄 소개 + 제목 11개 순서, CI 배지, PR 양식, CI(YAML 통과), RULES.md, ADR 틀 (CI 초록은 PR에서 확인)
PASS R1 태그 탈출 대소문자: </DATA>, </Data >, </document >, <DOCUMENT id="x"> (8 passed, 17 deselected in 0.10s)
PASS R2 채점자 md: 역할 이름 없음, 채점표는 시스템 프롬프트에 한 번 (1 passed, 24 deselected in 0.12s)
PASS R3 도구 예외: 루프가 이어지고 step에 error (1 passed, 24 deselected in 0.27s)
PASS R4 인자 정규화: nullable 칸만, detail에 normalized (2 passed, 23 deselected in 0.19s)
PASS R5 A9 비밀 검사 제외를 실행 산출물로 좁힘(추적 중인 data/ 파일도 검사)
PASS R6 역할 md 검사: roles/*.md + eval/judge.md 통과, 추가 섹션 허용 (3 passed, 22 deselected in 0.39s)
```

## 3. 관문 B 요약
| 대상 | 기준 | 결과 | 판정 |
|---|---|---|---|
| 수집: 글 소스 6곳 기간 덮음 | RSS 또는 백필 | 6곳 모두 | 통과 |
| 수집: 본문 추출 성공률 | 소스별 90% 이상, 분모는 원문 링크가 있는 글에서 의도적 건너뜀 제외(Q1) | GeekNews 98%(78/80), AI타임스 100%, OpenAI 93%, Anthropic·DeepMind 100% | 통과 |
| 수집: GeekNews 원문 링크 확보율 | 95% 이상 | 100%(83/83, 자기 글 57건은 수집에서 뺌) | 통과 |
| 수집: 트렌딩 | 주간 페이지에 보이는 전부, 누락 0, 0개면 실패(Q2) | 11/11, 누락 0 | 통과 |
| 수집: 중복 | 0 | 0 | 통과 |
| 1a repo_oneliner(3회 개선) | 코드 10/10, Q1 10/10, Q2·Q3 9/10 | 코드 8/10, Q1·Q2·Q3 8/8(잠정) | 미달 |
| 1a repo_oneliner(Q3 재측정, 1회) | 같음 | 코드 9/10(Images360 attention), Q1·Q2·Q3 9/9(잠정) | 미달 |

상세: `reports/S1_collection.md`(하루 신규 건수, 사람 확인용 샘플 포함), `reports/S1_quality.md`(repo_oneliner).

## 진행 체크리스트

### 1a S0 보완 (S0_ADDENDUM) + S0 리뷰 반영 (S0_REVIEW)
- [x] 1.1 역할 md 앞부분 `task`, `core_rules`(최대 3, 로더가 검증)
- [x] 1.2 메시지 조립: system = 역할 md + includes + data 규칙 / user = `<data>` → task → 핵심 규칙. 해시 = system + task + core_rules
- [x] 1.3 `render_data`(`core/render.py`): `Document`는 `<document id source title url>`, 짧은 칸은 `이름: 값`, 자료 안의 `<`는 모두 `&lt;`. 도구 결과도 같은 함수
- [x] 1.4 출력 스키마 칸 순서(log, attention 맨 끝, basis가 oneliner 앞, critique가 verdict 앞) + 테스트
- [x] 1.5 역할 md 검사(`check-config`): 고정 섹션 6개 순서, `<example>` 3~5개, 굵게 1개 이하, task·core_rules
- [x] 1.6 repo_oneliner 다시 쓰기: 템플릿, `basis` 칸, README를 `rp:` 문서로, 코드 검사(basis가 README 안에)
- [x] 1.7 예/아니오 채점: judge 출력 critique → verdict(Q1~Q3), 1~5점은 보고용
- [x] 1.8 라벨 도구: `eval --label`, `eval --agreement`. `eval/labels/repo_oneliner.csv` 생성(사용자가 채움)
- [x] 1.9 AGENTS.md(S6, 20달러·50달러, 역할 md 형식), CLAUDE.md(prompt_guide, RULES)
- [x] 1.10 README: main에 병합된 PR #2 판(설계 문서 36 골격)을 그대로 두고 CI 배지만 넣음(사용자 지시). 새 명령 설명은 `docs/DEVELOPMENT.md`. `.github/pull_request_template.md`, `.github/workflows/ci.yml`, `docs/RULES.md`, `docs/adr/0000-template.md`, `docs/images/`
- [x] R1 태그 탈출 대소문자(`<` 전부 무력화) / R2 채점자 md 역할 무관 / R3 도구 예외를 결과로 / R4 nullable 인자 정규화 / R5 A9 제외 범위 좁힘 / R6 검사 범위(roles + eval/judge.md, 추가 섹션 허용), lookup_agent 템플릿으로
- [x] 관문 A: `verify_s1.sh`의 P1~P6, R1~R6 PASS
- [~] 관문 B(repo_oneliner): 3회 개선 후 미달(코드 채점 8/10). 설계 결정 Q3 뒤 재측정(Q4로 예산 0.06): 코드 9/10, Q1·Q2·Q3 9/9 → 미달 그대로 보고

### 1b 수집
- [x] 설정: sources.yaml(백필 URL을 실제로 확인해 고침, GitHub 트렌딩 페이지), link_kinds.yaml, check-config 스키마(설정 5개)
- [x] safe_fetch(SSRF, 도메인별 1초, robots, 429·5xx 재시도, HTTP 캐시, 5MB, 허용 형식)
- [x] 글 수집(RSS, trafilatura 본문, 백필 list_pages/day_archive). GeekNews는 설계 결정 Q1대로 목록 수집(list_origin)
- [x] 유튜브(RSS, yt-dlp 메타데이터, 채널 목록 백필)
- [x] GitHub(트렌딩 주간 페이지, 추적 레포 릴리스, README)
- [x] 링크 판별, 키워드 매칭(제외어 규칙)
- [x] 칠판 테이블 + 마이그레이션(user_version 1, 2: items.meta_json)
- [x] CLI collect, items, report collection
- [x] 녹화 응답 픽스처(`tests/fixtures/http/`, 약 870KB), 테스트, verify_s1.sh A3~A12
- [x] 설계 결정 Q1(GeekNews 목록 수집), Q2(트렌딩 기준), Q3(README 정리 입력) 반영
- [x] 관문 B: 실제 수집(9/28~10/4) + `reports/S1_collection.md`. 바뀐 기준으로 5개 모두 통과

## 1a 관문 B (repo_oneliner, generate, 판정은 잠정)
| 회차 | 바꾼 것 하나 | 프롬프트 | 코드 채점 | Q1 | Q2 | Q3 |
|---|---|---|---|---|---|---|
| 1 | 새 템플릿(task, core_rules, basis, 문서 태그), 예/아니오 채점 | `2969b076772d` | 7/10 | 7/7 | 7/7 | 7/7 |
| 2 | md 문구: basis는 README 본문에서, 마크업이 끼지 않은 구간 | `7bbc556f62db` | 7/10 | 7/7 | 7/7 | 7/7 |
| 3 | 예시 교체: 함정 예시 awesome-python → flask(링크 기호가 낀 구절, description과 다른 문구) | `c16be6fbb27f` | 8/10 | 8/8 | 8/8 | 8/8 |

- 문턱값(Q1 10/10, Q2·Q3 9/10, 코드 채점 전부) 미달. 3회 상한이라 멈춤
- 남은 실패 2건(출력을 직접 읽고 분류)
  - hermes-agent(모델 한계): README가 `**The self-improving AI agent built by [Nous Research](…).**`인데 basis를 링크 기호를 뺀 "The self-improving AI agent built by Nous Research"로 옮김. md 지시와 예시를 줘도 3회 모두 같음
  - fastapi template(입력에 정보 부족 + 지시 위반): README 앞부분이 제목과 링크 달린 기술 목록뿐이라 기능을 말하는 구절이 없음. 3회 모두 description 문장을 basis로 씀
- 1회차 → 3회차 사이에 excalidraw(`</br>`가 낀 구절)는 해결, Images360은 2회차에만 attention을 false로 냄(같은 입력에서도 흔들림)

### 설계 결정 Q3 뒤 재측정(3회 상한과 별도, 1회)
- 바꾼 것: README 입력에서 마크다운·HTML 기호를 걷어 낸 본문(`core/textclean.py`), basis 검사는 정리 본문 + description. 역할 md의 basis 지시와 예시도 같은 기준으로(함정 예시는 스펙 1.6의 awesome 목록으로 되돌림). 리뷰 반영으로 예시의 README 밖 내용("C/C++", "Python")을 고침. 프롬프트 `d77414b2efaf`
- 결과(프롬프트 `a1a38c7f4dfe`, 10개 전부): 코드 채점 9/10, judge 판정 Q1·Q2·Q3 9/9(잠정). 문턱값(코드 10/10) 미달
  - 경과: 처음 재측정(`d77414b2efaf`)은 S1 상한 $0.05에 걸려 7개에서 멈춤 → 설계 결정 Q4로 0.06 → 2차 리뷰의 지시 모순 수정 뒤 다시 돌렸으나 마지막 채점 1건 직전에 또 상한(누적 $0.0550 + 예상 $0.0055) → 예상 비용이 추론 토큰 상한(800)을 출력 상한(1600)에 더해 2배 가까이 크게 잡고 있음을 확인(OpenRouter 문서: 추론 토큰은 max_tokens 안에서 셈)하고 고친 뒤 마지막 1건($0.0012)
  - hermes-agent(마크다운 링크)와 fastapi(description 근거)는 통과로 바뀜
  - 남은 실패 1건: Images360 attention이 false(기대 true). README가 제목과 한 줄뿐인데 "근거가 얇다"로 보지 않음(1a 2회차부터 같은 흔들림)
- 라벨 파일 `eval/labels/repo_oneliner.csv`를 이 재측정(`a1a38c7f4dfe`)의 출력으로 다시 만듦. 출력이 이전 파일과 같은 행만 라벨을 보존하는 규칙(이전 파일은 라벨이 비어 있어 보존된 행 없음)

## 1b 관문 B: 수집 (9/28~10/4, 실제 네트워크, 설계 결정 Q1·Q2·Q5 반영 후)
| 항목 | 기준 | 결과 | 판정 |
|---|---|---|---|
| 글 소스 6곳 기간 덮음 | RSS 또는 백필 | 6곳 모두 | 통과 |
| 본문 추출 성공률 | 소스별 90% 이상(feed_full 제외). 분모는 원문 링크가 있는 글에서 의도적 건너뜀을 뺀 수(Q1) | GeekNews 98%(78/80), AI타임스 100%(188/188), OpenAI 93%(14/15), Anthropic·DeepMind 100% | 통과 |
| GeekNews 원문 링크 확보율 | 95% 이상 | 100%(83/83, 자기 글 57건은 수집에서 뺌) | 통과 |
| 트렌딩 | 주간 페이지에 보이는 전부, 별 누락 0, 0개면 실패(Q2) | 페이지 11개 중 11개, 누락 0 | 통과 |
| 중복 | 0 | 0 | 통과 |

- 수집량: 글 308건(AI타임스 188, GeekNews 83, Simon Willison 18, OpenAI 15, Anthropic 2, DeepMind 2), 영상 17편, 릴리스 18건, 트렌딩 11개, 키워드 통과 184건
- 하루 신규 건수(게시일): GeekNews 9~15(평균 11.9, 날짜당 1페이지 20건에서 자기 글을 뺀 수), AI타임스 12~40(평균 26.9, 주말 적음), 나머지 하루 0~5. 참고: 날짜별 목록 전체를 읽은 이전 수집에서 GeekNews는 하루 34~54건(평균 45.6건, 자기 글 제외)이었다. 페이지 수를 정할 근거
- GeekNews(날짜당 1페이지): 의도적 건너뜀 3건(영상 2, robots 1), 실패 1건(추출 실패), 짧음 1건. 7일 140행 중 자기 글(Show GN) 57건은 점수 상위에 많이 올라 1페이지에 몰려 있음(10/1은 20행 중 7행)

### 거쳐 온 과정(위키 재료)
1. 처음 방식(RSS + 상세 페이지 요약): 상세 페이지를 짧은 시간에 25건 안팎 받으면 Cloudflare Turnstile 브라우저 확인이 나옴. 우회하지 않고 감지해서 멈춤
2. 실패 이유를 세어 기록하도록 고침: "본문 추출 실패"로만 보이던 것이 확인 페이지였음을 찾음
3. 설계 결정 Q1: 목록 페이지만, 본문은 원문에서. 상세 페이지 요청 0. 처음엔 어제 이후를 메인 화면(점수순 1~2페이지)으로 받음
4. AI타임스: 기간으로 거른 목록에 기간 안에 수정된 예전 글(게시일 9/23)이 섞여 "since보다 앞선 글이 나오면 멈춤" 규칙이 4페이지에서 멈춤(79건) → 기간으로 거른 목록은 빈 페이지까지 읽도록 고침(188건). 하루 신규 건수 표에서 9/28~9/30이 0으로 보여 발견
5. 트렌딩: GitHub 주간 페이지가 11~13개만 보여 줌 → 설계 결정 Q2로 기준 변경
6. 설계 결정 Q5: 메인 화면을 쓰지 않고 매일 수집과 백필 모두 날짜별 목록(날짜당 1페이지). 오늘은 하루가 끝나지 않아 읽지 않음

### 그 밖에 본 것
- AI타임스 AJAX가 한 번 "정상적인 접근이 아닙니다"로 거부했다가 다음엔 통과(일시적). 1회 재시도로 대응
- 유튜브 영상 1편은 채널 회원 전용이라 메타데이터 실패(정상)
- GitHub 비인증 API 한도(시간당 60회)를 시험 수집에서 다 써서 README 403. 본 수집은 `gh` 로그인 토큰을 `GITHUB_TOKEN`으로 넘김(저장하지 않음)
- 원문이 Hacker News 토론 페이지인 GeekNews 글은 토론 속 링크가 많이 잡힘. S3 원본 추적에서 거를 대상

## 4. 결정한 것 (스펙에 없어서 정한 것)
| 결정 | 이유 |
|---|---|
| **설계 결정 Q1(2026-10-07): GeekNews 목록 수집.** RSS와 상세 페이지(`topic?id=`)를 쓰지 않음. 목록 페이지에서만(처음엔 메인 + 날짜별 목록, Q5 뒤로는 날짜별 목록만). 목록에서 제목, 원문 링크, 요약 앞부분, 받을 때의 점수와 댓글 수(`items.meta_json`), 본문은 원문 링크에서. topic id로 중복 제거(`external_id=topic:<id>`). 원문 링크가 GeekNews 자신인 글은 수집에서 빼고 건수만(`n_self_excluded`). 목록 요청 5초 간격(`request_interval_s`). 수집 리포트에 하루 신규 건수. 본문 성공률 분모는 원문 링크가 있는 글에서 의도적 건너뜀(`skip_robots`, `skip_type`, `skip_video`)을 뺀 수, 403 등은 실패 | 사용자(설계) 결정. RSS 링크는 상세 페이지라 원문 링크가 없고, 상세 페이지는 짧은 시간에 여러 번 받으면 브라우저 확인이 나옴 |
| **설계 결정 Q2: 트렌딩 기준** "주간 페이지에 보이는 전부 수집, stars_this_week 누락 0, 0개면 실패". `top_n` 상한 없앰, 언어별·월간 페이지 추가 안 함 | 사용자(설계) 결정. 주간 페이지가 11~13개만 보여 줌 |
| **설계 결정 Q3: repo_oneliner 입력 정리.** README의 마크다운·HTML 기호(배지, 이미지, 링크 문법, 강조, 태그)를 걷어 낸 본문을 모델에(`core/textclean.py`), basis 검사는 정리 본문 + description. 관문 B 1회 재측정(3회 상한과 별도) | 사용자(설계) 결정. 3회 개선 뒤 남은 실패 2건이 기호와 description에서 왔음 |
| **설계 결정 Q4(2026-10-08): S1 예산 0.05 → 0.06** (`config/budget.yaml`) | Q3 재측정을 끝까지 돌리려고. 처음 재측정이 상한에 걸려 7개에서 멈춤 |
| **설계 결정 Q5(2026-10-08): GeekNews 메인 화면을 쓰지 않음.** 매일 수집(어제)과 백필 모두 날짜별 목록 `past?day=`, 날짜당 페이지 수는 `backfill.pages_per_day`(기본 1 = 그날 점수 상위 약 20건). 오늘은 읽지 않음. 점수, 댓글 수 저장은 그대로 | 메인 1~2페이지는 하루치를 날짜로 덮지 못함(2차 리뷰 4) |
| **라벨 파일 재생성 규칙(2026-10-08 설계 결정):** 출력이 이전 파일과 같은 행만 라벨 보존, 바뀐 행은 비움 | 다른 출력에 대한 사람 판정을 잘못 이어 쓰지 않게 |
| 예상 비용의 출력 토큰 = max(max_tokens, reasoning.max_tokens) | OpenRouter 문서 "추론 토큰은 max_tokens 안에서 센다". 전에는 둘을 더해 채점 호출을 2배 가까이 크게 잡아 Q3 재측정의 마지막 1건을 막았다. 상한을 늘린 것이 아니라 계산을 청구 구조에 맞춘 것(테스트 추가) |
| robots.txt가 5xx거나 닿지 않으면 그 출처는 막힌 것으로 보고 기록(RFC 9309). 형식 헤더가 없는 응답은 거부 | 리뷰 7, 8 |
| 기간 판정: 목록에 날짜가 없던 후보는 글 페이지·yt-dlp에서 얻은 날짜로 다시 보고 기간 밖이면 저장하지 않음(`n_out_of_range`). 유튜브 채널 목록의 대략 날짜는 앞뒤 3일까지 후보로 | 리뷰 2 |
| "기간 덮음"은 백필이 --since보다 앞선 항목이나 목록 끝까지 닿았을 때만 참. 백필 오류도 거짓 | 리뷰 3 |
| 수집 리포트는 같은 기간을 수집한 실행의 기록만 씀(`fetch_log.detail`에 since, until) | 리뷰 18 |
| 1a를 S1 브랜치 첫 커밋으로, README는 main(PR #2) 판에 CI 배지만(사용자 지시). 새 명령 설명은 `docs/DEVELOPMENT.md` | 사용자 지시 |
| repo_oneliner의 "보통" 예시는 ollama 대신 llama.cpp | ollama는 평가 픽스처라 기대 출력을 프롬프트에 박는 셈(S0과 같은 판단) |
| 재시도 오류 문구를 "120자 이하여야 함(지금 187자)"처럼 길이를 알리는 한국어로, "위 오류를 고친 JSON으로" | 무료 모델이 pydantic 영어 메시지로는 같은 출력을 반복함 |
| 백필 판단: 요청 시작일이 RSS의 가장 오래된 항목 날짜보다 앞서면 백필(가장 오래된 날도 다시 읽음) | RSS가 그날을 일부만 담을 수 있어서 |
| `list_pages`에 `page_template`(2페이지부터), `{since}` `{until}` 자리, 2페이지부터 Referer로 1페이지 | AI타임스의 실제 구조(1페이지 HTML, 이후 AJAX JSON) |
| `day_archive`에 `{date}`, `{page}`(20건 미만 페이지에서 멈춤) | GeekNews 날짜별 아카이브 구조 |
| robots.txt는 목록, 아카이브, 글 페이지에서만 확인. 피드(RSS, releases.atom)와 GitHub API는 기계용이라 생략 | 스펙 5.1 허용 |
| 기간은 한국 시간 게시일. RSS가 UTC면 바꿔서 판단 | 스펙 5.6. DeepMind 10/6 19:57 UTC 글은 10/7 |
| 본문 `MIN_BODY` 300자, 글마다 본문 속 바깥 링크 전부(다른 호스트) 저장 | 스펙 5.2 |
| `items`에 `via`(rss/backfill), `fetch_log`에 `n_seen`, `detail`, `t`, `repo_trending`에 키워드 칸 | 리포트와 실행 기록 화면 재료. 스펙 칸은 그대로 |
| 레포 키워드는 이름 + 설명으로 먼저 보고, 걸리면 README를 받아 다시 판정 | 스펙 5.4(README는 키워드에 걸린 레포만) |
| 추적 레포 릴리스는 `github_releases` 소스 하나로, 레포 이름을 제목 앞에 | 칠판의 소스 단위를 단순하게 |
| `collect --max-items N`(개발용) | 공통 규칙 4장 "개발 중에는 작은 샘플" |
| HTTP 테스트는 실제 응답을 녹화해 줄인 것(`scripts/record_http_fixtures.py`, gzip 744KB) + 녹화에 없는 URL은 연결 실패 | "저장한 응답으로 오프라인" + 네트워크가 새지 않게 |

## 5. 스펙과 다르게 한 것
| 스펙 | 실제 | 이유 |
|---|---|---|
| GeekNews RSS + 백필 후보 `list_pages ?page=` | 설계 결정 Q1·Q5: 매일 수집과 백필 모두 `day_archive past?day=`(날짜당 1페이지), RSS·상세 페이지·메인 화면 없음 | `?page=`는 점수순이라 날짜 백필에 못 씀, RSS·상세 페이지 문제, 메인은 날짜를 덮지 못함 |
| 백필 후보 AI타임스 `list_pages ?page=` | 1페이지 `sc_sdate/sc_edate` HTML, 2페이지부터 `ajaxArticlePaging.php` | `page` 값이 무시됨(더보기는 JS) |
| Anthropic `list_pages`(페이지 넘김) | 1페이지만(`max_pages: 1`) | 목록에 페이지 넘김이 없음. 피드가 2021년부터 있어 대체 수단 |
| GeekNews 본문 = 토픽 페이지 한국어 요약 | 원문 글(요약은 목록의 앞부분만 `summary_feed`, `origin_summary`) | 설계 결정 Q1 |
| repo_oneliner 함정 예시 = awesome 목록 레포(S0_ADDENDUM 1.6) | 3회차에 flask로 바꿨다가 Q3 뒤 awesome 목록으로 되돌림 | 기호 문제는 입력 정리로 해결되어 flask 예시가 필요 없어짐 |
| 날짜별 아카이브는 요청 기간의 날짜만 | `archive_tz: utc`(Simon Willison)는 시작일 하루 전 아카이브부터 | UTC 날짜 아카이브라 한국 시간 시작일 0~9시 글이 전날 아카이브에 있음(리뷰 5) |
| list_pages는 --since보다 앞선 항목이 나오면 멈춤 | 기간으로 거른 목록(주소에 `{since}`)은 빈 페이지까지 | AI타임스 목록에 기간 안에 수정된 예전 글이 섞여 일찍 멈춤(79건 → 188건) |
| README 수정 범위(기능 상태, 빠른 시작, 성과, 로드맵) | 맨 위 "현재 상태" 줄도 S1로 | 같은 파일의 S1 완료 표기와 어긋나서(리뷰 19). 기능 상태의 일부로 봄 |
| A9 "25개 내외" | 설계 결정 Q2: 주간 페이지에 보이는 전부(저장한 페이지 11개 = 저장 수), 파서는 월간 페이지 25개로도 확인 | Q2 |
| P6 "README 12개 제목" | 맨 위 한 줄 소개 + 지금 README의 제목 11개(`## 1. 왜 만들었나` … `## 만든 사람`) | 사용자 지시 |
| 허용 콘텐츠 형식 | + `text/javascript`(AI타임스 AJAX가 JSON을 이 형식으로), `application/vnd.github`(raw README) | 실제 응답 형식 |
| `sources.yaml`의 `fallback_list` | 없앰(백필 `list_pages`로 옮겨짐) | S1 묶음의 새 설정 |

## 6. 남은 문제, 다음 스펙 제안
- repo_oneliner Images360의 attention 흔들림(README가 한두 줄일 때 근거가 얇다고 보지 않는 경우). 코드 규칙으로 정할지(README 본문 길이 기준) S2 전에 결정 후보
- README 정리 함수(`core/textclean.py`)는 S3 레포 분석가 입력에서 그대로 쓸 수 있음
- 키워드 조정 후보(S2 전에): `eval`의 "평가"가 "과대평가"에 걸림, `frontier-release`의 GPT·Claude·Gemini가 회사 이름만 나와도 걸려 고객 사례 글이 통과(OpenAI 15건 중 11건 통과), `agent`의 "에이전트"가 넓음. 샘플은 `reports/S1_collection.md` 5장
- S2 입력량 추정: 한 주 키워드 통과 184건(AI타임스 106, GeekNews 52, Simon 12, OpenAI 11, Anthropic 2, DeepMind 1) + 영상 14편. 1차 요약 대상
- GeekNews 날짜당 1페이지는 하루 약 45.6건 중 점수 상위 20건(자기 글 빼면 약 12건). 놓치는 글이 문제가 되면 `pages_per_day`를 2~3으로(하루 신규 건수 표가 근거)
- 단계 사용액이 키 기준 $0.318로 실행 기록 합($0.108)보다 크다. 같은 키를 다른 곳에서 쓴 사용량이 반영된 것(단계 상한 $20 안)
- 원문 Hacker News 토론 페이지의 링크 소음, PDF 원문(3건)은 S3 원본 추적에서
- DNS 재바인딩: 검사 뒤 httpx가 다시 이름을 푼다(검사와 연결 사이 짧은 틈). 연결 주소 고정은 S3 실제 fetch 도구 전에 검토

## 7. 사용액
`uv run python -m trendsit cost --spec S1` (1b 수집은 LLM 호출 없음. 전부 1a repo_oneliner 관문 B와 Q3 재측정)
```
| 스펙 | 모델 | 호출 | 캐시 적중 | 입력 토큰 | 출력 토큰 | 사용액(달러) |
|---|---|---|---|---|---|---|
| S1 | google/gemini-3.8-flash | 44 | 18 | 87473 | 15050 | 0.036248 |
| S1 | qwen/qwen3.8-27b | 62 | 11 | 151508 | 3632 | 0.019976 |
| 합계 | | | | | | 0.056224 |

- 스펙 S1: 기록 합 $0.056224 / 상한 $0.06
- 단계(mvp) 사용액: $0.317723 / 상한 $20.00, 남은 예산 $19.682277
  - 키 기준(현재 usage − 기준값 $0.483310): $0.317723, 실행 기록 합: $0.108227 (키 반영이 늦으면 큰 쪽 사용)
- 키 limit_remaining: 49.198967026
```

## 7-1. README 갱신, 위키 메모
- README: 맨 위 현재 상태 줄(S1), 핵심 기능 상태(수집 S1 완료), 빠른 시작(`collect`, `report collection`), 성과 표(S1 수집 수치, repo_oneliner), 로드맵 체크. 1a에서는 CI 배지만
- 위키 메모
  - GeekNews 브라우저 확인: 1초 간격 25건 안팎에서 Turnstile 확인으로 넘어감 → 우회하지 않고 감지해서 멈춤 → 설계 결정으로 목록만 받고 원문을 본문으로. 실패 이유를 세지 않아 처음엔 "본문 추출 실패"로만 보였던 것이 교훈
  - 하루 신규 건수 표 덕분에 AI타임스 9/28~9/30이 0건인 것을 발견(기간 목록의 정렬 가정이 틀림)
  - AI타임스 목록의 `page`가 무시되는 구조(JS 더보기) → AJAX 엔드포인트를 찾아 날짜 범위로 백필
  - repo_oneliner 1a: 무료 모델이 120자 상한을 3번 연속 어김 → 재시도 문구에 현재 길이를 넣고 "같은 내용을" 문구를 빼서 해결. generate는 마크다운 링크가 낀 구절을 기호 없이 옮기는 실패가 남음

## 8. 서브에이전트 리뷰 지적과 처리
새 컨텍스트의 서브에이전트(code-reviewer)에게 스펙 4개, diff, 리포트만 주고 대조 리뷰를 받음(한 번 사용량 한도로 끊겨 이어서 받음). pytest·ruff 확인, 픽스처 전용 분기나 기대 출력 박기 없음.

| # | 지적 | 심각도 | 처리 |
|---|---|---|---|
| 1 | RSS로만 얻은 GeekNews 글은 브라우저 확인 뒤 원문 링크가 없어 본문 0(기본 1일 수집에서 재현) | high | 고침. RSS와 백필 후보를 합칠 때 원문 링크를 보존, 그래도 없으면 그날 날짜별 아카이브에서 찾음. 테스트 추가 |
| 2 | 날짜 없는 후보가 기간 필터를 통과하고, 나중에 얻은 날짜가 기간 밖이어도 저장. 유튜브 대략 날짜 | high | 고침. 저장 직전에 다시 확인, 유튜브는 앞뒤 3일 후보 + 정확한 시각으로 재확인. 테스트 추가. 유튜브 녹화 재확인에서 기간 밖 1편이 빠짐 |
| 3 | 백필이 상한·오류로 --since에 닿지 못해도 "기간 덮음" | high | 고침. 닿음·목록 끝만 덮음, 오류는 아님. 테스트 추가 |
| 4 | 시작일 = RSS 가장 오래된 날이면 백필 안 함 | medium | 고침(`since <= oldest`). 재수집에서 Simon Willison 1건이 새로 잡힘 |
| 5 | Simon 아카이브는 UTC 날짜 | medium | 고침. 하루 전 아카이브부터 |
| 6 | A5 기대 건수가 녹화 스냅샷이라 약함 | medium | 고침. 기간 안 후보 수(`n_in_range`)를 피드에서 직접 센 값과 비교, 모든 항목의 날짜 확인 |
| 7 | robots.txt 5xx·연결 실패면 그냥 가져오고 기록 없음 | medium | 고침. 막힌 것으로 보고 이유 기록, 출처마다 한 번 |
| 8 | 형식 헤더 없으면 허용 형식 검사를 건너뜀 | medium | 고침. 거부. 테스트 추가 |
| 9 | fec0::/10 통과, DNS 재바인딩 틈 | medium | fec0::/10 막음. 재바인딩은 S3 실제 fetch 도구 전에(6장) |
| 10 | repo_oneliner 예시가 README 밖 내용("C/C++", "Python")과 평가어 basis | medium | 고침(발췌에 README 실제 문장, basis 교체). 함정 예시 변경을 5장 표에. 재측정은 예산 때문에 안 함 |
| 11 | A9 기준 완화가 verify 출력에 안 보임 | medium | 고침(문구에 11개, 스펙 25개 내외 명시) |
| 12 | A12 grep이 약함 | medium | 고침(`trendsit collect --since`) |
| 13 | 같은 주 재실행 때 빠진 레포 행이 남음 | medium | 고침. 그 주 목록을 바꿈 |
| 14 | 레포 키워드를 이름으로 판정(제목 가중치) | medium | 고침. 설명, 토픽, README로(스펙 5.5) |
| 15 | 메타데이터 실패 영상 재시도 없음, Retry-After 날짜 형식 | low | 고침 |
| 16 | 중복을 (source_id, url)로 세서 항상 0 | low | 고침. 정규화한 URL로 셈 |
| 17 | fetch_log.day 시스템 시간대, 없는 소스면 run이 running으로, fetcher 안 닫음 | low | 고침 |
| 18 | 리포트가 다른 기간의 기록을 섞음 | low | 고침 |
| 19 | README 현재 상태 줄이 S0 | low | 고침 |
| 20 | 도메인이 아니라 호스트 단위 간격, link_kinds `paths` 미사용, `default` 검사 | low | 간격은 www를 뗀 도메인으로 고침. `paths`는 참고용(설정 주석에 적힘), `default`는 kinds 밖 값(other)이 정상이라 그대로 |

### 2차 리뷰(설계 결정 반영분, 새 컨텍스트)
설계 결정을 정면으로 어기는 곳은 없음(GeekNews 상세 페이지·RSS 요청 경로 없음, topic id 중복 제거, 점수·댓글 저장, 목록 5초 간격을 모의 실행으로 확인).

| # | 지적 | 심각도 | 처리 |
|---|---|---|---|
| 1 | robots.txt를 못 읽은 경우(타임아웃)도 skip_robots로 분류되어 분모에서 빠짐 | medium | 고침. "robots.txt가 막음"만 skip_robots, 확인 불가는 실패. 저장된 2건도 다시 분류(그때 93%, 276/296. Q5 뒤 재수집 98%, 78/80). 테스트 추가 |
| 2 | 품질 리포트의 대표 결과가 Q3 이전 기준 | medium | 고침. 마지막 전체 실행보다 새 부분 실행을 따로 표로, 가장 나쁜 사례도 최근 실행에서 |
| 3 | repo_oneliner 지시 모순(description을 basis로 써도 되나) | medium | 고침. "README에도 description에도 기능 구절이 없으면 비움"으로 통일 |
| 4 | 어제 이후를 평소 목록으로만 읽는데 "기간 덮음 예" | medium | 처음엔 리포트에 "일부"로 표시. 이후 설계 결정 Q5로 메인 화면을 없애고 날짜별 목록만 |
| 5 | 트렌딩 page_rows가 파서가 거른 뒤 수라 실패할 수 없음 | medium | 고침. 거르기 전 `article.Box-row` 수. 미달 쪽 테스트 추가 |
| 6 | 목록이 200인데 0행이면 조용히 0건 | low~medium | 고침. GeekNews 1페이지 0행은 오류(덮음 아님). 테스트 추가 |
| 7 | 원문 링크 확보율이 구조상 항상 100% | low | 리포트에 그 사실과 실제 확인 대상(자기 글 판정)을 적음 |
| 8 | 게시 시각 없는 목록 행이 집계 없이 사라짐 | low | 건수를 세서 메모에 |
| 9 | 자기 글 판정이 문자열 포함 검사 | low | 고침. 호스트로 판정. 테스트 추가 |
| 10 | `--no-body`의 skipped가 분모에, skip 이유가 "실패 이유"로 표시 | low | 고침. 분모에서 빼고 skip 이유를 따로 셈 |
| 11 | 아카이브 max_pages 도달이 기록 안 됨 | low | 고침. 메모 + 덮음 아님 |
| 12 | basis가 README와 description 경계를 넘어도 통과 | low | 고침. 각각 따로 검사. 테스트 추가 |
| 13 | DEVELOPMENT.md에 옛 GeekNews 설명 | low | 고침 |
| 14 | 옛 방식(URL 기반 id)으로 저장된 GeekNews 항목과 중복 가능 | low | 이 세션의 로컬 DB는 옛 항목을 지우고 다시 수집. 옛 DB가 따로 없음(코드 이전 단계) |
| T1~T4 | 자기 글 건수, 트렌딩 미달, 날짜 경계·간격·0행, robots 확인 불가 테스트가 없거나 약함 | - | 모두 추가(테스트 149개) |
