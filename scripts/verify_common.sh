# verify_s0~s5.sh 공용 헬퍼. source해서 쓴다(FAILED, 선택으로 EXTRA 배열을 호출한 쪽이 정함).
pass() { echo "PASS $1 $2"; }
fail() { echo "FAIL $1 $2"; FAILED=1; }
# pytest 묶음 하나를 항목 하나로: $1=항목 $2=설명 $3...=pytest 인자
pt() {
  local id=$1 desc=$2; shift 2
  local out
  out=$(uv run --quiet ${EXTRA[@]+"${EXTRA[@]}"} pytest -q "$@" 2>&1 | tail -1)
  if [[ "$out" == *passed* && "$out" != *failed* && "$out" != *error* ]]; then pass "$id" "$desc ($out)"; else fail "$id" "$desc: $out"; fi
}

# 이전 스펙 회귀 한 번: regress <번호>. 출력은 $TMP/s<번호>, 종료 코드를 그대로 돌려준다.
# 첫 인자 `--reuse <폴더>`로 불리면(verify_s5가 s0~s4를 한 번씩만 돌릴 때) 폴더에 이미 있는 출력과 종료 코드를 쓴다.
REUSE=""
[ "${1:-}" = "--reuse" ] && REUSE=$2
regress() {
  local n=$1
  if [ -n "$REUSE" ]; then cp "$REUSE/s$n" "$TMP/s$n"; return "$(cat "$REUSE/s$n.rc")"; fi
  bash "scripts/verify_s$n.sh" >"$TMP/s$n" 2>&1
}

# 모든 CLI 명령(하위 명령 포함)의 --help를 이어 붙여 출력(S5-1a C-4 스냅숏 형식). 하위 명령 목록은 도움말의 {a,b,...} 줄에서 읽는다.
help_all() {
  local path=${1:-} text sub first=${2:-1}
  text=$(COLUMNS=100 uv run --quiet python -m trendsit $path --help)
  [ "$first" = 1 ] || echo
  printf '$ trendsit%s --help\n%s\n' "${path:+ $path}" "$text"
  for sub in $(echo "$text" | awk '/^ +\{.*\}/ {line=$1; getline; if ($0 ~ /^    [^ ]/) {gsub(/[{}]/, "", line); print line; exit}}' | tr ',' ' '); do
    help_all "${path:+$path }$sub" 0
  done
}
