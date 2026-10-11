# TrendsIT 사이트 빌드(S6a). 실행: python3 site_src/build.py [--data data/site.json] [--out site]
# 입력: trendsit export가 만든 data/site.json / 출력: site/ 전체를 임시 폴더에 만든 뒤 한 번에 교체(실패하면 이전 사이트 그대로).
# 디자인 시스템 v1(docs/reference/s6_design/DESIGN.md)의 마크업. 표준 라이브러리만, 사이트에 JS 없음.
import argparse
import hashlib
import html
import json
import math
import os
import pathlib
import re
import shutil
import sys
import tempfile
from types import SimpleNamespace

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parent
SITE_URL = "https://trendsit.jiseop.com"
DEFAULT_DESC = "로컬 AI가 매주 정리하는 개인 기술 브리핑"
CH_ORDER = ["text", "video", "github"]
KIND_LABELS = {"weekly": "주간 브리핑", "nightly": "매일 수집"}
STATUS_LABELS = {"ok": "정상", "partial": "일부 실패", "failed": "실패", "skipped": "건너뜀", "stopped": "중단", "running": "실행 중"}
STATUS_ALERT = {"partial", "failed", "stopped"}
TABS = [("briefing", "/", "브리핑"), ("sources", "/sources/", "소스"), ("keywords", "/keywords/", "키워드"), ("runs", "/runs/", "실행 기록")]
CHK_CSS = ".chk{font-size:var(--fs-xs);color:var(--c-muted);margin-left:var(--sp-1);white-space:nowrap}\n"  # 확인 필요 표기(D-9, DESIGN 7장)
FONT_CSS = "".join(
    f'@font-face{{font-family:"Pretendard";font-weight:{w};font-display:swap;src:url("fonts/Pretendard-{n}.woff2") format("woff2")}}\n'
    for w, n in ((400, "Regular"), (500, "Medium")))
C = SimpleNamespace()  # 한 번의 빌드 동안 쓰는 색인(load가 채움)


class BuildError(Exception):
    pass


# ---------------------------------------------------------------- 문자열 도우미(한국어 조판: DESIGN 3장)
def esc(s):
    """이스케이프. 원문에 이미 엔티티(&#x27; 등)로 들어 있는 글자는 풀어서 한 번만 이스케이프(그대로 화면에 찍히지 않게)."""
    return html.escape(html.unescape(str(s)), quote=True)


TOKEN_RE = re.compile(r"([A-Za-z0-9][A-Za-z0-9.%$+\-_/:,~]*[A-Za-z0-9%)]|[A-Za-z0-9]{2,})")


def nb_tokens(s):
    """숫자·영문 토큰(20자 이하)을 줄에서 쪼개지지 않게 묶는다. 이미 이스케이프된 문자열에 적용, 태그 안은 건드리지 않음."""
    def rep(m):
        t = m.group(0)
        return t if len(t) > 20 or "&" in t else f'<span class="nb">{t}</span>'
    return "".join(p if p.startswith("<") else TOKEN_RE.sub(rep, p) for p in re.split(r"(<[^>]+>)", s))


def rich(s):
    """==형광== → mark, 숫자·영문 토큰 묶기, `코드` → code.ic."""
    out = nb_tokens(re.sub(r"==(.+?)==", r'<mark class="hl">\1</mark>', esc(s)))
    return re.sub(r"`([^`]+)`", lambda m: '<code class="ic">' + re.sub(r"</?span[^>]*>", "", m.group(1)) + "</code>", out)


def plain(s):
    return str(s).replace("==", "").replace("`", "")


def md(date_str):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str or "")
    return f"{int(m[2])}.{int(m[3])}" if m else (date_str or "")


def mdhm(ts):
    m = re.match(r"\d{4}-(\d{2})-(\d{2})T(\d{2}:\d{2})", ts or "")
    return f"{int(m[1])}.{int(m[2])} {m[3]}" if m else (ts or "")


SEP = ' <span class="sep">/</span> '
CHK = '<span class="chk">확인 필요</span>'


def meta_line(parts):
    return SEP.join(parts)


# ---------------------------------------------------------------- 데이터 색인
def load(d):
    for k in ("meta", "weeks", "topics", "repos", "sources", "keywords", "runs", "run_weeks"):
        if k not in d:
            raise BuildError(f"site.json에 {k} 칸이 없음")
    if not d["weeks"]:
        raise BuildError("site.json에 주가 없음")
    C.d = d
    C.topics = {t["id"]: t for t in d["topics"]}
    C.weeks = {w["id"]: w for w in d["weeks"]}
    C.chl = d["meta"]["channel_labels_topic"]
    C.signals = d["meta"]["signal_labels"]
    C.rws = {r["week"]: r for r in d["run_weeks"]}
    C.runs = {r["id"]: r for r in d["runs"]}
    C.latest = d["weeks"][0]


def src_order(t):
    """토픽 안 출처의 화면 번호: 채널 순서(글 → 영상 → 레포), 채널 안 id 순. {id: n}."""
    def key(s):
        m = re.search(r"\d+$", s["id"])
        return (CH_ORDER.index(s["channel"]), int(m[0]) if m else 0, s["id"])
    return {s["id"]: i + 1 for i, s in enumerate(sorted(t["sources"], key=key))}


def channel_counts(t):
    n = {c: 0 for c in CH_ORDER}
    for s in t["sources"]:
        n[s["channel"]] += 1
    return n


def shown_checks(t):
    """화면에 표시할 확인 필요 위치(포인트 밖): overview, summary, concepts[i]. '빠진 도식: …' 등은 표시 안 함."""
    return [c for c in t.get("checks", []) if c in ("overview", "summary") or re.fullmatch(r"concepts\[\d+\]", c)]


# ---------------------------------------------------------------- 페이지 틀
def header(active):
    links = "".join(f'<a href="{h}"{" aria-current=\"page\"" if k == active else ""}>{lb}</a>' for k, h, lb in TABS)
    return f'<header class="wrap top"><nav class="nav" aria-label="주 메뉴"><a class="wordmark" href="/">TrendsIT</a>{links}</nav></header>'


def page(title, body, active, path, desc=DEFAULT_DESC):
    return (
        '<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n"
        '<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png"><meta name="theme-color" content="#ffffff">\n'
        f'<meta name="description" content="{esc(desc)}">\n'
        '<meta property="og:type" content="website"><meta property="og:site_name" content="TrendsIT">\n'
        f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">\n'
        f'<meta property="og:url" content="{SITE_URL}{esc(path)}"><meta property="og:image" content="{SITE_URL}/og-image.png">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        f'<link rel="stylesheet" href="/assets/{C.css_name}">\n'
        f"</head><body>{header(active)}{body}</body></html>\n")


def write(rel, content):
    path = C.out / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def week_path(w):
    return f'/week/{w["id"]}/'


def topic_path(t):
    return f'/topic/{t["id"]}/'


# ---------------------------------------------------------------- 인용, 도식
def cite(t, sid, ctr):
    """인용 번호 + 툴팁(마우스·앵커 위치 지원에서만 보임). 번호를 누르면 출처 목록 항목(#src-id)."""
    s, n, k = C.srcs[sid], C.nums[sid], next(ctr)
    meta = " / ".join(x for x in (C.chl[s["channel"]], s.get("site"), md(s.get("date"))) if x)
    go = f'<a class="tip-go" href="{esc(s["url"])}" rel="noopener">원문 열기</a>' if s.get("url") else ""
    return (f'<span class="cite" id="c-{k}"><a class="ref" href="#src-{esc(sid)}" aria-label="출처 {n}" aria-describedby="tip-{k}">[{n}]</a>'
            f'<span class="tip" id="tip-{k}" role="tooltip"><span class="tip-m">{esc(meta)}</span><span class="tip-t">{esc(s.get("title") or "")}</span>'
            f'<span class="tip-a">{go}<a class="tip-l" href="#src-{esc(sid)}">출처 목록 [{n}]</a></span></span></span>')


def cites(t, refs, ctr):
    return "".join(cite(t, r, ctr) for r in refs if r in C.srcs)


def with_end(raw, tail):
    """원문 끝 어절 + &nbsp; + tail(인용 등)을 nb-end로 묶어 번호만 다음 줄로 넘어가지 않게. 마지막 어절이 한 음절이면 앞 어절까지.
    어절은 rich 변환 전의 원문에서 고른다(변환 뒤 HTML에서 고르면 <span class=...> 속을 잘라 마크업이 깨짐).
    ==형광==·`코드` 안의 공백은 끊는 자리가 아니고, 끝 덩어리가 24자를 넘으면 묶지 않고 인용만 붙인다."""
    raw = raw.strip()
    spans = [m.span() for m in re.finditer(r"==.+?==|`[^`]+`", raw)]
    cuts = [m.end() for m in re.finditer(r"\s+", raw) if not any(a < m.start() < b for a, b in spans)]
    start = cuts[-1] if cuts else 0
    if re.fullmatch(r"[가-힣][.,]?", raw[start:]):
        start = cuts[-2] if len(cuts) > 1 else 0
    if len(raw) - start > 24:
        return f'{rich(raw)}<span class="nb-end">&nbsp;{tail}</span>'
    return f'{rich(raw[:start])}<span class="nb-end">{rich(raw[start:])}&nbsp;{tail}</span>'


def point_html(t, p, ctr):
    return with_end(p["text"], cites(t, p["refs"], ctr) + (CHK if p.get("check") else ""))


def bar_value(it, unit):
    v = it["value"]
    if isinstance(v, (int, float)):
        return f"{v:g}{unit}"
    return f"{v}{unit}" if unit and re.fullmatch(r"[\d.,]+", v.strip()) else str(v)


def bars_html(t, g, ctr):
    nums = [float(m[0].replace(",", "")) if (m := re.search(r"\d[\d,]*\.?\d*", str(it["value"]))) else 0.0 for it in g["items"]]
    mx = max(nums, default=0) or 1
    rows = "".join(
        f'<div class="bar-row{" em" if it.get("emphasis") else ""}{" base" if it.get("baseline") else ""}"><span class="bar-l">{esc(it["label"])}</span>'
        f'<span class="bar-v">{esc(bar_value(it, g.get("unit") or ""))}</span><span class="bar-track"><span class="bar-fill" style="width:{max(2, round(n / mx * 100))}%"></span></span></div>'
        for it, n in zip(g["items"], nums))
    src = ""
    if g.get("ref") in C.srcs:
        src = f'<p class="dg-s">{esc(g["caption"]) if g.get("caption") else "출처"} {cite(t, g["ref"], ctr)}</p>'
    return f'<figure class="dg dg-bars"><figcaption class="dg-t">{esc(g["title"])}</figcaption>{ctx_p(g)}<div class="bars">{rows}</div>{src}</figure>'


def ctx_p(g):
    return f'<p class="dg-c">{rich(g["context"])}</p>' if g.get("context") else ""


def events_html(t, g, ctr):
    rows = ""
    for it in g["items"]:
        tail = ""
        if it.get("ref") in C.srcs:
            tail = " " + cite(t, it["ref"], ctr)
        elif it.get("topic_id"):
            tail = ' <span class="ev-prev">지난 토픽</span>'
        rows += f'<li><span class="ev-d">{md(it["date"])}</span><span class="ev-t">{rich(it["text"])}{tail}</span></li>'
    return (f'<figure class="dg dg-events"><figcaption class="dg-t">{esc(g["title"])}</figcaption>{ctx_p(g)}<ol class="events">{rows}</ol>'
            '<p class="dg-s">출처는 항목마다 번호로, 날짜는 각 출처 기준</p></figure>')


def video_html(g):
    rows = "".join(f'<li class="{"slide" if m.get("slide") else ""}"><span class="vt-t">{esc(m["t"])}</span>'
                   f'<span class="vt-x">{rich(m["text"])}{" (슬라이드)" if m.get("slide") else ""}</span></li>' for m in g["marks"])
    return f'<figure class="dg dg-video"><figcaption class="dg-t">{esc(g["title"])}</figcaption><ol class="vtl" aria-label="영상 타임라인">{rows}</ol></figure>'


def diagram_slots(t):
    """도식의 자리(포인트 번호 1부터). numbers·events는 anchor, 영상 타임라인은 그 영상을 처음 인용한 포인트(없으면 마지막). 같은 자리는 수치 → 사건 → 타임라인."""
    n = len(t["points"])
    slots = {}
    for g in t.get("diagrams", []):
        if g["type"] == "video":
            at = next((i + 1 for i, p in enumerate(t["points"]) if g["ref"] in p["refs"]), n)
            order = 2
        else:
            at, order = min(max(g.get("anchor", n), 1), n), 0 if g["type"] == "bars" else 1
        slots.setdefault(at, []).append((order, g))
    return {k: [g for _, g in sorted(v, key=lambda x: x[0])] for k, v in slots.items()}


# ---------------------------------------------------------------- 토픽
def follow_html(t):
    r = t.get("relation", {})
    prev = C.topics.get(r.get("topic_id")) if r.get("type") == "follow_up" else None
    if not prev:
        return ""
    wk = C.weeks[prev["week"]]["label"]
    return f'<p class="follow">지난 흐름 <a href="{topic_path(prev)}">{esc(wk)} ‘{esc(prev["title"])}’</a></p>'


def topic_meta(t):
    n = channel_counts(t)
    parts = [f'<span class="chs">{" / ".join(f"{C.chl[c]} {n[c]}" for c in CH_ORDER if n[c])}</span>']
    if t.get("relation", {}).get("type") == "follow_up":
        parts.append('<span class="fu">후속</span>')
    if t.get("has_check"):
        parts.append('<span class="fu">확인 필요</span>')
    return f'<p class="tmeta meta">{meta_line(parts)}</p>'


def source_list(t):
    out = ""
    for ch in CH_ORDER:
        ss = sorted((s for s in t["sources"] if s["channel"] == ch), key=lambda s: C.nums[s["id"]])
        if not ss:
            continue
        items = ""
        for s in ss:
            title = esc(s.get("title") or s["id"])
            link = f'<a href="{esc(s["url"])}">{title}</a>' if s.get("url") else title
            meta = " / ".join(x for x in (s.get("site"), md(s.get("date"))) if x)
            origin = ""
            if s.get("origin"):
                shown = re.sub(r"^https?://", "", s["origin"])
                origin = f'<p class="meta">원본 <a href="{esc(s["origin"])}">{esc(shown[:70])}</a></p>'
            items += (f'<li id="src-{esc(s["id"])}" class="src"><span class="src-n">[{C.nums[s["id"]]}]</span>'
                      f'<div><p class="src-t">{link}</p><p class="meta">{esc(meta)}</p>{origin}</div></li>')
        out += f'<h3 class="src-g">{C.chl[ch]} {len(ss)}</h3><ol class="srcs">{items}</ol>'
    return f'<section class="sec sources" aria-labelledby="h-src"><h2 class="sec-t" id="h-src">출처</h2>{out}</section>'


def render_topic(t):
    C.srcs = {s["id"]: s for s in t["sources"]}
    C.nums = src_order(t)
    ctr = iter(range(1, 10**6))
    w = C.weeks[t["week"]]
    checks = shown_checks(t)
    mark = lambda loc: CHK if loc in checks else ""  # noqa: E731
    slots = diagram_slots(t)
    pts = ""
    for i, p in enumerate(t["points"], 1):
        figs = "".join(bars_html(t, g, ctr) if g["type"] == "bars" else events_html(t, g, ctr) if g["type"] == "events" else video_html(g)
                       for g in slots.get(i, []))
        pts += f'<li id="pt-{i}" class="pt"><p class="pt-x">{point_html(t, p, ctr)}</p>{figs}</li>'
    cc = "".join(f'<dt>{esc(c["term"])}</dt><dd>{rich(c["desc"])}{mark(f"concepts[{i}]")}</dd>' for i, c in enumerate(t.get("concepts", [])))
    cb = "".join(f'<dt>{esc(C.chl.get(c["channel"], c["channel"]))}</dt><dd>{rich(c["text"])}</dd>' for c in t.get("contributions", []))
    sec = lambda cls, hid, title, inner: f'<section class="sec {cls}" aria-labelledby="{hid}"><h2 class="sec-t" id="{hid}">{title}</h2>{inner}</section>'  # noqa: E731
    pn = ""
    ids = w["topic_ids"]
    i = ids.index(t["id"])
    if len(ids) > 1:
        link = lambda tid, cls, k: (f'<a class="{cls}" href="{topic_path(C.topics[tid])}"><span class="pn-k">{k}</span>'  # noqa: E731
                                    f'<span class="pn-t">{esc(C.topics[tid]["title"])}</span></a>')
        pn = ('<nav class="pn" aria-label="같은 주 토픽">' + (link(ids[i - 1], "pn-prev", "이전 토픽") if i else "<span></span>")
              + (link(ids[i + 1], "pn-next", "다음 토픽") if i + 1 < len(ids) else "") + "</nav>")
    body = (
        f'<main class="wrap topic"><article><div class="mini" aria-hidden="true"><span class="mini-t">{esc(t["title"])}</span>'
        f'<a class="mini-s" href="#h-src" tabindex="-1">출처 {len(t["sources"])}</a></div>'
        f'<p class="back meta"><a href="{week_path(w)}">{esc(w["label"])} 브리핑</a></p>'
        f'<h1 class="tt ttl">{esc(t["title"])}</h1><p class="ts">{rich(t["summary"])}{mark("summary")}</p>{topic_meta(t)}{follow_html(t)}'
        + sec("sec-ov", "h-ov", "개요", f'<p class="ov">{rich(t["overview"])}{mark("overview")}</p>')
        + sec("sec-pt", "h-pt", "핵심 포인트", f'<ol class="pts">{pts}</ol>')
        + (sec("sec-cc", "h-cc", "핵심 개념", f'<dl class="cc">{cc}</dl>') if cc else "")
        + (sec("sec-cb", "h-cb", "소스별로 더한 것", f'<dl class="cb">{cb}</dl>') if cb else "")
        + source_list(t) + pn + "</article></main>")
    return page(f'{plain(t["title"])} - TrendsIT', body, "briefing", topic_path(t), plain(t["summary"])[:120])


# ---------------------------------------------------------------- 홈·주차
def read_minutes(w):
    chars = 0
    for tid in w["topic_ids"]:
        t = C.topics[tid]
        chars += sum(len(re.sub(r"\s", "", plain(x))) for x in (t["title"], t["summary"], t["overview"], *(p["text"] for p in t["points"])))
    return max(1, math.ceil(chars / 500))


def repo_html(r):
    name = esc(r["name"])
    name = f'<a href="{esc(r["url"])}">{name}</a>' if r.get("url") else name
    stars = f'<span class="rp-s"><span class="rp-sl">이번 주 별</span> <span class="rp-sv">{esc(r["stars_7d"])}</span></span>' if r.get("stars_7d") else ""
    sig = ""
    if r.get("signal"):
        label = esc(C.signals.get(r["signal"], r["signal"]))
        sig = f'<p class="rp-m meta"><span class="{"check" if r["signal"] == "needs_check" else "sig"}">{label}</span></p>'
    rel = C.topics.get(r.get("topic_id"))
    rel = f'<p class="rp-rel meta">관련 토픽 <a href="{topic_path(rel)}">{esc(rel["title"])}</a></p>' if rel else ""
    what = f'<p class="rp-w">{esc(r["what"])}</p>' if r.get("what") else ""
    return f'<li class="rp"><p class="rp-h"><span class="rp-n">{name}</span>{stars}</p>{what}{sig}{rel}</li>'


def render_week(w, path):
    ts = [C.topics[i] for i in w["topic_ids"]]
    repos = [r for r in C.d["repos"] if r["week"] == w["id"]]
    ws = list(C.d["weeks"])
    prev = ws[ws.index(w) + 1] if ws.index(w) + 1 < len(ws) else None
    prev_link = f'<a href="{week_path(prev)}">지난 주차: {esc(prev["label"])}</a>' if prev else ""
    items = "".join(f'<li class="it"><h3 class="it-t ttl"><a href="{topic_path(t)}">{esc(t["title"])}</a></h3><p class="it-s">{rich(t["summary"])}</p>{topic_meta(t)}</li>' for t in ts)
    if repos:
        note = "주간 기록이 없어 월간 목록으로 대신한다" if w.get("trending_approx") else "이번 주 별이 많이 늘어난 레포. 토픽 근거로 쓰인 레포도 함께 보임"
        repo_body = f'<p class="sec-d meta">{note}</p><ol class="rp-list">{"".join(repo_html(r) for r in repos)}</ol>'
    else:
        repo_body = '<p class="sec-d meta">이 주는 트렌딩 기록이 없다</p>'
    body = (
        f'<main class="wrap home has-tabs"><section class="whead"><h1 class="wtitle">{esc(w["label"])}</h1>'
        f'<p class="meta">{meta_line([esc(w["range"]), f"토픽 {w["topic_count"]}", f"소스 {w["source_count"]}", f"약 {read_minutes(w)}분"])}</p>'
        + (f'<p class="meta">{prev_link.replace("<a ", "<a class=\"prev\" ")}</p>' if prev else "")
        + f'</section><nav class="tabs" aria-label="이번 주 섹션"><a class="tb-t" href="#topics">주요 토픽 {len(ts)}</a><a class="tb-r" href="#repos">트렌딩 레포 {len(repos)}</a></nav>'
        f'<div class="panels"><section class="panel" id="topics" aria-labelledby="topics-t"><h2 class="sec-t" id="topics-t">주요 토픽 <span class="cnt">{len(ts)}</span></h2><ol class="list">{items}</ol></section>'
        f'<section class="panel" id="repos" aria-labelledby="repos-t"><h2 class="sec-t" id="repos-t">트렌딩 레포 <span class="cnt">{len(repos)}</span></h2>{repo_body}</section></div>'
        f'<footer class="foot meta">{prev_link}<p>발행 {mdhm(w["published_at"])}</p></footer></main>')
    return page(f'TrendsIT {w["label"]}', body, "briefing", path, f'{w["label"]} 기술 동향 브리핑, 토픽 {len(ts)}개')


# ---------------------------------------------------------------- 관리 화면(조작 요소 없음)
def ops_page(title, active, path, meta, inner):
    return page(f"{title} - TrendsIT", f'<main class="wrap ops"><div class="ph"><h1>{esc(title)}</h1><p class="meta">{meta}</p></div>{inner}</main>', active, path)


def table(heads, rows, nums=()):
    """heads: 열 이름, rows: 셀 HTML 목록의 목록(첫 칸은 행 머리). nums: 오른쪽 정렬할 열 번호."""
    th = "".join(f'<th scope="col"{" class=\"num\"" if i in nums else ""}>{h}</th>' for i, h in enumerate(heads))
    tr = "".join(f'<tr><th scope="row">{r[0]}</th>' + "".join(f'<td{" class=\"num\"" if i in nums else ""}>{c}</td>' for i, c in enumerate(r[1:], 1)) + "</tr>" for r in rows)
    return f'<div class="dtable-wrap"><table class="dtable"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def state(label, alert=False):
    return f'<span class="state {"check" if alert else "quiet"}">{esc(label)}</span>'


def render_sources():
    wid = C.latest["id"]
    rows, bad = [], 0
    for s in sorted(C.d["sources"], key=lambda s: (CH_ORDER.index(s["channel"]), s["name"])):
        last, wk = s.get("last"), s["weeks"].get(wid, {})
        if not s["enabled"]:
            st = state("꺼짐")
        elif last and last["status"] != "ok":
            st, bad = state(STATUS_LABELS.get(last["status"], last["status"]), True), bad + 1
        else:
            st = state("정상")
        name = f'<a href="{esc(s["url"])}">{esc(s["name"])}</a>' if s.get("url") else esc(s["name"])
        lastc = "-" if not last else f'{mdhm(last["at"])}, 새 항목 {last["count"]}건'
        if s.get("last_error"):
            lastc += f'<br><span class="dim">{esc(s["last_error"])}</span>'
        rows.append([name, C.d["meta"]["channel_labels"][s["channel"]], st, wk.get("collected", 0), wk.get("used_in_topics", 0), lastc])
    todo = f'<p class="todo"><b>확인할 것</b> 마지막 수집이 정상이 아닌 소스 {bad}개</p>'
    n_on = sum(s["enabled"] for s in C.d["sources"])
    return ops_page("소스", "sources", "/sources/", f'켜진 소스 {n_on} {SEP} 전체 {len(C.d["sources"])} {SEP} 수집 수는 {esc(C.latest["label"])} 기준',
                    todo + table(["이름", "채널", "상태", "이번 주 수집", "토픽에 쓰인 수", "마지막 수집"], rows, nums=(3, 4)))


def render_keywords():
    kw = C.d["keywords"]
    rows = []
    for k in kw["items"]:
        links = ", ".join(f'<a href="{topic_path(C.topics[i])}">{esc(C.topics[i]["title"])}</a>' for i in k["topics"] if i in C.topics) or "-"
        rows.append([esc(k["name"]), esc(", ".join(k["aliases"])) or "-", SEP.join(str(m) for m in k["mentions"]), links])
    first, last = C.weeks.get(kw["weeks"][0]), C.weeks.get(kw["weeks"][-1])
    span = f'{esc(first["label"])}부터 {esc(last["label"])}까지, 왼쪽이 오래된 주' if first and last else "최근 주차 순"
    return ops_page("키워드", "keywords", "/keywords/", f'관심 키워드 {len(rows)}개 {SEP} 언급 수는 {span}',
                    table(["이름", "별칭", "최근 4주 언급 수", "관련 토픽"], rows, nums=(2,)))


def run_path(r):
    return f'/runs/{r["week"]}/{r["id"]}/'


def minutes_text(m):
    return "-" if m is None else f"{round(m)}분" if m >= 1 else f"{round(m * 60)}초"


def render_runs_weeks():
    rows = []
    for rw in C.d["run_weeks"]:
        night = f'{rw["nightly"]}회' + (f', 실패 {rw["nightly_failed"]}' if rw["nightly_failed"] else "") if rw["nightly"] else "기록 없음"
        cell = lambda k: str(rw[k]) if rw.get(k) is not None else "-"  # noqa: E731
        rows.append([f'<a href="/runs/{rw["week"]}/">{esc(rw["label"])}</a> <span class="dim">{esc(rw["range"])}</span>', night,
                     cell("collected"), cell("candidates"), cell("published"), cell("rejected"), cell("needs_check")])
    return ops_page("실행 기록", "runs", "/runs/weeks/", '주차별. 주차를 누르면 그 주의 실행 목록',
                    table(["주차", "매일 수집", "수집", "후보", "발행", "반려", "확인 필요"], rows, nums=(2, 3, 4, 5, 6)))


def render_runs_week(rw, path):
    runs = sorted((r for r in C.d["runs"] if r.get("week") == rw["week"]), key=lambda r: r["at"], reverse=True)
    rows = [[f'<a href="{run_path(r)}">{mdhm(r["at"])}</a>', KIND_LABELS.get(r["kind"], r["kind"]),
             state(STATUS_LABELS.get(r["status"], r["status"]), r["status"] in STATUS_ALERT), minutes_text(r["duration_min"]), esc(r["summary"])]
            for r in runs]
    n_alert = sum(r["status"] in STATUS_ALERT for r in runs)
    inner = f'<p class="todo"><b>확인할 것</b> 일부 실패·실패한 실행 {n_alert}건</p>'
    if not rw["nightly"]:
        inner += '<p class="meta">매일 실행 기록 없음(손으로 실행)</p>'
    inner += table(["시각", "종류", "상태", "걸린 시간", "요약"], rows)
    return ops_page(f'실행 기록 {rw["label"]}', "runs", path, f'{esc(rw["range"])} {SEP} <a href="/runs/weeks/">주차별 보기</a>', inner)


def render_run(r):
    rw = C.rws[r["week"]]
    kind = KIND_LABELS.get(r["kind"], r["kind"])
    cost = r.get("cost_usd")
    kv = [("시작", mdhm(r["at"])), ("걸린 시간", minutes_text(r["duration_min"])), ("상태", STATUS_LABELS.get(r["status"], r["status"])),
          ("비용", f"${cost:.4f}" if cost and cost < 0.1 else f"${cost or 0:.2f}"), ("요약", r["summary"])]
    inner = '<dl class="kv">' + "".join(f"<dt>{k}</dt><dd>{esc(v)}</dd>" for k, v in kv) + "</dl>"
    c = r.get("counts") or {}
    rev = c.get("review") or {}
    cells = [("후보", c.get("candidates")), ("선정", c.get("selected")), ("근거", c.get("evidence_ids")), ("1차 통과", rev.get("passed_first")),
             ("반려", rev.get("rejected")), ("발행", c.get("published"))]
    cells = [(k, v) for k, v in cells if v is not None]
    if cells:
        inner += '<ul class="rail">' + "".join(f'<li><span class="k">{k}</span><span class="v">{v}</span></li>' for k, v in cells) + "</ul>"
    if c.get("related"):
        rel = c["related"]
        inner += f'<p class="meta">과거 대조: 후속 {rel["follow_up"]} {SEP} 신규 {rel["new"]} {SEP} 중복 {rel["duplicate"]}</p>'
    if r.get("steps"):
        has_t = any(s.get("t") for s in r["steps"])
        rows = [([esc(s.get("t") or "-")] if has_t else []) + [esc(s.get("role") or ""), esc(s["text"]), '<span class="check">확인 필요</span>' if s.get("attention") else ""]
                for s in r["steps"]]
        heads = (["시각"] if has_t else []) + ["역할", "내용", "확인"]
        inner += "<h2>단계 기록</h2>" + table(heads, [[x for x in row] for row in rows])
    for s in r.get("steps") or []:
        d = s.get("detail")
        if d:
            inner += (f'<h2>반려 비교</h2><div class="cmp"><div><h3>초안</h3><p>{esc(d["draft"])}</p></div><div><h3>근거</h3><p>{esc(d["evidence"])}</p></div>'
                      + (f'<div><h3>수정</h3><p>{esc(d["fixed"])}</p></div>' if d.get("fixed") else "") + "</div>")
    return ops_page(f'{kind} {mdhm(r["at"])}', "runs", run_path(r), f'<a href="/runs/{rw["week"]}/">{esc(rw["label"])} 실행 목록</a>', inner)


# ---------------------------------------------------------------- 빌드
def build_into(out):
    C.out = out
    css = FONT_CSS + (SRC / "tokens.css").read_text(encoding="utf-8") + (SRC / "trendsit.css").read_text(encoding="utf-8") + CHK_CSS
    C.css_name = f"trendsit.{hashlib.sha256(css.encode()).hexdigest()[:10]}.css"
    write(f"assets/{C.css_name}", css)
    static = SRC / "static"
    for f in sorted(static.iterdir()):
        if f.is_file():
            shutil.copyfile(f, out / f.name)
    shutil.copytree(static / "fonts", out / "assets" / "fonts")
    for i, w in enumerate(C.d["weeks"]):
        write(f'week/{w["id"]}/index.html', render_week(w, week_path(w)))
        if i == 0:
            write("index.html", render_week(w, "/"))
    for t in C.d["topics"]:
        write(f'topic/{t["id"]}/index.html', render_topic(t))
    write("sources/index.html", render_sources())
    write("keywords/index.html", render_keywords())
    write("runs/weeks/index.html", render_runs_weeks())
    for i, rw in enumerate(C.d["run_weeks"]):
        write(f'runs/{rw["week"]}/index.html', render_runs_week(rw, f'/runs/{rw["week"]}/'))
        if i == 0:
            write("runs/index.html", render_runs_week(rw, "/runs/"))
    for r in C.d["runs"]:
        if r.get("week") in C.rws:
            write(f'runs/{r["week"]}/{r["id"]}/index.html', render_run(r))


def build(data_path, out_path):
    """site.json → out_path. 임시 폴더에 다 만든 뒤 교체한다(C-10): 실패하면 out_path는 그대로."""
    try:
        d = json.loads(pathlib.Path(data_path).read_text(encoding="utf-8"))
        load(d)
    except (OSError, ValueError, BuildError) as e:
        raise BuildError(f"site.json을 읽을 수 없음({data_path}): {e}") from e
    out = pathlib.Path(out_path).resolve()  # 실행 폴더에서는 site가 작업 폴더로 가는 링크
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=out.name + ".tmp-", dir=out.parent))
    try:
        build_into(tmp)
        os.chmod(tmp, 0o755)
        old = out.with_name(out.name + ".old")
        shutil.rmtree(old, ignore_errors=True)
        had = out.exists()
        if had:
            out.rename(old)
        try:
            tmp.rename(out)
        except BaseException:
            if had:
                old.rename(out)  # 두 번째 rename이 실패하면 이전 사이트를 되돌린다
            raise
        shutil.rmtree(old, ignore_errors=True)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return sum(1 for _ in out.rglob("*.html"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "site.json"))
    ap.add_argument("--out", default=str(ROOT / "site"))
    a = ap.parse_args()
    try:
        n = build(a.data, a.out)
    except Exception as e:  # noqa: BLE001 - 어떤 실패든 종료 1, site/는 그대로
        print(f"빌드 실패: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(f"built {n} html files into {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
