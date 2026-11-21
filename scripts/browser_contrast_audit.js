() => {
  /*
   * browser_contrast_audit.js  -  WCAG 2.2 contrast + UI audit of the LIVE rendered page.
   *
   * ONE self-contained arrow function. It returns a JSON-serialisable report and changes nothing
   * except briefly focusing elements (to read their focus style); focus is restored.
   *   - Playwright MCP :  browser_evaluate  { function: <this whole file> }
   *   - Playwright     :  page.evaluate(<this file's text>)      (see browser_audit.py)
   *   - DevTools       :  paste "(" + file + ")()" in the console
   * Optional: set window.__CA_OPTS = { aaa:true, maxFocus:40, grid:[40,28], maxList:60 } first.
   *
   * Checks: text contrast (effective colors, alpha, opacity, gradients), placeholder text, UI component
   * borders (1.4.11), inline links distinguishable without color (1.4.1), keyboard focus indicator
   * (2.4.7), target size (2.5.8), horizontal scroll / reflow (1.4.10), and an area-weighted color
   * palette of what is actually painted (for the 60-30-10 split).
   * Cannot judge: text over <img>/<video>/canvas/blend-modes (reported as `uncertain`); measure
   * those from a screenshot with screenshot_analyze.py or by eye.
   */
  const OPT = Object.assign({ aaa: false, maxFocus: 40, grid: [48, 30], maxList: 60 }, window.__CA_OPTS || {});

  // ---------- color parsing (any CSS color syntax via canvas) ----------
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const cx = cv.getContext('2d', { willReadFrequently: true });
  const cache = new Map();
  function parseColor(str) {
    if (cache.has(str)) return cache.get(str);
    let out = null;
    const m = str.match(/^rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)(?:\s*[,/]\s*([\d.%]+))?\s*\)$/);
    if (m) {
      let a = m[4] === undefined ? 1 : (m[4].endsWith('%') ? parseFloat(m[4]) / 100 : parseFloat(m[4]));
      out = [Math.round(+m[1]), Math.round(+m[2]), Math.round(+m[3]), a];
    } else {
      try {
        cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = str; cx.fillRect(0, 0, 1, 1);
        const d = cx.getImageData(0, 0, 1, 1).data;
        out = [d[0], d[1], d[2], d[3] / 255];
      } catch (e) { out = null; }
    }
    cache.set(str, out); return out;
  }
  const hex = (c) => '#' + c.slice(0, 3).map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('').toUpperCase();
  const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const lum = (c) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
  const ratio = (a, b) => { const la = lum(a), lb = lum(b); return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); };
  const over = (fg, bg) => { // fg (with alpha) over opaque bg
    const a = fg[3]; return [fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a), 1];
  };

  // ---------- helpers ----------
  const cs = (el, pseudo) => getComputedStyle(el, pseudo || null);
  function cumOpacity(el) { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= parseFloat(cs(e).opacity || 1); return o; }
  function selector(el) {
    const parts = [];
    for (let e = el, n = 0; e && e.nodeType === 1 && n < 4; e = e.parentElement, n++) {
      let s = e.tagName.toLowerCase();
      if (e.id) { parts.unshift(s + '#' + CSS.escape(e.id)); break; }
      const cls = (e.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 2).map(c => '.' + CSS.escape(c)).join('');
      s += cls;
      const sib = e.parentElement ? [...e.parentElement.children].filter(x => x.tagName === e.tagName) : [];
      if (sib.length > 1) s += ':nth-of-type(' + (sib.indexOf(e) + 1) + ')';
      parts.unshift(s);
    }
    return parts.join(' > ');
  }
  function visible(el) {
    const s = cs(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.visibility === 'collapse') return false;
    if (parseFloat(s.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    if (s.clip === 'rect(0px, 0px, 0px, 0px)' || (s.position === 'absolute' && r.width <= 1 && r.height <= 1)) return false;
    return true;
  }
  function gradientStops(str) {
    const out = [], re = /(rgba?\([^)]*\)|hsla?\([^)]*\)|oklch\([^)]*\)|oklab\([^)]*\)|color\([^)]*\)|#[0-9a-fA-F]{3,8})/g;
    let m; while ((m = re.exec(str))) { const c = parseColor(m[1]); if (c) out.push(c); }
    return out;
  }
  /* Effective background layers behind `el`: returns {colors:[opaque rgb...], uncertain:reason|null}
     colors has >1 entry for gradients (worst case is evaluated). */
  function backdrop(el) {
    const chain = []; for (let e = el; e && e.nodeType === 1; e = e.parentElement) chain.push(e);
    let uncertain = null;
    let bases = [[255, 255, 255, 1]];            // canvas default
    const layers = [];                            // top -> bottom
    for (const e of chain) {
      const s = cs(e);
      if (s.backdropFilter && s.backdropFilter !== 'none') uncertain = uncertain || 'backdrop-filter';
      if (s.mixBlendMode && s.mixBlendMode !== 'normal') uncertain = uncertain || 'mix-blend-mode';
      if (s.filter && s.filter !== 'none' && e !== el) uncertain = uncertain || 'filter';
      const bi = s.backgroundImage;
      let imgStops = null;
      if (bi && bi !== 'none') {
        if (/url\(/.test(bi)) { uncertain = uncertain || 'background image'; }
        else if (/gradient/.test(bi)) imgStops = gradientStops(bi);
      }
      const bc = parseColor(s.backgroundColor);
      const o = cumOpacity(e) / (parseFloat(s.opacity) || 1) * 1; // ancestors' opacity above e is handled below
      if (imgStops && imgStops.length) { layers.push({ stops: imgStops }); if (imgStops.every(c => c[3] >= 0.99)) break; }
      if (bc && bc[3] > 0) { layers.push({ stops: [bc] }); if (bc[3] >= 0.99) break; }
      if (e.tagName === 'IMG' || e.tagName === 'VIDEO' || e.tagName === 'CANVAS' || e.tagName === 'PICTURE') uncertain = uncertain || e.tagName.toLowerCase();
    }
    // composite bottom-up for each gradient stop combination (worst case => take each stop independently)
    let results = bases;
    for (let i = layers.length - 1; i >= 0; i--) {
      const next = [];
      for (const base of results) for (const st of layers[i].stops) next.push(over(st, base));
      // cap blow-up: keep extremes only
      results = next.length > 12 ? [next.reduce((a, b) => lum(a) < lum(b) ? a : b), next.reduce((a, b) => lum(a) > lum(b) ? a : b)] : next;
    }
    return { colors: results, uncertain };
  }
  const isLarge = (px, w) => px >= 24 || (px >= 18.66 && w >= 700);

  const textFails = [], textPass = { n: 0 }, uncertain = [], groups = new Map();
  let checked = 0, minRatio = 99;

  function addText(el, fgStr, kind, textSample, pseudo) {
    const s = cs(el, pseudo);
    const px = parseFloat(s.fontSize), w = parseInt(s.fontWeight, 10) || 400;
    const fg0 = parseColor(fgStr); if (!fg0) return;
    const op = cumOpacity(el);
    const fg = [fg0[0], fg0[1], fg0[2], fg0[3] * op];
    const { colors, uncertain: unc } = backdrop(el);
    let worst = 99, worstBg = null;
    for (const bgc of colors) { const f = over(fg, bgc); const r = ratio(f, bgc); if (r < worst) { worst = r; worstBg = bgc; } }
    const large = isLarge(px, w);
    const req = OPT.aaa ? (large ? 4.5 : 7) : (large ? 3 : 4.5);
    checked++;
    if (unc) {
      uncertain.push({ type: kind, selector: selector(el), text: textSample, reason: unc, fg: hex(fg), estRatioOnFlatBg: +worst.toFixed(2) });
      return;
    }
    minRatio = Math.min(minRatio, worst);
    if (worst + 1e-9 >= req) { textPass.n++; return; }
    const key = [kind, hex(fg), hex(worstBg), req, Math.round(px)].join('|');
    const g = groups.get(key);
    if (g) { g.count++; if (g.samples.length < 3) g.samples.push({ selector: selector(el), text: textSample }); }
    else groups.set(key, {
      type: kind, fg: hex(fg), bg: hex(worstBg), ratio: +worst.toFixed(2), required: req,
      size: Math.round(px * 10) / 10, weight: w, large, gradient: colors.length > 1, count: 1,
      samples: [{ selector: selector(el), text: textSample }],
      suggest: `python3 contrast_check.py fix "${hex(fg)}" "${hex(worstBg)}" --target ${req}`
    });
  }

  // ---------- 1. text (every element that directly owns text) ----------
  const all = [...document.body.querySelectorAll('*')];
  for (const el of all) {
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'SVG', 'PATH'].includes(el.tagName.toUpperCase())) continue;
    const own = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim().length);
    if (own.length && visible(el)) {
      const disabled = el.matches(':disabled') || el.getAttribute('aria-disabled') === 'true' || el.closest('[aria-disabled="true"],fieldset:disabled');
      if (!disabled) addText(el, cs(el).color, 'text', own[0].textContent.trim().slice(0, 50));
    }
    if ((el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && el.getAttribute('placeholder') && visible(el)) {
      addText(el, cs(el, '::placeholder').color, 'placeholder', el.getAttribute('placeholder').slice(0, 50), '::placeholder');
    }
  }

  // ---------- 2. UI components (1.4.11) + links (1.4.1) + target size (2.5.8) ----------
  const ui = [], links = [], targets = { below24: [], below44: 0, total: 0 };
  const interactive = all.filter(e => e.matches('a[href],button,input:not([type=hidden]),select,textarea,[role=button],[role=checkbox],[role=switch],[tabindex]:not([tabindex="-1"])') && visible(e));
  for (const el of interactive) {
    const s = cs(el), r = el.getBoundingClientRect();
    targets.total++;
    const inlineLink = el.tagName === 'A' && s.display === 'inline';
    if (!inlineLink && (r.width < 24 || r.height < 24)) targets.below24.push({ selector: selector(el), size: Math.round(r.width) + 'x' + Math.round(r.height) });
    else if (!inlineLink && (r.width < 44 || r.height < 44)) targets.below44++;
    if (el.matches('input:not([type=checkbox]):not([type=radio]),select,textarea,button')) {
      const par = backdrop(el.parentElement || document.body).colors[0];
      const bw = parseFloat(s.borderTopWidth) || 0, bcol = parseColor(s.borderTopColor);
      const fillc = parseColor(s.backgroundColor);
      const cands = [];
      if (bw > 0 && bcol && bcol[3] > 0 && s.borderTopStyle !== 'none') cands.push(ratio(over(bcol, par), par));
      if (fillc && fillc[3] > 0.1) cands.push(ratio(over(fillc, par), par));
      const best = cands.length ? Math.max(...cands) : 1;
      const isField = !(el.tagName === 'BUTTON');
      if (isField && best < 3) ui.push({ selector: selector(el), issue: 'field boundary not visible', ratio: +best.toFixed(2), required: 3, border: bcol ? hex(bcol) : null, against: hex(par) });
    }
    if (inlineLink) {
      const block = el.closest('p,li,dd,td,blockquote');
      if (block && block !== el) {
        const td = s.textDecorationLine || s.textDecoration;
        const lc = parseColor(s.color), tc = parseColor(cs(block).color);
        const bold = parseInt(s.fontWeight, 10) >= 700 && parseInt(cs(block).fontWeight, 10) < 700;
        if (!/underline/.test(td) && !bold && lc && tc) {
          const rr = ratio(lc, tc);
          if (rr < 3) links.push({ selector: selector(el), text: (el.textContent || '').trim().slice(0, 40), linkVsText: +rr.toFixed(2), issue: 'link differs from body text by < 3:1 and has no underline' });
        }
      }
    }
  }

  // ---------- 3. focus indicators (2.4.7) ----------
  const focusIssues = [];
  const prev = document.activeElement;
  const sample = interactive.filter(e => e.tabIndex >= 0 && !e.disabled).slice(0, OPT.maxFocus);
  for (const el of sample) {
    const before = cs(el); const b = [before.outlineStyle, before.outlineWidth, before.outlineColor, before.boxShadow, before.borderTopColor, before.backgroundColor, before.textDecorationLine].join('|');
    try { el.focus({ preventScroll: true }); } catch (e) { continue; }
    const af = cs(el); const a = [af.outlineStyle, af.outlineWidth, af.outlineColor, af.boxShadow, af.borderTopColor, af.backgroundColor, af.textDecorationLine].join('|');
    const outlineVisible = af.outlineStyle !== 'none' && parseFloat(af.outlineWidth) > 0;
    if (b === a && !outlineVisible) focusIssues.push({ selector: selector(el), issue: 'no visible focus change detected (outline none, no style change)' });
    else if (outlineVisible) {
      const oc = parseColor(af.outlineColor), par = backdrop(el).colors[0];
      if (oc && oc[3] > 0) { const rr = ratio(over(oc, par), par); if (rr < 3) focusIssues.push({ selector: selector(el), issue: 'focus outline below 3:1 against its background', ratio: +rr.toFixed(2), outline: hex(oc), against: hex(par) }); }
    }
  }
  try { el_blur(); } catch (e) { }
  function el_blur() { if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur(); if (prev && prev.focus && prev !== document.body) prev.focus({ preventScroll: true }); }

  // ---------- 4. painted palette (area-weighted grid sample of what is on screen) ----------
  const [gx, gy] = OPT.grid, W = innerWidth, H = innerHeight, area = new Map(); let n = 0;
  for (let i = 0; i < gx; i++) for (let j = 0; j < gy; j++) {
    const el = document.elementFromPoint((i + 0.5) * W / gx, (j + 0.5) * H / gy); if (!el) continue;
    const bk = backdrop(el); const c = bk.colors[Math.floor(bk.colors.length / 2)]; const k = hex(c);
    area.set(k, (area.get(k) || 0) + 1); n++;
  }
  const palette = [...area.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10).map(([c, v]) => ({ color: c, areaPct: +(v / n * 100).toFixed(1) }));
  const accentColors = {};
  for (const el of interactive.slice(0, 120)) { const s = cs(el); const c = parseColor(s.backgroundColor); const t = parseColor(s.color); if (c && c[3] > 0.5) accentColors['fill ' + hex(c)] = (accentColors['fill ' + hex(c)] || 0) + 1; else if (t && el.tagName === 'A') accentColors['link ' + hex(t)] = (accentColors['link ' + hex(t)] || 0) + 1; }

  // ---------- assemble ----------
  const textFailList = [...groups.values()].sort((a, b) => a.ratio - b.ratio);
  const cap = (a) => a.slice(0, OPT.maxList);
  const totalFailNodes = textFailList.reduce((s, g) => s + g.count, 0);
  return {
    meta: {
      url: location.href, title: document.title, lang: document.documentElement.lang || null,
      viewport: [innerWidth, innerHeight], prefersDark: matchMedia('(prefers-color-scheme: dark)').matches,
      level: OPT.aaa ? 'AAA' : 'AA', hScroll: document.documentElement.scrollWidth > innerWidth + 1,
      scrollWidth: document.documentElement.scrollWidth
    },
    summary: {
      textChecked: checked, textPass: textPass.n, textFailNodes: totalFailNodes, textFailGroups: textFailList.length,
      uncertain: uncertain.length, lowestRatio: minRatio === 99 ? null : +minRatio.toFixed(2),
      uiFailures: ui.length, linkIssues: links.length, focusIssues: focusIssues.length,
      targetsBelow24: targets.below24.length, targetsBelow44: targets.below44, interactive: targets.total
    },
    textFailures: cap(textFailList),
    uncertain: cap(uncertain),
    uiComponents: cap(ui),
    links: cap(links),
    focus: cap(focusIssues),
    targets: { below24: cap(targets.below24), below44Count: targets.below44, total: targets.total },
    palette: { painted: palette, interactiveColors: accentColors }
  };
}
