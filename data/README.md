# Corpus — Libra Assist knowledge base

Fictional retail-banking corpus, split across two `product` families so retrieval can be
scoped per agent (see `app/agents/personas/*.json` -> `default_product`, and Assignment 3
Part 5 improvement #2, metadata filters):

- `product: cards | mortgages | accounts | onboarding | complaints | transfers | security`
  (documents `01`–`12`) — the general banking corpus, served by the `default` / `teller` /
  `compliance` / `lyrical` agents.
- `product: cybersecurity` (documents `13`–`21`) — the fraud/incident-response corpus,
  served by the **edi-libra** agent.

## Documents

| # | File | product | audience | Case it covers |
|---|---|---|---|---|
| 01 | `01_card_blocking.md` | cards | retail | long procedure with steps |
| 02 | `02_early_repayment_fee.md` | mortgages | retail | precise number |
| 03 | `03_mortgage_eligibility.md` | mortgages | retail | must combine with 04 |
| 04 | `04_mortgage_schedule.md` | mortgages | retail | must combine with 03 |
| 05 | `05_fees_2025.md` | accounts | retail | near-duplicate / contradiction (superseded by 06) |
| 06 | `06_fees_2026.md` | accounts | retail | near-duplicate / contradiction (current) |
| 07 | `07_account_types_table.md` | accounts | retail | table |
| 08 | `08_deposit_rates.md` | accounts | retail | precise number |
| 09 | `09_onboarding_process.md` | onboarding | retail | long procedure with steps |
| 10 | `10_phishing_and_security.md` | security | retail | precise rule (never asks for PIN/OTP) |
| 11 | `11_complaints_handling.md` | complaints | retail | long procedure with steps |
| 12 | `12_international_transfers.md` | transfers | retail | precise number |
| 13 | `13_phishing_and_smishing_recognition.md` | cybersecurity | retail | long procedure with steps |
| 14 | `14_fraud_reporting_and_card_freeze.md` | cybersecurity | retail | precise number (13 business days) |
| 15 | `15_password_mfa_policy.md` | cybersecurity | staff | precise numbers (12 chars, 90/30-day rotation) |
| 16 | `16_incident_response_procedure.md` | cybersecurity | staff | long procedure; must combine with 19 |
| 17 | `17_data_classification_table.md` | cybersecurity | staff | table |
| 18 | `18_incident_severity_sla_2025.md` | cybersecurity | staff | near-duplicate / contradiction (superseded by 19) |
| 19 | `19_incident_severity_sla_2026.md` | cybersecurity | staff | near-duplicate / contradiction (current); must combine with 16 |
| 20 | `20_device_and_remote_access_policy.md` | cybersecurity | staff | precise numbers (5-min lock, 8h VPN session) |
| 21 | `21_ransomware_and_malware_guidance.md` | cybersecurity | mixed | long procedure with steps |

**Deliberately absent** (edi-libra must refuse, not invent — see `data/questions_cybersecurity.md`
group C): bug-bounty program terms, cyber-insurance add-on pricing, and the bank's internal
firewall/network architecture. None of the above documents mention them.

## Ingesting

```bash
cd code/backend
uv run python scripts/load_corpus.py            # add/update everything in data/
uv run python scripts/load_corpus.py --reset    # wipe the collection first
```

The loader reads each file's front-matter (`title`, `product`, `audience`, `effective`,
`version`) and stores it as Qdrant payload metadata; `source` is the file stem, and chunk
ids are derived from `(source, index)`, so re-running the loader replaces a document's
chunks instead of duplicating them (`app/vectorstore.py::stable_point_id`).
