# TrendsIT S1 handoff 묶음 (S0 보완 + 레포 문서 틀 + 수집 + 백필)

S0이 병합된 `trendsit` 저장소에 이 묶음을 덮어쓰고, 코드 세션에 아래 문장을 전달한다.

> 이 묶음의 파일을 `trendsit` 저장소 같은 경로에 덮어쓴 뒤, `docs/handoff/COMMON.md`(6.1 역할 md 작성 규칙, 2장 채점 방식, 8장 스펙 순서 갱신) → `docs/handoff/S0_ADDENDUM.md` → `docs/handoff/S0_REVIEW.md` → `docs/handoff/S1_TASK.md` 순서로 읽고 진행해줘. 1a(S0 보완) → 1b(수집) 단계로 나눠 커밋해줘.

S0 PR #1은 2026-10-07 리뷰 후 병합됐고 S0_ADDENDUM은 들어가지 않았다. **그래서 1a(S0 보완 + S0 리뷰 반영)를 건너뛰지 않는다.**

## 바뀌거나 새로 생긴 파일
| 경로 | 내용 |
|---|---|
| docs/handoff/S1_TASK.md | 이번 스펙 (새 파일). 1a S0 보완 → 1b 수집. 관문 A에 R1~R6, 관문 B 수집 기간을 끝난 주(9/28~10/4)로 |
| docs/handoff/S0_REVIEW.md | S0 PR 리뷰 반영(1a에 함께): R1 태그 탈출 대소문자, R2 채점자 md 일반화, R3 도구 예외를 결과로, R4 nullable 인자 정규화, R5 비밀 검사 범위, R6 역할 md 검사 범위. S0에서 정한 것 중 유지할 것, 리포트 질문에 대한 답 (새 파일) |
| docs/handoff/S0_ADDENDUM.md | S0 보완: 레포 문서 틀(README 12칸 골격, PR 양식, CI, ADR 틀, RULES), AGENTS.md 예산 20달러, 역할 md 앞부분 task·core_rules, 메시지 조립(자료 위, 과제·핵심 규칙 아래), 문서별 태그, 출력 칸 순서, 역할 md 검사, repo_oneliner 다시 쓰기, 예/아니오 채점, judge 라벨 도구 (새 파일) |
| docs/handoff/COMMON.md | 1장 커밋 규칙·PR 양식·README와 위키 역할, 4장 예산 20달러(키 한도 50달러), 6.1 역할 md 작성 규칙, 2장 관문 B 예/아니오 채점과 judge 맞추기, 3장 고치는 순서, 8장 스펙 순서(7개) |
| docs/reference/prompt_guide.md | 프롬프트 작성 가이드: 역할 11개와 형태, 공통 원칙, 형태별 작성법, 공통 템플릿, 고치는 순서, judge 맞추기 (새 파일) |
| config/budget.yaml | `phase_total_usd: 20.00`, `specs.S1: 0.05` |
| config/sources.yaml | 백필 방법 추가, GitHub 트렌딩 출처를 OSS Insight → GitHub Trending 주간 페이지 |
| config/link_kinds.yaml | 링크 종류 판별 규칙 (새 파일) |
| docs/CONTEXT.md | 프로젝트 맥락 최신본 |
| docs/reference/agents_spec.md | 0.7 역할별 프롬프트 권고, 출력 칸 순서, 레포 분석가 입력을 트렌딩 페이지 기준으로, 임베딩 모델 |
| docs/reference/writer_draft.md | 작성자 지침 v2.1(writer_revise 분리, 예/아니오 채점, S5에서 구현) |
| docs/reference/sources_keywords.md | 소스 설정 최신본 |

## 문서 번호 대응
문서 안의 "문서 N"은 설계 프로젝트의 문서 번호다. 저장소에서는: 26 = `docs/reference/agents_spec.md`, 29 = `docs/reference/writer_draft.md`, 32 = `docs/reference/writing_visual_guide.md`, 33 = `docs/reference/youtube_analyze.md`, 35 = `docs/reference/prompt_guide.md`, 27 = `docs/reference/sources_keywords.md`, 30 = `docs/handoff/COMMON.md`, 21 = `docs/CONTEXT.md`.
