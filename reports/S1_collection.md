# S1 수집 리포트 (2026-09-28 ~ 2026-10-04)

> `python -m trendsit report collection`이 생성한다. 기간은 한국 시간 게시일 기준. GitHub 트렌딩은 과거 기록이 없어 실행 시점의 주간 목록이다(기간과 다름).

## 1. 소스별

| 소스 | 받는 방식 | RSS 가장 오래된 날 | 기간 덮음 | 백필(방법, 페이지) | 기간 안 항목 | 백필로 얻음 | 본문 추출 성공 | 키워드 통과 | 실패, 메모 |
|---|---|---|---|---|---|---|---|---|---|
| openai | feed_summary | 2015-12-11 | 예 | rss_only, 0 | 15 | 0 | 93% (14/15) | 73% (11/15) | - |
| anthropic | feed_summary | 2021-05-28 | 예 | list_pages, 0 | 2 | 0 | 100% (2/2) | 100% (2/2) | - |
| deepmind | feed_summary | 2025-11-11 | 예 | rss_only, 0 | 2 | 0 | 100% (2/2) | 50% (1/2) | - |
| geeknews | feed_summary | 2026-10-06 | 예 | day_archive, 26 | 376 | 376 | 77% (288/376) | 37% (138/376) | GeekNews가 브라우저 확인을 요구해 토픽 페이지 요청을 멈춤(우회 안 함). 원문 글을 본문으로 2건; GeekNews 브라우저 확인 요구 + 원문 링크 없음 46건; 원문 robots.txt가 막음 15건; 원문 HTTP 403 12건; 원문 허용 밖 형식: application/pdf 4건; 원문 robots.txt 확인 불가로 건너뜀(ReadTi |
| simonw | feed_full | 2026-09-28 | 예 | day_archive, 2 | 18 | 1 | 94% (17/18) | 67% (12/18) | - |
| aitimes | feed_summary | 2026-10-06 | 예 | list_pages, 4 | 79 | 79 | 100% (79/79) | 54% (43/79) | - |
| techbridge | rss + yt-dlp | 2026-10-02 | 예 | channel_listing, 1 | 17 | 10 | 94% (16/17) | 82% (14/17) | - |

## 2. 백필 URL 확인 (2026-10-07 실제로 열어 봄)

| 소스 | handoff 후보 | 지금 설정 | 확인 결과 |
|---|---|---|---|
| openai | `rss_only` | `rss_only` | 후보 그대로 |
| anthropic | `list_pages https://www.anthropic.com/news` | `list_pages https://www.anthropic.com/news` | 목록은 최신 10건 안팎, 페이지 넘김 없음. 커뮤니티 피드가 2021년부터 담고 있어 대체 수단으로만 |
| deepmind | `rss_only` | `rss_only` | 후보 그대로 |
| geeknews | `list_pages https://news.hada.io/?page={page}` | `day_archive https://news.hada.io/past?day={date}&page={page}` | ?page=는 추천순이라 날짜로 멈출 수 없음 → 날짜별 아카이브 past?day=(하루치를 20건씩 페이지로) |
| simonw | `day_archive https://simonwillison.net/{yyyy}/{Mon}/{d}/` | `day_archive https://simonwillison.net/{yyyy}/{Mon}/{d}/` | 후보 그대로 동작(조각마다 고유 주소, 시각) |
| aitimes | `list_pages https://www.aitimes.com/news/articleList.html?page={page}&view_type=sm` | `list_pages https://www.aitimes.com/news/articleList.html?sc_sdate={since}&sc_edate={until}&view_type=sm / 2페이지부터 https://www.aitimes.com/news/ajaxArticlePaging.php?page={page}&list_per_page=20&page_per_page=10&sc_sdate={since}&sc_edate={until}&sc_order_by=E&view_type=sm` | 목록의 page 값이 무시됨(더보기는 JS) → 1페이지는 sc_sdate/sc_edate로 거른 HTML, 2페이지부터 ajaxArticlePaging.php(JSON) |
| techbridge | `channel_listing (yt-dlp)` | `channel_listing` | yt-dlp 채널 목록(flat, approximate_date) 동작. 정확한 시각은 영상별 메타데이터 |

## 3. GitHub

- 트렌딩(주간 페이지, 실행 주차 2026-W41): 레포 11개, 키워드 통과 5개, 이번 주 별 누락 0개
- 추적 레포 릴리스(기간 안): 18건 — anthropics/claude-code v2.1.284(2026-09-29), anthropics/claude-code v2.1.285(2026-09-30), anthropics/claude-code v2.1.286(2026-10-01), ollama/ollama v0.35.1-rc1(2026-10-02), ollama/ollama v0.35.1-rc2(2026-10-02), anthropics/claude-code v2.1.287(2026-10-02), NousResearch/hermes-agent v0.21.4+canary.20261002T070111Z(2026-10-02), NousResearch/hermes-agent v0.21.4+canary.20261003T070620Z(2026-10-03), NousResearch/hermes-agent rc.34-v0.21.5(2026-10-03), NousResearch/hermes-agent abandoned-rc.33-v0.21.5(2026-10-03), NousResearch/hermes-agent rc.35-v0.21.5(2026-10-03), ollama/ollama v0.35.1(2026-10-03)

| 순위 | 레포 | 이번 주 별 | 전체 별 | 키워드 | 상태 |
|---|---|---|---|---|---|
| 1 | mvschwarz/openrig | 3327 | 5634 | agent, coding-agent, frontier-release | pass |
| 2 | boykopovar/AnyPS5 | 3073 | 8437 | - | filtered |
| 3 | heygen-com/hyperframes | 3614 | 58253 | agent, mcp-tools | pass |
| 4 | cursor/plugins | 1106 | 10185 | - | filtered |
| 5 | NVIDIA/OpenShell | 5228 | 15212 | agent | pass |
| 6 | Panniantong/Agent-Reach | 6454 | 92960 | agent, mcp-tools, frontier-release | pass |
| 7 | thedotmack/claude-mem | 2104 | 97435 | agent, coding-agent, rag-search, frontier-release | pass |
| 8 | pablostanley/yoinks | 2947 | 4991 | - | filtered |
| 9 | DuarteSantos8/openGym | 3318 | 6405 | - | filtered |
| 10 | tile-ai/tilelang | 675 | 8460 | - | filtered |
| 11 | HunxByts/GhostTrack | 2017 | 17304 | - | filtered |

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
  - [ ] 놓침 · The Lenfest Institute grows landmark program with expanded OpenAI support (no_keyword)
  - [ ] 놓침 · Helping small businesses put AI to work (no_keyword)
  - [ ] 놓침 · The Den frees up 10-15 hours a week to grow with ChatGPT Work (no_keyword)
  - [ ] 놓침 · How Albertsons Companies is reimagining retail from the inside out (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · A model guide for the GPT-6 family (점수 4)
  - [ ] 잘못 통과 · Introducing dots (점수 2)
  - [ ] 잘못 통과 · Introducing GPT-6.1 Sol (점수 5)
  - [ ] 잘못 통과 · How we will do better for Australia (점수 2)
  - [ ] 잘못 통과 · Chatham scales its capital markets expertise with OpenAI (점수 2)

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
  - [ ] 놓침 · Show GN: Brief - AI Slop이 만든 기——인 글을 GeekNews 요약처럼 만들어 주는 Mac 앱 (no_keyword)
  - [ ] 놓침 · F/OSS Comics #10: C언어의 아버지, 데니스 리치의 일생 (no_keyword)
  - [ ] 놓침 · Bob Cringely 별세 (no_keyword)
  - [ ] 놓침 · Show GN: AutoPixel Studio - 이미지 기반 매크로 프로그램 (no_keyword)
  - [ ] 놓침 · Show GN: SSGOI – 모바일 웹을 네이티브 앱처럼 만드는 페이지 전환 라이브러리 (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · Sam Altman은 왜 자유의 몸인가? (점수 1)
  - [ ] 잘못 통과 · 개발 못 하는 영업 직장인이 옵시디언에 클로드 코드를 붙여 일한 기록 (점수 1)
  - [ ] 잘못 통과 · Show GN: Blyck Video Understanding - Claude·Codex가 영상을 시각 근거와 함께 분석·검색하게 해주는 MCP (점수 9)
  - [ ] 잘못 통과 · 페이페이 리의 World Labs, AMD에 합류 (점수 1)
  - [ ] 잘못 통과 · 거의 모든 서비스에 예산을 넘으면 멈추는 기능이 필요해질 것 (점수 1)

### simonw
- 걸러진 글
  - [ ] 놓침 · sighting 404239413 (no_keyword)
  - [ ] 놓침 · S3 Is the Future, S3 Is the Past (no_keyword)
  - [ ] 놓침 · Rex's Dino Store (no_keyword)
  - [ ] 놓침 · He Built This City (no_keyword)
  - [ ] 놓침 · September sponsors-only newsletter (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · We're going to need default hard budget caps on pretty much everything (점수 1)
  - [ ] 잘못 통과 · 2026 in LLMs (so far) (점수 6)
  - [ ] 잘못 통과 · Quoting Muse AI Agent (점수 3)
  - [ ] 잘못 통과 · Quoting @joedaroo (점수 1)
  - [ ] 잘못 통과 · Photo Scrubber — local face blur & metadata removal (점수 2)

### aitimes
- 걸러진 글
  - [ ] 놓침 · 오스트리아 영농형 태양광서 겨울밀 수확량 14% 높아…가뭄 속 현장실증 (no_keyword)
  - [ ] 놓침 · 기상청, 태양광·풍력 발전량 예측 돕는다…1km 단위 기상자료 제공 (no_keyword)
  - [ ] 놓침 · 태양광 발전량·전력가격 예측하는 AI…일본 ESS 충·방전 자동화 (no_keyword)
  - [ ] 놓침 · [AI 이슈트렌드] 계속된 DMZ 논란 속 트럼프 LNG 협박·청주 흉기 성폭행 화제 (no_keyword)
  - [ ] 놓침 · 메타, AI 데이터센터 '실험 시설' 지정...수십억달러 세액공제 논란 (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · [10월2일] "뜻밖의 주인공은 로그인과 플러그인"…알트먼이 보여준 챗GPT의 다음 무대 (점수 4)
  - [ ] 잘못 통과 · 오픈AI 안전 총괄, 조직 문화 비판하며 사직..."시행착오 시대 끝났다" (점수 3)
  - [ ] 잘못 통과 · 애플, 13일 스마트홈 허브 공개…'AI 시리' 앞세워 아마존·구글에 도전장 (점수 1)
  - [ ] 잘못 통과 · 오퍼스 5.5 ‘이것은 중요합니다’ 남발…습관 못 버린 AI 글쓰기 (점수 1)
  - [ ] 잘못 통과 · 딥시크, 데스크톱 앱 '딥시크 하네스' 출시..."챗·코딩·문서 통합" (점수 4)

### techbridge
- 걸러진 글
  - [ ] 놓침 · [한영자막] 팟캐스트 풀버전 - SpaceX에서 매달 수천 개의 PR을 반영하는 방법을 알아봅니다 | Cursor & Grok Bot 개발자 L (no_keyword)
  - [ ] 놓침 · AI로 무엇이든 효과적으로 학습하는 방법 (no_keyword)
  - [ ] 놓침 · [한영자막] 400개 기업 데이터로 본 소프트웨어 개발 AI의 현주소입니다 (excluded:채용)
- 통과한 글
  - [ ] 잘못 통과 · [한영자막] 자는 동안 스스로 학습하는 AI: 단순 기억을 넘어 꿈으로 진화하는 에이전트의 비밀 (점수 5)
  - [ ] 잘못 통과 · [한영자막] 스스로 개선되는 AI 에이전트는 어떻게 만들었을까요? | Weights & Biases (점수 6)
  - [ ] 잘못 통과 · [한영자막] AI 시대, 스펙 기반 개발(SDD)을 실무에 적용하며 배운 교훈들 (점수 2)
  - [ ] 잘못 통과 · [한영자막] AI가 여러분의 데이터를 노출하고 있습니다: 눈에 보이지 않는 AI 보안의 숨은 위험 (점수 2)
  - [ ] 잘못 통과 · [한영자막] Claude Code와 Codex를 인간 연구자들과 경쟁시켰습니다 — Elie Bakouch, Prime Intellect (점수 8)

## 6. 링크

| 종류 | 링크 수 |
|---|---|
| other | 1809 |
| curation | 839 |
| repo | 231 |
| social | 143 |
| official | 103 |
| paper | 66 |
| news | 27 |
| press | 16 |

- GeekNews 원문 링크 확보율: 100% (330/330) (제목 링크가 GeekNews 자신인 Ask/Show GN 글 46건은 제외)
- 원문이 Hacker News 토론 페이지인 GeekNews 글은 토론 속 링크가 많이 잡힘(curation 링크 대부분). S3 원본 추적에서 거를 대상

## 7. 문턱값 (S1_TASK 7장)

| 항목 | 기준 | 결과 | 판정 |
|---|---|---|---|
| 글 소스 6곳 기간 덮음 | RSS 또는 백필 | 못 덮음: 없음 | 통과 |
| 본문 추출 성공률 | 소스별 90% 이상(feed_full 제외) | 미달: geeknews 77% | 미달 |
| GeekNews 원문 링크 확보율 | 95% 이상 | 100% (330/330) | 통과 |
| 트렌딩 | 20개 이상, stars_this_week 누락 0 | 11개, 누락 0 | 미달 |
| 중복 | 0 | 0 | 통과 |
