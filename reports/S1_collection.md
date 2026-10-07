# S1 수집 리포트 (2026-09-28 ~ 2026-10-04)

> `python -m trendsit report collection`이 생성한다. 기간은 한국 시간 게시일 기준. GitHub 트렌딩은 과거 기록이 없어 실행 시점의 주간 목록이다(기간과 다름).

## 1. 소스별

본문 추출 성공률의 분모는 원문 링크가 있는 글에서 의도적으로 건너뛴 것(robots 차단, PDF 등 허용 밖 형식, 영상)을 뺀 수. 403 같은 실패는 실패로 센다(설계 결정 Q1).

| 소스 | 받는 방식 | RSS 가장 오래된 날 | 기간 덮음 | 백필(방법, 페이지) | 기간 안 항목 | 백필로 얻음 | 본문 추출 성공 | 의도적 건너뜀 | 키워드 통과 | 실패, 메모 |
|---|---|---|---|---|---|---|---|---|---|---|
| openai | feed_summary | 2015-12-11 | 예 | rss_only, 0 | 15 | 0 | 93% (14/15) | - | 73% (11/15) | - |
| anthropic | feed_summary | 2021-05-28 | 예 | list_pages, 0 | 2 | 0 | 100% (2/2) | - | 100% (2/2) | - |
| deepmind | feed_summary | 2025-11-11 | 예 | rss_only, 0 | 2 | 0 | 100% (2/2) | - | 50% (1/2) | - |
| geeknews | list_origin | - | 예(날짜당 1페이지) | day_archive, 7 | 83 | 83 | 98% (78/80) | robots 차단 1, 영상 2 | 63% (52/83) | 자기 글(Show GN 등) 57건 제외; 실패: 본문 추출 실패 1건 |
| simonw | feed_full | 2026-09-28 | 예 | day_archive, 2 | 18 | 1 | 94% (17/18) | - | 67% (12/18) | - |
| aitimes | feed_summary | 2026-10-06 | 예 | list_pages, 11 | 188 | 188 | 100% (188/188) | - | 56% (106/188) | - |
| techbridge | rss + yt-dlp | 2026-10-02 | 예 | channel_listing, 1 | 17 | 10 | 94% (16/17) | - | 82% (14/17) | - |

### 하루 신규 건수(게시일, 한국 시간)

| 소스 | 09-28 | 09-29 | 09-30 | 10-01 | 10-02 | 10-03 | 10-04 | 하루 평균 |
|---|---|---|---|---|---|---|---|---|
| openai | 3 | 5 | 2 | 1 | 3 | 1 | 0 | 2.1 |
| anthropic | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0.3 |
| deepmind | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0.3 |
| geeknews | 9 | 15 | 9 | 13 | 11 | 11 | 15 | 11.9 |
| simonw | 5 | 3 | 4 | 2 | 1 | 1 | 2 | 2.6 |
| aitimes | 31 | 31 | 30 | 40 | 30 | 14 | 12 | 26.9 |
| techbridge | 2 | 2 | 2 | 3 | 3 | 2 | 3 | 2.4 |

## 2. 백필 URL 확인 (2026-10-07 실제로 열어 봄)

| 소스 | handoff 후보 | 지금 설정 | 확인 결과 |
|---|---|---|---|
| openai | `rss_only` | `rss_only` | 후보 그대로 |
| anthropic | `list_pages https://www.anthropic.com/news` | `list_pages https://www.anthropic.com/news` | 목록은 최신 10건 안팎, 페이지 넘김 없음. 커뮤니티 피드가 2021년부터 담고 있어 대체 수단으로만 |
| deepmind | `rss_only` | `rss_only` | 후보 그대로 |
| geeknews | `RSS + list_pages https://news.hada.io/?page={page}` | `day_archive https://news.hada.io/past?day={date}&page={page}` | 설계 결정(Q1, Q5): RSS·상세 페이지·메인 화면을 쓰지 않음. 매일 수집과 백필 모두 날짜별 목록 past?day=에서 날짜당 pages_per_day페이지(기본 1 = 그날 점수 상위 약 20건). 본문은 원문 링크에서 |
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
  - [ ] 놓침 · How Albertsons Companies is reimagining retail from the inside out (no_keyword)
  - [ ] 놓침 · The Den frees up 10-15 hours a week to grow with ChatGPT Work (no_keyword)
  - [ ] 놓침 · The Lenfest Institute grows landmark program with expanded OpenAI support (no_keyword)
  - [ ] 놓침 · Helping small businesses put AI to work (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · Disrupting a coordinated model-distillation campaign (점수 1)
  - [ ] 잘못 통과 · Chatham scales its capital markets expertise with OpenAI (점수 2)
  - [ ] 잘못 통과 · Are you a Codex Original? (점수 3)
  - [ ] 잘못 통과 · A model guide for the GPT-6 family (점수 4)
  - [ ] 잘못 통과 · Towards safety cases for frontier AI training (점수 2)

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
  - [ ] 놓침 · PostgreSQL JSONB: JSON 데이터 조회, 수정 및 인덱싱 (no_keyword)
  - [ ] 놓침 · 소프트웨어 품질의 시대인가, 타조의 시대인가? (no_keyword)
  - [ ] 놓침 · LLM Wiki의 불량 페이지를 Jev로 선별하는 것이 가능할까? (no_keyword)
  - [ ] 놓침 · Pluto - SOTA 스타크래프트 AI (no_keyword)
  - [ ] 놓침 · 왜 더 많은 개발자가 “플랫폼을 활용”하지 않을까? (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · 문제는 AI 코드가 아니라, 이제 아무도 아무것도 모른다는 것이다 (점수 3)
  - [ ] 잘못 통과 · DeepSeek Harness, 맥·윈도우용 데스크톱 앱 공개 (점수 4)
  - [ ] 잘못 통과 · 텍스트 분류를 위한 언어 모델: Bag-of-Words에서 Jev까지 (점수 2)
  - [ ] 잘못 통과 · 바이브 코딩한 웹사이트를 디자이너가 만든 것처럼 보이게 한 방법 (점수 2)
  - [ ] 잘못 통과 · 생각을 정리하는 도구로서의 커밋 설명 (점수 2)

### simonw
- 걸러진 글
  - [ ] 놓침 · September sponsors-only newsletter (no_keyword)
  - [ ] 놓침 · Rex's Dino Store (no_keyword)
  - [ ] 놓침 · Bluesky reply bot checker (no_keyword)
  - [ ] 놓침 · He Built This City (no_keyword)
  - [ ] 놓침 · sighting 404239413 (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · Photo Scrubber — local face blur & metadata removal (점수 2)
  - [ ] 잘못 통과 · Quoting Anthropic Frontier Red Team (점수 5)
  - [ ] 잘못 통과 · Quoting Matthew Green (점수 1)
  - [ ] 잘못 통과 · OpenAI DevDay 2026 live blog (점수 3)
  - [ ] 잘못 통과 · Claude Sonnet 5.5 (점수 5)

### aitimes
- 걸러진 글
  - [ ] 놓침 · 카카오, CA협의체 공동 의장에 김도영 카카오X 대표 내정자 확정 (no_keyword)
  - [ ] 놓침 · 우크라이나, '로봇 군단' 발족...드론 이어 지상 전장 무인화 박차 (no_keyword)
  - [ ] 놓침 · 미국 태양광 모듈값 하락에도 상업·대규모 시스템 가격 상승 (no_keyword)
  - [ ] 놓침 · 기업 태양광에 배터리 지원…그리스, 815만유로 배정 (no_keyword)
  - [ ] 놓침 · 스캐터랩, 캐릭터챗 '제타' 신규 기능 출시..."대화 따라 표정·배경 바뀐다" (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · 알트먼 "기업공개 압박 없이 AI 안전 확보가 우선" (점수 2)
  - [ ] 잘못 통과 · 일레븐랩스, 감정 표현·지연 시간 혁신한 '일레븐 v4' 공개…TTS 아레나 1위 (점수 6)
  - [ ] 잘못 통과 · 텐센트, 오라클서 AI 칩 10만개 임대…규제 피하려 동남아로 (점수 1)
  - [ ] 잘못 통과 · [9월28일] 메타 '뮤즈'가 찾아낸 새로운 유즈 케이스는 '구독 해지' (점수 1)
  - [ ] 잘못 통과 · AI '생각의 사슬' 무력화되나…'순환 깊이' 기술이 부른 불투명성 우려 (점수 2)

### techbridge
- 걸러진 글
  - [ ] 놓침 · AI로 무엇이든 효과적으로 학습하는 방법 (no_keyword)
  - [ ] 놓침 · [한영자막] 400개 기업 데이터로 본 소프트웨어 개발 AI의 현주소입니다 (excluded:채용)
  - [ ] 놓침 · [한영자막] 팟캐스트 풀버전 - SpaceX에서 매달 수천 개의 PR을 반영하는 방법을 알아봅니다 | Cursor & Grok Bot 개발자 L (no_keyword)
- 통과한 글
  - [ ] 잘못 통과 · [한영자막] MS 사티아 나델라가 밝힌 AI 미래: 코파일럿과 오토파일럿, 그리고 다가올 제품 경쟁 (점수 1)
  - [ ] 잘못 통과 · [한영자막] 소프트웨어 엔지니어링은 이제 소프트웨어 공장을 짓는 일이 될 것입니다 — Zach Lloyd (Warp) (점수 2)
  - [ ] 잘못 통과 · [한영자막] 진짜 '소프트웨어 팩토리'를 만들려면 무엇이 필요할까요? — Factory Tereza (점수 4)
  - [ ] 잘못 통과 · [한영자막] AI 에이전트를 위한 문서 컨텍스트 레이어 구축하는 법 — Jerry Liu, LlamaIndex (점수 6)
  - [ ] 잘못 통과 · [한영자막] 스스로 개선되는 AI 에이전트는 어떻게 만들었을까요? | Weights & Biases (점수 6)

## 6. 링크

| 종류 | 링크 수 |
|---|---|
| other | 587 |
| social | 99 |
| repo | 98 |
| official | 76 |
| paper | 50 |
| curation | 12 |
| news | 6 |
| press | 1 |

- GeekNews 원문 링크 확보율: 100% (83/83) (원문 링크가 GeekNews 자신인 글 57건은 수집에서 뺌. 목록에서 원문 링크가 있는 글만 수집하므로 구조상 100%이고, 실제 확인은 자기 글 판정이 맞는지)
- 원문이 Hacker News 토론 페이지인 GeekNews 글은 토론 속 링크가 많이 잡힘(curation 링크 대부분). S3 원본 추적에서 거를 대상

## 7. 문턱값 (S1_TASK 7장)

| 항목 | 기준 | 결과 | 판정 |
|---|---|---|---|
| 글 소스 6곳 기간 덮음 | RSS 또는 백필 | 못 덮음: 없음 | 통과 |
| 본문 추출 성공률 | 소스별 90% 이상(feed_full 제외) | 미달: 없음 | 통과 |
| GeekNews 원문 링크 확보율 | 95% 이상 | 100% (83/83) | 통과 |
| 트렌딩 | 주간 페이지에 보이는 전부, stars_this_week 누락 0, 0개면 실패(설계 결정 Q2) | 페이지 11개 중 11개, 누락 0 | 통과 |
| 중복 | 0 | 0 | 통과 |
