# 실행 기록 3쪽(S7a): /runs/ 주차별 표 → /runs/<주>/ 날 → run 표 → /runs/<주>/<run>/ 수치 레일 + 단계 목록(접힘 0, JS 0).
# build.py가 render_all(b)로 부른다. b = build 모듈(page·esc·table·write·C 등 공용 도구를 인자로 받아 순환 import를 피함).
from datetime import date

WEEKDAY = "월화수목금토일"
ARR = ' <span class="sep">→</span> '
# 상세 표 열 폭(같은 역할 열끼리 같은 폭). 머리 → 폭 목록
WIDTHS = {("a", "b", "판정", "이유", "확신도"): ("24%", "24%", "10em", "", "5em"), ("순위", "후보", "판정", "이유"): ("5em", "24%", "10em", ""),
          ("항목", "원본 추적 경로", "깊이", "대조"): ("24%", "", "5em", "24%"), ("위치", "종류", "지적", "수정"): ("24%", "10em", "", "32%")}
NUM_HEADS = ("확신도", "깊이", "순위")
LEGEND = ("결과: weekly는 clusters → candidates → selected → topics / code_rejects / check, "
          "topic 1개는 topics 1 / steps, nightly는 steps / exit≠0")


def run_path(r):
    return f'/runs/{r["week"]}/{r["id"]}/'


def dur_text(sec):
    return "-" if sec is None else f"{sec}초" if sec < 60 else f"{round(sec / 60)}분"


def cost_text(c):
    return "$0" if not c else f"${c:.3f}"


def hm(ts):
    return ts[11:16]


def day_text(day):
    d = date.fromisoformat(day)
    return f"{d.month}.{d.day} {WEEKDAY[d.weekday()]}"


def status_html(b, s):
    if s in ("partial", "failed"):
        return f'<span class="check">{b.esc(s)}</span>'
    return f'<span class="state{" ok" if s in ("ok", "published") else ""}">{b.esc(s)}</span>'


def mode_text(m):
    return "자동" if m == "auto" else "수동"


# ---------------------------------------------------------------- /runs/ 주차별 표
def render_weeks(b):
    rows = []
    for rw in b.C.d["run_weeks"]:
        w = rw["weekly"]
        weekly = str(w["total"]) + (f' <span class="dim">(full {w["full"]} / partial {w["partial"]} / topic {w["topic"]})</span>' if w["total"] else "")
        rows.append([f'<a href="/runs/{rw["week"]}/">{b.esc(rw["label"])}</a>', f'<span class="nb">{b.esc(rw["range"])}</span>', f'{rw["nightly_days"]}/7', weekly,
                     f'<span class="nb">{b.mdhm(rw["published_at"])}</span>' if rw["published_at"] else "-"])
    return b.ops_page("실행 기록", "runs", "/runs/", f'주차 → 날 → run{b.SEP}주차를 누르면 그 주의 run 목록',
                      b.table(["주차", "기간", "nightly", "weekly", "publish"], rows, nums=(2,)))


# ---------------------------------------------------------------- /runs/<주>/
def result_text(b, r):
    res = r["result"]
    if r["kind"] == "nightly":
        return f'steps {res["steps"]} / exit≠0 {res["failed"]}'
    if r["kind"] == "steps":
        parts = []
        for k, sts in res["kinds"].items():
            n = sum(sts.values())
            parts.append(f"{k} ×{n}" + ("" if list(sts) == ["ok"] else " (" + ", ".join(f"{s} {c}" for s, c in sts.items()) + ")"))
        return " / ".join(parts)
    if r["topic_id"]:
        return f'topics {res["topics"]} / steps {res["steps"]}'
    num = lambda k: "-" if res[k] is None else str(res[k])  # noqa: E731
    chain = ARR.join(num(k) for k in ("clusters", "candidates", "selected", "topics"))
    return f'{chain} / {num("code_rejects")} / {num("check_topics")}'


def run_cell(b, r):
    cur = ' <span class="cur">current</span>' if r["current"] else ""
    if r["kind"] == "steps":
        return '<span class="r-run">steps</span>'
    href = f'<a class="r-run" href="{run_path(r)}">{r["kind"]}</a>'
    if r["kind"] == "nightly":
        return f'{href} <span class="dim">{b.esc(r["label"].removeprefix("nightly "))}</span>'
    if r["topic_id"]:
        label = f'{href} <span class="dim">topic</span> {b.esc(r["topic_id"])}{cur}'
    else:
        label = f'{href} <span class="dim">{b.esc(r["label"])}</span>{cur}'
    return f'<span class="r-sub"><span class="r-mark">└</span>{label}</span>' if r["sub"] else label


def run_row(b, r):
    cls = ' class="tr-sub"' if r["sub"] else ' class="tr-steps"' if r["kind"] == "steps" else ""
    tail = b.SEP.join([dur_text(r["duration_sec"]), cost_text(r["cost_usd"])])
    return (f'<tr{cls}><td class="nw">{hm(r["at"])}</td><td class="nw dim">{mode_text(r["mode"])}</td><td class="r-runc">{run_cell(b, r)}</td>'
            f'<td class="r-res">{result_text(b, r)}</td><td class="num dim r-x">{tail}</td><td class="r-tail">{status_html(b, r["status"])}</td></tr>')


def publish_row(b, rw):
    cur = (rw["current_run_id"] or "-")[-4:]
    return (f'<tr><td class="nw">{hm(rw["published_at"])}</td><td class="nw dim">-</td><td class="r-runc"><span class="r-run">publish</span> '
            f'<span class="dim">weeks.published_at</span></td><td class="r-res">current {b.esc(cur)}</td><td class="num dim r-x"></td>'
            f'<td class="r-tail">{status_html(b, "published")}</td></tr>')


def render_week(b, rw, idx):
    runs = [r for r in b.C.d["runs"] if r["week"] == rw["week"]]
    days = {}
    for r in runs:
        days.setdefault(r["day"], []).append((r["at"], run_row(b, r)))
    if rw["published_at"]:
        days.setdefault(rw["published_at"][:10], []).append((rw["published_at"], publish_row(b, rw)))
    body = ""
    for day in sorted(days, reverse=True):
        rows = sorted(days[day], key=lambda x: x[0], reverse=True)
        body += (f'<tr class="rt-day"><th scope="rowgroup" colspan="6">{day_text(day)} <span class="dim">run {len(rows)}</span></th></tr>'
                 + "".join(x[1] for x in rows))
    head = ("<colgroup><col class=\"c-t\"><col class=\"c-m\"><col class=\"c-run\"><col><col class=\"c-x\"><col class=\"c-s\"></colgroup>"
            '<thead><tr><th scope="col">시각</th><th scope="col">자동/수동</th><th scope="col">run</th><th scope="col">결과</th>'
            '<th scope="col" class="num">시간 / 비용</th><th scope="col" class="r-tail">상태</th></tr></thead>')
    rws = b.C.d["run_weeks"]
    nav = []
    if idx + 1 < len(rws):
        nav.append(f'<a href="/runs/{rws[idx + 1]["week"]}/">← {b.esc(rws[idx + 1]["label"])}</a>')
    if idx:
        nav.append(f'<a href="/runs/{rws[idx - 1]["week"]}/">{b.esc(rws[idx - 1]["label"])} →</a>')
    inner = (f'<div class="ph"><p class="meta crumb"><a href="/runs/">실행 기록</a>{b.SEP}{b.esc(rw["label"])}</p><h1>{b.esc(rw["label"])}</h1></div>'
             f'<p class="meta rt-legend">{LEGEND}</p><div class="rt-wrap"><table class="rt v1">{head}<tbody>{body}</tbody></table></div>'
             + (f'<p class="meta wk-nav">{b.SEP.join(nav)}</p>' if nav else ""))
    path = f'/runs/{rw["week"]}/'
    return b.page(f'실행 기록 {rw["label"]} - TrendsIT', f'<main class="wrap ops">{inner}</main>', "runs", path)


# ---------------------------------------------------------------- /runs/<주>/<run>/
def k_text(n):
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def rail_group(b, title, items):
    """items: (이름, 값) 목록. 값이 None인 것은 뺀다. 이름·값 사이는 줄어드는 순서면 →로 이어 붙이는 .seq는 title에 ' → '가 있을 때."""
    items = [(k, v) for k, v in items if v is not None]
    lis = "".join(f'<li><span class="k">{b.esc(k)}</span><span class="v">{b.esc(v)}</span></li>' for k, v in items)
    seq = " seq" if " → " in title else ""
    return f'<div class="rail-g"><p class="rail-t">{b.esc(title)}</p><ol class="rail{seq}">{lis}</ol></div>'


def rails_html(b, r):
    s = r["summary"]
    if not s:
        return ""
    if r["kind"] == "weekly":
        rounds = ", ".join(f"{k} ×{v}" for k, v in (s.get("rounds") or {}).items() if v) or None
        return (rail_group(b, "cluster → select → write", [(k, s.get(k)) for k in ("clusters", "candidates", "selected", "topics", "published")])
                + rail_group(b, "review", [("rounds", rounds), ("code_rejects", s.get("code_rejects")), ("critic_rejects", s.get("critic_rejects")),
                                           ("check", s.get("check_topics"))]))
    return (rail_group(b, "collect → filter → summarize", [("collected", s["collected"]), ("filter keep", s["filter_keep"]), ("cards", s["cards"])])
            + rail_group(b, "plan이 고른 것", [("deep_text", s["deep_text"]), ("video", s["video"]), ("repo", s["repo"])])
            + rail_group(b, "steps", [("exit≠0", s["exit_nonzero"])]))


def who_html(b, who):
    if who["kind"] == "code":
        return '<span class="who">code</span>'
    txt = " / ".join(b.esc(x) for x in (who["kind"], who["role"], who["model"]) if x) + (f' ×{who["n"]}' if who["n"] else "")
    return f'<span class="who"><code class="ic">{txt}</code></span>'


def table_html(b, head, rows):
    widths = WIDTHS.get(tuple(head), ())
    cg = "<colgroup>" + "".join(f'<col style="width:{w}">' if w else "<col>" for w in widths) + "</colgroup>" if widths else ""
    num = lambda i: ' class="num"' if head[i] in NUM_HEADS else ""  # noqa: E731
    th = "".join(f'<th scope="col"{num(i)}>{b.esc(h)}</th>' for i, h in enumerate(head))
    tr = "".join(f'<tr><th scope="row">{b.esc(r[0])}</th>' + "".join(f"<td{num(i)}>{b.esc(c)}</td>" for i, c in enumerate(r[1:], 1)) + "</tr>" for r in rows)
    return f'<div class="dtable-wrap"><table class="dtable{" fixed" if widths else ""}">{cg}<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def topic_html(b, i, t):
    status = f'<span class="check">{b.esc(t["status"])}</span>' if t["status"] == "checked" else b.esc(t["status"] or "-")
    meta = b.SEP.join([f'rounds {t["final_round"] if t["final_round"] is not None else "-"}', status, f'in {k_text(t["tokens_in"])}',
                       f'out {k_text(t["tokens_out"])}', cost_text(t["cost_usd"])])
    chain = ARR.join(f'<span class="nb{" hit" if n == "code" and x.startswith(("반려", "checked", "failed", "중단")) else ""}">{b.esc(n)}</span> {b.esc(x)}'
                     for n, x in t["chain"])
    issues = table_html(b, ["위치", "종류", "지적", "수정"], t["issues"]) if t["issues"] else ""
    return (f'<div class="tp"><div class="tp-s"><span class="tp-n">{t["rank"]}</span><span><span class="tp-h">{b.esc(t["title"])}</span> '
            f'<span class="tp-m">{b.esc(t["topic_id"])}</span><br><span class="tp-m">{meta}</span></span></div>'
            f'<div class="tp-b"><p class="tp-chain">{chain}</p>{issues}</div></div>')


def detail_html(b, blocks):
    out = []
    for blk in blocks:
        if blk["type"] == "kv":
            out.append('<dl class="kv">' + "".join(f"<dt>{b.esc(k)}</dt><dd>{b.esc(v)}</dd>" for k, v in blk["items"]) + "</dl>")
        elif blk["type"] == "list":
            out.append('<ul class="pl">' + "".join(f"<li>{b.esc(x)}</li>" for x in blk["items"]) + "</ul>")
        elif blk["type"] == "table":
            out.append(table_html(b, blk["head"], blk["rows"]))
        else:
            out.append('<div class="tps">' + "".join(topic_html(b, i, t) for i, t in enumerate(blk["items"], 1)) + "</div>")
    return "".join(out)


def step_html(b, s):
    att = ' <span class="check">attention</span>' if s["attention"] else ""
    tail = b.SEP.join(x for x in (dur_text(s["duration_sec"]) if s["duration_sec"] is not None else "", cost_text(s["cost_usd"]) if s["cost_usd"] else "") if x)
    d = f'<div class="st-d">{detail_html(b, s["detail"])}</div>' if s["detail"] else ""
    return (f'<li class="st"><div class="st-t">{s["t"]}</div><div><div class="st-h"><span class="st-n">{b.esc(s["name"])}</span>'
            f'{" ".join(who_html(b, w) for w in s["who"])}{att}<span class="st-x">{tail}</span></div>'
            f'<div class="st-l">{b.esc(s["line"])}</div>{d}</div></li>')


def render_run(b, r):
    rw = b.C.rws[r["week"]]
    title = f'weekly {r["week"].upper()}' if r["kind"] == "weekly" else r["label"]
    crumb = b.SEP.join([f'<a href="/runs/">실행 기록</a>', f'<a href="/runs/{r["week"]}/">{b.esc(rw["label"])}</a>', b.esc(title)])
    sub = [f'{day_text(r["day"])} {hm(r["at"])}', mode_text(r["mode"]), status_html(b, r["status"])] + ([b.esc(r["label"])] if r["kind"] == "weekly" else [])
    n_att = sum(s["attention"] for s in r["steps"])
    inner = (f'<div class="ph rh"><p class="meta crumb">{crumb}</p><h1>{b.esc(title)}</h1><p class="meta">{b.SEP.join(sub)}</p>'
             f'<div class="rails">{rails_html(b, r)}</div></div><h2>steps {len(r["steps"])} <span class="meta">attention {n_att}</span></h2>'
             f'<ol class="steps">{"".join(step_html(b, s) for s in r["steps"])}</ol>')
    return b.page(f"{title} 실행 기록 - TrendsIT", f'<main class="wrap ops">{inner}</main>', "runs", run_path(r))


def render_all(b):
    runs = b.C.d["runs"]
    for r in runs:
        if r["kind"] == "steps" and r["steps"]:
            raise b.BuildError(f'runs[{r["id"]}]: kind steps인데 steps가 비어 있지 않음')
        if r["week"] not in b.C.rws:
            raise b.BuildError(f'runs[{r["id"]}]: week {r["week"]}가 run_weeks에 없음')
    b.write("runs/index.html", render_weeks(b))
    for i, rw in enumerate(b.C.d["run_weeks"]):
        b.write(f'runs/{rw["week"]}/index.html', render_week(b, rw, i))
    for r in runs:
        if r["kind"] != "steps":
            b.write(f'runs/{r["week"]}/{r["id"]}/index.html', render_run(b, r))
