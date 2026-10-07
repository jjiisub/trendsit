# S1 리포트: S0 보완 + 수집 (얕게 훑기의 코드 부분) + 백필

> 진행 체크리스트(COMMON 8장). 맥락이 끊기면 여기서 이어 간다.
> S0_ADDENDUM은 S0 PR(#1)에 들어가지 않았으므로 **S1의 첫 단계(1a)**로 했다.

## 1. 한 줄 요약
`trendsit collect --since 2026-09-28 --until 2026-10-04`로 글 6곳, 유튜브, GitHub 트렌딩과 추적 레포 릴리스를 한 주치 모아(RSS가 짧은 GeekNews, AI타임스, 유튜브는 백필) 본문, 링크 종류, 키워드 매칭까지 칠판에 저장하고, 다시 돌려도 중복이 생기지 않는다. 1a로 역할 md 작성 규칙(task, core_rules, 문서 태그, 예/아니오 채점, 라벨 도구)과 S0 리뷰 반영(R1~R6)을 바탕에 넣었다.

## 2. 관문 A
`bash scripts/verify_s1.sh` (2026-10-07, 종료 코드 0)
```
PASS A1 verify_s0.sh 전부 PASS (10개)
PASS A2 ruff 0, pytest 137 passed in 21.63s
PASS A3 새 sources.yaml, link_kinds.yaml 통과 + 잘못된 backfill method, 없는 kind가 경로를 짚어 실패 (3 passed, 49 deselected in 0.89s)
PASS A4 SSRF: 127.0.0.1, 10.0.0.5, 169.254.169.254, [::1], 사설 IP로 리다이렉트, 5MB 초과, 허용 밖 형식 거부 (21 passed, 31 deselected in 0.74s)
PASS A5 오프라인 collect(녹화에 없는 URL은 차단): 소스별 기대 건수, 본문, 링크, 키워드 저장 (1 passed, 51 deselected in 3.16s)
PASS A6 같은 collect 두 번: 항목 수 그대로, 중복 0 (1 passed, 51 deselected in 4.07s)
PASS A7 백필: list_pages(AI타임스)와 day_archive(GeekNews, Simon Willison), 유튜브 채널 목록, --since 앞에서 멈춤 (6 passed, 46 deselected in 2.37s)
PASS A8 실패 격리: 한 소스 500이어도 나머지 수집, fetch_log failed + 실행 기록 attention (1 passed, 51 deselected in 2.42s)
PASS A9 트렌딩 파서: 저장한 주간 페이지 11개(스펙 25개 내외, 지금 GitHub가 11~13개만 보임)와 월간 페이지 25개 전부, stars_this_week 모두 숫자, 빈 페이지는 실패로 기록 (3 passed, 49 deselected in 3.12s)
PASS A10 키워드: 제목 매칭 3점, 단어 경계(eval ≠ evaluate), 제외어 규칙 (1 passed, 51 deselected in 0.71s)
PASS A11 robots: 막힌 경로는 가져오지 않고 기록 (3 passed, 49 deselected in 0.78s)
PASS A12 README와 DEVELOPMENT.md에 수집 명령, reports/S1_report.md
PASS P1 역할 md 검사: 전부 통과 + 섹션 누락, core_rules 4개가 경로를 짚어 실패 (4 passed, 21 deselected in 0.47s)
PASS P2 메시지 조립: system에 입력 없음, <data> → task → 핵심 규칙, 해시는 입력과 무관 (3 passed, 22 deselected in 0.26s)
PASS P3 자료 탈출 방지: </document>, </data> 등이 태그 밖으로 나가지 않음 (8 passed, 17 deselected in 0.11s)
PASS P4 스키마 순서: 모든 출력의 마지막 두 칸 log, attention, basis가 oneliner 앞 (4 passed, 21 deselected in 0.12s)
PASS P5 라벨 도구: --label CSV 생성, 모의 라벨로 --agreement 일치율 (1 passed, 24 deselected in 0.15s)
PASS P6 README 한 줄 소개 + 제목 11개 순서, CI 배지, PR 양식, CI(YAML 통과), RULES.md, ADR 틀 (CI 초록은 PR에서 확인)
PASS R1 태그 탈출 대소문자: </DATA>, </Data >, </document >, <DOCUMENT id="x"> (8 passed, 17 deselected in 0.11s)
PASS R2 채점자 md: 역할 이름 없음, 채점표는 시스템 프롬프트에 한 번 (1 passed, 24 deselected in 0.10s)
PASS R3 도구 예외: 루프가 이어지고 step에 error (1 passed, 24 deselected in 0.21s)
PASS R4 인자 정규화: nullable 칸만, detail에 normalized (2 passed, 23 deselected in 0.25s)
PASS R5 A9 비밀 검사 제외를 실행 산출물로 좁힘(추적 중인 data/ 파일도 검사)
PASS R6 역할 md 검사: roles/*.md + eval/judge.md 통과, 추가 섹션 허용 (3 passed, 22 deselected in 0.47s)
```

## 3. 관문 B 요약
| 대상 | 기준 | 결과 | 판정 |
|---|---|---|---|
| 수집: 글 소스 6곳 기간 덮음 | RSS 또는 백필 | 6곳 모두 | 통과 |
| 수집: 본문 추출 성공률 | 소스별 90% 이상(feed_full 제외) | OpenAI 93%, Anthropic 100%, DeepMind 100%, AI타임스 100%, **GeekNews 77%**(Simon Willison 94%는 feed_full) | 미달 |
| 수집: GeekNews 원문 링크 확보율 | 95% 이상 | 100%(330/330, Show GN 46건 제외) | 통과 |
| 수집: 트렌딩 | 20개 이상, 별 누락 0 | **11개**, 누락 0 | 미달 |
| 수집: 중복 | 0 | 0 | 통과 |
| 1a repo_oneliner(generate) | 코드 채점 10/10, Q1 10/10, Q2·Q3 9/10 | 코드 8/10, Q1·Q2·Q3 8/8(잠정, 프롬프트 `c16be6fbb27f`) | 미달 |

- 리뷰 반영으로 repo_oneliner 예시의 사실 오류를 고쳐 프롬프트가 `e7acab58a7cd`로 바뀌었다. S1 예산이 $0.0145 남아 다시 재지 않았다(재측정은 S2 예산에서, 또는 Q3 결정 뒤)

상세: `reports/S1_collection.md`(사람 확인용 샘플 포함), `reports/S1_quality.md`(repo_oneliner).

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
- [~] 관문 B(repo_oneliner): 3회 개선 후 **미달**(코드 채점 8/10). 아래 1a 관문 B 참고

### 1b 수집
- [x] 설정: sources.yaml(백필 URL을 실제로 확인해 고침, GitHub 트렌딩 페이지), link_kinds.yaml, check-config 스키마(설정 5개)
- [x] safe_fetch(SSRF, 도메인별 1초, robots, 429·5xx 재시도, HTTP 캐시, 5MB, 허용 형식)
- [x] 글 수집(RSS, trafilatura 본문, GeekNews 요약 + 원문 링크, 백필 list_pages/day_archive)
- [x] 유튜브(RSS, yt-dlp 메타데이터, 채널 목록 백필)
- [x] GitHub(트렌딩 주간 페이지, 추적 레포 릴리스, README)
- [x] 링크 판별, 키워드 매칭(제외어 규칙)
- [x] 칠판 테이블 + 마이그레이션(user_version 1)
- [x] CLI collect, items, report collection
- [x] 녹화 응답 픽스처(`tests/fixtures/http/`, 744KB), 테스트, verify_s1.sh A3~A12
- [~] 관문 B: 실제 수집(9/28~10/4) + `reports/S1_collection.md`. 5개 중 3개 통과, 2개 미달(아래)

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
- 다음 시도 후보(설계 세션 결정 필요): README 입력 조립에서 마크다운·HTML 기호를 걷어 낸 본문을 모델에 주고, basis 검사도 그 본문 기준으로(S0_REVIEW 3장의 "README 배지·HTML 정리는 S3 입력 조립 코드에서"와 같은 작업). 채점 기준을 바꾸는 일이라 이번에는 하지 않음

## 1b 관문 B: 수집 (9/28~10/4, 실제 네트워크)
### 미달 1: GeekNews 본문 77% (288/376)
- 원인: GeekNews가 짧은 시간에 토픽 페이지를 25건 안팎 연속으로 받으면 Cloudflare Turnstile **브라우저 확인**(`/topic_browser_check`, 상태 200 또는 302, `x-gn-browser-check: required`)으로 넘긴다. 처음엔 1초 간격으로도 걸렸고, 한 번 걸린 뒤로는 같은 IP의 첫 요청부터 확인을 요구했다(쿠키 유효 24시간). 사이트의 의도적인 봇 보호라 **우회(확인 통과 시도)는 하지 않았다**
- 시도한 것(공통 규칙 3장, 파서·추출 설정)
  1. 실패 이유를 세어 기록(`fetch_errors`): 처음 실행에서 "본문 추출 실패"로만 보이던 것이 확인 페이지임을 찾음
  2. 확인 페이지를 감지하면 그 실행에서 토픽 페이지 요청을 멈추고(attention), 목록(`past?day=`)에서 얻은 원문 링크의 원문 글을 본문으로(요약 대신 원문). 376건 중 GeekNews 요약 43건, 원문 252건
  3. 목록 해석 실패 1회 재시도(AI타임스 AJAX 일시 거부 대응)
- 남은 실패 88건: Show GN 자기 소개 글 46건(본문이 토픽 페이지에만 있음), 원문 사이트 robots.txt 15건, 원문 403 12건, PDF 3건, 읽기 타임아웃 3건, 추출 실패 2건, 짧음 7건. Show GN을 빼도 87%
- 결정 필요(`reports/S1_questions.md` Q1): GeekNews 본문을 무엇으로 할지

### 미달 2: 트렌딩 11개
- GitHub Trending 주간 페이지가 지금 11~13개만 보여 준다(2026-10-07, 일간 12, 주간 11~13, 월간 23~25). 파서는 페이지의 레포 전부를 읽는다(월간 페이지 픽스처 25개로도 테스트)
- 기준을 낮추지 않았고, 다른 페이지를 섞는 것은 출처 정의를 바꾸는 일이라 하지 않음. 결정 필요(Q2)

### 그 밖에 본 것
- AI타임스 AJAX가 처음 녹화 때 한 번 "정상적인 접근이 아닙니다"로 거부했다가 다음엔 통과(일시적). 1회 재시도로 대응
- 유튜브 영상 1편은 채널 회원 전용이라 메타데이터 실패(정상)
- GitHub 비인증 API 한도(시간당 60회)를 시험 수집에서 다 써서 README 403. 본 수집은 `gh` 로그인 토큰을 `GITHUB_TOKEN`으로 넘겨 다시 돌림(토큰은 저장하지 않음)
- 원문이 Hacker News 토론 페이지인 GeekNews 글은 토론 속 링크가 많이 잡힘(curation 링크 839개 중 829개). S3 원본 추적에서 거를 대상

## 4. 결정한 것 (스펙에 없어서 정한 것)
| 결정 | 이유 |
|---|---|
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
| GeekNews 브라우저 확인 감지 시 멈추고 원문 글로 대체 | 위 미달 1. 우회하지 않는 선에서 본문을 최대한 확보 |

## 5. 스펙과 다르게 한 것
| 스펙 | 실제 | 이유 |
|---|---|---|
| 백필 후보 GeekNews `list_pages ?page=` | `day_archive past?day={date}&page={page}` | `?page=`는 추천순이라 날짜로 멈출 수 없음 |
| 백필 후보 AI타임스 `list_pages ?page=` | 1페이지 `sc_sdate/sc_edate` HTML, 2페이지부터 `ajaxArticlePaging.php` | `page` 값이 무시됨(더보기는 JS) |
| Anthropic `list_pages`(페이지 넘김) | 1페이지만(`max_pages: 1`) | 목록에 페이지 넘김이 없음. 피드가 2021년부터 있어 대체 수단 |
| GeekNews 본문 = 토픽 페이지 한국어 요약 | 확인 페이지가 나오면 원문 글(요약은 앞서 받은 43건만). RSS로만 얻은 글은 그날 목록에서 원문 링크를 찾음 | 미달 1. Q1 |
| repo_oneliner 함정 예시 = awesome 목록 레포(S0_ADDENDUM 1.6) | flask(링크 기호가 낀 구절, description과 다른 문구). awesome 목록 규칙은 판단 기준 문장으로 | 1a 관문 B 3회차 개선(실패 원인 두 가지를 한 예시로) |
| 날짜별 아카이브는 요청 기간의 날짜만 | 시작일 하루 전 아카이브부터 | Simon Willison 아카이브는 UTC 날짜라 한국 시간 시작일 0~9시 글이 전날 아카이브에 있음(리뷰 5) |
| README 수정 범위(기능 상태, 빠른 시작, 성과, 로드맵) | 맨 위 "현재 상태" 줄도 S1로 | 같은 파일의 S1 완료 표기와 어긋나서(리뷰 19). 기능 상태의 일부로 봄 |
| A9 "25개 내외" | 저장한 주간 페이지는 11개(실제가 그만큼), 월간 페이지 25개로 함께 테스트 | 미달 2 |
| P6 "README 12개 제목" | 맨 위 한 줄 소개 + 지금 README의 제목 11개(`## 1. 왜 만들었나` … `## 만든 사람`) | 사용자 지시 |
| 허용 콘텐츠 형식 | + `text/javascript`(AI타임스 AJAX가 JSON을 이 형식으로), `application/vnd.github`(raw README) | 실제 응답 형식 |
| `sources.yaml`의 `fallback_list` | 없앰(백필 `list_pages`로 옮겨짐) | S1 묶음의 새 설정 |

## 6. 남은 문제, 다음 스펙 제안
- Q1 GeekNews 본문, Q2 트렌딩 수(`reports/S1_questions.md`)
- 1a 관문 B 미달(코드 채점 8/10): README 마크다운·HTML 정리를 입력 조립에서 할지(S3 레포 분석가와 같은 작업)
- 키워드 조정 후보(S2 전에): `eval`의 "평가"가 "과대평가"에 걸림, `frontier-release`의 GPT·Claude·Gemini가 회사 이름만 나와도 걸려 고객 사례 글이 통과(OpenAI 15건 중 11건 통과), `agent`의 "에이전트"가 넓음. 샘플은 `reports/S1_collection.md` 5장
- S2 입력량 추정: 한 주 키워드 통과 207건(GeekNews 138, AI타임스 43, OpenAI 11, Simon 12, Anthropic 2, DeepMind 1) + 영상 14편. 1차 요약 대상
- 원문 Hacker News 토론 페이지의 링크 소음, PDF 원문(3건)은 S3 원본 추적에서
- DNS 재바인딩: 검사 뒤 httpx가 다시 이름을 푼다(검사와 연결 사이 짧은 틈). 연결 주소 고정은 S3 실제 fetch 도구 전에 검토

## 7. 사용액
`uv run python -m trendsit cost --spec S1` (1b 수집은 LLM 호출 없음, 전부 1a repo_oneliner 관문 B)
```
| 스펙 | 모델 | 호출 | 캐시 적중 | 입력 토큰 | 출력 토큰 | 사용액(달러) |
|---|---|---|---|---|---|---|
| S1 | google/gemini-3.8-flash | 22 | 7 | 48626 | 7294 | 0.021644 |
| S1 | qwen/qwen3.8-27b | 32 | 0 | 85167 | 1836 | 0.013836 |
| 합계 | | | | | | 0.035480 |

- 스펙 S1: 기록 합 $0.035480 / 상한 $0.05
- 단계(mvp) 사용액: $0.087484 / 상한 $20.00, 남은 예산 $19.912516
  - 키 기준(현재 usage − 기준값 $0.483310): $0.087484, 실행 기록 합: $0.087484 (키 반영이 늦으면 큰 쪽 사용)
- 키 limit_remaining: 49.429206287
```

## 7-1. README 갱신, 위키 메모
- README: 핵심 기능 상태(수집 S1 완료), 빠른 시작(`collect`, `report collection`), 성과 표(S1 수집 수치, repo_oneliner 1a), 로드맵 체크. 1a에서는 CI 배지만
- 위키 메모
  - GeekNews 브라우저 확인: 1초 간격 25건 안팎에서 Turnstile 확인으로 넘어감 → 우회하지 않고 감지해서 멈추고 원문으로 대체. 실패 이유를 세지 않아 처음엔 "본문 추출 실패"로만 보였던 것이 교훈
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
