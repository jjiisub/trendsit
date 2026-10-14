#!/usr/bin/env bash
# S7a 관문 A(S7a_TASK 6장). 항목마다 PASS/FAIL과 이유를 한 줄씩, 하나라도 FAIL이면 종료 코드 1. 0원, LLM·네트워크 호출 없음.
# 실제 data/trendsit.db와 site/는 건드리지 않는다(임시 DB·임시 폴더만). verify_s6-1.sh는 게이트에 넣지 않고 S-3 끝과 런 뒤 1회(A8).
set -u
cd "$(dirname "$0")/.."
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

source scripts/verify_common.sh

if uv run --quiet ruff check . >"$TMP/ruff" 2>&1; then pass A0 "ruff: $(tail -1 "$TMP/ruff")"; else fail A0 "ruff: $(tail -3 "$TMP/ruff" | tr '\n' ' ')"; fi

# ---------- S-1: ops + export ----------
pt A1 "nightly 끝 사이트 재생성(정상: site.json 교체·weeks 불변·summary.site, 실패·시간 초과·export 예외: nightly 결과·site.json 불변, 건너뜀·범위 없음·weekly는 안 부름), publish --site-only(0·1·2), 기존 publish 불변" \
  tests/test_ops.py tests/test_ops_publish.py tests/test_s7a.py -k "s7a or a1_ or b8 or b9 or b10 or publish"
pt A2 "run 선택·분류(C-1·C-2·C-9, label·sub·topic_id·current·week 귀속·③ 묶음·status·cost, 옛 칸 0, 픽스처가 새 계약)" tests/test_export.py tests/test_s7a.py -k "a1_ or a2_ or fixture"
pt A3 "run 1건 상세 칸(weekly 6단계·nightly 8단계 name·who·line·detail, 원천 행 수, 300자, 원천 없는 단계는 line만, 하위 run 날짜 짝짓기, 참조 없음 item <n>)" tests/test_s7a.py -k "a3_"

# ---------- S-2: build + check ----------
pt A4 "주차별 표(5열·행 수·링크)·주 목록(날 행 머리 수, run 줄 = runs + publish, tr-sub, .cur 1, 결과 열 3종, ③ 줄 링크 없음, 이전·다음 주, /runs/weeks/ 없음)" tests/test_s7a.py -k "a4_"
pt A5 "run 1건(빵부스러기 링크 2, 레일 묶음 수, li.st 수 = steps, who 글자·code.ic, .check 수 = attention, 토픽 블록·체인·반려 표, <details> 0), 계약 위반은 BuildError" tests/test_s7a.py -k "a5_ or build_rejects"
if uv run --quiet python site_src/check.py --fixture >"$TMP/check" 2>&1; then c_rc=0; else c_rc=$?; fi
chk() {  # chk <항목> <check.py 줄 정규식>...: 그 줄이 하나 이상 있고 FAIL이 없어야 PASS
  local id=$1 desc=$2; shift 2
  local lines
  lines=$(grep -E "^(PASS|FAIL) ($(IFS='|'; echo "$*")) " "$TMP/check")
  if [ -n "$lines" ] && ! echo "$lines" | grep -q '^FAIL'; then pass "$id" "$desc: $(echo "$lines" | wc -l | tr -d ' ')건 PASS"; else fail "$id" "$desc: ${lines:-결과 줄 없음}"; fi
}
chk A6 "공개 금칙(C-4)·details 0(C-9)·300자(C-5)·상태 어휘·D-11 낱말·site.json 3MB(C-6), A7 페이지 존재(C-3)" 'A7 페이지' 'C-4 관리' 'C-9 <details>' 'C-5 run' 'D-11 runs' 'C-6 site'
chk A7 "관문 9 Chromium·WebKit(375·768·1280, 대상에 run 목록·weekly·nightly, 1280 .rt 셀 줄바꿈 0, 375 넘침 0)" 'A8 관문' 'A9 관문'
if [ "$c_rc" = 0 ]; then pass C-all "check.py --fixture 종료 코드 0: $(tail -1 "$TMP/check")"; else fail C-all "check.py --fixture 종료 코드 $c_rc: $(grep -E '^FAIL' "$TMP/check" | head -2 | tr '\n' ' ')"; fi

# A6 뒤쪽: 실DB가 있으면 읽기 전용 사본(sqlite backup)을 export(크기 C-6) → build → 금칙(C-4) 정적 검사. 실DB·site/는 건드리지 않는다
a6real() {
  [ -f data/trendsit.db ] || { echo "(실DB 없음: 건너뜀)"; return 0; }
  local R=$TMP/real
  mkdir -p "$R" && uv run --quiet python - "$R/trendsit.db" <<'PY' || { echo "실DB 사본 실패"; return 1; }
import sqlite3, sys
src = sqlite3.connect("file:data/trendsit.db?mode=ro", uri=True)
dst = sqlite3.connect(sys.argv[1])
src.backup(dst)
PY
  uv run --quiet python - "$R" <<'PY' || { echo "실DB export 실패"; return 1; }
import sys
from pathlib import Path
from trendsit.core.db import DB
from trendsit.export import export
export(DB(Path(sys.argv[1]) / "trendsit.db"), Path(sys.argv[1]) / "site.json")
PY
  [ -d data/slides ] && cp -r data/slides "$R/slides"
  local kb=$(($(wc -c <"$R/site.json") / 1024))
  [ "$kb" -le 3072 ] || { echo "실DB export ${kb}KB > 3MB(C-6)"; return 1; }
  uv run --quiet python site_src/build.py --data "$R/site.json" --out "$R/site" >/dev/null || { echo "실DB 빌드 실패"; return 1; }
  # 금칙(C-4)은 정적 검사만(브라우저 관문은 --fixture가 맡는다)
  uv run --quiet python - "$R/site" "$R/site.json" <<'PY' || return 1
import pathlib, sys
sys.path.insert(0, "site_src")
import check
site = pathlib.Path(sys.argv[1])
pages = {f: check.parse(f) for f in sorted(site.rglob("*.html"))}
ban = [f.relative_to(site).as_posix() + " " + m[0] for f in pages for m in [check.BANNED.search(f.read_text(encoding="utf-8"))] if m]
if ban:
    print("실DB 금칙 문자열:", ban[:3])
    sys.exit(1)
PY
  echo "실DB export ${kb}KB, 생성 HTML 금칙 0"
}
if msg=$(a6real 2>&1); then pass A6b "실DB 사본 export·build·check: $msg"; else fail A6b "$msg"; fi

# ---------- S-3: 회귀·구조·문서 ----------
echo "== A8 회귀(시간이 걸림: pytest 전체, verify_s6a.sh, verify_s6b.sh) =="
out=$(uv run --quiet pytest -q 2>&1 | tail -1)
if [[ "$out" == *passed* && "$out" != *failed* && "$out" != *error* && "$out" != *skipped* ]]; then pass A8a "pytest 전체, 건너뜀 0 ($out)"; else fail A8a "pytest 전체: $out"; fi
for n in 6a 6b; do
  if bash "scripts/verify_s$n.sh" >"$TMP/s$n" 2>&1; then pass "A8-$n" "verify_s$n.sh 종료 코드 0"; else fail "A8-$n" "verify_s$n.sh: $(grep '^FAIL' "$TMP/s$n" | head -3 | tr '\n' ' ')"; fi
done

# A9 줄 수·함수 길이(verify_s5 B4 방식)·grep(C-11, 3.4)
a9() {
  local n bad=""
  n=$(wc -l <site_src/build.py); [ "$n" -le 700 ] || bad="$bad build.py $n줄"
  n=$(wc -l <site_src/build_runs.py); [ "$n" -le 500 ] || bad="$bad build_runs.py $n줄"
  n=$(wc -l <trendsit/export.py); [ "$n" -le 350 ] || bad="$bad export.py $n줄"
  n=$(wc -l <trendsit/export_runs.py); [ "$n" -le 470 ] || bad="$bad export_runs.py $n줄"
  n=$(wc -l <site_src/check.py); [ "$n" -le 480 ] || bad="$bad check.py $n줄"
  local longfn
  longfn=$(uv run --quiet python - <<'PY'
import ast
for path in ("trendsit/export_runs.py", "trendsit/export.py", "trendsit/ops.py", "trendsit/cli_ops.py", "site_src/build.py", "site_src/build_runs.py", "site_src/check.py"):
    for n in ast.walk(ast.parse(open(path, encoding="utf-8").read())):
        if isinstance(n, ast.FunctionDef) and n.end_lineno - n.lineno + 1 > 60:
            print(f"{path}:{n.name}:{n.end_lineno - n.lineno + 1}")
PY
)
  [ -z "$longfn" ] || bad="$bad 60줄 넘는 함수 $longfn"
  grep -q 'render_run\b' site_src/build.py && bad="$bad build.py에 render_run"
  grep -qE '\.v[2-5]\b|\.c-from|r-from' site_src/trendsit.css && bad="$bad CSS에 버린 안 조각"
  grep -q '<details' site_src/build.py site_src/build_runs.py && bad="$bad <details>"
  git diff "$(git merge-base HEAD origin/main 2>/dev/null || echo main)" -- trendsit site_src | grep -E '^\+.*(os\.environ|getenv)' && bad="$bad 새 환경 변수"
  [ -z "$bad" ] || { echo "$bad"; return 1; }
}
if msg=$(a9 2>&1); then pass A9 "줄 수(build ≤700, build_runs ≤500, export ≤350, export_runs ≤470, check ≤480)·함수 ≤60줄·render_run 0·버린 CSS 조각 0·details 0·새 환경 변수 0"; else fail A9 "$msg"; fi

# A11 문서
a11() {
  grep -q '실행 기록(S7a)' README.md && grep -q 'publish --site-only' README.md && grep -q '/runs/<주>/<run>/' README.md || { echo "README 실행 기록 단락(쪽 3종·nightly 끝 재생성·publish --site-only) 없음"; return 1; }
  grep -q 'S7a' CLAUDE.md || { echo "CLAUDE.md에 S7a 진행 블록 줄 없음"; return 1; }
  grep -q 'S7a_TASK.md` 5.2' AGENTS.md || { echo "AGENTS.md 출력 형식 줄에 5.2 참조 없음"; return 1; }
  for n in 1 2 3 4 5 6 7 8; do grep -q "^## $n\\." reports/S7a_report.md 2>/dev/null || { echo "reports/S7a_report.md에 $n장 없음"; return 1; }; done
  grep -q 'C-6' reports/S7a_report.md || { echo "리포트에 C-6 실측 크기 없음"; return 1; }
  local shots
  shots=$(ls reports/S7a/shots/*.png 2>/dev/null | wc -l | tr -d ' ')
  [ "${shots:-0}" -ge 4 ] || { echo "reports/S7a/shots/ png ${shots:-0}장(4장 이상 필요: A10 QA 산출물)"; return 1; }
}
if out=$(a11 2>&1); then pass A11 "README 실행 기록 단락, CLAUDE.md·AGENTS.md, reports/S7a_report.md 8장(C-6 크기 포함), shots ≥4장"; else fail A11 "$out"; fi

exit $FAILED
