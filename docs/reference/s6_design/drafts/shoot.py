# ruff: noqa
"""시안 빌드 + Chromium 캡처 + 관문 측정.

사용: python3 shoot.py [시안id ...]   (없으면 전부)
결과: out/<sid>/shots/*.png, out/gates.json
"""
import functools
import http.server
import json
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

import render
from variants import V

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
FONTROOT = HERE.parent / "fonts"
FONTPKG = {"IBM+Plex+Sans+KR": "package", "Noto+Sans+KR": "noto-sans-kr/package", "Noto+Serif+KR": "noto-serif-kr/package"}


def font_css(url):
    css = ""
    for fam, pkg in FONTPKG.items():
        if f"family={fam}" in url:
            for w in (400, 500, 600, 700):
                f = FONTROOT / pkg / f"{w}.css"
                if f.exists():
                    css += f.read_text().replace("url(./files/", f"url(http://127.0.0.1:{FONT_PORT[0]}/{pkg}/files/")
    return css


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


class TS(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(d, port):
    s = TS(("127.0.0.1", port), functools.partial(Q, directory=str(d)))
    s.daemon_threads = True
    s.allow_reuse_address = True
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


GATE_JS = r"""
(args) => {
  const [declared, tokens] = args;
  const vw = document.documentElement.clientWidth;
  const g = {};
  g.overflow = document.documentElement.scrollWidth - vw;
  // 대비
  function parse(c){const m=c.match(/[\d.]+/g); return m? m.map(Number):null;}
  function lum(rgb){const a=rgb.slice(0,3).map(v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)});return 0.2126*a[0]+0.7152*a[1]+0.0722*a[2];}
  function bgOf(el){while(el){const c=parse(getComputedStyle(el).backgroundColor); if(c && (c.length<4||c[3]>0.5)) return c; el=el.parentElement;} return [255,255,255];}
  const low=[]; const colors=new Set(); const wt=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); const seen=new Set();
  while(wt.nextNode()){const t=wt.currentNode; if(!t.textContent.trim()) continue; const el=t.parentElement; if(seen.has(el)) continue; seen.add(el);
    const cs=getComputedStyle(el); const r=el.getBoundingClientRect(); if(r.width===0||cs.visibility==='hidden') continue;
    if(el.closest('.sr,.sr-if')) continue;
    if(el.closest('details:not([open])') && !el.closest('summary')) continue;
    const fs=parseFloat(cs.fontSize), fw=parseInt(cs.fontWeight); const fg=parse(cs.color), bg=bgOf(el);
    const L1=lum(fg),L2=lum(bg); const ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    colors.add(cs.color);
    const large=fs>=24||(fs>=18.66&&fw>=700); if(ratio<(large?3:4.5)) low.push({sel:el.className||el.tagName, ratio:+ratio.toFixed(2), text:t.textContent.trim().slice(0,20)});
  }
  g.lowContrast=low.slice(0,10); g.lowContrastN=low.length;
  // 본문 크기·줄 간격
  const bodySel='.it-s,.lead-s,.ts,.ov,.pt-x,.cc dd,.cb dd,.rp-w,.intro-p';
  const bad=[]; for(const el of document.querySelectorAll(bodySel)){ if(el.closest('details:not([open])') && !el.closest('summary')) continue; const cs=getComputedStyle(el); const fs=parseFloat(cs.fontSize); const lh=parseFloat(cs.lineHeight)/fs; if(fs<16||lh<1.5) bad.push({sel:el.className, fs, lh:+lh.toFixed(2)});}
  g.bodyTextBad=bad.slice(0,5); g.bodyTextBadN=bad.length;
  // 줄바꿈: 단어 중간 끊김(형광 / 본문 전체)
  function midBreaks(root){
    const res=[]; const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT); const chars=[];
    while(w.nextNode()){const n=w.currentNode; if(n.parentElement.closest('.tip')) continue; for(let i=0;i<n.textContent.length;i++){const r=document.createRange(); r.setStart(n,i); r.setEnd(n,i+1); const rc=r.getClientRects()[0]; chars.push({ch:n.textContent[i], top: rc&&rc.width>0? Math.round(rc.top):null});}}
    let last=-1;
    for(let i=0;i<chars.length;i++){ if(chars[i].top===null) continue; if(last>=0 && chars[i].top>chars[last].top+4){
        let gap=false; for(let j=last+1;j<i;j++) if(/\s/.test(chars[j].ch)) gap=true;
        const a=chars[last].ch, b=chars[i].ch;
        if(!gap && !/\s/.test(a) && !/\s/.test(b) && !/[\-\/,.)\]·]/.test(a) && !/[(\[]/.test(b)) res.push(chars.slice(Math.max(0,last-3),last+1).map(c=>c.ch).join('')+'|'+chars.slice(i,i+3).map(c=>c.ch).join(''));
      } last=i; }
    return res;
  }
  const hlb=[]; for(const m of document.querySelectorAll('mark.hl')){ if(m.closest('details:not([open])') && !m.closest('summary')) continue; hlb.push(...midBreaks(m)); }
  g.hlMidBreaks=hlb;
  let bodyBreaks=[]; for(const el of document.querySelectorAll(bodySel)){ if(el.closest('details:not([open])') && !el.closest('summary')) continue; bodyBreaks.push(...midBreaks(el)); }
  g.bodyMidBreaks=bodyBreaks.length; g.bodyMidSample=bodyBreaks.slice(0,6);
  // 핵심 포인트 시작
  const pt=document.querySelector('.sec-pt'); g.pointsTop = pt? Math.round(pt.getBoundingClientRect().top + window.scrollY) : null;
  // 인용 터치
  const small=[]; for(const a of document.querySelectorAll('a.ref')){ if(a.closest('details:not([open])') && !a.closest('summary')) continue; const r=a.getBoundingClientRect(); if(r.width<24||r.height<24) small.push([Math.round(r.width),Math.round(r.height)]); }
  g.smallRefs=small.length;
  // 색 토큰
  const used=new Set(); for(const el of document.querySelectorAll('body, body *')){ const cs=getComputedStyle(el); for(const p of ['color','backgroundColor','borderTopColor','borderBottomColor','borderLeftColor']){ const v=cs[p]; if(v && v!=='rgba(0, 0, 0, 0)' && !(p.startsWith('border') && cs[p.replace('Color','Width')]==='0px')) used.add(v);} }
  g.colorsUsed=[...used]; g.colorsOff=[...used].filter(c=>!tokens.includes(c));
  // 글꼴
  g.fonts = declared.map(f=>[f, [...document.fonts].some(ff=>ff.family.replace(/["']/g,'')===f && ff.status==='loaded')]);
  // 제목 구조, title 속성
  const hs=[...document.querySelectorAll('h1,h2,h3,h4')].filter(h=>!h.closest('details:not([open])')||h.closest('summary')).map(h=>+h.tagName[1]); let skip=0; for(let i=1;i<hs.length;i++) if(hs[i]>hs[i-1]+1) skip++;
  g.headingSkips=skip; g.h1=hs.filter(x=>x===1).length;
  g.titleAttrs=document.querySelectorAll('[title]:not(link)').length;
  g.height=document.documentElement.scrollHeight;
  return g;
}
"""


def hex2rgb(h):
    h = h.lstrip("#")
    return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"


def tokens_of(css):
    import re
    hexes = set(re.findall(r"#[0-9a-fA-F]{6}\b", css))
    return [hex2rgb(h) for h in hexes] + ["rgb(255, 255, 255)", "rgb(0, 0, 0)"]


FONT_PORT = [0]
FAMS = {"plex": "IBM Plex Sans KR", "noto": "Noto Sans KR", "serif": "Noto Serif KR"}


def main(ids):
    for sid in ids:
        render.build(sid, V[sid])
    s1 = serve(OUT, 0)
    s2 = serve(FONTROOT, 0)
    FONT_PORT[0] = s2.server_address[1]
    SITE = s1.server_address[1]
    gates = {}
    gp = OUT / "gates.json"
    if gp.exists():
        gates = json.loads(gp.read_text())
    with sync_playwright() as p:
        br = p.chromium.launch()
        for sid in ids:
            o = V[sid]
            (OUT / sid / "shots").mkdir(exist_ok=True)
            toks = tokens_of(o["css"])
            declared = [FAMS[f] for f in o["fonts"]]
            res = {}
            for vw, vh in ((375, 812), (768, 1024), (1280, 900)):
                ctx = br.new_context(viewport={"width": vw, "height": vh}, is_mobile=vw < 500, has_touch=vw < 500)

                def route(r):
                    u = r.request.url
                    if "fonts.googleapis.com" in u:
                        r.fulfill(status=200, content_type="text/css", body=font_css(u))
                    elif "fonts.gstatic.com" in u:
                        r.abort()
                    else:
                        r.continue_()

                ctx.route("**/*", route)
                pg = ctx.new_page()
                for name in ["home"] + [f"topic-{t}" for t in render.TOPIC_PAGES]:
                    pg.goto(f"http://127.0.0.1:{SITE}/{sid}/{name}.html", wait_until="networkidle")
                    pg.evaluate("document.fonts.ready")
                    pg.wait_for_timeout(150)
                    if vw == 375 or name in ("home", "topic-w40-jev-race"):
                        pg.screenshot(path=str(OUT / sid / "shots" / f"{name}_{vw}.png"), full_page=True)
                    res[f"{name}_{vw}"] = pg.evaluate(GATE_JS, [declared, toks])
                ctx.close()
            gates[sid] = res
            # 요약
            def g(k, key):
                return res[k][key]
            summary = {
                "overflow": max(v["overflow"] for v in res.values()),
                "lowContrast": sum(v["lowContrastN"] for v in res.values()),
                "bodyTextBad": sum(v["bodyTextBadN"] for v in res.values()),
                "hlMidBreaks": sum(len(v["hlMidBreaks"]) for v in res.values()),
                "pointsTop375": g("topic-w40-jev-race_375", "pointsTop"),
                "smallRefs": sum(v["smallRefs"] for v in res.values()),
                "colorsOff": sorted({c for v in res.values() for c in v["colorsOff"]}),
                "fonts": res["home_375"]["fonts"],
                "headingSkips": sum(v["headingSkips"] for v in res.values()),
                "titleAttrs": sum(v["titleAttrs"] for v in res.values()),
                "bodyMidBreaks375": sum(v["bodyMidBreaks"] for k, v in res.items() if k.endswith("_375")),
                "homeH375": g("home_375", "height"), "topicH375": g("topic-w40-jev-race_375", "height"),
            }
            gates[sid]["_summary"] = summary
            print(sid, json.dumps(summary, ensure_ascii=False))
        br.close()
    gp.write_text(json.dumps(gates, ensure_ascii=False, indent=1))
    s1.shutdown(); s2.shutdown(); s1.server_close(); s2.server_close()


if __name__ == "__main__":
    main(sys.argv[1:] or list(V))
