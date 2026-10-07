# S1. 수집 (얕게 훑기의 코드 부분) + 백필

> 먼저 읽을 것: `docs/handoff/COMMON.md`(갱신됨: 8장 MVP 순서, 6.1 역할 md 작성 규칙, 2장 관문 B 예/아니오 채점과 judge 맞추기) → `docs/handoff/S0_ADDENDUM.md`(1a 단계) → `docs/handoff/S0_REVIEW.md`(1a 단계, S0 리뷰 반영) → 이 문서 → 필요할 때 `docs/reference/agents_spec.md`(0.4 깊이 규칙), `docs/reference/sources_keywords.md`.
> 작성: 2026-10-07. 전제: S0이 병합된 상태(PR #1, 2026-10-07 병합. S0_ADDENDUM은 S0에 들어가지 않았으므로 1a를 건너뛰지 않는다). 브랜치 `s1-collect`. **예산 상한 0.05달러**(1a S0 보완의 관문 B 재실행만. 수집 1b는 LLM 호출 없음).
> 단계: **1a S0 보완**(`S0_ADDENDUM.md`: 프롬프트 규칙 + 레포 문서 틀(README 골격, PR 양식, CI, ADR 틀), S0 PR에서 이미 했으면 건너뛰고 리포트에 적음) → **1b 수집**(이 문서 0~9장). 단계마다 커밋과 리포트 체크리스트를 따로 둔다(COMMON 8장).

## 0. 이 스펙이 끝나면 되는 것 (한 줄)
`trendsit collect --since 2026-10-12 --until 2026-10-18`처럼 **기간을 주면 글 6곳, 유튜브 1곳, GitHub 트렌딩과 추적 레포에서 그 기간 항목을 빠짐없이 모아(RSS가 짧으면 목록 페이지로 백필) 본문, 링크 종류, 키워드 매칭까지 칠판에 저장**하고, 수집 리포트가 나온다. 같은 명령을 다시 돌려도 중복이 생기지 않는다.

## 1. 맥락
- 02:00 흐름은 "① 얕게 훑기(깊이 1) → ② 편집장 계획 → ③ 깊게 → ④ 묶기"(agents_spec 0.4). S1은 ①의 **코드 부분**만: 수집, 본문 추출, 링크 판별, 키워드 매칭. ①의 LLM 부분(글 1차 요약)은 S2
- 수집은 매일 미리 돌리지 않는다. **필요할 때 지난 기간을 한 번에 긁어오는 백필**이 기본 사용법이다. 2026-10-07 확인: GeekNews RSS는 최근 50건(약 24시간), AI타임스는 50건(약 1.5일), Simon Willison은 20건(약 9일)만 담는다
- GitHub 트렌딩은 **GitHub Trending 주간 페이지만** 쓴다. OSS Insight Trends API는 현재 빈 데이터를 돌려준다(이벤트 수집 저하). 별 스냅샷은 하지 않고 페이지의 "이번 주 별" 수치를 그대로 쓴다. 이 페이지는 과거 기록이 없어 **실행한 그 시점의 주간 목록만** 얻는다
- 수집한 글은 이후 S3 글 분석가의 원본 추적 재료가 된다. 그래서 본문 속 링크와 그 종류(논문, 공식 블로그, 레포 등)를 지금 저장한다

## 2. 준비물
| 준비물 | 할 일 | 없으면 |
|---|---|---|
| S0 병합 | `main`에서 브랜치 | S0 PR 상태를 리포트에 적고 멈춤 |
| `GITHUB_TOKEN` (선택) | README, 릴리스 조회에 사용 | 비인증(시간당 60회)으로. 부족하면 README는 상위 일부만 |
| yt-dlp (선택, `video` 묶음) | 유튜브 메타데이터(길이, 자막 트랙, 챕터) | RSS 필드만 저장하고 경고. 클라우드 IP에서 막히면 같음 |
| 네트워크 | 실제 수집은 관문 B에서 1회 | 테스트는 저장한 응답으로 오프라인 |

## 3. 범위
### 3.1 만든다
0. (1a) `S0_ADDENDUM.md`의 1장 전부: 역할 md 앞부분 task·core_rules, 메시지 조립, render_data, 스키마 칸 순서, 역할 md 검사, repo_oneliner 다시 쓰기, 예/아니오 채점, 라벨 도구, AGENTS.md 수정(예산 20달러 포함), 레포 문서 틀 + `S0_REVIEW.md`의 R1~R6(태그 탈출 대소문자, 채점자 md 일반화, 도구 예외를 결과로, nullable 인자 정규화, 비밀 검사 범위, 역할 md 검사 범위)
1. 설정 갱신: `config/sources.yaml`(이 묶음의 새 버전으로 교체: 백필 방법, GitHub 트렌딩 출처), 새 `config/link_kinds.yaml`. `check-config` 스키마 갱신
2. `safe_fetch`: SSRF 방어, 예의(속도 제한, User-Agent, robots), 재시도, HTTP 캐시
3. 수집기: 글(RSS + 본문 추출 + 백필), 유튜브(RSS + 메타데이터 + 백필), GitHub(트렌딩 페이지 + 추적 레포 릴리스 + README 앞부분)
4. 링크 판별(link_kinds), 키워드 매칭(keywords.yaml, 제외어 규칙)
5. 칠판 테이블(아래 5.6)과 마이그레이션
6. CLI: `collect`, `items`, `report collection`
7. 저장한 응답 픽스처, 테스트, `scripts/verify_s1.sh`, `reports/S1_report.md`, `reports/S1_collection.md`

### 3.2 만들지 않는다
LLM 요약과 임베딩(S2), 원본 따라가기와 레포 분석(S3), 영상 다운로드와 전사(S4), 묶기(S5), 스케줄 실행(S6), 별 스냅샷

## 4. 폴더 (S0 구조에 추가)
```
trendsit/
  collect/
    fetch.py          safe_fetch, 속도 제한, robots, HTTP 캐시
    text.py           RSS → 항목, 본문 추출, 백필(list_pages, day_archive)
    sites/            사이트별 파서: geeknews.py, aitimes.py, simonw.py, anthropic.py
    youtube.py        채널 RSS, 메타데이터, 채널 목록 백필
    github.py         트렌딩 페이지 파서, 릴리스 피드, README
    links.py          링크 추출, 종류 판별
    keywords.py       키워드 매칭, 제외어
  core/db.py          마이그레이션 추가
tests/fixtures/http/  저장한 응답 (피드, 목록 페이지, 글 페이지, 트렌딩 페이지)
```

## 5. 상세 요구사항

### 5.1 safe_fetch (`collect/fetch.py`)
- http, https만. 호스트를 DNS로 풀어 **사설, 루프백, 링크로컬, 멀티캐스트, 예약 대역(IPv4, IPv6 모두)**이면 거부. 리다이렉트마다(최대 5회) 다시 검사
- 시간 제한(연결 5초, 읽기 15초), 크기 상한 5MB, 허용 콘텐츠 형식(html, xml, rss/atom, json, text)
- User-Agent: `TrendsIT/0.1 (+https://trendsit.jiseop.com)`
- 같은 도메인은 1초에 1번. 429, 5xx는 지수 백오프 재시도 3회(`Retry-After` 존중)
- robots.txt: **목록 페이지, 아카이브, 글 페이지**는 도메인별 robots.txt를 캐시해 확인하고, 막혀 있으면 가져오지 않고 기록(피드 URL은 기계용이므로 확인 생략 가능, 리포트에 방침 적기)
- HTTP 캐시 `data/http_cache/`(git 제외): URL 키, ETag/Last-Modified 조건부 요청. `--no-http-cache`로 끔
- 결과: `FetchResult(url, final_url, status, content_type, text, fetched_at, from_cache, error)`
- 테스트: `127.0.0.1`, `10.0.0.5`, `169.254.169.254`, `[::1]`, 사설 IP로 리다이렉트하는 공개 URL(모의), 5MB 초과, 허용 밖 형식

### 5.2 글 수집 (`collect/text.py`, `collect/sites/`)
- RSS/Atom 파싱 → 항목. `external_id` = 정규화한 URL(추적 파라미터 `utm_*`, `ref` 제거, 끝 슬래시 통일)의 해시
- `fetch` 방식대로 본문 확보: `feed_full`은 피드 본문, 나머지는 원글 페이지를 safe_fetch → trafilatura로 본문 추출. 추출 실패나 300자 미만이면 `body_status=short|failed`
- **GeekNews 토픽 페이지:** GeekNews의 한국어 요약 본문과 **원문 링크(토픽이 가리키는 바깥 URL)**를 따로 저장. 원문 링크는 `links`에 `role=origin_candidate`로
- 본문 속 모든 바깥 링크를 `links`에 저장하고 `link_kinds.yaml`로 종류 판별
- 기간 필터: `published_at`이 `--since ~ --until`(한국 시간) 안인 항목만
- **백필:** 요청 기간의 시작이 RSS의 가장 오래된 항목보다 앞서면 그 소스의 `backfill.method`로 거슬러 읽는다
  - `list_pages`: `{page}`를 1부터 올리며 목록 페이지를 읽고, 항목 날짜가 `--since`보다 앞서면 멈춤(상한 50페이지)
  - `day_archive`: 기간의 날짜마다 아카이브 페이지
  - `rss_only`: 백필 없음. RSS가 기간을 못 덮으면 리포트에 "부족"으로 기록
  - **백필 URL 후보(sources.yaml)는 설계 세션이 확인하지 못했다.** 구현 전에 실제로 열어 구조를 확인하고, 다르면 고친 뒤 리포트 표에 적는다(GeekNews 목록은 JS 없이 열리는지, AI타임스 `page` 값이 실제로 과거로 가는지 특히)
- 게시 시각이 없는 항목은 수집 시각으로 두고 `published_estimated=true`

### 5.3 유튜브 (`collect/youtube.py`)
- 채널 RSS(최근 15편) → 항목(video_id, 제목, 게시 시각, 설명, 썸네일 URL)
- 메타데이터(`video` 묶음이 있을 때): yt-dlp **다운로드 없이** 정보만(길이, 수동 자막 트랙 언어, 자동 자막 유무, 챕터). 없거나 실패하면 null + 경고. 이 정보는 편집장 계획(S3)의 처리 깊이 판단 재료
- 백필: RSS가 기간을 못 덮으면 yt-dlp 채널 목록(다운로드 없음)으로. 불가하면 리포트에 "부족"

### 5.4 GitHub (`collect/github.py`)
- **트렌딩 주간 페이지 파서:** 레포마다 `full_name, description, language, stars_total, forks, stars_this_week, rank`. 실행 주차(ISO, 한국 시간)로 `repo_trending`에 저장. 파서는 저장한 페이지 픽스처로 테스트하고, 실제 페이지 구조가 바뀌어 0건이면 **실패로 기록**(조용히 빈 결과 금지)
- 추적 레포: `releases.atom`에서 기간 안 릴리스 → 항목(channel=github, kind=release, 태그, 날짜, 노트 앞부분)
- README 앞부분(3,000자): 추적 레포 4개 + 키워드에 걸린 트렌딩 레포만 GitHub API로(깊이 1 재료, S0의 repo_oneliner 입력 형식과 맞춤)

### 5.5 키워드 매칭 (`collect/keywords.py`)
- `keywords.yaml`의 별칭을 제목, 요약, 본문 앞 2,000자에서 찾음. 영어 별칭은 단어 경계, 한국어는 부분 문자열, 대소문자 무시
- 점수 = 제목 매칭 × 3 + 본문 매칭 × 1(같은 키워드 중복은 1회). `filter_status`: 점수 1 이상이면 `pass`, 아니면 `filtered`
- 제외어: 제외어가 있고 제목에 포함 키워드가 하나도 없으면 `filtered`(이유 `excluded:<단어>`)
- **걸러진 항목도 지우지 않는다.** 이유와 함께 저장해 놓친 글을 사람이 확인할 수 있게
- 레포는 description, topics, README 앞부분으로 같은 방식

### 5.6 칠판 테이블 (`core/db.py`, 마이그레이션 `PRAGMA user_version`)
설계 세션 문서 25 초안의 일부. 칸은 늘려도 되고 이름은 유지.
```
sources(id TEXT PK, channel, kind, name, feed, enabled, config_json)      -- config에서 동기화
fetch_log(id, run_id, source_id, day, status CHECK(ok|failed|partial), n_new, n_backfilled, error)
items(id INTEGER PK, source_id, channel CHECK(text|video|github), kind, external_id, url, title,
      published_at, published_estimated, day, week, summary_feed, body_status,
      filter_status CHECK(pass|filtered), filter_reason, score, run_id, created_at,
      UNIQUE(source_id, external_id))
item_texts(item_id PK, text, origin_summary, expires_at)                  -- 본문, GeekNews 요약
item_keywords(item_id, keyword_id, where_matched, PRIMARY KEY(item_id, keyword_id))
links(id, item_id, url, anchor, kind, role CHECK(body|origin_candidate), UNIQUE(item_id, url))
videos(item_id PK, video_id, duration_sec, manual_sub_langs, has_auto_sub, chapters_json, meta_status)
repos(full_name PK, description, language, topics_json, readme_head, first_seen)
repo_trending(week, full_name, rank, stars_total, stars_this_week, forks, run_id, PRIMARY KEY(week, full_name))
```
- `day`, `week`는 한국 시간 기준, 주는 월~일(ISO). `item_texts.expires_at` = 수집 + 8주(저작권, 이후 본문만 지움)
- 같은 항목을 다시 수집하면 갱신하지 않고 건너뜀(본문이 비었던 항목만 다시 시도)

### 5.7 CLI
| 명령 | 하는 일 |
|---|---|
| `collect [--source ID] [--since DATE] [--until DATE] [--no-body] [--no-http-cache]` | 기간 수집. 기본 기간은 최근 1일. 실행마다 runs 1행, 소스마다 fetch_log |
| `items [--week W] [--source ID] [--status pass\|filtered] [--limit N]` | 항목 목록(제목, 소스, 날짜, 상태, 키워드) |
| `report collection [--since] [--until]` | `reports/S1_collection.md` 생성(아래 7장 항목) |

### 5.8 실행 기록
- 수집 실행도 S0의 runs/steps에 남긴다: `kind='collect'`, 소스마다 step 하나(`kind='code'`, text 예 "geeknews: 신규 312건, 백필 7페이지, 본문 실패 4건", 실패면 attention=true)
- 이 기록이 이후 실행 기록 화면의 "매일 수집" 줄이 된다

## 6. 관문 A (verify_s1.sh)
| # | 항목 | 확인 방법 |
|---|---|---|
| A1 | S0 회귀 | `verify_s0.sh` 통과 |
| A2 | 정적 검사, 테스트 | ruff 0, pytest 전부 통과 |
| A3 | 설정 | 새 sources.yaml, link_kinds.yaml이 check-config 통과. 잘못된 backfill method, 없는 kind가 경로를 짚어 실패 |
| A4 | SSRF | 5.1의 위험 주소 6종이 모두 거부(테스트) |
| A5 | 오프라인 수집 | 픽스처만으로 `collect`(네트워크 차단 모의) → 소스별 기대 건수, 본문, 링크, 키워드가 저장 |
| A6 | 멱등 | A5를 두 번 돌려도 항목 수 그대로, 중복 0 |
| A7 | 백필 | 목록 페이지 픽스처로 `--since`가 RSS보다 앞선 경우 백필이 돌고 `--since` 앞에서 멈춤. day_archive도 같음 |
| A8 | 실패 격리 | 한 소스를 500으로 모의해도 나머지는 수집되고, fetch_log에 failed + 실행 기록 attention |
| A9 | 트렌딩 파서 | 저장한 트렌딩 페이지에서 25개 내외, stars_this_week 모두 숫자. 빈 페이지면 실패로 기록 |
| A10 | 키워드 | 제목 매칭, 단어 경계(eval이 evaluate에 안 걸림), 제외어 규칙 테스트 |
| A11 | robots | robots.txt가 막은 경로는 가져오지 않고 기록 |
| A12 | 문서 | README에 수집 명령, `reports/S1_report.md` |
| P1~P6 | S0 보완(1a) | `S0_ADDENDUM.md` 2장 표. S0 PR에서 이미 했으면 verify_s0.sh에 있으므로 A1 회귀로 확인 |
| R1~R6 | S0 리뷰 반영(1a) | `S0_REVIEW.md` 4장 표 |

## 7. 관문 B (수집 품질, 실제 네트워크 1회)
- 실행: `collect --since 2026-09-28 --until 2026-10-04`(실행일 기준 이미 끝난 가장 최근 한 주, 월~일. 10/9에 돌리면 이 기간. 10/12 이후에 돌리면 10/5~10/11로 바꾸고 리포트에 적음) → `report collection`. GitHub 트렌딩은 과거 기록이 없어 실행 시점의 주간 목록이므로 기간이 다르다고 표시
- `reports/S1_collection.md`에 넣을 것
  1. 소스별 표: RSS로 덮은 기간, 백필 방법과 페이지 수, 신규 건수, 본문 추출 성공률, 키워드 통과율, 실패
  2. 백필 URL 확인 결과(설정 후보와 실제가 다르면 고친 값)
  3. GitHub: 트렌딩 레포 수, 키워드 통과 레포, 추적 레포 릴리스 수
  4. 유튜브: 영상 수, 메타데이터 성공 여부
  5. **사람 확인용 샘플:** 소스별로 걸러진 글 제목 5개 + 통과한 글 제목 5개(놓친 글, 잘못 통과한 글을 사용자가 표시할 수 있게 체크 칸)
  6. 링크 종류 분포(paper, official, repo 등)와 GeekNews 원문 링크 확보율
- 문턱값

| 항목 | 기준 |
|---|---|
| 글 소스 6곳 모두 기간을 덮음 | RSS 또는 백필로. 못 덮으면 이유가 리포트에 있어야 함 |
| 본문 추출 성공률 | 소스별 90% 이상(`feed_full` 제외). 미달 소스는 원인과 개선 시도 기록 |
| GeekNews 원문 링크 확보율 | 95% 이상 |
| 트렌딩 | 20개 이상, stars_this_week 누락 0 |
| 중복 | 0 |
- 미달이면 공통 규칙 3장대로 최대 3회 개선(파서, 추출 설정 수정. 기준 낮추기 금지)

## 8. 예산
- 1a S0 보완: 0.05달러 이내(repo_oneliner 관문 B 재실행). `config/budget.yaml`의 `specs.S1: 0.05`
- 1b 수집: LLM 호출 없음. `cost --spec S1`의 1b 몫은 0

## 9. 완료 시 넘길 것
- README 갱신: 1b가 끝나면 핵심 기능, 빠른 시작(`collect`), 로드맵 체크, 성과 표에 수집 수치(소스별 건수, 본문 추출 성공률)
- PR `s1-collect`: 관문 A 출력, 관문 B 요약 표(수집 + repo_oneliner 예/아니오 통과율), 백필 URL 확인 결과
- `eval/labels/repo_oneliner.csv`(사용자가 리뷰 때 채울 라벨 파일)
- `reports/S1_report.md`, `reports/S1_collection.md`(사람 확인용 샘플 포함)
- 다음 스펙(S2 글 1차 요약)을 위한 제안: 소스별 통과량(LLM 요약 대상 수 추정), 키워드 조정 후보
