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
