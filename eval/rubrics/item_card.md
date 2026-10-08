## 채점표: item_card
채점 대상은 글 1차 요약 카드(quotes, numbers, claims, summary, is_curation, origin_candidates, relevance, needs_original). 근거 문서는 글 본문이고, 본문 속 링크 목록(번호, URL, 종류)은 source_fields의 links에 있다.

### 통과 질문 (verdicts)
| id | 질문 |
|---|---|
| Q1 | 충실성: summary와 claims의 모든 내용이 quotes(본문 문장)로 뒷받침되나? |
| Q2 | 핵심: 부수 내용(행사 안내, 구독 권유, 저자 소개)이 아니라 본문의 주된 내용을 담았나? |
| Q3 | 원본 판정: needs_original이 "수치·주장의 출처가 본문 밖 링크에 있는지"와 맞나? |

### 보고용 점수 (scores, 1~5)
| 항목 | 5점 | 3점 | 1점 |
|---|---|---|---|
| 충실성 | 모든 문장이 인용으로 되짚어짐 | 일부가 인용 밖 추론 | 본문에 없는 내용이나 수치 |
| 핵심 포착 | 글의 주된 발표·주장·수치를 담음 | 주된 내용은 있으나 부수 내용이 섞임 | 부수 내용 위주 |
| 판정 | is_curation, relevance, needs_original이 모두 본문과 링크에 맞음 | 하나가 어긋남 | 둘 이상 어긋남 |
