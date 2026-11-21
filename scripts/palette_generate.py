#!/usr/bin/env python3
"""
palette_generate.py - generate a complete, contrast-verified 60-30-10 palette from ONE brand color.

  python3 palette_generate.py "#2563EB"                       # light + dark, AA, prints table + CSS
  python3 palette_generate.py "#2563EB" --level AAA --format dtcg -o tokens.json
  python3 palette_generate.py "#E11D48" --format tailwind -o tailwind.colors.js
  python3 palette_generate.py "#0EA5E9" --format json -o palette.json   # feeds contrast_check.py check

What it builds (for each mode):
  roles    bg surface surface-alt text muted border divider accent accent-hover accent-text on-accent
           focus error success warning (+ error-bg/success-bg/warning-bg tints)
  scales   brand 50-950 and neutral 50-950 (OKLCH, neutral tinted toward the brand hue)
  chart    6 series colors, each >= 3:1 against bg and surface (still add labels/patterns)
  extras   optional harmony hues (--harmony) for illustration only, NOT for UI chrome

Every text/UI pair is solved against its real backgrounds (not guessed) and re-verified at the end.
The brand color is preserved as the fill whenever it can pass; otherwise lightness moves minimally.
Exit code 1 if any required pair fails (should not happen; it is a self-check).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import (  # noqa: E402
    oklch_hex, parse_hex, ratio, rgb_to_oklch, solve_lightness, to_hex,
)

STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
STEP_L = [0.985, 0.967, 0.923, 0.869, 0.708, 0.556, 0.439, 0.371, 0.269, 0.205, 0.145]
SEM_HUE = {"error": 27, "success": 150, "warning": 65}
WHITE = "#FFFFFF"


def tint_c(base, L):
    """Neutral chroma tapers toward the extremes so near-white/near-black stay calm."""
    edge = min(L, 1 - L)
    return base * min(1.0, edge * 4 + 0.35)


def build_scales(h, brand_c, tint):
    neutral = {s: oklch_hex(L, tint_c(tint, L), h) for s, L in zip(STEPS, STEP_L)}
    brand = {s: oklch_hex(L, brand_c * (0.55 + 0.9 * min(L, 1 - L) * 1.8 if L > 0.9 else 1.0), h)
             for s, L in zip(STEPS, STEP_L)}
    return neutral, brand


def need(level):
    aaa = level == "AAA"
    return {
        "text": 7.0 if aaa else 4.5,   # accent-as-text, label on accent, semantic text
        "body": 12.0,                  # body text always aims high
        "muted": 7.0,                  # secondary text: >= 7 on every surface (skill default)
        "ui": 3.0,                     # borders, focus, icons
    }


def make_mode(mode, h, brand_c, seed_L, tint, level):
    n = need(level)
    r = {}
    if mode == "light":
        r["bg"] = oklch_hex(0.982, tint_c(tint, 0.982), h)
        r["surface"] = oklch_hex(0.998, tint_c(tint, 0.998), h)
        r["surface-alt"] = oklch_hex(0.945, tint_c(tint, 0.945), h)
        text_seed, muted_seed, border_seed = 0.20, 0.42, 0.58
    else:
        r["bg"] = oklch_hex(0.155, tint_c(tint, 0.155) * 1.4, h)
        r["surface"] = oklch_hex(0.205, tint_c(tint, 0.205) * 1.4, h)
        r["surface-alt"] = oklch_hex(0.265, tint_c(tint, 0.265) * 1.4, h)
        text_seed, muted_seed, border_seed = 0.95, 0.76, 0.58
    surfaces = [r["bg"], r["surface"], r["surface-alt"]]
    tc = tint * 0.8

    r["text"] = solve_lightness(h, tc, surfaces, n["body"], text_seed)
    r["muted"] = solve_lightness(h, tc, surfaces, n["muted"], muted_seed)
    r["border"] = solve_lightness(h, tint * 1.2, [r["bg"], r["surface"]], n["ui"], border_seed)
    r["divider"] = oklch_hex(0.90 if mode == "light" else 0.30, tint_c(tint, 0.9), h)  # decorative, exempt

    # ---- accent fill + label: keep brand when possible, move lightness minimally otherwise
    seed = seed_L if mode == "light" else max(seed_L, 0.72)
    c_acc = brand_c if mode == "light" else brand_c * 0.85  # dark mode: desaturate a touch
    dark_label = oklch_hex(0.17, tint * 0.8, h)
    best = None
    for label in (WHITE, dark_label):
        fill = solve_lightness(h, c_acc, [label], n["text"], seed)
        if fill:
            d = abs(rgb_to_oklch(parse_hex(fill)[0])[0] - seed)
            if best is None or d < best[0]:
                best = (d, fill, label)
    r["accent"], r["on-accent"] = best[1], best[2]
    acc_L = rgb_to_oklch(parse_hex(r["accent"])[0])[0]
    # hover: a step darker (light mode) / lighter (dark mode), label still has to pass
    hov_seed = acc_L - 0.06 if mode == "light" else acc_L + 0.06
    r["accent-hover"] = solve_lightness(h, c_acc, [r["on-accent"]], n["text"], hov_seed) or r["accent"]
    # accent as text / link / icon must pass on every surface
    r["accent-text"] = solve_lightness(h, c_acc, surfaces, n["text"], acc_L)
    r["focus"] = solve_lightness(h, c_acc, [r["bg"], r["surface"], r["surface-alt"]], n["ui"], acc_L)

    # ---- semantic (state only; each solved on every surface)
    for name, sh in SEM_HUE.items():
        c = 0.17 if name != "warning" else 0.13
        r[name] = solve_lightness(sh, c, surfaces, n["text"], 0.50 if mode == "light" else 0.78)
        tint_bg = oklch_hex(0.955 if mode == "light" else 0.27, 0.035, sh)
        r[f"{name}-bg"] = tint_bg
    return r


def chart_series(h, bgs, mode):
    out = []
    hues = [h, h + 60, h + 120, h + 180, h + 240, h + 300]
    seeds = [0.52, 0.66, 0.50, 0.68, 0.54, 0.64] if mode == "light" else [0.78, 0.68, 0.80, 0.70, 0.76, 0.66]
    for hh, s in zip(hues, seeds):
        out.append(solve_lightness(hh % 360, 0.14, bgs, 3.0, s))
    return out


def harmony_hues(h, kind):
    return {
        "analogous": [h - 30, h + 30],
        "complementary": [h + 180],
        "triadic": [h + 120, h + 240],
        "split": [h + 150, h + 210],
    }[kind]


# ---------------------------------------------------------------- self check

PAIRS = [
    ("Body text on bg", "text", "bg", 12.0, "text"),
    ("Body text on surface", "text", "surface", 7.0, "text"),
    ("Body text on surface-alt", "text", "surface-alt", 7.0, "text"),
    ("Muted on bg", "muted", "bg", 4.5, "text"),
    ("Muted on surface", "muted", "surface", 4.5, "text"),
    ("Muted on surface-alt", "muted", "surface-alt", 4.5, "text"),
    ("Label on accent", "on-accent", "accent", 4.5, "text"),
    ("Label on accent-hover", "on-accent", "accent-hover", 4.5, "text"),
    ("Accent text on bg", "accent-text", "bg", 4.5, "text"),
    ("Accent text on surface", "accent-text", "surface", 4.5, "text"),
    ("Border on surface", "border", "surface", 3.0, "ui"),
    ("Border on bg", "border", "bg", 3.0, "ui"),
    ("Focus ring on bg", "focus", "bg", 3.0, "ui"),
    ("Focus ring on surface", "focus", "surface", 3.0, "ui"),
    ("Error text on surface", "error", "surface", 4.5, "text"),
    ("Success text on surface", "success", "surface", 4.5, "text"),
    ("Warning text on surface", "warning", "surface", 4.5, "text"),
    ("Error text on error-bg", "error", "error-bg", 4.5, "text"),
    ("Success text on success-bg", "success", "success-bg", 4.5, "text"),
    ("Warning text on warning-bg", "warning", "warning-bg", 4.5, "text"),
]


def verify(roles, level):
    aaa = level == "AAA"
    rows, fails = [], 0
    for name, f, b, req, kind in PAIRS:
        if kind == "text" and aaa and req == 4.5:
            req = 7.0
        r = ratio(parse_hex(roles[f])[0], parse_hex(roles[b])[0])
        ok = r + 1e-9 >= req
        fails += 0 if ok else 1
        rows.append((name, roles[f], roles[b], r, req, ok))
    return rows, fails


# ---------------------------------------------------------------- output formats


def fmt_css(p, args):
    def block(sel, roles):
        lines = [f"  --{k}: {v};" for k, v in roles.items()]
        return f"{sel} {{\n" + "\n".join(lines) + "\n}"

    css = ["/* generated by palette_generate.py - brand {} - target {} */".format(args.brand.upper(), args.level),
           block(":root", p["light"]["roles"])]
    if "dark" in p:
        css.append(block('[data-theme="dark"]', p["dark"]["roles"]))
        css.append("@media (prefers-color-scheme: dark) {\n"
                   + block('  :root:not([data-theme="light"])', p["dark"]["roles"]).replace("\n", "\n  ")
                   + "\n}")
    css.append(":root {\n" + "\n".join(f"  --brand-{s}: {v};" for s, v in p["scales"]["brand"].items()) + "\n"
               + "\n".join(f"  --neutral-{s}: {v};" for s, v in p["scales"]["neutral"].items()) + "\n}")
    return "\n\n".join(css)


def fmt_tailwind(p, args):
    names = list(p["light"]["roles"].keys())
    colors = {n: f"var(--{n})" for n in names}
    body = json.dumps({"brand": p["scales"]["brand"], "neutral": p["scales"]["neutral"], **colors}, indent=2)
    return ("// tailwind.config.js -> theme.extend.colors  (pair with the CSS from --format css)\n"
            "module.exports = " + body + ";\n")


def fmt_dtcg(p, args):
    def group(d):
        return {k: {"$type": "color", "$value": v} for k, v in d.items()}

    out = {
        "primitive": {
            "brand": group({str(k): v for k, v in p["scales"]["brand"].items()}),
            "neutral": group({str(k): v for k, v in p["scales"]["neutral"].items()}),
        },
        "semantic": {"light": group(p["light"]["roles"])},
    }
    if "dark" in p:
        out["semantic"]["dark"] = group(p["dark"]["roles"])
    return json.dumps(out, indent=2)


def fmt_json(p, args):
    return json.dumps(p, indent=2)


FORMATS = {"css": fmt_css, "tailwind": fmt_tailwind, "dtcg": fmt_dtcg, "json": fmt_json}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brand", help="brand/accent seed, e.g. #2563EB")
    ap.add_argument("--mode", choices=["light", "dark", "both"], default="both")
    ap.add_argument("--level", choices=["AA", "AAA"], default="AA")
    ap.add_argument("--tint", type=float, default=0.012, help="neutral chroma (0.005-0.02)")
    ap.add_argument("--harmony", choices=["analogous", "complementary", "triadic", "split"],
                    help="extra illustration hues (not UI chrome)")
    ap.add_argument("--format", choices=list(FORMATS), default="css")
    ap.add_argument("-o", "--out", help="write formatted output to file (default: stdout)")
    ap.add_argument("--quiet", action="store_true", help="skip the verification table")
    args = ap.parse_args()

    rgb, _ = parse_hex(args.brand)
    seed_L, brand_c, h = rgb_to_oklch(rgb)
    if brand_c < 0.02:  # gray brand: pick a calm hue, keep chroma tiny
        h = 250.0
    brand_c = max(brand_c, 0.02)

    neutral, brand = build_scales(h, brand_c, args.tint)
    result = {"seed": args.brand.upper(), "level": args.level, "hue": round(h, 1),
              "scales": {"neutral": neutral, "brand": brand}}
    modes = ["light", "dark"] if args.mode == "both" else [args.mode]
    total_fail = 0
    tables = []
    for m in modes:
        roles = make_mode(m, h, brand_c, seed_L, args.tint, args.level)
        rows, fails = verify(roles, args.level)
        total_fail += fails
        tables.append((m, rows))
        result[m] = {"roles": roles,
                     "chart": chart_series(h, [roles["bg"], roles["surface"]], m)}
    if args.mode != "both":  # keep output shape stable for formatters
        if args.mode == "dark":
            result["light"] = result["dark"]
            del result["dark"]
    if args.harmony:
        result["extras"] = {"harmony": args.harmony,
                            "hues": [round(x % 360, 1) for x in harmony_hues(h, args.harmony)],
                            "note": "illustration/secondary graphics only; UI chrome keeps ONE accent hue"}
        result["extras"]["swatches"] = [oklch_hex(0.62, 0.14, x) for x in harmony_hues(h, args.harmony)]

    if not args.quiet:
        for m, rows in tables:
            sys.stderr.write(f"\n[{m}] {args.level}  brand {args.brand.upper()} (OKLCH h={h:.0f})\n")
            sys.stderr.write(f"{'Pair':28} {'FG':8} {'BG':8} {'Ratio':>7}  Need  Result\n" + "-" * 70 + "\n")
            for name, f, b, r, req, ok in rows:
                sys.stderr.write(f"{name:28} {f:8} {b:8} {r:6.2f}:1  {req:<4}  {'PASS' if ok else 'FAIL'}\n")
        sys.stderr.write("\nRESULT: " + ("ALL PAIRS PASS" if not total_fail else f"{total_fail} FAIL") + "\n")
        for m in modes:
            key = m if m in result else "light"
            kept = parse_hex(result[key]["roles"]["accent"])[0] == parse_hex(args.brand)[0]
            sys.stderr.write(f"[{m}] accent fill {result[key]['roles']['accent']} "
                             f"({'brand preserved' if kept else 'brand lightness adjusted to pass'}); "
                             f"text-safe accent {result[key]['roles']['accent-text']}\n")

    out = FORMATS[args.format](result, args)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(out + "\n")
        sys.stderr.write(f"wrote {args.out}\n")
    else:
        print(out)
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
