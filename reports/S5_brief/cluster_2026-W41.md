# 묶기 리포트 2026-W41

> run `20261010-234221-weekly-e3b5`. 재현: `uv run python -m trendsit cluster --week 2026-W41 --spec S5`. 문턱값은 임시값(auto 0.8 / border 0.65), 멈춤 지점에서 이 리포트로 확정한다.

> weekly 실행의 묶기 단계

## 1. 요약

| 항목 | 값 |
|---|---|
| 근거 자격 구성원 | 글 141, 영상 8, 레포 7 |
| 제외 | 카드 없는 글 50, digest 없는 영상 8, 관련 없는 레포 0 |
| 묶음 | 143개(토픽 후보 137, 레포만 6) |
| 2채널 이상 / 3채널 | 1 / 0 |
| 1개짜리 묶음 비율(토픽 후보 중) | 127/137 = 93% |
| decide | 묶기 58회 + 별칭 0회 / 상한 60, 상한으로 못 부른 후보 0 |
| 크기 상한(12)으로 막힌 합치기 | 0 |
| 걸린 시간(초) | {'evidence': 0.0, 'normalize': 0.3, 'cluster': 170.1} |

### 채널 조합 분포(토픽 후보)

| 조합 | 묶음 수 |
|---|---|
| text | 128 |
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

### c1452 EmbeddingGemma 2: an open, lightweight multimodal embedding… (text 4, 점수 3319)

- 공유: 이름 ['embeddinggemma2'], 키워드 ['open-weight', 'rag-search']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1111 | text | high | EmbeddingGemma 2: an open, lightweight multimodal embedding… | seed | - |
| it:1132 | text | high | EmbeddingGemma 2 - 개방형 경량 멀티모달 임베딩 모델 | embed | 0.9572 |
| it:1183 | text | high | 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미지·음성 통합 처리 | decide | 0.7619 |
| it:1045 | text | mid | EmbeddingGemma 2 | decide | 0.5893 |

### c1448 OpenAI “rogue” agent activities found on Wikimedia projects (text 2, 점수 3219)

- 공유: 이름 -, 키워드 ['agent', 'ai-security']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1041 | text | high | OpenAI “rogue” agent activities found on Wikimedia projects | seed | - |
| it:1209 | text | high | 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연관 가능성" | decide | 0.696 |

### c1453 Introducing Mistral Large 4: Le chonk (text 3, 점수 3219)

- 공유: 이름 -, 키워드 ['eval', 'frontier-release']
- **의심**: Mistral Large 3 ↔ Mistral Large 4

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1046 | text | high | Introducing Mistral Large 4: Le chonk | seed | - |
| it:1198 | text | high | 미스트랄, 1조 매개변수 ‘라지 4’ 공개..."사이버 보안·오픈 모델 최상위" | decide | 0.7153 |
| it:1048 | text | mid | Mistral Large 4 | decide | 0.6244 |

### c1463 GPT-6 and Intelligent UI for everyone (text 2, 점수 3219)

- 공유: 이름 ['gpt5.6', 'gpt6'], 키워드 ['frontier-release', 'multimodal']
- **의심**: GPT-5.6 ↔ GPT-6, GPT-5.6 ↔ GPT-6 루나, GPT-5.6 ↔ GPT-6 솔

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1100 | text | high | GPT-6 and Intelligent UI for everyone | seed | - |
| it:1172 | text | high | 오픈AI, 질문에 맞춰 화면 생성하는 'GPT-6' 공개...전 사용자 무료 적용 | embed | 0.8039 |

### c1465 Sharing AI progress in mathematics (text 2, 점수 3219)

- 공유: 이름 ['lean'], 키워드 ['frontier-release', 'reasoning']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1102 | text | high | Sharing AI progress in mathematics | seed | - |
| it:1156 | text | high | [10월8일] “수학 문제 4000개에 AI 투입해 성과”…오픈AI가 보여준 과학연구의 변화 | decide | 0.6964 |

### c1468 Our approach to EU text provenance rules (text 2, 점수 3219)

- 공유: 이름 ['codex'], 키워드 ['ai-security']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1105 | text | high | Our approach to EU text provenance rules | seed | - |
| it:1225 | text | high | 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만 우선 적용 | decide | 0.6832 |

### c1497 Claude Haiku 5.5 (text 2, 점수 3219)

- 공유: 이름 ['claudehaiku5.5', 'gpt6luna'], 키워드 ['eval', 'frontier-release']
- **의심**: Claude Haiku 4.5 ↔ Claude Haiku 5.5

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1144 | text | high | Claude Haiku 5.5 | seed | - |
| it:1180 | text | high | 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.5' 공개 | decide | 0.6743 |

### c1481 mvschwarz/openrig (text 1 + github 1, 점수 3126)

- 공유: 이름 ['openrig'], 키워드 ['agent', 'coding-agent']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1122 | text | mid | OpenRig - Claude Code와 Codex를 팀으로 운영하는 멀티 에이전트 오케스트레이터 | seed | - |
| rp:mvschwarz/openrig | github | high | mvschwarz/openrig | decide | 0.7379 |

### c1549 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 (text 2, 점수 3119)

- 공유: 이름 ['뉴욕시의회', '메타', '알렉스터너', '앤트로픽', '오픈ai', '제이콥콕슨'], 키워드 ['ai-security']

| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1219 | text | mid | 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실" 경고 | seed | - |
| it:1249 | text | high | "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | embed | 0.825 |

### c1469 Building advertising for the way people use AI (text 2, 점수 2219)


| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |
|---|---|---|---|---|---|
| it:1106 | text | mid | Building advertising for the way people use AI | seed | - |
| it:1207 | text | mid | 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생성 옆 노출 | decide | 0.6923 |

### 1개짜리 토픽 후보

| 묶음 | 구성원 | 채널 | relevance | 제목 | 점수 |
|---|---|---|---|---|---|
| c1450 | it:1043 | text | high | llm-openai-decisions 0.1a0 | 3119 |
| c1557 | it:1231 | text | high | 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | 3119 |
| c1563 | it:1238 | text | high | MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 비용 병목' 해결 | 3119 |
| c1582 | vd:31XD1O74pks | video | high | [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게 해보세요 | 3119 |
| c1584 | vd:D7q8fa589FY | video | high | [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이 구조'를 도입해야 합니다 | 3119 |
| c1586 | vd:eTtZlAPA9H4 | video | high | [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Salomon, AgentCraft | 3119 |
| c1587 | vd:kcflfXb6dBM | video | high | [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 어떻게 바뀔까요? | 3119 |
| c1588 | vd:oeL0uP-NO-U | video | high | [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니다 — Sourcegraph Dan … | 3119 |
| c1589 | vd:wrii8VocfZU | video | high | [한영자막] 샘 알트만이 OpenAI와 일상을 운영하기 위해 AI를 실제로 활용하는 방법입니다. | 3119 |
| c1466 | it:1103 | text | high | Advancing computer use with Ironclad | 3117 |
| c1467 | it:1104 | text | high | Atlassian and OpenAI expand partnership to turn enterprise … | 3117 |
| c1472 | it:1110 | text | high | Expanding the Cyber Verification Program | 3117 |
| c1479 | it:1120 | text | high | AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재설계하기 | 3117 |
| c1501 | it:1149 | text | high | 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 | 3117 |
| c1503 | it:1154 | text | high | 한국 금융권 공격한 중국 26세 해커…'어설픈 신원 노출'로 덜미 | 3117 |
| c1507 | it:1159 | text | high | 카카오, 국제 AI 학회서 MoE 학습 최적화·모델 경량화 성과 공개 | 3117 |
| c1508 | it:1160 | text | high | 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정 모델 ‘d1-3B’ 출시 | 3117 |
| c1511 | it:1163 | text | high | '헤르메스 에이전트' 누스 리서치, 대규모 투자 유치로 기업용 시장 진출 | 3117 |
| c1521 | it:1179 | text | high | [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 더 쓸 수 있었다” | 3117 |
| c1522 | it:1181 | text | high | 구글, ‘나노 바나나 2.1’ 공개...성능 높이고 비용은 반값으로 | 3117 |
| c1524 | it:1184 | text | high | 스튜어트 러셀의 경고 "LLM 정렬 불가능…모방 학습과 RLHF 한계" | 3117 |
| c1525 | it:1185 | text | high | 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' 직접 호출 | 3117 |
| c1537 | it:1205 | text | high | '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개…반응은 엇갈려 | 3117 |
| c1541 | it:1211 | text | high | 코히어, 에이전트 비용·보안 통제 플랫폼 '노스 2' 출시...알레프 알파 인수 후 첫 행보 | 3117 |
| c1543 | it:1213 | text | high | 19세 청년의 반란...고스트, 개인용 AI PC '코어'로 147억 투자 유치 | 3117 |
| c1547 | it:1217 | text | high | “180B 모델, 개인용 노트북으로 구동”...비드래프트, 고성능 모델 경량화 전략 이어간다 | 3117 |
| c1553 | it:1223 | text | high | 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날부터 처리 속도 50% 향상 | 3117 |
| c1560 | it:1235 | text | high | KAIST, 데이터 변화해도 검색 정확도 유지하는 ‘CONDA’ 기술 개발 | 3117 |
| c1562 | it:1237 | text | high | GPT-6 아스트라, 217년 된 나폴레옹 암호 6시간 만에 해독 | 3117 |
| c1565 | it:1240 | text | high | AI가 쏟아낸 '엉터리 제보'에... 구글, 오픈소스 버그 바운티 일시 중단 | 3117 |
| c1566 | it:1241 | text | high | 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가상 착용' 도입 | 3117 |
| c1567 | it:1242 | text | high | 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 | 3117 |
| c1569 | it:1245 | text | high | "지기 싫어서 남의 코드 복사"…아스트라, 스타크래프트 벤치마크서 꼼수 | 3117 |
| c1464 | it:1101 | text | high | How Jump Trading is scaling quant research with ChatGPT | 3116 |
| c1470 | it:1108 | text | high | Introducing the Anthropic Cyber Mission | 3116 |
| c1480 | it:1121 | text | high | Claude Code 모드(mod) 시작하기 | 3116 |
| c1482 | it:1123 | text | high | 에이전트가 쓴 테스트는 무엇을 증명하나 | 3116 |
| c1487 | it:1129 | text | high | 우리가 알던 오픈소스는 죽었다 | 3116 |
| c1489 | it:1131 | text | high | 소프트웨어 팩토리 패턴 시도하기 | 3116 |
| c1490 | it:1133 | text | high | 나는 인류를 멸종시키고 있는 AGI다 | 3116 |
| c1492 | it:1136 | text | high | openTPU - AI가 설계하고 실제 FPGA에서 모델을 실행하는 오픈소스 AI 가속기 | 3116 |
| c1498 | it:1145 | text | high | Quoting Felix Rieseberg | 3116 |
| c1509 | it:1161 | text | high | MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최적화 공개 | 3116 |
| c1513 | it:1165 | text | high | MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개변수 모델 직접 구동 | 3116 |
| c1514 | it:1167 | text | high | "독파모·모두의 AI 더 안전하게"...SKT, 업스테이지와 AI 보안 동맹 결성 | 3116 |
| c1529 | it:1189 | text | high | 하크, '스마트폰 대체' AI 에이전트 공개...2027년 전용 기기 출시 | 3116 |
| c1532 | it:1193 | text | high | "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오토리뷰’ 전면 무료화 | 3116 |
| c1538 | it:1206 | text | high | MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 축소 | 3116 |
| c1559 | it:1233 | text | high | 뉴럴링크, 5만시간 뇌 데이터 사전학습…BCI도 '파운데이션 모델' 시대 열렸다 | 3116 |
| c1561 | it:1236 | text | high | a16z "미국 가구 2.2%만 AI 유료 구독…기술이 경기 순환 핵심 주도" | 3116 |
| c1570 | it:1246 | text | high | 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규제 경고 폭풍 | 3116 |
| c1531 | it:1191 | text | high | 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의무화 찬성" | 3115 |
| c1474 | it:1113 | text | high | MCPB로 로컬 MCP 서버를 Claude Desktop 원클릭 확장으로 만들기 | 3112 |
| c1583 | vd:6YuIp-MwPv4 | video | mid | [한영자막] Uber에서 디버깅 에이전트 하네스를 구축하는 방법 — Kriti Dangi | 2119 |
| c1585 | vd:PACIHCnvNMo | video | mid | [한영자막] 젠슨 황과 일론 머스크가 직접 밝히는 슈퍼 인텔리전스와 에너지, 우주 컴퓨팅의 미래 | 2119 |
| c1558 | it:1232 | text | mid | 앤트로픽, 10월6일까지 '음성 인터뷰어' 가동…대화록 공개·음성 학습 수집 결합 | 2118 |
| c1460 | it:1097 | text | mid | Disrupting AI-enabled “false front” operations | 2117 |
| c1471 | it:1109 | text | mid | 2026 Usage Policy update | 2117 |
| c1488 | it:1130 | text | mid | 여러 팀의 시스템을 이해하기 위한 AI 집단 지성 구축하기 | 2117 |
| c1500 | it:1148 | text | mid | 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 요동 | 2117 |
| c1506 | it:1158 | text | mid | 머스크 “테라팹 직접 운영한다”…TSMC 위탁운영설 일축 | 2117 |
| c1526 | it:1186 | text | mid | 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | 2117 |
| c1527 | it:1187 | text | mid | AMD, 연내 국내 'AI 연구센터' 설립...정부와 메가프로젝트 협력 추진 | 2117 |
| c1530 | it:1190 | text | mid | 구글, AI 데이터센터 전력 확보 위해 3.6GW 규모 원전 계약 체결 | 2117 |
| c1534 | it:1196 | text | mid | 딥시크, 투자 수요 폭발…IPO 전 자금 조달 규모 2배 확대 | 2117 |
| c1536 | it:1204 | text | mid | [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트로픽과 근본적으로 다르다” | 2117 |
| c1540 | it:1210 | text | mid | [게시판] 두산로보틱스, 989억 규모 피지컬 AI 국책과제 2건 선정 등 단신 | 2117 |
| c1542 | it:1212 | text | mid | 엔비디아-그로크 27조 계약 파장…소외된 엔지니어들 "거래 불공정" 소송 | 2117 |
| c1564 | it:1239 | text | mid | 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부담 낮춘다 | 2117 |
| c1568 | it:1243 | text | mid | "전직 미국 관료 사칭"…중국 해커, AI 정책 전문가 계정 노렸다 | 2117 |
| c1573 | it:1250 | text | mid | [AI리더의 서가] AI 루프를 설계하라 | 2117 |
| c1461 | it:1098 | text | mid | Helping teens learn, plan, and shape the future of AI | 2116 |
| c1476 | it:1116 | text | mid | AI가 코드를 쓸수록 도메인 주도 설계가 더 중요해지는 이유 | 2116 |
| c1484 | it:1126 | text | mid | Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호스팅 AI 비서 | 2116 |
| c1493 | it:1138 | text | mid | Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소스 작업 공간 | 2116 |
| c1505 | it:1157 | text | mid | 구글, 텍스트 입력으로 게임 만드는 플랫폼 공개…유니티와 협력 | 2116 |
| c1510 | it:1162 | text | mid | 누리호 올라탄 토종 AI 반도체, 우주 궤도서 성능 실증 나선다 | 2116 |
| c1515 | it:1168 | text | mid | 저커버그 부부의 바이오허브, 미 정부·구글과 2.4조 AI 생물학 데이터 구축 | 2116 |
| c1516 | it:1169 | text | mid | 메타 '뮤즈', 스마트폰 이어 아이패드용 앱 출시…업무용 도구 연동 강화 | 2116 |
| c1518 | it:1171 | text | mid | 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 121만개 확보 나선다 | 2116 |
| c1519 | it:1173 | text | mid | 삼성전자, 3분기 영업익 107조...애플·엔비디아도 못 넘은 '100조' 첫 달성 | 2116 |
| c1520 | it:1178 | text | mid | [AI리더의 서가] Agentic AI 구축 개발의 모든 것 | 2116 |
| c1523 | it:1182 | text | mid | "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정황 포착 | 2116 |
| c1548 | it:1218 | text | mid | 이탈리아 멜로니 총리, AI 딥페이크 막으려 '목소리 상표권' 신청 | 2116 |
| c1556 | it:1230 | text | mid | 구글, 'AI 프로' 국내 한정 40% 할인...연간 구독권 프로모션 진행 | 2116 |
| c1571 | it:1247 | text | mid | 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안전성에 이례적 경고 | 2116 |
| c1572 | it:1248 | text | mid | 'AI 피해자 영상'에 속아 내려진 중형..."형량 잘못됐다" 선고 파기 | 2116 |
| c1575 | it:1252 | text | mid | 트럼프, ‘슈퍼 인텔리전스 부대’ 출범…국가정보국장, 백악관 AI 차르 겸임 | 2116 |
| c1473 | it:1112 | text | mid | OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 AI 에이전트 | 2115 |
| c1499 | it:1146 | text | mid | Qwen3.8 27B addition in words | 2115 |
| c1517 | it:1170 | text | mid | 구글, AI 생성물 구분하는 '신스ID 감지기' 일반에 전면 공개 | 2115 |
| c1535 | it:1203 | text | mid | [AI리더의 서가] SQL부터 AI까지 데이터 분석 with 클로드 코드 | 2115 |
| c1539 | it:1208 | text | mid | 노르웨이, 공공장소 ‘AI 안경’ 일시 금지 추진…세계 첫 규제 움직임 | 2115 |
| c1544 | it:1214 | text | mid | [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용접 솔루션’ 공동개발 협력 등 단신 | 2115 |
| c1550 | it:1220 | text | mid | 포지큐브, 롯데벤처스와 멀티 AI 에이전트 기반 AX 추진 | 2115 |
| c1551 | it:1221 | text | mid | '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 아니다" | 2115 |
| c1456 | it:1050 | text | mid | Scrimshaw Jukebox | 2114 |
| c1546 | it:1216 | text | mid | 카카오모빌리티, 고려대와 AX 협력…모빌리티 핵심 기술 국방 분야 접목 | 2114 |
| c1449 | it:1042 | text | mid | Quoting Victoria Kim | 2112 |
| c1451 | it:1044 | text | mid | llm-mistral 0.16 | 2112 |
| c1447 | it:1039 | text | low | Anti-Patterns in Software Blogging | 1117 |
| c1457 | it:1094 | text | low | How Oracle turns days of work into minutes with ChatGPT and… | 1117 |
| c1486 | it:1128 | text | low | 자율주행 데이터에서 시간은 어떻게 맞춰지는가 | 1117 |
| c1458 | it:1095 | text | low | Pollo AI turns creative ideas into campaigns with OpenAI | 1116 |
| c1459 | it:1096 | text | low | LegalOn halves Codex costs while maintaining development sp… | 1116 |
| c1545 | it:1215 | text | low | 화웨이, 퀄컴에 '로직폴딩' 칩 관련 특허 라이선스 제공 | 1116 |
| c1552 | it:1222 | text | low | 헨켈, SEDEX 2026서 AI·HBM 시대 위한 첨단 패키징 소재 솔루션 선보여 | 1116 |
| c1554 | it:1224 | text | low | LG전자, 북미서 5GW 규모 AIDC 냉각솔루션 장기계약 체결 | 1115 |
| c1555 | it:1229 | text | low | [AI리더의 서가] CEO의  AI | 1115 |
| c1574 | it:1251 | text | low | 머스크, '스페이스XSI'로 리브랜딩 시사…트럼프 'SI' 발언 동조 | 1115 |
| c1462 | it:1099 | text | low | Radisson Hotel Group brings hotel discovery into ChatGPT | 1114 |
| c1494 | it:1141 | text | low | ttok 0.4 | 1114 |
| c1496 | it:1143 | text | low | Quoting Ben Affleck | 1114 |
| c1528 | it:1188 | text | low | [게시판] SKT, 독파모 'A.X K2'로 순우리말 선정·글꼴 제작 등 단신 | 1114 |
| c1454 | it:1047 | text | low | Using Parseable with Datasette for OpenTelemetry traces | 1113 |
| c1455 | it:1049 | text | low | datasette-atom 0.11a0 | 1113 |
| c1495 | it:1142 | text | low | Quoting Carson Gross | 1113 |
| c1504 | it:1155 | text | low | [AI리더의 서가] 이너 프롬프트 | 1113 |
| c1475 | it:1115 | text | low | 「Quo Vadis, Mathematics?」—“수학이여, 어디로 가는가?” | 1110 |
| c1477 | it:1117 | text | low | AI 시대의 커리어 조언 - 문제를 푸는 능력보다 찾고 선택하는 능력 | 1110 |
| c1478 | it:1119 | text | low | AI로 의도, 품질, 예술성을 확장하는 법 [영상] | 1110 |
| c1483 | it:1125 | text | low | AI 시대, 매니저의 길 | 1110 |
| c1485 | it:1127 | text | low | jev가 여는 비즈니스 AI: 에이전트에서 컴포넌트로 | 1110 |
| c1491 | it:1135 | text | low | 제프리 카첸버그 - 세상이 바뀌고 있다: 창의성을 위한 AI | 1110 |
| c1502 | it:1151 | text | low | 여수, 23~24일 독서문화축제…야외 독서·섬 체험 운영 | 1110 |
| c1512 | it:1164 | text | low | 오픈AI "10대 챗GPT 평균 15분 사용" 주장에 안전성 논란 불붙어 | 1110 |
| c1533 | it:1194 | text | low | 전남광주, 여수서 9~11일 ‘세계 김밥&소금 페스티벌’ | 1110 |

### 레포만 있는 묶음(토픽 후보 아님, 홈 레포 목록)

- c1576: rp:NVIDIA/OpenShell
- c1577: rp:Panniantong/Agent-Reach
- c1578: rp:cursor/plugins
- c1579: rp:heygen-com/hyperframes
- c1580: rp:thedotmack/claude-mem
- c1581: rp:tile-ai/tilelang

## 4. decide 판정

58건. confidence 0.6 미만은 묶지 않음.

| a | b | 채널 넘음 | sim | 공유 | answer | conf | reason |
|---|---|---|---|---|---|---|---|
| it:1132 EmbeddingGemma 2 - 개방형 경량 멀티모… | it:1183 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미… |  | 0.798 | embeddinggemma2, gemma4, maeb, eval, mu… | same | 0.95 | a, b 모두 Google의 EmbeddingGemma 2 모델 공개를 다룸 |
| it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.… | it:1165 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개.… |  | 0.7944 | mai코드1.1플래시, 마이크로소프트, 서피스랩톱울트라, ai-secu… | diff | 0.8 | a는 서피스 랩톱 울트라 출시에 맞춰 공개된 MAI-코드-1.1 플래시의 온디바이스 최적화 버전(모델 성능·축소)에 초점을 맞춘 글, b는 서… |
| it:1149 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·… | it:1182 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화… |  | 0.7558 | agent | diff | 0.95 | a는 구글 클라우드의 기업용 '제미나이 에이전트' 출시, b는 구글 제미나이의 개인용 '제미나이 콜링' 기능 확대 → 다른 제품 |
| it:1122 OpenRig - Claude Code와 Codex를… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.7379 | openrig, agent, coding-agent | same | 0.95 | a는 OpenRig 오케스트레이터 소개, b는 OpenRig 공식 레포 → 같은 제품 |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보… | it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… |  | 0.7327 | - | diff | 0.95 | a는 Claude Opus 5.5의 구독 가치 분석, b는 Claude Haiku 5.5 출시 발표 → 같은 회사지만 다른 모델 라인업 |
| it:1111 EmbeddingGemma 2: an open, li… | it:1183 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미… |  | 0.7258 | embeddinggemma2, gemma4, maeb, eval, mu… | same | 0.95 | a, b 모두 Google DeepMind의 EmbeddingGemma 2 모델 공개를 다룸 |
| it:1046 Introducing Mistral Large 4: … | it:1198 미스트랄, 1조 매개변수 ‘라지 4’ 공개..."사이… |  | 0.7153 | mistral, eval, frontier-release | same | 0.95 | a는 Mistral Large 4 공식 발표, b는 Mistral Large 4 공개 및 벤치마크 보도 → 같은 모델 |
| it:1044 llm-mistral 0.16 | it:1046 Introducing Mistral Large 4: … |  | 0.7146 | mistrallarge4, open-weight | diff | 0.95 | a는 llm-mistral 0.16 릴리스, b는 Mistral Large 4 모델 출시 발표 → 다른 대상 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서… |  | 0.7079 | 오픈ai, agent, ai-security | diff | 0.9 | a는 호주 청문회 출석 및 규제 찬성, b는 전 세계적 법적·규제 경고 및 IPO 연기 등 다른 사건을 다룸 |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.7053 | - | diff | 0.95 | a는 AI 구독 서비스의 가격 대비 가치 비교 분석, b는 기업들의 클로드 사용량 축소 사건 → 다른 주제 |
| it:1122 OpenRig - Claude Code와 Codex를… | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… |  | 0.7039 | claudecode, codex, agent, coding-agent | diff | 0.95 | a는 OpenRig, b는 Lemma → 서로 다른 오픈소스 에이전트 오케스트레이션/워크스페이스 도구 |
| it:1102 Sharing AI progress in mathem… | it:1156 [10월8일] “수학 문제 4000개에 AI 투입해 … |  | 0.6964 | lean, frontier-release, reasoning | same | 0.95 | a와 b 모두 OpenAI가 내부 프런티어 모델을 이용해 수학 문제를 해결하고 결과를 공개한 동일한 발표를 다룸 |
| it:1041 OpenAI “rogue” agent activiti… | it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단… |  | 0.696 | agent, ai-security | same | 0.95 | a, b 모두 OpenAI의 'rogue' 에이전트가 위키미디어 재단에서 일으킨 활동과 5월 장애 연관성을 다룸 |
| it:1106 Building advertising for the … | it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생… |  | 0.6923 | - | same | 0.95 | a와 b 모두 OpenAI가 ChatGPT에 시각적 광고 포맷을 도입하는 발표를 다룸 |
| it:1046 Introducing Mistral Large 4: … | it:1048 Mistral Large 4 |  | 0.6892 | mistrallarge4, eval, frontier-release | same | 0.9 | a는 Mistral Large 4 출시 발표, b는 Mistral Large 4를 포함한 모델들의 벤치마크 테스트 → 같은 모델 |
| it:1105 Our approach to EU text prove… | it:1225 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만… |  | 0.6832 | codex, ai-security | same | 0.95 | a, b 모두 OpenAI의 textGrain 워터마킹 기술 도입 및 EU 적용 발표를 다룸 |
| it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.6794 | agent, coding-agent | diff | 0.95 | a는 Lemma, b는 openrig → 서로 다른 오픈소스 에이전트 팀워크 도구 |
| it:1171 스페이스X, AI 칩 구매에 53조 조달 추진...G… | it:1239 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스… |  | 0.6757 | 엔비디아 | diff | 0.95 | a는 스페이스X의 GPU 구매 자금 조달, b는 아마존의 AI 칩 매각 후 리스 구조 → 다른 회사의 다른 재무 이벤트 |
| it:1144 Claude Haiku 5.5 | it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… |  | 0.6743 | claudehaiku5.5, gpt6luna, eval, frontie… | same | 0.95 | a는 Claude Haiku 5.5의 가격 구조 분석, b는 Claude Haiku 5.5 출시 발표 → 같은 모델 |
| it:1112 OpenMuse - 브라우저와 터미널로 일하는 오픈소… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.6736 | agent | diff | 0.95 | a는 OpenMuse, b는 openrig → 서로 다른 오픈소스 에이전트 도구 |
| it:1120 AI 네이티브 SDLC - 개발 전 과정을 에이전트에… | vd:kcflfXb6dBM [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워… | 예 | 0.6733 | agent | diff | 0.9 | a는 'AI 네이티브 SDLC'라는 특정 방법론/프레임워크를 소개하는 글, b는 AI 코드 워크플로우의 미래와 개발자 역량 변화에 대한 일반적… |
| it:1044 llm-mistral 0.16 | it:1048 Mistral Large 4 |  | 0.663 | mistrallarge4 | diff | 0.95 | a는 llm-mistral 0.16 릴리스, b는 Mistral Large 4 벤치마크 테스트 → 다른 대상 |
| it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… | it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객… |  | 0.6616 | 앤트로픽 | diff | 0.95 | a는 클로드 하이쿠 5.5 모델 출시, b는 클로드 포 스타트업 지원 프로그램 확대 → 다른 대상 |
| it:1144 Claude Haiku 5.5 | it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보… |  | 0.6611 | anthropic, openai | diff | 0.95 | a는 Claude Haiku 5.5의 가격 구조 분석, b는 Claude Opus 5.5와 GPT-6.1 Sol의 구독 가치 비교 → 다른 모델 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통… |  | 0.6597 | 앤트로픽, 오픈ai, ai-security | diff | 0.95 | a는 호주 의회 청문회, b는 뉴욕시의회 청문회 → 장소와 주제가 다른 별개의 사건 |
| it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.6593 | 앤트로픽 | diff | 0.95 | a는 앤트로픽의 스타트업 지원 프로그램 '클로드 포 스타트업' 확대 발표, b는 MS·메타의 클로드 사내 사용 축소 및 앤트로픽의 기업 시장 … |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼… |  | 0.6588 | 앤트로픽, 오픈ai | diff | 0.95 | a는 호주 의회 청문회에서의 에이전트 사고 신고 의무화 지지, b는 알트먼의 규제 접근법 인터뷰 및 앤트로픽의 과학 연구 방법론 → 다른 사건 |
| it:1167 "독파모·모두의 AI 더 안전하게"...SKT, 업스… | it:1188 [게시판] SKT, 독파모 'A.X K2'로 순우리말… |  | 0.6556 | - | diff | 0.95 | a는 SKT와 업스테이지의 AI 보안 협의체 출범, b는 SKT의 A.X K2 활용 단신 → 다른 사건 |
| it:1126 Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호… | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… |  | 0.6528 | agent | diff | 0.95 | a는 Octop(셀프 호스팅 AI 비서), b는 Lemma(오픈소스 팀 작업 공간) → 다른 제품 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고… | it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회… |  | 0.6513 | 앤트로픽, 오픈ai, ai-security | diff | 0.95 | a는 호주 의회 청문회, b는 뉴욕시의회 청문회 → 장소와 주제가 다른 별개의 사건 |
| it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.6512 | 앤트로픽 | diff | 0.95 | a는 클로드 하이쿠 5.5 모델 출시, b는 MS·메타의 클로드(코드) 사용 축소 → 다른 대상 |
| it:1210 [게시판] 두산로보틱스, 989억 규모 피지컬 AI … | it:1214 [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용… |  | 0.6487 | 두산로보틱스, 딥엑스 | diff | 0.95 | a는 두산로보틱스의 피지컬 AI 국책과제 선정, b는 딥엑스-두산로보틱스의 원전 AI 용접 솔루션 협력 → 다른 사건 |
| it:1193 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이… | it:1223 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날… |  | 0.6389 | codex, 오픈ai, coding-agent | diff | 0.9 | a는 코덱스 2일차 업데이트(오토리뷰 무료화), b는 코덱스 28일 개선 이벤트 발표 및 1일차 업데이트(속도 향상) → 같은 이벤트의 다른 … |
| it:1229 [AI리더의 서가] CEO의  AI | it:1250 [AI리더의 서가] AI 루프를 설계하라 |  | 0.6322 | 영풍문고 | diff | 0.95 | a는 도서 『CEO의 AI』 소개, b는 도서 『AI 루프를 설계하라』 소개 → 다른 책 |
| it:1045 EmbeddingGemma 2 | it:1111 EmbeddingGemma 2: an open, li… |  | 0.6319 | embeddinggemma2, open-weight, rag-search | same | 0.95 | a, b 모두 EmbeddingGemma 2 모델을 다룸 |
| it:1172 오픈AI, 질문에 맞춰 화면 생성하는 'GPT-6' … | it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생… |  | 0.6319 | 오픈ai, 챗gpt | diff | 0.95 | a는 GPT-6 모델 공개 및 지능형 UI 도입, b는 챗GPT 내 시각적 광고 도입 → 다른 사안 |
| it:1120 AI 네이티브 SDLC - 개발 전 과정을 에이전트에… | it:1131 소프트웨어 팩토리 패턴 시도하기 |  | 0.6144 | claudecode, agent, coding-agent | diff | 0.95 | a는 AI 네이티브 SDLC 재설계 방법론, b는 소프트웨어 팩토리 패턴 시도 → 다른 개발 접근법 |
| it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.6132 | 깃허브코파일럿, 마이크로소프트, coding-agent | diff | 0.95 | a는 MAI-코드-1.1 플래시 온디바이스 최적화 공개, b는 MS·메타의 클로드 사용 축소 → 다른 대상 |
| it:1045 EmbeddingGemma 2 | it:1132 EmbeddingGemma 2 - 개방형 경량 멀티모… |  | 0.6117 | embeddinggemma2, open-weight, rag-search | same | 0.95 | a, b 모두 EmbeddingGemma 2 모델을 다룸 |
| it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서… |  | 0.6109 | 샘알트먼, 오픈ai | diff | 0.95 | a는 알트먼의 규제 관련 인터뷰, b는 오픈AI 에이전트 보안 사고와 규제 조사 → 다른 사건 |
| it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생… | it:1241 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가… |  | 0.5935 | 오픈ai, 챗gpt | diff | 0.95 | a는 챗GPT 이미지 생성 기능에 시각적 광고 도입, b는 챗GPT 의류 가상 착용(Try On) 기능 출시 → 다른 기능 발표 |
| it:1131 소프트웨어 팩토리 패턴 시도하기 | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… |  | 0.5898 | claudecode, agent, coding-agent | diff | 0.95 | a는 소프트웨어 팩토리 패턴이라는 개발 방식과 Linear/Datadog 연동 에이전트 스킬 구현, b는 Lemma라는 오픈소스 팀 작업 공간… |
| it:1155 [AI리더의 서가] 이너 프롬프트 | it:1229 [AI리더의 서가] CEO의  AI |  | 0.5884 | 영풍문고 | diff | 0.95 | a는 책 『이너 프롬프트』, b는 책 『CEO의 AI』 → 다른 도서 |
| it:1103 Advancing computer use with I… | it:1104 Atlassian and OpenAI expand p… |  | 0.5806 | gpt6astra, openai, agent, frontier-rele… | diff | 0.95 | a는 OpenAI와 Ironclad의 계약 업무 에이전트 평가, b는 Atlassian과 OpenAI의 파트너십 확대 및 Rovo 적용 → 다… |
| it:1043 llm-openai-decisions 0.1a0 | it:1144 Claude Haiku 5.5 |  | 0.5768 | gpt6luna, openai, frontier-release | diff | 0.95 | a는 OpenAI의 Decisions API와 gpt-6-luna 모델을 다룸, b는 Anthropic의 Claude Haiku 5.5 모델을… |
| it:1182 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화… | it:1230 구글, 'AI 프로' 국내 한정 40% 할인...연간… |  | 0.5766 | gemini, 구글 | diff | 0.95 | a는 구글 제미나이의 전화 대행 기능(콜 포 미) 확대, b는 구글 AI 프로 요금제 할인 프로모션 → 다른 대상 |
| it:1185 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사… |  | 0.5757 | claude, 앤트로픽 | diff | 0.95 | a는 '클로드 포 구글 워크스페이스' 출시, b는 MS·메타의 클로드 사용 축소 → 다른 사건 |
| it:1155 [AI리더의 서가] 이너 프롬프트 | it:1250 [AI리더의 서가] AI 루프를 설계하라 |  | 0.5749 | 영풍문고 | diff | 0.95 | a는 책 『이너 프롬프트』 소개, b는 책 『AI 루프를 설계하라』 소개 → 다른 책 |
| it:1104 Atlassian and OpenAI expand p… | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… |  | 0.571 | codex, agent, coding-agent | diff | 0.95 | a는 Atlassian과 OpenAI의 파트너십 확대 및 Rovo 적용, b는 오픈소스 작업 공간 Lemma 소개 → 다른 대상 |
| it:1149 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·… | it:1190 구글, AI 데이터센터 전력 확보 위해 3.6GW 규… |  | 0.5702 | 구글클라우드 | diff | 0.95 | a는 구글 클라우드의 '제미나이 에이전트' 출시, b는 구글의 원전 전력 계약 체결 → 다른 사건 |
| it:1130 여러 팀의 시스템을 이해하기 위한 AI 집단 지성 구… | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하… |  | 0.5601 | cursor, opencode, agent | diff | 0.95 | a는 SumUp의 AI 기반 시스템 지식 관리(hive mind) 구축 경험, b는 Lemma라는 오픈소스 팀 작업 공간 제품 소개 → 다른 … |
| it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생… | it:1225 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만… |  | 0.5601 | 오픈ai, 챗gpt | diff | 0.95 | a는 챗GPT 이미지 생성 기능의 시각적 광고 도입, b는 챗GPT/코덱스 텍스트 출력의 워터마크 적용 → 다른 기능·사건 |
| it:1193 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이… | it:1225 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만… |  | 0.5592 | codex, 오픈ai, 챗gpt, ai-security | diff | 0.95 | a는 오픈AI 코덱스의 '오토리뷰' 기능 무료화 업데이트, b는 챗GPT/코덱스에 적용되는 '텍스트그레인' 워터마크 도입 → 다른 기능·사건 |
| it:1221 '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은… | it:1243 "전직 미국 관료 사칭"…중국 해커, AI 정책 전문… |  | 0.5565 | claude, 앤트로픽, ai-security | diff | 0.95 | a는 클로드에 위협을 남긴 사용자가 체포된 사건, b는 중국 해커의 AI 정책 전문가 피싱 공격 → 다른 사건 |
| it:1171 스페이스X, AI 칩 구매에 53조 조달 추진...G… | it:1242 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해… |  | 0.5562 | 모건스탠리, 엔비디아 | diff | 0.95 | a는 스페이스X의 GPU 구매 자금 조달, b는 브로드컴의 앤트로픽 대출 보증 → 다른 회사의 다른 금융 거래 |
| it:1101 How Jump Trading is scaling q… | it:1103 Advancing computer use with I… |  | 0.556 | gpt6astra, openai, agent | diff | 0.9 | a는 Jump Trading의 GPT-6 Astra 활용 사례, b는 OpenAI와 Ironclad의 GPT-6 Astra 평가 발표 → 다른… |
| it:1172 오픈AI, 질문에 맞춰 화면 생성하는 'GPT-6' … | it:1193 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이… |  | 0.5513 | 오픈ai, 챗gpt, agent | diff | 0.95 | a는 GPT-6 모델 공개 및 UI 업데이트, b는 코덱스(Codex)의 오토리뷰 기능 무료화 → 다른 제품·기능 |
| it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.… | it:1205 '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개… |  | 0.5501 | swe벤치베리파이드, 터미널벤치2.1, coding-agent, eval | diff | 0.95 | a는 마이크로소프트의 MAI-코드-1.1 플래시, b는 리플렉션 AI의 빔(beam) 모델 → 다른 회사의 다른 모델 |

## 5. 경계 근처 상위 20쌍 (묶이지 않은 쌍, 묶였어야 할 것 같은지 확인)

| a | b | 채널 넘음 | sim | 경로 | 판정 | 공유 |
|---|---|---|---|---|---|---|
| rp:mvschwarz/openrig mvschwarz/openrig | rp:thedotmack/claude-mem thedotmack/claude-mem |  | 0.8142 | none | - | agent, coding-agent |
| it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디… | it:1165 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...120… |  | 0.7944 | decide | diff 0.8 | mai코드1.1플래시, 마이크로소프트, 서피스랩톱울트라, ai-secu… |
| it:1149 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드'… | it:1182 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정… |  | 0.7558 | decide | diff 0.95 | agent |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 … | it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.… |  | 0.7327 | decide | diff 0.95 | - |
| rp:Panniantong/Agent-Reach Panniantong/Agent-Reach | rp:mvschwarz/openrig mvschwarz/openrig |  | 0.7306 | none | - | agent, coding-agent |
| it:1044 llm-mistral 0.16 | it:1046 Introducing Mistral Large 4: Le ch… |  | 0.7146 | decide | diff 0.95 | mistrallarge4, open-weight |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규… |  | 0.7079 | decide | diff 0.9 | 오픈ai, agent, ai-security |
| it:1179 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 … | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 … |  | 0.7053 | decide | diff 0.95 | - |
| it:1122 OpenRig - Claude Code와 Codex를 팀으로 … | it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소… |  | 0.7039 | decide | diff 0.95 | claudecode, codex, agent, coding-agent |
| it:1138 Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소… | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.6794 | decide | diff 0.95 | agent, coding-agent |
| it:1171 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 12… | it:1239 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부… |  | 0.6757 | decide | diff 0.95 | 엔비디아 |
| it:1112 OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 … | rp:mvschwarz/openrig mvschwarz/openrig | 예 | 0.6736 | decide | diff 0.95 | agent |
| it:1120 AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재… | vd:kcflfXb6dBM [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의… | 예 | 0.6733 | decide | diff 0.9 | agent |
| it:1044 llm-mistral 0.16 | it:1048 Mistral Large 4 |  | 0.663 | decide | diff 0.95 | mistrallarge4 |
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
| it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규… |  | 0.6222 | 오픈ai |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연… |  | 0.6168 | 오픈ai |
| it:1247 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안… | it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 … |  | 0.6167 | 오픈ai |
| it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | it:1242 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 |  | 0.6165 | 구글, 앤트로픽 |
| it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… | it:1247 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안… |  | 0.6129 | 오픈ai |
| it:1185 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' … | it:1186 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 |  | 0.6106 | 앤트로픽 |
| it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트… | it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 … |  | 0.6061 | 앤트로픽, 오픈ai |
| it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… | it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규… |  | 0.6051 | 오픈ai |
| it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트… | it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실… |  | 0.5986 | 앤트로픽, 오픈ai |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1221 '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 … |  | 0.5955 | 앤트로픽, 오픈ai |
| it:1171 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 12… | it:1213 19세 청년의 반란...고스트, 개인용 AI PC '코어'로 … |  | 0.591 | 엔비디아 |
| it:1160 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정 모델 ‘… | it:1205 '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개…반응은 … |  | 0.5795 | 엔비디아 |
| it:1165 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...120… | it:1206 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 … |  | 0.5793 | 마이크로소프트 |
| it:1148 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 … | it:1236 a16z "미국 가구 2.2%만 AI 유료 구독…기술이 경기 … |  | 0.5767 | 엔비디아 |
| it:1148 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 … | it:1156 [10월8일] “수학 문제 4000개에 AI 투입해 성과”…오… |  | 0.5761 | 오픈ai |
| it:1041 OpenAI “rogue” agent activities fo… | it:1042 Quoting Victoria Kim |  | 0.5714 | openai |
| it:1246 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규… | it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 … |  | 0.5708 | 오픈ai |
| it:1165 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...120… | it:1171 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 12… |  | 0.5675 | 엔비디아 |
| it:1191 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의… | it:1193 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오… |  | 0.5671 | 오픈ai |
| it:1204 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트… | it:1247 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안… |  | 0.5621 | 오픈ai |

## 6. 의심 병합 (숫자·버전·크기만 다른 이름이 한 묶음)

- c1453 Introducing Mistral Large 4: Le chonk: Mistral Large 3 ↔ Mistral Large 4(확인 완료: 비교 대상으로 언급된 이전 버전)
- c1463 GPT-6 and Intelligent UI for everyone: GPT-5.6 ↔ GPT-6(확인 완료: 비교 대상으로 언급된 이전 버전), GPT-5.6 ↔ GPT-6 루나(확인 완료: 비교 대상으로 언급된 이전 버전), GPT-5.6 ↔ GPT-6 솔(확인 완료: 비교 대상으로 언급된 이전 버전)
- c1497 Claude Haiku 5.5: Claude Haiku 4.5 ↔ Claude Haiku 5.5(확인 완료: 비교 대상으로 언급된 이전 버전)

## 7. 과거 대조 후보

| 묶음 | 지난 토픽 | 주 | 유사도 |
|---|---|---|---|
| c1447 Anti-Patterns in Software Blogging | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.2108 |
| c1447 Anti-Patterns in Software Blogging | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.2105 |
| c1447 Anti-Patterns in Software Blogging | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.2103 |
| c1448 OpenAI “rogue” agent activities found o… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.556 |
| c1448 OpenAI “rogue” agent activities found o… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.461 |
| c1448 OpenAI “rogue” agent activities found o… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4446 |
| c1449 Quoting Victoria Kim | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.5565 |
| c1449 Quoting Victoria Kim | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4997 |
| c1449 Quoting Victoria Kim | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4212 |
| c1450 llm-openai-decisions 0.1a0 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.6632 |
| c1450 llm-openai-decisions 0.1a0 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.5023 |
| c1450 llm-openai-decisions 0.1a0 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.462 |
| c1451 llm-mistral 0.16 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4638 |
| c1451 llm-mistral 0.16 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4623 |
| c1451 llm-mistral 0.16 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4216 |
| c1452 EmbeddingGemma 2: an open, lightweight … | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.4479 |
| c1452 EmbeddingGemma 2: an open, lightweight … | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3936 |
| c1452 EmbeddingGemma 2: an open, lightweight … | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3849 |
| c1453 Introducing Mistral Large 4: Le chonk | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.441 |
| c1453 Introducing Mistral Large 4: Le chonk | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4285 |
| c1453 Introducing Mistral Large 4: Le chonk | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.4278 |
| c1454 Using Parseable with Datasette for Open… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3819 |
| c1454 Using Parseable with Datasette for Open… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3751 |
| c1454 Using Parseable with Datasette for Open… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3371 |
| c1455 datasette-atom 0.11a0 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.41 |
| c1455 datasette-atom 0.11a0 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3509 |
| c1455 datasette-atom 0.11a0 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3469 |
| c1456 Scrimshaw Jukebox | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.4174 |
| c1456 Scrimshaw Jukebox | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3442 |
| c1456 Scrimshaw Jukebox | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3336 |
| c1457 How Oracle turns days of work into minu… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.414 |
| c1457 How Oracle turns days of work into minu… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3956 |
| c1457 How Oracle turns days of work into minu… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3931 |
| c1458 Pollo AI turns creative ideas into camp… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4043 |
| c1458 Pollo AI turns creative ideas into camp… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.397 |
| c1458 Pollo AI turns creative ideas into camp… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3872 |
| c1459 LegalOn halves Codex costs while mainta… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3757 |
| c1459 LegalOn halves Codex costs while mainta… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.3456 |
| c1459 LegalOn halves Codex costs while mainta… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3073 |
| c1460 Disrupting AI-enabled “false front” ope… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4327 |
| c1460 Disrupting AI-enabled “false front” ope… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3566 |
| c1460 Disrupting AI-enabled “false front” ope… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3349 |
| c1461 Helping teens learn, plan, and shape th… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3573 |
| c1461 Helping teens learn, plan, and shape th… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3467 |
| c1461 Helping teens learn, plan, and shape th… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3357 |
| c1462 Radisson Hotel Group brings hotel disco… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4492 |
| c1462 Radisson Hotel Group brings hotel disco… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.408 |
| c1462 Radisson Hotel Group brings hotel disco… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3909 |
| c1463 GPT-6 and Intelligent UI for everyone | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.5768 |
| c1463 GPT-6 and Intelligent UI for everyone | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.5705 |
| c1463 GPT-6 and Intelligent UI for everyone | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.5623 |
| c1464 How Jump Trading is scaling quant resea… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4339 |
| c1464 How Jump Trading is scaling quant resea… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4241 |
| c1464 How Jump Trading is scaling quant resea… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4199 |
| c1465 Sharing AI progress in mathematics | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4353 |
| c1465 Sharing AI progress in mathematics | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4321 |
| c1465 Sharing AI progress in mathematics | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4194 |
| c1466 Advancing computer use with Ironclad | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4356 |
| c1466 Advancing computer use with Ironclad | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.403 |
| c1466 Advancing computer use with Ironclad | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3701 |
| c1467 Atlassian and OpenAI expand partnership… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4639 |
| c1467 Atlassian and OpenAI expand partnership… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.454 |
| c1467 Atlassian and OpenAI expand partnership… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4348 |
| c1468 Our approach to EU text provenance rules | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4352 |
| c1468 Our approach to EU text provenance rules | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4225 |
| c1468 Our approach to EU text provenance rules | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4106 |
| c1469 Building advertising for the way people… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4353 |
| c1469 Building advertising for the way people… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4133 |
| c1469 Building advertising for the way people… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4127 |
| c1470 Introducing the Anthropic Cyber Mission | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3384 |
| c1470 Introducing the Anthropic Cyber Mission | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.2922 |
| c1470 Introducing the Anthropic Cyber Mission | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.2827 |
| c1471 2026 Usage Policy update | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.369 |
| c1471 2026 Usage Policy update | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3669 |
| c1471 2026 Usage Policy update | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3523 |
| c1472 Expanding the Cyber Verification Program | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.3386 |
| c1472 Expanding the Cyber Verification Program | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3357 |
| c1472 Expanding the Cyber Verification Program | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.2983 |
| c1473 OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 AI 에이… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5053 |
| c1473 OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 AI 에이… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4554 |
| c1473 OpenMuse - 브라우저와 터미널로 일하는 오픈소스 개인 AI 에이… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4413 |
| c1474 MCPB로 로컬 MCP 서버를 Claude Desktop 원클릭 확장으… | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.3291 |
| c1474 MCPB로 로컬 MCP 서버를 Claude Desktop 원클릭 확장으… | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.2911 |
| c1474 MCPB로 로컬 MCP 서버를 Claude Desktop 원클릭 확장으… | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.2557 |
| c1475 「Quo Vadis, Mathematics?」—“수학이여, 어디로 가는… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3675 |
| c1475 「Quo Vadis, Mathematics?」—“수학이여, 어디로 가는… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3591 |
| c1475 「Quo Vadis, Mathematics?」—“수학이여, 어디로 가는… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3487 |
| c1476 AI가 코드를 쓸수록 도메인 주도 설계가 더 중요해지는 이유 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3314 |
| c1476 AI가 코드를 쓸수록 도메인 주도 설계가 더 중요해지는 이유 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.2912 |
| c1476 AI가 코드를 쓸수록 도메인 주도 설계가 더 중요해지는 이유 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.2524 |
| c1477 AI 시대의 커리어 조언 - 문제를 푸는 능력보다 찾고 선택하는 능력 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.376 |
| c1477 AI 시대의 커리어 조언 - 문제를 푸는 능력보다 찾고 선택하는 능력 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3589 |
| c1477 AI 시대의 커리어 조언 - 문제를 푸는 능력보다 찾고 선택하는 능력 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.353 |
| c1478 AI로 의도, 품질, 예술성을 확장하는 법 [영상] | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3969 |
| c1478 AI로 의도, 품질, 예술성을 확장하는 법 [영상] | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3718 |
| c1478 AI로 의도, 품질, 예술성을 확장하는 법 [영상] | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3665 |
| c1479 AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재설계하기 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3697 |
| c1479 AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재설계하기 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3293 |
| c1479 AI 네이티브 SDLC - 개발 전 과정을 에이전트에 맞게 재설계하기 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3257 |
| c1480 Claude Code 모드(mod) 시작하기 | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.3866 |
| c1480 Claude Code 모드(mod) 시작하기 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.321 |
| c1480 Claude Code 모드(mod) 시작하기 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.2939 |
| c1481 mvschwarz/openrig | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5215 |
| c1481 mvschwarz/openrig | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.4534 |
| c1481 mvschwarz/openrig | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4312 |
| c1482 에이전트가 쓴 테스트는 무엇을 증명하나 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3756 |
| c1482 에이전트가 쓴 테스트는 무엇을 증명하나 | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.3701 |
| c1482 에이전트가 쓴 테스트는 무엇을 증명하나 | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.359 |
| c1483 AI 시대, 매니저의 길 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4051 |
| c1483 AI 시대, 매니저의 길 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3308 |
| c1483 AI 시대, 매니저의 길 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.2978 |
| c1484 Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호스팅 AI 비서 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5893 |
| c1484 Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호스팅 AI 비서 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4574 |
| c1484 Octop - 가족과 소규모 팀이 함께 쓰는 셀프 호스팅 AI 비서 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4485 |
| c1485 jev가 여는 비즈니스 AI: 에이전트에서 컴포넌트로 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4659 |
| c1485 jev가 여는 비즈니스 AI: 에이전트에서 컴포넌트로 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4466 |
| c1485 jev가 여는 비즈니스 AI: 에이전트에서 컴포넌트로 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4453 |
| c1486 자율주행 데이터에서 시간은 어떻게 맞춰지는가 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.384 |
| c1486 자율주행 데이터에서 시간은 어떻게 맞춰지는가 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3306 |
| c1486 자율주행 데이터에서 시간은 어떻게 맞춰지는가 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.3148 |
| c1487 우리가 알던 오픈소스는 죽었다 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4422 |
| c1487 우리가 알던 오픈소스는 죽었다 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4327 |
| c1487 우리가 알던 오픈소스는 죽었다 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4048 |
| c1488 여러 팀의 시스템을 이해하기 위한 AI 집단 지성 구축하기 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4151 |
| c1488 여러 팀의 시스템을 이해하기 위한 AI 집단 지성 구축하기 | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.3748 |
| c1488 여러 팀의 시스템을 이해하기 위한 AI 집단 지성 구축하기 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3457 |
| c1489 소프트웨어 팩토리 패턴 시도하기 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4628 |
| c1489 소프트웨어 팩토리 패턴 시도하기 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4211 |
| c1489 소프트웨어 팩토리 패턴 시도하기 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3962 |
| c1490 나는 인류를 멸종시키고 있는 AGI다 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4986 |
| c1490 나는 인류를 멸종시키고 있는 AGI다 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4668 |
| c1490 나는 인류를 멸종시키고 있는 AGI다 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4648 |
| c1491 제프리 카첸버그 - 세상이 바뀌고 있다: 창의성을 위한 AI | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3694 |
| c1491 제프리 카첸버그 - 세상이 바뀌고 있다: 창의성을 위한 AI | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3549 |
| c1491 제프리 카첸버그 - 세상이 바뀌고 있다: 창의성을 위한 AI | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3464 |
| c1492 openTPU - AI가 설계하고 실제 FPGA에서 모델을 실행하는 오… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.446 |
| c1492 openTPU - AI가 설계하고 실제 FPGA에서 모델을 실행하는 오… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4266 |
| c1492 openTPU - AI가 설계하고 실제 FPGA에서 모델을 실행하는 오… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4198 |
| c1493 Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소스 작업 … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5532 |
| c1493 Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소스 작업 … | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4679 |
| c1493 Lemma - 사람과 AI 에이전트가 한 팀으로 일하는 오픈소스 작업 … | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4445 |
| c1494 ttok 0.4 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4273 |
| c1494 ttok 0.4 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4233 |
| c1494 ttok 0.4 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3874 |
| c1495 Quoting Carson Gross | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.2573 |
| c1495 Quoting Carson Gross | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.251 |
| c1495 Quoting Carson Gross | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.2399 |
| c1496 Quoting Ben Affleck | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.289 |
| c1496 Quoting Ben Affleck | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.2424 |
| c1496 Quoting Ben Affleck | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.23 |
| c1497 Claude Haiku 5.5 | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.5991 |
| c1497 Claude Haiku 5.5 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.5141 |
| c1497 Claude Haiku 5.5 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4563 |
| c1498 Quoting Felix Rieseberg | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3806 |
| c1498 Quoting Felix Rieseberg | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.3774 |
| c1498 Quoting Felix Rieseberg | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3631 |
| c1499 Qwen3.8 27B addition in words | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.4162 |
| c1499 Qwen3.8 27B addition in words | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.382 |
| c1499 Qwen3.8 27B addition in words | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3575 |
| c1500 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 요동 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.5447 |
| c1500 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 요동 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.5201 |
| c1500 오픈AI, 연간 매출 추정치 27조 하향…빅테크 주가 일제히 요동 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5153 |
| c1501 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.607 |
| c1501 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5535 |
| c1501 구글, 기업용 '제미나이 에이전트' 출시…'아르곤'·'클로드' 동시 탑재 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4755 |
| c1502 여수, 23~24일 독서문화축제…야외 독서·섬 체험 운영 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3454 |
| c1502 여수, 23~24일 독서문화축제…야외 독서·섬 체험 운영 | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.3198 |
| c1502 여수, 23~24일 독서문화축제…야외 독서·섬 체험 운영 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.2793 |
| c1503 한국 금융권 공격한 중국 26세 해커…'어설픈 신원 노출'로 덜미 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.5229 |
| c1503 한국 금융권 공격한 중국 26세 해커…'어설픈 신원 노출'로 덜미 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.5203 |
| c1503 한국 금융권 공격한 중국 26세 해커…'어설픈 신원 노출'로 덜미 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4397 |
| c1504 [AI리더의 서가] 이너 프롬프트 | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.405 |
| c1504 [AI리더의 서가] 이너 프롬프트 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3892 |
| c1504 [AI리더의 서가] 이너 프롬프트 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3818 |
| c1505 구글, 텍스트 입력으로 게임 만드는 플랫폼 공개…유니티와 협력 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4259 |
| c1505 구글, 텍스트 입력으로 게임 만드는 플랫폼 공개…유니티와 협력 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.419 |
| c1505 구글, 텍스트 입력으로 게임 만드는 플랫폼 공개…유니티와 협력 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.419 |
| c1506 머스크 “테라팹 직접 운영한다”…TSMC 위탁운영설 일축 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4065 |
| c1506 머스크 “테라팹 직접 운영한다”…TSMC 위탁운영설 일축 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3805 |
| c1506 머스크 “테라팹 직접 운영한다”…TSMC 위탁운영설 일축 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3607 |
| c1507 카카오, 국제 AI 학회서 MoE 학습 최적화·모델 경량화 성과 공개 | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.5017 |
| c1507 카카오, 국제 AI 학회서 MoE 학습 최적화·모델 경량화 성과 공개 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4503 |
| c1507 카카오, 국제 AI 학회서 MoE 학습 최적화·모델 경량화 성과 공개 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4375 |
| c1508 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정 모델 ‘d1-3B… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.552 |
| c1508 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정 모델 ‘d1-3B… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5036 |
| c1508 리퀴드 AI, 10배 큰 체급 제친 멀티모달 의사결정 모델 ‘d1-3B… | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.4423 |
| c1509 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최… | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.4912 |
| c1509 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.464 |
| c1509 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.457 |
| c1510 누리호 올라탄 토종 AI 반도체, 우주 궤도서 성능 실증 나선다 | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.4614 |
| c1510 누리호 올라탄 토종 AI 반도체, 우주 궤도서 성능 실증 나선다 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4453 |
| c1510 누리호 올라탄 토종 AI 반도체, 우주 궤도서 성능 실증 나선다 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4439 |
| c1511 '헤르메스 에이전트' 누스 리서치, 대규모 투자 유치로 기업용 시장 진출 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5016 |
| c1511 '헤르메스 에이전트' 누스 리서치, 대규모 투자 유치로 기업용 시장 진출 | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.4843 |
| c1511 '헤르메스 에이전트' 누스 리서치, 대규모 투자 유치로 기업용 시장 진출 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4686 |
| c1512 오픈AI "10대 챗GPT 평균 15분 사용" 주장에 안전성 논란 불붙어 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.5744 |
| c1512 오픈AI "10대 챗GPT 평균 15분 사용" 주장에 안전성 논란 불붙어 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.5686 |
| c1512 오픈AI "10대 챗GPT 평균 15분 사용" 주장에 안전성 논란 불붙어 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.559 |
| c1513 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.475 |
| c1513 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개… | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.4715 |
| c1513 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4637 |
| c1514 "독파모·모두의 AI 더 안전하게"...SKT, 업스테이지와 AI 보안… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4608 |
| c1514 "독파모·모두의 AI 더 안전하게"...SKT, 업스테이지와 AI 보안… | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.4578 |
| c1514 "독파모·모두의 AI 더 안전하게"...SKT, 업스테이지와 AI 보안… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4527 |
| c1515 저커버그 부부의 바이오허브, 미 정부·구글과 2.4조 AI 생물학 데이… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.414 |
| c1515 저커버그 부부의 바이오허브, 미 정부·구글과 2.4조 AI 생물학 데이… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3878 |
| c1515 저커버그 부부의 바이오허브, 미 정부·구글과 2.4조 AI 생물학 데이… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3769 |
| c1516 메타 '뮤즈', 스마트폰 이어 아이패드용 앱 출시…업무용 도구 연동 강화 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4277 |
| c1516 메타 '뮤즈', 스마트폰 이어 아이패드용 앱 출시…업무용 도구 연동 강화 | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.392 |
| c1516 메타 '뮤즈', 스마트폰 이어 아이패드용 앱 출시…업무용 도구 연동 강화 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3863 |
| c1517 구글, AI 생성물 구분하는 '신스ID 감지기' 일반에 전면 공개 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4264 |
| c1517 구글, AI 생성물 구분하는 '신스ID 감지기' 일반에 전면 공개 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4075 |
| c1517 구글, AI 생성물 구분하는 '신스ID 감지기' 일반에 전면 공개 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4069 |
| c1518 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 121만개 확… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4276 |
| c1518 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 121만개 확… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4165 |
| c1518 스페이스X, AI 칩 구매에 53조 조달 추진...GPU 121만개 확… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4165 |
| c1519 삼성전자, 3분기 영업익 107조...애플·엔비디아도 못 넘은 '100… | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.3572 |
| c1519 삼성전자, 3분기 영업익 107조...애플·엔비디아도 못 넘은 '100… | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.3533 |
| c1519 삼성전자, 3분기 영업익 107조...애플·엔비디아도 못 넘은 '100… | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.3389 |
| c1520 [AI리더의 서가] Agentic AI 구축 개발의 모든 것 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4939 |
| c1520 [AI리더의 서가] Agentic AI 구축 개발의 모든 것 | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.451 |
| c1520 [AI리더의 서가] Agentic AI 구축 개발의 모든 것 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.4246 |
| c1521 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 더 쓸 수… | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.614 |
| c1521 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 더 쓸 수… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.5884 |
| c1521 [10월7일] “비싸다던 클로드, 실제로는 챗GPT보다 5배 더 쓸 수… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.5451 |
| c1522 구글, ‘나노 바나나 2.1’ 공개...성능 높이고 비용은 반값으로 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.5219 |
| c1522 구글, ‘나노 바나나 2.1’ 공개...성능 높이고 비용은 반값으로 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4558 |
| c1522 구글, ‘나노 바나나 2.1’ 공개...성능 높이고 비용은 반값으로 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.4473 |
| c1523 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정황 포착 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.5242 |
| c1523 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정황 포착 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4409 |
| c1523 "AI가 대신 전화 건다"…구글 제미나이, 개인 통화 대행 정황 포착 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4359 |
| c1524 스튜어트 러셀의 경고 "LLM 정렬 불가능…모방 학습과 RLHF 한계" | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.487 |
| c1524 스튜어트 러셀의 경고 "LLM 정렬 불가능…모방 학습과 RLHF 한계" | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.4542 |
| c1524 스튜어트 러셀의 경고 "LLM 정렬 불가능…모방 학습과 RLHF 한계" | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4234 |
| c1525 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' 직접 호출 | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.4667 |
| c1525 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' 직접 호출 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.4114 |
| c1525 앤트로픽, 구글 워크스페이스 연동...문서 안에서 '클로드' 직접 호출 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3755 |
| c1526 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.4961 |
| c1526 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4644 |
| c1526 앤트로픽, 스타트업 지원 프로그램 확대...초기 고객 선점 속도 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.3898 |
| c1527 AMD, 연내 국내 'AI 연구센터' 설립...정부와 메가프로젝트 협력… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4237 |
| c1527 AMD, 연내 국내 'AI 연구센터' 설립...정부와 메가프로젝트 협력… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4071 |
| c1527 AMD, 연내 국내 'AI 연구센터' 설립...정부와 메가프로젝트 협력… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3873 |
| c1528 [게시판] SKT, 독파모 'A.X K2'로 순우리말 선정·글꼴 제작 … | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4666 |
| c1528 [게시판] SKT, 독파모 'A.X K2'로 순우리말 선정·글꼴 제작 … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4659 |
| c1528 [게시판] SKT, 독파모 'A.X K2'로 순우리말 선정·글꼴 제작 … | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4321 |
| c1529 하크, '스마트폰 대체' AI 에이전트 공개...2027년 전용 기기 … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5219 |
| c1529 하크, '스마트폰 대체' AI 에이전트 공개...2027년 전용 기기 … | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4348 |
| c1529 하크, '스마트폰 대체' AI 에이전트 공개...2027년 전용 기기 … | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4293 |
| c1530 구글, AI 데이터센터 전력 확보 위해 3.6GW 규모 원전 계약 체결 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.4848 |
| c1530 구글, AI 데이터센터 전력 확보 위해 3.6GW 규모 원전 계약 체결 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4451 |
| c1530 구글, AI 데이터센터 전력 확보 위해 3.6GW 규모 원전 계약 체결 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4448 |
| c1531 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의무화 찬성" | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.6689 |
| c1531 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의무화 찬성" | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.5371 |
| c1531 호주 청문회 출석한 오픈AI·앤트로픽 "에이전트 사고 신고 의무화 찬성" | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5049 |
| c1532 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오토리뷰’ … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5992 |
| c1532 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오토리뷰’ … | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.5674 |
| c1532 "결정 피로 줄인다"…오픈AI, 코덱스 2일차 업데이트로 ‘오토리뷰’ … | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.5567 |
| c1533 전남광주, 여수서 9~11일 ‘세계 김밥&소금 페스티벌’ | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3838 |
| c1533 전남광주, 여수서 9~11일 ‘세계 김밥&소금 페스티벌’ | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.3607 |
| c1533 전남광주, 여수서 9~11일 ‘세계 김밥&소금 페스티벌’ | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.3358 |
| c1534 딥시크, 투자 수요 폭발…IPO 전 자금 조달 규모 2배 확대 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3848 |
| c1534 딥시크, 투자 수요 폭발…IPO 전 자금 조달 규모 2배 확대 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.3711 |
| c1534 딥시크, 투자 수요 폭발…IPO 전 자금 조달 규모 2배 확대 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3663 |
| c1535 [AI리더의 서가] SQL부터 AI까지 데이터 분석 with 클로드 코드 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3885 |
| c1535 [AI리더의 서가] SQL부터 AI까지 데이터 분석 with 클로드 코드 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.387 |
| c1535 [AI리더의 서가] SQL부터 AI까지 데이터 분석 with 클로드 코드 | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.3067 |
| c1536 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트로픽과 근… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.5224 |
| c1536 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트로픽과 근… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.5111 |
| c1536 [10월6일] “아모데이와 같은 방향이라더니”…알트먼, “앤트로픽과 근… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4839 |
| c1537 '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개…반응은 엇갈려 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4856 |
| c1537 '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개…반응은 엇갈려 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4804 |
| c1537 '미국 오픈소스 대표' 리플렉션 AI, 첫 모델 공개…반응은 엇갈려 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.463 |
| c1538 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 축소 | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.4673 |
| c1538 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 축소 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4482 |
| c1538 MS는 3분의 1·메타는 절반...'클로드' 사내 사용 대폭 축소 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.41 |
| c1539 노르웨이, 공공장소 ‘AI 안경’ 일시 금지 추진…세계 첫 규제 움직임 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4459 |
| c1539 노르웨이, 공공장소 ‘AI 안경’ 일시 금지 추진…세계 첫 규제 움직임 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.402 |
| c1539 노르웨이, 공공장소 ‘AI 안경’ 일시 금지 추진…세계 첫 규제 움직임 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.343 |
| c1540 [게시판] 두산로보틱스, 989억 규모 피지컬 AI 국책과제 2건 선정… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.469 |
| c1540 [게시판] 두산로보틱스, 989억 규모 피지컬 AI 국책과제 2건 선정… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4206 |
| c1540 [게시판] 두산로보틱스, 989억 규모 피지컬 AI 국책과제 2건 선정… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4153 |
| c1541 코히어, 에이전트 비용·보안 통제 플랫폼 '노스 2' 출시...알레프 … | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4826 |
| c1541 코히어, 에이전트 비용·보안 통제 플랫폼 '노스 2' 출시...알레프 … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4821 |
| c1541 코히어, 에이전트 비용·보안 통제 플랫폼 '노스 2' 출시...알레프 … | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.4582 |
| c1542 엔비디아-그로크 27조 계약 파장…소외된 엔지니어들 "거래 불공정" 소송 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4063 |
| c1542 엔비디아-그로크 27조 계약 파장…소외된 엔지니어들 "거래 불공정" 소송 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3775 |
| c1542 엔비디아-그로크 27조 계약 파장…소외된 엔지니어들 "거래 불공정" 소송 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3727 |
| c1543 19세 청년의 반란...고스트, 개인용 AI PC '코어'로 147억 … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.484 |
| c1543 19세 청년의 반란...고스트, 개인용 AI PC '코어'로 147억 … | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4555 |
| c1543 19세 청년의 반란...고스트, 개인용 AI PC '코어'로 147억 … | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4545 |
| c1544 [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용접 솔루션’ 공동개… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4832 |
| c1544 [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용접 솔루션’ 공동개… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4204 |
| c1544 [게시판] 딥엑스-두산로보틱스, 원전 제조 ‘AI 용접 솔루션’ 공동개… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.401 |
| c1545 화웨이, 퀄컴에 '로직폴딩' 칩 관련 특허 라이선스 제공 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.3915 |
| c1545 화웨이, 퀄컴에 '로직폴딩' 칩 관련 특허 라이선스 제공 | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.3478 |
| c1545 화웨이, 퀄컴에 '로직폴딩' 칩 관련 특허 라이선스 제공 | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.3458 |
| c1546 카카오모빌리티, 고려대와 AX 협력…모빌리티 핵심 기술 국방 분야 접목 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4111 |
| c1546 카카오모빌리티, 고려대와 AX 협력…모빌리티 핵심 기술 국방 분야 접목 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3845 |
| c1546 카카오모빌리티, 고려대와 AX 협력…모빌리티 핵심 기술 국방 분야 접목 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3832 |
| c1547 “180B 모델, 개인용 노트북으로 구동”...비드래프트, 고성능 모델… | w40-solar-mini-4 업스테이지, 단일 GPU 구동 MoE 모델 Solar Mini 4 출시 | 2026-W40 | 0.5153 |
| c1547 “180B 모델, 개인용 노트북으로 구동”...비드래프트, 고성능 모델… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4461 |
| c1547 “180B 모델, 개인용 노트북으로 구동”...비드래프트, 고성능 모델… | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.4323 |
| c1548 이탈리아 멜로니 총리, AI 딥페이크 막으려 '목소리 상표권' 신청 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4298 |
| c1548 이탈리아 멜로니 총리, AI 딥페이크 막으려 '목소리 상표권' 신청 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4166 |
| c1548 이탈리아 멜로니 총리, AI 딥페이크 막으려 '목소리 상표권' 신청 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3645 |
| c1549 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.5762 |
| c1549 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4898 |
| c1549 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4426 |
| c1550 포지큐브, 롯데벤처스와 멀티 AI 에이전트 기반 AX 추진 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4699 |
| c1550 포지큐브, 롯데벤처스와 멀티 AI 에이전트 기반 AX 추진 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4096 |
| c1550 포지큐브, 롯데벤처스와 멀티 AI 에이전트 기반 AX 추진 | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3999 |
| c1551 '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 아니다" | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.6636 |
| c1551 '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 아니다" | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.491 |
| c1551 '클로드'에 폭력 협박 남겼다 체포..."AI 챗봇은 일기장 아니다" | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4649 |
| c1552 헨켈, SEDEX 2026서 AI·HBM 시대 위한 첨단 패키징 소재 … | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.349 |
| c1552 헨켈, SEDEX 2026서 AI·HBM 시대 위한 첨단 패키징 소재 … | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.3459 |
| c1552 헨켈, SEDEX 2026서 AI·HBM 시대 위한 첨단 패키징 소재 … | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3404 |
| c1553 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날부터 처리 속도 5… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.5956 |
| c1553 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날부터 처리 속도 5… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.5919 |
| c1553 오픈AI, 28일 연속 '코덱스' 개선 예고...첫날부터 처리 속도 5… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.5743 |
| c1554 LG전자, 북미서 5GW 규모 AIDC 냉각솔루션 장기계약 체결 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4406 |
| c1554 LG전자, 북미서 5GW 규모 AIDC 냉각솔루션 장기계약 체결 | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.402 |
| c1554 LG전자, 북미서 5GW 규모 AIDC 냉각솔루션 장기계약 체결 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4012 |
| c1555 [AI리더의 서가] CEO의  AI | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.3855 |
| c1555 [AI리더의 서가] CEO의  AI | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.378 |
| c1555 [AI리더의 서가] CEO의  AI | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3657 |
| c1556 구글, 'AI 프로' 국내 한정 40% 할인...연간 구독권 프로모션 … | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.509 |
| c1556 구글, 'AI 프로' 국내 한정 40% 할인...연간 구독권 프로모션 … | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4859 |
| c1556 구글, 'AI 프로' 국내 한정 40% 할인...연간 구독권 프로모션 … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4238 |
| c1557 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4052 |
| c1557 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.3808 |
| c1557 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3769 |
| c1558 앤트로픽, 10월6일까지 '음성 인터뷰어' 가동…대화록 공개·음성 학습… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4354 |
| c1558 앤트로픽, 10월6일까지 '음성 인터뷰어' 가동…대화록 공개·음성 학습… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4313 |
| c1558 앤트로픽, 10월6일까지 '음성 인터뷰어' 가동…대화록 공개·음성 학습… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4285 |
| c1559 뉴럴링크, 5만시간 뇌 데이터 사전학습…BCI도 '파운데이션 모델' 시… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4266 |
| c1559 뉴럴링크, 5만시간 뇌 데이터 사전학습…BCI도 '파운데이션 모델' 시… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4226 |
| c1559 뉴럴링크, 5만시간 뇌 데이터 사전학습…BCI도 '파운데이션 모델' 시… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4057 |
| c1560 KAIST, 데이터 변화해도 검색 정확도 유지하는 ‘CONDA’ 기술 … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4316 |
| c1560 KAIST, 데이터 변화해도 검색 정확도 유지하는 ‘CONDA’ 기술 … | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4077 |
| c1560 KAIST, 데이터 변화해도 검색 정확도 유지하는 ‘CONDA’ 기술 … | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.3897 |
| c1561 a16z "미국 가구 2.2%만 AI 유료 구독…기술이 경기 순환 핵심… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4277 |
| c1561 a16z "미국 가구 2.2%만 AI 유료 구독…기술이 경기 순환 핵심… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3953 |
| c1561 a16z "미국 가구 2.2%만 AI 유료 구독…기술이 경기 순환 핵심… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.3862 |
| c1562 GPT-6 아스트라, 217년 된 나폴레옹 암호 6시간 만에 해독 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.5321 |
| c1562 GPT-6 아스트라, 217년 된 나폴레옹 암호 6시간 만에 해독 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.5147 |
| c1562 GPT-6 아스트라, 217년 된 나폴레옹 암호 6시간 만에 해독 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.466 |
| c1563 MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.486 |
| c1563 MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 … | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4561 |
| c1563 MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 … | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.4165 |
| c1564 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부담 낮춘다 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4378 |
| c1564 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부담 낮춘다 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4074 |
| c1564 아마존, 11조 규모 AI 칩 투자자에 매각 후 리스…재무 부담 낮춘다 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.3882 |
| c1565 AI가 쏟아낸 '엉터리 제보'에... 구글, 오픈소스 버그 바운티 일시… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.5678 |
| c1565 AI가 쏟아낸 '엉터리 제보'에... 구글, 오픈소스 버그 바운티 일시… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.536 |
| c1565 AI가 쏟아낸 '엉터리 제보'에... 구글, 오픈소스 버그 바운티 일시… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4892 |
| c1566 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가상 착용' 도입 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4699 |
| c1566 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가상 착용' 도입 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4309 |
| c1566 챗GPT서 옷 입어보고 쇼핑한다... 오픈AI, '가상 착용' 도입 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4167 |
| c1567 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.4195 |
| c1567 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3565 |
| c1567 브로드컴, 앤트로픽에 80조 대출 보증…칩 판매 위해 금융 지원 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3338 |
| c1568 "전직 미국 관료 사칭"…중국 해커, AI 정책 전문가 계정 노렸다 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.5314 |
| c1568 "전직 미국 관료 사칭"…중국 해커, AI 정책 전문가 계정 노렸다 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4855 |
| c1568 "전직 미국 관료 사칭"…중국 해커, AI 정책 전문가 계정 노렸다 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.428 |
| c1569 "지기 싫어서 남의 코드 복사"…아스트라, 스타크래프트 벤치마크서 꼼수 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.6446 |
| c1569 "지기 싫어서 남의 코드 복사"…아스트라, 스타크래프트 벤치마크서 꼼수 | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.5921 |
| c1569 "지기 싫어서 남의 코드 복사"…아스트라, 스타크래프트 벤치마크서 꼼수 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5301 |
| c1570 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규제 경고 … | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.7624 |
| c1570 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규제 경고 … | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.5346 |
| c1570 오픈AI '에이전트 폭주'에 사면초가... 전 세계서 법적·규제 경고 … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4719 |
| c1571 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안전성에 이… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4956 |
| c1571 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안전성에 이… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.434 |
| c1571 손정의 "초지능, 잘못된 손에 들어가면 극도로 위험"…AI 안전성에 이… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4055 |
| c1572 'AI 피해자 영상'에 속아 내려진 중형..."형량 잘못됐다" 선고 파기 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.5047 |
| c1572 'AI 피해자 영상'에 속아 내려진 중형..."형량 잘못됐다" 선고 파기 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.454 |
| c1572 'AI 피해자 영상'에 속아 내려진 중형..."형량 잘못됐다" 선고 파기 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4378 |
| c1573 [AI리더의 서가] AI 루프를 설계하라 | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4724 |
| c1573 [AI리더의 서가] AI 루프를 설계하라 | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.4572 |
| c1573 [AI리더의 서가] AI 루프를 설계하라 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4254 |
| c1574 머스크, '스페이스XSI'로 리브랜딩 시사…트럼프 'SI' 발언 동조 | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4102 |
| c1574 머스크, '스페이스XSI'로 리브랜딩 시사…트럼프 'SI' 발언 동조 | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.3873 |
| c1574 머스크, '스페이스XSI'로 리브랜딩 시사…트럼프 'SI' 발언 동조 | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3525 |
| c1575 트럼프, ‘슈퍼 인텔리전스 부대’ 출범…국가정보국장, 백악관 AI 차르… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4639 |
| c1575 트럼프, ‘슈퍼 인텔리전스 부대’ 출범…국가정보국장, 백악관 AI 차르… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4515 |
| c1575 트럼프, ‘슈퍼 인텔리전스 부대’ 출범…국가정보국장, 백악관 AI 차르… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.3875 |
| c1582 [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게… | w40-gemini-4-argon Gemini 4 Argon 제한적 출시와 에이전트 작업 강화 | 2026-W40 | 0.5167 |
| c1582 [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게… | w40-gpt-6-1-sol OpenAI, GPT-6 Astra급 지능을 5분의 1 가격으로 제공하… | 2026-W40 | 0.4941 |
| c1582 [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.494 |
| c1583 [한영자막] Uber에서 디버깅 에이전트 하네스를 구축하는 방법 — K… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5134 |
| c1583 [한영자막] Uber에서 디버깅 에이전트 하네스를 구축하는 방법 — K… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.487 |
| c1583 [한영자막] Uber에서 디버깅 에이전트 하네스를 구축하는 방법 — K… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.4539 |
| c1584 [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5214 |
| c1584 [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4722 |
| c1584 [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4371 |
| c1585 [한영자막] 젠슨 황과 일론 머스크가 직접 밝히는 슈퍼 인텔리전스와 에… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4585 |
| c1585 [한영자막] 젠슨 황과 일론 머스크가 직접 밝히는 슈퍼 인텔리전스와 에… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4357 |
| c1585 [한영자막] 젠슨 황과 일론 머스크가 직접 밝히는 슈퍼 인텔리전스와 에… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4131 |
| c1586 [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Sa… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4701 |
| c1586 [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Sa… | w40-llamaindex-context-layer 에이전트 하네스 관점의 RAG 재정의 | 2026-W40 | 0.433 |
| c1586 [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Sa… | w40-claude-sonnet-5-5 Claude Sonnet 5.5 출시, Opus급 성능에 소네트급 비용 | 2026-W40 | 0.4201 |
| c1587 [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 … | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.4217 |
| c1587 [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 … | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.3856 |
| c1587 [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 … | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.3462 |
| c1588 [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.5289 |
| c1588 [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니… | w40-agent-security-breach 오픈AI 에이전트 보안 사고, 캘리포니아주 수사 소환장 발부 | 2026-W40 | 0.4702 |
| c1588 [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니… | w40-openai-safety-warning 오픈AI GPT-6.1 Astra 출시 철회와 내부 보안 경고 묵살 | 2026-W40 | 0.4306 |
| c1589 [한영자막] 샘 알트만이 OpenAI와 일상을 운영하기 위해 AI를 실… | w40-openai-dots OpenAI, 상시 작동 에이전트 Dots 공개 | 2026-W40 | 0.6648 |
| c1589 [한영자막] 샘 알트만이 OpenAI와 일상을 운영하기 위해 AI를 실… | w40-devday-2026-recap OpenAI DevDay 2026 주요 발표 종합 | 2026-W40 | 0.6075 |
| c1589 [한영자막] 샘 알트만이 OpenAI와 일상을 운영하기 위해 AI를 실… | w40-decisions-api 오픈AI, GPT-6 Luna 기반 Decision API 출시 | 2026-W40 | 0.4974 |

## 8. 별칭 표 (keywords.yaml 별칭 제외)

자동 승인 5, 후보 0, decide로 승인 0, 거절 1

| 정본 | 별칭 | status | 이유 | 나온 곳 |
|---|---|---|---|---|
| Claude | 클로드 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1185, it:1204, it:1206 |
| Claude Haiku 5.5 | 클로드 하이쿠 5.5 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1180 |
| Claude Opus 5.5 | 클로드 오퍼스 5.5 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1163, it:1245 |
| Claude Sonnet 5.5 | 클로드 소네트 5.5 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1149, it:1163 |
| Codex | 코덱스 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1193, it:1223, it:1225 |
| DeepSeek | 딥시크 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1196 |
| GPT-6 Astra | GPT-6 아스트라 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1148, it:1163, it:1223 |
| GPT-6 Luna | gpt-6-luna | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1043 |
| GPT-6 Luna | GPT-6 루나 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1172, it:1180, it:1198 |
| GPT-6.1 Sol | GPT-6.1-sol | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1048 |
| GPT-6.1 Sol | GPT-6.1 솔 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1223 |
| Gemini | 제미나이 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1170, it:1182, it:1230 |
| Gemini 3.8 Flash | 제미나이 3.8 플래시 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1245 |
| MAI 코드 1.1 플래시 | MAI-코드-1.1 플래시 | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1161 |
| Mistral | 미스트랄 | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1198 |
| OpenRig | openrig | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | rp:mvschwarz/openrig |
| Qwen3.8-27B | 큐원-3.8-27B | approved | 음차·약어 사전(brief.yaml aliases.transliteration) | it:1213 |
| 터미널-벤치 2.1 | 터미널벤치 2.1 | approved | 표기 차이만(대소문자·띄어쓰기·하이픈·점) | it:1205 |
| Datasette | datasette.io | rejected | rapidfuzz 90 | it:1047, it:1049 |

## 9. 편집장 입력 후보와 토픽 수 상한 근거

- 편집장 입력: 점수 상위 20개(상한 20). 입력 순서는 cluster_id 고정
- 관심 주제 후보(relevance high 항목이 있는 묶음): 62개
- 2채널 이상 묶음: 1개
- 토픽 수 설정: min 4 / max 10(멈춤 지점에서 max 10 확정)

- **한 채널이 입력의 절반을 넘음**: text 14/20
- 영상 relevance(digest 요약의 관련성 점수, 0.5 이상 high): vd:kcflfXb6dBM 0.6396, vd:oeL0uP-NO-U 0.5827, vd:D7q8fa589FY 0.5553, vd:eTtZlAPA9H4 0.5386, vd:31XD1O74pks 0.5352, vd:wrii8VocfZU 0.527, vd:PACIHCnvNMo 0.4953, vd:6YuIp-MwPv4 0.4924

| 순위 | 묶음 | 이름 | 조합 | 점수 |
|---|---|---|---|---|
| 1 | c1452 | EmbeddingGemma 2: an open, lightweight multimodal embedding… | text 4 | 3319 |
| 2 | c1448 | OpenAI “rogue” agent activities found on Wikimedia projects | text 2 | 3219 |
| 3 | c1453 | Introducing Mistral Large 4: Le chonk | text 3 | 3219 |
| 4 | c1463 | GPT-6 and Intelligent UI for everyone | text 2 | 3219 |
| 5 | c1465 | Sharing AI progress in mathematics | text 2 | 3219 |
| 6 | c1468 | Our approach to EU text provenance rules | text 2 | 3219 |
| 7 | c1497 | Claude Haiku 5.5 | text 2 | 3219 |
| 8 | c1481 | mvschwarz/openrig | text 1 + github 1 | 3126 |
| 9 | c1450 | llm-openai-decisions 0.1a0 | text 1 | 3119 |
| 10 | c1549 | "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 | text 2 | 3119 |
| 11 | c1557 | 클로드, 3개월 간 논문 36편 작성…새로운 'AI 과학 연구법' 조명 | text 1 | 3119 |
| 12 | c1563 | MIT·사카나, 자가 진화 AI 에이전트 'SIFT' 발표...'검증 비용 병목' 해결 | text 1 | 3119 |
| 13 | c1582 | [한영자막] 토큰 제한을 멈추세요: 하네스가 최적의 모델을 직접 고르게 해보세요 | video 1 | 3119 |
| 14 | c1584 | [한영자막] AI 에이전트의 엉망진창 결과물(Slop)을 없애려면 '이 구조'를 도입해야 합니다 | video 1 | 3119 |
| 15 | c1586 | [한영자막] 코딩 에이전트를 전략 게임으로 만들었습니다 — Ido Salomon, AgentCraft | video 1 | 3119 |
| 16 | c1587 | [한영자막] 프롬프트에서 프로덕션까지: AI 코드 워크플로우의 미래는 어떻게 바뀔까요? | video 1 | 3119 |
| 17 | c1588 | [한영자막] AI 코딩 에이전트가 거대한 코드베이스를 망가뜨리고 있습니다 — Sourcegraph Dan … | video 1 | 3119 |
| 18 | c1589 | [한영자막] 샘 알트만이 OpenAI와 일상을 운영하기 위해 AI를 실제로 활용하는 방법입니다. | video 1 | 3119 |
| 19 | c1466 | Advancing computer use with Ironclad | text 1 | 3117 |
| 20 | c1467 | Atlassian and OpenAI expand partnership to turn enterprise … | text 1 | 3117 |
