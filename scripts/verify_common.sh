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
# 호출한 스크립트가 `--reuse <폴더>` 인자를 받아 REUSE에 넣었으면(verify_s5가 s0~s4를 한 번씩만 돌릴 때) 폴더에 이미 있는 출력과 종료 코드를 쓴다.
regress() {
  local n=$1
  if [ -n "${REUSE:-}" ]; then cp "$REUSE/s$n" "$TMP/s$n"; return "$(cat "$REUSE/s$n.rc")"; fi
  bash "scripts/verify_s$n.sh" >"$TMP/s$n" 2>&1
}
