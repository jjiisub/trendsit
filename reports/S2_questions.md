# S2 질문 (설계 세션에게)

> COMMON 1장: 구현 방향을 바꿀 정도로 모호한 것. 사소한 것은 정하고 `reports/S2_report.md` "결정한 것"에 적었다.

## Q1. repo_oneliner 관문 B: attention 항목을 enforce 후 출력으로 볼지 (0단계, M2)
- S1_REVIEW M2는 "평가의 코드 채점은 enforce 전·후를 둘 다 기록하고, 통과 판정은 원래 출력 기준"이라고 한다. 그대로 구현했다
- 그런데 repo_oneliner의 미달 원인(Images360 attention)이 바로 M2 규칙이 코드로 가져간 칸이다. 원래 출력 기준이면 모델이 같은 답을 내는 한 재실행해도 **코드 9/10(미달) 그대로**이고, enforce 후 출력 기준이면 10/10이다
- 저장된 마지막 전체 실행(`reports/eval/repo_oneliner_generate_20261008-071621.json`)에 enforce를 적용해 다시 채점한 결과: 원래 9/10, enforce 후 10/10. 바뀐 것은 Images360 attention 하나(README 정리 본문 48자 < 200자)
- 선택지: (가) 지금대로 두고 "코드가 지키는 칸"은 리포트에서만 따로 본다 (나) 채점기에 "enforce가 소유한 칸은 enforce 후 출력으로 본다"를 넣는다(채점기 수정이라 설계 세션 결정 필요)
- 지금은 (가)로 두었다

## Q2. 클라우드 환경의 막힌 네트워크와 키 (S2~S3 전체)
- 이 클라우드 세션에는 `OPENROUTER_API_KEY`가 없고, 네트워크 정책이 openrouter.ai, huggingface.co, export.arxiv.org, github.com, 수집 소스 도메인을 막는다. GitHub API도 이 저장소만 열려 있다
- 그래서 LLM 관문 B 5개 역할, 실제 임베딩 점수·문턱값, 실제 한 주 데이터가 필요한 일은 모두 `reports/S2S3_mac_todo.md`로 옮겼다(S2S3_TASK 2장 "없으면 맥 확인 목록으로")
- 다음 클라우드 묶음에서도 같은 일을 하려면 환경 설정에서 위 도메인을 허용하고 키를 환경 변수로 넣어야 한다

## Q3. 합성 GitHub 응답 픽스처 (S3 3c)
- `tests/fixtures/http/repo_tools`의 커밋·기여자·릴리스 응답은 GitHub API 형식대로 만든 합성이다(`meta.json`에 표시). 맥에서 실제 녹화로 바꿀지, 합성을 테스트 전용으로 둘지 정해 주기 바람. 지금은 합성 그대로 두고 맥 확인 목록에 "(선택) 실제 녹화로"를 넣었다

## Q4. 픽스처 수가 스펙보다 적은 것 (S2 2b)
- item_card 픽스처 17건(스펙 20건). 녹화 응답의 실제 글이 16건뿐이라 맥에서 실제 한 주로 3건을 더한다(추가만, 기존은 고치지 않음). 다른 세 역할(repo_analyst 10, editor_plan, text_analyst 10)의 관문 B 픽스처는 실제 데이터가 있어야 만들 수 있어 만드는 명령(`--fixtures`, `--fixture`)만 넣었다
