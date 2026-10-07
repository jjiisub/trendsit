# S1 수집 리포트 (2026-09-28 ~ 2026-10-04)

> `python -m trendsit report collection`이 생성한다. 기간은 한국 시간 게시일 기준. GitHub 트렌딩은 과거 기록이 없어 실행 시점의 주간 목록이다(기간과 다름).

## 1. 소스별

본문 추출 성공률의 분모는 원문 링크가 있는 글에서 의도적으로 건너뛴 것(robots 차단, PDF 등 허용 밖 형식, 영상)을 뺀 수. 403 같은 실패는 실패로 센다(설계 결정 Q1).

| 소스 | 받는 방식 | RSS 가장 오래된 날 | 기간 덮음 | 백필(방법, 페이지) | 기간 안 항목 | 백필로 얻음 | 본문 추출 성공 | 의도적 건너뜀 | 키워드 통과 | 실패, 메모 |
|---|---|---|---|---|---|---|---|---|---|---|
| openai | feed_summary | 2015-12-11 | 예 | rss_only, 0 | 15 | 0 | 93% (14/15) | - | 73% (11/15) | - |
| anthropic | feed_summary | 2021-05-28 | 예 | list_pages, 0 | 2 | 0 | 100% (2/2) | - | 100% (2/2) | - |
| deepmind | feed_summary | 2025-11-11 | 예 | rss_only, 0 | 2 | 0 | 100% (2/2) | - | 50% (1/2) | - |
| geeknews | list_origin | - | 예 | day_archive, 23 | 319 | 319 | 93% (274/294) | robots 차단 18, 허용 밖 형식(PDF 등) 4, 영상 3 | 37% (117/319) | 자기 글(Show GN 등) 57건 제외; robots.txt가 막음 16건; HTTP 403 12건; 본문 추출 실패 4건; 허용 밖 형식: application/pdf 4건; 영상 링크 3건 |
| simonw | feed_full | 2026-09-28 | 예 | day_archive, 2 | 18 | 1 | 94% (17/18) | - | 67% (12/18) | - |
| aitimes | feed_summary | 2026-10-06 | 예 | list_pages, 11 | 188 | 188 | 100% (188/188) | - | 56% (106/188) | - |
| techbridge | rss + yt-dlp | 2026-10-02 | 예 | channel_listing, 1 | 17 | 10 | 94% (16/17) | - | 82% (14/17) | - |

### 하루 신규 건수(게시일, 한국 시간)

| 소스 | 09-28 | 09-29 | 09-30 | 10-01 | 10-02 | 10-03 | 10-04 | 하루 평균 |
|---|---|---|---|---|---|---|---|---|
| openai | 3 | 5 | 2 | 1 | 3 | 1 | 0 | 2.1 |
| anthropic | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0.3 |
| deepmind | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0.3 |
| geeknews | 54 | 50 | 37 | 51 | 51 | 34 | 42 | 45.6 |
| simonw | 5 | 3 | 4 | 2 | 1 | 1 | 2 | 2.6 |
| aitimes | 31 | 31 | 30 | 40 | 30 | 14 | 12 | 26.9 |
| techbridge | 2 | 2 | 2 | 3 | 3 | 2 | 3 | 2.4 |

## 2. 백필 URL 확인 (2026-10-07 실제로 열어 봄)

| 소스 | handoff 후보 | 지금 설정 | 확인 결과 |
|---|---|---|---|
| openai | `rss_only` | `rss_only` | 후보 그대로 |
| anthropic | `list_pages https://www.anthropic.com/news` | `list_pages https://www.anthropic.com/news` | 목록은 최신 10건 안팎, 페이지 넘김 없음. 커뮤니티 피드가 2021년부터 담고 있어 대체 수단으로만 |
| deepmind | `rss_only` | `rss_only` | 후보 그대로 |
| geeknews | `RSS + list_pages https://news.hada.io/?page={page}` | `day_archive https://news.hada.io/past?day={date}&page={page}` | 설계 결정(Q1): RSS·상세 페이지를 쓰지 않음. 평소는 메인(점수순) 1~2페이지, 지난 기간은 날짜별 목록 past?day=(20건씩 페이지). 본문은 원문 링크에서 |
| simonw | `day_archive https://simonwillison.net/{yyyy}/{Mon}/{d}/` | `day_archive https://simonwillison.net/{yyyy}/{Mon}/{d}/` | 후보 그대로 동작(조각마다 고유 주소, 시각) |
| aitimes | `list_pages https://www.aitimes.com/news/articleList.html?page={page}&view_type=sm` | `list_pages https://www.aitimes.com/news/articleList.html?sc_sdate={since}&sc_edate={until}&view_type=sm / 2페이지부터 https://www.aitimes.com/news/ajaxArticlePaging.php?page={page}&list_per_page=20&page_per_page=10&sc_sdate={since}&sc_edate={until}&sc_order_by=E&view_type=sm` | 목록의 page 값이 무시됨(더보기는 JS) → 1페이지는 sc_sdate/sc_edate로 거른 HTML, 2페이지부터 ajaxArticlePaging.php(JSON) |
| techbridge | `channel_listing (yt-dlp)` | `channel_listing` | yt-dlp 채널 목록(flat, approximate_date) 동작. 정확한 시각은 영상별 메타데이터 |

## 3. GitHub

- 트렌딩(주간 페이지, 실행 주차 2026-W41): 페이지에 보인 11개 중 11개 저장, 키워드 통과 5개, 이번 주 별 누락 0개
- 추적 레포 릴리스(기간 안): 18건 — anthropics/claude-code v2.1.284(2026-09-29), anthropics/claude-code v2.1.285(2026-09-30), anthropics/claude-code v2.1.286(2026-10-01), ollama/ollama v0.35.1-rc1(2026-10-02), ollama/ollama v0.35.1-rc2(2026-10-02), anthropics/claude-code v2.1.287(2026-10-02), NousResearch/hermes-agent v0.21.4+canary.20261002T070111Z(2026-10-02), NousResearch/hermes-agent v0.21.4+canary.20261003T070620Z(2026-10-03), NousResearch/hermes-agent rc.34-v0.21.5(2026-10-03), NousResearch/hermes-agent abandoned-rc.33-v0.21.5(2026-10-03), NousResearch/hermes-agent rc.35-v0.21.5(2026-10-03), ollama/ollama v0.35.1(2026-10-03)

| 순위 | 레포 | 이번 주 별 | 전체 별 | 키워드 | 상태 |
|---|---|---|---|---|---|
| 1 | mvschwarz/openrig | 3327 | 5638 | agent, coding-agent, frontier-release | pass |
| 2 | boykopovar/AnyPS5 | 3073 | 8548 | - | filtered |
| 3 | heygen-com/hyperframes | 3614 | 58269 | agent, mcp-tools | pass |
| 4 | cursor/plugins | 1106 | 10190 | - | filtered |
| 5 | NVIDIA/OpenShell | 5228 | 15216 | agent | pass |
| 6 | Panniantong/Agent-Reach | 6454 | 92975 | agent, mcp-tools, frontier-release | pass |
| 7 | thedotmack/claude-mem | 2104 | 97448 | agent, coding-agent, rag-search, frontier-release | pass |
| 8 | pablostanley/yoinks | 2947 | 4998 | - | filtered |
| 9 | DuarteSantos8/openGym | 3318 | 6429 | - | filtered |
| 10 | tile-ai/tilelang | 675 | 8463 | - | filtered |
| 11 | HunxByts/GhostTrack | 2017 | 17311 | - | filtered |

## 4. 유튜브 (Tech Bridge)

- 영상 17편, 메타데이터 성공 94% (16/17)

| 날짜 | 제목 | 길이(초) | 수동 자막 | 자동 자막 | 챕터 수 | 얻은 곳 |
|---|---|---|---|---|---|---|
| 2026-09-28 | [한영자막] Claude Code와 Codex를 인간 연구자들과 경쟁시켰습니다 — Elie | 1148 | [] | 있음 | 9 | backfill |
| 2026-09-28 | [한영자막] AI 에이전트를 위한 문서 컨텍스트 레이어 구축하는 법 — Jerry Liu, | 1233 | [] | 있음 | 11 | backfill |
| 2026-09-29 | [한영자막] MS 사티아 나델라가 밝힌 AI 미래: 코파일럿과 오토파일럿, 그리고 다가올  | 1547 | [] | 있음 | 11 | backfill |
| 2026-09-29 | [한영자막] 스스로 개선되는 AI 에이전트는 어떻게 만들었을까요? | Weights & B | 993 | [] | 있음 | 19 | backfill |
| 2026-09-30 | [한영자막] 루프 자체가 제품입니다 — xAI 출신 창업자가 밝히는 차세대 AI 에이전트의 | 1095 | [] | 있음 | 18 | backfill |
| 2026-09-30 | [한영자막] 자는 동안 스스로 학습하는 AI: 단순 기억을 넘어 꿈으로 진화하는 에이전트의 | 1887 | [] | 있음 | 8 | backfill |
| 2026-10-01 | [한영자막] 공장이 아니라 오케스트라입니다: 최고 속도로 개발하는 사람들의 일하는 방식 | 1016 | [] | 있음 | 13 | backfill |
| 2026-10-01 | [한영자막] 진짜 '소프트웨어 팩토리'를 만들려면 무엇이 필요할까요? — Factory T | 1315 | [] | 있음 | 28 | backfill |
| 2026-10-01 | [한영자막] AI가 여러분의 데이터를 노출하고 있습니다: 눈에 보이지 않는 AI 보안의 숨 | 675 | [] | 있음 | 7 | backfill |
| 2026-10-02 | [한영자막] AI 시대, 스펙 기반 개발(SDD)을 실무에 적용하며 배운 교훈들 | 1841 | [] | 있음 | 9 | rss |
| 2026-10-02 | [한영자막] 소프트웨어 엔지니어링은 이제 소프트웨어 공장을 짓는 일이 될 것입니다 — Za | 1209 | [] | 있음 | 29 | rss |
| 2026-10-02 | [한영자막] 400개 기업 데이터로 본 소프트웨어 개발 AI의 현주소입니다 | 1122 | [] | 있음 | 14 | rss |
| 2026-10-03 | [한영자막] 코드 리뷰의 종말: 데이터가 보여주는 진짜 현실입니다 | 1451 | [] | 있음 | 21 | rss |
| 2026-10-03 | Lauren Tan(SpaceX - Cursor & Grok Bot 개발자)의 AI 에이전 | 696 | [] | 있음 | 15 | rss |
| 2026-10-04 | [한영자막] 팟캐스트 풀버전 - SpaceX에서 매달 수천 개의 PR을 반영하는 방법을 알 | None | - | 없음 | 0 | backfill |
| 2026-10-04 | [한영자막] 글을 쓰지 않는 AI 모델? Jev의 정체는 무엇일까요? | 891 | [] | 있음 | 10 | rss |
| 2026-10-04 | AI로 무엇이든 효과적으로 학습하는 방법 | 1006 | [] | 있음 | 18 | rss |

## 5. 사람 확인용 샘플

걸러진 글 중 놓친 것, 통과한 글 중 잘못 통과한 것에 체크한다.

### openai
- 걸러진 글
  - [ ] 놓침 · Helping small businesses put AI to work (no_keyword)
  - [ ] 놓침 · How Albertsons Companies is reimagining retail from the inside out (no_keyword)
  - [ ] 놓침 · The Den frees up 10-15 hours a week to grow with ChatGPT Work (no_keyword)
  - [ ] 놓침 · The Lenfest Institute grows landmark program with expanded OpenAI support (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · A model guide for the GPT-6 family (점수 4)
  - [ ] 잘못 통과 · Are you a Codex Original? (점수 3)
  - [ ] 잘못 통과 · Introducing GPT-6.1 Sol (점수 5)
  - [ ] 잘못 통과 · Chatham scales its capital markets expertise with OpenAI (점수 2)
  - [ ] 잘못 통과 · The eternal complement (점수 1)

### anthropic
- 걸러진 글
  - (없음)
- 통과한 글
  - [ ] 잘못 통과 · Barclays scales Claude to upgrade operations and improve client experience (점수 5)
  - [ ] 잘못 통과 · Anthropic invests $100 million to train 10,000 engineers and tackle the enterpri (점수 1)

### deepmind
- 걸러진 글
  - [ ] 놓침 · Introducing SynthID Bio (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · Gemini 4 Argon: our next era of frontier intelligence (점수 5)

### geeknews
- 걸러진 글
  - [ ] 놓침 · 로댕 박물관 3D 스캔 판결의 배신 (no_keyword)
  - [ ] 놓침 · Ledge.sh - 실행 가능한 Markdown 노트 (no_keyword)
  - [ ] 놓침 · Newgrounds - 게임·애니메이션·음악·그림을 공유하는 창작 커뮤니티 (no_keyword)
  - [ ] 놓침 · Bob Cringely 별세 (no_keyword)
  - [ ] 놓침 · Debian, 커널 CVE 1,313건을 담은 보안 업데이트 공개 (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · 바이브 코딩한 웹사이트를 디자이너가 만든 것처럼 보이게 한 방법 (점수 2)
  - [ ] 잘못 통과 · Anthropic의 IPO 투자설명서에 담긴 AI 비전과 급증하는 비용 (점수 3)
  - [ ] 잘못 통과 · NobodyWho - 앱과 게임에 로컬 AI를 넣는 온디바이스 추론 엔진 (점수 3)
  - [ ] 잘못 통과 · Pi 1.0 출시 - 미니멀한 터미널 코딩 에이전트 (점수 7)
  - [ ] 잘못 통과 · 컨텍스트 언어 모델 - 자신의 컨텍스트를 직접 편집하는 AI (점수 2)

### simonw
- 걸러진 글
  - [ ] 놓침 · sighting 404239413 (no_keyword)
  - [ ] 놓침 · S3 Is the Future, S3 Is the Past (no_keyword)
  - [ ] 놓침 · Rex's Dino Store (no_keyword)
  - [ ] 놓침 · He Built This City (no_keyword)
  - [ ] 놓침 · September sponsors-only newsletter (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · GPT 6.1 Sol: Near-Astra intelligence for a fifth of the price (점수 3)
  - [ ] 잘못 통과 · 2026 in LLMs (so far) (점수 6)
  - [ ] 잘못 통과 · llm-anthropic 0.30 (점수 1)
  - [ ] 잘못 통과 · We're going to need default hard budget caps on pretty much everything (점수 1)
  - [ ] 잘못 통과 · Claude Sonnet 5.5 (점수 5)

### aitimes
- 걸러진 글
  - [ ] 놓침 · [AI카툰] Bob, Senior IT guy - 밥, AI가 못 들어가는 틈새시장 개발자 (no_keyword)
  - [ ] 놓침 · 정부, 송전망 수용량 52GW 늘린다…2030년 재생에너지 100GW 대응 (no_keyword)
  - [ ] 놓침 · 브록먼 오픈AI 사장, 사내 반발에 '친AI' 정치 단체 340억 추가 기부 철회 (excluded:정치)
  - [ ] 놓침 · 저커버그·아모데이·젠슨 황, 29일 트럼프와 백악관서 AI 정책 논의 (excluded:정치)
  - [ ] 놓침 · 미 재무장관 "AI 정부 규제 요구하는 CEO들은 한니발 렉터와 같아" (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · "아스트라급 지능을 5분의 1 가격에"…오픈AI, 'GPT-6.1 솔' 공개 (점수 5)
  - [ ] 잘못 통과 · 앤트로픽, IPO 신청서에 "AI의 실존적 위험" 공식 경고 (점수 2)
  - [ ] 잘못 통과 · 오픈AI, 반도체 설계 전용 'GPT-시놉시스' 개발 합의…'수익 공유' 적용 (점수 4)
  - [ ] 잘못 통과 · 오퍼스 5.5, 자기개선 평가서 1위…'완전 RSI' 내년 7월로 앞당겨 (점수 5)
  - [ ] 잘못 통과 · 오픈클로, 기업용 AI 에이전트 제어 플랫폼 'OCE' 공개 (점수 4)

### techbridge
- 걸러진 글
  - [ ] 놓침 · AI로 무엇이든 효과적으로 학습하는 방법 (no_keyword)
  - [ ] 놓침 · [한영자막] 400개 기업 데이터로 본 소프트웨어 개발 AI의 현주소입니다 (excluded:채용)
  - [ ] 놓침 · [한영자막] 팟캐스트 풀버전 - SpaceX에서 매달 수천 개의 PR을 반영하는 방법을 알아봅니다 | Cursor & Grok Bot 개발자 L (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · [한영자막] AI 에이전트를 위한 문서 컨텍스트 레이어 구축하는 법 — Jerry Liu, LlamaIndex (점수 6)
  - [ ] 잘못 통과 · [한영자막] Claude Code와 Codex를 인간 연구자들과 경쟁시켰습니다 — Elie Bakouch, Prime Intellect (점수 8)
  - [ ] 잘못 통과 · [한영자막] 진짜 '소프트웨어 팩토리'를 만들려면 무엇이 필요할까요? — Factory Tereza (점수 4)
  - [ ] 잘못 통과 · [한영자막] 루프 자체가 제품입니다 — xAI 출신 창업자가 밝히는 차세대 AI 에이전트의 핵심 (점수 4)
  - [ ] 잘못 통과 · [한영자막] MS 사티아 나델라가 밝힌 AI 미래: 코파일럿과 오토파일럿, 그리고 다가올 제품 경쟁 (점수 1)

## 6. 링크

| 종류 | 링크 수 |
|---|---|
| other | 1757 |
| curation | 838 |
| repo | 232 |
| social | 167 |
| official | 103 |
| paper | 72 |
| news | 27 |
| press | 16 |

- GeekNews 원문 링크 확보율: 100% (319/319) (원문 링크가 GeekNews 자신인 글 57건은 수집에서 뺌)
- 원문이 Hacker News 토론 페이지인 GeekNews 글은 토론 속 링크가 많이 잡힘(curation 링크 대부분). S3 원본 추적에서 거를 대상

## 7. 문턱값 (S1_TASK 7장)

| 항목 | 기준 | 결과 | 판정 |
|---|---|---|---|
| 글 소스 6곳 기간 덮음 | RSS 또는 백필 | 못 덮음: 없음 | 통과 |
| 본문 추출 성공률 | 소스별 90% 이상(feed_full 제외) | 미달: 없음 | 통과 |
| GeekNews 원문 링크 확보율 | 95% 이상 | 100% (319/319) | 통과 |
| 트렌딩 | 주간 페이지에 보이는 전부, stars_this_week 누락 0, 0개면 실패(설계 결정 Q2) | 페이지 11개 중 11개, 누락 0 | 통과 |
| 중복 | 0 | 0 | 통과 |
