# Corpus — edi-libra knowledge base

Fictional cybersecurity / fraud-response corpus, all under a single `product: cybersecurity`
family (see `app/agents/personas/edi-libra.json` -> `default_product`, and Assignment 3
Part 5 improvement #2, metadata filters). Split by `audience` instead: `retail` documents are
customer-facing procedures and rules; `staff` documents are internal policy the assistant may
reference but should not surface verbatim to a customer.

Documents `01`–`12` were originally a general-banking corpus (cards, mortgages, accounts,
onboarding, complaints, transfers) and have been fully replaced with cybersecurity content, so
every document `01`–`21` now belongs to this one corpus. The `default`/`teller`/`compliance`/
`lyrical` personas have no corpus of their own anymore — with `use_rag: true` they now retrieve
from this same cybersecurity collection, since it is the only one that exists.

## Documents

| # | File | product | audience | Case it covers |
|---|---|---|---|---|
| 01 | `01_compromised_account_recovery.md` | cybersecurity | retail | long procedure with steps |
| 02 | `02_login_lockout_policy.md` | cybersecurity | retail | precise number (30-min lock after 5 attempts) |
| 03 | `03_two_factor_enrollment_requirements.md` | cybersecurity | retail | must combine with 04 |
| 04 | `04_two_factor_recovery_options.md` | cybersecurity | retail | must combine with 03 |
| 05 | `05_fraud_alert_notification_2025.md` | cybersecurity | retail | near-duplicate / contradiction (superseded by 06) |
| 06 | `06_fraud_alert_notification_2026.md` | cybersecurity | retail | near-duplicate / contradiction (current) |
| 07 | `07_security_tier_comparison_table.md` | cybersecurity | retail | table |
| 08 | `08_session_and_biometric_limits.md` | cybersecurity | retail | precise numbers (3-min timeout, 3 biometric attempts) |
| 09 | `09_device_migration_procedure.md` | cybersecurity | retail | long procedure with steps |
| 10 | `10_public_network_banking_rules.md` | cybersecurity | retail | precise rule (never bank over open public Wi-Fi) |
| 11 | `11_data_breach_reporting.md` | cybersecurity | retail | long procedure with steps |
| 12 | `12_fraud_reimbursement_timelines.md` | cybersecurity | retail | precise number (10 business days, 50 EUR cap) |
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
uv run python scripts/load_corpus.py --reset    # wipe the collection, then load 01–21
```

`--reset` matters here: documents `01`–`12` were renamed, so without it the old chunks
(`source: 01_card_blocking`, etc.) would stay in Qdrant alongside the new ones instead of
being replaced — the loader only overwrites a chunk when it recomputes the same `(source, index)`
id (`app/vectorstore.py::stable_point_id`), and a renamed file has a different `source`.

The loader reads each file's front-matter (`title`, `product`, `audience`, `effective`,
`version`) and stores it as Qdrant payload metadata.
