# Audit Rubric, Checklist & Report Template

## Contents
1. 100-point rubric
2. Pre-delivery checklist
3. Audit report template
4. Severity rules
5. Fix-writing rules

---

## 1. 100-point rubric

| Area | Points | Full marks when |
|---|---|---|
| **Contrast (WCAG)** | 30 | Every text pair ≥ 4.5:1 (large ≥ 3:1), UI components/focus ≥ 3:1, all states checked. AAA body text earns +5 bonus (cap 30) |
| **60-30-10 discipline** | 20 | Roles assigned; area split within tolerance; one accent hue; ≤ 1 primary CTA per viewport; neutrals tinted; tokens used (no raw hex in components) |
| **Hierarchy & focal point** | 15 | One clear primary, 3 levels max, squint and grayscale tests pass, order = priority |
| **Balance & composition** | 10 | Weight distribution feels stable, counterweight present, grid-aligned, no orphan elements |
| **Spacing & rhythm** | 10 | 8-pt scale, group spacing > in-group spacing, consistent card/section padding |
| **Non-color cues & states** | 5 | Status has icon/text, links underlined or ≥ 3:1 + cue, focus visible, hover/active/disabled defined |
| **Dark mode / theming** | 5 | Separate tuned dark palette, passes the same pairs, elevation by lightness (N/A → full marks if no dark mode is offered) |
| **Responsive & resilience** | 5 | Works at 360/768/1024/1440, 200% zoom, long strings, non-Latin scripts |

Grades: 90-100 ship-ready | 75-89 good, fix listed items | 60-74 needs a pass | < 60 rework the system.

Automatic caps: any text pair < 3:1 caps the whole score at 70; no visible focus indicator caps at 75; color-only status caps at 80.

## 2. Pre-delivery checklist

Contrast
- [ ] Body text ≥ 4.5:1 (target ≥ 7:1 for long reading)
- [ ] Muted/secondary text ≥ 4.5:1 on *each* surface it appears on
- [ ] Placeholder and helper text ≥ 4.5:1
- [ ] Label on accent/primary button ≥ 4.5:1 in default, hover, active, focus
- [ ] Links ≥ 4.5:1 and distinguishable without color (underline)
- [ ] Input borders, checkbox/radio, toggle, icon buttons ≥ 3:1
- [ ] Focus ring ≥ 3:1, ≥ 2px, never clipped or hidden by sticky bars
- [ ] Text over images has a scrim; measured at the worst pixel
- [ ] Charts: series ≥ 3:1, labeled or patterned, color-blind safe
- [ ] Dark mode re-measured, not assumed

60-30-10
- [ ] Dominant/secondary/accent tokens named and documented
- [ ] Estimated area within 55-70 / 20-35 / 5-12 (or deliberate, stated exception)
- [ ] Exactly one accent hue; semantic colors only where state exists
- [ ] Accent reserved for CTA, active state, key data, focus
- [ ] Neutrals tinted toward the brand hue
- [ ] No raw hex in components; tokens only

Balance & composition
- [ ] One focal point (squint test)
- [ ] ≤ 3 hierarchy levels; ≥ 1.5× step between levels
- [ ] Counterweight present (image / accent / whitespace)
- [ ] Elements aligned to the grid; optical alignment checked
- [ ] Spacing from the 8-pt scale; between-group ≥ 2× in-group
- [ ] Line length 45-75ch; body ≥ 16px, line-height ≥ 1.5
- [ ] Targets ≥ 44px (touch) / ≥ 24px (pointer minimum)
- [ ] Reading order = DOM order = Tab order

Resilience
- [ ] Verified at 360, 768, 1024, 1440
- [ ] 200% zoom and 320px reflow without clipping
- [ ] Longest realistic strings and non-Latin text fit
- [ ] `prefers-reduced-motion`, `prefers-color-scheme`, `forced-colors` considered

## 3. Audit report template

```
# UI Audit: <screen/product>        Score: NN/100 (grade)   Target: WCAG 2.2 AA (+AAA for body)

## Summary (3 lines max)
<what works> | <biggest risk> | <fastest win>

## Contrast results
| Pair (state) | FG | BG | Ratio | Needs | Result |
|---|---|---|---|---|---|
| Muted text on card | #9CA3AF | #FFFFFF | 2.54 | 4.5 | FAIL -> #6B7280 (4.83) |

## 60-30-10
| Role | Estimated area | Target | Verdict |
|---|---|---|---|
| Dominant | 68% | 55-70 | OK |
| Secondary | 24% | 20-35 | OK |
| Accent | 8% | 5-12 | OK |
Notes: <accent hues found, accent misuse, untinted neutrals>

## Balance & composition
<focal point, hierarchy levels found, weight distribution, grid/spacing issues>

## Top 5 fixes (ordered by impact / effort)
1. <exact change with before -> after value and ratio>
2. ...

## Out of scope / needs manual testing
<screen reader pass, keyboard walkthrough, real device, user testing>
```

## 4. Severity rules

| Severity | Definition | Examples |
|---|---|---|
| Blocker | A user cannot perceive or operate something | Text < 3:1, focus removed, color-only error, CTA label unreadable |
| Major | Perceivable only with strain, or breaks a stated target | Body text 3-4.4:1, borders < 3:1, accent overused, no focal point |
| Minor | Polish | Off-scale spacing, inconsistent radius, tinting |
| Note | Opportunity | AAA upgrade, dark-mode refinement |

## 5. Fix-writing rules

1. Every fix has a before value, an after value, and the new ratio.
2. Prefer changing lightness, not hue; keep brand identity.
3. Fix at the token level so one change corrects every instance.
4. Re-run the pair after the change; report the measured number, not an estimate.
5. If you cannot measure (no shell), say the number was computed by hand and show the formula inputs.
6. Say what you did not check (screen reader, real devices, user testing). Automated checks catch a minority of accessibility barriers; a clean report is a floor.
