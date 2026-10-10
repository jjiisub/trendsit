#!/usr/bin/env bash
# S4 관문 A(S4_TASK 6장). 항목마다 PASS/FAIL과 이유를 한 줄씩, 하나라도 FAIL이면 종료 코드 1.
# 맥에서는 video 선택 묶음을 넣고(uv run --extra video) 맥 전용 테스트까지 돈다. 그 밖에서는 그 테스트만 건너뜀 표시.
set -u
cd "$(dirname "$0")/.."
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
EXTRA=()
[ "$(uname -s)" = "Darwin" ] && EXTRA=(--extra video)

source scripts/verify_common.sh

# A1 회귀
for s in 0 1; do
  [ -n "${VERIFY_NESTED:-}" ] && continue
  if bash "scripts/verify_s$s.sh" >"$TMP/s$s" 2>&1; then :; else fail A1 "verify_s$s.sh: $(grep '^FAIL' "$TMP/s$s" | head -2 | tr '\n' ' ')"; fi
done
if [ -n "${VERIFY_NESTED:-}" ]; then
  echo "SKIP A1 verify_s5가 s0·s1을 이미 실행함"
elif ! grep -q '^FAIL' "$TMP/s0" "$TMP/s1"; then pass A1 "verify_s0.sh $(grep -c '^PASS' "$TMP/s0")개, verify_s1.sh $(grep -c '^PASS' "$TMP/s1")개 전부 PASS"; fi

# A2 정적 검사, 테스트(맥 전용은 mac_video 표시 하나로만 건너뜀)
if uv run --quiet "${EXTRA[@]}" ruff check . >"$TMP/ruff" 2>&1 && uv run --quiet "${EXTRA[@]}" pytest -q -rs >"$TMP/pt" 2>&1; then
  skips=$(grep -c '^SKIPPED' "$TMP/pt" || true)
  # 허용: 맥 전용(video 묶음) + S2 실제 임베더 테스트의 embed 묶음 없음(이 스크립트는 --extra video만 넣음)
  other=$(grep '^SKIPPED' "$TMP/pt" | grep -v 'video 묶음' | grep -vc 'embed 선택 묶음 없음' || true)
  if [ "$other" = "0" ]; then pass A2 "ruff 0, pytest $(tail -1 "$TMP/pt") (건너뜀 ${skips}건은 맥 전용·embed 묶음 표시뿐)"; else fail A2 "허용 밖의 건너뜀 ${other}건"; fi
else
  fail A2 "$(tail -1 "$TMP/ruff") / $(tail -1 "$TMP/pt")"
fi

# A3 설정
if uv run --quiet python -m trendsit check-config >"$TMP/cc" 2>&1; then
  pt A3 "check-config 통과($(cat "$TMP/cc")) + 잘못된 mode·상한이 경로를 짚어 실패" tests/test_s4_media.py -k "video_config"
else
  fail A3 "$(head -2 "$TMP/cc" | tr '\n' ' ')"
fi

# A4 역할 md(검사 통과 + 예시 3개)
A4_MISS=""
for r in video_slide video_summary; do
  n=$(grep -c '^<example>' "roles/$r.md")
  [ "$n" = "3" ] || A4_MISS+=" $r:예시${n}개"
done
if [ -z "$A4_MISS" ]; then pt A4 "video_slide, video_summary 역할 md 검사 통과, 예시 3개" tests/test_s1a.py -k "lint"; else fail A4 "$A4_MISS"; fi

pt A5 "픽스처 MediaResult 계약 통과 + 깨뜨린 사본(시간 역순, 상한 초과, 작업 폴더 밖 경로 등) 실패" tests/test_s4_media.py -k "fixtures_exist or contract_rejects"
pt A6 "큐 계약 JSON → mode별 설정, captions에 수동 자막 없으면 건너뜀(올리지 않음)" tests/test_s4_media.py tests/test_s4_pipeline.py -k "queue or captions"
pt A7 "suspect_hallucination·empty에서 전사를 근거로 쓰지 않음, 둘 다 없으면 내용 없음 + attention" tests/test_s4_pipeline.py tests/test_s4_roles.py -k "bad_transcript or no_sources or no_content"
pt A8 "대조: 다른 표기의 같은 수치는 대조됨, 30초 밖은 slide_only, check는 따로" tests/test_s4_align.py
pt A9 "enforce: 판독 수치(ocr_text 안), 표기 쌍, 근거·타임라인 초 범위(모의 LLM)" tests/test_s4_roles.py -k "slide_numbers or non_slide or summary_enforce"
pt A10 "이미지 입력: 메시지 모양, 캐시 키가 이미지 바이트에 따름, 기록·캐시에 원본 없음, 예상 비용" tests/test_s4_roles.py -k "message_shape or transport_gets or cache_key or estimate or changed_image"
pt A11 "보관: purge는 7일 지난 작업 폴더만, DB 텍스트 유지, 8주 지난 segments 텍스트 삭제" tests/test_s4_media.py tests/test_s4_pipeline.py -k "purge or segment_text"
pt A12 "마이그레이션 대역: S4 번호 모두 20~29, video_ 표만, 묶음 A 번호와 순서 무관" tests/test_s4_pipeline.py -k "migrations or either_order"
pt A13 "자동 자막 경로 없음(자동 자막만 있는 메타데이터에서 captions는 건너뜀)" tests/test_s4_media.py -k "auto_caption"

# A14 문서
A14_MISS=""
grep -q "trendsit video run" README.md || A14_MISS+=" README:video run"
grep -qi "ffmpeg" README.md || A14_MISS+=" README:ffmpeg"
grep -q "JS 런타임" README.md || A14_MISS+=" README:JS 런타임"
grep -q "영상 분석가" README.md || A14_MISS+=" README:기능"
grep -q "trendsit video" docs/DEVELOPMENT.md || A14_MISS+=" DEVELOPMENT:video"
[ -f reports/S4_report.md ] || A14_MISS+=" reports/S4_report.md"
[ -z "$A14_MISS" ] && pass A14 "README(기능, 빠른 시작, 시스템 의존성), DEVELOPMENT.md 명령표, 리포트" || fail A14 "없음:$A14_MISS"

exit $FAILED
