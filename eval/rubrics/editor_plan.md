## 채점표: editor_plan
채점 대상은 편집장 계획(text_queue, video_queue, repo_queue의 reason과 결정). 근거는 source_fields의 후보 메타데이터(new_videos: 길이, 자막, 설명, 챕터 / repo_candidates / text_candidates)와 keywords, budget이다.

### 통과 질문 (verdicts)
| id | 질문 |
|---|---|
| Q1 | 근거: 각 결정의 reason이 그 후보의 입력 메타데이터(길이, 자막, 설명, relevance, 별 수 등)와 맞나? 메타데이터에 없는 사실을 지어내지 않았나? |
| Q2 | 우선순위: 큐 순서와 고른 항목이 관심 키워드와의 관련성에 맞나? 관련 높은 후보를 빼고 관련 낮은 후보를 넣지 않았나? |

### 보고용 점수 (scores, 1~5)
| 항목 | 5점 | 3점 | 1점 |
|---|---|---|---|
| 근거 | 모든 reason이 메타데이터로 되짚어짐 | 일부 reason이 일반론 | 메타데이터와 어긋남 |
| 배분 | 예산 80% 안에서 관련 높은 것 위주 | 관련 낮은 항목이 섞임 | 예산을 넘기거나 관련 낮은 것 위주 |
| mode 선택 | 자막·발표 형식에 맞는 mode | 하나가 어긋남 | 대부분 어긋남 |
