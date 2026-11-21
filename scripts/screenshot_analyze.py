#!/usr/bin/env python3
"""
screenshot_analyze.py - automatic color analysis of a UI screenshot (any app, any language).

  python3 screenshot_analyze.py shot.png
  python3 screenshot_analyze.py shot.png --region 0,0,1440,700 --json report.json --palette-json palette.json
  python3 screenshot_analyze.py a.png b.png --colors 20

Needs Pillow (pip install pillow). No numpy required.

What it does
  1. Quantizes the screenshot, merges near-identical colors (OKLab distance), measures area share.
  2. Estimates the 60-30-10 split (dominant / secondary / accent) and says where it deviates.
  3. Finds colors that TOUCH each other (pixel adjacency) and computes real WCAG contrast for those
     pairs. Thin features (text, icons, hairlines) are held to 4.5:1 / 3:1; region boundaries are info.
  4. Infers role colors (bg, surface, text, muted, accent, on-accent) -> palette.json that
     `contrast_check.py check` accepts. Inference is heuristic: ALWAYS confirm by eye.
  5. Color-blind check: pairs that are distinct normally but collapse under protan/deutan/tritan.

Photos, video frames and gradients blur the estimate. Crop them out with --region or judge by eye.
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import (  # noqa: E402
    CVD, delta_e_ok, luminance, ratio, rgb_to_oklch, simulate_cvd, to_hex,
)


def need_pillow():
    try:
        from PIL import Image  # noqa: F401
        return Image
    except ImportError:
        sys.exit("Pillow missing: pip install pillow  (add --break-system-packages in managed Pythons)")


def load(path, region, max_side):
    Image = need_pillow()
    im = Image.open(path).convert("RGB")
    if region:
        x, y, w, h = region
        im = im.crop((x, y, x + w, y + h))
    scale = max(im.width, im.height) / max_side
    if scale > 1:  # NEAREST keeps real pixel colors (no blended halo colors)
        im = im.resize((round(im.width / scale), round(im.height / scale)), Image.NEAREST)
    return im


def cluster_colors(im, n_colors, merge_de):
    Image = need_pillow()
    q = im.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()[: n_colors * 3]
    data = list(q.get_flattened_data()) if hasattr(q, "get_flattened_data") else list(q.getdata())
    used = sorted(set(data))
    cols = {i: tuple(pal[i * 3:i * 3 + 3]) for i in used}
    # greedy merge by area (no chaining): a color joins the first larger representative within `merge_de`
    cnt = Counter(data)
    reps, mapping = [], {}
    for i in sorted(used, key=lambda k: -cnt[k]):
        home = next((r for r in reps if delta_e_ok(cols[i], cols[r]) < merge_de), None)
        if home is None:
            reps.append(i)
            home = i
        mapping[i] = home
    return q.width, q.height, [mapping[i] for i in data], {i: cols[i] for i in reps}


def analyze(path, args):
    im = load(path, args.region, args.max_side)
    w, h, idx, cols = cluster_colors(im, args.colors, args.merge)
    total = w * h
    counts = Counter(idx)

    # adjacency (4-neighbourhood) between different color clusters
    edges = Counter()
    for y in range(h):
        row = idx[y * w:(y + 1) * w]
        for a, b in zip(row, row[1:]):
            if a != b:
                edges[(a, b) if a < b else (b, a)] += 1
        if y + 1 < h:
            nxt = idx[(y + 1) * w:(y + 2) * w]
            for a, b in zip(row, nxt):
                if a != b:
                    edges[(a, b) if a < b else (b, a)] += 1
    total_edges = sum(edges.values()) or 1

    info = {}
    for i, rgb in cols.items():
        L, C, hh = rgb_to_oklch(rgb)
        info[i] = {"hex": to_hex(rgb), "rgb": rgb, "share": counts[i] / total * 100, "L": L, "C": C, "h": hh}
    order = sorted(info, key=lambda i: -info[i]["share"])

    # ---- 60-30-10 estimate
    bg_i = order[0]
    chromatic = [i for i in order if info[i]["C"] >= args.chroma]
    neutrals = [i for i in order if i not in chromatic]
    dom_ref = neutrals[0] if neutrals else bg_i
    dom = [i for i in neutrals if abs(info[i]["L"] - info[dom_ref]["L"]) <= 0.12 or i == dom_ref]
    # text on the page is part of the 60 per the skill: add thin dark/light neutrals touching the bg
    sec = [i for i in neutrals if i not in dom]
    acc = chromatic
    dom_s, sec_s, acc_s = (sum(info[i]["share"] for i in grp) for grp in (dom, sec, acc))

    # ---- pair contrast (touching colors)
    pairs = []
    for (a, b), cnt in edges.most_common(40):
        if cnt / total_edges * 100 < args.min_edge_pct:
            continue
        r = ratio(info[a]["rgb"], info[b]["rgb"])
        small = min(counts[a], counts[b])
        density = cnt / max(small, 1)
        thin = density > 0.12 and not (r < 1.35 and min(info[a]["share"], info[b]["share"]) >= 1.5)  # big low-contrast neighbours = gradient steps
        req = 4.5 if thin else 3.0
        if thin:
            status = "PASS" if r >= 4.5 else ("WARN" if r >= 3.0 else "FAIL")
            kind = "thin feature (text/icon/line)"
        else:
            status = "info" if r >= 1.5 else "info-subtle"
            kind = "region boundary"
        pairs.append({"a": info[a]["hex"], "b": info[b]["hex"], "ratio": round(r, 2), "edge_share_pct": round(cnt / total_edges * 100, 1),
                      "kind": kind, "needs": req if thin else None, "status": status,
                      "fix_hint": (f"python3 contrast_check.py fix {info[a]['hex'] if luminance(info[a]['rgb']) < luminance(info[b]['rgb']) else info[b]['hex']} "
                                   f"{info[b]['hex'] if luminance(info[a]['rgb']) < luminance(info[b]['rgb']) else info[a]['hex']} --target 4.5") if status in ("FAIL", "WARN") else None})

    # ---- role inference
    def edge_cnt(a, b):
        return edges.get((a, b) if a < b else (b, a), 0)

    roles = {}
    roles["bg"] = bg_i
    surf = [i for i in neutrals if i != bg_i and info[i]["share"] >= 2 and abs(info[i]["L"] - info[bg_i]["L"]) <= 0.15]
    if surf:
        roles["surface"] = max(surf, key=lambda i: edge_cnt(i, bg_i) + info[i]["share"])
    thin_neutral = [i for i in neutrals if i != bg_i and info[i]["share"] < 20 and edge_cnt(i, bg_i) > 0
                    and edge_cnt(i, bg_i) / max(counts[i], 1) > 0.12]
    if thin_neutral:
        ranked = sorted(thin_neutral, key=lambda i: -ratio(info[i]["rgb"], info[bg_i]["rgb"]))
        roles["text"] = ranked[0]
        if len(ranked) > 1:
            roles["muted"] = ranked[1]
    if chromatic:
        roles["accent"] = max(chromatic, key=lambda i: info[i]["share"] * (1 + info[i]["C"] * 3))
        nb = [(edge_cnt(roles["accent"], j), j) for j in info if j != roles["accent"]]
        nb = [t for t in nb if t[0] > 0]
        if nb:
            roles["on-accent"] = max(nb)[1]
    suggested = {k: info[v]["hex"] for k, v in roles.items()}

    # ---- color-blind check on the most relevant colors
    focus = []
    for i in order:
        if info[i]["share"] >= 0.5 or i in roles.values():
            focus.append(i)
    focus = focus[:9]
    cvd = []
    for kind in CVD:
        for ia, a in enumerate(focus):
            for b in focus[ia + 1:]:
                n_de = delta_e_ok(info[a]["rgb"], info[b]["rgb"])
                s_de = delta_e_ok(simulate_cvd(info[a]["rgb"], kind), simulate_cvd(info[b]["rgb"], kind))
                if n_de >= 0.10 and s_de < 0.045 and (info[a]["C"] >= 0.05 or info[b]["C"] >= 0.05):
                    cvd.append({"mode": kind, "a": info[a]["hex"], "b": info[b]["hex"],
                                "normal_dE": round(n_de, 3), "simulated_dE": round(s_de, 3)})

    return {
        "file": path, "size": [w, h], "theme_guess": "dark" if luminance(info[bg_i]["rgb"]) < 0.18 else "light",
        "palette": [{"hex": info[i]["hex"], "share_pct": round(info[i]["share"], 1), "oklch": [round(info[i]["L"], 3), round(info[i]["C"], 3), round(info[i]["h"])]} for i in order],
        "split": {"dominant": round(dom_s), "secondary": round(sec_s), "accent": round(acc_s)},
        "split_ok": 50 <= dom_s <= 75 and 18 <= sec_s <= 40 and 2 <= acc_s <= 16,
        "touching_pairs": pairs,
        "suggested_roles": suggested,
        "color_blind_risks": cvd,
    }


def report(r):
    print(f"\n=== {r['file']}  ({r['size'][0]}x{r['size'][1]} analysed, theme looks {r['theme_guess']})")
    print("\nPalette (area share)")
    for p in r["palette"][:10]:
        print(f"  {p['hex']}  {p['share_pct']:5.1f}%   OKLCH {p['oklch']}")
    s = r["split"]
    print(f"\n60-30-10 estimate   dominant {s['dominant']}% | secondary {s['secondary']}% | accent {s['accent']}%   "
          f"-> {'within tolerance' if r['split_ok'] else 'OUTSIDE tolerance (inspect; photos/gradients skew this)'}")
    print("\nTouching color pairs (real contrast where colors meet)")
    print(f"  {'A':8} {'B':8} {'ratio':>7}  {'edge%':>5}  status  kind")
    shown = [p for p in r["touching_pairs"] if p["status"] != "info-subtle"][:14]
    for p in shown:
        print(f"  {p['a']:8} {p['b']:8} {p['ratio']:6.2f}:1 {p['edge_share_pct']:5.1f}  {p['status']:11} {p['kind']}")
    bad = [p for p in r["touching_pairs"] if p["status"] in ("FAIL", "WARN")]
    for p in bad:
        print(f"  -> {p['status']}: {p['a']} vs {p['b']} = {p['ratio']}:1 (needs {p['needs']}:1). {p['fix_hint']}")
    print("\nInferred roles (verify by eye):", json.dumps(r["suggested_roles"]))
    if r["color_blind_risks"]:
        print("\nColor-blind risks (distinct normally, similar when simulated)")
        for c in r["color_blind_risks"][:8]:
            print(f"  {c['mode']:12} {c['a']} vs {c['b']}  dE {c['normal_dE']} -> {c['simulated_dE']}  (add icon/label/pattern)")
    else:
        print("\nColor-blind check: no collapsing pairs among the main colors.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--region", help="x,y,w,h crop (e.g. exclude a photo hero)")
    ap.add_argument("--colors", type=int, default=24, help="quantization colors (default 24)")
    ap.add_argument("--merge", type=float, default=0.035, help="OKLab distance to merge similar colors")
    ap.add_argument("--chroma", type=float, default=0.07, help="OKLCH chroma that counts as 'colored'")
    ap.add_argument("--max-side", type=int, default=1100)
    ap.add_argument("--min-edge-pct", type=float, default=0.8, help="ignore pairs below this share of all edges")
    ap.add_argument("--json", help="write full report JSON")
    ap.add_argument("--palette-json", help="write inferred roles for contrast_check.py check (single image)")
    args = ap.parse_args()
    if args.region:
        args.region = tuple(int(v) for v in args.region.split(","))
    results = [analyze(p, args) for p in args.images]
    for r in results:
        report(r)
    if args.json:
        json.dump(results if len(results) > 1 else results[0], open(args.json, "w"), indent=2)
    if args.palette_json:
        json.dump(results[0]["suggested_roles"], open(args.palette_json, "w"), indent=2)
    fails = sum(1 for r in results for p in r["touching_pairs"] if p["status"] == "FAIL")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
