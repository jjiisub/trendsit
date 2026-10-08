# S2 질문 (설계 세션에게)

> COMMON 1장: 구현 방향을 바꿀 정도로 모호한 것. 사소한 것은 정하고 `reports/S2_report.md` "결정한 것"에 적었다.

## Q1. repo_oneliner 관문 B: attention 항목을 enforce 후 출력으로 볼지 (0단계, M2)
- S1_REVIEW M2는 "평가의 코드 채점은 enforce 전·후를 둘 다 기록하고, 통과 판정은 원래 출력 기준"이라고 한다. 그대로 구현했다
- 그런데 repo_oneliner의 미달 원인(Images360 attention)이 바로 M2 규칙이 코드로 가져간 칸이다. 원래 출력 기준이면 모델이 같은 답을 내는 한 재실행해도 **코드 9/10(미달) 그대로**이고, enforce 후 출력 기준이면 10/10이다
- 저장된 마지막 전체 실행(`reports/eval/repo_oneliner_generate_20261008-071621.json`)에 enforce를 적용해 다시 채점한 결과: 원래 9/10, enforce 후 10/10. 바뀐 것은 Images360 attention 하나(README 정리 본문 48자 < 200자)
- 선택지: (가) 지금대로 두고 "코드가 지키는 칸"은 리포트에서만 따로 본다 (나) 채점기에 "enforce가 소유한 칸은 enforce 후 출력으로 본다"를 넣는다(채점기 수정이라 설계 세션 결정 필요)
- 지금은 (가)로 두었다
