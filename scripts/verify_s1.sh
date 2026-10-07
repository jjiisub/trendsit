#!/usr/bin/env bash
# S1 관문 A. 항목마다 PASS/FAIL과 이유를 한 줄씩 출력하고, 하나라도 FAIL이면 종료 코드 1.
# 1a(S0 보완 P1~P6, S0 리뷰 반영 R1~R6) + 1b(수집 A1~A12).
set -u
cd "$(dirname "$0")/.."
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

pass() { echo "PASS $1 $2"; }
fail() { echo "FAIL $1 $2"; FAILED=1; }
# pytest 묶음 하나를 항목 하나로: $1=항목 $2=설명 $3...=pytest 인자
pt() {
  local id=$1 desc=$2; shift 2
  local out
  out=$(uv run --quiet pytest -q "$@" 2>&1 | tail -1)
  if [[ "$out" == *passed* && "$out" != *failed* && "$out" != *error* ]]; then pass "$id" "$desc ($out)"; else fail "$id" "$desc: $out"; fi
}

# ---------- 1b 공통: 회귀, 정적 검사 ----------
if bash scripts/verify_s0.sh >"$TMP/s0" 2>&1; then
  pass A1 "verify_s0.sh 전부 PASS ($(grep -c '^PASS' "$TMP/s0")개)"
else
  fail A1 "verify_s0.sh: $(grep '^FAIL' "$TMP/s0" | head -2 | tr '\n' ' ')"
fi
if uv run --quiet ruff check . >"$TMP/ruff" 2>&1 && uv run --quiet pytest -q >"$TMP/pt" 2>&1; then
  pass A2 "ruff 0, pytest $(tail -1 "$TMP/pt")"
else
  fail A2 "$(tail -1 "$TMP/ruff") / $(tail -1 "$TMP/pt")"
fi

# ---------- 1a: S0 보완 (S0_ADDENDUM 2장) ----------
pt P1 "역할 md 검사: 전부 통과 + 섹션 누락, core_rules 4개가 경로를 짚어 실패" tests/test_s1a.py -k "lint"
pt P2 "메시지 조립: system에 입력 없음, <data> → task → 핵심 규칙, 해시는 입력과 무관" tests/test_s1a.py -k "message_order or prompt_hash or render_uses"
pt P3 "자료 탈출 방지: </document>, </data> 등이 태그 밖으로 나가지 않음" tests/test_s1a.py -k "escape or attribute"
pt P4 "스키마 순서: 모든 출력의 마지막 두 칸 log, attention, basis가 oneliner 앞" tests/test_s1a.py -k "schema_ends or basis_before"
pt P5 "라벨 도구: --label CSV 생성, 모의 라벨로 --agreement 일치율" tests/test_s1a.py -k "label"
P6_MISS=""
# 지금 README의 제목(PR #2 판) 기준: 맨 위 한 줄 소개(제목 없음) + 아래 11개
HEADS=("1. 왜 만들었나" "2. 핵심 기능" "3. 아키텍처" "4. 빠른 시작" "5. 사용 예시 / 결과물" "6. 성과와 평가" "7. 기술적 도전" "8. 기술 스택" "9. 폴더 구조" "10. 로드맵 / 한계" "만든 사람")
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
head -1 README.md | grep -q '^# TrendsIT' && sed -n '2,4p' README.md | grep -q '^> ' || P6_MISS+=" README:맨 위 한 줄 소개"
grep -q 'actions/workflows/ci.yml/badge.svg' README.md || P6_MISS+=" README:CI 배지"
[ -z "$P6_MISS" ] && pass P6 "README 한 줄 소개 + 제목 11개 순서, CI 배지, PR 양식, CI(YAML 통과), RULES.md, ADR 틀 (CI 초록은 PR에서 확인)" || fail P6 "없음:$P6_MISS"

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
