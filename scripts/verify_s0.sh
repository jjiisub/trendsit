#!/usr/bin/env bash
# S0 관문 A. 항목마다 PASS/FAIL과 이유를 한 줄씩 출력하고, 하나라도 FAIL이면 종료 코드 1.
# A4~A6은 smoke(무료) 모델을 실제로 호출한다. OPENROUTER_API_KEY가 없으면 FAIL("키 없음").
set -u
cd "$(dirname "$0")/.."
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
FIXTURE=eval/fixtures/repo_oneliner/encode__httpx.json

pass() { echo "PASS $1 $2"; }
fail() { echo "FAIL $1 $2"; FAILED=1; }
py() { uv run --quiet python "$@"; }

# A1 설치와 정적 검사
if uv sync --quiet >"$TMP/a1" 2>&1 && uv run --quiet ruff check . >>"$TMP/a1" 2>&1; then
  pass A1 "uv sync 성공, ruff 오류 0"
else
  fail A1 "$(tail -1 "$TMP/a1")"
fi

# A2 단위 테스트
if uv run --quiet pytest -q >"$TMP/a2" 2>&1; then
  pass A2 "pytest $(tail -1 "$TMP/a2")"
else
  fail A2 "pytest $(tail -1 "$TMP/a2")"
fi

# A3 설정 검증: 정상 통과 + 망가뜨린 설정 3종이 파일과 경로를 짚어 실패
broken() {  # $1=이름 $2=파이썬 수정 코드, 결과 출력은 $TMP/$1.out
  local root="$TMP/$1"
  mkdir -p "$root" && cp -R config roles skills "$root/"
  (cd "$root" && py -c "$2")
  py -m trendsit check-config --root "$root" >"$TMP/$1.out" 2>&1
  echo $?
}
A3_OK=1; A3_MSG=""
py -m trendsit check-config >"$TMP/a3" 2>&1 || { A3_OK=0; A3_MSG="정상 설정 실패: $(head -1 "$TMP/a3")"; }
rc=$(broken alias "import pathlib; p=pathlib.Path('roles/repo_oneliner.md'); p.write_text(p.read_text().replace('model: generate','model: genrate'))")
[ "$rc" = 1 ] && grep -q "roles/repo_oneliner.md: model:.*genrate" "$TMP/alias.out" || { A3_OK=0; A3_MSG+=" 없는 별칭($(head -1 "$TMP/alias.out"))"; }
rc=$(broken keyword "import pathlib,re; p=pathlib.Path('config/keywords.yaml'); s=p.read_text(); s=s.replace('aliases: [RAG, retrieval', 'aliases: RAG\n    x: [retrieval', 1); p.write_text(s)")
[ "$rc" = 1 ] && grep -q "keywords.yaml: keywords\[4\]" "$TMP/keyword.out" || { A3_OK=0; A3_MSG+=" 키워드 형식($(head -1 "$TMP/keyword.out"))"; }
rc=$(broken budget "import pathlib; p=pathlib.Path('config/budget.yaml'); p.write_text(p.read_text().replace('S0: 0.15','S0: -0.15'))")
[ "$rc" = 1 ] && grep -q "budget.yaml: specs: .*S0" "$TMP/budget.out" || { A3_OK=0; A3_MSG+=" 예산 음수($(head -1 "$TMP/budget.out"))"; }
if [ $A3_OK = 1 ]; then
  pass A3 "정상 통과 / $(head -1 "$TMP/alias.out") / $(head -1 "$TMP/keyword.out") / $(head -1 "$TMP/budget.out")"
else
  fail A3 "$A3_MSG"
fi

# A4~A6 실제 호출(smoke, 무료)
HAS_KEY=$(py -c "from trendsit.core.config import get_secret; print(1 if get_secret('OPENROUTER_API_KEY') else 0)")
step_of() { grep -o 'step_id=[0-9]*' "$1" | tail -1 | cut -d= -f2; }
if [ "$HAS_KEY" != 1 ]; then
  fail A4 "키 없음(OPENROUTER_API_KEY)"; fail A5 "키 없음"; fail A6 "키 없음"
else
  # A4 역할 1회 실행(캐시 읽기 끔 → 실제 호출)
  py -m trendsit role repo_oneliner --input "$FIXTURE" --model smoke --no-cache >"$TMP/a4.json" 2>"$TMP/a4.err"
  S4=$(step_of "$TMP/a4.err")
  R4=$(py - "$S4" "$TMP/a4.json" <<'EOF'
import json, sys
from trendsit.core.artifacts import RepoOneliner
from trendsit.core.config import ROOT
from trendsit.core.db import DB
step_id, out_path = sys.argv[1], sys.argv[2]
try:
    out = RepoOneliner.model_validate(json.load(open(out_path)))
except Exception as e:
    print(f"FAIL 출력 스키마 오류: {e}"); sys.exit()
db = DB(ROOT / "data" / "trendsit.db")
s = db.step(int(step_id)) if step_id else None
if s is None:
    print("FAIL step 없음"); sys.exit()
# 성공 step은 정확히 1행. 스키마 재시도(5.5)가 일어나면 실패 step이 함께 남으므로 따로 센다
ok_rows = db.conn.execute("SELECT COUNT(*) FROM steps WHERE run_id=? AND error IS NULL",
                          (s["run_id"],)).fetchone()[0]
retries = db.conn.execute("SELECT COUNT(*) FROM steps WHERE run_id=? AND error IS NOT NULL",
                          (s["run_id"],)).fetchone()[0]
empty = [k for k in ("prompt_hash", "model", "tokens_in", "tokens_out", "latency_ms") if s[k] is None]
if ok_rows != 1 or empty or s["cache_hit"] or s["error"]:
    print(f"FAIL 성공 step {ok_rows}행, 빈 칸 {empty}, cache_hit={s['cache_hit']}, error={s['error']}")
else:
    extra = f" (스키마 재시도 {retries}회 기록)" if retries else ""
    print(f"OK \"{out.oneliner}\" / step {s['id']} hash={s['prompt_hash']} model={s['model']} "
          f"tokens={s['tokens_in']}/{s['tokens_out']} latency={s['latency_ms']}ms{extra}")
EOF
)
  case "$R4" in OK*) pass A4 "${R4#OK }";; *) fail A4 "${R4#FAIL } $(tail -1 "$TMP/a4.err")";; esac

  # A5 캐시: 다시 실행하면 cache_hit=1, cost 0 (네트워크 0은 tests/test_cache_budget.py 모의 테스트)
  py -m trendsit role repo_oneliner --input "$FIXTURE" --model smoke >/dev/null 2>"$TMP/a5.err"
  S5=$(step_of "$TMP/a5.err")
  R5=$(py -c "
from trendsit.core.config import ROOT; from trendsit.core.db import DB
s = DB(ROOT/'data'/'trendsit.db').step(int('${S5:-0}'))
print('OK' if s and s['cache_hit'] == 1 and (s['cost_usd'] or 0) == 0 else f'FAIL step={dict(s) if s else None}')")
  T5=$(uv run --quiet pytest -q tests/test_cache_budget.py -k cache_hit 2>&1 | tail -1)
  if [ "$R5" = OK ] && [[ "$T5" == *passed* ]]; then
    pass A5 "step $S5 cache_hit=1 cost=0, 모의 클라이언트 네트워크 0회($T5)"
  else
    fail A5 "$R5 / $T5"
  fi

  # A6 재생: 같은 요청으로 실행되고 새 step
  py -m trendsit role --replay "$S4" >/dev/null 2>"$TMP/a6.err"
  S6=$(step_of "$TMP/a6.err")
  R6=$(py -c "
from trendsit.core.config import ROOT; from trendsit.core.db import DB
db = DB(ROOT/'data'/'trendsit.db'); a, b = db.llm_call(int('$S4')), db.llm_call(int('${S6:-0}'))
same = a and b and a['request']['body'] == b['request']['body']
print('OK' if same and int('${S6:-0}') > int('$S4') else 'FAIL 요청 불일치 또는 새 step 없음')")
  if [ "$R6" = OK ]; then pass A6 "step $S4 재생 → 새 step $S6, 요청 본문 동일"; else fail A6 "$R6 $(tail -1 "$TMP/a6.err")"; fi
fi

# A7 예산 장치 (모의)
T7=$(uv run --quiet pytest -q tests/test_cache_budget.py -k "spec_cap or phase_usage or limit_remaining or key_failure or session_cost" 2>&1 | tail -1)
[[ "$T7" == *passed* && "$T7" != *failed* ]] && pass A7 "BudgetExceeded로 호출 전 중단, /key 모의로 단계 사용액과 limit_remaining 검사 ($T7)" || fail A7 "$T7"

# A8 에이전트 상한 (모의)
T8=$(uv run --quiet pytest -q tests/test_agent.py 2>&1 | tail -1)
[[ "$T8" == *passed* && "$T8" != *failed* ]] && pass A8 "max_steps 대체 출력, 깊이 4 거부, 허용 밖 도구 거부, 도구 호출 kind='tool' 기록 ($T8)" || fail A8 "$T8"

# A9 비밀 없음
LEAK=$(git grep -nIE --untracked 'sk-or-v1-[0-9a-f]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}' -- . ':!data' 2>/dev/null | head -3)
IGN_ENV=$(git check-ignore -q .env && echo 1 || echo 0)
IGN_DATA=$(git check-ignore -q data/trendsit.db && echo 1 || echo 0)
TRACKED=$(git ls-files | grep -E '(^|/)\.env$|^data/(trendsit\.db|cache/|budget_state)' | head -3)
if [ -z "$LEAK" ] && [ "$IGN_ENV" = 1 ] && [ "$IGN_DATA" = 1 ] && [ -z "$TRACKED" ]; then
  pass A9 "키 문자열 없음, .env와 data/가 .gitignore에 있음"
else
  fail A9 "누출=[$LEAK] .env 무시=$IGN_ENV data 무시=$IGN_DATA 추적중=[$TRACKED]"
fi

# A10 문서
MISSING=""
for cmd in "uv sync" check-config "role " "--replay" "eval " "cost" "trace"; do
  grep -q -- "$cmd" README.md 2>/dev/null || MISSING+=" $cmd"
done
[ -f reports/S0_report.md ] || MISSING+=" reports/S0_report.md"
[ -z "$MISSING" ] && pass A10 "README에 설치와 명령, reports/S0_report.md 있음" || fail A10 "없음:$MISSING"

exit $FAILED
