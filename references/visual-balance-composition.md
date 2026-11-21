# Visual Balance & Composition Reference

## Contents
1. Visual weight model
2. Hierarchy system
3. Balance types and how to choose
4. Grid, spacing, and rhythm (numbers)
5. Typography for balance
6. Layout recipes (landing, dashboard, mobile, form, pricing, card grid)
7. Responsive balance
8. Self-critique protocol (squint, grayscale, remove-one)
9. Fix catalog

---

## 1. Visual weight model

An element's pull on the eye = **size + contrast with its surroundings + saturation + isolation (whitespace around it) + position (top-left and optical center pull more) + density/texture + motion**.

| Heavy | Light |
|---|---|
| Large, dark on light (or bright on dark), saturated, isolated, near optical center, has a face/photo | Small, low contrast, muted, crowded by neighbors, at the edges |

Use it to *spend* weight deliberately: the primary element gets most signals, tertiary elements get none.

## 2. Hierarchy system

Three levels maximum per view.

| Level | Count | How it earns attention |
|---|---|---|
| Primary | 1 | Largest size, highest contrast, most whitespace, usually carries the accent |
| Secondary | 2-4 | Medium size, strong text color, no accent fill |
| Tertiary | many | Smallest, muted (but ≥ 4.5:1), grouped tightly |

Separation rules:
- Adjacent levels differ by ≥ 1.5× in type size, or by a clear weight step (400 → 600+) plus a color step.
- Use **at most two** differentiators per step (size + weight, or size + color). Using four makes it noisy.
- Only one element per view gets the accent *fill*. Everything else uses outline, text, or tinted surfaces.
- Order must match importance: reading order in DOM = visual order = priority order.

## 3. Balance types and how to choose

| Type | Feel | Use for | How |
|---|---|---|---|
| Symmetrical | Stable, formal, trustworthy | Banks, legal, government, certificates | Mirror weight across a central axis |
| Asymmetrical | Dynamic, modern, editorial | Startups, creative, product pages, marketing | Counterweight a heavy block with a smaller but vivid/isolated one; balance like a seesaw (weight × distance from center) |
| Radial | Focus, ceremony | Dashboards with a hero metric, onboarding, logos | Elements radiate from a center focal point |
| Mosaic / grid | Even, scannable | Catalogs, galleries, bento | Equal cells, one or two larger "anchor" cells for variety |

Test: cover half the layout with your hand. If one side feels like it would "tip", the weights are off. Fix by moving weight (accent, image, or whitespace), not by adding clutter.

## 4. Grid, spacing, and rhythm (numbers)

| Item | Value |
|---|---|
| Spacing scale | 4, 8, 12, 16, 24, 32, 48, 64, 96, 128 |
| Inside-group gap vs between-group gap | between ≥ 2× inside (e.g. 8 inside, 24-32 between) |
| Section padding (marketing) | 80-128 desktop, 48-64 mobile |
| Card padding | 16-24 |
| Page margins | 24-32 mobile, 48-96 tablet/desktop; max content width 1120-1280 |
| Columns | 12 (desktop, gutter 24), 8 (tablet, gutter 16-24), 4 (mobile, gutter 16) |
| Max line length | 45-75 characters (≈ 60-70ch; set `max-width: 65ch`) |
| Touch targets | ≥ 44×44, spacing ≥ 8 between adjacent targets |
| Corner radius | One scale: 4, 8, 12, 16, full. Nested radius = outer − padding |
| Icon stroke | One weight everywhere (1.5 or 2 px at 24px) |
| Shadow system | 3 levels max (sm/md/lg), same light direction |
| Whitespace share | 30-40% of a marketing page; 20-30% of a dense app screen |

Rhythm rule: repeating items (cards, rows, sections) use the *same* spacing. Break rhythm only to emphasize one thing.

Alignment: every element's left edge aligns to a column or to another element's edge. Optical fixes: round shapes overshoot ~2-3%, play icons shift right, large headlines need tighter tracking (−1 to −3%), all-caps labels need +4-8% tracking.

## 5. Typography for balance

| Use | Size (desktop / mobile) | Weight | Line-height |
|---|---|---|---|
| Display / hero | 56-72 / 36-44 | 600-800 | 1.05-1.15 |
| H1 | 40-48 / 30-34 | 600-700 | 1.15-1.25 |
| H2 | 28-32 / 24-26 | 600 | 1.25 |
| H3 | 20-24 / 18-20 | 600 | 1.3 |
| Body | 16-18 / 16 | 400 | 1.5-1.7 |
| Caption/label | 12-14 / 12-14 | 500 | 1.4 |

- One type scale ratio: 1.200 (apps), 1.250 (balanced), 1.333 (editorial/marketing).
- Two typefaces max (one for display, one for text), or one family with weight contrast.
- Contrast of style creates hierarchy: pair a heavy display with a calm text face; do not pair two similar fonts.
- Bengali, Arabic, Devanagari, Thai: add 1-2px to size and 0.1-0.2 to line-height; pick a face designed for screens (e.g. Noto family, Hind Siliguri, Tiro); avoid weights below 400.
- Avoid widows/orphans in headings (`text-wrap: balance`), but never depend on it.

## 6. Layout recipes

**Landing page (Z/F scan):**
1. Nav (low weight) → Hero: left = headline (primary) + sub (secondary) + one CTA; right = visual counterweight (image/product shot).
2. Proof strip (logos, numbers) in tertiary weight.
3. Features: 3-column or bento with one anchor cell; icon + title + two lines.
4. Social proof / case study as a full-width band (secondary surface).
5. Pricing/CTA band: the only second place accent fills heavily.
6. Footer: tertiary, dense but readable.
Alternate background (dominant ↔ secondary) every section to create rhythm without extra color.

**Dashboard:**
- Left nav (secondary surface, narrow) + top bar (low weight) + content on dominant bg.
- Hero metric row: 3-4 KPI cards, the most important one 1.5× wider or larger number.
- Charts: one primary chart ≥ 2/3 width; secondary charts smaller. Accent color only on the data that matters; gray/neutral for context series.
- Tables: zebra off, row dividers at low contrast (decorative) but text 4.5:1+, header row lightly separated.
- Density: 8-pt rhythm, row height 40-48 (compact 32-36 only on desktop).

**Mobile app screen:**
- Single column, 16-20 margins. Primary action in the thumb zone (bottom, ≥ 48 high).
- Focal element in the top third; content scrolls beneath a quiet header.
- Bottom nav 4-5 items, active item uses accent + label (not color alone).

**Form / checkout:**
- One column, labels above fields, 24 between fields, 40-48 field height, 1 primary CTA aligned with the field edge, secondary link text-only.
- Error state: border + icon + message in error color, announced to screen readers.

**Pricing:**
- 3 plans; the recommended plan gets the accent border/badge and is 8-12% taller or elevated; the others stay on secondary surfaces. Do not accent all three.

**Card grid:**
- Equal width cards, equal internal padding, same image ratio (16:9 or 4:3), one action per card, titles clamped to 2 lines. Hover lifts by shadow step, not by color change alone.

## 7. Responsive balance

- Reflow order = priority order. On mobile the focal element stays first; the counterweight (image) moves below or becomes a background with a scrim.
- Scale spacing with a fluid clamp (`clamp(16px, 4vw, 48px)`), not by shrinking type below 16px.
- Check four widths: 360, 768, 1024, 1440. Verify focal point and accent budget at each.
- Containers use `min-height`, not fixed height; allow text to grow 200%.

## 8. Self-critique protocol

Run before delivering, answer each:

1. **Squint test:** blur the screen. Is there one clear winner and a clear second?
2. **Grayscale test:** desaturate. Does hierarchy survive without hue?
3. **Remove-one test:** remove the least necessary element. If nothing is lost, delete it permanently.
4. **Thumb/cover test:** cover half. Does either side tip?
5. **Rhythm test:** are there any spacing values not on the scale? Any misaligned edge?
6. **Accent audit:** count accent uses. More than 3 distinct accent *fills* in a viewport → demote.
7. **Reading-order test:** Tab through the page; does focus order match the visual order?
8. **Real-content test:** replace placeholder text with the longest realistic strings (and Bengali/Arabic if relevant). Does the layout hold?

## 9. Fix catalog

| Problem | Concrete fix |
|---|---|
| Hero lacks hook | Headline to 56-72px weight 700+, sub to 18-20 at 70% contrast (still ≥ 4.5:1), single CTA, remove secondary CTA |
| All cards look identical and dull | Make one card an anchor (2× span), vary only size, not decoration |
| Page feels long and monotone | Alternate bg tokens by section; vary layout between 3-col, split, and full-bleed band |
| Cramped | Raise spacing one step up the scale (16 → 24, 24 → 32) before touching content |
| Too many borders | Replace borders with spacing or a one-step surface change |
| Weak CTA | Accent fill + `on-accent` ≥ 4.5:1, ≥ 44px height, 24-32px horizontal padding, whitespace ≥ 24 around it, one per viewport |
| Chart noise | Mute context series to neutral, accent one series, direct-label lines |
| Misaligned feel | Snap to 8-pt grid; align left edges of headline, body, and CTA |
| Heavy, "too much" | Reduce number of weights/sizes in use (target ≤ 3 sizes and ≤ 2 weights per section) |
