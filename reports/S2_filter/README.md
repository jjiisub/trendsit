# S2 임베딩 필터 검증 산출물

> `uv run python -m trendsit filter --since 2026-09-28 --until 2026-10-04 --report`가 만든다. 판정 목록은 `decisions.csv`(점수 내림차순). 임베딩 벡터는 git에 넣지 않는다.

## 실행 환경

| 항목 | 값 |
|---|---|
| 모델 | `Qwen/Qwen3-Embedding-0.6B` |
| 장치 | mps |
| 라이브러리 | sentence-transformers 6.1.0, torch 2.14.1, transformers 5.19.0, 파이썬 3.12.14 |
| 처리 건수 | 325건(글 308, 영상 17), 새 임베딩 0 |
| 걸린 시간 | 1.6초 |
| run_id | `20261009-000927-filter-e87a` |

## 문턱값(잠정)

- drop_below 0.3, rescue_above 0.5
- 근거: 잠정(labeler opus-5.5, PR #6 리뷰 3장): 2026-09-28~10-04 MPS 점수 + 라벨 40건. drop_below 0.30 유지(0.30~0.32에 관심 글 2건, 시드 keep 0.330), rescue_above 0.50(되살린 3건 모두 관심 밖, 걸러진 0.40 이상 10건에 관심 글 0. 정밀도 61.9→68.4%, 재현율 그대로)

## 판정 요약

| 이유 | 건수 |
|---|---|
| excluded:스포츠 | 1 |
| excluded:시가총액 | 1 |
| excluded:인수 | 3 |
| excluded:정치 | 4 |
| excluded:주가 | 2 |
| excluded:채용 | 1 |
| keyword_pass | 278 |
| low_similarity | 9 |
| no_keyword | 26 |

## 점수 분포 (0.05 구간)

| 구간 | 키워드 통과 | 키워드 걸러짐 |
|---|---|---|
| 0.10~0.15 | 0 | 1 |
| 0.15~0.20 | 1 | 0 |
| 0.20~0.25 | 2 | 1 |
| 0.25~0.30 | 6 | 5 |
| 0.30~0.35 | 18 | 4 |
| 0.35~0.40 | 26 | 9 |
| 0.40~0.45 | 42 | 9 |
| 0.45~0.50 | 73 | 5 |
| 0.50~0.55 | 76 | 3 |
| 0.55~0.60 | 39 | 1 |
| 0.60~0.65 | 4 | 0 |

## 시드 라벨 결과 (`relevance_seed.csv`, 찾은 13/13건 중 맞음 11)

| 소스 | 제목 | 기대 | 점수 | 판정 | 맞음 |
|---|---|---|---|---|---|
| geeknews | LLM Wiki의 불량 페이지를 Jev로 선별하는 것이 가능할까? | keep | 0.477991 | keep | ○ |
| geeknews | Pluto - SOTA 스타크래프트 AI | keep | 0.476133 | keep | ○ |
| techbridge | [한영자막] 400개 기업 데이터로 본 소프트웨어 개발 AI의 현주소입니다 | keep | 0.553146 | keep | ○ |
| techbridge | [한영자막] 팟캐스트 풀버전 - SpaceX에서 매달 수천 개의 PR을 반영하는 방법을 알아봅니다 \| Cur | keep | 0.366139 | keep | ○ |
| techbridge | AI로 무엇이든 효과적으로 학습하는 방법 | keep | 0.485442 | keep | ○ |
| aitimes | 스캐터랩, 캐릭터챗 '제타' 신규 기능 출시..."대화 따라 표정·배경 바뀐다" | keep | 0.475189 | keep | ○ |
| deepmind | Introducing SynthID Bio | keep | 0.365765 | keep | ○ |
| openai | Chatham scales its capital markets expertise with OpenAI | drop | 0.355736 | keep | × |
| anthropic | Barclays scales Claude to upgrade operations and improve cli | drop | 0.328914 | keep | × |
| anthropic | Anthropic invests $100 million to train 10,000 engineers and | keep | 0.329758 | keep | ○ |
| geeknews | 생각을 정리하는 도구로서의 커밋 설명 | keep | 0.428106 | keep | ○ |
| aitimes | 텐센트, 오라클서 AI 칩 10만개 임대…규제 피하려 동남아로 | keep | 0.489645 | keep | ○ |
| aitimes | 알트먼 "기업공개 압박 없이 AI 안전 확보가 우선" | keep | 0.547728 | keep | ○ |

- 못 찾은 행은 분모에서 뺀다(S2S3_TASK 7장)

## 라벨 결과 (`relevance.csv`, 40건, labeler opus-5.5, 잠정)

| keep 정밀도 | keep 재현율 | keep·keep | keep·drop(오판) | drop·keep(놓침) | drop·drop |
|---|---|---|---|---|---|
| 0.684 | 0.929 | 13 | 6 | 1 | 20 |

- 칸 순서: 판정·라벨. 문턱값을 바꾸면 같은 라벨로 다시 잰다

## 문턱값 근처 20건 (±0.05 안팎, 사람 확인용)

| 확인 | id | 소스 | 제목 | 키워드 | 점수 | 판정 |
|---|---|---|---|---|---|---|
| [ ] | 215 | aitimes | 오픈AI, '불량 에이전트' 무단 활동 100여곳 조직에 통보 | pass | 0.500108 | keep(keyword_pass) |
| [ ] | 897 | aitimes | 일관성·제어력 강화한 '클링 4.0' 공개... '시댄스' 추격 나서 | pass | 0.499632 | keep(keyword_pass) |
| [ ] | 854 | aitimes | 오픈AI, 자체 에이전트에 ‘디시전스 API’ 적용...아키텍처 판도 바뀐다 | pass | 0.499617 | keep(keyword_pass) |
| [ ] | 901 | aitimes | 알트먼·아모데이, 호주 의회 AI 청문회 불참...오픈AI는 CSO 파견 | pass | 0.500519 | keep(keyword_pass) |
| [ ] | 861 | aitimes | "앤트로픽 몸값 1.5조 달러로 하향해야"…월가의 AI IPO '거품' 경고 | pass | 0.500601 | keep(keyword_pass) |
| [ ] | 848 | aitimes | 오스트리아, 개인 간 전력 공유 허용…태양광 잉여전력 직접 판매 | pass | 0.300925 | keep(keyword_pass) |
| [ ] | 211 | aitimes | 백악관에 모인 AI 수장들…젠슨 황·저커버그, 아모데이에 '질문 세례' | pass | 0.49874 | keep(keyword_pass) |
| [ ] | 214 | aitimes | “반도체 성능 지표 ‘K-Perf’, 실험실 벗어나 실제 현장서 실증” | pass | 0.498495 | keep(keyword_pass) |
| [ ] | 944 | aitimes | 마키나락스, 'AI 참모' 군 지휘통제체계 적용...을지연습서 실증 나서 | pass | 0.501686 | keep(keyword_pass) |
| [ ] | 891 | aitimes | 스페인 연구진, 태양광발전소 맹금류 행동 추적…사냥·휴식 공간 활용 | pass | 0.298313 | drop(low_similarity) |
| [ ] | 279 | techbridge | [한영자막] Claude Code와 Codex를 인간 연구자들과 경쟁시켰습니다 — Elie Bakouch,  | pass | 0.502863 | keep(keyword_pass) |
| [ ] | 176 | aitimes | 아일랜드, 주택용 태양광·배터리 지원 확대…국내는 마을 단위 실증 | pass | 0.302915 | keep(keyword_pass) |
| [ ] | 915 | aitimes | 교황 "AI 멸망론, 가짜 뉴스 아니다"...트럼프 입장과 대립각 | pass | 0.503123 | keep(keyword_pass) |
| [ ] | 4 | openai | How Albertsons Companies is reimagining retail from the insi | pass | 0.296578 | drop(low_similarity) |
| [ ] | 239 | aitimes | 네이버, 웨일 브라우저 내 'AI 챗' 탑재..."타 서비스 도입도 검토" | pass | 0.50347 | keep(keyword_pass) |
| [ ] | 198 | aitimes | [10월2일] "뜻밖의 주인공은 로그인과 플러그인"…알트먼이 보여준 챗GPT의 다음 무대 | pass | 0.503735 | keep(keyword_pass) |
| [ ] | 179 | aitimes | 루마니아 태양광, 최대 8600억원 금융약정…2028년 가동 목표 | pass | 0.296131 | drop(low_similarity) |
| [ ] | 903 | aitimes | 일레븐랩스, 감정 표현·지연 시간 혁신한 '일레븐 v4' 공개…TTS 아레나 1위 | pass | 0.504623 | keep(keyword_pass) |
| [ ] | 245 | aitimes | 메타, AI 데이터센터 '실험 시설' 지정...수십억달러 세액공제 논란 | pass | 0.494998 | keep(keyword_pass) |
| [ ] | 185 | aitimes | 딥시크, 데스크톱 앱 '딥시크 하네스' 출시..."챗·코딩·문서 통합" | pass | 0.494657 | keep(keyword_pass) |

## 되살린 글(rescued) 0건

| id | 소스 | 제목 | 점수 | 가까운 관심사 |
|---|---|---|---|---|

## 떨어뜨린 글(low_similarity) 9건

| id | 소스 | 제목 | 점수 | 가까운 관심사 |
|---|---|---|---|---|
| 891 | aitimes | 스페인 연구진, 태양광발전소 맹금류 행동 추적…사냥·휴식 공간 활용 | 0.298313 | open-weight |
| 4 | openai | How Albertsons Companies is reimagining retail from the inside out | 0.296578 | open-weight |
| 179 | aitimes | 루마니아 태양광, 최대 8600억원 금융약정…2028년 가동 목표 | 0.296131 | open-weight |
| 164 | simonw | Quoting Muse AI Agent | 0.292698 | eval |
| 151 | simonw | We're going to need default hard budget caps on pretty much everything | 0.279002 | coding-agent |
| 7 | openai | Helping small businesses put AI to work | 0.274969 | agent |
| 156 | simonw | He Built This City | 0.243605 | open-weight |
| 166 | simonw | S3 Is the Future, S3 Is the Past | 0.221068 | open-weight |
| 153 | simonw | Rex's Dino Store | 0.191386 | reasoning |

## 같은 URL 연결 1건

| 경유 항목 | 기준 항목 | 공유 URL |
|---|---|---|
| 1032 geeknews: 거의 모든 서비스에 예산을 넘으면 멈추는 기능이 필요해질 것 | 151 simonw: We're going to need default hard budget  | https://simonwillison.net/2026/Oct/3/default-hard-budget-caps |

## 내용이 비슷한 쌍 상위 30 (keep 글끼리, 합치지 않음. S5 묶기 재료)

| 유사도 | A | B |
|---|---|---|
| 0.9033 | 895 aitimes: "아스트라급 지능을 5분의 1 가격에"…오픈AI, 'GPT-6.1 솔' 공개 | 981 geeknews: OpenAI, GPT-6.1 Sol 공개 |
| 0.9019 | 864 aitimes: 구글, '제미나이 4 아르곤' 공개…성능 1위 탈환에도 "일반 사용 제한" | 997 geeknews: 제미나이 4 아르곤(Argon): 프론티어 인텔리전스의 새로운 시대 |
| 0.8901 | 901 aitimes: 알트먼·아모데이, 호주 의회 AI 청문회 불참...오픈AI는 CSO 파견 | 941 aitimes: '정부망 침투' 여파…호주 상원, 오픈AI·앤트로픽 CEO 소환 |
| 0.8808 | 8 openai: Introducing GPT-6.1 Sol | 981 geeknews: OpenAI, GPT-6.1 Sol 공개 |
| 0.8661 | 866 aitimes: 배경훈 장관 “독파모 계속된다…SPC 프론티어 AI 도전과 병행” | 926 aitimes: 과기부, 국대 AI 중단설 일축..."현 구조로는 프런티어 역부족" 지적도 |
| 0.8653 | 10 openai: Introducing dots | 986 geeknews: OpenAI Dots - 상시 작동하는 AI 에이전트 공개 |
| 0.8421 | 850 aitimes: 비드래프트, 법률 데이터 학습 없이 글로벌 벤치마크 1위 달성 | 929 aitimes: 비드래프트, ‘재귀적 자기개선’ AI로 글로벌 5개 리더보드 석권 |
| 0.841 | 186 aitimes: 메타, 오픈소스 '뮤즈 가젯' 공개...AI 에이전트 하드웨어 이식 본격화 | 1022 geeknews: Muse Gadgets - Meta의 AI 에이전트를 직접 만든 기기에 연결하기 |
| 0.8224 | 211 aitimes: 백악관에 모인 AI 수장들…젠슨 황·저커버그, 아모데이에 '질문 세례' | 909 aitimes: 저커버그·아모데이·젠슨 황, 29일 트럼프와 백악관서 AI 정책 논의 |
| 0.8124 | 924 aitimes: 앤트로픽, '클로드 소네트 5.5' 공개…오퍼스급 지능에 최강 가성비 | 951 aitimes: 앤트로픽, '클로드 소네트 5.5' 출시 임박...오픈AI '데브데이' 견제하나 |
| 0.8052 | 860 aitimes: 업스테이지, sLM '솔라 미니 4' 출시... '프로·미니' 투트랙 본격화 | 1034 geeknews: 업스테이지, GPU 한 장에서 실행하는 Solar Mini 4 발표 |
| 0.8048 | 180 aitimes: "수익성 불투명한 10조달러 투자"...월가, AI 거품 붕괴 경고 | 861 aitimes: "앤트로픽 몸값 1.5조 달러로 하향해야"…월가의 AI IPO '거품' 경고 |
| 0.8038 | 979 geeknews: Jeff - 집에서 학습한 Jev 호환 0.8B 의사결정 모델 | 984 geeknews: Jeeves - 판단 전에 추론하는 Jev 방식의 의사결정 모델 |
| 0.8025 | 861 aitimes: "앤트로픽 몸값 1.5조 달러로 하향해야"…월가의 AI IPO '거품' 경고 | 898 aitimes: 앤트로픽, IPO 추진 속 적자 폭 확대..."매출 12배 늘었지만 영업손실 80 |
| 0.8001 | 18 deepmind: Gemini 4 Argon: our next era of frontier inte | 997 geeknews: 제미나이 4 아르곤(Argon): 프론티어 인텔리전스의 새로운 시대 |
| 0.7974 | 880 aitimes: 오픈AI, 호주 정부망 무단 접근 사과..."재발 방지·특별 조사팀 구성" | 941 aitimes: '정부망 침투' 여파…호주 상원, 오픈AI·앤트로픽 CEO 소환 |
| 0.7945 | 880 aitimes: 오픈AI, 호주 정부망 무단 접근 사과..."재발 방지·특별 조사팀 구성" | 901 aitimes: 알트먼·아모데이, 호주 의회 AI 청문회 불참...오픈AI는 CSO 파견 |
| 0.7901 | 223 aitimes: 앤트로픽, 14일 투자자 행사 개최...11월 추수감사절 전 상장 목표 | 898 aitimes: 앤트로픽, IPO 추진 속 적자 폭 확대..."매출 12배 늘었지만 영업손실 80 |
| 0.7816 | 8 openai: Introducing GPT-6.1 Sol | 895 aitimes: "아스트라급 지능을 5분의 1 가격에"…오픈AI, 'GPT-6.1 솔' 공개 |
| 0.7748 | 223 aitimes: 앤트로픽, 14일 투자자 행사 개최...11월 추수감사절 전 상장 목표 | 861 aitimes: "앤트로픽 몸값 1.5조 달러로 하향해야"…월가의 AI IPO '거품' 경고 |
| 0.7733 | 211 aitimes: 백악관에 모인 AI 수장들…젠슨 황·저커버그, 아모데이에 '질문 세례' | 955 aitimes: 트럼프, 아모데이와 백악관 첫 일대일 만찬 개최 |
| 0.7723 | 1 openai: A model guide for the GPT-6 family | 8 openai: Introducing GPT-6.1 Sol |
| 0.7618 | 220 aitimes: 오픈AI, 내부 기밀 유출 혐의로 정렬·안전팀 연구원 3명 해고 | 874 aitimes: NYT "오픈AI, 직원·외부 연구원 AI 보안 경고 묵살" |
| 0.7615 | 242 aitimes: "증시 폭락해서라도 AI 기업 IPO 막아야"…마이클 버리의 강력 경고 | 861 aitimes: "앤트로픽 몸값 1.5조 달러로 하향해야"…월가의 AI IPO '거품' 경고 |
| 0.7574 | 8 openai: Introducing GPT-6.1 Sol | 158 simonw: GPT 6.1 Sol: Near-Astra intelligence for a fi |
| 0.7554 | 1 openai: A model guide for the GPT-6 family | 981 geeknews: OpenAI, GPT-6.1 Sol 공개 |
| 0.7523 | 158 simonw: GPT 6.1 Sol: Near-Astra intelligence for a fi | 981 geeknews: OpenAI, GPT-6.1 Sol 공개 |
| 0.7513 | 893 aitimes: 오픈AI, 24시간 자율 에이전트 '닷츠' 공개…소비자용 아닌 B2B 승부수 | 986 geeknews: OpenAI Dots - 상시 작동하는 AI 에이전트 공개 |
| 0.7491 | 204 aitimes: 구글 "우주 데이터센터 실현 위해 스타십 최소 1800회 발사 필요" | 916 aitimes: 스페이스X, 스타십 최초 궤도 진입 성공… '우주 데이터센터' 구축 발판 |
| 0.7463 | 984 geeknews: Jeeves - 판단 전에 추론하는 Jev 방식의 의사결정 모델 | 1001 geeknews: 텍스트 분류를 위한 언어 모델: Bag-of-Words에서 Jev까지 |

## 재현

```
uv sync --extra embed
uv run python -m trendsit filter --since 2026-09-28 --until 2026-10-04 --report
uv run python -m trendsit filter-fixtures   # eval/fixtures/filter 20건 점수만(리뷰어 CPU용)
```
