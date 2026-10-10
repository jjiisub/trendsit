# TrendsIT S5 handoff 묶음 (2026-10-09)

맥 코드 세션 1개가 순차로 구현한다. 이 묶음의 파일을 저장소 **같은 경로에 덮어쓰고**, 아래 "직접 고칠 파일" 두 개를 고친 뒤 `s5-brief` 브랜치 첫 커밋(`docs(s5): handoff 묶음`)으로 넣는다.

## 전달 문장 (맥 Claude Code 세션)
> trendsit 저장소에서 작업 폴더가 `p1-env`에 있으면 `git checkout main && git pull`(02:00 수집 시각은 피해서) 하고, `git checkout -b s5-brief`로 브랜치를 만들어줘. 첨부한 `trendsit-s5-handoff.zip`을 풀어 저장소 같은 경로에 덮어쓰고, `docs/handoff/README_S5.md`의 "직접 고칠 파일"(CONTEXT.md, README.md)을 고친 뒤 첫 커밋 `docs(s5): handoff 묶음`으로 넣어줘. 그다음 `docs/handoff/COMMON.md`(2026-10-09 갱신: README 갱신 시점, 라벨 정책 D1-3, 3.1 탈출 조건 E1~E11) → `docs/handoff/S5_TASK.md` → `docs/reference/s5_role_notes.md` 순서로 읽고 S5_TASK의 0단계부터 진행해줘. 0단계에 원격 브랜치 정리와 임시 수집 로그 확인이 있어. **3단계(묶기)가 끝나면 묶기 리포트를 커밋·푸시하고 멈춰서 내 "진행"을 기다려줘.** 진행 블록(E11)은 단계 시작·끝마다 출력해줘.

## 바뀌거나 새로 생긴 파일
| 경로 | 내용 |
|---|---|
| docs/handoff/S5_TASK.md | S5 스펙: 0 환경 점검·정리 → 1 공통 수정·재료 개선·재생성 → 2 근거 목록·표기 정규화 → 3 묶기·과거 대조(**멈춤**) → 4 편집장 선별 → 5 작성자·코드 검사 → 6 검수자·수정 루프 → 7 weekly·저장·실행 요약 → 8 관문 B(W42 + W41) (새 파일) |
| docs/handoff/COMMON.md | 1장 README는 단계 커밋마다 갱신·handoff 묶음 커밋, 2장 judge 너그러움 대응·라벨 정책 D1-3·점수 병기, 3.1 반복 탈출 조건 E1~E11, 4장 사용액은 키 기준, 6장 ENFORCED_FIELDS·원래 출력으로 품질 검사, 6.1-9 출력 잘림, 8장 스펙 순서 최신화, 9장 병행 규칙 접고 파일 소유·대역(S5 30~39)만, 11장은 클라우드 구현 때만 |
| docs/handoff/README_S5.md | 이 파일 (새 파일) |
| docs/reference/s5_role_notes.md | S5 역할 5개의 요구사항·과거 교훈(S1~S4 리뷰에서 옮김)·픽스처·측정. 역할 md 고도화의 근거 (새 파일) |
| docs/reference/trendsit-example.json | 출력 계약 참고(예시 사이트 화면용 데이터, 88KB). 스키마를 맞추지 않고 참고만 (새 파일) |
| roles/decide.md | 묶기 판단 초안 (새 파일) |
| roles/editor_select.md | 편집장 선별 초안: 넣을지(관심 주제 + 읽을 거리)와 순서(채널·수치·추세) 분리, 토픽 4~10 (새 파일) |
| roles/writer.md | 작성자 초안: 화면 칸 대응, 도식은 포인트에 붙임(anchor + context) (새 파일) |
| roles/writer_revise.md | 작성자 수정 초안: 고친 칸만 출력 (새 파일) |
| roles/critic.md | 검수자 초안: 원자 사실 대조, 길이 편향 경고, 이슈 유형 7개 (새 파일) |
| skills/diagrams.md | 도식 규칙(A~D, 포인트에 붙이는 배치, 상한) (새 파일) |
| config/brief.yaml | S5 조정값 초안(근거 상한, 묶기 임시 문턱값, 토픽 수, 라운드). S5 스펙 소유 (새 파일) |
| config/budget.yaml | S5 3.00 추가 |
| config/keywords.yaml | 제외어 4개 추가(태양광, 재생에너지, 송전망, 전력망) |

## 직접 고칠 파일 (첫 커밋에서 코드 세션이)
### docs/CONTEXT.md
1. 맨 위 "마지막 갱신"을 `2026-10-09 (6주차, S5 handoff)`로
2. "1. 현재 상태"의 "다음:" 줄을 지우고 아래를 그 자리에 넣는다
```
- 2026-10-08: **S2~S3 PR #6, S4 PR #7 리뷰 후 병합**(문서 56~62). 관문 B는 잠정(labeler opus-5.5, D1-3). 미달 항목(item_card 충실성, 영상 요약 Q1~Q3, 시드 11/13)은 S5 첫 단계 재료 개선으로
- 2026-10-09: **P1 작업 환경 정리 PR #8 병합.** 세 DB를 main 하나로(s4는 id 대응표), W41 백필, 매일 02:00 collect 임시 launchd(LLM 0원, S6 정식 launchd 때 제거). worktree 정리. 사용액 키 기준 $2.46 / 20
- 2026-10-09: **S5 handoff 전달**(`docs/handoff/S5_TASK.md`). 한 스펙·한 PR, 묶기 끝에서 한 번 멈춤. 시연 두 주 W42 + W41. 역할 md 5개는 설계 세션 초안 + 근거 메모(`docs/reference/s5_role_notes.md`)를 넘기고 코드 세션이 고도화
- 다음: S5 구현(맥 코드 세션) → 묶기 리포트 확인 → PR 리뷰 → S6(export, 사이트 연결, 정식 launchd). 일정은 사용자가 관리
```
3. "12. 코드 구조" 제목 괄호에 `S5 brief/` 추가
4. "16. 결정 기록" 끝에 추가
```
- 2026-10-09 S5 진행 방식: 검증 수준 유지(55 효율화만, COMMON 3.1 E1~E11), 코드 세션 1 + 리뷰 1 순차(병행 없음). 모델은 MVP까지 qwen3.8-27b 하나(작성자·검수자 포함), 여유가 생기면 모델 분리보다 로컬화 먼저
- 2026-10-09 S5 설계: 묶기는 주 1회(weekly 시작 때), 결과는 run_id로 쌓고 현재판은 weeks.current_run_id. 채널을 넘는 묶음은 키워드·별칭 공유 + decide. 숫자·버전이 다른 이름은 별칭 아님. 레포만 있는 묶음은 토픽이 아니라 홈 레포 목록. 편집장 선별은 넣을지(관심 주제 + 읽을 거리, 근거 1건도 됨)와 순서(채널·수치·추세)를 분리, 토픽 4~10. 도식은 포인트에 붙임(anchor + context). 고칠 수 있는 형식은 코드가 직접 고치고, 같은 이슈가 2회 남으면 '확인 필요'로 확정. 예시 JSON은 화면 참고용(스키마를 맞추지 않음)
- 2026-10-09 handoff 전달은 zip 묶음을 스펙 브랜치 첫 커밋으로(main에 따로 PR 안 함). README는 단계 커밋마다 갱신
```
5. "17. 사람 확인 부채" 표에 S2~S3 행이 없으면 추가: `| S2~S3 | relevance 경계·item_card judge 너그러움·editor_plan mode 경계 | 9행·21건·3행 | 문서 61·62 | 경계 행 사람 판정 |`

### README.md (저장소 루트, 지금 S1 상태에 머물러 있음)
1. "현재 상태" 인용 줄을 `> 현재 상태(2026-10-09): **S0~S4 완료, S5(주간 브리핑) 진행 중.** 글 6곳·유튜브·GitHub 트렌딩 수집, 글 1차 요약과 원본 추적, 레포 분석, 영상 전사와 슬라이드 판독까지 동작한다. 매일 02:00 수집이 돌고 있다. 묶기·선별·작성 ⇄ 검수(주간 브리핑)는 S5에서 붙인다. 예시 사이트는 예시 데이터로 만든 화면이다.`로
2. 핵심 기능 표: 원본 추적 상태 `S3` → `**S3 완료**(원본 확보 14/16)`, 소스 간 교차 연계와 근거 검수 `S5` → `S5 진행 중`
3. 역할 표: item_card·editor_plan·text_analyst·repo_analyst의 "S2/S3 구현, 맥 확인, 리뷰 반영(잠정 채점)" → `**S2~S3 완료**(관문 B 잠정)`. 마지막 행(편집장 · 선별 / 작성자 / 검수자)의 스펙 칸 `S5` → `S5 진행 중`
4. 로드맵: S2, S3 체크 `[x]`, S5 줄 끝에 `(진행 중)`
5. 그 밖의 줄은 고치지 않는다. 이후 S5 단계 커밋마다 COMMON 1장대로 갱신

## 문서 번호 대응
문서 안의 "문서 N"은 설계 프로젝트의 문서 번호다. 저장소에서는: 21 = `docs/CONTEXT.md`, 26 = `docs/reference/agents_spec.md`, 27 = `docs/reference/sources_keywords.md`, 29 = `docs/reference/writer_draft.md`, 30 = `docs/handoff/COMMON.md`, 32 = `docs/reference/writing_visual_guide.md`, 33 = `docs/reference/youtube_analyze.md`, 35 = `docs/reference/prompt_guide.md`. 47(6주차 모델 비교), 53~62(S1~S4 리뷰), 64(S5 기획과 결정 부록 C), 66(P1 결과)은 저장소에 없고, S5에 필요한 내용은 `s5_role_notes.md`와 `S5_TASK.md`에 옮겼다.
