# Figma color token validation

`scripts/figma_token_validate.py` checks that a design system's color variables are **accessible, themed
correctly, and structured cleanly**. It reads the data, not the canvas, so it works for any file size.

## Contents
1. Get the data out of Figma (three routes)
2. Run it
3. What is checked
4. Token architecture it expects
5. Role mapping overrides
6. Fixing what it finds

---

## 1. Get the data out of Figma

**A. REST API (Enterprise plans only for variables):**
```bash
curl -H "X-Figma-Token: $FIGMA_TOKEN" "https://api.figma.com/v1/files/$FILE_KEY/variables/local" -o figma-variables.json
```
The script reads this response as is (`meta.variables` + `meta.variableCollections`).

**B. Plugin console (any plan).** Run this in a development plugin (Plugins > Development > New plugin) or any plugin runner. It prints JSON in the same shape as the REST response; copy it into a file:
```js
(async () => {
  const collections = await figma.variables.getLocalVariableCollectionsAsync();
  const variables = await figma.variables.getLocalVariablesAsync('COLOR');
  const out = { meta: { variableCollections: {}, variables: {} } };
  for (const c of collections) out.meta.variableCollections[c.id] = { name: c.name, modes: c.modes, defaultModeId: c.defaultModeId };
  for (const v of variables) out.meta.variables[v.id] = { name: v.name, resolvedType: v.resolvedType, variableCollectionId: v.variableCollectionId, valuesByMode: v.valuesByMode, remote: v.remote };
  console.log(JSON.stringify(out));
  figma.closePlugin();
})();
```

**C. Any export:** a variables-export plugin, Tokens Studio, Style Dictionary, or a Figma MCP variables tool that returns JSON/CSS. DTCG, Tokens Studio sets, flat `{name: hex}` and CSS custom properties are all auto-detected.

## 2. Run it

```bash
python3 scripts/figma_token_validate.py figma-variables.json                 # AA
python3 scripts/figma_token_validate.py figma-variables.json --level AAA --json report.json
python3 scripts/figma_token_validate.py tokens.json --map accent=brand/600 --map text=ink/default
python3 scripts/figma_token_validate.py src/theme.css --strict               # fail CI on warnings too
```
Exit code 1 on any error (and on warnings with `--strict`), so it can gate CI or a design-handoff step.

## 3. What is checked (per mode: Light, Dark, brand themes...)

Errors (block delivery)
- broken alias, circular alias, unparsable color
- body text, muted text, accent-as-text, label-on-accent, error/success/warning text: WCAG AA (4.5:1) or AAA (7:1) against bg/surface
- border and focus colors below 3:1 against bg/surface (WCAG 1.4.11)
- every `on-*` token against the fill it labels
- dark bg not darker than light bg (modes mis-bound)

Warnings (fix before shipping a system)
- required role missing (bg, text, accent, on-accent)
- token present in light but not dark (and vice versa)
- raw hex in the semantic layer when a primitive layer exists (should alias a primitive)
- near-duplicate colors (OKLab dE < 0.015): token sprawl
- pure #000 / #FFF body text; accent identical in light and dark; dark surface darker than bg
- more than one accent hue (one-accent rule); translucent semantic colors (contrast depends on backdrop)
- non-semantic names (`Color 1`, `Untitled`, bare hex)

## 4. Token architecture it expects

```
Primitives (1 mode)   blue/50...950, neutral/50...950          raw hex only
Semantic  (Light/Dark) color/bg/default, color/surface/default, color/text/default, color/text/muted,
                       color/accent/default, color/text/on-accent, color/border/default, color/focus/ring,
                       color/status/error|success|warning
Components (optional)  button/primary/bg -> alias to semantic
```
Components bind to semantic variables, semantic variables alias primitives, primitives hold hex. Never bind
fills to raw hex. Mode switch (Light/Dark) happens only in the semantic layer.

## 5. Role mapping overrides

The script prints the detected role map for each mode. When names are unconventional pass
`--map role=path` (paths use `/`; DTCG dots are normalised). Roles: `bg surface text muted accent on-accent border focus error success warning`.

## 6. Fixing what it finds

- Failing pair: `python3 scripts/contrast_check.py fix <fg> <bg> --target 4.5` keeps hue and moves lightness; apply it to the semantic token's primitive alias, not by overriding the semantic token with hex.
- No palette at all or a mess: `python3 scripts/palette_generate.py <brand> --format dtcg -o tokens.json`, then import with Tokens Studio or a DTCG/variables import plugin and re-run the validator.
- Brand color fails as text: keep it as fill, add `accent-text` (a darker/lighter step) for text and links.
