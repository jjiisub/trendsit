# 이번 작업 지시서: 예시 사이트 생성 + trendsit.jiseop.com 공개

> 대상: 사용자 맥(M1 Max, 집, 상시 켜짐)의 Claude Code. 작성 2026-10-06.
> 위에서부터 순서대로 진행하고, 단계마다 **완료 기준**을 직접 확인한 뒤 넘어간다. 애매하거나 11번 금지 사항에 걸리는 일, 또는 "멈추고 묻는다"라고 적힌 곳에서는 사용자에게 묻는다.

## 0. 범위
- **할 일 세 가지:** ① 프로젝트 맥락 저장 ② 예시 데이터로 정적 사이트 생성 ③ `trendsit.jiseop.com`에 공개
- **하지 않는 것:** 백엔드, DB, LLM, 수집기, 스펙 문서, Access(로그인 잠금) 설정, 다른 서브도메인이나 기존 앱 수정. `01_CONTEXT.md`에 나오는 다음 작업은 시작하지 않는다

## 1. 받은 파일 (이 지시서와 같은 묶음)
| 파일 | 내용 |
|---|---|
| `README.md` | 읽는 순서 |
| `docs/01_CONTEXT.md` | 프로젝트 전체 맥락. 프로젝트 루트 `CLAUDE.md`가 된다 |
| `docs/02_DESIGN.md` | 화면 디자인 명세 (토큰, 요소, 화면, 도식) |
| `docs/03_TASK.md` | 이 문서 |
| `data/trendsit-example.json` | 2주치 예시 데이터 (토픽 11, 레포 10, 소스, 키워드, 실행 기록) |
| `data/make_data.py` | 위 JSON을 만든 스크립트 (참고용, 고칠 필요 없음) |
| `mockups/` 8개 | 디자인 시각 기준. 브라우저로 열어 본다. 홈 모바일, 토픽 모바일, 홈 PC, 소스, 키워드, 실행 기록 3단(주차별, 이번 주차, 실행 상세) |

## 2. 결과물
- `~/Claude/projects/trendsit/` 프로젝트 폴더 (CLAUDE.md, docs, data, mockups, site_src, site)
- `site_src/build.py` 실행 → `site/`에 정적 HTML 생성
- launchd `com.jiseop.trendsit-web`이 `127.0.0.1:8788`에서 `site/`를 서빙
- `https://trendsit.jiseop.com` 공개(로그인 없음)

## 3. 사전 확인 (읽기만)
```bash
which python3 cloudflared git
python3 --version
lsof -nP -iTCP:8788 -sTCP:LISTEN || echo "8788 free"
ls ~/Library/LaunchAgents | grep -i "jiseop\|cloudflare" || true
launchctl print gui/$(id -u)/com.cloudflare.cloudflared >/dev/null 2>&1 && echo "cloudflared: gui agent OK" || echo "cloudflared: gui agent NOT FOUND"
grep -n "hostname\|service" ~/.cloudflared/config.yml
ls -d ~/Claude/projects/trendsit ~/Claude/projects/trendscope 2>/dev/null || true
```
완료 기준: python3(3.9 이상), cloudflared가 있다 / `cloudflared: gui agent OK` / config.yml에 pt.jiseop.com 규칙과 마지막 404 규칙이 보인다.

**멈추고 묻는 경우**
- `cloudflared: gui agent NOT FOUND`: cloudflared가 다른 방식(시스템 서비스 등)으로 돌고 있다. 재시작에 sudo가 필요할 수 있으니 진행하지 말고 보고한다
- 8788이 이미 사용 중이거나 `com.jiseop.trendscope-web`이 있거나 config.yml에 `trend.jiseop.com`이 있다: 이전 지시서(trendscope 정적 페이지)가 실행된 상태다. 사용자에게 보여 주고 다음 중 고르게 한다
  - (권장) 기존 trendscope-web을 내리고 같은 포트 8788에 trendsit-web을 올린다. 재부팅 때 다시 뜨지 않도록 `launchctl bootout gui/$(id -u)/com.jiseop.trendscope-web` 다음 `launchctl disable gui/$(id -u)/com.jiseop.trendscope-web`. plist 파일은 지우지 않는다. 이 경우 `trend.jiseop.com`도 같은 포트라 TrendsIT 화면을 보여 주게 된다는 점을 알리고, 그 규칙과 DNS를 지울지는 사용자가 정한다
  - 다른 포트(8790 등)를 쓴다
- `~/Claude/projects/trendsit`이 이미 있다: 내용을 보여 주고 어떻게 할지 묻는다

## 4. 프로젝트 폴더 준비
**셸 변수는 명령 실행 사이에 유지되지 않는다.** 아래 블록은 한 번에 실행하고, 나눠 실행할 때는 블록 맨 위의 `H=`, `P=` 두 줄을 매번 다시 넣는다. `H`는 이 README가 있는 폴더의 **절대 경로**로 바꾼다.
```bash
H="/절대/경로/trendsit-handoff"          # README.md가 있는 폴더로 바꿀 것
P="$HOME/Claude/projects/trendsit"
[ -f "$H/README.md" ] || { echo "H is wrong"; exit 1; }
mkdir -p "$P/docs" "$P/data" "$P/mockups" "$P/site_src" "$P/site"
cp "$H/docs/01_CONTEXT.md" "$H/docs/02_DESIGN.md" "$H/docs/03_TASK.md" "$P/docs/"
if [ -e "$P/CLAUDE.md" ]; then echo "CLAUDE.md exists - do not overwrite, tell the user"; else cp "$H/docs/01_CONTEXT.md" "$P/CLAUDE.md"; fi
cp "$H/data/trendsit-example.json" "$H/data/make_data.py" "$P/data/"
cp "$H/mockups/"*.html "$P/mockups/"
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(len(d['topics']),'topics',len(d['repos']),'repos')" "$P/data/trendsit-example.json"
```
완료 기준: `CLAUDE.md`가 있고, `11 topics 10 repos`가 나온다. `data/make_data.py`는 참고용이라 실행하지 않는다(실행하면 같은 폴더의 JSON을 다시 쓴다).

선택(권장): 로컬 git 세이브 포인트. 원격 push는 하지 않고, git 전역 설정은 바꾸지 않는다. 커밋이 사용자 정보 부족으로 실패하면 건너뛰고 보고한다.
```bash
P="$HOME/Claude/projects/trendsit"
cd "$P" || exit 1
[ "$(pwd)" = "$P" ] || exit 1
git init -q && printf "site/\n.DS_Store\n*.log\n.env\n" > .gitignore && git add -A && git commit -qm "TrendsIT: 맥락, 디자인, 예시 데이터" && git log --oneline | head -1
```

## 5. 사이트 생성 요구사항

### 5.1 방식
- `site_src/build.py` 하나 + `site_src/style.css`. **파이썬 표준 라이브러리만** 쓴다(템플릿은 f-string이나 `string.Template`)
- 실행: `python3 site_src/build.py` → `site/`를 지우지 않고 덮어써서 생성. 같은 입력이면 같은 출력(결정적)
- 자바스크립트 없이 동작해야 한다. 외부 요청은 Google Fonts(IBM Plex Sans KR)뿐
- 디자인은 `docs/02_DESIGN.md`를 따르고, 시각은 `mockups/`와 맞춘다. 막히면 목업의 CSS 값을 가져오되, 목업을 보기 좋게 감싼 바깥 틀(`body` 회색 배경, `body>div`의 `box-shadow`)은 가져오지 않는다

### 5.2 생성할 페이지
| 주소 | 파일 | 내용 |
|---|---|---|
| `/` | `site/index.html` | 최신 주차(`weeks[0]`, 10월 1주차) 브리핑 홈 |
| `/week/2026-w39/` | `site/week/2026-w39/index.html` | 지난 주차 브리핑 홈 (주차마다 하나. 최신 주차도 `/week/2026-w40/`로 하나 더 만든다) |
| `/topic/<id>/` | `site/topic/<id>/index.html` | 토픽 페이지 11개 |
| `/sources/` | `site/sources/index.html` | 소스 (02_DESIGN 6.3) |
| `/keywords/` | `site/keywords/index.html` | 키워드 (6.4) |
| `/runs/` | `site/runs/index.html` | 실행 기록 메인 = 최신 주차 (6.5). `/runs/2026-w40/`도 같은 내용으로 하나 더 |
| `/runs/<주차id>/` | `site/runs/2026-w39/index.html` 등 | 주차별 메인 (`runs[].week`가 있는 주차: w40, w39) |
| `/runs/weeks/` | `site/runs/weeks/index.html` | 실행 기록 상위: 주차별 목록 |
| `/runs/<주차id>/<실행id>/` | 실행마다 1개 (16개) | 실행 기록 하위: 실행 1건 상세 |
| `/assets/style.css` | | 공통 CSS |

### 5.3 데이터 → 화면 매핑 (`data/trendsit-example.json`)
- `meta.notice`: 모든 페이지 맨 아래 작은 회색 안내. 상단 오른쪽에는 "예시 데이터"
- `weeks[]`: 주차 이름 `label`, 기간 `range`, `collected`(채널 막대와 범례), `source_count`, `topic_count`, `published_at`, `next_run`. 주차 이동 링크(이전/다음)
- `topics[]` (주차별로 `weeks[].topic_ids` 순서)
  - 홈: `lead: true`는 리드 카드, 나머지는 목록. 제목 `title`, 요약 `summary`, 메타는 `channels`, `relation.type == "follow_up"`이면 "지난 흐름의 후속", `has_check`면 "확인 필요"
  - 토픽 페이지: `overview`, `points[]`(`refs`는 그 토픽 `sources[].id`, 화면에는 출처 목록 순번 [1][2]로), `diagrams[]`, `concepts[]`, `contributions[]`, `sources[]`, `relation`(후속이면 헤더와 소스 연결도에 지난 토픽 링크)
  - 문자열의 `==텍스트==` → `<mark class="hl">텍스트</mark>` (HTML 이스케이프 먼저, 그다음 변환)
- `diagrams[].type`: `bars` → B 수치 막대, `events` → D 사건 흐름, `video` → C 영상 타임라인. 소스 연결도(A)는 데이터와 상관없이 항상 `sources[]`로 그린다
- `topics[].sources[]`(토픽의 출처): `example: true`(예시 영상)는 링크 없이 "예시 영상" 표시. 나머지는 `url`로 새 탭(`rel="noopener"`)
- `repos[]` (주차별 `week`): 이름, `stars_7d`(문자열 그대로, 예 "+1.9k"), `what`(하는 일 한 문장), 셋째 줄은 `signal` 라벨(`meta.signal_labels`) / `note`(있을 때만) / `topic_id`가 있으면 "'토픽 제목' 토픽과 관련" 링크(없으면 생략). `url`이 없으면(가상 레포) 링크 없음
- 채널 라벨: 주간 수집 범례는 `meta.channel_labels`(글, 영상, GitHub), 토픽 메타와 소스별로 더한 것은 `meta.channel_labels_topic`(글, 영상, 레포)
- 영상 타임라인 시각: 화면에는 `t`(MM:SS), 원본 링크에는 `sec`(초)를 `?t=` 값으로. 이번 데이터의 영상은 모두 예시라 링크 없음
- 최상위 `sources[]`(소스 설정, 토픽 안의 `topics[].sources[]`와 다름): `id`, `name`, `type`, `channel`, `url`, `enabled`, `added_at`, `note`(없으면 null), `daily[주차id]`(월~일 7칸, `null`은 그날 실패), `weeks[주차id]`(`collected`, `failed_days`, `used_in_topics`), `last`, `last_error`(없으면 null), `repos`(추적 레포 소스만). 소스 페이지는 최신 주차 기준
- `keywords.items[]`: `id`, `name`, `aliases`, `added_at`, `mentions`(`keywords.weeks` 4주 순서, 마지막이 이번 주), `topics`. `keywords.candidates[]`: `id`, `status`(pending/rejected), `alias`, `keyword_id`, `reason`, `by`, `evidence[]`(title, date, url), `seen`, `run_id`(후보를 낸 실행), `decided_at`(거절만)
- `runs[]`: `id`, `week`, `kind`(nightly/weekly), `at`, `duration_min`, `status`(ok/partial), `summary`, `model`, `counts`, `errors[]`(빈 배열 가능), `decisions`(판단 수 = `auto`가 아닌 단계 수), `steps[]`(`role`, `text`, `auto`, `attention`, weekly만 `t`, 반려만 `detail`{topic_id, draft, evidence, evidence_ref, fixed})
  - **매일 수집(nightly)은 실행일 02:00에 전날 것을 모은다.** 그래서 `nightly-2026-09-28`은 9월 4주차(w39) 소속이고, 소스의 실패 칸(`daily`의 null)은 수집 대상 날짜(10.2), `last_error.at`은 실행 시각(10.3 02:00)이다. 주차 페이지에 넣을 실행은 날짜가 아니라 `runs[].week`로 고른다
  - `steps[].detail.evidence_ref`는 `topics[]`에서 `detail.topic_id` 토픽의 `sources[].id`. 반려 상자 근거 줄 끝의 "(GeekNews, 10.2)"는 그 출처의 `site`, `date`
- `run_weeks[]`: 주차별 요약(상위 화면). `detail`이 false인 주(w38)는 페이지와 링크가 없다
- 날짜 표시: 제목, 목록 줄은 "10.5 (월) 07:00"(요일 포함), 경로 줄과 짧은 링크는 "10.5 주간 발행"처럼 요일 생략. 요일은 고정 표 `"월화수목금토일"[date.weekday()]`로 붙인다(`strftime('%a')`는 영어라 쓰지 않음)
- 라벨 표: 소스 유형 rss→RSS, arxiv→arXiv, youtube→유튜브, oss_insight→OSS Insight, github_repos→레포 추적 / 실행 종류 weekly→주간 발행, nightly→매일 수집 / 상태 ok→정상, partial→일부 실패

### 5.4 검증 (모두 통과해야 완료)
`site_src/check.py`를 만들어 자동으로 확인할 수 있는 것은 자동으로 확인한다.
- [ ] `python3 site_src/build.py`를 두 번 실행해도 결과 파일이 같다
- [ ] 로컬 서버에서 모든 페이지 200: `/`, `/week/2026-w39/`, `/week/2026-w40/`, 토픽 11개, `/sources/`, `/keywords/`, `/runs/`, `/runs/weeks/`, `/runs/2026-w40/`, `/runs/2026-w39/`, 실행 상세 16개, `/assets/style.css`
- [ ] 내부 링크(`href="/..."`) 깨짐 0건
- [ ] 홈: 리드 카드 정확히 1개, 목록이 rank 순, 레포가 그 주차 것만(10월 1주차 5개)
- [ ] 소스: 채널 묶음 합계가 글 41 / 영상 3 / GitHub 11, "토픽에 29건", 확인할 것 2개(블로그 A 실패, 2주째 안 쓰인 소스 4개), 7일 막대 9줄 + 꺼짐 1줄
- [ ] 키워드: 후보 3개(승인/거절 버튼 비활성), 최근 거절 1줄, 키워드 8개가 이번 주 언급 많은 순, 가지에 후보 3개는 점선, Luna는 취소선
- [ ] 실행 기록: 메뉴 링크가 `/runs/`로 열리고 10월 1주차 메인이 보인다 / 봐야 할 판단 3개 / 단계 레일 숫자 55, 9, 6, 6, 5(반려 1), 6 / 실행 8개 목록 / 상위에 3주, 9월 3주차는 "승인 모드"와 링크 없음 / 상세 16개 모두 경로 줄로 위로 이동 가능 / 10.5 주간 발행 상세에 반려 상자(초안, 근거, 수정)
- [ ] 형광 밑줄 개수(`<mark class="hl">` 개수): 홈 토픽 요약마다 1개 이하 / 토픽 페이지는 개요 + 핵심 포인트 합계 4개 이하 (토픽 페이지에는 요약을 다시 싣지 않는다)
- [ ] 토픽 페이지: 소스 연결도가 항상 있음 / `diagrams`에 없는 도식은 그리지 않음 / 출처 번호가 출처 목록과 맞음 / `check: true` 문장에 "확인 필요"
- [ ] 색: CSS와 HTML(인라인 style, SVG `fill`/`stroke` 포함)의 색 값이 `02_DESIGN.md` 3장 표의 값, `#fff`, `transparent`, `none`뿐. 유채색은 #ffd5c0 하나
- [ ] 금지 CSS 없음: `box-shadow`, `text-transform: uppercase`, `monospace`, `animation`, `transition`, 알약 모양(`border-radius` 999px 이상). 원형은 12px 이하의 점과 SVG 원에만 허용
- [ ] 외부 리소스는 Google Fonts뿐: `<link href>`, `<script src>`, `<img src>`, CSS `@import`, `url()`에서 fonts.googleapis.com, fonts.gstatic.com 외 외부 주소 0건 (`<a href>` 원본 링크는 대상 아님)
- [ ] 390px, 1280px 폭에서 가로 스크롤 없음. 헤드리스 브라우저(Playwright, Chrome)가 있으면 스크린샷을 `site_src/shots/`에 저장하고 `document.documentElement.scrollWidth <= innerWidth`로 확인. 없으면 이 항목은 "수동 확인 필요"로 보고
- [ ] 눈으로 확인(자동 아님): `mockups/`와 나란히 놓고 글자 크기, 간격, 색이 크게 다르지 않다. 스크린샷 경로를 사용자에게 안내

로컬 확인용 임시 서버는 `python3 -m http.server 8799 --bind 127.0.0.1 --directory site`로 띄우고 확인이 끝나면 끈다.

## 6. 로컬 서빙 (launchd)
`~/Library/LaunchAgents/com.jiseop.trendsit-web.plist`를 만든다. `__PY__`는 `which python3` 결과, `__HOME__`은 `$HOME` 값으로 바꾼다(plist에는 `~`나 변수를 쓸 수 없음).
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.jiseop.trendsit-web</string>
  <key>ProgramArguments</key><array>
    <string>__PY__</string><string>-m</string><string>http.server</string>
    <string>8788</string><string>--bind</string><string>127.0.0.1</string>
    <string>--directory</string><string>__HOME__/Claude/projects/trendsit/site</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>__HOME__/Library/Logs/trendsit-web.log</string>
  <key>StandardErrorPath</key><string>__HOME__/Library/Logs/trendsit-web.log</string>
</dict></plist>
```
```bash
plutil -lint ~/Library/LaunchAgents/com.jiseop.trendsit-web.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.jiseop.trendsit-web.plist
sleep 1
for u in / /week/2026-w39/ /topic/w40-jev-race/ /assets/style.css; do curl -s -o /dev/null -w "%{http_code} $u\n" http://127.0.0.1:8788$u; done
lsof -nP -iTCP:8788 -sTCP:LISTEN
```
완료 기준: 모두 200 / 리스닝 주소가 `127.0.0.1:8788` (0.0.0.0이면 실패).

## 7. 터널 규칙과 DNS
```bash
cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.bak-$(date +%Y%m%d%H%M)
```
`~/.cloudflared/config.yml`의 ingress 목록에서 **마지막 404 규칙 바로 위**에 아래 두 줄을 넣는다. 들여쓰기는 기존 규칙과 똑같이, 다른 줄은 바꾸지 않는다.
```yaml
  - hostname: trendsit.jiseop.com
    service: http://127.0.0.1:8788
```
```bash
cloudflared tunnel ingress validate
cloudflared tunnel ingress rule https://trendsit.jiseop.com/
cloudflared tunnel ingress rule https://pt.jiseop.com/
cloudflared tunnel route dns home trendsit.jiseop.com
launchctl kickstart -k gui/$(id -u)/com.cloudflare.cloudflared
sleep 5
cloudflared tunnel info home | head -20
```
완료 기준: validate 통과 / trendsit은 `http://127.0.0.1:8788`, pt는 기존 `http://127.0.0.1:8787`에 매칭 / route가 CNAME 생성(또는 이미 존재)을 알림 / 터널에 엣지 연결이 보임.

## 8. 외부 확인
```bash
for u in / /week/2026-w39/ /topic/w40-jev-race/ /sources/ /keywords/ /runs/ /runs/weeks/ /runs/2026-w40/weekly-2026-10-05/; do curl -s -o /dev/null -w "%{http_code} $u\n" https://trendsit.jiseop.com$u; done
curl -s https://trendsit.jiseop.com/ | grep -o "<title>[^<]*</title>"
curl -s -o /dev/null -w "%{http_code} pt\n" https://pt.jiseop.com/
```
완료 기준: trendsit 모두 200, title에 `TrendsIT` / pt는 **여전히 302**(Access 잠금 유지). DNS 전파 때문에 처음 몇 분은 실패할 수 있으니 1~2분 간격으로 최대 5번 재시도.

## 9. 보고
사용자에게 짧게 보고한다. 비밀 값은 넣지 않는다.
- 만든 폴더와 주요 파일 경로, `build.py` 실행 방법
- 5.4 검증 결과(체크리스트), 스크린샷 경로(있으면)
- plist 경로, config.yml에 추가한 줄, 6~8번 상태 코드
- 3번에서 기존 trendscope 설정을 만났다면 무엇을 했고 무엇이 남았는지(지울지 사용자 결정 필요)
- 사이트에서 목업과 다르게 만든 부분과 이유

## 10. 문제가 생기면
- 8788 충돌: 멈추고 다른 87xx 포트를 사용자에게 제안
- validate 실패: 백업으로 복구(`cp ~/.cloudflared/config.yml.bak-... ~/.cloudflared/config.yml`) 후 원인 보고
- 외부 502 또는 1033: cloudflared 로그(`~/Library/Logs/` 아래 cloudflared 로그)와 로컬 curl 결과를 함께 보고
- 되돌리기: config.yml 백업 복원 → cloudflared kickstart → `launchctl bootout gui/$(id -u)/com.jiseop.trendsit-web` → plist 삭제는 사용자 승인 후. DNS CNAME은 Cloudflare 대시보드에서 사용자가 지운다

## 11. 금지 사항
- 비밀 파일(`~/.cloudflared/cert.pem`, 터널 json, `api-token`) 내용 출력, 복사, 커밋
- `0.0.0.0` 바인딩, 공유기 포트포워딩, sudo
- pt.jiseop.com 규칙이나 다른 LaunchAgent 수정. 예외: 3번에서 사용자가 고른 경우의 trendscope-web 내리기, 7번의 cloudflared 재시작(`kickstart`, 몇 초간 pt.jiseop.com도 끊길 수 있음)
- 예시 데이터 내용 임의 수정(문제가 보이면 고치지 말고 보고)
- 파일 삭제는 사용자 승인 후에만
- git 원격 push

## 12. 다음 작업 예고 (이번엔 하지 않음)
- 정적 사이트를 실제 앱으로: FastAPI가 같은 JSON 형태를 주고, 지금 템플릿을 그대로 쓰는 방향(7주차 결정). 바꾸기 전에 **Access 앱을 먼저 생성**하고 같은 포트 8788에서 프로세스만 교체
- 스펙 문서(specs/)와 코어 골격은 별도 지시서로 진행
