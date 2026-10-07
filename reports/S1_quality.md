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

### 가장 나쁜 사례 3개 (generate, 2026-10-07T16:56:57+09:00)

1. **NousResearch__hermes-agent**
   - 입력: `{"full_name": "NousResearch/hermes-agent", "description": "The agent that grows with you", "topics": ["ai", "ai-agent", "ai-agents", "anthropic", "chatgpt", "claude", "claude-code", "codex", "hermes", "hermes-agent", "llm", "nous-research", "openai"], "readme_head": "<p align=\"center\">\n  <img src=\"assets/banner.png\" alt=\"Hermes Agent\" width=\"100%\">\n</p>\n\n# Hermes Agent ☤\n<p align=\"center\">\n  <a href=\"https://hermes-agent.nousresearch.com/\">Hermes Agent</a> \| <a href=\"https://hermes-agent.nousresearch.com/\">Hermes Desktop</a>\n</p>\n<p align=\"center\">\n  <a href=\"ht…"}`
   - 출력: `{"log": "README 첫 문단 근거", "attention": false, "basis": "The self-improving AI agent built by Nous Research", "oneliner": "경험 기반 학습 루프를 갖춘 AI 에이전트"}`
   - 코드 채점 실패: basis가 README 안에 있음: The self-improving AI agent built by Nous Research
2. **fastapi__full-stack-fastapi-template**
   - 입력: `{"full_name": "fastapi/full-stack-fastapi-template", "description": "Full-stack web application template with FastAPI, React, SQLModel, PostgreSQL, Vite, Tailwind CSS, shadcn/ui, FastAPI Cloud, and Docker Compose.", "topics": ["docker", "docker-compose", "fastapi", "fastapi-cloud", "full-stack", "github-actions", "jwt", "openapi", "playwright", "postgresql", "pytest", "python", "react", "shadcn-ui", "sqlmodel", "tailwindcss", "tanstack-query", "tanstack-router", "typescript", "vite"], "readme_head": "# Full Stack FastAPI Template\n\n[![Test Docker Compose](../../actions/workflows/test-docker-compose.yml/badge.svg)](../../actions/workflows/test-docker-compose.yml)\n[![Test Backend](../../actions/workflows/test-backend.yml/badge.svg)](../../actions/workflows/test-backend.yml)\n\n## Technology Stack and…"}`
   - 출력: `{"log": "README 제목과 기술 스택 목록 근거", "attention": false, "basis": "Full-stack web application template with FastAPI, React, SQLModel, PostgreSQL, Vite, Tailwind CSS, shadcn/ui", "oneliner": "FastAPI와 React 기반 풀스택 웹앱 시작 템플릿"}`
   - 코드 채점 실패: basis가 README 안에 있음: Full-stack web application template with FastAPI, React, SQL
3. **Python3WebSpider__Images360**
   - 입력: `{"full_name": "Python3WebSpider/Images360", "description": "Download Images From 360 Using Scrapy", "topics": [], "readme_head": "# Images360\n\nDownload Images From 360 Using Scrapy"}`
   - 출력: `{"log": "README 제목과 설명 한 줄 근거", "attention": true, "basis": "Download Images From 360 Using Scrapy", "oneliner": "Scrapy로 360 이미지 다운로드 스크립트"}`
   - Q1 pass: 출력의 'Scrapy로 360 이미지 다운로드'는 문서의 'Download Images From 360 Using Scrapy'와 정확히 일치함
   - Q2 pass: 대상(360 이미지)과 동작(Scrapy로 다운로드)이 명확히 드러남
   - Q3 pass: README의 유일한 설명이자 주된 기능인 이미지 다운로드를 핵심으로 기술함

### 반복 기록

| 시각 | 모델 | 프롬프트 | 결과 | 비용 | 메모(바꾼 것) |
|---|---|---|---|---|---|
| 2026-10-07T16:54:25+09:00 | generate | `2969b076772d` | 코드 7/10, Q1 7/7, Q2 7/7, Q3 7/7, 미달 | $0.0149 | 1a 1회차: 새 템플릿(task, core_rules, basis, 문서 태그), 예/아니오 채점 |
| 2026-10-07T16:55:30+09:00 | generate | `7bbc556f62db` | 코드 7/10, Q1 7/7, Q2 7/7, Q3 7/7, 미달 | $0.0100 | 1a 2회차: md 문구 1개(basis는 README 본문에서, 마크업이 끼지 않은 구간) |
| 2026-10-07T16:56:57+09:00 | generate | `c16be6fbb27f` | 코드 8/10, Q1 8/8, Q2 8/8, Q3 8/8, 미달 | $0.0106 | 1a 3회차: 예시 교체 1개(함정 예시 awesome-python → flask: 링크 기호가 낀 구절, description과 다른 문구) |
