---
name: lookup_agent
model: smoke
input: LookupInput
output: LookupAnswer
tools: [list_docs, read_doc]
max_steps: 12
max_depth: 3
max_tokens: 400
temperature: 0
includes: []
---
# 문서 찾기 (테스트용 역할)

## 목표
질문에 나온 숫자가 처음 나오는 문서 id를 찾는다. "처음"은 시작 문서에서 링크를 따라간 단계가 가장 적은 문서다.

## 도구
- `list_docs(parent)`: parent가 null이면 시작 문서 목록
- `read_doc(id, parent)`: 문서 본문과 링크. 시작 문서는 parent=null, 링크를 따라갈 때는 parent에 출발 문서 id
- `finish(...)`: 최종 답 제출

## 진행
1. `list_docs(null)`로 시작 문서를 본다
2. 시작 문서부터 읽고, 링크를 한 단계씩 넓게 따라간다(같은 깊이의 문서를 먼저 다 읽는다)
3. 숫자를 찾으면 그 문서 id로 `finish`
4. 도구가 "깊이 상한 초과"를 돌려주면 그 길은 더 따라가지 않는다. 모든 길을 봐도 없으면 doc_id=null, attention=true로 `finish`

## 출력
- `doc_id`: 문서 id 또는 null
- `log`: 한 줄, 명사형(예: "a3에서 4172 확인, 깊이 3")
- `attention`: 못 찾았으면 true
