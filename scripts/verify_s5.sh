#!/usr/bin/env bash
# S5 관문 A(S5_TASK 6장). 항목마다 PASS/FAIL과 이유를 한 줄씩, 하나라도 FAIL이면 종료 코드 1.
# 3단계 멈춤 시점: A1~A7, A11(묶기 저장 부분). A8~A10, A12~A14는 4~8단계에서 채운다(아직이면 FAIL로 표시).
set -u
cd "$(dirname "$0")/.."
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
EXTRA=(--extra embed)
[ "$(uname -s)" = "Darwin" ] && EXTRA+=(--extra video)

pass() { echo "PASS $1 $2"; }
fail() { echo "FAIL $1 $2"; FAILED=1; }
pt() {
  local id=$1 desc=$2; shift 2
  local out
  out=$(uv run --quiet "${EXTRA[@]}" pytest -q "$@" 2>&1 | tail -1)
  if [[ "$out" == *passed* && "$out" != *failed* && "$out" != *error* ]]; then pass "$id" "$desc ($out)"; else fail "$id" "$desc: $out"; fi
}

# A1 회귀
for s in 0 1 2 3 4; do
  bash "scripts/verify_s$s.sh" >"$TMP/s$s" 2>&1 || true
done
if grep -q '^FAIL' "$TMP"/s[0-4]; then
  fail A1 "$(grep -h '^FAIL' "$TMP"/s[0-4] | head -3 | tr '\n' ' ')"
else
  pass A1 "verify_s0~s4 전부 PASS($(cat "$TMP"/s[0-4] | grep -c '^PASS')개)"
fi

# A2 정적 검사, 테스트(건너뜀 0)
if uv run --quiet "${EXTRA[@]}" ruff check . >"$TMP/ruff" 2>&1 && uv run --quiet "${EXTRA[@]}" pytest -q -rs >"$TMP/pt" 2>&1; then
  skips=$(grep -c '^SKIPPED' "$TMP/pt" || true)
  if [ "$skips" = "0" ]; then pass A2 "ruff 0, pytest $(tail -1 "$TMP/pt"), 건너뜀 0"; else fail A2 "건너뜀 ${skips}건"; fi
else
  fail A2 "$(tail -1 "$TMP/ruff") / $(tail -1 "$TMP/pt")"
fi

# A3 설정: brief.yaml, budget S5, 역할 md 5개
if uv run --quiet python -m trendsit check-config >"$TMP/cc" 2>&1 \
   && grep -q 'S5:' config/budget.yaml; then
  pass A3 "check-config $(cat "$TMP/cc"), budget S5 있음, 역할 md 5개(decide, editor_select, writer, writer_revise, critic) 섹션 검사 포함"
else
  fail A3 "$(grep FAIL "$TMP/cc" | head -3 | tr '\n' ' ')"
fi

pt A4 "공통 수정 5.1(명사 예외, ImageError 계열, 중첩 ImageFile 거부, ClassVar, 예산 기준값 위치, 수치 모듈)" tests/test_s5_common.py
pt A5 "근거 목록(자격, 근거 id 형식, 입력 상한과 뺀 근거)" tests/test_s5_evidence.py -k "eligibility or v2 or cap_pack"
pt A6 "정규화(표기 차이만 자동 승인, 숫자·버전 다른 쌍 후보 아님, name_pairs 전역 미반영)" tests/test_s5_evidence.py -k "version or spelling or name_pairs or decided"
pt A7 "묶기(채널 넘는 조건, confidence 미달, 평균 연결, 레포만 묶음, 1개짜리, 재실행 run 보존)" tests/test_s5_cluster.py

for a in A8 A9 A10 A11 A12 A13 A14; do
  fail "$a" "아직 구현 전(4~8단계)"
done
exit $FAILED
