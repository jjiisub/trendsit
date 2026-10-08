## 채점표: repo_analyst
채점 대상은 레포 분석 카드(evidence, relevant, why_trending, hype_flags, signal). 근거는 source_fields의 트렌딩 수치(trending), 과열 규칙 결과(hype), 관심 키워드(keywords), 이번 주 글 목록(week_items)과 출력의 evidence(도구 결과에서 옮긴 사실)다.

### 통과 질문 (verdicts)
| id | 질문 |
|---|---|
| Q1 | 관련성: relevant 판단이 관심 키워드와 README·설명(evidence)에 맞나? |
| Q2 | 뜨는 이유: why_trending의 모든 내용이 evidence(도구 결과)로 뒷받침되나? 근거가 없으면 빈 문자열이어야 통과 |
| Q3 | 과열: signal과 hype_flags가 수치(이번 주 별, 7일 커밋, 기여자)와 맞나? 별 수만으로 중요하다고 단정하지 않았나? |

### 보고용 점수 (scores, 1~5)
| 항목 | 5점 | 3점 | 1점 |
|---|---|---|---|
| 근거 | 모든 판단이 도구 결과 사실로 되짚어짐 | 일부 판단이 근거 밖 | 근거 없는 단정 |
| 신호 판단 | signal과 과열 판단이 수치와 정확히 맞음 | 대체로 맞으나 하나가 어긋남 | 수치와 반대 |
| 표현 | 명사형, 평가어 없음 | 군더더기 1개 | 평가어나 홍보 문구 |
