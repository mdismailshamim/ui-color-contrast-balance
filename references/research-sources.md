# Research Sources (20 GitHub repos reviewed, Nov 2026)

Method: README / SKILL.md excerpts of each repo surfaced through search and fetch, compared on three axes: color ratio (60-30-10), WCAG contrast (AA/AAA), balance and composition. I did not clone and read every file in every repo, so treat "adopted" as "idea taken from what the repo publishes", and check the repo itself for the full text.

| # | Repo | What it is | Adopted here | Deliberately not copied |
|---|---|---|---|---|
| 1 | nextlevelbuilder/ui-ux-pro-max-skill | Design-intelligence skill: reasoning engine, 80 styles, 194 palettes, 130 UX rules, pre-delivery checklist, Master+Overrides persistence | Pre-delivery checklist, anti-pattern list, persisting decisions as a token file, data-driven palettes idea | Large CSV/BM25 engine (this skill stays small and numeric); its own output marks accessibility as "conditional; verify", so contrast is verified by script here |
| 2 | GithubAnant/skills | Claude plugin: "60-30-10 Color Rule" adapted from cinematic color control + Capy design-system inspector | Role framing of the three colors | Film-theory narrative; no contrast numbers |
| 3 | sickn33/antigravity-awesome-skills (design-it) | Router for 48 UI styles with 10 palettes and a 60-30-10 mapping | Idea of fixed vetted palettes instead of random neon | Its mapping puts text/accents in the 30%; this skill puts text in the 60 family and surfaces in the 30 (more consistent with measuring area) |
| 4 | practicalswan/agent-skills (frontend-design) | Color theory + 60-30-10 + React/Tailwind variables, WCAG mention | CSS-variable / Tailwind token approach, color-category thinking | Generic category lists with no ratios |
| 5 | ItsssssJack/power-design | 20 numeric design principles for decks: WCAG ≥ 4.5 (aim 7), 60-30-10, one accent per slide, never hue alone, F-pattern, line ≤ 60ch | One-accent rule, aim-for-AAA body text, never hue alone, F-pattern, numeric thresholds with citations | Slide-specific brand-extraction workflow |
| 6 | pinkpixel-dev/keyper (awesome-copilot color guide, web-design-review skill) | HTML/CSS color guide: hot/cool/neutral/binary, 60-30-10, never-use/recommended lists, gradients; web-design-review workflow | Explicit never-use lists, gradient caution | Hue-category taxonomy as a rule |
| 7 | warpirate/design-engineer | 4,100-line design skill: palette from one hex, dark/light tokens, CTA science, evals.json | "Derive full palette from one brand color", dark/light token pairs, test-scenario habit | 993-line single skill (too heavy for context) |
| 8 | spencerpauly/awesome-cursor-skills (using-ui-stack) | Structured design system: spacing scale + 60-30-10 | Spacing scale discipline | Cursor-specific packaging |
| 9 | Community-Access/accessibility-agents | WCAG 2.2 agents: AA default, AAA opt-in, "numbers live in one place", APCA flagged non-normative | AA default with AAA on request; APCA never used to pass/fail; WCAG 2.2 facts (9 new SC, 4.1.1 removed) | Multi-agent orchestration |
| 10 | jpeetz/agent-skills (accessibility-compliance-audit) | WCAG 2.2 AA audit; every violation carries SC reference, user impact, severity, fix-ready code | Report structure: SC + impact + severity + concrete fix | Framework-specific code audits |
| 11 | charlesjones-dev/ai-agent-plugins (accessibility-audit) | Audit command with version + level + scope parameters and saved dated report | Audit header with WCAG version and target level | Playwright dependency |
| 12 | majiayu000/claude-skill-registry (layout-composition-critic) | Layout critique: hierarchy, spacing, alignment, color balance; symptom to cause table; exact fixes | Symptom → cause → fix table; "make 24px → 32px" style fixes | Registry packaging |
| 13 | andrewr303/ultimate-claude-code (interface/composition) | Composition engine: typography contrast, subtle border/background shifts over "floating card soup", density balance | Surface-step and borders over heavy shadows; density balance | CLI contract/workspace machinery |
| 14 | syahiidkamil/Software-Engineer-AI-Agent-Atlas (frontend-design) | Anthropic-derived skill with expert review lens: "does the composition feel balanced", hierarchy, flow | Self-critique questions | Bold-aesthetic push (this skill is style-neutral) |
| 15 | qodex-ai/ai-agent-skills (visual-composition) | Philosophy-driven composition: minimal text, spatial expression, negative space | Whitespace as a design element | Abstract/art-poster focus; no measurable rules |
| 16 | pbakaus/impeccable | 1 skill + 20+ commands + ~27 deterministic anti-pattern rules; OKLCH, tinted neutrals, "don't use gray text on color", don't default to blue/orange | OKLCH and tinted neutrals, anti-pattern culture, critique/audit/polish stages, avoid default hues | Command surface area; Apache-2 text not copied |
| 17 | vercel-labs/web-interface-guidelines | 100+ UI rules: focus-visible, hit targets (24 / 44 px), redundant status cues, color-scheme/theme-color | Focus rules, target sizes, "don't rely on color alone" | Framework/React-specific rules |
| 18 | Dammyjay93/interface-design | Craft + memory + consistency: squint test, token test, surface elevation system, `system.md` memory | Squint test, elevation = lightness in dark mode, persisting decisions | Scope limited to dashboards/tools |
| 19 | anthropics/skills (frontend-design) | Official skill: dominant colors with sharp accents beat timid even palettes; avoid purple-gradient-on-white default | Dominant + sharp accent principle (the philosophical base of 60-30-10) | Open-ended "BOLD aesthetic" mandate |
| 20 | Myndex/apca-w3 + Myndex/SAPC-APCA | APCA reference implementation and docs: Lc scale, polarity, WCAG 2 overstates dark-color contrast | Informative APCA thresholds (Lc 75 body min, 90 preferred, 30 floor) as a secondary check only | Using APCA as a pass/fail standard (not normative) |

## Patterns found across the 20

1. **60-30-10 is everywhere but defined three different ways.** Some put text in the 30, some put it in the 60, some treat it as "three colors". This skill fixes the ambiguity: it is an **area** rule; text belongs to the dominant family; secondary = surfaces/structure; accent = attention.
2. **Accessibility is mostly stated, rarely computed.** Most design skills say "ensure WCAG contrast" with no formula, no per-state pairs, no failure examples. This skill ships a checker and verified palettes.
3. **Composition skills are either pure philosophy or pure checklists.** The best ones (layout critic, interface-design) pair a test (squint, remove-one) with exact numeric fixes. This skill keeps both.
4. **Dark mode is under-specified.** Few repos explain elevation by lightness, accent desaturation, or `on-accent` flipping. Covered in the color reference.
5. **APCA is handled responsibly only by the dedicated accessibility repos** (labeled non-normative). Same stance adopted here.
6. **Bloat is the main failure of "big" skills.** 900-line single files and 190-rule engines are strong but costly in context. This skill keeps SKILL.md small and pushes depth into references loaded on demand.

## Gaps this skill fills

- One numeric spec joining **color ratio + AA/AAA + balance/composition**.
- A **verified** contrast tool with auto-fix, palette audit and screenshot ratio estimator.
- **Five tested palettes** (AA, AAA, dark, warm, green) with measured ratios.
- Explicit handling of **hover/focus/disabled pairs, brand-color rescue, text over images, non-Latin scripts**.
- A **100-point rubric with automatic caps** so audits are comparable between projects.

## Keeping it current

- WCAG: https://www.w3.org/TR/WCAG22/ (WCAG 3.0 is still a working draft; do not switch targets).
- Re-check this skill's palettes with `scripts/contrast_check.py check` after any edit.
- If the user asks for "the latest" on WCAG 3 or APCA status, search the web first; this reference reflects the state at the date above.
