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

PAGES = ["/", "/week/2026-w39/", "/week/2026-w40/"] + [f'/topic/{t["id"]}/' for t in DATA["topics"]] + ["/sources/", "/keywords/", "/runs/", "/assets/style.css"]

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
        check(f"{u} 요약 재수록 없음", t["summary"].replace("==", "")[:30] not in s.replace('<mark class="hl">', "").replace("</mark>", ""))
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
                      "/sources/": "sources", "/keywords/": "keywords", "/runs/": "runs"}
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
