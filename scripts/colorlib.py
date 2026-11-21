#!/usr/bin/env python3
"""
colorlib.py - shared, stdlib-only color maths for the ui-color-contrast-balance toolkit.

WCAG 2.x relative luminance / contrast, alpha blending, OKLab / OKLCH conversion,
gamut mapping, lightness solving, and simple color-vision-deficiency simulation.
"""
import math

# ---------------------------------------------------------------- parsing / WCAG


def parse_hex(h):
    """'#RGB' | '#RGBA' | '#RRGGBB' | '#RRGGBBAA' -> ((r,g,b), alpha 0..1)."""
    h = str(h).strip().lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        raise ValueError(f"bad color: {h!r}")
    rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    alpha = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return rgb, alpha


def to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*[max(0, min(255, int(round(c)))) for c in rgb])


def blend(fg, alpha, bg):
    return tuple(round(alpha * f + (1 - alpha) * b) for f, b in zip(fg, bg))


def resolve(fg_s, bg_s):
    """Blend an (optionally translucent) fg over bg. Returns (fg_rgb, bg_rgb)."""
    bg, _ = parse_hex(bg_s)
    fg, a = parse_hex(fg_s)
    return (blend(fg, a, bg) if a < 1 else fg), bg


def lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def unlin(c):
    c = max(0.0, min(1.0, c))
    v = c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return v * 255


def luminance(rgb):
    r, g, b = (lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = luminance(a), luminance(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def ratio_hex(fg_hex, bg_hex):
    fg, bg = resolve(fg_hex, bg_hex)
    return ratio(fg, bg)


# ---------------------------------------------------------------- OKLab / OKLCH


def rgb_to_oklab(rgb):
    r, g, b = (lin(x) for x in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_linear(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def rgb_to_oklch(rgb):
    L, a, b = rgb_to_oklab(rgb)
    C = math.hypot(a, b)
    h = math.degrees(math.atan2(b, a)) % 360 if C > 1e-4 else 0.0
    return L, C, h


def _in_gamut(lin_rgb, eps=1e-4):
    return all(-eps <= c <= 1 + eps for c in lin_rgb)


def oklch_to_rgb(L, C, h):
    """OKLCH -> sRGB (0-255 ints). Out-of-gamut colors keep L and h; chroma is reduced."""
    L = max(0.0, min(1.0, L))
    hr = math.radians(h)

    def conv(c):
        return oklab_to_linear(L, c * math.cos(hr), c * math.sin(hr))

    if not _in_gamut(conv(C)):
        lo, hi = 0.0, C
        for _ in range(24):
            mid = (lo + hi) / 2
            if _in_gamut(conv(mid)):
                lo = mid
            else:
                hi = mid
        C = lo
    r, g, b = conv(C)
    return tuple(int(round(unlin(x))) for x in (r, g, b))


def oklch_hex(L, C, h):
    return to_hex(oklch_to_rgb(L, C, h))


def delta_e_ok(rgb1, rgb2):
    """Euclidean distance in OKLab (~1.0 = black vs white; 0.02 = just noticeable)."""
    a, b = rgb_to_oklab(rgb1), rgb_to_oklab(rgb2)
    return math.dist(a, b)


def hue_distance(h1, h2):
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


# ---------------------------------------------------------------- solving


def solve_lightness(h, C, bgs, target, seed_L, steps=1000):
    """
    Pick the OKLCH lightness closest to seed_L (same hue/chroma, gamut-mapped) whose contrast
    against EVERY color in `bgs` (hex strings) is >= target. Returns hex, or None.
    """
    bg_rgbs = [parse_hex(b)[0] for b in bgs]
    best, best_d = None, 9.0
    for i in range(steps + 1):
        L = i / steps
        rgb = oklch_to_rgb(L, C, h)
        if min(ratio(rgb, b) for b in bg_rgbs) >= target:
            d = abs(L - seed_L)
            if d < best_d:
                best, best_d = rgb, d
    return to_hex(best) if best else None


# ---------------------------------------------------------------- color-vision deficiency
# Machado, Oliveira & Fernandes (2009), severity 1.0, applied in linear sRGB.
CVD = {
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def simulate_cvd(rgb, kind):
    m = CVD[kind]
    v = [lin(c) for c in rgb]
    out = [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]
    return tuple(int(round(unlin(max(0.0, min(1.0, x))))) for x in out)


def is_chromatic(rgb, min_c=0.04):
    return rgb_to_oklch(rgb)[1] >= min_c
