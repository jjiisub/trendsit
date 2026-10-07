# S4. 영상 분석가 (전사 + 슬라이드 판독, 맥)

> 먼저 읽을 것: `docs/handoff/COMMON.md`(갱신: 8장 일정 열 삭제, **9장 병행 개발, 10장 검증 산출물**) → `docs/handoff/CONTRACTS.md` → `docs/handoff/S1_REVIEW.md`(M1 마이그레이션 등록: 이 스펙이 기다리는 것) → 이 문서 → `docs/reference/youtube_analyze.md`(V1~V12, 이 스펙의 설계 근거) → 역할을 쓸 때 `docs/reference/prompt_guide.md`, `docs/reference/agents_spec.md`(0.7, 4장).
> 작성: 2026-10-08. 전제: S1 병합(PR #3). **묶음 B**: 맥 로컬 세션(M1 Max 32GB). 같은 시기에 묶음 A(S2~S3)가 클라우드에서 진행된다(COMMON 9장). 브랜치 `s4-video`, 작업 폴더 `git worktree add -b s4-video ../trendsit-s4`(main 폴더와 따로, `data/`도 따로).
> 예산: **S4 0.80달러**(맥). `config/budget.yaml`에 이미 있음. 모든 실행에 `TRENDSIT_SPEC=S4`(기본값 S0에 잡히지 않게).
> `agents_spec.md` 4장과 다른 곳(슬라이드 실패 대체 = whisper 결과만, 판독 출력의 confidence 위치)은 이 문서와 `CONTRACTS.md`가 우선한다.

## 0. 이 스펙이 끝나면 되는 것 (한 줄)
`trendsit video run --queue q.json`(또는 `--video-id ID --mode whisper+slides`)을 주면 **영상을 받아 로컬 Whisper로 전사하고, 슬라이드 프레임을 골라 판독하고, 발화에 없고 화면에만 있는 수치(slide_only_facts)를 시각과 함께 뽑아 요약·타임라인과 함께 VideoDigest로 저장**한다. 영상과 프레임은 7일 뒤 지워지고, DB에는 텍스트만 남는다.

## 1. 맥락과 진행 순서
- 영상 분석가는 "판단 + 코드 분기": 단계는 고정(받기 → 전사·프레임 → 품질 확인 → 판독 → 대조 → 정리), 판단 지점만 LLM. 처리 깊이(mode)는 편집장 계획(S3 3a)이 정하고 영상 분석가는 올리지 않는다(CONTRACTS 1장)
- 맥의 `youtube-analyze` 스킬은 **참고 구현**이다. 스킬 경로, venv, CLI를 부르지 않는다. 사용자 본인 코드라 필요한 부분(중복 제거, 화면 지시 표현 목록, 전사 품질 판정, 작업 폴더 원자적 커밋)을 옮겨 와도 되고, 옮긴 코드는 이 저장소의 테스트와 계약을 따른다. 옮긴 파일과 원본 위치를 리포트 표에
- 진행 순서(묶음 A와 충돌을 피하려고)
  1. **DB 없는 부분 먼저**: 준비물 확인(2장) → 1차 처리(`collect/video/`) → 계약 테스트 → 픽스처 → 품질 규칙 → 대조(align)
  2. 묶음 A의 0단계 PR(`s2-0-base`: 마이그레이션 번호 키 등록, enforce 훅)이 main에 병합되면 `git merge origin/main` → 마이그레이션 20번대 추가, 역할 출력의 코드 규칙을 enforce 훅으로 옮김
  3. 이미지 입력(공통 코어, 이 스펙이 주인. 별도 커밋) → 역할 `video_slide`, `video_summary` → CLI → 관문 B
- 0단계 PR이 아직이면 2를 미루고 3의 역할 작업을 먼저 해도 된다(저장은 JSON 파일로 임시). 마이그레이션을 목록 방식에 덧붙이지 않는다

## 2. 준비물 (시작할 때 확인해서 리포트 표에)
| 준비물 | 할 일 | 없으면 |
|---|---|---|
| ffmpeg, ffprobe | `brew` 설치 확인, 버전 기록 | 설치(시스템 의존성, README에 명시) |
| yt-dlp용 JS 런타임 | deno → node → bun 중 하나(없으면 yt-dlp가 403) | 설치 |
| `video` 선택 묶음 | `s2-0-base` 병합 전에는 `uv pip install yt-dlp mlx-whisper`로 작업 폴더에만 설치. 병합 뒤 `pyproject.toml`에 `video = ["yt-dlp", "mlx-whisper; sys_platform == 'darwin'"]` 추가 → `uv sync --extra video` | - |
| Whisper 모델 | mlx-whisper `large-v3-turbo` 첫 실행 때 받음(약 1.6GB) | 디스크 확인 후 |
| **generate 모델의 이미지 입력** | 프레임 1장으로 `generate` 별칭에 이미지 메시지 1회(비용 기록). 6주차 모델 비교에서 qwen3.8-27b 이미지 묶음은 1.00이었지만 고정 제공사(DeepInfra)에서 다시 확인 | **멈추고 질문 파일에.** `models.yaml`은 설계 세션 소유(이미지 전용 별칭을 추가할지 설계 세션이 정함). 그동안 판독 이전 단계를 진행 |
| Tech Bridge 자막 형태 | 최근 영상 2편에서 한국어 자막이 영상에 입힌 하드 자막인지 업로더 자막 트랙인지 | 하드 자막이면 `video_slide` md에 자막 줄 무시 규칙(이미 넣을 예정)과 예시 강화 |
| 디스크 | `data/media/` 여유 10GB 이상 | 영상 해상도 상한을 낮춤(1080p → 720p) |

## 3. 범위
### 3.1 만든다
1차 처리(받기, 전사, 프레임 후보·중복 제거·화면 지시 프레임, 작업 폴더·정리), 1차 처리 결과 계약 테스트, 전사 품질 규칙, 이미지 입력(공통 코어), 역할 `video_slide`·`video_summary`, 대조(slide_only_facts), 표기 쌍, VideoDigest 저장(마이그레이션 20~29), CLI, 픽스처, `scripts/verify_s4.sh`, 리포트와 검증 산출물
### 3.2 만들지 않는다
편집장 계획(S3 3a, 큐 JSON을 받기만), 묶기·영상 ItemCard 변환(S5), 자동 실행(S6), 유튜브 자동 자막 사용, 외부 전사 API, OCR 라이브러리(ocrmac 등), OpenCV, PySceneDetect

## 4. 폴더 (추가분)
```
trendsit/
  cli_video.py              register(sub): video(하위: run, purge, report). 기존 `report` 명령에는 손대지 않음
  core/artifacts_video.py   VideoQueueItem(계약), MediaResult, SlideReading, VideoSummary, VideoDigest
  collect/video/
    source.py               yt-dlp 받기(다운로드 1회 재시도, 1080p 이하, 재생목록·채널 URL 거부)
    transcribe.py           mlx-whisper 전사, 다지점 언어 감지, transcript_quality
    frames.py               키프레임·장면전환·균등 후보 → 32×32 회색 썸네일 픽셀차 중복 제거 → 적응형 예산
    cues.py                 화면 지시 표현("이 화면", "this slide" 등) 시점 프레임, 프레임별 spoken_text
    workspace.py            data/media/<video_id>, 원자적 커밋, purge
    process.py              media_process(): 전사(GPU)와 프레임 1차 추출(CPU) 동시 실행
    contract.py             1차 처리 결과 계약 검사(V12)
  video/
    align.py                판독 수치 ↔ 발화 대조, 수치 정규화
    pipeline.py             단계 실행, 품질 분기, 대체 동작
roles/  video_slide.md  video_summary.md
config/video.yaml           mode별 설정, 프레임 상한, 해상도, 보관 일수 (S4 소유)
tests/fixtures/video/       1차 처리 결과 JSON(실제 실행에서 저장), 썸네일 몇 장
tests/fixtures/contracts/video_queue.json   CONTRACTS 1장(묶음 A와 같은 내용)
```

## 5. 상세 요구사항

### 5.1 1차 처리 (`media_process(video_id, mode, start_sec, end_sec)`)
- mode → 설정(V3, `config/video.yaml`): `captions` = 업로더 수동 자막 트랙만 받아 segments로(없으면 건너뜀 + 기록, whisper로 올리지 않음), `whisper` = 전사만(프레임 끔), `whisper+slides` = 전사 + 프레임 auto(장면전환이 많은 슬라이드 발표는 full), 해상도 기본 768(수치 많은 발표는 1024), 프레임 상한 20장
- 60분 넘는 영상: start/end가 있으면 그 구간, 없으면 앞 60분(V4). 이유를 log에
- 전사와 프레임 1차 추출을 동시에(스킬 방식). LLM 판독은 전사가 끝난 뒤(이후 로컬 모델 전환 때 메모리 순서 유지)
- 결과 `MediaResult`(pydantic): `segments[]`(start, end, text), `language`, `transcript_source`(whisper/manual), `transcript_quality`(ok/suspect_hallucination/empty), `frames[]`(t, path, reason: transcript-cue/scene-change/first-frame/uniform, segment_index, spoken_text), `frames_meta`(후보 수, 중복 제거 전후 수, 예산), `frames_error`, `warnings[]`, `duration_sec`, 장치·라이브러리 버전
- 전사 품질 규칙(V5, 스킬의 판정 방식 참고): 반복 구간, 압축률, 무음 비율 등으로 suspect_hallucination, 글자가 거의 없으면 empty. 판정 근거 수치를 warnings에
- 작업 폴더 `data/media/<video_id>/`(git 제외), 원자적 커밋(임시 폴더 → 이름 바꾸기), `video purge --older-than 7`
- 실패: 받기·전사 각 1회 재시도. 프레임 단계 실패는 전사 결과 유지 + `frames_error`
- 계약 테스트(V12): segments 시간 순서와 겹침 없음, 프레임 t가 영상 길이(또는 구간) 안, 프레임마다 segment_index와 spoken_text, 품질 값 집합, 프레임 수 ≤ 상한, 경로가 작업 폴더 안
- 픽스처: 실제 영상 2~3편의 `MediaResult`를 JSON으로 저장(segments 전체는 수십 KB 이내, 넘으면 앞부분만 + 표시). 판독 이후 단계 테스트는 이 픽스처로 어디서나(CI 포함)

### 5.2 이미지 입력 (공통 코어 수정, 별도 커밋)
- 역할 입력에 이미지 칸(파일 경로)을 두면 메시지 조립이 `image_url`(data URI) 부분을 붙인다. 자료 규칙(`<data>`)은 텍스트 부분에 그대로, 이미지는 자료 블록 바로 뒤
- 캐시 키에 이미지 바이트 해시 포함. 실행 기록 `llm_calls`에는 이미지 원본이 아니라 경로와 해시만
- 예상 비용 계산에 이미지 토큰(장당 추정치, 상수 이름)을 넣는다
- 테스트: 모의 전송으로 메시지 모양, 캐시 키가 이미지에 따라 바뀜, 기록에 원본 없음

### 5.3 슬라이드 판독 (`video_slide`, 이미지 추출, 프레임당 1회)
- 대상: `whisper+slides`의 프레임 중 우선순위 transcript-cue, scene-change, first-frame → uniform 순으로 상한까지(V6)
- 입력: 프레임 이미지, 시각, 그 시점 `spoken_text`(자료로)
- 출력(칸 순서): `frame_kind`(slide/demo/speaker/other) → `ocr_text`(화면 글자 그대로. slide가 아니면 빈 문자열) → `numbers[]`(confidence: high/low/check 먼저 → value: ocr_text 안 문자열 그대로 → unit → what) → `table`(행 목록 또는 null) → `title` → `log`, `attention`
- md에 넣을 것(`agents_spec` 0.7): 화면 텍스트·수치·표를 그대로, 흐린 숫자는 값 대신 check, **하드 자막 줄은 무시**, 예시 3개(보통 슬라이드 / 슬라이드가 아닌 화면 → 빈칸이 맞음 / 함정: 흐린 숫자 → check)
- enforce(훅 병합 전에는 파이프라인 코드): value가 ocr_text에 없으면 지우고 attention, slide가 아닌데 numbers가 있으면 비움
- 판독 결과는 텍스트만 DB에

### 5.4 대조 (`align`, 코드, V8)
- 판독 수치를 정규화(쉼표, `K/M/B`, `%`, `x`/`배`, 소수점, 영어 수사 one~twenty·hundred·thousand·million·billion)해 그 프레임의 `spoken_text`와 앞뒤 30초 segments에서 찾음. 없으면 `slide_only_facts`(fact, value, unit, sec, 근거 id `vd:{item_id}@{sec}`, confidence)
- check 판독은 slide_only_facts에 넣지 않고 따로 목록(사람 확인용)
- 테스트: 같은 수치가 다른 표기로 발화된 경우 대조됨, 30초 밖이면 slide_only

### 5.5 영상 요약 (`video_summary`, LLM 1회)
- 입력: 전사(`transcript_quality=ok`일 때만. 아니면 빈 문서 + 품질 표시), 판독 결과 목록(시각, title, ocr_text 앞부분), slide_only_facts, 영상 메타데이터(제목, 길이, 챕터), mode
- 출력(칸 순서): `name_pairs[]`(spoken: 전사 표기 그대로, screen: 화면 표기 그대로, sec) → `key_points[]`(text, evidence: `vd:` id 목록) → `timeline[]`(sec, label, slide 여부) → `chapters[]` → `summary` → `log`, `attention`
- md에 넣을 것: V5 품질 규칙(suspect면 화면만, 둘 다 없으면 "내용 없음" + attention, 지어내지 않음), 비중은 발화 시간으로(스쳐 간 화면을 주제로 부풀리지 않음), 전사와 화면이 다르면 각각 기술(고유명사 병기만 허용)
- enforce: name_pairs의 spoken은 전사에, screen은 ocr_text에 실제로 있어야 남김 / evidence·timeline 초는 영상 길이(구간) 안 / 전사가 쓸 수 없는 품질인데 전사만 근거로 한 key_point는 지움
- 표기 쌍은 별칭 후보로 리포트에 모은다(V7. keywords.yaml 반영은 설계 세션)

### 5.6 저장과 CLI
- 마이그레이션 20~29: `video_runs(item_id, video_id, mode, start_sec, end_sec, transcript_source, transcript_quality, status, run_id, created_at)`, `video_segments(video_id, idx, start, end, text, expires_at)`(수집 + 8주 뒤 텍스트 삭제, item_texts와 같은 원칙), `video_frames(video_id, t, reason, spoken_text, reading_json)`, `video_digests(video_id PK, digest_json, model, run_id, created_at)`. 테이블 이름은 `video_` 접두어만(CONTRACTS 3장)
- `VideoDigest`: `agents_spec` 4장 표(transcript_source, transcript_quality, name_pairs, segments 참조, slides, slide_only_facts, timeline, summary, chapters, log, attention)
- CLI: `video run --video-id ID --mode M [--start --end]`, `video run --queue FILE|-`(CONTRACTS 1장 JSON 배열), `video purge [--older-than 7]`, `video report [--since --until]`
- 실행 기록: 영상마다 run 1개, 단계마다 step(code: 받기·전사·프레임·대조 / llm: 판독·요약). 단계 실패는 attention

## 6. 관문 A (verify_s4.sh)
| # | 항목 | 확인 방법 |
|---|---|---|
| A1 | 회귀 | `verify_s0.sh`, `verify_s1.sh` 통과 |
| A2 | 정적 검사, 테스트 | ruff 0, pytest 전부(CI에서는 픽스처로, 맥 전용 테스트는 `video` 묶음·맥이 아니면 건너뜀 표시. 이 한 종류만) |
| A3 | 설정 | `video.yaml` check-config 통과, 잘못된 mode·상한이 경로를 짚어 실패 |
| A4 | 역할 md | `video_slide`, `video_summary`가 역할 md 검사 통과, 예시 3개 |
| A5 | 계약 | 픽스처 MediaResult가 계약 검사 통과, 일부러 깨뜨린 사본(시간 역순, 상한 초과, 작업 폴더 밖 경로)이 실패 |
| A6 | 큐 계약 | `tests/fixtures/contracts/video_queue.json`을 읽어 mode별 설정으로 바뀜, captions에 수동 자막이 없으면 건너뜀(올리지 않음) |
| A7 | 품질 분기 | suspect_hallucination·empty 픽스처에서 전사를 근거로 쓰지 않음, 둘 다 없으면 "내용 없음" + attention |
| A8 | 대조 | 5.4 테스트 |
| A9 | enforce | 판독 수치·표기 쌍·초 범위 규칙(모의 LLM 응답) |
| A10 | 이미지 입력 | 5.2 테스트 |
| A11 | 보관 | purge가 7일 지난 작업 폴더만 지우고 DB 텍스트는 유지, 8주 지난 segments 텍스트 삭제 |
| A12 | 마이그레이션 대역 | 이 스펙이 추가한 번호가 모두 20~29, 묶음 A 번호와 겹치지 않음 |
| A13 | 자동 자막 금지 | 자동 자막 경로가 코드에 없음(테스트: 자동 자막만 있는 메타데이터에서 captions는 건너뜀) |
| A14 | 문서 | README(기능, 빠른 시작, 시스템 의존성 ffmpeg·JS 런타임, 성과 행), `docs/DEVELOPMENT.md` 명령표, 리포트 |

## 7. 관문 B (실제 영상, 맥)
- 대상: S1 `videos`의 Tech Bridge 최근 영상 10편. 슬라이드 발표 6편 이상 + 대담·데모 섞어서. 큐는 사람이 만든 JSON(편집장 계획 병합 전이므로). mode는 슬라이드 발표 `whisper+slides`, 나머지 `whisper`, 수동 자막이 있는 1편은 `captions`도 비교
- 문턱값
| 항목 | 기준 |
|---|---|
| 1차 처리 | 10편 모두 성공 또는 실패 이유 기록. 계약 검사 전부 통과 |
| 판독 수치 정확도 | 사용자 라벨에서 slide_only_facts가 실제 화면에 있는 비율 90% 이상 |
| 슬라이드 전용 정보 포착률 | 사용자 라벨 기준 80% 이상(`agents_spec` 4장) |
| video_summary | judge Q1 key_points가 전사·판독으로 뒷받침되는가, Q2 타임라인 초가 맞는가, Q3 품질이 나쁜 때 지어내지 않았는가. 각 80% 이상 + 라벨 일치 80% |
- 라벨(사용자, 리뷰 때): `eval/labels/video_summary.csv` 10행(Q1~Q3, `eval --agreement`용). slide_only_facts "화면에 있음/없음"과 썸네일(최대 5장)마다 "놓친 수치 있음/없음"(포착률 근사)은 `reports/S4_video/`의 체크 칸 표에
- 비교: 슬라이드 발표 2편은 `whisper`만 vs `whisper+slides`로 요약을 나란히(슬라이드가 더한 정보 리포트)
- 미달이면 COMMON 3장대로 역할마다 최대 3회 개선

## 8. 예산 (S4 0.80, 맥)
| 단계 | 상한 |
|---|---|
| 이미지 입력 확인 | 0.01 |
| 개발 중 판독·요약(작은 샘플, 캐시) | 0.15 |
| 관문 B 10편(판독 약 120장 + 요약 + judge) | 0.40 |
| 비교, 재실행 예비 | 0.24 |
- 시작할 때 `trendsit cost`로 단계 사용액을 기록. 묶음 A가 같은 키를 쓰므로 단계 사용액에 그쪽 몫이 섞인다(정상). 스펙 상한은 이 폴더의 실행 기록 기준

## 9. 검증 산출물 (`reports/S4_video/`, COMMON 10장)
- 실행 환경: 장치(MPS), mlx-whisper·yt-dlp·ffmpeg 버전, 모델, 영상별 길이·처리 시간·프레임 수(중복 제거 전후)
- 전사: 영상별 앞 2분 발췌(타임스탬프), 언어, 품질 판정과 근거 수치
- 프레임: 영상당 저해상도 썸네일 최대 5장(PNG, 장당 수십 KB) + 그 프레임의 판독 결과와 발화 대조
- slide_only_facts 전체 표(영상, 초, 수치, 무엇, confidence, 썸네일 링크) — 사람 확인 체크 칸
- 표기 쌍 목록, `whisper` vs `whisper+slides` 비교
- 재현 명령. 원본 영상·오디오·전체 프레임은 커밋하지 않음. 전체 크기 수 MB 이내

## 10. 완료 시 넘길 것
- PR `s4-video`(맥 세션이 직접 구현했으므로 "맥 확인" 단계 없음): 관문 A 출력, 관문 B 요약 표, 비용 표, "공통 코어 수정"(이미지 입력) 목록, 마이그레이션 번호 목록, 스킬에서 옮긴 코드 표
- 두 번째로 병합되는 쪽이면 main을 받아 충돌 해결 → 병합된 트리의 `scripts/verify_s*.sh` 전부와 pytest 결과를 PR 코멘트로(COMMON 9장)
- 리포트: `reports/S4_report.md`, `S4_quality.md`, `S4_video/`
- README 갱신: 핵심 기능(멀티모달 수집 ★ 영상 줄), 빠른 시작(`video run`), 시스템 의존성, 성과 행, 로드맵 체크
- 다음 스펙을 위한 제안: 편집장 계획의 mode 기준(실제 처리 시간·비용 기준), `config/deep.yaml`의 영상 예산(분, 프레임) 실측값, 묶기에서 VideoDigest 쓰는 법
