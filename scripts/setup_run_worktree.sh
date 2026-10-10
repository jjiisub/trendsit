#!/bin/bash
# 자동 실행용 폴더(main worktree) 만들기. 두 번 돌려도 결과가 같다.
# 사용: setup_run_worktree.sh [작업 폴더] [실행 폴더]  (기본 ~/Claude/projects/trendsit, ~/Claude/projects/trendsit-run)
# 실행 폴더는 main만 체크아웃하고(git worktree), data/와 site/는 작업 폴더 것을 링크로 같이 쓴다(웹 서버가 site/를 서빙하므로).
set -eu
WORK=$(cd "${1:-$HOME/Claude/projects/trendsit}" && pwd)
RUN=${2:-$HOME/Claude/projects/trendsit-run}

if [ ! -e "$RUN/.git" ]; then
  git -C "$WORK" worktree add -q "$RUN" main
  # data/에는 추적 파일(예시 JSON 등)이 있어 링크와 겹친다. 실행 폴더의 data/는 지우고 작업 폴더 것을 링크한다
  rm -rf "$RUN/data"
  echo "실행 폴더 만듦: $RUN (main)"
  # uv sync는 정확 동기화라 지정하지 않은 묶음을 지운다. video(영상)와 embed(임베딩 필터)를 함께 둔다. 이미 있는 폴더는 링크만 확인
  if [ -f "$RUN/pyproject.toml" ]; then
    (cd "$RUN" && uv sync --extra video --extra embed)
  fi
fi

for name in data site; do
  if [ -L "$RUN/$name" ] && [ "$(readlink "$RUN/$name")" = "$WORK/$name" ]; then
    continue
  elif [ -e "$RUN/$name" ] || [ -L "$RUN/$name" ]; then
    echo "$RUN/$name 가 이미 있고 $WORK/$name 링크가 아님. 확인 후 지우고 다시 실행" >&2
    exit 1
  fi
  mkdir -p "$WORK/$name"
  ln -s "$WORK/$name" "$RUN/$name"
done

mkdir -p "$WORK/data/logs/ops"  # launchd가 StandardOutPath를 열려면 폴더가 먼저 있어야 함

echo "준비됨: $RUN -> data, site 링크 확인"
