#!/bin/bash
# 임시 매일 수집(P1). collect만 돌린다(LLM 호출 없음, 0원). S6 정식 launchd로 바꿀 때 제거.
# launchd 에이전트 com.trendsit.collect-temp가 매일 02:00에 부른다. 범위는 실행일 기준 최근 2일(어제~오늘, 겹치는 것은 중복 제거)
set -u
cd "$(dirname "$0")/.." || exit 1
today=$(date +%F)
since=$(date -v-1d +%F)
log_dir=data/logs/collect-temp
mkdir -p "$log_dir"
log="$log_dir/$today.log"
run() { /opt/homebrew/bin/uv run python -m trendsit collect --since "$since" --until "$today" --spec P1 "$@"; }
{
  echo "== $(date '+%F %T %z') collect $since~$today"
  out=$(run 2>&1); echo "$out"
  # 실패한 소스만 60초 뒤 한 번 더(유튜브 RSS가 가끔 404)
  for sid in $(echo "$out" | sed -n 's/^  \([a-z_]*\): 실패.*/\1/p'); do
    sleep 60
    echo "== 재시도 $sid"
    run --source "$sid"
  done
  echo "== 끝 $(date '+%F %T %z')"
} >>"$log" 2>&1
