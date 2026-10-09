# S5 리포트: 주간 브리핑

> 진행 중. 맥락이 끊기면 아래 체크리스트를 보고 이어 간다.

## 진행 체크리스트
- [x] 0 환경 점검·정리(5.0) + handoff 묶음 커밋 + README 맞춤
- [ ] 1 공통 수정(5.1) → 재료 품질 개선(P4 1·2·3·6·7) → 대상 두 주 재료 생성·재생성(5.2)
- [ ] 2 근거 목록(EvidencePack) + 표기 정규화 v0(5.3)
- [ ] 3 묶기 + 과거 대조 → 묶기 리포트(5.4) — **멈춤**
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
