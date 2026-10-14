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

exit $FAILED
