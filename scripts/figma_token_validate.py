#!/usr/bin/env python3
"""
figma_token_validate.py - validate color tokens/variables from Figma (or any design-token source).

  python3 figma_token_validate.py figma-variables.json          # Figma REST "local variables" response
  python3 figma_token_validate.py tokens.json                   # DTCG / Tokens Studio / palette_generate dtcg
  python3 figma_token_validate.py theme.css --level AAA         # CSS custom properties (:root, .dark, [data-theme])
  python3 figma_token_validate.py tokens.json --map accent=brand/600 --map text=ink/default --json out.json

Accepted inputs (auto-detected)
  figma  : GET /v1/files/:key/variables/local  (Enterprise REST API)  OR the same JSON saved from a plugin
  dtcg   : {"color":{"bg":{"$type":"color","$value":"#fff"}}}  incl. {alias} refs, light/dark groups,
           "$extensions":{"mode":{"light":..,"dark":..}} and Tokens Studio sets
  flat   : {"bg":"#F8FAFC","text":"#0F172A",...} or {"light":{...},"dark":{...}}
  css    : --token: #hex | rgb() | hsl() | var(--other)   per :root / .dark / [data-theme=dark] / @media dark
  No Enterprise API? Export variables with any Figma variables-export plugin (JSON/CSS/DTCG) or the
  Figma MCP variable tools, save the result, and point this script at it.

Checks (per mode)
  ERRORS   broken / circular aliases, unparsable colors, required text pairs below WCAG AA/AAA,
           UI pairs (border, focus) below 3:1, label-on-fill pairs below target
  WARNINGS missing roles, missing dark/light counterparts, raw hex in the semantic layer (should alias a
           primitive), near-duplicate colors (token sprawl), pure #000/#FFF text, identical accent in light
           and dark, dark surfaces not lighter than bg, more than one accent hue, translucent colors
Role mapping is heuristic and printed; override with --map role=token/path.
Exit code 1 on ERRORS (and on WARNINGS with --strict).
"""
import argparse
import colorsys
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import blend, delta_e_ok, hue_distance, parse_hex, ratio, rgb_to_oklch, to_hex  # noqa: E402

NAMED = {"white": "#FFFFFF", "black": "#000000"}
PRIM_RE = re.compile(r"(^|/)(primitive|primitives|palette|core|ref|reference|global|scale|scales|base-colors?)(/|$)", re.I)
STEP_RE = re.compile(r"[-_/](50|[1-9]00|950|[0-9]{2})$")


# ---------------------------------------------------------------- color text -> hex / alias
def to_color(v):
    """Return ('hex', '#RRGGBB[AA]') | ('alias', 'path') | (None, reason)."""
    if isinstance(v, dict):  # Figma {r,g,b,a} floats or DTCG color object
        if "type" in v and v.get("type") == "VARIABLE_ALIAS":
            return "alias", v["id"]
        if all(k in v for k in ("r", "g", "b")):
            r, g, b = (round(max(0, min(1, v[k])) * 255) for k in ("r", "g", "b"))
            a = v.get("a", 1)
            return "hex", to_hex((r, g, b)) + ("" if a >= 0.999 else "{:02X}".format(round(a * 255)))
        if "hex" in v:
            return to_color(v["hex"])
        if "components" in v:
            c = v["components"]
            return "hex", to_hex(tuple(round(x * 255) for x in c[:3])) + ("" if v.get("alpha", 1) >= .999 else "{:02X}".format(round(v["alpha"] * 255)))
        return None, "object"
    if not isinstance(v, str):
        return None, str(type(v))
    s = v.strip()
    m = re.match(r"^\{([^}]+)\}$", s)
    if m:
        return "alias", norm_path(m.group(1))
    m = re.match(r"^var\(\s*--([\w-]+)", s)
    if m:
        return "alias", norm_path(m.group(1))
    if s.lower() in NAMED:
        return "hex", NAMED[s.lower()]
    if re.match(r"^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$", s):
        r, a = parse_hex(s)
        return "hex", to_hex(r) + ("" if a >= .999 else "{:02X}".format(round(a * 255)))
    m = re.match(r"^rgba?\(\s*([\d.]+%?)[ ,]+([\d.]+%?)[ ,]+([\d.]+%?)(?:\s*[,/]\s*([\d.]+%?))?\s*\)$", s)
    if m:
        def ch(x):
            return round(float(x[:-1]) * 2.55) if x.endswith("%") else round(float(x))
        a = 1.0 if m.group(4) is None else (float(m.group(4)[:-1]) / 100 if m.group(4).endswith("%") else float(m.group(4)))
        return "hex", to_hex((ch(m.group(1)), ch(m.group(2)), ch(m.group(3)))) + ("" if a >= .999 else "{:02X}".format(round(a * 255)))
    m = re.match(r"^hsla?\(\s*([\d.]+)(?:deg)?[ ,]+([\d.]+)%[ ,]+([\d.]+)%(?:\s*[,/]\s*([\d.]+%?))?\s*\)$", s)
    if m:
        h, sat, l = float(m.group(1)) / 360, float(m.group(2)) / 100, float(m.group(3)) / 100
        r, g, b = colorsys.hls_to_rgb(h, l, sat)
        a = 1.0 if m.group(4) is None else (float(m.group(4)[:-1]) / 100 if m.group(4).endswith("%") else float(m.group(4)))
        return "hex", to_hex((r * 255, g * 255, b * 255)) + ("" if a >= .999 else "{:02X}".format(round(a * 255)))
    return None, s[:40]


def norm_path(p):
    return re.sub(r"[./\\]+", "/", p.strip()).strip("/").lower()


# ---------------------------------------------------------------- loaders -> {mode: {path: ('hex',x)|('alias',p)|(None,why)}}
def load_figma(d):
    meta = d.get("meta", d)
    variables, cols = meta["variables"], meta["variableCollections"]
    names = {vid: norm_path(v["name"]) for vid, v in variables.items()}
    seen = {}
    for vid, n in names.items():  # disambiguate duplicates across collections
        seen.setdefault(n, []).append(vid)
    for n, ids in seen.items():
        if len(ids) > 1:
            for vid in ids:
                names[vid] = norm_path(cols[variables[vid]["variableCollectionId"]]["name"]) + "/" + n
    modes = {}
    mode_names = []
    for c in cols.values():
        for m in c["modes"]:
            if m["name"] not in mode_names:
                mode_names.append(m["name"])
    for mn in mode_names:
        modes[mn] = {}
        for vid, v in variables.items():
            if v.get("resolvedType") != "COLOR" or v.get("remote"):
                continue
            col = cols[v["variableCollectionId"]]
            if mn not in [m["name"] for m in col["modes"]] and len(col["modes"]) > 1:
                continue  # multi-mode collections only appear in the modes they define
            mid = next((m["modeId"] for m in col["modes"] if m["name"] == mn), col["defaultModeId"])
            raw = v["valuesByMode"].get(mid)
            if raw is None:
                raw = v["valuesByMode"].get(col["defaultModeId"])
            kind, val = to_color(raw)
            if kind == "alias":
                val = names.get(val, "missing:" + str(val))
            modes[mn][names[vid]] = (kind, val)
    return modes, "figma"


def is_leaf(node):
    return isinstance(node, dict) and ("$value" in node or "value" in node)


MODE_KEY = re.compile(r"^(light|dark)([-_ ]?mode)?$", re.I)


def load_tree(d):
    shared, bymode = {}, {}

    def put(path, node, mode):
        val = node.get("$value", node.get("value"))
        typ = node.get("$type", node.get("type"))
        ext = (node.get("$extensions") or {}).get("mode") if isinstance(node.get("$extensions"), dict) else None
        if ext:
            for mk, mv in ext.items():
                bymode.setdefault(mk.lower(), {})[path] = to_color(mv)
        if typ and str(typ).lower() != "color":
            return
        tgt = shared if mode is None else bymode.setdefault(mode, {})
        tgt[path] = to_color(val)

    def walk(node, path, mode):
        if is_leaf(node):
            put(norm_path("/".join(path)), node, mode)
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if k.startswith("$"):
                    continue
                mk = MODE_KEY.match(k)
                if mk and mode is None and isinstance(v, dict):
                    walk(v, path, mk.group(1).lower())
                else:
                    walk(v, path + [k], mode)
        elif isinstance(node, (str, dict)) or node is not None:
            c = to_color(node)
            if c[0]:
                (shared if mode is None else bymode.setdefault(mode, {}))[norm_path("/".join(path))] = c
    walk(d, [], None)
    if not bymode:
        return {"default": shared}, "dtcg/flat"
    return {m: {**shared, **t} for m, t in bymode.items()}, "dtcg/flat (modes: %s)" % ", ".join(bymode)


def load_css(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    modes = {}

    def parse_block(sel, body, in_dark):
        mode = "dark" if (in_dark or re.search(r"dark|night", sel, re.I)) else "light"
        for m in re.finditer(r"--([\w-]+)\s*:\s*([^;]+);", body):
            modes.setdefault(mode, {})[norm_path(m.group(1))] = to_color(m.group(2).strip())

    pos = 0
    def scan(s, in_dark):
        i = 0
        while True:
            j = s.find("{", i)
            if j < 0:
                return
            head = s[i:j].strip()
            depth, k = 1, j + 1
            while k < len(s) and depth:
                depth += (s[k] == "{") - (s[k] == "}")
                k += 1
            body = s[j + 1:k - 1]
            if head.startswith("@media"):
                scan(body, in_dark or bool(re.search(r"prefers-color-scheme\s*:\s*dark", head)))
            elif head.startswith("@"):
                pass
            else:
                parse_block(head, body, in_dark)
            i = k
    scan(text, False)
    if "light" in modes and "dark" in modes:
        modes["dark"] = {**{k: v for k, v in modes["light"].items()}, **modes["dark"]}
    return modes, "css"


def load(path):
    raw = open(path, encoding="utf-8").read()
    if path.lower().endswith((".css", ".scss", ".less")) or raw.lstrip().startswith((":root", "@", "html", ".", "[")):
        return load_css(raw)
    d = json.loads(raw)
    if isinstance(d, dict) and (("variables" in d and "variableCollections" in d) or ("meta" in d and "variables" in d.get("meta", {}))):
        return load_figma(d)
    return load_tree(d)


# ---------------------------------------------------------------- resolve
def resolve_mode(tokens):
    """-> ({path: hex}, errors[{path, msg}])"""
    out, errs = {}, []

    def res(p, trail):
        kind, val = tokens[p]
        if kind == "hex":
            return val
        if kind == "alias":
            tgt = val
            if tgt not in tokens:
                alt = [k for k in tokens if k.endswith("/" + tgt) or k == tgt]
                if len(alt) == 1:
                    tgt = alt[0]
                else:
                    errs.append({"path": p, "msg": f"broken alias -> {val}"})
                    return None
            if tgt in trail:
                errs.append({"path": p, "msg": "circular alias: " + " -> ".join(list(trail) + [tgt])})
                return None
            return res(tgt, trail + [tgt])
        errs.append({"path": p, "msg": f"unparsable color ({val})"})
        return None

    for p in tokens:
        v = res(p, [p])
        if v:
            out[p] = v
    return out, errs


# ---------------------------------------------------------------- role mapping
RULES = {
    "on-accent": [r"(^|/)on[-_/]?(accent|primary|brand|action|cta)(/default|/base)?$", r"(accent|primary|brand|action|cta)[-_/](foreground|fg|contrast|label|on)(/default)?$", r"(^|/)(text|content|fg)[-_/]on[-_/](accent|primary|brand|action)"],
    "accent": [r"(^|/)(accent|primary|brand|action|cta)(/default|/base|/main|/fill)?$", r"(^|/)(accent|primary|brand|action)[-_/](default|base|main|fill|bg|background)$", r"(bg|background|surface|fill)[-_/](accent|primary|brand|action)(/default)?$"],
    "bg": [r"(^|/)(bg|background|canvas|page|app)(/default|/base|/primary|/page)?$", r"(bg|background)[-_/](default|base|primary|page|canvas|app)$"],
    "surface": [r"(^|/)(surface|card|panel|elevated)(/default|/base|/primary)?$", r"(bg|background)[-_/](surface|card|secondary|elevated|raised)$"],
    "muted": [r"(text|fg|foreground|content)[-_/](muted|secondary|subtle|tertiary|soft|weak|helper)$", r"(^|/)(muted|subtle[-_]text)(/default)?$"],
    "text": [r"(^|/)(text|fg|foreground|content|on[-_]?surface|on[-_]?background|ink)(/default|/base|/primary|/body)?$", r"(text|fg|foreground|content)[-_/](default|base|primary|body|strong)$"],
    "border": [r"(^|/)(border|stroke|outline)(/default|/base|/strong|/input|/control)?$", r"(border|stroke)[-_/](default|base|strong|input|control)$"],
    "focus": [r"focus([-_/](ring|outline|border|color))?(/default)?$"],
    "error": [r"(^|/)(error|danger|negative|destructive|critical)(/default|/text|/fg|/base)?$", r"(text|fg|foreground)[-_/](error|danger|negative)$"],
    "success": [r"(^|/)(success|positive)(/default|/text|/fg|/base)?$", r"(text|fg|foreground)[-_/](success|positive)$"],
    "warning": [r"(^|/)(warning|caution)(/default|/text|/fg|/base)?$", r"(text|fg|foreground)[-_/](warning|caution)$"],
}
EXCLUDE = re.compile(r"hover|active|pressed|disabled|inverse|inverted|overlay|alpha|opacity|selected|visited", re.I)


def is_semantic(path):
    return not PRIM_RE.search(path) and not STEP_RE.search(path)


def map_roles(paths, overrides):
    roles = {}
    for role, rules in RULES.items():
        best = None
        for p in paths:
            if EXCLUDE.search(p):
                continue
            for pri, rx in enumerate(rules):
                if re.search(rx, p):
                    key = (0 if is_semantic(p) else 1, pri, len(p))
                    if best is None or key < best[0]:
                        best = (key, p)
                    break
        if best:
            roles[role] = best[1]
    for r, p in overrides.items():
        roles[r] = norm_path(p)
    return roles


# ---------------------------------------------------------------- checks
def rgb_of(hexs, bg_hex=None):
    rgb, a = parse_hex(hexs)
    if a < 1 and bg_hex:
        return blend(rgb, a, parse_hex(bg_hex)[0])
    return rgb


def validate(modes_raw, level, overrides):
    aaa = level == "AAA"
    report = {"modes": {}, "errors": 0, "warnings": 0}
    resolved = {}
    for mn, toks in modes_raw.items():
        resolved[mn], errs = resolve_mode(toks)
        report["modes"][mn] = {"tokens": len(toks), "issues": [], "roles": {}, "pairs": []}
        for e in errs:
            report["modes"][mn]["issues"].append({"sev": "error", **e})
    # only judge modes that actually define a UI role set
    for mn, vals in resolved.items():
        M = report["modes"][mn]
        roles = map_roles(list(vals), overrides)
        M["roles"] = roles
        if len(roles) < 3:
            M["note"] = "fewer than 3 roles recognised; shown as primitive-only mode (use --map)"
            continue

        def get(r):
            return vals.get(roles[r]) if r in roles else None

        bg = get("bg")
        if bg is None and "surface" in roles:
            bg = get("surface")
        pairs = [("Body text on bg", "text", "bg", 4.5, 7.0, "text"), ("Body text on surface", "text", "surface", 4.5, 7.0, "text"),
                 ("Muted text on bg", "muted", "bg", 4.5, 7.0, "text"), ("Muted text on surface", "muted", "surface", 4.5, 7.0, "text"),
                 ("Accent as text on bg", "accent", "bg", 4.5, 7.0, "text"), ("Label on accent", "on-accent", "accent", 4.5, 7.0, "text"),
                 ("Border on bg", "border", "bg", 3.0, 3.0, "ui"), ("Border on surface", "border", "surface", 3.0, 3.0, "ui"),
                 ("Focus on bg", "focus", "bg", 3.0, 3.0, "ui"), ("Error on bg", "error", "bg", 4.5, 7.0, "text"),
                 ("Success on bg", "success", "bg", 4.5, 7.0, "text"), ("Warning on bg", "warning", "bg", 4.5, 7.0, "text")]
        for name, f, b, aa, aaa_t, kind in pairs:
            fv, bv = get(f), get(b)
            if fv is None or bv is None:
                continue
            bgrgb = rgb_of(bv)
            r = ratio(rgb_of(fv, bv), bgrgb)
            req = aaa_t if aaa else aa
            ok = r + 1e-9 >= req
            M["pairs"].append({"pair": name, "fg": roles[f], "bg": roles[b], "fgHex": fv[:7], "bgHex": bv[:7], "ratio": round(r, 2), "need": req, "ok": ok})
            if not ok:
                M["issues"].append({"sev": "error", "path": roles[f], "msg": f"{name}: {fv[:7]} on {bv[:7]} = {r:.2f}:1 (needs {req}:1)  -> python3 contrast_check.py fix {fv[:7]} {bv[:7]} --target {req}"})
        # auto "on-*" label pairs
        for p, v in vals.items():
            m = re.search(r"(?:^|/)on[-_/]([\w-]+?)(?:/(default|base))?$", p)
            if m:
                tgt = [q for q in vals if q.endswith("/" + m.group(1)) or q == m.group(1) or q.endswith(m.group(1) + "/default")]
                if len(tgt) >= 1 and p not in roles.values():
                    t = sorted(tgt, key=len)[0]
                    r = ratio(rgb_of(v, vals[t]), rgb_of(vals[t]))
                    req = 7.0 if aaa else 4.5
                    M["pairs"].append({"pair": f"{p} on {t}", "ratio": round(r, 2), "need": req, "ok": r >= req, "fgHex": v[:7], "bgHex": vals[t][:7], "fg": p, "bg": t})
                    if r < req:
                        M["issues"].append({"sev": "error", "path": p, "msg": f"label {p} on {t} = {r:.2f}:1 (needs {req}:1)"})
        # warnings
        for need_r in ("bg", "text", "accent", "on-accent"):
            if need_r not in roles:
                M["issues"].append({"sev": "warn", "path": "", "msg": f"required role not found: {need_r} (use --map {need_r}=<token path>)"})
        for p, v in vals.items():
            if len(v) == 9:
                M["issues"].append({"sev": "warn", "path": p, "msg": f"translucent color {v}: contrast depends on what is behind it; verify on each surface"}) if is_semantic(p) else None
        t = get("text")
        if t and t[:7] in ("#000000", "#FFFFFF"):
            M["issues"].append({"sev": "warn", "path": roles["text"], "msg": f"pure {t[:7]} body text: use tinted near-black/near-white (halation in dark mode, glare in light)"})
        if mn.lower().startswith("dark") and get("bg") and get("surface"):
            if rgb_to_oklch(rgb_of(get("surface")))[0] < rgb_to_oklch(rgb_of(get("bg")))[0] - 0.005:
                M["issues"].append({"sev": "warn", "path": roles["surface"], "msg": "dark mode: surface is darker than bg (elevation should get LIGHTER)"})
        # hues
        hues = []
        for p, v in vals.items():
            if is_semantic(p) and re.search(r"accent|primary|secondary|tertiary|brand", p) and not EXCLUDE.search(p):
                L, C, h = rgb_to_oklch(rgb_of(v))
                if C >= 0.06:
                    hues.append((p, h))
        distinct = []
        for p, h in hues:
            if all(hue_distance(h, x) > 30 for _, x in distinct):
                distinct.append((p, h))
        if len(distinct) > 1:
            M["issues"].append({"sev": "warn", "path": "", "msg": "more than one accent hue among " + ", ".join(p for p, _ in distinct[:4]) + " (rule: one accent hue per view)"})

    # cross-mode
    names = list(resolved)
    light = next((m for m in names if m.lower().startswith("light")), None)
    dark = next((m for m in names if m.lower().startswith("dark")), None)
    if light and dark:
        rl, rd = report["modes"][light]["roles"], report["modes"][dark]["roles"]
        for p in set(resolved[light]) - set(resolved[dark]):
            report["modes"][dark]["issues"].append({"sev": "warn", "path": p, "msg": "token exists in light but not in dark"})
        for p in set(resolved[dark]) - set(resolved[light]):
            report["modes"][light]["issues"].append({"sev": "warn", "path": p, "msg": "token exists in dark but not in light"})
        if "accent" in rl and "accent" in rd and resolved[light].get(rl["accent"]) and resolved[light].get(rl["accent"]) == resolved[dark].get(rd["accent"]):
            report["modes"][dark]["issues"].append({"sev": "warn", "path": rd["accent"], "msg": "accent is identical in light and dark: saturated accents vibrate on dark surfaces; lighten/desaturate for dark"})
        if rl.get("bg") and rd.get("bg"):
            from colorlib import luminance
            if luminance(rgb_of(resolved[dark][rd["bg"]])) >= luminance(rgb_of(resolved[light][rl["bg"]])):
                report["modes"][dark]["issues"].append({"sev": "error", "path": rd["bg"], "msg": "dark bg is not darker than light bg - modes look swapped/mis-bound"})
    elif len(names) == 1:
        report["note"] = "single mode found: dark/light parity cannot be checked"

    # hygiene on first role-bearing mode: raw hex in semantic layer + near duplicates
    base = next((m for m in names if report["modes"][m]["roles"]), None)
    if base:
        toks = modes_raw[base]
        raw_sem = [p for p, (k, v) in toks.items() if k == "hex" and is_semantic(p)]
        has_prims = any(not is_semantic(p) for p in toks)
        if has_prims and raw_sem:
            report["modes"][base]["issues"].append({"sev": "warn", "path": "", "msg": f"{len(raw_sem)} semantic token(s) hold raw hex instead of aliasing a primitive: " + ", ".join(raw_sem[:6]) + (" ..." if len(raw_sem) > 6 else "")})
        raws = [(p, v) for p, (k, v) in toks.items() if k == "hex" and len(v) == 7]
        near = []
        for i in range(len(raws)):
            for j in range(i + 1, len(raws)):
                if raws[i][1] != raws[j][1] and delta_e_ok(parse_hex(raws[i][1])[0], parse_hex(raws[j][1])[0]) < 0.015:
                    near.append((raws[i], raws[j]))
        if near:
            report["modes"][base]["issues"].append({"sev": "warn", "path": "", "msg": f"{len(near)} near-duplicate color pair(s) (dE<0.015, token sprawl), e.g. {near[0][0][0]} {near[0][0][1]} ~ {near[0][1][0]} {near[0][1][1]}"})
        bad_names = [p for p in toks if re.search(r"(^|/)(color|colour)[-_ ]?\d+$|untitled|copy|^[0-9a-f]{6}$", p)]
        if bad_names:
            report["modes"][base]["issues"].append({"sev": "warn", "path": "", "msg": "non-semantic token names: " + ", ".join(bad_names[:5])})
    for m in report["modes"].values():
        report["errors"] += sum(1 for i in m["issues"] if i["sev"] == "error")
        report["warnings"] += sum(1 for i in m["issues"] if i["sev"] == "warn")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--level", choices=["AA", "AAA"], default="AA")
    ap.add_argument("--map", action="append", default=[], help="role=token/path override (repeatable)")
    ap.add_argument("--json", help="write full report as JSON")
    ap.add_argument("--strict", action="store_true", help="fail on warnings too")
    a = ap.parse_args()
    overrides = dict(x.split("=", 1) for x in a.map)
    modes, fmt = load(a.file)
    if not modes or not any(modes.values()):
        sys.exit("no color tokens found - check the file format (see --help)")
    rep = validate(modes, a.level, overrides)
    rep["format"] = fmt
    print(f"Source: {a.file}  [{fmt}]  target {a.level}")
    for mn, M in rep["modes"].items():
        print(f"\n=== Mode: {mn}  ({M['tokens']} color tokens)")
        if M.get("note"):
            print("  ", M["note"])
        if M["roles"]:
            print("  role map:", ", ".join(f"{r}={p}" for r, p in M["roles"].items()))
        for p in M["pairs"]:
            print(f"  {'PASS' if p['ok'] else 'FAIL'}  {p['pair'][:34]:34} {p['fgHex']} on {p['bgHex']}  {p['ratio']:>6}:1 (need {p['need']})")
        for i in sorted(M["issues"], key=lambda x: x["sev"] != "error"):
            print(f"  {'ERROR' if i['sev'] == 'error' else 'warn '} {i['path'] + ': ' if i['path'] else ''}{i['msg']}")
    if rep.get("note"):
        print("\nNote:", rep["note"])
    print(f"\nRESULT: {rep['errors']} error(s), {rep['warnings']} warning(s)")
    if a.json:
        json.dump(rep, open(a.json, "w"), indent=2)
    sys.exit(1 if rep["errors"] or (a.strict and rep["warnings"]) else 0)


if __name__ == "__main__":
    main()
