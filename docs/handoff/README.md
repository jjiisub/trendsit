# TrendsIT S0 handoff 묶음

설계 세션이 만든 첫 구현 스펙 묶음이다. 코드 세션에 이 폴더를 넘기고 아래 문장을 전달한다.

> 이 폴더의 README.md를 읽고, 내용을 GitHub 비공개 저장소 `trendsit`의 루트에 옮긴 뒤 `docs/handoff/S0_TASK.md`대로 진행해줘. 공통 규칙은 `docs/handoff/COMMON.md`.

## 읽는 순서
1. `AGENTS.md` — 명령, 원칙, 함정 (짧음)
2. `docs/handoff/COMMON.md` — 모든 스펙 공통: 일하는 방식, 관문 A/B, 자체 루프, 예산, 모델, 리포트 형식
3. `docs/handoff/S0_TASK.md` — 이번 스펙
4. 필요할 때: `docs/CONTEXT.md`(프로젝트 전체 맥락), `docs/reference/`

## 묶음 구성
| 경로 | 내용 | 저장소에서 |
|---|---|---|
| AGENTS.md, CLAUDE.md | 코딩 에이전트 지침(CLAUDE.md는 AGENTS.md 참조) | 루트 |
| config/sources.yaml, keywords.yaml | MVP 고정 소스(글 6, 영상 1, GitHub)와 키워드 10개 + 제외어 | 그대로 |
| config/models.yaml, budget.yaml | 모델 별칭(generate, judge, compare, smoke)과 예산(단계 2달러, S0 0.15달러) 초안 | 그대로 |
| skills/style_ko.md | 한국어 문체 규칙 | 그대로 |
| docs/handoff/ | 공통 규칙 + S0 스펙 | 그대로. 이후 스펙도 여기에 추가 |
| docs/CONTEXT.md | 프로젝트 맥락(설계 세션 문서 21과 같음) | 그대로 |
| docs/reference/agents_spec.md | 에이전트별 역할, 입출력, 제약 | 그대로 |
| docs/reference/writer_draft.md | 작성자 지침 v2 + 도식 규칙 + 채점(S6에서 사용) | 그대로 |
| docs/reference/writing_visual_guide.md | 문서 작성 가독성·도식화 가이드 요약(작성자 지침의 근거) | 그대로 |
| docs/reference/sources_keywords.md | 소스, 키워드 결정 배경 | 그대로 |
| docs/reference/dev_env_report.md | 개발환경 구조 판단 요약 | 그대로 |
| docs/reference/youtube_analyze.md | 맥의 영상 분석 스킬 요약 + 영상 분석가에 가져올 방식(참고만, 의존 안 함. S4에서 사용) | 그대로 |

참고 문서 안의 "프로젝트 문서 N번"은 설계 세션 쪽 문서 번호다. 저장소에 없는 문서는 필요하면 리포트에 요청한다.
