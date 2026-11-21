# Automation toolkit: workflows, CI, and honest limits

Six capabilities, one shared color engine (`scripts/colorlib.py`: WCAG luminance, OKLab/OKLCH, gamut mapping, CVD simulation).
All scripts are Python 3.8+ stdlib, except Pillow (screenshots, regression) and Playwright (live browser).

## Contents
1. Capability map
2. Pick the right tool
3. Recipes
4. CI snippets
5. Playwright Test native screenshots
6. What automation cannot judge
7. Setup

---

## 1. Capability map

| # | Capability | Tool | Needs | Output |
|---|---|---|---|---|
| 1 | Screenshot color analysis | `scripts/screenshot_analyze.py` | Pillow | palette + area share, 60-30-10 estimate, contrast of colors that touch, inferred role palette, color-blind collapse pairs |
| 2 | Figma/token validation | `scripts/figma_token_validate.py` | stdlib | per-mode contrast + hygiene report, exit code |
| 3 | Browser contrast testing | `scripts/browser_contrast_audit.js` (+ `browser_audit.py`) | a browser | text/UI/link/focus/target/reflow findings, painted palette |
| 4 | Playwright MCP | `references/playwright-mcp.md` | Node 18+ | Claude drives the browser, runs #3, captures shots for #1/#6 |
| 5 | Palette generation | `scripts/palette_generate.py` | stdlib | light+dark role palette, scales, chart colors; css/tailwind/dtcg/json |
| 6 | Visual regression | `scripts/visual_regression.py` | Pillow | pixel diff, changed regions, color drift, diff images, exit code |

Older helpers still apply: `contrast_check.py pair | fix | check | ratio`.

## 2. Pick the right tool

| The user gives / asks | Run |
|---|---|
| A brand color, "make me a palette/theme" | `palette_generate.py` -> validate with `contrast_check.py check` (the generator self-verifies) |
| A URL or localhost app, "is it accessible / check contrast" | #4 Playwright MCP (Recipe A) or `browser_audit.py` |
| A screenshot or image, "review this UI" | `screenshot_analyze.py` + visual judgment (sections 1-3 of SKILL.md) |
| Figma file / variables / tokens / CSS theme | `figma_token_validate.py` |
| "Did my change break the design?" / PR review | `visual_regression.py compare` (+ `browser_audit.py` for contrast) |
| Only a list of hex pairs | `contrast_check.py check` |
| No shell, no browser | compute by hand with the WCAG formula, say so in the report |

## 3. Recipes

**New product from one brand color**
1. `palette_generate.py "#BRAND" --level AA --format css -o theme.css` (+ `--format dtcg -o tokens.json` for Figma/Tokens Studio, `--format tailwind` for Tailwind)
2. `figma_token_validate.py theme.css` (hygiene) 
3. Compose the layout with SKILL.md section 3; apply tokens only.

**Audit a live site (best quality)**
1. Playwright MCP: Recipe A at 1440, 390, 320 widths, light + dark, plus open states.
2. For every `uncertain` item: screenshot -> `screenshot_analyze.py --region x,y,w,h`.
3. Fix with exact values (`contrast_check.py fix`), re-run until `summary.textFailNodes == 0`.
4. Report using the template in `audit-checklist.md`; paste the tool's numbers.

**Design-system handoff**
1. Export variables (see `figma-token-validation.md`), run the validator for AA and AAA.
2. Take Figma frames as PNG exports and run `screenshot_analyze.py` for balance/60-30-10 sanity.
3. Fix tokens, never individual fills.

**Release gate**
1. Baseline: `browser_audit.py URL --schemes light,dark --viewports 390x844,1440x900 --screenshots --out audit/`
2. Approve: `visual_regression.py approve audit/ baseline/`
3. Each PR: repeat step 1 into `current/`, then `visual_regression.py compare baseline/ current/ --out diff/ --ignore-aa`.

## 4. CI snippets

GitHub Actions (contrast gate + visual regression):
```yaml
name: ui-quality
on: [pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install playwright pillow && playwright install --with-deps chromium
      - run: npm ci && npm run build && (npx serve -l 4173 dist &) && sleep 3
      - run: python3 skills/ui-color-contrast-balance/scripts/browser_audit.py http://localhost:4173 / /pricing --schemes light,dark --viewports 390x844,1440x900 --screenshots --fail-on text --out audit
      - run: python3 skills/ui-color-contrast-balance/scripts/visual_regression.py compare tests/baseline audit --out diff --ignore-aa --allow-new
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: ui-quality, path: "audit\ndiff" }
  tokens:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python3 skills/ui-color-contrast-balance/scripts/figma_token_validate.py design/tokens.json --level AA --strict
```
Note: `browser_audit.py` names files `<url-slug>__<scheme>__<WxH>.png`; keep baselines in the same naming.
Render the same browser on the same OS image for baselines and checks, or fonts will differ.

## 5. Playwright Test native screenshots (JS/TS projects)

```ts
// playwright.config.ts
export default defineConfig({
  expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.001, animations: 'disabled' } },
  projects: [
    { name: 'light', use: { colorScheme: 'light', viewport: { width: 1440, height: 900 } } },
    { name: 'dark',  use: { colorScheme: 'dark',  viewport: { width: 1440, height: 900 } } },
  ],
});
// test: await expect(page).toHaveScreenshot('home.png', { fullPage: true });
```
Update baselines with `npx playwright test --update-snapshots`. Use `visual_regression.py` when you also want
**color-drift reporting** or when the screenshots come from MCP, Figma exports, or non-JS stacks.

## 6. What automation cannot judge (say this in reports when relevant)

- Text on photos, video, blur, blend modes: measured only on flat approximations; use a scrim and verify by eye/screenshot.
- Screenshot role inference (bg/text/accent) is a heuristic; confirm the mapping before trusting `check` on it.
- Pixel adjacency flags *where colors touch*, not whether a thing is text. Thin-feature = likely text/icon.
- Focus check uses programmatic focus; confirm real keyboard focus once by tabbing.
- Contrast ratio is necessary, not sufficient: font weight, size, spacing, language and context still matter (non-Latin scripts: see SKILL.md section 7).
- WCAG 2.x ratios decide pass/fail. APCA is not part of WCAG 2.2.
- Color-blind simulation is an approximation (Machado 2009, severity 1.0); keep redundant cues (icon/label/pattern).

## 7. Setup

```bash
pip install pillow playwright        # add --break-system-packages in managed Pythons
playwright install chromium          # only for browser_audit.py
node -v                              # >= 18 for Playwright MCP
```
Everything else is stdlib. Run scripts from the skill folder or by absolute path.
