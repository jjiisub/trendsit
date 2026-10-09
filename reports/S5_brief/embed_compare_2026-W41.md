# 묶기 임베딩 비교 2026-W41: body vs card

- 라벨: `eval/labels/decide.csv`의 31쌍(labeler opus-5.5-code, 잠정)
- body: 글은 관련성 필터 본문 임베딩(제목 + 피드 요약 + 본문 앞 1,000자), 영상·레포는 제목 + 요약
- card: 모든 채널 제목 + 요약(글 카드 summary, 영상 digest 요약, 레포 oneliner)
- 문턱값 auto 0.8 / border 0.65 / name_border 0.55(두 방식 같음)

| 기준 | body | card |
|---|---|---|
| 라벨 쌍 일치 | 30/31 | 30/31 |
| 같은 대상 묶음(라벨 same, 같은 묶음) | 10/11 | 10/11 |
| 오병합(라벨 diff인데 같은 묶음) | 0 | 0 |
| 지정 묶음 it:1045,it:1111,it:1132 | 모임 | 모임 |
| decide 호출 | 58(경로 border 31, name 27) | 60(경로 border 35, name 25) |
| 상한으로 못 부른 후보 | 0 | 11 |
| 묶음 / 토픽 후보 | 143 / 137 | 143 / 137 |
| 1개짜리 비율 | 92% | 92% |
| 2채널 이상 | 1 | 1 |

## body: 2개 이상 묶음

1. it:1111 EmbeddingGemma 2: an open, lightweight multimodal embedding  (seed) / it:1132 EmbeddingGemma 2 - 개방형 경량 멀티모달 임베딩 모델 (embed) / it:1183 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미지·음성 통합 처리 (decide) / it:1045 EmbeddingGemma 2 (decide)
2. it:1041 OpenAI “rogue” agent activities found on Wikimedia projects (seed) / it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연관 가능성" (decide)
3. it:1046 Introducing Mistral Large 4: Le chonk (seed) / it:1198 미스트랄, 1조 매개변수 ‘라지 4’ 공개..."사이버 보안·오픈 모델 최상위" (decide)
4. it:1100 GPT-6 and Intelligent UI for everyone (seed) / it:1172 오픈AI, 질문에 맞춰 화면 생성하는 'GPT-6' 공개...전 사용자 무료 적용 (embed)
5. it:1102 Sharing AI progress in mathematics (seed) / it:1156 [10월8일] “수학 문제 4000개에 AI 투입해 성과”…오픈AI가 보여준 과학연구의 변화 (decide)
6. it:1105 Our approach to EU text provenance rules (seed) / it:1225 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만 우선 적용 (decide)
7. it:1144 Claude Haiku 5.5 (seed) / it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.5' 공개 (decide)
8. it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최적화 공개 (seed) / it:1165 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개변수 모델 직접 구동 (decide)
9. it:1122 OpenRig - Claude Code와 Codex를 팀으로 운영하는 멀티 에이전트 오케스트레이터 (seed) / rp:mvschwarz/openrig mvschwarz/openrig (decide)
10. it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실" 경고 (seed) / it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 (embed)
11. it:1106 Building advertising for the way people use AI (seed) / it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생성 옆 노출 (decide)

## card: 2개 이상 묶음

1. it:1111 EmbeddingGemma 2: an open, lightweight multimodal embedding  (seed) / it:1132 EmbeddingGemma 2 - 개방형 경량 멀티모달 임베딩 모델 (embed) / it:1183 구글, 온디바이스 ‘임베딩젬마 2’ 공개…텍스트·이미지·음성 통합 처리 (embed) / it:1045 EmbeddingGemma 2 (embed)
2. it:1041 OpenAI “rogue” agent activities found on Wikimedia projects (seed) / it:1209 위키피디아 "오픈AI 불량 에이전트, 5월 장애·무단 편집 연관 가능성" (decide)
3. it:1046 Introducing Mistral Large 4: Le chonk (seed) / it:1198 미스트랄, 1조 매개변수 ‘라지 4’ 공개..."사이버 보안·오픈 모델 최상위" (decide)
4. it:1100 GPT-6 and Intelligent UI for everyone (seed) / it:1172 오픈AI, 질문에 맞춰 화면 생성하는 'GPT-6' 공개...전 사용자 무료 적용 (embed)
5. it:1102 Sharing AI progress in mathematics (seed) / it:1156 [10월8일] “수학 문제 4000개에 AI 투입해 성과”…오픈AI가 보여준 과학연구의 변화 (embed)
6. it:1105 Our approach to EU text provenance rules (seed) / it:1225 오픈AI, 챗GPT에 '투명 워터마크' 도입… EU만 우선 적용 (embed)
7. it:1144 Claude Haiku 5.5 (seed) / it:1180 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.5' 공개 (decide)
8. it:1161 MS, 서피스 랩톱 울트라 출시에 'MAI-코드-1.1' 온디바이스 최적화 공개 (seed) / it:1165 MS, 온디바이스 AI '서피스 랩톱 울트라' 공개...1200억 매개변수 모델 직접 구동 (embed)
9. it:1122 OpenRig - Claude Code와 Codex를 팀으로 운영하는 멀티 에이전트 오케스트레이터 (seed) / rp:mvschwarz/openrig mvschwarz/openrig (decide)
10. it:1219 뉴욕시의회, AI 빅테크 청문회…전직 내부고발자 "통제력 상실" 경고 (seed) / it:1249 "AI가 인류 위협" 경고한 제이콥 콕슨, 뉴욕시의회 청문회 선다 (embed)
11. it:1106 Building advertising for the way people use AI (seed) / it:1207 오픈AI, 챗GPT에 '시각적 광고' 도입…이미지 생성 옆 노출 (embed)
