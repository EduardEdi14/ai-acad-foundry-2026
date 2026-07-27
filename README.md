# AI Engineering on Azure — Libra Bank Academy

Course materials for **Lucian Gruia's** module (sessions 9–15) of the Libra Bank
Academy, delivered by **Digital Stack** for **Libra Bank**. Seven sessions ×
2.5h = 17.5h, Wed 22 Jul → Thu 30 Jul 2026, on Azure AI Foundry.

The module is one continuous build: students extend the agent they already built
with George (given a banking persona) into a production-grade, Azure-native
solution — grounded, measured, observable, cost-bounded, able to act.

## Repository layout

```
ai-acad-foundry-2026/
├── curriculum-ai-engineering-on-azure.md   ← v1 plan (superseded by docs/curriculum.html; kept for depth)
├── HANDOFF.md                              ← context dump — read this first if you're a new agent
├── resources/                              ← shared assets
│   ├── theme.css                           ← the one stylesheet every page links
│   ├── nav.js                              ← shared page behaviour (section nav, theme toggle)
│   └── ui-kit.md                           ← design system + component reference
├── docs/                                   ← student-facing course material (standalone HTML)
│   ├── curriculum.html                     ← the living curriculum — module homepage
│   ├── session-template.html               ← clone this per session
│   ├── sessions/                           ← one page per session (sNN-<slug>.html)
│   │   ├── s01-foundations.html            ← Session 1 · Foundations
│   │   ├── s02-foundry.html                ← Session 2 · Microsoft Foundry
│   │   └── s03-model-integration.html      ← Session 3 · Model Integration
│   ├── topics/                             ← reference deep-dives (cross-linked from sessions)
│   │   ├── ref-foundry.html                ← Microsoft Foundry, step by step
│   │   ├── ref-cloud-computing.html        ← cloud computing overview
│   │   └── ref-git.html                    ← how git works
│   └── assignments/                        ← homework briefs (aNN.md)
│       └── a1.md                           ← Assignment 1 · run backend, build admin UI
├── code/                                   ← demo code shown live
│   └── backend/                            ← RAG Teaching API (FastAPI + Qdrant, uv, docker compose;
│                                              see its README for run & credentials guides)
└── _raw_inputs/   (git-ignored)            ← private source material (WhatsApp, spreadsheet, logs)
```

## Conventions

- **Docs are plain HTML.** Each session page links `resources/theme.css` and uses
  the classes documented in `resources/ui-kit.md`. Start from `session-template.html`.
- **Palette is locked.** Primary `#2c2d2f · #0de7e7 · #c73a52 · #eeeeee`;
  secondary `#1cb9c8 · #001240 · #ed6a5a · #292f36 · #e4c02e`. Reference tokens,
  never hardcode hexes. See the UI kit.
- **Demos live in `code/`.** Python against Azure AI Foundry (`azure-ai-projects`,
  `azure-ai-inference`), keyless auth (`DefaultAzureCredential`). Models in play:
  `gpt-5.1` + `text-embedding-3-small`. Never commit endpoints or keys.
- **`_raw_inputs/` is git-ignored** and stays local.

## Getting oriented

1. Read `curriculum-ai-engineering-on-azure.md` — what's being taught and why.
2. Read `HANDOFF.md` — where we are, decisions locked, and open blockers.
3. Read `resources/ui-kit.md` — how to make anything look right.
