# TrendsIT 사이트 검증(S6a). 실행: uv run python site_src/check.py [--fixture | --site DIR --data FILE]
# 정적 검사(C-3~C-5, 링크, 글꼴·CSS, 관리 화면) → 관문 9(Chromium·WebKit) + 동작(툴팁, 탭, 미니 바)은 gate.js(Node, 전역 playwright-core).
# 인자 없이 돌리면 site/(실데이터)를 data/site.json 기준으로, --fixture면 tests/fixtures/site/site.json을 임시 폴더에 빌드해서 같은 기준으로 검사.
# 하나라도 실패하면 종료 코드 1(실패 목록을 끝에 다시 출력). 브라우저 측정 도구를 못 찾으면 그것도 실패(건너뛰지 않음).
import argparse
import functools
import glob
import html
import http.server
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from html.parser import HTMLParser

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parent
FIXTURE = ROOT / "tests" / "fixtures" / "site" / "site.json"
FORBIDDEN_TEXT = ("동작 안 함", "예시")
OPS_BANNED = ("button", "form", "input", "select", "textarea")
VOID = {"meta", "link", "br", "img", "input", "hr", "source"}
results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags, self.links, self.ids, self.titles, self.text, self.classes, self.pn = {}, [], set(), 0, [], [], []
        self.open, self.mismatch = [], 0  # 태그 중첩 어긋남 수

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in VOID:
            self.open.append(tag)
        self.tags[tag] = self.tags.get(tag, 0) + 1
        if "id" in a:
            self.ids.add(a["id"])
        if "title" in a and tag != "link":
            self.titles += 1
        if "class" in a:
            self.classes.append((tag, a["class"].split()))
        if tag == "a" and {"pn-prev", "pn-next"} & set(a.get("class", "").split()):
            self.pn.append(a["href"])
        for k in ("href", "src"):
            if a.get(k) is not None:
                self.links.append((tag, a.get("rel", ""), k, a[k]))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.open and self.open[-1] == tag:
            self.open.pop()
        else:
            self.mismatch += 1
            if tag in self.open:
                while self.open.pop() != tag:
                    pass

    def handle_data(self, data):
        self.text.append(data)


def parse(path):
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    return p


def page_url(site, f):
    rel = f.relative_to(site).as_posix()
    return "/" + rel[: -len("index.html")] if rel.endswith("index.html") else "/" + rel


def is_internal(href):
    return not re.match(r"^([a-z][a-z0-9+.-]*:|//)", href, re.I)


def static_checks(site, data, pages):
    files = sorted(site.rglob("*.html"))
    check("A7 페이지 존재: 홈, 소스, 키워드, 실행 기록(주차별·이번 주차·1건)",
          all((site / p).exists() for p in ("index.html", "sources/index.html", "keywords/index.html", "runs/index.html", "runs/weeks/index.html"))
          and any(f.parent.parent.parent.name == "runs" for f in files), f"html {len(files)}개")
    broken = [f"{page_url(site, f)} 중첩 어긋남 {p.mismatch}" for f, p in pages.items() if p.mismatch or p.open]
    broken += [f"{page_url(site, f)} 본문에 마크업 조각·엔티티 노출" for f, p in pages.items() if re.search(r'class="|<span|</span|&#\w+;|&(?:quot|amp|lt|gt);', "".join(p.text))]
    check("M-1 마크업 무결성: 태그 중첩 어긋남 0, 본문 글자에 class=·<span·엔티티(&#x27; &quot; &amp;) 노출 0", not broken, "; ".join(broken[:3]))
    # C-3 내부 링크의 대상 파일·앵커
    bad = []
    for f, p in pages.items():
        for tag, _rel, _k, href in p.links:
            if not is_internal(href) or href == "":
                continue
            u = urllib.parse.urlparse(urllib.parse.urljoin("http://x" + page_url(site, f), href))
            path = urllib.parse.unquote(u.path)
            target = site / (path.lstrip("/") + ("index.html" if path.endswith("/") else ""))
            if not target.is_file():
                bad.append(f"{page_url(site, f)} → {href}")
            elif u.fragment and target.suffix == ".html":
                tp = pages.get(target) or parse(target)
                if u.fragment not in tp.ids:
                    bad.append(f"{page_url(site, f)} → {href}(앵커 없음)")
    check("C-3 내부 링크 대상 파일·앵커 존재", not bad, "; ".join(bad[:4]))
    # A5 링크 규칙(D-6)
    weeks = data["weeks"]
    oldest = site / "week" / weeks[-1]["id"] / "index.html"
    first = [oldest] + ([site / "index.html"] if len(weeks) == 1 else [])
    absent = [f"{page_url(site, f)}" for f in [*first, *(site / "week" / w["id"] / "index.html" for w in weeks), *(site / "topic" / t["id"] / "index.html" for t in data["topics"])] if f not in pages]
    if absent:  # site.json과 site/가 어긋남(예: 발행 중 실패로 한쪽만 바뀜): 트레이스백 대신 실패로 기록
        check("A5 링크 규칙", False, f"data에는 있고 site/에는 없는 페이지: {', '.join(absent[:3])}")
        return
    ok1 = all("지난 주차" not in "".join(pages[f].text) for f in first)
    ok2 = all(any(h == f'/week/{weeks[i + 1]["id"]}/' for _, _, _, h in pages[site / "week" / w["id"] / "index.html"].links)
              for i, w in enumerate(weeks[:-1]))
    topics = {t["id"]: t for t in data["topics"]}
    bad = []
    for t in data["topics"]:
        p = pages[site / "topic" / t["id"] / "index.html"]
        rel = t.get("relation", {})
        has_follow = any("follow" in c for _, c in p.classes)
        want = rel.get("type") == "follow_up" and rel.get("topic_id") in topics
        if has_follow != want or (want and f'/topic/{rel["topic_id"]}/' not in [h for _, _, _, h in p.links]):
            bad.append(f'{t["id"]} follow={has_follow} 기대={want}')
        wk = next(w for w in weeks if w["id"] == t["week"])
        if any(h.split("/")[2] not in wk["topic_ids"] for h in p.pn):
            bad.append(f'{t["id"]} 이전·다음이 다른 주로 이어짐')
    check("A5 첫 주에 지난 주차 링크 없음, 대상 없는 follow_up은 링크 없음, 이전·다음은 같은 주 안", ok1 and ok2 and not bad,
          "; ".join(bad[:3]) or ("" if ok1 and ok2 else f"지난 주차 링크 오류 첫 주 {ok1} 나머지 {ok2}"))
    # C-4, A6 외부 요청·글꼴·CSS
    css_files = sorted((site / "assets").glob("*.css"))
    css = "\n".join(f.read_text(encoding="utf-8") for f in css_files)
    ext = []
    for f, p in pages.items():
        if p.tags.get("script"):
            ext.append(f"{page_url(site, f)} script {p.tags['script']}")
        ext += [h for tag, rel, _k, h in p.links if tag in ("link", "script", "img", "source") and not is_internal(h)]
    ext += re.findall(r"@import|url\(\s*[\"']?(?:https?:)?//[^)]*", css)
    check("C-4 외부 요청 0: link·script·@import·url()에 http 없음, script 0", not ext, "; ".join(map(str, ext[:3])))
    faces = re.findall(r"@font-face\{[^}]*\}", css)
    weights = sorted(re.findall(r"font-weight:(\d+)", "".join(faces)))
    names = [f.name for f in css_files]
    googles = [f.name for f in [*files, *css_files] if re.search(r"fonts\.(googleapis|gstatic)", f.read_text(encoding="utf-8"))]
    check("A6 @font-face 400·500 둘뿐, CSS 파일명에 해시, Google Fonts 문자열 0",
          weights == ["400", "500"] and len(faces) == 2 and len(names) == 1 and re.fullmatch(r"trendsit\.[0-9a-f]{10}\.css", names[0])
          and not googles and (site / "assets/fonts/Pretendard-Regular.woff2").is_file() and (site / "assets/fonts/Pretendard-Medium.woff2").is_file(),
          f"faces {len(faces)} weights {weights} css {names} google {googles}")
    # C-5, C-7(title 속성) 관리 화면 조작 요소, 문구
    banned = [f"{page_url(site, f)} <{t}>" for f, p in pages.items() for t in OPS_BANNED if p.tags.get(t)]
    check("C-5 button·form·input·select·textarea 0", not banned, "; ".join(banned[:3]))
    own = [s for s in data_strings(data) if any(w in s for w in FORBIDDEN_TEXT)]
    hits = []
    for f, p in pages.items():
        text = "".join(p.text)
        for s in sorted(own, key=len, reverse=True):  # 브리핑 내용(데이터) 안의 단어는 뺀다: 화면이 만든 문구만 검사
            text = text.replace(s, "")
        hits += [f"{page_url(site, f)} '{w}'" for w in FORBIDDEN_TEXT if w in text]
    check("A7 '동작 안 함'·'예시' 문구 0(사이트 전체, 데이터 본문 제외)", not hits, "; ".join(hits[:3]))
    check("C-7 title 속성 0", not any(p.titles for p in pages.values()))


def data_strings(data):
    out = []

    def walk(v):
        if isinstance(v, str):
            out.append(v.replace("==", "").replace("`", ""))
            out.append(html.unescape(v))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(data)
    return out


def find_playwright():
    """(node, playwright-core 경로). 전역 @playwright/cli에 든 playwright-core를 npm root -g와 nvm 설치 폴더에서 찾는다."""
    roots = []
    if shutil.which("npm"):
        r = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True)
        roots.append(r.stdout.strip())
    roots += glob.glob(str(pathlib.Path.home() / ".nvm/versions/node/*/lib/node_modules"))
    roots.append(str(pathlib.Path.home() / ".local/lib/node_modules"))
    for root in roots:
        pw = pathlib.Path(root) / "@playwright/cli/node_modules/playwright-core"
        node = pathlib.Path(root).parent.parent / "bin" / "node"
        node = str(node) if node.exists() else shutil.which("node")
        if pw.is_dir() and node:
            return node, str(pw)
    return None, None


def pick_pages(data):
    """측정할 페이지: 홈, 토픽 3(제목이 가장 긴 것, 출처 가장 많은 것, 출처 가장 적은 것), 소스, 키워드, 실행 기록 1건."""
    ts = data["topics"]
    chosen = []
    for key in (lambda t: len(t["title"]), lambda t: len(t["sources"]), lambda t: -len(t["sources"])):
        t = next((t for t in sorted(ts, key=key, reverse=True) if t not in chosen), None)
        if t:
            chosen.append(t)
    most = max(ts, key=lambda t: len(t["sources"]))
    pages = [{"name": "home", "path": "/"}]
    pages += [{"name": f'topic {t["id"]}', "path": f'/topic/{t["id"]}/', "topic": True, "longTopic": t is most} for t in chosen]
    run = next((r for r in data["runs"] if r["kind"] == "weekly" and r.get("week")), None)
    pages += [{"name": "sources", "path": "/sources/"}, {"name": "keywords", "path": "/keywords/"}]
    if run:
        pages.append({"name": "run", "path": f'/runs/{run["week"]}/{run["id"]}/'})
    return pages


def gate9(g, vh):
    """gate.js 한 건 → 실패한 항목 이름 목록(관문 9의 9항목)."""
    bad = []
    for ok, name in ((g["overflow"] <= 0, "1 가로 넘침"), (g["lowContrastN"] == 0, "2 대비"), (g["bodyTextBadN"] == 0, "3 본문 크기·줄 간격"),
                     (not g["hlMidBreaks"], "4 형광 끊김"), (g["smallRefs"] == 0, "6 인용 누를 영역"), (not g["colorsOff"], "7 토큰 밖 색"),
                     (all(f[1] for f in g["fonts"]), "8 글꼴 로드"), (g["headingSkips"] == 0 and g["titleAttrs"] == 0, "9 제목 단계·title")):
        if not ok:
            bad.append(name)
    return bad


def browser_checks(site, data):
    node, pw = find_playwright()
    if not node:
        check("A8 관문 9 Chromium", False, "playwright-core(전역 @playwright/cli)나 node를 찾지 못함: 브라우저 AC는 건너뛰지 않고 실패로 둔다")
        check("A9 관문 9 WebKit", False, "같은 이유")
        check("A10 동작", False, "같은 이유")
        return
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None}), directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    pages = pick_pages(data)
    try:
        r = subprocess.run([node, str(SRC / "gate.js"), pw, base, json.dumps(pages), str(SRC / "tokens.css")], capture_output=True, text=True, timeout=600)
    finally:
        server.shutdown()
    if r.returncode != 0:
        for n in ("A8 관문 9 Chromium", "A9 관문 9 WebKit", "A10 동작"):
            check(n, False, f"gate.js 실패(종료 {r.returncode}): {r.stderr.strip()[-300:]}")
        return
    out = json.loads(r.stdout)
    for name, eng, aid in (("chromium", "Chromium 375·768·1280", "A8"), ("webkit", "WebKit 375(모바일·터치)·1280", "A9")):
        bad = []
        for e in (x for x in out["gates"] if x["browser"] == name):
            miss = gate9(e["gate"], 812)
            if e["topic"] and e["vw"] == 375 and not (e["gate"]["pointsTop"] is not None and e["gate"]["pointsTop"] < 812):
                miss.append(f'5 핵심 포인트가 첫 화면 밖({e["gate"]["pointsTop"]})')
            bad += [f'{e["vw"]} {e["page"]}: {m}' for m in miss]
        n = sum(x["browser"] == name for x in out["gates"])
        extra = ""
        if name == "webkit":
            t = out["touch"]
            if not (t["hash"] == t["href"] and t["target"]):
                bad.append(f'터치: 375에서 인용 번호를 눌러도 출처 목록으로 이동하지 않음({t})')
            extra = f", 터치 {t['href']} → {t['hash']}"
        check(f"{aid} 관문 9 {eng}: 페이지·화면 {n}건 × 9항목", not bad, "; ".join(bad[:5]) or f"전부 통과{extra}")
    check("C-4 브라우저가 낸 요청이 모두 같은 서버(외부 요청 0)", not out["external"], "; ".join(out["external"][:3]))
    b = out["behavior"]
    ms = b.get("miniScrolled") or {}
    problems = [m for ok, m in (
        (b.get("cites", 0) >= 2, "인용이 2개 미만"), (b.get("early") is False, "툴팁이 0.15초 전에 보임"), (b.get("shown"), "0.15초 뒤에 안 보임"),
        (b.get("lingers"), "벗어나자마자 닫힘(0.6초 유지 아님)"), (b.get("closed"), "1초 뒤에도 안 닫힘"), (b.get("only") == [b.get("expectOnly")], f'동시에 하나가 아님 {b.get("only")} 기대 {b.get("expectOnly")}'),
        (b.get("miniTop") == "hidden", f'맨 위에서 미니 바가 보임({b.get("miniTop")})'),
        (ms.get("visibility") == "visible" and 0 <= ms.get("top", -1) < ms.get("height", 0), f"제목이 빠져도 미니 바가 안 보임({ms})"),
        (b["tabDefault"] == {"topics": "block", "repos": "none"}, f'기본 탭 {b["tabDefault"]}'),
        (b["tabRepos"] == {"topics": "none", "repos": "block"}, f'#repos 탭 {b["tabRepos"]}'),
        (b["tabClick"] == {"topics": "none", "repos": "block"}, f'탭 클릭 {b["tabClick"]}')) if not ok]
    check("A10 동작(Chromium 1280): 툴팁 0.15초 뒤·0.6초 유지·1초 뒤 닫힘·동시에 하나, 탭(기본·#repos), 미니 바", not problems, "; ".join(problems))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", action="store_true", help="픽스처를 임시 폴더에 빌드해서 검사")
    ap.add_argument("--site", default=str(ROOT / "site"))
    ap.add_argument("--data", default=str(ROOT / "data" / "site.json"))
    a = ap.parse_args()
    tmp = None
    site, data_path = pathlib.Path(a.site), pathlib.Path(a.data)
    if a.fixture:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="check-site-"))
        site, data_path = tmp / "site", FIXTURE
        r = subprocess.run([sys.executable, str(SRC / "build.py"), "--data", str(FIXTURE), "--out", str(site)], capture_output=True, text=True)
        check("픽스처 빌드", r.returncode == 0 and site.is_dir(), (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")
    try:
        if not site.is_dir() or not data_path.is_file():
            check("검사 대상", False, f"{site} 또는 {data_path} 없음")
        else:
            data = json.loads(data_path.read_text(encoding="utf-8"))
            pages = {f: parse(f) for f in sorted(site.rglob("*.html"))}
            for step in (lambda: static_checks(site, data, pages), lambda: browser_checks(site, data)):
                try:
                    step()
                except Exception as e:  # noqa: BLE001 - 어긋난 입력에서도 트레이스백 대신 실패 목록으로
                    check("검사 실행", False, f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} 통과")
    for name, _, detail in failed:
        print(f"실패: {name}  ({detail})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
