#!/usr/bin/env bash
# S3 관문 A(M3, 3c, 3a, 3b). 항목마다 PASS/FAIL과 이유를 한 줄씩 출력하고, 하나라도 FAIL이면 종료 코드 1.
# S0, S1 회귀 포함(S2는 verify_s2.sh가 따로). 네트워크·키 없이(모의 LLM, 녹화 HTTP)
set -u
cd "$(dirname "$0")/.."
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

pass() { echo "PASS $1 $2"; }
fail() { echo "FAIL $1 $2"; FAILED=1; }
pt() {
  local id=$1 desc=$2; shift 2
  local out
  out=$(uv run --quiet pytest -q "$@" 2>&1 | tail -1)
  if [[ "$out" == *passed* && "$out" != *failed* && "$out" != *error* ]]; then pass "$id" "$desc ($out)"; else fail "$id" "$desc: $out"; fi
}

# ---------- 공통 ----------
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
if uv run --quiet python -m trendsit check-config >"$TMP/a3" 2>&1; then
  pt A3 "deep.yaml이 check-config 통과 + 잘못된 값(깊이 순서, 범위)이 경로를 짚어 실패" tests/test_s3_misc.py -k "deep_yaml"
else
  fail A3 "$(head -2 "$TMP/a3" | tr '\n' ' ')"
fi
A4_MISS=""
for r in repo_analyst editor_plan text_analyst; do
  [ -f "roles/$r.md" ] || A4_MISS+=" roles/$r.md"
  [ -f "eval/rubrics/$r.md" ] || A4_MISS+=" eval/rubrics/$r.md"
  n=$(grep -c '<example>' "roles/$r.md" 2>/dev/null || echo 0)
  [ "$n" -ge 3 ] || A4_MISS+=" $r 예시 $n개"
done
[ -f skills/origin_trace.md ] || A4_MISS+=" skills/origin_trace.md"
if [ -z "$A4_MISS" ] && uv run --quiet python -m trendsit check-config >/dev/null 2>&1; then
  pt A4 "S3 역할 md 3개(repo_analyst, editor_plan, text_analyst)와 채점표, 원본 추적 지침이 역할 md 검사 통과, 예시 3개" \
    tests/test_s1a.py -k "all_role_files"
else
  fail A4 "없음:$A4_MISS"
fi

# ---------- S1 리뷰 M3 ----------
pt M3 "safe_fetch 연결 주소 고정: 검사한 IP로만 연결(Host는 원래 이름), 리다이렉트마다 다시 고정, 검사 안 한 이름은 거부" \
  tests/test_s3_dns.py

# ---------- 3c, 3a, 3b ----------
pt A9 "에이전트 오프라인: 녹화 픽스처로 3c(GitHub 응답), 3b(GeekNews 원문 페이지) 루프가 끝까지(모의 LLM)" \
  tests/test_s3c.py tests/test_s3b.py -k "agent_loop_offline or traces_written or depth2_offline or read_more"
pt A10 "깊이·도구 상한: max_depth별 허용 도구(3c), 깊이 상한 밖·parent 없는 읽기 거부(3b), 도구 호출 6회 상한" \
  tests/test_s3c.py tests/test_s3b.py tests/test_s3_agent_core.py \
  -k "depth1 or depth_limit or trap or tool_cap or narrows or input_depth_limit or depth_seed"
pt A11 "계획 검증: 예산 초과 꼬리 자르기, max_depth 자르기, 없는 id 제거, 대체 계획" \
  tests/test_s3a.py -k "cuts or slide or depth_clip or within_80 or fallback or run_role"
pt A12 "계약: video_queue.json이 VideoQueueItem으로 읽히고 plan show --video-queue 출력이 같은 모양" \
  tests/test_s3a.py -k "contract"
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
A14_MISS=""
for c in "trendsit plan" "trendsit deep text" "trendsit repo-analyze"; do
  grep -q "$c" README.md || A14_MISS+=" README:$c"
  grep -q "$c" docs/DEVELOPMENT.md || A14_MISS+=" DEVELOPMENT:$c"
done
grep -q "^| S3 " README.md || A14_MISS+=" README:성과 행"
for h in "## 3c" "## 3a" "## 3b"; do grep -q "$h" reports/S3_report.md 2>/dev/null || A14_MISS+=" reports/S3_report.md($h)"; done
[ -f reports/S2S3_mac_todo.md ] || A14_MISS+=" reports/S2S3_mac_todo.md"
[ -z "$A14_MISS" ] && pass A14 "README(빠른 시작, 성과 행), DEVELOPMENT 명령표, S3 리포트, 맥 확인 목록" || fail A14 "없음:$A14_MISS"

exit $FAILED
