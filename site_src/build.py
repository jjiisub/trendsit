# TrendsIT 정적 예시 사이트 빌드. 실행: python3 site_src/build.py
# 입력: data/trendsit-example.json / 출력: site/ (지우지 않고 덮어씀). 표준 라이브러리만 쓴다.
import datetime
import hashlib
import html
import json
import math
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "trendsit-example.json"
OUT = ROOT / "site"
CSS_SRC = pathlib.Path(__file__).resolve().parent / "style.css"
# CSS 주소에 내용 해시를 붙여 Cloudflare 캐시(4시간)가 옛 CSS를 주지 않게 한다
CSS_VER = hashlib.sha256(CSS_SRC.read_bytes()).hexdigest()[:10]
STATIC = pathlib.Path(__file__).resolve().parent / "static"  # 파비콘, 공유 미리보기 이미지 → site/ 루트로 복사
SITE_URL = "https://trendsit.jiseop.com"
DEFAULT_DESC = "로컬 AI가 매주 정리하는 개인 기술 브리핑 (예시 데이터)"
# 간격으로만 떨어진 항목 사이의 글자 구분. 화면에는 숨기고 텍스트에는 남긴다
SEP = '<span class="sr-sep"> / </span>'

FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;700&amp;display=swap">'
)

# 채널 회색 (02_DESIGN 3장)
CH_FILL = {"text": "#2a3038", "video": "#868b94", "github": "#d1d3d8"}
CH_ORDER = ["text", "video", "github"]
SOURCE_TYPE_LABELS = {"rss": "RSS", "arxiv": "arXiv", "youtube": "유튜브", "oss_insight": "OSS Insight", "github_repos": "레포 추적"}
RUN_KIND_LABELS = {"weekly": "주간 발행", "nightly": "매일 수집"}
RUN_STATUS_LABELS = {"ok": "정상", "partial": "일부 실패"}
DISABLED_NOTE = "예시 사이트라 동작 안 함"


# ---------------------------------------------------------------- 공통 도우미
def esc(s):
    return html.escape(str(s), quote=True)


def hl(s):
    """HTML 이스케이프 먼저, 그다음 ==텍스트== → 형광 밑줄."""
    return re.sub(r"==(.+?)==", r'<mark class="hl">\1</mark>', esc(s))


def plain(s):
    return str(s).replace("==", "")


def md(date_str):
    """'2026-09-22' → '9.22'"""
    _, m, d = date_str[:10].split("-")
    return f"{int(m)}.{int(d)}"


def mdhm(ts):
    """'2026-10-05T07:00:00+09:00' → '10.5 07:00'"""
    return f"{md(ts)} {ts[11:16]}"


def num(v):
    return str(int(v)) if float(v).is_integer() else str(v)


def text_w(s, size):
    """SVG 글자 폭 어림값(px). 한글·전각은 0.95em, 나머지는 0.56em."""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3 or 0x3130 <= o <= 0x318F or 0x4E00 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFFEF:
            w += 0.95
        elif ch == " ":
            w += 0.28
        else:
            w += 0.56
    return w * size


def channel_bar(counts, cls="bar"):
    parts = "".join(
        f'<span class="c-{c}" style="flex: {counts[c]}"></span>' for c in CH_ORDER if counts.get(c)
    )
    return f'<span class="{cls}" aria-hidden="true">{parts}</span>'


def channel_text(counts, labels):
    return " / ".join(f"{labels[c]} {counts[c]}" for c in CH_ORDER if counts.get(c))


def badge(text):
    return f'<span class="badge">{esc(text)}</span>'


def write(rel, content):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------- 페이지 틀
TABS = [("briefing", "/", "브리핑"), ("sources", "/sources/", "소스"), ("keywords", "/keywords/", "키워드"), ("runs", "/runs/", "실행 기록")]


def tabs_html(active):
    out = []
    for key, href, label in TABS:
        cur = ' class="on" aria-current="page"' if key == active else ""
        out.append(f'<a href="{href}"{cur}>{label}</a>')
    return SEP.join(out)


def site_header(active):
    return (
        '<header class="top">\n'
        '  <div class="top-in">\n'
        '    <a class="wordmark" href="/">TrendsIT</a>\n'
        f'    {SEP}<nav class="tabs">{tabs_html(active)}</nav>\n'
        f'    {SEP}<span class="ex">예시 데이터</span>\n'
        "  </div>\n"
        "</header>"
    )


def page(title, body, header, path, desc=DEFAULT_DESC):
    head_meta = (
        '<link rel="icon" href="/favicon.ico" sizes="any">\n'
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
        '<meta name="theme-color" content="#ffffff">\n'
        f'<meta name="description" content="{esc(desc)}">\n'
        '<meta property="og:type" content="website">\n'
        '<meta property="og:site_name" content="TrendsIT">\n'
        f'<meta property="og:title" content="{esc(title)}">\n'
        f'<meta property="og:description" content="{esc(desc)}">\n'
        f'<meta property="og:url" content="{SITE_URL}{esc(path)}">\n'
        f'<meta property="og:image" content="{SITE_URL}/og-image.png">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
    )
    return (
        "<!doctype html>\n"
        '<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n{head_meta}{FONT_LINKS}\n"
        f'<link rel="stylesheet" href="/assets/style.css?v={CSS_VER}">\n'
        "</head>\n<body>\n"
        f"{header}\n{body}\n"
        "</body>\n</html>\n"
    )


# ---------------------------------------------------------------- 홈 (주차 브리핑)
def topic_meta(t, meta, ctx):
    bits = [channel_bar(t["channels"]), f'<span>{esc(channel_text(t["channels"], meta["channel_labels_topic"]))}</span>']
    if t["relation"]["type"] == "follow_up":
        bits.append("<span>지난 흐름의 후속</span>")
    checks = sum(1 for p in t["points"] if p.get("check"))
    if t.get("has_check") and checks:
        bits.append(badge(f"확인 필요 {checks}"))
    return f'<div class="meta">{bits[0]}{SEP.join(bits[1:])}</div>'


def collect_block(w, meta, cls):
    c = w["collected"]
    legend = SEP.join(
        f'<span class="lg"><span class="sq c-{ch}"></span>{esc(meta["channel_labels"][ch])} {c[ch]}</span>'
        for ch in CH_ORDER
    )
    return (
        f'<div class="collect {cls}">'
        f'{channel_bar(c, "wbar")}'
        f'<div class="legend">{legend}</div>'
        "</div>"
    )


def repo_item(r, meta, topics):
    stars_cls = "stars dim" if r["signal"] == "needs_check" else "stars"
    name = esc(r["name"])
    if r.get("url"):
        name = f'<a class="rname" href="{esc(r["url"])}" target="_blank" rel="noopener">{name}</a>'
    else:
        name = f'<span class="rname">{name}</span>'
    third = []
    sig = meta["signal_labels"][r["signal"]]
    third.append(badge(sig) if r["signal"] == "needs_check" else esc(sig))
    if r.get("note"):
        third.append(esc(r["note"]))
    if r.get("topic_id"):
        tt = topics[r["topic_id"]]["title"]
        third.append(f'<a class="lk" href="/topic/{esc(r["topic_id"])}/">\'{esc(tt)}\' 토픽과 관련</a>')
    return (
        '<li class="repo">'
        f'<div class="r1">{name}{SEP}<span class="{stars_cls}">{esc(r["stars_7d"])}</span></div>'
        f'<div class="r2">{esc(r["what"])}</div>'
        f'<div class="r3">{" / ".join(third)}</div>'
        "</li>"
    )


def week_path(w, latest_id):
    return "/" if w["id"] == latest_id else f'/week/{w["id"]}/'


def render_week(d, wi, topics, path):
    meta = d["meta"]
    weeks = d["weeks"]
    w = weeks[wi]
    ts = [topics[i] for i in w["topic_ids"]]
    ts.sort(key=lambda t: t["rank"])
    lead = [t for t in ts if t.get("lead")]
    rest = [t for t in ts if not t.get("lead")]
    this = "이번 주" if wi == 0 else "이 주"  # 지난 주차 페이지는 "이 주"
    prev_link = ""
    if wi + 1 < len(weeks):
        pw = weeks[wi + 1]
        prev_link = f'{SEP}<a class="wprev u" href="/week/{esc(pw["id"])}/">지난 주차: {esc(pw["label"])}</a>'

    head = (
        '<div class="whead">'
        f'<h1 class="wtitle">{esc(w["label"])}</h1>'
        f'{SEP}<div class="wsub">{esc(w["range"])} / 소스 {w["source_count"]}건에서 토픽 {w["topic_count"]}개</div>'
        f"{prev_link}"
        f'{collect_block(w, meta, "m-only")}'
        "</div>"
    )
    lead_html = ""
    for t in lead:
        lead_html += (
            f'<a class="lead row" href="/topic/{esc(t["id"])}/">'
            f'<div class="lead-k">{"이번 주" if wi == 0 else "이 주의"} 핵심 토픽</div>'
            f'<h2 class="t lead-t">{esc(t["title"])}</h2>'
            f'<p class="lead-s">{hl(t["summary"])}</p>'
            f"{topic_meta(t, meta, 'lead')}"
            "</a>"
        )
    items = "".join(
        f'<li><a class="item row" href="/topic/{esc(t["id"])}/">'
        f'<h3 class="t item-t">{esc(t["title"])}</h3>'
        f'<p class="item-s">{hl(t["summary"])}</p>'
        f"{topic_meta(t, meta, 'item')}"
        "</a></li>"
        for t in rest
    )
    repos = [r for r in d["repos"] if r["week"] == w["id"]]
    repo_html = "".join(repo_item(r, meta, topics) for r in repos)

    nav = []
    if wi + 1 < len(weeks):
        pw = weeks[wi + 1]
        nav.append(f'<a class="lk" href="/week/{esc(pw["id"])}/">지난 주차: {esc(pw["label"])}</a>')
    if wi > 0:
        nw = weeks[wi - 1]
        nav.append(f'<a class="lk" href="/week/{esc(nw["id"])}/">다음 주차: {esc(nw["label"])}</a>')

    body = (
        '<div class="wrap two">\n'
        f'<main class="col-main">{head}{lead_html}<ul class="items">{items}</ul></main>\n'
        '<aside class="col-side">'
        f'<section class="side-collect p-only"><h2 class="side-h">{this} 수집</h2>'
        f'{collect_block(w, meta, "")}</section>'
        f'<section class="repos"><h2 class="side-h"><span class="m-only">{this} </span>관심 분야 레포</h2>'
        f'<ul class="repo-list">{repo_html}</ul></section>'
        f'<nav class="weeknav">{SEP.join(nav)}</nav>'
        f'<div class="runat">발행 {mdhm(w["published_at"])}<span class="sep"> / </span><br class="p-br">다음 발행 {mdhm(w["next_run"])}</div>'
        "</aside>\n"
        "</div>"
    )
    title = "TrendsIT" if wi == 0 else f'{w["label"]} 브리핑 | TrendsIT'
    desc = f'{w["label"]} 기술 동향 브리핑. 토픽 {w["topic_count"]}개, 소스 {w["source_count"]}건'
    return page(title, body, site_header("briefing"), path, desc)


# ---------------------------------------------------------------- 도식 A: 소스 연결도
def place_labels(nodes, W, H, center_box, segments, size=11, line_h=13):
    """노드마다 라벨 위치 후보(위, 아래, 바깥쪽 옆, 두 줄)를 차례로 시도해 겹치지 않는 첫 자리를 고른다.
    다른 라벨, 노드, 가운데 상자와 겹친 넓이 + 선 위에 놓인 정도를 비용으로 본다."""
    placed = []
    line_pts = []
    for (x1, y1, x2, y2) in segments:
        steps = max(1, int(math.hypot(x2 - x1, y2 - y1) / 4))
        line_pts += [(x1 + (x2 - x1) * k / steps, y1 + (y2 - y1) * k / steps) for k in range(steps + 1)]
    obstacles = [center_box] + [(n["x"] - n["r"] - 2, n["y"] - n["r"] - 2, n["x"] + n["r"] + 2, n["y"] + n["r"] + 2) for n in nodes]

    def overlap(a, b):
        return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))

    def boxes_for(n, lines):
        w = max(text_w(s, size) for s in lines)
        h = line_h * len(lines)
        gap = n["r"] + 4
        x, y = n["x"], n["y"]
        cands = []
        up = y <= H / 2
        vert = [("above", (x - w / 2, y - gap - h, x + w / 2, y - gap)), ("below", (x - w / 2, y + gap, x + w / 2, y + gap + h))]
        if not up:
            vert.reverse()
        side = []
        if x >= W / 2:
            side.append(("right", (x + gap, y - h / 2, x + gap + w, y + h / 2)))
        if x <= W / 2:
            side.append(("left", (x - gap - w, y - h / 2, x - gap, y + h / 2)))
        for kind, b in vert + side:
            # 세로 배치는 좌우를 캔버스 안으로 밀어 넣는다
            if kind in ("above", "below"):
                if b[0] < 4:
                    b = (4, b[1], 4 + w, b[3])
                if b[2] > W - 4:
                    b = (W - 4 - w, b[1], W - 4, b[3])
            cands.append((kind, b))
        return cands

    for i, n in enumerate(nodes):
        best = None
        for lines in n["label_options"]:
            for kind, b in boxes_for(n, lines):
                if b[0] < 2 or b[2] > W - 2 or b[1] < 2 or b[3] > H - 2:
                    cost = 1e6
                else:
                    own = obstacles[1 + i]
                    cost = sum(overlap(b, o) for j, o in enumerate(obstacles) if o is not own) + sum(overlap(b, p) for p in placed)
                    cost += 30 * sum(1 for (px, py) in line_pts if b[0] - 1 <= px <= b[2] + 1 and b[1] - 1 <= py <= b[3] + 1)
                if best is None or cost < best[0]:
                    best = (cost, kind, b, lines)
                if cost == 0:
                    break
            if best[0] == 0:
                break
        _, kind, b, lines = best
        placed.append(b)
        n["label"] = (kind, b, lines)


def source_graph(t, topics, weeks_by_id, src_num, W, H):
    cx, cy = W / 2, H / 2
    rx, ry = (W / 2 - 50, H / 2 - 40) if W < 500 else (W / 2 - 110, H / 2 - 50)
    srcs = t["sources"]
    diag_refs = {g.get("ref") for g in t.get("diagrams", []) if g.get("ref")}
    follow = t["relation"]["type"] == "follow_up"
    slots = len(srcs) + (1 if follow else 0)
    nodes = []
    for k in range(slots):
        if follow:
            ang = math.pi / 2 + 2 * math.pi * k / slots  # 0번 칸(아래 가운데)은 지난 토픽
        else:
            ang = -math.pi / 2 + 2 * math.pi * k / slots
        x = round(cx + rx * math.cos(ang), 1)
        y = round(cy + ry * math.sin(ang), 1)
        if follow and k == 0:
            pt = topics[t["relation"]["topic_id"]]
            wl = weeks_by_id[pt["week"]]["label"]
            head = plain(pt["title"])[:14].rstrip(" ,.-:/")
            nodes.append({
                "x": x, "y": y, "r": 5, "past": True, "href": f'/topic/{pt["id"]}/',
                "label_options": [[f"{wl} {head}"], [wl, head]],
            })
            continue
        s = srcs[k - 1] if follow else srcs[k]
        lab = {"text": "글", "video": "영상", "github": "레포"}[s["channel"]]
        head = s["title"][:14].rstrip(" ,.-:/")
        nodes.append({
            "x": x, "y": y, "r": 6, "src": s, "strong": s["id"] in diag_refs,
            "href": None if s.get("example") or not s.get("url") else s["url"],
            "label_options": [[f"{lab} / {head}"], [f"{lab} / {head[:7].rstrip()}", head[7:].lstrip()] if len(head) > 7 else [f"{lab} / {head}"]],
        })
    box_w, box_h = 94, 34
    center_box = (cx - box_w / 2 - 2, cy - box_h / 2 - 2, cx + box_w / 2 + 2, cy + box_h / 2 + 2)
    place_labels(nodes, W, H, center_box, [(cx, cy, n["x"], n["y"]) for n in nodes])

    lines, dots = [], []
    for n in nodes:
        if n.get("past"):
            lines.append(f'<line x1="{cx}" y1="{cy}" x2="{n["x"]}" y2="{n["y"]}" stroke="#b0b3ba" stroke-width="1.5" stroke-dasharray="4 4"/>')
        elif n["strong"]:
            lines.append(f'<line x1="{cx}" y1="{cy}" x2="{n["x"]}" y2="{n["y"]}" stroke="#2a3038" stroke-width="2.5"/>')
        else:
            lines.append(f'<line x1="{cx}" y1="{cy}" x2="{n["x"]}" y2="{n["y"]}" stroke="#d1d3d8" stroke-width="1.5"/>')
    for n in nodes:
        kind, b, lab_lines = n["label"]
        if kind == "left":
            anchor, tx = "end", b[2]
        elif kind == "right":
            anchor, tx = "start", b[0]
        else:
            anchor, tx = "middle", (b[0] + b[2]) / 2
        fill = "#868b94" if n.get("past") else "#2a3038"
        tspans = "".join(
            f'<tspan x="{round(tx, 1)}" y="{round(b[1] + 10 + 13 * i, 1)}">{esc(s)}</tspan>' for i, s in enumerate(lab_lines)
        )
        label = f'<text class="glabel" font-size="11" fill="{fill}" text-anchor="{anchor}">{tspans}</text>'
        if n.get("past"):
            circ = f'<circle cx="{n["x"]}" cy="{n["y"]}" r="5" fill="#ffffff" stroke="#868b94" stroke-width="1.5"/>'
            title = f"<title>{esc(t['relation']['label'])}</title>"
        else:
            s = n["src"]
            if s["channel"] == "github":
                circ = f'<circle cx="{n["x"]}" cy="{n["y"]}" r="6" fill="#d1d3d8" stroke="#868b94"/>'
            else:
                circ = f'<circle cx="{n["x"]}" cy="{n["y"]}" r="6" fill="{CH_FILL[s["channel"]]}"/>'
            title = f'<title>[{src_num[s["id"]]}] {esc(s["title"])}</title>'
        g = f"{title}{circ}{label}"
        if n["href"]:
            ext = "" if n.get("past") else ' target="_blank" rel="noopener"'
            dots.append(f'<a href="{esc(n["href"])}"{ext}>{g}</a>')
        else:
            dots.append(f"<g>{g}</g>")
    center = (
        f'<rect x="{cx - box_w / 2}" y="{cy - box_h / 2}" width="{box_w}" height="{box_h}" rx="8" fill="#1a1c20"/>'
        f'<text x="{cx}" y="{cy + 4}" font-size="12" fill="#ffffff" text-anchor="middle" font-weight="700">이번 토픽</text>'
    )
    return (
        f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="소스 연결도: 소스 {len(srcs)}개">'
        + "".join(lines) + center + "".join(dots) + "</svg>"
    )


# ---------------------------------------------------------------- 도식 B, C, D
def bars_diagram(g):
    items = g["items"]
    mx = max(i["value"] for i in items) or 1
    unit = g.get("unit", "")

    def val(i):
        if i.get("display"):
            return i["display"]
        sep = " " if unit and unit[0].isascii() and unit[0].isalpha() else ""
        return f"{num(i['value'])}{sep}{unit}"

    vals = [val(i) for i in items]
    lab_w = max(42, min(110, math.ceil(max(text_w(i["label"], 13) for i in items)) + 4))
    val_w = math.ceil(max(text_w(v, 13) for v in vals)) + 4
    long = val_w > 64
    rows = []
    for i, v in zip(items, vals):
        fill = "f-em" if i.get("emphasis") else "f-base"
        pct = round(i["value"] / mx * 100, 2)
        rows.append(
            f'<div class="brow">'
            f'<span class="blab" style="width: {lab_w}px">{esc(i["label"])}</span>'
            f'<span class="btrack"><span class="bfill {fill}" style="width: {num(pct)}%"></span></span>'
            f'{SEP}<span class="bval" style="width: {val_w}px">{esc(v)}</span>'
            "</div>"
        )
    cap = g.get("caption", "")
    if g.get("example") and "가상 수치" not in cap:
        cap += " (가상 수치)"
    cls = "bars long" if long else "bars"
    return f'<div class="{cls}">{"".join(rows)}</div><p class="cap">{esc(cap)}</p>'


def video_diagram(g, src):
    marks = []
    link = src.get("url") and not src.get("example")
    for m in g["marks"]:
        cls = "tl slide" if m.get("slide") else "tl"
        if link:
            sep = "&" if "?" in src["url"] else "?"
            tm = f'<a class="tm lk" href="{esc(src["url"])}{sep}t={m["sec"]}" target="_blank" rel="noopener">{esc(m["t"])}</a>'
        else:
            tm = f'<span class="tm">{esc(m["t"])}</span>'
        slide = '<span class="vh">슬라이드</span>' if m.get("slide") else ""
        marks.append(f'<li class="{cls}"><i></i>{tm}{SEP}<span class="tx">{esc(m["text"])}{slide}</span></li>')
    ex = "<span>예시 영상</span>" if src.get("example") else ""
    head = (
        f'<div class="vhead"><span class="vtitle">{esc(src["title"])}</span>{SEP}'
        f'<span class="vmeta">{esc(src.get("duration", ""))}{" / " if ex else ""}{ex}</span></div>'
    )
    cap = f'출처: {src["title"]}' + (" (가상)" if src.get("example") else "") + " / 진한 점: 슬라이드에서 읽은 장면"
    return f'{head}<ol class="timeline">{"".join(marks)}</ol><p class="cap">{esc(cap)}</p>'


def events_diagram(g, topics, src_num):
    rows = []
    cited, past = [], []
    for e in g["items"]:
        if e.get("topic_id"):
            text = f'<a class="lk" href="/topic/{esc(e["topic_id"])}/">{esc(e["text"])}</a>'
            if e["topic_id"] not in past:
                past.append(e["topic_id"])
        else:
            text = esc(e["text"])
            if e.get("ref"):
                n = src_num[e["ref"]]
                text += f' <a class="ref" href="#src-{n}">[{n}]</a>'
                if n not in cited:
                    cited.append(n)
        rows.append(f'<li class="ev"><span class="ed">{md(e["date"])}</span>{SEP}<span class="et">{text}</span></li>')
    cap = []
    if cited:
        cap.append("이 토픽의 출처 " + " ".join(f"[{n}]" for n in sorted(cited)))
    if past:
        cap.append("링크된 사건: 지난 토픽 " + ", ".join(f"'{plain(topics[p]['title'])}'" for p in past))
    return f'<ol class="events">{"".join(rows)}</ol><p class="cap">출처: {esc(" / ".join(cap))}</p>'


# ---------------------------------------------------------------- 토픽 페이지
def render_topic(d, t, topics, weeks_by_id):
    meta = d["meta"]
    latest_id = d["weeks"][0]["id"]
    w = weeks_by_id[t["week"]]
    back = f'<a class="back" href="{week_path(w, latest_id)}">{esc(w["label"])} 브리핑으로</a>'
    src_num = {s["id"]: i + 1 for i, s in enumerate(t["sources"])}
    src_by_id = {s["id"]: s for s in t["sources"]}

    rel = ""
    if t["relation"]["type"] == "follow_up":
        rel = f'<div class="rel"><a class="lk" href="/topic/{esc(t["relation"]["topic_id"])}/">{esc(t["relation"]["label"])}</a></div>'
    header = (
        '<div class="thead">'
        f'<div class="p-only">{back}</div>'
        f'<h1 class="ttitle">{esc(t["title"])}</h1>'
        '<div class="meta tmeta">'
        f'{channel_bar(t["channels"])}<span>{esc(channel_text(t["channels"], meta["channel_labels_topic"]))}</span>'
        f'{SEP}<span>{t["cross_checked"]}개 채널에서 확인</span></div>'
        f"{rel}</div>"
    )
    secs = [header]
    secs.append(f'<section class="sec"><h2 class="h">개요</h2><p class="body">{hl(t["overview"])}</p></section>')
    graph = (
        f'<div class="graph"><div class="g-m">{source_graph(t, topics, weeks_by_id, src_num, 350, 210)}</div>'
        f'<div class="g-p">{source_graph(t, topics, weeks_by_id, src_num, 680, 240)}</div></div>'
    )
    gcap = "굵은 선: 수치를 직접 준 소스" + (" / 점선: 이어지는 지난 토픽" if t["relation"]["type"] == "follow_up" else "")
    secs.append(f'<section class="sec"><h2 class="h">소스 연결</h2>{graph}<p class="cap">{gcap}</p></section>')

    pts = []
    for p in t["points"]:
        refs = "".join(f'<a class="ref" href="#src-{src_num[r]}">[{src_num[r]}]</a>' for r in p["refs"])
        chk = " " + badge("확인 필요") if p.get("check") else ""
        pts.append(f'<li class="pt"><span class="dot"></span><span>{hl(p["text"])} {refs}{chk}</span></li>')
    secs.append(f'<section class="sec"><h2 class="h">핵심 포인트</h2><ul class="points">{"".join(pts)}</ul></section>')

    for g in t.get("diagrams", []):
        if g["type"] == "bars":
            inner = bars_diagram(g)
        elif g["type"] == "video":
            inner = video_diagram(g, src_by_id[g["ref"]])
        elif g["type"] == "events":
            inner = events_diagram(g, topics, src_num)
        else:
            raise ValueError(f'unknown diagram type {g["type"]} in {t["id"]}')
        secs.append(f'<section class="sec diag-{g["type"]}"><h2 class="h">{esc(g["title"])}</h2>{inner}</section>')

    if t.get("concepts"):
        cs = "".join(f'<div class="concept"><b>{esc(c["term"])}</b><br>{esc(c["desc"])}</div>' for c in t["concepts"])
        secs.append(f'<section class="sec"><h2 class="h">핵심 개념</h2>{cs}</section>')
    if t.get("contributions"):
        cs = "".join(
            f'<li><span class="cl">{esc(meta["channel_labels_topic"][c["channel"]])}</span>{SEP}<span>{esc(c["text"])}</span></li>'
            for c in t["contributions"]
        )
        secs.append(f'<section class="sec"><h2 class="h">소스별로 더한 것</h2><ul class="contrib">{cs}</ul></section>')

    srcs = []
    for s in t["sources"]:
        n = src_num[s["id"]]
        if s.get("example") or not s.get("url"):
            title = f'<span class="stitle">{esc(s["title"])}</span>'
            sub = f'예시 영상 / {esc(s.get("duration", ""))} / 링크 없음' if s["channel"] == "video" else f'{esc(s["site"])} / 링크 없음'
        else:
            title = f'<a class="lk stitle" href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>'
            sub = f'{esc(s["site"])} / {md(s["date"])}'
        srcs.append(f'<li id="src-{n}" class="src"><span class="sn">[{n}]</span>{SEP}<span><span class="sl">{title}</span>{SEP}<span class="ss">{sub}</span></span></li>')
    sources = f'<section class="sec srcs"><h2 class="h">출처</h2><ol class="src-list">{"".join(srcs)}</ol></section>'

    topbar = (
        '<header class="tbar m-flex">'
        f"{back}{SEP}"
        '<a class="wordmark small" href="/">TrendsIT</a>'
        "</header>"
    )
    header_all = f'<div class="p-only">{site_header("briefing")}</div>{topbar}'
    body = (
        '<div class="wrap two topic">\n'
        f'<main class="col-main">{"".join(secs)}</main>\n'
        f'<aside class="col-side side-src">{sources}</aside>\n'
        "</div>"
    )
    return page(f'{plain(t["title"])} | TrendsIT', body, header_all, f'/topic/{t["id"]}/', plain(t["summary"]))


# ---------------------------------------------------------------- 관리 화면 공통
WEEKDAYS = "월화수목금토일"


def dt(ts):
    return datetime.date.fromisoformat(ts[:10])


def md_wd(ts):
    """'2026-10-05T07:00…' → '10.5 (월)'"""
    return f"{md(ts)} ({WEEKDAYS[dt(ts).weekday()]})"


def md_wd_hm(ts):
    """'10.5 (월) 07:00' — 제목, 목록 줄용"""
    return f"{md_wd(ts)} {ts[11:16]}"


def short_name(name):
    """'예시 블로그 A (로컬 LLM 실험기)' → '예시 블로그 A'"""
    return re.sub(r"\s*\([^)]*\)$", "", name)


def btn(label, primary=False):
    cls = "btn primary" if primary else "btn"
    return f'<button type="button" class="{cls}" disabled>{esc(label)}</button>'


def dis_note():
    return f'<span class="dis-note">{DISABLED_NOTE}</span>'


def attention_hl(text):
    """관리 화면 형광: 첫 ':' 앞부분, 없으면 '확인 필요' 부분."""
    if ":" in text:
        head, rest = text.split(":", 1)
        return f'<mark class="hl">{esc(head)}</mark>:{esc(rest)}'
    t = esc(text)
    return t.replace("확인 필요", '<mark class="hl">확인 필요</mark>', 1)


def crumbs(parts):
    """경로 줄. parts = [(글자, 링크 또는 None)]"""
    out = [f'<a class="u" href="{href}">{esc(label)}</a>' if href else esc(label) for label, href in parts]
    return " / ".join(out)


def mgmt_page(title, active, inner, path):
    body = f'<div class="wrap one"><main class="col-main mgmt">{inner}</main></div>'
    return page(title, body, site_header(active), path)


# ---------------------------------------------------------------- 소스 (6.3)
def render_sources(d):
    meta = d["meta"]
    w = d["weeks"][0]
    wid = w["id"]
    srcs = d["sources"]
    on = [s for s in srcs if s["enabled"]]
    total = sum(s["weeks"][wid]["collected"] for s in srcs)
    used = sum(s["weeks"][wid]["used_in_topics"] for s in srcs)
    head = (
        f'<h1 class="ptitle">소스 {len(srcs)}개</h1>'
        f'<p class="psub">켜짐 {len(on)} / 꺼짐 {len(srcs) - len(on)}. {esc(w["label"])} 수집 {total}건, 토픽에 쓰인 것 {used}건</p>'
    )

    # 확인할 것: 이번 주 실패 / 2주 연속 토픽에 안 쓰인 켜진 소스
    checks = []
    start = datetime.date.fromisoformat(w["start"])
    for s in on:
        fd = s["weeks"][wid]["failed_days"]
        if fd > 0:
            day = s["daily"][wid]
            idx = [i for i, v in enumerate(day) if v is None]
            when = ", ".join(md((start + datetime.timedelta(days=i)).isoformat()) for i in idx)
            recovered = idx and idx[-1] + 1 < len(day) and day[idx[-1] + 1] is not None
            times = f" {fd}회" if fd > 1 else ""
            tail = ", 다음 날 정상" if recovered else ""
            checks.append(f'{esc(short_name(s["name"]))}: <mark class="hl">{when} 수집 실패{times}</mark>{tail}')
    recent = [x["id"] for x in d["weeks"][:2]]
    idle = [s for s in on if len(recent) == 2 and all(s["weeks"][k]["used_in_topics"] == 0 for k in recent)]
    if idle:
        kinds = {}  # 이름에 든 종류 낱말로 센다(없으면 소스 유형 라벨), 처음 나온 순서
        for x in idle:
            k = next((w_ for w_ in ("블로그", "뉴스레터", "채널") if w_ in x["name"]), SOURCE_TYPE_LABELS.get(x["type"], x["type"]))
            kinds[k] = kinds.get(k, 0) + 1
        breakdown = ", ".join(f"{k} {n}" for k, n in kinds.items())
        title_attr = esc(", ".join(short_name(x["name"]) for x in idle))
        checks.append(f'<span title="{title_attr}">2주째 토픽에 쓰이지 않은 소스 {len(idle)}곳 ({breakdown})</span>: <mark class="hl">끄거나 키워드 필터 추가 검토</mark>')
    alert = ""
    if checks:
        alert = (
            f'<div class="alert"><div class="alert-h">확인할 것 {len(checks)}개</div>'
            + "".join(f"<p>{c}</p>" for c in checks)
            + "</div>"
        )

    days = "".join(f"<span>{c}</span>" for c in WEEKDAYS)
    groups = []
    for ch in CH_ORDER:
        rows = [s for s in srcs if s["channel"] == ch]
        if not rows:
            continue
        n = sum(s["weeks"][wid]["collected"] for s in rows)
        items = []
        for s in rows:
            wk = s["weeks"][wid]
            kind = SOURCE_TYPE_LABELS.get(s["type"], s["type"])
            if not s["enabled"]:
                items.append(
                    f'<li class="srow off"><span class="sinfo"><span class="sname">{esc(s["name"])}</span>{SEP}'
                    f'<span class="smeta">{esc(s.get("note") or "")}</span></span>{SEP}<span class="soff">꺼짐</span></li>'
                )
                continue
            m = f'{kind} / {wk["collected"]}건, 토픽에 {wk["used_in_topics"]}건'
            if wk["failed_days"]:
                m += f' / 실패 {wk["failed_days"]}회'
            bars = []
            for v in s["daily"][wid]:
                if v is None:
                    bars.append('<i class="d fail" title="실패"></i>')
                elif v == 0:
                    bars.append('<i class="d zero" title="0건"></i>')
                else:
                    h = max(4, min(22, v * 3))
                    bars.append(f'<i class="d" style="height: {h}px" title="{v}건"></i>')
            items.append(
                f'<li class="srow"><span class="sinfo"><span class="sname">{esc(s["name"])}</span>{SEP}'
                f'<span class="smeta">{esc(m)}</span></span>'
                f'<span class="days" aria-label="최근 7일 수집">{"".join(bars)}</span></li>'
            )
        groups.append(
            f'<section class="sgroup"><h2 class="sgroup-h"><span>{esc(meta["channel_labels"][ch])}</span>{SEP}'
            f'<span class="sgroup-n">{len(rows)}개 / {n}건</span></h2><ul>{"".join(items)}</ul></section>'
        )
    legend = (
        '<div class="slegend">'
        f'<span><i class="d" style="height: 12px"></i>그날 수집</span>{SEP}'
        f'<span><i class="d zero"></i>새 글 없음</span>{SEP}'
        '<span><i class="d fail small"></i>실패</span>'
        "</div>"
    )
    inner = (
        head + alert
        + f'<div class="dayhead" aria-hidden="true">{days}</div>'
        + "".join(groups) + legend
        + f'<div class="dis">{btn("소스 추가")}{SEP}{dis_note()}</div>'
    )
    return mgmt_page("소스 | TrendsIT", "sources", inner, "/sources/")


# ---------------------------------------------------------------- 키워드 (6.4)
def render_keywords(d, runs_by_id):
    kw = d["keywords"]
    items = kw["items"]
    names = {k["id"]: k["name"] for k in items}
    pending = [c for c in kw["candidates"] if c["status"] == "pending"]
    rejected = [c for c in kw["candidates"] if c["status"] == "rejected"]
    head = (
        f'<h1 class="ptitle">키워드 {len(items)}개</h1>'
        '<p class="psub">여러 표기를 한 키워드로 묶음. 다른 대상을 잘못 묶지 않는 것이 우선</p>'
    )
    cand_html = ""
    if pending:
        run = runs_by_id.get(pending[0]["run_id"])
        src = ""
        if run:
            src = f'<a class="u" href="/runs/{esc(run["week"])}/{esc(run["id"])}/">{mdhm(run["at"])} 실행에서 나옴</a>'
        rows = []
        for c in pending:
            ev = "".join(
                f'<a class="ev-link" href="{esc(e["url"])}" target="_blank" rel="noopener">근거: {esc(e["title"])}</a>'
                for e in c.get("evidence", [])
            )
            rows.append(
                '<li class="cand">'
                f'<div class="cand-a"><mark class="hl">{esc(c["alias"])}</mark></div>'
                f'<div class="cand-q">묶을 키워드: {esc(names[c["keyword_id"]])}</div>'
                f'<div class="cand-r">{esc(c["reason"])} / 제안: {esc(c["by"])}</div>'
                f"{ev}"
                f'<div class="dis">{btn("승인", True)}{SEP}{btn("거절")}{SEP}{dis_note()}</div>'
                "</li>"
            )
        cand_html = (
            f'<div class="sec-h"><h2>확인할 별칭 후보 {len(pending)}개</h2>{SEP}<span class="sec-r">{src}</span></div>'
            f'<ul class="cands">{"".join(rows)}</ul>'
        )
    rej_html = ""
    if rejected:
        last = sorted(rejected, key=lambda c: c.get("decided_at", ""))[-1]
        rej_html = f'<p class="rejline">최근 거절: {esc(last["alias"])}: {esc(last["reason"])}</p>'

    legend = (
        '<div class="klegend">'
        f'<span><i class="br solid"></i>확정</span>{SEP}'
        f'<span><i class="br dashed"></i>후보</span>{SEP}'
        '<span><i class="br dotted"></i>거절</span>'
        "</div>"
    )
    order = sorted(range(len(items)), key=lambda i: (-items[i]["mentions"][-1], i))
    trees = []
    for i in order:
        k = items[i]
        now, prev = k["mentions"][-1], k["mentions"][-2]
        delta = now - prev
        dtext = f"+{delta}" if delta > 0 else (f"{delta}" if delta < 0 else "±0")
        leaves = [f'<li><i class="br solid"></i><span class="lv">{esc(a)}</span></li>' for a in k["aliases"]]
        for c in kw["candidates"]:
            if c["keyword_id"] != k["id"]:
                continue
            if c["status"] == "pending":
                leaves.append(f'<li class="pend"><i class="br dashed"></i><span class="lv">{esc(c["alias"])}</span>{SEP}<span class="lt">후보</span></li>')
            elif c["status"] == "rejected":
                leaves.append(f'<li class="rejd"><i class="br dotted"></i><s class="lv">{esc(c["alias"])}</s>{SEP}<span class="lt">거절, 다른 대상</span></li>')
        trees.append(
            '<li class="kw">'
            f'<div class="kw-h"><h3>{esc(k["name"])}</h3>{SEP}<span>이번 주 {now}회 / 지난주 {dtext}</span></div>'
            f'<ul class="tree">{"".join(leaves)}</ul>'
            "</li>"
        )
    inner = (
        head + cand_html + rej_html
        + '<h2 class="sub-h">키워드와 별칭</h2>' + legend
        + f'<ul class="kws">{"".join(trees)}</ul>'
        + f'<div class="dis">{btn("키워드 추가")}{SEP}{dis_note()}</div>'
    )
    return mgmt_page("키워드 | TrendsIT", "keywords", inner, "/keywords/")


# ---------------------------------------------------------------- 실행 기록 3단 (6.5)
def run_path(r):
    return f'/runs/{r["week"]}/{r["id"]}/'


def run_title_short(r):
    """'10.5 주간 발행' — 경로 줄, 짧은 링크용"""
    return f'{md(r["at"])} {RUN_KIND_LABELS[r["kind"]]}'


def run_step_time(r, s):
    return f'{md(r["at"])} {s.get("t") or r["at"][11:16]}'


def render_runs_week(d, rw, rws, week_runs, weeks_by_id, path):
    wi = rws.index(rw)
    prev = rws[wi + 1] if wi + 1 < len(rws) else None
    if prev and prev["detail"]:
        right = f'<a class="u" href="/runs/{esc(prev["week"])}/">지난 주차: {esc(prev["label"])}</a>'
    else:
        right = '<a class="u" href="/runs/weeks/">주차별 목록</a>'
    weekly = next((r for r in week_runs if r["kind"] == "weekly"), None)
    model = weekly["model"] if weekly else week_runs[0]["model"]
    head = (
        f'<div class="bc"><span>{crumbs([("주차별", "/runs/weeks/"), (rw["label"], None)])}</span>{SEP}<span>{right}</span></div>'
        f'<h1 class="ptitle bc-title">{esc(rw["label"])} 실행 기록</h1>'
        f'<p class="psub">{esc(rw["range"])} / 모델 {esc(model)} / 실행 {len(week_runs)}번</p>'
    )
    att = []
    for r in week_runs:
        for si, s in enumerate(r["steps"]):
            if s.get("attention"):
                att.append(
                    f'<li><a class="att" href="{run_path(r)}#step-{si + 1}">'
                    f'<span class="att-t">{attention_hl(s["text"])}</span>{SEP}'
                    f'<span class="att-m">{run_step_time(r, s)} {esc(s["role"])} / 판단 기록 보기</span></a></li>'
                )
    att_html = f'<h2 class="sub-h">봐야 할 판단 {len(att)}개</h2><ul class="atts">{"".join(att)}</ul>' if att else ""

    rail = ""
    if weekly:
        c = weekly["counts"]
        rel = c["related"]
        rv = c["review"]
        wk = weeks_by_id.get(rw["week"])
        coll = channel_text(wk["collected"], d["meta"]["channel_labels_topic"]) if wk else ""
        steps = [
            ("수집", f'{rw["collected"]}건', f'매일 02:00 {rw["nightly"]}번' + (f", {coll}" if coll else "")),
            ("묶기와 과거 대조", f'후보 {c["candidates"]}개', f'후속 {rel["follow_up"]}, 신규 {rel["new"]}, 중복 {rel["duplicate"]}'),
            ("선별", f'{c["selected"]}개', "편집장, 소스가 많이 겹친 순서"),
            ("작성", f'초안 {c["selected"]}개', f'근거 id {c["evidence_ids"]}개'),
            ("검수", f'{rv["passed_first"]}개 바로 통과', f'반려 {rv["rejected"]}회 후 통과' if rv["rejected"] else "반려 없음"),
            ("발행", f'{c["published"]}개', md_wd_hm(weekly["at"])),
        ]
        rows = "".join(
            f'<li><div class="rl-h"><span>{name}</span>{SEP}<b>{esc(n)}</b></div><div class="rl-s">{esc(sub)}</div></li>'
            for name, n, sub in steps
        )
        rail = f'<h2 class="sub-h ruled">브리핑이 나오기까지</h2><ol class="rail">{rows}</ol>'

    runs_rows = []
    for r in week_runs:
        st = RUN_STATUS_LABELS[r["status"]]
        st_cls = "rs bad" if r["status"] != "ok" else "rs"
        t_cls = "rt weekly" if r["kind"] == "weekly" else "rt"
        runs_rows.append(
            f'<li><a class="runrow" href="{run_path(r)}">'
            f'<span><span class="{t_cls}">{md_wd_hm(r["at"])} {RUN_KIND_LABELS[r["kind"]]}</span>{SEP}'
            f'<span class="rsum">{esc(r["summary"])}</span></span>{SEP}'
            f'<span class="rright"><span class="{st_cls}">{st}</span>{SEP}<span class="rdec">판단 {r["decisions"]}개</span></span>'
            "</a></li>"
        )
    inner = (
        head + att_html + rail
        + f'<h2 class="sub-h ruled">이 주의 실행 {len(week_runs)}번</h2><ul class="runs">{"".join(runs_rows)}</ul>'
        + '<p class="foot-note">실행을 누르면 단계별 판단 기록</p>'
    )
    return mgmt_page(f'{rw["label"]} 실행 기록 | TrendsIT', "runs", inner, path)


def render_runs_weeks(d, rws):
    old_first = list(reversed(rws))
    total = sum(w["published"] for w in rws)
    rej = " / ".join(f'{w["rejected"]}회' for w in old_first)
    head = (
        f'<div class="bc"><span>{crumbs([("실행 기록", "/runs/"), ("주차별", None)])}</span></div>'
        '<h1 class="ptitle bc-title">주차별 실행 기록</h1>'
        f'<p class="psub">{len(rws)}주 발행 {total}개, 검수 반려 {rej}</p>'
    )
    mx = max(max(w["published"], w["rejected"]) for w in rws) or 1
    unit = min(8, 56 / mx)

    def h(v):
        return 2 if v == 0 else round(v * unit)

    cols = "".join(
        f'<div class="wcol"><div class="wbars">'
        f'<span class="wb pub" style="height: {h(w["published"])}px" title="발행 {w["published"]}"></span>'
        f'<span class="wb rej" style="height: {h(w["rejected"])}px" title="반려 {w["rejected"]}"></span>'
        f'</div><span class="wl">{esc(w["label"].removesuffix("차"))}</span></div>{SEP}'
        for w in old_first
    )
    chart = (
        '<div class="wchart"><div class="wchart-k">주별 발행 토픽과 검수 반려</div>'
        f'<div class="wchart-in">{cols}'
        f'<div class="wlegend"><span><span class="sq pub"></span>발행 토픽</span>{SEP}<span><span class="sq rej"></span>검수 반려</span></div>'
        "</div></div>"
    )
    rows = []
    for i, w in enumerate(rws):
        badge_html = " " + badge("승인 모드") if w["approval_mode"] else ""
        when = esc(w["range"]) + (" / 이번 주" if i == 0 else "")
        fail = f' (실패 {w["nightly_failed"]})' if w["nightly_failed"] else ""
        body = (
            f'<div class="wk-h"><h2>{esc(w["label"])}{badge_html}</h2>{SEP}<span>{when}</span></div>'
            f'<div class="wk-n"><span>수집 {w["collected"]}건</span><span class="slash">/</span><span>후보 {w["candidates"]}</span>'
            f'<span class="slash">/</span><b>발행 {w["published"]}</b></div>'
            f'<div class="wk-m">매일 수집 {w["nightly"]}회{fail} / 검수 반려 {w["rejected"]}회 / 확인 필요 {w["needs_check"]}문장</div>'
            f'<div class="wk-note">{esc(w.get("note") or "")}</div>'
        )
        if w["detail"]:
            rows.append(f'<li><a class="wk" href="/runs/{esc(w["week"])}/">{body}</a></li>')
        else:
            rows.append(f'<li><div class="wk">{body}<div class="wk-out">단계별 기록 없음 (예시 데이터 범위 밖)</div></div></li>')
    inner = (
        head + chart + f'<ul class="wks">{"".join(rows)}</ul>'
        + '<p class="foot-note">주차를 누르면 그 주 실행 기록</p>'
    )
    return mgmt_page("주차별 실행 기록 | TrendsIT", "runs", inner, "/runs/weeks/")


def render_run_detail(d, r, rw, week_runs, topics, enabled_count, latest):
    title = f'{md_wd(r["at"])} {RUN_KIND_LABELS[r["kind"]]}'
    week_href = "/runs/" + rw["week"] + "/"
    head = (
        f'<div class="bc"><span>{crumbs([("주차별", "/runs/weeks/"), (rw["label"], week_href), (run_title_short(r), None)])}</span></div>'
        f'<h1 class="ptitle bc-title dtitle">{esc(title)}</h1>'
    )
    if r["kind"] == "weekly":
        c = r["counts"]
        inp = f'{"이번 주" if latest else "이 주"} 수집 {rw["collected"]}건, 후보 토픽 {c["candidates"]}개'
        out = f'토픽 {c["published"]}개 발행, 근거 id {c["evidence_ids"]}개'
    else:
        inp = f"켜진 소스 {enabled_count}개"
        out = r["summary"]
    info = [("시작", md_wd_hm(r["at"])), ("걸린 시간", f'{r["duration_min"]}분'), ("모델", r["model"]), ("입력", inp), ("결과", out)]
    info_html = '<dl class="info">' + "".join(f"<div><dt>{k}</dt><dd>{esc(v)}</dd></div>" for k, v in info) + "</dl>"

    roles = []
    for s in r["steps"]:
        if s["role"] not in roles:
            roles.append(s["role"])
    tabs = [f'<span class="on">전체 {len(r["steps"])}</span>'] + [
        f'<span>{esc(ro)} {sum(1 for s in r["steps"] if s["role"] == ro)}</span>' for ro in roles
    ]
    tabs_html = f'<div class="rtabs">{SEP.join(tabs)}</div>'

    has_t = r["kind"] == "weekly"
    # 수집 실패(errors)는 판단 로그가 아니라 맨 위 한 줄로만 (2차 리뷰)
    errs = "".join(
        f'<p class="errline"><mark class="hl">{esc(short_name(e["source"]))} 수집 실패</mark>: {esc(e["text"])}</p>'
        for e in r.get("errors", [])
    )
    log = []
    for si, s in enumerate(r["steps"]):
        text = attention_hl(s["text"]) if s.get("attention") else esc(s["text"])
        role = esc(s["role"]) + (" / 자동" if s.get("auto") else "")
        box = ""
        det = s.get("detail")
        if det:
            src = next((x for x in topics[det["topic_id"]]["sources"] if x["id"] == det["evidence_ref"]), None)
            where = f' <span class="dim">({esc(src["site"])}, {md(src["date"])})</span>' if src else ""
            box = (
                '<div class="reject">'
                f'<div><span class="rk">초안</span>{SEP}<span>{esc(det["draft"])}</span></div>'
                f'<div><span class="rk">근거</span>{SEP}<span>"{esc(det["evidence"])}"{where}</span></div>'
                f'<div class="fixed"><span class="rk">수정</span>{SEP}<span>{esc(det["fixed"])}</span></div>'
                "</div>"
            )
        t = f'<span class="lg-t">{esc(s.get("t", ""))}</span>{SEP}' if has_t else ""
        log.append(
            f'<li class="lg-row" id="step-{si + 1}">{t}<span class="lg-b"><span class="lg-role">{role}</span>{SEP}'
            f'<span class="lg-text">{text}</span>{box}</span></li>'
        )
    links = []
    if r["kind"] == "weekly":
        links.append(f'<a class="u" href="/week/{esc(r["week"])}/">이 실행이 만든 {esc(rw["label"])} 브리핑 보기</a>')
    seq = sorted(week_runs, key=lambda x: x["at"])
    i = seq.index(r)
    if i > 0:
        links.append(f'<a class="u" href="{run_path(seq[i - 1])}">이전 실행: {md(seq[i - 1]["at"])} {seq[i - 1]["at"][11:16]} {RUN_KIND_LABELS[seq[i - 1]["kind"]]}</a>')
    if i + 1 < len(seq):
        links.append(f'<a class="u" href="{run_path(seq[i + 1])}">다음 실행: {md(seq[i + 1]["at"])} {seq[i + 1]["at"][11:16]} {RUN_KIND_LABELS[seq[i + 1]["kind"]]}</a>')
    inner = (
        head + info_html + errs + tabs_html
        + f'<ol class="log">{"".join(log)}</ol>'
        + f'<nav class="dlinks">{SEP.join(links)}</nav>'
    )
    return mgmt_page(f"{title} | TrendsIT", "runs", inner, run_path(r))


# ---------------------------------------------------------------- 실행
def build():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    topics = {t["id"]: t for t in d["topics"]}
    weeks_by_id = {w["id"]: w for w in d["weeks"]}
    OUT.mkdir(exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    shutil.copyfile(CSS_SRC, OUT / "assets" / "style.css")
    for f in sorted(STATIC.iterdir()):
        if f.is_file():
            shutil.copyfile(f, OUT / f.name)
    for wi, w in enumerate(d["weeks"]):
        write(f'week/{w["id"]}/index.html', render_week(d, wi, topics, f'/week/{w["id"]}/'))
        if wi == 0:
            write("index.html", render_week(d, wi, topics, "/"))
    for t in d["topics"]:
        write(f'topic/{t["id"]}/index.html', render_topic(d, t, topics, weeks_by_id))
    write("sources/index.html", render_sources(d))
    runs_by_id = {r["id"]: r for r in d["runs"]}
    write("keywords/index.html", render_keywords(d, runs_by_id))
    rws = d["run_weeks"]
    enabled_count = sum(1 for s in d["sources"] if s["enabled"])
    write("runs/weeks/index.html", render_runs_weeks(d, rws))
    for wi, rw in enumerate(rws):
        if not rw["detail"]:
            continue
        week_runs = [r for r in d["runs"] if r["week"] == rw["week"]]
        write(f'runs/{rw["week"]}/index.html', render_runs_week(d, rw, rws, week_runs, weeks_by_id, f'/runs/{rw["week"]}/'))
        if wi == 0:
            write("runs/index.html", render_runs_week(d, rw, rws, week_runs, weeks_by_id, "/runs/"))
        for r in week_runs:
            write(f'runs/{rw["week"]}/{r["id"]}/index.html', render_run_detail(d, r, rw, week_runs, topics, enabled_count, wi == 0))
    n = sum(1 for _ in OUT.rglob("*.html"))
    print(f"built {n} html files into {OUT}")


if __name__ == "__main__":
    build()
