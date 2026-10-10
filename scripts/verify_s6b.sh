#!/usr/bin/env bash
# S6b 관문 A(S6b_TASK 6장). 항목마다 PASS/FAIL과 이유를 한 줄씩, 하나라도 FAIL이면 종료 코드 1. 0원, 네트워크·LLM 호출 없음.
set -u
cd "$(dirname "$0")/.."
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

source scripts/verify_common.sh

# 정적 검사
if uv run --quiet ruff check . >"$TMP/ruff" 2>&1; then pass A1 "ruff: $(tail -1 "$TMP/ruff")"; else fail A1 "ruff: $(tail -3 "$TMP/ruff" | tr '\n' ' ')"; fi

# B1~B10: 가짜 실행기와 임시 DB 테스트(-k로 항목마다)
pt B1 "따라잡기 범위(이전 행 없음, 이어서, 10일 밀림, 범위 빔, --day, C-1)" tests/test_ops.py -k "test_b1_"
pt B2 "단계 순서·인자·--spec 주차 꼬리표·video만 --extra video·빈 큐면 video 없음" tests/test_ops.py -k "test_b2_"
pt B3 "부분 실패: 나머지 단계 계속, 종료 코드 1, partial, summary_json 칸" tests/test_ops.py -k "test_b3_"
pt B4 "잠금: nightly 즉시 종료 코드 3·skipped·days [], weekly 대기 상한 뒤 3" tests/test_ops.py -k "test_b4_"
pt B5 "계획 후보에서 digest 있는 영상, 그 주 repo_card 있는 레포 제외" tests/test_ops.py -k "test_b5_"
pt B6 "비용 꼬리표 RUN-주차 상한, 틀린 형식·없는 스펙 거부" tests/test_ops_publish.py -k "test_b6_"
pt B7 "마이그레이션 40: 행·current_run_id 보존, published 저장, 다른 값 CHECK 실패" tests/test_migration_40.py
pt B8 "publish: done 주 빌드 0 → published, 빌드 1 → 상태 그대로, open 주 → 2" tests/test_ops_publish.py -k "test_b8_"
pt B9 "published 주 weekly 거부 2·행 수 그대로, --force는 실행" tests/test_ops_publish.py -k "test_b9_"
pt B10 "ops weekly: 지난 주 계산, 실패 시 발행 없음, 이미 발행이면 아무것도 안 함, --force 없음" tests/test_ops.py -k "test_b10_"
pt A2 "ops 테스트 전체(CLI 연결 포함)" tests/test_ops.py tests/test_ops_publish.py tests/test_migration_40.py

# B11 실행 폴더·래퍼·plist: 임시 저장소에서(실제 trendsit-run은 만들지 않는다)
b11() {
  local T=$TMP/b11 repo=$PWD
  mkdir -p "$T/bin" && git init -q --bare "$T/origin.git" && git clone -q "$T/origin.git" "$T/work" 2>/dev/null || return 1
  (
    cd "$T/work" && git config user.email t@t && git config user.name t && git checkout -q -b main &&
      mkdir -p data scripts && echo '{}' >data/example.json && cp "$repo/scripts/run_ops.sh" scripts/ &&
      git add -A && git commit -q -m init && git push -q origin main && git checkout -q -b dev
  ) >/dev/null 2>&1 || { echo "임시 저장소 준비 실패"; return 1; }
  printf '#!/bin/bash\necho "$@" >>"%s/uv.log"\n[ "${1:-}" = run ] && exit "${UV_FAKE_EXIT:-0}"\nexit 0\n' "$T" >"$T/bin/uv"
  chmod +x "$T/bin/uv"
  local out
  out=$(bash scripts/setup_run_worktree.sh "$T/work" "$T/run" 2>&1) || { echo "setup 1회차 실패: $out"; return 1; }
  out=$(bash scripts/setup_run_worktree.sh "$T/work" "$T/run" 2>&1) || { echo "setup 2회차 실패: $out"; return 1; }
  [ "$(git -C "$T/work" worktree list | wc -l | tr -d ' ')" = 2 ] || { echo "worktree가 2개가 아님"; return 1; }
  for n in data site; do
    [ -L "$T/run/$n" ] && [ "$(readlink "$T/run/$n")" = "$T/work/$n" ] || { echo "$n 링크 아님"; return 1; }
  done
  [ -f "$T/run/data/example.json" ] && [ "$(git -C "$T/run" rev-parse --abbrev-ref HEAD)" = main ] || { echo "data 링크 안의 파일 또는 main 체크아웃 확인 실패"; return 1; }
  # 래퍼: pull 성공 / pull 실패(origin 끊김)에도 ops 실행, 종료 코드는 ops의 것, main 아니면 3
  PATH="$T/bin:$PATH" bash "$T/run/scripts/run_ops.sh" nightly >/dev/null 2>&1 || { echo "래퍼가 정상 경로에서 실패"; return 1; }
  git -C "$T/run" remote set-url origin "$T/nonexistent.git"
  PATH="$T/bin:$PATH" bash "$T/run/scripts/run_ops.sh" weekly >/dev/null 2>&1 || { echo "pull 실패 때 ops를 실행하지 않음"; return 1; }
  grep -q 'run python -m trendsit ops nightly' "$T/uv.log" && grep -q 'run python -m trendsit ops weekly' "$T/uv.log" ||
    { echo "uv run ... ops <job> 호출 기록 없음"; return 1; }
  grep -q 'sync --extra video --extra embed' "$T/uv.log" || { echo "uv sync에 video·embed 묶음이 없음"; return 1; }
  grep -rq 'git pull 실패' "$T/work/data/logs/ops" || { echo "pull 실패가 로그에 없음"; return 1; }
  UV_FAKE_EXIT=7 PATH="$T/bin:$PATH" bash "$T/run/scripts/run_ops.sh" nightly >/dev/null 2>&1
  [ $? = 7 ] || { echo "ops 종료 코드를 그대로 돌려주지 않음"; return 1; }
  git -C "$T/run" checkout -q -b not-main
  : >"$T/uv.log"
  PATH="$T/bin:$PATH" bash "$T/run/scripts/run_ops.sh" nightly >/dev/null 2>&1
  [ $? = 3 ] && [ ! -s "$T/uv.log" ] || { echo "main이 아닐 때 종료 코드 3·미실행이 아님"; return 1; }
  grep -rq '실행 폴더가 main 아님' "$T/work/data/logs/ops" || { echo "main 아님이 로그에 없음"; return 1; }
  # plist
  for job in nightly weekly; do
    f=ops/launchd/com.trendsit.$job.plist
    plutil -lint "$f" >/dev/null || { echo "$f lint 실패"; return 1; }
    [[ "$(plutil -extract ProgramArguments.1 raw -o - "$f")" == */trendsit-run/scripts/run_ops.sh ]] &&
      [ "$(plutil -extract ProgramArguments.2 raw -o - "$f")" = "$job" ] || { echo "$f 경로·인자가 trendsit-run/run_ops.sh $job 아님"; return 1; }
  done
  [ "$(plutil -extract StartCalendarInterval.Hour raw -o - ops/launchd/com.trendsit.nightly.plist)" = 2 ] &&
    [ "$(plutil -extract StartCalendarInterval.Minute raw -o - ops/launchd/com.trendsit.nightly.plist)" = 0 ] &&
    ! plutil -extract StartCalendarInterval.Weekday raw -o - ops/launchd/com.trendsit.nightly.plist >/dev/null 2>&1 ||
    { echo "nightly 시각이 매일 02:00이 아님"; return 1; }
  w=ops/launchd/com.trendsit.weekly.plist
  [ "$(plutil -extract StartCalendarInterval.Weekday raw -o - $w)" = 1 ] && [ "$(plutil -extract StartCalendarInterval.Hour raw -o - $w)" = 7 ] &&
    [ "$(plutil -extract StartCalendarInterval.Minute raw -o - $w)" = 0 ] || { echo "weekly 시각이 월 07:00이 아님"; return 1; }
  return 0
}
if msg=$(b11); then pass B11 "임시 저장소: setup 두 번에 worktree 1개·data·site 링크, 래퍼(pull 실패에도 실행·종료 코드 전달·main 아니면 3), plist lint·경로·시각"; else fail B11 "$msg"; fi

# B12 정리·문서
b12() {
  [ ! -e scripts/collect_temp.sh ] && [ ! -e scripts/com.trendsit.collect-temp.plist ] || { echo "임시 예약 파일이 남음"; return 1; }
  grep -q '자동 실행' README.md || { echo "README에 '자동 실행' 절 없음"; return 1; }
  [ "$(grep -c 'launchctl bootstrap' README.md)" -ge 2 ] || { echo "README에 launchctl bootstrap 2줄 미만"; return 1; }
  grep -q 'launchctl bootout.*com.trendsit.collect-temp' README.md || { echo "README에 임시 예약 bootout 없음"; return 1; }
  grep -q 'setup_run_worktree.sh' README.md && grep -q 'data/logs/ops' README.md || { echo "README에 setup 명령 또는 로그 위치 없음"; return 1; }
  uv run --quiet python -m trendsit check-config >"$TMP/cc" 2>&1 && grep -q '^OK' "$TMP/cc" || { echo "check-config 실패: $(head -2 "$TMP/cc")"; return 1; }
  mkdir -p "$TMP/cfgroot" && cp -R config "$TMP/cfgroot/config" && ln -s "$PWD/roles" "$TMP/cfgroot/roles" && ln -s "$PWD/skills" "$TMP/cfgroot/skills"
  sed -i.bak 's/^max_catchup_days:.*/max_catchup_days: 0/' "$TMP/cfgroot/config/ops.yaml"
  if uv run --quiet python -m trendsit check-config --root "$TMP/cfgroot" >"$TMP/cc2" 2>&1 || ! grep -q 'ops.yaml' "$TMP/cc2"; then
    echo "check-config가 ops.yaml의 잘못된 값을 잡지 못함"; return 1
  fi
  for n in 1 2 3 4 5 6 7 8; do grep -q "^## $n\\." reports/S6b_report.md 2>/dev/null || { echo "reports/S6b_report.md에 $n장 없음"; return 1; }; done
  return 0
}
if msg=$(b12); then pass B12 "임시 예약 파일 없음, README 자동 실행 절, check-config의 ops.yaml 검증, 리포트 8장"; else fail B12 "$msg"; fi

exit $FAILED
