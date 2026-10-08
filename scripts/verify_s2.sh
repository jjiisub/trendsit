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
pt M2 "enforce 훅: 칸을 바꾸면 step detail enforced 기록, eval이 원래·enforce 후를 모두 기록(판정은 원래 출력 + 코드 소유 칸만 enforce 후, 설계 결정 Q1), repo_oneliner README 200자 규칙" \
  tests/test_s2_enforce.py -k "enforce or eval_records"
pt M4 "도구 거부 메시지: 중첩 인자 오류에 칸 경로(origin.kind, pages[1])" tests/test_s2_enforce.py -k "nested_arg or bad_json"
M6_HIT=$(grep -rn "메인(점수순)\|RSS + list_pages" trendsit/ 2>/dev/null)
[ -z "$M6_HIT" ] && pass M6 "낡은 문구 두 개(geeknews.py 설명, report.py 계획 표기) 없음" || fail M6 "남음: $(echo "$M6_HIT" | head -2 | tr '\n' ' ')"

[ "$STAGE" = 0 ] && exit $FAILED

# ---------- 2a, 2b (S2S3_TASK 6장) ----------
if uv run --quiet python -m trendsit check-config >"$TMP/a3" 2>&1; then
  pt A3 "filter.yaml, 바뀐 keywords.yaml(13개)이 check-config 통과 + 없는 키워드 id, 범위 밖 문턱값이 경로를 짚어 실패" \
    tests/test_s2a.py -k "filter_yaml or handoff_draft"
else
  fail A3 "$(head -2 "$TMP/a3" | tr '\n' ' ')"
fi
pt A5 "rematch: 키워드를 바꾸면 판정·item_keywords·트렌딩 판정이 바뀌고, 다시 돌려도 같음" tests/test_s2a.py -k "rematch"
pt A6 "필터(모의 임베더): 네 갈래 판정, 제외어는 되살리지 않음, 두 번째 실행 임베딩 계산 0" \
  tests/test_s2a.py -k "four_way or run_filter or blob or distribution or seed_lookup"
pt A7 "같은 정규화 URL(원문 링크 포함)이 same_as로 연결, 기준 항목은 공식 > 개인 블로그 > 언론 > 큐레이션" tests/test_s2a.py -k "same_url"
A13=$(uv run --quiet python - <<'PY'
import re
from trendsit.core.migrations import MIGRATIONS
src = open("trendsit/core/migrations.py", encoding="utf-8").read()
block = src.split("# ---------- S2~S3 (10~19) ----------")[1].split("# ---------- S4 (20~29) ----------")[0]
mine = [int(n) for n in re.findall(r"register\((\d+),", block)]
bad = [n for n in mine if not 10 <= n <= 19]
print(("OK " if mine and not bad else "BAD ") + f"이 묶음 번호 {mine}, 대역 밖 {bad}, 등록 전체 {sorted(MIGRATIONS)}")
PY
)
[[ "$A13" == OK* ]] && pass A13 "마이그레이션 대역: ${A13#OK }" || fail A13 "${A13#BAD }"
if uv run --quiet python -m trendsit check-config >"$TMP/a4" 2>&1; then
  A4_MISS=""
  for r in item_card; do
    [ -f "roles/$r.md" ] || A4_MISS+=" roles/$r.md"
    [ -f "eval/rubrics/$r.md" ] || A4_MISS+=" eval/rubrics/$r.md"
    n=$(grep -c '<example>' "roles/$r.md" 2>/dev/null || echo 0)
    [ "$n" -ge 3 ] || A4_MISS+=" $r 예시 $n개"
  done
  [ -z "$A4_MISS" ] && pt A4 "S2 새 역할 md(item_card)와 채점표가 역할 md 검사 통과, 예시 3개(보통/빈칸/함정). S3 역할은 verify_s3.sh" \
    tests/test_s1a.py -k "all_role_files" || fail A4 "없음:$A4_MISS"
else
  fail A4 "$(head -2 "$TMP/a4" | tr '\n' ' ')"
fi
pt A8 "item_card enforce: 본문에 없는 quote, quote에 없는 수치, 목록 밖 키워드·링크 정리 + detail 기록, 코드 채점(인젝션, 인용 일치율)" \
  tests/test_s2b.py
A14_MISS=""
grep -q "trendsit filter" README.md || A14_MISS+=" README:filter"
grep -q "trendsit summarize" README.md || A14_MISS+=" README:summarize"
grep -q "^| S2 " README.md || A14_MISS+=" README:성과 행"
for c in rematch "trendsit filter" filter-fixtures "trendsit summarize"; do grep -q "$c" docs/DEVELOPMENT.md || A14_MISS+=" DEVELOPMENT:$c"; done
grep -q "## 2a" reports/S2_report.md 2>/dev/null || A14_MISS+=" reports/S2_report.md(2a)"
grep -q "## 2b" reports/S2_report.md 2>/dev/null || A14_MISS+=" reports/S2_report.md(2b)"
[ -f reports/S2S3_mac_todo.md ] || A14_MISS+=" reports/S2S3_mac_todo.md"
[ -z "$A14_MISS" ] && pass A14 "README(기능, 빠른 시작, 성과 행), DEVELOPMENT 명령표, S2 리포트, 맥 확인 목록" || fail A14 "없음:$A14_MISS"

exit $FAILED
