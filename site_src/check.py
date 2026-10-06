# TrendsIT 예시 사이트 검증 (docs/03_TASK.md 5.4). 실행: python3 site_src/check.py
# 스크린샷: 전역 Playwright(npm root -g 아래)가 있으면 site_src/shots/에 저장하고 가로 스크롤을 잰다.
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parent
SITE = ROOT / "site"
SHOTS = SRC / "shots"
DATA = json.loads((ROOT / "data" / "trendsit-example.json").read_text(encoding="utf-8"))
PORT = 8799

ALLOWED_COLORS = {
    "#ffffff", "#f7f8f9", "#f3f4f5", "#eeeff1", "#dcdee3", "#d1d3d8", "#b0b3ba",
    "#868b94", "#555d6d", "#2a3038", "#1a1c20", "#ffd5c0", "#fff",
}
NAMED_COLORS = {
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "black", "white", "gray", "grey",
    "navy", "teal", "lime", "aqua", "cyan", "magenta", "fuchsia", "maroon", "olive", "silver", "brown", "gold",
}
FONT_HOSTS = ("https://fonts.googleapis.com", "https://fonts.gstatic.com")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def skip(name, detail):
    print(f"SKIP {name}  ({detail})")


def html_files():
    return sorted(SITE.rglob("*.html"))


def read(p):
    return p.read_text(encoding="utf-8")


def url_of(p):
    rel = p.relative_to(SITE).as_posix()
    return "/" + rel[: -len("index.html")]


def snapshot():
    return {p.relative_to(SITE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SITE.rglob("*")) if p.is_file()}


# ---------------------------------------------------------------- 1. 결정적 빌드
def build():
    subprocess.run([sys.executable, str(SRC / "build.py")], check=True, stdout=subprocess.DEVNULL)


build()
a = snapshot()
build()
b = snapshot()
check("빌드 두 번 결과 동일", a == b, f"{len(a)}개 파일")

RUN_DETAILS = [f'/runs/{r["week"]}/{r["id"]}/' for r in DATA["runs"]]
PAGES = (["/", "/week/2026-w39/", "/week/2026-w40/"] + [f'/topic/{t["id"]}/' for t in DATA["topics"]]
         + ["/sources/", "/keywords/", "/runs/", "/runs/weeks/", "/runs/2026-w40/", "/runs/2026-w39/"] + RUN_DETAILS + ["/assets/style.css"]
         + ["/favicon.ico", "/favicon.svg", "/favicon-16.png", "/favicon-32.png", "/favicon-48.png", "/apple-touch-icon.png", "/icon-512.png", "/og-image.png"])
SITE_URL = "https://trendsit.jiseop.com"
SEP = '<span class="sr-sep"> / </span>'

# ---------------------------------------------------------------- 2. 로컬 서버 200
server = subprocess.Popen(
    [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", str(SITE)],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    bad = []
    for u in PAGES:
        try:
            code = urllib.request.urlopen(f"http://127.0.0.1:{PORT}{u}", timeout=5).status
        except Exception as e:
            code = getattr(e, "code", str(e))
        if code != 200:
            bad.append(f"{u}={code}")
    check(f"로컬 서버 모든 페이지 200 ({len(PAGES)}개)", not bad, ", ".join(bad))

    # ------------------------------------------------------------ 3. 내부 링크
    broken = []
    for p in html_files():
        s = read(p)
        ids = set(re.findall(r'\bid="([^"]+)"', s))
        for href in re.findall(r'(?:href|src)="(/[^"]*|#[^"]*)"', s):
            if href.startswith("#"):
                if href[1:] not in ids:
                    broken.append(f"{url_of(p)} {href}")
                continue
            path, _, frag = href.partition("#")
            path = path.split("?", 1)[0]
            target = SITE / path.lstrip("/")
            if path.endswith("/"):
                target = target / "index.html"
            if not target.is_file():
                broken.append(f"{url_of(p)} {href}")
            elif frag and f'id="{frag}"' not in read(target):
                broken.append(f"{url_of(p)} {href}")
    check("내부 링크 깨짐 0건", not broken, "; ".join(broken[:10]))

    # ------------------------------------------------------------ 4~6. 홈, 형광 밑줄, 토픽
    topics = {t["id"]: t for t in DATA["topics"]}
    for wi, w in enumerate(DATA["weeks"]):
        pages = [SITE / "week" / w["id"] / "index.html"] + ([SITE / "index.html"] if wi == 0 else [])
        for p in pages:
            s = read(p)
            u = url_of(p)
            check(f"{u} 리드 카드 정확히 1개", s.count('class="lead row"') == 1)
            ids = re.findall(r'class="item row" href="/topic/([^/]+)/"', s)
            want = [t["id"] for t in sorted((topics[i] for i in w["topic_ids"]), key=lambda t: t["rank"]) if not t.get("lead")]
            check(f"{u} 목록이 rank 순", ids == want, f"{ids}")
            repo_names = re.findall(r'class="rname"[^>]*>([^<]+)<', s)
            want_r = [r["name"] for r in DATA["repos"] if r["week"] == w["id"]]
            check(f"{u} 레포가 그 주차 것만 ({len(want_r)}개)", repo_names == want_r, f"{len(repo_names)}개")
            sums = re.findall(r'<p class="(?:lead-s|item-s)">(.*?)</p>', s)
            over = [x[:20] for x in sums if x.count('<mark class="hl">') > 1]
            check(f"{u} 토픽 요약마다 형광 1개 이하", len(sums) == len(w["topic_ids"]) and not over, f"요약 {len(sums)}개")

    for t in DATA["topics"]:
        p = SITE / "topic" / t["id"] / "index.html"
        s = read(p)
        u = url_of(p)
        n_hl = s.count('<mark class="hl">')
        check(f"{u} 형광 밑줄 4개 이하", n_hl <= 4, f"{n_hl}개")
        check(f"{u} 요약 재수록 없음", t["summary"].replace("==", "")[:30] not in s.split("<body>", 1)[1].replace('<mark class="hl">', "").replace("</mark>", ""))
        check(f"{u} 소스 연결도 있음", s.count('<div class="graph">') == 1 and s.count("<svg") == 2)
        want = {k: sum(1 for g in t.get("diagrams", []) if g["type"] == k) for k in ("bars", "video", "events")}
        got = {k: s.count(f'class="sec diag-{k}"') for k in want}
        check(f"{u} 도식이 데이터와 일치", want == got, f"{got}")
        num = {x["id"]: i + 1 for i, x in enumerate(t["sources"])}
        pts = re.findall(r'<li class="pt">(.*?)</li>', s)
        ok = len(pts) == len(t["points"])
        detail = ""
        for p_html, pt in zip(pts, t["points"]):
            got_refs = [int(x) for x in re.findall(r'href="#src-(\d+)">\[\1\]', p_html)]
            if got_refs != [num[r] for r in pt["refs"]]:
                ok, detail = False, f"refs {got_refs}"
            if bool(pt.get("check")) != ("확인 필요" in p_html):
                ok, detail = False, "확인 필요 표시 불일치"
        src_ids = re.findall(r'<li id="src-(\d+)" class="src">', s)
        if src_ids != [str(i + 1) for i in range(len(t["sources"]))]:
            ok, detail = False, f"출처 목록 {src_ids}"
        check(f"{u} 출처 번호와 확인 필요 표시", ok, detail)
        check(f"{u} title", f"<title>{t['title'].replace('==', '')} | TrendsIT</title>" in s)

    # ------------------------------------------------------------ 관리 화면 (5.4 추가 항목)
    def page_of(u):
        return read(SITE / u.lstrip("/") / "index.html")

    s = page_of("/sources/")
    groups = re.findall(r'<h2 class="sgroup-h"><span>([^<]+)</span>(?:' + re.escape(SEP) + r')?<span class="sgroup-n">(\d+)개 / (\d+)건</span>', s)
    check("소스: 채널 묶음 합계 글 41 / 영상 3 / GitHub 11", [(g[0], g[2]) for g in groups] == [("글", "41"), ("영상", "3"), ("GitHub", "11")], f"{groups}")
    check("소스: \"토픽에 29건\"", "수집 55건, 토픽에 쓰인 것 29건" in s)
    check("소스: 확인할 것 2개 (블로그 A 실패, 2주째 안 쓰인 소스 4개)",
          "확인할 것 2개" in s and '예시 블로그 A: <mark class="hl">10.2 수집 실패</mark>, 다음 날 정상' in s
          and "2주째 토픽에 쓰이지 않은 소스 4곳 (블로그 3, 뉴스레터 1)</span>: <mark class=\"hl\">끄거나 키워드 필터 추가 검토</mark>" in s)
    check("소스: 7일 막대 9줄 + 꺼짐 1줄", s.count('<li class="srow">') == 9 and s.count('<li class="srow off">') == 1
          and s.count('class="days"') == 9 and len(re.findall(r'<i class="d', s.split('class="slegend"')[0])) == 63)

    k = page_of("/keywords/")
    cands = re.findall(r'<li class="cand">(.*?)</li>', k)
    check("키워드: 후보 3개, 승인/거절 버튼 비활성", len(cands) == 3 and all(c.count("disabled") == 2 and "승인" in c and "거절" in c for c in cands))
    check("키워드: 최근 거절 1줄", k.count('<p class="rejline">최근 거절: Luna') == 1)
    order = re.findall(r'<div class="kw-h"><h3>([^<]+)</h3>', k)
    items = DATA["keywords"]["items"]
    want = [items[i]["name"] for i in sorted(range(len(items)), key=lambda i: (-items[i]["mentions"][-1], i))]
    check("키워드: 8개가 이번 주 언급 많은 순", order == want and len(order) == 8, f"{order}")
    check("키워드: 가지에 후보 3개 점선, Luna 취소선", k.count('<li class="pend"><i class="br dashed">') == 3 and '<s class="lv">Luna</s>' in k)

    r = page_of("/runs/")
    no_url = lambda h: re.sub(r'<meta property="og:url"[^>]*>', "", h)
    check("실행 기록: 메뉴 링크가 /runs/, 10월 1주차 메인", 'href="/runs/" class="on"' in r and "10월 1주차 실행 기록</h1>" in r and no_url(r) == no_url(page_of("/runs/2026-w40/")))
    check("실행 기록: 봐야 할 판단 3개", "봐야 할 판단 3개" in r and r.count('class="att"') == 3)
    rail = re.findall(r'<div class="rl-h"><span>[^<]+</span>(?:' + re.escape(SEP) + r')?<b>([^<]+)</b></div><div class="rl-s">([^<]*)</div>', r)
    nums = [re.search(r"\d+", b).group() for b, _ in rail]
    check("실행 기록: 단계 레일 55, 9, 6, 6, 5(반려 1), 6", nums == ["55", "9", "6", "6", "5", "6"] and "반려 1회" in rail[4][1], f"{rail}")
    check("실행 기록: 실행 8개 목록", r.count('class="runrow"') == 8 and "이 주의 실행 8번" in r)
    w = page_of("/runs/weeks/")
    wk = re.findall(r'<li>(<a class="wk"|<div class="wk")', w)
    w38 = w.split("9월 3주차")[1] if "9월 3주차" in w else ""
    check("실행 기록: 상위에 3주, 9월 3주차는 승인 모드 + 링크 없음",
          len(wk) == 3 and wk[2] == '<div class="wk"' and '<span class="badge">승인 모드</span>' in w38 and "/runs/2026-w38/" not in w)
    bad = []
    for u in RUN_DETAILS:
        h = page_of(u)
        wid = u.split("/")[2]
        if not ('href="/runs/weeks/"' in h and f'href="/runs/{wid}/"' in h and h.count('<div class="bc">') == 1):
            bad.append(u)
    check(f"실행 기록: 상세 {len(RUN_DETAILS)}개 모두 경로 줄로 위로 이동", len(RUN_DETAILS) == 16 and not bad, ", ".join(bad))
    dd = page_of("/runs/2026-w40/weekly-2026-10-05/")
    box = re.search(r'<div class="reject">(.*?)</div></span>', dd)
    check("실행 기록: 10.5 주간 발행 상세에 반려 상자(초안, 근거, 수정)",
          bool(box) and all(x in box.group(1) for x in ['class="rk">초안', 'class="rk">근거', 'class="rk">수정', "(GeekNews, 10.2)"]))
    att_links = re.findall(r'class="att" href="([^"]+)"', r)
    check("실행 기록: 봐야 할 판단 링크가 판단 줄로 이동", all("#step-" in a for a in att_links))

    hl_over = []
    for u in ["/sources/", "/keywords/", "/runs/", "/runs/2026-w39/", "/runs/weeks/"] + RUN_DETAILS:
        n = page_of(u).count('<mark class="hl">')
        if n > 4:
            hl_over.append(f"{u}={n}")
    check("관리 화면 형광 밑줄 화면당 4개 이하", not hl_over, ", ".join(hl_over))
    notice = DATA["meta"]["notice"]
    with_notice = [url_of(p) for p in html_files() if notice[:20] in read(p)]
    check("맨 아래 예시 데이터 안내 문구 없음 (사용자 결정)", not with_notice, ", ".join(with_notice[:5]))

    # ------------------------------------------------------------ 05_TASK: 문체, 2차 리뷰
    haeyo = {}
    for p in sorted(SITE.rglob("*")):
        if p.is_file() and p.suffix in (".html", ".css", ".svg"):
            for m in re.findall(r"[가-힣]+(?:어요|에요|해요|예요|까요|세요|돼요|줘요)", p.read_text(encoding="utf-8")):
                haeyo[m] = haeyo.get(m, 0) + 1
    check("문체: 해요체 0건 (05 2-3 grep)", not haeyo, f"{haeyo}")
    fixed = {"/sources/": "예시 사이트라 동작 안 함", "/keywords/": "묶을 키워드: 판단 모델",
             "/topic/w40-jev-race/": "굵은 선: 수치를 직접 준 소스 / 점선: 이어지는 지난 토픽",
             "/runs/weeks/": "3주 발행 15개, 검수 반려 3회 / 0회 / 1회"}
    miss = [u for u, t in fixed.items() if t not in page_of(u)]
    check("문체: 화면 고정 문구 (02_DESIGN 10장 표)", not miss and "단계별 기록 없음 (예시 데이터 범위 밖)" in page_of("/runs/weeks/")
          and "여러 표기를 한 키워드로 묶음. 다른 대상을 잘못 묶지 않는 것이 우선" in page_of("/keywords/"), ", ".join(miss))
    n3 = page_of("/runs/2026-w40/nightly-2026-10-03/")
    tabs = re.search(r'<div class="rtabs">(.*?)</div>', n3).group(1)
    tab_txt = re.sub(r"<[^>]+>", "", tabs)
    check("2차 리뷰: 매일 수집 실패는 맨 위 한 줄만, 로그에 수집기 줄 없음, 탭은 steps만",
          n3.count('<p class="errline">') == 1 and "수집기" not in n3 and tab_txt == "전체 2 / 편집장 1 / 레포 분석가 1", tab_txt)
    w39w = page_of("/runs/2026-w39/weekly-2026-09-28/")
    check("2차 리뷰: 지난 주차 실행 상세는 \"이 주 수집\"", "<dd>이 주 수집 45건" in w39w and "이번 주" not in w39w.split("<body>")[1]
          and "<dd>이번 주 수집 55건" in page_of("/runs/2026-w40/weekly-2026-10-05/") and "이번 주" not in page_of("/runs/2026-w39/").split("<body>")[1])

    # ------------------------------------------------------------ 04_TASK: 파비콘, 공유 미리보기, 1차 리뷰
    HEAD_TAGS = ['<link rel="icon" href="/favicon.ico" sizes="any">', '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
                 '<link rel="apple-touch-icon" href="/apple-touch-icon.png">', '<meta name="theme-color" content="#ffffff">',
                 '<meta name="description" content="', '<meta property="og:type" content="website">',
                 '<meta property="og:site_name" content="TrendsIT">', '<meta property="og:title" content="',
                 '<meta property="og:description" content="', '<meta property="og:url" content="',
                 f'<meta property="og:image" content="{SITE_URL}/og-image.png">', '<meta name="twitter:card" content="summary_large_image">']
    bad_head = []
    for p in html_files():
        h = read(p)
        u = url_of(p)
        miss = [t for t in HEAD_TAGS if h.count(t) != 1]
        title = re.search(r"<title>([^<]*)</title>", h).group(1)
        ogt = re.search(r'<meta property="og:title" content="([^"]*)">', h)
        ogu = re.search(r'<meta property="og:url" content="([^"]*)">', h)
        desc = re.search(r'<meta name="description" content="([^"]*)">', h)
        ogd = re.search(r'<meta property="og:description" content="([^"]*)">', h)
        if miss or not ogt or ogt.group(1) != title or not ogu or ogu.group(1) != SITE_URL + u or not desc or not desc.group(1) or not ogd or ogd.group(1) != desc.group(1):
            bad_head.append(f"{u} {miss[:2]}")
    check(f"head 태그가 모든 페이지에 한 번씩, og:url이 그 페이지 주소 ({len(html_files())}개)", not bad_head, "; ".join(bad_head[:5]))
    import html as _html
    descs = {
        "/": f'{DATA["weeks"][0]["label"]} 기술 동향 브리핑. 토픽 {DATA["weeks"][0]["topic_count"]}개, 소스 {DATA["weeks"][0]["source_count"]}건',
        "/week/2026-w39/": f'{DATA["weeks"][1]["label"]} 기술 동향 브리핑. 토픽 {DATA["weeks"][1]["topic_count"]}개, 소스 {DATA["weeks"][1]["source_count"]}건',
        "/topic/w40-jev-race/": next(t for t in DATA["topics"] if t["id"] == "w40-jev-race")["summary"].replace("==", ""),
        "/sources/": "로컬 AI가 매주 정리하는 개인 기술 브리핑 (예시 데이터)",
    }
    got = {u: _html.unescape(re.search(r'<meta name="description" content="([^"]*)">', page_of(u)).group(1)) for u in descs}
    check("설명 문구 규칙 (홈/주차, 토픽 summary, 나머지 기본)", got == descs, f"{got}")

    leftover = [url_of(p) for p in html_files() if "==" in read(p)]
    check('형광: HTML에 "==" 남지 않음', not leftover, ", ".join(leftover[:5]))

    GLUE = [r"\d(?:지난|영상|레포|GitHub|확인|판단|정상|일부|편집장|작성자|검수자|수집기|이번|다음|예시)", r"(?:정상|일부 실패)판단",
            r"브리핑소스", r"키워드실행", r"TrendsIT브리핑", r"데이터TrendsIT", r"(?:확정|후보)(?:후보|거절)", r"\d{1,2}:\d{2}[가-힣]",
            r"(?:초안|근거|수정)(?:Pi|\")", r"\][A-Za-z가-힣]", r"[가-힣]\d+(?:\.\d+)?%"]
    glued = []
    for p in html_files():
        body = read(p).split("<body>", 1)[1]
        # 블록 경계는 텍스트 도구가 줄을 바꾸므로 줄바꿈으로, 나머지 태그는 지운다(인라인 항목 붙음만 잡는다)
        body = re.sub(r"</?(?:div|p|li|ul|ol|dl|dt|dd|h[1-6]|section|nav|header|main|aside|br)\b[^>]*>", "\n", body)
        text = _html.unescape(re.sub(r"<[^>]+>", "", body))
        for g in GLUE:
            for m in re.finditer(g, text):
                glued.append(f"{url_of(p)}: …{text[max(0, m.start() - 8):m.end() + 6]}…")
    check("붙어 읽히는 항목 없음 (태그를 지운 텍스트 기준)", not glued, " | ".join(glued[:8]))

    w39 = page_of("/week/2026-w39/")
    w40 = page_of("/")
    check("지난 주차 문구: 이 주의 핵심 토픽 / 이 주 관심 분야 레포 / 이 주 수집",
          all(x in w39 for x in ["이 주의 핵심 토픽", "이 주 수집", '<span class="m-only">이 주 </span>관심 분야 레포']) and "이번 주" not in w39.split("<body>")[1]
          and all(x in w40 for x in ["이번 주 핵심 토픽", "이번 주 수집"]))
    check('title: 지난 주차 "9월 4주차 브리핑 | TrendsIT", 최신 홈 "TrendsIT"',
          "<title>9월 4주차 브리핑 | TrendsIT</title>" in w39 and "<title>TrendsIT</title>" in w40 and "<title>TrendsIT</title>" in page_of("/week/2026-w40/"))
    check("헤더에 지난 주차 링크 (있을 때만)",
          all('class="wprev u" href="/week/2026-w39/"' in page_of(u) for u in ["/", "/week/2026-w40/"]) and 'class="wprev' not in w39)

    # ------------------------------------------------------------ 7. 색
    css = (SITE / "assets" / "style.css").read_text(encoding="utf-8")
    color_src = [("style.css", css)]
    for p in html_files():
        s = read(p)
        for m in re.findall(r'style="([^"]*)"', s):
            color_src.append((url_of(p) + " style", m))
        for m in re.findall(r'(?:fill|stroke|stop-color|color)="([^"]*)"', s):
            color_src.append((url_of(p) + " attr", m))
        for m in re.findall(r"<style[^>]*>(.*?)</style>", s, re.S):
            color_src.append((url_of(p) + " <style>", m))
    bad_colors = set()
    for where, text in color_src:
        for hx in re.findall(r"#[0-9a-fA-F]{3,8}\b", text):
            if hx.lower() not in ALLOWED_COLORS:
                bad_colors.add(f"{where}:{hx}")
        for fn in re.findall(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklch|oklab|color)\(", text):
            bad_colors.add(f"{where}:{fn}")
        for word in re.findall(r"(?<![\w-])[a-zA-Z]+(?![\w-])", re.sub(r"var\([^)]*\)|--[\w-]+|\"[^\"]*\"", "", text)):
            if word.lower() in NAMED_COLORS:
                bad_colors.add(f"{where}:{word}")
    if not color_src:
        bad_colors.add("검사 대상 없음")
    check("색 값은 토큰, #fff, transparent, none뿐 (유채색은 #ffd5c0 하나)", not bad_colors, ", ".join(sorted(bad_colors)[:10]))

    # ------------------------------------------------------------ 8. 금지 CSS
    all_css = [("style.css", css)] + [(w, t) for w, t in color_src if not w.endswith(" attr")]
    bad_css = []
    for where, text in all_css:
        low = text.lower()
        for pat, label in [
            (r"box-shadow", "box-shadow"), (r"text-transform\s*:\s*uppercase", "uppercase"), (r"monospace", "monospace"),
            (r"\banimation", "animation"), (r"@keyframes", "keyframes"), (r"\btransition", "transition"),
        ]:
            if re.search(pat, low):
                bad_css.append(f"{where}:{label}")
        for v in re.findall(r"border-radius\s*:\s*([^;}]+)", low):
            for px in re.findall(r"([\d.]+)px", v):
                if float(px) >= 999:
                    bad_css.append(f"{where}:radius {v.strip()}")
    for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if re.search(r"border-radius\s*:\s*50%", decl):
            w_ = re.search(r"(?<![-\w])width\s*:\s*([\d.]+)px", decl)
            h_ = re.search(r"(?<![-\w])height\s*:\s*([\d.]+)px", decl)
            if not (w_ and h_ and float(w_.group(1)) <= 12 and float(h_.group(1)) <= 12):
                bad_css.append(f"원형이 12px 초과 또는 크기 미지정: {sel.strip()}")
    check("금지 CSS 없음 (그림자, 대문자, 고정폭, 애니메이션, 전환, 알약, 큰 원)", not bad_css, "; ".join(bad_css[:10]))

    # ------------------------------------------------------------ 9. 외부 리소스
    ext = []
    for p in html_files():
        s = read(p)
        for tag, attr in [("link", "href"), ("script", "src"), ("img", "src"), ("iframe", "src"), ("source", "src"), ("image", "href")]:
            for m in re.findall(rf"<{tag}\b[^>]*\b{attr}=\"([^\"]+)\"", s):
                if re.match(r"(https?:)?//", m) and not m.startswith(FONT_HOSTS):
                    ext.append(f"{url_of(p)} <{tag}> {m}")
        if "<script" in s:
            ext.append(f"{url_of(p)} <script> 있음")
    for where, text in all_css:
        for m in re.findall(r"@import\s+(?:url\()?['\"]?([^'\")\s;]+)", text) + re.findall(r"url\(\s*['\"]?([^'\")]+)", text):
            if not m.startswith(FONT_HOSTS):
                ext.append(f"{where} {m}")
    check("외부 리소스는 Google Fonts뿐, 스크립트 없음", not ext, "; ".join(ext[:10]))

    # ------------------------------------------------------------ 기타: lang, title
    lt = [url_of(p) for p in html_files() if '<html lang="ko">' not in read(p) or not re.search(r"<title>[^<]*TrendsIT[^<]*</title>", read(p))]
    check('모든 페이지 lang="ko"와 title에 TrendsIT', not lt, ", ".join(lt))

    # ------------------------------------------------------------ 10. 가로 스크롤 + 스크린샷
    def find_playwright():
        roots = []
        try:
            roots.append(pathlib.Path(subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, timeout=20).stdout.strip()))
        except Exception:
            pass
        cli = shutil.which("playwright-cli")
        if cli:  # .../lib/node_modules/@playwright/cli/... 에서 node_modules 루트를 찾는다
            for parent in pathlib.Path(cli).resolve().parents:
                if parent.name == "node_modules":
                    roots.append(parent)
                    break
        for root in roots:
            for rel in ("playwright", "@playwright/cli/node_modules/playwright", "@playwright/test/node_modules/playwright"):
                if (root / rel / "package.json").is_file():
                    return str(root / rel)
        return None

    pw = find_playwright()
    if not pw:
        skip("390px, 1280px 가로 스크롤 없음", "수동 확인 필요: Playwright 없음")
    else:
        SHOTS.mkdir(exist_ok=True)
        shot_pages = {"/": "home", "/week/2026-w39/": "week-w39", "/topic/w40-jev-race/": "topic-w40-jev-race",
                      "/topic/w40-measure/": "topic-w40-measure", "/topic/w40-browser-security/": "topic-w40-browser-security",
                      "/sources/": "sources", "/keywords/": "keywords", "/runs/": "runs",
                      "/runs/weeks/": "runs-weeks", "/runs/2026-w40/weekly-2026-10-05/": "run-weekly-2026-10-05",
                      "/runs/2026-w40/nightly-2026-10-03/": "run-nightly-2026-10-03"}
        js = """
const { chromium } = require(process.env.PW);
(async () => {
  const pages = JSON.parse(process.env.PAGES), shots = JSON.parse(process.env.SHOT_PAGES);
  const browser = await chromium.launch();
  const out = [];
  for (const width of [390, 1280]) {
    const ctx = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    for (const u of pages) {
      if (u.endsWith('.css')) continue;
      await page.goto(process.env.BASE + u, { waitUntil: 'networkidle' });
      await page.evaluate(() => document.fonts.ready);
      const r = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth,
        font: document.fonts.check('16px "IBM Plex Sans KR"') }));
      out.push({ u, width, ...r });
      if (shots[u]) await page.screenshot({ path: `${process.env.SHOTS}/${shots[u]}-${width}.png`, fullPage: true });
    }
    await ctx.close();
  }
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
"""
        with tempfile.NamedTemporaryFile("w", suffix=".cjs", delete=False) as f:
            f.write(js)
        env = dict(os.environ, PW=pw, PAGES=json.dumps(PAGES), SHOT_PAGES=json.dumps(shot_pages),
                   BASE=f"http://127.0.0.1:{PORT}", SHOTS=str(SHOTS))
        r = subprocess.run(["node", f.name], capture_output=True, text=True, env=env, timeout=300)
        os.unlink(f.name)
        if r.returncode != 0:
            skip("390px, 1280px 가로 스크롤 없음", "수동 확인 필요: 브라우저 실행 실패 " + r.stderr.strip()[-200:])
        else:
            rows = json.loads(r.stdout.strip().splitlines()[-1])
            over = [f'{x["u"]}@{x["width"]} ({x["sw"]}>{x["iw"]})' for x in rows if x["sw"] > x["iw"]]
            check(f"390px, 1280px 가로 스크롤 없음 ({len(rows)}회 측정)", not over, "; ".join(over))
            nofont = sorted({x["u"] for x in rows if not x["font"]})
            print(("INFO IBM Plex Sans KR 로드됨" if not nofont else f"INFO 웹폰트 미로드: {nofont}"))
            print(f"INFO 스크린샷: {SHOTS}")
finally:
    server.terminate()
    server.wait()

failed = [n for n, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} 통과")
sys.exit(1 if failed else 0)
