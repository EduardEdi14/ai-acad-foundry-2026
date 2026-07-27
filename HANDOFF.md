# HANDOFF — read this first

Context dump for the next Claude Code thread working in this repo. Written 21 Jul 2026.
If you're an AI agent picking this up cold: read this top to bottom, then
`curriculum-ai-engineering-on-azure.md`, then `resources/ui-kit.md`. You'll be current.

---

## Who & what

- **User: Lucian Gruia** — PhD student, Head of Data Science & AI, leads teams of hundreds.
  Senior executive presence. Wants output that matches: **professional, technical,
  senior register.** **All course material in full English** (his explicit choice).
- **Project:** he mentors the Libra Bank Academy. This repo is **his module only —
  "AI Engineering on Azure", sessions 9–15** of the master agenda (S1–S7 within the
  module). 7 × 2.5h = 17.5h, **Wed 22 Jul → Thu 30 Jul 2026, 09:30–12:00, online.**
  He also co-teaches session 24 (final project eval).
- **Chain:** delivered by **Digital Stack** (vendor) to **Libra Bank** (client;
  contact **Andrei @ Libra**, who tracks which models get used — a governance signal).

## The three decisions that shape everything (locked 21 Jul)

1. **Audience is junior in practice.** Per the Python mentor's field report, most
   students have *little/no hands-on Python* — let alone frameworks, agents, or
   production. Motivated but **overwhelmed** by a fast pace, no time to consolidate.
   → Design for consolidation and scaffolding, not acceleration. Don't assume fluency.
2. **The build is their existing agent, re-skinned.** Students already hand-built a
   personality agent (KB, chunking, embeddings, semantic search, token/cost tracking)
   with George. **We keep their code, swap the persona for a banking one ("Libra
   Assist"), and rebuild each hand-rolled piece the Azure-native way.** No new project.
   Every Azure concept is introduced as the production version of something they built by hand.
3. **S1 assumes a pre-provisioned environment.** Students connect to a Foundry
   resource + endpoint that already exists. Access has been shaky (see blockers), so
   S1 *validates and repairs* rather than provisions. Provisioning is an appendix.

## Confirmed technical facts

- **Models deployed for students:** `gpt-5.1` (2025-11-13) chat + `text-embedding-3-small`
  (v1, 1536-dim). George reports **no token cap** on the chat model. He also referenced
  a "gpt mini" — possible extra SKU; confirm the exact catalog.
- **Auth:** keyless everywhere (`DefaultAzureCredential`), no hardcoded keys — this is
  a deliberate teaching stance and a bank requirement.
- **SDKs for demos:** `azure-ai-projects`, `azure-ai-inference` (OpenAI-SDK compatible).

## Adjacencies (other mentors)

- **George Flurche** — Python mentor, sessions 1–8. Owns the run-up incl. the agent
  project our whole module builds on. His grading rubric (mandatory/extensions/optional)
  maps almost 1:1 onto our S3/S5/S6 — good source of lab extensions. Don't compete with
  his code; extend it.
- **Gabi Preda** — sessions 18–23 (3–4 Aug), *after* us, **overlaps our S4/S5/S6**
  (prompt eng, RAG, agents). Treated as deliberate reinforcement, not turf; Lucian
  teaches each first, Azure-grounded. **Gabi has explicitly asked to align with Lucian
  on his "AI Deployment & Scaling / deploy agents in production" module, and to add
  Lucian to his private GitHub of course apps.** ← action for Lucian.
- **Alex Gatu** — session 16/17 (31 Jul), Security & governance. Sits right after our
  module. We touch guardrails/approval-gate in S6 but hand off to him explicitly in S7.

## Open items / blockers

1. **ACCESS (hard blocker, S1 is imminent).** Mentor access has been broken (Gabi's
   FortiClient VPN kills all internet on macOS; no Azure resource details were circulated).
   S1 is built to degrade gracefully, but "everyone makes a real `gpt-5.1` call" needs a
   real environment. Confirm with Carmen/Libra exactly what students can reach.
2. **S5 document corpus (long lead).** The RAG lab needs a real/anonymized/synthetic
   banking document set for the "Libra Assist" persona. Longest-lead item — decide the source.
3. **Gabi alignment call** — see adjacencies.
4. **Spreadsheet fixes** (master agenda, in `_raw_inputs/`): session 15 is misnumbered
   "Sesiunea 8" → should be S7; the module rename to *AI Engineering on Azure* isn't
   written in; sessions 6–8 still carry senior titles Lucian drafted but George now owns.
   **Not applied — the xlsx has only ever been read, never modified.**
5. **Persona confirmation** — lock the banking persona so the S5 corpus and S6 tools match.

## What to do next (suggested)

**S1 is 22 Jul.** The immediate critical path is building the **Session 1 package**:
- A **lab notebook** (Jupyter) — keyless auth → read the assigned Foundry topology →
  first real `gpt-5.1` call → token/cost readout. Provisioning-from-scratch as an appendix.
- A **facilitation guide** — the 150-min timing, the "everyone green" checkpoint.
- A **session doc** in `docs/` (clone `session-template.html`) and **slide-style HTML**.

Then proceed S2→S7. Each session: theory + one hands-on lab that advances the same agent.

## Repo & conventions (see README.md + resources/ui-kit.md)

- **Docs = plain standalone HTML** in `docs/`, each linking `resources/theme.css` and
  using classes from `resources/ui-kit.md`. Clone `docs/session-template.html`.
- **Demos = Python/JS** in `code/` (empty so far, `.gitkeep` only).
- **Palette is locked** (in `theme.css`): primary `#2c2d2f · #0de7e7 · #c73a52 · #eeeeee`,
  secondary `#1cb9c8 · #001240 · #ed6a5a · #292f36 · #e4c02e`. Reference tokens, never hardcode.
  Cyan is the dark-theme hero; teal is the readable accent on light. No off-palette greens.
- **`_raw_inputs/` is git-ignored** and holds the private source material:
  - `_raw_conversations/` — WhatsApp export (`_chat.txt`) + 2 photos (George's project rubric slide; the Foundry model-list screenshot).
  - `_Program Mentori_ Academia Libra V1.xlsx` — the master agenda (volatile — re-read it, it gets re-assigned between sessions without notice).
  - `conversation-log-2026-07-16.md` — log of the first planning session.

## Memory

The prior session's memory has been **pre-seeded into this repo's Claude project memory**
(`~/.claude/projects/<this-repo-slug>/memory/`) — so a new thread here should auto-load
the index. If it didn't (slug mismatch), everything you need is in this file plus the
curriculum plan. Memory files: `user-profile-lucian`, `libra-academy-program`,
`george-student-project-rubric`, `ai-acad-repo`.

## Ground truth notes

- Today per the working clock is **21 Jul 2026**; S1 = **22 Jul** (tomorrow at handoff time).
- The master spreadsheet has **not** been edited — all changes to it are still pending (item 4).
