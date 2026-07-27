# AI Engineering on Azure

**Module owner:** Lucian Gruia
**Programme:** Libra Bank Academy (delivered by Digital Stack for Libra Bank)
**Sessions:** 9–15 in the master agenda (S1–S7 within this module)
**Schedule:** Wed 22 Jul → Thu 30 Jul 2026, 09:30–12:00, seven consecutive working sessions
**Volume:** 7 × 2.5h = **17.5h**
**Delivery:** online
**Language:** English (delivery, slides, code, labs)
**Model stack (confirmed):** `gpt-5.1` (2025-11-13) chat + `text-embedding-3-small` (1536-dim) on the students' Azure AI Foundry deployment; no token cap reported on the chat model

> Status: curriculum plan. Titles and subsections only. Slides, labs, notebooks and facilitation guides come after this plan is signed off.

### Decisions locked (21 Jul)
1. **Audience is junior in practice.** Per George's field report, most students have little/no hands-on Python — let alone frameworks, agents or production. Motivated but overwhelmed by a fast pace. This module is designed for consolidation, not acceleration.
2. **The build is their existing agent, re-skinned.** Students already built a hand-rolled personality agent (KB, chunking, embeddings, semantic search, token/cost tracking) with George. I keep their code and architecture, **swap the drawn persona for a banking one**, and rebuild each piece the Azure-native way. No new project.
3. **S1 assumes a pre-provisioned environment.** Students connect to a Foundry resource + endpoint that already exists; access has been shaky, so S1 validates and repairs rather than provisions. Provisioning-from-scratch is an appendix.

---

## 1. Audience

Participants have completed eight Python sessions (Python recap, advanced constructs, APIs & async, agents in Python, file processing & embeddings, AI integration with Python, testing/logging/packaging, and a capstone kickoff). But the mentor field report is blunt: **most have little or no hands-on experience even with Python** — let alone frameworks, applications, production, or agents. They are motivated and curious, but **overwhelmed**: the pace has been fast and they have had little time to consolidate. They have *seen* embeddings and agents, and hand-rolled a naive version, but they have not internalized them.

The consequence for this module: I do not re-teach Python, but I also do not assume fluency. Every session leans on deliberate repetition, and every Azure concept is introduced as the production-grade version of something they already built by hand — so the new material has an anchor. The through-line: they made an LLM work once, in a notebook, under a firehose. This module is the second, slower pass where it actually sticks.

## 2. Positioning

This module is deliberately **not** an Azure administration course, and not a generic "intro to AI" course. It is an **engineering** course that happens to use Azure as its substrate.

The distinction to hold in every session: participants have already made an LLM work once, and hand-rolled chunking, embeddings and a retrieval loop in plain Python. This module is about everything between that and a system a bank would actually run — architecture, identity, model selection under constraints, measurement, grounding, orchestration, observability, and cost. They meet each idea twice: their naive version, then the Azure-native one.

## 3. The spine

The module runs as **one continuous build**, not seven topics — and the thing being built is **the agent each student already has**. George's project already gave every student a working personality agent (they drew a theme — cooking chef, game master, python mentor) with a hand-rolled knowledge base, chunking, embeddings, semantic search and cost tracking. I do not start a new project. I keep their code and architecture and **swap the drawn persona for a banking one**, then rebuild each hand-rolled piece the Azure-native way on top of it.

> The spine: take your existing agent, give it a banking persona ("Libra Assist"), and promote it — call by call — from a notebook demo into something a bank could run: grounded in real documents with citations, measured, observable, cost-bounded, and able to act behind an approval gate.

This keeps cognitive load low (no new project to learn), maximizes consolidation (they see their own naive component done properly), and lands on the academy's final brief (session 24: *a banking-domain AI assistant with RAG or agent logic; deliverable: an end-to-end GenAI solution*).

How the spine accumulates:

| Session | What the participant leaves with |
|---|---|
| S1 | Their assigned Foundry environment validated and authenticated (keyless), making a real `gpt-5.1` call |
| S2 | A model chosen on evidence rather than on defaults |
| S3 | A resilient, typed inference client that behaves under failure |
| S4 | Proof, in numbers, that their prompt is better than the alternative |
| S5 | Their hand-rolled retrieval replaced by Azure AI Search — grounded, with citations |
| S6 | Their agent able to act, with an approval boundary, on Foundry Agent Service |
| S7 | The whole thing defended, evaluated, and demo-ready |

Nothing is thrown away between sessions. The evaluation harness built in S4 is deliberately reused in S5 (groundedness) and S6 (agent evaluation) — that reuse is the payoff that justifies spending a session on measurement. And each of S5/S6 explicitly retires a piece of hand-rolled code the students wrote with George.

---

## 4. Sessions

### S1 — Reference Architecture for AI Solutions on Azure: Services, Resources, Identity

*Session 9 · Wed 22 Jul · 09:30–12:00*

The foundation session, under a hard operational constraint: **every participant must leave able to make a real model call**, because all six remaining sessions depend on it. Access has been shaky (see open items), so the session is built defensively — we validate and repair the environment they were handed, we do not assume it works and we do not burn the slot on provisioning.

| # | Subsection | Min |
|---|---|---|
| 1 | Framing: what actually changes when AI leaves the notebook | 10 |
| 2 | The Azure AI service landscape — Foundry, Azure OpenAI, AI Search, Container Apps, Monitor, and which question each one answers | 15 |
| 3 | Reading your environment: the topology you were handed — subscription → resource group → Foundry resource → project → deployment. Regions, model availability, TPM quota, and which of these cannot be changed later | 20 |
| 4 | Identity and access: Entra ID, managed identity, RBAC roles, keyless authentication — and why API keys are a dead end inside a bank | 20 |
| — | *Break* | 10 |
| 5 | Three reference architectures: direct inference, RAG, agentic. What each costs, and where each one breaks | 20 |
| 6 | **Lab 1** — validate and authenticate your assigned Foundry project (keyless), then make a first real `gpt-5.1` call from Python. Everyone green before we close; broken access repaired on the spot. Provisioning-from-scratch as an appendix for anyone who needs it | 45 |
| 7 | Cost and capacity: pay-as-you-go vs provisioned throughput, TPM budgeting, what bank-scale traffic actually costs | 10 |

---

### S2 — LLM Foundations and the Azure AI Foundry Model Catalog: From Attention to Inference

*Session 10 · Thu 23 Jul · 09:30–12:00*

The "what is actually behind this" session. Depth is calibrated to reasoning about model *behaviour* — why it hallucinates, why it refuses, why long context is expensive — not to reimplementing a transformer. Pitched for juniors: intuition first, math only where it pays.

| # | Subsection | Min |
|---|---|---|
| 1 | Transformer architecture: attention, and why this design scaled when others did not | 25 |
| 2 | The inference path: tokenization → embeddings → logits → sampling. Where latency and cost are actually incurred | 20 |
| 3 | Context window, KV cache, prefill vs decode — the economics of long context | 15 |
| 4 | How models are made: pretraining → SFT → RLHF/DPO. Why models hallucinate, refuse, and flatter | 15 |
| — | *Break* | 10 |
| 5 | Reasoning models and inference-time compute — when the extra tokens are worth paying for | 10 |
| 6 | The Foundry model catalog: model families, who sells vs who hosts, and the three deployment types — serverless (MaaS), managed compute, provisioned throughput | 20 |
| 7 | **Lab 2** — probe the deployed models side by side (`gpt-5.1`, plus a mini/alternative if one is deployed): tokenization, latency, cost per call, refusal behaviour. Deploy an extra catalog model if quota allows | 30 |
| 8 | The decision boundary: fine-tuning vs prompting vs retrieval (sets up S3–S5) | 5 |

---

### S3 — Model Integration and Inference: SDKs, Model Selection, and Production Trade-offs

*Session 11 · Fri 24 Jul · 09:30–12:00*

Where the model becomes a dependency in an application rather than a demo. This session leans directly on the async and API work participants did with George — and turns their ad-hoc call into a real client.

| # | Subsection | Min |
|---|---|---|
| 1 | The Foundry SDK surface: `azure-ai-projects`, `azure-ai-inference`, OpenAI SDK compatibility — and when to reach for which | 15 |
| 2 | Anatomy of a chat completion: messages, roles, system prompt, and what each parameter actually does | 15 |
| 3 | Structured outputs: JSON schema and tool calling — making a model return something a program can consume | 25 |
| 4 | Streaming, async, and batching — throughput patterns | 15 |
| — | *Break* | 10 |
| 5 | Resilience: retries, 429s and rate limits, timeouts, idempotency, circuit breakers | 15 |
| 6 | Model selection as an engineering decision: the quality/latency/cost triangle, model router, fallback chains | 15 |
| 7 | **Lab 3** — refactor their agent's model call into a typed, resilient inference client: structured output + retry + fallback + per-call cost accounting | 35 |
| 8 | Content filters: what fires, what it costs you, and how to handle it | 5 |

---

### S4 — Prompt Engineering and Systematic Evaluation: Metrics, Benchmarking, and Foundry Evaluations

*Session 12 · Mon 27 Jul · 09:30–12:00*

**The centre of gravity of this module.** Deliberately weighted towards *evaluation* rather than prompt craft — for three reasons: it is what separates an engineer from an enthusiast; it de-conflicts with Gabi Preda's later prompt-design session; and it anchors an otherwise theory-heavy topic to real Azure tooling, which makes the Azure hours legitimate rather than forced.

| # | Subsection | Min |
|---|---|---|
| 1 | Prompting as specification, not incantation: system prompts, few-shot, decomposition, chain-of-thought | 20 |
| 2 | Why "it looks good to me" collapses at scale — the case for measurement | 10 |
| 3 | Building an evaluation set: golden datasets, coverage, and where banking edge cases come from | 15 |
| 4 | The evaluator taxonomy: deterministic metrics, model-graded quality (groundedness, relevance, coherence, fluency), and risk & safety evaluators | 20 |
| — | *Break* | 10 |
| 5 | LLM-as-judge: how it works, the biases it carries, and how you validate the judge itself | 15 |
| 6 | **Lab 4** — run evaluations in Azure AI Foundry, local SDK and cloud. Compare two prompt variants on a golden set and ship the winner on evidence | 40 |
| 7 | Prompt regression testing in CI; continuous evaluation in production | 15 |
| 8 | Prompt versioning and the change-management problem | 5 |

---

### S5 — Retrieval-Augmented Generation: Embeddings, Vector Search, and Grounding with Azure AI Search

*Session 13 · Tue 28 Jul · 09:30–12:00*

The consolidation payoff: students hand-rolled chunking, embeddings and semantic search with George. This session **retires that code** and replaces it with Azure AI Search done properly — so they finally see why the naive version leaked.

| # | Subsection | Min |
|---|---|---|
| 1 | Why retrieval: the parametric-knowledge problem. RAG vs fine-tuning vs simply using long context | 15 |
| 2 | Embeddings and vector space: semantic similarity, dimensionality, embedding-model choice — with the deployed `text-embedding-3-small` (1536-dim) as the working example | 15 |
| 3 | Chunking — the highest-leverage decision in the whole pipeline, and the one their hand-rolled version most likely got wrong | 20 |
| 4 | Vector stores on Azure: AI Search, Cosmos DB, PostgreSQL/pgvector — selection criteria | 10 |
| — | *Break* | 10 |
| 5 | Azure AI Search in depth: indexes, integrated vectorization, hybrid search (BM25 + vector), semantic ranker, filters, and **security trimming** — non-negotiable in a bank | 25 |
| 6 | **Lab 5** — replace their manual retrieval with end-to-end RAG over a banking document corpus: index, hybrid retrieval, grounded generation with citations | 45 |
| 7 | Evaluating RAG: groundedness, retrieval metrics, citation accuracy — reusing the harness from S4 | 10 |

---

### S6 — Orchestration and Agentic Workflows: Multi-Step Pipelines with Azure AI Foundry Agent Service

*Session 14 · Wed 29 Jul · 09:30–12:00*

Their agent's hand-rolled reasoning loop, promoted to Foundry Agent Service — and given the ability to act, safely.

| # | Subsection | Min |
|---|---|---|
| 1 | When one call is not enough: workflows vs agents, and the autonomy spectrum | 15 |
| 2 | Agent anatomy — reasoning loop, tools, memory, termination. And the failure modes: loops, drift, tool misuse | 20 |
| 3 | Orchestration design patterns: prompt chaining, routing, parallelization, orchestrator-worker, evaluator-optimizer, reflection | 20 |
| — | *Break* | 10 |
| 4 | Azure AI Foundry Agent Service: threads, runs, and tools — File Search, Azure AI Search, function calling, OpenAPI, Code Interpreter, Logic Apps | 25 |
| 5 | Multi-agent systems: connected agents and hand-off patterns — when the extra complexity earns its keep, and when it is cargo cult | 10 |
| 6 | **Lab 6** — give their banking agent tools and a human-in-the-loop approval gate on Foundry Agent Service | 40 |
| 7 | Observability for agents: OpenTelemetry tracing, Application Insights, and agent-specific evaluators (intent resolution, tool-call accuracy, task adherence) | 10 |

---

### S7 — Capstone: An End-to-End AI Solution on Azure

*Session 15 · Thu 30 Jul · 09:30–12:00*
*Note: currently misnumbered as "Sesiunea 8" in the master spreadsheet — should be S7.*

Not a new project. This is the Azure stage of the agent they have carried since session 8, now with a banking persona — the same artefact assessed in session 24.

| # | Subsection | Min |
|---|---|---|
| 1 | The brief: consolidating their agent into a defensible end-to-end solution on Azure | 10 |
| 2 | Architecture defence — each team presents and defends its design against the reference architectures from S1 | 30 |
| — | *Break* | 10 |
| 3 | Supervised build block | 50 |
| 4 | The evaluation gate: run your own eval suite from S4 against your own system. Evidence, not vibes | 20 |
| 5 | Demo and critique round | 25 |
| 6 | Hand-off: what session 24 will assess, and what Alex Gatu's security & governance session (31 Jul) will demand of you | 5 |

**Production-readiness checklist** issued as the closing artefact — the non-negotiables: keyless auth, grounding with citations, an eval suite, tracing, cost ceiling, and a documented approval boundary.

---

## 5. Cross-cutting threads

Four threads run through every session rather than being taught once:

1. **Cost.** Every lab reports its own token spend. Introduced in S1, never dropped. This also upgrades the cost-estimation they hand-rolled with George into something measured. Participants should finish able to price a workload.
2. **Identity and least privilege.** Keyless from S1 onwards. No lab ever hardcodes a key — a deliberate teaching choice, and one Libra's own model-governance tracking (Andrei's request) reinforces.
3. **Evaluation.** Introduced properly in S4, then reused in S5 and S6. The module's argument is that unmeasured AI is not engineering.
4. **Observability.** Tracing appears in S3, deepens in S6, and is a gate in S7.

## 6. Adjacencies to resolve with other mentors

**Gabi Preda's module (sessions 18–23, 3–4 Aug) runs *after* this one and overlaps it substantially:**

| His session | Collides with | Proposed split |
|---|---|---|
| S2: Prompt Design & Engineering | My S4 | I cover evaluation and measurement; he covers prompt craft and design technique |
| S4: RAG & knowledge systems | My S5 | I cover the Azure implementation (AI Search, hybrid, security trimming); he covers conceptual RAG |
| S5: AI Agents & tool use | My S6 | I cover Foundry Agent Service and production orchestration; he covers agent concepts generally |
| S6: AI Deployment & Scaling | My S1/S7 | I cover Azure reference architecture; he covers scaling concepts — **he has explicitly asked to align with me on this one** |

The mentors are treating this overlap as **deliberate reinforcement**, not turf — which, given the "too fast to consolidate" feedback, is the right call. Since I teach each topic **first**, participants meet the Azure-grounded version before the conceptual one (concrete before abstract). That ordering just needs to be a shared decision. **Gabi has asked to align on his "AI Deployment & Scaling / deploy agents in production" module and to add me to his private GitHub of course apps — take that call before 22 Jul.**

**Alex Gatu (session 16/17, 31 Jul — Security & governance, Azure + AI)** sits immediately after this module. I touch guardrails, content safety and the approval boundary in S6 but deliberately *don't* dwell — and hand off explicitly at the end of S7.

**George Flurche (sessions 1–8)** owns everything up to and including the Python→Azure transition and the capstone kickoff. My S1 assumes his groundwork; the whole module builds directly on the agent + project rubric he set. My labs must extend his code, not compete with it.

## 7. Open items

1. **Access confirmation (blocker, S1 is 22 Jul).** Mentor access has been broken (Gabi's VPN kills all internet; no Azure resource details circulated). S1 now assumes a pre-provisioned Foundry project and is built to validate/repair — but I need confirmation from Libra/Carmen of exactly what students can reach, before the morning of 22 Jul.
2. **Regions and quota.** Model availability and TPM limits for the target region; a fallback model chosen. Confirm `gpt-5.1` + `text-embedding-3-small` are the deployment for every student (not just Gabi's).
3. **Document corpus for S5.** The RAG lab needs a real banking document set for the "Libra Assist" persona — anonymized or synthetic. Longest-lead item; needs a decision and a source now.
4. **Spreadsheet fixes.** Session 15 numbered "Sesiunea 8" → should be S7. Column J titles for sessions 9/10 say "ok"; module rename to *AI Engineering on Azure* not yet written in. Sessions 6–8 still carry senior titles I drafted but George now owns — hand over or clear. Not yet applied.
5. **Gabi alignment call.** See §6 — his Module 3 expectations + his GitHub invite.
6. **Persona swap.** Confirm the banking persona for the labs (e.g. an internal staff assistant "Libra Assist") so the S5 corpus and S6 tools match it.
