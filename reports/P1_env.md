# P1 작업 환경 정리 리포트

기준: main d7c89d4. 2026-10-09 실행. LLM 사용액 $0(collect만, 캐시 확인은 가짜 키로 호출 차단).
data/는 git 밖이라 수치는 이 리포트에만 남긴다.

## 1. DB·작업 폴더 통합

main 작업 폴더를 `s1-collect` → main으로 옮긴 뒤, 세 DB를 main `data/trendsit.db` 하나로 합쳤다.

### 옮기기 전 상태

| 표 | main | s2s3 | s4 |
|---|---|---|---|
| 마이그레이션 | 기록 표 없음(user_version 2) | 1,2,10~13,20 | 1,2,20 |
| items | 343 | 355 | 60(영상만, id 1~60) |
| item_cards / item_relevance | – | 269 / 325 | – |
| repo_trending / repo_cards | 11 / – | 11 / 7 | 0 / – |
| video_runs / segments / frames / digests | – | 0 | 46 / 3046 / 160 / 11 |
| runs / steps / llm_calls | 75 / 428 / 315 | 189 / 1789 / 1164 | 105 / 1114 / 889 |

- main ↔ s2s3: 키 일치. main의 항목 343개는 id와 (source_id, external_id)가 s2s3와 같고, s2s3에만 12개(W41 simonw)가 더 있다. 값이 다른 곳은 S2 재채점 칸(items.score·filter_status, repo_trending 별 수·점수)뿐이다. main의 runs·steps·llm_calls는 행 단위로 모두 s2s3에 있다(빠진 행 0). → s2s3 DB를 main DB로 복사했다.
- main·s2s3 ↔ s4: 키 어긋남. s4는 영상 60개를 id 1~60으로 넣어 글 항목 id와 겹쳤다. 같은 영상 17개는 id가 다르고(예: `xRZHLI5SPWo` main 252, s4 15), steps.id는 1114개가 겹친다. runs.id(텍스트)는 겹치지 않는다. → 사용자 결정으로 A(id 대응표)를 적용했다.

### s4 병합(A, 복사본에서 작업 후 교체)

- 항목: (source_id, external_id)로 맞췄다. 겹친 17개는 main 기존 id를 쓰고 main 행을 유지했다. 겹친 항목의 딸린 행 중 s4와 다른 것은 item_texts.expires_at 17건뿐이다(내용 같음). 새 항목 43개는 새 id를 받았다.
- 고친 참조: item_texts·item_keywords·links·videos·video_runs·video_digests의 item_id, `digest_json` 안의 item_id
- steps·llm_calls: 새 id = 옛 id + 1789. fetch_log는 새 id. runs, video_segments, video_frames는 그대로
- 대응표: `reports/P1_id_map.json`(items 옛 id→새 id, 겹친 17개 목록, steps 오프셋, fetch_log)
- S4 리포트에 적힌 옛 step_id로는 `role --replay`가 맞지 않는다. 대응표의 오프셋을 더해 찾는다.

검사 결과:

| 검사 | 결과 |
|---|---|
| integrity_check | ok |
| foreign_key_check | 위반 0 |
| 표별 행 수 = main + s4 − 겹친 항목 몫 | 24개 표 모두 일치(items 398 = 355 + 60 − 17, steps 2903, llm_calls 2053, video_segments 3046 등) |
| digest_json item_id 실재 | 11/11(같은 영상의 video 항목을 가리킴) |
| video_runs item_id | 46/46 |
| 고아 행(llm_calls→steps, steps→runs) | 0 |
| (source_id, external_id) 중복 | 0 |

### 캐시·미디어

- 응답 캐시 `data/cache`: main 200 + s2s3 + s4 → 1,267개. 같은 키로 내용이 다른 파일 1개(smoke 별칭의 repo_oneliner)는 s2s3 것을 썼다.
- HTTP 캐시: s2s3 것으로(1,152개). s4 미디어(`data/media`, 영상 11개, 프레임 포함)도 main으로 옮겼다.
- `budget_state.json`은 main 것(기준값 10/7)을 유지했다. s4 것은 10/8에 기준값을 다시 잡아 사용액이 적게 나온다.
- 백업: `data/backup/pre-P1-20261009/`(옮기기 전 main DB, 캐시 tar), `data/backup/post-s2s3-20261009.db`

### 캐시로 digest 재실행(0원 확인)

repo 복사본(`/tmp`, DB·캐시 사본)에서 가짜 키로 `video run --video-id xRZHLI5SPWo --mode whisper+slides --reuse-media`를 실행했다. 캐시에 없는 호출은 401로 막혀 비용이 나지 않는다.

| 역할 | 호출 | 캐시 적중 | 결과 |
|---|---|---|---|
| video_slide(프레임 판독) | 20 | 20 | 0원 |
| video_summary | 1 | 0 | 캐시 없음(401로 중단, 대체 출력) |

- 원인: video_summary·judge 요청 본문에 `item_id: 15`, `vd:15@0`처럼 item id가 들어가는데, id가 252로 바뀌어 캐시 키가 달라졌다. 프레임 판독은 id가 들어가지 않아 그대로 적중한다.
- 그래서 영상 재실행은 판독 0원, 요약만 새로 호출된다. s4 기록상 캐시 없는 video_summary 1회는 평균 $0.0043(최대 $0.0083)이라, digest 11개를 다시 만들면 약 $0.05~0.1이다. S5 1단계 재판독에 포함된다.

### 사용액 기록

| 출처 | 금액 |
|---|---|
| 실행 기록 합(통합 DB, S0~S4) | $1.82(S0 0.052, S1 0.056, S2 0.688, S3 0.499, S4 0.521) |
| 그중 s2s3 몫(S0~S3) | $1.30 |
| 키 기준 단계 사용액(`cost`, 기준값 이후 usage) | $2.46 |

예상한 약 $2.5는 키 기준 금액과 맞다. 기록 합과의 차이 $0.65는 세 DB에 남지 않은 호출이다(지운 실험 DB, 다른 worktree 임시 실행 등으로 추정, 따로 추적하지 않음). 예산 판단은 지금처럼 큰 쪽(키 기준)을 쓴다.

### 옮긴 뒤 확인

- `check-config`: OK 설정 8개, 역할 9개
- `pytest`(--extra video --extra embed): 414 passed, 건너뜀 0
- `items --week 2026-W40`, `2026-W41`: 정상 출력

## 2. W41 백필

`collect --since 2026-10-05 --spec P1`(10/5~10/9): 글 159, 레포 릴리스 36, 트렌딩 11. techbridge는 RSS 404로 실패했고, 바로 `--source techbridge`로 다시 돌려 3건을 받았다. 로그: `data/logs/collect-temp/backfill-W41-2026-10-09.log`

## 3. 매일 수집 임시 예약

- collect는 LLM을 부르지 않는다(`trendsit/collect`에 llm·role 호출 없음, repo_oneliner는 S3 단계). 끌 옵션 없이 0원이다.
- `scripts/collect_temp.sh`: 실행일 기준 어제~오늘을 수집한다(겹치는 것은 중복 제거). 실패한 소스만 60초 뒤 한 번 더 돌린다. 로그는 `data/logs/collect-temp/YYYY-MM-DD.log`이고 git에서 빠진다(`.gitignore`의 `data/*`).
- `scripts/com.trendsit.collect-temp.plist`: 매일 02:00. 잠든 사이 놓친 실행은 깨어날 때 한 번 돈다(전원이 꺼져 있던 동안은 안 돈다).
- 주차: 트렌딩은 실행일의 ISO 주로 저장되고 같은 주에 다시 돌리면 그 주 목록을 바꾼다. 일요일 02:00 수집분이 그 주 마지막 목록이고, 월요일 02:00부터 다음 주다.

명령:

```bash
# 설치
mkdir -p ~/Claude/projects/trendsit/data/logs/collect-temp
cp ~/Claude/projects/trendsit/scripts/com.trendsit.collect-temp.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.trendsit.collect-temp.plist
# 확인(runs, last exit code), 바로 한 번 실행, 오늘 로그
launchctl print gui/$(id -u)/com.trendsit.collect-temp | grep -E "state|runs|last exit"
launchctl kickstart gui/$(id -u)/com.trendsit.collect-temp
cat ~/Claude/projects/trendsit/data/logs/collect-temp/$(date +%F).log
# 제거(S6 정식 launchd로 바꿀 때)
launchctl bootout gui/$(id -u)/com.trendsit.collect-temp
rm ~/Library/LaunchAgents/com.trendsit.collect-temp.plist
git rm scripts/collect_temp.sh scripts/com.trendsit.collect-temp.plist
```

상태(2026-10-09 12:28):

- 설치됨. launchd로 두 번 실행(kickstart), 둘 다 exit 0
- 첫 실행(12:25, 10/8~10/9): 새 항목 0(직전 백필과 겹침), fetch_log +9, 트렌딩 W41 11개 갱신
- 두 번째 실행(12:26): 재시도 동작 확인
- 다음 실행: 2026-10-10 02:00
- 남은 위험: techbridge 유튜브 RSS가 12:20 이후 계속 404다(직접 curl 5회 모두 404, 피드 쪽 문제). 영상은 나중에도 받을 수 있어(채널 목록 백필) 그 주에만 받을 수 있는 트렌딩과 달리 놓쳐도 회복된다. 404가 며칠 이어지면 S5에서 yt-dlp 채널 목록으로 메운다.

## 4. 주차별 재료(통합 DB, 2026-10-09 12:30)

| 소스·재료 | W37 | W38 | W39 | W40 | W41 | W42 |
|---|---|---|---|---|---|---|
| aitimes | 0 | 0 | 0 | 188 | 106 | 0 |
| geeknews | 0 | 0 | 0 | 83 | 29 | 0 |
| openai | 0 | 0 | 0 | 15 | 13 | 0 |
| simonw | 0 | 0 | 0 | 18 | 18 | 0 |
| anthropic | 0 | 0 | 0 | 2 | 4 | 0 |
| deepmind | 0 | 0 | 0 | 2 | 1 | 0 |
| github_releases | 0 | 0 | 0 | 18 | 36 | 0 |
| techbridge(영상) | 3 | 14 | 14 | 17 | 15 | 0 |
| items 합 | 3 | 14 | 14 | 343 | 222 | 0 |
| 관련성 판정 keep | 0 | 0 | 0 | 278 | 0 | 0 |
| item_card v1 / v2 | 0 | 0 | 0 | 264 / 5 | 0 | 0 |
| 영상 digest | 0 | 1 | 1 | 3 | 6 | 0 |
| repo_trending(주차 목록) | 없음 | 없음 | 없음 | 없음 | 11 | 없음 |
| repo_cards | 0 | 0 | 0 | 0 | 7 | 0 |

- W41 글은 10/5~10/9(일자별 26~37건)까지다. 10/10~10/11은 매일 수집이 채운다. GeekNews는 두 주 모두 날짜당 1페이지인데, W41은 아직 4일치(10/9 목록은 0건, 다음 수집에서 다시 받음)이고 10/6·10/8이 4건씩이라 적다.
- W39 이전 글과 W39·W40 트렌딩은 없다. 트렌딩은 지난 주를 받을 수 없어 W40 이전은 채울 수 없다.

### 시연용 지난 주 후보

| 주 | 있는 것 | 빈 곳 |
|---|---|---|
| W40 | 글 308 + 릴리스 18, 관련성·item_card 완료, 편집장 계획 1개(10/4), 영상 17·digest 3 | 트렌딩 없음, repo_cards 없음 |
| W41 | 글 171 + 릴리스 36(10/9까지), 트렌딩 11·repo_cards 7, 영상 15·digest 6 | 글 관련성·item_card 미실행(171건 판정 전), 10/10~11 수집 남음 |

W41은 세 채널(글·영상·트렌딩)을 다 갖춘 유일한 주다. 시연에 트렌딩을 넣으려면 W41이고, S5 1단계에서 W41 글의 필터·item_card를 돌리면 된다. 재료 생성을 바로 쓰려면 W40이다.

## 5. 정리 대상(삭제 안 함, 승인 대기)

| 대상 | 브랜치 | 미커밋 변경 | main 병합 |
|---|---|---|---|
| worktree `../trendsit-s2s3` | s2-s3 | 없음 | 됨 |
| worktree `../trendsit-s4` | s4-video | 없음 | 됨 |
| 로컬 브랜치 | s0-foundation, s1-collect | – | – |

두 worktree의 `data/`(DB, 캐시, s4 media 658M)는 통합 뒤 필요 없다. worktree를 지우면 함께 지워진다.
