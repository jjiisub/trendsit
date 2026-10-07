# youtube-analyze 스킬과 TrendsIT 영상 분석가 연동

> 작성: 2026-10-07. 사용자 맥에 이미 있는 영상 분석 CLI 스킬을 정리하고, TrendsIT 요구사항에 반영한 결정을 적는다. 구현은 S4(영상 분석가).
> **원칙: 스킬은 참고 구현이다. TrendsIT는 스킬에 의존하지 않는다**(스킬 경로, 스킬 venv, 스킬 CLI 호출 없음). 검증된 설계와 규칙을 가져와 TrendsIT 안에서 직접 구현한다. 스킬 코드는 사용자 본인 코드이므로 필요한 부분을 옮겨 와도 되지만, 옮긴 코드는 TrendsIT 저장소의 테스트와 계약을 따른다.

## A. 스킬 요약

- 위치: 맥 `~/.claude/skills/youtube-analyze/` (`SKILL.md`, `scripts/` 약 3.6k줄, 전용 `.venv`)
- 하는 일: 유튜브 URL이나 로컬 영상을 **로컬 Whisper로 전사**하고, 영상이면 **화면 프레임을 전사와 같은 시간축에 맞춰** 뽑는다. 요약하지 않고 빠짐없이 구조화하는 용도
- 의존성: 전용 venv(Homebrew python3.14), mlx-whisper 0.4.3(Apple Silicon GPU, 기본 모델 large-v3-turbo), yt-dlp 2026.7.4(JS 런타임 필요: deno → node → bun → quickjs, 없으면 403), ffmpeg/ffprobe 8.1.2. 외부 전사 API, 유튜브 자동 자막, OpenCV는 쓰지 않음
- 구조: `media_analyze.py`(진입점, stdout에 JSON 배열, stderr에 로그) / `media_source.py`(URL과 로컬 파일 통일, 재생목록·채널 URL 거부, 1080p 이하) / `transcribe.py`(언어 다지점 감지, 전사 품질 판정) / `video_frames.py`(키프레임·장면전환·균등 후보 → ffmpeg 32×32 썸네일 픽셀차로 중복 제거 → 적응형 예산) / `frame_cues.py`("이 화면", "this slide" 같은 화면 지시 표현으로 프레임 시각 선택, 프레임마다 그 시점 발화 `spoken_text`) / `workspace.py`(캐시 `~/.cache/youtube-analyze/<video_id>`, 원자적 커밋, purge) / `*_validate.py`(출력 계약 C1~C14 검사)
- 실행: 반드시 venv 절대경로의 python으로
  ```
  ~/.claude/skills/youtube-analyze/.venv/bin/python ~/.claude/skills/youtube-analyze/scripts/media_analyze.py "<URL>" [옵션] 1>out.json 2>run.log
  ```
- 주요 옵션: `--model`(기본 large-v3-turbo), `--lang`, `--frames off|auto|full`(기본 auto), `--frames-res`(기본 768, 1024는 토큰 약 1.8배), `--frames-cap`, `--timestamps 4:32,7:10`, `--start/--end`, `--no-dedup`, `--work-dir`, `--purge-older-than N`
- 출력 필드: `text`, `segments[]`(start, end, text), `transcript_quality`(`ok` / `suspect_hallucination` / `empty`), `frames[]`(t, path, reason, segment_index, spoken_text), `frames_meta`, `frames_error`, `work_dir`, `warnings[]`. 실패 항목은 `{source, error}`
- 실행 흐름: 전사(GPU)와 프레임 1차 추출(CPU)을 동시에. 전사 품질이 ok가 아니면 프레임 예산을 늘림. 프레임 단계가 실패해도 전사는 유효(`frames_error`만)
- 참고 수치: 768px 프레임 1장 약 1.1~1.4k 토큰, 10분 영상 40~60장. 실측 7분 영상 35초, 12분 영상 73초(프레임 포함)
- 스킬의 읽기 규칙: `warnings[]` 전부 읽기 / `transcript_quality`를 먼저 확인(`suspect_hallucination`이면 전사를 믿지 않고 프레임으로, `empty`면 프레임으로, 프레임도 없으면 내용 없음을 알림. 지어내는 것이 최악) / 프레임은 `transcript-cue`, `scene-change`, `first-frame` 먼저, `uniform`은 보완 / 화면 텍스트는 그대로 옮김 / 전사와 화면이 어긋나면 임의로 맞추지 않고 각각 기술(단, 전사가 뭉갠 고유명사에 화면 표기 병기는 허용, 예: 전사 "라마 쓰리 포인트 원" / 화면 `Llama 3.1`) / 순간 스쳐간 화면을 주요 주제로 다루지 않음(비중은 `spoken_text`로)
- 사용자 전역 원칙: 전사는 로컬로. 외부 전사 API나 유튜브 자동 자막을 기본안으로 쓰지 않음

## B. TrendsIT 반영 결정 (스킬에서 가져오는 것)

| # | 결정 | 이전 계획과의 차이 |
|---|---|---|
| V1 | 영상 분석가의 음성 줄, 화면 줄은 **TrendsIT 안에서 직접 구현**(`trendsit/collect/video/`). 스킬의 검증된 방식을 그대로 따름: 전사(GPU)와 프레임 1차 추출(CPU) 동시 실행, 키프레임·장면전환·균등 후보 → ffmpeg 32×32 회색 썸네일 픽셀차로 중복 제거 → 적응형 예산, 화면 지시 표현("이 화면", "this slide") 시점 프레임, 프레임별 `spoken_text`, 다지점 언어 감지, 전사 품질 판정. 출력은 스킬과 비슷한 필드 구조로 두되 TrendsIT 스키마(pydantic)로 정의 | 기존 계획의 youtube-transcript-api, PySceneDetect, imagehash, ocrmac를 빼고 스킬 방식(ffmpeg만으로)으로 단순화 |
| V2 | **전사는 로컬 Whisper가 기본.** 수동(업로더) 자막은 보조(한국어 용어 확인)로만, 자동 자막은 쓰지 않음 | 기존 "수동 자막 우선, 없으면 전사"를 뒤집음(사용자 전역 원칙). Tech Bridge는 해외 발표 원음(주로 영어)을 전사하므로 영어 슬라이드와 대조하기에도 유리 |
| V3 | 처리 깊이 ↔ 설정: 깊이 1 = 메타데이터(수집기, 다운로드 없음) / 깊이 2 = 프레임 끔(전사만) / 깊이 3 = 프레임 auto, 슬라이드 발표는 full(장면전환 기준), 수치 많은 발표는 해상도 1024. 프레임 상한 20장(예산). 스킬의 옵션 이름(`frames`, `frames_res`, `frames_cap`, `start/end`)을 함수 인자 이름으로 그대로 써서 대응을 쉽게 | 편집장 CollectionPlan의 mode가 이 설정으로 바로 바뀜 |
| V4 | 60분 넘는 영상: 편집장이 start/end 구간을 지정하거나 앞 60분만. 구간을 정한 이유를 log에 | 신규 |
| V5 | `transcript_quality` 규칙을 영상 분석가에 그대로: `suspect_hallucination`이면 전사를 근거로 쓰지 않고 프레임만, `empty`면 프레임만, 프레임도 없으면 VideoDigest를 비우고 attention=true + "내용 없음". 어떤 경우에도 지어내지 않음 | 신규 |
| V6 | 프레임 판독(VLM, generate 모델의 이미지 입력): 우선순위 `transcript-cue` / `scene-change` / `first-frame` → `uniform`. 화면 텍스트, 수치, 표는 그대로 옮김. 전사와 화면이 어긋나면 각각 기록 | 기존 "OCR 밀도로 프레임 고르기(ocrmac)"는 MVP에서 뺌. VLM 비용이 문제될 때 사전 필터로 검토 |
| V7 | 전사가 뭉갠 고유명사와 화면 표기 쌍(예: "라마 쓰리 포인트 원" ↔ `Llama 3.1`)은 VideoDigest에 남기고 **별칭 후보로도 넘김**(표기 정규화) | 신규. 정규화 품질에 도움 |
| V8 | 슬라이드 전용 수치: 판독한 수치가 프레임의 `spoken_text`와 앞뒤 30초 `segments`에 없으면 `slide_only_facts`(TrendsIT 코드) | 대조 방식은 같고, 재료를 스킬 출력에서 받음 |
| V9 | 보관: VideoDigest(텍스트)만 DB에. 영상과 프레임 이미지는 TrendsIT 작업 폴더(`data/media/<video_id>`, git 제외)에 두고 7일 뒤 정리(스킬의 원자적 커밋, 무결성 검사, purge 방식 참고). 영구 보관 안 함 | 기존 "처리 직후 삭제"를 7일 보관으로 완화 |
| V10 | 환경: 전사는 맥 전용(mlx-whisper). TrendsIT `pyproject.toml`에 선택 의존성 묶음 `video`(mlx-whisper, yt-dlp)로 두고, ffmpeg와 yt-dlp용 JS 런타임은 시스템 의존성으로 README에 명시. 맥이 아니거나 `video` 묶음이 없으면 전사 단계는 건너뛰고 경고. 판독 이후 단계는 **저장해 둔 1차 처리 결과 JSON 픽스처**로 어디서나 테스트 | 스킬 venv, 경로에 의존하지 않음 |
| V11 | 예산: 영상당 프레임 20장 × 약 1.3k 토큰 ≈ 26k 입력 토큰. generate 모델 기준 영상당 약 0.004달러 + 판독 출력. 주 3편이면 무시할 수준 | 추산 |
| V12 | 스킬의 출력 계약 검사(C1~C14)를 참고해 TrendsIT 1차 처리 결과의 계약 테스트를 만든다(segments 시간 순서, 프레임 t가 영상 길이 안, 프레임마다 segment_index와 spoken_text, 품질 값 집합 등) | 신규 |

## C. 남은 확인 (S4 전에)
- Tech Bridge 영상이 원음 영어 + 한국어 자막(영상에 입힌 하드 자막인지, 업로더 자막 트랙인지). 하드 자막이면 프레임에 한국어 자막이 찍혀 판독에 섞이므로 프롬프트에서 자막 줄은 무시하도록
- 스킬에서 옮겨 올 부분과 새로 쓸 부분을 S4 handoff에서 나눔(예: 프레임 중복 제거, 화면 지시 표현 목록은 옮겨 오기 후보)
