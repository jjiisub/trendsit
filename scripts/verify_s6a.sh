#!/usr/bin/env bash
# S6a 관문 A(S6a_TASK 6장). 항목마다 PASS/FAIL과 이유를 한 줄씩, 하나라도 FAIL이면 종료 코드 1. 0원, LLM 호출 없음.
# 실제 data/trendsit.db와 site/는 건드리지 않는다(임시 DB, 임시 폴더만).
set -u
cd "$(dirname "$0")/.."
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
EXTRA=()

source scripts/verify_common.sh

# ruff
if uv run --quiet ruff check . >"$TMP/ruff" 2>&1; then pass A0 "ruff: $(tail -1 "$TMP/ruff")"; else fail A0 "ruff: $(tail -3 "$TMP/ruff" | tr '\n' ' ')"; fi

# ---------- S-1: export, 주차 표기, W40 근사, data/ 정리 ----------
pt A1 "export 구조(최상위 8칸, 칸별 값, example/notice/markup 없음, published 주만 C-1, C-2 실패 시 파일 유지, 종료 코드)" tests/test_export.py -k "a1_"
pt A2 "주차 표기(W39 9월 4주차, W40 10월 1주차, W41 10월 2주차, W42 10월 3주차, 연말 W53 12월 5주차, 2027-W01)" tests/test_export.py -k "a2_"
pt A11 "W40 근사(다른 주 레포 제외, 상위 10, stars NULL, run note, 두 번 실행 같은 행 수, export trending_approx, 실패 시 DB 불변)" tests/test_export.py -k "a11_"

# A14 data/ 정리와 verify_s5 B7·A17
a14() {
  local n pat="data/trendsit-example""\.json" f
  [ "$(git ls-files data | wc -l | tr -d ' ')" = 0 ] || { echo "git ls-files data가 비어 있지 않음"; return 1; }
  for f in trendsit-example.json make_data.py; do
    [ -f "site_src/example/$f" ] || { echo "site_src/example/$f 없음"; return 1; }
    [ "$(shasum -a 256 <"site_src/example/$f" | cut -d' ' -f1)" = "$(git show "3967cd4:data/$f" | shasum -a 256 | cut -d' ' -f1)" ] ||
      { echo "$f 내용이 옮기기 전(3967cd4)과 다름"; return 1; }
  done
  n=$(grep -rnI "$pat" trendsit site_src scripts --exclude-dir=shots --exclude-dir=__pycache__ | head -3)
  [ -z "$n" ] || { echo "예시 파일 경로 문자열이 남음: $n"; return 1; }
  # 실행 폴더처럼 data, site가 심볼릭 링크일 때도 .gitignore가 무시하는지(임시 저장소)
  local g=$TMP/ign
  mkdir -p "$g/real" && git init -q "$g" && cp .gitignore "$g/" && ln -s real "$g/data" && ln -s real "$g/site" || { echo "임시 저장소 준비 실패"; return 1; }
  git -C "$g" check-ignore -q data && git -C "$g" check-ignore -q site || { echo "data·site 링크를 .gitignore가 무시하지 않음"; return 1; }
  # verify_s5 B7·A17: 스냅숏의 명령·옵션이 하나도 사라지지 않음. 현재 CLI는 PASS, 옵션을 지운 가짜 help는 FAIL
  eval "$(sed -n '/^help_all() {/,/^}/p;/^help_compat() {/,/^}/p' scripts/verify_s5.sh)"
  help_all >"$TMP/help_now.txt" 2>&1 || { echo "help 실행 실패"; return 1; }
  n=$(help_compat reports/S5-1/help_before.txt "$TMP/help_now.txt") || { echo "현재 CLI에서 사라진 것: $n"; return 1; }
  grep -v -e '--spec' "$TMP/help_now.txt" >"$TMP/help_fake.txt"
  help_compat reports/S5-1/help_before.txt "$TMP/help_fake.txt" >/dev/null && { echo "옵션을 지운 가짜 help가 통과함"; return 1; }
  # 설명 문장 속 --xxx는 옵션이 아니다(옵션 줄에서만 추출)
  { cat reports/S5-1/help_before.txt; printf '$ trendsit check-config --help\n                        설명에 나오는 --no-such-flag 같은 말\n'; } >"$TMP/help_prose.txt"
  help_compat "$TMP/help_prose.txt" "$TMP/help_now.txt" >/dev/null || { echo "설명 문장 속 --xxx를 옵션으로 셈"; return 1; }
  return 0
}
if out=$(a14 2>&1); then pass A14 "data/ 추적 파일 0, example/에 두 파일(내용 해시 동일), 예시 경로 문자열 0, data·site 링크 무시, B7·A17 호환 판정(현재 PASS, 가짜 FAIL)"; else fail A14 "$out"; fi

# ---------- S-2: 사이트 빌드 ----------
pt A3 "도식 배치(C-8)·출처 번호(채널 순·id 순)·#src-id 앵커·타임라인이 첫 영상 인용 포인트 아래" tests/test_site.py -k "a3_"
pt F01 "끝 어절 묶기는 원문 어절 단위(43점·\`코드\`조사·==형광==됨에서 마크업 정상), check.py가 깨진 마크업을 잡음" tests/test_site.py -k "f01_"
pt A4 "확인 필요 표기(C-9 개수, 포인트는 .nb-end 안, 홈 메타 / 확인 필요)" tests/test_site.py -k "a4_"

# ---------- S-3: check.py(정적 + 관문 9 + 동작), 발행 연결 ----------
if uv run --quiet python site_src/check.py --fixture >"$TMP/check" 2>&1; then c_rc=0; else c_rc=$?; fi
for id in A5 A6 A7 A8 A9 A10; do
  lines=$(grep -E "^(PASS|FAIL) $id " "$TMP/check")
  if [ -n "$lines" ] && ! echo "$lines" | grep -q '^FAIL'; then pass "$id" "check.py --fixture: $(echo "$lines" | head -1 | cut -c6-200)"; else fail "$id" "check.py --fixture: ${lines:-결과 줄 없음} / $(grep -E '^(FAIL|실패)' "$TMP/check" | head -2 | tr '\n' ' ')"; fi
done
if [ "$c_rc" = 0 ]; then pass C-all "check.py --fixture 종료 코드 0(C-3·C-4·C-5·C-6·C-7 포함): $(tail -1 "$TMP/check")"; else fail C-all "check.py --fixture 종료 코드 $c_rc: $(grep -E '^FAIL' "$TMP/check" | head -2 | tr '\n' ' ')"; fi
pt A12 "발행 연결(export → 빌드 순서), 빌드 실패 시 site/ 바이트 그대로·status 그대로, 깨진 입력·렌더 중 실패에도 site/ 불변(C-10), 정적 검사가 위반을 잡아냄" tests/test_site.py -k "a12_ or c10_ or a5_to_a7 or f12_"
pt A2b "ops 테스트(publish 순서 변경 반영)" tests/test_ops.py tests/test_ops_publish.py
pt A-all "S6a 테스트 전체(export·site)" tests/test_export.py tests/test_site.py

# ---------- S-4: 문서 ----------
a13() {
  grep -q '^### 사이트 (S6a)' README.md && grep -q 'trendsit export' README.md && grep -q 'publish --week' README.md && grep -q 'site_src/check.py' README.md || { echo "README 사이트 절(export·publish·check 명령) 없음"; return 1; }
  grep -q '^## 8\. ' reports/S6a_report.md 2>/dev/null || { echo "reports/S6a_report.md 8장까지 없음"; return 1; }
  [ ! -e site_src/style.css ] || { echo "site_src/style.css가 남음"; return 1; }
  local g
  g=$(grep -rIl "fonts.googleapis\|fonts.gstatic\|IBM Plex" site_src --exclude=check.py --exclude-dir=shots --exclude-dir=example --exclude-dir=__pycache__)
  [ -z "$g" ] || { echo "옛 Google Fonts 코드가 남음: $g"; return 1; }
}
if out=$(a13 2>&1); then pass A13 "README 사이트 절, reports/S6a_report.md 8장까지, style.css·옛 Google Fonts 코드 없음"; else fail A13 "$out"; fi

exit $FAILED
