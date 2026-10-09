#!/usr/bin/env bash
# S5 관문 A(S5_TASK 6장). 항목마다 PASS/FAIL과 이유를 한 줄씩, 하나라도 FAIL이면 종료 코드 1.
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

pt A8 "선별 검증(리드 1, 개수 범위, 범위 밖 합치기·나누기 거부, relation은 과거 대조 후보 안, 입력 순서 cluster_id, reason 값 대조, 재시도·대체)" \
  tests/test_s5_select_checks.py tests/test_s5_weekly.py -k "valid or reject or max_topics or order or reason or slug or retries"
pt A9 "코드 검사(수치 대조·단위 환산 미허용, anchor, 도식 상한, 금지어, 자동 수정은 반려 아님, 경고)" \
  tests/test_s5_select_checks.py -k "clean or number or anchor or forbidden or alias or unknown or warnings or noun or reset"
pt A10 "라운드(상한 3, 코드 반려도 셈, 같은 이슈 2회 check, 지적 안 된 칸 되돌림, 1부터 센 위치 바로잡기)" tests/test_s5_weekly.py tests/test_s5_select_checks.py -k "rounds or one_based"
pt A11 "저장(마이그레이션 30~33, 재실행 run 보존·current_run_id, topic_evidence = 최종판 refs)" \
  tests/test_s5_weekly.py tests/test_s5_cluster.py -k "rounds or stage_cluster"
pt A12 "실행 요약 JSON 형식과 표에서 다시 계산한 값 일치" tests/test_s5_weekly.py -k rounds
pt A13 "저장값만으로 예시 JSON 토픽 칸(매핑 함수 초안)" tests/test_s5_weekly.py -k rounds

# A14 문서: README S5, 리포트 체크리스트, reports/eval 역할·모델별 최신 1개(라벨이 가리키는 실행은 예외)
labeled=$(grep -ho 'reports/eval/[a-z_]*_[0-9-]*\.json' eval/labels/* 2>/dev/null | sort -u)
extra=$(ls reports/eval/*.json | sed 's#.*/##' | sed -E 's/_[0-9]{8}-[0-9]{6}\.json$//' | sort | uniq -c | awk '$1>1{print $2}')
over=""
for k in $extra; do
  n2=$(for f in reports/eval/${k}_*.json; do echo "$labeled" | grep -qx "$f" || echo "$f"; done | wc -l | tr -d ' ')
  [ "$n2" -gt 1 ] && over="$over $k($n2)"
done
if grep -q 'S5' README.md && grep -q '진행 체크리스트' reports/S5_report.md && [ -z "$over" ]; then
  pass A14 "README S5 상태, S5_report 체크리스트, reports/eval 역할·모델별 최신 1개(+ 라벨 기준 실행)"
else
  fail A14 "README/리포트/eval 정리 확인:${over}"
fi
exit $FAILED
