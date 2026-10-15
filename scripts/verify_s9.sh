#!/usr/bin/env bash
# S9 관문(109_S9_handoff.md §7). 하나라도 실패하면 종료 코드 1. 0원, LLM·네트워크 호출 없음.
# = ruff check . && pytest -q && check-config && verify_s6-1.sh && verify_s6b.sh + C-7(config/models.yaml:
# generate 외 별칭 내용이 origin/main과 같음)
set -u
cd "$(dirname "$0")/.."
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

source scripts/verify_common.sh

if uv run --quiet ruff check . >"$TMP/ruff" 2>&1; then pass ruff "$(tail -1 "$TMP/ruff")"; else fail ruff "$(tail -3 "$TMP/ruff" | tr '\n' ' ')"; fi

if uv run --quiet pytest -q >"$TMP/pytest" 2>&1; then pass pytest "$(tail -1 "$TMP/pytest")"; else fail pytest "$(tail -5 "$TMP/pytest" | tr '\n' ' ')"; fi

if out=$(uv run --quiet python -m trendsit check-config 2>&1) && echo "$out" | grep -q '^OK'; then
  pass check-config "$out"
else
  fail check-config "$out"
fi

echo "== 회귀: verify_s6-1.sh, verify_s6b.sh =="
if out=$(bash scripts/verify_s6-1.sh 2>&1); then pass verify_s6-1 "종료 코드 0"; else fail verify_s6-1 "$(echo "$out" | grep '^FAIL' | tr '\n' ' ')"; fi
if out=$(bash scripts/verify_s6b.sh 2>&1); then pass verify_s6b "종료 코드 0"; else fail verify_s6b "$(echo "$out" | grep '^FAIL' | tr '\n' ' ')"; fi

# C-7: config/models.yaml에서 generate 외 별칭의 내용이 origin/main과 같다(구조 비교, 들여쓰기·줄바꿈 차이는 무시)
c7() {
  uv run --quiet python - <<'PY'
import subprocess
import sys

import yaml

old_text = subprocess.run(["git", "show", "origin/main:config/models.yaml"], capture_output=True, text=True, check=True).stdout
old = yaml.safe_load(old_text)
new = yaml.safe_load(open("config/models.yaml", encoding="utf-8"))
old_models = {k: v for k, v in (old.get("models") or {}).items() if k != "generate"}
new_models = {k: v for k, v in (new.get("models") or {}).items() if k != "generate"}
sys.exit(0 if old_models == new_models else 1)
PY
}
if c7; then pass C7 "config/models.yaml: generate 외 별칭 내용이 origin/main과 같음"; else fail C7 "config/models.yaml: generate 외 별칭이 origin/main과 다름"; fi

exit $FAILED
