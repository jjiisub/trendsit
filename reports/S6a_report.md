# S6a 리포트: 사이트 (DB → 화면 JSON, 디자인 시스템 v1, 발행 연결)

기준 main `3967cd4`, 브랜치 `s6a-site`. 명세 `docs/handoff/S6a_TASK.md`. 구현 런 `005-s6a` 1라운드(A1).

## 진행 체크리스트
- [x] S-1 data/ 정리(첫 커밋), verify_s5 B7·A17 호환 판정, export, 주차 표기, W40 근사 스크립트 (A14, A1, A2, A11)
- [x] S-2 build 다시 쓰기(읽기 + 관리 화면), 글꼴·CSS, 확인 필요 표기 (A3~A7)
- [x] S-3 check.py·gate.js, publish 연결, 원자 교체 (A8~A10, A12)
- [x] S-4 README, 리포트 (A13)
- [ ] 런 뒤(워크플로우 밖): W40 근사 실행, publish W40·W41, 실사이트 check, WebKit 캡처(7장)

## 1. 한 줄 요약
`trendsit export`가 published 주만 `data/site.json`(예시 JSON 구조)으로 꺼내고, `site_src/build.py`가 그것을 디자인 시스템 v1 마크업(홈·주차·토픽·소스·키워드·실행 기록)으로 임시 폴더에 빌드한 뒤 `site/`를 한 번에 교체한다. `publish`는 export → 빌드 순서이고 둘 중 하나가 실패하면 상태를 바꾸지 않는다. `site_src/check.py`가 정적 검사와 관문 9(Chromium·WebKit)·동작을 잰다. 워크플로우 안 유료 호출 0.

## 2. 관문 A 결과
`bash scripts/verify_s6a.sh`(구현 런의 관문과 같은 스크립트), 약 50초. 마지막 실행 FAIL 0줄. 항목: A0 ruff, A1·A2·A11(export·주차·W40 근사), A14(data/ 정리·B7/A17), A3·A4(도식·번호·확인 필요), A5~A10(check.py --fixture), A12(발행·원자 교체), A13(문서).
게이트 밖 전체 `uv run pytest -q`: 649 passed. 실데이터 사본(W40·W41을 임시 DB 사본에서 published 처리)으로 export → 임시 폴더 빌드 → `check.py` 13/13 통과(Chromium·WebKit 관문 9, 동작 포함).

## 3. 관문 B 결과
없음(LLM 역할 변경 없음).

## 4. 결정한 것 (명세 9장 "구현 시점 기본값" 포함)
- 읽는 시간 글자 범위: 토픽의 제목·요약·개요·포인트 글자(공백 제외) 합 ÷ 500 올림, 최소 1분
- 실행 1건 경로 `runs/<주>/<run_id>/`, 이번 주차 `runs/`(= 최신 주), 주차별 `runs/weeks/`. 매일 수집 run의 주는 export가 `week`로 줌(처리한 마지막 날의 ISO 주, 기록이 없으면 시작일 전날)
- 소스 표 정렬 채널 → 이름, 키워드 언급 수 `0 / 2 / 9 / 11`(왼쪽이 오래된 주), 미니 바 "출처 n" = 토픽 출처 수
- `weeks[].source_count` = 그 주 토픽들이 인용한 서로 다른 출처 수(채널+url), `collected` = items 표 채널별 개수
- `sources[].weeks[].used_in_topics` = 그 주 토픽이 근거로 쓴 서로 다른 구성원(글·영상·레포) 수. 레포는 `github_trending` 소스로 셈
- 레포 탭에 넣는 기준: 토픽 근거 레포 + 트렌딩 레포 중 (카드가 있으면 relevant, 없으면 키워드 필터 통과 + 한 줄 설명 있음). 별 많은 순, 별 없으면 뒤
- 신호 키: DB 값 `check`를 `needs_check`로 바꿔 내보내고 `signal_labels`는 trending·rising·release·needs_check(예시의 `new_trending`은 실제 의미와 달라 `trending`으로)
- 실행 기록의 `counts.review.needs_check`는 요약 칸(`check_points`, 라운드 누적이라 화면보다 큼)이 아니라 화면에 실제 표시되는 확인 필요 수(포인트 + 개요·요약·개념)
- `runs[].cost_usd`를 더함(키-값의 "비용" 원천이 필요). 반려 비교는 steps.detail에 `draft`·`evidence`가 있을 때만 `detail`로 내보냄
- 영상 타임라인(`type: video`, `marks`)은 `export_topic`이 만들지 않아 실데이터에는 없고 픽스처로만 검증한다(빌드는 지원)
- `check.py`의 "예시"·"동작 안 함" 검사는 site.json 본문 문자열을 뺀 화면 문구에만 적용(실제 글에 "예시"가 흔히 나옴)
- Python 3.12 f-string 문법(따옴표 중첩)을 `build.py`에서 씀. 시스템 `python3`은 3.14라 문제 없음
- `esc()`는 원문을 풀지 않고 한 번만 이스케이프하고, `nb_tokens`는 태그와 엔티티(`&#x27;` `&quot;` `&amp;` `&lt;`)를 건드리지 않는다(처음 구현은 엔티티 속 `x27`·`quot`를 토큰으로 감싸 화면에 글자로 찍혔음, 실데이터 사본 38건 → 0건). check.py M-1은 태그 중첩 어긋남과 엔티티가 태그로 쪼개진 곳만 실패시킨다(5장 F50)
- 매일 수집의 비용은 `summary_json.cost_usd`, 소스는 `sources.yaml`에 있는 것만(daily 칸 포함), `nightly_failed`는 partial·failed·stopped만
- ruff: 디자인 시안 복사본(`docs/reference/s6_design/drafts/*.py`) 머리에 `# ruff: noqa`(5장 F47)

## 5. 스펙과 다르게 한 것 (모두 명세 갱신은 기획 몫)
- **발행 직전의 주를 export에 담는 내부 인자(`export.export(db, out, with_week)`)**: `publish`는 status를 바꾸기 전에 export·빌드를 돌려야(S6b C-3) 하는데 export는 published 주만 담는다. 공개 CLI 옵션으로 열면 C-1을 우회할 수 있어(리뷰 F04) CLI에는 두지 않고 `ops.publish`가 함수로 직접 부른다. 결과는 `data/site.json.new`로 받아 그 파일로 빌드하고 성공했을 때만 `data/site.json`으로 바꾼다. 이 때문에 publish의 export는 실행기(runner)를 거치지 않는다
- **`runs`는 발행 주의 nightly만(C-1 우선)**: 명세 5.1 표의 "`kind='nightly'` 전부"와 C-1("runs는 그 주들 것만")이 충돌해 C-1을 따름. 명세 보완 필요
- `BUILD_CMD`는 `[sys.executable, "site_src/build.py"]`(run_ops.sh가 `uv run python -m trendsit`으로 부르므로 venv의 3.12). bare `python3`는 launchd 최소 PATH에서 3.9일 수 있어 build.py 문법(3.12)이 안 맞음
- **기존 테스트 2개 파일 수정**(예산 "변경하는 기존 파일 ≤ 8"에 테스트가 안 세어져 있음): `tests/test_ops.py`·`tests/test_ops_publish.py`가 publish의 호출 순서를 "빌드 1번"으로 단언하고 있어 "export → 빌드"로 고침(약화 아님, 순서를 더 엄격히 확인)
- 관문 9의 7번(토큰 밖 색)은 `shoot.py`가 허용하던 `rgb(0,0,0)`·흰색 추가를 빼고 tokens.css 색 10개만 허용(통과함)

- **C-5 "예시" 검사는 화면 문구만**: 실데이터 본문에 "예시"가 흔해(브리핑 글 자체) 사이트 전체 0회는 불가능해서 site.json 본문 문자열은 빼고 화면이 만든 문구만 검사한다(리뷰 F26 rejected)
- **`site/` 교체는 rename 두 번**(F30 rejected): 실행 폴더에서 `site`가 링크라 링크 교체 방식은 쓰지 않았고, 두 번째 rename이 실패하면 이전 사이트를 되돌린다
- **매일 수집 runs의 steps에는 `t`가 없다**: 원천(`summary_json.steps`)에 시각이 없어 칸을 뺐다(D-11 "못 만드는 칸은 뺌"). build는 `t`가 없으면 시각 열을 그리지 않는다
- **`.gitignore` 두 줄(`/site.tmp-*`, `/site.old`)**: 명세 3.1 0번이 정한 변경 밖이지만 build의 임시 폴더 이름 때문에 필요(F32 수용)
- **실행 1건 화면**: `.rail`은 명세 5.6대로 steps의 역할 문장, counts는 키-값(`.kv`)으로 보인다
- **verify_s6a의 ruff 우회 제거(F47)**: `docs/reference/s6_design/drafts/common.py`·`shoot.py`(참고 복사본) 머리에 `# ruff: noqa`를 넣고 pyproject는 그대로 둔다. `--extend-exclude docs/reference`를 뺐고 `uv run ruff check .`가 전체에서 통과한다(이전 스펙 verify의 ruff 항목 회귀 해소)
- **M-1은 빌드가 만든 깨짐만(F50)**: `esc()`는 원문을 풀지 않고 한 번만 이스케이프해 본문의 `<span`·`&amp;` 글자가 화면에 그대로 보인다. M-1은 태그 중첩 어긋남과 "엔티티가 태그로 쪼개짐(`&#<span`)"만 잡는다(데이터 원문 글자로 오탐 없음)
- **내부 근거 id 제거(F68)**: 도식 설명(`context`) 끝의 `[it:8#q2]`·`[it:924#q3, it:924#q4]`는 build가 화면에 내기 전에 뺀다(brief/는 건드리지 않음). check.py에 M-2(`[it:`·`#q숫자` 노출 0)를 추가, 픽스처 도식 설명 2곳에 해당 표기를 넣어 둠
- **publish의 export 예외(F53)**: ExportError·sqlite3.Error뿐 아니라 어떤 예외든 잡아 종료 1과 이유 한 줄(`export 실패: 예외이름: 내용`)을 남기고 상태는 그대로 둔다
- **build 시작 시 복구(F59)**: `site/`가 없고 `site.old`가 있으면 되살린 뒤 시작한다
- **C-6 측정 확장(F64)**: gate.js가 오른쪽 테두리·outline·text-decoration 색과 box-shadow 색도 토큰 10개와 대조한다. 단, 검정+투명도 그림자(툴팁의 `rgb(0 0 0 / .08)`, 복사본 CSS 그대로)는 색이 아니라 깊이 표현이라 뺀다
- **소스 화면 GitHub Trending 수집 수(F69)**: `github_trending`의 주별 `collected`는 items가 아니라 그 주 `repo_trending` 행 수. 레포 설명은 `repo_oneliners`에서만 읽는다(F57, 레포 카드에 없는 칸을 읽던 죽은 분기 제거)
- **check.py `--site`·`--data` 옵션**: 명세에는 없는 옵션. 7장 QA("그 폴더에 check 실행")에 필요해서 둠
- **`.gitignore` 두 줄(`/site.tmp-*`, `/site.old`)**: 위에 적은 대로 build의 임시 폴더 때문에 추가(명세 3.1 0번 밖)
- `weeks[].start·end`는 쓰는 곳이 없어 내보내지 않는다. 키워드 관련 토픽·`used_in_topics`는 사이트에 실린 토픽만 센다

## 6. 남은 문제, 다음 스펙 제안
- 원자 교체는 `rename` 두 번(옛 폴더 → .old, 새 폴더 → site)이라 그 사이 수 ms는 `site/`가 없다. 정적 서버가 그 요청에 404를 줄 수 있음(발행은 월요일 한 번)
- 실데이터 반려 비교(`.cmp`)는 안 나온다: 실제 `steps.detail`에 초안·근거 쌍이 없다(D-12는 예시 steps 모양을 전제). 나오게 하려면 검수 단계가 draft/evidence를 detail에 남겨야 함(S5 쪽)
- 홈 메타 "/ 확인 필요"는 명세대로 `has_check`(빠진 도식만 있는 토픽 포함)를 따르는데 토픽 화면에는 그때 표기가 없다
- 실행 폴더 1회 정리(`fetch` + `reset --hard origin/main`)는 병합 절차(7장), 이 구현에서 하지 않음

- **기획에 넘길 것(C1 #1)**: 레포 목록 원천은 명세 5.1이 "repo_trending(그 주 마지막 수집 run)"인데, `repo_trending`은 `(week, full_name)` upsert라 주에 수집 run 행이 여럿 섞여 있다. 구현은 run을 가리지 않고 그 주의 모든 수집 run 행을 쓴다. 명세 글자대로(마지막 run만)면 실데이터 W41 레포가 0개가 된다(마지막 run의 레포 9개는 카드·한 줄 설명이 없어 빠짐). "그 주 누적 + 카드·설명 있는 것"으로 명세를 고칠지 정해야 한다

## 7. 런 뒤 단계 (워크플로우 밖, 2026-10-11 13:44~13:46)
자동 모드가 실제 DB 쓰기를 막아 ①②는 사용자가 터미널에서 직접 실행했다(명령은 명세 그대로).
- ① `scripts/trending_monthly.py --week 2026-W40`: "근사 목록 10개 저장(월간 23개 중 뒤 주 레포 제외 뒤 상위)". runs `20261011-134409-collect-35c2`(note `trending monthly approx`) + oneliner run `20261011-134409-role-d397` **$0.0020**(S6a 상한 $0.10). stars_this_week NULL
- ② `publish --week 2026-W40` → 13:44:35, `--week 2026-W41` → 13:44:50 published. 공개 사이트 trendsit.jiseop.com이 새 디자인으로 바뀜: html **31쪽**(홈·주차 2·토픽 20·소스·키워드·실행 기록), 예시 사이트 전부 교체
- ③ `check.py`(실사이트 site/): **14/14 통과**(C-3~C-7, M-1·M-2, A5~A7, A8 Chromium 21건, A9 WebKit 375 터치 14건, A10)
- ④ 공개 주소 WebKit 375(모바일·터치) 캡처, 세 쪽 모두 200·가로 넘침 0(scrollWidth 375)
  - 홈: `reports/S6a/webkit375_home.png`
  - 홈 레포 탭(`#repos`): `reports/S6a/webkit375_home-repos.png`
  - 토픽 `w41-claude-haiku-5-5`: `reports/S6a/webkit375_topic.png`
- 정리 전 DB 백업은 자동 모드가 같이 막아 만들지 못했다. 바뀐 것은 repo_trending W40 10행·repo_oneliners·runs 2행·weeks 2행 상태다

## 8. impl-workflow SUMMARY 요약
라운드 A1 구현 완료, 게이트(`verify_s6a.sh`) 통과. 변경 기존 파일 8(`.gitignore`, `README.md`, `scripts/verify_s5.sh`, `site_src/build.py`, `site_src/check.py`, `trendsit/ops.py`, `trendsit/cli_ops.py`, `style.css` 삭제) + 목록 밖 4(`tests/test_ops.py`, `tests/test_ops_publish.py`, `docs/reference/s6_design/drafts/common.py`·`shoot.py`의 `# ruff: noqa`) = 12로 예산 ≤ 8 초과(테스트 2는 5장, drafts 2는 F47), 새 파일 14, 옮긴 파일 2, 새 의존성 0, `build.py` 566줄(≤ 1050).
