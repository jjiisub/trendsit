#!/usr/bin/env bash
# S6-1 7장 런 뒤 ①~⑤를 한 번에(D-46). 실DB에 쓴다(backup·weekly·publish): 사용자 승인 뒤에만 돌린다.
# 한 단계라도 실패하면(명령 실패 또는 비용 상한 초과) 거기서 멈추고 종료 코드 1. 사용: bash scripts/s6_1_regen.sh
set -Eeu  # -E: 함수 안 실패에도 ERR trap이 걸림(007-A2-17, check_cost·week_state 포함)
cd "$(dirname "$0")/.."

DB="data/trendsit.db"
FORCED=()  # 이번 실행에서 --force로 푼 주들("week|이전status|이전run_id"), 실패 시 trap이 전부 안내

week_state() {  # "status|current_run_id"(읽기만, -readonly)
  sqlite3 -readonly -separator '|' "$DB" "SELECT status, current_run_id FROM weeks WHERE week='$1'"
}

on_err() {  # v1.2: weekly 명령 자체가 실패(set -e)해도, --force한 모든 주의 복구 명령을 안내하고 종료 코드 1
  local code=$?
  if [ "${#FORCED[@]}" -gt 0 ]; then
    echo "실패(종료 코드 $code). --force로 푼 주가 있음. 복구(필요한 주만):" >&2
    for f in "${FORCED[@]}"; do
      local week="${f%%|*}" rest="${f#*|}"
      echo "  sqlite3 $DB \"UPDATE weeks SET status='${rest%%|*}', current_run_id='${rest##*|}' WHERE week='$week'\"" >&2
    done
  fi
  exit 1
}
trap on_err ERR  # 명령 실패 종료 코드와 무관하게 1로(7장 "멈추고 종료 코드 1")

check_cost() {  # 합 ≤ 1.50(2장), 넘으면 멈춤
  local line spent cap
  line=$(uv run python -m trendsit cost --spec S6-1 | tee /dev/stderr | grep '^- 스펙')
  spent=$(echo "$line" | grep -oE '기록 합 \$[0-9.]+' | grep -oE '[0-9.]+')
  cap=$(echo "$line" | grep -oE '상한 \$[0-9.]+' | grep -oE '[0-9.]+')
  if awk -v s="$spent" -v c="$cap" 'BEGIN{exit !(s>c)}'; then
    echo "비용 상한 초과: \$$spent / \$$cap, 멈춤" >&2
    return 1  # 007-A2-17: exit는 ERR trap을 안 거치므로 return으로(set -Ee가 전파)
  fi
}

# weekly --force는 시작하자마자 그 주를 published → done으로 푼다. v1.2부터 토픽 일부만 failed(partial)여도
# weeks.status는 done이라 publish를 받지만, 토픽 전부 failed거나 예산 중단이면 done이 안 돼 거부(2)된다.
# 그러면 두 주가 미발행으로 남으므로 여기서 멈추고 되돌릴 방법을 안내한다(이전 current_run_id로 복구).
check_week_publishable() {  # ③ 각 weekly 뒤: week prev_state("status|current_run_id")
  local week="$1" prev="$2" now status
  now=$(week_state "$week")
  status="${now%%|*}"
  if [ "$status" != "done" ] && [ "$status" != "published" ]; then
    echo "주 ${week}이 발행 가능 상태가 아님: $status(= 토픽 전부 실패 또는 예산 중단, publish 거부됨)" >&2
    echo "복구: data/backup/의 pre-s6-1 백업(②)으로 되돌리거나, 아래로 이전 판을 되돌린 뒤 publish를 다시 시도할 것:" >&2
    echo "  sqlite3 $DB \"UPDATE weeks SET status='${prev%%|*}', current_run_id='${prev##*|}' WHERE week='$week'\"" >&2
    return 1  # 007-A2-17: exit는 ERR trap을 안 거치므로 return으로(set -Ee가 전파)
  fi
}

echo "== ① 영상 파일 확인 =="
for vid in S-bRN-avZ4Q D7q8fa589FY; do
  if ! ls "data/media/$vid"/media.* >/dev/null 2>&1; then
    echo "data/media/$vid/media.*가 없음(7일 보관 기간이 지났을 수 있음): 슬라이드 없이 진행"
  fi
done

echo "== ② trendsit backup --tag pre-s6-1 =="
uv run python -m trendsit backup --tag pre-s6-1

echo "== ③ weekly --force --spec S6-1(W40, W41) =="
prev40=$(week_state 2026-W40)
FORCED+=("2026-W40|$prev40")
uv run --extra embed python -m trendsit weekly --week 2026-W40 --force --spec S6-1
check_cost
check_week_publishable 2026-W40 "$prev40"
prev41=$(week_state 2026-W41)
FORCED+=("2026-W41|$prev41")
uv run --extra embed python -m trendsit weekly --week 2026-W41 --force --spec S6-1
check_cost
check_week_publishable 2026-W41 "$prev41"

echo "== ④ 읽기본 확인(손으로 reports/S5_brief/briefing_<week>.md 훑기) =="
echo "reports/S5_brief/briefing_2026-W40.md, briefing_2026-W41.md을 열어 작성 실패·⚠ 수를 리포트에 적을 것"

echo "== ⑤ publish → check.py(실사이트) → WebKit 375 캡처 =="
uv run python -m trendsit publish --week 2026-W40
uv run python -m trendsit publish --week 2026-W41
python3 site_src/check.py
echo "실사이트(trendsit.jiseop.com) 홈·토픽 2개(표·슬라이드) 캡처를 reports/S6-1/shots/에 손으로 추가할 것"

echo "모두 끝남. reports/S6-1_report.md 7장을 이 실행 결과로 채우고, ⑥(eval 픽스처 재생성)·⑦(리뷰·커밋)은 그 뒤 손으로"
