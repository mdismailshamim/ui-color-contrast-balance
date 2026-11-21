#!/usr/bin/env python3
"""
contrast_check.py - WCAG 2.x contrast + 60-30-10 audit helper.

Stdlib only (Pillow optional, only for the `ratio` command).

Commands
  pair  FG BG                 Contrast ratio + AA/AAA verdicts for one pair
  fix   FG BG [--target 4.5]  Nudge FG lightness until it reaches the target ratio
  check FILE.json             Audit many pairs / a role palette (see below)
  ratio IMAGE.png             Estimate 60-30-10 area split of a screenshot

Colors: #RGB, #RRGGBB or #RRGGBBAA (alpha is blended over BG).

`check` accepts either:
  {"pairs":[{"name":"Body","fg":"#111","bg":"#fff","kind":"text"}]}   kind: text|large|ui|text-aaa
or a role palette (auto-builds the standard pairs):
  {"bg":"#F8FAFC","surface":"#FFFFFF","text":"#0F172A","muted":"#475569",
   "accent":"#1D4ED8","on-accent":"#FFFFFF","border":"#64748B","focus":"#1D4ED8",
   "error":"#B91C1C","success":"#15803D","warning":"#92400E"}

Exit code 1 if any required pair fails, so it can gate CI / a review step.
"""
import argparse
import colorsys
import json
import sys


# ---------- core maths (WCAG 2.2 relative luminance / contrast ratio) ----------
def parse_hex(h):
    h = h.strip().lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        raise ValueError(f"bad color: {h!r}")
    rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    alpha = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return rgb, alpha


def blend(fg, alpha, bg):
    return tuple(round(alpha * f + (1 - alpha) * b) for f, b in zip(fg, bg))


def lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = luminance(a), luminance(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def resolve(fg_s, bg_s):
    bg, _ = parse_hex(bg_s)
    fg, a = parse_hex(fg_s)
    return blend(fg, a, bg) if a < 1 else fg, bg


def levels(r):
    return {
        "text AA (4.5)": r >= 4.5,
        "large text AA (3.0)": r >= 3.0,
        "UI/graphics AA (3.0)": r >= 3.0,
        "text AAA (7.0)": r >= 7.0,
        "large text AAA (4.5)": r >= 4.5,
    }


def mark(ok):
    return "PASS" if ok else "FAIL"


# ---------- commands ----------
def cmd_pair(args):
    fg, bg = resolve(args.fg, args.bg)
    r = ratio(fg, bg)
    print(f"{to_hex(fg)} on {to_hex(bg)}  ->  {r:.2f}:1")
    for k, v in levels(r).items():
        print(f"  {mark(v):4}  {k}")
    return 0


def cmd_fix(args):
    fg, bg = resolve(args.fg, args.bg)
    if ratio(fg, bg) >= args.target:
        print(f"already {ratio(fg, bg):.2f}:1 - no change: {to_hex(fg)}")
        return 0
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in fg))
    go_darker = luminance(bg) > 0.18  # light bg -> darken text, dark bg -> lighten
    step = -0.005 if go_darker else 0.005
    for _ in range(400):
        l = min(1.0, max(0.0, l + step))
        cand = tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, l, s))
        if ratio(cand, bg) >= args.target:
            print(f"{to_hex(fg)} -> {to_hex(cand)}  ({ratio(cand, bg):.2f}:1 on {to_hex(bg)}, target {args.target})")
            return 0
    print("could not reach target by lightness alone - change hue/background", file=sys.stderr)
    return 1


STANDARD_PAIRS = [
    # name, fg role, bg role, kind
    ("Body text on page", "text", "bg", "text"),
    ("Body text on surface", "text", "surface", "text"),
    ("Muted text on page", "muted", "bg", "text"),
    ("Muted text on surface", "muted", "surface", "text"),
    ("Accent as text/link on page", "accent", "bg", "text"),
    ("Accent as UI (icon/outline) on page", "accent", "bg", "ui"),
    ("Label on accent button", "on-accent", "accent", "text"),
    ("Input/control border on surface", "border", "surface", "ui"),
    ("Focus ring on page", "focus", "bg", "ui"),
    ("Focus ring on surface", "focus", "surface", "ui"),
    ("Error text on page", "error", "bg", "text"),
    ("Success text on page", "success", "bg", "text"),
    ("Warning text on page", "warning", "bg", "text"),
]
NEED = {"text": 4.5, "large": 3.0, "ui": 3.0, "text-aaa": 7.0}


def cmd_check(args):
    data = json.load(open(args.file))
    pairs = data.get("pairs")
    if pairs is None:  # role palette
        pairs = [
            {"name": n, "fg": data[f], "bg": data[b], "kind": k}
            for n, f, b, k in STANDARD_PAIRS
            if f in data and b in data
        ]
    fails = 0
    print(f"{'Pair':38} {'FG':8} {'BG':8} {'Ratio':>7}  Need  AA    AAA")
    print("-" * 86)
    for p in pairs:
        fg, bg = resolve(p["fg"], p["bg"])
        r = ratio(fg, bg)
        kind = p.get("kind", "text")
        need = NEED[kind]
        ok = r >= need
        aaa = None if kind == "ui" else r >= (4.5 if kind == "large" else 7.0)
        fails += 0 if ok else 1
        aaa_s = "n/a " if aaa is None else mark(aaa)
        print(f"{p['name'][:38]:38} {to_hex(fg):8} {to_hex(bg):8} {r:6.2f}:1  {need:<4}  {mark(ok):5} {aaa_s}")
    print("-" * 86)
    print("RESULT:", "ALL REQUIRED PAIRS PASS AA" if not fails else f"{fails} pair(s) FAIL AA")
    return 1 if fails else 0


def cmd_ratio(args):
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed: pip install pillow --break-system-packages", file=sys.stderr)
        return 2
    im = Image.open(args.image).convert("RGB")
    im.thumbnail((400, 400))
    q = im.quantize(colors=args.colors, method=Image.Quantize.MEDIANCUT).convert("RGB")
    total = q.width * q.height
    counts = sorted(q.getcolors(total), reverse=True)
    rows, cum = [], 0.0
    for n, rgb in counts:
        share = n / total * 100
        h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
        rows.append((share, rgb, s, l))
    dom = sec = acc = 0.0
    for share, rgb, s, l in rows:
        if cum < 55:
            dom += share
        elif cum < 88:
            sec += share
        else:
            acc += share
        cum += share
    print("Top colors (area share)")
    for share, rgb, s, l in rows[:8]:
        print(f"  {to_hex(rgb)}  {share:5.1f}%")
    print(f"\nEstimated split  dominant {dom:.0f}% | secondary {sec:.0f}% | accent {acc:.0f}%   (target ~60/30/10)")
    ok = 50 <= dom <= 72 and 18 <= sec <= 40 and 3 <= acc <= 16
    print("Heuristic verdict:", "within tolerance" if ok else "outside tolerance - inspect by eye; this is a rough estimate")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pair"); p.add_argument("fg"); p.add_argument("bg"); p.set_defaults(fn=cmd_pair)
    p = sub.add_parser("fix"); p.add_argument("fg"); p.add_argument("bg"); p.add_argument("--target", type=float, default=4.5); p.set_defaults(fn=cmd_fix)
    p = sub.add_parser("check"); p.add_argument("file"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("ratio"); p.add_argument("image"); p.add_argument("--colors", type=int, default=12); p.set_defaults(fn=cmd_ratio)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
