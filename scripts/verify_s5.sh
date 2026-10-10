#!/usr/bin/env bash
# S5 관문 A(S5_TASK 6장). 항목마다 PASS/FAIL과 이유를 한 줄씩, 하나라도 FAIL이면 종료 코드 1.
set -u
cd "$(dirname "$0")/.."
FAST=0
[ "${1:-}" = "--fast" ] && FAST=1  # A1(s0~s4 회귀 재실행)만 건너뜀. A2의 전체 pytest가 s0~s4 테스트를 포함
FAILED=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
EXTRA=(--extra video --extra embed)  # 건너뜀 0은 두 extra 모두에서(리뷰 R16)

source scripts/verify_common.sh

# A1 회귀: 종료 코드로 판정(리뷰 R16)
if [ "$FAST" = 1 ]; then
  echo "SKIP A1 --fast: verify_s0~s4 재실행 생략(A2 전체 pytest가 s0~s4 테스트 포함)"
else
  a1_bad=""
  mkdir "$TMP/reuse"
  for s in 0 1 2 3 4; do
    # s1~s4가 앞 스펙 회귀를 다시 돌리지 않고 이미 나온 출력을 쓰게 한다(--reuse). s0~s4가 각각 한 번만 돌고 PASS 줄은 그대로
    rc=0
    if [ "$s" = 0 ]; then bash scripts/verify_s0.sh >"$TMP/reuse/s0" 2>&1 || rc=$?
    else bash "scripts/verify_s$s.sh" --reuse "$TMP/reuse" >"$TMP/reuse/s$s" 2>&1 || rc=$?; fi
    echo "$rc" >"$TMP/reuse/s$s.rc"
    [ "$rc" = 0 ] || a1_bad="$a1_bad s$s"
  done
  if [ -n "$a1_bad" ]; then
    fail A1 "종료 코드 실패:${a1_bad} / $(grep -h '^FAIL' "$TMP"/reuse/s[0-4] | head -3 | tr '\n' ' ')"
  else
    pass A1 "verify_s0~s4 종료 코드 0, PASS $(cat "$TMP"/reuse/s[0-4] | grep -c '^PASS')개"
  fi
fi

# A2 정적 검사, 테스트(건너뜀 0)
if uv run --quiet "${EXTRA[@]}" ruff check . >"$TMP/ruff" 2>&1 && uv run --quiet "${EXTRA[@]}" pytest -q -rs >"$TMP/pt" 2>&1; then
  skips=$(grep -c '^SKIPPED' "$TMP/pt" || true)
  if [ "$skips" = "0" ]; then pass A2 "ruff 0, pytest $(tail -1 "$TMP/pt"), 건너뜀 0"; else fail A2 "건너뜀 ${skips}건"; fi
else
  fail A2 "$(tail -1 "$TMP/ruff") / $(tail -1 "$TMP/pt")"
fi

# A3 설정: brief.yaml, budget S5, 역할 md 5개
roles_ok=1
for r in decide editor_select writer writer_revise critic; do [ -f "roles/$r.md" ] || roles_ok=0; done
if uv run --quiet python -m trendsit check-config >"$TMP/cc" 2>&1 \
   && grep -q 'S5:' config/budget.yaml && [ "$roles_ok" = 1 ]; then
  pass A3 "check-config $(cat "$TMP/cc"), budget S5 있음, 역할 md 5개(decide, editor_select, writer, writer_revise, critic) 섹션 검사 포함"
else
  fail A3 "$(grep FAIL "$TMP/cc" | head -3 | tr '\n' ' ') 역할 md 5개 존재=$roles_ok"
fi

pt A4 "공통 수정 5.1(명사 예외, ImageError 계열, 중첩 ImageFile 거부, ClassVar, 예산 기준값 위치, 수치 모듈) + 출력 잘림 감지" tests/test_s5_common.py
pt A5 "근거 목록(자격, 근거 id 형식, 입력 상한과 뺀 근거)" tests/test_s5_evidence.py -k "eligibility or v2 or cap_pack"
pt A6 "정규화(표기 차이만 자동 승인, 숫자·버전 다른 쌍 후보 아님, name_pairs 전역 미반영)" tests/test_s5_evidence.py -k "version or spelling or name_pairs or decided"
pt A7 "묶기(채널 넘는 조건, confidence 미달, 평균 연결, 레포만 묶음, 1개짜리, 재실행 run 보존)" tests/test_s5_cluster.py

pt A8 "선별 검증(리드 1, 개수 범위, 범위 밖 합치기·나누기 거부, relation은 과거 대조 후보 안, 입력 순서 cluster_id, reason 값·채널 수 대조, 재시도·대체, 점수 동점은 관심 유사도(C-21 수정), 영상 자리(C-20))" \
  tests/test_s5_select_checks.py tests/test_s5_weekly.py -k "valid or reject or max_topics or order or reason or slug or retries or reconcile or c20 or c21 or r14"
pt A9 "코드 검사(수치 대조 값 비교·제목·도식 칸까지·단위 환산 미허용, 막대 단위·빈 단위·라벨 단위, anchor, 도식 상한, 금지어·전망형, contributions 채널, points 자르기, 음차 정본, 자동 수정은 반려 아님, 경고)" \
  tests/test_s5_select_checks.py tests/test_s5_evidence.py -k "clean or number or anchor or forbidden or alias or unknown or warnings or noun or reset or unit or bar or r3 or r4 or r11 or f1 or f3 or f7 or f11 or g2 or g3 or g7 or h1"
pt A10 "라운드(상한 3, 코드 반려도 셈, 같은 이슈 2회 check, 지적 안 된 칸 되돌림, 1부터 센 위치 바로잡기, 원자 사실 0개 판정 거부, 도식은 코드 확인 오류만 뺌, 목록 위치 add·채널 없는 기여 문장)" tests/test_s5_weekly.py tests/test_s5_select_checks.py -k "rounds or one_based or empty_atoms or f2 or diagram_issue or g6"
pt A11 "저장(마이그레이션 30~35, 재실행 run 보존·current_run_id, topic_evidence = 최종판 refs, 토픽 수준 확인 필요)" \
  tests/test_s5_weekly.py tests/test_s5_cluster.py -k "rounds or stage_cluster"
pt A12 "실행 요약 JSON 형식과 표에서 다시 계산한 값 일치" tests/test_s5_weekly.py -k rounds
pt A13 "저장값만으로 예시 JSON 토픽 칸(매핑 함수 초안: numbers·events·og 출처 origin·checks)" tests/test_s5_weekly.py -k "rounds or export"

# A14 문서: README S5, 리포트 체크리스트, reports/eval 역할·모델별 최신 1개(라벨이 가리키는 실행은 예외)
labeled=$(grep -ho 'reports/eval/[a-z_]*_[0-9-]*\.json' eval/labels/* 2>/dev/null | sort -u)
extra=$(ls reports/eval/*.json | sed 's#.*/##' | sed -E 's/_[0-9]{8}-[0-9]{6}\.json$//' | sort | uniq -c | awk '$1>1{print $2}')
over=""
for k in $extra; do
  n2=$(for f in reports/eval/${k}_*.json; do echo "$labeled" | grep -qx "$f" || echo "$f"; done | wc -l | tr -d ' ')
  [ "$n2" -gt 1 ] && over="$over $k($n2)"
done
if grep -q 'S5' README.md && grep -q '진행 체크리스트' reports/S5_report.md && [ -z "$over" ]; then
  pass A14 "README S5 상태, S5_report 체크리스트, reports/eval 역할·모델별 최신 1개(+ 라벨 기준 실행)"
else
  fail A14 "README/리포트/eval 정리 확인:${over}"
fi

# ---------- S5-1a: 리팩터 불변(프롬프트, 코드 검사 결과, CLI 도움말) ----------
if uv run --quiet python scripts/s5_1_prompts.py --diff reports/S5-1/prompts_before.json >"$TMP/a15" 2>&1; then
  pass A15 "프롬프트 불변(역할별 system·스키마·픽스처 메시지 sha256 동일)"
else
  fail A15 "$(head -1 "$TMP/a15")"
fi
if uv run --quiet python scripts/s5_1_golden.py --out "$TMP/g.json" >"$TMP/a16" 2>&1 && diff -q "$TMP/g.json" reports/S5-1/golden_before.json >/dev/null; then
  pass A16 "코드 검사 결과 불변(W40·W41 현재판 모든 라운드의 issues·autofix·warnings)"
else
  fail A16 "골든 차이 또는 실행 실패: $(head -1 "$TMP/a16")"
fi
if help_all >"$TMP/help.txt" 2>&1 && diff -q "$TMP/help.txt" reports/S5-1/help_before.txt >/dev/null; then
  pass A17 "CLI --help 전부 불변"
else
  fail A17 "--help 차이: $(diff "$TMP/help.txt" reports/S5-1/help_before.txt | head -2 | tr '\n' ' ')"
fi
# A18 효과 없는 설정 키 0(S5-1a 5.7 표): yaml은 주석을 떼고, 스키마(core/config*.py)는 필드 정의 줄에서 찾는다
DEAD='auto_approve|linkage|per_point_max|runtime|weekly_target_minutes|lang|channel_handle|why|paths|video_max_minutes|frames_per_slide_video'
dead=$(for f in config/*.yaml; do sed 's/#.*//' "$f" | grep -nE "(^|[[:space:]{,-])($DEAD):" | sed "s#^#$f:#"; done
       grep -nE "^[[:space:]]+($DEAD)[[:space:]]*:" trendsit/core/config*.py)
if [ -z "$dead" ] && uv run --quiet python -m trendsit check-config >"$TMP/a18" 2>&1; then
  pass A18 "삭제 대상 설정 키 0건, $(cat "$TMP/a18")"
else
  fail A18 "남은 키: $(echo "$dead" | head -3 | tr '\n' ' ') / $(tail -1 "$TMP/a18")"
fi
pt A19 "예산 초과 시 멈춤(write·select·cluster 도중 BudgetExceeded: 현재판 불변, run stopped, 종료 코드 1, 남은 일 시작 0)" tests/test_s5_weekly.py -k budget_stop
pt A20 "실행 요약 상태(전부 실패 failed, 일부 partial, 예산 stopped)" -k summary_status
pt A21 "read_more 열쇠(fetch_page가 저장한 열쇠로 찾음: github 대문자, http, arxiv pdf)" -k read_more_page_key
# A22 지운 코드가 없음(S5-1a 5.8)
gone=$(uv run --quiet python - <<'PY'
from trendsit.core.artifacts import RoleOutput  # noqa: F401
from trendsit.core.artifacts_brief import BriefingPlan, FactCheck, ReviewVerdict, TopicPage, TopicPageRevision
from trendsit.core.artifacts_text import CollectionPlan
from trendsit.core.artifacts_video import SlideReading
print(" ".join(c.__name__ for c in (BriefingPlan, TopicPage, TopicPageRevision, ReviewVerdict, FactCheck, SlideReading, CollectionPlan)
               if "fallback" in vars(c)))
PY
)
gone="$gone$([ -e trendsit/collect/video/settings.py ] && echo ' settings.py')"
gone="$gone $(grep -rnE --include='*.py' 'def (as_dicts|have_tools)\b' trendsit | head -2 | tr '\n' ' ')"
gone="$gone $(grep -nE 'def score\(.*trend|키워드 추세|def save\(.*truncated' trendsit/brief/cluster.py | tr '\n' ' ')"
gone="$gone $(grep -nE 'def sources_index.*tuple' trendsit/brief/briefing.py)"
if [ -z "$(echo "$gone" | tr -d ' ')" ]; then pass A22 "fallback() 7개, collect/video/settings.py, F-18 이름 모두 없음"; else fail A22 "남아 있음: $gone"; fi

# A23 trendsit/ 순 줄 수 감소(a259b99 기준)
stat=$(git diff --shortstat a259b99 -- trendsit/)
ins=$(echo "$stat" | sed -nE 's/.* ([0-9]+) insertion.*/\1/p'); del=$(echo "$stat" | sed -nE 's/.* ([0-9]+) deletion.*/\1/p')
if [ "${del:-0}" -gt "${ins:-0}" ]; then pass A23 "trendsit/ 추가 ${ins:-0}줄 < 삭제 ${del:-0}줄"; else fail A23 "순 감소 아님: $stat"; fi

# A24 리포트·README
if [ -f reports/S5-1a_report.md ] && grep -q '\[x\]' reports/S5-1a_report.md && ! grep -q '\[ \]' reports/S5-1a_report.md \
   && grep '현재 상태' README.md | grep -q 'S5-1a'; then
  pass A24 "S5-1a_report 체크리스트 전부 [x], README 현재 상태에 S5-1a"
else
  fail A24 "reports/S5-1a_report.md 체크리스트 또는 README 현재 상태 줄"
fi
exit $FAILED
