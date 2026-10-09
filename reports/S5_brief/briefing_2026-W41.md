# 주간 브리핑 2026-W41 (리뷰용 읽기본)

> run `20261009-163817-weekly-be4c`. S6 export 전 임시 화면. 홈 순서대로 토픽, 끝에 홈 레포 목록. 근거 id 옆은 출처 제목. ⚠ = 확인 필요(같은 이슈가 두 번 남았거나 3라운드 뒤 남은 이슈)

## 1. (리드 · 작성 실패) w41-mistral-large-4

## 2. (작성 실패) w41-gpt-6-intelligent-ui

## 3. (작성 실패) w41-embedding-gemma-2

## 4. Claude Haiku 5.5 출시와 토크나이저 변경에 따른 실질 API 비용 변화

`w41-claude-haiku-5-5` · 상태 checked · 2라운드 · 축: 토크나이저 변경과 실질 API 비용 변화

**요약(홈)** Anthropic이 Claude Haiku 5.5를 출시하며 100,000 토큰 이하 구간에서 전작 대비 90% 가격 인하를 발표했다. ==토크나이저 변경으로 토큰 사용량이 1.25배 증가해 실질 비용 절감 효과가 제한적==이라는 분석이 나왔다.

**개요** Anthropic이 소형 모델 Claude Haiku 5.5를 출시하며 100,000 토큰 이하 구간에서 전작 대비 90% 가격 인하를 발표했다. 그러나 토크나이저 변경으로 인해 실제 토큰 사용량이 1.25배 증가하면서 명목상 인하율보다 실질 비용 절감 효과가 줄어드는 쟁점이 발생했다. 100,000 토큰 이하 워크로드에서는 GPT-6 Luna와 동일한 가격에 벤치마크 점수가 더 높아 경쟁력이 확보됐다.

**핵심 포인트**

1. 100,000 토큰 이하 구간에서 입력/출력 토큰 가격이 100만 토큰당 각각 0.10달러, 0.50달러로 책정되어 전작 대비 90% 인하됨  
   ← `it:1180#q2` 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.5' 공개
2. ==토크나이저 변경으로 같은 프롬프트의 토큰 사용량이 Haiku 4.5 대비 약 1.25배 증가하여 숨겨진 가격 인상이 발생함==  
   ← `it:1144#q4` Claude Haiku 5.5
3. 100,000 토큰 초과 시 가격은 5배로 증가하여 입력/출력 각각 $0.50/$2.50이 적용됨  
   ← `it:1144#q3` Claude Haiku 5.5
4. 100,000 토큰 이하 워크로드에서는 GPT-6 Luna와 가격이 동일하며 벤치마크 점수가 더 높음  
   ← `it:1144#q5` Claude Haiku 5.5
5. GDPval-AA v2.1에서 1620점을 기록해 전작 Haiku 4.5(735점)와 GPT-6 Luna(1437점)를 상회함  
   ← `it:1180#q4` 앤트로픽, API 비용 최대 90% 낮춘 '클로드 하이쿠 5.5' 공개

   **도식(수치): Claude Haiku 5.5가 GDPval-AA v2.1에서 경쟁 모델보다 점수 높음** (점) — 지식 노동 역량을 평가하는 GDPval-AA v2.1 벤치마크에서 Claude Haiku 5.5, 전작 Haiku 4.5, GPT-6 Luna의 점수 비교 [it:1180#q4]

   | 라벨 | 값 | 근거 | 표시 |
   |---|---|---|---|
   | Claude Haiku 5.5 | 1620 | `it:1180#q4` | 강조 |
   | GPT-6 Luna | 1437 | `it:1180#q4` |  |
   | Haiku 4.5 | 735 | `it:1180#q4` |  |

**소스별로 더한 것**

- github: 토크나이저 변경으로 인한 실질 토큰 사용량 증가(1.25배)와 숨겨진 가격 인상 분석
- github: 전작 대비 90% 가격 인하 및 GDPval-AA v2.1, OS월드 2.1 등 벤치마크 성능 수치 공개

출처 2곳: `it:1180`, `it:1144`

## 5. (작성 실패) w41-openai-rogue-agent

## 6. (작성 실패) w41-openai-math-results

## 7. (작성 실패) w41-openai-textgrain

## 8. (작성 실패) w41-ms-mai-code-1

## 홈 레포 목록

- ★ mvschwarz/openrig · 신호 release · 이번 주 별 2693 · v0.6.6 릴리스(2026-10-07), 7일 커밋 100+로 개발 활발
- ★ NVIDIA/OpenShell · 신호 trending · 이번 주 별 None · 7일 커밋 86·작성자 24로 개발 지속, v0.1.2(09-28) 이후 안정 릴리스 주기 운영
- ★ Panniantong/Agent-Reach · 신호 trending · 이번 주 별 6987 · 도구로 확인된 릴리스·글 언급 없음, 별 급증 원인 미확인
- ★ cursor/plugins · 신호 trending · 이번 주 별 1109 · 7일 커밋 26, 기여자 8명으로 개발이 이어짐. 릴리스와 글 언급은 확인되지 않음
- heygen-com/hyperframes · 신호 release · 이번 주 별 3996 · 이번 주 릴리스 5개(v0.8.137~141)와 7일 커밋 100+로 개발이 활발
- thedotmack/claude-mem · 신호 release · 이번 주 별 3153 · v13.34.0~v13.34.2 릴리스(2026-10-06), 7일 커밋 100+
- tile-ai/tilelang · 신호 release · 이번 주 별 None · v0.1.15 릴리스(2026-09-30, Ascend 950 NPU 네이티브 지원), 최근 7일 커밋 14

## 실행 요약

```json
{
 "week": "2026-W41",
 "model": "qwen/qwen3.8-27b",
 "status": "ok",
 "cluster_run": "20261009-150737-weekly-24db",
 "evidence": {
  "items": {
   "text": 141,
   "video": 8,
   "github": 7
  },
  "excluded": {
   "no_card": 29,
   "no_digest": 7,
   "irrelevant_repo": 0
  },
  "truncated_topics": 0
 },
 "aliases": {
  "candidates": 0,
  "auto_approved": 5,
  "decide_calls": 0
 },
 "cluster": {
  "clusters": 144,
  "single_item": 127,
  "multi_channel": 1,
  "three_channel": 0,
  "decide_calls": 31,
  "decide_merged": 10,
  "past": {
   "new": 8,
   "follow_up": 0,
   "duplicate": 0
  }
 },
 "select": {
  "candidates": 20,
  "selected": 8,
  "merges": 0,
  "splits": 0,
  "drops": {
   "duplicate": 0,
   "low_relevance": 0,
   "thin": 0,
   "other": 12
  }
 },
 "write": {
  "topics": 8,
  "failed": 0
 },
 "review": {
  "rounds": {
   "1": 0,
   "2": 1,
   "3": 0
  },
  "code_rejects": 2,
  "critic_rejects": 0,
  "autofixes": 0,
  "reverts": 0,
  "issues": {
   "unsupported": 0,
   "number_mismatch": 0,
   "overclaim": 0,
   "missing_key": 0,
   "wrong_ref": 0,
   "overuse": 0,
   "missing_diagram": 0
  },
  "check_points": 0
 },
 "cost_usd": {
  "decide": 0.0,
  "editor_select": 0.0,
  "writer": 0.0,
  "writer_revise": 0.000742,
  "critic": 0.0,
  "total": 0.000742
 },
 "duration_sec": {
  "evidence": 0,
  "cluster": 0,
  "select": 0.0,
  "write_review": 4.1,
  "total": 8.1
 }
}
```
