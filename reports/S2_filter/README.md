# S2 임베딩 필터 검증 산출물

> `uv run python -m trendsit filter --since 2026-09-28 --until 2026-10-04 --report`가 만든다. 판정 목록은 `decisions.csv`(점수 내림차순). 임베딩 벡터는 git에 넣지 않는다.

## 실행 환경

| 항목 | 값 |
|---|---|
| 모델 | `Qwen/Qwen3-Embedding-0.6B` |
| 장치 | mps |
| 라이브러리 | sentence-transformers 6.1.0, torch 2.14.1, transformers 5.19.0, 파이썬 3.12.14 |
| 처리 건수 | 325건(글 308, 영상 17), 새 임베딩 325 |
| 걸린 시간 | 155.4초 |
| run_id | `20261008-150730-filter-e3e1` |

## 문턱값(잠정)

- drop_below 0.3, rescue_above 0.45
- 근거: 자리값. 실제 모델 점수 분포를 보기 전(맥 확인 목록)

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
| no_keyword | 23 |
| rescued | 3 |

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

## 문턱값 근처 20건 (±0.05 안팎, 사람 확인용)

| 확인 | id | 소스 | 제목 | 키워드 | 점수 | 판정 |
|---|---|---|---|---|---|---|
| [ ] | 191 | aitimes | [내면 지도 그리기] 36 Inner Mapping: 나를 찾는 지도 | filtered | 0.449758 | drop(no_keyword) |
| [ ] | 908 | aitimes | 과기부, AI중심대학 18개교·AX대학원 15개교 출범 | pass | 0.450665 | keep(keyword_pass) |
| [ ] | 184 | aitimes | '나만의 클로드 코드' 만든다...앤트로픽, 커스텀 확장 기능 '모드' 출시 | pass | 0.450754 | keep(keyword_pass) |
| [ ] | 928 | aitimes | 앤트로픽, 클로드로 이론물리학 난제 ‘9루프 산란 진폭’ 계산 성공 | pass | 0.450783 | keep(keyword_pass) |
| [ ] | 848 | aitimes | 오스트리아, 개인 간 전력 공유 허용…태양광 잉여전력 직접 판매 | pass | 0.300925 | keep(keyword_pass) |
| [ ] | 157 | simonw | Quoting Anthropic Frontier Red Team | pass | 0.448953 | keep(keyword_pass) |
| [ ] | 186 | aitimes | 메타, 오픈소스 '뮤즈 가젯' 공개...AI 에이전트 하드웨어 이식 본격화 | pass | 0.451129 | keep(keyword_pass) |
| [ ] | 950 | aitimes | 'AI 칩 부족' 중국, 엔비디아 PC용 GPU 구매 허용하나 | pass | 0.451383 | keep(keyword_pass) |
| [ ] | 930 | aitimes | AI 불안 확산에 '인간 과학자 vs AI' 연구 맞대결서 '협력'으로 선회 | pass | 0.45145 | keep(keyword_pass) |
| [ ] | 949 | aitimes | 메타, 스마트폰으로 AI 게임 만드는 '호라이즌 크리에이트' 공개 | pass | 0.448431 | keep(keyword_pass) |
| [ ] | 891 | aitimes | 스페인 연구진, 태양광발전소 맹금류 행동 추적…사냥·휴식 공간 활용 | pass | 0.298313 | drop(low_similarity) |
| [ ] | 1003 | geeknews | 벡터 데이터베이스여, 안녕 | pass | 0.451698 | keep(keyword_pass) |
| [ ] | 189 | aitimes | 엔비디아, 4999달러짜리 ‘DGX 스파크’ 출시...메모리 대란에 가격 낮췄다 | pass | 0.448274 | keep(keyword_pass) |
| [ ] | 177 | aitimes | 태양광 발전량·전력가격 예측하는 AI…일본 ESS 충·방전 자동화 | pass | 0.452 | keep(keyword_pass) |
| [ ] | 1022 | geeknews | Muse Gadgets - Meta의 AI 에이전트를 직접 만든 기기에 연결하기 | pass | 0.452747 | keep(keyword_pass) |
| [ ] | 176 | aitimes | 아일랜드, 주택용 태양광·배터리 지원 확대…국내는 마을 단위 실증 | pass | 0.302915 | keep(keyword_pass) |
| [ ] | 1029 | geeknews | Claude와 Claude Code에서 Opus 5.5를 최대한 활용하는 방법 | pass | 0.446866 | keep(keyword_pass) |
| [ ] | 1026 | geeknews | 하네스가 곧 회사다 | pass | 0.446696 | keep(keyword_pass) |
| [ ] | 224 | aitimes | 엔비디아·소프트뱅크, 오픈AI 투자 잔여분 27조 최종 집행 | pass | 0.453368 | keep(keyword_pass) |
| [ ] | 913 | aitimes | 삼성 6개사, 미국 AI 인프라 기업 헬릭스에 1.4조 투자 | pass | 0.453384 | keep(keyword_pass) |

## 되살린 글(rescued) 3건

| id | 소스 | 제목 | 점수 | 가까운 관심사 |
|---|---|---|---|---|
| 961 | geeknews | 계속 승진하는 것이 좋은 커리어일까? 엔지니어 Philip Su의 경험 [동영상] | 0.488066 | dev-practice |
| 966 | geeknews | 글 쓰다가 막혔을 때 대처법 | 0.481487 | dev-practice |
| 965 | geeknews | 서버 모니터링 분석 가이드 | 0.466792 | dev-practice |

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
