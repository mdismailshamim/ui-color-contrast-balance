---
name: ui-color-contrast-balance
description: Design and audit any UI (web, mobile, dashboard, landing page, design system, Figma, slides) with the 60-30-10 color ratio, WCAG 2.2 AA and AAA contrast, and visual balance and composition (hierarchy, grid, spacing, whitespace, focal point). Use this skill whenever the user mentions color palette, color scheme, 60-30-10, accent or CTA color, contrast ratio, WCAG, AA, AAA, accessibility, dark mode colors, "my UI looks off / unbalanced / cluttered / boring", visual hierarchy, layout balance, composition, design tokens, or asks to review, critique, fix or generate any interface, even if they never say "accessibility". Ships a verified contrast-checker script, ready palettes that already pass AA/AAA, and a 100-point audit rubric.
---

# UI Color, Contrast & Balance

One skill, three jobs: **(1) color ratio (60-30-10)**, **(2) contrast that passes WCAG AA/AAA**, **(3) visual balance & composition**. It works for any project, stack, brand, language, or platform. It does not pick a "style"; it makes whatever style you choose coherent, readable, and balanced.

Load extra files only when needed:

| Need | Read |
|---|---|
| Palette recipes, token mapping, dark mode, color-blind rules | `references/color-60-30-10.md` |
| Every WCAG success criterion that touches color/focus/target, edge cases, APCA note | `references/wcag-contrast.md` |
| Hierarchy, visual weight, grid, spacing, type scale, focal-point rules | `references/visual-balance-composition.md` |
| 100-point scoring rubric + pre-delivery checklist + report template | `references/audit-checklist.md` |
| Which 20 GitHub repos informed this skill and what was kept | `references/research-sources.md` |

---

## Workflow (always in this order)

1. **Context (1 minute, don't over-ask).** Product type, audience, brand colors if any, light/dark/both, target level (default **AA**, go **AAA** for body text/health/finance/gov/education or when asked), platforms. Missing info: state an assumption in one line and continue.
2. **Choose structure before color.** Decide the 3 roles (below), then the composition skeleton (focal point, hierarchy levels, grid).
3. **Build tokens, not hex-in-components.** Every color is a named role token. Components only reference tokens.
4. **Verify with numbers, not eyeballs.** Run `scripts/contrast_check.py` (see "Verify"). Never claim a pair passes without computing its ratio.
5. **Report in a table** with ratios and PASS/FAIL (format below). Fix failures before delivering.

---

## 1. The 60-30-10 rule (precise version)

It is an **area** rule, not a "3 hues" rule. Measure by how much of the screen each role covers.

| Share | Role | What it is | Typical tokens |
|---|---|---|---|
| **60%** | Dominant | Page background and large calm areas. Almost always a tinted neutral | `bg`, `text` (counts here visually) |
| **30%** | Secondary | Structure that separates content: cards, sidebars, nav, section bands, inputs | `surface`, `surface-alt`, `border`, `muted` |
| **10%** | Accent | The few things you want clicked or noticed: primary CTA, active state, key data, links, focus | `accent`, `accent-hover`, `on-accent`, `focus` |

Hard rules:

- **One accent hue per view.** Support colors (success/warning/error) are *semantic*, they do not count as a second accent and appear only when state exists.
- **Accent budget ≤ ~10% of area and ≤ 1 primary CTA per viewport.** If everything is accent, nothing is. Secondary actions use outline/ghost in the 30% role.
- **Tolerance is real:** acceptable bands are roughly 55-70 / 20-35 / 5-12. Data-dense dashboards drift to 70/25/5; hero/marketing can push the accent to 15% in one band. Break the ratio on purpose, never by accident.
- **Dark mode keeps the same split.** Dominant becomes a dark tinted neutral, surfaces get *lighter* as they elevate, the accent is desaturated/lightened to keep contrast (details in reference).
- **Neutrals are tinted, not dead gray.** Tint every neutral a few percent toward the brand hue (OKLCH chroma ≈ 0.005-0.02). It creates cohesion without looking "colored".
- **Text color is part of the 60.** Body text must be near-neutral, never the accent color.

Quick token skeleton (copy and rename to the project):

```css
:root{
  /* 60 */ --bg:#F8FAFC;   --text:#0F172A;
  /* 30 */ --surface:#FFFFFF; --surface-alt:#E2E8F0; --muted:#475569; --border:#64748B;
  /* 10 */ --accent:#1D4ED8; --on-accent:#FFFFFF; --focus:#1D4ED8;
  /* semantic (state only) */ --error:#B91C1C; --success:#15803D; --warning:#92400E;
}
```

Ready palettes (all computed with the script, light AA, light AAA, dark AA, warm light, green light) are in `references/color-60-30-10.md`.

---

## 2. Contrast: WCAG AA and AAA cheat sheet

Ratio formula: `(L1 + 0.05) / (L2 + 0.05)` using sRGB relative luminance (WCAG 2.x). Calculate with the script.

| Element | AA (target) | AAA (enhanced) | SC |
|---|---|---|---|
| Body text (< 24px regular, < ~18.66px bold) | **4.5 : 1** | **7 : 1** | 1.4.3 / 1.4.6 |
| Large text (≥ 24px regular, or ≥ ~18.66px bold) | **3 : 1** | **4.5 : 1** | 1.4.3 / 1.4.6 |
| UI components & states: input borders, icons that carry meaning, focus ring, checkbox, chart marks | **3 : 1** against adjacent colors | no AAA tier (aim 4.5+) | 1.4.11 |
| Text over images/gradients | Worst point under the text must pass | same | 1.4.3 |
| Disabled controls, pure decoration, logos | Exempt (still keep legible) | exempt | n/a |

Related AA/AAA requirements that are *design-time* decisions:

- **Never use color alone** to convey meaning (error, link in body text, chart series, status). Add text, icon, pattern, or underline. (1.4.1)
- **Visible keyboard focus** on every interactive element; ring ≥ 3:1 vs neighbors, not hidden by sticky bars. (2.4.7, 2.4.11; AAA 2.4.13: ≥ 2px thick ring)
- **Touch/click target ≥ 24×24 CSS px (AA)**; design to **44×44** on touch. (2.5.8)
- Text must survive **200% zoom/reflow** and user text-spacing overrides without clipping. (1.4.4, 1.4.10, 1.4.12)
- Hover/pressed/visited/selected states are **separate pairs**, each must pass.

Defaults that save you from most failures:

| Use | Light mode | Dark mode |
|---|---|---|
| Body text | ≥ 12:1 (aim for AAA) | ≥ 12:1 on `bg` and on elevated `surface` |
| Secondary/muted text | ≥ 7:1 on bg, never below 4.5:1 | ≥ 7:1 |
| Placeholder / helper text | ≥ 4.5:1 (placeholders are text) | ≥ 4.5:1 |
| Accent as text/link | ≥ 4.5:1 (use a darker accent shade than the button fill if needed) | lighten accent until ≥ 4.5:1 |
| Label on accent button | ≥ 4.5:1 (AAA: ≥ 7:1) | same |

APCA (`Lc`) is **experimental, not part of WCAG 2.2 or any W3C standard**. Use it only as a secondary sanity check, e.g. for dark mode, and never to pass or fail a deliverable. WCAG 2.x ratios remain the requirement.

---

## 3. Visual balance & composition (the rules that actually move quality)

Visual weight = size × contrast × saturation × isolation × position. Balance is *equilibrium of weight*, not symmetry.

1. **One focal point per view.** Squint test (blur the screen): exactly one thing should win, the second thing should be clearly weaker.
2. **Three hierarchy levels, max.** Primary (1 element), secondary (2-4 elements), tertiary (the rest). Adjacent levels differ by ≥ 1.5× in size *or* a clear weight/contrast step, never by one signal alone.
3. **Balance by counterweight.** A heavy left hero is balanced by a lighter-but-vivid element on the right (accent button, image), not by cloning the same weight. Asymmetric balance feels modern; symmetric feels formal/stable. Pick deliberately.
4. **Proximity beats decoration.** Space inside a group < space between groups (rule of thumb: between ≥ 2× within). Avoid boxes and dividers when spacing already groups.
5. **8-pt rhythm.** Spacing tokens: 4, 8, 12, 16, 24, 32, 48, 64, 96. No arbitrary 13/17/22. Section padding 64-96 desktop, 40-56 mobile.
6. **Grid:** 12 columns desktop (gutters 24), 8 tablet, 4 mobile (gutters 16). Align edges; every element sits on a column. Break the grid only for one intentional hero element.
7. **Type scale:** pick one ratio (1.200 minor third for apps, 1.250-1.333 for editorial) and stay on it. Body 16-18px, line-height 1.5-1.7, line length **45-75 characters**.
8. **Whitespace is a color.** 30-40% of a marketing page should be empty. If it feels "busy" add space before removing content.
9. **Reading patterns:** F-pattern for text/list pages (key info top-left), Z-pattern for sparse landing sections (logo → nav → hero → CTA). Place the primary CTA at the *end of the scan path*, not floating randomly.
10. **Repeat to unify.** Same radius, same shadow system, same icon stroke, same spacing steps. Consistency reads as quality faster than any effect.
11. **Align optically,** not just mathematically (round icons overshoot, play-icons shift right, large type needs negative tracking).

Diagnosing "something feels off" (symptom → cause → fix):

| Symptom | Likely cause | Fix |
|---|---|---|
| Busy / noisy | Too many focal points, too many accent uses | Cut accent to one per view; add whitespace; merge groups |
| Flat / boring | No hierarchy, only one size/weight | Increase primary size ≥ 1.5×; add one accent moment |
| Muddy / low energy | Low contrast, similar mid-tones | Push text to ≥ 7:1; separate surfaces by value, not hue |
| Unbalanced / lopsided | Weight all on one side | Counterweight with image/accent/whitespace on the light side |
| Cheap / generic | Default gray, random radii, uneven spacing | Tint neutrals, one radius scale, 8-pt spacing |
| Unfinished | Misaligned edges, orphan elements | Snap to grid; align to shared edges; fix optical alignment |

Full numeric guidance and layout recipes (landing, dashboard, mobile, form, pricing, card grid) are in `references/visual-balance-composition.md`.

---

## 4. Verify (don't skip)

```bash
# one pair
python3 scripts/contrast_check.py pair "#6B7280" "#FFFFFF"
# auto-fix a failing text color (keeps hue, moves lightness)
python3 scripts/contrast_check.py fix "#777777" "#FFFFFF" --target 4.5     # -> #767676
python3 scripts/contrast_check.py fix "#777777" "#FFFFFF" --target 7       # AAA
# audit a whole role palette or a custom pair list (exit code 1 on any AA failure)
python3 scripts/contrast_check.py check palette.json
# estimate the 60-30-10 area split of a screenshot (needs Pillow)
python3 scripts/contrast_check.py ratio screenshot.png
```

`palette.json` role keys: `bg surface text muted accent on-accent border focus error success warning` (any subset). 8-digit hex (`#RRGGBBAA`) is alpha-blended over its background before measuring. The `ratio` command is a rough heuristic; judge by eye too.

If the script cannot run (no shell), compute luminance by hand with the formula above and state that values were calculated manually.

---

## 5. Output formats

**When generating a design/palette**, always return:

1. One-line assumptions (product, mode, AA/AAA target).
2. A **role table** with hex, ratio, and result:

| Role | Token | Hex | Pair checked | Ratio | AA | AAA |
|---|---|---|---|---|---|---|
| Dominant 60 | `bg` / `text` | #F8FAFC / #0F172A | text on bg | 17.1 | ✅ | ✅ |
| Secondary 30 | `surface` / `muted` | #FFFFFF / #475569 | muted on surface | 7.6 | ✅ | ✅ |
| Accent 10 | `accent` / `on-accent` | #1D4ED8 / #FFFFFF | label on accent | 6.7 | ✅ | ❌ |

3. The token block (CSS variables, Tailwind config, or Figma variables, whichever the project uses).
4. A 3-line **composition note**: where the focal point is, where the accent lands, how the layout balances.

**When auditing existing UI**, use the report template in `references/audit-checklist.md` (score out of 100, top-5 fixes with exact values, before/after ratios). Fixes must be concrete ("change `#9CA3AF` → `#6B7280`, 2.5:1 → 4.8:1"), never "improve contrast".

**Figma:** express colors as variables with semantic names (`color/bg/default`, `color/accent/default`, `color/text/on-accent`) and a light/dark mode pair; bind fills to variables, never raw hex.

---

## 6. Anti-patterns (reject on sight)

- Light gray text on white "for elegance" (`#999`/`#AAA`, 2.3-2.8:1). 
- Accent color used for body text, for large backgrounds *and* for buttons at once.
- Two competing accents, or gradients that put text on a low-contrast stop.
- Pure `#000` on pure `#FFF` for long reading in dark mode (halation): use tinted near-black/near-white.
- Same saturated accent reused unchanged in dark mode (vibrates, fails on dark surfaces).
- Status shown by red/green only; charts distinguished only by hue.
- Gray text on a colored background (use a darker/lighter tint of that background instead).
- Focus ring removed (`outline:none`) without a replacement.
- Placeholder as the only label; placeholder at 2:1.
- Equal-weight everything (three same-size cards + three same-size buttons) with no focal point.
- Decorating with the default AI look (purple→pink gradient on white, unsolicited glassmorphism) when the brand did not ask for it.

---

## 7. Edge cases

- **Brand color fails contrast:** keep it as the *fill* or illustration color, derive a darker `accent-text` token for text/links and a matching `on-accent`. Brand is preserved, accessibility passes.
- **Photo/video backgrounds:** add a scrim (solid or gradient overlay ≥ 40-60% in the text zone) or put text on a solid panel; measure at the lightest pixel under text.
- **Non-Latin scripts (Bengali, Arabic, Devanagari, CJK):** diacritics and thin strokes lose contrast at small sizes. Use +1-2px size, line-height 1.6-1.8, avoid light font weights, and treat 4.5:1 as the floor, not the goal. RTL layouts mirror balance; re-check the focal point.
- **Colored text on colored surfaces (badges, chips):** compute each badge pair; do not assume the tint you like passes.
- **Charts/data viz:** series need ≥ 3:1 vs the background and vs neighbors *or* direct labels/patterns; use a color-blind-safe set and never rely on hue alone.
- **Slides/print/social graphics:** same ratios, but raise body text to AAA (7:1) because projectors and sunlight wash colors out.
- **User gives a palette that breaks the rules:** keep their brand, show the failing pairs with numbers, and offer the minimal adjustment that fixes them.
