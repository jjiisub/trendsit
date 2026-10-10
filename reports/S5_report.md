# S5 리포트: 주간 브리핑

> 한 줄 요약: `trendsit weekly --week W`가 한 주의 글·영상·레포를 묶고(과거 대조 포함) 편집장이 토픽을 고르고 작성자 ⇄ 코드 검사·검수자가 근거 id 달린 토픽 페이지를 만들어 칠판에 run_id로 쌓는다. PR #9 리뷰 두 차례(R1~R18, F1~F12, C-20~C-22) 반영 뒤 W40·W41 20토픽 작성 실패 0. 2차 라벨(이전 출력) 통과 12/20, 바뀐 10토픽 재실행 뒤 judge(잠정) 원자 사실 17/20 토픽 100%(미달), Q1~Q4 90~100%, 코드 문체 위반 0.

## 진행 체크리스트
- [x] 0 환경 점검·정리(5.0) + handoff 묶음 커밋 + README 맞춤
- [x] 1 공통 수정(5.1) → 재료 품질 개선(P4 1·2·3·6·7) → 대상 두 주 재료 생성·재생성(5.2) — W41(10/5~10/9)까지. W42는 10/19 이후
- [x] 2 근거 목록(EvidencePack) + 표기 정규화 v0(5.3)
- [x] 3 묶기 + 과거 대조 → 묶기 리포트(5.4) — **멈춤: 리뷰 확인 대기**(W41 리포트)
- [x] 4 편집장 선별(5.5)
- [x] 5 작성자 + 코드 검사(5.6, 5.7)
- [x] 6 검수자 + writer_revise 루프(5.8)
- [x] 7 weekly + 저장 + 실행 요약(5.9, 5.10)
- [x] 8 관문 B(**W40 + W41**, 멈춤 지점 결정 7), 리포트, PR
- [x] 9 PR #9 리뷰 반영(R1~R18, C-20, C-21 수정, judge 보정) → W40·W41 재실행
- [x] 10 반영 확인 리뷰(2차) 반영(F1~F12, C-22) → 10토픽 재실행 → **반영 확인 리뷰 대기**

## 0단계: 환경 점검·정리 (2026-10-09 13:30, LLM 0원)

### 준비물 확인표(E6)
| 준비물 | 확인 | 결과 |
|---|---|---|
| main `44921dc` 이후 + 이 묶음 | `git log` | main `44921dc` 위에 `s5-brief`, 첫 커밋 `docs(s5): handoff 묶음` |
| 작업 폴더가 main | `git branch --show-current` | `p1-env`에서 main으로 옮긴 뒤 `s5-brief`. 로컬 `p1-env` 삭제 |
| 통합 DB와 주차별 재료 | `items --week 2026-W41`·`W42` | W41 글 171(관련성·카드 미실행) + 릴리스 36, 영상 15(digest 6), 트렌딩 11(repo_cards 7). W42는 0건(10/12부터) |
| 매일 수집 임시 예약 | `launchctl print …collect-temp` | 등록됨, runs 2, last exit 0. 첫 정기 실행은 10/10 02:00이라 정기 실행 로그는 아직 없음 |
| OpenRouter 키, GitHub 토큰 | `cost --spec S5` | 키 조회 정상. 단계(mvp) 키 기준 $2.46 / 20, limit_remaining $47.05 |
| `--extra video --extra embed` | `uv sync`, pytest | 건너뜀 0. 실패 5건(아래) |
| budget S5 3.00, `brief.yaml` | `check-config` | 설정 통과. 역할 md 5개는 출력 클래스가 아직 없어 FAIL(2~6단계에서 생김) |

pytest 실패 5건(0단계 시점, 모두 handoff 묶음이 원인): 새 역할 md 5개의 출력 클래스 없음(4건: `test_real_config_passes`, `test_role_with_unknown_alias_fails`, `test_all_role_files_pass_lint`, `test_lint_allows_extra_sections_and_counts_examples_and_bold`), `keywords.yaml`에 제외어 4개가 더해져 S2 초안(`keywords_next.yaml`)과 달라짐(`test_real_keywords_file_is_the_handoff_draft`). 1단계 공통 수정에서 처리.

### 원격 브랜치 정리
- `git branch -r --merged origin/main` 기준 병합된 7개(s0-foundation, docs-readme-skeleton, s1-collect, s2-0-base, s2-s3, s4-video, p1-env)는 삭제함. 자동 모드가 `push --delete`를 막아 사용자가 직접 실행
- **`docs-s2s4-handoff`는 남김**: PR #4가 스쿼시 병합(3b024bf)이라 git 기준으로는 병합으로 나오지 않는다. 스펙 규칙(병합 안 된 것은 지우지 말고 보고)대로 두었다. 내용은 main에 있으므로 지워도 된다
- 10/9 16:06 사용자가 `docs-s2s4-handoff`도 삭제. `git fetch --prune` 뒤 남은 원격 브랜치는 main, s5-brief뿐

### 임시 수집 로그
| 실행 | 소스 성공 | 실패 | 트렌딩 |
|---|---|---|---|
| 10/9 12:25(kickstart) | 글 6, 트렌딩, 릴리스 | techbridge RSS 404 | W41 11개 갱신 |
| 10/9 12:26(kickstart, 재시도 포함) | 같음 | techbridge RSS 404(재시도도 404) | W41 11개 |
| 10/9 13:36(수동 `--source techbridge`, 10/5~10/9) | techbridge RSS 정상 | - | - |

- 10/10 이후 정기 실행 로그는 아직 없다(오늘 10/9). W41 마지막 트렌딩은 10/11(일) 02:00 수집분, W42는 10/18(일) 수집분 이후
- **유튜브 RSS 404 대응**: RSS가 간헐적으로 404를 낸다(P1 12:20 이후, 13:36에는 정상). `collect`에서 RSS가 실패하면 `channel_listing` 백필이 있는 소스는 yt-dlp 채널 목록으로 대체하고, 둘 다 실패하면 소스 실패로 기록한다(`trendsit/collect/youtube.py`, 테스트 `tests/test_s5_env.py`). W41 영상은 13:36 수집에서 이미 다 있어(기존 13, 신규 0) 백필할 것이 없었다

### 결정한 것
- 일정: W41은 10/11, W42는 10/18에 끝난다. 3단계 묶기 리포트는 우선 10/5~10/9 재료로 W41을 만들고, 주가 끝난 뒤 다시 돌려 갱신한다

## 1단계: 공통 수정 → 재료 품질 개선 → 재료 생성

### 공통 수정(5.1, 커밋 `4a81644`, PR 설명 맨 위 "공통 코어 수정")
| # | 한 것 |
|---|---|
| 1 | 문체 정규식을 `trendsit/core/style.py` 한 곳으로(`HAEYO`, `NOUN_YO`, `SENTENCE_END`, `ends_as_sentence`, `is_haeyo`). `graders_video`의 자체 `SENTENCE_END` 삭제, 공통 규칙 + '요'로 끝나는 명사 예외를 같이 씀. S5 코드 검사도 이 모듈을 쓴다 |
| 2 | `write_quality`의 입력 축약: 중첩 입력(목록·객체)은 JSON 앞 500자(`NESTED_BRIEF`) |
| 3 | 예산 기준값 파일을 `~/.config/trendsit/budget_state.json`으로(`core/context.budget_state_path`). 처음 열 때 `data/budget_state.json`(10/7 기준값 $0.48331)을 그대로 복사. 테스트처럼 data 폴더를 따로 주면 그 안 |
| 4 | `VideoSummary.ENFORCED_FIELDS = ("name_pairs",)` ClassVar. 채점기는 클래스 값을 등록. S5 새 출력 클래스도 ClassVar(`ReviewVerdict.ENFORCED_FIELDS`) |
| 5 | judge 대상(원래 출력이 코드 채점 실패면 enforce 후 전체)과 통과 판정(코드 소유 칸만 enforce 후)의 차이를 `docs/DEVELOPMENT.md`와 품질 리포트 머리말에 |
| 6 | `ImageError(LLMError)`. `LLMError`는 `core/errors.py`로 옮김(llm ↔ images 순환 방지, `core.llm.LLMError`는 그대로 쓸 수 있음). `check_roles`가 최상위가 아닌 ImageFile 칸(목록 안, 하위 모델 안)을 거부 |
| 7 | `reports/eval/` 역할별 최신 1개: 삭제는 자동 모드가 막아 사용자가 실행(3단계 끝 절). 34개 삭제. 남길 12개 = 역할·모델별 최신 전체 실행 + 라벨 파일이 가리키는 실행(일치율 재현용) |
| 8 | (선택) 하지 않음 |
| 9 | 수치 정규화를 `core/numbers.py`로(S4 `video/align.py`에서 옮김). S4 대조와 S5 코드 검사가 같이 씀 |
| 10 | 검토 결과 그대로 둠: video_summary 입력의 판독 문서 id가 `vd:{item_id}@{sec}`라 메시지에 item_id가 들어가고, 근거 id 형식은 바꾸지 않으므로 캐시 키에서 뺄 수 없다. 이번에 한 번 재생성 |

### 재료 품질 개선(P4, 커밋 `66f6ffa`)
| # | 한 것 | 확인 |
|---|---|---|
| P4-1 | `SlideNumber.kind`(claim/ui/example/version/axis, 같은 호출). 코드: claim만 slide_only 후보(나머지는 excluded `kind=…`), 프레임 수치 10개 이상이면 `dense`로 뒤로, 같은 대상을 발화가 다른 값으로 말하면 `spoken_value`(교정 후보, 예 'Sweebench Pro 88%' ↔ 화면 80.3%). 저장된 S4 판독(kind 없음)은 claim으로 읽음. `video_slide.md`: 해상도 문구 768 → 1024(설정 `frames_res`), `style_ko` includes 뺌(화면 표기 그대로 옮기는 역할) | `tests/test_s5_material.py` |
| P4-2 | item_card: summary·claims는 quotes 안만(이유 + 함정 예시), 단위·방향 그대로. judge 채점표 Q1에 실패 예시 5종(인용 밖 고유명사, 결과 서술, 단위 왜곡, 방향 반전, 지어낸 인과) | 아래 전후 비교 |
| P4-3 | item_card: 고객 사례 홍보 글 relevance low 규칙 + 함정 예시 | 아래 전후 비교 |
| P4-6 | video_summary Q2를 구간 라벨 기준으로(그 초 30초 전 ~ 다음 항목 초, 두 주제를 묶으면 둘 다 구간 안). 근거 상한 초과는 enforce가 자르는 코드 소유 규칙(`fix(owned=True)`)이라 통과 판정 실패가 아니고 모델 일치율(key_points)로 기록 | `test_evidence_cap_is_code_owned_not_a_failure` |
| P4-7 | text_analyst: 부분 확인 내림을 근거 없는 판정 문턱값(0~1건)에 포함. 저장된 맥 평가(195542)는 이제 5건으로 미달 | `test_r3_n2_regrade_saved_text_analyst` |

#### item_card 전후(E1, 기존 픽스처 21건, 바꾼 것은 md 하나)
- 가설: "quotes 밖 내용 금지 + 함정 예시"를 넣으면 요약·주장의 인용 밖 서술이 줄고, 고객 사례 2건(Basis, Jump Trading)이 low가 된다
- 결과(이전 `195536` → 이후 `140559`, 프롬프트 `0792946e0c88`)
  - 코드 채점 20/21 → 20/21(오탐 수정 뒤). 남은 1건 kakapo-party는 "15초"가 인용 밖이고 이전에도 같은 이유로 실패
  - 인용 밖 영문 고유명사(코드로 센 대리 지표) 24 → 20. METR(34873)은 그대로 남음
  - 고객 사례: Basis high → low, Jump Trading high 그대로. relevance가 내려간 것 4건(215688, 215986, 34739, john-gruber)
  - deepmind는 단위 왜곡("입력 토큰당 $2")이 "100만 개당 $2"로 바로잡혔다. 그런데 채점기가 "100만"의 100을 인용 밖 숫자로 잡았다(인용은 "per million"). 채점기 오탐을 버그로 고침(`scaled_in`: 한국어 큰 단위가 붙은 수를 값으로 비교). 버그 수정 뒤 재채점은 횟수에 세지 않음
  - judge Q1 17/19(judge는 너그럽다). 2차 라벨은 이전 출력에 달린 것이라 새 출력과 일치율을 잴 수 없음
- 판단: 방향은 맞지만 Jump Trading과 METR이 같은 출력으로 남았다. E1에 따라 item_card 쪽 반복은 여기서 끝낸다. 고객 사례의 두 번째 거름망은 편집장 선별(low_relevance)이다
- 사용액 $0.089

#### 영상 digest 11개 재판독(P4-1) + 요약 재생성
- 첫 실행(14:22~14:26)은 판독 0장: `data/media/<id>/media_result.json`의 work_dir가 P1에서 지운 worktree(`../trendsit-s4`) 절대 경로라 프레임을 못 찾았고, 판독 없이 요약만 다시 만들어 digest를 덮어썼다. `video run --reuse-media`가 작업 폴더를 지금 위치로 바꿔 읽도록 고친 뒤(`cli_video.py`) 다시 실행해 복구했다
- 결과: whisper+slides 8편 판독 159장, 슬라이드 전용 수치 124 → 74개. kind로 뺀 것은 example 17, version 17, ui 6개이고, 이름에 붙은 버전 1개는 기존 규칙으로 뺐다. 31XD1O74pks는 표·대시보드 프레임 수치 31개가 dense로 뒤로 갔다
- 교정 후보(spoken_value): -TeOEuplMrQ에서 SWE-Bench Pro 화면 80.3% ↔ 발화 88%를 잡았다(S4 리포트 사례). 같은 영상 29.3% ↔ 88%, 31XD1O74pks의 $ 값들처럼 가까운 다른 숫자를 고른 오탐도 있다. 교정 후보는 묶기·작성에 쓰지 않는 기록 칸이라 그대로 두고 S6 제안으로 넘긴다(발화 쪽 숫자 위치를 이름 바로 뒤로 좁히기)

#### W41 재료 생성(10/5~10/9 수집분, 스크립트 순서 = nightly 흐름)
| 단계 | 결과 | 사용액 |
|---|---|---|
| rematch(제외어 4개 반영) | 222건 중 22건 판정 바뀜(pass→filtered 11, filtered→pass 2) | 0 |
| filter(MPS) | 186건 keep 156 / drop 30(태양광 11 등), 같은 URL 1 | 0 |
| summarize(item_card, 새 md) | 141건(대체 1), relevance high 63 / mid 51 / low 27, 원본 확인 필요 77, 잘린 인용 6.8% | $0.31 |
| plan run --day 2026-10-09 | 글 5, 영상 4, 레포 10(영상 1편 예산 초과로 잘림) | 약 $0.003 |
| deep text | 5건, 원본 확보 4(깊이 2), confirmed 9 / differs 1 / not_found 37 | 약 $0.02 |
| video run(계획 큐) | 새 영상 2편 whisper(6YuIp-MwPv4, D7q8fa589FY). 큐에 있던 31XD1O74pks·oeL0uP-NO-U는 이미 whisper+slides digest가 있는데 큐는 whisper라 실행을 멈추고 뺐다(아래 결정) | 약 $0.01 |
| 레포 분석가 | 다시 돌리지 않음(스펙). W41 repo_cards 7 | 0 |

- 1단계 S5 사용액: 키 기준 약 $0.64(평가·재판독 포함)

## 2단계: 근거 목록과 표기 정규화 v0
- `trendsit/brief/evidence.py`: 근거 자격(카드 있는 글, v2에 원본이 있으면 og: 근거를 앞에, digest 있는 영상, relevant RepoCard), 같은 URL로 묶인 글은 기준 항목 하나, 근거 id는 CONTRACTS 그대로. `cap_pack`: 토픽당 입력 상한(약 8,000토큰) 넘으면 관련성 → 채널 다양성 → 출처 균형(구성원마다 근거를 돌려 담기) 순서, 뺀 근거 id 반환
- `trendsit/brief/aliases.py`: keywords.yaml 별칭(approved, keyword_id 붙음, 같은 대상 신호로는 쓰지 않음), 표기 차이만 → 자동 approved, 숫자·버전·크기 다른 이름은 후보로도 안 만듦, rapidfuzz 90 이상 → candidate(묶기 신호, decide가 같다고 하면 approved, 주당 10회), 영상 name_pairs는 그 영상 안(Member.corrections)만
- 마이그레이션 30~33(aliases, weeks, clusters, cluster_items, cluster_pairs, member_embeddings, briefing_plans, topics, topic_pages, verdicts, topic_evidence, topic_embeddings, runs.week·summary_json). member_embeddings는 스펙 표에 없지만 영상·레포 임베딩을 다시 계산하지 않으려고 31에 더했다
- S5 역할 스키마 5개(`core/artifacts_brief.py`)는 check-config를 통과시키려고 미리 정의했다(4~6단계에서 enforce·검증을 붙임). 설계 초안 역할 md 5개는 굵게 강조가 여러 개라 lint를 못 넘어, 줄 머리 굵은 소제목을 `###`로 바꾸고 문장 속 굵게는 md마다 하나만 남겼다(내용은 그대로)
- W41 결과: 별칭 자동 승인 5, 후보 0, decide 거절 1. 한글 음차 ↔ 영문(오픈AI ↔ OpenAI, 클로드 ↔ Claude)은 v0에서 잡지 못한다(후보 원천에 음차 규칙 없음)

## 3단계: 묶기 + 과거 대조 (W41, 멈춤 지점)
- 리포트: `reports/S5_brief/cluster_2026-W41.md`, 쌍 목록 `reports/S5_brief/cluster_pairs_2026-W41.csv`, 라벨 시트 `eval/labels/decide.csv`(decide 31쌍)·`eval/labels/aliases.csv`(빈칸, 리뷰 세션이 채움)
- 재현: `uv run --extra embed --extra video python -m trendsit cluster --week 2026-W41 --spec S5`
- 현재판 run `20261009-150737-weekly-24db`(weeks.current_run_id). 첫 실행 `20261009-150423-weekly-c377`도 남아 있다(지우는 행 없음)
- decide 평가(픽스처 10, 실제 W40·W41 글 7쌍 + 합성 3쌍): 10/10, 오병합 0, $0.003
- 첫 실행에서 고친 것(버그, 문턱값과 무관)
  1. 오병합: 서로 다른 레포 openrig ↔ claude-mem이 임베딩 0.81로 자동 묶임 → 레포끼리는 묶지 않음(이름이 다르면 다른 대상, cannot-link)
  2. 영상·레포 구성원 키워드가 비어 있어 채널 넘는 후보 조건(키워드 공유)을 못 채움 → item_keywords·repo_trending.keywords를 읽음
  3. 의심 병합 표시가 회사 ↔ 제품(Google ↔ Pixel 11 Pro)까지 잡음 → 두 이름 모두 숫자가 있을 때만
  4. 리포트에 border 아래 0.55~0.65 이름 공유 쌍 표 추가
- W41 숫자: 구성원 156(글 141, 영상 8, 레포 7), 묶음 144(토픽 후보 138, 레포만 6), 2채널 이상 1, 3채널 0, 1개짜리 92%, decide 31회(같다 10). 묶기 단계 $0.011, 40초

### 리뷰 세션이 정할 것(멈춤 지점)
1. **문턱값**: 같은 채널 쌍 유사도가 낮게 몰려 있다(0.65 이상 34쌍뿐). 같은 발표의 영문 원문 ↔ 한국어 기사 쌍은 0.66~0.80에 있었고 decide가 거의 맞게 묶었다(6쌍). 그런데 EmbeddingGemma 2(Simon Willison 글)는 0.61·0.63으로 border 아래라 따로 남았다. border를 0.60으로 낮추면 decide 후보가 늘지만, 0.60~0.65 이름 공유 쌍 대부분은 같은 회사의 다른 사건이다(오픈AI 청문회·소송 등). decide 상한 60 안에 들어가는지는 리포트 2장 분포로 계산할 수 있다
2. **채널을 넘는 묶음**: 1개뿐(OpenRig 글 ↔ 레포). 글 본문 임베딩과 영상 요약 임베딩의 유사도가 낮게 나오고(최고 0.67) 같은 대상인 영상·글이 실제로 드물다. 채널 넘는 쌍만 border를 따로 둘지(예 0.55), 이름 공유만으로 decide에 보낼지
3. **토픽 수 상한**: 관심 주제 후보(relevance high 항목 있는 묶음) 63개, 편집장 입력은 점수 상위 20. 7·10·12 중 확정
4. **영상 relevance**: 영상에는 relevance 칸이 없어 high로 두었다(편집장 계획이 처리할 영상으로 고른 것). 그래서 근거 수가 많은 1개짜리 영상 8편이 편집장 입력 상위 20에 들어간다. 영상을 mid로 둘지
5. 과거 대조: W41은 첫 실행이라 지난 토픽 없음(전부 new 후보). W42 때 처음 대조된다

### 결정한 것
- 넓은 1차 그물 키워드(ai-general, ai-industry, dev-practice)는 같은 대상 신호(채널 넘는 후보 조건, 공유 키워드)에서 뺐다. 거의 모든 글이 가진다
- 채널을 넘는 쌍은 brief.yaml 주석대로 "키워드·별칭 공유 + border 이상"일 때 decide
- decide가 다르다고 한 쌍(confidence 0.6 이상)은 cannot-link: 그 두 항목이 든 묶음끼리는 합치지 않는다
- 묶음 점수: (3 − 최고 relevance 등급)×1000 + 그 등급 항목 수×100 + 채널 수×10 + 근거 id 수(최대 9) + 키워드 추세. 관련성이 먼저고 나머지는 같은 관련성 안 순서
- 편집장 계획 큐가 이미 더 깊게 처리한 영상(whisper+slides digest)을 whisper로 다시 처리하려 하면 실행하지 않았다(digest를 얕은 결과로 덮어쓰지 않게). S6 nightly에서 "이미 같은 깊이 이상 digest가 있으면 건너뜀"을 코드로 넣기를 제안

### 자동 모드가 막은 것: 처리 완료(사용자 실행, 2026-10-09)
- `reports/eval/` 정리(5.1-7, E10): 사용자가 34개를 `git rm`, 커밋 `chore(s5): reports/eval 역할별 최신 1개만 남김(E10)`. 남은 것은 남길 목록 12개 + 그 뒤 S5 실행 2개(item_card `140559`, decide `141903`)
- 원격 `docs-s2s4-handoff` 삭제(사용자)

### 멈춤 지점 결정 (2026-10-09 16:06 사용자 "진행", 리뷰 확인 결과)
| # | 결정 | 반영 | 근거·확인 |
|---|---|---|---|
| 1 | auto 0.80 / border 0.65 그대로. 구체적 이름(제품·모델·프로젝트) 공유 + 유사도 0.55 이상이면 같은 채널·다른 채널 모두 decide | `brief.yaml` `cluster.name_border: 0.55`, `cluster.generic_names`(회사·기관 이름, 표기 차이 무시), `Pair.specific_names`·`via`(border/name) | W41: decide 58회 중 name 경로 27회. EmbeddingGemma 2 Simon Willison 글(it:1045, 0.61~0.63)이 name 경로로 묶임 |
| 2 | 묶기 임베딩 body vs card(모든 채널 제목 + 요약) 비교 후 나은 쪽 | `cluster.embed_text: body` | `reports/S5_brief/embed_compare_2026-W41.md`. 라벨 31쌍 일치 30/31 동률, 오병합 0 동률, EmbeddingGemma 3건 모두 모임. card는 5쌍을 decide 없이 임베딩만으로 자동 병합하고 decide 상한에 걸려 11개 후보를 못 부름. body는 58회로 상한 안, 모든 병합을 decide가 확인 → body. 놓친 1쌍(it:1046 ↔ 1048, Mistral Large 4)은 두 방식 모두 decide가 diff |
| 3 | 토픽 수 max 10 | `select.topics.max: 10` | |
| 4 | 영상 relevance = digest 요약의 S2 관련성 점수(0.50 이상 high, 아래 mid). 편집장 입력 상위 20에서 한 채널이 절반을 넘으면 표시 | `evidence.video_relevance_high: 0.50`, `cluster.score_video_relevance`, 묶기 리포트 9장 | |
| 5 | 의심 병합 3건(Mistral Large 3↔4, GPT-5.6↔6, Haiku 4.5↔5.5)은 비교 대상으로 언급된 이전 버전이라 오탐. 표시 규칙 그대로 | `cluster.reviewed_suspicious`, 리포트에 "확인 완료" | |
| 7 | 관문 B 대상 주 W42 + W41 → **W40 + W41**(설계 결정). W42는 10/18 수집 뒤 시연 준비로 weekly만 | W40 글 카드 새 md로 재생성(`summarize --redo`), W40 영상은 기존 digest, W40 weekly(과거 대조 없음) → W41 weekly(W40과 대조) | |
| 8 | W40 트렌딩 재구성(stargazers 기준) | **접음**: GitHub API가 stargazer 시각을 주지 않음(REST 403·404·401, GraphQL FORBIDDEN·빈 목록). W40은 레포 없이 | `reports/S5_brief/trending_reconstructed_2026-W40.md`, `scripts/reconstruct_trending.py` |
| 8-1 | 주마다 브리핑 읽기본 `reports/S5_brief/briefing_<week>.md` | 7단계에서 | |

- decide 라벨 31쌍은 비어 있어(D1-3 리뷰 세션 몫) 비교 기준으로 코드 세션이 잠정 라벨을 달았다(labeler `opus-5.5-code(잠정)`, 30쌍 모델 판정 동의, it:1046↔1048만 same). 리뷰 세션이 덮어쓴다

## 4~7단계: 편집장 선별, 작성자 + 코드 검사, 검수자 ⇄ 수정, weekly·저장·실행 요약
코드: `trendsit/brief/select.py`, `checks.py`, `write.py`, `pipeline.py`, `briefing.py`, `cli_brief.py`(weekly, select, write, review). 테스트: `tests/test_s5_select_checks.py`, `tests/test_s5_weekly.py`(모의 LLM으로 weekly 끝까지).

### 결정한 것
- 선별 재시도: 코드 검증 오류를 `EditorSelectInput.previous_errors`로 넣어 다시 부른다(최대 2회). 그래도 실패면 점수 순 상위 min개 대체 계획(`briefing_plans.source=fallback`)
- 선별 검증에 "select인데 topics에 없음"을 더했다. W41 첫 실행에서 18개를 select하고 10개만 토픽에 넣었다. 상한을 넘겨 못 넣은 후보는 drop(other) + reason "토픽 수 상한"(md에도)
- 나누기(splits): 토픽에 넣을 무리를 groups 첫 번째에 둔다. 그 후보를 토픽에 넣으면 첫 무리만 쓰고, 나머지 무리는 그 주 브리핑에서 빠진다(md에 명시). 나눈 무리마다 따로 토픽을 만들려면 새 cluster id가 필요해 이번에는 하지 않았다
- relation.label: "N월 N주차" = 그 주 월요일이 든 달력 줄(1일이 든 주가 1주차). W40(9/28 월) → "9월 5주차"
- 코드 검사 반려 유형으로 `format`을 더했다(분량, 빈 필수 칸, 금지 표현, 명사형, 도식 칸 규칙). 검수자 7유형과 구분
- 코드가 직접 고치는 것(반려 아님)
  - 형광 개수: 칸별 상한, 페이지 최대 4개, 넘치면 뒤쪽부터 제거
  - 공백·문장부호
  - 승인 별칭을 정본으로 치환
  - contributions: 근거 채널이 2개 이상일 때만, 그 채널만, 채널마다 1문장. 넘치는 것은 뺌
- 명사형 검사(points·contributions·concepts가 문장으로 끝나면 반려)와 "summary·overview는 '~다'"는 스펙 반려 목록에 없지만 넣었다. 관문 B 문체 항목이 "코드 정규식 위반 0"을 요구해, 이걸 잡지 않으면 W41 첫 실행 포인트가 거의 다 "~했다."로 끝난 채 통과했다
- `points[].check`는 코드 소유(`TopicPage.enforce`가 작성자 출력의 check를 false로). 같은 위치·같은 유형 이슈가 두 번 남으면 그 포인트를 check로 확정한다. 포인트가 아닌 위치(summary 등)면 토픽 status만 checked
- 검수자·수정이 위치를 1부터 센 경우(항목 2개인데 `contributions[2]`) 마지막 다음 번호를 0부터로 바로잡는다(`normalize_loc`). critic·writer_revise md에도 "번호는 0부터"를 적었다
- 수정 합치기: 지적된 최상위 칸만 반영하고 나머지 변경은 되돌린 뒤 횟수를 센다. 되돌림 전 원래 출력은 `topic_pages.raw_json`에 둔다. 칸 전체 삭제(`contributions`, `numbers`)도 받는다
- 단계 명령: `select`(선별까지), `write`(초안 + 코드 검사, 검수자 없음), `review`(현재판 초안부터 검사 ⇄ 검수 ⇄ 수정), `weekly --from-step`. 앞 단계 결과는 그 주 현재판 run에서 읽고 새 run에 쓴다. 묶기 run은 `runs.summary_json.cluster_run`으로 이어진다
- 토픽 근거 상한을 넘겨 뺀 근거 id는 토픽마다 steps.detail.truncated(실행 요약 `evidence.truncated_topics`)에 둔다. clusters.body_json에는 넣지 않았다. 근거 목록은 토픽 단위라 묶음 행보다 토픽 쪽이 맞다고 봤다
- 실행 요약은 표와 steps.detail에서 다시 계산한다(`pipeline.compute_summary`, 관문 A12)

### E1 첫 실행(W41 토픽 2개)에서 고친 버그
| 증상 | 원인 | 수정 |
|---|---|---|
| 같이 돌던 W40 summarize가 "database is locked"로 83/247에서 멈춤 | weekly·cluster가 `UPDATE runs SET week`를 커밋 없이 실행해 쓰기 트랜잭션을 LLM 호출 내내 잡음 | 바로 커밋(`with db.conn`), W40 summarize 다시 실행(이미 만든 83건은 캐시라 0원) |
| 작성자가 points에 check true를 달아 냄 | check가 출력 스키마에 있고 코드 소유 표시가 없었음 | `TopicPage.enforce`가 false로 |
| 글뿐인 토픽에 contributions channel github, 같은 채널 3개 | 규칙이 md에만 있었음 | 코드 자동 수정 |
| 검수 이슈 `contributions[2]`(실제로는 두 번째)를 수정이 새 항목으로 덧붙임 → 같은 이슈 두 번으로 check | 위치를 1부터 셈 | `normalize_loc` + md |
| 포인트가 "~했다."로 끝나도 통과 | 명사형 검사가 코드에 없었음 | 반려 추가 |
| 칸 전체(`contributions`) 삭제 수정이 반영되지 않음 | 위치 형식이 번호 있는 칸만 받음 | 받게 고침(이후 contributions는 자동 수정이라 반려 자체가 없어짐) |
- 고친 뒤: Mistral Large 4는 명사형 반려 1회 → 2라운드 통과, Claude Haiku 5.5는 1라운드 통과. 토픽당 1~2.5분, 약 $0.01~0.02

### W40 weekly에서 고친 것(버그, E1 횟수에 세지 않음)
| 실행 | 증상 | 원인 | 수정 |
|---|---|---|---|
| 17:05 | 선별 3회 모두 거부 → 대체 계획(토픽 4개) | 모델이 decisions의 select/drop과 topics를 서로 어긋나게 냄 | topics를 기준으로 decisions를 코드가 맞춤(`select.reconcile`). 원래 출력 오류는 errors_by_try에 그대로 기록(모델 품질) |
| 17:26 | writer 29회 중 12회가 max_tokens 3000에서 잘림, 토픽 2개 작성 실패 | 잘림 감지 없음 + 상한이 출력보다 작음(평균 1,888, 최대 3,000) | 공통 코어 `run_role`에 잘림 감지(한 번만 더 짧게). max_tokens writer 5000, critic 4000, editor_select 4000(스펙 5.6의 3000과 다름: COMMON 6.1-9 "출력 길이에 맞게") |
| 17:43 | 5000으로도 잘림 3토픽 | 잘린 7건 모두 `numbers[].items[].value:` 뒤에서 공백·\r 반복. 스키마가 문자열만 받는데 모델이 숫자를 쓰려 해 구조화 출력 문법에 막힘 | `NumberItem.value`가 숫자도 받고 문자열로 저장 |
| 17:43 | 검수자가 overview·summary·title의 맞는 문장을 "근거 없음"으로 반려(예: "오픈소스") | 검수자 입력이 refs가 가리키는 근거만이라, refs가 없는 칸의 근거와 자동 수정으로 빠진 contributions의 근거가 빠짐 | 검수자에게 토픽 근거 원문 전체(refs 먼저). 스펙 5.8 "refs가 가리키는 근거 원문만"과 다름: 요약 칸이 아니라 원문을 주는 원칙은 그대로 |
| 17:43 | 수정이 `numbers[0].items[1]`을 고치면 반영 안 됨 | 합치기가 최상위 칸만 받음 | 하위 위치(items[j], context, title, unit) 받기 |

### 관문 B 반복 기록(E1, 역할마다 가설 1개·한 번에 하나)
| # | 역할 | 가설과 기대 변화 | 바꾼 것 | 결과 |
|---|---|---|---|---|
| 1 | writer | core_rules에 명사형 규칙을 올리면 1라운드 명사형 반려 10/10 → 3/10 이하 | `roles/writer.md` core_rules | W41 1라운드 명사형 반려 0/10, 1라운드 통과 4/10. 유지 |
| 2 | 코드 검사 | 막대 값의 단위를 근거 표기와 대조하면 단위 섞인 막대 2건(gpt-6-1-sol, decision-api)이 반려돼 고쳐짐(Q2 16→18) | `checks.evidence_unit` | 규칙은 걸렸지만 수정이 두 라운드 모두 못 고쳐 check만 달고 막대가 그대로 발행 → judge 결과 같음. 이 방향(반려로 고치게 하기)은 끝냄 |
| 3 | 검수 루프(다른 방법) | 도식 위치 이슈가 두 번 남으면 그 도식을 빼면 단위 섞인 막대가 발행되지 않음 | `write.write_topic` 확정 처리 | 두 토픽 Q1~Q4 통과, 원자 사실 23/23·21/21 |
| 4 | critic | 시제·확정도 바꿈, 한쪽 성격을 다른 대상에 붙이는 유형을 이슈 표에 넣으면 최종판 충실성 미달 2건(jev, mistral)을 반려함 | `roles/critic.md` 이슈 표 | 두 토픽 원자 사실 34/34·36/36, Q1~Q4 통과 |
- 2~4는 실패한 토픽만 다시 돌림(E2). 3·4 뒤 두 주 전체를 한 번 다시 돌려 최종 수치를 냄(아래 관문 B)
- 버그 수정 뒤 재실행은 횟수에 세지 않음(위 W40·E1 버그 표)

### 실행 시간(5.10)
| 주 | OpenRouter 실측 | 로컬 추정(qwen3.8-27b q4, 디코딩 8 tok/s, 프리필 15.6k 토큰 101초) |
|---|---|---|
| W41(묶기부터 끝까지, run `20261009-180904-weekly-7454`) | 499초(묶기 2.0+5.3초, 선별 41.5초, 작성·검수 449.6초) | LLM 84회(decide 58, editor_select 1, writer 10, writer_revise 6, critic 9), 입력 218,090 / 출력 39,019 토큰 → 디코딩 약 81분 + 프리필 약 24분 = **약 105분**(목표 90분 초과) |
- decide 58회는 출력이 짧아(4,228토큰) 디코딩보다 프리필이 크다(91,372토큰, 약 10분). writer·critic 출력(31,720토큰)이 디코딩의 대부분
- S6 제안: decide 상한을 30으로 낮추거나 쌍 여러 개를 한 호출로, writer 출력 상한(포인트 80자) 지키기, critic atoms를 이슈 있는 칸만으로(출력 절반)

## PR #9 리뷰 반영 (2026-10-10, 설계 세션 리뷰 + 1차 라벨 opus-5.5)

> 새 규칙 C-19: 리뷰 지적은 모두 이 PR에서 고친다. "S6 제안"으로 넘기지 않는다(S6 범위 기능만 S6).

### 라벨 기록과 일치율
- 부록 라벨을 `eval/labels/`에 옮김(labeler opus-5.5, 다른 칸 그대로). decide는 모든 행 label = answer, 단 it:1046↔it:1048 same, it:1193↔it:1223 비평 추가
- 1차 라벨과 그 출력의 judge 결과는 `eval/labels/s5_r1/`에 스냅숏(재실행 뒤 시트는 새 출력 것)
- `uv run python scripts/s5_gate_b.py --weeks x --agreement <judge.json>`(라벨 폴더는 `S5_LABELS`) 집계가 리뷰 2장 표와 같다: 충실성 11/20, Q1 19, Q2 16, Q3 16, Q4 19, 검수 14/26, decide 57/58·오병합 0, 정규화 6/6, drop 이유 18/19, 표현 선택 남발 1·누락 1. judge ↔ 라벨: 종합 9/20, 충실성 10/20

### judge 보정(R5, COMMON 2: 80% 미만이면 라벨 비평을 judge 예시로, 최대 3회)
| 회 | 바꾼 것 하나 | 충실성 일치 | Q1 | Q2 | Q3 | Q4 | 종합 |
|---|---|---|---|---|---|---|---|
| 0(PR) | - | 10/20 | 20/20 | 16/20 | 17/20 | 19/20 | 9/20 |
| 1 | 라벨 비평 유형(범위 부풀림·인과 합침·확정도·동률·파생 수치·전망·개념)을 judge_facts.md와 writer 채점표 실패 예시에 | 14/20 | 19/20 | 16/20 | 16/20 | 19/20 | 17/20 |
| 2 | judge_facts 출력 순서: title·summary·overview 원자 사실 먼저(다시 잰 것은 어긋난 6토픽만, E2) | **16/20** | 19/20 | 16/20 | 16/20 | 19/20 | 16/20 |
- 2회째에 모든 항목 80% 이상. 다만 2회째 개선은 Solar·Jev(judge가 라벨보다 엄격하던 것)가 뒤집힌 것이고, 라벨이 잡은 요약 범위 부풀림(GPT-6.1 Sol)·"앞선다"(Mistral)는 judge가 여전히 놓친다 → 관문 B 충실성은 judge와 라벨을 함께 적는다
- 원자료: `eval/labels/s5_r1/judge_r5_pass1.json`, `judge_r5_pass2.json`

### 지적 처리
| # | 처리 | 확인 |
|---|---|---|
| R1 | 검수자 입력에서 요약만 있는 id 제외, `raw_evidence`가 요약을 원문으로 주지 않음. critic.md 절차 1에 numbers 제목·concepts·title, refs 없는 칸(title·summary·overview·concepts)은 근거 원문 전체와, 함정 8종 표(범위 부풀림, 두 출처 인과, 가능성→확인, 동률→앞선다, 의미 바꿈, 파생 수치, 전망·평가, 개념 오류) + 요약 범위 예시 | 재실행 critic 판정(관문 B 표) |
| R2 | 작성자 근거 줄 머리: "원문:", "(카드 수치, 위 원문에서 뽑음)", "(카드 주장 요약, 원문 아님)". writer.md에 "주장 줄은 근거 문장이 아님". 코드 수치 대조와 `graders_brief._pack_from_docs`도 원문 기준(주장·요약 줄 제외) | `test_r3_numbers_checked_in_titles_and_by_value_not_substring` |
| R3 | (a) 단위 종류에 시간·분·분기·개월·개·명·회·건, 라벨 끝 괄호 단위 ↔ 그룹 단위, 근거 단위를 못 찾으면 경고 (b) 빈 단위 반려 (c) 수치 대조를 제목·요약·개요·concepts·도식 제목·context·사건 글·contributions까지, 값 비교(부분 문자열 제거) (d) 금지어 `주목된다·것으로 보인다·것으로 전망된다·지 주목`, points에 평가어. writer.md·diagrams.md 예시의 파생값("7%p", "6.9%p") 교체 | A9 `test_r3_*`, `test_bar_value_unit_*` |
| R4 | 토픽 수준 `checks`(남은 위치 목록, 마이그레이션 35 `topics.checks_json`), 실행 요약 `review.check_topics`, 읽기본 "⚠ 확인 필요" 배지, export `checks`·`has_check`. points 개수 초과는 코드가 뒤에서 자르고 잘린 포인트의 도식도 뺌(반려 아님) | A11·A13, `test_r4_points_over_cap_*` |
| R5 | 위 judge 보정 | 위 표 |
| R6 | C-20 영상 자리 적용, C-21은 설계 세션 수정안으로(아래) | A8 `test_c20_*`, `test_c21_*` |
| R7 | "값 2개 막대" 문구 3곳 → "baseline 없는 값 2개 막대, 또는 summary에 그 값이 없는 전후 비교"(채점표 Q2·실패 예시, critic overuse, writer 함정 예시). `autofix.drawable`은 그대로 | - |
| R8 | 실행 요약 `select.drops_by`: model(모델 직접) / code(reconcile가 drop으로 바꿈) / fallback(대체 계획) | A12 |
| R9 | 원인: 수집이 그 주 트렌딩을 지우고 다시 써서 마지막 수집(10/10)에 빠진 레포 2개(NVIDIA/OpenShell, tile-ai/tilelang)의 행이 사라짐. 공통 코어 수정: 카드가 있는 레포 행은 남김. 두 행은 10/9 DB 백업의 이전 수집판 값으로 되살림(3,690·639). 읽기본은 None이면 "별 정보 없음" | `test_r9_clear_trending_keeps_repos_with_cards` |
| R10 | S5_TASK 5.3·writer.md에 `og:{item_id}#q{n}` 명시, export sources에 `origin`(원본 URL) | A13 `test_export_numbers_events_og_and_checks` |
| R11 | 음차·약어 사전 `aliases.transliteration`(brief.yaml): 낱말 단위로 바꾸면 같은 이름이면 자동 approved(정본은 영문), 작성자 출력의 음차 표기("GPT-6 루나", "딥시크-V4.1 플래시")는 코드가 정본으로 고침. "Luna 5.6" 같은 버전 오기는 규칙으로 못 막음(검수 몫) | `test_r11_transliteration_aliases_and_autofix` |
| R12 | 근거 채널 2개 이상이면 채널마다 contributions 1문장, 빠진 채널은 반려 | `test_unknown_ref_and_single_source_contributions` |
| R13 | R1과 함께(검수 절차·함정 표에 concepts), 코드 수치 대조도 concepts까지 | - |
| R14 | 후보 문서 "채널 N개: text(글 3건)", 편집장 md에 채널 3종 명시, reason의 "채널 N"을 입력 채널 수와 대조(attention) | `test_r14_reason_channel_count_checked` |
| R15 | decide.md: 출시 발표 글 ↔ 같은 모델 시험 글 = same 예시와 표 행 | 재실행 decide(it:1046↔1048) |
| R16 | verify_s5: A1 종료 코드, extra video·embed 항상, A8·A9·A13 테스트 범위 넓힘 | 관문 A |
| R17 | W40 묶기부터 다시 돌려 `reports/S5_brief/cluster_2026-W40.md` 생성 | 파일 |
| R18 | 아래 실행 시간 분해 표(`s5_gate_b.py --runtime`) | 표 |

### 재실행에서 찾아 고친 것
| 무엇 | 원인 | 처리 |
|---|---|---|
| 검수자가 원자 사실 0개(출력 49토큰)로 3토픽 통과(W40 dots, Sonnet 5.5, Claude Code 스킬) | 대조를 건너뛴 판정을 코드가 그대로 받음 | 원자 사실 0개 통과는 판정으로 받지 않음: 한 번 다시 부르고 또 비면 검수 실패(attention). 3토픽만 review 단계부터 다시(E2) → 실제 판정(1토픽 반려 후 checked) |
| Haiku "토크나이저 → 숨겨진 가격 인상"이 재실행에도 개요에 | "(카드 주장 요약, 원문 아님)" 표시만으로는 작성자가 씀 | 작성자 근거에서 글 카드 주장 줄을 뺌(R2 마무리). 수치 줄은 원문에서 뽑은 값이라 둠 |
| EmbeddingGemma 개념 MRL "저장 공간 절감" | 개념 풀이를 배경 지식으로 채움 | writer.md: concepts 풀이는 근거 원문 범위만, 풀이가 없으면 넣지 않음(E1 writer 1회, 미달 4토픽만 다시) |
| 편집장 reason의 "0.55"를 입력 밖 숫자로 잡음 | 영상 자리 문턱값이 md에만 있음 | `limits.video_relevance_min`으로 입력에 |
| 관문 B 스크립트가 후보를 다시 고를 때 동점 순서가 달라 KeyError | 유사도 없이 다시 계산 | pipeline과 같이 유사도로 |
| 라벨 시트가 바뀐 출력에 이전 라벨을 옮김, decide 시트가 앞 주 행을 지움 | 열쇠(topic_id)만 맞춰 옮김 | 출력이 그대로인 행에만 라벨, decide는 다른 주 행 보존 |

### C-20·C-21 (선별)
- C-20: 입력 후보에 영상 관련성 0.55 이상 영상 묶음이 있으면 영상 묶음 토픽 1개 이상(검증, 대체 계획도). 후보 문서에 영상 관련성, 영상 항목에 핵심 포인트 수·슬라이드 전용 수치 수
- C-21 원안(유사도 구간 0.05 먼저, 코드가 순서): LLM 0원 미리보기에서 큰 발표가 밀림(W40 이전 선정 11개 중 5개만 상위 20, Introducing dots 44위, Claude Sonnet 5.5 109위). 유사도가 0.46~0.63에 몰려 구간이 출처 수보다 먼저 정해짐 → 사용자 보류 → 설계 세션 수정안 적용
- C-21 수정안(적용): 묶기 점수 그대로, 동점이면 관심 유사도 높은 순(cluster_id 동점 깨기 대체). 토픽 순서는 편집장. 비교 표 `reports/S5_brief/select_order_2026-W40.md`·`W41.md`(수정안·이전·원안 세 열)
  - W40: 이전 선정 11개 중 10개 상위 20, 영상 든 후보 상위 20 안 3개(이전 1). c301(Simon Willison "Claude Sonnet 5.5", 지난번 c296과 합쳐 한 토픽)은 점수 3119 동점 무리에서 유사도가 가장 낮아(0.459) 21위로 빠짐
  - W41: 10/10, 영상 6개(이전과 같음)

## 반영 확인 리뷰(2차) 반영 (2026-10-10)

> 설계 세션 반영 확인 리뷰: 새 출력 라벨 통과 6/20 → 12/20. 남은 미달 원인이 코드 규칙·입력이라 이 PR에서 고침(C-19). 라벨 스냅숏 `eval/labels/s5_r2/`(그 출력의 judge `judge_r2.json`)

### 2차 라벨 집계(새 출력, `S5_LABELS=eval/labels/s5_r2 ... --agreement eval/labels/s5_r2/judge_r2.json`)
리뷰 2장 표와 같다: 충실성 17/20, Q1 17, Q2 18, Q3 19, Q4 18, 종합 12/20, 검수 16/24(67%), decide 58/58, 정규화 17/17, drop 이유 15/18, 표현 선택 남발 0·누락 2. judge ↔ 라벨 충실성 19/20, 종합 16/20

### 지적 처리
| # | 처리 | 확인 |
|---|---|---|
| F1 | 요약·개요 "~다"를 문장마다(`sentences()`), 관문 B 정규식 집계도 같게 | `test_f1_*`(Solar 개요, 디시전스 요약 문장 그대로) |
| F2 | 도식은 최종판에서 코드가 확인한 형식·수치 오류(단위 섞임, 값 불일치, 빈 단위)일 때만 뺌. 검수자 의미 지적만 남으면 도식은 두고 ⚠. ⚠가 빠진 도식을 가리키면 "빠진 도식: 제목", 남은 도식은 뺀 뒤 번호로. 뺀 도식과 남은 이슈는 실행 기록(`dropped_diagrams`)과 S5_quality 표 | `test_f2_*`, 기존 단위 섞인 도식 테스트에 "빠진 도식: 점수" |
| F3 | (a) 누락 경고: 같은 근거 문장(id)의 같은 단위 값 3개 이상만, 값 앞 약·최대·평균·~ 제거, 개수·차원 단위 제외. critic.md "경고는 의심, 같은 지표·같은 조건 비교가 아니면 missing_diagram 아님" (b) 검수자 입력에 `previous`(지난 토픽 요약·포인트), 지난 토픽을 말하는 문장은 previous와 대조 | `test_f3_*`(스킬 약 50·20·60개, 차원 768/512/256, 서로 다른 문장의 %는 경고 없음) |
| F4 | writer.md: angle은 방향이지 문장 재료가 아님, 동사 바꾸지 않음(제시→풀이, 프리뷰 발표→출시). critic·judge 함정 표에 동사 바꿈, angle을 사실처럼 | 재실행 |
| F5 | writer.md: 영상 근거만 받치는 문장은 "발표자는 …라고 설명했다", 요약 첫 문장은 주어(발표자 포함), 여러 발표 합친 토픽은 "발표 3편". critic·judge 함정에 발표 주장 → 사실 | 재실행 |
| F6 | writer.md: 요약·개요는 points에 있는 사실만. critic: 포인트에 없는 사실은 근거에 있어도 unsupported | 재실행 |
| F7 | 코드 경고 "핵심 의심": angle 핵심 낱말(조사·일반어 제외)이 첫 point에 하나도 없으면 → critic.md가 missing_key(points[0])로 | `test_f7_*` |
| F8 | 관문 B 라벨 시트에 출력 해시(`page_hash`) 칸, 라벨은 해시가 같은 행에만 옮김 | 다음 시트 |
| F9 | editor_select.md: 0.55는 영상 자리 보장 기준이지 제외 기준이 아님, reason에 "0.55 미만"을 빼는 이유로 쓰지 않음 | 선별 재실행 안 함(지시: 선별 그대로) |
| F10 | 음차를 정규식으로: 낱말 사이 띄어쓰기·하이픈 무관, 한글 경계(조사만 허용, '솔루션'의 '솔'은 아님), 한글 음차뿐인 이름(클로드 소네트 5.5)도 사전으로 되돌린 영문이 정본. 사전 보강: 소네트, 디시전스, 큐원·퀜, 네모트론(값에 '|'로 여러 음차) | `test_r11_*` 확장 |
| F11 | 금지어 추가: "것이 쟁점이다", "핵심 변화다", "핵심 축으로", "부상했다"("쟁점은 …이다"는 허용) | `test_f11_*` |
| F12 | Mistral: it:1048(같은 모델 시험 글)은 묶음(c926)에 들었고 작성자 근거 목록에도 있었다(q1, q2, 상한으로 빠지지 않음). 작성자가 인용하지 않아 출처에 없음. 재실행 대상이 아니라 그대로 | 기록 |
| C-22 | 관문 B 선별 검증 = 코드 정리(reconcile) 뒤 100%(2/2). 원래 출력 오류는 `drops_by`와 리포트에 계속 기록, md 반복은 하지 않음 | 관문 B 표 |

### 10토픽 재실행 결과(선별·묶기 그대로, 토픽 단위 `--from-step write --topic`)
현재판: W40 `20261010-111536-weekly-32f0`, W41 `20261010-112923-weekly-10c9`. judge는 바뀐 10토픽만 다시(나머지 10토픽은 그대로).

| 항목 | 2차 라벨(이전 출력) | 재실행 judge(잠정) | 문턱값 | 판정 |
|---|---|---|---|---|
| 근거 충실성 | 17/20 | 17/20 | 모든 토픽 | 미달(잠정) |
| Q1 / Q2 / Q3 / Q4 | 17 · 18 · 19 · 18 | 18 · 19 · 20 · 19 | 90% | Q1만 90% 경계, 나머지 통과(잠정) |
| 코드 문체 정규식(문장마다 "~다", 새 금지어) | 위반 2(검사가 놓침) | 0 | 0 | 통과 |
| 선별 코드 검증(C-22: 정리 뒤) | 2/2 | 2/2(선별 재실행 안 함) | 100% | 통과 |
| 코드가 뺀 도식 | - | 0(F2: 의미 지적만 남은 도식은 이제 남김) | - | - |

- 고쳐진 것(judge): 수학 요약 동사("풀고" 없어짐), Claude Code 스킬 요약의 포인트 밖 수치, 디시전스 API 스펙 명사형 요약, 코딩 에이전트 발표 3편 요약(발표자 귀속), OpenRig contributions는 여전히 github 한 줄이라 ⚠(R12 반려 2회 뒤 checked)
- 남은 것(같은 실패가 반복돼 E1상 이 방향은 멈추고 리뷰에 올림)
  - **Solar Mini 4 첫 point(3회째)**: F7 코드 경고 "핵심 의심"은 떴으나(1라운드) 검수자가 따르지 않고 통과. 다음 수단은 이 경고를 코드 반려(missing_key)로 올리는 것인데, 낱말 겹침 0 규칙의 오탐 범위를 아직 재지 않아 결정을 리뷰에 맡김
  - **LlamaIndex 영상(3회째)**: 요약·개념의 "ParseBench가 3가지 처리 영역을 구분"이 judge 기준 근거 밖. 영상 근거 원문(전사 앞뒤 30초 + 판독)에 그 설명이 있는지 리뷰 확인 필요
  - **Haiku**: points[3] "100,000 토큰 초과 시 토큰당(100만 토큰당)" 표기 꼬임(judge 비지지 1). 구간별 가격 도식은 작성자가 이번에 만들지 않음(코드가 뺀 것 아님) → 표현 선택 누락은 남음. textGrain 탐지율 도식도 작성자가 만들지 않음
  - Sonnet 5.5 Q1: 첫 point가 벤치 점수(angle은 토큰 설계). 충실성은 37/37로 고쳐짐
- 재실행하지 않은 10토픽의 ⚠는 이전 규칙으로 저장된 값이라, 읽기본·export가 없는 도식을 가리키는 위치를 "빠진 도식(numbers[1])"로 보여 준다(`briefing.visible_checks`, LLM 0원). 새로 쓰는 토픽은 "빠진 도식: 제목"

## 관문 B (1차 반영 뒤 W40 + W41 전체 재실행, 잠정, 2차 반영 결과는 위 절)
자세한 표: `reports/S5_quality.md`(끝 절 "실제 실행"), 최종판 judge 원자료 `reports/S5_brief/gate_b_final_judge.json`, 읽기본 `reports/S5_brief/briefing_2026-W40.md`·`briefing_2026-W41.md`. 현재판 run: W40 `20261010-082349-weekly-8cdc`(묶기부터 `20261010-073230-weekly-d33d` + 토픽 단위 재실행), W41 `20261010-082802-weekly-b543`(묶기부터 `20261010-075543-weekly-fd8a` + 토픽 단위 재실행).

판정 칸: "judge"는 보정한 judge(R5) 결과, 새 출력의 2차 라벨은 설계 세션 반영 확인 리뷰에서. 1차 라벨(이전 출력) 기준은 리뷰 2장 표(`eval/labels/s5_r1/`).

| 항목 | 이전 출력: PR judge / 1차 라벨 | 재실행: 원래 출력 | 재실행: 코드 정리·자동 수정 뒤(최종판) | 문턱값 | 판정 |
|---|---|---|---|---|---|
| 근거 충실성 | 17/20 / 11/20 | - | judge **18/20 토픽 100%** | 모든 토픽 | **미달(잠정)** |
| Q1 핵심 | 19/20 / 19/20 | - | judge 19/20 | 90% | 통과(잠정) |
| Q2 군더더기 | 18/20 / 16/20 | - | judge 18/20 | 90% | 통과(잠정) |
| Q3 읽기 쉬움 | 19/20 / 16/20 | - | judge 20/20 | 90% | 통과(잠정) |
| Q4 문체 / 코드 정규식 | 20/20·0 / 19/20·1 | - | judge 20/20 / 정규식 0(새 금지어 포함) | 90% / 0 | 통과(잠정) |
| 선별 코드 검증 | 원래 0/2 | **원래 첫 시도 1/2**(W41 통과, W40은 decisions가 20개 모두 select) | 코드 정리(reconcile) 뒤 2/2, 영상 자리 2/2(W40 LlamaIndex 영상, W41 코딩 에이전트 발표 영상) | 100% | 원래 출력 미달 |
| decide | 픽스처 10/10 / 57/58·오병합 0 | W41 라벨 58쌍 58/58·오병합 0(it:1046↔1048 이제 same, R15) | - | 오병합 0 | 통과(잠정) |
| 검수 실제 판정 | 픽스처 95% / 14/26 | 원자 사실 0개 통과 3건 발견 → 코드가 판정으로 받지 않음 | 라벨 대기(`eval/labels/critic.csv`) | 80% | 잠정 |
| 표현 선택 | - / 남발 1·누락 1 | - | 라벨 대기(`diagram_labels.json`) | 남발 0, 누락 ≤1 | 잠정 |
| 정규화 | - / 6/6 | 음차 사전 추가 | 라벨 대기(`aliases.csv`) | 90%, 오병합 0 | 잠정 |
| 확인 필요 표시 | check_points만(토픽 수준 0) | - | 토픽 수준 checks: W40 4토픽, W41 5토픽(읽기본 ⚠ 배지) | 기록 | - |

- 근거 충실성 미달 2토픽(judge, 토픽 단위 E1 1회 뒤)
  - w40-claude-sonnet-5-5 44/45: 개요 "컨텍스트·출력 토큰 설계에 반영됐다"는 인과·평가
  - w40-llamaindex-context 13/15(영상): 개요의 "ParseBench로 3가지 처리 영역 구분", 개념 "에이전트 하네스" 풀이가 전사·화면 판독에 없음
  - 고친 것(같은 E1 1회): Haiku "토크나이저 → 숨겨진 가격 인상"(카드 주장 줄을 작성자 입력에서 뺌, R2 마무리), EmbeddingGemma MRL "저장 공간 절감"(writer.md concepts는 근거 원문 범위만) → 둘 다 100%
- 재실행 첫판(토픽 단위 E1 전) judge는 16/20. 이전 PR 출력(17/20)과는 선별된 토픽이 일부 달라 직접 비교하지 않는다
- judge 보정 뒤에도 judge가 요약 범위 부풀림·"앞선다"를 놓친 사례가 1차 라벨에 있어(위 R5 표), 충실성은 라벨 확인 전까지 잠정
- 라벨 시트(새 출력, 비어 있음): `eval/labels/writer.csv`, `critic.csv`, `editor_select.csv`, `diagram_labels.json`. 출력이 그대로인 행만 이전 라벨을 옮겼다(`decide.csv` W41 58쌍은 쌍 단위라 그대로)

### 이전 출력의 관문 B(PR #9 첫 제출, 참고)
자세한 표: `reports/S5_quality.md`(역할 픽스처 평가 + 끝 절 "실제 실행"), 최종판 judge 원자료 `reports/S5_brief/gate_b_final_judge.json`, 읽기본 `reports/S5_brief/briefing_2026-W40.md`·`briefing_2026-W41.md`.

| 항목 | 채점 | 결과 | 문턱값 | 판정 |
|---|---|---|---|---|
| 근거 충실성 | judge_facts(원자 사실) → 코드 지지율, 최종판 20토픽, **judge 입력은 근거 원문**(리뷰 지적 8 반영 뒤) | **17/20 토픽 100%**(원자 사실 499/504 지지) | 모든 토픽 100% | **미달(잠정)** |
| 핵심 포착 Q1 | judge | 19/20(95%) | 90% | 통과(잠정) |
| 군더더기 없음 Q2 | judge | 18/20(90%) | 90% | 통과(잠정) |
| 읽기 쉬움 Q3 | judge | 19/20(95%) | 90% | 통과(잠정) |
| 문체 | 코드 정규식(최종판) / judge Q4 | 위반 0 / 20/20 | 0 / 90% | 통과 / 통과(잠정) |
| 표현 선택 | 도식 라벨 대비 | 라벨 대기(`eval/labels/diagram_labels.json`) | 남발 0, 누락 20 중 1 이하 | 잠정 |
| 묶기 | 라벨 대비 오병합 | decide 31쌍 코드 세션 잠정 라벨 기준 0, 2채널 이상 토픽 1/20 | 0 | 잠정 |
| 정규화 | 별칭 라벨 대비 | 라벨 대기(`eval/labels/aliases.csv`) | 정확도 90%, 오병합 0 | 잠정 |
| 선별 | 코드 검증 / drop 이유 라벨 | **원래 출력 기준 첫 시도 검증 0/2 주**(두 주 모두 decisions↔topics 어긋남), 코드 정리(reconcile) 뒤 2/2. 픽스처 8/8은 정리 뒤 판정(원래 출력 어긋남은 aggregate에 따로) / 라벨 대기 | 100% / 80% | **원래 출력 미달**, 정리 뒤 통과 / 잠정 |
| 검수 | 심은 오류 픽스처 20(깨끗한 8 + 오류 12) | 판정 일치 19/20(95%), 심은 오류 반려 12/12, 깨끗한 초안 과잉 반려 1/8 | 일치 80% | 통과(픽스처) / 실제 판정 라벨 대기(`eval/labels/critic.csv`) |
| decide | 픽스처 10 | 10/10, 오병합 0 | 오병합 0 | 통과 |

- 근거 충실성 미달 3토픽(최종 run W40 `20261009-200528-weekly-eafd`, W41 `20261009-201517-weekly-2101`, 예산 소진으로 개선 반복을 더 하지 않음)
  - w41-claude-haiku-5-5 18/21: "토크나이저 변경이 원인"(points[3]·overview·summary). 카드 주장·요약에 있던 해석이 quote 원문(it:1144#q4)에는 없음 → 작성자가 근거 문서의 "주장:" 줄을 근거로 씀. 검수자도 통과
  - w40-solar-mini-4 33/34: "Solar Mini 4는 MoE 구조"가 it:860#q1에 없음
  - w41-sift-framework 21/22: concepts 설명 1개. 같은 토픽 numbers가 % 그룹에 시간 값(5, 42)을 섞음(근거에서 값 뒤 단위를 못 찾아 단위 대조가 건너뜀) → Q2·Q3도 실패
  - 앞선 실행(judge 입력에 요약·주장 줄이 있던 때)은 20/20이었다. 원문만 주자 더 엄격해졌고 이 판정이 맞다고 본다
  - S6 제안: 작성자 근거 문서에서 "주장:" 줄도 빼거나 "원문 아님" 표시, 단위를 못 찾은 값은 단위 대조 대신 반려하지 않고 경고로 검수자에게
- 이전 실행의 문체 1건(w40-deepseek-harness "핵심이다")은 리뷰 반영 뒤 재실행에서 나오지 않았다(0건). 작성자 초안 단계의 평가형 마무리는 여전히 잦다(S6: 작성자 md 함정 예시)
- writer 픽스처 평가(첫 초안, 루프 전)는 코드 11/20, Q2 6/11로 미달이다. 이 표는 초안 품질(모델) 기록이고, 관문 B는 루프를 거친 최종판 기준이다(위 표)
- writer_revise 픽스처: 4/8. 지적 안 된 칸 변경 2(코드가 되돌림), 근거로 못 고친다며 수정 0 + attention 2(심은 문장 삭제 기대). 스펙 관문 B 표에 revise 문턱값은 없어 기록만
- **채점표 확인 요청**: writer 채점표 Q2 실패 예시 "값 2개만 있는 막대 그룹"은 스펙 5.6·diagrams.md의 허용 조건(값 2개 + baseline + summary에 그 값)과 어긋난다. 최종판 Q2 실패 2건(solar-mini-4, vidraft-darwin)이 이 경우다. 채점표를 지금 고쳐 다시 매기면 통과를 위한 변경이 되므로 고치지 않았다. 리뷰 세션이 정해 주면 다음에 반영한다
- 라벨 시트(D1-3, 리뷰 세션 opus-5.5가 채움): `eval/labels/writer.csv`(최종판 20토픽, Q0 충실성 + Q1~Q4), `critic.csv`(실제 검수 판정 라운드별), `diagram_labels.json`, `decide.csv`(31쌍, 코드 세션 잠정 라벨 있음), `aliases.csv`, `editor_select.csv`

### 실행 시간 분해(R18, 재실행, `s5_gate_b.py --runtime <run>`, 로컬은 디코딩 8 tok/s·프리필 15.6k 토큰 101초)
| 주(run) | decide | editor_select | writer | writer_revise | critic | 합(로컬 추정) | OpenRouter 실측 |
|---|---|---|---|---|---|---|---|
| W40 `d33d` | 60회 21.4분 | 6.1분 | 31.4분 | 4.8분 | 10회 30.5분 | **94분** | 15분(919초) |
| W41 `fd8a` | 58회 19.8분 | 7.0분 | 29.0분 | 4.6분 | 15회 54.5분 | **115분** | 17분(1,007초) |
- 목표 90분 초과. 가장 큰 몫은 디코딩(W41 82.9분 중 critic 44.3분): 검수 라운드가 늘수록(W41 critic 15회) 원자 사실 출력이 쌓인다. decide는 출력이 짧아 프리필이 반

## 사용액 (`trendsit cost --spec S5`)
| 모델 | 호출 | 캐시 적중 | 입력 토큰 | 출력 토큰 | 사용액 |
|---|---|---|---|---|---|
| qwen/qwen3.8-27b | 1456 | 332 | 6,011,409 | 1,165,501 | $2.24 |
| google/gemini-3.8-flash(judge) | 133 | 40 | 613,742 | 136,008 | $0.33 |
| 합계(기록) | | | | | **$2.57** / 상한 $3.00 |
- PR #9 첫 제출 때 키 기준: 단계 $5.31 − S5 시작 때 $2.46 = 약 $2.85 / $3.00
- PR #9 리뷰 반영 뒤(상한 4.00, 사용자 승인): 키 기준 단계 $5.94 − $2.46 = **약 $3.48 / $4.00**. 리뷰 반영 몫 약 $0.63(judge 보정 2회·최종 judge 2회 약 $0.35, W40·W41 재실행과 토픽 단위 재실행 약 $0.25). 단계 합계 $5.94 / $20
- 큰 몫: W41·W40 글 카드 재생성 $0.68, 작성·검수 반복 실행(버그 수정 재실행 포함) 약 $0.9, judge $0.33

## 스펙과 다르게 한 것
| 스펙 | 한 것 | 이유 |
|---|---|---|
| 관문 B 대상 W42 + W41 | W40 + W41 | 멈춤 지점 결정 7(설계). W42는 10/18 수집 뒤 weekly만 |
| writer max_tokens 3000(5.6) | 5000(critic 4000, editor_select 4000) | 출력 길이 분포(평균 1,888, 최대 3,000 도달 41%). COMMON 6.1-9 |
| 검수자 입력: refs가 가리키는 근거 원문만(5.8) | 토픽 근거 원문 전체(refs 먼저) | overview·summary·title은 refs가 없어 근거가 빠졌다(맞는 문장을 반려) |
| 반려 목록(5.7) | 명사형·"~다" 끝 검사 추가, contributions 채널 규칙은 반려 대신 자동 수정 | 관문 B 문체 "코드 정규식 위반 0"과 맞추려고 / 고칠 수 있는 형식은 코드가 고친다(5.7 원칙) |
| 도식 | 그리는 조건(diagrams.md)을 코드가 적용해 미달 도식을 뺌, 도식 위치 이슈가 두 번 남으면 그 도식을 뺌 | diagrams.md "그릴지는 코드가 정한다", 틀린 막대가 check만 달고 발행되던 문제 |
| 선별 검증(5.5: 어기면 재시도 → 대체) | decisions의 select/drop을 topics에 맞추는 코드 정리(reconcile) 뒤 검증 | W40에서 세 번 모두 어긋나 대체 계획이 됐다. topics에서 끌어낼 수 있는 값이라 코드가 맞추되, 원래 출력 오류는 기록하고 관문 B 선별 항목은 원래 출력 기준 미달로 적는다(리뷰 지적 3) |
| 근거 id(CONTRACTS 2장) | EvidencePack에 요약 id `it:{n}`·`vd:{n}`(kind summary)를 둠. 작성자 근거 문서와 judge·검수 입력에는 넣지 않음 | 묶기·선별 입력에 글·영상 요약이 필요. 작성자가 원문이 아닌 요약을 근거로 다는 것을 막으려고 문서에서 뺐다(리뷰 지적 8) |
| 넘친 근거 기록(5.3: clusters.body_json) | 토픽마다 steps.detail.truncated | 근거 목록이 토픽 단위라 |
| W40 트렌딩 재구성 | 접음 | GitHub API가 stargazer 시각을 주지 않음(0단계 뒤 결정 8 절) |
| W41 재료 | 10/5~10/9 수집분(재실행은 10/10 02:00 수집까지) | 10/11 수집 뒤 한 번 더 돌려 갱신(결정 7) |
| 선별 순서 C-21 원안(유사도 구간 먼저, 코드가 순서) | 설계 세션 수정안: 점수 그대로, 동점만 유사도, 순서는 편집장 | 미리보기에서 큰 발표가 밀려 사용자 보류 → 설계 세션 수정(2026-10-10) |
| 근거 id 글 카드 주장 줄(같은 quote id) | 작성자 입력에서 뺌 | 리뷰 R2, "원문 아님" 표시로는 재실행에서도 쓰임 |

## 남은 문제
> C-19: 리뷰 지적은 이 PR에서 고쳤다. 아래는 지적 밖에서 남은 관찰과 S6 범위(export, 사이트, 정식 launchd, P4 4·5)

- 근거 충실성 2토픽 미달(위 관문 B), 실행 시간 로컬 추정 94·115분(목표 90분, 위 분해 표)
- 선별 원래 출력: W40은 decisions를 20개 모두 select로 내 코드 정리(reconcile)로 맞춤. 같은 실패가 두 번째라(E1) 이 방향(md 문구)은 접고 코드 정리 + 기록을 유지
- 2채널 이상 토픽 1/20(W41 OpenRig text+github). 영상 digest가 적고(W40 3편, W41 8편) W40은 레포 근거가 없음
- 편집장 계획 큐의 얕은 mode 재처리, spoken_value 오탐: nightly·영상 쪽 관찰(S5 스펙 밖)
- S6 범위: export(매핑 초안 `briefing.export_topic`에서 시작, 도식은 anchor로 포인트에 붙음, 출처 번호 새로 매김), 영상 타임라인(C 도식), 임시 수집 예약 제거, P4 4·5

## README 갱신과 위키 메모
- README: 현재 상태 줄, 빠른 시작에 `cluster`·`weekly` 명령, 핵심 기능·역할 표 상태, 성과 표 S5 행, 로드맵 S5 체크
- 위키 메모(막혔다 푼 것)
  - 구조화 출력에서 문자열만 받는 숫자 칸 → 모델이 숫자를 쓰려다 공백 반복으로 max_tokens까지(잘림 7건 모두 `"value":` 뒤). 칸이 숫자도 받게 하자 0건
  - 검수자가 위치를 1부터 셈 → 심은 오류 13건 중 12건이 한 칸 뒤. 위치 이름이 붙은 줄을 입력에 주자 다음 평가에서 12/12 정확
  - 같은 실패가 반복되는 형식(명사형)은 md 본문보다 core_rules(user 메시지 끝)에 둘 때 효과(1라운드 반려 10/10 → 0/10)
  - 묶기 임베딩: 본문(body) vs 제목+요약(card) 결과 같음, card는 자동 병합을 늘려 decide 확인이 빠짐 → body

## 서브에이전트 리뷰(새 컨텍스트, 스펙 + 코드 + 리포트만) 지적과 처리
| # | 지적(심각도) | 처리 |
|---|---|---|
| 1 | 같은 라운드 안 같은 (위치, 유형) 이슈 2건이면 첫 라운드에 check 확정(높음) | 라운드마다 중복 제거 후 셈. 모의 LLM 테스트 추가 |
| 2 | 코드 반려만 이어져 검수자를 한 번도 거치지 않은 최종판 6개(높음) | 그런 판은 발행 전 검수자 1회, 이슈 위치 check. 테스트 추가 |
| 3 | 선별 "검증 100%" 보고가 원래 출력과 다름(높음) | 관문 B 표를 원래 출력 기준 0/2(미달)로 정정, reconcile을 "스펙과 다르게 한 것"에 |
| 4 | 수정 합치기 예외가 weekly를 멈추고 현재판이 반쯤 끝난 run으로(중간~높음) | 하위 위치 형식 검사·스키마 실패 시 이전 판 유지, 토픽 단위 예외 처리(failed), weekly는 끝에서만 current_run_id 갱신 |
| 5 | 목록 전체 위치(points, numbers) 이슈를 고칠 수 없음(중간) | 목록이 지적되면 그 목록 항목 변경 허용, points 전체 삭제는 받지 않음 |
| 6 | 채널을 넘는 묶음이 decide 없이 전이로 생김(중간) | 합칠 때 생기는 채널 넘는 쌍이 모두 decide same이어야 함. 테스트 추가 |
| 7 | cluster_id 순서가 점수 순서(중간) | 저장 순서를 첫 구성원 키로(리포트는 점수 순 표시). 테스트 추가 |
| 8 | 요약 id가 CONTRACTS 밖이고 judge 입력에 요약 줄(중간) | 작성자 근거 문서에서 요약 id 제외, 최종판 judge는 근거 원문으로 다시 잼 |
| 9 | reason 숫자 대조가 입력 전체 부분 문자열이라 사실상 꺼짐(중간) | 그 후보 문서 + 짧은 공통 칸에서만, 숫자 경계 |
| 10 | 묶기 테스트가 경로 규칙을 다시 구현 / A14 예외(중간) | 실제 build_pairs 테스트 추가(이름 경로·회사 이름 제외). A14 예외(라벨이 가리키는 실행)는 일치율 재현에 필요해 유지 |
| 11 | relation_label 미저장, 별칭 부분 치환, critic 실패를 pass로 기록, 묶기부터 다시 돌릴 때 이어 오기, 미사용 설정·코드 상수, ENFORCED_FIELDS 선언, 숫자 다른 표기 자동 승인(낮음) | relation_label 저장(마이그레이션 34), 단어 경계 치환, 검수 실패는 판정 기록 안 함(attention), 묶기부터면 이어 오지 않음, broad_keywords·alias_decide_max를 brief.yaml로, ReviewVerdict ENFORCED_FIELDS에 status·attention, 숫자 다른 표기는 자동 승인 안 함. 미사용 설정(linkage, auto_approve, per_point_max, runtime)은 스펙 초안 칸이라 남김 |

## 관문 A (`bash scripts/verify_s5.sh`, 2026-10-10 08:45, PR #9 리뷰 반영 뒤)
```
PASS A1 verify_s0~s4 종료 코드 0, PASS 73개
PASS A2 ruff 0, pytest 520 passed in 168.73s (0:02:48), 건너뜀 0
PASS A3 check-config OK 설정 9개, 역할 15개, budget S5 있음, 역할 md 5개(decide, editor_select, writer, writer_revise, critic) 섹션 검사 포함
PASS A4 공통 수정 5.1(명사 예외, ImageError 계열, 중첩 ImageFile 거부, ClassVar, 예산 기준값 위치, 수치 모듈) + 출력 잘림 감지 (19 passed in 0.69s)
PASS A5 근거 목록(자격, 근거 id 형식, 입력 상한과 뺀 근거) (3 passed, 10 deselected in 0.19s)
PASS A6 정규화(표기 차이만 자동 승인, 숫자·버전 다른 쌍 후보 아님, name_pairs 전역 미반영) (8 passed, 5 deselected in 1.17s)
PASS A7 묶기(채널 넘는 조건, confidence 미달, 평균 연결, 레포만 묶음, 1개짜리, 재실행 run 보존) (16 passed in 0.91s)
PASS A8 선별 검증(리드 1, 개수 범위, 범위 밖 합치기·나누기 거부, relation은 과거 대조 후보 안, 입력 순서 cluster_id, reason 값·채널 수 대조, 재시도·대체, 점수 동점은 관심 유사도(C-21 수정), 영상 자리(C-20)) (21 passed, 23 deselected in 1.30s)
PASS A9 코드 검사(수치 대조 값 비교·제목·도식 칸까지·단위 환산 미허용, 막대 단위·빈 단위·라벨 단위, anchor, 도식 상한, 금지어·전망형, contributions 채널, points 자르기, 음차 정본, 자동 수정은 반려 아님, 경고) (18 passed, 31 deselected in 0.62s)
PASS A10 라운드(상한 3, 코드 반려도 셈, 같은 이슈 2회 check, 지적 안 된 칸 되돌림, 1부터 센 위치 바로잡기) (2 passed, 42 deselected in 1.45s)
PASS A11 저장(마이그레이션 30~35, 재실행 run 보존·current_run_id, topic_evidence = 최종판 refs, 토픽 수준 확인 필요) (2 passed, 22 deselected in 1.64s)
PASS A12 실행 요약 JSON 형식과 표에서 다시 계산한 값 일치 (1 passed, 7 deselected in 1.38s)
PASS A13 저장값만으로 예시 JSON 토픽 칸(매핑 함수 초안: numbers·events·og 출처 origin·checks) (2 passed, 6 deselected in 1.27s)
PASS A14 README S5 상태, S5_report 체크리스트, reports/eval 역할·모델별 최신 1개(+ 라벨 기준 실행)
```
- 이전 제출(10/09 21:03)의 A14 FAIL(S2 때 item_card 평가 결과)은 사용자가 지운 뒤 커밋(`42d7687`)
