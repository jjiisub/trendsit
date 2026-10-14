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
# 다른 ops 실행이 잠금을 쥐고 있으면 그 실행이 쓰는 코드·환경을 바꾸지 않는다(pull·sync 건너뜀). ops가 잠금 대기나 종료 코드 3을 처리
mkdir -p data/locks
if python3 -c 'import fcntl, sys
f = open(sys.argv[1], "a")
try:
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit(1)' data/locks/ops.lock; [ $? = 1 ]; then
  say "ops 잠금 사용 중: git pull·uv sync 건너뜀"
else
  # 실패해도 기존 코드로 계속하되, ops가 runs 행(note, summary_json.pull_failed)에 남기게 환경 변수로 알린다. 서버가 멈춰도 60초 뒤 포기
  # 실행 폴더는 배포 전용이라 로컬 변경을 만들지 않는다: fetch 뒤 origin/main으로 하드 리셋(머지 대신). data·site는 .gitignore라 보존
  if ! { GIT_HTTP_LOW_SPEED_LIMIT=1000 GIT_HTTP_LOW_SPEED_TIME=60 git fetch origin main && git reset --hard origin/main; } >>"$log" 2>&1; then
    say "git 동기화 실패: 기존 코드로 계속"
    export TRENDSIT_PULL_FAILED=1
  fi
  # 정확 동기화라 지정하지 않은 묶음을 지운다: 영상(video)과 임베딩 필터(embed) 둘 다
  uv sync --extra video --extra embed >>"$log" 2>&1 || say "uv sync 실패: 기존 환경으로 계속"
fi
say "ops $job 시작 ($(git rev-parse --short HEAD))"
# exec: launchd의 SIGTERM이 ops까지 닿게(uv run은 신호를 자식에 전달함). 종료 코드와 단계 기록은 ops 로그·runs 행에 남음
exec uv run python -m trendsit ops "$job"
