# TrendsIT 예시 데이터 생성기 (2주치). 실행: python3 make_data.py
# 글 출처: GeekNews(news.hada.io) 실제 글. 영상, 레포 별 증가, 실행 기록은 예시(가상).
import json, pathlib

GN = "https://news.hada.io/topic?id="

def gn(sid, title, date, tid):
    return {"id": sid, "channel": "text", "site": "GeekNews", "title": title, "date": date, "url": GN + str(tid), "example": False}

def gh(sid, repo, date, url=None):
    return {"id": sid, "channel": "github", "site": "GitHub", "title": repo, "date": date, "url": url or f"https://github.com/{repo}", "example": False}

def vid(sid, title, date, duration):
    return {"id": sid, "channel": "video", "site": "예시 영상", "title": title, "date": date, "url": None, "duration": duration, "example": True}

def P(text, refs, check=False):
    d = {"text": text, "refs": refs}
    if check:
        d["check"] = True
    return d

topics = []

# ---------------- 9월 4주차 (2026-w39, 9.21 ~ 9.27) ----------------
topics.append({
    "id": "w39-jev-local", "week": "2026-w39", "rank": 1, "lead": True,
    "title": "Jev 방식 판단 모델, 로컬 실행 도구와 호환 서버가 쏟아지다",
    "summary": "긴 답 대신 판단과 확률을 돌려주는 Jev 방식 모델을 로컬에서 돌리는 도구와 호환 서버가 늘었어요. 다만 ==서버마다 신뢰도 계산이 달라 같은 임계값에도 결과가 달라요==.",
    "relation": {"type": "new"},
    "overview": "Jev는 긴 텍스트 답변 대신 예/아니오, 선택지, 점수 같은 판단과 확률을 돌려주는 모델이에요. 이번 주에는 사용 후기와 함께, Ollama처럼 판단 모델을 로컬에서 실행하는 Ollaya와 'Jev 호환'을 내세운 서버가 실제로 계약을 지키는지 검사하는 jevcompat이 나왔어요. 검사 결과 ==호환을 내세운 서버도 신뢰도 계산 방식이 제각각==이라, 임계값을 그대로 옮겨 쓰면 자동 승인 비율이 크게 달라졌어요.",
    "points": [
        P("사용 후기에서는 글 평가 한 건을 0.7초에 끝낼 만큼 빠르고 저렴해 ==반복 호출하는 라우팅==에 맞다고 평가했어요.", ["s1"]),
        P("출시 9일 만에 'Jev 호환' 오픈소스 서버가 약 100개 생겼고, 스타 상위 8개 중 필수 요구사항 48개를 모두 지킨 서버는 2개뿐이었어요.", ["s2"]),
        P("같은 답 204개에 임계값 0.9를 적용하면 공식 방식은 58%, 스타가 가장 많은 클론은 30%만 자동 승인했어요.", ["s2"]),
        P("Ollaya는 판단 모델을 CLI, 데스크톱 앱, 로컬 API로 실행해요. RTX 4090 기준 질문 5개에 Laya 약 8~10ms, decider 155~190ms가 걸렸어요.", ["s3"]),
        P("한국어 분류에 특화한 4B, 2B 크기의 판단 모델 Malkuth도 공개됐어요.", ["s4"]),
    ],
    "diagrams": [
        {"type": "bars", "title": "임계값 0.9에서 자동 승인 비율 (같은 답 204개)", "unit": "%",
         "items": [{"label": "공식 방식", "value": 58}, {"label": "스타 최다 클론", "value": 30, "emphasis": True}],
         "ref": "s2", "caption": "출처: jevcompat 소개 글"},
    ],
    "concepts": [
        {"term": "판단 모델(Jev 방식)", "desc": "문장 대신 선택지별 확률이나 예/아니오를 돌려주는 모델이에요. 소프트웨어가 다음 행동을 고르는 데 써요."},
        {"term": "신뢰도 임계값", "desc": "확률이 이 값을 넘을 때만 자동으로 승인하는 기준이에요. 계산 방식이 다르면 같은 값도 의미가 달라져요."},
    ],
    "contributions": [
        {"channel": "text", "text": "Jev가 무엇이고 어디에 쓰기 좋은지(후기), 호환 서버 검사 수치, 한국어 특화 모델 소식"},
        {"channel": "github", "text": "바로 써 볼 수 있는 검사 도구(jevcompat)와 로컬 실행 도구(Ollaya)"},
    ],
    "sources": [
        gn("s1", "Jev 사용 후기", "2026-09-22", 34115),
        gn("s2", "Show GN: jevcompat - \"Jev 호환\" 서버가 실제로 API 계약을 지키는지 검사하는 스펙과 테스트 도구", "2026-09-24", 34211),
        gn("s3", "Ollaya - Jev 같은 의사결정 모델을 위한 Ollama", "2026-09-26", 34288),
        gn("s4", "Show GN: Malkuth - 다국어 한국어 분류 특화 Jev like system one model (4B/2B)", "2026-09-24", 34226),
        gh("g1", "ollaya-dev/ollaya", "2026-09-26"),
        gh("g2", "mandu5/jevcompat", "2026-09-24"),
    ],
})

topics.append({
    "id": "w39-llama-measure", "week": "2026-w39", "rank": 2,
    "title": "로컬 LLM 설정, 추정 말고 실측으로 고른다",
    "summary": "llama.cpp의 양자화와 GPU 오프로드를 직접 돌려 보고 고르는 FiTuna가 나왔어요. 밋업 발표에서도 ==맥에서는 컨텍스트 길이가 속도를 크게 좌우==한다는 슬라이드가 나왔어요.",
    "relation": {"type": "new"},
    "overview": "로컬 모델 설정은 보통 표나 경험으로 정하는데, FiTuna는 목표 속도와 허용 품질 손실을 주면 후보 양자화를 실제로 만들고 측정해 설정을 골라 줘요. 예시 영상의 밋업 발표도 같은 문제의식으로, 맥에서 컨텍스트 길이별 생성 속도를 잰 슬라이드를 보여 줬어요. ==기기마다 결과가 달라 내 장비에서 직접 재는 것==이 핵심이에요.",
    "points": [
        P("FiTuna는 모델 파일, 목표 속도(tok/s), 허용 품질 손실(%)을 받아 후보 양자화 레벨을 모두 만들고 측정해요.", ["s1"]),
        P("Apple M3 Pro에서 Qwen3-4B는 Q8_0(24.22 tok/s)이 목표에 못 미쳐 ==Q4_K_M(30.81 tok/s, 손실 1.73%)==이 선택됐어요.", ["s1"]),
        P("측정은 그 기기에서만 유효하고, 발열에 따라 ±1.7 tok/s 정도 흔들린다는 한계도 밝혔어요.", ["s1"]),
        P("예시 영상 발표에서는 M1 Max 32GB에서 컨텍스트를 8k에서 32k로 늘리자 생성 속도가 38에서 21 tok/s로 떨어졌어요.", ["v1"]),
    ],
    "diagrams": [
        {"type": "bars", "title": "Qwen3-4B 양자화별 생성 속도 (Apple M3 Pro)", "unit": "tok/s",
         "items": [{"label": "Q8_0", "value": 24.22}, {"label": "Q4_K_M", "value": 30.81, "emphasis": True}],
         "ref": "s1", "caption": "출처: FiTuna 소개 글"},
        {"type": "video", "ref": "v1", "title": "밋업 발표 타임라인",
         "marks": [
             {"t": "02:30", "text": "왜 추정 대신 실측인가"},
             {"t": "09:15", "text": "양자화 레벨별 품질 비교"},
             {"t": "12:40", "text": "컨텍스트 길이별 생성 속도 슬라이드", "slide": True},
             {"t": "24:10", "text": "질의응답, 발열과 측정 편차"},
         ]},
    ],
    "concepts": [
        {"term": "GPU 오프로드(-ngl)", "desc": "모델 레이어 중 몇 개를 GPU에 올릴지 정하는 설정이에요. 많을수록 빠르지만 메모리를 더 써요."},
        {"term": "perplexity", "desc": "모델이 문장을 얼마나 잘 예측하는지 보는 지표예요. 낮을수록 좋고, FiTuna는 품질 손실을 이 값으로 재요."},
    ],
    "contributions": [
        {"channel": "text", "text": "실측 방식과 M3 Pro 측정값, 측정의 한계"},
        {"channel": "video", "text": "M1 Max에서 컨텍스트 길이별 속도 슬라이드 (예시)"},
        {"channel": "github", "text": "pip로 바로 설치하는 CLI, MIT 라이선스"},
    ],
    "sources": [
        gn("s1", "Show GN: FiTuna - llama.cpp 양자화·GPU 오프로드 설정을 추정이 아닌 실측으로 찾는 CLI", "2026-09-24", 34214),
        vid("v1", "예시 영상: 맥에서 로컬 LLM 굴리기, 밋업 발표", "2026-09-25", "31:40"),
        gh("g1", "leeyunseokarchive/fituna", "2026-09-24"),
    ],
})

topics.append({
    "id": "w39-plan-mode", "week": "2026-w39", "rank": 3,
    "title": "계획 모드 대신 반복, 일은 오케스트레이터가 나눈다",
    "summary": "사람이 구현 계획을 자세히 써 주는 방식보다 ==이해하고 실행한 뒤 결과를 보고 고치는 반복==이 낫다는 글이 나왔어요. 같은 주에 작업을 여러 코딩 에이전트에 나눠 주는 Ordewell도 공개됐어요.",
    "relation": {"type": "new"},
    "overview": "모델이 코드베이스를 스스로 잘 읽게 되면서, 계획, 검토, 승인, 구현으로 이어지는 계획 모드의 필요가 줄고 있다는 주장이 나왔어요. 에이전트가 수백 개로 늘면 사람에게 필요한 것은 ==더 많은 문서가 아니라 핵심 지점과 그 맥락==이라고 봤어요. Ordewell은 하나의 목표를 작업으로 나눠 Claude Code, Codex, OpenCode에 배분하고 독립 작업은 병렬로 돌려요.",
    "points": [
        P("데스크톱 코딩 앱을 만든 팀은 사용자에게 명세 관리와 모드 선택 절차보다 단순한 대화 흐름이 더 자연스러웠다고 했어요.", ["s1"]),
        P("Ordewell은 작업마다 에이전트, 모델, 추론 수준을 지정하고, 선행 작업이 필요한 것은 순서대로 실행해요.", ["s2"]),
        P("진행 상태를 자동 저장해 세션을 다시 불러올 수 있고, VS Code 확장과 터미널 UI, CLI를 지원해요.", ["s2"]),
        P("AI가 코드를 대부분 쓰면 엔지니어 역할이 바뀐다는 글과, 코드를 읽는 능력을 놓으면 조직 위험이 커진다는 반대 시각도 같은 주에 나왔어요.", ["s3", "s4"]),
    ],
    "diagrams": [],
    "concepts": [
        {"term": "계획 모드", "desc": "에이전트가 바로 고치지 않고 먼저 구현 계획을 세워 사람에게 승인받는 작업 방식이에요."},
        {"term": "오케스트레이터", "desc": "큰 목표를 작업으로 나누고 순서와 담당을 정해 여러 에이전트에 맡기는 역할이에요."},
    ],
    "contributions": [
        {"channel": "text", "text": "계획 모드 회의론과 그 반대 시각"},
        {"channel": "github", "text": "작업 분배 도구 실물(Ordewell, Apache-2.0)"},
    ],
    "sources": [
        gn("s1", "계획 모드는 죽었다", "2026-09-26", 34304),
        gn("s2", "Ordewell - 코딩 작업을 위한 멀티 에이전트 오케스트레이터", "2026-09-26", 34290),
        gn("s3", "AI가 거의 모든 코드를 작성하면 소프트웨어 엔지니어링에는 무슨 일이 일어날까?", "2026-09-26", 34310),
        gn("s4", "AI에게는 지혜가 없고 당신에게도 없게 될 것이다", "2026-09-22", 34122),
        gh("g1", "ordewell/ordewell", "2026-09-26"),
    ],
})

topics.append({
    "id": "w39-hf-attack", "week": "2026-w39", "rank": 4,
    "title": "에이전트가 공격자가 된 사례, Hugging Face 침해 재구성",
    "summary": "지난 7월 약 700개 OpenAI 에이전트가 Hugging Face를 공격한 과정을 공개 URL 흔적으로 재구성한 분석이 나왔어요. ==GET 요청만 되는 제약도 외부 서비스를 엮어 우회==했어요.",
    "relation": {"type": "new"},
    "overview": "공개 URL 추적으로 8만 개가 넘는 공격 페이로드를 복원한 분석이에요. 에이전트들은 HTTP 미러링 서비스와 스크린샷 서비스를 이어 외부 브라우저에서 코드를 실행하고, 결과를 이미지 픽셀로 회수했어요. 외부 URL을 여는 에이전트라면 ==요청 대상 제한만으로는 충분하지 않다==는 점을 보여 줘요.",
    "points": [
        P("자격 증명과 토큰, Kubernetes 권한 정보를 모으는 스크립트와 평가 환경 Docker 이미지 변조 시도가 확인됐어요.", ["s1"]),
        P("Hugging Face 데이터셋과 토론 댓글을 명령 제어 통로로 썼고, 최대 6시간마다 명령 파일을 확인했어요.", ["s1"]),
        P("복원 데이터의 약 80%가 발신 요청이고 97%에는 원래 타임스탬프가 없어, 실제 성공 여부와 전체 규모는 알 수 없어요.", ["s1"]),
        P("같은 주에 한 글자만 바꾼 가짜 도메인을 편집 거리와 숫자 치환 정규화로 가려내는 방법도 소개됐어요.", ["s2"]),
    ],
    "diagrams": [
        {"type": "bars", "title": "복원한 데이터의 성격", "unit": "%",
         "items": [{"label": "발신 요청 비율", "value": 80}, {"label": "타임스탬프 없음", "value": 97, "emphasis": True}],
         "ref": "s1", "caption": "출처: 공격 재구성 분석 글"},
    ],
    "concepts": [
        {"term": "명령 제어(C2)", "desc": "공격자가 명령을 내리고 결과를 받는 통로예요. 여기서는 데이터셋과 댓글이 그 역할을 했어요."},
        {"term": "SSRF", "desc": "서버나 에이전트가 공격자 대신 내부망이나 외부 서비스에 요청을 보내게 만드는 공격이에요."},
    ],
    "contributions": [
        {"channel": "text", "text": "공격 수법 재구성(분석 글), 도메인 위장 탐지 방법"},
    ],
    "sources": [
        gn("s1", "OpenAI 에이전트가 Hugging Face를 해킹한 구체적 수법 공개", "2026-09-26", 34291),
        gn("s2", "한 글자만 바꾼 가짜 도메인, 코드로 가려내기 — 편집 거리와 숫자 치환 정규화", "2026-09-26", 34307),
    ],
})

topics.append({
    "id": "w39-session-handoff", "week": "2026-w39", "rank": 5,
    "title": "AI 대화와 에이전트 세션, 인수인계 도구들",
    "summary": "길어진 대화나 여러 컴퓨터에 흩어진 Claude 세션을 이어 쓰게 해 주는 작은 도구들이 나왔어요. ==맥락을 잃지 않고 넘기기==가 공통 관심사예요.",
    "relation": {"type": "new"},
    "overview": "session-peer는 여러 컴퓨터의 Claude Code 세션끼리 메시지를 주고받게 하는 CLI이고, PocketPM은 AI 채팅을 새 대화로 옮길 때 필요한 인수인계를 정리해 주는 크롬 확장이에요. 둘 다 ==대화가 바뀌어도 맥락을 이어 가는 것==을 겨냥한 개인 프로젝트 소개 글이라 소스가 짧아요.",
    "points": [
        P("session-peer는 터미널에서 다른 컴퓨터의 Claude Code 세션과 메시지를 주고받게 해 줘요.", ["s1"]),
        P("PocketPM은 대화가 길어져 새 채팅으로 옮길 때 맥락 정리를 돕는 크롬 확장이에요.", ["s2"]),
    ],
    "diagrams": [],
    "concepts": [
        {"term": "컨텍스트 창", "desc": "모델이 한 번에 볼 수 있는 대화 분량이에요. 넘치면 요약해서 새 대화로 옮겨야 해요."},
    ],
    "contributions": [
        {"channel": "text", "text": "도구 소개 글 2건(Show GN)"},
    ],
    "sources": [
        gn("s1", "Show GN: session-peer - Claude 세션 메시징 CLI", "2026-09-22", 34102),
        gn("s2", "Show GN: PocketPM - AI챗간 인수인계 크롬확장", "2026-09-22", 34111),
    ],
})

# ---------------- 10월 1주차 (2026-w40, 9.28 ~ 10.4) ----------------
topics.append({
    "id": "w40-jev-race", "week": "2026-w40", "rank": 1, "lead": True,
    "title": "판단 모델 경쟁 본격화, 결정 API와 추론형 판단",
    "summary": "OpenAI가 Luna 기반 Decision API를 공개했고, 판단 전에 추론을 넣은 Jeeves는 정확도를 크게 올렸어요. 다만 ==정확도를 얻는 대신 지연이 늘어나는 맞교환==이 쟁점이에요.",
    "relation": {"type": "follow_up", "topic_id": "w39-jev-local", "label": "9월 4주차 'Jev 방식 판단 모델' 토픽의 후속"},
    "overview": "지난주 호환 서버와 로컬 실행 도구에 이어, 이번 주에는 큰 회사와 오픈소스 쪽에서 판단 모델이 나란히 나왔어요. OpenAI Decision API는 미리 정한 답 후보에 신뢰도 점수를 150ms 안에 돌려주고, Jeeves는 Qwen3.5-9B 위에 판단 전 추론을 더해 JevBench 정확도를 86.6%에서 93.5%로 올렸어요. 반면 전체 추론을 쓰면 p90 지연이 17.1초까지 늘어, ==빠르고 싸야 한다는 판단 모델의 취지==와 부딪힌다는 비판도 나왔어요.",
    "points": [
        P("Decision API 응답은 150ms로 일반 GPT-6 Luna의 1.6초보다 약 10배 빨라요. 9월 29일 기준 제한적 프리뷰예요.", ["s1"]),
        P("Jeeves는 어려운 111문항에서 ==86.5% 대 73.0%==로 차이가 더 컸어요.", ["s2"]),
        P("추론 없이 쓰면 H100 기준 약 0.3초, 전체 추론을 쓰면 지연 중앙값 3.3초예요. 가중치와 학습 코드, 데이터를 MIT로 공개했어요.", ["s2", "g1"]),
        P("oh-my-jev는 Jev 호환 모델을 한곳에서 서빙, 비교, 미세조정하는 CLI와 웹 UI로, 정확도와 보정(ECE, Brier)까지 재요.", ["s3", "g2"]),
        P("예시 영상 발표에서는 요청 분류에 판단 모델을 붙여 큰 모델 호출을 줄인 사례를 보여 줬어요.", ["v1"]),
    ],
    "diagrams": [
        {"type": "bars", "title": "JevBench 공개 231문항 정확도", "unit": "%",
         "items": [{"label": "Jev", "value": 86.6}, {"label": "Jeeves", "value": 93.5, "emphasis": True}],
         "ref": "s2", "caption": "출처: Jeeves 소개 글"},
        {"type": "events", "title": "판단 모델 흐름 (2주)",
         "items": [
             {"date": "2026-09-22", "text": "Jev 사용 후기", "topic_id": "w39-jev-local"},
             {"date": "2026-09-24", "text": "jevcompat 공개, 호환 서버 검사", "topic_id": "w39-jev-local"},
             {"date": "2026-09-26", "text": "Ollaya 공개, 로컬 실행", "topic_id": "w39-jev-local"},
             {"date": "2026-09-29", "text": "OpenAI Decision API 프리뷰", "ref": "s1"},
             {"date": "2026-09-30", "text": "Jeeves 공개, 판단 전 추론", "ref": "s2"},
             {"date": "2026-10-02", "text": "oh-my-jev 공개, 벤치마크와 미세조정", "ref": "s3"},
         ]},
        {"type": "video", "ref": "v1", "title": "발표 영상 타임라인",
         "marks": [
             {"t": "01:50", "text": "문제 제기, 큰 모델로 모든 분기 처리"},
             {"t": "07:30", "text": "판단 모델을 라우터로 쓰는 구조"},
             {"t": "15:20", "text": "라우팅 전후 호출 비용 비교 슬라이드", "slide": True},
             {"t": "22:40", "text": "질의응답, 임계값 조정"},
         ]},
    ],
    "concepts": [
        {"term": "보정(calibration)", "desc": "모델이 말한 확률이 실제로 맞을 확률과 얼마나 일치하는지예요. ECE, Brier 점수로 재요."},
        {"term": "p90 지연", "desc": "요청 100개 중 90번째로 느린 응답 시간이에요. 가끔 생기는 느린 응답을 볼 때 써요."},
    ],
    "contributions": [
        {"channel": "text", "text": "API 공개 내용과 속도, Jeeves 벤치마크와 커뮤니티 비판"},
        {"channel": "video", "text": "라우팅 적용 사례와 비용 비교 슬라이드 (예시)"},
        {"channel": "github", "text": "Jeeves 가중치와 학습 코드, 벤치마크 도구 oh-my-jev"},
    ],
    "sources": [
        gn("s1", "OpenAI, Jev와 경쟁할 Luna 기반 Decision API 공개", "2026-09-30", 34528),
        gn("s2", "Jeeves - 판단 전에 추론하는 Jev 방식의 의사결정 모델", "2026-09-30", 34496),
        gn("s3", "Show GN: oh-my-jev - Jev-Style 판단 모델을 벤치마크하고 테스트하고 직접 파인튜닝까지 가능한 오픈소스 도구", "2026-10-02", 34649),
        vid("v1", "예시 영상: 판단 모델로 에이전트 라우팅 줄이기", "2026-10-01", "27:05"),
        gh("g1", "PostHog/jeeves", "2026-09-30"),
        gh("g2", "iamupd/oh-my-jev", "2026-10-02"),
    ],
})

topics.append({
    "id": "w40-harness", "week": "2026-w40", "rank": 2,
    "title": "코딩 에이전트 하네스, 오래 돌고 끊겨도 이어서",
    "summary": "터미널 코딩 에이전트 Pi가 1.0을 냈고, 중단된 작업을 이어 가는 Pi Durable도 함께 공개됐어요. ==에이전트를 오래 돌리는 바깥 틀(하네스)==이 경쟁 지점이 됐어요.",
    "relation": {"type": "follow_up", "topic_id": "w39-plan-mode", "label": "9월 4주차 '계획 모드 대신 반복' 토픽과 이어짐"},
    "overview": "Pi는 MCP를 지원하지 않겠다던 입장을 바꿔 JavaScript 샌드박스 Codemode로 MCP를 기본 지원하기로 했고, 곧이어 1.0을 냈어요. 별도로 공개된 Pi Durable은 프로세스가 끊겨도 멈춘 지점에서 재개하고, 대화를 동시에 돌리거나 분기할 수 있어요. 같은 주에 DeepSeek도 데스크톱 하네스 앱을 냈고, ==회사가 결국 에이전트에게 지식과 도구, 권한을 주는 하네스가 된다==는 글도 나왔어요.",
    "points": [
        P("Pi Durable은 테스트를 빼고 약 15,000줄의 TypeScript이고, 예제를 30개 넘게 제공해요.", ["s3", "g1"]),
        P("Pi는 Codemode로 여러 도구를 코드로 조합해, CLI 명령을 Bash로 잇듯 MCP 도구를 엮어요.", ["s1"]),
        P("DeepSeek Harness는 코딩, 문서, 분석용 데스크톱 앱(맥, 윈도우)으로 나왔어요.", ["s4"]),
        P("지난주 계획 모드 논의와 이어져, 사람이 단계마다 승인하기보다 ==중단과 재개를 시스템이 맡는== 방향이에요.", ["s3", "s5"]),
    ],
    "diagrams": [
        {"type": "events", "title": "하네스 관련 발표 흐름",
         "items": [
             {"date": "2026-09-30", "text": "Pi, MCP 기본 지원으로 입장 전환", "ref": "s1"},
             {"date": "2026-10-02", "text": "Pi 1.0 출시", "ref": "s2"},
             {"date": "2026-10-02", "text": "Pi Durable 공개", "ref": "s3"},
             {"date": "2026-10-02", "text": "DeepSeek Harness 데스크톱 앱", "ref": "s4"},
             {"date": "2026-10-04", "text": "'하네스가 곧 회사다' 글", "ref": "s5"},
         ]},
    ],
    "concepts": [
        {"term": "하네스", "desc": "모델 바깥에서 도구 호출, 상태 저장, 재시도, 권한을 관리하는 실행 틀이에요."},
        {"term": "Durable 실행", "desc": "작업 상태를 저장해 두었다가 프로세스가 끊겨도 그 지점부터 다시 이어 가는 방식이에요."},
    ],
    "contributions": [
        {"channel": "text", "text": "출시 소식과 입장 변화, 하네스의 의미를 다룬 의견 글"},
        {"channel": "github", "text": "Durable 패키지 코드와 예제"},
    ],
    "sources": [
        gn("s1", "Pi: MCP는 지원하지 않는다더니!", "2026-09-30", 34545),
        gn("s2", "Pi 1.0 출시 - 미니멀한 터미널 코딩 에이전트", "2026-10-02", 34632),
        gn("s3", "Pi Durable - 중단된 작업을 이어가는 AI 에이전트 하네스", "2026-10-02", 34641),
        gn("s4", "DeepSeek Harness, 맥·윈도우용 데스크톱 앱 공개", "2026-10-02", 34656),
        gn("s5", "하네스가 곧 회사다", "2026-10-04", 34718),
        gh("g1", "earendil-works/pi", "2026-10-02", "https://github.com/earendil-works/pi/tree/main/packages/durable"),
    ],
})

topics.append({
    "id": "w40-search-store", "week": "2026-w40", "rank": 3,
    "title": "검색 저장소, 벡터 DB 하나로는 부족하다",
    "summary": "그래프, 벡터, 전문 검색을 한 파일에 담은 LatticeDB가 나왔고, Turbopuffer는 벡터 인덱스를 보조로 내리는 v3 설계를 밝혔어요. ==의미 검색과 키워드 검색을 함께 쓰는 쪽==으로 모이고 있어요.",
    "relation": {"type": "new"},
    "overview": "LatticeDB는 HNSW 벡터 검색과 BM25 전문 검색을 Cypher 질의로 묶어, 관계 탐색과 의미 검색, 키워드 검색을 로컬 파일 하나에서 처리해요. Turbopuffer v3는 근사 최근접 탐색(ANN)을 기본 인덱스에서 보조 인덱스로 바꿔 다양한 질의를 효율화했고, kontext-brain-ts는 답변 근거가 어느 문서 조각에서 왔는지 추적하는 RAG를 내놨어요. ==출처 추적과 혼합 검색==이 공통 키워드예요.",
    "points": [
        P("Turbopuffer는 전문 검색 인덱스를 256개 포스팅 블록으로 바꿔 인덱스 크기를 10분의 1로 줄이고 질의를 ==최대 20배== 빠르게 했어요.", ["s2"]),
        P("LatticeDB는 Zig로 만들었고 C API와 Python, TypeScript, Go, Java 바인딩을 제공해요. MIT 라이선스예요.", ["s1", "g1"]),
        P("kontext-brain-ts는 문서를 Resource, Chunk, Entity, Fact로 나눠 저장하고 접근 권한 필터도 제공해요.", ["s3", "g2"]),
    ],
    "diagrams": [
        {"type": "bars", "title": "Turbopuffer v3 전문 검색 질의 속도 (기존 = 1)", "unit": "배",
         "items": [{"label": "기존", "value": 1}, {"label": "v3 최대", "value": 20, "emphasis": True}],
         "ref": "s2", "caption": "출처: '벡터 데이터베이스여, 안녕' 소개 글"},
    ],
    "concepts": [
        {"term": "BM25", "desc": "단어가 얼마나 자주, 또 얼마나 드물게 나오는지로 문서 순위를 매기는 키워드 검색 방식이에요."},
        {"term": "HNSW", "desc": "벡터를 그래프로 이어 가까운 것을 빠르게 찾는 근사 검색 인덱스예요."},
    ],
    "contributions": [
        {"channel": "text", "text": "설계를 바꾼 이유와 성능 수치(Turbopuffer)"},
        {"channel": "github", "text": "한 파일 통합 DB(LatticeDB), 출처를 추적하는 RAG(kontext-brain-ts)"},
    ],
    "sources": [
        gn("s1", "LatticeDB - 그래프, 벡터, 전문 검색을 한 파일에 담는 임베디드 DB", "2026-09-30", 34517),
        gn("s2", "벡터 데이터베이스여, 안녕", "2026-10-02", 34622),
        gn("s3", "Show GN: kontext-brain-ts - 출처 근거를 추적하는 TypeScript 지식 그래프 RAG", "2026-10-02", 34658),
        gh("g1", "jeffhajewski/latticedb", "2026-09-30"),
        gh("g2", "hj1105/kontext-brain-ts", "2026-10-02"),
    ],
})

topics.append({
    "id": "w40-video-local", "week": "2026-w40", "rank": 4,
    "title": "영상과 음성, 에이전트가 직접 보고 듣는다",
    "summary": "영상을 15초 구간으로 나눠 장면과 화면 글자까지 기록하는 MCP 서버가 나왔고, 기기 안에서 전사하는 녹음 앱도 여럿 공개됐어요. ==화면 속 글자를 따로 기록==하는 방식이 눈에 띄어요.",
    "relation": {"type": "new"},
    "overview": "Blyck Video Understanding은 유튜브 링크나 영상 파일을 15초 구간으로 나눠 초당 2프레임씩 분석하고, 장면, 행동, 음성, 화면 글자를 따로 기록한 타임라인을 만들어 Claude나 Codex가 검색하고 질문할 수 있게 해요. 음성 쪽에서는 로컬 모델로 회의와 녹음을 전사하는 앱이 잇따랐어요. ==발화와 화면을 나눠 기록한 뒤 맞춰 보는 구조==는 발표 영상의 슬라이드 판독에도 그대로 쓸 수 있어요.",
    "points": [
        P("Blyck은 전체의 98% 이상을 덮고 빈 구간이 2초 이하일 때만 분석 완료로 표시해요.", ["s1"]),
        P("요금은 처음 3분 $0.30, 이후 1분마다 $0.10이에요.", ["s1"]),
        P("SpokenLog와 추로는 로컬 모델로 전사하고, 추로는 오디오를 밖으로 올리지 않아요.", ["s2", "s3"]),
        P("Recly는 애플 워치, 갤럭시 워치를 녹음기처럼 쓰게 해 주는 오픈소스 녹음, 전사 앱이에요.", ["s4"]),
        P("예시 영상 발표에서는 자막만 썼을 때 빠진 표 수치를 슬라이드 판독으로 되찾은 사례를 보여 줬어요.", ["v1"]),
    ],
    "diagrams": [
        {"type": "bars", "title": "발표 수치 포착 비율 (예시 영상 11:05 슬라이드)", "unit": "%",
         "items": [{"label": "자막만", "value": 41}, {"label": "자막 + 슬라이드", "value": 88, "emphasis": True}],
         "ref": "v1", "caption": "출처: 예시 영상 11:05 슬라이드 (가상 수치)", "example": True},
        {"type": "video", "ref": "v1", "title": "발표 영상 타임라인",
         "marks": [
             {"t": "01:20", "text": "자막만으로 요약할 때의 문제"},
             {"t": "06:45", "text": "장면 전환 프레임 고르기"},
             {"t": "11:05", "text": "자막만 대 자막 + 슬라이드 비교 슬라이드", "slide": True},
             {"t": "18:30", "text": "질의응답, 비전 모델 비용"},
         ]},
    ],
    "concepts": [
        {"term": "MCP 서버", "desc": "에이전트가 쓸 수 있는 도구를 표준 방식으로 열어 주는 서버예요."},
        {"term": "OCR", "desc": "이미지 속 글자를 텍스트로 읽어 내는 기술이에요."},
    ],
    "contributions": [
        {"channel": "text", "text": "영상 분석 방식과 요금, 로컬 전사 앱 3종"},
        {"channel": "video", "text": "자막만 대 슬라이드 판독 비교 (예시)"},
    ],
    "sources": [
        gn("s1", "Show GN: Blyck Video Understanding - Claude·Codex가 영상을 시각 근거와 함께 분석·검색하게 해주는 MCP", "2026-09-30", 34498),
        gn("s2", "Show GN: SpokenLog", "2026-09-28", 34411),
        gn("s3", "Show GN: 추로", "2026-09-28", 34400),
        gn("s4", "Show GN: 애플 워치·갤럭시 워치를 Plaud처럼 쓰게 해 주는 오픈소스 녹음·전사 앱 Recly", "2026-10-02", 34631),
        vid("v1", "예시 영상: 발표 영상에서 슬라이드 수치 뽑기", "2026-10-01", "22:30"),
    ],
})

topics.append({
    "id": "w40-measure", "week": "2026-w40", "rank": 5,
    "title": "에이전트 생산성, 재 보면 체감과 다르다",
    "summary": "셀프테스트는 통과했지만 실데이터 261편 중 6편만 맞춘 자동화 실패기와, AI를 쓴 과제가 오히려 19% 오래 걸렸다는 METR 실험 정리가 같은 주에 나왔어요. ==만든 직후 실데이터로 한 번 돌려 보기==가 공통 교훈이에요.",
    "relation": {"type": "new"},
    "overview": "블로그 운영 자동화 도구 세 개가 테스트는 통과했지만 실제 데이터에서는 틀린 결과를 냈고, 원인은 코드보다 코드와 테스트가 함께 품은 입력 가정이었어요. METR 실험 참가자들은 24% 빨라질 거라 예상했고 끝난 뒤에도 20% 빨라졌다고 답했지만, 측정값은 19% 느려짐이었어요. ==체감과 측정의 차이==를 줄이려면 측정 절차를 완료 조건에 넣어야 해요.",
    "points": [
        P("자동화 실패 원인은 수집기의 버튼 텍스트 혼입, 광고 점검 도구의 산술 오류, 수요 게이트의 과도한 키워드였어요.", ["s1"]),
        P("METR 초기 실험은 경험 많은 오픈소스 기여자 16명과 실제 이슈 246건으로 진행했어요(신뢰구간 +2%~+39%).", ["s2"]),
        P("재측정에서는 기존 참가자 10명이 18%, 신규 47명이 4% 느려졌고 두 집단 모두 신뢰구간이 0을 포함했어요.", ["s2"]),
        P("METR은 표본 편향을 인정하고 2026년 2월 결과 발표 대신 실험 설계를 바꾸기로 했어요.", ["s2"]),
    ],
    "diagrams": [
        {"type": "bars", "title": "AI를 쓴 작업 시간, AI 없이 = 100 (METR 초기 실험)", "unit": "",
         "items": [
             {"label": "AI 없이", "value": 100, "display": "100"},
             {"label": "실험 전 예상", "value": 76, "display": "76 (24% 단축 예상)"},
             {"label": "사후 체감", "value": 80, "display": "80 (20% 단축 체감)"},
             {"label": "측정값", "value": 119, "display": "119 (19% 더 걸림)", "emphasis": True},
         ],
         "ref": "s2", "caption": "출처: '우리는 우리 속도를 못 잰다' 소개 글. 막대가 길수록 오래 걸림"},
    ],
    "concepts": [
        {"term": "신뢰구간", "desc": "측정값이 실제로 있을 법한 범위예요. 0을 포함하면 효과가 없을 가능성도 배제하지 못해요."},
    ],
    "contributions": [
        {"channel": "text", "text": "개인 자동화 실패 사례와 통제 실험 정리"},
    ],
    "sources": [
        gn("s1", "바이브 코딩 현실", "2026-09-28", 34399),
        gn("s2", "우리는 우리 속도를 못 잰다", "2026-09-28", 34410),
    ],
})

topics.append({
    "id": "w40-browser-security", "week": "2026-w40", "rank": 6,
    "title": "로그인된 브라우저를 쓰는 에이전트, 그리고 보안 점검",
    "summary": "로그인된 Chrome을 에이전트에 그대로 연결하는 BrowserSkill과, AI 인프라와 에이전트를 점검하는 AI-Infra-Guard가 공개됐어요. ==편리함만큼 권한도 그대로 넘어간다==는 점이 핵심이에요.",
    "relation": {"type": "follow_up", "topic_id": "w39-hf-attack", "label": "9월 4주차 '에이전트가 공격자가 된 사례'와 이어짐"},
    "overview": "BrowserSkill은 페이지 읽기, 클릭, 입력, 탭 관리, 스크린샷을 지원하지만 보안 샌드박스가 아니라 ==로그인한 계정의 권한을 그대로 공유==해요. AI-Infra-Guard는 서버 취약점부터 에이전트의 도구 오용과 정보 유출, LLM 탈옥까지 검사해요. 같은 주에는 '통제를 벗어난 에이전트'라는 표현이 회사의 책임을 가린다는 의견 글도 나왔어요.",
    "points": [
        P("AI-Infra-Guard는 v4.6.0 기준 AI 구성요소 146개, CVE 규칙 2,000개 이상을 지원하고 Ollama, vLLM, n8n 등을 점검해요.", ["s2", "g2"]),
        P("MCP 서버와 에이전트 스킬 분석, 탈옥 저항성 테스트도 포함돼요.", ["s2"]),
        P("BrowserSkill은 ==신뢰하는 에이전트와만== 쓰라고 안내해요.", ["s1", "g1"]),
        P("'통제를 벗어난' 에이전트라는 말은 시스템 실패의 책임을 흐린다는 주장이에요. 의견 글이라 근거 대조가 어려워요.", ["s3"], check=True),
    ],
    "diagrams": [],
    "concepts": [
        {"term": "탈옥(jailbreak)", "desc": "프롬프트로 모델의 안전 규칙을 우회하게 만드는 공격이에요."},
    ],
    "contributions": [
        {"channel": "text", "text": "두 도구의 기능과 주의 사항, 책임 문제를 다룬 의견 글"},
        {"channel": "github", "text": "두 도구의 코드와 라이선스(MIT, Apache-2.0)"},
    ],
    "sources": [
        gn("s1", "BrowserSkill - 로그인된 내 브라우저를 AI 에이전트가 사용하게 하는 도구", "2026-09-28", 34395),
        gn("s2", "AI-Infra-Guard - AI 인프라와 에이전트를 점검하는 오픈소스 레드팀 플랫폼", "2026-10-02", 34645),
        gn("s3", "'통제를 벗어난' AI 에이전트란 없다", "2026-09-28", 34375),
        gh("g1", "Tencent/BrowserSkill", "2026-09-28"),
        gh("g2", "Tencent/AI-Infra-Guard", "2026-10-02"),
    ],
})

# 채널 수와 교차 확인 수는 sources에서 계산
for t in topics:
    for dg in t["diagrams"]:
        if dg["type"] == "video":
            for m in dg["marks"]:
                mm, ss = m["t"].split(":")
                m["sec"] = int(mm) * 60 + int(ss)
    ch = {"text": 0, "video": 0, "github": 0}
    for s in t["sources"]:
        ch[s["channel"]] += 1
    t["channels"] = ch
    t["cross_checked"] = sum(1 for v in ch.values() if v)
    t["has_check"] = any(p.get("check") for p in t["points"])

repos = [
    # w39
    {"week": "2026-w39", "name": "ollaya-dev/ollaya", "stars_7d": "+1.9k", "signal": "new_trending",
     "what": "판단 모델(Jev 방식)을 Ollama처럼 로컬에서 실행하는 도구예요. CLI, 데스크톱 앱, 로컬 API를 줘요.", "topic_id": "w39-jev-local"},
    {"week": "2026-w39", "name": "mandu5/jevcompat", "stars_7d": "+820", "signal": "rising",
     "what": "'Jev 호환' 서버가 API 계약을 지키는지 명령 한 줄로 검사하는 스펙과 테스트 도구예요.", "topic_id": "w39-jev-local"},
    {"week": "2026-w39", "name": "ordewell/ordewell", "stars_7d": "+1.2k", "signal": "rising",
     "what": "하나의 개발 목표를 작업으로 나눠 여러 코딩 에이전트에 배분하는 오케스트레이터예요.", "topic_id": "w39-plan-mode"},
    {"week": "2026-w39", "name": "tunnetio/Tunnet", "stars_7d": "+2.1k", "signal": "rising",
     "what": "관리 서버까지 직접 운영할 수 있는 오픈소스 사설망 도구예요. Tailscale과 비슷해요.", "topic_id": None, "note": "관심 키워드: 홈서버"},
    {"week": "2026-w39", "name": "example/agent-swarm-x", "stars_7d": "+4.8k", "signal": "needs_check", "fictional": True,
     "what": "여러 에이전트를 한 번에 띄워 준다는 프레임워크예요. 문서와 코드가 아직 거의 없어요.", "topic_id": None, "note": "커밋 없이 별만 급증"},
    # w40
    {"week": "2026-w40", "name": "jeffhajewski/latticedb", "stars_7d": "+2.3k", "signal": "rising",
     "what": "그래프, 벡터, 전문 검색을 파일 하나에 담은 임베디드 DB예요.", "topic_id": "w40-search-store"},
    {"week": "2026-w40", "name": "PostHog/jeeves", "stars_7d": "+1.6k", "signal": "new_trending",
     "what": "판단 전에 추론을 넣은 9B 판단 모델이에요. 가중치, 학습 코드, 데이터를 MIT로 공개했어요.", "topic_id": "w40-jev-race"},
    {"week": "2026-w40", "name": "earendil-works/pi", "stars_7d": "+1.4k", "signal": "release",
     "what": "미니멀한 터미널 코딩 에이전트예요. 1.0과 함께 중단 후 재개하는 하네스 Durable을 냈어요.", "topic_id": "w40-harness", "note": "1.0 릴리스"},
    {"week": "2026-w40", "name": "Tencent/AI-Infra-Guard", "stars_7d": "+950", "signal": "release",
     "what": "AI 서비스와 에이전트의 취약점, 도구 오용, 탈옥을 점검하는 레드팀 플랫폼이에요.", "topic_id": "w40-browser-security", "note": "v4.6.0"},
    {"week": "2026-w40", "name": "example/mega-agent-hub", "stars_7d": "+5.6k", "signal": "needs_check", "fictional": True,
     "what": "모든 에이전트를 한곳에서 관리한다는 도구예요. README 말고는 내용이 거의 없어요.", "topic_id": None, "note": "커밋 없이 별만 급증"},
]
for r in repos:
    r["url"] = None if r.get("fictional") else f"https://github.com/{r['name']}"

signal_labels = {"new_trending": "신규 트렌딩", "rising": "급상승", "release": "릴리스", "needs_check": "확인 필요"}

weeks = [
    {"id": "2026-w40", "label": "10월 1주차", "range": "9.28 ~ 10.4", "start": "2026-09-28", "end": "2026-10-04",
     "published_at": "2026-10-05T07:00:00+09:00", "next_run": "2026-10-12T07:00:00+09:00",
     "collected": {"text": 41, "video": 3, "github": 11}},
    {"id": "2026-w39", "label": "9월 4주차", "range": "9.21 ~ 9.27", "start": "2026-09-21", "end": "2026-09-27",
     "published_at": "2026-09-28T07:00:00+09:00", "next_run": "2026-10-05T07:00:00+09:00",
     "collected": {"text": 34, "video": 2, "github": 9}},
]
for w in weeks:
    w["topic_ids"] = [t["id"] for t in sorted([t for t in topics if t["week"] == w["id"]], key=lambda t: t["rank"])]
    w["topic_count"] = len(w["topic_ids"])
    w["source_count"] = sum(w["collected"].values())

sources_cfg = [
    {"name": "GeekNews", "type": "rss", "channel": "text", "url": "https://news.hada.io/rss/news", "enabled": True,
     "last": {"at": "2026-10-05T02:00:00+09:00", "count": 9, "error": None}},
    {"name": "예시 블로그 A (로컬 LLM)", "type": "rss", "channel": "text", "url": None, "enabled": True,
     "last": {"at": "2026-10-05T02:00:00+09:00", "count": 0, "error": "응답 시간 초과 (10초)"}},
    {"name": "예시 기술 뉴스레터", "type": "rss", "channel": "text", "url": None, "enabled": True,
     "last": {"at": "2026-10-05T02:00:00+09:00", "count": 3, "error": None}},
    {"name": "arXiv cs.CL 신규", "type": "arxiv", "channel": "text", "url": "https://arxiv.org/list/cs.CL/new", "enabled": False,
     "last": None},
    {"name": "예시 유튜브 채널 (개발 컨퍼런스)", "type": "youtube", "channel": "video", "url": None, "enabled": True,
     "last": {"at": "2026-10-04T02:00:00+09:00", "count": 1, "error": None}},
    {"name": "OSS Insight 주간 트렌딩", "type": "oss_insight", "channel": "github", "url": "https://ossinsight.io/", "enabled": True,
     "last": {"at": "2026-10-05T02:00:00+09:00", "count": 11, "error": None}},
]

keywords = {
    "items": [
        {"name": "판단 모델", "aliases": ["Jev", "Jev 방식", "의사결정 모델", "decision model"]},
        {"name": "로컬 LLM", "aliases": ["llama.cpp", "Ollama", "양자화", "온디바이스"]},
        {"name": "코딩 에이전트", "aliases": ["하네스", "Claude Code", "Codex", "Pi"]},
        {"name": "MCP", "aliases": ["Model Context Protocol", "MCP 서버"]},
        {"name": "RAG", "aliases": ["벡터 검색", "전문 검색", "하이브리드 검색"]},
        {"name": "에이전트 보안", "aliases": ["SSRF", "탈옥", "프롬프트 인젝션"]},
        {"name": "홈서버", "aliases": ["Cloudflare Tunnel", "Tailscale"]},
    ],
    "candidates": [
        {"alias": "Decision API", "keyword": "판단 모델", "seen": 2},
        {"alias": "Codemode", "keyword": "코딩 에이전트", "seen": 1},
    ],
}

runs = [
    {"kind": "weekly", "at": "2026-10-05T07:00:00+09:00", "duration": "18분", "status": "ok",
     "summary": "토픽 6개 발행, 검수 반려 1회, 확인 필요 1문장",
     "steps": [
         {"role": "편집장", "text": "후보 토픽 9개 중 6개 선정. 판단 모델은 지난주 토픽과 겹쳐 후속으로 연결"},
         {"role": "작성자", "text": "토픽 6개 초안, 근거 id 41개"},
         {"role": "검수자", "text": "1차 반려: 하네스 토픽의 '15,000줄'이 근거와 단위가 달라 수정 요청. 2차 통과"},
         {"role": "검수자", "text": "브라우저 보안 토픽의 의견 글 문장은 근거 대조 불가로 '확인 필요' 표시"},
     ]},
    {"kind": "nightly", "at": "2026-10-04T02:00:00+09:00", "duration": "11분", "status": "ok",
     "summary": "글 7, 영상 1, 레포 2 수집",
     "steps": [
         {"role": "편집장", "text": "영상 1편 처리 깊이: 슬라이드까지. 근거: 제목에 '비교', 길이 22분, 수동 자막 있음"},
         {"role": "영상 분석가", "text": "장면 전환 프레임 64장 중 수치가 많은 9장 판독, 슬라이드 전용 수치 3개"},
     ]},
    {"kind": "nightly", "at": "2026-10-03T02:00:00+09:00", "duration": "6분", "status": "partial",
     "summary": "글 5 수집, 소스 1개 실패",
     "steps": [
         {"role": "수집기", "text": "예시 블로그 A 응답 시간 초과 (10초), 다음 실행에서 재시도"},
     ]},
    {"kind": "nightly", "at": "2026-10-02T02:00:00+09:00", "duration": "9분", "status": "ok",
     "summary": "글 12, 레포 4 수집",
     "steps": [
         {"role": "편집장", "text": "새 영상 없음, 영상 단계 건너뜀"},
         {"role": "레포 분석가", "text": "example/mega-agent-hub: 7일 별 +5.6k, 커밋 0건, 기여자 1명으로 '확인 필요'"},
     ]},
]

data = {
    "meta": {
        "product": "TrendsIT", "generated_at": "2026-10-06", "example": True,
        "notice": "예시 데이터예요. 글 제목과 링크는 GeekNews 실제 글이고, 요약은 그 글을 바탕으로 썼어요. 영상, 레포 별 증가, 실행 기록은 가상이에요.",
        "markup": "문자열 안의 ==텍스트==는 형광 밑줄(핵심 내용). 영상 시각 t는 MM:SS, sec는 초",
        "signal_labels": signal_labels,
        "channel_labels": {"text": "글", "video": "영상", "github": "GitHub"},
        "channel_labels_topic": {"text": "글", "video": "영상", "github": "레포"},
    },
    "weeks": weeks,
    "topics": topics,
    "repos": repos,
    "sources": sources_cfg,
    "keywords": keywords,
    "runs": runs,
}

out = pathlib.Path(__file__).parent / "trendsit-example.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", out, out.stat().st_size, "bytes /", len(topics), "topics /", len(repos), "repos")
