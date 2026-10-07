# TrendsIT

[![CI](https://github.com/jjiisub/trendsit/actions/workflows/ci.yml/badge.svg)](https://github.com/jjiisub/trendsit/actions/workflows/ci.yml)
· 예시 사이트 https://trendsit.jiseop.com · [위키](https://github.com/jjiisub/trendsit/wiki)

## 한 줄 소개
글, 유튜브 발표 영상, GitHub 트렌드를 매주 모아 **출처 달린 기술 동향 브리핑**을 만드는 개인용 AI 에이전트. 동향 파악에 쓰는 시간을 주 3시간에서 15분으로 줄이고, 브리핑의 모든 문장을 원본 링크나 영상 시각으로 확인할 수 있게 한다.

## 왜 만들었나
- 개발자로 일하며 새 기술을 따라가려면 뉴스레터, 블로그, 발표 영상, GitHub 트렌딩을 따로 훑어야 했다. 기능별 오픈소스는 있지만 세 채널을 합쳐 같은 주제로 묶고 원본까지 확인해 주는 도구는 없었다
- 접근: 흐름은 코드, 판단이 필요한 곳만 LLM. 수집 → 1차 요약 → 원본 추적 → 묶기 → 작성 ⇄ 검수를 역할별로 나누고, 모든 판단을 실행 기록에 남긴다

## 핵심 기능
| 기능 | 상태 |
|---|---|
| 멀티모달 수집: 글 6곳, 유튜브 발표 영상(전사 + 슬라이드 판독), GitHub 트렌딩 (차별점) | S1 수집, S4 영상 이후 |
| 원본 추적: 요약 글이 인용한 1차 자료를 찾아 수치와 주장을 대조 (차별점) | S3 이후 |
| 소스 간 교차 연계: 같은 주제의 글, 영상, 레포를 한 토픽으로 묶어 서술 (차별점) | S5 이후 |
| 출처 달린 주간 브리핑 + 검수 반려 루프 | S5 이후 |
| 실행 기록, 비용 상한, 응답 캐시, 평가 틀 (모든 역할의 바탕) | S0 완료 |

## 아키텍처
![아키텍처](docs/images/architecture.png) (그림은 이후 추가)

파이썬 코어 하나. 역할은 `roles/<이름>.md`(프롬프트) + pydantic 출력 스키마 + `run_role`(LLM 1회) / `run_agent`(도구 루프). 산출물은 SQLite 칠판에 쓰고, 역할끼리 직접 대화하지 않는다.

| 역할 | 입력 → 출력 | 모델 별칭 | 상태 |
|---|---|---|---|
| 레포 한 줄 (`repo_oneliner`) | README 앞부분 → 하는 일 한 문장 + 근거 구절 | generate | S0 |
| 글 1차 요약 (`item_card`) | 글 본문 → ItemCard(인용, 수치, 주장, 원본 확인 필요) | generate | S2 |
| 편집장 계획 (`editor_plan`) | 얕게 훑은 후보 → 항목별 처리 깊이 | generate | S3 |
| 글 분석가 (`text_analyst`) | 요약 글 → 원본 추적, 대조 결과 | generate (도구 에이전트) | S3 |
| 레포 분석가 (`repo_analyst`) | 트렌딩 레포 → RepoCard(신호, 과열 신호) | generate (도구 에이전트) | S3 |
| 영상 분석가 (`video_slide`, `video_summary`) | 전사 + 프레임 → 슬라이드 수치, 타임라인 | generate | S4 |
| 묶기 판단, 편집장 선별, 작성자, 검수자 | 항목 → 토픽 → 브리핑 | generate | S5 |
| 채점자 (`eval/judge.md`) | 출력 + 근거 → 질문별 pass/fail | judge | S0 |

## 빠른 시작
```bash
uv sync                                    # 파이썬 3.12 + 의존성
mkdir -p ~/.config/trendsit && $EDITOR ~/.config/trendsit/.env   # OPENROUTER_API_KEY=... (권한 600, 저장소에 두지 않음)
uv run python -m trendsit check-config     # 설정 + 역할 md 검사
uv run python -m trendsit role repo_oneliner --input eval/fixtures/repo_oneliner/encode__httpx.json --model smoke
uv run python -m trendsit cost --spec S1
```
변수 이름은 `.env.example`. 환경 변수가 있으면 그것을 먼저 쓴다.

| 명령 | 하는 일 |
|---|---|
| `uv run ruff check . && uv run pytest` | 정적 검사 + 단위 테스트(네트워크 없음, CI와 같음) |
| `bash scripts/verify_s<n>.sh` | 스펙 관문 A. 항목별 PASS/FAIL |
| `uv run python -m trendsit check-config [--root DIR]` | 설정 파일 + 역할 md(섹션, 예시 수, task, core_rules) 검사 |
| `uv run python -m trendsit role <이름> --input <json> [--model 별칭] [--no-cache]` | 역할 1회 실행. stderr에 run_id, step_id, 비용 |
| `uv run python -m trendsit role --replay <step_id> [--model 별칭] [--no-cache]` | 기록된 요청으로 다시 실행(모델 비교) |
| `uv run python -m trendsit eval <역할> [--model 별칭] [--limit N] [--note 메모]` | 픽스처 → 코드 채점 → judge 판정 → `reports/<스펙>_quality.md` |
| `uv run python -m trendsit eval <역할> --label` / `--agreement` | 사람 라벨 CSV 생성 / judge·사람 일치율 |
| `uv run python -m trendsit cost [--spec S1]` | 스펙별, 모델별 사용액과 남은 예산 |
| `uv run python -m trendsit trace <run_id>` | 실행 1건의 걸음(시각, 역할, 판단, 비용) |

## 사용 예시와 결과물
S5(주간 브리핑) 이후. 지금은 예시 데이터로 만든 정적 사이트 https://trendsit.jiseop.com 에서 완성 모습을 볼 수 있다.

## 성과와 평가
| 스펙 | 지표 | 결과 |
|---|---|---|
| S0 | repo_oneliner 관문 B(1~5점, generate) | 정확성 4.8, 구체성 4.9, 표현 5.0, 코드 채점 10/10 |
| S0 | 사용액 | $0.052 / 상한 $0.15 |

스펙마다 관문 B 수치, 비용(`cost`), 처리 시간을 이 표에 더한다. 자세한 것은 `reports/`.

## 기술적 도전
- **키 사용량 반영 지연:** OpenRouter `/key`의 누적 사용액이 몇 분 늦게 반영돼(기록 $0.033일 때 키 $0.018) 예산을 적게 볼 수 있었다 → 단계 사용액 = max(키 기준, 실행 기록 합). 몇 분 뒤 두 값이 소수점까지 일치해 `usage.cost` 기록의 정확성도 확인
- **깊이 상한 우회:** 모델이 `parent=null`로 깊은 문서를 바로 읽으면 깊이 상한이 무력해진다 → 모델이 준 parent가 아니라 코드가 실제로 읽은 문서의 링크만 인정
- **무료 모델의 도구 인자 실수:** nullable 인자에 문자열 `"None"`을 넣는 실수가 5건에 14회 → 코드가 null로 정규화하고 기록

## 기술 스택과 선택 이유
- Python 3.12, uv, ruff, pytest
- LLM 호출: 공식 `openai` SDK(OpenAI 호환 `/v1`) + pydantic. 에이전트 프레임워크 없이 루프와 기록만 직접 작성(프롬프트, 컨텍스트, 제어 흐름을 직접 소유)
- 모델: 개발은 OpenRouter(생성 Qwen 3.8 27B, 채점 Gemini 3.8 Flash, 다른 계열), 이후 로컬 Ollama로 전환(설정만 바꿈)
- 저장: SQLite 하나(WAL). 이후 sqlite-vec, FTS5
- 결정 기록: `docs/adr/`(설계 세션이 채움)

## 폴더 구조
```
config/      models.yaml(모델 별칭, 제공사 고정) budget.yaml(예산) sources.yaml keywords.yaml
roles/       역할 md = 프롬프트 폴더. 앞부분 실행 설정(모델, 스키마, 도구, 상한, task, core_rules) + 본문(목표/입력/판단 기준/출력/막혔을 때/예시)
skills/      여러 역할이 같이 쓰는 지침 md(style_ko)
trendsit/    파이썬 패키지: cli, core(config, llm, cache, budget, render, role, agent, trace, db, artifacts), tools
eval/        fixtures/<역할>/, rubrics/, judge.md(채점자 역할), labels/(사람 라벨), graders.py, run_eval.py
tests/       단위 테스트(LLM은 모의 전송, 네트워크 없음)
scripts/     verify_s<n>.sh(관문 A), fetch_fixtures.py
reports/     스펙별 리포트, 품질 리포트, eval 원자료
docs/        CONTEXT.md(맥락), handoff/(스펙), reference/(명세, 가이드), adr/, RULES.md
data/        실행 기록 DB, 캐시(git 제외). 예외: trendsit-example.json(출력 계약)
site_src/    예시 사이트 빌드(build.py → site/)
```

## 로드맵과 한계
- [x] S0 바탕: 레포 골격, LLM 호출(제공사 고정, 비용, 캐시, 예산), run_role / run_agent, 실행 기록, 재생, 평가 틀
- [ ] S1 수집: 글 6곳(RSS + 백필), 유튜브, GitHub 트렌딩, safe_fetch, 링크 판별, 키워드 매칭
- [ ] S2 글 1차 요약 + 임베딩 필터
- [ ] S3 깊게 보기: 편집장 계획, 글 분석가(원본 추적), 레포 분석가
- [ ] S4 영상 분석가
- [ ] S5 주간 브리핑: 묶기, 선별, 작성 ⇄ 검수
- [ ] S6 공개와 자동화: export, 정적 사이트, nightly / weekly

알려진 한계: judge 판정은 사람 라벨로 일치율을 재기 전까지 잠정. GitHub 트렌딩은 과거 기록이 없어 실행한 주의 목록만 얻는다.

## 만든 사람
LeeJiSeop · 서강대 "실전 AI 에이전트 시스템 설계, 구축"(2026-2) 관통 프로젝트

### 예시 사이트 (정적)
- 빌드 `python3 site_src/build.py` → `site/`, 검증 `python3 site_src/check.py`
- 데이터 `data/trendsit-example.json`(최종 출력 계약, S6에서 연결)
- 서빙 launchd `com.jiseop.trendsit-web` → 127.0.0.1:8788
