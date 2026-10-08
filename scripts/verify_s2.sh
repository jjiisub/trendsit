#!/usr/bin/env bash
# S2 관문 A. 항목마다 PASS/FAIL과 이유를 한 줄씩 출력하고, 하나라도 FAIL이면 종료 코드 1.
# --stage 0: 0단계(s2-0-base PR) 몫만 = A1~A4 + S1 리뷰 M1, M2, M4, M6. 인자 없으면 S2 전체(0단계 + 2a + 2b).
set -u
cd "$(dirname "$0")/.."
STAGE=all
[ "${1:-}" = "--stage" ] && STAGE="${2:-all}"
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

# ---------- 공통: 회귀, 정적 검사, 설정, 역할 md ----------
for n in 0 1; do
  if bash "scripts/verify_s$n.sh" >"$TMP/s$n" 2>&1; then ok[$n]=1; else ok[$n]=0; fi
done
if [ "${ok[0]}" = 1 ] && [ "${ok[1]}" = 1 ]; then
  pass A1 "verify_s0.sh $(grep -c '^PASS' "$TMP/s0")개, verify_s1.sh $(grep -c '^PASS' "$TMP/s1")개 전부 PASS"
else
  fail A1 "회귀: verify_s0.sh FAIL [$(grep '^FAIL' "$TMP/s0" | cut -c6- | cut -c1-40 | tr '\n' ';')] verify_s1.sh FAIL [$(grep '^FAIL' "$TMP/s1" | cut -d' ' -f2 | tr '\n' ' ')]"
fi
if uv run --quiet ruff check . >"$TMP/ruff" 2>&1 && uv run --quiet pytest -q >"$TMP/pt" 2>&1; then
  pass A2 "ruff 0, pytest $(tail -1 "$TMP/pt")"
else
  fail A2 "$(tail -1 "$TMP/ruff") / $(tail -1 "$TMP/pt")"
fi
if [ "$STAGE" = 0 ]; then
  if uv run --quiet python -m trendsit check-config >"$TMP/a3" 2>&1; then
    pass A3 "check-config 통과 ($(head -1 "$TMP/a3")). filter.yaml·deep.yaml은 2a·3a 단계 몫"
  else
    fail A3 "$(head -2 "$TMP/a3" | tr '\n' ' ')"
  fi
  pt A4 "역할 md 검사: 기존 역할 전부 통과(새 역할 md는 2b 이후 몫)" tests/test_s1a.py -k "all_role_files"
fi

# ---------- S1 리뷰 반영 (S1_REVIEW 4장) ----------
pt M1 "마이그레이션 번호 키: user_version 2 기존 DB 재적용 없음, 10·20 등록 순서 무관, 늦게 추가된 10번 적용, 실패는 기록 없이 재시도" \
  tests/test_s2_migrations.py
pt M2 "enforce 훅: 칸을 바꾸면 step detail enforced 기록, eval이 원래·enforce 후를 모두 기록(판정은 원래 출력), repo_oneliner README 200자 규칙" \
  tests/test_s2_enforce.py -k "enforce or eval_records"
pt M4 "도구 거부 메시지: 중첩 인자 오류에 칸 경로(origin.kind, pages[1])" tests/test_s2_enforce.py -k "nested_arg or bad_json"
M6_HIT=$(grep -rn "메인(점수순)\|RSS + list_pages" trendsit/ 2>/dev/null)
[ -z "$M6_HIT" ] && pass M6 "낡은 문구 두 개(geeknews.py 설명, report.py 계획 표기) 없음" || fail M6 "남음: $(echo "$M6_HIT" | head -2 | tr '\n' ' ')"

[ "$STAGE" = 0 ] && exit $FAILED

# ---------- 2a, 2b (S2S3_TASK 6장) ----------
for id in A3 A4 A5 A6 A7 A8 A13 A14; do fail "$id" "미구현(2a·2b 단계에서 추가)"; done

exit $FAILED
