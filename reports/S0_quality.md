# S0 품질 리포트 (관문 B)

> `python -m trendsit eval`이 자동 생성한다. 원자료는 `reports/eval/*.json`.

## repo_oneliner

문턱값(generate 기준): 정확성 평균 4.5 이상이고 1점 0개, 나머지 평균 4.0 이상, 3점 미만 항목 0개, 코드 채점 전부 통과

### 모델별 최신 결과 (전체 실행만)

| 모델 | 코드 통과 | 정확성 평균(1점) | 구체성 평균(1점) | 표현 평균(1점) | 3점 미만 | 문턱값 | 비용 | 프롬프트 |
|---|---|---|---|---|---|---|---|---|
| generate (`qwen/qwen3.8-27b`) | 10/10 | 4.8 (0) | 4.9 (0) | 5.0 (0) | 0 | 통과 | $0.0096 | `c03ec9c6dcee` |
| judge (`google/gemini-3.8-flash`) | 10/10 | 5.0 (0) | 5.0 (0) | 5.0 (0) | 0 | 통과 | $0.0098 | `c03ec9c6dcee` |

- judge 행은 상한선 측정용. 생성과 채점이 같은 모델이라 자기 출력 채점 편향 가능성이 있음

### 출력 나란히

| 픽스처 | generate | judge |
|---|---|---|
| NousResearch__hermes-agent | 경험 기반 학습 루프를 갖춘 AI 에이전트 [5/4/5] | 경험을 통해 기술을 학습하고 다양한 메신저 및 터미널을 지원하는 AI 에이전트 [5/5/5] |
| Python3WebSpider__Images360 | Scrapy로 360 이미지 다운로드 스크립트 [5/5/5] | Scrapy를 사용해 360에서 이미지를 다운로드하는 도구 [5/5/5] |
| anthropics__claude-code | 터미널에서 자연어 명령으로 코드 작업과 git 워크플로우를 처리하는 에이전틱 코딩 도구 [5/5/5] | 터미널에서 자연어로 코드 설명과 Git 작업을 수행하는 코딩 도구 [5/5/5] |
| encode__httpx | HTTP/1.1과 HTTP/2를 지원하는 Python HTTP 클라이언트 라이브러리 [5/5/5] | 동기 및 비동기 API와 HTTP/2를 지원하는 Python용 HTTP 클라이언트 라이브러리 [5/5/5] |
| excalidraw__excalidraw | 손그림 스타일 다이어그램을 만드는 오픈소스 가상 화이트보드 [5/5/5] | 손그림 스타일의 다이어그램을 그리는 가상 화이트보드 협업 도구 [5/5/5] |
| fastapi__full-stack-fastapi-template | FastAPI, React, PostgreSQL 기반 풀스택 웹앱 개발을 위한 템플릿 [5/5/5] | FastAPI와 React 기반 웹 애플리케이션 개발 템플릿 [5/5/5] |
| kakao__khaiii | CNN 기반 한국어 형태소분석 라이브러리 [5/5/5] | CNN 기반 딥러닝 알고리즘을 사용하는 한국어 형태소 분석기 [5/5/5] |
| ollama__ollama | 로컬에서 오픈소스 LLM을 실행하고 관리하는 도구 [5/5/5] | 오픈 모델을 로컬에서 실행하고 관리하는 도구 [5/5/5] |
| openai__codex | 터미널에서 로컬 코딩 작업을 수행하는 OpenAI CLI 에이전트 [5/5/5] | 로컬 터미널 환경에서 실행되는 OpenAI의 코딩 에이전트 CLI 도구 [5/5/5] |
| punkpeye__awesome-mcp-servers | MCP 서버 구현체와 클라이언트를 주제별로 정리한 목록 [3/5/5] | 다양한 Model Context Protocol(MCP) 서버 구현체를 정리한 목록 [5/5/5] |

### 가장 나쁜 사례 3개 (generate, 2026-10-07T15:57:46+09:00)

1. **punkpeye__awesome-mcp-servers**
   - 입력: `{"full_name": "punkpeye/awesome-mcp-servers", "description": "A collection of MCP servers.", "topics": ["ai", "mcp"], "readme_head": "[![ไทย](https://img.shields.io/badge/Thai-Click-blue)](README-th.md)\n[![English](https://img.shields.io/badge/English-Click-yellow)](README.md)\n[![繁體中文](https://img.shields.io/badge/繁體中文-點擊查看-orange)](README-zh_TW.md)\n[![简体中文](https://img.shields.io/badge/简体中文-点击查看-orange)](README-zh.md)\n[![日本語](htt…"}`
   - 출력: `{"log": "README 첫 문단과 목차 근거", "attention": false, "oneliner": "MCP 서버 구현체와 클라이언트를 주제별로 정리한 목록"}`
   - 정확성 3점: README에서 클라이언트는 별도 저장소(awesome-mcp-clients)를 보라고 안내하며 이 저장소는 MCP 서버 구현체 모음(A curated list of awesome Model Context Protocol (MCP) servers)이 주 내용인데, '클라이언트를 정리한 목록'까지 포함하여 범위가 다소 어긋남
   - 구체성 5점: MCP 서버 구현체 목록이라는 대상과 형태를 명확히 제시하여 무엇을 하는 레포인지 바로 파악할 수 있음
   - 표현 5점: 명사형으로 깔끔하게 마무리되었으며 평가어 및 불필요한 군더더기가 없음
2. **NousResearch__hermes-agent**
   - 입력: `{"full_name": "NousResearch/hermes-agent", "description": "The agent that grows with you", "topics": ["ai", "ai-agent", "ai-agents", "anthropic", "chatgpt", "claude", "claude-code", "codex", "hermes", "hermes-agent", "llm", "nous-research", "openai"], "readme_head": "<p align=\"center\">\n  <img src=\"assets/banner.png\" alt=\"Hermes Agent\" width=\"100%\">\n</p>\n\n# Hermes Agent ☤\n<p align=\"center\">\n  <a href=\"https://hermes-agent.nousresearch.com/\">Hermes Agent</a> \| <a href=\"https://hermes-agent.nousresearch.com/\">Hermes Desktop</a>\n</p>\n<p align=\"center\">\n  <a href=\"ht…"}`
   - 출력: `{"log": "README 첫 문단과 학습 루프 설명 근거", "attention": false, "oneliner": "경험 기반 학습 루프를 갖춘 AI 에이전트"}`
   - 정확성 5점: README의 'built-in learning loop — it creates skills from experience' 내용과 일치함
   - 구체성 4점: 경험 기반 학습 루프를 갖춘 AI 에이전트라는 핵심 동작과 대상이 드러나지만 세부 기능 설명은 다소 압축됨
   - 표현 5점: 명사형 종결이며 불필요한 평가어나 군더더기 없이 간결함
3. **Python3WebSpider__Images360**
   - 입력: `{"full_name": "Python3WebSpider/Images360", "description": "Download Images From 360 Using Scrapy", "topics": [], "readme_head": "# Images360\n\nDownload Images From 360 Using Scrapy"}`
   - 출력: `{"log": "README 제목과 설명 문구 근거", "attention": true, "oneliner": "Scrapy로 360 이미지 다운로드 스크립트"}`
   - 정확성 5점: README 및 description의 'Download Images From 360 Using Scrapy'와 정확히 일치함.
   - 구체성 5점: Scrapy를 사용해 360 이미지를 다운로드한다는 대상과 동작이 명확히 드러남.
   - 표현 5점: 명사형 종결이며 평가어나 군더더기 없이 간결하게 작성됨.

### 반복 기록

| 시각 | 모델 | 프롬프트 | 결과 | 비용 | 메모 |
|---|---|---|---|---|---|
| 2026-10-07T15:39:55+09:00 | generate | `c03ec9c6dcee` | 코드 1/1, 정확성 None, 구체성 None, 표현 None, 미달 (부분 실행) | $0.0004 | 배관 확인(1건) |
| 2026-10-07T15:40:45+09:00 | generate | `c03ec9c6dcee` | 코드 1/1, 정확성 5.0, 구체성 5.0, 표현 5.0, 통과 (부분 실행) | $0.0010 | 배관 확인(1건), judge 추론 설정 수정 후 |
| 2026-10-07T15:41:43+09:00 | generate | `c03ec9c6dcee` | 코드 10/10, 정확성 4.9, 구체성 5.0, 표현 5.0, 통과 | $0.0117 | 1회차: 역할 md 초안 |
| 2026-10-07T15:42:52+09:00 | judge | `c03ec9c6dcee` | 코드 10/10, 정확성 5.0, 구체성 5.0, 표현 5.0, 통과 | $0.0187 | 상한선: judge 모델로 생성(같은 역할 md) |
| 2026-10-07T15:57:46+09:00 | generate | `c03ec9c6dcee` | 코드 10/10, 정확성 4.8, 구체성 4.9, 표현 5.0, 통과 | $0.0096 | 2회차: 리뷰 반영(채점표에서 스펙 밖 문장 제거, 생성은 캐시) |
| 2026-10-07T15:58:27+09:00 | judge | `c03ec9c6dcee` | 코드 10/10, 정확성 5.0, 구체성 5.0, 표현 5.0, 통과 | $0.0098 | 상한선 재채점(채점표 수정 후) |

## lookup_agent

문턱값: 코드 채점 전부 통과

### 모델별 최신 결과 (전체 실행만)

| 모델 | 코드 통과 | 3점 미만 | 문턱값 | 비용 | 프롬프트 |
|---|---|---|---|---|---|
| smoke (`nvidia/nemotron-3-super-120b-a12b:free`) | 5/5 | - | 통과 | $0.0000 | `8543e77a09df` |


### 가장 나쁜 사례 3개 (smoke, 2026-10-07T15:44:47+09:00)

1. **depth1_root**
   - 입력: `{"question": "숫자 6614가 처음 나오는 문서 id를 찾아라."}`
   - 출력: `{"log": "r2에서 6614 확인, 깊이 0", "attention": false, "doc_id": "r2"}`
2. **depth2_shallowest**
   - 입력: `{"question": "숫자 2836이 처음 나오는 문서 id를 찾아라."}`
   - 출력: `{"log": "b2에서 2836 확인, 깊이 1", "attention": false, "doc_id": "b2"}`
3. **depth3_found**
   - 입력: `{"question": "숫자 4172가 처음 나오는 문서 id를 찾아라."}`
   - 출력: `{"log": "a3에서 4172 확인, 깊이 3", "attention": false, "doc_id": "a3"}`

### 반복 기록

| 시각 | 모델 | 프롬프트 | 결과 | 비용 | 메모 |
|---|---|---|---|---|---|
| 2026-10-07T15:44:47+09:00 | smoke | `8543e77a09df` | 코드 5/5, 통과 | $0.0000 | smoke 모델로 도구 루프 실제 1회 확인 |
