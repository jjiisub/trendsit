"""시안 공통: 데이터 읽기, 문자열 도우미, 공통 블록 렌더러.

표준 라이브러리만 쓴다(build.py와 같은 방식). 각 시안은 sNN.py에서 옵션과 CSS만 바꾼다.
"""
import html
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = json.load(open(BASE / "design-sample.json", encoding="utf-8"))
WEEK = DATA["weeks"][0]
PREV_WEEK = DATA["weeks"][1]
TOPICS = {t["id"]: t for t in DATA["topics"]}
W_TOPICS = [TOPICS[i] for i in WEEK["topic_ids"]]
REPOS = [r for r in DATA["repos"] if r["week"] == WEEK["id"]]
SIGNAL = DATA["meta"]["signal_labels"]
CH_LABEL = {"text": "글", "video": "영상", "github": "레포"}
CH_ORDER = ["text", "video", "github"]
TOPIC_PAGES = ["w40-jev-race", "w40-eval-cost", "w40-terminal-table"]

FONT_URLS = {
    "plex": "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;700&display=swap",
    "noto": "https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap",
    "serif": "https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@600;700&display=swap",
}


def esc(s):
    return html.escape(str(s), quote=True)


TOKEN_RE = re.compile(r"([A-Za-z0-9][A-Za-z0-9.%$+\-_/:,~]*[A-Za-z0-9%)]|[A-Za-z0-9]{2,})")


def nb_tokens(s):
    """숫자·영문 토큰을 줄에서 쪼개지지 않게 묶는다(이미 이스케이프된 문자열에 적용). 20자 넘는 토큰은 그대로."""
    def rep(m):
        t = m.group(0)
        if len(t) > 20 or "&" in t:
            return t
        return f'<span class="nb">{t}</span>'
    # 태그 안은 건드리지 않음
    parts = re.split(r"(<[^>]+>)", s)
    return "".join(p if p.startswith("<") else TOKEN_RE.sub(rep, p) for p in parts)


def rich(s):
    """==형광== → mark, 토큰 묶기."""
    out = re.sub(r"==(.+?)==", r'<mark class="hl">\1</mark>', esc(s))
    out = nb_tokens(out)
    # `코드` -> 인라인 코드(줄에서 쪼개지지 않게)
    return re.sub(r"`([^`]+)`", lambda m: '<code class="ic">' + re.sub(r"</?span[^>]*>", "", m.group(1)) + "</code>", out)


def plain(s):
    return str(s).replace("==", "")


def md(d):
    _, m, dd = d[:10].split("-")
    return f"{int(m)}.{int(dd)}"


def channels_text(ch, sep=" / "):
    return sep.join(f"{CH_LABEL[c]} {ch[c]}" for c in CH_ORDER if ch.get(c))


def source_count(t):
    return len(t["sources"])


def read_minutes():
    chars = sum(len(plain(t["summary"])) for t in W_TOPICS) + sum(len(r["what"]) for r in REPOS)
    chars += sum(len(plain(t["overview"])) + sum(len(plain(p["text"])) for p in t["points"]) for t in W_TOPICS)
    return max(1, round(chars / 500))


def src_index(t):
    return {s["id"]: i + 1 for i, s in enumerate(t["sources"])}


def topic_href(tid):
    return f"topic-{tid}.html" if tid in TOPIC_PAGES else "#"


def cites(t, refs, cls="ref"):
    idx = src_index(t)
    return "".join(f'<a class="{cls}" href="#src-{r}" aria-label="출처 {idx[r]}">[{idx[r]}]</a>' for r in refs if r in idx)


def point_html(t, p, cls="ref"):
    """마지막 단어와 인용 번호를 함께 묶어 번호만 다음 줄로 넘어가지 않게."""
    body = rich(p["text"])
    c = cites(t, p["refs"], cls)
    m = re.search(r"(\S+)$", body)
    # 마지막 어절이 한 음절이면 앞 어절까지 함께 묶어 '큼 [2]'만 다음 줄로 가지 않게
    if m and re.fullmatch(r"[가-힣][.,]?", m.group(1)):
        m2 = re.search(r"(\S+\s\S+)$", body)
        if m2 and "<" not in m2.group(1) and ">" not in m2.group(1):
            m = m2
    if m and not body.endswith(">"):
        body = body[: m.start()] + f'<span class="nb-end">{m.group(1)}&nbsp;{c}</span>'
    else:
        body = f'{body}<span class="nb-end">&nbsp;{c}</span>'
    if p.get("check"):
        body += ' <span class="check">확인 필요</span>'
    return body


def diagram_html(t, g):
    idx = src_index(t)
    parts = [f'<figure class="dg dg-{g["type"]}">',
             f'<figcaption class="dg-t">{esc(g["title"])}</figcaption>']
    if g.get("context"):
        parts.append(f'<p class="dg-c">{rich(g["context"])}</p>')
    if g["type"] == "bars":
        mx = max(i["value"] for i in g["items"]) or 1
        parts.append('<div class="bars">')
        for it in g["items"]:
            w = max(2, round(it["value"] / mx * 100))
            if it.get("display"):
                val = it["display"]
            elif g.get("unit") == "$":
                val = f'${it["value"]:.2f}'
            else:
                val = f'{it["value"]:g}{g.get("unit", "")}'
            cls = "bar-row" + (" em" if it.get("emphasis") else "") + (" base" if it.get("baseline") else "")
            parts.append(f'<div class="{cls}"><span class="bar-l">{esc(it["label"])}</span>'
                         f'<span class="bar-v">{esc(val)}</span>'
                         f'<span class="bar-track"><span class="bar-fill" style="width:{w}%"></span></span></div>')
        parts.append("</div>")
    elif g["type"] == "events":
        parts.append('<ol class="events">')
        for it in g["items"]:
            ref = ""
            if it.get("ref") in idx:
                ref = f' <a class="ref" href="#src-{it["ref"]}">[{idx[it["ref"]]}]</a>'
            elif it.get("topic_id"):
                ref = ' <span class="ev-prev">지난 토픽</span>'
            parts.append(f'<li><span class="ev-d">{md(it["date"])}</span><span class="ev-t">{rich(it["text"])}{ref}</span></li>')
        parts.append("</ol>")
    src = g.get("ref")
    if src and src in idx and g.get("caption"):
        parts.append(f'<p class="dg-s">{esc(g["caption"])} <a class="ref" href="#src-{src}">[{idx[src]}]</a></p>')
    elif g["type"] == "events":
        parts.append('<p class="dg-s">출처는 항목마다 번호로, 날짜는 각 출처 기준</p>')
    parts.append("</figure>")
    return "".join(parts)


def video_timeline_html(g):
    rows = "".join(
        f'<li class="{"slide" if it.get("slide") else ""}"><span class="vt-t">{esc(it["t"])}</span>'
        f'<span class="vt-x">{rich(it["text"])}{" (슬라이드)" if it.get("slide") else ""}</span></li>'
        for it in g["items"])
    return f'<ol class="vtl" aria-label="영상 타임라인">{rows}</ol>'


def diagrams_for(t, n):
    return [g for g in t.get("diagrams", []) if g.get("anchor") == n]


def video_for(t, sid):
    return [g for g in t.get("diagrams", []) if g["type"] == "video" and g.get("ref") == sid]


def follow_html(t, cls="follow"):
    r = t.get("relation", {})
    if r.get("type") != "follow_up":
        return ""
    prev = TOPICS.get(r["topic_id"])
    title = prev["title"] if prev else ""
    return f'<p class="{cls}">지난 흐름 <a href="#">{esc(PREV_WEEK["label"])} ‘{esc(title)}’</a></p>'


def repo_topic_link(r):
    if not r.get("topic_id"):
        return ""
    t = TOPICS[r["topic_id"]]
    return f'<a href="{topic_href(t["id"])}">{esc(t["title"])}</a>'


def page(title, css_fonts, css, body, lang="ko"):
    links = "".join(f'<link rel="stylesheet" href="{FONT_URLS[f]}">' for f in css_fonts)
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{esc(title)}</title>'
            f'<link rel="preconnect" href="https://fonts.googleapis.com">{links}'
            f'<style>{css}</style></head><body>{body}</body></html>')


BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--text);font-family:var(--font);font-size:16px;line-height:1.6;letter-spacing:0;word-break:var(--wb,normal);overflow-wrap:anywhere}
a{color:inherit;text-decoration:underline;text-decoration-color:var(--line-strong);text-underline-offset:3px;text-decoration-thickness:1px}
a:hover{text-decoration-color:var(--text)}
:focus-visible{outline:2px solid var(--title);outline-offset:2px;border-radius:2px}
mark.hl{background:linear-gradient(transparent 56%,var(--hl) 56%);color:inherit;font-weight:500;padding:0 1px;word-break:keep-all;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.nb{white-space:nowrap}
.nb-end{white-space:nowrap}
.sr,.sr-if{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
h1,h2,h3,.ttl{color:var(--title);word-break:keep-all;text-wrap:balance;overflow-wrap:break-word}
ol,ul{list-style:none}
.ref{display:inline-block;min-width:24px;min-height:24px;line-height:24px;text-align:center;font-size:13px;color:var(--muted);text-decoration:none;font-variant-numeric:tabular-nums;vertical-align:baseline}
.ref:hover{color:var(--title);text-decoration:underline}
.check{display:inline-block;font-size:13px;line-height:20px;padding:0 6px;border:1px solid var(--muted);border-radius:4px;color:var(--title);white-space:nowrap}
.meta{color:var(--muted);font-size:14px;font-variant-numeric:tabular-nums}
.wrap{max-width:var(--maxw,720px);margin:0 auto;padding:0 20px}
.nav{display:flex;gap:20px;align-items:center;padding:14px 0 0;font-size:15px}
.nav a{text-decoration:none;color:var(--muted);display:inline-block;padding:10px 0;min-height:44px}
.nav a[aria-current]{color:var(--title);font-weight:700;box-shadow:inset 0 -2px 0 var(--title)}
.wordmark{font-weight:700;font-size:18px;color:var(--title);text-decoration:none;margin-right:auto}
/* 도식 */
.dg{margin:12px 0 4px;padding:14px 16px;background:var(--panel);border-radius:8px}
.dg-t{font-size:14px;font-weight:700;color:var(--title);line-height:1.5}
.dg-c{font-size:14px;color:var(--text);margin-top:4px;line-height:1.6}
.dg-s{font-size:13px;color:var(--muted);margin-top:8px}
.bars{margin-top:10px;display:grid;gap:8px}
.bar-row{display:grid;grid-template-columns:1fr auto;grid-template-areas:"l v" "b b";gap:2px 8px;font-size:14px}
.bar-l{grid-area:l;color:var(--text)}
.bar-v{grid-area:v;font-variant-numeric:tabular-nums;color:var(--text)}
.bar-track{grid-area:b;height:8px;background:var(--track);border-radius:4px;overflow:hidden}
.bar-fill{display:block;height:100%;background:var(--bar);border-radius:4px}
.bar-row.em .bar-fill{background:var(--title)}
.bar-row.em .bar-l,.bar-row.em .bar-v{font-weight:700;color:var(--title)}
.bar-row.base .bar-fill{background:var(--bar-base)}
.events{margin-top:10px;display:grid;gap:6px;font-size:14px}
.events li{display:grid;grid-template-columns:44px 1fr;gap:8px}
.ev-d{color:var(--muted);font-variant-numeric:tabular-nums}
.ev-prev{font-size:13px;color:var(--muted)}
.vtl{margin-top:8px;display:grid;gap:4px;font-size:14px}
.vtl li{display:grid;grid-template-columns:48px 1fr;gap:8px}
.vt-t{font-variant-numeric:tabular-nums;color:var(--muted)}
.vtl li.slide .vt-x{font-weight:500;color:var(--title)}
"""
