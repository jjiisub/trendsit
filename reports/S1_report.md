# S1 리포트: S0 보완 + 수집 (얕게 훑기의 코드 부분) + 백필

> 진행 체크리스트(COMMON 8장). 맥락이 끊기면 여기서 이어 간다.
> S0_ADDENDUM은 S0 PR(#1)에 들어가지 않았으므로 **S1의 첫 단계(1a)**로 했다.

## 진행 체크리스트

### 1a S0 보완 (S0_ADDENDUM) + S0 리뷰 반영 (S0_REVIEW)
- [x] 1.1 역할 md 앞부분 `task`, `core_rules`(최대 3, 로더가 검증)
- [x] 1.2 메시지 조립: system = 역할 md + includes + data 규칙 / user = `<data>` → task → 핵심 규칙. 해시 = system + task + core_rules
- [x] 1.3 `render_data`(`core/render.py`): `Document`는 `<document id source title url>`, 짧은 칸은 `이름: 값`, 자료 안의 `<`는 모두 `&lt;`. 도구 결과도 같은 함수
- [x] 1.4 출력 스키마 칸 순서(log, attention 맨 끝, basis가 oneliner 앞, critique가 verdict 앞) + 테스트
- [x] 1.5 역할 md 검사(`check-config`): 고정 섹션 6개 순서, `<example>` 3~5개, 굵게 1개 이하, task·core_rules
- [x] 1.6 repo_oneliner 다시 쓰기: 템플릿, `basis` 칸, README를 `rp:` 문서로, 코드 검사(basis가 README 안에)
- [x] 1.7 예/아니오 채점: judge 출력 critique → verdict(Q1~Q3), 1~5점은 보고용
- [x] 1.8 라벨 도구: `eval --label`, `eval --agreement`. `eval/labels/repo_oneliner.csv` 생성(사용자가 채움)
- [x] 1.9 AGENTS.md(S6, 20달러·50달러, 역할 md 형식), CLAUDE.md(prompt_guide, RULES)
- [x] 1.10 README 12칸 골격, `.github/pull_request_template.md`, `.github/workflows/ci.yml`, `docs/RULES.md`, `docs/adr/0000-template.md`, `docs/images/`
- [x] R1 태그 탈출 대소문자(`<` 전부 무력화) / R2 채점자 md 역할 무관 / R3 도구 예외를 결과로 / R4 nullable 인자 정규화 / R5 A9 제외 범위 좁힘 / R6 검사 범위(roles + eval/judge.md, 추가 섹션 허용), lookup_agent 템플릿으로
- [x] 관문 A: `verify_s1.sh`의 P1~P6, R1~R6 PASS
- [~] 관문 B(repo_oneliner): 3회 개선 후 **미달**(코드 채점 8/10). 아래 1a 관문 B 참고

### 1b 수집
- [ ] 설정: sources.yaml(백필, GitHub 트렌딩 페이지), link_kinds.yaml, check-config 스키마
- [ ] safe_fetch(SSRF, 속도 제한, robots, 재시도, HTTP 캐시)
- [ ] 글 수집(RSS, 본문 추출, GeekNews 원문 링크, 백필 list_pages/day_archive)
- [ ] 유튜브(RSS, yt-dlp 메타데이터, 백필)
- [ ] GitHub(트렌딩 주간 페이지, 추적 레포 릴리스, README)
- [ ] 링크 판별, 키워드 매칭
- [ ] 칠판 테이블 + 마이그레이션(user_version)
- [ ] CLI collect, items, report collection
- [ ] 픽스처, 테스트, verify_s1.sh A3~A12
- [ ] 관문 B: 실제 수집 1회 + `reports/S1_collection.md`

## 1a 관문 B (repo_oneliner, generate, 판정은 잠정)
| 회차 | 바꾼 것 하나 | 프롬프트 | 코드 채점 | Q1 | Q2 | Q3 |
|---|---|---|---|---|---|---|
| 1 | 새 템플릿(task, core_rules, basis, 문서 태그), 예/아니오 채점 | `2969b076772d` | 7/10 | 7/7 | 7/7 | 7/7 |
| 2 | md 문구: basis는 README 본문에서, 마크업이 끼지 않은 구간 | `7bbc556f62db` | 7/10 | 7/7 | 7/7 | 7/7 |
| 3 | 예시 교체: 함정 예시 awesome-python → flask(링크 기호가 낀 구절, description과 다른 문구) | `c16be6fbb27f` | 8/10 | 8/8 | 8/8 | 8/8 |

- 문턱값(Q1 10/10, Q2·Q3 9/10, 코드 채점 전부) 미달. 3회 상한이라 멈춤
- 남은 실패 2건(출력을 직접 읽고 분류)
  - hermes-agent(모델 한계): README가 `**The self-improving AI agent built by [Nous Research](…).**`인데 basis를 링크 기호를 뺀 "The self-improving AI agent built by Nous Research"로 옮김. md 지시와 예시를 줘도 3회 모두 같음
  - fastapi template(입력에 정보 부족 + 지시 위반): README 앞부분이 제목과 링크 달린 기술 목록뿐이라 기능을 말하는 구절이 없음. 3회 모두 description 문장을 basis로 씀
- 1회차 → 3회차 사이에 excalidraw(`</br>`가 낀 구절)는 해결, Images360은 2회차에만 attention을 false로 냄(같은 입력에서도 흔들림)
- 다음 시도 후보(설계 세션 결정 필요): README 입력 조립에서 마크다운·HTML 기호를 걷어 낸 본문을 모델에 주고, basis 검사도 그 본문 기준으로(S0_REVIEW 3장의 "README 배지·HTML 정리는 S3 입력 조립 코드에서"와 같은 작업). 채점 기준을 바꾸는 일이라 이번에는 하지 않음
