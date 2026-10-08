# S2 품질 리포트 (관문 B)

> `python -m trendsit eval`이 자동 생성한다. 원자료는 `reports/eval/*.json`.

## repo_oneliner

문턱값(generate 기준, 코드 채점 통과분의 질문별 통과율): Q1 100%, Q2 90%, Q3 90% 이상 + 코드 채점 전부 통과

- Q1: 근거: oneliner의 모든 내용이 README에 있나?
- Q2: 구체성: 처음 보는 사람이 대상과 동작을 알 수 있나?
- Q3: 핵심: 부수 기능이나 설치법이 아니라 README의 주된 기능을 골랐나?

judge 판정: 사람 라벨과 일치율 확인됨(아래)

### 모델별 최신 결과 (전체 실행만, 점수는 보고용)

| 모델 | 코드 통과 | enforce 후 코드 통과 | Q1 통과 | Q2 통과 | Q3 통과 | 정확성 평균 | 구체성 평균 | 표현 평균 | 문턱값 | 비용 | 프롬프트 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| generate (`qwen/qwen3.8-27b`) | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 5.0 | 5.0 | 5.0 | 통과 | $0.0166 | `a1a38c7f4dfe` |

- generate 모델 일치율(코드 소유 칸, 통과 판정은 enforce 후 값): attention 9/10

### judge·사람 일치율 (라벨 9건, reports/eval/repo_oneliner_generate_20261008-071621.json)

| 질문 | 일치 | 비교 수 | 일치율 |
|---|---|---|---|
| Q1 | 9 | 9 | 1.0 |
| Q2 | 8 | 9 | 0.889 |
| Q3 | 9 | 9 | 1.0 |
| 전체 | 26 | 27 | 0.963 |

### 출력 나란히

| 픽스처 | generate |
|---|---|
| NousResearch__hermes-agent | 경험 기반 학습 루프를 갖춘 AI 에이전트 [Q1○ Q2○ Q3○] |
| Python3WebSpider__Images360 | Scrapy로 360에서 이미지를 다운로드하는 스크립트 [Q1○ Q2○ Q3○] |
| anthropics__claude-code | 터미널에서 자연어 명령으로 코드 작업과 git 워크플로를 처리하는 에이전틱 코딩 도구 [Q1○ Q2○ Q3○] |
| encode__httpx | HTTP/1.1과 HTTP/2를 지원하는 Python HTTP 클라이언트 라이브러리 [Q1○ Q2○ Q3○] |
| excalidraw__excalidraw | 손그림 스타일 다이어그램을 그리는 오픈소스 가상 화이트보드 [Q1○ Q2○ Q3○] |
| fastapi__full-stack-fastapi-template | FastAPI와 React 기반 풀스택 웹앱 시작 템플릿 [Q1○ Q2○ Q3○] |
| kakao__khaiii | 데이터 기반 CNN 알고리즘으로 동작하는 한국어 형태소분석기 [Q1○ Q2○ Q3○] |
| ollama__ollama | 오픈 소스 LLM을 로컬에서 실행하고 관리하는 도구 [Q1○ Q2○ Q3○] |
| openai__codex | 터미널에서 로컬로 실행되는 OpenAI 코딩 에이전트 CLI [Q1○ Q2○ Q3○] |
| punkpeye__awesome-mcp-servers | MCP 서버를 모은 큐레이션 목록 [Q1○ Q2○ Q3○] |

### 가장 나쁜 사례 3개 (generate, 2026-10-08T14:03:18+09:00)

1. **NousResearch__hermes-agent**
   - 입력: `{"full_name": "NousResearch/hermes-agent", "description": "The agent that grows with you", "topics": ["ai", "ai-agent", "ai-agents", "anthropic", "chatgpt", "claude", "claude-code", "codex", "hermes", "hermes-agent", "llm", "nous-research", "openai"], "readme_head": "<p align=\"center\">\n  <img src=\"assets/banner.png\" alt=\"Hermes Agent\" width=\"100%\">\n</p>\n\n# Hermes Agent ☤\n<p align=\"center\">\n  <a href=\"https://hermes-agent.nousresearch.com/\">Hermes Agent</a> \| <a href=\"https://hermes-agent.nousresearch.com/\">Hermes Desktop</a>\n</p>\n<p align=\"center\">\n  <a href=\"ht…"}`
   - 출력: `{"log": "README 첫 문단 근거", "attention": false, "basis": "The self-improving AI agent built by Nous Research", "oneliner": "경험 기반 학습 루프를 갖춘 AI 에이전트"}`
   - Q1 pass: 출력의 '경험 기반 학습 루프'와 'AI 에이전트'는 문서의 'built-in learning loop', 'creates skills from experience', 'AI agent'와 일치
   - Q2 pass: 경험을 통해 학습 루프를 도는 AI 에이전트라는 대상과 주요 동작 특성이 명확함
   - Q3 pass: README 첫 문단에서 강조하는 핵심 정의인 자기 개선/학습 루프 에이전트를 잘 포착함
2. **Python3WebSpider__Images360**
   - 입력: `{"full_name": "Python3WebSpider/Images360", "description": "Download Images From 360 Using Scrapy", "topics": [], "readme_head": "# Images360\n\nDownload Images From 360 Using Scrapy"}`
   - 출력: `{"log": "README 제목과 설명 문장 근거", "attention": false, "basis": "Download Images From 360 Using Scrapy", "oneliner": "Scrapy로 360에서 이미지를 다운로드하는 스크립트"}`
   - enforce: attention False → True (README 본문 200자 미만)
   - Q1 pass: 출력의 'Scrapy로 360에서 이미지를 다운로드'는 문서의 'Download Images From 360 Using Scrapy'와 정확히 일치함
   - Q2 pass: 대상(360의 이미지)과 동작(Scrapy로 다운로드)이 명확히 드러남
   - Q3 pass: 문서 전체가 나타내는 단일 핵심 기능을 정확히 포착함
3. **anthropics__claude-code**
   - 입력: `{"full_name": "anthropics/claude-code", "description": "Claude Code is an agentic coding tool that lives in your terminal, understands your codebase, and helps you code faster by executing routine tasks, explaining complex code, and handling git workflows - all through natural language commands.", "topics": [], "readme_head": "# Claude Code\n\n![](https://img.shields.io/badge/Node.js-18%2B-brightgreen?style=flat-square) [![npm]](https://www.npmjs.com/package/@anthropic-ai/claude-code)\n\n[npm]: https://img.shields.io/npm/v/@anthropic-ai/claude-code.svg?style=flat-square\n\nClaude Code is an agentic coding tool that lives in you…"}`
   - 출력: `{"log": "README 첫 문단 기능 설명 근거", "attention": false, "basis": "agentic coding tool that lives in your terminal, understands your codebase, and helps you code faster", "oneliner": "터미널에서 자연어 명령으로 코드 작업과 git 워크플로를 처리하는 에이전틱 코딩 도구"}`
   - Q1 pass: 출력의 터미널, 자연어 명령, 코드 작업 및 git 워크플로 처리는 README 첫 문단의 'lives in your terminal', 'natural language commands', 'executing routine tasks... git workflows'와 정확히 일치함
   - Q2 pass: 대상(터미널 환경, 코드 및 git 워크플로)과 동작(자연어 명령으로 처리하는 에이전틱 코딩)이 구체적으로 명시되어 처음 보는 사람도 기능을 바로 파악할 수 있음
   - Q3 pass: 설치법이나 플러그인 등 부수 내용이 아닌 README 서두의 주된 핵심 기능 설명을 정확히 골라냄

### 반복 기록

| 시각 | 모델 | 프롬프트 | 결과 | 비용 | 메모(바꾼 것) |
|---|---|---|---|---|---|
| 2026-10-08T10:42:52+09:00 | generate | `a1a38c7f4dfe` | 코드 9/10, Q1 9/9, Q2 9/9, Q3 9/9, 미달 | $0.0155 |  |
| 2026-10-08T14:03:18+09:00 | generate | `a1a38c7f4dfe` | 코드 10/10, Q1 10/10, Q2 10/10, Q3 10/10, 통과 | $0.0166 | 재채점(설계 결정 Q1) reports/eval/repo_oneliner_generate_20261008-104252.json |

## item_card

문턱값(generate 기준, 코드 채점 통과분의 질문별 통과율): Q1 80%, Q2 80%, Q3 80% 이상 + 코드 채점 전부 통과

- Q1: 충실성: summary와 claims의 모든 내용이 quotes(본문 문장)로 뒷받침되나?
- Q2: 핵심: 부수 내용(행사 안내, 구독 권유, 저자 소개)이 아니라 본문의 주된 내용을 담았나?
- Q3: 원본 판정: needs_original이 "수치·주장의 출처가 본문 밖 링크에 있는지"와 맞나?

judge 판정: **잠정**(사람 라벨 없음. `eval/labels/item_card.csv`를 채우면 일치율을 잰다)

### 모델별 최신 결과 (전체 실행만, 점수는 보고용)

| 모델 | 코드 통과 | enforce 후 코드 통과 | Q1 통과 | Q2 통과 | Q3 통과 | 충실성 평균 | 핵심 포착 평균 | 판정 평균 | 문턱값 | 비용 | 프롬프트 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| generate (`qwen/qwen3.8-27b`) | 20/21 | 21/21 | 20/20 | 20/20 | 19/20 | 5.0 | 5.0 | 4.9 | 미달 | $0.0914 | `2691c9a33fbc` |

- generate 전체 지표: 인용 본문 일치 108/108 (100.0%), 잘린 인용 5/108 (4.6%)
- generate 모델 일치율(코드 소유 칸, 통과 판정은 enforce 후 값): attention 20/21, quotes 16/21
- generate 미달 이유: 코드 채점 통과 20/21

### 가장 나쁜 사례 3개 (generate, 2026-10-08T15:20:08+09:00)

1. **simonw__kakapo-party**
   - 입력: `{"item_id": 28, "title": "kakapo party", "source_name": "Simon Willison's Weblog", "source_kind": "curation", "url": "https://simonwillison.net/2026/Sep/26/kakapo-party/", "body": {"id": "it:28", "source": "Simon Willison's Weblog", "text": "I presented a closing keynote for the WeAreDevelopers World Congress North America yesterday. As a STAR moment I decided to weave in references to the record breaking kākāpō breeding season we had in 2026.\nFor my closing slide I wanted to celebrate, and I had seen some buzz around how good Claude Opus 5.5 was at creating pixel art animations. So I rounded up three Kakapo photos from Google image search and dropped them into Claude with this prompt:\nHere are some photos of kakapo parrots just to remind you what they look like I need you to make an animation in animated pixel art on HTML 5 canvas of obviously pixel art kakapo jumping up and down having a party with confetti and suchlike - there should be at least 20 of them\nHere are some photos of kakapo parrots just to remind you what they look like\nI need you to make an animation in animated pixel art on HTML 5 canvas of obviously pixel art kakapo jumping up and down having a party with confetti and suchlike - there should be at least 20 of them\nHere's the transcript, and this is the resulting page. It's pretty great!\nI wanted to embed it in a Keynote presentation file, so I downloaded the HTML and told a local Claude Code session:\nMake me a video of file:///Users/simon/Downloads/kakapo-party.html - you need to load it in a browser and click on it a few times to get the confetti effect, the video should be 15s long don't start clicking until 3s in make sure several clicks are spread around the clickable area\nMake me a video of file:///Users/simon/Downloads/kakapo-party.html - you need to load it in a browser and click on it a few times to get the confetti effect, the video should be 15s long\ndon't start clicking until 3s in\nmake sure several clicks are spread around the clickable area\nClaude Code used Playwright (transcript here) and produced this video, which was exactly what I needed for my final slide:\nYour browser does not support HTML5 video.\nHere's the full Playwright script it used, which was pleasingly short:\n# /// script # dependencies = [\"playwright\"] # /// import time from playwright.sync_api import sync_playwright W, H = 1280, 720 # Canvas fills the viewport; spread clicks across corners, edges and centre clicks = [ (3.0, 640, 360), # centre (4.2, 160, 120), # top-left (5.4, 1120, 120), # top-right (6.6, 180, 600), # bottom-left (7.8, 1100, 600), # bottom-right (9.0, 640, 100), # top-centre (10.0, 380, 380), # mid-left (11.0, 900, 380), # mid-right (12.2, 640, 620), # bottom-centre (13.2, 640, 300), # finale centre ] with sync_playwright() as p: b = p.chromium.launch() ctx = b.new_context(viewport={\"width\":W,\"height\":H}, record_video_dir=\"vids\", record_video_size={\"width\":W,\"height\":H}) page = ctx.new_page() t0 = time.time() page.goto(\"file:///Users/simon/Downloads/kakapo-party.html\") for t,x,y in clicks: time.sleep(max(0, t-(time.time()-t0))) page.mouse.click(x,y) time.sleep(max(0, 16.0-(time.time()-t0))) ctx.close(); b.close()", "title": "kakapo party", "url": "https://simonwillison.net/2026/Sep/26/kakapo-party/"}, "links": [{"n": 1, "url": "https://tools.simonwillison.net/kakapo-party", "kind": "curation", "anchor": "Kākāpō Party", "role": "body"}, {"n": 2, "url": "https://www.wearedevelopers.com/world-congress-north-america", "kind": "other", "anchor": "WeAreDevelopers World Congress North America", "role": "body"}, {"n": 3, "url": "https://www.doc.govt.nz/news/media-releases/2026-media-releases/kakapo-population-reaches-new-milestone/", "kind": "other", "anchor": "kākāpō breeding season", "role": "body"}, {"n": 4, "url": "https://claude.ai/share/43bec0be-a0a3-4737-bfac-34894af34ddc", "kind": "other", "anchor": "the transcript", "role": "body"}, {"n": 5, "url": "https://gisthost.github.io/?368b481fba654c4fb84d90188da77581/page-001.html", "kind": "other", "anchor": "transcript here", "role": "body"}], "keywords": [{"id": "agent", "name": "AI 에이전트"}, {"id": "coding-agent", "name": "코딩 에이전트"}, {"id": "mcp-tools", "name": "MCP · 도구 호출"}, {"id": "open-weight", "name": "오픈웨이트 · 로컬 LLM"}, {"id": "rag-search", "name": "RAG · 검색"}, {"id": "multimodal", "name": "멀티모달"}, {"id": "reasoning", "name": "추론 · 판단 모델"}, {"id": "eval", "name": "평가 · 벤치마크"}, {"id": "ai-security", "name": "AI 보안"}, {"id": "frontier-release", "name": "프런티어 모델 출시"}, {"id": "ai-industry", "name": "AI 산업 · 시장"}, {"id": "dev-practice", "name": "개발 실무 · 경험"}, {"id": "ai-general", "name": "AI 일반"}]}`
   - 출력: `{"log": "개발 실무 경험 글, 수치 2개, 원본 확인 불필요", "attention": false, "quotes": [{"n": 1, "text": "I presented a closing keynote for the WeAreDevelopers World Congress North America yesterday."}, {"n": 2, "text": "I had seen some buzz around how good Claude Opus 5.5 was at creating pixel art animations."}, {"n": 3, "text": "I rounded up three Kakapo photos from Google image search and dropped them into Claude with this prompt:"}, {"n": 4, "text": "I wanted to embed it in a Keynote presentation file, so I downloaded the HTML and told a local Claude Code session:"}, {"n": 5, "text": "Claude Code used Playwright (transcript here) and produced this video, which was exactly what I needed for my final slide:"}], "numbers": [{"quote_n": 3, "value": "three", "unit": "", "what": "Claude에 입력한 카카포 사진 수"}, {"quote_n": 5, "value": "15s", "unit": "", "what": "생성된 영상 길이"}], "claims": [{"quote_ns": [1, 2, 3], "text": "WeAreDevelopers World Congress North America 기조연설을 위해 Claude Opus 5.5로 카카포 픽셀 아트 애니메이션을 생성했다."}, {"quote_ns": [4, 5], "text": "Claude Code가 Playwright를 사용해 HTML 파일을 브라우저에서 조작하고 15초짜리 영상을 생성했다."}], "summary": "Simon Willison은 WeAreDevelopers World Congress North America 기조연설을 위해 Claude Opus 5.5로 카카포 픽셀 아트 애니메이션을 생성했다. 이후 Claude Code를 통해 Playwright 스크립트를 작성해 해당 HTML을 브라우저에서 조작하고 15초짜리 영상을 만들어 프레젠테이션에 활용했다.", "entities": ["Simon Willison", "WeAreDevelopers World Congress North America", "Claude Opus 5.5", "Claude Code", "Playwright", "Kākāpō"], "keywords": ["coding-agent", "dev-practice", "multimodal"], "is_curation": false, "origin_candidates": [], "relevance_reason": "Claude Code와 Playwright를 활용한 개발 실무 사례로 코딩 에이전트 활용법에 해당", "relevance": "mid", "needs_original_reason": "글 자체가 직접 경험한 개발 실무 기록이며 외부 출처 확인이 필요한 수치나 주장 없음", "needs_original": false}`
   - 코드 채점 실패: 수치가 그 quote 안에 있음: 15s(q5)
   - enforce: numbers [{'quote_n': 3, 'value': 'three', 'unit': '', 'what': 'Claude에 입력한 카카포 사진 수'}, {'quote_n': 5, 'value': '15s', 'unit': '', 'what': '생성된 영상 길이'}] → [{'quote_n': 3, 'value': 'three', 'unit': '', 'what': 'Claude에 입력한 카카포 사진 수'}] (인용에 없는 수치 삭제)
   - enforce: attention False → True (인용·수치 정리가 있어 사람 확인)
2. **aitimes__articleView-html-idxno-215937**
   - 입력: `{"item_id": 189, "title": "엔비디아, 4999달러짜리 ‘DGX 스파크’ 출시...메모리 대란에 가격 낮췄다", "source_name": "AI타임스", "source_kind": "news", "url": "https://www.aitimes.com/news/articleView.html?idxno=215937", "body": {"id": "it:189", "source": "AI타임스", "text": "엔비디아가 최근 메모리 수급 악화로 고성능 장비 가격이 치솟는 상황에서 개발자의 가격 부담을 낮춘 데스크톱 AI 슈퍼컴퓨터를 선보였다.\n엔비디아는 2일(현지시간) 데스크톱에서 대규모 AI 모델과 에이전트를 직접 실행할 수 있도록 설계한 ‘DGX 스파크’의 64GB 모델을 공개했다.\n클라우드 API를 호출하는 대신 개인용 컴퓨터에서 오픈 모델과 AI 에이전트를 상시 실행하려는 개발자를 겨냥한 제품이다.\n새로운 64GB DGX 스파크는 4999달러(약 674만원)부터 시작하며, 오는 23일부터 에이서, 에이수스, 델, 기가바이트, HP, MSI 등 파트너사를 통해 출시된다. 최근 메모리 수급 악화로 기존 128GB 모델 가격이 6950달러(약 936만원)까지 상승함에 따라, 개발자들의 가격 부담을 낮추기 위한 대안으로 기획됐다.\n기존 제품과 마찬가지로 엔비디아의 GB10 그레이스 블랙웰 슈퍼칩과 CUDA 기반 AI 소프트웨어 스택, ConnectX-7 네트워크를 탑재한다. 차이는 통합 메모리가 기존 128GB에서 64GB LPDDR5x로 줄었다는 점이다.\n엔비디아는 64GB 모델이 현재 활용도가 높은 300억~350억 매개변수급 오픈 모델을 실행하기에 적합하다고 설명했다. 더 큰 모델이나 메모리가 많이 필요한 작업에는 기존 128GB 모델을 사용할 수 있다.\n이 제품의 핵심은 CPU와 GPU가 하나의 메모리 풀을 공유하는 구조다. GB10은 20코어 그레이스 CPU와 5세대 텐서 코어를 탑재한 블랙웰 GPU를 결합했으며, GPU는 희소성(sparsity)을 적용할 경우 최대 1페타플롭의 FP4 AI 연산 성능을 제공한다. CPU와 GPU는 NV링크-C2C로 연결돼 PCIe 5세대보다 높은 대역폭으로 데이터를 공유한다.\n이 구조에서는 모델 가중치를 시스템 메모리와 GPU 메모리 사이에서 복사할 필요가 없다. 여러 모델과 KV 캐시, 에이전트의 도구 프로세스를 하나의 메모리 공간에서 처리할 수 있어 장시간 실행되는 AI 에이전트에 적합하다는 설명이다.\n소프트웨어도 처음부터 갖춰져 있다. DGX OS에는 파이토치와 주피터, 올라마 등이 포함되며, 엔비디아의 '네모클로(NemoClaw)'를 설치하면 '오픈클로(OpenClaw)' 에이전트에 개인정보 보호와 보안 기능을 추가할 수 있다. 엔비디아 오픈셸과 에이전트 툴킷을 이용하면 정책 기반 가드레일도 적용할 수 있다.\n두 대의 64GB DGX 스파크를 연결하면 클러스터 전체에서 128GB 메모리와 더 많은 연산 성능을 사용할 수 있다. 엔비디아에 따르면 64GB 모델 2대를 연결할 경우, 동일한 메모리 용량을 가진 단일 128GB 시스템 대비 최대 1.7배 높은 성능을 낼 수 있다. ConnectX-7 200GbE 네트워크를 이용하며, 싱크 클러스터 어시스턴트(Sync Cluster Assistant)가 여러 시스템의 연결과 설정을 지원한다. 최대 4대까지 연결할 수 있다.\n로컬 AI 환경에서 활용할 수 있는 모델과 도구도 소개했다. 메타의 ‘뮤즈 글리머(Muse Glimmer)’ 같은 300억 매개변수급 모델을 이용해 개인용 AI 에이전트를 만들거나, 코드 저장소와 테스트 도구를 연결해 개발 작업을 자동화할 수 있다. 새로운 오픈 모델이 공개되면 로컬에서 직접 내려받아 자체 평가를 반복하는 것도 가능하다.\n이처럼 로컬에서 AI를 실행하는 이유 중 하나는 에이전트 사용량 증가다. 에이전트는 도구 호출과 재시도, 긴 컨텍스트, 여러 단계의 작업 과정에서 지속적으로 토큰을 소비한다. 클라우드 API에서는 사용한 토큰마다 비용이 발생하지만, 자체 장비에서는 모델을 실행하는 동안 토큰당 별도 요금이 발생하지 않는다.\n시장에서는 이번 64GB DGX 스파크 출시가 애플의 '맥 미니 M4 프로'나 '맥 스튜디오' 등 64GB 이상 통합 메모리를 갖춘 개인용 AI 개발 장비 수요를 직접 겨냥한 것으로 보고 있다. 맥 미니 M4 프로는 64GB 통합 메모리 옵션을 적용하더라도 2000달러대 후반에서 3000달러대 초반 수준으로 가격 경쟁력이 뛰어난 편이다.\n이처럼 맥 시리즈가 상대적으로 저렴한 가격과 높은 메모리 대역폭을 앞세운다면, 엔비디아는 4999달러라는 가격에 데스크톱 크기에서 데이터센터급 쿠다(CUDA) 소프트웨어 생태계와 고성능 AI 연산, 초고속 클러스터링을 완벽히 지원한다는 점을 차별점으로 내세운다.\n한편, 기존의 DGX 스파크 128GB 모델은 더 큰 AI 모델 구동이나 미세조정 등 메모리 집약적인 작업을 위해 계속 제공된다.\n박찬 기자 cpark@aitimes.com", "title": "엔비디아, 4999달러짜리 ‘DGX 스파크’ 출시...메모리 대란에 가격 낮췄다", "url": "https://www.aitimes.com/news/articleView.html?idxno=215937"}, "links": [], "keywords": [{"id": "agent", "name": "AI 에이전트"}, {"id": "coding-agent", "name": "코딩 에이전트"}, {"id": "mcp-tools", "name": "MCP · 도구 호출"}, {"id": "open-weight", "name": "오픈웨이트 · 로컬 LLM"}, {"id": "rag-search", "name": "RAG · 검색"}, {"id": "multimodal", "name": "멀티모달"}, {"id": "reasoning", "name": "추론 · 판단 모델"}, {"id": "eval", "name": "평가 · 벤치마크"}, {"id": "ai-security", "name": "AI 보안"}, {"id": "frontier-release", "name": "프런티어 모델 출시"}, {"id": "ai-industry", "name": "AI 산업 · 시장"}, {"id": "dev-practice", "name": "개발 실무 · 경험"}, {"id": "ai-general", "name": "AI 일반"}]}`
   - 출력: `{"log": "언론 보도, 수치 4개, 원본 확인 필요", "attention": false, "quotes": [{"n": 1, "text": "엔비디아는 2일(현지시간) 데스크톱에서 대규모 AI 모델과 에이전트를 직접 실행할 수 있도록 설계한 ‘DGX 스파크’의 64GB 모델을 공개했다."}, {"n": 2, "text": "새로운 64GB DGX 스파크는 4999달러(약 674만원)부터 시작하며, 오는 23일부터 에이서, 에이수스, 델, 기가바이트, HP, MSI 등 파트너사를 통해 출시된다."}, {"n": 3, "text": "최근 메모리 수급 악화로 기존 128GB 모델 가격이 6950달러(약 936만원)까지 상승함에 따라, 개발자들의 가격 부담을 낮추기 위한 대안으로 기획됐다."}, {"n": 4, "text": "엔비디아는 64GB 모델이 현재 활용도가 높은 300억~350억 매개변수급 오픈 모델을 실행하기에 적합하다고 설명했다."}, {"n": 5, "text": "엔비디아에 따르면 64GB 모델 2대를 연결할 경우, 동일한 메모리 용량을 가진 단일 128GB 시스템 대비 최대 1.7배 높은 성능을 낼 수 있다."}], "numbers": [{"quote_n": 2, "value": "4999달러", "unit": "", "what": "64GB DGX 스파크 시작 가격"}, {"quote_n": 3, "value": "6950달러", "unit": "", "what": "기존 128GB 모델 가격"}, {"quote_n": 4, "value": "300억~350억", "unit": "매개변수", "what": "적합한 오픈 모델 규모"}, {"quote_n": 5, "value": "1.7배", "unit": "", "what": "2대 연결 시 단일 128GB 대비 성능"}], "claims": [{"quote_ns": [1, 2, 3], "text": "엔비디아가 메모리 수급 악화로 인한 가격 상승을 고려해 4999달러의 64GB DGX 스파크 모델을 출시했다."}, {"quote_ns": [4], "text": "64GB 모델은 300억~350억 매개변수급 오픈 모델 실행에 적합하다."}, {"quote_ns": [5], "text": "64GB 모델 2대를 연결하면 단일 128GB 시스템 대비 최대 1.7배 높은 성능을 낸다."}], "summary": "엔비디아가 메모리 수급 악화로 기존 128GB 모델 가격이 상승한 상황에서, 4999달러의 64GB DGX 스파크 모델을 출시했다. 이 모델은 300억~350억 매개변수급 오픈 모델 실행에 적합하며, 2대를 연결하면 단일 128GB 시스템 대비 최대 1.7배 높은 성능을 제공한다.", "entities": ["엔비디아", "DGX 스파크", "GB10", "CUDA", "ConnectX-7", "NemoClaw", "OpenClaw", "Muse Glimmer"], "keywords": ["agent", "open-weight", "ai-industry"], "is_curation": false, "origin_candidates": [], "relevance_reason": "로컬 AI 실행용 하드웨어 출시와 에이전트·오픈웨이트 모델 관련 수치가 중심", "relevance": "high", "needs_original_reason": "언론 기사로 엔비디아 발표 내용을 보도했으며, 원본 링크가 제공되지 않아 원본 대조가 필요", "needs_original": true}`
   - Q1 pass: summary와 claims의 내용(4999달러 64GB 모델 출시, 300억~350억 매개변수 오픈 모델 적합, 2대 연결 시 1.7배 성능 등)이 quotes 1~5의 본문 문장과 정확히 일치함
   - Q2 pass: 엔비디아의 64GB DGX 스파크 출시 배경, 가격, 사양 및 활용 목적 등 기사의 핵심 발표 내용을 충실히 담고 있음
   - Q3 fail: source_fields.links가 '(없음)'이고 본문에도 외부 원본 링크가 없는데 needs_original을 true로 판정함
3. **aitimes__articleView-html-idxno-215688**
   - 입력: `{"item_id": 23, "title": "원프레딕트 “버려지던 제조 데이터, AI 자산으로 바꾸겠다”", "source_name": "AI타임스", "source_kind": "news", "url": "https://www.aitimes.com/news/articleView.html?idxno=215688", "body": {"id": "it:23", "source": "AI타임스", "text": "산업 AI 전문 원프레딕트(대표 윤병동)는 ‘제조 데이터 자산화’를 통해 공장 전체 운영을 AI 중심으로 혁신하는 ‘AI 네이티브 팩토리’를 추진하겠다고 밝혔다.\n윤병동 원프레딕트 대표는 현재 제조 현장의 가장 큰 문제로 설비와 시스템별로 파편화된 데이터 구조를 꼽았다. 제품이나 공정 조건과 연결되지 못한 채, 설비 상태 확인이나 생산 결과 기록 등 일회성으로 소비되고 버려지는 소모성 데이터가 대부분이라는 지적이다.\n이처럼 현장에 축적된 데이터를 AI가 지속적으로 학습·재활용할 수 있는 ‘자산성 데이터’로 바꾸지 않는다면, AI를 도입할 때마다 데이터를 재정리해야 해 막대한 시간과 비용이 소요될 수밖에 없다.\n■ 소모성 데이터를 반복 활용 가능한 '자산'으로\n'제조 데이터 자산화'란 데이터 자체와 발생 맥락을 함께 축적해 AI가 반복 활용할 수 있도록 만드는 과정이다. 서로 다른 형식의 데이터를 동일한 기준에 맞춰 정제하고 시간 축을 맞추는 구조화 작업이 선행돼야 한다.\n결국 핵심은 산재한 산업 데이터를 단순히 모으는 데 그치지 않고, 현장의 맥락을 반영해 AI 학습에 즉시 투입 가능한 ‘AI 레디 데이터’로 재구성하는 데 있다.\n이를 수행하는 데이터 수집·정제·저장 플랫폼이 '데이터스루(DATATHRU)'다. 멀티모달 산업 데이터를 처리하고 제조 현장의 맥락을 결합해 구조화한다. 이렇게 자산화된 데이터는 제조 데이터·AI 운영 플랫폼 ‘사이클론(cyclone)’을 통해 관리되며, 이후 제조 특화 AI 모델링과 실제 현장 운영으로 연결된다.\n데이터의 맥락이 결합면 전체 공정에 대한 유기적 해석이 가능해진다. 예를 들어 설비의 진동 수치 상승만으로는 원인 파악이 어렵지만, 당시 생산 제품, 운전 조건, 생산 부하, 품질 결과가 함께 연동되면 비로소 AI가 분석할 수 있는 유의미한 정보가 된다.\n■ 데이터 자산화 기반의 현장 판단과 조치 자동화\n데이터스루와 사이클론이 데이터 자산화와 AI 모델 운영 기반을 담당하고 나면, 산업 AI 운영 플랫폼 ‘pdx’는 자산성 데이터를 실제 제조 업무로 연결한다. 일종의 팩토리 운영체계(OS)로, AI 분석 결과와 판단에 필요한 정보를 현장 담당자에게 제공해 점검·정비·공정 운영을 위한 판단과 조치를 지원한다.\n원프레딕트는 현재 230개 이상 사이트와 1431개 이상 설비 규모의 산업현장에서 기술 적용 경험을 축적해 왔으며, 누적 100여개사·200건 이상의 거래 경험을 보유하고 있다. 그만큼 유의미한 사례도 다수 있다고 밝혔다.\n실제 발전소 설비 예지보전 사례가 대표적이다. 분산된 설비 데이터를 통합 연결하고 pdx를 통해 주요 설비의 건전성을 모니터링하는 체계를 구축해 구체적인 성과를 입증했다. AI가 모터의 전류 불평형을 감지한 뒤 진동 데이터를 합산 분석해 기어 결함을 특정했으며, 이를 통해 비계획 다운타임(시스템 중단 시간)을 30% 줄였다.\n운영 단계의 데이터 관리도 고도화했다. ‘테크플럭스(TECHFLUX)’는 학습부터 재학습, 버전 관리에 이르는 6단계 운영 구조를 통해 데이터 변화 및 드리프트를 24시간 내 탐지한다. 이를 통해 AI 운영 공수를 약 70% 절감했다. 아울러 다양한 제조 환경에 맞춰 기술체계를 표준화함으로써 연동 개발 공수를 최대 50% 줄이고 신규 산업 적용 기간도 크게 단축했다.\n■ 'AI 네이티브 팩토리'가 갖는 차별성\n윤 대표는 정부의 제조 AI 확산 사업 등 개별 공정에 단편적으로 AI를 붙이는 기존 'AI 팩토리'와 자사의 'AI 네이티브 팩토리'를 명확히 구분했다. 원프레딕트의 비전은 제조 데이터와 AI 모델·에이전트를 공장 운영 전반에 내재화하는 데 있다.\n이를 위해 데이터 준비부터 모델링, 현장 운영으로 이어지는 산업 AI 전주기 기술 체계를 구축했다. 범용 AI와 달리 제조 AI는 물리적 특성과 도메인 지식 이해가 필수적인 만큼, 원프레딕트는 관련 특허 21건을 포함해 총 42건의 국내 등록 특허를 확보하며 기술 자산을 축적해 왔다.\n윤 대표는 “AI 에이전트 도입이 본격화할수록 데이터의 지속적인 축적과 재활용성이 현장 맞춤형 AI 고도화의 핵심이 될 것”이라고 말했다.\n이어 “제조 AI 경쟁의 축이 단순한 '데이터의 양'에서 '데이터의 활용도'로 이동하고 있다”며 “일회성 데이터를 지속 가능한 자산으로 전환하는 것이 AI 네이티브 팩토리 구축의 출발점”이라고 강조했다.\n한편, 원프레딕트는 최근 코스닥 기술특례 상장을 위한 기술성 평가를 통과했으며, 연내 상장 예비심사를 추진할 예정이다.\n장세민 기자 semim99@aitimes.com", "title": "원프레딕트 “버려지던 제조 데이터, AI 자산으로 바꾸겠다”", "url": "https://www.aitimes.com/news/articleView.html?idxno=215688"}, "links": [], "keywords": [{"id": "agent", "name": "AI 에이전트"}, {"id": "coding-agent", "name": "코딩 에이전트"}, {"id": "mcp-tools", "name": "MCP · 도구 호출"}, {"id": "open-weight", "name": "오픈웨이트 · 로컬 LLM"}, {"id": "rag-search", "name": "RAG · 검색"}, {"id": "multimodal", "name": "멀티모달"}, {"id": "reasoning", "name": "추론 · 판단 모델"}, {"id": "eval", "name": "평가 · 벤치마크"}, {"id": "ai-security", "name": "AI 보안"}, {"id": "frontier-release", "name": "프런티어 모델 출시"}, {"id": "ai-industry", "name": "AI 산업 · 시장"}, {"id": "dev-practice", "name": "개발 실무 · 경험"}, {"id": "ai-general", "name": "AI 일반"}]}`
   - 출력: `{"log": "산업 AI 기사, 수치 10개, 원본 확인 불필요", "attention": false, "quotes": [{"n": 1, "text": "산업 AI 전문 원프레딕트(대표 윤병동)는 ‘제조 데이터 자산화’를 통해 공장 전체 운영을 AI 중심으로 혁신하는 ‘AI 네이티브 팩토리’를 추진하겠다고 밝혔다."}, {"n": 2, "text": "이를 수행하는 데이터 수집·정제·저장 플랫폼이 '데이터스루(DATATHRU)'다. 멀티모달 산업 데이터를 처리하고 제조 현장의 맥락을 결합해 구조화한다."}, {"n": 3, "text": "원프레딕트는 현재 230개 이상 사이트와 1431개 이상 설비 규모의 산업현장에서 기술 적용 경험을 축적해 왔으며, 누적 100여개사·200건 이상의 거래 경험을 보유하고 있다."}, {"n": 4, "text": "AI가 모터의 전류 불평형을 감지한 뒤 진동 데이터를 합산 분석해 기어 결함을 특정했으며, 이를 통해 비계획 다운타임(시스템 중단 시간)을 30% 줄였다."}, {"n": 5, "text": "‘테크플럭스(TECHFLUX)’는 학습부터 재학습, 버전 관리에 이르는 6단계 운영 구조를 통해 데이터 변화 및 드리프트를 24시간 내 탐지한다. 이를 통해 AI 운영 공수를 약 70% 절감했다."}, {"n": 6, "text": "원프레딕트는 관련 특허 21건을 포함해 총 42건의 국내 등록 특허를 확보하며 기술 자산을 축적해 왔다."}], "numbers": [{"quote_n": 3, "value": "230개", "unit": "", "what": "기술 적용 경험 사이트 수"}, {"quote_n": 3, "value": "1431개", "unit": "", "what": "기술 적용 경험 설비 규모"}, {"quote_n": 3, "value": "100여개사", "unit": "", "what": "누적 거래 경험 기업 수"}, {"quote_n": 3, "value": "200건", "unit": "", "what": "누적 거래 경험 건수"}, {"quote_n": 4, "value": "30%", "unit": "", "what": "비계획 다운타임 감소율"}, {"quote_n": 5, "value": "6단계", "unit": "", "what": "테크플럭스 운영 구조 단계"}, {"quote_n": 5, "value": "24시간", "unit": "", "what": "데이터 드리프트 탐지 시간"}, {"quote_n": 5, "value": "70%", "unit": "", "what": "AI 운영 공수 절감률"}, {"quote_n": 6, "value": "21건", "unit": "", "what": "관련 특허 수"}, {"quote_n": 6, "value": "42건", "unit": "", "what": "총 국내 등록 특허 수"}], "claims": [{"quote_ns": [1], "text": "원프레딕트는 제조 데이터 자산화를 통해 AI 네이티브 팩토리를 추진한다."}, {"quote_ns": [2], "text": "데이터스루(DATATHRU) 플랫폼이 멀티모달 산업 데이터를 처리하고 구조화한다."}, {"quote_ns": [3, 4, 5], "text": "230개 이상 사이트에서 기술 적용했으며, 발전소 예지보전 사례로 다운타임을 30% 줄이고 AI 운영 공수를 70% 절감했다."}, {"quote_ns": [6], "text": "총 42건의 국내 등록 특허를 확보했다."}], "summary": "원프레딕트는 제조 데이터 자산화를 통해 AI 네이티브 팩토리를 추진하며, 데이터스루와 사이클론, pdx 플랫폼을 통해 데이터를 구조화하고 현장 운영에 적용한다. 230개 이상 사이트에서 기술 적용 경험을 쌓았으며, 발전소 예지보전 사례로 비계획 다운타임을 30% 줄이고 AI 운영 공수를 70% 절감했다.", "entities": ["원프레딕트", "데이터스루(DATATHRU)", "사이클론(cyclone)", "pdx", "테크플럭스(TECHFLUX)"], "keywords": ["multimodal", "ai-industry"], "is_curation": false, "origin_candidates": [], "relevance_reason": "제조 산업 AI 플랫폼과 데이터 자산화 기법, 구체적 성과 수치가 중심", "relevance": "high", "needs_original_reason": "기사 자체에 수치와 주장이 포함되어 있고, 원본 링크가 없으며 공식 발표가 아님에도 확인 가능한 별도 원본이 명시되지 않음", "needs_original": false}`
   - Q1 pass: summary와 claims에 포함된 플랫폼 구성(데이터스루, 사이클론, pdx), 다운타임 30% 및 공수 70% 절감 등의 수치와 주장이 모두 quotes 본문 인용 문장과 일치함
   - Q2 pass: 원프레딕트의 제조 데이터 자산화 비전과 플랫폼 구성, 실제 현장 적용 수치 성과 등 기사의 핵심 내용을 정확히 담음
   - Q3 pass: 외부 원본 링크가 전혀 없고 기사 자체에서 취재 내용과 수치를 기술하고 있어 needs_original=false 판정이 적절함

### 반복 기록

| 시각 | 모델 | 프롬프트 | 결과 | 비용 | 메모(바꾼 것) |
|---|---|---|---|---|---|
| 2026-10-08T10:56:52+09:00 | generate | `4a88561d8bd4` | 코드 0/17, Q1 0/0, Q2 0/0, Q3 0/0, 미달 (부분 실행) | $0.0644 |  |
| 2026-10-08T11:11:05+09:00 | generate | `4a88561d8bd4` | 코드 14/17, Q1 14/14, Q2 14/14, Q3 13/14, 미달 (부분 실행) | $0.0301 |  |
| 2026-10-08T11:32:13+09:00 | generate | `2691c9a33fbc` | 코드 14/17, Q1 14/14, Q2 14/14, Q3 14/14, 미달 (부분 실행) | $0.0852 | 반복1: quotes 3~6개·200자 문구 |
| 2026-10-08T11:43:16+09:00 | generate | `2691c9a33fbc` | 코드 16/17, Q1 16/16, Q2 16/16, Q3 16/16, 미달 (부분 실행) | $0.0787 | 반복2: max_tokens 1400→2000 |
| 2026-10-08T12:02:30+09:00 | generate | `e66573de84fa` | 코드 16/17, Q1 16/16, Q2 16/16, Q3 15/16, 미달 (부분 실행) | $0.0756 | 반복3: 긴 문장 자르기 예시 |
| 2026-10-08T12:03:44+09:00 | generate | `2691c9a33fbc` | 코드 16/17, Q1 16/16, Q2 16/16, Q3 16/16, 미달 (부분 실행) | $0.0000 | 최종: 반복2 프롬프트(반복3 되돌림) |
| 2026-10-08T15:20:08+09:00 | generate | `2691c9a33fbc` | 코드 20/21, Q1 20/20, Q2 20/20, Q3 19/20, 미달 | $0.0914 | 맥: 설계 결정 Q1·Q6 반영 + 실제 한 주 픽스처 4건 추가(설계 변경 재실행, 개선 횟수 아님) |
