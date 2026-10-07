# 27. MVP 소스와 키워드 설정 (고정값)

작성: 2026-10-07. MVP는 소스와 키워드를 설정 파일로 고정한다(화면에서 바꾸는 기능은 MVP 밖).
아래 두 블록을 코드 저장소의 `config/sources.yaml`, `config/keywords.yaml`로 그대로 쓴다. 피드 주소는 2026-10-07에 열리는 것을 확인했다(Anthropic 커뮤니티 피드, 추적 레포 릴리스 피드는 구현 때 재확인).

## 1. 구성 요약

| 채널 | 소스 | 성격 |
|---|---|---|
| 글 (6) | OpenAI News, Anthropic News, Google DeepMind 블로그 | 해외 1차 자료 |
| | GeekNews, Simon Willison's Weblog | 큐레이션 (국내, 해외) |
| | AI타임스 | 국내 뉴스 |
| 영상 (1) | Tech Bridge (@TechBridge-KR) | 해외 기술 발표 + 한국어 자막 |
| GitHub | OSS Insight 주간 트렌딩 + 추적 레포 4개 | ollama, hermes-agent, codex, claude-code |

- 같은 소식이 1차 자료 → 큐레이션 → 국내 기사 → 발표 영상으로 여러 번 나타나도록 고른 구성(교차 연계 D2, 원본 추적)
- 필터 전 글 양은 하루 50건 안팎(GeekNews, AI타임스가 대부분). 키워드 필터를 통과한 것만 LLM 요약

## 2. config/sources.yaml

```yaml
# MVP 고정 소스. fetch 값:
#   feed_full    피드에 본문 전체가 있음
#   feed_summary 피드에는 요약만 → 원글 페이지에서 본문 추출(trafilatura)
#   feed_title   피드에는 제목, 링크만 → 원글 페이지에서 본문 추출
text:
  - id: openai
    name: OpenAI News
    kind: primary          # primary(1차 자료) / curation / news
    lang: en
    feed: https://openai.com/news/rss.xml
    fetch: feed_summary
    note: 기업 사례 글이 많음. 필터로 거름

  - id: anthropic
    name: Anthropic News
    kind: primary
    lang: en
    feed: https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml
    fallback_list: https://www.anthropic.com/news   # 공식 RSS 없음. 커뮤니티 피드가 멈추면 목록 페이지를 직접 파싱
    fetch: feed_summary
    note: 커뮤니티가 매시간 생성하는 피드(공식 아님)

  - id: deepmind
    name: Google DeepMind Blog
    kind: primary
    lang: en
    feed: https://deepmind.google/blog/rss.xml
    fetch: feed_summary

  - id: geeknews
    name: GeekNews
    kind: curation
    lang: ko
    feed: https://news.hada.io/rss/news
    fetch: feed_summary
    note: 기술 외 글이 섞임. 글마다 원문 링크가 있어 원본 추적 대상

  - id: simonw
    name: Simon Willison's Weblog
    kind: curation
    lang: en
    feed: https://simonwillison.net/atom/everything/
    fetch: feed_full
    note: 전문 + 원본 링크가 많음. 짧은 링크 글이 많아 하루 여러 건

  - id: aitimes
    name: AI타임스
    kind: news
    lang: ko
    feed: https://www.aitimes.com/rss/allArticle.xml
    fetch: feed_summary
    note: 하루 20~25건. 국내 업계 소식. 필터 필수

video:
  - id: techbridge
    name: Tech Bridge
    lang: ko                 # 전사는 로컬 Whisper(원음, 주로 영어). 수동 자막은 보조, 자동 자막은 쓰지 않음
    channel_handle: "@TechBridge-KR"
    channel_id: UC895rbZX2iXLTDfji7W4PfA
    feed: https://www.youtube.com/feeds/videos.xml?channel_id=UC895rbZX2iXLTDfji7W4PfA
    note: 해외 발표를 번역한 영상. 설명란의 원본 영상 링크는 이후 원본 추적 후보

github:
  trending:
    source: ossinsight
    period: past_week
    language: null           # 전체. 관련성은 레포 분석가가 키워드로 판단
    top_n: 30                # 얕게 훑기에서 볼 후보 수
  tracked:                   # 릴리스를 매주 챙겨 보는 레포
    - repo: ollama/ollama
      why: 로컬 전환 때 쓸 실행 환경
    - repo: NousResearch/hermes-agent
      why: 10주차 수업 도구
    - repo: openai/codex
      why: 코딩 에이전트. OpenAI 글과 교차
    - repo: anthropics/claude-code
      why: 코딩 에이전트. Anthropic 글과 교차
  # 릴리스 피드: https://github.com/<repo>/releases.atom, 메타데이터와 커밋은 GitHub API(토큰)
```

## 3. config/keywords.yaml

```yaml
# 포함 키워드: 필터(걸린 글만 LLM 요약)와 토픽 묶기 기준을 겸함
# 매칭 규칙(코드):
#   - 대소문자 무시
#   - 영어 별칭은 단어 경계로 매칭 (예: "eval"이 "evaluate" 안에서 걸리지 않게 word: true)
#   - 한국어 별칭은 부분 문자열 매칭
#   - 제목 매칭은 본문 매칭보다 가중치 높게
keywords:
  - id: agent
    canonical: AI 에이전트
    aliases: [agent, agents, agentic, 에이전트, 에이전틱]

  - id: coding-agent
    canonical: 코딩 에이전트
    aliases: [coding agent, Codex, Claude Code, 하네스, harness, 코딩 에이전트]

  - id: mcp-tools
    canonical: MCP · 도구 호출
    aliases: [MCP, Model Context Protocol, tool calling, tool use, function calling, 도구 호출, 함수 호출]

  - id: open-weight
    canonical: 오픈웨이트 · 로컬 LLM
    aliases: [open-weight, open weights, 오픈웨이트, 오픈소스 모델, local LLM, 로컬 LLM, Ollama, llama.cpp, GGUF, quantization, 양자화, Gemma, Qwen]

  - id: rag-search
    canonical: RAG · 검색
    aliases: [RAG, retrieval, 검색 증강, vector database, 벡터 DB, 벡터 데이터베이스, embedding, 임베딩, reranker]

  - id: multimodal
    canonical: 멀티모달
    aliases: [multimodal, 멀티모달, vision, 비전, video model, 영상 모델, speech, 음성, TTS, ASR]

  - id: reasoning
    canonical: 추론 · 판단 모델
    aliases: [reasoning, reasoning model, thinking, 추론 모델, 판단 모델, decision model]

  - id: eval
    canonical: 평가 · 벤치마크
    aliases: [eval, evals, evaluation, benchmark, leaderboard, 벤치마크, 리더보드, 평가]

  - id: ai-security
    canonical: AI 보안
    aliases: [prompt injection, 프롬프트 인젝션, jailbreak, 탈옥, guardrail, 가드레일, red team, 레드팀, AI safety]

  - id: frontier-release
    canonical: 프런티어 모델 출시
    aliases: [GPT, Claude, Gemini, 새 모델, model release, 모델 공개, 모델 출시]
    note: 이름만으로 넓게 걸림. 출시, 공개 글인지는 1차 요약의 관련성 판단에 맡김

# 제외어: 기술과 무관한 글 거르기
# 규칙: 제외어가 있고 포함 키워드가 제목에 하나도 없으면 제외 (포함 키워드가 본문에만 있으면 제외됨)
exclude:
  - 합병
  - 인수
  - 주가
  - 시가총액
  - 채용
  - 부고
  - 정치
  - 선거
  - 연예
  - 스포츠
```

## 4. 첫 주에 볼 것
- 소스별 필터 전후 건수(특히 GeekNews, AI타임스 통과율)
- 놓친 글: 필터에서 빠졌지만 실제로는 관련 있는 글 샘플 10건
- 너무 넓게 걸리는 별칭(`agent`, `GPT`, `Claude`)과 너무 좁은 키워드
- Anthropic 커뮤니티 피드가 제때 갱신되는지
- 결과를 보고 키워드, 제외어, 가중치 조정 → 이 문서 갱신
