# S5 주간 브리핑: 묶기 → 선별 → 작성 ⇄ 검수

> 설계 세션 작성 2026-10-09. 기준 커밋 **main `44921dc` 이후**(P1 병합). 공통 규칙은 `docs/handoff/COMMON.md`(이번 묶음에서 갱신), 이 문서가 우선한다.
> 맥 코드 세션 1개가 순차로 구현하고, 리뷰는 설계 세션이 한다(병행 없음). 브랜치 `s5-brief`, 한 스펙·한 PR. **3단계(묶기) 끝에서 한 번 멈춘다.**
> 근거 문서: 역할 설계의 "왜"는 `docs/reference/s5_role_notes.md`(S1~S4 리뷰 교훈), 역할별 명세는 `docs/reference/agents_spec.md` 6~8장·0.7, 작성자 지침은 `docs/reference/writer_draft.md`(아래 5.5~5.7과 다르면 이 문서가 우선), 프롬프트 형식은 `docs/reference/prompt_guide.md`. 화면 참고는 `docs/reference/trendsit-example.json`(스키마를 여기에 맞추지 않음, 11장).

## 0. 이 스펙이 끝나면 되는 것
`trendsit weekly --week 2026-W42`를 주면 그 주의 글·영상·레포를 **토픽으로 묶고, 지난 토픽과 대조하고, 편집장이 토픽과 순서를 정하고, 작성자가 근거 id 달린 토픽 페이지를 쓰고, 코드 검사와 검수자가 반려(최대 2회)하며 다듬어** 칠판(SQLite)에 저장한다. 저장된 값만으로 S6 export가 예시 JSON 형식의 화면 데이터를 만들 수 있어야 한다. export·사이트·정식 자동 실행은 S6.

## 1. 맥락
- 지금까지: S0 바탕, S1 수집, S2 글 요약·필터, S3 편집장 계획·글/레포 분석가, S4 영상 분석가, P1 작업 환경 정리(DB 통합, 매일 수집 임시 예약)까지 main에 병합
- 이 스펙이 TrendsIT의 핵심 차별점(소스 간 교차 연계, 근거 검수)을 처음 결과물로 만든다. 8주차 MVP 시연(W42 + W41 브리핑)의 본체
- 진행 방식: **검증 수준은 그대로**(관문 A·B 문턱값 유지), 반복 낭비만 줄인다(COMMON 3.1 탈출 조건 E1~E11)
- 모델: 모든 역할 `generate`(qwen3.8-27b) 하나. 검수자도 같은 모델의 새 메시지 목록. 관문 B 채점은 `judge`(gemini-3.8-flash), 라벨은 리뷰 세션의 opus-5.5(COMMON 2장 D1-3)

## 2. 진행 순서 (단계별 커밋, 진행 블록 E11)
| 단계 | 내용 | 멈춤 |
|---|---|---|
| 0 | 환경 점검·정리(5.0) + handoff 묶음 커밋 + README 맞춤 | - |
| 1 | 공통 수정 커밋(5.1) → 재료 품질 개선(P4 1·2·3·6·7) → 대상 두 주 재료 생성·재생성(5.2) | - |
| 2 | 근거 목록(EvidencePack) + 표기 정규화 v0(5.3) | - |
| 3 | 묶기 + 과거 대조 → 묶기 리포트(5.4) | **멈춤: 리포트 커밋·푸시 후 "리뷰 확인 대기"를 출력하고 대기. 사용자가 "진행"을 주면 4단계** |
| 4 | 편집장 선별(5.5) | - |
| 5 | 작성자 + 코드 검사(5.6, 5.7) | - |
| 6 | 검수자 + writer_revise 루프(5.8) | - |
| 7 | `weekly` 명령으로 한 주 끝까지 + 저장 + 실행 요약(5.9, 5.10) | - |
| 8 | 관문 B(W42 + W41 실제 실행), 리포트, PR(7장) | - |

- 커밋 메시지 `<종류>(s5): …`, 본문 첫 줄에 단계 번호. 맥락이 끊기면 `reports/S5_report.md`의 체크리스트를 보고 이어 간다
- **README는 의미 있는 단계 커밋마다 갱신**(COMMON 1장): "현재 상태" 줄, 핵심 기능·역할 표의 상태, 로드맵 체크. 관문 B 수치는 확정 때

## 3. 준비물 (0단계 확인표, E6)
| 준비물 | 확인 | 없으면 |
|---|---|---|
| main `44921dc` 이후 + 이 묶음 | `git log` | pull |
| 작업 폴더가 main | `git branch --show-current` | 5.0 |
| 통합 DB와 주차별 재료 | `reports/P1_env.md` 4장 표와 `items --week 2026-W41`·`W42` | 멈추고 질문 |
| 매일 수집 임시 예약 동작 | `launchctl print gui/$(id -u)/com.trendsit.collect-temp`, `data/logs/collect-temp/` 최근 로그 | 5.0 |
| OpenRouter 키, GitHub 토큰(`~/.config/trendsit/.env`) | `cost` | 멈추고 질문 |
| `--extra video --extra embed` | pytest 건너뜀 0 | 설치 |
| `config/budget.yaml` S5 3.00, `config/brief.yaml` | `check-config` | 이 묶음에 있음 |

## 4. 범위
### 4.1 만든다
공통 수정(5.1), P4 재료 개선, 근거 목록, 표기 정규화 v0, 묶기(코드 + decide), 과거 대조, 편집장 선별, 작성자·writer_revise, 코드 검사(자동 수정 포함), 검수자, 반려 루프, weekly 명령과 단계별 재실행, 저장(마이그레이션 30~33), 실행 요약, 평가(픽스처·채점표·judge), `scripts/verify_s5.sh`, 리포트·검증 산출물
### 4.2 만들지 않는다
export·build·사이트 연결과 화면 수정(S6), 정식 launchd(S6. 임시 수집 예약은 그대로 둠), P4 4·5(편집장 계획 reason·mode, 원본 추적 개선 → S6), 매일 묶기(MVP 뒤), 관리 화면, 아카이브 RAG Q&A, 역할별 모델 분리, 발행 상태(published)와 공개

## 5. 상세 요구사항

### 5.0 환경 점검·정리 (0단계, LLM 0원)
1. **작업 폴더를 main으로**: P1 PR #8이 병합됐으므로 `p1-env`에 있으면 `git checkout main && git pull`(02:00 수집 시각을 피해서). 예약 스크립트 경로는 같다. 끝나면 로컬 `p1-env` 브랜치 삭제
2. **GitHub 원격 브랜치 정리**(사용자 승인됨, 2026-10-09): 병합된 8개 삭제 — `git push origin --delete s0-foundation docs-readme-skeleton s1-collect docs-s2s4-handoff s2-0-base s2-s3 s4-video p1-env`. 각 브랜치가 main에 병합됐는지 먼저 확인하고(`git branch -r --merged origin/main`), 병합 안 된 것이 있으면 지우지 말고 보고
3. **임시 수집 로그 확인**: 10/10 이후 `data/logs/collect-temp/*.log`에서 소스별 성공·실패, W41·W42 트렌딩 갱신 여부를 표로 리포트에
4. **유튜브(techbridge) RSS 404 대응**: 로그에서 404가 이어지면 **yt-dlp로 채널 영상 목록(`--flat-playlist`, 업로드 날짜 포함)을 받아 대상 주(W41·W42)에 올라온 영상을 items·videos에 백필**한다. 기존 수집 경로(중복 제거, 키워드 판정, 메타데이터)를 그대로 쓰고, 수집 경로 보강으로 `collect`에 넣는다(RSS 실패 시 채널 목록으로 대체). LLM 0원. RSS가 정상이면 하지 않는다
5. **handoff 묶음 커밋**: 이 묶음 파일을 저장소에 덮어쓴 것을 `s5-brief` 브랜치 첫 커밋(`docs(s5): handoff 묶음`)으로. `docs/handoff/README_S5.md`의 "README 맞춤" 항목도 같은 커밋에
6. 환경 점검표(3장)를 리포트에

### 5.1 공통 수정 (1단계 앞쪽 별도 커밋, 출력 재생성 없음)
PR 설명 맨 위에 "공통 코어 수정"으로 표시.
| # | 내용 |
|---|---|
| 1 | 문체 검사: 공통 `SENTENCE_END` 명사 예외("개요", "필요" 등 '요'로 끝나는 명사), `graders_video`의 자체 정규식을 공통으로 정리(`NOUN_YO` 예외 포함) |
| 2 | 품질 리포트 축약: `write_quality`가 중첩 입력을 앞 500자로 |
| 3 | 예산 기준값 파일(`budget_state.json`)을 작업 폴더 밖 공용 위치로(예: `~/.config/trendsit/`). 옮길 때 지금 기준값(10/7) 유지 |
| 4 | 코드 소유 칸 선언 방식 통일: VideoSummary도 ClassVar `ENFORCED_FIELDS`. S5 새 출력 클래스도 처음부터 ClassVar |
| 5 | judge 대상(enforce 후 전체)과 통과 판정(소유 칸만)의 차이를 `eval/` 문서와 리포트 템플릿에 명시 |
| 6 | `ImageError`를 `LLMError` 계열로, 중첩 ImageFile은 `check_roles`에서 거부 |
| 7 | `reports/eval/` JSON은 역할별 최신 전체 실행 1개만(E10). 지금 쌓인 것 정리 |
| 8 | (선택) 임베더 테스트 실패 메시지에 "모델 받기 실패(네트워크)", GitHub 도구 "성공 0" 집계에서 도구를 안 부른 항목 제외 |
| 9 | **수치 정규화를 공통 모듈로**: S4 align의 숫자·단위 정규화를 `core/numbers.py`(이름은 자유)로 옮겨 S4와 S5 코드 검사가 같이 쓴다(5.7) |
| 10 | **video_summary 캐시 키에서 item_id 영향 제거 여부 검토**: P1에서 id가 바뀌어 캐시가 안 맞았다. 근거 id 형식(`vd:{item_id}@{sec}`)은 바꾸지 않는다. 고칠 수 없으면 그대로 두고 이번에 한 번 재생성(5.2) |

### 5.2 재료 품질 개선과 재생성 (1단계)
| # | 대상 | 내용 | 방식 |
|---|---|---|---|
| P4-1 | video_slide + align | 판독 수치마다 `kind`(claim / ui / example / version / axis) — 같은 호출, 출력 조금 늘어남. 코드: claim만 slide_only 후보, 프레임당 수치 10개 이상이면 표·대시보드로 보고 낮은 순위, 발화에 있어도 화면 값이 다르면 `correction`으로 남김(예: 'Sweebench Pro 88%' → SWE-Bench Pro 80.3%). `video_slide.md`의 768 문구, `style_ko` includes 여부 정리(화면 표기 보존) | LLM 표시 + 코드 거르기 |
| P4-2 | item_card | summary·claims는 **quotes 안의 내용만**(지시 + 함정 예시: 인용 밖 본문의 고유명사·결과 서술). judge 채점표 Q1에 인용 밖 서술 fail 예시 추가 | md + 채점표 |
| P4-3 | item_card | 고객 사례 홍보 글(어느 회사가 AI 제품을 도입해 효과를 봤다는 글) relevance 규칙 + 함정 예시 | md |
| P4-6 | eval | video_summary 타임라인 Q2: ±30초 기준을 구간 라벨에 맞게(라벨 주제가 구간 안이면 통과), 근거 5개 사례 처리 | 채점 코드·채점표 |
| P4-7 | eval | text_analyst "부분 확인 내림"을 근거 없는 판정 문턱값(0~1건)에 포함 | 채점 코드 |

- 개선 반복은 E1(가설 1개 + 기대 변화를 먼저 적고, 같은 실패가 2회 남으면 그 방향 종료). 바꾼 md는 기존 픽스처로 전후 비교(기존 픽스처·채점표는 고치지 않고 예시 추가만)
- **재생성 범위**(키 기준 약 $0.8)
  - **W41·W42 글**: 관련성 필터 → item_card(W41 글은 아직 필터·카드 미실행). W42는 주가 끝난 뒤(10/19 일요일 수집 이후)
  - W41 레포: repo_cards 7개 있음, 레포 분석가는 다시 돌리지 않음. W42 레포는 W42 트렌딩으로 레포 분석가 실행
  - 영상: 대상 두 주 영상 중 편집장 계획이 고른 것 처리. 기존 digest 11개는 P4-1 반영해 **재판독(캐시로 판독 0원) + 요약 재생성(약 $0.1, P1에서 캐시 불일치 확인)**
  - 편집장 계획·글 분석가는 두 주의 nightly 흐름대로(개선 없이 현재 md)
  - W40은 평가 토픽 20개가 모자랄 때만(7장)

### 5.3 근거 목록과 표기 정규화 (2단계)
**근거 자격**(이것만 근거): item_card가 있는 글(v2가 있으면 v2), VideoDigest가 있는 영상, `relevant=true` RepoCard. 메타데이터만 있는 영상, 카드 없는 글은 제외하고 실행 요약에 센다.

**주차 경계**: ISO 주(월~일). 그 주 브리핑은 **일요일 새벽 수집분까지**, 월요일 새벽 수집분은 다음 주. 트렌딩은 그 주 마지막 수집판.

**EvidencePack**(표로 저장하지 않음: DB에서 매번 같게 조립, 작성자에게 실제로 준 입력은 llm_calls에 남음)
- 항목 = `{id, member, channel, kind, text, value?, unit?, sec?, source{site, title, date, url}}`
- kind: quote / number / claim / slide_fact / timeline / summary / repo_field
- 근거 id는 기존 규칙 그대로(CONTRACTS): 글 `it:{item_id}#q{n}`, 원본 문서 `og:{item_id}#q{n}`(ItemCard v2가 있으면 원본 문장, 글 자체 인용 `it:`과 함께), 영상 `vd:{item_id}@{sec}`, 레포 `rp:{owner/name}`. export sources는 `og:` 근거의 원본 URL을 `origin`으로 보존(PR #9 리뷰 R10)
- 영상은 digest의 거른 slide_only_facts(P4-1 뒤 claim만), timeline, summary 문장. 레포는 oneliner, signal, stars_this_week, release
- **토픽당 입력 상한 약 8,000토큰**(`brief.yaml`). 넘치면 관련성 → 채널 다양성 → 출처당 균형 순으로 고르고, 뺀 근거 id는 clusters.body_json과 실행 요약 `evidence.truncated_topics`에 기록

**표기 정규화 v0**: 원문은 바꾸지 않는다(인용 대조가 원문 기준). 분석 뒤 별칭 표(aliases)를 만들어 묶기 신호·작성자 입력·코드 자동 수정에 쓴다.
| 별칭 후보 | status |
|---|---|
| keywords.yaml의 별칭 | approved |
| 표기 차이만(대소문자·띄어쓰기·하이픈·점) | **자동 approved** |
| 이름 속 숫자·버전·크기가 다름(Qwen3 ↔ Qwen3.5, GPT-5 ↔ GPT-5 mini) | **후보로도 만들지 않음**(rapidfuzz 점수와 무관) |
| 한글 음차·약어(클로드 ↔ Claude) | candidate: 묶기 신호로만 쓰고 정본 치환은 하지 않음. decide 또는 편집장이 확인하면 approved |
| 영상 name_pairs(잘못 들은 말 ↔ 화면 표기) | **그 영상 안에서만 교정**, 전역 별칭으로 올리지 않음 |
- 후보 원천: keywords.yaml 별칭 + 카드 entities 간 rapidfuzz + 영상 name_pairs. 애매한 것만 decide
- aliases 칸: canonical, alias, keyword_id, reason, evidence_json(항목 id), origin(normalizer/editor), status, seen, run_id
- 성공 기준: 정규화 정확도 90%, 서로 다른 대상 오병합 0

### 5.4 묶기와 과거 대조 (3단계) — 끝에서 멈춤
- 시점: **주 1회, weekly 시작 때 한 번.** 재실행·재시도 결과도 지우지 않고 run_id로 쌓으며, 그 주 현재판은 `weeks.current_run_id`
- 묶음 구성원 키 `member` = `it:{item_id}` / `vd:{video_id}` / `rp:{full_name}`. `item_same_as`(같은 URL)는 처음부터 하나
- 임베딩: 기존 `item_embeddings` 재사용. 영상은 digest 요약, 레포는 oneliner + description을 새로 임베딩(같은 Qwen3-Embedding-0.6B)
- 규칙
  - 같은 채널 쌍: 유사도 **높음 구간은 자동**, **경계 구간은 decide**
  - 채널을 넘는 쌍: **키워드·별칭을 공유할 때만 후보**, 후보는 전부 decide(자동 묶음 없음)
  - 문턱값은 **임시값으로 시작**(`brief.yaml`: 높음 0.80 / 경계 0.65), **멈춤 지점에서 분포를 보고 확정**
  - 사슬 묶임 방지: **평균 연결**(새 항목은 묶음 전체와의 평균 유사도로 판단). 묶음 최대 12개, 넘으면 리포트 표시
  - decide: 주당 상한 60회(넘으면 유사도 높은 순), confidence 0.6 미만은 묶지 않음. 판정은 모두 cluster_pairs에
  - 오병합 0이 우선이다. 문턱값을 낮춰 억지로 묶지 않는다
- **레포만 있는 묶음은 토픽 후보가 아니다**: 홈의 트렌딩 레포 목록에만 들어간다. 글·영상 묶음에 붙은 레포는 그 토픽 안에도
- **항목 1개짜리 묶음도 토픽 후보**(글·영상이면). 근거 1건이라는 것만으로 빼지 않는다(편집장 선별이 판단)
- 과거 대조: 지난 주들의 현재판 토픽(제목 + 요약) 임베딩(topic_embeddings)과 비교해 상위 3개를 후보 관계로 저장(new/follow_up/duplicate 후보). 확정은 편집장 선별. 토픽 수가 적어 벡터 DB 없이 전부 비교. **첫 실행(W41)은 지난 토픽이 없으므로 전부 new**, W42가 W41과 대조된다
- **묶기 리포트** `reports/S5_brief/cluster_<week>.md`(W41 먼저, W42는 주가 끝난 뒤 추가)
  - 묶음 수, 채널 조합 분포, 2채널 이상·3채널 묶음 수, **1개짜리 묶음 비율**
  - 묶음별 항목 제목 목록(묶인 이유: joined_by, 유사도)
  - decide 판정 표(쌍, 유사도, answer, confidence, reason)
  - **경계 근처 상위 20쌍**(묶였어야 할 것 같은 쌍)과 유사도 분포 히스토그램 → 문턱값 근거
  - 의심 병합(같은 회사 다른 제품, 숫자 다른 이름이 한 묶음)
  - 과거 대조 후보, 별칭 표(자동 승인·후보)
  - **편집장 입력 후보 수**(관련성 우선 점수 상위 20, 5.5)와 관심 주제 후보 수 → 토픽 수 상한 확정 근거
- **멈춤**: 리포트와 코드를 커밋·푸시하고, 진행 블록에 `[사용자 필요] 묶기 리포트 확인 대기`를 출력한 뒤 멈춘다. 리뷰 세션이 확인해 문턱값·토픽 수 상한을 정하면 사용자가 "진행"과 함께 값을 준다. 받은 값은 `brief.yaml`에 넣고 리포트에 기록

### 5.5 편집장 선별 (4단계, `roles/editor_select.md`, LLM 1회)
- 역할 md: **이 묶음의 초안을 출발점으로**(코드 세션이 고도화, E1). 근거는 `s5_role_notes.md` 2장
- 입력 조립
  - 후보는 점수 상위 20개까지. **점수는 관련성이 먼저**(묶음 안 항목의 relevance 최댓값·개수), 채널 수·근거 수·키워드 추세는 같은 관련성 안에서의 순서만(근거 1건인 개발 경험담이 여기서 잘리지 않게)
  - **입력 순서는 cluster_id 고정**(위치 편향 방지, 점수순으로 넣지 않음)
  - 후보마다 `<document id="c{cluster_id}">`: 임시 이름, 항목(근거 키, 채널, 제목, 한 줄 요약, relevance), 채널별 수, 근거 수, 점수, 과거 대조 후보(지난 토픽 id, 제목, 유사도)
  - recent_topics(지난 4주), keyword_trend, repo_cards(관련 레포), limits(min 4, max 10, lead 1)
- 판단 기준(md에 있음): **넣을지 = 관심 주제 + 읽을 거리**(새 발표·기법·수치, 또는 구체적인 경험과 결과. 근거 1건도 됨) / **순서 = 여러 채널·출처 → 수치 → 키워드 추세** / drop 이유 duplicate · low_relevance(관심 밖, 고객 사례 홍보) · thin(내용이 짧아 페이지가 안 됨) · other
- 출력 BriefingPlan(칸 순서): `decisions[]{cluster_id, reason, action, drop_reason?}`(**모든 후보**) → `splits[]` → `topics[]{cluster_ids, rank, lead, relation{type, topic_id?}, relation_reason, angle, slug_hint}` → `featured_repos[]` → log, attention
- 코드 검증(어기면 오류 메시지로 재시도 2회, 그래도 실패면 대체)
  - 리드 정확히 1, 토픽 수 min~max(**max는 채울 목표가 아님**), rank 1부터 연속
  - cluster_ids·splits는 입력 후보와 그 항목 안에서만(새 항목·다른 후보 항목 금지)
  - relation.topic_id는 그 후보의 과거 대조 후보 안에서만
  - **reason 속 숫자·출처 이름이 입력 값과 맞는지 대조**(S3 editor_plan에서 입력에 없는 사실을 reason에 쓴 문제). 어긋나면 attention + 리포트
- 적용: 토픽 id = `w{주 번호}-{slug}`(예 `w42-jev-local`, slug_hint를 소문자·하이픈으로, 중복이면 `-2`). relation.label은 코드 문장틀("N월 N주차 '제목' 토픽의 후속"). topics·briefing_plans에 저장
- 대체: 점수 순 상위 N(min과 후보 수 중 작은 값), 1위 리드, `briefing_plans.source=fallback`

### 5.6 작성자 (5단계, `roles/writer.md`, LLM 1회, `skills/diagrams.md`)
- 역할 md: 이 묶음의 초안 출발점. 근거는 `writer_draft.md`(29) ①과 `s5_role_notes.md` 3장. 이 문서와 다르면 이 문서 우선
- 입력: plan(rank, angle, relation), 그 토픽의 EvidencePack만(`<document id="근거 id">`), previous(후속 토픽이면 지난 토픽 요약·포인트), aliases(정본 표기)
- **화면 ↔ 칸**(작성자가 토픽 하나 전체를 한 번에 씀)
  - 홈 목록: 제목 = `title`, 요약 1~2문장 = `summary`(목록 전용, 상세 페이지에는 안 나옴)
  - 상세 페이지: 제목 → (코드 배지) → 개요 `overview` → (코드 소스 연결도) → 핵심 포인트 `points` + 붙은 도식 → 핵심 개념 `concepts` → 소스별로 더한 것 `contributions` → (코드 출처)
- 출력 TopicPage(칸 순서: 근거 id 붙은 칸 먼저)

| 칸 | 필수 | 분량·조건 |
|---|---|---|
| points[] {text, refs} | 필수 | 근거 소스 1개면 2~3개, 여러 개면 3~6개. 항목 1~2문장 80자 안팎. 중요도 순. refs 1~3개 |
| numbers[] {anchor, group, title, context, unit, items[{label, value, ref, baseline?, emphasis?}]} | 선택 | 같은 단위 값 3개 이상(또는 전후 비교 + summary에 그 값). **최대 2그룹**, 그룹당 2~6개 |
| events[] {anchor, title, context, flow_is_point?, items[{date, text, ref 또는 topic_id}]} | 선택 | 날짜 다른 사건 3개 이상(또는 2개 + flow_is_point). **최대 1그룹** |
| contributions[] {channel, text, refs} | 선택 | 근거 소스 2개 이상일 때 채널마다 1문장 |
| concepts[] {term, desc} | 선택 | 처음 볼 용어만 0~3개 |
| overview | 필수 | **1문단 2~4문장** |
| summary | 필수 | 1~2문장(최대 3), 첫 문장이 결론(누가, 무엇을, 얼마나) |
| title | 필수 | 명사구 30자 안팎 |
| log, attention | | |

- **도식은 포인트에 붙인다**: 포인트를 중요도 순으로 쓴 뒤, 그림이 나은 포인트에만 numbers·events를 만들고 그 포인트 번호를 `anchor`에. 도식마다 `context` 1~2문장(무엇을 어떤 조건에서 비교했는지, 근거 id 포함). 한 포인트에 도식 하나. **포인트 문장은 그림 없이도 읽히게**(코드가 조건 미달로 그림을 뺄 수 있음). 영상 타임라인은 코드가 영상 근거를 처음 인용한 포인트 아래에 붙인다
- 문체: summary·overview "~다", points·contributions·concepts 명사형. 형광 `==` summary 1, overview 1, 포인트당 최대 1, 페이지 3~4. 고유명사는 원문 언어 그대로(정본 표기), 숫자는 근거 표기 그대로. 슬라이드에서만 나온 수치는 "발표 슬라이드 기준"
- max_tokens 3000, temperature 0.3. 실패 대체: 그 토픽 제외 + attention "작성 실패"

### 5.7 코드 검사 (5단계, 검수자 앞)
29 ②를 기본으로 하고 아래로 바꾼다.

**고칠 수 있는 형식은 코드가 직접 고친다(반려하지 않음)**: 형광 개수 초과(뒤쪽부터 제거), 공백·문장부호, 별칭 표기를 정본으로 치환, 분량 초과 항목의 순서. 고친 것은 `verdicts.autofix_json`과 log.

**반려하는 것**(LLM 비용 0, 라운드에 셈)
- 필수 칸·분량(summary 3문장, overview 4문장, points 개수, 2~3단어짜리 항목 금지)
- 모든 point·number item·event·context의 refs가 존재하고 그 토픽 EvidencePack에 실재
- **수치 대조**: 본문 숫자가 refs 근거(quote·OCR·레포 수치)에 있음. 5.1-9 공통 수치 정규화 후 값 비교(쉼표·%·배·백만/million·한국어 수사). 숫자 추출은 S3 `figures` 규칙(%, 배, 소수, 4자리 이상. 버전·제품명 속 숫자·작은 개수 제외. 예: Orbit-7의 7). **단위 환산이 필요한 경우(토큰당 ↔ 100만 토큰당)는 같은 값으로 보지 않음**
- numbers 그룹 안 단위 하나, title·context 존재, anchor가 실제 포인트 번호이고 중복 없음, 그룹 수 상한
- events 날짜 형식과 근거 존재
- concepts 3개 이하, contributions는 소스 2개 이상일 때만
- 금지어 정규식(모델 md에는 넣지 않음): 해요체, 평가형 마무리("눈에 띈다", "핵심이다", "주목할 만하다", "공통 교훈이다"), 일반론 시작("최근 .* 업계에서는"), 감탄, 질문형 끝, 이모지. 5.1-1의 명사 예외 적용
- 같은 point 중복(문자 유사도 0.8 이상)은 경고

**반려 메시지는 위치·근거·힌트를 구체적으로**: 예 "points[2]의 '15%'가 it:812#q2에 없음. 근거의 값은 1.5%".

**도식 판단 경고**(검수자 입력으로 넘김): 누락 의심(numbers가 비었는데 근거에 같은 단위 값 3개 이상 / events가 비었는데 날짜 다른 사건 3개 이상), 남발 의심(값 2개 그룹에 baseline 없음 / events 2개인데 flow_is_point 없음).

### 5.8 검수자와 수정 루프 (6단계, `roles/critic.md`, `roles/writer_revise.md`)
- critic: 이 묶음의 초안 출발점. 근거는 `s5_role_notes.md` 5장. **같은 모델, 작성자와 다른 새 메시지 목록**, temperature 0
  - 입력: page, refs가 가리키는 **근거 원문만**(요약 칸이 아니라 quote·OCR·레포 필드), angle, code_warnings, round
  - 출력 ReviewVerdict(칸 순서): `atoms[]{loc, fact, evidence_id, supported}` → `fact_support{total, supported}`(코드가 다시 셈) → `issues[]{loc, type, evidence_id, comment, hint}` → status → log, attention
  - 이슈 유형 7개: unsupported / number_mismatch / overclaim / wrong_ref / missing_key / overuse / missing_diagram. 문체·형광은 반려 사유 아님
  - 출력 잘림 감지(max_tokens 도달) → 재시도 1회, 그래도면 대체
- writer_revise: **지적된 칸만 고친 칸을 출력**하고(`changed[]` + 바뀐 칸 값), 코드가 이전 판에 합친다. 지적되지 않은 칸이 바뀌면 코드가 되돌리고 횟수를 기록(되돌림 전 원래 출력도 저장)
- 라운드: 초안(1) → 반려 → 수정(2) → 반려 → 수정(3). 최대 3라운드, 코드 반려도 셈
  - **같은 이슈가 같은 위치에 두 번 남으면 그 이슈는 더 돌리지 않고** 해당 포인트 `check: true`로 확정, 남은 다른 이슈만 다음 라운드
  - 3라운드 뒤 남은 이슈의 포인트는 `check: true`, 토픽 status=checked
  - 모든 라운드의 초안·판정 보관(topic_pages, verdicts)
- 반려 상세는 steps.detail에 `{topic_id, draft, evidence, evidence_ref, fixed}`(예시 JSON runs.steps.detail과 같은 정보)
- 대체: critic 실패 → 코드 검사만 통과한 판 + attention "검수 실패", writer_revise 실패 → 이전 판 유지 + 남은 이슈 check

### 5.9 저장 (마이그레이션 30~33)
원칙: **weekly가 만드는 모든 행에 run_id.** 그 주 현재판은 `weeks.current_run_id` 하나로 가리키고 **지우는 행은 없다**. 저장 방식은 기존과 같음(산출물 JSON 통째 + 조회용 열).
| 번호 | 표 | 주요 칸 | 비고 |
|---|---|---|---|
| 30 | aliases | id, canonical, alias, keyword_id, reason, evidence_json, origin(normalizer/editor), status(candidate/approved/rejected), seen, run_id, updated_at, UNIQUE(canonical, alias) | |
| 31 | weeks | week PK, start_day, end_day, status(open/clustered/selected/written/done/failed), current_run_id | published는 S6 |
| 31 | clusters | id, run_id, week, label, channels_json, n_items, score, body_json(공유 키워드·별칭, 과거 대조 상위 3, 넘친 근거) | 1개짜리 묶음도 |
| 31 | cluster_items | cluster_id, member, channel, joined_by(embed/keyword/alias/decide), sim | |
| 31 | cluster_pairs | run_id, a, b, sim, cross_channel, decided, answer, confidence, step_id | 묶기 리포트·평가 |
| 32 | briefing_plans | id, run_id, week, source(model/fallback), plan_json | 기존 plans(날짜별 계획)와 별개 |
| 32 | topics | (run_id, topic_id) PK, week, cluster_ids_json, rank, lead, relation_type, relation_topic_id, status(selected/passed/checked/failed), final_round, title, summary | |
| 32 | topic_pages | run_id, topic_id, round, page_json, raw_json(되돌림 전), step_id, UNIQUE(run_id, topic_id, round) | |
| 32 | verdicts | run_id, topic_id, round, checker(code/critic), status(pass/reject), issues_json, autofix_json, step_id | |
| 32 | topic_evidence | run_id, topic_id, evidence_id, member, field(point/number/event/context/contribution), idx | 최종판 기준. 출처 목록·평가 추적·다음 주 과거 대조·11주차 RAG가 씀 |
| 33 | topic_embeddings | topic_id, run_id, model, dim, vec, text_hash | 과거 대조 |
| 33 | runs 칸 추가 | week, summary_json | 5.10 |
- 마이그레이션 대역 S5 = 30~39(COMMON 9장)
- 재실행: weekly를 다시 돌리면 새 run_id, `weeks.current_run_id` 갱신, 이전 run 행은 남음. 단계별 재실행은 `--from-step`

### 5.10 weekly 명령과 실행 요약 (7단계)
- CLI(`cli_brief.py`의 `register(sub)`): `weekly --week W [--from-step cluster|select|write|review]`, 단계별 `cluster|select|write|review --week W [--topic T]`
- 단계마다 steps에 기록(role, text, attention). 화면 실행 기록의 문장이 되므로 명사형 한 줄(예: "후보 12개 중 8개 선정, 후속 2", "1차 반려: 수치 단위 불일치")
- **실행 요약**: weekly 끝에 표들에서 계산한 파생값을 `runs.summary_json`에 한 번 저장(틀리면 다시 계산 가능)
```json
{
  "week": "2026-W42", "model": "qwen/qwen3.8-27b", "status": "ok|partial|failed",
  "evidence": {"items": {"text": 0, "video": 0, "github": 0}, "excluded": {"no_card": 0, "no_digest": 0, "irrelevant_repo": 0}, "truncated_topics": 0},
  "aliases": {"candidates": 0, "auto_approved": 0, "decide_calls": 0},
  "cluster": {"clusters": 0, "single_item": 0, "multi_channel": 0, "three_channel": 0, "decide_calls": 0, "decide_merged": 0,
              "past": {"new": 0, "follow_up": 0, "duplicate": 0}},
  "select": {"candidates": 0, "selected": 0, "merges": 0, "splits": 0, "drops": {"duplicate": 0, "low_relevance": 0, "thin": 0, "other": 0}},
  "write": {"topics": 0, "failed": 0},
  "review": {"rounds": {"1": 0, "2": 0, "3": 0}, "code_rejects": 0, "critic_rejects": 0, "autofixes": 0, "reverts": 0,
             "issues": {"unsupported": 0, "number_mismatch": 0, "overclaim": 0, "missing_key": 0, "wrong_ref": 0, "overuse": 0, "missing_diagram": 0},
             "check_points": 0},
  "cost_usd": {"decide": 0, "editor_select": 0, "writer": 0, "writer_revise": 0, "critic": 0, "total": 0},
  "duration_sec": {"evidence": 0, "cluster": 0, "select": 0, "write_review": 0, "total": 0}
}
```
- 화면용으로만 쓰이는 값(예시 JSON의 cross_checked 등)은 저장하지 않는다(S6에서 계산)
- 실행 시간 목표 weekly 1시간 30분 이내. OpenRouter 기준 실측 + 로컬 추정(qwen3.8-27b q4 decode 약 8 tok/s, 첫 토큰 15.6k 입력 약 101초, 문서 47 실측)을 리포트에

### 5.11 config/brief.yaml (이 묶음의 초안, 스펙 소유)
토픽 수, 문턱값, 상한, 라운드 같은 조정값은 모두 여기. 코드에 박지 않는다. 멈춤 지점 뒤 바꾼 값은 리포트에 기록.

## 6. 관문 A (`scripts/verify_s5.sh`)
| # | 항목 |
|---|---|
| A1 | 회귀: verify_s0~s4 전부 PASS |
| A2 | ruff, pytest(`--extra video --extra embed`, 건너뜀 0) |
| A3 | check-config: brief.yaml, budget S5, 역할 md 5개(decide, editor_select, writer, writer_revise, critic) 앞부분·섹션 순서(COMMON 6.1) |
| A4 | 공통 수정 5.1 항목별 테스트(명사 예외 오탐 0, ImageError 계열, 중첩 ImageFile 거부, ClassVar 선언) |
| A5 | 근거 목록: 자격 규칙(카드 없는 글·digest 없는 영상·관련 없는 레포 제외), 근거 id 형식, 입력 상한과 뺀 근거 기록 |
| A6 | 정규화: 표기 차이만 자동 승인, **숫자·버전 다른 쌍은 후보 아님**, name_pairs 전역 미반영 |
| A7 | 묶기: 채널 넘는 묶음은 키워드·별칭 공유 필수, confidence 0.6 미만 미병합, 평균 연결(사슬 예제), 레포만 묶음은 토픽 후보 아님, 1개짜리 묶음은 후보 |
| A8 | 선별 검증: 리드 1, 개수 범위, 범위 밖 합치기·나누기 거부, relation은 과거 대조 후보 안, 입력 순서 cluster_id 고정, reason 값 대조 |
| A9 | 코드 검사(모의 출력): 수치 대조(단위 환산 미허용 포함), anchor 검사, 도식 상한, 금지어, 자동 수정(형광 초과 등)은 반려 아님 |
| A10 | 라운드: 상한 3, 코드 반려도 셈, 같은 이슈 2회면 check 확정, 지적 안 된 칸 되돌리기 |
| A11 | 저장: 마이그레이션 30~33 대역, 재실행 시 이전 run 행 보존·current_run_id 갱신, topic_evidence가 최종판 refs와 일치 |
| A12 | 실행 요약 JSON 형식(5.10)과 표에서 다시 계산한 값 일치 |
| A13 | 출력 계약 참고 대응: 저장값만으로 예시 JSON 토픽의 칸(title, summary, overview, points, numbers→bars, events, concepts, contributions, sources, channels, has_check, relation)을 만들 수 있음을 테스트 하나로(export 구현 아님, 매핑 함수 초안) |
| A14 | 문서: README 갱신, S5_report 체크리스트, reports/eval JSON 역할별 1개 |

## 7. 관문 B (W42 + W41 실제 실행) — 기준 그대로, 라벨은 잠정
| 항목 | 채점 | 문턱값 |
|---|---|---|
| 근거 충실성 | judge가 원자 사실로 쪼개 지지/비지지 → 코드가 지지율 | **모든 토픽 100%** |
| 핵심 포착 | "summary 첫 문장이 결론이고 angle의 핵심이 첫 point에 있나?" | 통과율 90% |
| 군더더기 없음 | "조건에 맞지 않는데 채운 칸이나 겹치는 point가 없나? 개요가 포인트를 되풀이하지 않나?" | 90% |
| 읽기 쉬움 | "처음 읽는 사람이 3분 안에 무슨 일인지, 왜 중요한지, 무엇을 열어 볼지 알 수 있나? 도식마다 context가 맥락을 설명하나?" | 90% |
| 문체 | 코드 정규식 + "번역투나 어색한 문장이 없나?" | 위반 0, 90% |
| 표현 선택 | 도식 판단 라벨 대비 누락률·남발률(코드 계산) | 남발 0, 누락 20개 중 1 이하 |
| 묶기 | 라벨 대비 오병합 | **0**, 2채널 이상 토픽 비율 기록 |
| 정규화 | 별칭 표 라벨 대비 | 정확도 90%, 오병합 0 |
| 선별 | 코드 검증 통과, drop 이유 라벨 일치 | 검증 100%, 일치 80% |
| 검수 | critic 판정 vs 라벨(반려해야 할 것을 반려, 깨끗한 것을 통과), 반려 후 통과율 | 일치 80% |
| decide | 쌍 라벨 대비 정확도 | 오병합 0 |

- **judge 채점표에 처음부터 실패 예시를 넣는다**: 인용 밖 서술, 단위 왜곡("100만 토큰당" ↔ "토큰당"), 방향 반전, 입력에 없는 reason, 부분 확인. judge 입력에는 근거 원문을 준다(S2~S4에서 judge가 이 유형을 모두 통과시켰다, `s5_role_notes.md` 5·6장)
- **라벨**: 토픽 20개(W42 + W41, 모자라면 W40 추가 실행)에 도식 판단 + 작성·검수 통과/실패 + 한 줄 비평을 리뷰 세션 opus-5.5가 한 번에 단다(D1-3). 라벨 파일 `eval/labels/writer.csv`·`critic.csv`·`diagram_labels.json`·`decide.csv`·`aliases.csv`를 코드가 만들어 두고(빈칸), PR 리뷰 때 채워진다. 그 전 judge 결과는 "잠정"
- judge 일치율은 같은 라벨로 1회
- 픽스처: writer·critic은 비율 지표라 20(E3 예외, 깨끗한 초안 다수 포함), decide·editor_select·writer_revise는 8~10(보통/빈칸/함정/인젝션). 구성은 `s5_role_notes.md` 역할별 "픽스처"
- 결과 `reports/S5_quality.md`: 항목별 통과율, 가장 나쁜 사례 3개, 반복 기록(E1), 점수 병기(원래 / 통과 판정 / enforce 후)

## 8. 예산
- **S5 3.00달러**(`budget.yaml`). 판단은 **키 기준 사용액**(P1 확인: 키 기준 $2.46 vs 기록 합 $1.82, 큰 쪽)
- 대략 배분: 재료 재생성 약 0.8(W41·W42 item_card, digest 요약, W42 레포·영상), 묶기·선별·작성·검수 개발 반복 약 0.8, 관문 B 두 주 실행 약 0.4, judge 채점 약 0.3, 예비 0.7
- 개발은 작은 샘플(토픽 2~3개)로, 두 주 전체 실행은 끝에 1회(E2)

## 9. 검증 산출물 (`reports/S5_brief/`, COMMON 10장)
묶기 리포트(주별), 토픽별 라운드 표(초안 → 판정 → 수정, 되돌림 포함), 코드 검사 위반·자동 수정 통계, 도식 판단 표, 별칭 표, 선별 결정 표(후보·action·reason·입력 대조 결과), 실행 요약 JSON, 실행 시간(OpenRouter 실측 + 로컬 추정), 사용액. 평가 JSON은 역할별 최신 1개(E10). 재현 명령 포함

## 10. 완료 시 넘길 것
- PR(공통 코어 수정 목록, 마이그레이션 번호, 멈춤 지점에서 받은 값)
- `reports/S5_report.md`(COMMON 7장), `reports/S5_quality.md`
- README 갱신(현재 상태, 기능·역할 표, 성과 표 S5 행, 로드맵 체크)
- S6 제안: export 매핑에서 걸린 것(도식 anchor 배치, 주차 표기 W→w, 출처 번호), 실행 시간 실측, 임시 수집 예약 제거, P4 4·5, 발견한 화면 칸 문제

## 11. 출력 계약 참고 (`docs/reference/trendsit-example.json`)
- 예시 JSON은 **화면 디자인을 위해 만든 예시**다. 스키마는 이 스펙의 필요로 정했고 예시는 참고만 한다. 화면에 필요한데 S5 데이터로 못 만드는 칸은 S6에서 화면 쪽을 고친다
- 대응(참고): topics의 id·week·rank·lead·relation ← 선별, title·summary·overview·points·concepts·contributions ← 작성자, diagrams(bars·events·video) ← numbers·events·영상 refs(**S5는 anchor로 포인트에 붙임, 예시는 페이지 아래 묶음 → S6 화면이 맞춤**), sources·channels ← topic_evidence, has_check ← 검수. repos ← repo_trending + RepoCard + featured_repos. runs ← runs.summary_json + steps. keywords.candidates ← aliases(by ↔ origin, evidence는 항목 id → export가 제목·URL로)
- 주차 표기: 내부는 CLI 표기 `2026-W42`, 예시는 `2026-w42`(export가 변환)

## 부록. 결정 출처 (설계 프로젝트 문서 64 부록 C, 2026-10-09)
C-0 예시 JSON은 참고 / C-1 실행 요약 / C-2 토픽↔항목 연결 저장 / C-3 별칭 칸 / C-4 주차 경계·근거 자격·레포만 묶음·수치 대조·고유명사·입력 상한 / C-5 루프 방지(자동 수정, 같은 이슈 2회 check) / C-6 1개짜리 묶음 / C-7 P1 분리 / C-8 DB 표 / C-9 묶기·정규화 기준 / C-10 역할 초안과 근거 넘기기 / C-11 README 갱신 / C-12 zip 전달·예산·공통 수정·COMMON / C-13 선별 기준(넣을지와 순서 분리) / C-14 화면 대응·도식 anchor / C-15 P1 결과·시연 두 주(W42 + W41)·토픽 수 4~10
