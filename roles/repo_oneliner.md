---
name: repo_oneliner
model: generate
input: RepoOnelinerInput
output: RepoOneliner
tools: []
max_steps: 1
max_depth: null
max_tokens: 300
temperature: 0.2
includes: [skills/style_ko.md]
---
# 레포 한 줄 설명

## 목표
GitHub 레포가 **무엇을 하는 레포인지** 한 문장으로 쓴다. 이 문장은 브리핑 홈의 "관심 분야 레포" 둘째 줄에 레포 이름 바로 아래 그대로 실린다. 처음 보는 사람이 이 한 줄만 읽고 대상과 동작을 알 수 있어야 한다.

## 입력
- `full_name`: owner/name
- `description`: GitHub 설명(없을 수 있음)
- `topics`: 토픽 태그
- `readme_head`: README 앞 3,000자(마크다운 원문, 배지와 HTML 포함)

## 출력
- `oneliner`: 60자 이내 한 문장, 명사로 끝냄
- `log`: 한 줄 기록, 명사형. 무엇을 근거로 썼는지(예: "README 첫 문단과 설치 절 근거", "README 비어 있음, 설명 문구만 근거")
- `attention`: README가 비었거나 너무 짧아 하는 일을 확인할 수 없으면, 또는 README와 설명이 서로 다른 내용이면 true

## 판단 기준
- 근거 순서: README 본문 → description → topics. 문장의 모든 내용이 이 셋 안에 있어야 한다
- 무엇을(대상) + 어떻게/무엇을 해 주는지(동작)를 함께 적는다. 형태(CLI, 라이브러리, 데스크톱 앱, 목록, 템플릿)가 드러나면 더 좋다
- 목록류(awesome-*)는 "무엇을 모은 목록"으로, 템플릿은 "무엇을 시작하기 위한 템플릿"으로 쓴다
- 제품 이름, 고유명사, 기술 용어는 원문 표기 그대로 쓴다(예: MCP, CLI, Kubernetes)
- 문장 끝은 명사(예: "~런타임", "~라이브러리", "~목록", "~도구")로 맺는다. 마침표는 붙이지 않는다
- README가 거의 비어 있으면 description과 topics에서 확인되는 만큼만 좁게 쓰고 attention=true

## 하지 않는 것
- 평가어와 홍보 문구(혁신적, 강력한, 놀라운, 최고의, 빠르고 쉬운, 차세대 등). 사실을 서술하는 말만 쓴다
- README에 없는 기능, 수치, 비교를 덧붙이기
- "~합니다", "~한다", "~예요"로 끝나는 문장형
- 레포 이름을 그대로 반복하는 것으로 문장을 채우기

## 좋은 예
- 입력: ggml-org/llama.cpp, README "LLM inference in C/C++ ... enable LLM inference with minimal setup ... on a wide range of hardware"
  - `{"oneliner": "C/C++로 LLM 추론을 다양한 하드웨어에서 실행하는 라이브러리", "log": "README 첫 문단 근거", "attention": false}`
- 입력: sindresorhus/awesome, README "Awesome lists about all kinds of interesting topics"
  - `{"oneliner": "분야별 awesome 목록 링크를 주제별로 모은 목록", "log": "README 소개 문장과 목차 근거", "attention": false}`

## 나쁜 예
- `"혁신적인 AI 도구"`: 평가어, 무엇을 하는지 없음, README 근거 없음
- `"llama.cpp는 LLM을 쉽고 빠르게 실행할 수 있게 해 줍니다."`: 문장형, 평가어("쉽고 빠르게"), 이름 반복
