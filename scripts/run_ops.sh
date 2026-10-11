#!/bin/bash
# launchd가 부르는 래퍼. 사용: run_ops.sh <nightly|weekly>. 종료 코드는 `trendsit ops`의 것(0 성공, 1 실패, 3 못 돌림)
set -u
job=${1:?사용: run_ops.sh <nightly|weekly>}
cd "$(dirname "$0")/.." || exit 3
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"  # launchd의 기본 PATH에는 uv가 없음(이미 PATH에 있으면 그것이 먼저)
log_dir=data/logs/ops
mkdir -p "$log_dir"
log="$log_dir/$(date +%F)-$job.log"
say() { echo "== $(date '+%F %T %z') $*" >>"$log"; }

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$branch" != "main" ]; then
  say "실행 폴더가 main 아님 ($branch): 실행하지 않음"
  echo "실행 폴더가 main 아님 ($branch)" >&2
  exit 3
fi
# 실패해도 기존 코드로 계속하되, ops가 runs 행(note, summary_json.pull_failed)에 남기게 환경 변수로 알린다
if ! git pull --ff-only origin main >>"$log" 2>&1; then
  say "git pull 실패: 기존 코드로 계속"
  export TRENDSIT_PULL_FAILED=1
fi
# 정확 동기화라 지정하지 않은 묶음을 지운다: 영상(video)과 임베딩 필터(embed) 둘 다
uv sync --extra video --extra embed >>"$log" 2>&1 || say "uv sync 실패: 기존 환경으로 계속"
say "ops $job 시작 ($(git rev-parse --short HEAD))"
uv run python -m trendsit ops "$job"
code=$?
say "ops $job 종료 코드 $code"
exit $code
