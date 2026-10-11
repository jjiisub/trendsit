# 교차 계약 (S2~S3 ⇄ S4, 2026-10-08)

> `agents_spec.md`와 다른 곳은 이 문서가 우선한다. 두 묶음이 동시에 개발되면서 서로의 결과를 주고받는 지점이다. 이 문서를 바꿔야 하면 코드 세션은 직접 고치지 않고 질문 파일에 적는다(설계 세션이 고쳐 main에 넣음).

## 1. 영상 처리 지시 (편집장 계획 → 영상 분석가)
S3 3a의 `CollectionPlan.video_queue[]` 항목이자 S4 `video run --queue`의 입력이다. 두 쪽 모두 이 형식을 pydantic 모델로 각자 정의하고(S3: `core/artifacts_text.py`, S4: `core/artifacts_video.py`), 같은 JSON 픽스처(`tests/fixtures/contracts/video_queue.json`, 두 묶음에 같은 내용)로 테스트한다. 병합 뒤 S6에서 하나로 합친다.

```json
{"video_id": "dQw4w9WgXcQ", "mode": "whisper+slides", "start_sec": null, "end_sec": null,
 "reason": "컨퍼런스 발표, 수동 자막 없음, 슬라이드 수치 많음"}
```
| 칸 | 형식 | 뜻 |
|---|---|---|
| video_id | 11자 유튜브 id | S1 `videos.video_id` |
| mode | `skip` / `captions` / `whisper` / `whisper+slides` | 처리 깊이. `captions` = 업로더 수동 자막만(자동 자막 금지), `whisper` = 로컬 전사, `whisper+slides` = 전사 + 슬라이드 판독. `skip`은 큐에 넣지 않아도 되지만 이유를 남길 때 씀 |
| start_sec, end_sec | 정수 또는 null | 60분 넘는 영상의 처리 구간. null이면 처음부터, 끝 null이면 최대 60분 |
| reason | 문자열 1줄 | 왜 이 깊이인지. 영상 분석가 log에 그대로 이어 씀 |

- 영상 분석가는 mode를 올리지 않는다(내리는 것은 실패 대체로만: slides 실패 → whisper 결과만, `captions`에 수동 자막이 없으면 whisper로 바꾸지 않고 건너뜀 + 기록)
- S3는 `trendsit plan show --day D --video-queue` 로 이 형식의 JSON 배열을 출력한다. S4는 파일이나 표준 입력으로 받는다

## 2. 근거 id
| 종류 | 형식 | 예 |
|---|---|---|
| 글 문장 | `it:{item_id}#q{n}` | `it:812#q3` (ItemCard quotes의 n) |
| 영상 시각 | `vd:{item_id}@{sec}` | `vd:905@754` (초 정수. item_id는 S1 `items.id`) |
| 레포 | `rp:{owner/name}` | `rp:ollama/ollama` |
| 원본 문서(S3b) | `og:{item_id}#q{n}` | ItemCard v2 quotes의 n |
| 글 원문 문장(S6-1) | `it:{item_id}#s{n}` | `it:812#s7` (item_texts.text를 fulltext.sentences()로 나눈 n번째 문장) |
| 레포 사실(S6-1) | `rp:{owner/name}#f{n}` | `rp:ollama/ollama#f1`부터 RepoCard evidence[].fact 순서 → (있으면) 뜨는 이유 → 릴리스 한 줄 |
| 슬라이드 판독(S6-1) | `sl:{item_id}@{sec}` | `sl:905@754` (frame_kind=slide인 프레임의 판독, slides.py 후보 중) |
- 전사 묶음(S6-1)은 `vd:{item_id}@{sec}`(video_segments start 25초 묶음의 시작 초, 글 자리와 같은 형식이지만 범위가 넓음)

## 3. 테이블 소유
| 테이블 | 소유 | 다른 쪽 |
|---|---|---|
| S0 `runs`, `steps`, `llm_calls` | 공통(쓰기는 기존 함수로만) | 둘 다 씀 |
| S1 `sources`, `fetch_log`, `items`, `item_texts`, `item_keywords`, `links`, `videos`, `repos`, `repo_trending` | S1(구조 변경 금지) | 둘 다 읽기. S2의 `rematch`만 `items.filter_*`, `item_keywords`를 다시 씀 |
| `schema_migrations` | S2 0단계 | - |
| S2~S3 새 테이블(마이그레이션 10~19): 관련성 점수, 임베딩, ItemCard, 계획, RepoCard 등 | 묶음 A | S4는 읽지 않음 |
| `video_*` (마이그레이션 20~29) | 묶음 B | 묶음 A는 읽지 않음(편집장 계획은 S1 `videos`만 읽음) |

## 4. 공통 코어 수정의 주인
| 수정 | 주인 | 다른 쪽 |
|---|---|---|
| 마이그레이션 등록(`core/migrations.py`), `RoleOutput.enforce` 훅, 도구 거부 메시지 경로 | 묶음 A 0단계 PR(`s2-0-base`, 먼저 병합) | 묶음 B는 병합 뒤 main을 받아 사용. 그 전에는 같은 검사를 자기 파이프라인 코드 안에서 |
| safe_fetch 연결 주소 고정(DNS) | 묶음 A(S3 도구 전) | 묶음 B는 safe_fetch를 쓰지 않음(yt-dlp가 직접 받음) |
| 이미지 입력(메시지에 이미지 넣기, 캐시 키에 이미지 해시: `llm.py`, `role.py`, `cache.py`, `trace.py`) | 묶음 B | 묶음 A는 쓰지 않음 |
| `core/db.py`, `core/migrations.py`(등록 방식), `core/artifacts.py`·`cli.py`의 스펙별 합치는 자리 | 묶음 A 0단계 | 묶음 B는 병합 뒤 자기 줄만 추가 |
| `pyproject.toml` 선택 묶음 | A = `embed`, B = `video` | 같은 `[project.optional-dependencies]` 표에 한 줄씩. 병합 때 `uv lock` 재생성 |

## 5. 영상 결과의 다음 단계
- S4는 `VideoDigest`까지만 만든다. 글 ItemCard와 같은 모양으로 바꾸는 변환(묶기 입력)은 S5에서 쓴다. S4가 `artifacts_text`를 가져다 쓰지 않는다(병행 중 의존 없음)
