# S1 수집 리포트 (2026-09-28 ~ 2026-10-04)

> `python -m trendsit report collection`이 생성한다. 기간은 한국 시간 게시일 기준. GitHub 트렌딩은 과거 기록이 없어 실행 시점의 주간 목록이다(기간과 다름).

## 1. 소스별

| 소스 | 받는 방식 | RSS 가장 오래된 날 | 기간 덮음 | 백필(방법, 페이지) | 기간 안 항목 | 백필로 얻음 | 본문 추출 성공 | 키워드 통과 | 실패, 메모 |
|---|---|---|---|---|---|---|---|---|---|
| openai | feed_summary | 2015-12-11 | 예 | rss_only, 0 | 15 | 0 | 93% (14/15) | 73% (11/15) | - |
| anthropic | feed_summary | 2021-05-28 | 예 | list_pages, 0 | 2 | 0 | 100% (2/2) | 100% (2/2) | - |
| deepmind | feed_summary | 2025-11-11 | 예 | rss_only, 0 | 2 | 0 | 100% (2/2) | 50% (1/2) | - |
| geeknews | feed_summary | 2026-10-06 | 예 | day_archive, 23 | 376 | 376 | 77% (288/376) | 37% (138/376) | GeekNews가 브라우저 확인을 요구해 토픽 페이지 요청을 멈춤(우회 안 함). 원문 글을 본문으로 252건; GeekNews 브라우저 확인 요구 + 원문 링크 없음 46건; 원문 robots.txt가 막음 15건; 원문 HTTP 403 12건; 원문 허용 밖 형식: application/pdf 3건; 원문 ReadTimeout: The read oper |
| simonw | feed_full | 2026-09-28 | 예 | day_archive, 0 | 17 | 0 | 100% (17/17) | 71% (12/17) | - |
| aitimes | feed_summary | 2026-10-06 | 예 | list_pages, 4 | 79 | 79 | 100% (79/79) | 54% (43/79) | - |
| techbridge | rss + yt-dlp | 2026-10-02 | 예 | channel_listing, 1 | 17 | 10 | 94% (16/17) | 82% (14/17) | 메타데이터 실패: 5tdMgKkX5dU |

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
| 1 | mvschwarz/openrig | 3327 | 5628 | agent, coding-agent, frontier-release | pass |
| 2 | boykopovar/AnyPS5 | 3073 | 8246 | - | filtered |
| 3 | heygen-com/hyperframes | 3614 | 58238 | agent, mcp-tools | pass |
| 4 | cursor/plugins | 1106 | 10180 | - | filtered |
| 5 | NVIDIA/OpenShell | 5228 | 15208 | agent | pass |
| 6 | Panniantong/Agent-Reach | 6454 | 92943 | agent, mcp-tools, frontier-release | pass |
| 7 | thedotmack/claude-mem | 2104 | 97416 | agent, coding-agent, rag-search, frontier-release | pass |
| 8 | pablostanley/yoinks | 2947 | 4982 | - | filtered |
| 9 | DuarteSantos8/openGym | 3318 | 6359 | - | filtered |
| 10 | tile-ai/tilelang | 675 | 8456 | - | filtered |
| 11 | HunxByts/GhostTrack | 2017 | 17300 | - | filtered |

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
  - [ ] 놓침 · The Den frees up 10-15 hours a week to grow with ChatGPT Work (no_keyword)
  - [ ] 놓침 · How Albertsons Companies is reimagining retail from the inside out (no_keyword)
  - [ ] 놓침 · The Lenfest Institute grows landmark program with expanded OpenAI support (no_keyword)
  - [ ] 놓침 · Helping small businesses put AI to work (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · Introducing dots (점수 2)
  - [ ] 잘못 통과 · How we will do better for Australia (점수 2)
  - [ ] 잘못 통과 · Introducing GPT-6.1 Sol (점수 5)
  - [ ] 잘못 통과 · Are you a Codex Original? (점수 3)
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
  - [ ] 놓침 · Show GN: cuesheet - 링크 하나로 MSW 응답을 바꿔, AI도 QA도 상황별 화면을 확인하는 도구 (no_keyword)
  - [ ] 놓침 · PostgreSQL JSONB: JSON 데이터 조회, 수정 및 인덱싱 (no_keyword)
  - [ ] 놓침 · F/OSS Comics #11: BSD 유닉스 1화 – UC 버클리로 간 유닉스 코드 (no_keyword)
  - [ ] 놓침 · example.com이 바뀐 이유를 설명한 IANA의 이메일 (no_keyword)
  - [ ] 놓침 · Chess.com을 8,400만원에 인수해 연 매출 3,000억원으로 키우기 (excluded:인수)
- 통과한 글
  - [ ] 잘못 통과 · Google은 언제부터 이렇게 이상해졌을까? (점수 1)
  - [ ] 잘못 통과 · 얀 르쿤, AI의 인류 멸종 위험에 “전혀 우려 없다” (점수 2)
  - [ ] 잘못 통과 · Muse Gadgets - Meta의 AI 에이전트를 직접 만든 기기에 연결하기 (점수 3)
  - [ ] 잘못 통과 · 모두가 짐을 싸고 있다 (점수 1)
  - [ ] 잘못 통과 · ChatGPT Sites - 대화로 웹사이트와 앱을 만들고 게시하기 (점수 1)

### simonw
- 걸러진 글
  - [ ] 놓침 · S3 Is the Future, S3 Is the Past (no_keyword)
  - [ ] 놓침 · Bluesky reply bot checker (no_keyword)
  - [ ] 놓침 · He Built This City (no_keyword)
  - [ ] 놓침 · September sponsors-only newsletter (no_keyword)
  - [ ] 놓침 · Rex's Dino Store (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · OpenAI DevDay 2026 live blog (점수 3)
  - [ ] 잘못 통과 · pwasm 0.2a0 (점수 1)
  - [ ] 잘못 통과 · We're going to need default hard budget caps on pretty much everything (점수 1)
  - [ ] 잘못 통과 · Quoting @joedaroo (점수 1)
  - [ ] 잘못 통과 · Photo Scrubber — local face blur & metadata removal (점수 2)

### aitimes
- 걸러진 글
  - [ ] 놓침 · 아일랜드, 주택용 태양광·배터리 지원 확대…국내는 마을 단위 실증 (no_keyword)
  - [ ] 놓침 · 태양광 발전량·전력가격 예측하는 AI…일본 ESS 충·방전 자동화 (no_keyword)
  - [ ] 놓침 · "다섯 손가락 필요 없다"...보스턴 다이내믹스, 네 손가락 로봇 손 공개 (no_keyword)
  - [ ] 놓침 · 구글 "우주 데이터센터 실현 위해 스타십 최소 1800회 발사 필요" (no_keyword)
  - [ ] 놓침 · 엔비디아·소프트뱅크, 오픈AI 투자 잔여분 27조 최종 집행 (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · 앤트로픽, 중국 'GLM-5.3' 해킹 위험성 경고..."클로드 미소스와 맞먹는 능력" (점수 3)
  - [ ] 잘못 통과 · 네이버, 웨일 브라우저 내 'AI 챗' 탑재..."타 서비스 도입도 검토" (점수 3)
  - [ ] 잘못 통과 · 원프레딕트 “버려지던 제조 데이터, AI 자산으로 바꾸겠다” (점수 2)
  - [ ] 잘못 통과 · 애플, AI 에이전트 공격 대비해 맥OS '전체 디스크 접근' 제어 강화 (점수 4)
  - [ ] 잘못 통과 · 오픈AI, 내부 기밀 유출 혐의로 정렬·안전팀 연구원 3명 해고 (점수 3)

### techbridge
- 걸러진 글
  - [ ] 놓침 · [한영자막] 팟캐스트 풀버전 - SpaceX에서 매달 수천 개의 PR을 반영하는 방법을 알아봅니다 | Cursor & Grok Bot 개발자 L (no_keyword)
  - [ ] 놓침 · AI로 무엇이든 효과적으로 학습하는 방법 (no_keyword)
  - [ ] 놓침 · [한영자막] 400개 기업 데이터로 본 소프트웨어 개발 AI의 현주소입니다 (excluded:채용)
- 통과한 글
  - [ ] 잘못 통과 · [한영자막] 코드 리뷰의 종말: 데이터가 보여주는 진짜 현실입니다 (점수 3)
  - [ ] 잘못 통과 · [한영자막] 진짜 '소프트웨어 팩토리'를 만들려면 무엇이 필요할까요? — Factory Tereza (점수 4)
  - [ ] 잘못 통과 · [한영자막] 자는 동안 스스로 학습하는 AI: 단순 기억을 넘어 꿈으로 진화하는 에이전트의 비밀 (점수 5)
  - [ ] 잘못 통과 · [한영자막] 루프 자체가 제품입니다 — xAI 출신 창업자가 밝히는 차세대 AI 에이전트의 핵심 (점수 4)
  - [ ] 잘못 통과 · [한영자막] 소프트웨어 엔지니어링은 이제 소프트웨어 공장을 짓는 일이 될 것입니다 — Zach Lloyd (Warp) (점수 2)

## 6. 링크

| 종류 | 링크 수 |
|---|---|
| other | 1807 |
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
