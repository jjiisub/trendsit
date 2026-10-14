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

exit $FAILED
