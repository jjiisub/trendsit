# TrendsIT 사이트 빌드(S6a). 실행: uv run python site_src/build.py [--data data/site.json] [--out site]
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
def link(url):
    """수집한 URL은 http(s)만 링크로 쓴다(javascript: 등은 링크 없이 글자만). 아니면 None."""
    return url if isinstance(url, str) and re.match(r"https?://", url, re.I) else None


def esc(s):
    """이스케이프. 원문 글자(&amp; 등 포함)는 그대로 화면에 보이게 한 번만 이스케이프."""
    return html.escape(str(s), quote=True)


TOKEN_RE = re.compile(r"([A-Za-z0-9][A-Za-z0-9.%$+\-_/:,~]*[A-Za-z0-9%)]|[A-Za-z0-9]{2,})")


def nb_tokens(s):
    """숫자·영문 토큰(20자 이하)을 줄에서 쪼개지지 않게 묶는다. 이미 이스케이프된 문자열에 적용, 태그 안과 엔티티(&#x27; &quot; &amp; 등)는 건드리지 않음."""
    def rep(m):
        t = m.group(0)
        return t if len(t) > 20 or "&" in t else f'<span class="nb">{t}</span>'
    return "".join(p if re.fullmatch(r"<[^>]+>|&#?\w+;", p) else TOKEN_RE.sub(rep, p) for p in re.split(r"(<[^>]+>|&#?\w+;)", s) if p)


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
    """화면에 표시할 확인 필요 위치(절 밖): summary, title. '빠진 시각 요소: …' 등은 표시 안 함."""
    return [c for c in t.get("checks", []) if c in ("summary", "title")]


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


def write_bytes(rel, content):
    path = C.out / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def week_path(w):
    return f'/week/{w["id"]}/'


def topic_path(t):
    return f'/topic/{t["id"]}/'


# ---------------------------------------------------------------- 인용, 도식
def cite(t, sid, ctr):
    """인용 번호 + 툴팁(마우스·앵커 위치 지원에서만 보임). 번호를 누르면 출처 목록 항목(#src-id)."""
    s, n, k = C.srcs[sid], C.nums[sid], next(ctr)
    meta = " / ".join(x for x in (C.chl[s["channel"]], s.get("site"), md(s.get("date"))) if x)
    go = f'<a class="tip-go" href="{esc(s["url"])}" rel="noopener">원문 열기</a>' if link(s.get("url")) else ""
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


def para_html(t, p, ctr, chk=""):
    return f'<p class="dp">{with_end(p["text"], cites(t, p["refs"], ctr) + chk)}</p>'


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
        src = f'<p class="dg-s">출처 {cite(t, g["ref"], ctr)}</p>'
    return f'<figure class="dg dg-bars"><figcaption class="dg-t">{esc(g["title"])}</figcaption>{ctx_p(g)}<div class="bars">{rows}</div>{src}</figure>'


EVIDENCE_ID_RE = re.compile(r"\s*\[\s*(?:it|og|vd|rp|sl):[\w./#@:-]+(?:\s*,\s*(?:it|og|vd|rp|sl):[\w./#@:-]+)*\s*\]")


def ctx_p(g):
    """도식 설명 끝의 내부 근거 id([it:8#q2] 등)는 공개 화면에 내지 않는다."""
    ctx = EVIDENCE_ID_RE.sub("", g.get("context") or "").strip()
    return f'<p class="dg-c">{rich(ctx)}</p>' if ctx else ""


def table_html(g):
    heads = "".join(f"<th>{esc(c)}</th>" for c in g["columns"])
    rows = "".join("<tr>" + "".join(f"<{'th scope=\"row\"' if i == 0 else 'td'}>{esc(c)}</{'th' if i == 0 else 'td'}>"
                                    for i, c in enumerate(row)) + "</tr>" for row in g["rows"])
    note = f'<p class="dg-s">{esc(g["note"])}</p>' if g.get("note") else ""
    return (f'<figure class="dg dg-table"><figcaption class="dg-t">{esc(g["title"])}</figcaption>'
            f'<div class="cmpt-wrap"><table class="cmpt"><thead><tr>{heads}</tr></thead><tbody>{rows}</tbody></table></div>{note}</figure>')


def tile_html(x, t, ctr):
    return (f'<div class="tile"><span class="tile-v">{rich(x["value"])}</span><span class="tile-l">{esc(x["label"])}</span>'
            f'<span class="tile-s">{esc(x.get("note") or "")}</span><span class="tile-x">{cites(t, x["refs"], ctr)}</span></div>')


def tiles_wrap_html(items, t, ctr):
    return f'<div class="tiles n{len(items)}">' + "".join(tile_html(x, t, ctr) for x in items) + "</div>"


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


def visual_html(t, sec, ctr):
    v = sec.get("visual")
    if not v:
        return ""
    if v["type"] == "bars":
        return bars_html(t, v, ctr)
    if v["type"] == "table":
        return table_html(v)
    if v["type"] == "tiles":
        return f'<figure class="dg dg-tiles">{tiles_wrap_html(v["items"], t, ctr)}</figure>'
    if v["type"] == "events":
        return events_html(t, v, ctr)
    return ""


def slide_html(s, video_url):
    sl = s.get("slide")
    if not sl:
        return ""
    url = video_url
    cap_parts = [esc(sl["title"])] if sl.get("title") else []
    if sl.get("caption"):
        cap_parts.append(esc(sl["caption"]))
    time_text = f"슬라이드 {esc(mmss(sl['sec']))}"
    time_link = f'<a href="{esc(url)}&t={sl["sec"]}s">{time_text}</a>' if url and link(url) else time_text
    cap = meta_line([time_link, *cap_parts])
    return (f'<figure class="simg"><img src="/assets/slides/{esc(sl["image"].split("/")[-1])}" width="960" height="540" '
            f'loading="lazy" alt="슬라이드: {esc(sl.get("title") or "")}"><figcaption>{cap}</figcaption></figure>')


def video_secs_html(s, video_url):
    secs = s.get("video_secs") or []
    if not secs or not video_url:
        return ""
    rows = "".join(f'<li class="{"vx" if m.get("slide") else ""}"><a href="{esc(video_url)}&t={m["sec"]}s">{mmss(m["sec"])}</a> '
                   f'{rich(m.get("label", ""))}</li>' for m in secs)
    return f'<ol class="vgo" aria-label="영상 구간">{rows}</ol>'


# ---------------------------------------------------------------- 토픽
def follow_html(t):
    r = t.get("relation", {})
    prev = C.topics.get(r.get("topic_id")) if r.get("type") == "follow_up" else None
    if not prev:
        return ""
    wk = C.weeks[prev["week"]]["label"]
    return f'<p class="follow">지난 흐름 <a href="{topic_path(prev)}">{esc(wk)} ‘{esc(prev["title"])}’</a></p>'


def topic_meta(t, read_min=None, link_check=False):
    n = channel_counts(t)
    parts = [f'<span class="chs">{" / ".join(f"{C.chl[c]} {n[c]}" for c in CH_ORDER if n[c])}</span>']
    if t.get("relation", {}).get("type") == "follow_up":
        parts.append('<span class="fu">후속</span>')
    if t.get("has_check"):
        parts.append('<a class="fu" href="#chk-1">확인 필요</a>' if link_check else '<span class="fu">확인 필요</span>')
    if read_min is not None:
        parts.append(f"약 {read_min}분")
    return f'<p class="tmeta meta">{meta_line(parts)}</p>'


def source_list(t):
    """채널 머리 없이 화면 번호 순으로 한 목록(QA-11). 영상 출처는 그 아래 전체 타임라인(5.8)."""
    items = ""
    for s in sorted(t["sources"], key=lambda s: C.nums[s["id"]]):
        title = esc(s.get("title") or s["id"])
        anchor = f'<a href="{esc(s["url"])}">{title}</a>' if link(s.get("url")) else title
        meta = " / ".join(x for x in (C.chl[s["channel"]], s.get("site"), md(s.get("date"))) if x)
        origin = ""
        if link(s.get("origin")):
            shown = re.sub(r"^https?://", "", s["origin"])
            origin = f'<p class="meta">원본 <a href="{esc(s["origin"])}">{esc(shown[:70])}</a></p>'
        tl = video_timeline_html(s) if s["channel"] == "video" else ""
        items += (f'<li id="src-{esc(s["id"])}" class="src"><span class="src-n">[{C.nums[s["id"]]}]</span>'
                  f'<div><p class="src-t">{anchor}</p><p class="meta">{esc(meta)}</p>{origin}{tl}</div></li>')
    out = f'<ol class="srcs">{items}</ol>'
    return f'<section class="sec sources" aria-labelledby="h-src"><h2 class="sec-t" id="h-src">출처</h2>{out}</section>'


def mmss(sec):
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


def video_timeline_html(s):
    """영상 출처 아래 전체 타임라인(5.8). v1 토픽 데이터에는 timeline 칸이 없어 없으면 빈 글자."""
    marks = s.get("timeline") or []
    if not marks or not link(s.get("url")):
        return ""
    rows = "".join(f'<li class="{"slide" if m.get("slide") else ""}"><span class="vt-t">'
                   f'<a href="{esc(s["url"])}&t={m["sec"]}s">{mmss(m["sec"])}</a></span>'
                   f'<span class="vt-x">{rich(m.get("label", ""))}{" (슬라이드)" if m.get("slide") else ""}</span></li>'
                   for m in marks)
    return f'<ol class="vtl" aria-label="영상 타임라인">{rows}</ol>'


def topic_read_minutes(t):
    chars = len(re.sub(r"\s", "", plain(t["title"]))) + len(re.sub(r"\s", "", plain(t["summary"])))
    for s in t["sections"]:
        chars += sum(len(re.sub(r"\s", "", plain(p["text"]))) for p in s["paragraphs"])
    return max(1, math.ceil(chars / 500))


def video_url_of(t):
    return next((s["url"] for s in t["sources"] if s["channel"] == "video" and link(s.get("url"))), None)


def section_html(t, s, idx, chk_ctr, video_url, ctr):
    chk = ""
    if s.get("check"):
        chk = f'<span class="chk" id="chk-{next(chk_ctr)}">확인 필요</span>'
    paras = s["paragraphs"]
    inner = para_html(t, paras[0], ctr, chk) if paras else ""
    inner += visual_html(t, s, ctr)
    inner += "".join(para_html(t, p, ctr) for p in paras[1:])
    inner += slide_html(s, video_url)
    inner += video_secs_html(s, video_url)
    return f'<section class="dsec" id="sec-{idx}"><h2 class="dsec-t">{esc(s["heading"])}</h2>{inner}</section>'


def render_topic(t):
    C.srcs = {s["id"]: s for s in t["sources"]}
    C.nums = src_order(t)
    ctr = iter(range(1, 10**6))
    w = C.weeks[t["week"]]
    checks = shown_checks(t)
    video_url = video_url_of(t)
    chk_ctr = iter(range(1, 10**6))
    # 문서 순서대로 번호를 매긴다(제목·요약이 절보다 먼저 와서 ⚠면 #chk-1이 그쪽을 가리켜야 함)
    title_chk = f'<span class="chk" id="chk-{next(chk_ctr)}">확인 필요</span>' if "title" in checks else ""
    summary_chk = f'<span class="chk" id="chk-{next(chk_ctr)}">확인 필요</span>' if "summary" in checks else ""
    secs_html = "".join(section_html(t, s, i, chk_ctr, video_url, ctr) for i, s in enumerate(t["sections"]))
    tiles = tiles_wrap_html(t["head_tiles"], t, ctr) if t.get("head_tiles") else ""
    pn = ""
    ids = w["topic_ids"]
    i = ids.index(t["id"])
    if len(ids) > 1:
        nav_link = lambda tid, cls, k: (f'<a class="{cls}" href="{topic_path(C.topics[tid])}"><span class="pn-k">{k}</span>'  # noqa: E731
                                    f'<span class="pn-t">{esc(C.topics[tid]["title"])}</span></a>')
        pn = ('<nav class="pn" aria-label="같은 주 토픽">' + (nav_link(ids[i - 1], "pn-prev", "이전 토픽") if i else "<span></span>")
              + (nav_link(ids[i + 1], "pn-next", "다음 토픽") if i + 1 < len(ids) else "") + "</nav>")
    read_min = topic_read_minutes(t)
    body = (
        f'<main class="wrap topic"><article><div class="mini" aria-hidden="true"><span class="mini-t">{esc(t["title"])}</span>'
        f'<a class="mini-s" href="#h-src" tabindex="-1">출처 {len(t["sources"])}</a></div>'
        f'<p class="back meta"><a href="{week_path(w)}">{esc(w["label"])} 브리핑</a></p>'
        f'<h1 class="tt ttl">{esc(t["title"])}{title_chk}</h1><p class="ts">{rich(t["summary"])}{summary_chk}</p>'
        f'{topic_meta(t, read_min, link_check=True)}{follow_html(t)}'
        + (f'<div class="tiles-wrap">{tiles}</div>' if tiles else "")
        + secs_html + source_list(t) + pn + "</article></main>")
    return page(f'{plain(t["title"])} - TrendsIT', body, "briefing", topic_path(t), plain(t["summary"])[:120])


# ---------------------------------------------------------------- 홈·주차
def read_minutes(w):
    chars = 0
    for tid in w["topic_ids"]:
        chars += sum(len(re.sub(r"\s", "", plain(x))) for x in (C.topics[tid]["title"], C.topics[tid]["summary"]))
        chars += sum(len(re.sub(r"\s", "", plain(p["text"]))) for s in C.topics[tid]["sections"] for p in s["paragraphs"])
    return max(1, math.ceil(chars / 500))


def repo_html(r):
    """신호 글자를 메타 줄로(QA-14): 이번 주 별 / 신호 / 관련 토픽을 ' / '로(가운뎃점 없음). needs_check는 .check 유지."""
    name = esc(r["name"])
    name = f'<a href="{esc(r["url"])}">{name}</a>' if link(r.get("url")) else name
    what = f'<p class="rp-w">{esc(r["what"])}</p>' if r.get("what") else ""
    parts = []
    if r.get("stars_7d"):
        parts.append(f"이번 주 별 {esc(r['stars_7d'])}")
    if r.get("signal"):
        label = esc(C.signals.get(r["signal"], r["signal"]))
        parts.append(f'<span class="check">{label}</span>' if r["signal"] == "needs_check" else label)
    rel = C.topics.get(r.get("topic_id"))
    if rel:
        parts.append(f'관련 토픽 <a href="{topic_path(rel)}">{esc(rel["title"])}</a>')
    meta = f'<p class="rp-m meta">{meta_line(parts)}</p>' if parts else ""
    return f'<li class="rp"><p class="rp-h"><span class="rp-n">{name}</span></p>{what}{meta}</li>'


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
        + '</section><span class="tab-anchor" id="topics"></span><span class="tab-anchor" id="repos"></span>'
        f'<nav class="tabs" aria-label="이번 주 섹션"><a class="tb-t" href="#topics">주요 토픽 {len(ts)}</a><a class="tb-r" href="#repos">트렌딩 레포 {len(repos)}</a></nav>'
        f'<div class="panels"><section class="panel" id="panel-topics" aria-labelledby="topics-t"><h2 class="sec-t" id="topics-t">주요 토픽 <span class="cnt">{len(ts)}</span></h2><ol class="list">{items}</ol></section>'
        f'<section class="panel" id="panel-repos" aria-labelledby="repos-t"><h2 class="sec-t" id="repos-t">트렌딩 레포 <span class="cnt">{len(repos)}</span></h2>{repo_body}</section></div>'
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
        name = f'<a href="{esc(s["url"])}">{esc(s["name"])}</a>' if link(s.get("url")) else esc(s["name"])
        lastc = "-" if not last else f'{mdhm(last["at"])}, 새 항목 {last["count"]}건'
        if s.get("last_error"):
            lastc += f'<br><span class="dim">{esc(s["last_error"])}</span>'
        rows.append([name, C.d["meta"]["channel_labels"][s["channel"]], st, wk.get("collected", 0), wk.get("used_in_topics", 0), lastc])
    todo = f'<p class="todo"><b>확인할 것</b> 마지막 수집이 정상이 아닌 소스 {bad}개</p>'
    n_on = sum(s["enabled"] for s in C.d["sources"])
    return ops_page("소스", "sources", "/sources/", f'켜진 소스 {n_on} {SEP} 전체 {len(C.d["sources"])} {SEP} 수집 수는 {esc(C.latest["label"])} 기준',
                    todo + table(["이름", "채널", "상태", "이번 주 수집", "토픽에 쓰인 수", "마지막 수집"], rows, nums=(3, 4)))


KEYWORD_TOPIC_LINKS_MAX = 5


def render_keywords():
    kw = C.d["keywords"]
    rows = []
    for k in kw["items"]:
        ids = [i for i in k["topics"] if i in C.topics]
        shown = ", ".join(f'<a href="{topic_path(C.topics[i])}">{esc(C.topics[i]["title"])}</a>' for i in ids[:KEYWORD_TOPIC_LINKS_MAX])
        extra = len(ids) - KEYWORD_TOPIC_LINKS_MAX
        links = (shown + (f', 외 {extra}개' if extra > 0 else "")) if ids else "-"
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
    if r.get("fallback_select"):  # C-30: 선별이 대체 계획(점수 순)으로 돈 run
        inner += '<p class="meta">선별 대체 계획(점수 순)</p>'
    c = r.get("counts") or {}
    rev = c.get("review") or {}
    if c:  # D-37: 이 주 발행 n개 / 이 실행이 쓴 토픽 m개
        inner += f'<p class="meta">이 주 발행 {c.get("published", 0)}개 / 이 실행이 쓴 토픽 {c.get("written", 0)}개</p>'
    cells = [("후보", c.get("candidates")), ("선정", c.get("selected")), ("근거 id", c.get("evidence_ids")), ("1차 통과", rev.get("passed_first")),
             ("반려", rev.get("rejected")), ("확인 필요", rev.get("needs_check")), ("발행", c.get("published"))]
    inner += '<dl class="kv">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in cells if v is not None) + "</dl>" if c else ""
    if c.get("related"):
        rel = c["related"]
        inner += f'<p class="meta">과거 대조: 후속 {rel["follow_up"]} {SEP} 신규 {rel["new"]} {SEP} 중복 {rel["duplicate"]}</p>'
    if r.get("steps"):  # 단계 레일: steps의 역할 문장(확인이 필요한 단계만 .check)
        lis = "".join(f'<li><span class="k">{esc(" ".join(x for x in (s.get("t"), s.get("role")) if x))}</span>'
                      f'<span class="v">{esc(s["text"] + (" (대체 계획)" if s.get("fallback") else ""))}</span>'
                      + ('<span class="check">확인 필요</span>' if s.get("attention") else "") + "</li>" for s in r["steps"])
        inner += f'<h2>단계 기록</h2><ol class="rail">{lis}</ol>'
    cmps = [s["detail"] for s in r.get("steps") or [] if s.get("detail")]
    if cmps:
        inner += "<h2>반려 비교</h2>" + "".join(
            f'<div class="cmp"><div><h3>초안</h3><p>{esc(d["draft"])}</p></div><div><h3>근거</h3><p>{esc(d["evidence"])}</p></div>'
            + (f'<div><h3>수정</h3><p>{esc(d["fixed"])}</p></div>' if d.get("fixed") else "") + "</div>" for d in cmps)
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
    slides_src = C.data_dir / "slides"
    for t in C.d["topics"]:
        for s in t["sections"]:
            if s.get("slide"):
                fname = s["slide"]["image"].split("/")[-1]
                src = slides_src / fname
                if not src.is_file():
                    raise BuildError(f"슬라이드 파일 없음: {src}")
                write_bytes(f"assets/slides/{fname}", src.read_bytes())
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
    C.data_dir = pathlib.Path(data_path).resolve().parent  # 슬라이드는 --data 파일 옆 slides/(기본값이면 data/slides/, 기존과 같음)
    out = pathlib.Path(out_path).resolve()  # 실행 폴더에서는 site가 작업 폴더로 가는 링크
    out.parent.mkdir(parents=True, exist_ok=True)
    old = out.with_name(out.name + ".old")
    if not out.exists() and old.exists():
        old.rename(out)  # 이전 빌드가 두 rename 사이에 죽어 site/가 없으면 이전 사이트를 되살린다(입력 검증 뒤)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=out.name + ".tmp-", dir=out.parent))
    try:
        build_into(tmp)
        os.chmod(tmp, 0o755)
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
