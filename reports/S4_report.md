# S4 리포트: 영상 분석가 (전사 + 슬라이드 판독, 맥)

## 1. 한 줄 요약
`trendsit video run --queue q.json`(또는 `--video-id ID --mode whisper+slides`)이 영상을 받아 로컬 mlx-whisper로 전사하고, 슬라이드 프레임을 골라 판독하고, 발화에 없고 화면에만 있는 수치를 시각 근거 id와 함께 뽑아 요약·타임라인과 함께 VideoDigest로 저장한다. Tech Bridge 10편에서 1차 처리 10/10, 판독 139/140장, 슬라이드 전용 수치 124개. 관문 B(잠정, labeler opus-5.5): 판독 수치 정확도 98.2%, 포착률 87.9%로 통과, video_summary Q1 67%·Q2 42%·Q3 75%로 미달(설계 결정 D2·D5대로 4회차 개선 없이 기록, S5에서 다룸).

## 진행 체크리스트
- [x] 준비물 확인(2장)
- [x] 1차 처리(`collect/video/`), 계약 검사, 실제 영상 픽스처 3편
- [x] 대조(align)
- [x] `s2-0-base` 병합 뒤 main 받기 → 마이그레이션 20, video 선택 묶음, video.yaml 설정 검사
- [x] 이미지 입력(공통 코어, 별도 커밋) → 역할 `video_slide`, `video_summary`, enforce
- [x] 파이프라인, 저장, CLI(`video run·purge·report`)
- [x] 관문 B(실제 영상 10편), 비교, 검증 산출물(`reports/S4_video/`)
- [x] 관문 A 전부 PASS
- [x] 서브에이전트 리뷰(13건 반영), PR
- [x] 관문 B 2차 채점 기록(labeler opus-5.5, 잠정): `eval/labels/video_summary.csv` 12행, `reports/S4_video/README.md` 체크 칸
- [x] 2차 리뷰(PR #7 댓글) 4장 체크리스트 반영(9장)
  - 채점표 준비 완료: 판독 수치는 `reports/S4_video/README.md` 4장(124행 전부 썸네일, '쓸 수 없음' 칸), 요약은 `reports/S4_video/label_summary.md`(12절, Q1~Q3 칸). `scripts/s4_label_sheets.py`

## 준비물 (S4_TASK 2장)
| 준비물 | 결과 |
|---|---|
| ffmpeg, ffprobe | 8.1.2 (Homebrew) |
| yt-dlp용 JS 런타임 | deno 2.9.7, node v26.8.2도 있음 |
| `video` 선택 묶음 | 병합 전 `uv pip install`, 병합 뒤 `video = ["yt-dlp>=2026.8.19", "mlx-whisper>=0.4.3; sys_platform == 'darwin'"]` → `uv lock`. yt-dlp 2026.8.19, mlx-whisper 0.4.3, mlx 0.32.3 |
| Whisper 모델 | `large-v3-turbo` 이미 캐시에 있음 |
| generate 모델의 이미지 입력 | 됨. qwen3.8-27b(DeepInfra 고정)에 768px 프레임 1장: 입력 386토큰(이미지 약 300), 0.0002달러. 질문 파일 없음(`scripts/check_image_input.py`) |
| Tech Bridge 자막 형태 | 하드 자막(영어 노란 한 줄 + 한국어 흰 두 줄). 채널이 왼쪽 위에 구간 제목과 "Source: 날짜 · 출처"를 덧붙이고, 행사 영상은 슬라이드 옆에 행사 배너가 있다. 9/1 이후 60편 모두 업로더 자막 트랙 없음 → `video_slide`에 자막·채널 표시·배너 제외 규칙과 예시 |
| 디스크 | 여유 759GB, 1080p 유지 |

## 2. 관문 A
맥에서 `bash scripts/verify_s4.sh`(video 묶음 포함, 맥 전용 테스트까지 실행):
```
PASS A1 verify_s0.sh 10개, verify_s1.sh 24개 전부 PASS
PASS A2 ruff 0, pytest 286 passed in 66.11s (0:01:06) (건너뜀 0건은 맥 전용 표시뿐)
PASS A3 check-config 통과(OK 설정 6개, 역할 5개) + 잘못된 mode·상한이 경로를 짚어 실패 (6 passed, 35 deselected in 0.85s)
PASS A4 video_slide, video_summary 역할 md 검사 통과, 예시 3개 (4 passed, 23 deselected in 1.09s)
PASS A5 픽스처 MediaResult 계약 통과 + 깨뜨린 사본(시간 역순, 상한 초과, 작업 폴더 밖 경로 등) 실패 (2 passed, 39 deselected in 0.71s)
PASS A6 큐 계약 JSON → mode별 설정, captions에 수동 자막 없으면 건너뜀(올리지 않음) (12 passed, 45 deselected in 3.33s)
PASS A7 suspect_hallucination·empty에서 전사를 근거로 쓰지 않음, 둘 다 없으면 내용 없음 + attention (7 passed, 21 deselected in 4.16s)
PASS A8 대조: 다른 표기의 같은 수치는 대조됨, 30초 밖은 slide_only, check는 따로 (47 passed in 0.55s)
PASS A9 enforce: 판독 수치(ocr_text 안), 표기 쌍, 근거·타임라인 초 범위(모의 LLM) (3 passed, 9 deselected in 0.43s)
PASS A10 이미지 입력: 메시지 모양, 캐시 키가 이미지 바이트에 따름, 기록·캐시에 원본 없음, 예상 비용 (5 passed, 7 deselected in 0.70s)
PASS A11 보관: purge는 7일 지난 작업 폴더만, DB 텍스트 유지, 8주 지난 segments 텍스트 삭제 (2 passed, 55 deselected in 1.75s)
PASS A12 마이그레이션 대역: S4 번호 모두 20~29, video_ 표만, 묶음 A 번호와 순서 무관 (2 passed, 14 deselected in 11.34s)
PASS A13 자동 자막 경로 없음(자동 자막만 있는 메타데이터에서 captions는 건너뜀) (2 passed, 39 deselected in 7.62s)
PASS A14 README(기능, 빠른 시작, 시스템 의존성), DEVELOPMENT.md 명령표, 리포트
```

## 3. 관문 B (실제 영상, 맥)
대상: `reports/S4_video/queue_gateB.json`(사람이 만든 큐). 슬라이드 발표 7편 `whisper+slides`, 대담·인터뷰 3편 `whisper`. 상세와 확인 칸은 [`reports/S4_video/README.md`](S4_video/README.md), 요약 품질은 [`S4_quality.md`](S4_quality.md).

| 항목 | 기준 | 결과 |
|---|---|---|
| 1차 처리 | 10편 모두 성공 또는 실패 이유, 계약 검사 전부 통과 | 10/10 성공, 계약 위반 0. 전사 품질 10편 모두 ok. 10~31분 영상 전사 58~150초(모델 적재 포함) |
| 판독 수치 정확도 | slide_only_facts가 화면에 있는 비율 90% | **잠정, labeler opus-5.5: 98.2% 통과**(화면에 있음 111 / 없음 2 / 판단 불가 11, 판단 불가 제외. 판단 불가를 실패로 보면 89.5%). 쓸 수 있는 수치만 60/62 = 96.8%. 124개(영상별 44, 3, 1, 43, 26, 7, 0), 판독 139/140장 |
| 슬라이드 전용 정보 포착률 | 80% | **잠정, labeler opus-5.5: 87.9% 통과**(놓침 4 / 놓치지 않음 29 / 판단 불가 2. 보수 82.9%). 놓친 수치는 브리핑에 쓸 수 있는 결과·규모 수치만 셈 |
| video_summary | Q1~Q3 각 80% + judge·라벨 일치 80% | **잠정, labeler opus-5.5: Q1 8/12 67%, Q2 5/12 42%(두 부분 라벨 규칙을 완화하면 9/12 75%), Q3 9/12 75% → 미달.** judge는 12/12 모두 pass(그중 4건은 enforce 후 출력으로 채점) → judge·라벨 일치 12행 Q1 66.7%, Q2 41.7%, Q3 75%(원래 judge를 받은 8행만 보면 Q1 75%, Q2 50%, Q3 100%). 불일치는 모두 judge가 놓친 fail(근거 창 밖 내용을 합친 포인트, 그 초에 아직 나오지 않은 내용을 붙인 라벨) |
| video_summary 코드 채점 | (내부) 코드 채점 전부 통과 | 나란히: 원래 출력 8/12(모델 품질) / 통과 판정 11/12(코드 소유 칸 `name_pairs`만 enforce 후, D2-1) / enforce 후 전체 12/12. 남은 1건은 S-bRN-avZ4Q 포인트 하나의 근거 id 5개(`key_points`는 코드 소유 칸이 아니라 원래 값으로 판정, 저장 출력은 D2-2 상한으로 3개) |
| "쓸 수 없음"(S5 묶기 근거) | - | 62/124(50%): 도식 예시 29, UI 값 28, 슬라이드 번호 2, 기타(연대·지표 이름) 2, 버전 1 |
| 비교(whisper만 vs whisper+slides) | 슬라이드가 더한 정보 | 2편, 같은 전사로 요약만 다시. 잘못 들은 수치가 화면 값으로 바뀜("Sweebench Pro 88%" → "SWE-Bench Pro 80.3%", "약 74개" → "73개"), 발화에 없던 그래프 값("Q3 2025 78 → Q2 2026 114") 추가 |
| captions 비교 | 수동 자막이 있는 1편 | 하지 못함. Tech Bridge 60편 모두 업로더 자막 트랙 없음(하드 자막) |

### 반복 기록
| 역할 | 회 | 바꾼 것 하나 | 전후 | 프롬프트 |
|---|---|---|---|---|
| video_slide | (개발 중, 관문 B 전) | 슬라이드 사각형 밖·축 눈금·작은 데이터 레이블 규칙, 함정 예시를 그래프로 | 그래프 프레임 2장: 축 눈금 8개를 수치로 → 0개, 행사 배너 → 제외 | - |
| video_slide | 설정 | whisper+slides 해상도 768 → 1024 | 데이터 레이블 4개 중 1개 → 4개 맞음 | - |
| video_slide | 1 | max_tokens 900 → 1600 | 판독 실패 3/140 → 1/140 | 같음 |
| (대조 코드) | 1 | 수치가 아닌 판독 제외(단위 없는 연도, 이름에 붙은 버전, 슬라이드 번호) | 13개 제외(excluded로 기록) | - |
| video_summary | 1 | max_tokens 1800 → 3500(챕터 20여 개 영상에서 JSON이 잘림) | 요약 실패 1/10 → 0/10 | `b671…` 이전 |
| video_summary | 2 | md 문구: 포인트 명사형·6개 상한, 표기 쌍 screen은 판독에 있는 표기만 | 기록상 2/12 → 8/12. 같은 최종 채점기로 다시 매기면 1회 4/12 → 2회 8/12(채점기 수정 몫 +2, 프롬프트 몫 +4) | `b671779982e1` |
| video_summary | 3 | 예시 1에 표기 쌍에서 빼는 경우 추가 | 8/12 그대로, 예시의 "Llama 3.1" 쌍을 베낀 출력이 생김 → 2회로 되돌림 | `8ee3fccb5714`(폐기) |

채점기 수정(이 스펙의 채점기, 통과를 위한 기준 완화가 아니라 오탐 제거라 따로 적음). 2회·3회 때 프롬프트와 같은 실행에서 바꿔 효과가 섞였으므로, 모든 회차의 저장된 출력을 최종 채점기로 다시 매겨 위 표에 나눠 적음(1회 4/12, 2회 8/12, 3회 8/12). 문턱값(코드 채점 전부 통과)은 그대로:
- 문체 검사는 `summary` 칸만(`ROLE_STYLE_FIELDS`, S2~S3 브랜치와 같은 코드). `chapters`는 업로더 제목을, `name_pairs`는 화면 표기를 그대로 옮긴 칸이라 해요체 검사 대상이 아님("…인가요?" 같은 챕터 제목이 실패로 잡혔음)
- 포인트·라벨 명사형 검사는 자체 정규식. 공통 `SENTENCE_END`, `HAEYO`는 "개요", "필요"처럼 요로 끝나는 명사도 문장 끝으로 잡음(공통 채점기 문제, 6장 질문)

남은 코드 채점 실패 4건(2회 프롬프트): 표기 쌍 3건(screen이 판독에 없거나 전사와 같은 표기. enforce가 저장 전에 지움), 포인트 하나에 근거 id 5개 1건(md는 1~3개)

### 가장 나쁜 사례(판독)
1. xRZHLI5SPWo 966초: 가치 흐름도 그림 속 예시 값 29개를 수치로 판독, 일부는 잘못 읽음("CT = 6 s"를 8 s로). 화면에는 있으므로 "화면에 있음" 라벨로는 잡히지 않을 수 있지만 브리핑에 쓸 수치는 아님
2. 31XD1O74pks 488초: 터미널을 흉내 낸 데모 슬라이드의 실행 시간·줄 수(0.8s, 42 lines)를 수치로 판독(frame_kind demo가 맞음)
3. 확신도 check를 한 번도 쓰지 않음(140장). 1024px로 올린 뒤 흐린 값이 줄었지만, 모델이 자신 없는 값도 high로 내는지는 판단 불가 11줄을 원본 해상도로 확인해야 함(사람 확인 부채, CONTEXT 17장)

## 4. 결정한 것(스펙에 없어서 정한 것과 이유)
1. 프레임 reason은 계약의 네 값으로: 스킬의 keyframe 후보는 scene-change로, 발화 공백 신호(gap)는 transcript-cue로 묶음. 후보 엔진은 `frames_meta.engine`에 남음
2. 프레임 경로는 작업 폴더 기준 상대 경로, `work_dir`는 절대 경로. 계약 검사가 "작업 폴더 안"을 경로 문자열로 확인(절대 경로, `..` 금지)
3. 프레임마다 `segment_index`·`spoken_text` 칸은 항상 있고, 프레임 시각 2초 안에 발화가 없으면 null·빈 문자열(스킬과 같은 허용 오차)
4. 전사 segments는 시간 역순·겹침·구간 밖·빈 글자를 전사 단계에서 정리(계약의 "겹침 없음"). 실측: 7분 영상 끝에서 글자 없는 segment 31건, 깨진 문자(U+FFFD)
5. 전사 품질이 ok가 아니면 대조에서도 발화(segments와 프레임 spoken_text 모두)를 없는 것으로 봄(환각 전사가 화면 수치를 "발화에 있음"으로 덮지 않게, `align(spoken_usable=False)`)
6. 마이그레이션은 20번 하나에 표 네 개(한 트랜잭션). 21~29는 비워 둠
7. `video` 명령은 `--spec`과 `TRENDSIT_SPEC`이 없으면 S4로 기록
8. 1차 처리 결과를 작업 폴더에 `media_result.json`으로 남김(7일 정리와 함께 지워짐). `--reuse-media`, `--from-json`으로 전사 없이 판독 이후만 다시(관문 B 반복이 전사 없이 돎)
9. 요약 입력의 전사는 `[초] 문장` 줄 한 문서(id `vd:{item}@{구간 시작}`), 판독은 프레임별 문서(id `vd:{item}@{초}`, 같은 글자의 슬라이드는 하나만). 전사도 판독도 없으면 LLM을 부르지 않음
10. 이미지 입력: 메시지·캐시 키·실행 기록에는 `image:sha256=…`와 경로만, 전송 직전에만 data URI. 캐시 키는 경로가 아니라 바이트 해시(폴더를 옮겨도 캐시 유지). 예상 비용은 장당 1500토큰(실측 약 300, 상한 쪽)
11. `RoleOutput` 등록: main의 `_merge`는 스펙 모듈이 먼저 읽히면(순환) 빈 모듈을 보므로 `artifacts_video.py` 끝에서도 등록(S2~S3 브랜치의 `register_schemas`로 병합 때 바꿀 수 있음)
12. 평가 픽스처에 파생 2편(그중 `derived_empty`는 전사도 판독도 없는 경우로, 실제 파이프라인은 LLM을 부르지 않는 길이라 eval에서만 모델을 부른다. 모델이 지어내지 않는지 보려는 것)(전사 품질을 suspect_hallucination, empty로 바꾼 사본, 이름 `derived_`). 실제 Tech Bridge 영상은 전사가 모두 ok라 Q3(품질이 나쁠 때 지어내지 않음)를 재려고 추가. 라벨 파일은 12행
13. `eval/graders.py` 끝에 스펙별 채점 모듈을 읽는 `_load` 자리와 `ROLE_STYLE_FIELDS`(S2~S3 브랜치와 같은 코드)
14. 수치 정규화: 한 글자 크기 단위는 대문자 K·M·B·T와 소문자 k만(소문자 m·b·t는 미터·바이트·톤일 수 있음). unit 칸이 B 하나면 10억으로 봄(슬라이드에서 바이트는 GB, MB로 씀). 영어 수사는 'and'를 hundred·thousand 뒤에서만 잇고 'two three'처럼 이어진 단위 수사는 따로 셈. 한국어 천만·백만·천억, '만큼'의 만은 크기 아님

## 5. 스펙과 다르게 한 것과 이유
1. whisper+slides 기본 해상도 1024(스펙: 기본 768, 수치 많은 발표는 1024). 768px에서 그래프 데이터 레이블 4개 중 3개를 축 눈금으로 짐작해 틀렸고(high 확신도), 1024px에서 4개 모두 맞음. 장당 약 0.0001달러 더 듦. 영상 처리 지시 계약에는 해상도 칸이 없어 편집장 계획이 1024를 고를 방법이 없음. `--res`로 영상별 덮어쓰기 가능
2. 대조 전에 수치가 아닌 판독을 코드로 제외(연도, 이름에 붙은 버전, 슬라이드 번호). md에 이미 금지가 있는데 모델이 따르지 않아 COMMON 3장 순서상 코드 규칙으로. 판독 자체는 그대로 저장하고 대조 단계의 `excluded`에 이유와 함께 기록
3. captions 비교(관문 B)는 대상 영상이 없어 하지 않음(3장)

## 6. 남은 문제, 다음 스펙 제안
- 질문(설계 세션)
  - 공통 채점기 `HAEYO`, `SENTENCE_END`가 "개요", "필요" 같은 명사를 해요체·문장 끝으로 잡음. 다른 역할에도 영향(S4는 자체 정규식으로 피함)
  - 평가 픽스처 `eval/fixtures/video_summary/`에 전사 전문이 들어감(12개, 336KB). item_texts는 8주 뒤 지우는 원칙과 맞추려면 픽스처를 앞부분만 두거나 비공개 유지 확인이 필요
  - `reports/S4_quality.md`가 113KB: 공통 `write_quality`의 "가장 나쁜 사례"가 중첩 입력(전사 문서)을 줄이지 않고 씀
  - 작업 폴더마다 `data/budget_state.json`이 따로라 이 폴더의 단계 기준값은 S4 시작 때의 키 사용액($1.079). 단계 사용액은 키 기준이라 다른 폴더 사용분도 잡히지만 그 이전 사용분은 빠짐
- `uv run`은 선택 묶음을 지운다. 영상 명령과 관문 A는 `uv run --extra video`(README, DEVELOPMENT에 적음). S2~S3의 embed 묶음도 같은 문제
- `roles/video_slide.md`의 "가로 768px 안팎" 문구를 1024로(리뷰 9, 다음 판독 개선 때)
- 확신도 check가 0건: 판독 정확도가 낮게 확인되면 다음 개선은 "자신 없는 값은 check" 예시 보강이나 1280px
- 도식 속 예시 값(가치 흐름도 등)은 수치로 쓰면 안 되는데 판독이 그대로 옮김. 묶기(S5)에서 slide_only_facts를 쓸 때 "도식" 판독(같은 프레임 수치 10개 이상 등)을 낮게 보는 규칙 제안
- 편집장 계획 mode 기준(실측): whisper+slides는 20분 발표에 전사 약 2분 + 판독 20장 약 1.5분, 비용 약 0.011~0.016달러(판독 20장 약 0.011 + 요약 약 0.003). whisper만은 약 0.003달러. 대담·인터뷰는 whisper로 충분(슬라이드 없음)
- `config/deep.yaml` 영상 예산 실측: 영상당 프레임 20장, 판독 장당 입력 약 2,500토큰(시스템 프롬프트 포함, 1024px), 요약 입력 영상 길이에 따라 4천~1만5천 토큰
- 묶기(S5)에서 VideoDigest 쓰는 법: key_points의 `vd:` 근거 id를 ItemCard quotes처럼, slide_only_facts는 "발표 슬라이드 기준" 수치로, timeline은 `?t=` 링크로. 같은 주 글과 연결할 때 name_pairs의 화면 표기를 정규 표기로
- 판독이 출력 상한을 넘는 큰 표 1장(31XD1O74pks): 표가 크면 max_tokens를 넘김. 필요하면 표 행 수 상한을 md에

## 7. 사용액 (`trendsit cost --spec S4`)
| 스펙 | 모델 | 호출 | 캐시 적중 | 입력 토큰 | 출력 토큰 | 사용액(달러) |
|---|---|---|---|---|---|---|
| S4 | qwen/qwen3.8-27b | 801 | 434 | 3,341,312 | 304,069 | 0.414637 |
| S4 | google/gemini-3.8-flash | 46 | 25 | 460,320 | 20,258 | 0.106554 |
| 합계 | | | | | | 0.521191 |

- 상한 0.80 중 0.521(1차 리뷰 반영 뒤 재채점, 2차 리뷰 D2-4 judge 4건 0.025, R7 실측 0.0002 포함). 단계별: 이미지 입력 확인 0.0002, 개발 중 판독·요약 약 0.07, 관문 B 10편 판독·요약 약 0.15, 판독 재실행(max_tokens, 1024 반영) 약 0.08, 요약 개선 3회 eval 약 0.18(대부분 긴 전사 재생성), 채점 약 0.08
- 영상 한 편(whisper+slides, 20분 안팎): 약 0.011~0.016달러

## 7-1. README 갱신, 위키 메모
- README: 핵심 기능(영상 분석가 S4 완료), 역할 표, 빠른 시작(`video run`, `purge`), 시스템 의존성(ffmpeg, JS 런타임, `--extra video`), 폴더 구조, 성과 행, 로드맵 체크
- DEVELOPMENT.md: 명령표 6행, "영상 분석가 (S4)" 절
- 위키 메모
  - 768px에서는 그래프의 작은 데이터 레이블을 축 눈금으로 짐작해 high로 냄 → 1024px에서 맞음. 이미지 토큰은 장당 약 300(예상의 4분의 1)
  - Whisper가 오디오 끝에서 글자 없는 segment와 깨진 문자를 줄줄이 냄(7분 영상 31건). 같은 영상인데 전사 시간 80초 ↔ 212초. segment 정규화에서 지움
  - 하드 자막 영상: 영어·한국어 자막과 채널 덧붙임, 행사 배너를 판독에서 빼는 규칙이 없으면 발화 수치가 화면 수치로 둔갑
  - 요약 JSON이 출력 상한에 잘리면 같은 상한으로 재시도해 3번 다 실패(업로더 챕터 20여 개). 재시도는 상한을 바꾸지 않음
  - 예시에 표기 쌍 빼는 경우를 넣자 예시의 "Llama 3.1" 쌍을 다른 영상에 베낌 → 되돌림
  - 같은 전사에 슬라이드를 더하면 잘못 들은 수치가 화면 값으로 바뀜(SWE-Bench Pro 88% → 80.3%)

## 8. 서브에이전트 리뷰 지적과 처리
새 컨텍스트의 리뷰 에이전트(code-reviewer)에게 스펙 문서, diff, 이 리포트만 주고 대조 리뷰를 받았다. 지적 13건 모두 반영하거나 이유를 적었다.

| # | 지적(심각도) | 처리 |
|---|---|---|
| 1 | captions 모드의 받기 오류, 받은 파일 ffprobe 실패가 MediaFailed가 아니라서 fetch_log·video_runs 없이 새고 CLI 큐 전체가 멈춤(높음) | captions의 메타데이터·자막 받기 1회 재시도 후 MediaFailed, ProbeError → MediaFailed, CLI는 영상별로 예상 밖 오류를 기록(video_runs failed + attention)하고 다음 영상으로. 테스트 3개 |
| 2 | `--from-json`이 mode를 확인하지 않아 whisper 지시에 슬라이드 판독(높음) | `analyze`가 저장한 결과의 mode가 지시와 다르면 판독 없이 실패 기록, CLI도 거부. 테스트 |
| 3 | 전사 품질 미달이어도 프레임 spoken_text가 대조에 들어감(중간) | `align(spoken_usable=False)`면 spoken_text도 쓰지 않음. 결정 5 문구 고침. 테스트 |
| 4 | 수치 정규화 오류("five and ten" → 15, 단위 m을 백만으로, "5천만" → 5천 등)(중간) | 수사 묶음 규칙, 대소문자 구분 크기 단위, unit 크기 단위 목록, 한국어 복합 단위. 결정 14. 테스트 12개 |
| 5 | verify_s4.sh A6가 `-k` 두 번이라 큐 테스트가 빠짐(중간) | `-k "queue or captions"` 하나로 |
| 6 | 채점기와 프롬프트를 같은 회차에 바꿔 효과를 나눌 수 없음(중간) | 모든 회차 출력을 최종 채점기로 다시 매겨 반복 기록에 나눠 적음(채점기 +2, 프롬프트 +4). "~까요" 미검출도 고침 |
| 7 | enforce가 check 수치("1?8")를 ocr_text에 없다고 지움(중간) | check는 글자 일치 규칙에서 제외(확인 필요 목록으로). 테스트. 관문 B 판독에서 check가 0건이었던 것과의 관계는 확인 못 함(그 영상들의 판독 출력에도 check가 없었음) |
| 8 | 계약 검사가 mode와 transcript_source를 묶지 않음(중간) | captions ⇔ manual 검사 추가, 깨뜨린 사본에 추가 |
| 9 | video_slide md의 "가로 768px 안팎"이 1024와 다름(낮음) | md는 그대로 둠: 고치면 프롬프트 해시가 바뀌어 관문 B 판독 140장이 다른 버전이 됨. 다음 판독 개선 때 함께 고침(6장) |
| 10 | 60분 상한 이유가 log에 없음(낮음) | 구간을 정한 이유(`resolve_span` 문구)를 log에 |
| 11 | PriceUnknown이 영상별로 기록되지 않음(낮음) | BudgetExceeded와 같이 처리 |
| 12 | video_frames 기본 키(video_id, t)로 같은 시각 프레임의 판독이 조용히 덮임(낮음) | 저장 때 판독이 있는 쪽을 남기고 빠진 수를 step(attention)으로. 테스트 |
| 13 | judge 8/8이 보이는 것보다 약함(코드 실패 4편은 judge 안 받음, derived_empty는 실제로는 LLM을 안 부르는 길)(낮음) | 결정 12와 3장에 적음. 2차 리뷰 D2-4로 4건도 enforce 후 출력으로 judge 채점(12행) |

리뷰 반영 뒤 관문 B 결과를 최종 코드로 다시 계산(판독·요약은 캐시): 영상별 수치와 요약은 같음. 파생 suspect 픽스처만 대조가 바뀌어 다시 생성·채점(0.009달러).

## 스킬에서 옮긴 코드 (맥 `~/.claude/skills/youtube-analyze/scripts/`)
| TrendsIT 파일 | 원본 | 옮긴 것 | 바꾼 것 |
|---|---|---|---|
| `collect/video/ff.py` | `media_util.py`, `media_source.py` | ffprobe 호출, 스트림으로 kind 판정, 길이 올림 | 버전·장치 기록 추가 |
| `collect/video/source.py` | `media_source.py` | 유튜브 URL 판별, 재생목록·채널 거부, 포맷 선택자 2단(재시도), JS 런타임 찾기, 받은 파일 찾기 | 로컬 파일 소스 제거, 입력은 video_id, 수동 자막 받기와 VTT 해석 추가(자동 자막 경로 없음) |
| `collect/video/transcribe.py` | `transcribe.py` | 16kHz WAV, 무음 비율, 다지점 언어 감지, segment 정규화, 품질 신호와 판정(문턱값 그대로) | 겹침 보정, 빈 글자·U+FFFD 제거, whisper·감지 함수 주입(테스트) |
| `collect/video/frames.py` | `video_frames.py` | FrameEngine 전체(썸네일 후보, 중복 제거 8.0, 적응형 예산, 정밀 seek 2단, 남은 예산 채움) | 상한 20(설정), reason 네 값, 지정 시각(explicit)·구간 밀도 배수 제거 |
| `collect/video/cues.py` | `frame_cues.py` | 한국어·영어 화면 지시 표현 목록과 점수, 4초 창, 발화 공백 신호, 프레임별 발화 | 모든 프레임에 칸(없으면 null), gap도 transcript-cue |
| `collect/video/workspace.py` | `workspace.py` | 원자적 커밋, 재사용 전 4단 검사, 루트 밖 방어, purge | 루트 `data/media`, 캐시 경고 제거 |
| `collect/video/contract.py` | `media_analyze_validate.py` | C3, C8, C9, C10, C13, C14 | segments 겹침 금지, 경로가 작업 폴더 안, mode별 프레임 유무 |
| `collect/video/process.py` | `media_analyze.py` | 전사 ∥ 프레임 1차 동시 실행, 품질 미달이면 예산 상향, 발화 신호 → 채움 → 발화 붙이기 | 영상 처리 지시(mode), 60분 상한 구간, captions 경로, 전사 1회 재시도, MediaResult |

## 공통 코어 수정
- 이미지 입력(커밋 `feat(s4): 이미지 입력(공통 코어 수정)`): `core/images.py`(새 파일), `core/llm.py`(예상 비용에 이미지, 전송 직전 data URI), `core/cache.py`(키에서 이미지 경로 제외), `core/role.py`(이미지 칸 → 메시지 부분)
- `core/config.py`: `video.yaml` 등록 한 줄(`core/config_video.py`의 VideoConfig)
- `eval/graders.py`: `ROLE_STYLE_FIELDS`, `AGGREGATES` 선언, `code_grade`의 문체 칸, 끝의 `_load` 자리(모두 S2~S3 브랜치와 같은 코드)

## 마이그레이션 번호
- 20: `video_runs`, `video_segments`, `video_frames`, `video_digests`

## 9. 2차 리뷰(PR #7 리뷰 댓글, 설계 결정 D1~D4) 처리
채점 방식(D1-3): MVP 동안 관문 B 사람 채점은 하지 않고 opus-5.5(설계 세션)가 2차 채점. 이 리포트의 관문 B 판정은 모두 잠정이다. 라벨은 `eval/labels/video_summary.csv`(labeler 칸 `opus-5.5`), 판독 체크 칸은 `reports/S4_video/README.md` 3·4장(표 위에 labeler 표시). 사람이 나중에 확인할 것은 `docs/CONTEXT.md` 17장.

| # | 지적 | 처리 |
|---|---|---|
| R1 | 코드 소유 칸(`ENFORCED_FIELDS`) 장치 없음 | 공통 채점기에 장치(별도 커밋 `c0c3178`): `graders.ENFORCED_FIELDS`, `basis_output`, `summarize`의 통과 판정(`code_pass_basis`), `run_eval`의 `code_basis`와 judge 대상(칸을 선언한 역할은 원래 출력이 실패해도 enforce 후 출력이 통과하면 그 출력, `judged_output` 표시), `agreement`에 표시. 칸을 선언하지 않은 역할은 동작 그대로. video_summary는 `name_pairs` 선언. 테스트 `tests/test_eval_enforced_fields.py` |
| R2 | 표기 쌍 spoken ≠ screen 규칙 없음 | enforce와 코드 채점에 같은 표기 제외(`same_spelling`). 띄어쓰기만 다른 쌍은 상수 `NAME_PAIR_SPACING_ONLY_SAME = True`로 같은 표기(제외), 대소문자만 다른 쌍은 남김. 테스트 |
| D2-2 | 근거 3개 상한 | `MAX_EVIDENCE = 3`, 넘으면 앞 3개(enforced 기록). 테스트 |
| D2-4 | judge 못 받은 4건 | enforce 후 출력으로 judge 채점(0.025달러, 요약 출력은 재생성 없음). 4건은 "judge = enforce 후 출력, 라벨 = 원래 출력"(`eval --agreement` 출력에도 표시) |
| 라벨 | labeler 칸 | `make_labels`가 `labeler` 칸을 보존, `agreement`·`eval --agreement`·품질 리포트가 "labeler opus-5.5, 잠정"으로 표시(별도 커밋 `02a1255`, 공통 코어). 테스트 `tests/test_eval_labeler.py` |
| R3 | 병합 충돌 예상 | #6이 main을 받을 때 처리(이 PR은 할 것 없음) |
| R4 | `eval/graders.py`는 #6의 부분집합 | PR 설명 문구 정정: #6에는 `NOUN_YO`와 `summarize`의 AGGREGATES 적용이 더 있음. 이 PR은 그 부분집합 + R1 장치 |
| R5, R6 | ImageError 경로, 중첩 이미지 칸 | S5 공통 수정 PR(리뷰 처리대로) |
| R7 | `IMAGE_TOKENS_EST` 주석 | 1024px 실측으로 갱신: 같은 프레임·문구에서 1024px 요청 626토큰(이미지 약 540), 768px 386토큰(약 300), 관문 B 판독 1장 평균 입력 약 3,030토큰. 상수 1500은 그대로(상한 쪽). 실측 0.0002달러 |
| R8~R11 | 판독 includes, 요약 품질, judge, 쓸 수 없음 거르기 | 출력 재생성이 필요해 S5로 넘김(이 PR에서 재생성 안 함) |
| D3② | 공개 전 정리 | `docs/CONTEXT.md` 15장에 한 줄 |
| 부채 | 사람 확인 부채 | `docs/CONTEXT.md` 17장 |
