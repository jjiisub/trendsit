# S2~S3 맥 확인 목록

> COMMON 11장. 클라우드 세션이 구현했고, 맥 세션이 아래를 확인한 뒤 결과 칸을 채운다. 고칠 것은 같은 브랜치(`s2-s3`)에 커밋하고, 끝나면 PR 설명 맨 위를 "맥 확인 완료"로 바꾼다.
> 클라우드 환경(2026-10-08): `OPENROUTER_API_KEY` 없음. 네트워크는 패키지 저장소와 `api.github.com`(이 저장소만)만 열림. openrouter.ai, huggingface.co, export.arxiv.org, github.com(트렌딩), 수집 소스 도메인은 막힘. 그래서 LLM 호출, 실제 임베딩, 실제 한 주 데이터가 필요한 것은 모두 여기로 옮겼다.
> **두 번째 클라우드 세션(2026-10-08) 추가**: 키와 openrouter.ai·huggingface.co·export.arxiv.org가 열려 **픽스처 범위의 관문 B만** 클라우드에서 돌렸다(결과 칸에 "클라우드 2차"로 표시). github.com, 이 저장소 밖 GitHub API, news.hada.io는 여전히 막혀 있다. 실제 한 주 데이터로 하는 일과 사람 라벨은 그대로 맥 몫이다. 클라우드 사용액은 S2 $0.3707, S3 $0.0625(맥 몫 S2 0.20, S3 0.40은 그대로)
> 순서: 1 → 2 → 3(S2) → 4(S3). 맥 몫 예산은 S2 0.20달러, S3 0.40달러(→ 설계 결정 Q7: S2 상한 1.50, 맥 몫 S2 약 1.12, S3 약 1.93. 맥 사용 S2 $0.686, S3 $0.499). LLM을 부르기 전에 `uv run python -m trendsit cost --spec S2`(S3)를 결과 칸에 적고, 맥 몫을 넘을 실행이면 멈추고 질문한다. 클라우드 사용액은 첫 세션 S2 $0, S3 $0, 두 번째 세션 S2 $0.3707, S3 $0.0625. 맥 세션의 실행 기록 DB에는 클라우드 사용액이 없으니 더해서 본다.
> 예산 주의: 캐시가 없어 item_card 재평가(약 $0.08)와 한 주 summarize(개발 DB 기준 건당 약 $0.0014, 184건이면 약 $0.26)를 합치면 S2 맥 몫 0.20을 넘을 수 있다. 넘기 전에 멈추고 질문(질문 파일 Q7)
> 실제 임베더는 `uv run --extra embed ...`로 실행한다(`uv run`만 쓰면 embed 묶음이 지워진다).

## 1. 준비

| 확인 | 항목 | 클라우드에서 못 한 이유 | 확인 명령 | 기대 결과 | 결과 |
|---|---|---|---|---|---|
| [x] | 작업 폴더와 설치 | 맥 전용(Apple Silicon) | `git fetch origin && git worktree add ../trendsit-s2s3 s2-s3 && cd ../trendsit-s2s3 && uv sync --extra embed` | 설치 성공(torch, sentence-transformers) | **맥**: 2026-10-08 맥: `../trendsit-s2s3` worktree, `uv sync --extra embed` 성공(sentence-transformers 6.1.0, torch 2.14.1). data는 맥 S1 DB 사본 |
| [x] | 비밀 위치 | 클라우드에는 키 없음 | `ls -l ~/.config/trendsit/.env` | 권한 600, 저장소에 비밀 없음(`verify_s0.sh` A9) | **맥**: `-rw-------` 600. `OPENROUTER_API_KEY`, (뒤에 사용자 추가) `GITHUB_TOKEN`. verify_s0 A9 PASS, 토큰 값이 저장소·data·로그에 없음 확인 |
| [x] | 0단계 PR(`s2-0-base`) 병합 뒤 main 받기 | 이 브랜치는 `s2-0-base` 위에 쌓음 | `git merge origin/main` (충돌 시 해결) | 충돌 없음 또는 해결 | **맥**: `git merge origin/main` 충돌 없음(`a7846d9`) |
| [x] | 관문 A 회귀(A1) | verify_s0 A4~A6이 smoke 모델 실제 호출(키 필요) | `bash scripts/verify_s2.sh && bash scripts/verify_s3.sh` | 전부 PASS(A1 포함). 클라우드에서는 A1만 FAIL(키 없음) | 클라우드 2차: verify_s2·verify_s3 전부 PASS(A1 포함). 맥 환경에서 한 번 더 / **맥**: verify_s2·verify_s3 전부 PASS(A1 포함). 마지막 커밋(main 병합 뒤): 25개 PASS, `uv run --extra embed pytest -q` 402 passed + 1 skipped(S4 video 묶음 전용) |
| [x] | 0단계 repo_oneliner 재실행 | 키 없음 | `uv run python -m trendsit eval repo_oneliner --spec S2` → `eval repo_oneliner --agreement --spec S2` | 캐시로 약 0원. 원래 출력 코드 9/10, enforce 후 10/10 예상(질문 파일 Q1) | 클라우드 2차: 코드 9/10, enforce 후 10/10, Q1~Q3 각 9/9, $0.0155. agreement 0.963(라벨 결과 기준). 맥에서 다시 할 필요 없음 / **맥**: 설계 결정 Q1대로 재생성 없이 재채점(`eval --regrade`): 코드 10/10 통과, 모델 일치율 attention 9/10, Q1~Q3 각 10/10. `cost --spec S2` 전 $0 → $0.0011 |
| [x] | 실제 HTTPS 수집에서 연결 주소 고정(M3) | 클라우드는 프록시 환경이라 고정이 적용되지 않음 | `uv run python -m trendsit collect --source simonw --since <어제> --until <어제>` | 정상 수집(SNI, 인증서 확인 통과). 실패하면 `collect/fetch.py` PinnedTransport 확인 | **맥**: `collect --source simonw --since 2026-10-07 --until 2026-10-07`: 요청 14회, 신규 12, 본문 ok 11·short 1. 오류 없음 |

## 2. 데이터

| 확인 | 항목 | 클라우드에서 못 한 이유 | 확인 명령 | 기대 결과 | 결과 |
|---|---|---|---|---|---|
| [x] | 맥의 S1 DB로 한 주 재판정 | 클라우드에는 `data/trendsit.db` 없음, 수집 소스 막힘 | `uv run python -m trendsit rematch --since 2026-09-28 --until 2026-10-04` | 키워드 13개로 통과 건수 증가(184건보다 많음), 다시 돌리면 0건 바뀜 | **맥**: 343건 중 295건 바뀜(filtered→pass 89), 통과 305건(>184). 다시 돌려 0건 |
| [x] | 이번 주 트렌딩(3c 관문 B용) | github.com 트렌딩 막힘 | `uv run python -m trendsit collect --source github_trending` | 실행 주차의 트렌딩 저장(주차를 3c 리포트에 적음) | **맥**: 2026-W41: trending 11, pass 7, README 7 |

## 3. S2 (임베딩 필터, 글 1차 요약)

| 확인 | 항목 | 클라우드에서 못 한 이유 | 확인 명령 | 기대 결과 | 결과 |
|---|---|---|---|---|---|
| [x] | 실제 임베딩 모델 테스트 | huggingface.co 막힘(모델 못 받음). 클라우드에서는 이 테스트 1개만 건너뜀 | `uv run --extra embed pytest -q tests/test_s2a.py -k real_embedder` | 통과 | 클라우드 2차: 통과(CPU, `--extra embed`). 맥은 같은 명령에 `--extra embed`를 붙여 한 번 / **맥**: 통과(45초). 테스트가 장치를 cpu로 고정해 맥에서는 bf16 CPU 계산으로 70분 넘게 안 끝남 → 자동 선택(MPS)으로 바꿈(`bf73dd7`) |
| [x] | 재현 픽스처 점수: CPU와 MPS | 모델 없음 | `uv run --extra embed python -m trendsit filter-fixtures --embedder real --device mps --record` (cpu로 기록하면 클라우드 리눅스 CPU 기록(`…@cpu`)을 덮어쓰므로 cpu는 돌리지 않음) | `reports/S2_filter/fixture_scores.json`에 두 장치 점수, 최대 차이 0.001 이하, 걸린 시간 기록 | 클라우드 2차: 리눅스 CPU 점수 기록(200초). 맥은 `--device mps --record`만 돌려 이 기록과 비교(맥 CPU도 원하면 따로) / **맥**: MPS 기록. 클라우드 CPU와 최대 차이 0.0050(둘 다 bf16), 판정이 갈리는 픽스처 0. 처음 기준(0.001)으로는 미달 → **설계 결정 N5로 기준 변경(판정 변화 0건 + 최대 차이 0.01 이하) → 통과**. S2 리포트 2a |
| [x] | 한 주 필터 + 검증 산출물 | 모델·데이터 없음 | `uv run --extra embed python -m trendsit filter --since 2026-09-28 --until 2026-10-04 --embedder real --report --labels` | `reports/S2_filter/README.md`(환경, 분포, 근처 20건, 되살림·떨어뜨림, 같은 URL, 유사 쌍 30), `decisions.csv`, `eval/labels/relevance.csv` 40건 | **맥**: MPS 325건 155.4초, keep 281 / drop 44, 같은 URL 1. 산출물·relevance.csv 40행. S4 Whisper·관문 B와 겹치지 않게 확인 후 실행 |
| [x] | 시드 라벨 13건 | 모델 없음 | 위 README의 "시드 라벨 결과" | 찾은 행 중 85% 이상 맞음(못 찾은 행은 분모에서 뺌) | **맥**: **11/13(84.6%) 미달**. 틀린 2건: 고객 사례 글(OpenAI Chatham, Anthropic Barclays) keep |
| [x] | 문턱값 확정 | 분포를 못 봄(지금 `drop_below 0.30`, `rescue_above 0.45`는 자리값, `thresholds_status: provisional`) | 분포 표 + 사용자 라벨(relevance.csv 40건 expected 채움) → `config/filter.yaml` 문턱값·`thresholds_basis`·`thresholds_status: confirmed` 갱신 → filter 재실행 | 근거를 `reports/S2_report.md` 2a와 filter.yaml에. keep 정밀도·재현율 기록 | **맥**: 잠정 확정(2026-10-09, labeler opus-5.5, PR #6 리뷰 3장): drop_below 0.30 유지, rescue_above 0.50, `thresholds_status: provisional`. 라벨 40건 keep 정밀도 68.4%, 재현율 92.9%. filter 재실행(새 임베딩 0) keep 281 → 278 |
| [x] | item_card 픽스처 20건 채우기 | 녹화 글이 16건뿐(DeepMind 없음) | 실제 한 주 글에서 3건 이상 추가(DeepMind 1건 포함, 수치 많은 글 우선): `eval/fixtures/item_card/`에 `summarize.build_input` 형식으로 추가 | 픽스처 20건 이상(기존 17건은 고치지 않음, 추가분은 리포트에 표시) | **맥**: 4건 추가(21건): DeepMind Gemini 4 Argon, AI타임스 215937·215863, OpenAI Basis. 기존 17건 그대로 |
| [x] | item_card 관문 B | 키 없음 | `uv run python -m trendsit eval item_card --spec S2` → `eval item_card --label --spec S2` | 코드 채점 전부, 인용 본문 일치 95% 이상, judge Q1~Q3 각 80% 이상(잠정). 미달이면 COMMON 3장(최대 3회) | 클라우드 2차(픽스처 17건): 반복 3회 끝. 코드 16/17 미달(jump-trading 249자 인용, 질문 Q6), 인용 일치 100%, Q1~Q3 각 16/16(잠정). 맥은 픽스처 3건 추가 뒤 다시. **응답 캐시(`data/cache`)는 git 밖이라 맥에 없다**: 17건도 새로 생성·채점(약 $0.08 + 3건), 결과가 클라우드와 다를 수 있으니 `reports/eval/item_card_generate_20261008-120344.json`과 건별로 비교해 리포트에. 반복 횟수는 이미 다 썼으므로 추가 개선은 Q6 결정 뒤 / **맥**: `cost` 전 S2 $0.0011. Q1·Q6 반영 뒤 재실행: 코드 **20/21 미달**(kakapo-party 지어낸 수치 15s), 인용 일치 108/108, Q1 20/20·Q2 20/20·Q3 19/20(잠정), 잘린 인용 5/108, $0.0914. 클라우드 대비 건별 비교는 S2 리포트 2b. 반복 횟수 소진이라 추가 개선 없음 |
| [x] | 한 주 요약 실행 | 키·데이터 없음 | `uv run python -m trendsit summarize --since 2026-09-28 --until 2026-10-04 --spec S2` | 건수, 비용, relevance 분포, needs_original 비율을 S2 리포트 2b에 | 클라우드 2차 참고값(개발 DB 15건, 실제 한 주 아님): high 8 / mid 4 / low 3, 원본 확인 필요 6, 대체 1, $0.0213 / **맥**: `cost` 전 S2 $0.0926(+클라우드 0.37). 264건(대체 1), high 134 / mid 91 / low 39, 원본 확인 필요 158(59.8%), 잘린 인용 56/1352(4.1%), $0.5934 |
| [x] | 사용자 라벨: relevance 40, item_card 20 | 사람 몫 | `eval/labels/relevance.csv` expected, `eval/labels/item_card.csv` Q1~Q3 | 채운 뒤 `eval item_card --agreement --spec S2` 80% 이상, 필터 문턱값 확정 | 클라우드 2차: `eval/labels/item_card.csv` 17행 생성(빈칸). 맥에서 픽스처 추가 뒤 `eval item_card --label --spec S2`로 다시 만들면 출력이 같은 행의 라벨은 보존 / **맥**: 사람 라벨 대신 리뷰 세션 2차 채점(labeler opus-5.5, 잠정, 설계 결정 D1-3)을 옮겨 기록. item_card 모델 대 모델 일치율 Q1 47.6%(완화 85.7%, N3), Q2·Q3 100%. 사람 확인 부채: S2 리포트 |

## 4. S3 (레포 분석가, 편집장 계획, 글 분석가)

| 확인 | 항목 | 클라우드에서 못 한 이유 | 확인 명령 | 기대 결과 | 결과 |
|---|---|---|---|---|---|
| [x] | GitHub 도구 실제 호출 | 클라우드 GitHub API는 이 저장소만 허용 | `uv run python -m trendsit repo-analyze --week <이번 주> --top 2 --spec S3` | 도구 결과가 실제 수치(커밋, 기여자, 릴리스) | **맥**: `repo-analyze --week 2026-W41 --top 2`: 실제 수치(커밋 100+/작성자 9, 기여자 36, 릴리스 날짜). S3 $0.0082 |
| [x] | (선택) 합성 응답을 실제 녹화로 | 위와 같음 | `tests/fixtures/http/repo_tools`의 synthetic 항목을 녹화로 교체 | 테스트 그대로 통과(바뀐 수치에 맞춰 기대값은 고치지 않고, 안 맞으면 리포트에) | **맥**: 설계 결정 Q3대로 교체 아니라 **추가**: 실제 레포 3개 15응답(`recorded`), 합성 유지. 형식 차이(dev 프리릴리스) → releases에 prerelease 칸. 녹화·기록에 비밀 없음 테스트 |
| [x] | repo_analyst 관문 B | 키·트렌딩 없음 | `repo-analyze --week <이번 주> --top 10 --fixtures eval/fixtures/repo_analyst` (관련 높음 5, 낮음 5가 섞이게 큐 조정) → `eval repo_analyst --spec S3` → `--label` | judge Q1~Q3 각 80%(잠정), 관련 낮은 레포 80% 이상이 커밋 도구 없이 끝, 평균 도구 호출 4회 이하 | 클라우드 2차: 실행 안 함(GitHub API 403). 그대로 맥 몫 / **맥**: 2026-W41 10개(통과 5, 걸러짐·경계 5). 반복 0 코드 4/10 → 반복 1(md) 통과: 코드 10/10, Q1~Q3 각 10/10(잠정), 평균 도구 3.4, 관련 낮음 4/5 얕게. 중간 실행 1회는 GitHub 403으로 무효(S3 리포트 6장). 라벨 10행 |
| [x] | 레포 검증 산출물 | 위와 같음 | `repo-analyze --week <이번 주> --traces --spec S3` | `reports/S3_traces/repo/` 레포별 입력 수치 + 도구 경로 + 카드 | **맥**: `reports/S3_traces/repo/` 7개 |
| [x] | editor_plan 관문 B | 키 없음, 영상 4편뿐 | `plan --day 2026-10-04 --fixture eval/fixtures/editor_plan/2026-10-04.json --spec S3`(최근 영상 10편 들어가게 day 선택) → `eval editor_plan --spec S3` | 코드 채점 전부(예산 초과 0, reason, id), judge Q1~Q2 80% | 클라우드 2차: 개발 DB 픽스처 2건(`eval/fixtures/editor_plan/dev-2026-10-04.json`, `dev-2026-10-06.json`, 영상 1편)으로 코드 2/2, Q1·Q2 각 2/2 잠정 통과. 맥은 실제 영상 10편 픽스처를 **추가**(클라우드 것은 `dev-` 접두어라 이름이 겹치지 않음). 캐시가 없어 `dev-` 2건도 다시 생성·채점된다(약 $0.01) / **맥**: 실제 `2026-10-04.json`(영상 17, 글 158, 레포 4) 추가. 코드 3/3, Q1·Q2 각 3/3(잠정), $0.0283 |
| [x] | 계획 실행과 산출물, 영상 mode 라벨 | 위와 같음 | `plan --day 2026-10-04 --report --labels --spec S3` → 사용자가 `eval/labels/editor_plan_mode.csv` agree 채움 → `plan agreement --day 2026-10-04` (judge 라벨은 `eval editor_plan --label` → `eval/labels/editor_plan.csv`, 설계 결정 Q5) | `reports/S3_plan.md`, 동의율 80% 이상 | **맥**: 계획: 영상 5편 whisper(84분), 글 5, 레포 4. `reports/S3_plan.md`, `editor_plan_mode.csv` 17행(동의 15/17, 잠정), judge 라벨 `editor_plan.csv` 3행. 동의율 88.2%(잠정) |
| [x] | S4 계약 넘기기 | - | `plan show --day 2026-10-04 --video-queue > /tmp/q.json` | CONTRACTS 1장 형식(S4 `video run --queue` 입력) | **맥**: `plan show --video-queue`: 5항목 목록, {video_id, mode, start_sec, end_sec, reason} |
| [x] | text_analyst 관문 B | 키 없음, export.arxiv.org·원문 사이트 막힘 | `deep text --day 2026-10-04 --fixtures eval/fixtures/text_analyst --spec S3`(needs_original 글 10건이 되게) → `eval text_analyst --spec S3` → `--label` | enforce 전 근거 없는 confirmed 0~1건, judge Q1~Q3 80%(잠정), 원본 확보율·깊이 분포 기록 | 클라우드 2차: 개발 DB 픽스처 6건(`dev-it5,6,20,21,22,23`)으로 근거 없는 판정 0, Q1~Q3 각 6/6 잠정 통과, 원본 확보 6/6(깊이 2). github.com이 막혀 it5·it21은 공식 사이트로 대신 확인. 맥은 실제 한 주 needs_original 10건을 **추가**(개발 DB 6건은 참고로 남김, 이름이 `dev-`라 겹치지 않음). 캐시가 없고 맥은 github.com이 열려 있어 `dev-it5`·`dev-it21` 결과가 바뀔 수 있다(원본 문장 대조 4/6 → 개선 예상). 원본 확보 집계 6/6 중 2건은 대체 문서·인용 0이었다 / **맥**: 실제 10건(계획 큐 5 + 수동 5) 추가. 반복 0 근거 없는 판정 7(5건은 평가 버그 `b09261f`) → 2(’→') → 반복 1(md) 통과: 0건, 코드 16/16, Q1~Q3 각 16/16(잠정), 원본 확보 14/16, dev-it5·it21 대조 6/6 |
| [x] | 글 추적 산출물 | 위와 같음 | `deep text --day 2026-10-04 --traces --spec S3` | `reports/S3_traces/text/` 항목별 경로, v1 ↔ v2 | **맥**: `reports/S3_traces/text/` 5개, 대조 confirmed 38 / not_found 1 |
| [x] | 사용자 라벨: repo_analyst 10, editor_plan 10, text_analyst 10 | 사람 몫 | 각 csv | 채운 뒤 `eval <역할> --agreement --spec S3` 80% 이상 | 클라우드 2차: `eval/labels/text_analyst.csv` 6행 생성(빈칸). editor_plan judge 라벨은 경로가 mode 라벨과 겹쳐 만들지 않음(질문 Q5) / **맥**: 2차 채점(labeler opus-5.5, 잠정) 기록. 모델 대 모델 일치율 repo_analyst 90/90/100%, editor_plan 33.3/100%, text_analyst 93.8/75.0/93.8%, 영상 mode 동의율 88.2%. 사람 확인 부채: S3 리포트 |

## 5. 마무리
| 확인 | 항목 | 확인 명령 | 기대 결과 | 결과 |
|---|---|---|---|---|
| [x] | 리포트 수치 채우기 | `reports/S2_report.md`, `S2_quality.md`, `S3_report.md`, `S3_quality.md`의 "맥 확인 후" 자리 | 관문 B 표, 비용 표(클라우드/맥) | **맥**: S2·S3 리포트, 품질 리포트(자동), 사람 확인 부채 절, 리뷰 반영(2026-10-09) 수치 |
| [x] | README 성과 행 | S2, S3 행의 "맥 확인 뒤 기록"을 수치로 | | **맥**: S2, S3 행 수치 |
| [x] | 질문 Q5(라벨 경로), Q6(200자 넘는 인용) 결정 반영 | `reports/S2_questions.md` | 결정대로 코드·문서 | **맥**: 설계 결정 Q1~Q7 전부 반영. 위치는 S2·S3 리포트 "결정 반영" 절 |
| [x] | PR 표시 | PR 설명 맨 위 "맥 확인 대기" → "맥 확인 완료" | | **맥**: PR #6 설명 맨 위 "맥 확인 완료" → 리뷰 반영 뒤 "리뷰 반영 완료" |
