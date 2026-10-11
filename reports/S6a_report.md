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
`bash scripts/verify_s6a.sh`(= `.workflow/gate.sh`), 약 50초. 마지막 실행 FAIL 0줄(원문은 `.workflow/005-s6a/A1-impl.md`). 항목: A0 ruff, A1·A2·A11(export·주차·W40 근사), A14(data/ 정리·B7/A17), A3·A4(도식·번호·확인 필요), A5~A10(check.py --fixture), A12(발행·원자 교체), A13(문서).
게이트 밖 전체 `uv run pytest -q`: 626 passed. 실데이터 사본(W40·W41을 임시 DB 사본에서 published 처리)으로 export → 임시 폴더 빌드 → `check.py` 13/13 통과(Chromium·WebKit 관문 9, 동작 포함).

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
- `esc()`는 원문에 이미 들어 있는 `&#x27;` 같은 엔티티를 풀어 한 번만 이스케이프하고, `nb_tokens`는 태그와 엔티티(`&#x27;` `&quot;` `&amp;` `&lt;`)를 건드리지 않는다(처음 구현은 엔티티 속 `x27`·`quot`를 토큰으로 감싸 화면에 글자로 찍혔음, 실데이터 사본 38건 → 0건). check.py M-1이 렌더된 글자에 엔티티·마크업 조각이 보이면 실패시킨다
- 매일 수집의 비용은 `summary_json.cost_usd`, 소스는 `sources.yaml`에 있는 것만(daily 칸 포함), `nightly_failed`는 partial·failed·stopped만
- ruff는 `docs/reference`(디자인 시안 복사본, E702 등)를 `--extend-exclude`로 뺌(pyproject 변경 없이)

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
- `weeks[].start·end`는 쓰는 곳이 없어 내보내지 않는다. 키워드 관련 토픽·`used_in_topics`는 사이트에 실린 토픽만 센다

## 6. 남은 문제, 다음 스펙 제안
- 원자 교체는 `rename` 두 번(옛 폴더 → .old, 새 폴더 → site)이라 그 사이 수 ms는 `site/`가 없다. 정적 서버가 그 요청에 404를 줄 수 있음(발행은 월요일 한 번)
- 실데이터 반려 비교(`.cmp`)는 안 나온다: 실제 `steps.detail`에 초안·근거 쌍이 없다(D-12는 예시 steps 모양을 전제). 나오게 하려면 검수 단계가 draft/evidence를 detail에 남겨야 함(S5 쪽)
- 홈 메타 "/ 확인 필요"는 명세대로 `has_check`(빠진 도식만 있는 토픽 포함)를 따르는데 토픽 화면에는 그때 표기가 없다
- 실행 폴더 1회 정리(`fetch` + `reset --hard origin/main`)는 병합 절차(7장), 이 구현에서 하지 않음

## 7. 런 뒤 단계 (워크플로우 밖, 구현 세션)
이 리포트 작성 시점에는 하지 않았다(실제 DB·사이트 불변, 유료 호출 0 약속). ① `uv run python scripts/trending_monthly.py --week 2026-W40` ② `trendsit publish --week 2026-W40`, `--week 2026-W41` ③ `python3 site_src/check.py` ④ trendsit.jiseop.com WebKit 375 캡처(홈·토픽 1개).

## 8. impl-workflow SUMMARY 요약
라운드 A1 구현 완료, 게이트(`verify_s6a.sh`) 통과. 변경 기존 파일 8(`.gitignore`, `README.md`, `scripts/verify_s5.sh`, `site_src/build.py`, `site_src/check.py`, `trendsit/ops.py`, `trendsit/cli_ops.py`, `style.css` 삭제) + 테스트 2(위 5장), 새 파일 14, 옮긴 파일 2, 새 의존성 0, `build.py` 549줄(≤ 1050).
