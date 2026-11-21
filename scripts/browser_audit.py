#!/usr/bin/env python3
"""
browser_audit.py - run the in-page WCAG audit (browser_contrast_audit.js) on real pages with Playwright.

  python3 browser_audit.py https://example.com
  python3 browser_audit.py http://localhost:3000 /pricing /login --schemes light,dark \
          --viewports 360x800,768x1024,1440x900 --out audit/ --screenshots
  python3 browser_audit.py file:///abs/path/index.html --aaa --fail-on any

Per URL x color-scheme x viewport it: loads the page, waits for network idle, runs the audit, and
saves JSON (+ optional full-page screenshot, ready for screenshot_analyze.py / visual_regression.py).
Writes <out>/report.md and <out>/report.json. Exit code 1 when the chosen --fail-on level is hit.

Setup (once):  pip install playwright && playwright install chromium
Login-protected pages: --storage-state state.json (created with `playwright codegen --save-storage`).
Extra checks: 320px viewport (WCAG 1.4.10 reflow) is added automatically with --reflow.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def slug(s):
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")[:60] or "page"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="+", help="full URLs; paths (/x) are joined to the first full URL")
    ap.add_argument("--schemes", default="light,dark", help="comma list of color schemes (light,dark)")
    ap.add_argument("--viewports", default="390x844,1440x900")
    ap.add_argument("--out", default="audit-out")
    ap.add_argument("--aaa", action="store_true", help="evaluate against AAA instead of AA")
    ap.add_argument("--screenshots", action="store_true", help="save full-page screenshots")
    ap.add_argument("--reflow", action="store_true", help="also check 320px wide (1.4.10)")
    ap.add_argument("--forced-colors", action="store_true", help="also run with forced-colors: active")
    ap.add_argument("--wait", type=int, default=600, help="extra ms to wait after load (animations)")
    ap.add_argument("--storage-state", help="Playwright storage state JSON for authenticated pages")
    ap.add_argument("--fail-on", choices=["text", "any", "never"], default="text",
                    help="text: text-contrast failures only | any: also UI/focus/links/targets | never")
    ap.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("pip install playwright && playwright install chromium")

    base = next((u for u in args.urls if re.match(r"^(https?|file)://", u)), None)
    urls = [u if re.match(r"^(https?|file)://", u) else (base.rstrip("/") + u) for u in args.urls]
    viewports = [tuple(int(x) for x in v.lower().split("x")) for v in args.viewports.split(",")]
    if args.reflow and (320, 640) not in viewports:
        viewports.append((320, 640))
    schemes = [s.strip() for s in args.schemes.split(",") if s.strip()]
    js = open(os.path.join(HERE, "browser_contrast_audit.js"), encoding="utf-8").read()
    os.makedirs(args.out, exist_ok=True)

    runs, worst_text, worst_any = [], 0, 0
    with sync_playwright() as p:
        browser = getattr(p, args.browser).launch()
        for url in urls:
            for scheme in schemes:
                for (w, h) in viewports:
                    ctx_kw = dict(viewport={"width": w, "height": h}, color_scheme=scheme)
                    if args.storage_state:
                        ctx_kw["storage_state"] = args.storage_state
                    ctx = browser.new_context(**ctx_kw)
                    page = ctx.new_page()
                    try:
                        page.goto(url, wait_until="networkidle", timeout=45000)
                    except Exception:
                        page.goto(url, wait_until="load", timeout=45000)
                    page.wait_for_timeout(args.wait)
                    if args.aaa:
                        page.evaluate("window.__CA_OPTS = { aaa: true }")
                    res = page.evaluate(js)
                    name = f"{slug(url)}__{scheme}__{w}x{h}"
                    res["meta"]["scheme"] = scheme
                    json.dump(res, open(os.path.join(args.out, name + ".json"), "w"), indent=2)
                    if args.screenshots:
                        page.screenshot(path=os.path.join(args.out, name + ".png"), full_page=True)
                    s = res["summary"]
                    runs.append({"name": name, "url": url, "scheme": scheme, "viewport": f"{w}x{h}", "summary": s,
                                 "hScroll": res["meta"]["hScroll"], "top": res["textFailures"][:5],
                                 "uncertain": res["uncertain"][:3], "focus": res["focus"][:3],
                                 "ui": res["uiComponents"][:3], "links": res["links"][:3]})
                    worst_text += s["textFailNodes"]
                    worst_any += s["textFailNodes"] + s["uiFailures"] + s["focusIssues"] + s["linkIssues"] + s["targetsBelow24"] + (1 if res["meta"]["hScroll"] and w <= 390 else 0)
                    if args.forced_colors:
                        fc = browser.new_context(viewport={"width": w, "height": h}, forced_colors="active")
                        fp = fc.new_page(); fp.goto(url, wait_until="load"); fp.wait_for_timeout(args.wait)
                        if args.screenshots:
                            fp.screenshot(path=os.path.join(args.out, name + "__forced-colors.png"), full_page=True)
                        fc.close()
                    ctx.close()
        browser.close()

    json.dump(runs, open(os.path.join(args.out, "report.json"), "w"), indent=2)
    L = [f"# Browser contrast audit ({'AAA' if args.aaa else 'AA'})", "",
         "| Page | Scheme | Viewport | Text checked | Text fails | Lowest | UI | Focus | Links | Targets<24 | Uncertain | H-scroll |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in runs:
        s = r["summary"]
        L.append(f"| {r['url'][:48]} | {r['scheme']} | {r['viewport']} | {s['textChecked']} | {s['textFailNodes']} | {s['lowestRatio']} | "
                 f"{s['uiFailures']} | {s['focusIssues']} | {s['linkIssues']} | {s['targetsBelow24']} | {s['uncertain']} | {'YES' if r['hScroll'] else 'no'} |")
    L += ["", "## Top text failures (grouped by identical fg/bg/size)"]
    seen = set()
    for r in runs:
        for g in r["top"]:
            k = (g["fg"], g["bg"], g["required"], r["scheme"])
            if k in seen:
                continue
            seen.add(k)
            L.append(f"- [{r['scheme']} {r['viewport']}] `{g['fg']}` on `{g['bg']}` = **{g['ratio']}:1** (needs {g['required']}), "
                     f"{g['count']} node(s), e.g. `{g['samples'][0]['selector']}` \"{g['samples'][0]['text']}\"  \n  fix: `{g['suggest']}`")
    for title, key, fmt in (("Focus", "focus", lambda x: x["issue"]), ("UI components", "ui", lambda x: f"{x['issue']} ({x['ratio']}:1)"),
                            ("Links", "links", lambda x: x["issue"]), ("Uncertain (judge by eye / screenshot)", "uncertain", lambda x: f"over {x['reason']}")):
        rows = [(r["scheme"], i) for r in runs for i in r[key]]
        if rows:
            L += ["", f"## {title}"]
            done = set()
            for sc, i in rows:
                k = (i["selector"], fmt(i))
                if k in done:
                    continue
                done.add(k)
                L.append(f"- [{sc}] `{i['selector']}` - {fmt(i)}")
    open(os.path.join(args.out, "report.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    bad = worst_text if args.fail_on == "text" else worst_any if args.fail_on == "any" else 0
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
