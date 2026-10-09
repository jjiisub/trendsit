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
| 7 | `reports/eval/` 역할별 최신 1개: **삭제는 자동 모드가 막아 사용자 몫**(아래 "사용자 필요"). 지울 34개 목록은 계산해 둠. 남길 12개 = 역할·모델별 최신 전체 실행 + 라벨 파일이 가리키는 실행(일치율 재현용) |
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

### [사용자 필요] 자동 모드가 막은 것
- `reports/eval/` 정리(5.1-7, E10): `git rm`이 막혔다. 지울 34개(역할·모델별 최신 전체 실행과 라벨이 가리키는 실행만 남김):
```
git rm reports/eval/editor_plan_generate_20261008-122719.json reports/eval/editor_plan_generate_20261008-183430.json reports/eval/item_card_generate_20261008-105652.json reports/eval/item_card_generate_20261008-111105.json reports/eval/item_card_generate_20261008-113213.json reports/eval/item_card_generate_20261008-114316.json reports/eval/item_card_generate_20261008-120230.json reports/eval/item_card_generate_20261008-120344.json reports/eval/item_card_generate_20261008-152008.json reports/eval/repo_analyst_generate_20261008-164718.json reports/eval/repo_analyst_generate_20261008-165334.json reports/eval/repo_analyst_generate_20261008-182928.json reports/eval/repo_oneliner_generate_20261007-153955.json reports/eval/repo_oneliner_generate_20261007-154045.json reports/eval/repo_oneliner_generate_20261007-154143.json reports/eval/repo_oneliner_generate_20261007-155746.json reports/eval/repo_oneliner_generate_20261007-165425.json reports/eval/repo_oneliner_generate_20261007-165530.json reports/eval/repo_oneliner_generate_20261007-165657.json reports/eval/repo_oneliner_generate_20261007-220820.json reports/eval/repo_oneliner_generate_20261008-071529.json reports/eval/repo_oneliner_generate_20261008-104252.json reports/eval/repo_oneliner_generate_20261008-140318.json reports/eval/repo_oneliner_judge_20261007-154252.json reports/eval/text_analyst_generate_20261008-122802.json reports/eval/text_analyst_generate_20261008-185127.json reports/eval/text_analyst_generate_20261008-185514.json reports/eval/text_analyst_generate_20261008-191228.json reports/eval/text_analyst_generate_20261009-001826.json reports/eval/video_summary_generate_20261008-135012.json reports/eval/video_summary_generate_20261008-135824.json reports/eval/video_summary_generate_20261008-140606.json reports/eval/video_summary_generate_20261008-140800.json reports/eval/video_summary_generate_20261008-153823.json
```
- 원격 `docs-s2s4-handoff` 브랜치(스쿼시 병합, 0단계)
