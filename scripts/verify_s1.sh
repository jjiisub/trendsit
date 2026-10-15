#!/usr/bin/env bash
# S1 관문 A. 항목마다 PASS/FAIL과 이유를 한 줄씩 출력하고, 하나라도 FAIL이면 종료 코드 1.
# 1a(S0 보완 P1~P6, S0 리뷰 반영 R1~R6) + 1b(수집 A1~A12).
set -u
cd "$(dirname "$0")/.."
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

REUSE=""
[ "${1:-}" = "--reuse" ] && REUSE=$2  # verify_s5가 이미 돌린 s0·s1 출력을 쓰게 하는 인자
source scripts/verify_common.sh

# ---------- 1b 공통: 회귀, 정적 검사 ----------
if regress 0; then
  pass A1 "verify_s0.sh 전부 PASS ($(grep -c '^PASS' "$TMP/s0")개)"
else
  fail A1 "verify_s0.sh: $(grep '^FAIL' "$TMP/s0" | head -2 | tr '\n' ' ')"
fi
if uv run --quiet ruff check . >"$TMP/ruff" 2>&1 && uv run --quiet pytest -q >"$TMP/pt" 2>&1; then
  pass A2 "ruff 0, pytest $(tail -1 "$TMP/pt")"
else
  fail A2 "$(tail -1 "$TMP/ruff") / $(tail -1 "$TMP/pt")"
fi

# ---------- 1b 수집 (S1_TASK 6장). 네트워크 없이 저장한 응답(tests/fixtures/http)으로 ----------
if uv run --quiet python -m trendsit check-config >"$TMP/a3" 2>&1; then
  pt A3 "새 sources.yaml, link_kinds.yaml 통과 + 잘못된 backfill method, 없는 kind가 경로를 짚어 실패" \
    tests/test_s1b.py -k "new_config or bad_backfill or backfill_needs"
else
  fail A3 "$(head -2 "$TMP/a3" | tr '\n' ' ')"
fi
pt A4 "SSRF: 127.0.0.1, 10.0.0.5, 169.254.169.254, [::1], 사설 IP로 리다이렉트, 5MB 초과, 허용 밖 형식 거부" \
  tests/test_s1b.py -k "private_addresses or dangerous_urls or redirect_to_private or size_and_content"
pt A5 "오프라인 collect(녹화에 없는 URL은 차단): 소스별 기대 건수, 본문, 링크, 키워드 저장" tests/test_s1b.py -k "offline_collect"
pt A6 "같은 collect 두 번: 항목 수 그대로, 중복 0" tests/test_s1b.py -k "idempotent"
pt A7 "백필: list_pages(AI타임스)와 day_archive(GeekNews, Simon Willison), 유튜브 채널 목록, --since 앞에서 멈춤" \
  tests/test_s1b.py -k "backfill_from_saved or day_archive_pages or stops_before_since"
pt A8 "실패 격리: 한 소스 500이어도 나머지 수집, fetch_log failed + 실행 기록 attention" tests/test_s1b.py -k "one_source_failing"
pt A9 "트렌딩(설계 결정 Q2): 주간 페이지에 보이는 전부 저장(페이지 수 = 저장 수), stars_this_week 모두 숫자, 0개면 실패로 기록. 파서는 월간 페이지 25개로도 확인" \
  tests/test_s1b.py -k "trending_parser or empty_trending or trending_verdict"
pt A10 "키워드: 제목 매칭 3점, 단어 경계(eval ≠ evaluate), 제외어 규칙" tests/test_s1b.py -k "keyword_rules"
pt A11 "robots: 막힌 경로는 가져오지 않고 기록" tests/test_s1b.py -k "robots"
A12_MISS=""
grep -q "trendsit collect --since" README.md docs/DEVELOPMENT.md docs/RESULTS.md || A12_MISS+=" README:collect"
grep -q "trendsit collect" docs/DEVELOPMENT.md || A12_MISS+=" DEVELOPMENT:collect"
grep -q "## 1b 수집" reports/S1_report.md 2>/dev/null || A12_MISS+=" reports/S1_report.md(1b)"
[ -z "$A12_MISS" ] && pass A12 "README와 DEVELOPMENT.md에 수집 명령, reports/S1_report.md" || fail A12 "없음:$A12_MISS"

# ---------- 1a: S0 보완 (S0_ADDENDUM 2장) ----------
pt P1 "역할 md 검사: 전부 통과 + 섹션 누락, core_rules 4개가 경로를 짚어 실패" tests/test_s1a.py -k "lint"
pt P2 "메시지 조립: system에 입력 없음, <data> → task → 핵심 규칙, 해시는 입력과 무관" tests/test_s1a.py -k "message_order or prompt_hash or render_uses"
pt P3 "자료 탈출 방지: </document>, </data> 등이 태그 밖으로 나가지 않음" tests/test_s1a.py -k "escape or attribute"
pt P4 "스키마 순서: 모든 출력의 마지막 두 칸 log, attention, basis가 oneliner 앞" tests/test_s1a.py -k "schema_ends or basis_before"
pt P5 "라벨 도구: --label CSV 생성, 모의 라벨로 --agreement 일치율" tests/test_s1a.py -k "label"
P6_MISS=""
# 지금 README의 제목(repo-tidy 판) 기준: 맨 위 한 줄 소개(제목 없음) + 아래 6개. 옛 4·6·7장은 docs/DEVELOPMENT.md·docs/RESULTS.md
HEADS=("무엇을 하나" "어떻게 동작하나" "지금 상태" "실행 (내 환경 기준)" "폴더" "라이선스")
ORDER=$(grep -n '^## ' README.md | sed 's/^\([0-9]*\):## /\1 /')
last=0
for h in "${HEADS[@]}"; do
  n=$(echo "$ORDER" | awk -v h="$h" '{line=$1; $1=""; sub(/^ /,""); if ($0==h) {print line; exit}}')
  if [ -z "$n" ] || [ "$n" -le "$last" ]; then P6_MISS+=" README:$h"; else last=$n; fi
done
for f in .github/pull_request_template.md .github/workflows/ci.yml docs/RULES.md docs/adr/0000-template.md; do
  [ -f "$f" ] || P6_MISS+=" $f"
done
uv run --quiet python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" 2>/dev/null || P6_MISS+=" ci.yml 문법"
head -1 README.md | grep -q '^# TrendsIT' && sed -n '3p' README.md | grep -q . || P6_MISS+=" README:맨 위 한 줄 소개"
grep -q 'actions/workflows/ci.yml' README.md || P6_MISS+=" README:CI 링크"
[ -z "$P6_MISS" ] && pass P6 "README 한 줄 소개 + 제목 6개 순서, CI 링크, PR 양식, CI(YAML 통과), RULES.md, ADR 틀 (CI 초록은 PR에서 확인)" || fail P6 "없음:$P6_MISS"

# ---------- 1a: S0 리뷰 반영 (S0_REVIEW 4장) ----------
pt R1 "태그 탈출 대소문자: </DATA>, </Data >, </document >, <DOCUMENT id=\"x\">" tests/test_s1a.py -k "escape"
pt R2 "채점자 md: 역할 이름 없음, 채점표는 시스템 프롬프트에 한 번" tests/test_s1a.py -k "judge_md"
pt R3 "도구 예외: 루프가 이어지고 step에 error" tests/test_s1a.py -k "tool_exception"
pt R4 "인자 정규화: nullable 칸만, detail에 normalized" tests/test_s1a.py -k "normaliz"
if grep -q "':!data/trendsit.db\*'" scripts/verify_s0.sh && ! grep -q "':!data'" scripts/verify_s0.sh; then
  pass R5 "A9 비밀 검사 제외를 실행 산출물로 좁힘(추적 중인 data/ 파일도 검사)"
else
  fail R5 "verify_s0.sh A9 제외 범위"
fi
if uv run --quiet python -m trendsit check-config >"$TMP/r6" 2>&1; then
  pt R6 "역할 md 검사: roles/*.md + eval/judge.md 통과, 추가 섹션 허용" tests/test_s1a.py -k "all_role_files or extra_sections or applies_to_judge"
else
  fail R6 "$(head -2 "$TMP/r6" | tr '\n' ' ')"
fi

exit $FAILED
