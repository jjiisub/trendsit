# 개발환경 구조 판단 요약 (2026-10-07)

근거: Anthropic Building effective agents, Multi-agent research system, Context engineering, Writing tools, Evals / OpenAI A practical guide to building agents, Agents SDK / GitHub 12-factor-agents, AGENTS.md / Octomind, Cognition, Docker 실무 후기.

- 흐름은 코드, LLM은 판단 지점만, 에이전트는 단계 수를 모르는 곳만. 구조 사다리: LLM 1회 → 워크플로 → 단일 에이전트 → 멀티에이전트. 한 칸 올릴 때마다 이유를 한 줄로
- 프레임워크보다 API 직접 호출 + 작은 코드. 프롬프트, 컨텍스트, 제어 흐름을 직접 소유
- 개발환경의 핵심: 평가 세트, 실행 기록(trace), 스키마 검증. 실제 사례 20~50개로 시작, 채점은 코드 → LLM → 사람
- 도구는 적고 겹치지 않게, 결과는 요약해서, 오류 메시지가 다음 행동을 안내하게
- 반드시 지켜질 것은 프롬프트가 아니라 코드로
- 작은 모델(10B 미만)은 도구 호출 편차가 큼 → 로컬 전환 시 에이전트 역할이 가장 위험
- TrendsIT 적용: 구조는 현재 설계 유지(LangGraph, 멀티에이전트화는 MVP 이후 실험). 평가 틀과 실행 기록, 재생을 S0으로 앞당김. 레포 분석가 깊이 2는 "코드 수집 + LLM 1회"로 강등할지 S4 전에 픽스처로 비교
