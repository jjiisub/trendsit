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
| generate (`qwen/qwen3.8-27b`) | 9/10 | 9/9 | 9/9 | 9/9 | 5.0 | 5.0 | 5.0 | 미달 | $0.0012 | `a1a38c7f4dfe` |

- generate 미달 이유: 코드 채점 통과 9/10

### 출력 나란히

| 픽스처 | generate |
|---|---|
| NousResearch__hermes-agent | 경험 기반 학습 루프를 갖춘 AI 에이전트 [Q1○ Q2○ Q3○] |
| Python3WebSpider__Images360 | Scrapy로 360에서 이미지를 다운로드하는 스크립트 [코드 실패] |
| anthropics__claude-code | 터미널에서 코드베이스를 이해하고 자연어 명령으로 개발 작업을 수행하는 에이전틱 코딩 도구 [Q1○ Q2○ Q3○] |
| encode__httpx | HTTP/1.1과 HTTP/2를 지원하는 Python HTTP 클라이언트 라이브러리 [Q1○ Q2○ Q3○] |
| excalidraw__excalidraw | 손그림 스타일 다이어그램을 그리는 오픈소스 가상 화이트보드 [Q1○ Q2○ Q3○] |
| fastapi__full-stack-fastapi-template | FastAPI와 React 기반 풀스택 웹앱 개발용 템플릿 [Q1○ Q2○ Q3○] |
| kakao__khaiii | 데이터 기반 CNN 알고리즘을 활용한 한국어 형태소분석기 [Q1○ Q2○ Q3○] |
| ollama__ollama | 로컬에서 오픈 모델을 실행하고 관리하는 도구 [Q1○ Q2○ Q3○] |
| openai__codex | 터미널에서 로컬로 실행되는 OpenAI 코딩 에이전트 CLI [Q1○ Q2○ Q3○] |
| punkpeye__awesome-mcp-servers | MCP 서버를 정리한 목록 [Q1○ Q2○ Q3○] |

### 가장 나쁜 사례 3개 (generate, 2026-10-08T07:16:21+09:00)

1. **Python3WebSpider__Images360**
   - 입력: `{"full_name": "Python3WebSpider/Images360", "description": "Download Images From 360 Using Scrapy", "topics": [], "readme_head": "# Images360\n\nDownload Images From 360 Using Scrapy"}`
   - 출력: `{"log": "README 제목과 설명 문장 근거", "attention": false, "basis": "Download Images From 360 Using Scrapy", "oneliner": "Scrapy로 360에서 이미지를 다운로드하는 스크립트"}`
   - 코드 채점 실패: attention: 기대 True, 출력 False
2. **NousResearch__hermes-agent**
   - 입력: `{"full_name": "NousResearch/hermes-agent", "description": "The agent that grows with you", "topics": ["ai", "ai-agent", "ai-agents", "anthropic", "chatgpt", "claude", "claude-code", "codex", "hermes", "hermes-agent", "llm", "nous-research", "openai"], "readme_head": "<p align=\"center\">\n  <img src=\"assets/banner.png\" alt=\"Hermes Agent\" width=\"100%\">\n</p>\n\n# Hermes Agent ☤\n<p align=\"center\">\n  <a href=\"https://hermes-agent.nousresearch.com/\">Hermes Agent</a> \| <a href=\"https://hermes-agent.nousresearch.com/\">Hermes Desktop</a>\n</p>\n<p align=\"center\">\n  <a href=\"ht…"}`
   - 출력: `{"log": "README 첫 문단 근거", "attention": false, "basis": "The self-improving AI agent built by Nous Research", "oneliner": "경험 기반 학습 루프를 갖춘 AI 에이전트"}`
   - Q1 pass: 출력의 '경험 기반 학습 루프를 갖춘 AI 에이전트'는 README의 'The self-improving AI agent', 'built-in learning loop', 'creates skills from experience'와 일치함
   - Q2 pass: 대상(AI 에이전트)과 동작/핵심 메커니즘(경험 기반 학습 루프)이 명확히 드러남
   - Q3 pass: 설치법이나 메신저 연동 등 부수 기능이 아닌 프로젝트의 핵심 정체성인 'self-improving/learning loop'를 잘 포착함
3. **anthropics__claude-code**
   - 입력: `{"full_name": "anthropics/claude-code", "description": "Claude Code is an agentic coding tool that lives in your terminal, understands your codebase, and helps you code faster by executing routine tasks, explaining complex code, and handling git workflows - all through natural language commands.", "topics": [], "readme_head": "# Claude Code\n\n![](https://img.shields.io/badge/Node.js-18%2B-brightgreen?style=flat-square) [![npm]](https://www.npmjs.com/package/@anthropic-ai/claude-code)\n\n[npm]: https://img.shields.io/npm/v/@anthropic-ai/claude-code.svg?style=flat-square\n\nClaude Code is an agentic coding tool that lives in you…"}`
   - 출력: `{"log": "README 첫 문단 기능 설명 근거", "attention": false, "basis": "agentic coding tool that lives in your terminal, understands your codebase", "oneliner": "터미널에서 코드베이스를 이해하고 자연어 명령으로 개발 작업을 수행하는 에이전틱 코딩 도구"}`
   - Q1 pass: 출력의 '터미널', '코드베이스 이해', '자연어 명령', '에이전틱 코딩 도구'는 README 첫 문단의 'lives in your terminal, understands your codebase, agentic coding tool, natural language commands'와 일치함
   - Q2 pass: 터미널 환경에서 자연어 명령으로 코드베이스를 이해하고 개발 작업을 돕는 도구임이 대상과 동작으로 명확히 드러남
   - Q3 pass: 설치법이나 부수 플러그인이 아닌 README의 핵심 소개 문구인 agentic coding tool 기능을 정확히 반영함

### 반복 기록

| 시각 | 모델 | 프롬프트 | 결과 | 비용 | 메모(바꾼 것) |
|---|---|---|---|---|---|
| 2026-10-07T16:54:25+09:00 | generate | `2969b076772d` | 코드 7/10, Q1 7/7, Q2 7/7, Q3 7/7, 미달 | $0.0149 | 1a 1회차: 새 템플릿(task, core_rules, basis, 문서 태그), 예/아니오 채점 |
| 2026-10-07T16:55:30+09:00 | generate | `7bbc556f62db` | 코드 7/10, Q1 7/7, Q2 7/7, Q3 7/7, 미달 | $0.0100 | 1a 2회차: md 문구 1개(basis는 README 본문에서, 마크업이 끼지 않은 구간) |
| 2026-10-07T16:56:57+09:00 | generate | `c16be6fbb27f` | 코드 8/10, Q1 8/8, Q2 8/8, Q3 8/8, 미달 | $0.0106 | 1a 3회차: 예시 교체 1개(함정 예시 awesome-python → flask: 링크 기호가 낀 구절, description과 다른 문구) |
| 2026-10-07T22:08:20+09:00 | generate | `d77414b2efaf` | 코드 6/7, Q1 5/5, Q2 5/5, Q3 5/5, 미달 (부분 실행) | $0.0089 | 설계 결정 Q3 재측정(3회 상한과 별도): README 기호 정리 입력 + basis 검사를 정리 본문·description 기준으로 |
| 2026-10-08T07:15:29+09:00 | generate | `a1a38c7f4dfe` | 코드 9/10, Q1 8/8, Q2 8/8, Q3 8/8, 미달 (부분 실행) | $0.0107 | 설계 결정 Q3 재측정 완료(Q4로 S1 예산 0.06): README 기호 정리 입력 + basis 검사 정리 본문·description 각각, 2차 리뷰로 지시 모순 수정 |
| 2026-10-08T07:16:21+09:00 | generate | `a1a38c7f4dfe` | 코드 9/10, Q1 9/9, Q2 9/9, Q3 9/9, 미달 | $0.0012 | 설계 결정 Q3 재측정 완료(Q4 예산 0.06 + 예상 비용 계산의 추론 토큰 이중 합산 수정 뒤 마지막 채점 1건) |
