# 설계 결정: S2~S3 맥 확인 전 (2026-10-08)

> `reports/S2_questions.md` Q1~Q7에 대한 설계 세션 답이다. `S2S3_TASK.md`와 다른 곳은 이 댓글이 우선한다.
> **맥 세션 할 일**: 이 댓글 전문을 `docs/handoff/S2S3_DECISIONS.md`로 이 브랜치에 저장(커밋 `docs(s2): 설계 결정 Q1~Q7 기록`)하고, 아래 결정을 코드·문서에 반영한다. 반영 위치는 `reports/S2_report.md`·`S3_report.md`의 "결정 반영" 절에 적는다. `config/budget.yaml`은 원래 설계 세션 소유지만 Q7의 S2 상한 한 줄은 이 댓글을 근거로 맥 세션이 바꾼다(커밋 메시지에 "설계 결정 Q7").

## Q1. enforce가 맡은 칸의 통과 판정 → 두 갈래로 나눔
- **코드 소유 칸**(코드가 값을 정하는 칸): 코드 채점의 통과 판정은 enforce 후 출력 기준. 원래 출력과 다른 건수는 칸별 "모델 일치율"로 품질 리포트에 따로 적음
- **품질 드러내는 정리**(모델이 틀린 것을 코드가 지우거나 내리는 것): 지금대로 원래 출력 기준. 기존 문턱값(인용 일치 95%, 근거 없는 판정 0~1건, 예산 초과 0 등)은 그대로
- 구현: 역할 출력 클래스에 `ENFORCED_FIELDS: ClassVar[tuple[str, ...]]`(코드 소유 칸 이름). 채점기는 원래 출력에 이 칸만 enforce 후 값으로 덮어 채점. 칸 목록은 코드에(역할 md 아님). 공통 코어 수정(`core/artifacts.py`, `eval/graders.py`, `eval/run_eval.py`)이므로 별도 커밋

| 역할 | 코드 소유 칸 (enforce 후로 채점) | 품질 드러내는 정리 (원래 출력으로 채점) |
|---|---|---|
| repo_oneliner | attention(README 200자 규칙) | - |
| item_card | quotes 길이 자르기(Q6), attention | 본문에 없는 quote 삭제, quote에 없는 수치 삭제, 목록 밖 키워드·링크 삭제 |
| repo_analyst | signal(과열 → check 고정), hype_flags(코드 규칙 플래그), attention | 입력 밖 글 id 삭제, 근거 없는 why_trending |
| editor_plan | attention(80% 초과) | 없는 id·중복 제거, max_depth 자르기, 예산 넘는 꼬리 자르기 |
| text_analyst | attention(differs) | 근거 없는 confirmed/differs → not_found, 연 적 없는 페이지 인용 삭제, trail 밖 origin |

- 분류가 애매한 규칙은 품질 드러내는 쪽으로 두고 리포트에 적음
- repo_oneliner S1 관문 B: 코드 10/10(통과), 모델 일치율 9/10. 재실행 없이 클라우드 2차 결과로 다시 채점만

## Q2. 클라우드 네트워크와 키
- 이번 묶음은 막힌 일을 지금처럼 맥 확인 목록으로. 다음 클라우드 묶음 전 환경 설정은 설계 세션·사용자 몫(코드 세션 할 일 아님)

## Q3. 합성 GitHub 응답 → 실제 녹화 추가, 합성 유지
- 실제 레포 2~3개(활발한 레포, 릴리스 있는 레포, 작은 개인 레포)의 `github_repo`, `recent_commits`, `contributors`, `releases` 응답을 녹화해 `tests/fixtures/http/repo_tools`에 **추가**하고 정상 경로 테스트를 더함(`meta.json`에 `recorded`). 토큰 등 비밀이 녹화에 남지 않게
- 합성은 경계 사례(7일 커밋 0, 기여자 1, 빈 릴리스)용으로 유지, `synthetic` 표시 유지, 기대값 고치지 않음
- 녹화에서 형식 차이(빈 레포 응답 코드, 페이지 나눔 등)가 보이면 도구 코드를 고치고 리포트에

## Q4. 픽스처 수 → 맥에서 추가
- item_card: 실제 한 주 글에서 3건 이상 추가(DeepMind 1건 포함, 수치 많은 글 우선). 기존 17건 그대로
- repo_analyst 10, editor_plan(최근 영상 10편), text_analyst 10: 맥 확인 목록대로 실제 데이터로. `dev-` 픽스처는 참고로 남김

## Q5. editor_plan 라벨 경로 → mode 라벨 분리
- 영상 mode 동의 라벨(`plan --labels`, `plan agreement`): `eval/labels/editor_plan_mode.csv`
- judge 확인 라벨(`eval editor_plan --label`, `--agreement`): `eval/labels/editor_plan.csv`(다른 역할과 같은 규칙)
- 코드, `docs/DEVELOPMENT.md`, 맥 확인 목록 명령을 같이 고침

## Q6. 200자 넘는 인용 → 코드가 자름 (결과 품질이 떨어지면 다시 조정)
- 모델용 스키마의 quote 상한을 넉넉한 안전 상한(예: 1,000자)으로 올려 스키마 오류로 다시 묻지 않게 함. 역할 md의 "200자 이내" 지시는 그대로
- enforce: 200자를 넘는 quote를 본문의 **연속 부분 문자열**로 200자 안에서 자름. 공백(단어 경계)에서 자르고 말줄임 기호는 붙이지 않음. 그 quote를 가리키는 numbers.value가 모두 들어가는 구간 우선, 안 되면 앞에서부터. 빠진 수치는 기존 규칙대로 지워지고 기록됨
- 코드 소유 칸(Q1). attention은 켜지 않음. 자른 건수·비율을 품질 리포트와 한 주 요약 리포트에
- 반영 뒤 item_card 관문 B 재실행(설계 변경에 따른 재실행이라 COMMON 3장 개선 횟수에 넣지 않음)
- 다시 볼 조건: 한 주 실행에서 잘린 인용이 5% 초과, 또는 잘린 인용 때문에 요약 근거가 약해진 사례

## Q7. 예산 → S2 상한 1.50, 맥 몫 = 상한 − 클라우드 사용액
| 스펙 | 상한 | 클라우드 사용(2차까지) | 맥 몫 |
|---|---|---|---|
| S2 | **1.50** (1.00에서 올림) | 0.3707 | 약 1.12 |
| S3 | 2.00 (유지) | 0.0625 | 약 1.93 |
- `config/budget.yaml`: `S2: 1.50  # 설계 결정 Q7(2026-10-08). 클라우드 0.37 사용, 나머지 맥`, S3 주석은 `클라우드 0.06 사용, 나머지 맥`
- LLM 호출 전 `cost --spec S2/S3`를 적고, 맥 기록 합 + 클라우드 사용액이 상한을 넘을 실행이면 멈추고 질문. 단계 상한 20달러는 그대로

## 리뷰 때 볼 것
Q1 분류가 위 표와 같은지·문턱값 미하향·별도 커밋 / Q6 자른 quote가 본문 연속 부분 문자열인지·잘린 비율 / Q5 두 라벨 파일이 서로 덮어쓰지 않는지 / Q3 녹화에 비밀 없음·합성 기대값 미변경 / 예산 합이 상한 이내

🤖 Generated with [Claude Code](https://claude.com/claude-code)
