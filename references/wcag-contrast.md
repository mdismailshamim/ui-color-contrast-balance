# WCAG 2.2 Contrast & Related Criteria

## Contents
1. The formula
2. Criteria table (AA and AAA)
3. What counts as "large text"
4. What is measured against what
5. Edge cases and gotchas
6. Testing method (design review and code)
7. APCA and WCAG 3 (informative only)

---

## 1. The formula

```
channel = value/255
linear  = channel <= 0.04045 ? channel/12.92 : ((channel + 0.055)/1.055) ^ 2.4
L       = 0.2126*R_lin + 0.7152*G_lin + 0.0722*B_lin
ratio   = (L_lighter + 0.05) / (L_darker + 0.05)        // 1:1 to 21:1
```

Ratios are not rounded up: 4.48 fails 4.5. Known edge: `#777777` on white is 4.48:1 (fails AA text), `#767676` is 4.54:1 (passes).

## 2. Criteria table

| SC | Name | Level | Requirement (design-relevant) |
|---|---|---|---|
| 1.4.1 | Use of Color | A | Color is not the only way to convey information, an action, a state or a distinction |
| 1.4.3 | Contrast (Minimum) | AA | Text ≥ 4.5:1; large text ≥ 3:1 |
| 1.4.6 | Contrast (Enhanced) | AAA | Text ≥ 7:1; large text ≥ 4.5:1 |
| 1.4.11 | Non-text Contrast | AA | UI component boundaries/states and meaningful graphics ≥ 3:1 vs adjacent colors |
| 1.4.10 | Reflow | AA | No two-direction scroll at 320 CSS px width / 400% zoom |
| 1.4.4 | Resize Text | AA | Text resizes to 200% without loss of content/function |
| 1.4.12 | Text Spacing | AA | Content survives line-height 1.5, paragraph spacing 2×, letter-spacing 0.12em, word-spacing 0.16em |
| 1.4.13 | Content on Hover or Focus | AA | Tooltips/popovers dismissible, hoverable, persistent |
| 2.4.7 | Focus Visible | AA | Keyboard focus indicator is visible |
| 2.4.11 | Focus Not Obscured (Minimum) | AA | Focused element not entirely hidden by sticky headers/footers/modals |
| 2.4.12 | Focus Not Obscured (Enhanced) | AAA | Focused element not hidden at all |
| 2.4.13 | Focus Appearance | AAA | Focus indicator area at least a 2 CSS px perimeter, with ≥ 3:1 change of contrast between focused and unfocused states |
| 2.5.8 | Target Size (Minimum) | AA | Pointer targets ≥ 24×24 CSS px (with spacing exceptions) |
| 2.5.5 | Target Size (Enhanced) | AAA | Targets ≥ 44×44 CSS px |
| 1.4.8 | Visual Presentation | AAA | Line length ≤ 80 characters, line-height ≥ 1.5, paragraph spacing ≥ 1.5× line height, no justified text, user-selectable colors |

WCAG 2.2 removed 4.1.1 Parsing and added nine criteria (including 2.4.11, 2.4.13, 2.5.7, 2.5.8, 3.3.7, 3.3.8). Conformance targets for most laws and contracts remain **WCAG 2.x AA**.

## 3. What counts as "large text"

- ≥ 18 pt regular = **24 CSS px** regular, or
- ≥ 14 pt bold = **≈ 18.66 CSS px** bold (600+ weight).

Anything smaller needs the normal-text ratio. Do not call 16-17px text "large". Do not use "large text" to excuse a hero subtitle at 20px regular.

## 4. What is measured against what

| Item | Foreground | Background |
|---|---|---|
| Body/paragraph text | text color | the surface directly behind it (not the page, if it is on a card) |
| Text on a button | label color | the button fill, in each state |
| Link inside a paragraph | link color | the surface; **plus** ≥ 3:1 vs surrounding text color if relying on color alone (underline is the safe solution) |
| Input border | border color | the surface around the input (or the input fill if the border is the only boundary) |
| Icon button / meaningful icon | icon color | surface |
| Focus ring | ring color | both the component's neighbors and the component itself; test against the page and the surface |
| Chart bar / line / marker | series color | chart background, and against the neighboring series if distinguished by color |
| Placeholder text | placeholder color | input fill. It is text: needs 4.5:1 |
| Selected/active tab, pressed, checked | indicator | adjacent colors; the *state change* itself must be perceivable at 3:1 |

Exemptions: inactive (disabled) controls, pure decoration, logos/wordmarks, incidental text in a photo. Still keep disabled controls recognizable (not below ~2:1) for usability.

## 5. Edge cases and gotchas

- **Text over images, video, gradients:** measure at the *worst* background point under the text. Prefer a scrim, solid panel, or text-shadow-free layout. A 40-60% dark overlay in the text zone is a safe default for white text.
- **Semi-transparent colors:** blend over the real background first (the script does this for `#RRGGBBAA`), then measure.
- **Hover / active / visited / selected / focus:** each is a separate pair. A hover color that gets *lighter* on a light page often fails.
- **Brand colors:** keep the brand as fill, derive a text-safe shade (see color reference). Logos are exempt but nearby text is not.
- **Dark mode:** WCAG 2.x ratios over-credit very dark colors, so dark UIs can pass numerically but still feel low-contrast for small light-weight text. Use weight 400+ and ≥ 7:1 for body text; verify visually on a real screen.
- **Large touch-target icons:** a 24px glyph in a 44px hit area still needs the glyph at 3:1 vs its surface.
- **Zoom/reflow:** fixed-height containers clip text. Use min-height, rem/em, and test at 200% and at 320px width.
- **Disabled text in forms:** exempt, but "read-only" text is not disabled and must pass.
- **Error identification (3.3.1):** error text color + icon + message, with the field outlined at ≥ 3:1.
- **Color-only legends (charts, maps):** add labels, patterns, or markers.
- **Print/projector/sunlight:** target AAA for presentation and outdoor mobile.

## 6. Testing method

Design review (no code):
1. List every foreground/background pair on the screen, by state.
2. Compute ratios (script: `contrast_check.py pair FG BG` or `check palette.json`).
3. Mark each as AA text / AA large / AA UI / AAA text.
4. Re-test in dark mode and on image backgrounds.
5. Squint + grayscale screenshot test for hierarchy independent of hue.

Code review additions:
- Search for `outline: none`/`outline: 0` without `:focus-visible` replacement.
- Search hex values lighter than `#767676` used for text on white.
- Check `prefers-color-scheme`, `prefers-contrast`, `forced-colors` handling (use system colors for the border/outline in forced-colors mode).
- Run an automated tool (axe-core, Lighthouse, WAVE, Stark): they find a minority of issues; a clean report is a floor, not proof. Manual keyboard and screen-reader pass still required.

## 7. APCA and WCAG 3 (informative only)

- **APCA** (Accessible Perceptual Contrast Algorithm, Myndex) is a candidate method under discussion for WCAG 3. It returns a signed lightness-contrast value `Lc` (0-106) that depends on polarity, font size, and weight.
- WCAG 3.0 is a working draft; APCA is **not normative** in WCAG 2.2 or any W3C standard.
- Published APCA guidance (Myndex "Bronze simple" levels): `Lc 75` is a minimum for body text, `Lc 90` preferred; `Lc 60` for larger content text; `Lc 45` for large headlines; `Lc 30` as an absolute floor for spot/non-text. These are not equivalent to WCAG 2.x levels and do not replace them.
- Practical use: treat APCA only as a secondary perceptual check for dark mode and thin fonts. Never use an APCA number to pass or fail a deliverable that must meet WCAG 2.x.
