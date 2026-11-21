#!/usr/bin/env python3
"""
visual_regression.py - screenshot baseline vs current: pixel diff, changed regions, COLOR drift.

  python3 visual_regression.py compare baseline/ current/ --out diff/ --max-diff-pct 0.1
  python3 visual_regression.py compare base.png cur.png --out diff/ --side-by-side
  python3 visual_regression.py compare baseline/ current/ --ignore-region 0,0,1440,80 --ignore-aa
  python3 visual_regression.py approve current/ baseline/                # accept current as new baseline
  python3 visual_regression.py approve current/hero.png baseline/        # accept one file

Pairs files by relative path (a/b.png <-> a/b.png). Needs Pillow only (no numpy).

Per file it reports: % changed pixels, changed regions (bounding boxes), size changes, and
COLOR DRIFT: which dominant colors moved (hex before -> after, OKLab dE), new dominant colors, and
area-share shifts. That is what separates "a pixel moved" from "the brand color changed".
Writes <out>/<name>.diff.png (changed pixels in red, regions boxed) and <out>/report.json|md.

Exit code 1 when any file exceeds --max-diff-pct, a color drifted beyond --max-color-dE, a size
changed, a baseline is missing (unless --allow-new) or a current screenshot is missing.

Tips: freeze dynamic content before screenshots (animations off, fixed data, hide carets/ads),
keep browser, OS fonts, viewport and device scale factor identical, and take baselines per theme.
"""
import argparse
import json
import os
import shutil
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import delta_e_ok, to_hex  # noqa: E402

EXT = (".png", ".jpg", ".jpeg", ".webp")


def pil():
    try:
        from PIL import Image, ImageChops, ImageDraw, ImageFilter
        return Image, ImageChops, ImageDraw, ImageFilter
    except ImportError:
        sys.exit("Pillow missing: pip install pillow")


def list_images(p):
    if os.path.isfile(p):
        return {os.path.basename(p): p}
    out = {}
    for root, _, files in os.walk(p):
        for f in files:
            if f.lower().endswith(EXT):
                full = os.path.join(root, f)
                out[os.path.relpath(full, p)] = full
    return out


def top_colors(im, n=8):
    Image, *_ = pil()
    t = im.convert("RGB")
    t.thumbnail((400, 400), Image.NEAREST)
    q = t.quantize(colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()
    data = list(q.get_flattened_data()) if hasattr(q, "get_flattened_data") else list(q.getdata())
    cnt = Counter(data)
    total = len(data)
    reps = []
    for i, c in cnt.most_common():
        rgb = tuple(pal[i * 3:i * 3 + 3])
        if any(delta_e_ok(rgb, r["rgb"]) < 0.035 for r in reps):
            for r in reps:
                if delta_e_ok(rgb, r["rgb"]) < 0.035:
                    r["n"] += c
                    break
        else:
            reps.append({"rgb": rgb, "n": c})
    return [{"rgb": r["rgb"], "hex": to_hex(r["rgb"]), "share": r["n"] / total * 100} for r in sorted(reps, key=lambda r: -r["n"])[:n]]


def color_drift(a, b, max_de):
    ta, tb = top_colors(a), top_colors(b)
    shifts, new = [], []
    for ca in ta:
        if ca["share"] < 1.5:
            continue
        near = min(tb, key=lambda c: delta_e_ok(ca["rgb"], c["rgb"]))
        de = delta_e_ok(ca["rgb"], near["rgb"])
        if de > 0.012:
            shifts.append({"from": ca["hex"], "to": near["hex"], "dE": round(de, 3), "share_before": round(ca["share"], 1), "share_after": round(near["share"], 1), "breaking": de > max_de})
        elif abs(ca["share"] - near["share"]) > 4:
            shifts.append({"from": ca["hex"], "to": near["hex"], "dE": round(de, 3), "share_before": round(ca["share"], 1), "share_after": round(near["share"], 1), "breaking": False, "note": "area share changed"})
    for cb in tb:
        if cb["share"] >= 2 and all(delta_e_ok(cb["rgb"], ca["rgb"]) > 0.04 for ca in ta):
            new.append({"hex": cb["hex"], "share": round(cb["share"], 1)})
    return shifts, new


def regions_from_mask(mask, block=24):
    Image, *_ = pil()
    w, h = mask.size
    gw, gh = max(1, -(-w // block)), max(1, -(-h // block))
    small = mask.resize((gw, gh), Image.BOX).point(lambda v: 255 if v > 0 else 0)
    px = small.load()
    seen, boxes = set(), []
    for y in range(gh):
        for x in range(gw):
            if px[x, y] and (x, y) not in seen:
                stack, comp = [(x, y)], []
                seen.add((x, y))
                while stack:
                    cx, cy = stack.pop()
                    comp.append((cx, cy))
                    for dx in (-2, -1, 0, 1, 2):  # bridge small gaps so a card isn't 20 boxes
                        for dy in (-2, -1, 0, 1, 2):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < gw and 0 <= ny < gh and px[nx, ny] and (nx, ny) not in seen:
                                seen.add((nx, ny))
                                stack.append((nx, ny))
                xs, ys = [c[0] for c in comp], [c[1] for c in comp]
                boxes.append((min(xs) * block, min(ys) * block, min(w, (max(xs) + 1) * block), min(h, (max(ys) + 1) * block)))
    return sorted(boxes, key=lambda b: -((b[2] - b[0]) * (b[3] - b[1])))


def compare_pair(name, bp, cp, args):
    Image, ImageChops, ImageDraw, ImageFilter = pil()
    a, b = Image.open(bp).convert("RGB"), Image.open(cp).convert("RGB")
    res = {"name": name, "baseline": bp, "current": cp, "size_baseline": a.size, "size_current": b.size}
    size_changed = a.size != b.size
    w, h = min(a.width, b.width), min(a.height, b.height)
    ac, bc = a.crop((0, 0, w, h)), b.crop((0, 0, w, h))
    r, g, bl = ImageChops.difference(ac, bc).split()
    mx = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    mask = mx.point(lambda v: 255 if v > args.tolerance else 0)
    if args.ignore_aa:  # drop isolated pixels (<3 changed pixels in their 3x3 neighbourhood)
        dens = mask.filter(ImageFilter.BoxBlur(1)).point(lambda v: 255 if v >= 255 * 3 / 9 - 1 else 0)
        mask = ImageChops.darker(mask, dens)
    for reg in args.ignore_region or []:
        x, y, rw, rh = reg
        mask.paste(0, (x, y, x + rw, y + rh))
    changed = mask.histogram()[255]
    total = max(a.width * a.height, b.width * b.height)
    extra = total - w * h  # area that exists in only one image counts as changed
    pct = (changed + extra) / total * 100
    boxes = regions_from_mask(mask) if changed else []
    shifts, new = color_drift(a, b, args.max_color_de)
    breaking_color = any(s["breaking"] for s in shifts) or any(n["share"] >= 5 for n in new)
    fail = pct > args.max_diff_pct or size_changed or breaking_color
    res.update({"changed_pixels": changed, "diff_pct": round(pct, 4), "size_changed": size_changed, "regions": [list(x) for x in boxes[:10]],
                "region_count": len(boxes), "color_shifts": shifts, "new_colors": new, "status": "FAIL" if fail else "PASS"})
    if args.out and (changed or size_changed):
        os.makedirs(args.out, exist_ok=True)
        base = os.path.splitext(name.replace(os.sep, "__"))[0]
        vis = bc.copy()
        red = Image.new("RGB", (w, h), (255, 0, 80))
        vis.paste(red, (0, 0), mask)
        d = ImageDraw.Draw(vis)
        for (x0, y0, x1, y1) in boxes[:30]:
            d.rectangle((x0, y0, x1 - 1, y1 - 1), outline=(255, 140, 0), width=3)
        path = os.path.join(args.out, base + ".diff.png")
        if args.side_by_side:
            sheet = Image.new("RGB", (w * 3 + 40, h), (30, 30, 30))
            sheet.paste(ac, (0, 0)); sheet.paste(bc, (w + 20, 0)); sheet.paste(vis, (2 * w + 40, 0))
            sheet.save(path)
        else:
            vis.save(path)
        res["diff_image"] = path
    return res


def cmd_compare(args):
    B, C = list_images(args.baseline), list_images(args.current)
    if os.path.isfile(args.baseline) and os.path.isfile(args.current):  # single file mode: pair them
        B = {os.path.basename(args.current): args.baseline}
        C = {os.path.basename(args.current): args.current}
    results = []
    for name in sorted(set(B) | set(C)):
        if name not in C:
            results.append({"name": name, "status": "FAIL", "note": "current screenshot missing"})
        elif name not in B:
            results.append({"name": name, "status": "NEW" if args.allow_new else "FAIL", "note": "no baseline (run approve to create it)"})
        else:
            results.append(compare_pair(name, B[name], C[name], args))
    lines = [f"# Visual regression  (tolerance {args.tolerance}/255, max diff {args.max_diff_pct}%, max color dE {args.max_color_de})", "",
             "| Screenshot | Status | Changed % | Regions | Color drift |", "|---|---|---|---|---|"]
    for r in results:
        if "diff_pct" not in r:
            lines.append(f"| {r['name']} | {r['status']} | - | - | {r.get('note', '')} |")
            continue
        cd = "; ".join(f"{s['from']}->{s['to']} (dE {s['dE']})" for s in r["color_shifts"][:3]) or "none"
        if r["new_colors"]:
            cd += "; new " + ", ".join(n["hex"] for n in r["new_colors"][:3])
        if r["size_changed"]:
            cd += f"; SIZE {tuple(r['size_baseline'])}->{tuple(r['size_current'])}"
        lines.append(f"| {r['name']} | {r['status']} | {r['diff_pct']} | {r['region_count']} | {cd} |")
    for r in results:
        if r.get("regions"):
            lines.append(f"\n`{r['name']}` changed regions (x0,y0,x1,y1): " + ", ".join(str(tuple(x)) for x in r["regions"][:5]) + (f"  diff: {r['diff_image']}" if r.get("diff_image") else ""))
    out = "\n".join(lines)
    print(out)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        json.dump(results, open(os.path.join(args.out, "report.json"), "w"), indent=2, default=list)
        open(os.path.join(args.out, "report.md"), "w").write(out + "\n")
    return 1 if any(r["status"] == "FAIL" for r in results) else 0


def cmd_approve(args):
    src = list_images(args.current)
    n = 0
    for name, path in src.items():
        dst = os.path.join(args.baseline, name) if os.path.isdir(args.current) else os.path.join(args.baseline, os.path.basename(path))
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.copyfile(path, dst)
        n += 1
    print(f"approved {n} screenshot(s) -> {args.baseline}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare")
    c.add_argument("baseline"); c.add_argument("current")
    c.add_argument("--out", help="diff output directory")
    c.add_argument("--tolerance", type=int, default=8, help="per-channel difference (0-255) ignored as noise")
    c.add_argument("--max-diff-pct", type=float, default=0.1, help="fail above this %% of changed pixels")
    c.add_argument("--max-color-de", type=float, default=0.03, help="fail when a dominant color moves more than this OKLab dE")
    c.add_argument("--ignore-aa", action="store_true", help="ignore isolated 1-2px anti-aliasing noise")
    c.add_argument("--ignore-region", action="append", type=lambda s: tuple(int(v) for v in s.split(",")), help="x,y,w,h to mask (clock, ads, carousel)")
    c.add_argument("--side-by-side", action="store_true")
    c.add_argument("--allow-new", action="store_true", help="screenshots without baseline are NEW, not FAIL")
    c.set_defaults(fn=cmd_compare)
    a = sub.add_parser("approve")
    a.add_argument("current"); a.add_argument("baseline")
    a.set_defaults(fn=cmd_approve)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
