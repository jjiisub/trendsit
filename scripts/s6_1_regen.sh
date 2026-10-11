#!/usr/bin/env bash
# S6-1 7장 런 뒤 ①~⑤를 한 번에(D-46). 실DB에 쓴다(backup·weekly·publish): 사용자 승인 뒤에만 돌린다.
# 한 단계라도 실패하면 거기서 멈추고 종료 코드 1. 사용: bash scripts/s6_1_regen.sh
set -eu
cd "$(dirname "$0")/.."

echo "== ① 영상 파일 확인 =="
for vid in S-bRN-avZ4Q D7q8fa589FY; do
  if ! ls "data/media/$vid"/media.* >/dev/null 2>&1; then
    echo "data/media/$vid/media.*가 없음(7일 보관 기간이 지났을 수 있음): 슬라이드 없이 진행"
  fi
done

echo "== ② trendsit backup --tag pre-s6-1 =="
uv run python -m trendsit backup --tag pre-s6-1

echo "== ③ weekly --force --spec S6-1(W40, W41) =="
uv run --extra embed python -m trendsit weekly --week 2026-W40 --force --spec S6-1
uv run python -m trendsit cost --spec S6-1
uv run --extra embed python -m trendsit weekly --week 2026-W41 --force --spec S6-1
uv run python -m trendsit cost --spec S6-1

echo "== ④ 읽기본 확인(손으로 reports/S5_brief/briefing_<week>.md 훑기) =="
echo "reports/S5_brief/briefing_2026-W40.md, briefing_2026-W41.md을 열어 작성 실패·⚠ 수를 리포트에 적을 것"

echo "== ⑤ publish → check.py(실사이트) → WebKit 375 캡처 =="
uv run python -m trendsit publish --week 2026-W40
uv run python -m trendsit publish --week 2026-W41
python3 site_src/check.py
echo "실사이트(trendsit.jiseop.com) 홈·토픽 2개(표·슬라이드) 캡처를 reports/S6-1/shots/에 손으로 추가할 것"

echo "모두 끝남. reports/S6-1_report.md 7장을 이 실행 결과로 채우고, ⑥(eval 픽스처 재생성)·⑦(리뷰·커밋)은 그 뒤 손으로"
