# S1 품질 리포트 (관문 B)

> `python -m trendsit eval`이 자동 생성한다. 원자료는 `reports/eval/*.json`.

## repo_oneliner

문턱값(generate 기준, 코드 채점 통과분의 질문별 통과율): Q1 100%, Q2 90%, Q3 90% 이상 + 코드 채점 전부 통과

- Q1: 근거: oneliner의 모든 내용이 README에 있나?
- Q2: 구체성: 처음 보는 사람이 대상과 동작을 알 수 있나?
- Q3: 핵심: 부수 기능이나 설치법이 아니라 README의 주된 기능을 골랐나?

judge 판정: **잠정**(사람 라벨 없음. `eval/labels/repo_oneliner.csv`를 채우면 일치율을 잰다)

### 모델별 최신 결과 (전체 실행만, 점수는 보고용)

| 모델 | 코드 통과 | Q1 통과 | Q2 통과 | Q3 통과 | 정확성 평균 | 구체성 평균 | 표현 평균 | 문턱값 | 비용 | 프롬프트 |
|---|---|---|---|---|---|---|---|---|---|---|
| generate (`qwen/qwen3.8-27b`) | 8/10 | 8/8 | 8/8 | 8/8 | 5.0 | 5.0 | 5.0 | 미달 | $0.0106 | `c16be6fbb27f` |

- generate 미달 이유: 코드 채점 통과 8/10

### 가장 최근 실행(부분, 2026-10-07T22:08:20+09:00, 프롬프트 `d77414b2efaf`)

- 설계 결정 Q3 재측정(3회 상한과 별도): README 기호 정리 입력 + basis 검사를 정리 본문·description 기준으로
- 픽스처 7개까지 진행, 코드 통과 6/7, Q1 5/5, Q2 5/5, Q3 5/5
- 멈춘 이유: 채점 BudgetExceeded: 스펙 S1 상한 초과: 누적 $0.0444 + 예상 $0.0057 > 상한 $0.05 (시도: judge(google/gemini-3.8-flash) max_tokens=1600)

| 픽스처 | 출력 | 판정 |
|---|---|---|
| NousResearch__hermes-agent | 경험 기반 학습 루프를 갖춘 AI 에이전트 | Q1○ Q2○ Q3○  |
| Python3WebSpider__Images360 | Scrapy로 360에서 이미지를 다운로드하는 스크레이퍼 | 코드 실패 (attention: 기대 True, 출력 False) |
| anthropics__claude-code | 터미널에서 코드베이스를 이해하고 자연어 명령으로 개발 작업을 수행하는 에이전틱 코딩 도구 | Q1○ Q2○ Q3○  |
| encode__httpx | HTTP/1.1과 HTTP/2를 지원하는 Python HTTP 클라이언트 라이브러리 | Q1○ Q2○ Q3○  |
| excalidraw__excalidraw | 손그림 스타일 다이어그램을 그리는 오픈소스 가상 화이트보드 | Q1○ Q2○ Q3○  |
| fastapi__full-stack-fastapi-template | FastAPI와 React 기반 풀스택 웹앱 개발용 템플릿 | Q1○ Q2○ Q3○  |
| kakao__khaiii | CNN 기반 한국어 형태소분석기 | 채점 전  |

### 출력 나란히

| 픽스처 | generate |
|---|---|
| NousResearch__hermes-agent | 경험 기반 학습 루프를 갖춘 AI 에이전트 [코드 실패] |
| Python3WebSpider__Images360 | Scrapy로 360 이미지 다운로드 스크립트 [Q1○ Q2○ Q3○] |
| anthropics__claude-code | 터미널에서 코드베이스를 이해해 코딩 작업을 수행하는 에이전틱 코딩 도구 [Q1○ Q2○ Q3○] |
| encode__httpx | HTTP/1.1과 HTTP/2를 지원하는 Python HTTP 클라이언트 라이브러리 [Q1○ Q2○ Q3○] |
| excalidraw__excalidraw | 손그림 스타일 다이어그램을 그리는 오픈소스 가상 화이트보드 [Q1○ Q2○ Q3○] |
| fastapi__full-stack-fastapi-template | FastAPI와 React 기반 풀스택 웹앱 시작 템플릿 [코드 실패] |
| kakao__khaiii | 데이터 기반 한국어 형태소분석기 [Q1○ Q2○ Q3○] |
| ollama__ollama | 오픈 소스 LLM을 로컬에서 실행하고 관리하는 도구 [Q1○ Q2○ Q3○] |
| openai__codex | 터미널에서 로컬로 실행되는 OpenAI 코딩 에이전트 CLI [Q1○ Q2○ Q3○] |
| punkpeye__awesome-mcp-servers | MCP 서버를 정리한 큐레이션 목록 [Q1○ Q2○ Q3○] |

### 가장 나쁜 사례 3개 (generate, 2026-10-07T22:08:20+09:00, 부분 실행)

1. **Python3WebSpider__Images360**
   - 입력: `{"full_name": "Python3WebSpider/Images360", "description": "Download Images From 360 Using Scrapy", "topics": [], "readme_head": "# Images360\n\nDownload Images From 360 Using Scrapy"}`
   - 출력: `{"log": "README 제목과 설명 문장 근거", "attention": false, "basis": "Download Images From 360 Using Scrapy", "oneliner": "Scrapy로 360에서 이미지를 다운로드하는 스크레이퍼"}`
   - 코드 채점 실패: attention: 기대 True, 출력 False
2. **kakao__khaiii**
   - 입력: `{"full_name": "kakao/khaiii", "description": "Kakao Hangul Analyzer III", "topics": [], "readme_head": "khaiii\n====\nkhaiii는 \"Kakao Hangul Analyzer III\"의 첫 글자들만 모아 만든 이름으로 카카오에서 개발한 세 번째 형태소분석기입니다. 두 번째 버전의 형태소분석기 이름인 dha2 (Daumkakao Hangul Analyzer 2)를 계승한 이름이기도 합니다.\n\n형태소는 언어학에서 일정한 의미가 있는 가장 작은 말의 단위로 발화체 내에서 따로 떼어낼 수 있는 것을 말합니다. 즉, 더 분석하면 뜻이 없어지는 말의 단위입니다. 형태소분석기는 단어를 보고 형태소 단위로 분리해내는 소프트웨어를 말합니다. 이…"}`
   - 출력: `{"log": "README 첫 문단 근거", "attention": false, "basis": "카카오에서 개발한 세 번째 형태소분석기", "oneliner": "CNN 기반 한국어 형태소분석기"}`
3. **NousResearch__hermes-agent**
   - 입력: `{"full_name": "NousResearch/hermes-agent", "description": "The agent that grows with you", "topics": ["ai", "ai-agent", "ai-agents", "anthropic", "chatgpt", "claude", "claude-code", "codex", "hermes", "hermes-agent", "llm", "nous-research", "openai"], "readme_head": "<p align=\"center\">\n  <img src=\"assets/banner.png\" alt=\"Hermes Agent\" width=\"100%\">\n</p>\n\n# Hermes Agent ☤\n<p align=\"center\">\n  <a href=\"https://hermes-agent.nousresearch.com/\">Hermes Agent</a> \| <a href=\"https://hermes-agent.nousresearch.com/\">Hermes Desktop</a>\n</p>\n<p align=\"center\">\n  <a href=\"ht…"}`
   - 출력: `{"log": "README 첫 문단 근거", "attention": false, "basis": "The self-improving AI agent built by Nous Research", "oneliner": "경험 기반 학습 루프를 갖춘 AI 에이전트"}`
   - Q1 pass: 출력의 '경험 기반 학습 루프를 갖춘 AI 에이전트'는 README의 'The self-improving AI agent', 'built-in learning loop', 'creates skills from experience'와 일치함
   - Q2 pass: 대상(AI 에이전트)과 동작/핵심 메커니즘(경험 기반 학습 루프)이 명확히 드러남
   - Q3 pass: 설치법이나 메신저 연동 등 부수 기능이 아닌 프로젝트의 핵심 정체성인 'self-improving/learning loop'를 잘 포착함

### 반복 기록

| 시각 | 모델 | 프롬프트 | 결과 | 비용 | 메모(바꾼 것) |
|---|---|---|---|---|---|
| 2026-10-07T16:54:25+09:00 | generate | `2969b076772d` | 코드 7/10, Q1 7/7, Q2 7/7, Q3 7/7, 미달 | $0.0149 | 1a 1회차: 새 템플릿(task, core_rules, basis, 문서 태그), 예/아니오 채점 |
| 2026-10-07T16:55:30+09:00 | generate | `7bbc556f62db` | 코드 7/10, Q1 7/7, Q2 7/7, Q3 7/7, 미달 | $0.0100 | 1a 2회차: md 문구 1개(basis는 README 본문에서, 마크업이 끼지 않은 구간) |
| 2026-10-07T16:56:57+09:00 | generate | `c16be6fbb27f` | 코드 8/10, Q1 8/8, Q2 8/8, Q3 8/8, 미달 | $0.0106 | 1a 3회차: 예시 교체 1개(함정 예시 awesome-python → flask: 링크 기호가 낀 구절, description과 다른 문구) |
| 2026-10-07T22:08:20+09:00 | generate | `d77414b2efaf` | 코드 6/7, Q1 5/5, Q2 5/5, Q3 5/5, 미달 (부분 실행) | $0.0089 | 설계 결정 Q3 재측정(3회 상한과 별도): README 기호 정리 입력 + basis 검사를 정리 본문·description 기준으로 |
