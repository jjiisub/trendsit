// 관문 9 측정 + 동작 검사(S6a). check.py가 부른다. 사이트에는 나가지 않음(측정 전용).
// 사용: node gate.js <playwright-core 경로> <기준 URL> <페이지 JSON: [{name, path, topic}]> <tokens.css>
// 출력(stdout): JSON {gates: [...], touch: {...}, behavior: {...}, external: [...]}. 판정은 check.py가 한다.
const fs = require('fs');
const pw = require(process.argv[2]);
const base = process.argv[3];
const pages = JSON.parse(process.argv[4]);
const tokenCss = fs.readFileSync(process.argv[5], 'utf8');

const hex2rgb = (h) => `rgb(${parseInt(h.slice(1, 3), 16)}, ${parseInt(h.slice(3, 5), 16)}, ${parseInt(h.slice(5, 7), 16)})`;
const TOKENS = [...new Set(tokenCss.match(/--c-[a-z-]+:\s*#[0-9a-fA-F]{6}/g).map((s) => hex2rgb(s.slice(s.indexOf('#')))))];
const WEIGHTS = ['400', '500'];

// 관문 9의 9항목 측정(drafts/shoot.py의 GATE_JS, 이 사이트의 토큰·클래스에 맞게). 브라우저 안에서 실행
async function gateInBrowser([weights, tokens]) {
  const vw = document.documentElement.clientWidth;
  const g = {};
  g.overflow = document.documentElement.scrollWidth - vw;
  const parse = (c) => { const m = c.match(/[\d.]+/g); return m ? m.map(Number) : null; };
  const lum = (rgb) => { const a = rgb.slice(0, 3).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2]; };
  const bgOf = (el) => { while (el) { const c = parse(getComputedStyle(el).backgroundColor); if (c && (c.length < 4 || c[3] > 0.5)) return c; el = el.parentElement; } return [255, 255, 255]; };
  const low = [];
  const wt = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (wt.nextNode()) {
    const t = wt.currentNode;
    if (!t.textContent.trim()) continue;
    const el = t.parentElement;
    if (seen.has(el)) continue;
    seen.add(el);
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (r.width === 0 || cs.visibility === 'hidden' || el.closest('.sr, .tip')) continue;
    const fs = parseFloat(cs.fontSize);
    const fw = parseInt(cs.fontWeight);
    const L1 = lum(parse(cs.color));
    const L2 = lum(bgOf(el));
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const large = fs >= 24 || (fs >= 18.66 && fw >= 700);
    if (ratio < (large ? 3 : 4.5)) low.push({ sel: el.className || el.tagName, ratio: +ratio.toFixed(2), text: t.textContent.trim().slice(0, 20) });
  }
  g.lowContrast = low.slice(0, 10);
  g.lowContrastN = low.length;
  const bodySel = '.it-s, .ts, .dp, .rp-w';
  const bad = [];
  for (const el of document.querySelectorAll(bodySel)) {
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    const lh = parseFloat(cs.lineHeight) / fs;
    if (fs < 16 || lh < 1.5) bad.push({ sel: el.className, fs, lh: +lh.toFixed(2) });
  }
  g.bodyTextBadN = bad.length;
  g.bodyTextBad = bad.slice(0, 5);
  // 형광 구절이 단어 중간에서 끊긴 곳
  const midBreaks = (root) => {
    const res = [];
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const chars = [];
    while (w.nextNode()) {
      const n = w.currentNode;
      if (n.parentElement.closest('.tip')) continue;
      for (let i = 0; i < n.textContent.length; i++) {
        const r = document.createRange();
        r.setStart(n, i);
        r.setEnd(n, i + 1);
        const rc = r.getClientRects()[0];
        chars.push({ ch: n.textContent[i], top: rc && rc.width > 0 ? Math.round(rc.top) : null });
      }
    }
    let last = -1;
    for (let i = 0; i < chars.length; i++) {
      if (chars[i].top === null) continue;
      if (last >= 0 && chars[i].top > chars[last].top + 4) {
        let gap = false;
        for (let j = last + 1; j < i; j++) if (/\s/.test(chars[j].ch)) gap = true;
        const a = chars[last].ch;
        const b = chars[i].ch;
        if (!gap && !/\s/.test(a) && !/\s/.test(b) && !/[\-\/,.)\]·]/.test(a) && !/[(\[]/.test(b)) {
          res.push(chars.slice(Math.max(0, last - 3), last + 1).map((c) => c.ch).join('') + '|' + chars.slice(i, i + 3).map((c) => c.ch).join(''));
        }
      }
      last = i;
    }
    return res;
  };
  g.hlMidBreaks = [];
  for (const m of document.querySelectorAll('mark.hl')) g.hlMidBreaks.push(...midBreaks(m));
  const pt = document.querySelector('.tiles, .dsec');  // v1.3: 본문 시작 = 머리 타일 또는 첫 절(문서 순서 첫 것)
  g.pointsTop = pt ? Math.round(pt.getBoundingClientRect().top + window.scrollY) : null;
  const small = [];
  for (const a of document.querySelectorAll('a.ref')) {
    const r = a.getBoundingClientRect();
    if (r.width < 24 || r.height < 24) small.push([Math.round(r.width), Math.round(r.height)]);
  }
  g.smallRefs = small.length;
  const used = new Set();
  for (const el of document.querySelectorAll('body, body *')) {
    const cs = getComputedStyle(el);
    for (const p of ['color', 'backgroundColor', 'borderTopColor', 'borderRightColor', 'borderBottomColor', 'borderLeftColor', 'outlineColor', 'textDecorationColor']) {
      const v = cs[p];
      if (!v || v === 'rgba(0, 0, 0, 0)') continue;
      if (p.startsWith('border') && cs[p.replace('Color', 'Width')] === '0px') continue;
      if (p === 'outlineColor' && (cs.outlineStyle === 'none' || cs.outlineWidth === '0px')) continue;
      if (p === 'textDecorationColor' && cs.textDecorationLine === 'none') continue;
      used.add(v);
    }
    // box-shadow 색(밑줄 역할). 검정 + 투명도(툴팁 그림자)는 색이 아니라 깊이 표현이라 뺀다
    for (const m of (cs.boxShadow === 'none' ? [] : cs.boxShadow.match(/rgba?\([^)]*\)/g) || [])) if (!/^rgba\(0, 0, 0, [\d.]+\)$/.test(m)) used.add(m);
  }
  g.colorsOff = [...used].filter((c) => !tokens.includes(c));
  g.fonts = weights.map((w) => [w, [...document.fonts].some((ff) => ff.family.replace(/["']/g, '') === 'Pretendard' && String(ff.weight) === w && ff.status === 'loaded')]);
  const hs = [...document.querySelectorAll('h1, h2, h3, h4')].map((h) => +h.tagName[1]);
  let skip = 0;
  for (let i = 1; i < hs.length; i++) if (hs[i] > hs[i - 1] + 1) skip++;
  g.headingSkips = skip + (hs[0] === 1 ? 0 : 1);
  g.titleAttrs = document.querySelectorAll('[title]:not(link)').length;
  // S6-1 5.9: 표는 자신만 가로로 스크롤(overflow-x), 이미지는 로드됨, 375에서 타일 글자 안 잘림
  g.cmptOverflowBad = [...document.querySelectorAll('.cmpt-wrap')].filter((el) => !['auto', 'scroll'].includes(getComputedStyle(el).overflowX)).length;
  // 006-C1-15: loading="lazy"인 슬라이드 img는 화면 밖이면 아직 요청 전이라 complete가 false라 위 판정에서 늘 빠진다.
  // 화면으로 스크롤해 decode()까지 기다린 뒤에 봐야 실제 로드 실패를 잡는다
  for (const img of document.querySelectorAll('img')) {
    if (!img.complete) {
      img.scrollIntoView();
      await img.decode().catch(() => {});
    }
  }
  g.imgBad = [...document.querySelectorAll('img')].filter((img) => img.complete && img.naturalWidth === 0).length;
  // S7a: 1024 이상에서 run 표 셀(③ steps 줄의 긴 결과 칸 제외)은 한 줄(줄 높이 × 1.5 이하)
  g.rtWrapBad = [...document.querySelectorAll('.rt tbody tr:not(.rt-day):not(.tr-steps) td')].filter((td) => {
    const cs = getComputedStyle(td);
    return vw >= 1024 && td.scrollHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom) > parseFloat(cs.lineHeight) * 1.5;
  }).length;
  g.tileOverflowBad = [...document.querySelectorAll('.tiles .tile-v, .tiles .tile-l, .tiles .tile-s')].filter((el) => el.scrollWidth > el.clientWidth + 1).length;
  return g;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const tipOn = (page, idx) => page.evaluate((i) => { const t = document.querySelectorAll('.cite > .tip')[i]; const cs = getComputedStyle(t); return cs.visibility === 'visible' && parseFloat(cs.opacity) > 0.5; }, idx);

async function open(ctx, path, external) {
  const page = await ctx.newPage();
  page.on('request', (r) => { if (!r.url().startsWith(base) && !r.url().startsWith('data:')) external.push(r.url()); });
  await page.goto(base + path, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(100);
  return page;
}

async function gates(browser, name, viewports, out, external) {
  for (const [w, h, mobile] of viewports) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: mobile, hasTouch: mobile });
    for (const p of pages) {
      const page = await open(ctx, p.path, external);
      out.push({ browser: name, vw: w, page: p.name, topic: !!p.topic, gate: await page.evaluate(gateInBrowser, [WEIGHTS, TOKENS]) });
      await page.close();
    }
    await ctx.close();
  }
}

async function touch(browser, topicPath) {
  const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  await page.goto(base + topicPath, { waitUntil: 'networkidle' });
  const first = page.locator('.dp a.ref').first();
  const href = await first.getAttribute('href');
  await first.tap();
  await page.waitForTimeout(200);
  const res = await page.evaluate((h) => ({ hash: location.hash, target: !!document.querySelector(h) && document.querySelector(h).classList.contains('src') }), href);
  await ctx.close();
  return { href, ...res };
}

async function behavior(browser, longTopic, homePath) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const b = {};
  let page = await ctx.newPage();
  await page.goto(base + longTopic, { waitUntil: 'networkidle' });
  const nCites = await page.locator('.cite > .tip').count();
  b.cites = nCites;
  if (nCites >= 2) {
    // 화면 안에 함께 보이는 인용 번호들(마우스가 정확히 올라간 시각부터 재려고 좌표로 움직임)
    await page.evaluate(() => { const r = document.querySelector('.dp .cite > .ref').getBoundingClientRect(); window.scrollTo(0, window.scrollY + r.top - 150); });
    await sleep(100);
    const pos = await page.evaluate(() => [...document.querySelectorAll('.cite > .ref')].map((a, i) => { const r = a.getBoundingClientRect(); return { i, x: r.x + r.width / 2, y: r.y + r.height / 2, ok: r.top > 0 && r.bottom < innerHeight }; }).filter((p) => p.ok));
    const A = pos[0];
    await page.mouse.move(2, 2);
    await sleep(300);
    await page.mouse.move(A.x, A.y);
    await sleep(60);
    b.early = await tipOn(page, A.i); // 0.15초 전에는 숨김
    await sleep(340);
    b.shown = await tipOn(page, A.i);
    const rect = await page.evaluate((i) => { const r = document.querySelectorAll('.cite > .tip')[i].getBoundingClientRect(); return { l: r.left - 8, r: r.right + 8, t: r.top - 8, b: r.bottom + 8 }; }, A.i);
    const B = pos.find((p) => p.i !== A.i && !(p.x > rect.l && p.x < rect.r && p.y > rect.t && p.y < rect.b));
    await page.mouse.move(2, 2);
    await sleep(300);
    b.lingers = await tipOn(page, A.i); // 벗어나도 0.6초 유지
    await sleep(800);
    b.closed = !(await tipOn(page, A.i)); // 1초 뒤 닫힘
    if (B) {
      await page.mouse.move(A.x, A.y);
      await sleep(400);
      await page.mouse.move(B.x, B.y);
      await sleep(400);
      b.expectOnly = B.i;
      b.only = await page.evaluate(() => [...document.querySelectorAll('.cite > .tip')].map((t, i) => { const cs = getComputedStyle(t); return cs.visibility === 'visible' && parseFloat(cs.opacity) > 0.5 ? i : -1; }).filter((i) => i >= 0));
    }
  }
  await page.close();
  // 탭: 기본은 토픽, #repos면 레포
  const panel = (pg) => pg.evaluate(() => ({ topics: getComputedStyle(document.querySelector('#panel-topics')).visibility, repos: getComputedStyle(document.querySelector('#panel-repos')).visibility }));
  page = await ctx.newPage();
  await page.goto(base + homePath, { waitUntil: 'networkidle' });
  b.tabDefault = await panel(page);
  await page.goto(base + homePath + '#repos', { waitUntil: 'networkidle' });
  b.tabRepos = await panel(page);
  await page.goto(base + homePath, { waitUntil: 'networkidle' });
  await page.click('.tb-r');
  b.tabClick = await panel(page);
  await ctx.close();
  return b;
}

// 미니 바(PC 상세, S6a): 맨 위에서는 숨김, 제목이 위로 빠지면 보임. 독립된 새 컨텍스트·새 페이지에서 바로
// 스크롤해 측정한다(behavior()의 툴팁 측정에서 이미 스크롤·마우스 조작을 거친 같은 페이지로 재 측정하면
// animation-timeline:view()의 진행도 계산이 그 이전 scrollTo들의 영향을 받아 가끔 틀어짐, O01).
async function miniBar(browser, longTopic) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(base + longTopic, { waitUntil: 'networkidle' });
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(150);
  const miniTop = await page.evaluate(() => { const m = document.querySelector('.mini'); return m ? getComputedStyle(m).visibility : null; });
  await page.evaluate(() => window.scrollTo(0, 1400));
  await sleep(300);
  const miniScrolled = await page.evaluate(() => { const m = document.querySelector('.mini'); if (!m) return null; const r = m.getBoundingClientRect(); return { visibility: getComputedStyle(m).visibility, top: Math.round(r.top), height: Math.round(r.height), scrollY: Math.round(window.scrollY) }; });
  await ctx.close();
  return { miniTop, miniScrolled };
}

// D-1·D-40·C-10: 두 탭을 실제로 눌렀을 때 스크롤 위치가 거의 같고(.tabs 바로 위 0높이 앵커) .nav가 가려지지 않음.
// behavior()와 독립된 컨텍스트에서(같은 컨텍스트를 더 오래 잡고 있으면 미니 바 view-timeline 측정에 영향이 있었음)
async function tabAnchorScroll(browser, homePath, viewport) {
  const ctx = await browser.newContext({ viewport, isMobile: viewport.width < 768, hasTouch: viewport.width < 768 });
  const page = await ctx.newPage();
  const scrollState = () => ({ y: Math.round(window.scrollY), navTop: Math.round(document.querySelector('.nav').getBoundingClientRect().top) });
  await page.goto(base + homePath, { waitUntil: 'networkidle' });
  await page.click('.tb-t');
  await sleep(50);
  const topics = await page.evaluate(scrollState);
  await page.click('.tb-r');
  await sleep(50);
  const repos = await page.evaluate(scrollState);
  await ctx.close();
  return { topics, repos, diff: Math.abs(topics.y - repos.y) };
}

(async () => {
  const out = { gates: [], external: [] };
  const chromium = await pw.chromium.launch();
  await gates(chromium, 'chromium', [[375, 812, true], [768, 1024, false], [1280, 900, false]], out.gates, out.external);
  const longTopic = (pages.find((p) => p.longTopic) || pages.find((p) => p.topic)).path;
  out.behavior = await behavior(chromium, longTopic, pages[0].path);
  out.behavior.tabScroll = await tabAnchorScroll(chromium, pages[0].path, { width: 1280, height: 900 });
  Object.assign(out.behavior, await miniBar(chromium, longTopic));
  await chromium.close();
  const webkit = await pw.webkit.launch();
  await gates(webkit, 'webkit', [[375, 812, true], [1280, 900, false]], out.gates, out.external);
  out.touch = await touch(webkit, pages.find((p) => p.topic).path);
  out.tabScrollMobile = await tabAnchorScroll(webkit, pages[0].path, { width: 375, height: 812 });
  await webkit.close();
  out.tokens = TOKENS;
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String(e && e.stack || e) + '\n'); process.exit(2); });
