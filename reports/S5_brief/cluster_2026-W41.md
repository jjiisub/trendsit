# 묶기 리포트 2026-W41

> run `20261009-150737-weekly-24db`. 재현: `uv run python -m trendsit cluster --week 2026-W41 --spec S5`. 문턱값은 임시값(auto 0.8 / border 0.65), 멈춤 지점에서 이 리포트로 확정한다.

> W41 재료는 10/5~10/9 수집분(10/10~11 수집 전). 주가 끝난 뒤 다시 돌려 갱신한다. 2차 실행: 레포끼리 묶지 않기, 영상·레포 키워드 반영

## 1. 요약

| 항목 | 값 |
|---|---|
| 근거 자격 구성원 | 글 141, 영상 8, 레포 7 |
| 제외 | 카드 없는 글 29, digest 없는 영상 7, 관련 없는 레포 0 |
| 묶음 | 144개(토픽 후보 138, 레포만 6) |
| 2채널 이상 / 3채널 | 1 / 0 |
| 1개짜리 묶음 비율(토픽 후보 중) | 127/138 = 92% |
| decide | 묶기 31회 + 별칭 0회 / 상한 60, 상한으로 못 부른 후보 0 |
| 크기 상한(12)으로 막힌 합치기 | 0 |
| 걸린 시간(초) | {'evidence': 0.0, 'normalize': 1.6, 'cluster': 39.5} |

### 채널 조합 분포(토픽 후보)

| 조합 | 묶음 수 |
|---|---|
| text | 129 |
| video | 8 |
| text + github | 1 |

## 2. 유사도 분포 (문턱값 근거)

전체 쌍 12090(같은 채널 9919, 채널 넘음 2171). 0.05 구간별 쌍 수. 글은 본문 임베딩(관련성 필터), 영상은 digest 요약, 레포는 oneliner + description 임베딩이라 채널을 넘는 유사도는 같은 채널보다 낮게 나오는 경향이 있다.

| 구간 | 같은 채널 | 채널 넘음 | 표시 |
|---|---|---|---|
| 0.30~0.35 | 2093 | 459 |  |
| 0.35~0.40 | 1990 | 557 |  |
| 0.40~0.45 | 1522 | 412 |  |
| 0.45~0.50 | 741 | 236 |  |
| 0.50~0.55 | 304 | 95 |  |
| 0.55~0.60 | 100 | 28 |  |
| 0.60~0.65 | 30 | 7 |  |
| 0.65~0.70 | 19 | 3 | border~auto(decide) |
| 0.70~0.75 | 8 | 1 | border~auto(decide) |
| 0.75~0.80 | 3 | 0 | border~auto(decide) |
| 0.80~0.85 | 3 | 0 | auto 이상 |
| 0.85~0.90 | 0 | 0 | auto 이상 |
| 0.90~0.95 | 0 | 0 | auto 이상 |
| 0.95~1.00 | 1 | 0 | auto 이상 |

## 3. 묶음 목록 (토픽 후보, 점수 순)

점수 = 관련성 먼저(최고 relevance, 그 등급 항목 수) → 채널 수 → 근거 수. 묶인 이유: seed(첫 항목), embed(같은 채널 auto 이상), decide(판정 same). sim은 묶음 나머지와의 평균 유사도.

### c144 EmbeddingGemma 2: an open, lightweight multimodal embedding… (text 3, 점수 3319.0)

- 공유: 이름 ['embeddinggemma2', 'gemma4', 'maeb', 'mteb'], 키워드 ['eval', 'multimodal', 'open-weight', 'rag-search']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1111 | text | high | EmbeddingGemma 2: an open, lightweight multimodal embedding… | seed | - |
| it:1132 | text | high | EmbeddingGemma 2 - 개방형 경량 멀티모달 임베딩 모델 | embed | 0.9572 |
| it:1183 | text | high | 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미지·음성 통합 처리 | decide | 0.7619 |

### c145 OpenAI “rogue” agent activities found on Wikimedia projects (text 2, 점수 3219.0)

- 공유: 이름 -, 키워드 ['agent', 'ai-security']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1041 | text | high | OpenAI “rogue” agent activities found on Wikimedia projects | seed | - |
| it:1209 | text | high | 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연관 가능성" | decide | 0.696 |

### c146 Introducing Mistral Large 4: Le chonk (text 2, 점수 3219.0)

- 공유: 이름 -, 키워드 ['eval', 'frontier-release', 'open-weight']
- **의심**: Mistral Large 3 ↔ Mistral Large 4

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1046 | text | high | Introducing Mistral Large 4: Le chonk | seed | - |
| it:1198 | text | high | 미스트랄, 1조 매개변수 ‘라지 4’ 공개..."사이버 보안·오픈 모델 최상위" | decide | 0.7153 |

### c147 GPT-6 and Intelligent UI for everyone (text 2, 점수 3219.0)

- 공유: 이름 ['gpt5.6', 'gpt6'], 키워드 ['frontier-release', 'multimodal']
- **의심**: GPT-5.6 ↔ GPT-6, GPT-5.6 ↔ GPT-6 루나, GPT-5.6 ↔ GPT-6 솔

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1100 | text | high | GPT-6 and Intelligent UI for everyone | seed | - |
| it:1172 | text | high | 오픈AI, 질문에 맞춰 화면 생성하는 'GPT-6' 공개...전 사용자 무료 적용 | embed | 0.8039 |

### c148 Sharing AI progress in mathematics (text 2, 점수 3219.0)

- 공유: 이름 ['lean'], 키워드 ['frontier-release', 'reasoning']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1102 | text | high | Sharing AI progress in mathematics | seed | - |
| it:1156 | text | high | [10월8일] “수학 문제 4000개에 AI 투입해 성과”…오픈AI가 보여준 과학연구의 변화 | decide | 0.6964 |

### c149 Our approach to EU text provenance rules (text 2, 점수 3219.0)

- 공유: 이름 -, 키워드 ['ai-security']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1105 | text | high | Our approach to EU text provenance rules | seed | - |
| it:1225 | text | high | 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만 우선 적용 | decide | 0.6832 |

### c150 Claude Haiku 5.5 (text 2, 점수 3219.0)

- 공유: 이름 -, 키워드 ['eval', 'frontier-release']
- **의심**: Claude Haiku 4.5 ↔ Claude Haiku 5.5

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1144 | text | high | Claude Haiku 5.5 | seed | - |
| it:1180 | text | high | 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.5' 공개 | decide | 0.6743 |

### c151 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최적화 공개 (text 2, 점수 3219.0)

- 공유: 이름 ['mai코드1.1플래시', '마이크로소프트', '서피스랩톱울트라'], 키워드 ['ai-security', 'open-weight']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1161 | text | high | MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최적화 공개 | seed | - |
| it:1165 | text | high | MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개변수 모델 직접 구동 | decide | 0.7944 |

### c152 mvschwarz/openrig (text 1 + github 1, 점수 3126.0)

- 공유: 이름 ['openrig'], 키워드 ['agent', 'coding-agent']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1122 | text | mid | OpenRig - Claude Code와 Codex를 팀으로 운영하는 멀티 에이전트 오케스트레이터 | seed | - |
| rp:mvschwarz/openrig | github | high | mvschwarz/openrig | decide | 0.7379 |

### c154 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 (text 2, 점수 3119.0)

- 공유: 이름 ['뉴욕시의회', '메타', '알렉스터너', '앤트로픽', '오픈ai', '제이콥콕슨'], 키워드 ['ai-security']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1219 | text | mid | 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실" 경고 | seed | - |
| it:1249 | text | high | "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | embed | 0.825 |

### c213 Building advertising for the way people use AI (text 2, 점수 2219.0)


| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1106 | text | mid | Building advertising for the way people use AI | seed | - |
| it:1207 | text | mid | 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생성 옆 노출 | decide | 0.6923 |

### 1개짜리 토픽 후보

| 묶음 | 구성원 | 채널 | relevance | 제목 | 점수 |
|---|---|---|---|---|---|
| c153 | it:1043 | text | high | llm-openai-decisions 0.1a0 | 3119.0 |
| c155 | it:1231 | text | high | 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | 3119.0 |
| c156 | it:1238 | text | high | MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 비용 병목' 해결 | 3119.0 |
| c157 | vd:31XD1O74pks | video | high | [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게 해보세요 | 3119.0 |
| c158 | vd:6YuIp-MwPv4 | video | high | [한영자막] Uber에서 디버깅 에이전트 하네스를 구축하는 방법 — Kriti Dangi | 3119.0 |
| c159 | vd:D7q8fa589FY | video | high | [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이 구조'를 도입해야 합니다 | 3119.0 |
| c160 | vd:PACIHCnvNMo | video | high | [한영자막] 젠슨 황과 일론 머스크가 직접 밝히는 슈퍼 인텔리전스와 에너지, 우주 컴퓨팅의 미래 | 3119.0 |
| c161 | vd:eTtZlAPA9H4 | video | high | [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Salomon, AgentCraft | 3119.0 |
| c162 | vd:kcflfXb6dBM | video | high | [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 어떻게 바뀔까요? | 3119.0 |
| c163 | vd:oeL0uP-NO-U | video | high | [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니다 — Sourcegraph Dan … | 3119.0 |
| c164 | vd:wrii8VocfZU | video | high | [한영자막] 샘 알트만이 OpenAI와 일상을 운영하기 위해 AI를 실제로 활용하는 방법입니다. | 3119.0 |
| c165 | it:1103 | text | high | Advancing computer use with Ironclad | 3117.0 |
| c166 | it:1104 | text | high | Atlassian and OpenAI expand partnership to turn enterprise … | 3117.0 |
| c167 | it:1110 | text | high | Expanding the Cyber Verification Program | 3117.0 |
| c168 | it:1120 | text | high | AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재설계하기 | 3117.0 |
| c169 | it:1149 | text | high | 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 | 3117.0 |
| c170 | it:1154 | text | high | 한국 금융권 공격한 중국 26세 해커…'어설픈 신원 노출'로 덜미 | 3117.0 |
| c171 | it:1159 | text | high | 카카오, 국제 AI 학회서 MoE 학습 최적화·모델 경량화 성과 공개 | 3117.0 |
| c172 | it:1160 | text | high | 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정 모델 ‘d1-3B’ 출시 | 3117.0 |
| c173 | it:1163 | text | high | '헤르메스 에이전트' 누스 리서치, 대규모 투자 유치로 기업용 시장 진출 | 3117.0 |
| c174 | it:1179 | text | high | [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 더 쓸 수 있었다” | 3117.0 |
| c175 | it:1181 | text | high | 구글, ‘나노 바나나 2.1’ 공개...성능 높이고 비용은 반값으로 | 3117.0 |
| c176 | it:1184 | text | high | 스튜어트 러셀의 경고 "LLM 정렬 불가능…모방 학습과 RLHF 한계" | 3117.0 |
| c177 | it:1185 | text | high | 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' 직접 호출 | 3117.0 |
| c178 | it:1205 | text | high | '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개…반응은 엇갈려 | 3117.0 |
| c179 | it:1211 | text | high | 코히어, 에이전트 비용·보안 통제 플랫폼 '노스 2' 출시...알레프 알파 인수 후 첫 행보 | 3117.0 |
| c180 | it:1213 | text | high | 19세 청년의 반란...고스트, 개인용 AI PC '코어'로 147억 투자 유치 | 3117.0 |
| c181 | it:1217 | text | high | “180B 모델, 개인용 노트북으로 구동”...비드래프트, 고성능 모델 경량화 전략 이어간다 | 3117.0 |
| c182 | it:1223 | text | high | 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날부터 처리 속도 50% 향상 | 3117.0 |
| c183 | it:1235 | text | high | KAIST, 데이터 변화해도 검색 정확도 유지하는 ‘CONDA’ 기술 개발 | 3117.0 |
| c184 | it:1237 | text | high | GPT-6 아스트라, 217년 된 나폴레옹 암호 6시간 만에 해독 | 3117.0 |
| c185 | it:1240 | text | high | AI가 쏟아낸 '엉터리 제보'에... 구글, 오픈소스 버그 바운티 일시 중단 | 3117.0 |
| c186 | it:1241 | text | high | 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가상 착용' 도입 | 3117.0 |
| c187 | it:1242 | text | high | 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 | 3117.0 |
| c188 | it:1245 | text | high | "지기 싫어서 남의 코드 복사"…아스트라, 스타크래프트 벤치마크서 꼼수 | 3117.0 |
| c189 | it:1101 | text | high | How Jump Trading is scaling quant research with ChatGPT | 3116.0 |
| c190 | it:1108 | text | high | Introducing the Anthropic Cyber Mission | 3116.0 |
| c191 | it:1121 | text | high | Claude Code 모드(mod) 시작하기 | 3116.0 |
| c192 | it:1123 | text | high | 에이전트가 쓴 테스트는 무엇을 증명하나 | 3116.0 |
| c193 | it:1129 | text | high | 우리가 알던 오픈소스는 죽었다 | 3116.0 |
| c194 | it:1131 | text | high | 소프트웨어 팩토리 패턴 시도하기 | 3116.0 |
| c195 | it:1133 | text | high | 나는 인류를 멸종시키고 있는 AGI다 | 3116.0 |
| c196 | it:1136 | text | high | openTPU - AI가 설계하고 실제 FPGA에서 모델을 실행하는 오픈소스 AI 가속기 | 3116.0 |
| c197 | it:1145 | text | high | Quoting Felix Rieseberg | 3116.0 |
| c198 | it:1167 | text | high | "독파모·모두의 AI 더 안전하게"...SKT, 업스테이지와 AI 보안 동맹 결성 | 3116.0 |
| c199 | it:1189 | text | high | 하크, '스마트폰 대체' AI 에이전트 공개...2027년 전용 기기 출시 | 3116.0 |
| c200 | it:1193 | text | high | "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오토리뷰’ 전면 무료화 | 3116.0 |
| c201 | it:1206 | text | high | MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 축소 | 3116.0 |
| c202 | it:1233 | text | high | 뉴럴링크, 5만시간 뇌 데이터 사전학습…BCI도 '파운데이션 모델' 시대 열렸다 | 3116.0 |
| c203 | it:1236 | text | high | a16z "미국 가구 2.2%만 AI 유료 구독…기술이 경기 순환 핵심 주도" | 3116.0 |
| c204 | it:1246 | text | high | 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규제 경고 폭풍 | 3116.0 |
| c205 | it:1191 | text | high | 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의무화 찬성" | 3115.0 |
| c206 | it:1113 | text | high | MCPB로 로컬 MCP 서버를 Claude Desktop 원클릭 확장으로 만들기 | 3112.0 |
| c214 | it:1232 | text | mid | 앤트로픽, 10월6일까지 '음성 인터뷰어' 가동…대화록 공개·음성 학습 수집 결합 | 2118.0 |
| c215 | it:1097 | text | mid | Disrupting AI-enabled “false front” operations | 2117.0 |
| c216 | it:1109 | text | mid | 2026 Usage Policy update | 2117.0 |
| c217 | it:1130 | text | mid | 여러 팀의 시스템을 이해하기 위한 AI 집단 지성 구축하기 | 2117.0 |
| c218 | it:1148 | text | mid | 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 요동 | 2117.0 |
| c219 | it:1158 | text | mid | 머스크 “테라팹 직접 운영한다”…TSMC 위탁운영설 일축 | 2117.0 |
| c220 | it:1186 | text | mid | 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | 2117.0 |
| c221 | it:1187 | text | mid | AMD, 연내 국내 'AI 연구센터' 설립...정부와 메가프로젝트 협력 추진 | 2117.0 |
| c222 | it:1190 | text | mid | 구글, AI 데이터센터 전력 확보 위해 3.6GW 규모 원전 계약 체결 | 2117.0 |
| c223 | it:1196 | text | mid | 딥시크, 투자 수요 폭발…IPO 전 자금 조달 규모 2배 확대 | 2117.0 |
| c224 | it:1204 | text | mid | [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트로픽과 근본적으로 다르다” | 2117.0 |
| c225 | it:1210 | text | mid | [게시판] 두산로보틱스, 989억 규모 피지컬 AI 국책과제 2건 선정 등 단신 | 2117.0 |
| c226 | it:1212 | text | mid | 엔비디아-그로크 27조 계약 파장…소외된 엔지니어들 "거래 불공정" 소송 | 2117.0 |
| c227 | it:1239 | text | mid | 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부담 낮춘다 | 2117.0 |
| c228 | it:1243 | text | mid | "전직 미국 관료 사칭"…중국 해커, AI 정책 전문가 계정 노렸다 | 2117.0 |
| c229 | it:1250 | text | mid | [AI리더의 서가] AI 루프를 설계하라 | 2117.0 |
| c230 | it:1045 | text | mid | EmbeddingGemma 2 | 2116.0 |
| c231 | it:1098 | text | mid | Helping teens learn, plan, and shape the future of AI | 2116.0 |
| c232 | it:1116 | text | mid | AI가 코드를 쓸수록 도메인 주도 설계가 더 중요해지는 이유 | 2116.0 |
| c233 | it:1126 | text | mid | Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호스팅 AI 비서 | 2116.0 |
| c234 | it:1138 | text | mid | Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소스 작업 공간 | 2116.0 |
| c235 | it:1157 | text | mid | 구글, 텍스트 입력으로 게임 만드는 플랫폼 공개…유니티와 협력 | 2116.0 |
| c236 | it:1162 | text | mid | 누리호 올라탄 토종 AI 반도체, 우주 궤도서 성능 실증 나선다 | 2116.0 |
| c237 | it:1168 | text | mid | 저커버그 부부의 바이오허브, 미 정부·구글과 2.4조 AI 생물학 데이터 구축 | 2116.0 |
| c238 | it:1169 | text | mid | 메타 '뮤즈', 스마트폰 이어 아이패드용 앱 출시…업무용 도구 연동 강화 | 2116.0 |
| c239 | it:1171 | text | mid | 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 121만개 확보 나선다 | 2116.0 |
| c240 | it:1173 | text | mid | 삼성전자, 3분기 영업익 107조...애플·엔비디아도 못 넘은 '100조' 첫 달성 | 2116.0 |
| c241 | it:1178 | text | mid | [AI리더의 서가] Agentic AI 구축 개발의 모든 것 | 2116.0 |
| c242 | it:1182 | text | mid | "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정황 포착 | 2116.0 |
| c243 | it:1218 | text | mid | 이탈리아 멜로니 총리, AI 딥페이크 막으려 '목소리 상표권' 신청 | 2116.0 |
| c244 | it:1230 | text | mid | 구글, 'AI 프로' 국내 한정 40% 할인...연간 구독권 프로모션 진행 | 2116.0 |
| c245 | it:1247 | text | mid | 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안전성에 이례적 경고 | 2116.0 |
| c246 | it:1248 | text | mid | 'AI 피해자 영상'에 속아 내려진 중형..."형량 잘못됐다" 선고 파기 | 2116.0 |
| c247 | it:1252 | text | mid | 트럼프, ‘슈퍼 인텔리전스 부대’ 출범…국가정보국장, 백악관 AI 차르 겸임 | 2116.0 |
| c248 | it:1112 | text | mid | OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 AI 에이전트 | 2115.0 |
| c249 | it:1146 | text | mid | Qwen3.8 27B addition in words | 2115.0 |
| c250 | it:1170 | text | mid | 구글, AI 생성물 구분하는 '신스ID 감지기' 일반에 전면 공개 | 2115.0 |
| c251 | it:1203 | text | mid | [AI리더의 서가] SQL부터 AI까지 데이터 분석 with 클로드 코드 | 2115.0 |
| c252 | it:1208 | text | mid | 노르웨이, 공공장소 ‘AI 안경’ 일시 금지 추진…세계 첫 규제 움직임 | 2115.0 |
| c253 | it:1214 | text | mid | [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용접 솔루션’ 공동개발 협력 등 단신 | 2115.0 |
| c254 | it:1220 | text | mid | 포지큐브, 롯데벤처스와 멀티 AI 에이전트 기반 AX 추진 | 2115.0 |
| c255 | it:1221 | text | mid | '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 아니다" | 2115.0 |
| c256 | it:1050 | text | mid | Scrimshaw Jukebox | 2114.0 |
| c257 | it:1216 | text | mid | 카카오모빌리티, 고려대와 AX 협력…모빌리티 핵심 기술 국방 분야 접목 | 2114.0 |
| c258 | it:1048 | text | mid | Mistral Large 4 | 2113.0 |
| c259 | it:1042 | text | mid | Quoting Victoria Kim | 2112.0 |
| c260 | it:1044 | text | mid | llm-mistral 0.16 | 2112.0 |
| c261 | it:1039 | text | low | Anti-Patterns in Software Blogging | 1117.0 |
| c262 | it:1094 | text | low | How Oracle turns days of work into minutes with ChatGPT and… | 1117.0 |
| c263 | it:1128 | text | low | 자율주행 데이터에서 시간은 어떻게 맞춰지는가 | 1117.0 |
| c264 | it:1095 | text | low | Pollo AI turns creative ideas into campaigns with OpenAI | 1116.0 |
| c265 | it:1096 | text | low | LegalOn halves Codex costs while maintaining development sp… | 1116.0 |
| c266 | it:1215 | text | low | 화웨이, 퀄컴에 '로직폴딩' 칩 관련 특허 라이선스 제공 | 1116.0 |
| c267 | it:1222 | text | low | 헨켈, SEDEX 2026서 AI·HBM 시대 위한 첨단 패키징 소재 솔루션 선보여 | 1116.0 |
| c268 | it:1224 | text | low | LG전자, 북미서 5GW 규모 AIDC 냉각솔루션 장기계약 체결 | 1115.0 |
| c269 | it:1229 | text | low | [AI리더의 서가] CEO의  AI | 1115.0 |
| c270 | it:1251 | text | low | 머스크, '스페이스XSI'로 리브랜딩 시사…트럼프 'SI' 발언 동조 | 1115.0 |
| c271 | it:1099 | text | low | Radisson Hotel Group brings hotel discovery into ChatGPT | 1114.0 |
| c272 | it:1141 | text | low | ttok 0.4 | 1114.0 |
| c273 | it:1143 | text | low | Quoting Ben Affleck | 1114.0 |
| c274 | it:1188 | text | low | [게시판] SKT, 독파모 'A.X K2'로 순우리말 선정·글꼴 제작 등 단신 | 1114.0 |
| c275 | it:1047 | text | low | Using Parseable with Datasette for OpenTelemetry traces | 1113.0 |
| c276 | it:1049 | text | low | datasette-atom 0.11a0 | 1113.0 |
| c277 | it:1142 | text | low | Quoting Carson Gross | 1113.0 |
| c278 | it:1155 | text | low | [AI리더의 서가] 이너 프롬프트 | 1113.0 |
| c279 | it:1115 | text | low | 「Quo Vadis, Mathematics?」—“수학이여, 어디로 가는가?” | 1110.0 |
| c280 | it:1117 | text | low | AI 시대의 커리어 조언 - 문제를 푸는 능력보다 찾고 선택하는 능력 | 1110.0 |
| c281 | it:1119 | text | low | AI로 의도, 품질, 예술성을 확장하는 법 [영상] | 1110.0 |
| c282 | it:1125 | text | low | AI 시대, 매니저의 길 | 1110.0 |
| c283 | it:1127 | text | low | jev가 여는 비즈니스 AI: 에이전트에서 컴포넌트로 | 1110.0 |
| c284 | it:1135 | text | low | 제프리 카첸버그 - 세상이 바뀌고 있다: 창의성을 위한 AI | 1110.0 |
| c285 | it:1151 | text | low | 여수, 23~24일 독서문화축제…야외 독서·섬 체험 운영 | 1110.0 |
| c286 | it:1164 | text | low | 오픈AI "10대 챗GPT 평균 15분 사용" 주장에 안전성 논란 불붙어 | 1110.0 |
| c287 | it:1194 | text | low | 전남광주, 여수서 9~11일 ‘세계 김밥&소금 페스티벌’ | 1110.0 |

### 레포만 있는 묶음(토픽 후보 아님, 홈 레포 목록)

- c207: rp:NVIDIA/OpenShell
- c208: rp:Panniantong/Agent-Reach
- c209: rp:cursor/plugins
- c210: rp:heygen-com/hyperframes
- c211: rp:thedotmack/claude-mem
- c212: rp:tile-ai/tilelang

## 4. decide 판정

31건. confidence 0.6 미만은 묶지 않음.

| a | b | 채널 넘음 | sim | 공유 | answer | conf | reason |
|---|---|---|---|---|---|---|---|
| it:1132 EmbeddingGemma 2 - 개방형 경량 멀티모… | it:1183 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미… |  | 0.798 | embeddinggemma2, gemma4, maeb, eval, mu… | same | 0.95 | a, b 모두 Google의 EmbeddingGemma 2 모델 공개를 다룸 |
| it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.… | it:1165 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개.… |  | 0.7944 | mai코드1.1플래시, 마이크로소프트, 서피스랩톱울트라, ai-secu… | same | 0.95 | a는 서피스 랩톱 울트라 출시에 맞춰 공개된 MAI-코드-1.1 플래시의 온디바이스 최적화 및 성능을, b는 서피스 랩톱 울트라 하드웨어 자체… |
| it:1149 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·… | it:1182 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화… |  | 0.7558 | agent | diff | 0.95 | a는 구글 클라우드의 기업용 '제미나이 에이전트' 출시, b는 구글 제미나이의 개인용 '전화 대행' 기능 포착 → 다른 제품/기능 |
| it:1122 OpenRig - Claude Code와 Codex를… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.7379 | openrig, agent, coding-agent | same | 0.95 | a는 OpenRig 오케스트레이터 소개, b는 OpenRig GitHub 레포 → 같은 제품 |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보… | it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… |  | 0.7327 | - | diff | 0.95 | a는 Claude Opus 5.5의 구독 가치 분석, b는 Claude Haiku 5.5의 출시 발표 → 같은 회사의 다른 모델 라인업 |
| it:1111 EmbeddingGemma 2: an open, li… | it:1183 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미… |  | 0.7258 | embeddinggemma2, gemma4, maeb, eval, mu… | same | 0.98 | a, b 모두 Google DeepMind의 EmbeddingGemma 2 모델 공개를 다룸 |
| it:1046 Introducing Mistral Large 4: … | it:1198 미스트랄, 1조 매개변수 ‘라지 4’ 공개..."사이… |  | 0.7153 | eval, frontier-release | same | 0.95 | a, b 모두 Mistral Large 4(ML4) 모델의 공개와 스펙을 다룸 |
| it:1044 llm-mistral 0.16 | it:1046 Introducing Mistral Large 4: … |  | 0.7146 | mistrallarge4, open-weight | diff | 0.9 | a는 llm-mistral 0.16 릴리스, b는 Mistral Large 4 모델 발표 → 다른 대상 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서… |  | 0.7079 | 오픈ai, agent, ai-security | diff | 0.9 | a는 호주 청문회 출석 및 규제 찬성, b는 전 세계적 법적 소송 및 IPO 연기 등 광범위한 규제 대응을 다룸 → 다른 사건 |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.7053 | - | diff | 0.95 | a는 AI 구독 서비스의 가격 대비 성능 비교 분석, b는 MS와 메타의 클로드 사내 사용 축소 사건 → 다른 주제 |
| it:1122 OpenRig - Claude Code와 Codex를… | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… |  | 0.7039 | claudecode, codex, agent, coding-agent | diff | 0.95 | a는 OpenRig, b는 Lemma → 서로 다른 오픈소스 프로젝트 |
| it:1102 Sharing AI progress in mathem… | it:1156 [10월8일] “수학 문제 4000개에 AI 투입해 … |  | 0.6964 | lean, frontier-release, reasoning | same | 0.95 | a와 b 모두 OpenAI가 내부 프런티어 모델을 이용해 수학 문제를 해결하고 결과를 공개한 동일한 발표(722편 원고, Lean 형식화, C… |
| it:1041 OpenAI “rogue” agent activiti… | it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단… |  | 0.696 | agent, ai-security | same | 0.95 | a와 b 모두 OpenAI의 'rogue' 에이전트가 위키미디어 프로젝트에서 일으킨 활동과 5월 장애 연관성을 다루는 같은 사건 보도임 |
| it:1106 Building advertising for the … | it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생… |  | 0.6923 | - | same | 0.95 | a와 b 모두 OpenAI가 ChatGPT에 시각적 광고 포맷을 도입하고 테스트를 시작한다는 발표를 다룸 |
| it:1046 Introducing Mistral Large 4: … | it:1048 Mistral Large 4 |  | 0.6892 | mistrallarge4, eval, frontier-release | diff | 0.9 | a는 Mistral Large 4의 공식 출시 발표(스펙, 학습 환경, API 공개), b는 Mistral Large 4를 포함한 여러 모델의… |
| it:1105 Our approach to EU text prove… | it:1225 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만… |  | 0.6832 | ai-security | same | 0.95 | a, b 모두 OpenAI의 textGrain 워터마킹 기술 도입 및 EU 적용 발표를 다룸 |
| it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.6794 | agent, coding-agent | diff | 0.95 | a는 Lemma, b는 openrig → 서로 다른 오픈소스 프로젝트 |
| it:1171 스페이스X, AI 칩 구매에 53조 조달 추진...G… | it:1239 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스… |  | 0.6757 | 엔비디아 | diff | 0.95 | a는 스페이스X의 GPU 구매 자금 조달, b는 아마존의 AI 칩 매각 후 리스 구조 → 다른 회사의 다른 재무/구매 사안 |
| it:1144 Claude Haiku 5.5 | it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… |  | 0.6743 | eval, frontier-release | same | 0.95 | a, b 모두 Anthropic의 Claude Haiku 5.5 모델 출시 및 가격·성능을 다룸 |
| it:1112 OpenMuse - 브라우저와 터미널로 일하는 오픈소… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.6736 | agent | diff | 0.95 | a는 OpenMuse, b는 openrig → 서로 다른 오픈소스 에이전트 도구 |
| it:1120 AI 네이티브 SDLC - 개발 전 과정을 에이전트에… | vd:kcflfXb6dBM [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워… | 예 | 0.6733 | agent | diff | 0.9 | a는 'AI 네이티브 SDLC'라는 특정 방법론/프레임워크를 소개하는 글, b는 AI 코드 워크플로우의 미래와 개발자 역량 변화에 대한 일반적… |
| it:1044 llm-mistral 0.16 | it:1048 Mistral Large 4 |  | 0.663 | mistrallarge4 | diff | 0.9 | a는 llm-mistral 0.16 릴리스, b는 Mistral Large 4 벤치마크 테스트 → 다른 대상 |
| it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… | it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객… |  | 0.6616 | 앤트로픽 | diff | 0.95 | a는 '클로드 하이쿠 5.5' 모델 출시, b는 '클로드 포 스타트업' 지원 프로그램 확대 → 다른 대상 |
| it:1144 Claude Haiku 5.5 | it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보… |  | 0.6611 | anthropic, openai | diff | 0.95 | a는 Claude Haiku 5.5의 가격 구조 분석, b는 Claude Opus 5.5와 GPT-6.1 Sol의 구독 가치 비교 → 다른 모델 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통… |  | 0.6597 | 앤트로픽, 오픈ai, ai-security | diff | 0.95 | a는 호주 의회 청문회, b는 뉴욕시의회 청문회 → 장소와 주제가 다른 별개의 사건 |
| it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.6593 | 앤트로픽 | diff | 0.95 | a는 앤트로픽의 스타트업 지원 프로그램 '클로드 포 스타트업' 확대 발표, b는 MS·메타의 클로드 사내 사용 축소 및 앤트로픽의 기업 시장 … |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼… |  | 0.6588 | 앤트로픽, 오픈ai | diff | 0.95 | a는 호주 의회 청문회에서의 AI 에이전트 사고 신고 의무화 논의, b는 알트먼의 규제 관련 인터뷰 및 앤트로픽의 과학 연구 방법론 발표 → … |
| it:1167 "독파모·모두의 AI 더 안전하게"...SKT, 업스… | it:1188 [게시판] SKT, 독파모 'A.X K2'로 순우리말… |  | 0.6556 | - | diff | 0.95 | a는 SKT와 업스테이지의 AI 보안 협의체 출범, b는 SKT의 A.X K2 활용 단신 → 다른 사건 |
| it:1126 Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호… | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… |  | 0.6528 | agent | diff | 0.95 | a는 Octop(셀프 호스팅 AI 비서), b는 Lemma(오픈소스 팀 작업 공간) → 다른 제품 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회… |  | 0.6513 | 앤트로픽, 오픈ai, ai-security | diff | 0.95 | a는 호주 의회 청문회, b는 뉴욕시의회 청문회 → 장소와 주제가 다른 별개의 사건 |
| it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.6512 | 앤트로픽 | diff | 0.95 | a는 앤트로픽의 신규 모델 '클로드 하이쿠 5.5' 출시 발표, b는 MS와 메타의 '클로드' 및 '클로드 코드' 사내 사용 축소 소식 → 다… |

## 5. 경계 근처 상위 20쌍 (묶이지 않은 쌍, 묶였어야 할 것 같은지 확인)

| a | b | 채널 넘음 | sim | 경로 | 판정 | 공유 |
|---|---|---|---|---|---|---|
| rp:mvschwarz/openrig mvschwarz/openrig | rp:thedotmack/claude-mem thedotmack/claude-mem |  | 0.8142 | none | - | agent, coding-agent |
| it:1149 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드'… | it:1182 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정… |  | 0.7558 | decide | diff 0.95 | agent |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 … | it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.… |  | 0.7327 | decide | diff 0.95 | - |
| rp:Panniantong/Agent-Reach Panniantong/Agent-Reach | rp:mvschwarz/openrig mvschwarz/openrig |  | 0.7306 | none | - | agent, coding-agent |
| it:1044 llm-mistral 0.16 | it:1046 Introducing Mistral Large 4: Le ch… |  | 0.7146 | decide | diff 0.9 | mistrallarge4, open-weight |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규… |  | 0.7079 | decide | diff 0.9 | 오픈ai, agent, ai-security |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 … | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 … |  | 0.7053 | decide | diff 0.95 | - |
| it:1122 OpenRig - Claude Code와 Codex를 팀으로 … | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소… |  | 0.7039 | decide | diff 0.95 | claudecode, codex, agent, coding-agent |
| it:1046 Introducing Mistral Large 4: Le ch… | it:1048 Mistral Large 4 |  | 0.6892 | decide | diff 0.9 | mistrallarge4, eval, frontier-release |
| it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.6794 | decide | diff 0.95 | agent, coding-agent |
| it:1171 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 12… | it:1239 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부… |  | 0.6757 | decide | diff 0.95 | 엔비디아 |
| it:1112 OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 … | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.6736 | decide | diff 0.95 | agent |
| it:1120 AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재… | vd:kcflfXb6dBM [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의… | 예 | 0.6733 | decide | diff 0.9 | agent |
| it:1044 llm-mistral 0.16 | it:1048 Mistral Large 4 |  | 0.663 | decide | diff 0.9 | mistrallarge4 |
| it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.… | it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 |  | 0.6616 | decide | diff 0.95 | 앤트로픽 |
| rp:mvschwarz/openrig mvschwarz/openrig | rp:tile-ai/tilelang tile-ai/tilelang |  | 0.6616 | none | - | - |
| it:1144 Claude Haiku 5.5 | it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 … |  | 0.6611 | decide | diff 0.95 | anthropic, openai |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… |  | 0.6597 | decide | diff 0.95 | 앤트로픽, 오픈ai, ai-security |
| it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 … |  | 0.6593 | decide | diff 0.95 | 앤트로픽 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트… |  | 0.6588 | decide | diff 0.95 | 앤트로픽, 오픈ai |

### border 아래(0.55~0.65)에서 이름을 공유하는 쌍 상위 20

문턱값을 낮추면 decide로 갈 후보. 같은 대상인데 여기 있으면 border를 낮출 근거다.

| a | b | 채널 넘음 | sim | 공유 이름 |
|---|---|---|---|---|
| it:1210 [게시판] 두산로보틱스, 989억 규모 피지컬 AI 국책과제 … | it:1214 [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용접 솔루션… |  | 0.6487 | 두산로보틱스, 딥엑스 |
| it:1193 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오… | it:1223 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날부터 처리… |  | 0.6389 | 오픈ai, 코덱스 |
| it:1229 [AI리더의 서가] CEO의  AI | it:1250 [AI리더의 서가] AI 루프를 설계하라 |  | 0.6322 | 영풍문고 |
| it:1045 EmbeddingGemma 2 | it:1111 EmbeddingGemma 2: an open, lightwe… |  | 0.6319 | embeddinggemma2 |
| it:1172 오픈AI, 질문에 맞춰 화면 생성하는 'GPT-6' 공개...… | it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생성 옆 노출 |  | 0.6319 | 오픈ai, 챗gpt |
| it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규… |  | 0.6222 | 오픈ai |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연… |  | 0.6168 | 오픈ai |
| it:1247 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안… | it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 … |  | 0.6167 | 오픈ai |
| it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | it:1242 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 |  | 0.6165 | 구글, 앤트로픽 |
| it:1120 AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재… | it:1131 소프트웨어 팩토리 패턴 시도하기 |  | 0.6144 | claudecode |
| it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 … |  | 0.6132 | 깃허브코파일럿, 마이크로소프트 |
| it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… | it:1247 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안… |  | 0.6129 | 오픈ai |
| it:1045 EmbeddingGemma 2 | it:1132 EmbeddingGemma 2 - 개방형 경량 멀티모달 임베딩… |  | 0.6117 | embeddinggemma2 |
| it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규… |  | 0.6109 | 샘알트먼, 오픈ai |
| it:1185 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' … | it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 |  | 0.6106 | 앤트로픽 |
| it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트… | it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 … |  | 0.6061 | 앤트로픽, 오픈ai |
| it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규… |  | 0.6051 | 오픈ai |
| it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트… | it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… |  | 0.5986 | 앤트로픽, 오픈ai |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1221 '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 … |  | 0.5955 | 앤트로픽, 오픈ai |
| it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생성 옆 노출 | it:1241 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가상 착용'… |  | 0.5935 | 오픈ai, 챗gpt |

## 6. 의심 병합 (숫자·버전·크기만 다른 이름이 한 묶음)

- c146 Introducing Mistral Large 4: Le chonk: Mistral Large 3 ↔ Mistral Large 4
- c147 GPT-6 and Intelligent UI for everyone: GPT-5.6 ↔ GPT-6, GPT-5.6 ↔ GPT-6 루나, GPT-5.6 ↔ GPT-6 솔
- c150 Claude Haiku 5.5: Claude Haiku 4.5 ↔ Claude Haiku 5.5

## 7. 과거 대조 후보

- 지난 토픽 없음(첫 실행): 모든 묶음이 new 후보

## 8. 별칭 표 (keywords.yaml 별칭 제외)

자동 승인 5, 후보 0, decide로 승인 0, 거절 1

| 정본 | 별칭 | status | 이유 | 나온 곳 |
|---|---|---|---|---|
| GPT-6 Luna | gpt-6-luna | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1043 |
| GPT-6.1 Sol | GPT-6.1-sol | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1048 |
| MAI 코드 1.1 플래시 | MAI-코드-1.1 플래시 | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1161 |
| OpenRig | openrig | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | rp:mvschwarz/openrig |
| 터미널-벤치 2.1 | 터미널벤치 2.1 | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1205 |
| Datasette | datasette.io | rejected | rapidfuzz 90 | it:1047, it:1049 |

## 9. 편집장 입력 후보와 토픽 수 상한 근거

- 편집장 입력: 점수 상위 20개(상한 20). 입력 순서는 cluster_id 고정
- 관심 주제 후보(relevance high 항목이 있는 묶음): 63개
- 2채널 이상 묶음: 1개
- 지금 토픽 수 설정: min 4 / max 10(설계 초안: 7·10·12 중 확정)

| 순위 | 묶음 | 이름 | 조합 | 점수 |
|---|---|---|---|---|
| 1 | c144 | EmbeddingGemma 2: an open, lightweight multimodal embedding… | text 3 | 3319.0 |
| 2 | c145 | OpenAI “rogue” agent activities found on Wikimedia projects | text 2 | 3219.0 |
| 3 | c146 | Introducing Mistral Large 4: Le chonk | text 2 | 3219.0 |
| 4 | c147 | GPT-6 and Intelligent UI for everyone | text 2 | 3219.0 |
| 5 | c148 | Sharing AI progress in mathematics | text 2 | 3219.0 |
| 6 | c149 | Our approach to EU text provenance rules | text 2 | 3219.0 |
| 7 | c150 | Claude Haiku 5.5 | text 2 | 3219.0 |
| 8 | c151 | MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최적화 공개 | text 2 | 3219.0 |
| 9 | c152 | mvschwarz/openrig | text 1 + github 1 | 3126.0 |
| 10 | c153 | llm-openai-decisions 0.1a0 | text 1 | 3119.0 |
| 11 | c154 | "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | text 2 | 3119.0 |
| 12 | c155 | 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | text 1 | 3119.0 |
| 13 | c156 | MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 비용 병목' 해결 | text 1 | 3119.0 |
| 14 | c157 | [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게 해보세요 | video 1 | 3119.0 |
| 15 | c158 | [한영자막] Uber에서 디버깅 에이전트 하네스를 구축하는 방법 — Kriti Dangi | video 1 | 3119.0 |
| 16 | c159 | [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이 구조'를 도입해야 합니다 | video 1 | 3119.0 |
| 17 | c160 | [한영자막] 젠슨 황과 일론 머스크가 직접 밝히는 슈퍼 인텔리전스와 에너지, 우주 컴퓨팅의 미래 | video 1 | 3119.0 |
| 18 | c161 | [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Salomon, AgentCraft | video 1 | 3119.0 |
| 19 | c162 | [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 어떻게 바뀔까요? | video 1 | 3119.0 |
| 20 | c163 | [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니다 — Sourcegraph Dan … | video 1 | 3119.0 |
