# 추가 작업 지시서: 파비콘, 공유 미리보기, 1차 리뷰 반영

> 대상: 맥 Claude Code (`~/Claude/projects/trendsit`). 작성 2026-10-06. `docs/03_TASK.md`의 규칙과 금지 사항을 그대로 따른다. 사이트 구조나 데이터는 바꾸지 않는다.

## 0. 받은 파일 (이 문서와 같은 폴더)
| 파일 | 쓰임 |
|---|---|
| `favicon.svg` | 기본 아이콘(32 이상, 최신 브라우저) |
| `favicon-16.svg`, `favicon-16.png` | 16px 전용(형광 띠와 T를 굵게 다시 그림) |
| `favicon-32.png`, `favicon-48.png`, `favicon.ico` | 브라우저 호환용 |
| `apple-touch-icon.png` (180), `icon-512.png` | 홈 화면 추가, 큰 아이콘 |
| `og-image.png` (1200 × 630) | 카톡, 슬랙 링크 미리보기 이미지 |
| `*.svg` 원본 | 수정이 필요하면 이걸 고친다 |

## 1. 파일 두기
- 이 폴더의 파일을 `site_src/static/`에 복사하고, `build.py`가 빌드 때 `site/` 루트로 그대로 복사하게 한다(`site/favicon.ico`, `site/favicon.svg` ...)
- 완료 기준: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8788/favicon.ico` 가 200

## 2. 모든 페이지 `<head>`에 추가
```html
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#ffffff">
<meta name="description" content="{설명}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="TrendsIT">
<meta property="og:title" content="{페이지 title과 같은 값}">
<meta property="og:description" content="{설명}">
<meta property="og:url" content="https://trendsit.jiseop.com{현재 경로}">
<meta property="og:image" content="https://trendsit.jiseop.com/og-image.png">
<meta name="twitter:card" content="summary_large_image">
```
- `{설명}`: 브리핑 홈과 주차 페이지는 "{주차 label} 기술 동향 브리핑. 토픽 {n}개, 소스 {m}건" / 토픽 페이지는 `summary`에서 `==`를 뺀 문장 / 나머지는 "로컬 AI가 매주 정리하는 개인 기술 브리핑 (예시 데이터)"
- 완료 기준: 모든 HTML에 위 태그가 한 번씩, `og:url`이 그 페이지 주소

## 3. 1차 리뷰 반영
1. **줄바꿈** (`site_src/style.css`): 본문은 글자 단위, 제목류는 단어 단위 + 줄 길이 균형
```css
body { word-break: normal; line-break: strict; overflow-wrap: anywhere; }
.wtitle, .ttitle, .lead-t, .item-t, .h, .ptitle, .side-h, .tabs, .badge, button { word-break: keep-all; text-wrap: balance; }
.body, .lead-s, .item-s, .points li, .r2, .l2 { text-wrap: pretty; }
```
2. **지난 주차 문구**: 최신 주차가 아닌 브리핑 페이지(`/week/2026-w39/`)에서는 "이번 주 핵심 토픽" → "이 주의 핵심 토픽", "이번 주 관심 분야 레포" → "이 주 관심 분야 레포", "이번 주 수집" → "이 주 수집". 최신 주차(`/`, `/week/2026-w40/`)는 그대로
3. **주차 이동**: 맨 아래 링크는 그대로 두고, 주차 헤더(기간 줄 오른쪽 또는 아래)에 작은 "지난 주차" 텍스트 링크 하나 추가(12~13px, #555d6d, 회색 밑줄). 지난 주차가 없으면 넣지 않는다. 달력은 만들지 않는다
4. **붙어 읽히는 항목**: 메타 줄, 범례, 역할 필터처럼 간격으로만 떨어진 항목 사이에 글자 구분을 넣는다. 보이는 구분이 필요 없으면 `<span class="sr-sep"> / </span>`(화면에는 숨기고 텍스트에는 남김)
```css
.sr-sep { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
```
   - 확인: 홈 HTML에서 태그를 지운 텍스트에 "레포 2지난", "글 41영상" 같은 붙은 글자가 없어야 함
5. **`<title>`**: 지난 주차 브리핑은 "9월 4주차 브리핑 | TrendsIT", 최신 홈은 "TrendsIT"
6. **형광 확인**: 토픽 페이지와 실행 상세의 HTML에 `==`가 남아 있지 않은지 `grep -c "==" site/topic/*/index.html site/runs/*/*/index.html`로 확인(0이어야 함)
7. PC 관리 화면 본문 왼쪽 정렬은 그대로 둔다(명세 쪽을 고침)

## 4. 확인과 보고
- `python3 site_src/build.py` → `site_src/check.py`(기존 검증) 통과 + 위 완료 기준
- launchd 서버는 같은 폴더를 서빙하므로 다시 띄울 필요 없음. 외부에서 `https://trendsit.jiseop.com/favicon.ico`, `/og-image.png` 200 확인
- 보고: 바꾼 파일, 확인 결과. 링크 미리보기는 사용자가 카톡이나 슬랙에 주소를 붙여 확인(캐시 때문에 처음엔 안 보일 수 있음)
