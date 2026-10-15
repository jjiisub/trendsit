# 추가 작업 지시서 05: 문체 변경 + 2차 리뷰 반영

> 대상: 맥 Claude Code (`~/Claude/projects/trendsit`). 작성 2026-10-06. **04 지시서(파비콘, 공유 미리보기, 1차 리뷰)를 끝낸 뒤** 진행한다. `docs/archive/03_TASK.md`의 규칙과 금지 사항은 그대로.

## 0. 받은 파일 (이 문서와 같은 폴더)
| 파일 | 바뀐 점 |
|---|---|
| `data/trendsit-example.json` | 표시 문장 문체 변경(해요체 → 요약, 개요 "~다" / 포인트, 설명 명사형). **구조, 숫자, id, 형광 위치는 같음** |
| `data/make_data.py` | 위 JSON 생성 스크립트 (참고용) |
| `docs/archive/02_DESIGN.md` | 10장 "문체" 추가(규칙 + 화면 고정 문구 표), 6.3~6.5 예시 문구 변경, PC 관리 화면 왼쪽 정렬로 수정 |
| `docs/01_CONTEXT.md` | 결정 기록에 문체, 파비콘 추가 |

## 1. 파일 교체
```bash
H="/절대/경로/trendsit-update-05"      # 이 문서가 있는 폴더로 바꿀 것
P="$HOME/Claude/projects/trendsit"
[ -f "$H/05_TASK_문체_2차리뷰.md" ] || { echo "H is wrong"; exit 1; }
cp "$P/data/trendsit-example.json" "$P/data/trendsit-example.before05.json"
cp "$H/data/trendsit-example.json" "$H/data/make_data.py" "$P/data/"
cp "$H/docs/archive/02_DESIGN.md" "$H/docs/01_CONTEXT.md" "$P/docs/"
python3 - "$P/data/trendsit-example.before05.json" "$P/data/trendsit-example.json" <<'PY'
import json,sys
a,b=[json.load(open(x)) for x in sys.argv[1:]]
def shape(x):
    if isinstance(x,dict): return {k:shape(v) for k,v in x.items()}
    if isinstance(x,list): return [shape(v) for v in x]
    return type(x).__name__
print("same structure:", shape(a)==shape(b))
PY
```
- `CLAUDE.md`는 사용자가 고쳤을 수 있으니 덮어쓰지 말고, `docs/01_CONTEXT.md`의 "16. 결정 기록" 마지막 두 줄과 "11. 화면"의 문체 줄만 옮겨 넣는다(내용이 이미 있으면 건너뜀)
- 완료 기준: `same structure: True`. False면 멈추고 보고

## 2. 문체 반영
1. 데이터에서 오는 문장은 1번 교체로 끝. 빌드만 다시 한다
2. 템플릿에 직접 쓴 문구를 `docs/archive/02_DESIGN.md` 10장 "화면 고정 문구" 표대로 바꾼다. 표에 없는 문구도 같은 규칙(명사형, 질문으로 끝내지 않음)
   - 예: "예시 사이트라 동작하지 않아요" → "예시 사이트라 동작 안 함", "<키워드>의 별칭으로 묶을까요?" → "묶을 키워드: <키워드>", 소스 머리, "확인할 것", 소스 연결도 캡션, 실행 기록 상위 요약과 안내
3. 확인(0이어야 함):
```bash
cd "$HOME/Claude/projects/trendsit"
grep -rhoE "[가-힣]+(어요|에요|해요|예요|까요|세요|돼요|줘요)" site | sort | uniq -c
```

## 3. 2차 리뷰 반영
1. **매일 수집 상세의 실패 중복**: `errors[]`는 맨 위 형광 한 줄로만 보여 주고, 판단 로그에는 "수집기" 줄을 만들지 않는다. 역할 탭 숫자는 `steps[]`만 센다
2. **역할 탭 표기**: "전체 (2)" → "전체 2 / 편집장 1 / 레포 분석가 1"처럼 괄호 없이, 탭 사이 글자 구분(04의 `.sr-sep` 또는 보이는 " / ")
3. **지난 주차 실행 상세 문구**: 최신 주차가 아닌 실행의 정보 표 "입력: 이번 주 수집 45건" → "입력: 이 주 수집 45건". 메인, 상위 화면에도 "이번 주"가 지난 주차에 나오는 곳이 있으면 같은 규칙
4. **형광 변환 확인**: `grep -c "==" site/index.html site/week/*/index.html site/topic/*/index.html site/runs/*/index.html site/runs/*/*/index.html` 결과가 모두 0

## 4. 확인과 보고
- `python3 site_src/build.py` → `site_src/check.py` 통과 + 위 2-3, 3-4 확인 결과 0
- 바뀐 화면 몇 개를 사용자가 볼 수 있게 경로 안내: `/`, `/topic/w40-jev-race/`, `/sources/`, `/keywords/`, `/runs/2026-w40/nightly-2026-10-03/`
- 보고: 바꾼 파일, 확인 결과, 문체 규칙을 적용하기 애매했던 문구 목록(있으면)
