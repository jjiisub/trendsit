# 묶기 리포트 2026-W41

> run `20261013-182607-weekly-c716`. 재현: `uv run python -m trendsit cluster --week 2026-W41 --spec S5`. 문턱값은 임시값(auto 0.8 / border 0.65), 멈춤 지점에서 이 리포트로 확정한다.

> weekly 실행의 묶기 단계

## 1. 요약

| 항목 | 값 |
|---|---|
| 근거 자격 구성원 | 글 186, 영상 15, 레포 13 |
| 제외 | 카드 없는 글 61, digest 없는 영상 6, 관련 없는 레포 0 |
| 묶음 | 201개(토픽 후보 189, 레포만 12) |
| 2채널 이상 / 3채널 | 1 / 0 |
| 1개짜리 묶음 비율(토픽 후보 중) | 178/189 = 94% |
| decide | 묶기 60회 + 별칭 0회 / 상한 60, 상한으로 못 부른 후보 38 |
| 크기 상한(12)으로 막힌 합치기 | 0 |
| 걸린 시간(초) | {'evidence': 0.6, 'normalize': 4.7, 'cluster': 1007.8} |

### 채널 조합 분포(토픽 후보)

| 조합 | 묶음 수 |
|---|---|
| text | 173 |
| video | 15 |
| text + github | 1 |

## 2. 유사도 분포 (문턱값 근거)

전체 쌍 22791(같은 채널 17388, 채널 넘음 5403). 0.05 구간별 쌍 수. 글은 본문 임베딩(관련성 필터), 영상은 digest 요약, 레포는 oneliner + description 임베딩이라 채널을 넘는 유사도는 같은 채널보다 낮게 나오는 경향이 있다.

| 구간 | 같은 채널 | 채널 넘음 | 표시 |
|---|---|---|---|
| 0.30~0.35 | 3684 | 1166 |  |
| 0.35~0.40 | 3349 | 1325 |  |
| 0.40~0.45 | 2462 | 1027 |  |
| 0.45~0.50 | 1168 | 586 |  |
| 0.50~0.55 | 473 | 196 |  |
| 0.55~0.60 | 170 | 67 |  |
| 0.60~0.65 | 69 | 23 |  |
| 0.65~0.70 | 37 | 6 | border~auto(decide) |
| 0.70~0.75 | 18 | 2 | border~auto(decide) |
| 0.75~0.80 | 9 | 0 | border~auto(decide) |
| 0.80~0.85 | 5 | 0 | auto 이상 |
| 0.85~0.90 | 1 | 0 | auto 이상 |
| 0.90~0.95 | 1 | 0 | auto 이상 |
| 0.95~1.00 | 1 | 0 | auto 이상 |

## 3. 묶음 목록 (토픽 후보, 점수 순)

점수 = 관련성 먼저(최고 relevance, 그 등급 항목 수) → 채널 수 → 근거 수. 묶인 이유: seed(첫 항목), embed(같은 채널 auto 이상), decide(판정 same). sim은 묶음 나머지와의 평균 유사도.

### c1860 EmbeddingGemma 2: an open, lightweight multimodal embedding… (text 3, 점수 3319)

- 공유: 이름 ['embeddinggemma2', 'gemma4', 'maeb', 'mteb'], 키워드 ['eval', 'multimodal', 'open-weight', 'rag-search']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1111 | text | high | EmbeddingGemma 2: an open, lightweight multimodal embedding… | seed | - |
| it:1132 | text | high | EmbeddingGemma 2 - 개방형 경량 멀티모달 임베딩 모델 | embed | 0.9572 |
| it:1183 | text | high | 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미지·음성 통합 처리 | decide | 0.7619 |

### c1835 OpenAI “rogue” agent activities found on Wikimedia projects (text 2, 점수 3219)

- 공유: 이름 -, 키워드 ['agent', 'ai-security']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1041 | text | high | OpenAI “rogue” agent activities found on Wikimedia projects | seed | - |
| it:1209 | text | high | 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연관 가능성" | decide | 0.696 |

### c1840 Introducing Mistral Large 4: Le chonk (text 3, 점수 3219)

- 공유: 이름 -, 키워드 ['eval', 'frontier-release']
- **의심**: Mistral Large 3 ↔ Mistral Large 4

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1046 | text | high | Introducing Mistral Large 4: Le chonk | seed | - |
| it:1198 | text | high | 미스트랄, 1조 매개변수 ‘라지 4’ 공개..."사이버 보안·오픈 모델 최상위" | decide | 0.7153 |
| it:1048 | text | mid | Mistral Large 4 | decide | 0.6244 |

### c1850 GPT-6 and Intelligent UI for everyone (text 2, 점수 3219)

- 공유: 이름 ['gpt5.6', 'gpt6'], 키워드 ['frontier-release', 'multimodal']
- **의심**: GPT-5.6 ↔ GPT-6, GPT-5.6 ↔ GPT-6 루나, GPT-5.6 ↔ GPT-6 솔

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1100 | text | high | GPT-6 and Intelligent UI for everyone | seed | - |
| it:1172 | text | high | 오픈AI, 질문에 맞춰 화면 생성하는 'GPT-6' 공개...전 사용자 무료 적용 | embed | 0.8039 |

### c1852 Sharing AI progress in mathematics (text 2, 점수 3219)

- 공유: 이름 ['lean'], 키워드 ['frontier-release', 'reasoning']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1102 | text | high | Sharing AI progress in mathematics | seed | - |
| it:1156 | text | high | [10월8일] “수학 문제 4000개에 AI 투입해 성과”…오픈AI가 보여준 과학연구의 변화 | decide | 0.6964 |

### c1885 Claude Haiku 5.5 (text 2, 점수 3219)

- 공유: 이름 ['claudehaiku5.5', 'gpt6luna'], 키워드 ['eval', 'frontier-release']
- **의심**: Claude Haiku 4.5 ↔ Claude Haiku 5.5

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1144 | text | high | Claude Haiku 5.5 | seed | - |
| it:1180 | text | high | 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.5' 공개 | decide | 0.6743 |

### c1889 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 (text 2, 점수 3219)

- 공유: 이름 -, 키워드 ['agent']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1149 | text | high | 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 | seed | - |
| it:1381 | text | high | 구글, 업무용 Gemini 에이전트 발표 — 장시간 작업과 기억 유지, Claude 지원 | decide | 0.7026 |

### c1986 MS, 에이전트 의사결정 특화 모델 ‘디시전-1’ 공개…오픈AI도 API 정식 출시 (text 2, 점수 3219)

- 공유: 이름 ['gpt6sol'], 키워드 ['eval', 'frontier-release', 'reasoning']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1342 | text | high | MS, 에이전트 의사결정 특화 모델 ‘디시전-1’ 공개…오픈AI도 API 정식 출시 | seed | - |
| it:1377 | text | high | Microsoft-Decision-1 - 선택지별 확률을 반환하는 저비용 의사결정 모델 | decide | 0.7611 |

### c1869 mvschwarz/openrig (text 1 + github 1, 점수 3129)

- 공유: 이름 ['openrig'], 키워드 ['agent', 'coding-agent']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1122 | text | mid | OpenRig - Claude Code와 Codex를 팀으로 운영하는 멀티 에이전트 오케스트레이터 | seed | - |
| rp:mvschwarz/openrig | github | high | mvschwarz/openrig | decide | 0.7432 |

### c1937 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 (text 2, 점수 3119)

- 공유: 이름 ['뉴욕시의회', '메타', '알렉스터너', '앤트로픽', '오픈ai', '제이콥콕슨'], 키워드 ['ai-security']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1219 | text | mid | 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실" 경고 | seed | - |
| it:1249 | text | high | "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | embed | 0.825 |

### c1856 Building advertising for the way people use AI (text 2, 점수 2219)


| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1106 | text | mid | Building advertising for the way people use AI | seed | - |
| it:1207 | text | mid | 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생성 옆 노출 | decide | 0.6923 |

### 1개짜리 토픽 후보

| 묶음 | 구성원 | 채널 | relevance | 제목 | 점수 |
|---|---|---|---|---|---|
| c1837 | it:1043 | text | high | llm-openai-decisions 0.1a0 | 3119 |
| c1851 | it:1101 | text | high | How Jump Trading is scaling quant research with ChatGPT | 3119 |
| c1853 | it:1103 | text | high | Advancing computer use with Ironclad | 3119 |
| c1854 | it:1104 | text | high | Atlassian and OpenAI expand partnership to turn enterprise … | 3119 |
| c1855 | it:1105 | text | high | Our approach to EU text provenance rules | 3119 |
| c1857 | it:1108 | text | high | Introducing the Anthropic Cyber Mission | 3119 |
| c1859 | it:1110 | text | high | Expanding the Cyber Verification Program | 3119 |
| c1862 | it:1113 | text | high | MCPB로 로컬 MCP 서버를 Claude Desktop 원클릭 확장으로 만들기 | 3119 |
| c1867 | it:1120 | text | high | AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재설계하기 | 3119 |
| c1868 | it:1121 | text | high | Claude Code 모드(mod) 시작하기 | 3119 |
| c1870 | it:1123 | text | high | 에이전트가 쓴 테스트는 무엇을 증명하나 | 3119 |
| c1875 | it:1129 | text | high | 우리가 알던 오픈소스는 죽었다 | 3119 |
| c1877 | it:1131 | text | high | 소프트웨어 팩토리 패턴 시도하기 | 3119 |
| c1878 | it:1133 | text | high | 나는 인류를 멸종시키고 있는 AGI다 | 3119 |
| c1880 | it:1136 | text | high | openTPU - AI가 설계하고 실제 FPGA에서 모델을 실행하는 오픈소스 AI 가속기 | 3119 |
| c1886 | it:1145 | text | high | Quoting Felix Rieseberg | 3119 |
| c1891 | it:1154 | text | high | 한국 금융권 공격한 중국 26세 해커…'어설픈 신원 노출'로 덜미 | 3119 |
| c1895 | it:1159 | text | high | 카카오, 국제 AI 학회서 MoE 학습 최적화·모델 경량화 성과 공개 | 3119 |
| c1896 | it:1160 | text | high | 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정 모델 ‘d1-3B’ 출시 | 3119 |
| c1897 | it:1161 | text | high | MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최적화 공개 | 3119 |
| c1899 | it:1163 | text | high | '헤르메스 에이전트' 누스 리서치, 대규모 투자 유치로 기업용 시장 진출 | 3119 |
| c1901 | it:1165 | text | high | MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개변수 모델 직접 구동 | 3119 |
| c1902 | it:1167 | text | high | "독파모·모두의 AI 더 안전하게"...SKT, 업스테이지와 AI 보안 동맹 결성 | 3119 |
| c1909 | it:1179 | text | high | [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 더 쓸 수 있었다” | 3119 |
| c1910 | it:1181 | text | high | 구글, ‘나노 바나나 2.1’ 공개...성능 높이고 비용은 반값으로 | 3119 |
| c1912 | it:1184 | text | high | 스튜어트 러셀의 경고 "LLM 정렬 불가능…모방 학습과 RLHF 한계" | 3119 |
| c1913 | it:1185 | text | high | 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' 직접 호출 | 3119 |
| c1917 | it:1189 | text | high | 하크, '스마트폰 대체' AI 에이전트 공개...2027년 전용 기기 출시 | 3119 |
| c1919 | it:1191 | text | high | 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의무화 찬성" | 3119 |
| c1920 | it:1193 | text | high | "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오토리뷰’ 전면 무료화 | 3119 |
| c1925 | it:1205 | text | high | '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개…반응은 엇갈려 | 3119 |
| c1926 | it:1206 | text | high | MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 축소 | 3119 |
| c1929 | it:1211 | text | high | 코히어, 에이전트 비용·보안 통제 플랫폼 '노스 2' 출시...알레프 알파 인수 후 첫 행보 | 3119 |
| c1931 | it:1213 | text | high | 19세 청년의 반란...고스트, 개인용 AI PC '코어'로 147억 투자 유치 | 3119 |
| c1935 | it:1217 | text | high | “180B 모델, 개인용 노트북으로 구동”...비드래프트, 고성능 모델 경량화 전략 이어간다 | 3119 |
| c1941 | it:1223 | text | high | 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날부터 처리 속도 50% 향상 | 3119 |
| c1943 | it:1225 | text | high | 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만 우선 적용 | 3119 |
| c1946 | it:1231 | text | high | 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | 3119 |
| c1948 | it:1233 | text | high | 뉴럴링크, 5만시간 뇌 데이터 사전학습…BCI도 '파운데이션 모델' 시대 열렸다 | 3119 |
| c1949 | it:1235 | text | high | KAIST, 데이터 변화해도 검색 정확도 유지하는 ‘CONDA’ 기술 개발 | 3119 |
| c1950 | it:1236 | text | high | a16z "미국 가구 2.2%만 AI 유료 구독…기술이 경기 순환 핵심 주도" | 3119 |
| c1951 | it:1237 | text | high | GPT-6 아스트라, 217년 된 나폴레옹 암호 6시간 만에 해독 | 3119 |
| c1952 | it:1238 | text | high | MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 비용 병목' 해결 | 3119 |
| c1954 | it:1240 | text | high | AI가 쏟아낸 '엉터리 제보'에... 구글, 오픈소스 버그 바운티 일시 중단 | 3119 |
| c1955 | it:1241 | text | high | 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가상 착용' 도입 | 3119 |
| c1956 | it:1242 | text | high | 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 | 3119 |
| c1958 | it:1245 | text | high | "지기 싫어서 남의 코드 복사"…아스트라, 스타크래프트 벤치마크서 꼼수 | 3119 |
| c1959 | it:1246 | text | high | 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규제 경고 폭풍 | 3119 |
| c1966 | it:1303 | text | high | 앤트로픽 '클로드 사이언스', 인류 최초 자외선 전체 하늘 지도 완성 | 3119 |
| c1969 | it:1307 | text | high | 앤트로픽, ‘클로드 대시보드·모션’ 공개…"기업 데이터 분석·영상 제작" | 3119 |
| c1972 | it:1310 | text | high | "오픈소스 취약점 AI가 잡는다"...앤트로픽, 무료 보안 검사 도구 공개 | 3119 |
| c1974 | it:1319 | text | high | Expo bets big on React Native's agentic future | 3119 |
| c1977 | it:1323 | text | high | 수학자가 Lean 정리 증명기에 대해 알아야 할 것: 신뢰성과 AI | 3119 |
| c1981 | it:1333 | text | high | Quoting The New York Times | 3119 |
| c1982 | it:1335 | text | high | 저커버그, 경쟁 제품 압박에 안전 우려에도 ‘뮤즈’ 출시 강행 | 3119 |
| c1985 | it:1341 | text | high | 엔비디아, AI 추론 칩 d-매트릭스에 투자 계획…GPU 중심 생태계 확장 | 3119 |
| c1988 | it:1344 | text | high | 알리바바, 연산 단계 줄여 속도·효율 높인 '큐원 이미지 2.1 터보' 공개 | 3119 |
| c1989 | it:1345 | text | high | 메타 인수 무산된 마누스, 6700억 투자 유치로 독립 경영 가속 | 3119 |
| c1990 | it:1346 | text | high | 물리 법칙 실시간 예측하는 월드 모델 '오딧세이-3' 공개..."벤치마크 최고 기록" | 3119 |
| c1992 | it:1348 | text | high | 백악관, AI 기업 '보안 사고' 보고 의무화...앤트로픽 침해 사건이 계기 | 3119 |
| c1994 | it:1350 | text | high | 앤트로픽 AI, 경찰 미제사건 제보 사이트에 '허위 제보' 소동 | 3119 |
| c1995 | it:1351 | text | high | 타입세이프, '제브' 출시 3주 만에 대규모 투자 유치...기업가치 10조 등극 | 3119 |
| c1997 | it:1353 | text | high | 구글, '제미나이 4 아르곤' 후속 '카본' 테스트 중…"오퍼스 5.5 수준" | 3119 |
| c2000 | it:1376 | text | high | 코딩 에이전트는 왜 이렇게 멍청할까? | 3119 |
| c2002 | it:1379 | text | high | Eve - 디렉터리 하나로 AI 에이전트를 정의하고 배포하는 Vercel 프레임워크 | 3119 |
| c2004 | it:1390 | text | high | 중국 AI 모델 안전성 평가 공개율 3.6%...출시 전 공개는 고작 1.1% | 3119 |
| c2005 | it:1391 | text | high | 나델라 “AI에도 비상 브레이크 필요”...인간 통제·독립 감사 강조 | 3119 |
| c2020 | vd:0kVsv2WlL44 | video | high | [한영자막] AI 에이전트에 학습하는 메모리를 제공해 보세요 — Jake Broekhuizen, LangC… | 3119 |
| c2021 | vd:31XD1O74pks | video | high | [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게 해보세요 | 3119 |
| c2022 | vd:5bg469hWGGc | video | high | [한영자막] 대시보드는 끝났습니다: AI 에이전트가 소프트웨어를 쓰는 법 | 3119 |
| c2023 | vd:5tdMgKkX5dU | video | high | [한영자막] 팟캐스트 풀버전 - SpaceX에서 매달 수천 개의 PR을 반영하는 방법을 알아봅니다 ／ Cu… | 3119 |
| c2025 | vd:8DRjkp_X8yY | video | high | [한영자막] AI 시대에 쏟아지는 PR 병목, 어떻게 해결해야 할까요? | 3119 |
| c2026 | vd:D7q8fa589FY | video | high | [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이 구조'를 도입해야 합니다 | 3119 |
| c2027 | vd:HjQ1G1NvvHQ | video | high | [한영자막] 인간은 비동기 API입니다: AI 에이전트가 사람을 기다리다 멈추지 않는 법 | 3119 |
| c2029 | vd:RVnSsolR3uE | video | high | [한영자막] Codex로 요리하기 — OpenAI의 Charlie Guo와 Gabriel Chua | 3119 |
| c2030 | vd:eTtZlAPA9H4 | video | high | [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Salomon, AgentCraft | 3119 |
| c2031 | vd:kcflfXb6dBM | video | high | [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 어떻게 바뀔까요? | 3119 |
| c2032 | vd:oeL0uP-NO-U | video | high | [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니다 — Sourcegraph Dan … | 3119 |
| c2033 | vd:sAu_4QuAI0w | video | high | [한영자막] 하네스 엔지니어링: 코딩 에이전트로 '소프트웨어 팩토리'를 만드는 방법 | 3119 |
| c2034 | vd:wrii8VocfZU | video | high | [한영자막] 샘 알트만이 OpenAI와 일상을 운영하기 위해 AI를 실제로 활용하는 방법입니다. | 3119 |
| c1839 | it:1045 | text | mid | EmbeddingGemma 2 | 2119 |
| c1843 | it:1050 | text | mid | Scrimshaw Jukebox | 2119 |
| c1847 | it:1097 | text | mid | Disrupting AI-enabled “false front” operations | 2119 |
| c1848 | it:1098 | text | mid | Helping teens learn, plan, and shape the future of AI | 2119 |
| c1858 | it:1109 | text | mid | 2026 Usage Policy update | 2119 |
| c1861 | it:1112 | text | mid | OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 AI 에이전트 | 2119 |
| c1864 | it:1116 | text | mid | AI가 코드를 쓸수록 도메인 주도 설계가 더 중요해지는 이유 | 2119 |
| c1872 | it:1126 | text | mid | Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호스팅 AI 비서 | 2119 |
| c1876 | it:1130 | text | mid | 여러 팀의 시스템을 이해하기 위한 AI 집단 지성 구축하기 | 2119 |
| c1881 | it:1138 | text | mid | Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소스 작업 공간 | 2119 |
| c1887 | it:1146 | text | mid | Qwen3.8 27B addition in words | 2119 |
| c1888 | it:1148 | text | mid | 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 요동 | 2119 |
| c1893 | it:1157 | text | mid | 구글, 텍스트 입력으로 게임 만드는 플랫폼 공개…유니티와 협력 | 2119 |
| c1894 | it:1158 | text | mid | 머스크 “테라팹 직접 운영한다”…TSMC 위탁운영설 일축 | 2119 |
| c1903 | it:1168 | text | mid | 저커버그 부부의 바이오허브, 미 정부·구글과 2.4조 AI 생물학 데이터 구축 | 2119 |
| c1904 | it:1169 | text | mid | 메타 '뮤즈', 스마트폰 이어 아이패드용 앱 출시…업무용 도구 연동 강화 | 2119 |
| c1905 | it:1170 | text | mid | 구글, AI 생성물 구분하는 '신스ID 감지기' 일반에 전면 공개 | 2119 |
| c1906 | it:1171 | text | mid | 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 121만개 확보 나선다 | 2119 |
| c1907 | it:1173 | text | mid | 삼성전자, 3분기 영업익 107조...애플·엔비디아도 못 넘은 '100조' 첫 달성 | 2119 |
| c1908 | it:1178 | text | mid | [AI리더의 서가] Agentic AI 구축 개발의 모든 것 | 2119 |
| c1911 | it:1182 | text | mid | "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정황 포착 | 2119 |
| c1914 | it:1186 | text | mid | 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | 2119 |
| c1915 | it:1187 | text | mid | AMD, 연내 국내 'AI 연구센터' 설립...정부와 메가프로젝트 협력 추진 | 2119 |
| c1918 | it:1190 | text | mid | 구글, AI 데이터센터 전력 확보 위해 3.6GW 규모 원전 계약 체결 | 2119 |
| c1922 | it:1196 | text | mid | 딥시크, 투자 수요 폭발…IPO 전 자금 조달 규모 2배 확대 | 2119 |
| c1923 | it:1203 | text | mid | [AI리더의 서가] SQL부터 AI까지 데이터 분석 with 클로드 코드 | 2119 |
| c1924 | it:1204 | text | mid | [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트로픽과 근본적으로 다르다” | 2119 |
| c1927 | it:1208 | text | mid | 노르웨이, 공공장소 ‘AI 안경’ 일시 금지 추진…세계 첫 규제 움직임 | 2119 |
| c1928 | it:1210 | text | mid | [게시판] 두산로보틱스, 989억 규모 피지컬 AI 국책과제 2건 선정 등 단신 | 2119 |
| c1930 | it:1212 | text | mid | 엔비디아-그로크 27조 계약 파장…소외된 엔지니어들 "거래 불공정" 소송 | 2119 |
| c1932 | it:1214 | text | mid | [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용접 솔루션’ 공동개발 협력 등 단신 | 2119 |
| c1934 | it:1216 | text | mid | 카카오모빌리티, 고려대와 AX 협력…모빌리티 핵심 기술 국방 분야 접목 | 2119 |
| c1936 | it:1218 | text | mid | 이탈리아 멜로니 총리, AI 딥페이크 막으려 '목소리 상표권' 신청 | 2119 |
| c1939 | it:1221 | text | mid | '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 아니다" | 2119 |
| c1945 | it:1230 | text | mid | 구글, 'AI 프로' 국내 한정 40% 할인...연간 구독권 프로모션 진행 | 2119 |
| c1947 | it:1232 | text | mid | 앤트로픽, 10월6일까지 '음성 인터뷰어' 가동…대화록 공개·음성 학습 수집 결합 | 2119 |
| c1953 | it:1239 | text | mid | 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부담 낮춘다 | 2119 |
| c1957 | it:1243 | text | mid | "전직 미국 관료 사칭"…중국 해커, AI 정책 전문가 계정 노렸다 | 2119 |
| c1960 | it:1247 | text | mid | 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안전성에 이례적 경고 | 2119 |
| c1961 | it:1248 | text | mid | 'AI 피해자 영상'에 속아 내려진 중형..."형량 잘못됐다" 선고 파기 | 2119 |
| c1962 | it:1250 | text | mid | [AI리더의 서가] AI 루프를 설계하라 | 2119 |
| c1964 | it:1252 | text | mid | 트럼프, ‘슈퍼 인텔리전스 부대’ 출범…국가정보국장, 백악관 AI 차르 겸임 | 2119 |
| c1965 | it:1300 | text | mid | Quoting Matthew Green | 2119 |
| c1967 | it:1304 | text | mid | 오픈AI, 연구원 해고 논란 해명..."안전 제기 보복 아닌 보안 위반" | 2119 |
| c1968 | it:1306 | text | mid | 데이터센터 전문 퍼머스, 호주 IPO 철회…'엔비디아 후광'도 안 통했다 | 2119 |
| c1971 | it:1309 | text | mid | 아마존, 안드로이드 태블릿 첫 출시…프리미엄 시장 도전 | 2119 |
| c1973 | it:1318 | text | mid | vgpu - 브라우저와 Node.js에서 같은 코드로 쓰는 경량 WebGPU 라이브러리 | 2119 |
| c1975 | it:1321 | text | mid | 프로그래밍은 특별하지 않다 | 2119 |
| c1976 | it:1322 | text | mid | 누구도 섬이 아니다 - AI가 지적 공동체를 해체할 때 | 2119 |
| c1984 | it:1338 | text | mid | 앤트로픽, 자체 음성 모델 개발하나…클로드 웹에 ‘보이스’ 메뉴 포착 | 2119 |
| c1996 | it:1352 | text | mid | "6~12개월 내 터진다"…주요 AI 기업, 최악의 AI 재난 시나리오 가동 | 2119 |
| c1999 | it:1375 | text | mid | REA Reverse - 무엇이든 리버스 엔지니어링하기 | 2119 |
| c2001 | it:1378 | text | mid | MXC - 샌드박스 코드 실행 시스템 | 2119 |
| c2006 | it:1392 | text | mid | [기고] 한국딥러닝 "기업 4곳 중 3곳이 AI 데이터에 투자…이제 ‘AI-레디’만으론 부족" | 2119 |
| c2007 | it:1393 | text | mid | 엔비디아, 미국 오픈소스 대표 리플렉션 AI 인수·투자 확대 논의 | 2119 |
| c2024 | vd:6YuIp-MwPv4 | video | mid | [한영자막] Uber에서 디버깅 에이전트 하네스를 구축하는 방법 — Kriti Dangi | 2119 |
| c2028 | vd:PACIHCnvNMo | video | mid | [한영자막] 젠슨 황과 일론 머스크가 직접 밝히는 슈퍼 인텔리전스와 에너지, 우주 컴퓨팅의 미래 | 2119 |
| c1836 | it:1042 | text | mid | Quoting Victoria Kim | 2118 |
| c1898 | it:1162 | text | mid | 누리호 올라탄 토종 AI 반도체, 우주 궤도서 성능 실증 나선다 | 2118 |
| c1938 | it:1220 | text | mid | 포지큐브, 롯데벤처스와 멀티 AI 에이전트 기반 AX 추진 | 2118 |
| c1838 | it:1044 | text | mid | llm-mistral 0.16 | 2116 |
| c1834 | it:1039 | text | low | Anti-Patterns in Software Blogging | 1119 |
| c1844 | it:1094 | text | low | How Oracle turns days of work into minutes with ChatGPT and… | 1119 |
| c1845 | it:1095 | text | low | Pollo AI turns creative ideas into campaigns with OpenAI | 1119 |
| c1846 | it:1096 | text | low | LegalOn halves Codex costs while maintaining development sp… | 1119 |
| c1849 | it:1099 | text | low | Radisson Hotel Group brings hotel discovery into ChatGPT | 1119 |
| c1863 | it:1115 | text | low | 「Quo Vadis, Mathematics?」—“수학이여, 어디로 가는가?” | 1119 |
| c1874 | it:1128 | text | low | 자율주행 데이터에서 시간은 어떻게 맞춰지는가 | 1119 |
| c1882 | it:1141 | text | low | ttok 0.4 | 1119 |
| c1883 | it:1142 | text | low | Quoting Carson Gross | 1119 |
| c1884 | it:1143 | text | low | Quoting Ben Affleck | 1119 |
| c1890 | it:1151 | text | low | 여수, 23~24일 독서문화축제…야외 독서·섬 체험 운영 | 1119 |
| c1892 | it:1155 | text | low | [AI리더의 서가] 이너 프롬프트 | 1119 |
| c1900 | it:1164 | text | low | 오픈AI "10대 챗GPT 평균 15분 사용" 주장에 안전성 논란 불붙어 | 1119 |
| c1916 | it:1188 | text | low | [게시판] SKT, 독파모 'A.X K2'로 순우리말 선정·글꼴 제작 등 단신 | 1119 |
| c1921 | it:1194 | text | low | 전남광주, 여수서 9~11일 ‘세계 김밥&소금 페스티벌’ | 1119 |
| c1933 | it:1215 | text | low | 화웨이, 퀄컴에 '로직폴딩' 칩 관련 특허 라이선스 제공 | 1119 |
| c1940 | it:1222 | text | low | 헨켈, SEDEX 2026서 AI·HBM 시대 위한 첨단 패키징 소재 솔루션 선보여 | 1119 |
| c1942 | it:1224 | text | low | LG전자, 북미서 5GW 규모 AIDC 냉각솔루션 장기계약 체결 | 1119 |
| c1944 | it:1229 | text | low | [AI리더의 서가] CEO의  AI | 1119 |
| c1963 | it:1251 | text | low | 머스크, '스페이스XSI'로 리브랜딩 시사…트럼프 'SI' 발언 동조 | 1119 |
| c1970 | it:1308 | text | low | 애플, 10월 말 첫 터치스크린 맥북 공개...M6 칩으로 전문가 시장 공략 | 1119 |
| c1978 | it:1325 | text | low | AI 시대, 수학 진로를 고민하는 학생들에게 무엇을 말해줘야 할까? | 1119 |
| c1980 | it:1332 | text | low | Python 3.15.0 added to actions/python-versions | 1119 |
| c1983 | it:1336 | text | low | 전남광주, 여성폭력 피해지원 종사자 교육…복합사례·2차 피해 예방 | 1119 |
| c1987 | it:1343 | text | low | 테슬라, 유럽 승인 위해 'FSD' 명칭 떼고 '보조 주행'으로 교체 | 1119 |
| c1991 | it:1347 | text | low | [AI 이슈트렌드] 대통령 지지율 제자리 속 은행권 해킹·누리호 발사·북한 도발 주목 | 1119 |
| c1993 | it:1349 | text | low | 목포항구축제 16일 개막…파시·수산물 경매·항구 미식 한자리 | 1119 |
| c2003 | it:1380 | text | low | 중학생이 AI(Claude)와 함께 '자기 자신을 통과하지 못하는 입체' 추측을 증명 | 1119 |
| c1841 | it:1047 | text | low | Using Parseable with Datasette for OpenTelemetry traces | 1118 |
| c1842 | it:1049 | text | low | datasette-atom 0.11a0 | 1117 |
| c1998 | it:1355 | text | low | [AI카툰] Bob, Senior IT guy - 밥, 마운자로 효과 보면… | 1116 |
| c1865 | it:1117 | text | low | AI 시대의 커리어 조언 - 문제를 푸는 능력보다 찾고 선택하는 능력 | 1110 |
| c1866 | it:1119 | text | low | AI로 의도, 품질, 예술성을 확장하는 법 [영상] | 1110 |
| c1871 | it:1125 | text | low | AI 시대, 매니저의 길 | 1110 |
| c1873 | it:1127 | text | low | jev가 여는 비즈니스 AI: 에이전트에서 컴포넌트로 | 1110 |
| c1879 | it:1135 | text | low | 제프리 카첸버그 - 세상이 바뀌고 있다: 창의성을 위한 AI | 1110 |
| c1979 | it:1328 | text | low | 컴퓨터는 결정을 내릴 수 없다 | 1110 |

### 레포만 있는 묶음(토픽 후보 아님, 홈 레포 목록)

- c2008: rp:NVIDIA/OpenShell
- c2009: rp:NousResearch/hermes-agent
- c2010: rp:Panniantong/Agent-Reach
- c2011: rp:anthropics/claude-code
- c2012: rp:cursor/plugins
- c2013: rp:earthtojake/text-to-cad
- c2014: rp:heygen-com/hyperframes
- c2015: rp:mattpocock/skills
- c2016: rp:ollama/ollama
- c2017: rp:openai/codex
- c2018: rp:thedotmack/claude-mem
- c2019: rp:tile-ai/tilelang

## 4. decide 판정

60건. confidence 0.6 미만은 묶지 않음.

| a | b | 채널 넘음 | sim | 공유 | answer | conf | reason |
|---|---|---|---|---|---|---|---|
| it:1132 EmbeddingGemma 2 - 개방형 경량 멀티모… | it:1183 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미… |  | 0.798 | embeddinggemma2, gemma4, maeb, eval, mu… | same | 0.95 | a, b 모두 Google의 EmbeddingGemma 2 모델 공개를 다룸 |
| it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.… | it:1165 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개.… |  | 0.7944 | mai코드1.1플래시, 마이크로소프트, 서피스랩톱울트라, ai-secu… | diff | 0.8 | a는 서피스 랩톱 울트라 출시에 맞춰 공개된 MAI-코드-1.1 플래시의 온디바이스 최적화 버전(모델 성능·축소)에 초점을 맞춘 글, b는 서… |
| it:1342 MS, 에이전트 의사결정 특화 모델 ‘디시전-1’ 공… | it:1377 Microsoft-Decision-1 - 선택지별 확… |  | 0.7611 | gpt6sol, eval, frontier-release | same | 0.95 | a는 마이크로소프트의 '디시전-1' 모델 공개를 다루며, b는 'Microsoft-Decision-1' 모델의 상세 스펙과 벤치마크를 다루므로… |
| it:1149 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·… | it:1182 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화… |  | 0.7558 | agent | diff | 0.95 | a는 구글 클라우드의 기업용 '제미나이 에이전트' 출시, b는 구글 제미나이의 개인용 '제미나이 콜링' 기능 확대 → 다른 제품 |
| it:1122 OpenRig - Claude Code와 Codex를… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.7432 | openrig, agent, coding-agent | same | 0.95 | a는 OpenRig 오케스트레이터 소개, b는 OpenRig 공식 레포 → 같은 제품 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1348 백악관, AI 기업 '보안 사고' 보고 의무화...앤… |  | 0.7396 | 앤트로픽, ai-security | diff | 0.95 | a는 호주 청문회에서의 규제 찬성, b는 백악관의 사고 보고 의무화 발표 → 다른 사건 |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보… | it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… |  | 0.7327 | - | diff | 0.95 | a는 Claude Opus 5.5의 구독 가치 분석, b는 Claude Haiku 5.5 출시 발표 → 같은 회사지만 다른 모델 라인업 |
| it:1111 EmbeddingGemma 2: an open, li… | it:1183 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미… |  | 0.7258 | embeddinggemma2, gemma4, maeb, eval, mu… | same | 0.95 | a, b 모두 Google DeepMind의 EmbeddingGemma 2 모델 공개를 다룸 |
| it:1046 Introducing Mistral Large 4: … | it:1198 미스트랄, 1조 매개변수 ‘라지 4’ 공개..."사이… |  | 0.7153 | mistral, eval, frontier-release | same | 0.95 | a는 Mistral Large 4 공식 발표, b는 Mistral Large 4 공개 및 벤치마크 보도 → 같은 모델 |
| it:1044 llm-mistral 0.16 | it:1046 Introducing Mistral Large 4: … |  | 0.7146 | mistrallarge4, open-weight | diff | 0.95 | a는 llm-mistral 0.16 릴리스, b는 Mistral Large 4 모델 출시 발표 → 다른 대상 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서… |  | 0.7079 | 오픈ai, agent, ai-security | diff | 0.9 | a는 호주 청문회 출석 및 규제 찬성, b는 전 세계적 법적·규제 경고 및 IPO 연기 등 다른 사건을 다룸 |
| it:1160 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정… | it:1342 MS, 에이전트 의사결정 특화 모델 ‘디시전-1’ 공… |  | 0.7075 | eval, reasoning | diff | 0.95 | a는 리퀴드 AI의 d1-3B 모델 출시, b는 마이크로소프트의 디시전-1 모델 공개 → 다른 회사의 다른 모델 |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.7053 | - | diff | 0.95 | a는 AI 구독 서비스의 가격 대비 가치 비교 분석, b는 기업들의 클로드 사용량 축소 사건 → 다른 주제 |
| it:1112 OpenMuse - 브라우저와 터미널로 일하는 오픈소… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.7045 | agent | diff | 0.95 | a는 OpenMuse, b는 openrig → 서로 다른 에이전트 도구 |
| it:1122 OpenRig - Claude Code와 Codex를… | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… |  | 0.7039 | claudecode, codex, agent, coding-agent | diff | 0.95 | a는 OpenRig, b는 Lemma → 서로 다른 오픈소스 에이전트 오케스트레이션/워크스페이스 도구 |
| it:1149 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·… | it:1381 구글, 업무용 Gemini 에이전트 발표 — 장시간 … |  | 0.7026 | agent | same | 0.95 | a는 '제미나이 에이전트' 출시, b는 'Gemini agent' 발표 → 같은 제품 |
| it:1185 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '… | it:1307 앤트로픽, ‘클로드 대시보드·모션’ 공개…"기업 데이… |  | 0.6979 | claude, 앤트로픽 | diff | 0.95 | a는 구글 워크스페이스 연동 기능, b는 대시보드·모션 등 다른 제품군 공개 → 다른 발표 |
| it:1102 Sharing AI progress in mathem… | it:1156 [10월8일] “수학 문제 4000개에 AI 투입해 … |  | 0.6964 | lean, frontier-release, reasoning | same | 0.95 | a와 b 모두 OpenAI가 내부 프런티어 모델로 생성한 수학 결과를 GitHub에 공개한 동일한 발표를 다룸 |
| it:1041 OpenAI “rogue” agent activiti… | it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단… |  | 0.696 | agent, ai-security | same | 0.95 | a, b 모두 OpenAI의 'rogue' 에이전트가 위키미디어 재단에서 일으킨 활동과 5월 장애 연관성을 다룸 |
| it:1181 구글, ‘나노 바나나 2.1’ 공개...성능 높이고 … | it:1344 알리바바, 연산 단계 줄여 속도·효율 높인 '큐원 이… |  | 0.6956 | frontier-release, multimodal | diff | 0.95 | a는 구글의 '나노 바나나 2.1', b는 알리바바의 '큐원 이미지 2.1 터보' → 다른 회사의 다른 모델 |
| it:1106 Building advertising for the … | it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생… |  | 0.6923 | - | same | 0.95 | a와 b 모두 OpenAI가 ChatGPT에 시각적 광고 포맷을 도입하는 발표를 다룸 |
| it:1046 Introducing Mistral Large 4: … | it:1048 Mistral Large 4 |  | 0.6892 | mistrallarge4, eval, frontier-release | same | 0.9 | a는 Mistral Large 4 출시 발표, b는 Mistral Large 4를 포함한 모델들의 벤치마크 테스트 → 같은 모델 |
| it:1169 메타 '뮤즈', 스마트폰 이어 아이패드용 앱 출시…업… | it:1335 저커버그, 경쟁 제품 압박에 안전 우려에도 ‘뮤즈’ … |  | 0.6888 | 메타, 센서타워, agent | diff | 0.0 | 대체 출력: LLMError |
| it:1348 백악관, AI 기업 '보안 사고' 보고 의무화...앤… | it:1350 앤트로픽 AI, 경찰 미제사건 제보 사이트에 '허위 … |  | 0.6835 | ftc, 앤트로픽, ai-security | diff | 0.0 | 대체 출력: LLMError |
| it:1105 Our approach to EU text prove… | it:1225 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만… |  | 0.6832 | codex, ai-security | diff | 0.0 | 대체 출력: LLMError |
| it:1307 앤트로픽, ‘클로드 대시보드·모션’ 공개…"기업 데이… | it:1338 앤트로픽, 자체 음성 모델 개발하나…클로드 웹에 ‘보… |  | 0.6831 | claude, 앤트로픽 | diff | 0.0 | 대체 출력: LLMError |
| it:1171 스페이스X, AI 칩 구매에 53조 조달 추진...G… | it:1239 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스… |  | 0.6757 | 엔비디아 | diff | 0.95 | a는 스페이스X의 GPU 구매 자금 조달, b는 아마존의 AI 칩 매각 후 리스 구조 → 다른 회사의 다른 재무 이벤트 |
| it:1232 앤트로픽, 10월6일까지 '음성 인터뷰어' 가동…대화… | it:1338 앤트로픽, 자체 음성 모델 개발하나…클로드 웹에 ‘보… |  | 0.6744 | claude, 앤트로픽, 테스팅카탈로그, multimodal | diff | 0.0 | 대체 출력: LLMError |
| it:1144 Claude Haiku 5.5 | it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… |  | 0.6743 | claudehaiku5.5, gpt6luna, eval, frontie… | same | 0.95 | a는 Claude Haiku 5.5, b는 클로드 하이쿠 5.5(음차)로 같은 모델의 출시를 다룸 |
| it:1120 AI 네이티브 SDLC - 개발 전 과정을 에이전트에… | vd:kcflfXb6dBM [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워… | 예 | 0.6733 | agent | diff | 0.9 | a는 Claude 공식 블로그의 'AI 네이티브 SDLC' 프로세스를 다루고, b는 AI 코드 워크플로우의 미래와 개발자 역량 변화에 대한 일… |
| it:1341 엔비디아, AI 추론 칩 d-매트릭스에 투자 계획…G… | it:1393 엔비디아, 미국 오픈소스 대표 리플렉션 AI 인수·투… |  | 0.6696 | 엔비디아 | diff | 0.95 | a는 엔비디아가 d-매트릭스에 투자하는 사건, b는 엔비디아가 리플렉션 AI를 인수·투자하는 사건 → 대상 회사가 다름 |
| it:1240 AI가 쏟아낸 '엉터리 제보'에... 구글, 오픈소스… | it:1310 "오픈소스 취약점 AI가 잡는다"...앤트로픽, 무료… |  | 0.6692 | ai-security | diff | 0.0 | 대체 출력: LLMError |
| it:1348 백악관, AI 기업 '보안 사고' 보고 의무화...앤… | it:1352 "6~12개월 내 터진다"…주요 AI 기업, 최악의 … |  | 0.6683 | 앤트로픽, ai-security | diff | 0.0 | 대체 출력: LLMError |
| it:1044 llm-mistral 0.16 | it:1048 Mistral Large 4 |  | 0.663 | mistrallarge4 | diff | 0.95 | a는 llm-mistral 0.16 릴리스, b는 Mistral Large 4 벤치마크 테스트 → 다른 대상 |
| it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… | it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객… |  | 0.6616 | 앤트로픽 | diff | 0.95 | a는 클로드 하이쿠 5.5 모델 출시, b는 클로드 포 스타트업 지원 프로그램 확대 → 다른 대상 |
| it:1144 Claude Haiku 5.5 | it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보… |  | 0.6611 | anthropic, openai | diff | 0.0 | 대체 출력: LLMError |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통… |  | 0.6597 | 앤트로픽, 오픈ai, ai-security | diff | 0.95 | a는 호주 의회 청문회, b는 뉴욕시의회 청문회 → 장소와 주제가 다른 별개의 사건 |
| it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.6593 | 앤트로픽 | diff | 0.95 | a는 앤트로픽의 스타트업 지원 프로그램 '클로드 포 스타트업' 확대 발표, b는 MS·메타의 클로드 사내 사용 축소 및 앤트로픽의 기업 시장 … |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼… |  | 0.6588 | 앤트로픽, 오픈ai | diff | 0.95 | a는 호주 의회 청문회에서의 에이전트 사고 신고 의무화 지지, b는 알트먼의 규제 접근법 인터뷰 및 앤트로픽의 과학 연구 방법론 → 다른 사건 |
| it:1221 '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은… | it:1350 앤트로픽 AI, 경찰 미제사건 제보 사이트에 '허위 … |  | 0.6559 | 앤트로픽, ai-security | diff | 0.0 | 대체 출력: LLMError |
| it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.6557 | agent, coding-agent | diff | 0.95 | a는 Lemma라는 오픈소스 작업 공간, b는 openrig라는 에이전트 오케스트레이션 CLI → 다른 제품 |
| it:1167 "독파모·모두의 AI 더 안전하게"...SKT, 업스… | it:1188 [게시판] SKT, 독파모 'A.X K2'로 순우리말… |  | 0.6556 | - | diff | 0.95 | a는 SKT와 업스테이지의 AI 보안 협의체 출범, b는 SKT의 A.X K2 활용 단신 → 다른 사건 |
| it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… | rp:openai/codex openai/codex | 예 | 0.6539 | codex | diff | 0.95 | a는 오픈소스 팀 작업 공간 Lemma, b는 OpenAI의 코딩 에이전트 CLI Codex → 다른 제품 |
| it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통… | it:1352 "6~12개월 내 터진다"…주요 AI 기업, 최악의 … |  | 0.6533 | 앤트로픽, 오픈ai, ai-security | diff | 0.95 | a는 뉴욕시의회가 개최한 AI 기업 임원 청문회, b는 AI 기업들의 내부 재난 시나리오 검토 → 다른 사건 |
| it:1126 Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호… | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… |  | 0.6528 | agent | diff | 0.95 | a는 Octop(셀프 호스팅 AI 비서), b는 Lemma(오픈소스 팀 작업 공간) → 다른 제품 |
| it:1185 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '… | it:1338 앤트로픽, 자체 음성 모델 개발하나…클로드 웹에 ‘보… |  | 0.6524 | claude, 앤트로픽 | diff | 0.95 | a는 구글 워크스페이스 연동 기능 출시, b는 클로드 웹의 음성 기능 포착 → 다른 기능/사건 |
| it:1102 Sharing AI progress in mathem… | it:1323 수학자가 Lean 정리 증명기에 대해 알아야 할 것:… |  | 0.6517 | lean, openai | diff | 0.95 | a는 OpenAI의 프런티어 모델로 생성한 수학 결과 공개, b는 Lean 증명기 신뢰성과 AI 자동형식화 현황을 다루는 Thomas Hale… |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회… |  | 0.6513 | 앤트로픽, 오픈ai, ai-security | diff | 0.95 | a는 호주 의회 청문회, b는 뉴욕시의회 청문회 → 장소와 주제가 다른 별개의 사건 |
| it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.6512 | 앤트로픽 | diff | 0.95 | a는 클로드 하이쿠 5.5 모델 출시, b는 MS·메타의 클로드(코드) 사용 축소 → 다른 대상 |
| it:1210 [게시판] 두산로보틱스, 989억 규모 피지컬 AI … | it:1214 [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용… |  | 0.6487 | 두산로보틱스, 딥엑스 | diff | 0.95 | a는 두산로보틱스의 피지컬 AI 국책과제 선정, b는 딥엑스-두산로보틱스의 원전 AI 용접 솔루션 협력 → 다른 사건 |
| it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… | rp:anthropics/claude-code anthropics/claude-code | 예 | 0.6471 | claudecode | diff | 0.95 | a는 오픈소스 팀 작업 공간 Lemma, b는 Anthropic의 코딩 에이전트 Claude Code → 다른 제품 |
| it:1205 '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개… | it:1393 엔비디아, 미국 오픈소스 대표 리플렉션 AI 인수·투… |  | 0.6469 | 리플렉션ai, 엔비디아, agent, open-weight | diff | 0.95 | a는 리플렉션 AI의 모델 '빔' 공개, b는 엔비디아의 리플렉션 AI 인수·투자 논의 → 다른 사건 |
| it:1193 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이… | it:1223 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날… |  | 0.6389 | codex, 오픈ai, coding-agent | diff | 0.9 | a는 코덱스 2일차 업데이트(오토리뷰 무료화), b는 코덱스 28일 개선 이벤트 발표 및 1일차 업데이트(속도 향상) → 같은 이벤트의 다른 … |
| it:1229 [AI리더의 서가] CEO의  AI | it:1250 [AI리더의 서가] AI 루프를 설계하라 |  | 0.6322 | 영풍문고 | diff | 0.95 | a는 도서 『CEO의 AI』 소개, b는 도서 『AI 루프를 설계하라』 소개 → 다른 책 |
| it:1045 EmbeddingGemma 2 | it:1111 EmbeddingGemma 2: an open, li… |  | 0.6319 | embeddinggemma2, open-weight, rag-search | diff | 0.0 | 대체 출력: LLMError |
| it:1172 오픈AI, 질문에 맞춰 화면 생성하는 'GPT-6' … | it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생… |  | 0.6319 | 오픈ai, 챗gpt | diff | 0.95 | a는 GPT-6 모델 공개 및 지능형 UI 도입, b는 챗GPT 내 시각적 광고 도입 → 다른 사안 |
| it:1122 OpenRig - Claude Code와 Codex를… | rp:openai/codex openai/codex | 예 | 0.6226 | codex | diff | 0.95 | a는 Claude Code와 Codex를 오케스트레이션하는 OpenRig, b는 OpenAI의 Codex CLI 자체 → 다른 대상 |
| it:1149 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·… | it:1353 구글, '제미나이 4 아르곤' 후속 '카본' 테스트 … |  | 0.6201 | 앤트로픽, 제미나이4아르곤, frontier-release | diff | 0.95 | a는 기업용 솔루션 '제미나이 에이전트' 출시, b는 모델 '제미나이 4 아르곤'의 후속 '카본' 테스트 → 다른 대상 |
| it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… | it:1307 앤트로픽, ‘클로드 대시보드·모션’ 공개…"기업 데이… |  | 0.6194 | claude, 앤트로픽 | diff | 0.95 | a는 MS·메타의 클로드 사용 축소, b는 앤트로픽의 Claude Dashboards·Motion 공개 → 다른 사건 |
| it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼… | it:1348 백악관, AI 기업 '보안 사고' 보고 의무화...앤… |  | 0.6183 | claude, 앤트로픽 | diff | 0.95 | a는 알트먼의 규제 관련 인터뷰, b는 앤트로픽 보안 사고에 따른 백악관 의무화 조치 → 다른 사건 |

## 5. 경계 근처 상위 20쌍 (묶이지 않은 쌍, 묶였어야 할 것 같은지 확인)

| a | b | 채널 넘음 | sim | 경로 | 판정 | 공유 |
|---|---|---|---|---|---|---|
| rp:anthropics/claude-code anthropics/claude-code | rp:openai/codex openai/codex |  | 0.9001 | none | - | - |
| rp:mvschwarz/openrig mvschwarz/openrig | rp:openai/codex openai/codex |  | 0.8744 | none | - | - |
| rp:anthropics/claude-code anthropics/claude-code | rp:mvschwarz/openrig mvschwarz/openrig |  | 0.8405 | none | - | - |
| rp:ollama/ollama ollama/ollama | rp:openai/codex openai/codex |  | 0.8133 | none | - | - |
| rp:NousResearch/hermes-agent NousResearch/hermes-agent | rp:mvschwarz/openrig mvschwarz/openrig |  | 0.8066 | none | - | - |
| it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디… | it:1165 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...120… |  | 0.7944 | decide | diff 0.8 | mai코드1.1플래시, 마이크로소프트, 서피스랩톱울트라, ai-secu… |
| rp:mvschwarz/openrig mvschwarz/openrig | rp:thedotmack/claude-mem thedotmack/claude-mem |  | 0.7942 | none | - | agent, coding-agent |
| rp:NousResearch/hermes-agent NousResearch/hermes-agent | rp:openai/codex openai/codex |  | 0.785 | none | - | - |
| rp:openai/codex openai/codex | rp:thedotmack/claude-mem thedotmack/claude-mem |  | 0.7798 | none | - | - |
| rp:mvschwarz/openrig mvschwarz/openrig | rp:ollama/ollama ollama/ollama |  | 0.7688 | none | - | - |
| it:1149 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드'… | it:1182 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정… |  | 0.7558 | decide | diff 0.95 | agent |
| rp:NousResearch/hermes-agent NousResearch/hermes-agent | rp:thedotmack/claude-mem thedotmack/claude-mem |  | 0.7518 | none | - | - |
| rp:anthropics/claude-code anthropics/claude-code | rp:thedotmack/claude-mem thedotmack/claude-mem |  | 0.7497 | none | - | - |
| rp:NousResearch/hermes-agent NousResearch/hermes-agent | rp:Panniantong/Agent-Reach Panniantong/Agent-Reach |  | 0.749 | none | - | - |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1348 백악관, AI 기업 '보안 사고' 보고 의무화...앤트로픽 침… |  | 0.7396 | decide | diff 0.95 | 앤트로픽, ai-security |
| rp:ollama/ollama ollama/ollama | rp:thedotmack/claude-mem thedotmack/claude-mem |  | 0.7386 | none | - | - |
| rp:NousResearch/hermes-agent NousResearch/hermes-agent | rp:ollama/ollama ollama/ollama |  | 0.7354 | none | - | - |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 … | it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.… |  | 0.7327 | decide | diff 0.95 | - |
| rp:anthropics/claude-code anthropics/claude-code | rp:ollama/ollama ollama/ollama |  | 0.7282 | none | - | - |
| rp:Panniantong/Agent-Reach Panniantong/Agent-Reach | rp:openai/codex openai/codex |  | 0.7276 | none | - | - |

### border 아래(0.55~0.65)에서 이름을 공유하는 쌍 상위 20

문턱값을 낮추면 decide로 갈 후보. 같은 대상인데 여기 있으면 border를 낮출 근거다.

| a | b | 채널 넘음 | sim | 공유 이름 |
|---|---|---|---|---|
| it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | it:1307 앤트로픽, ‘클로드 대시보드·모션’ 공개…"기업 데이터 분석·… |  | 0.6415 | 앤트로픽 |
| it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | it:1338 앤트로픽, 자체 음성 모델 개발하나…클로드 웹에 ‘보이스’ 메… |  | 0.6412 | 앤트로픽 |
| it:1171 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 12… | it:1341 엔비디아, AI 추론 칩 d-매트릭스에 투자 계획…GPU 중심… |  | 0.6387 | 엔비디아 |
| it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… | it:1348 백악관, AI 기업 '보안 사고' 보고 의무화...앤트로픽 침… |  | 0.6339 | 앤트로픽 |
| it:1043 llm-openai-decisions 0.1a0 | it:1377 Microsoft-Decision-1 - 선택지별 확률을 반환… |  | 0.6295 | openai |
| it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 … | it:1348 백악관, AI 기업 '보안 사고' 보고 의무화...앤트로픽 침… |  | 0.6273 | 앤트로픽 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1304 오픈AI, 연구원 해고 논란 해명..."안전 제기 보복 아닌 … |  | 0.6245 | 오픈ai |
| it:1239 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부… | it:1341 엔비디아, AI 추론 칩 d-매트릭스에 투자 계획…GPU 중심… |  | 0.6225 | 엔비디아 |
| it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규… |  | 0.6222 | 오픈ai |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연… |  | 0.6168 | 오픈ai |
| it:1247 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안… | it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 … |  | 0.6167 | 오픈ai |
| it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | it:1242 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 |  | 0.6165 | 구글, 앤트로픽 |
| it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… | it:1247 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안… |  | 0.6129 | 오픈ai |
| it:1185 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' … | it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 |  | 0.6106 | 앤트로픽 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1352 "6~12개월 내 터진다"…주요 AI 기업, 최악의 AI 재난… |  | 0.6098 | 앤트로픽, 오픈ai |
| it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디… | it:1342 MS, 에이전트 의사결정 특화 모델 ‘디시전-1’ 공개…오픈A… |  | 0.6089 | 마이크로소프트 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1350 앤트로픽 AI, 경찰 미제사건 제보 사이트에 '허위 제보' 소동 |  | 0.6065 | 앤트로픽 |
| it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트… | it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 … |  | 0.6061 | 앤트로픽, 오픈ai |
| it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규… |  | 0.6051 | 오픈ai |
| it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트… | it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… |  | 0.5986 | 앤트로픽, 오픈ai |

## 6. 의심 병합 (숫자·버전·크기만 다른 이름이 한 묶음)

- c1840 Introducing Mistral Large 4: Le chonk: Mistral Large 3 ↔ Mistral Large 4(확인 완료: 비교 대상으로 언급된 이전 버전)
- c1850 GPT-6 and Intelligent UI for everyone: GPT-5.6 ↔ GPT-6(확인 완료: 비교 대상으로 언급된 이전 버전), GPT-5.6 ↔ GPT-6 루나(확인 완료: 비교 대상으로 언급된 이전 버전), GPT-5.6 ↔ GPT-6 솔(확인 완료: 비교 대상으로 언급된 이전 버전)
- c1885 Claude Haiku 5.5: Claude Haiku 4.5 ↔ Claude Haiku 5.5(확인 완료: 비교 대상으로 언급된 이전 버전)

## 7. 과거 대조 후보

| 묶음 | 지난 토픽 | 주 | 유사도 |
|---|---|---|---|
| c1834 Anti-Patterns in Software Blogging | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.2314 |
| c1834 Anti-Patterns in Software Blogging | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.2313 |
| c1834 Anti-Patterns in Software Blogging | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.2108 |
| c1835 OpenAI “rogue” agent activities found o… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3979 |
| c1835 OpenAI “rogue” agent activities found o… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3774 |
| c1835 OpenAI “rogue” agent activities found o… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.362 |
| c1836 Quoting Victoria Kim | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3703 |
| c1836 Quoting Victoria Kim | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3371 |
| c1836 Quoting Victoria Kim | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.325 |
| c1837 llm-openai-decisions 0.1a0 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.5116 |
| c1837 llm-openai-decisions 0.1a0 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4418 |
| c1837 llm-openai-decisions 0.1a0 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4348 |
| c1838 llm-mistral 0.16 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4565 |
| c1838 llm-mistral 0.16 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4141 |
| c1838 llm-mistral 0.16 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3845 |
| c1839 EmbeddingGemma 2 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3719 |
| c1839 EmbeddingGemma 2 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.33 |
| c1839 EmbeddingGemma 2 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3089 |
| c1840 Introducing Mistral Large 4: Le chonk | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4502 |
| c1840 Introducing Mistral Large 4: Le chonk | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4366 |
| c1840 Introducing Mistral Large 4: Le chonk | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4227 |
| c1841 Using Parseable with Datasette for Open… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3665 |
| c1841 Using Parseable with Datasette for Open… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3665 |
| c1841 Using Parseable with Datasette for Open… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3497 |
| c1842 datasette-atom 0.11a0 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3683 |
| c1842 datasette-atom 0.11a0 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3231 |
| c1842 datasette-atom 0.11a0 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3204 |
| c1843 Scrimshaw Jukebox | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4409 |
| c1843 Scrimshaw Jukebox | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3787 |
| c1843 Scrimshaw Jukebox | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.2976 |
| c1844 How Oracle turns days of work into minu… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4045 |
| c1844 How Oracle turns days of work into minu… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3957 |
| c1844 How Oracle turns days of work into minu… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3397 |
| c1845 Pollo AI turns creative ideas into camp… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3945 |
| c1845 Pollo AI turns creative ideas into camp… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3818 |
| c1845 Pollo AI turns creative ideas into camp… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3356 |
| c1846 LegalOn halves Codex costs while mainta… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4074 |
| c1846 LegalOn halves Codex costs while mainta… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3956 |
| c1846 LegalOn halves Codex costs while mainta… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3523 |
| c1847 Disrupting AI-enabled “false front” ope… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3038 |
| c1847 Disrupting AI-enabled “false front” ope… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.2678 |
| c1847 Disrupting AI-enabled “false front” ope… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.2528 |
| c1848 Helping teens learn, plan, and shape th… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3352 |
| c1848 Helping teens learn, plan, and shape th… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3329 |
| c1848 Helping teens learn, plan, and shape th… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3255 |
| c1849 Radisson Hotel Group brings hotel disco… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3981 |
| c1849 Radisson Hotel Group brings hotel disco… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.396 |
| c1849 Radisson Hotel Group brings hotel disco… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3876 |
| c1850 GPT-6 and Intelligent UI for everyone | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.5212 |
| c1850 GPT-6 and Intelligent UI for everyone | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4623 |
| c1850 GPT-6 and Intelligent UI for everyone | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4121 |
| c1851 How Jump Trading is scaling quant resea… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4393 |
| c1851 How Jump Trading is scaling quant resea… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4245 |
| c1851 How Jump Trading is scaling quant resea… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3469 |
| c1852 Sharing AI progress in mathematics | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3718 |
| c1852 Sharing AI progress in mathematics | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3576 |
| c1852 Sharing AI progress in mathematics | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3512 |
| c1853 Advancing computer use with Ironclad | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4381 |
| c1853 Advancing computer use with Ironclad | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4099 |
| c1853 Advancing computer use with Ironclad | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3853 |
| c1854 Atlassian and OpenAI expand partnership… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4716 |
| c1854 Atlassian and OpenAI expand partnership… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3884 |
| c1854 Atlassian and OpenAI expand partnership… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3526 |
| c1855 Our approach to EU text provenance rules | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3317 |
| c1855 Our approach to EU text provenance rules | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.2875 |
| c1855 Our approach to EU text provenance rules | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.2847 |
| c1856 Building advertising for the way people… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4208 |
| c1856 Building advertising for the way people… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3616 |
| c1856 Building advertising for the way people… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3595 |
| c1857 Introducing the Anthropic Cyber Mission | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3031 |
| c1857 Introducing the Anthropic Cyber Mission | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.2598 |
| c1857 Introducing the Anthropic Cyber Mission | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.2568 |
| c1858 2026 Usage Policy update | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3695 |
| c1858 2026 Usage Policy update | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3346 |
| c1858 2026 Usage Policy update | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.316 |
| c1859 Expanding the Cyber Verification Program | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3427 |
| c1859 Expanding the Cyber Verification Program | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3144 |
| c1859 Expanding the Cyber Verification Program | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.2816 |
| c1860 EmbeddingGemma 2: an open, lightweight … | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.462 |
| c1860 EmbeddingGemma 2: an open, lightweight … | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4452 |
| c1860 EmbeddingGemma 2: an open, lightweight … | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4103 |
| c1861 OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 AI 에이… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.5102 |
| c1861 OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 AI 에이… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4433 |
| c1861 OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 AI 에이… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.401 |
| c1862 MCPB로 로컬 MCP 서버를 Claude Desktop 원클릭 확장으… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3486 |
| c1862 MCPB로 로컬 MCP 서버를 Claude Desktop 원클릭 확장으… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3078 |
| c1862 MCPB로 로컬 MCP 서버를 Claude Desktop 원클릭 확장으… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3067 |
| c1863 「Quo Vadis, Mathematics?」—“수학이여, 어디로 가는… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3826 |
| c1863 「Quo Vadis, Mathematics?」—“수학이여, 어디로 가는… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3789 |
| c1863 「Quo Vadis, Mathematics?」—“수학이여, 어디로 가는… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3688 |
| c1864 AI가 코드를 쓸수록 도메인 주도 설계가 더 중요해지는 이유 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3137 |
| c1864 AI가 코드를 쓸수록 도메인 주도 설계가 더 중요해지는 이유 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3016 |
| c1864 AI가 코드를 쓸수록 도메인 주도 설계가 더 중요해지는 이유 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.2654 |
| c1865 AI 시대의 커리어 조언 - 문제를 푸는 능력보다 찾고 선택하는 능력 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.393 |
| c1865 AI 시대의 커리어 조언 - 문제를 푸는 능력보다 찾고 선택하는 능력 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3697 |
| c1865 AI 시대의 커리어 조언 - 문제를 푸는 능력보다 찾고 선택하는 능력 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.365 |
| c1866 AI로 의도, 품질, 예술성을 확장하는 법 [영상] | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4014 |
| c1866 AI로 의도, 품질, 예술성을 확장하는 법 [영상] | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.381 |
| c1866 AI로 의도, 품질, 예술성을 확장하는 법 [영상] | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3279 |
| c1867 AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재설계하기 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3775 |
| c1867 AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재설계하기 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3454 |
| c1867 AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재설계하기 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3283 |
| c1868 Claude Code 모드(mod) 시작하기 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3982 |
| c1868 Claude Code 모드(mod) 시작하기 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3946 |
| c1868 Claude Code 모드(mod) 시작하기 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.315 |
| c1869 mvschwarz/openrig | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4802 |
| c1869 mvschwarz/openrig | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4626 |
| c1869 mvschwarz/openrig | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4598 |
| c1870 에이전트가 쓴 테스트는 무엇을 증명하나 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4142 |
| c1870 에이전트가 쓴 테스트는 무엇을 증명하나 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.413 |
| c1870 에이전트가 쓴 테스트는 무엇을 증명하나 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3694 |
| c1871 AI 시대, 매니저의 길 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3637 |
| c1871 AI 시대, 매니저의 길 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3605 |
| c1871 AI 시대, 매니저의 길 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3244 |
| c1872 Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호스팅 AI 비서 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4969 |
| c1872 Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호스팅 AI 비서 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4471 |
| c1872 Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호스팅 AI 비서 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4439 |
| c1873 jev가 여는 비즈니스 AI: 에이전트에서 컴포넌트로 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.5186 |
| c1873 jev가 여는 비즈니스 AI: 에이전트에서 컴포넌트로 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4965 |
| c1873 jev가 여는 비즈니스 AI: 에이전트에서 컴포넌트로 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4217 |
| c1874 자율주행 데이터에서 시간은 어떻게 맞춰지는가 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3434 |
| c1874 자율주행 데이터에서 시간은 어떻게 맞춰지는가 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3385 |
| c1874 자율주행 데이터에서 시간은 어떻게 맞춰지는가 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.311 |
| c1875 우리가 알던 오픈소스는 죽었다 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4006 |
| c1875 우리가 알던 오픈소스는 죽었다 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3618 |
| c1875 우리가 알던 오픈소스는 죽었다 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3486 |
| c1876 여러 팀의 시스템을 이해하기 위한 AI 집단 지성 구축하기 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4438 |
| c1876 여러 팀의 시스템을 이해하기 위한 AI 집단 지성 구축하기 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3862 |
| c1876 여러 팀의 시스템을 이해하기 위한 AI 집단 지성 구축하기 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3575 |
| c1877 소프트웨어 팩토리 패턴 시도하기 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4299 |
| c1877 소프트웨어 팩토리 패턴 시도하기 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3875 |
| c1877 소프트웨어 팩토리 패턴 시도하기 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3683 |
| c1878 나는 인류를 멸종시키고 있는 AGI다 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4225 |
| c1878 나는 인류를 멸종시키고 있는 AGI다 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4191 |
| c1878 나는 인류를 멸종시키고 있는 AGI다 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.375 |
| c1879 제프리 카첸버그 - 세상이 바뀌고 있다: 창의성을 위한 AI | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3477 |
| c1879 제프리 카첸버그 - 세상이 바뀌고 있다: 창의성을 위한 AI | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3405 |
| c1879 제프리 카첸버그 - 세상이 바뀌고 있다: 창의성을 위한 AI | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3335 |
| c1880 openTPU - AI가 설계하고 실제 FPGA에서 모델을 실행하는 오… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4346 |
| c1880 openTPU - AI가 설계하고 실제 FPGA에서 모델을 실행하는 오… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3932 |
| c1880 openTPU - AI가 설계하고 실제 FPGA에서 모델을 실행하는 오… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3922 |
| c1881 Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소스 작업 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4673 |
| c1881 Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소스 작업 … | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4556 |
| c1881 Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소스 작업 … | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.452 |
| c1882 ttok 0.4 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3858 |
| c1882 ttok 0.4 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3797 |
| c1882 ttok 0.4 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3624 |
| c1883 Quoting Carson Gross | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.2612 |
| c1883 Quoting Carson Gross | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.2307 |
| c1883 Quoting Carson Gross | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.2186 |
| c1884 Quoting Ben Affleck | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.306 |
| c1884 Quoting Ben Affleck | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.2763 |
| c1884 Quoting Ben Affleck | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.2659 |
| c1885 Claude Haiku 5.5 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.6496 |
| c1885 Claude Haiku 5.5 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.5646 |
| c1885 Claude Haiku 5.5 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4725 |
| c1886 Quoting Felix Rieseberg | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3729 |
| c1886 Quoting Felix Rieseberg | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3472 |
| c1886 Quoting Felix Rieseberg | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3467 |
| c1887 Qwen3.8 27B addition in words | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4024 |
| c1887 Qwen3.8 27B addition in words | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3786 |
| c1887 Qwen3.8 27B addition in words | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3746 |
| c1888 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 요동 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.5361 |
| c1888 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 요동 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4959 |
| c1888 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 요동 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4801 |
| c1889 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.5603 |
| c1889 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4794 |
| c1889 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4195 |
| c1890 여수, 23~24일 독서문화축제…야외 독서·섬 체험 운영 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.394 |
| c1890 여수, 23~24일 독서문화축제…야외 독서·섬 체험 운영 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3101 |
| c1890 여수, 23~24일 독서문화축제…야외 독서·섬 체험 운영 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.2902 |
| c1891 한국 금융권 공격한 중국 26세 해커…'어설픈 신원 노출'로 덜미 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4371 |
| c1891 한국 금융권 공격한 중국 26세 해커…'어설픈 신원 노출'로 덜미 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4216 |
| c1891 한국 금융권 공격한 중국 26세 해커…'어설픈 신원 노출'로 덜미 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4108 |
| c1892 [AI리더의 서가] 이너 프롬프트 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4379 |
| c1892 [AI리더의 서가] 이너 프롬프트 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4025 |
| c1892 [AI리더의 서가] 이너 프롬프트 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.388 |
| c1893 구글, 텍스트 입력으로 게임 만드는 플랫폼 공개…유니티와 협력 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4511 |
| c1893 구글, 텍스트 입력으로 게임 만드는 플랫폼 공개…유니티와 협력 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.405 |
| c1893 구글, 텍스트 입력으로 게임 만드는 플랫폼 공개…유니티와 협력 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3736 |
| c1894 머스크 “테라팹 직접 운영한다”…TSMC 위탁운영설 일축 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4001 |
| c1894 머스크 “테라팹 직접 운영한다”…TSMC 위탁운영설 일축 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3849 |
| c1894 머스크 “테라팹 직접 운영한다”…TSMC 위탁운영설 일축 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3539 |
| c1895 카카오, 국제 AI 학회서 MoE 학습 최적화·모델 경량화 성과 공개 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.5237 |
| c1895 카카오, 국제 AI 학회서 MoE 학습 최적화·모델 경량화 성과 공개 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4731 |
| c1895 카카오, 국제 AI 학회서 MoE 학습 최적화·모델 경량화 성과 공개 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4707 |
| c1896 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정 모델 ‘d1-3B… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.5036 |
| c1896 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정 모델 ‘d1-3B… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4773 |
| c1896 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정 모델 ‘d1-3B… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4571 |
| c1897 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.5454 |
| c1897 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.5002 |
| c1897 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4688 |
| c1898 누리호 올라탄 토종 AI 반도체, 우주 궤도서 성능 실증 나선다 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.5023 |
| c1898 누리호 올라탄 토종 AI 반도체, 우주 궤도서 성능 실증 나선다 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4335 |
| c1898 누리호 올라탄 토종 AI 반도체, 우주 궤도서 성능 실증 나선다 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4085 |
| c1899 '헤르메스 에이전트' 누스 리서치, 대규모 투자 유치로 기업용 시장 진출 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.534 |
| c1899 '헤르메스 에이전트' 누스 리서치, 대규모 투자 유치로 기업용 시장 진출 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.5166 |
| c1899 '헤르메스 에이전트' 누스 리서치, 대규모 투자 유치로 기업용 시장 진출 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4979 |
| c1900 오픈AI "10대 챗GPT 평균 15분 사용" 주장에 안전성 논란 불붙어 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4824 |
| c1900 오픈AI "10대 챗GPT 평균 15분 사용" 주장에 안전성 논란 불붙어 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4706 |
| c1900 오픈AI "10대 챗GPT 평균 15분 사용" 주장에 안전성 논란 불붙어 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4601 |
| c1901 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.5226 |
| c1901 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4798 |
| c1901 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.473 |
| c1902 "독파모·모두의 AI 더 안전하게"...SKT, 업스테이지와 AI 보안… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4266 |
| c1902 "독파모·모두의 AI 더 안전하게"...SKT, 업스테이지와 AI 보안… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4248 |
| c1902 "독파모·모두의 AI 더 안전하게"...SKT, 업스테이지와 AI 보안… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3898 |
| c1903 저커버그 부부의 바이오허브, 미 정부·구글과 2.4조 AI 생물학 데이… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4281 |
| c1903 저커버그 부부의 바이오허브, 미 정부·구글과 2.4조 AI 생물학 데이… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4193 |
| c1903 저커버그 부부의 바이오허브, 미 정부·구글과 2.4조 AI 생물학 데이… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3715 |
| c1904 메타 '뮤즈', 스마트폰 이어 아이패드용 앱 출시…업무용 도구 연동 강화 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4567 |
| c1904 메타 '뮤즈', 스마트폰 이어 아이패드용 앱 출시…업무용 도구 연동 강화 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4166 |
| c1904 메타 '뮤즈', 스마트폰 이어 아이패드용 앱 출시…업무용 도구 연동 강화 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4163 |
| c1905 구글, AI 생성물 구분하는 '신스ID 감지기' 일반에 전면 공개 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4605 |
| c1905 구글, AI 생성물 구분하는 '신스ID 감지기' 일반에 전면 공개 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4075 |
| c1905 구글, AI 생성물 구분하는 '신스ID 감지기' 일반에 전면 공개 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3848 |
| c1906 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 121만개 확… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.455 |
| c1906 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 121만개 확… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4261 |
| c1906 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 121만개 확… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4206 |
| c1907 삼성전자, 3분기 영업익 107조...애플·엔비디아도 못 넘은 '100… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4227 |
| c1907 삼성전자, 3분기 영업익 107조...애플·엔비디아도 못 넘은 '100… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3826 |
| c1907 삼성전자, 3분기 영업익 107조...애플·엔비디아도 못 넘은 '100… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3526 |
| c1908 [AI리더의 서가] Agentic AI 구축 개발의 모든 것 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4715 |
| c1908 [AI리더의 서가] Agentic AI 구축 개발의 모든 것 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4682 |
| c1908 [AI리더의 서가] Agentic AI 구축 개발의 모든 것 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4296 |
| c1909 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 더 쓸 수… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.6711 |
| c1909 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 더 쓸 수… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.6357 |
| c1909 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 더 쓸 수… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.5659 |
| c1910 구글, ‘나노 바나나 2.1’ 공개...성능 높이고 비용은 반값으로 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.5345 |
| c1910 구글, ‘나노 바나나 2.1’ 공개...성능 높이고 비용은 반값으로 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4814 |
| c1910 구글, ‘나노 바나나 2.1’ 공개...성능 높이고 비용은 반값으로 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4619 |
| c1911 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정황 포착 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.5113 |
| c1911 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정황 포착 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4597 |
| c1911 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정황 포착 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4051 |
| c1912 스튜어트 러셀의 경고 "LLM 정렬 불가능…모방 학습과 RLHF 한계" | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.5403 |
| c1912 스튜어트 러셀의 경고 "LLM 정렬 불가능…모방 학습과 RLHF 한계" | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3881 |
| c1912 스튜어트 러셀의 경고 "LLM 정렬 불가능…모방 학습과 RLHF 한계" | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3758 |
| c1913 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' 직접 호출 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4753 |
| c1913 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' 직접 호출 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.444 |
| c1913 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' 직접 호출 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4332 |
| c1914 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.514 |
| c1914 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4606 |
| c1914 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4141 |
| c1915 AMD, 연내 국내 'AI 연구센터' 설립...정부와 메가프로젝트 협력… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3992 |
| c1915 AMD, 연내 국내 'AI 연구센터' 설립...정부와 메가프로젝트 협력… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3885 |
| c1915 AMD, 연내 국내 'AI 연구센터' 설립...정부와 메가프로젝트 협력… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3505 |
| c1916 [게시판] SKT, 독파모 'A.X K2'로 순우리말 선정·글꼴 제작 … | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4442 |
| c1916 [게시판] SKT, 독파모 'A.X K2'로 순우리말 선정·글꼴 제작 … | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4348 |
| c1916 [게시판] SKT, 독파모 'A.X K2'로 순우리말 선정·글꼴 제작 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4317 |
| c1917 하크, '스마트폰 대체' AI 에이전트 공개...2027년 전용 기기 … | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.5215 |
| c1917 하크, '스마트폰 대체' AI 에이전트 공개...2027년 전용 기기 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4741 |
| c1917 하크, '스마트폰 대체' AI 에이전트 공개...2027년 전용 기기 … | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4492 |
| c1918 구글, AI 데이터센터 전력 확보 위해 3.6GW 규모 원전 계약 체결 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4916 |
| c1918 구글, AI 데이터센터 전력 확보 위해 3.6GW 규모 원전 계약 체결 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4186 |
| c1918 구글, AI 데이터센터 전력 확보 위해 3.6GW 규모 원전 계약 체결 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4033 |
| c1919 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의무화 찬성" | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4506 |
| c1919 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의무화 찬성" | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4062 |
| c1919 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의무화 찬성" | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4043 |
| c1920 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오토리뷰’ … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.535 |
| c1920 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오토리뷰’ … | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.49 |
| c1920 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오토리뷰’ … | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4822 |
| c1921 전남광주, 여수서 9~11일 ‘세계 김밥&소금 페스티벌’ | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3594 |
| c1921 전남광주, 여수서 9~11일 ‘세계 김밥&소금 페스티벌’ | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3542 |
| c1921 전남광주, 여수서 9~11일 ‘세계 김밥&소금 페스티벌’ | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3312 |
| c1922 딥시크, 투자 수요 폭발…IPO 전 자금 조달 규모 2배 확대 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4285 |
| c1922 딥시크, 투자 수요 폭발…IPO 전 자금 조달 규모 2배 확대 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3888 |
| c1922 딥시크, 투자 수요 폭발…IPO 전 자금 조달 규모 2배 확대 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3524 |
| c1923 [AI리더의 서가] SQL부터 AI까지 데이터 분석 with 클로드 코드 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3688 |
| c1923 [AI리더의 서가] SQL부터 AI까지 데이터 분석 with 클로드 코드 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3621 |
| c1923 [AI리더의 서가] SQL부터 AI까지 데이터 분석 with 클로드 코드 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3494 |
| c1924 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트로픽과 근… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4516 |
| c1924 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트로픽과 근… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4264 |
| c1924 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트로픽과 근… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3737 |
| c1925 '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개…반응은 엇갈려 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4851 |
| c1925 '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개…반응은 엇갈려 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4756 |
| c1925 '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개…반응은 엇갈려 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4549 |
| c1926 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 축소 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.5259 |
| c1926 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 축소 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4609 |
| c1926 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 축소 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4529 |
| c1927 노르웨이, 공공장소 ‘AI 안경’ 일시 금지 추진…세계 첫 규제 움직임 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3266 |
| c1927 노르웨이, 공공장소 ‘AI 안경’ 일시 금지 추진…세계 첫 규제 움직임 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3194 |
| c1927 노르웨이, 공공장소 ‘AI 안경’ 일시 금지 추진…세계 첫 규제 움직임 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3088 |
| c1928 [게시판] 두산로보틱스, 989억 규모 피지컬 AI 국책과제 2건 선정… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4646 |
| c1928 [게시판] 두산로보틱스, 989억 규모 피지컬 AI 국책과제 2건 선정… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4154 |
| c1928 [게시판] 두산로보틱스, 989억 규모 피지컬 AI 국책과제 2건 선정… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3977 |
| c1929 코히어, 에이전트 비용·보안 통제 플랫폼 '노스 2' 출시...알레프 … | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.5005 |
| c1929 코히어, 에이전트 비용·보안 통제 플랫폼 '노스 2' 출시...알레프 … | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4884 |
| c1929 코히어, 에이전트 비용·보안 통제 플랫폼 '노스 2' 출시...알레프 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4691 |
| c1930 엔비디아-그로크 27조 계약 파장…소외된 엔지니어들 "거래 불공정" 소송 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3971 |
| c1930 엔비디아-그로크 27조 계약 파장…소외된 엔지니어들 "거래 불공정" 소송 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3799 |
| c1930 엔비디아-그로크 27조 계약 파장…소외된 엔지니어들 "거래 불공정" 소송 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3579 |
| c1931 19세 청년의 반란...고스트, 개인용 AI PC '코어'로 147억 … | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4854 |
| c1931 19세 청년의 반란...고스트, 개인용 AI PC '코어'로 147억 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.483 |
| c1931 19세 청년의 반란...고스트, 개인용 AI PC '코어'로 147억 … | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4534 |
| c1932 [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용접 솔루션’ 공동개… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4809 |
| c1932 [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용접 솔루션’ 공동개… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4621 |
| c1932 [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용접 솔루션’ 공동개… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3878 |
| c1933 화웨이, 퀄컴에 '로직폴딩' 칩 관련 특허 라이선스 제공 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4262 |
| c1933 화웨이, 퀄컴에 '로직폴딩' 칩 관련 특허 라이선스 제공 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4093 |
| c1933 화웨이, 퀄컴에 '로직폴딩' 칩 관련 특허 라이선스 제공 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3884 |
| c1934 카카오모빌리티, 고려대와 AX 협력…모빌리티 핵심 기술 국방 분야 접목 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3859 |
| c1934 카카오모빌리티, 고려대와 AX 협력…모빌리티 핵심 기술 국방 분야 접목 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3595 |
| c1934 카카오모빌리티, 고려대와 AX 협력…모빌리티 핵심 기술 국방 분야 접목 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3542 |
| c1935 “180B 모델, 개인용 노트북으로 구동”...비드래프트, 고성능 모델… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.5696 |
| c1935 “180B 모델, 개인용 노트북으로 구동”...비드래프트, 고성능 모델… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4946 |
| c1935 “180B 모델, 개인용 노트북으로 구동”...비드래프트, 고성능 모델… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4816 |
| c1936 이탈리아 멜로니 총리, AI 딥페이크 막으려 '목소리 상표권' 신청 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3741 |
| c1936 이탈리아 멜로니 총리, AI 딥페이크 막으려 '목소리 상표권' 신청 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3472 |
| c1936 이탈리아 멜로니 총리, AI 딥페이크 막으려 '목소리 상표권' 신청 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3397 |
| c1937 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4235 |
| c1937 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4055 |
| c1937 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3948 |
| c1938 포지큐브, 롯데벤처스와 멀티 AI 에이전트 기반 AX 추진 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.5032 |
| c1938 포지큐브, 롯데벤처스와 멀티 AI 에이전트 기반 AX 추진 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4324 |
| c1938 포지큐브, 롯데벤처스와 멀티 AI 에이전트 기반 AX 추진 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3981 |
| c1939 '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 아니다" | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4352 |
| c1939 '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 아니다" | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4123 |
| c1939 '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 아니다" | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3996 |
| c1940 헨켈, SEDEX 2026서 AI·HBM 시대 위한 첨단 패키징 소재 … | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4756 |
| c1940 헨켈, SEDEX 2026서 AI·HBM 시대 위한 첨단 패키징 소재 … | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4117 |
| c1940 헨켈, SEDEX 2026서 AI·HBM 시대 위한 첨단 패키징 소재 … | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3537 |
| c1941 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날부터 처리 속도 5… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.5766 |
| c1941 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날부터 처리 속도 5… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.5162 |
| c1941 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날부터 처리 속도 5… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.5003 |
| c1942 LG전자, 북미서 5GW 규모 AIDC 냉각솔루션 장기계약 체결 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4184 |
| c1942 LG전자, 북미서 5GW 규모 AIDC 냉각솔루션 장기계약 체결 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4172 |
| c1942 LG전자, 북미서 5GW 규모 AIDC 냉각솔루션 장기계약 체결 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3996 |
| c1943 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만 우선 적용 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.439 |
| c1943 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만 우선 적용 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4355 |
| c1943 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만 우선 적용 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4318 |
| c1944 [AI리더의 서가] CEO의  AI | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4289 |
| c1944 [AI리더의 서가] CEO의  AI | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3728 |
| c1944 [AI리더의 서가] CEO의  AI | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3541 |
| c1945 구글, 'AI 프로' 국내 한정 40% 할인...연간 구독권 프로모션 … | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.5811 |
| c1945 구글, 'AI 프로' 국내 한정 40% 할인...연간 구독권 프로모션 … | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4926 |
| c1945 구글, 'AI 프로' 국내 한정 40% 할인...연간 구독권 프로모션 … | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4255 |
| c1946 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4439 |
| c1946 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4283 |
| c1946 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3755 |
| c1947 앤트로픽, 10월6일까지 '음성 인터뷰어' 가동…대화록 공개·음성 학습… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4683 |
| c1947 앤트로픽, 10월6일까지 '음성 인터뷰어' 가동…대화록 공개·음성 학습… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4376 |
| c1947 앤트로픽, 10월6일까지 '음성 인터뷰어' 가동…대화록 공개·음성 학습… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3878 |
| c1948 뉴럴링크, 5만시간 뇌 데이터 사전학습…BCI도 '파운데이션 모델' 시… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4309 |
| c1948 뉴럴링크, 5만시간 뇌 데이터 사전학습…BCI도 '파운데이션 모델' 시… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4293 |
| c1948 뉴럴링크, 5만시간 뇌 데이터 사전학습…BCI도 '파운데이션 모델' 시… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4032 |
| c1949 KAIST, 데이터 변화해도 검색 정확도 유지하는 ‘CONDA’ 기술 … | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4995 |
| c1949 KAIST, 데이터 변화해도 검색 정확도 유지하는 ‘CONDA’ 기술 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4127 |
| c1949 KAIST, 데이터 변화해도 검색 정확도 유지하는 ‘CONDA’ 기술 … | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.384 |
| c1950 a16z "미국 가구 2.2%만 AI 유료 구독…기술이 경기 순환 핵심… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4377 |
| c1950 a16z "미국 가구 2.2%만 AI 유료 구독…기술이 경기 순환 핵심… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4081 |
| c1950 a16z "미국 가구 2.2%만 AI 유료 구독…기술이 경기 순환 핵심… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4031 |
| c1951 GPT-6 아스트라, 217년 된 나폴레옹 암호 6시간 만에 해독 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.5134 |
| c1951 GPT-6 아스트라, 217년 된 나폴레옹 암호 6시간 만에 해독 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4211 |
| c1951 GPT-6 아스트라, 217년 된 나폴레옹 암호 6시간 만에 해독 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4045 |
| c1952 MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 … | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4993 |
| c1952 MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 … | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4953 |
| c1952 MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4627 |
| c1953 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부담 낮춘다 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4171 |
| c1953 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부담 낮춘다 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4136 |
| c1953 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부담 낮춘다 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4059 |
| c1954 AI가 쏟아낸 '엉터리 제보'에... 구글, 오픈소스 버그 바운티 일시… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4828 |
| c1954 AI가 쏟아낸 '엉터리 제보'에... 구글, 오픈소스 버그 바운티 일시… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4307 |
| c1954 AI가 쏟아낸 '엉터리 제보'에... 구글, 오픈소스 버그 바운티 일시… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4131 |
| c1955 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가상 착용' 도입 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4011 |
| c1955 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가상 착용' 도입 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4007 |
| c1955 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가상 착용' 도입 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3873 |
| c1956 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4113 |
| c1956 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3854 |
| c1956 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3849 |
| c1957 "전직 미국 관료 사칭"…중국 해커, AI 정책 전문가 계정 노렸다 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4385 |
| c1957 "전직 미국 관료 사칭"…중국 해커, AI 정책 전문가 계정 노렸다 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3984 |
| c1957 "전직 미국 관료 사칭"…중국 해커, AI 정책 전문가 계정 노렸다 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3893 |
| c1958 "지기 싫어서 남의 코드 복사"…아스트라, 스타크래프트 벤치마크서 꼼수 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.5838 |
| c1958 "지기 싫어서 남의 코드 복사"…아스트라, 스타크래프트 벤치마크서 꼼수 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.5143 |
| c1958 "지기 싫어서 남의 코드 복사"…아스트라, 스타크래프트 벤치마크서 꼼수 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4347 |
| c1959 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규제 경고 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4166 |
| c1959 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규제 경고 … | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3569 |
| c1959 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규제 경고 … | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3527 |
| c1960 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안전성에 이… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3975 |
| c1960 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안전성에 이… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3752 |
| c1960 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안전성에 이… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3515 |
| c1961 'AI 피해자 영상'에 속아 내려진 중형..."형량 잘못됐다" 선고 파기 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3851 |
| c1961 'AI 피해자 영상'에 속아 내려진 중형..."형량 잘못됐다" 선고 파기 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3536 |
| c1961 'AI 피해자 영상'에 속아 내려진 중형..."형량 잘못됐다" 선고 파기 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3416 |
| c1962 [AI리더의 서가] AI 루프를 설계하라 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.518 |
| c1962 [AI리더의 서가] AI 루프를 설계하라 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4294 |
| c1962 [AI리더의 서가] AI 루프를 설계하라 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3563 |
| c1963 머스크, '스페이스XSI'로 리브랜딩 시사…트럼프 'SI' 발언 동조 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3909 |
| c1963 머스크, '스페이스XSI'로 리브랜딩 시사…트럼프 'SI' 발언 동조 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3801 |
| c1963 머스크, '스페이스XSI'로 리브랜딩 시사…트럼프 'SI' 발언 동조 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3707 |
| c1964 트럼프, ‘슈퍼 인텔리전스 부대’ 출범…국가정보국장, 백악관 AI 차르… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4217 |
| c1964 트럼프, ‘슈퍼 인텔리전스 부대’ 출범…국가정보국장, 백악관 AI 차르… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4051 |
| c1964 트럼프, ‘슈퍼 인텔리전스 부대’ 출범…국가정보국장, 백악관 AI 차르… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3934 |
| c1965 Quoting Matthew Green | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.325 |
| c1965 Quoting Matthew Green | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.2955 |
| c1965 Quoting Matthew Green | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.2856 |
| c1966 앤트로픽 '클로드 사이언스', 인류 최초 자외선 전체 하늘 지도 완성 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4361 |
| c1966 앤트로픽 '클로드 사이언스', 인류 최초 자외선 전체 하늘 지도 완성 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3933 |
| c1966 앤트로픽 '클로드 사이언스', 인류 최초 자외선 전체 하늘 지도 완성 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.379 |
| c1967 오픈AI, 연구원 해고 논란 해명..."안전 제기 보복 아닌 보안 위반" | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3784 |
| c1967 오픈AI, 연구원 해고 논란 해명..."안전 제기 보복 아닌 보안 위반" | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3624 |
| c1967 오픈AI, 연구원 해고 논란 해명..."안전 제기 보복 아닌 보안 위반" | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3281 |
| c1968 데이터센터 전문 퍼머스, 호주 IPO 철회…'엔비디아 후광'도 안 통했다 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4513 |
| c1968 데이터센터 전문 퍼머스, 호주 IPO 철회…'엔비디아 후광'도 안 통했다 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4245 |
| c1968 데이터센터 전문 퍼머스, 호주 IPO 철회…'엔비디아 후광'도 안 통했다 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3789 |
| c1969 앤트로픽, ‘클로드 대시보드·모션’ 공개…"기업 데이터 분석·영상 제작" | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.5142 |
| c1969 앤트로픽, ‘클로드 대시보드·모션’ 공개…"기업 데이터 분석·영상 제작" | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4907 |
| c1969 앤트로픽, ‘클로드 대시보드·모션’ 공개…"기업 데이터 분석·영상 제작" | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4291 |
| c1970 애플, 10월 말 첫 터치스크린 맥북 공개...M6 칩으로 전문가 시장… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4682 |
| c1970 애플, 10월 말 첫 터치스크린 맥북 공개...M6 칩으로 전문가 시장… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4171 |
| c1970 애플, 10월 말 첫 터치스크린 맥북 공개...M6 칩으로 전문가 시장… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4165 |
| c1971 아마존, 안드로이드 태블릿 첫 출시…프리미엄 시장 도전 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4754 |
| c1971 아마존, 안드로이드 태블릿 첫 출시…프리미엄 시장 도전 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4388 |
| c1971 아마존, 안드로이드 태블릿 첫 출시…프리미엄 시장 도전 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3912 |
| c1972 "오픈소스 취약점 AI가 잡는다"...앤트로픽, 무료 보안 검사 도구 … | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.5269 |
| c1972 "오픈소스 취약점 AI가 잡는다"...앤트로픽, 무료 보안 검사 도구 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4682 |
| c1972 "오픈소스 취약점 AI가 잡는다"...앤트로픽, 무료 보안 검사 도구 … | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4391 |
| c1973 vgpu - 브라우저와 Node.js에서 같은 코드로 쓰는 경량 Web… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3838 |
| c1973 vgpu - 브라우저와 Node.js에서 같은 코드로 쓰는 경량 Web… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3733 |
| c1973 vgpu - 브라우저와 Node.js에서 같은 코드로 쓰는 경량 Web… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3564 |
| c1974 Expo bets big on React Native's agentic… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3713 |
| c1974 Expo bets big on React Native's agentic… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3641 |
| c1974 Expo bets big on React Native's agentic… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3177 |
| c1975 프로그래밍은 특별하지 않다 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.2506 |
| c1975 프로그래밍은 특별하지 않다 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.2265 |
| c1975 프로그래밍은 특별하지 않다 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.1937 |
| c1976 누구도 섬이 아니다 - AI가 지적 공동체를 해체할 때 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3164 |
| c1976 누구도 섬이 아니다 - AI가 지적 공동체를 해체할 때 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.294 |
| c1976 누구도 섬이 아니다 - AI가 지적 공동체를 해체할 때 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.2911 |
| c1977 수학자가 Lean 정리 증명기에 대해 알아야 할 것: 신뢰성과 AI | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3575 |
| c1977 수학자가 Lean 정리 증명기에 대해 알아야 할 것: 신뢰성과 AI | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.2418 |
| c1977 수학자가 Lean 정리 증명기에 대해 알아야 할 것: 신뢰성과 AI | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.2381 |
| c1978 AI 시대, 수학 진로를 고민하는 학생들에게 무엇을 말해줘야 할까? | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.2827 |
| c1978 AI 시대, 수학 진로를 고민하는 학생들에게 무엇을 말해줘야 할까? | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.2566 |
| c1978 AI 시대, 수학 진로를 고민하는 학생들에게 무엇을 말해줘야 할까? | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.2535 |
| c1979 컴퓨터는 결정을 내릴 수 없다 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3982 |
| c1979 컴퓨터는 결정을 내릴 수 없다 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.2959 |
| c1979 컴퓨터는 결정을 내릴 수 없다 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.2743 |
| c1980 Python 3.15.0 added to actions/python-v… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3148 |
| c1980 Python 3.15.0 added to actions/python-v… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3105 |
| c1980 Python 3.15.0 added to actions/python-v… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.2763 |
| c1981 Quoting The New York Times | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3528 |
| c1981 Quoting The New York Times | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.346 |
| c1981 Quoting The New York Times | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3064 |
| c1982 저커버그, 경쟁 제품 압박에 안전 우려에도 ‘뮤즈’ 출시 강행 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4843 |
| c1982 저커버그, 경쟁 제품 압박에 안전 우려에도 ‘뮤즈’ 출시 강행 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4003 |
| c1982 저커버그, 경쟁 제품 압박에 안전 우려에도 ‘뮤즈’ 출시 강행 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3987 |
| c1983 전남광주, 여성폭력 피해지원 종사자 교육…복합사례·2차 피해 예방 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.2954 |
| c1983 전남광주, 여성폭력 피해지원 종사자 교육…복합사례·2차 피해 예방 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.2705 |
| c1983 전남광주, 여성폭력 피해지원 종사자 교육…복합사례·2차 피해 예방 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.2688 |
| c1984 앤트로픽, 자체 음성 모델 개발하나…클로드 웹에 ‘보이스’ 메뉴 포착 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.5309 |
| c1984 앤트로픽, 자체 음성 모델 개발하나…클로드 웹에 ‘보이스’ 메뉴 포착 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.5058 |
| c1984 앤트로픽, 자체 음성 모델 개발하나…클로드 웹에 ‘보이스’ 메뉴 포착 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4149 |
| c1985 엔비디아, AI 추론 칩 d-매트릭스에 투자 계획…GPU 중심 생태계 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4818 |
| c1985 엔비디아, AI 추론 칩 d-매트릭스에 투자 계획…GPU 중심 생태계 … | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3937 |
| c1985 엔비디아, AI 추론 칩 d-매트릭스에 투자 계획…GPU 중심 생태계 … | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.368 |
| c1986 MS, 에이전트 의사결정 특화 모델 ‘디시전-1’ 공개…오픈AI도 AP… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4748 |
| c1986 MS, 에이전트 의사결정 특화 모델 ‘디시전-1’ 공개…오픈AI도 AP… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.473 |
| c1986 MS, 에이전트 의사결정 특화 모델 ‘디시전-1’ 공개…오픈AI도 AP… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4445 |
| c1987 테슬라, 유럽 승인 위해 'FSD' 명칭 떼고 '보조 주행'으로 교체 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.355 |
| c1987 테슬라, 유럽 승인 위해 'FSD' 명칭 떼고 '보조 주행'으로 교체 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.342 |
| c1987 테슬라, 유럽 승인 위해 'FSD' 명칭 떼고 '보조 주행'으로 교체 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3322 |
| c1988 알리바바, 연산 단계 줄여 속도·효율 높인 '큐원 이미지 2.1 터보'… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4824 |
| c1988 알리바바, 연산 단계 줄여 속도·효율 높인 '큐원 이미지 2.1 터보'… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4739 |
| c1988 알리바바, 연산 단계 줄여 속도·효율 높인 '큐원 이미지 2.1 터보'… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4434 |
| c1989 메타 인수 무산된 마누스, 6700억 투자 유치로 독립 경영 가속 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4617 |
| c1989 메타 인수 무산된 마누스, 6700억 투자 유치로 독립 경영 가속 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.388 |
| c1989 메타 인수 무산된 마누스, 6700억 투자 유치로 독립 경영 가속 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3824 |
| c1990 물리 법칙 실시간 예측하는 월드 모델 '오딧세이-3' 공개..."벤치마… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4225 |
| c1990 물리 법칙 실시간 예측하는 월드 모델 '오딧세이-3' 공개..."벤치마… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3953 |
| c1990 물리 법칙 실시간 예측하는 월드 모델 '오딧세이-3' 공개..."벤치마… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3886 |
| c1991 [AI 이슈트렌드] 대통령 지지율 제자리 속 은행권 해킹·누리호 발사·… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.376 |
| c1991 [AI 이슈트렌드] 대통령 지지율 제자리 속 은행권 해킹·누리호 발사·… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3618 |
| c1991 [AI 이슈트렌드] 대통령 지지율 제자리 속 은행권 해킹·누리호 발사·… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3551 |
| c1992 백악관, AI 기업 '보안 사고' 보고 의무화...앤트로픽 침해 사건이… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.412 |
| c1992 백악관, AI 기업 '보안 사고' 보고 의무화...앤트로픽 침해 사건이… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3594 |
| c1992 백악관, AI 기업 '보안 사고' 보고 의무화...앤트로픽 침해 사건이… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3473 |
| c1993 목포항구축제 16일 개막…파시·수산물 경매·항구 미식 한자리 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.361 |
| c1993 목포항구축제 16일 개막…파시·수산물 경매·항구 미식 한자리 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3462 |
| c1993 목포항구축제 16일 개막…파시·수산물 경매·항구 미식 한자리 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3421 |
| c1994 앤트로픽 AI, 경찰 미제사건 제보 사이트에 '허위 제보' 소동 | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.401 |
| c1994 앤트로픽 AI, 경찰 미제사건 제보 사이트에 '허위 제보' 소동 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3973 |
| c1994 앤트로픽 AI, 경찰 미제사건 제보 사이트에 '허위 제보' 소동 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3854 |
| c1995 타입세이프, '제브' 출시 3주 만에 대규모 투자 유치...기업가치 1… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4705 |
| c1995 타입세이프, '제브' 출시 3주 만에 대규모 투자 유치...기업가치 1… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.463 |
| c1995 타입세이프, '제브' 출시 3주 만에 대규모 투자 유치...기업가치 1… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4455 |
| c1996 "6~12개월 내 터진다"…주요 AI 기업, 최악의 AI 재난 시나리오… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4652 |
| c1996 "6~12개월 내 터진다"…주요 AI 기업, 최악의 AI 재난 시나리오… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4004 |
| c1996 "6~12개월 내 터진다"…주요 AI 기업, 최악의 AI 재난 시나리오… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.396 |
| c1997 구글, '제미나이 4 아르곤' 후속 '카본' 테스트 중…"오퍼스 5.5… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.6466 |
| c1997 구글, '제미나이 4 아르곤' 후속 '카본' 테스트 중…"오퍼스 5.5… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4856 |
| c1997 구글, '제미나이 4 아르곤' 후속 '카본' 테스트 중…"오퍼스 5.5… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4538 |
| c1998 [AI카툰] Bob, Senior IT guy - 밥, 마운자로 효과 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4514 |
| c1998 [AI카툰] Bob, Senior IT guy - 밥, 마운자로 효과 … | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3837 |
| c1998 [AI카툰] Bob, Senior IT guy - 밥, 마운자로 효과 … | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3791 |
| c1999 REA Reverse - 무엇이든 리버스 엔지니어링하기 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4347 |
| c1999 REA Reverse - 무엇이든 리버스 엔지니어링하기 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3859 |
| c1999 REA Reverse - 무엇이든 리버스 엔지니어링하기 | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.3354 |
| c2000 코딩 에이전트는 왜 이렇게 멍청할까? | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3997 |
| c2000 코딩 에이전트는 왜 이렇게 멍청할까? | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3872 |
| c2000 코딩 에이전트는 왜 이렇게 멍청할까? | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3434 |
| c2001 MXC - 샌드박스 코드 실행 시스템 | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3859 |
| c2001 MXC - 샌드박스 코드 실행 시스템 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3545 |
| c2001 MXC - 샌드박스 코드 실행 시스템 | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3448 |
| c2002 Eve - 디렉터리 하나로 AI 에이전트를 정의하고 배포하는 Verce… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4328 |
| c2002 Eve - 디렉터리 하나로 AI 에이전트를 정의하고 배포하는 Verce… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4155 |
| c2002 Eve - 디렉터리 하나로 AI 에이전트를 정의하고 배포하는 Verce… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3869 |
| c2003 중학생이 AI(Claude)와 함께 '자기 자신을 통과하지 못하는 입체… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3542 |
| c2003 중학생이 AI(Claude)와 함께 '자기 자신을 통과하지 못하는 입체… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3511 |
| c2003 중학생이 AI(Claude)와 함께 '자기 자신을 통과하지 못하는 입체… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3247 |
| c2004 중국 AI 모델 안전성 평가 공개율 3.6%...출시 전 공개는 고작 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3854 |
| c2004 중국 AI 모델 안전성 평가 공개율 3.6%...출시 전 공개는 고작 … | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3703 |
| c2004 중국 AI 모델 안전성 평가 공개율 3.6%...출시 전 공개는 고작 … | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.3576 |
| c2005 나델라 “AI에도 비상 브레이크 필요”...인간 통제·독립 감사 강조 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3927 |
| c2005 나델라 “AI에도 비상 브레이크 필요”...인간 통제·독립 감사 강조 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3903 |
| c2005 나델라 “AI에도 비상 브레이크 필요”...인간 통제·독립 감사 강조 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3852 |
| c2006 [기고] 한국딥러닝 "기업 4곳 중 3곳이 AI 데이터에 투자…이제 ‘… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4616 |
| c2006 [기고] 한국딥러닝 "기업 4곳 중 3곳이 AI 데이터에 투자…이제 ‘… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4413 |
| c2006 [기고] 한국딥러닝 "기업 4곳 중 3곳이 AI 데이터에 투자…이제 ‘… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.3646 |
| c2007 엔비디아, 미국 오픈소스 대표 리플렉션 AI 인수·투자 확대 논의 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4133 |
| c2007 엔비디아, 미국 오픈소스 대표 리플렉션 AI 인수·투자 확대 논의 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.3855 |
| c2007 엔비디아, 미국 오픈소스 대표 리플렉션 AI 인수·투자 확대 논의 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.3717 |
| c2020 [한영자막] AI 에이전트에 학습하는 메모리를 제공해 보세요 — Jak… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.5072 |
| c2020 [한영자막] AI 에이전트에 학습하는 메모리를 제공해 보세요 — Jak… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4571 |
| c2020 [한영자막] AI 에이전트에 학습하는 메모리를 제공해 보세요 — Jak… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.403 |
| c2021 [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.554 |
| c2021 [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.5395 |
| c2021 [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.5231 |
| c2022 [한영자막] 대시보드는 끝났습니다: AI 에이전트가 소프트웨어를 쓰는 법 | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4989 |
| c2022 [한영자막] 대시보드는 끝났습니다: AI 에이전트가 소프트웨어를 쓰는 법 | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4459 |
| c2022 [한영자막] 대시보드는 끝났습니다: AI 에이전트가 소프트웨어를 쓰는 법 | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4309 |
| c2023 [한영자막] 팟캐스트 풀버전 - SpaceX에서 매달 수천 개의 PR을… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.5069 |
| c2023 [한영자막] 팟캐스트 풀버전 - SpaceX에서 매달 수천 개의 PR을… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.5001 |
| c2023 [한영자막] 팟캐스트 풀버전 - SpaceX에서 매달 수천 개의 PR을… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4393 |
| c2024 [한영자막] Uber에서 디버깅 에이전트 하네스를 구축하는 방법 — K… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.5239 |
| c2024 [한영자막] Uber에서 디버깅 에이전트 하네스를 구축하는 방법 — K… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4828 |
| c2024 [한영자막] Uber에서 디버깅 에이전트 하네스를 구축하는 방법 — K… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.479 |
| c2025 [한영자막] AI 시대에 쏟아지는 PR 병목, 어떻게 해결해야 할까요? | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4924 |
| c2025 [한영자막] AI 시대에 쏟아지는 PR 병목, 어떻게 해결해야 할까요? | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4378 |
| c2025 [한영자막] AI 시대에 쏟아지는 PR 병목, 어떻게 해결해야 할까요? | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4179 |
| c2026 [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.501 |
| c2026 [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4942 |
| c2026 [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이… | w40-solar-mini-4 Solar Mini 4: 단일 GPU 실행 MoE와 에이전트 작업 최적화 | 2026-W40 | 0.4126 |
| c2027 [한영자막] 인간은 비동기 API입니다: AI 에이전트가 사람을 기다리… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.5179 |
| c2027 [한영자막] 인간은 비동기 API입니다: AI 에이전트가 사람을 기다리… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4998 |
| c2027 [한영자막] 인간은 비동기 API입니다: AI 에이전트가 사람을 기다리… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4015 |
| c2028 [한영자막] 젠슨 황과 일론 머스크가 직접 밝히는 슈퍼 인텔리전스와 에… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4345 |
| c2028 [한영자막] 젠슨 황과 일론 머스크가 직접 밝히는 슈퍼 인텔리전스와 에… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4234 |
| c2028 [한영자막] 젠슨 황과 일론 머스크가 직접 밝히는 슈퍼 인텔리전스와 에… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.42 |
| c2029 [한영자막] Codex로 요리하기 — OpenAI의 Charlie Gu… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4977 |
| c2029 [한영자막] Codex로 요리하기 — OpenAI의 Charlie Gu… | w40-gemini-4-argon Gemini 4 Argon: 에이전트 작업 강화와 출시 기념 가격 구조 | 2026-W40 | 0.4404 |
| c2029 [한영자막] Codex로 요리하기 — OpenAI의 Charlie Gu… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.4404 |
| c2030 [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Sa… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4329 |
| c2030 [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Sa… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4275 |
| c2030 [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Sa… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.426 |
| c2031 [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 … | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4169 |
| c2031 [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 … | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.3707 |
| c2031 [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 … | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.3542 |
| c2032 [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.52 |
| c2032 [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4894 |
| c2032 [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4378 |
| c2033 [한영자막] 하네스 엔지니어링: 코딩 에이전트로 '소프트웨어 팩토리'를… | w40-llamaindex-context RAG를 에이전트 하네스와 문서 컨텍스트 레이어로 재정의 | 2026-W40 | 0.4481 |
| c2033 [한영자막] 하네스 엔지니어링: 코딩 에이전트로 '소프트웨어 팩토리'를… | w40-deepseek-harness DeepSeek 하네스, 채팅·코딩·문서 통합 데스크톱 앱 프리뷰 | 2026-W40 | 0.4346 |
| c2033 [한영자막] 하네스 엔지니어링: 코딩 에이전트로 '소프트웨어 팩토리'를… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.4071 |
| c2034 [한영자막] 샘 알트만이 OpenAI와 일상을 운영하기 위해 AI를 실… | w40-openai-dots Dots, B2B 상시 에이전트 포지셔닝 | 2026-W40 | 0.578 |
| c2034 [한영자막] 샘 알트만이 OpenAI와 일상을 운영하기 위해 AI를 실… | w40-claude-sonnet-5-5 Claude Sonnet 5.5, 오퍼스급 지능에 가성비 | 2026-W40 | 0.5115 |
| c2034 [한영자막] 샘 알트만이 OpenAI와 일상을 운영하기 위해 AI를 실… | w40-gpt-6-1-sol GPT-6.1 Sol: Astra급 지능 5분의 1 가격 | 2026-W40 | 0.4433 |

## 8. 별칭 표 (keywords.yaml 별칭 제외)

자동 승인 9, 후보 0, decide로 승인 0, 거절 1

| 정본 | 별칭 | status | 이유 | 나온 곳 |
|---|---|---|---|---|
| Claude | 클로드 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1185, it:1204, it:1206 |
| Claude Code | claude-code | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | rp:anthropics/claude-code |
| Claude Haiku 5.5 | 클로드 하이쿠 5.5 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1180 |
| Claude Opus 5.5 | 클로드 오퍼스 5.5 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1163, it:1245 |
| Claude Sonnet 5.5 | 클로드 소네트 5.5 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1149, it:1163 |
| Codex | codex | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | rp:openai/codex |
| Codex | 코덱스 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1193, it:1223, it:1225 |
| DeepSeek | 딥시크 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1196, it:1390 |
| GPT-6 Astra | GPT-6 아스트라 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1148, it:1163, it:1223 |
| GPT-6 Luna | gpt-6-luna | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1043 |
| GPT-6 Luna | GPT-6 루나 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1172, it:1180, it:1198 |
| GPT-6 Sol | GPT-6 솔 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1172, it:1342 |
| GPT-6.1 Sol | GPT-6.1-sol | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1048 |
| GPT-6.1 Sol | GPT-6.1 솔 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1223 |
| Gemini | 제미나이 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1170, it:1182, it:1230 |
| Gemini 3.8 Flash | 제미나이 3.8 플래시 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1245 |
| MAI 코드 1.1 플래시 | MAI-코드-1.1 플래시 | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1161 |
| Mistral | 미스트랄 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1198 |
| Ollama | ollama | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | rp:ollama/ollama |
| OpenRig | openrig | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | rp:mvschwarz/openrig |
| Qwen3.8-27B | 큐원-3.8-27B | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1213 |
| 터미널-벤치 2.1 | 터미널벤치 2.1 | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1205 |
| 테스팅 카탈로그 | 테스팅카탈로그 | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1338 |
| Datasette | datasette.io | rejected | rapidfuzz 90 | it:1047, it:1049 |

## 9. 편집장 입력 후보와 토픽 수 상한 근거

- 편집장 입력: 점수 상위 20개(상한 20). 입력 순서는 cluster_id 고정
- 관심 주제 후보(relevance high 항목이 있는 묶음): 90개
- 2채널 이상 묶음: 1개
- 토픽 수 설정: min 4 / max 10(멈춤 지점에서 max 10 확정)

- **한 채널이 입력의 절반을 넘음**: text 20/20
- 영상 relevance(digest 요약의 관련성 점수, 0.5 이상 high): vd:kcflfXb6dBM 0.6396, vd:sAu_4QuAI0w 0.5942, vd:oeL0uP-NO-U 0.5827, vd:5bg469hWGGc 0.5678, vd:HjQ1G1NvvHQ 0.5618, vd:D7q8fa589FY 0.5553, vd:RVnSsolR3uE 0.5495, vd:eTtZlAPA9H4 0.5386, vd:31XD1O74pks 0.5352, vd:8DRjkp_X8yY 0.5328, vd:wrii8VocfZU 0.527, vd:5tdMgKkX5dU 0.5183, vd:0kVsv2WlL44 0.5154, vd:PACIHCnvNMo 0.4953, vd:6YuIp-MwPv4 0.4924

| 순위 | 묶음 | 이름 | 조합 | 점수 |
|---|---|---|---|---|
| 1 | c1860 | EmbeddingGemma 2: an open, lightweight multimodal embedding… | text 3 | 3319 |
| 2 | c1835 | OpenAI “rogue” agent activities found on Wikimedia projects | text 2 | 3219 |
| 3 | c1840 | Introducing Mistral Large 4: Le chonk | text 3 | 3219 |
| 4 | c1850 | GPT-6 and Intelligent UI for everyone | text 2 | 3219 |
| 5 | c1852 | Sharing AI progress in mathematics | text 2 | 3219 |
| 6 | c1885 | Claude Haiku 5.5 | text 2 | 3219 |
| 7 | c1889 | 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 | text 2 | 3219 |
| 8 | c1986 | MS, 에이전트 의사결정 특화 모델 ‘디시전-1’ 공개…오픈AI도 API 정식 출시 | text 2 | 3219 |
| 9 | c1869 | mvschwarz/openrig | text 1 + github 1 | 3129 |
| 10 | c1837 | llm-openai-decisions 0.1a0 | text 1 | 3119 |
| 11 | c1851 | How Jump Trading is scaling quant research with ChatGPT | text 1 | 3119 |
| 12 | c1853 | Advancing computer use with Ironclad | text 1 | 3119 |
| 13 | c1854 | Atlassian and OpenAI expand partnership to turn enterprise … | text 1 | 3119 |
| 14 | c1855 | Our approach to EU text provenance rules | text 1 | 3119 |
| 15 | c1857 | Introducing the Anthropic Cyber Mission | text 1 | 3119 |
| 16 | c1859 | Expanding the Cyber Verification Program | text 1 | 3119 |
| 17 | c1862 | MCPB로 로컬 MCP 서버를 Claude Desktop 원클릭 확장으로 만들기 | text 1 | 3119 |
| 18 | c1867 | AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재설계하기 | text 1 | 3119 |
| 19 | c1868 | Claude Code 모드(mod) 시작하기 | text 1 | 3119 |
| 20 | c1870 | 에이전트가 쓴 테스트는 무엇을 증명하나 | text 1 | 3119 |
