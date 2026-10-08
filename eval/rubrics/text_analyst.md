## 채점표: text_analyst
채점 대상은 원본 추적 카드 v2(trail, quotes, verified, differences, origin, summary). 근거는 source_fields의 1차 요약 카드(card_v1), 원래 글 링크(links), 확인할 것(checks)과 출력의 quotes(원본에서 옮긴 문장, 코드가 실제로 가져온 페이지에 있는지 확인함)다.

### 통과 질문 (verdicts)
| id | 질문 |
|---|---|
| Q1 | 원본: origin이 실제 1차 자료(논문, 공식 문서·블로그, 보도자료, 레포)인가? 또 다른 요약·큐레이션 글을 원본으로 삼지 않았나? 못 찾아 null이면 통과 |
| Q2 | 대조: 각 verified 판정(confirmed / differs / not_found)이 그 check와 가리킨 quote의 내용에 맞나? |
| Q3 | 차이: differences의 각 항목이 quotes와 checks로 뒷받침되나? 없는 차이를 만들거나 있는 차이를 놓치지 않았나? |

### 보고용 점수 (scores, 1~5)
| 항목 | 5점 | 3점 | 1점 |
|---|---|---|---|
| 원본 선택 | 가장 1차에 가까운 자료 | 1차 자료지만 더 원본이 링크에 있었음 | 요약 글을 원본으로 |
| 대조 정확성 | 모든 판정이 인용과 맞음 | 하나가 어긋남 | 둘 이상 어긋남 |
| 효율 | 필요한 페이지만 열고 멈춤 | 불필요한 열기 1~2회 | 상한까지 헤맴 |
