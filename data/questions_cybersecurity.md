# Golden question set — Edi_Libra (cybersecurity / fraud-response agent)

15 questions against the `product: cybersecurity` corpus (`data/13`–`21`, see
`data/README.md`), run live through `POST /ask` with `"agent": "edi-libra"`,
`"use_rag": true`, `top_k: 4`, no explicit `product` filter — the persona's
`default_product: "cybersecurity"` applied automatically (confirmed by
`product_filter: "cybersecurity"` on every response, and every retrieved
source being a `13`–`21` document, never a banking one), measured live against
Azure Foundry (`gpt-5-mini`) on 2026-07-29.

Scoring: **correct** / **wrong** / **refused correctly** / **refused when it should have answered**.

## A · Simple retrieval (7)

| # | Question | Expected answer / doc | Result |
|---|---|---|---|
| A1 | I got a text saying my card will be blocked today unless I click a link — is that really from the bank? | Phishing/smishing warning signs; block card, don't click, report — `13` | **correct** — identified as smishing, led with "block the card / call 021.999.000", cited `[1][2][3][4]` |
| A2 | What is the deadline to file a dispute for an unauthorized transaction? | 13 business days — `14` | **correct** — "13 business days", plus the 10-business-day provisional credit as a bonus fact |
| A3 | How long can staff passwords go without being changed? | 90 days standard / 30 days privileged — `15` | **correct** |
| A4 | How long before the screen locks on a company device? | 5 minutes — `20` | **correct**, but see limitation note below |
| A5 | What should I do first if I clicked a suspicious attachment on my phone? | Disconnect Wi-Fi/data first — `21` | **correct** — led with "disconnect immediately", right order |
| A6 | How is Confidential data allowed to be shared internally? | Need-to-know + manager approval — `17` | **correct** |
| A7 | What is the emergency phone number if I suspect fraud on my account? | 021.999.000 — `14` / `13` | **correct** |

## B · Multi-step (5)

| # | Question | Needs | Result |
|---|---|---|---|
| B1 | A Severity 1 phishing incident is reported right now — how fast must it reach the CISO, and what's the first thing containment requires? | `19` (1h escalation) + `16` (Contain phase) | **partially wrong** — got the 1-hour escalation right (cited `19`), but did not surface the Contain step ("isolate the account/endpoint before further investigation") even though `16` was retrieved — the model answered "I do not have the containment procedure" instead of reading the passage it was given. A real generation-quality gap, not a retrieval gap. |
| B2 | A privileged admin password hasn't been rotated in 45 days — in policy? What's the standard-user max? | `15`, arithmetic (45 > 30) | **correct** — "out of policy", 90-day standard max, correct comparison |
| B3 | Staff device infected with malware — what severity today, and how does that compare to the 2025 SLA? | `21` (→ min Sev2) + `18` vs `19` (24h → 8h) | **wrong / honest refusal** — correctly said "at minimum Severity 2", retrieved both SLA tables, but explicitly declined to say which one is "current" ("I cannot definitively compare today vs 2025"). Root cause: `dynamic` chunking split the "Valid in 2025" / "Valid for 2026" heading away from the table rows into a different chunk than the one retrieved — the disambiguating text existed in the source doc but not in the passage the model actually saw. See note below. |
| B4 | How long must the team keep monitoring after containment, and how many days after that for the post-incident report? | `16`, two facts one doc | **correct** — 48 hours monitoring, 5 business days for the report |
| B5 | Current max time to escalate a Severity 2 incident to the CISO vs. before the 2026 update? | `18` vs `19` | **correct** — 8 hours now vs 24 hours before, explicitly attributed to "the 2026 change" |

## C · Must refuse (3)

| # | Question | Why it must refuse | Result |
|---|---|---|---|
| C1 | What is the payout for reporting a critical vulnerability under Libra Bank's bug bounty program? | No bug-bounty document exists | **refused correctly** — "none of the retrieved passages mention... program or payout", pointed to Call Center |
| C2 | How much does the cyber-insurance add-on cost per month? | No such product/doc exists | **refused correctly** |
| C3 | What is the IP range of Libra Bank's internal firewall and VPN network? | Not in corpus (and shouldn't be answerable even if it existed) | **refused correctly** — also reiterated it will never ask for PIN/CVV/password, unprompted |

## Score: 12 / 15 correct, 3 / 15 in group B showed a real weakness (0 hallucinations, 0 group-C failures)

## What this exposed

1. **B1's gap is a generation problem, not retrieval** — the Contain-phase text was in the
   top-4 passages but the model didn't use it. `require_citations: true` makes the model
   cite only what it's confident about, and it chose to under-claim rather than paraphrase
   loosely — arguably the safer failure mode for a fraud-response agent, but it means the
   answer was incomplete, not just cautious.
2. **B3 is a chunking problem**: `18_incident_severity_sla_2025.md` and
   `19_incident_severity_sla_2026.md` are near-duplicates by design (Assignment 3, Part 3),
   and the disambiguating words — "Valid in 2025" / "Valid for 2026" — live in the H1
   heading, which `dynamic` chunking sometimes separates from the table rows into a chunk
   that doesn't make the top-`k`. The Qdrant payload *does* carry the correct `effective`
   date and `version` for every chunk (Part 4 improvement #2), but `app/rag.py::build_augmented_prompt`
   never puts that metadata into the prompt — only the raw chunk text. Fixing this is Part 4
   improvement #5 (prefix each chunk with its document title/date before sending it to the
   model) and would very likely fix B3 without touching the corpus at all.
3. **A4's style quirk**: Edi_Libra's "put the immediate action on line one" rule fires even
   on a question with nothing to secure (a screen-lock policy lookup), producing a slightly
   odd "contact the Call Center" opener before the real 5-minute answer. Harmless, but shows
   a persona-level style rule can be applied too eagerly on out-of-incident questions — a
   sharper instruction ("...only when the question describes an active incident") would fix
   it without another corpus or retrieval change.
