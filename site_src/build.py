# TrendsIT 정적 예시 사이트 빌드. 실행: python3 site_src/build.py
# 입력: data/trendsit-example.json / 출력: site/ (지우지 않고 덮어씀). 표준 라이브러리만 쓴다.
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

FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;700&amp;display=swap">'
)

# 채널 회색 (02_DESIGN 3장)
CH_FILL = {"text": "#2a3038", "video": "#868b94", "github": "#d1d3d8"}
CH_ORDER = ["text", "video", "github"]
SOURCE_TYPE_LABELS = {"rss": "RSS", "arxiv": "arXiv", "youtube": "YouTube", "oss_insight": "OSS Insight"}
RUN_STATUS_LABELS = {"ok": "정상", "partial": "일부 실패"}
DISABLED_NOTE = "예시 사이트라 동작하지 않아요"


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
    return "".join(out)


def site_header(active):
    return (
        '<header class="top">\n'
        '  <div class="top-in">\n'
        '    <a class="wordmark" href="/">TrendsIT</a>\n'
        f'    <nav class="tabs">{tabs_html(active)}</nav>\n'
        '    <span class="ex">예시 데이터</span>\n'
        "  </div>\n"
        "</header>"
    )


def page(title, body, notice, header):
    return (
        "<!doctype html>\n"
        '<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n{FONT_LINKS}\n"
        '<link rel="stylesheet" href="/assets/style.css">\n'
        "</head>\n<body>\n"
        f"{header}\n{body}\n"
        f'<footer class="notice"><div class="notice-in">{esc(notice)}</div></footer>\n'
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
    return f'<div class="meta">{"".join(bits)}</div>'


def collect_block(w, meta, cls):
    c = w["collected"]
    legend = "".join(
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
        f'<div class="r1">{name}<span class="{stars_cls}">{esc(r["stars_7d"])}</span></div>'
        f'<div class="r2">{esc(r["what"])}</div>'
        f'<div class="r3">{" / ".join(third)}</div>'
        "</li>"
    )


def week_path(w, latest_id):
    return "/" if w["id"] == latest_id else f'/week/{w["id"]}/'


def render_week(d, wi, topics):
    meta = d["meta"]
    weeks = d["weeks"]
    w = weeks[wi]
    ts = [topics[i] for i in w["topic_ids"]]
    ts.sort(key=lambda t: t["rank"])
    lead = [t for t in ts if t.get("lead")]
    rest = [t for t in ts if not t.get("lead")]

    head = (
        '<div class="whead">'
        f'<h1 class="wtitle">{esc(w["label"])}</h1>'
        f'<div class="wsub">{esc(w["range"])} / 소스 {w["source_count"]}건에서 토픽 {w["topic_count"]}개</div>'
        f'{collect_block(w, meta, "m-only")}'
        "</div>"
    )
    lead_html = ""
    for t in lead:
        lead_html += (
            f'<a class="lead row" href="/topic/{esc(t["id"])}/">'
            '<div class="lead-k">이번 주 핵심 토픽</div>'
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
        '<section class="side-collect p-only"><h2 class="side-h">이번 주 수집</h2>'
        f'{collect_block(w, meta, "")}</section>'
        '<section class="repos"><h2 class="side-h"><span class="m-only">이번 주 </span>관심 분야 레포</h2>'
        f'<ul class="repo-list">{repo_html}</ul></section>'
        f'<nav class="weeknav">{"".join(nav)}</nav>'
        f'<div class="runat">발행 {mdhm(w["published_at"])}<span class="sep"> / </span><br class="p-br">다음 발행 {mdhm(w["next_run"])}</div>'
        "</aside>\n"
        "</div>"
    )
    title = "TrendsIT" if wi == 0 else f'{w["label"]} | TrendsIT'
    return page(title, body, meta["notice"], site_header("briefing"))


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
            f'<span class="bval" style="width: {val_w}px">{esc(v)}</span>'
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
        marks.append(f'<li class="{cls}"><i></i>{tm}<span class="tx">{esc(m["text"])}{slide}</span></li>')
    ex = "<span>예시 영상</span>" if src.get("example") else ""
    head = (
        f'<div class="vhead"><span class="vtitle">{esc(src["title"])}</span>'
        f'<span class="vmeta">{esc(src.get("duration", ""))}{" / " if ex else ""}{ex}</span></div>'
    )
    cap = f'출처: {src["title"]}' + (" (가상)" if src.get("example") else "") + ". 진한 점은 슬라이드에서 읽은 장면이에요."
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
        rows.append(f'<li class="ev"><span class="ed">{md(e["date"])}</span><span class="et">{text}</span></li>')
    cap = []
    if cited:
        cap.append("이 토픽의 출처 " + " ".join(f"[{n}]" for n in sorted(cited)))
    if past:
        cap.append("링크가 걸린 사건은 지난 토픽 " + ", ".join(f"'{plain(topics[p]['title'])}'" for p in past))
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
        f'<span>{t["cross_checked"]}개 채널에서 확인</span></div>'
        f"{rel}</div>"
    )
    secs = [header]
    secs.append(f'<section class="sec"><h2 class="h">개요</h2><p class="body">{hl(t["overview"])}</p></section>')
    graph = (
        f'<div class="graph"><div class="g-m">{source_graph(t, topics, weeks_by_id, src_num, 350, 210)}</div>'
        f'<div class="g-p">{source_graph(t, topics, weeks_by_id, src_num, 680, 240)}</div></div>'
    )
    gcap = "굵은 선은 수치를 직접 제공한 소스" + (", 점선은 이어지는 지난 토픽이에요." if t["relation"]["type"] == "follow_up" else "예요.")
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
            f'<li><span class="cl">{esc(meta["channel_labels_topic"][c["channel"]])}</span><span>{esc(c["text"])}</span></li>'
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
        srcs.append(f'<li id="src-{n}" class="src"><span class="sn">[{n}]</span><span><span class="sl">{title}</span><span class="ss">{sub}</span></span></li>')
    sources = f'<section class="sec srcs"><h2 class="h">출처</h2><ol class="src-list">{"".join(srcs)}</ol></section>'

    topbar = (
        '<header class="tbar m-flex">'
        f"{back}"
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
    return page(f'{plain(t["title"])} | TrendsIT', body, meta["notice"], header_all)


# ---------------------------------------------------------------- 읽기 전용 목록
def disabled_btn(label):
    return f'<div class="dis"><button type="button" disabled>{esc(label)}</button><span>{DISABLED_NOTE}</span></div>'


def render_sources(d):
    rows = []
    for s in d["sources"]:
        st = "켜짐" if s["enabled"] else "꺼짐"
        kind = f'{SOURCE_TYPE_LABELS.get(s["type"], s["type"])} / {d["meta"]["channel_labels"][s["channel"]]}'
        last = s.get("last")
        if last:
            info = f'마지막 수집 {mdhm(last["at"])} / {last["count"]}건'
            err = f'<div class="l3">실패: {esc(last["error"])}</div>' if last.get("error") else ""
        else:
            info, err = "아직 수집 기록 없음", ""
        rows.append(
            f'<li class="lrow"><div class="l1"><span class="ln">{esc(s["name"])}</span><span class="lst">{st}</span></div>'
            f'<div class="l2">{esc(kind)}</div><div class="l3">{esc(info)}</div>{err}</li>'
        )
    body = (
        '<div class="wrap one"><main class="col-main">'
        '<h1 class="ptitle">소스</h1>'
        f'<ul class="list">{"".join(rows)}</ul>'
        f'{disabled_btn("소스 추가")}'
        "</main></div>"
    )
    return page("소스 | TrendsIT", body, d["meta"]["notice"], site_header("sources"))


def render_keywords(d):
    kw = d["keywords"]
    rows = "".join(
        f'<li class="lrow"><div class="l1"><span class="ln">{esc(k["name"])}</span></div>'
        f'<div class="l2">{esc(", ".join(k["aliases"]))}</div></li>'
        for k in kw["items"]
    )
    cands = "".join(
        f'<li class="lrow"><div class="l1"><span class="ln">{esc(c["keyword"])} → {esc(c["alias"])}</span></div>'
        f'<div class="l3">본 횟수 {c["seen"]}번</div>{disabled_btn("승인")}</li>'
        for c in kw["candidates"]
    )
    body = (
        '<div class="wrap one"><main class="col-main">'
        '<h1 class="ptitle">키워드</h1>'
        f'<ul class="list">{rows}</ul>'
        f'{disabled_btn("키워드 추가")}'
        '<h2 class="sub-h">별칭 후보</h2>'
        f'<ul class="list">{cands}</ul>'
        "</main></div>"
    )
    return page("키워드 | TrendsIT", body, d["meta"]["notice"], site_header("keywords"))


def render_runs(d):
    rows = []
    for r in d["runs"]:
        steps = "".join(f'<li>{esc(s["role"])}: {esc(s["text"])}</li>' for s in r.get("steps", []))
        rows.append(
            f'<li class="lrow"><div class="l1"><span class="ln">{esc(r["kind"])}</span>'
            f'<span class="lst">{RUN_STATUS_LABELS.get(r["status"], r["status"])}</span></div>'
            f'<div class="l3">{mdhm(r["at"])} / {esc(r["duration"])}</div>'
            f'<div class="l2">{esc(r["summary"])}</div>'
            f'<ul class="steps">{steps}</ul></li>'
        )
    body = (
        '<div class="wrap one"><main class="col-main">'
        '<h1 class="ptitle">실행 기록</h1>'
        f'<ul class="list">{"".join(rows)}</ul>'
        "</main></div>"
    )
    return page("실행 기록 | TrendsIT", body, d["meta"]["notice"], site_header("runs"))


# ---------------------------------------------------------------- 실행
def build():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    topics = {t["id"]: t for t in d["topics"]}
    weeks_by_id = {w["id"]: w for w in d["weeks"]}
    OUT.mkdir(exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    shutil.copyfile(CSS_SRC, OUT / "assets" / "style.css")
    for wi, w in enumerate(d["weeks"]):
        html_ = render_week(d, wi, topics)
        write(f'week/{w["id"]}/index.html', html_)
        if wi == 0:
            write("index.html", html_)
    for t in d["topics"]:
        write(f'topic/{t["id"]}/index.html', render_topic(d, t, topics, weeks_by_id))
    write("sources/index.html", render_sources(d))
    write("keywords/index.html", render_keywords(d))
    write("runs/index.html", render_runs(d))
    n = sum(1 for _ in OUT.rglob("*.html"))
    print(f"built {n} html files into {OUT}")


if __name__ == "__main__":
    build()
