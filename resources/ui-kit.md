# AI Engineering on Azure — UI Kit

> **Purpose.** The single source of truth for the visual language of every
> asset in this repo: the session guideline pages in `docs/`, and any demo UI
> in `code/`. It exists so that anything authored later — by Lucian or by an AI
> agent — reads as *the same product*, not a new page each time.
>
> **Audience.** Whoever is about to build a session doc, a slide-like HTML
> page, or a demo screen. Read **Quick reference** first; dive into a section
> only when you need the detail.
>
> **Source of truth for tokens.** [`resources/theme.css`](./theme.css) — the
> `:root` block. Everything here is derived from those variables. When in
> doubt, open that file. Never hardcode a hex in markup; reference a token.
>
> **Stack.** Plain HTML + vanilla CSS custom properties. No framework, no build
> step. A page is stunning by *linking one stylesheet* and using these classes.

---

## Quick reference

| Need | Reach for |
|---|---|
| A new session page | Copy [`docs/session-template.html`](../docs/session-template.html) |
| The stylesheet | `<link rel="stylesheet" href="../resources/theme.css">` |
| The page shell (side menu, sections, footer, jump buttons) | `.layout` + `.side-nav` + `.doc-section` + `.page-nav` + `.site-footer` + `nav.js` (§8) |
| The agenda time-split donut | `.chart` + `--chart-*` tokens (§9 — validated hexes, don't improvise) |
| A hierarchy / flow diagram | `.diagram` + `.dg-*` boxes (§9) |
| A standalone concept explainer | New page `docs/ref-<slug>.html`, same shell, brand "Reference" |
| A page header band (theme-aware: light on light, navy on dark) | `.hero` (with `.eyebrow`, `h1`, `p`) |
| A dark island inside a light page | `.panel-dark` |
| A standard panel | `.card` (add `.hover`, or `.card--accent` for a top gradient) |
| A KPI / number tile | `.stat` → `.stat__value.gradient-text` + `.stat__label` |
| A status / label chip | `.badge .badge--{cyan\|teal\|crimson\|coral\|gold\|navy}` |
| A note / warning / tip box | `.callout .callout--{info\|tip\|warn\|danger\|success}` |
| A primary call-to-action | `.btn .btn-primary` (crimson→coral gradient) |
| A "live / AI" accent button | `.btn .btn-accent` (cyan→teal gradient) |
| A code sample with a filename tag | `.code-block` → `.code-block__label` + `<pre>` |
| A data table | `.table-wrap` wrapping a `<table>` |
| A big gradient headline word | `.gradient-text` on a `<span>` |
| A responsive column grid | `.grid .grid-2` / `.grid-3` / `.grid-auto` |
| Enter animation | `.animate-in` on stacked children |

---

## 1. Palette

The locked brand palette. **Primary** carries the identity; **secondary** extends it for status, depth and warmth.

| Role | Token | Hex | Where it lives |
|---|---|---|---|
| **Primary** | | | |
| Charcoal / ink | `--c-ink` | `#2c2d2f` | Body text on light, dark UI text |
| Electric cyan | `--c-cyan` | `#0de7e7` | The signature accent — glows on navy, focus rings, "AI/live", gradient start |
| Crimson | `--c-crimson` | `#c73a52` | Primary CTA, emphasis, danger |
| Paper | `--c-paper` | `#eeeeee` | Light surfaces, text on dark |
| **Secondary** | | | |
| Teal | `--c-teal` | `#1cb9c8` | Links & accents on light (cyan is too pale for text), gradient partner |
| Deep navy | `--c-navy` | `#001240` | Dark canvas, hero background |
| Coral | `--c-coral` | `#ed6a5a` | Warm accent, warnings, CTA gradient tail |
| Slate | `--c-slate` | `#292f36` | Code panels, secondary dark surface |
| Gold | `--c-gold` | `#e4c02e` | Tips, attention, highlights |

**Readability rule.** Raw cyan (`#0de7e7`) is beautiful on navy but unreadable as text on white. On **light** surfaces, accent text/links use `--c-teal-ink` (`#0e7f8a`); on **dark** surfaces they use raw cyan. The semantic token `--accent` already flips for you — use it and stop thinking about it. The same applies to gradient **text**: `.gradient-text` paints the per-theme `--grad-text` (light: teal-ink→navy · dark: cyan→teal), so it stays readable in both themes. Never point text at `--grad-accent` directly — that pair is for buttons and strips.

### Signature gradients (tokens)

| Token | Stops | Use |
|---|---|---|
| `--grad-accent` | cyan → teal | Accent buttons, card top-strips (surfaces, not text) |
| `--grad-text` | light: teal-ink → navy · dark: cyan → teal | **Text** gradients — what `.gradient-text` uses; flips per theme |
| `--grad-cta` | crimson → coral | Primary CTAs |
| `--grad-hero` | navy → slate | Dark hero / dark panels |
| `--grad-line` | cyan → teal → crimson | Thin decorative accent strips |

There is **no green** in this palette by design — "success" reads as **teal**, "warning" as **gold/coral**, "danger" as **crimson**. Don't introduce off-palette functional colours.

---

## 2. Theming (light / dark)

`theme.css` ships **light as the default** (best for long reading — the session guidelines) with a full **dark** override.

```html
<html data-theme="light">   <!-- force light -->
<html data-theme="dark">    <!-- force dark (keynote / demo) -->
<html>                      <!-- follow the OS setting -->
```

- **Long guideline docs → light** (`data-theme="light"`), but open them with a `.hero` band so they still land with impact.
- **Demos, slide-style pages → dark** (`data-theme="dark"`) — cyan on navy is the money shot.
- **`.hero` is theme-aware**: airy paper with ink text on light, the navy aurora on dark. The one component that stays dark in every theme is `.panel-dark` — the deliberate dark island (use sparingly, e.g. a closing band).

A one-line toggle (optional), drop before `</body>`:

```html
<button class="btn btn-outline" onclick="document.documentElement.dataset.theme =
  document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'">Toggle theme</button>
```

---

## 3. Tokens: radii, shadows, type

- **Radii.** `--r-xs 6` · `--r-sm 9` · `--r 12` · `--r-lg 16` (cards) · `--r-xl 22` (hero) · `--r-pill`. Cards/hero are the signature soft-rounded shapes.
- **Shadows.** `--shadow-soft` (resting) → `--shadow-lift` (hover / elevated). On dark, `--glow` adds a cyan halo — reserve it for accent buttons and "live" elements, never body chrome.
- **Type.** `--font-sans` = Inter → system-ui fallback; `--font-mono` = JetBrains Mono → system mono. Headings are `700` with `-0.02em` tracking (baked in). Fluid sizes via `clamp()` — don't hardcode heading `font-size`.
- **Eyebrow label.** `.eyebrow` — uppercase, letter-spaced, accent-coloured kicker above a title. Use once per section head.

---

## 4. Components

### Hero / page header

```html
<header class="hero">
  <span class="eyebrow">Session 2 · Azure AI Foundry</span>
  <h1>LLM Foundations &amp; the <span class="gradient-text">Model Catalog</span></h1>
  <p>From attention to inference — what's actually behind the endpoint, and how to choose.</p>
</header>
```

The hero is **theme-aware**: on light pages it's an airy paper gradient with ink text and soft auroras; on dark it paints the navy→slate gradient with the cyan aurora and crimson counter-glow. `.gradient-text` inside `h1` clips the per-theme `--grad-text` to a word — readable in both themes.

### Card

```html
<article class="card card--accent hover">
  <h3>Reference architecture</h3>
  <p class="card__meta">Session 1 · 20 min</p>
  <p>Direct inference, RAG, agentic — what each costs and where it breaks.</p>
</article>
```

`.card` is **the** panel. Modifiers: `.hover` (lift on hover), `.card--accent` (cyan→teal top strip), `.card--cta` (crimson strip), `.card--gold` (gold strip). **One accent per row** — don't make a rainbow. Wrap cards in `.grid .grid-3` for a row.

### Stat tile

```html
<div class="card stat">
  <span class="stat__value gradient-text">17.5h</span>
  <span class="stat__label">Module volume</span>
</div>
```

### Badges

```html
<span class="badge badge--cyan">Foundry</span>
<span class="badge badge--gold">Hands-on</span>
<span class="badge badge--crimson">Blocker</span>
```

Tones: `cyan`, `teal`, `crimson`, `coral`, `gold`, `navy`. Keep the label short. They re-tint automatically in dark mode.

### Buttons

```html
<a class="btn btn-primary" href="#">Start the lab</a>     <!-- crimson→coral -->
<a class="btn btn-accent"  href="#">Open in Foundry</a>   <!-- cyan→teal, glows -->
<a class="btn btn-outline" href="#">Docs</a>
<button class="btn btn-ghost">Skip</button>
```

`btn-primary` = the one main action per view. `btn-accent` = the "AI / live / launch" action.

### Callouts

```html
<div class="callout callout--tip">
  <p class="callout__title">Pro tip</p>
  <p>Keyless auth from S1 — no lab ever hardcodes a key.</p>
</div>
```

Variants → meaning: `info` (cyan, neutral note), `tip` (gold, do-this), `success` (teal, done/good), `warn` (coral, careful), `danger` (crimson, will-break). Uses `color-mix` for the tinted fill — modern browsers only (fine for local/demo).

### Code

```html
<div class="code-block">
  <span class="code-block__label">client.py</span>
  <pre><code>from azure.ai.inference import ChatCompletionsClient
client = ChatCompletionsClient(endpoint, credential)</code></pre>
</div>
```

Inline `<code>` gets an accent-tinted chip. Blocks scroll horizontally on overflow — never let a page scroll sideways because of a code line. (Do your own syntax highlighting later with Prism/Shiki if wanted; the base style is clean without it.)

### Table

```html
<div class="table-wrap">
  <table>
    <thead><tr><th>Session</th><th>Date</th><th>Focus</th></tr></thead>
    <tbody>
      <tr><td>S1</td><td>Wed 22 Jul</td><td>Reference architecture</td></tr>
    </tbody>
  </table>
</div>
```

Always wrap tables in `.table-wrap` so they scroll on small screens instead of blowing out the layout.

---

## 5. Layout & rhythm

- `.container` — centered, max `1080px`, fluid side padding. Wrap page content in it.
- `.section` — vertical breathing room between blocks.
- `.stack > * + *` — uniform vertical spacing for a column of elements.
- `.prose` — caps line length at `72ch` for readable body copy.
- Grids: `.grid` + `.grid-2` / `.grid-3` / `.grid-auto` (auto-fit min-220px). All collapse to one column under 760px.
- `.animate-in` — a 400ms rise-in; stagger is automatic for the first five siblings. Respects `prefers-reduced-motion`.

---

## 6. Do / Don't

| ✅ Do | ❌ Don't |
|---|---|
| Reference tokens (`var(--accent)`, `--surface`) | Hardcode `#0de7e7` in a style attribute |
| Let `--accent` flip per theme | Use raw cyan as text on white (unreadable) |
| Open pages with a `.hero` | Start with a bare `<h1>` on flat background |
| One accent strip per card row | A different `card--*` colour on every card |
| Wrap tables/code in a scroll container | Let a long line force horizontal page scroll |
| `btn-primary` once per view | Three primary CTAs competing |
| Keep success=teal, warn=gold, danger=crimson | Introduce an off-palette green/blue |
| Reuse `session-template.html` | Re-derive page scaffolding from scratch |

---

## 7. Starting a new page (recipe)

1. Copy `docs/session-template.html` to `docs/sessions/sNN-<slug>.html`.
2. Set `data-theme` (`light` for guidelines, `dark` for demos).
3. Fill the `.side-nav` — one `.side-nav__link` per slide `id`, in page order.
4. Fill the sections: `#overview` (hero: title, subtitle, day summary, badges), `#agenda`
   (timed table with format badges + the time-split donut), `#outcomes`, one `.doc-section`
   per topic — **tutorial-length prose, not slides** — then
   `#conclusions` · `#takeaways` · `#references` · `#assignment`.
5. Update the `.site-footer` line and keep the `.page-nav` buttons and the
   `<script src="../resources/nav.js">` include untouched.
6. Keep the `<link>` to `../resources/theme.css` — never inline the palette.
7. **Every visible string must be student-ready** — these pages go on a shared screen.
   No internal notes, planning talk or mentor-coordination content.
8. Open in a browser at 375px and 1280px to confirm nothing scrolls sideways.

**When this doc drifts from the code, the code wins** — `theme.css` is the truth. If you invent a pattern used in 3+ pages, add it to `theme.css` and document it here.

---

## 8. Page shell: side-nav, doc-sections, page-nav, fixed footer

Every `docs/` page shares one chrome, styled by `theme.css` §17 and driven by
[`resources/nav.js`](./nav.js) (vanilla, no dependencies):

```html
<body>
  <div class="layout container">
    <aside class="side-nav">
      <p class="side-nav__brand">Session 1<small>AI Engineering on Azure</small></p>
      <a class="side-nav__link" href="#overview">Overview</a>
      <span class="side-nav__group">Today's topics</span>
      <a class="side-nav__link" href="#topic-1">Topic one</a>
      …
    </aside>
    <main>
      <section id="overview" class="doc-section"> … </section>
      <section id="topic-1" class="doc-section"> … </section>
      …
    </main>
  </div>
  <nav class="page-nav">
    <button class="btn" data-nav="up">↑</button>
    <button class="btn" data-nav="down">↓</button>
    <button class="btn" data-nav="theme">◐</button>
  </nav>
  <footer class="site-footer">Session 1 · … · Libra Bank Academy</footer>
  <script src="../resources/nav.js"></script>
</body>
```

- **`.layout`** — grid: 240px sticky sidebar + content; collapses to one column ≤900px
  (the side-nav hides on small screens).
- **`.side-nav`** — the persistent left menu. `nav.js` highlights the link whose section is
  on screen (`.is-active`). Use `.side-nav__group` for small uppercase group labels.
- **`.doc-section`** — a document section: **tutorial-length, flows at content height** —
  as long as the material needs. `nav.js` targets `main > section[id]`, so the ↑/↓ buttons
  and the side-nav jump between sections regardless of their length.
- **`.page-nav`** — fixed bottom-right stack: `data-nav="up" | "down"` jump to the
  previous/next section, `data-nav="theme"` toggles light/dark. `nav.js` wires all three.
- **`.site-footer`** — the persistent fixed footer bar (height `--footer-h`); `.layout`
  reserves the space so content never hides beneath it.

**Register rule (content, not CSS).** These pages are official course material presented on
a shared screen: multi-paragraph technical prose with precise terminology, structured by h3
subsections, tables, diagrams and code. **Cards are for summary content only** (outcomes,
takeaways, link indexes) — never for body content.

**Agenda format badges** (convention, no extra CSS — must rhyme with the chart tokens in §9):
`Theory` = `badge--navy` · `Walkthrough` = `badge--cyan` · `Live coding` = `badge--crimson` ·
`Lab` = `badge--gold` · `Q&A` / `Discussion` = `badge--coral` · `Break` = plain text (—).

---

## 9. Charts & diagrams

### The agenda donut (`.chart`, `--chart-*`)

Each session's agenda table is followed by a donut of the 150′ split by format. The slice
colours are **derived chart steps** — the raw brand colours fail as area fills (too dark,
too pale, or CVD-confusable). These hexes passed the dataviz six-check validator in **both**
themes on their respective card surfaces, in adjacent-pair mode:

| Token | Light | Dark | Format |
|---|---|---|---|
| `--chart-theory` | `#4a63d0` | `#5a74e8` | Theory |
| `--chart-walkthrough` | `#17a3b8` | `#17a3b8` | Walkthrough |
| `--chart-coding` | `#a62c43` | `#a62c43` | Live coding |
| `--chart-lab` | `#b8940e` | `#ad8a0d` | Lab |
| `--chart-qa` | `#ed6a5a` | `#e05747` | Q&A / Discussion |
| `--chart-break` | `#8f959e` | `#3a4a63` | Break (neutral) |

Rules: **ring order is fixed** — Lab → Live coding → Theory → Walkthrough → Q&A → Break
(pages with fewer formats keep the same relative order); slices are SVG `<path>` arcs with
`stroke="var(--surface)" stroke-width="2"` gaps and a `<title>` hover each; the centre shows
the total; the legend lists every slice with swatch + "Format — N′ (P%)" **in text tokens,
never the series colour**; the agenda table above stays the accessible data view.
**If you change any chart hex, re-run the dataviz palette validator before shipping.**
Copy the markup from `session-template.html` and recompute the arc paths for the session's
minutes.

### Diagrams (`.diagram`, `.dg-*`)

Token-true box diagrams in plain HTML — no images, theme-aware by construction:

```html
<div class="diagram">
  <div class="dg-row">
    <div class="dg-box">Input</div>
    <span class="dg-arrow">→</span>
    <div class="dg-box dg-box--accent">Process</div>
    <span class="dg-arrow">→</span>
    <div class="dg-box">Output</div>
  </div>
  <p class="diagram__caption">One line stating what the diagram shows.</p>
</div>
```

- `.dg-row` / `.dg-stack` lay out horizontally / vertically; rows wrap on small screens.
- `.dg-box` is a node; `--accent` highlights, `--muted` recedes.
- `.dg-box--frame` + a `.dg-label` first child makes a labelled container — nest frames for
  hierarchies (tenant → subscription → resource group; region → zones).
- `.dg-note` for small secondary text inside a box; `.dg-arrow` for → ↓ ⇄ connectors.
- Matrix tables (e.g. shared responsibility): `td.dg-you` / `td.dg-shared` / `td.dg-provider`.
- Always end with a `.diagram__caption`.
