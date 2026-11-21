# Playwright MCP: let Claude drive a real browser for color/contrast work

Playwright MCP (`@playwright/mcp`, by Microsoft) gives an MCP client a real browser. For this skill it
is the bridge that lets Claude **open the page, switch theme/viewport, run the contrast audit, take
screenshots, and read the numbers**, instead of guessing from a description.

## Contents
1. Install (any MCP client)
2. Tools this skill uses
3. Recipe A: full contrast audit with no shell (MCP only)
4. Recipe B: audit + screenshots + analysis (MCP + shell)
5. Light/dark and viewport control
6. Limits and troubleshooting
7. When to use the plain Playwright script instead

---

## 1. Install

Requires Node.js 18+. Standard config (Claude Desktop, Cursor, VS Code, Windsurf, Gemini CLI and most clients):

```json
{ "mcpServers": { "playwright": { "command": "npx", "args": ["@playwright/mcp@latest"] } } }
```

Claude Code: `claude mcp add playwright npx @playwright/mcp@latest`
Codex: `codex mcp add playwright npx "@playwright/mcp@latest"`

Options live in the package README (`npx @playwright/mcp@latest --help`). Verify flag and tool names
against the README of the version you installed: they evolve (this file was written against the
0.0.7x series).

## 2. Tools this skill uses

| Tool | Use here |
|---|---|
| `browser_navigate` | open the URL (local dev server, staging, production, `file:///...`) |
| `browser_resize` | 360x800 / 768x1024 / 1440x900 / 320x640 (reflow) |
| `browser_evaluate` | **run `scripts/browser_contrast_audit.js`** and get the JSON report |
| `browser_take_screenshot` | PNG for `screenshot_analyze.py` / `visual_regression.py` (`fullPage`, `filename`, or an element ref) |
| `browser_snapshot` | accessibility tree: headings order, labels, roles (not a contrast tool, but confirms semantics) |
| `browser_click` / `browser_press_key` | open menus/modals/tabs so their states are audited; Tab to see focus rings |
| `browser_console_messages` | catch audit-script errors, CSP problems |
| `browser_run_code` | run a Playwright snippet, e.g. `page.emulateMedia({colorScheme:'dark'})` (if your build exposes it) |

## 3. Recipe A: full audit, MCP only (no shell needed)

1. `browser_navigate` to the page. `browser_resize` to 1440x900.
2. Read `scripts/browser_contrast_audit.js` and pass its **entire contents** as the `function` argument
   of `browser_evaluate` (it is one arrow function; it takes no arguments).
   To audit against AAA first run `browser_evaluate` with `() => { window.__CA_OPTS = { aaa: true }; }`.
3. The result is compact JSON: `summary`, grouped `textFailures` (identical fg/bg/size are merged and
   carry `count`, sample selectors and a ready-to-run `contrast_check.py fix` command), `uncertain`,
   `uiComponents`, `links`, `focus`, `targets`, `palette.painted` (area-weighted colors of what is on screen).
4. Switch theme (section 5), repeat. Repeat at 390x844 and 320x640 (`meta.hScroll` = true means horizontal scroll = reflow failure).
5. Open interactive states (menu, modal, hover via `browser_hover`, form errors) and audit again; most real failures hide in states.
6. Report with the table format from SKILL.md section 5. Fixes must contain exact hex before/after and ratios; compute replacements with `contrast_check.py fix` or by hand with the WCAG formula.

## 4. Recipe B: MCP + shell (best quality)

```text
browser_navigate  -> url
browser_resize    -> 1440x900
browser_take_screenshot (fullPage, filename: shots/home-light.png)
# theme switch (section 5)
browser_take_screenshot (fullPage, filename: shots/home-dark.png)
```
then in the shell: `python3 scripts/screenshot_analyze.py shots/home-light.png` and
`python3 scripts/visual_regression.py compare baseline/ shots/ --out diff/`.
Screenshot files are written relative to the MCP server's output directory; check the path returned by the tool.

## 5. Light/dark and viewport control

- **Viewport:** `browser_resize`.
- **Theme, option 1 (no restart):** `browser_run_code` with `async (page) => { await page.emulateMedia({ colorScheme: 'dark' }); }`.
- **Theme, option 2 (always works):** register two servers with different config files:

```json
{ "browser": { "contextOptions": { "colorScheme": "dark", "viewport": { "width": 1440, "height": 900 } } } }
```
```json
{ "mcpServers": {
  "playwright-light": { "command": "npx", "args": ["@playwright/mcp@latest", "--config", "pw-light.json"] },
  "playwright-dark":  { "command": "npx", "args": ["@playwright/mcp@latest", "--config", "pw-dark.json"] } } }
```
- **Theme, option 3 (apps with a toggle):** click the toggle with `browser_click`; the audit reports `meta.prefersDark` (OS preference) and the actually painted colors, so a class-based theme is measured correctly.
- **Forced colors / reduced motion:** `page.emulateMedia({ forcedColors: 'active' })`, `{ reducedMotion: 'reduce' }` through `browser_run_code`.

## 6. Limits and troubleshooting

- `browser_evaluate` cannot pass arguments: set options by running a tiny evaluate that assigns `window.__CA_OPTS` first.
- Text over `<img>`, `<video>`, canvas, blend modes, filters or `backdrop-filter` is returned under `uncertain`, never silently passed. Measure those from a screenshot (`screenshot_analyze.py --region`) or by eye with a scrim rule.
- Focus is checked by calling `.focus()` programmatically. `:focus-visible` rules written for keyboard only may not trigger; confirm real keyboard focus with `browser_press_key` Tab + a screenshot.
- Authenticated pages: log in once through the MCP browser (persistent profile) or use `--storage-state`.
- Cross-origin iframes cannot be inspected by in-page scripts; audit the iframe URL directly.
- Cookie banners and chat widgets add noise: dismiss them first or note them in the report.
- Large pages: the script caps list sizes (`maxList`, default 60) and groups duplicates to keep MCP output small.
- The Playwright team also ships a CLI + skills workflow aimed at coding agents. MCP is the better fit for the iterative inspect-fix-reinspect loop used here; use whichever your client supports.

## 7. Plain Playwright instead of MCP

For CI, scheduled checks, or many pages/viewports/themes at once use `scripts/browser_audit.py`
(same audit script, no MCP, writes `report.md/json` and exits non-zero on failure).
