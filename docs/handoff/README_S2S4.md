# TrendsIT S2~S4 handoff 묶음 (병행: 묶음 A = S2~S3, 묶음 B = S4)

이 파일들은 **먼저 main에 넣고**, 두 코드 세션이 각자 main에서 브랜치를 만든다. 두 묶음이 같은 공통 문서를 쓰므로 브랜치마다 따로 덮어쓰면 같은 파일이 두 번 들어가 병합 때 헷갈린다.

## 전달 문장
**묶음 A (클라우드 Claude Code 세션, 저장소 `trendsit`):**
> main을 받아서 `docs/handoff/COMMON.md`(9~11장 새로 추가) → `docs/handoff/S1_REVIEW.md` → `docs/handoff/CONTRACTS.md` → `docs/handoff/S2S3_TASK.md` 순서로 읽고 진행해줘. 먼저 0단계를 `s2-0-base` 브랜치의 작은 PR로 열고, 그다음 `s2-s3` 브랜치에서 2a → 2b → 3c → 3a → 3b 순서로 단계별 커밋해줘. 맥에서 해야 할 것은 `reports/S2S3_mac_todo.md`에 정리하고 PR 맨 위에 "맥 확인 대기"라고 써줘.

**묶음 B (맥 Claude Code 세션):**
> trendsit 저장소에서 `git pull` 후 `git worktree add -b s4-video ../trendsit-s4` 로 만든 폴더에서만 작업해줘. `docs/handoff/COMMON.md`(9~10장 새로 추가) → `docs/handoff/CONTRACTS.md` → `docs/handoff/S1_REVIEW.md`(M1) → `docs/handoff/S4_TASK.md` → `docs/reference/youtube_analyze.md` 순서로 읽고 진행해줘. DB 없는 부분부터 하고, 마이그레이션은 `s2-0-base` PR이 main에 병합된 뒤 main을 받아서 20번대로 추가해줘.

**묶음 A 맥 확인 (A의 PR이 "맥 확인 대기"가 된 뒤, 맥 세션):**
> `git fetch` 후 `git worktree add ../trendsit-s2s3 s2-s3` 폴더에서 `reports/S2S3_mac_todo.md` 목록대로 확인하고, 결과를 그 파일에 채운 뒤 고칠 것은 같은 브랜치에 커밋해줘. 끝나면 PR 설명 맨 위를 "맥 확인 완료"로 바꿔줘.

## 바뀌거나 새로 생긴 파일
| 경로 | 내용 |
|---|---|
| docs/handoff/S2S3_TASK.md | 묶음 A: 0단계(S1 리뷰 반영) → 2a 키워드 재판정·임베딩 필터·중복 연결 → 2b 글 1차 요약 → 3c 레포 분석가 → 3a 편집장 계획 → 3b 글 분석가. 맥 확인 목록 (새 파일) |
| docs/handoff/S4_TASK.md | 묶음 B: 영상 1차 처리(전사, 프레임) → 이미지 입력 → 슬라이드 판독 → 대조 → 영상 요약 (새 파일) |
| docs/handoff/S1_REVIEW.md | S1 PR 리뷰 반영: M1 마이그레이션 번호 키 등록, M2 enforce 훅과 repo_oneliner 200자 규칙, M3 DNS 연결 주소 고정, M4 도구 거부 메시지 경로, M5 키워드 조정, M6 낡은 문구 (새 파일) |
| docs/handoff/CONTRACTS.md | 두 묶음의 교차 계약: 영상 처리 지시 형식, 근거 id, 테이블 소유, 공통 코어 수정의 주인 (새 파일) |
| docs/handoff/COMMON.md | 8장 목표일 열 삭제, 9장 병행 개발, 10장 검증 산출물, 11장 맥 확인 단계, 설정 파일 소유 |
| docs/CONTEXT.md | 현재 상태와 결정 기록(S1 병합, 6주차 결정, 병행 handoff) |
| config/budget.yaml | S2 1.00, S3 2.00, S4 0.80 추가 |
| config/keywords.yaml | 키워드 13개(ai-general, ai-industry, dev-practice 추가), eval 별칭 구체화, SynthID·Cursor 추가 |
| eval/labels/repo_oneliner.csv | 사용자 라벨 10행 채움(9건 통과, hermes-agent Q2 실패) |
| eval/labels/relevance_seed.csv | 수집 샘플 사용자 판정 13건(S2 관련성 필터 기준) (새 파일) |
| tests/fixtures/contracts/video_queue.json | 영상 처리 지시 계약 픽스처(두 묶음 공용) (새 파일) |

## 문서 번호 대응
문서 안의 "문서 N"은 설계 프로젝트의 문서 번호다. 저장소에서는: 26 = `docs/reference/agents_spec.md`, 29 = `docs/reference/writer_draft.md`, 32 = `docs/reference/writing_visual_guide.md`, 33 = `docs/reference/youtube_analyze.md`, 35 = `docs/reference/prompt_guide.md`, 27 = `docs/reference/sources_keywords.md`, 30 = `docs/handoff/COMMON.md`, 21 = `docs/CONTEXT.md`.
