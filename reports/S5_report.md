# S5 리포트: 주간 브리핑

> 진행 중. 맥락이 끊기면 아래 체크리스트를 보고 이어 간다.

## 진행 체크리스트
- [x] 0 환경 점검·정리(5.0) + handoff 묶음 커밋 + README 맞춤
- [x] 1 공통 수정(5.1) → 재료 품질 개선(P4 1·2·3·6·7) → 대상 두 주 재료 생성·재생성(5.2) — W41(10/5~10/9)까지. W42는 10/19 이후
- [x] 2 근거 목록(EvidencePack) + 표기 정규화 v0(5.3)
- [x] 3 묶기 + 과거 대조 → 묶기 리포트(5.4) — **멈춤: 리뷰 확인 대기**(W41 리포트)
- [ ] 4 편집장 선별(5.5)
- [ ] 5 작성자 + 코드 검사(5.6, 5.7)
- [ ] 6 검수자 + writer_revise 루프(5.8)
- [ ] 7 weekly + 저장 + 실행 요약(5.9, 5.10)
- [ ] 8 관문 B(W42 + W41), 리포트, PR

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
