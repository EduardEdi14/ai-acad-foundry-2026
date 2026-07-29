---
title: Data Classification Levels and Handling Rules
product: cybersecurity
audience: staff
effective: 2025-06-01
version: 1
---

# Data Classification — Internal Handling Rules

Every document and dataset at Libra Assist carries one of four classification levels. The table below is the single source of truth for how each level must be stored, shared, and disposed of.

| Level | Examples | Storage | Sharing | Retention |
| :--- | :--- | :--- | :--- | :--- |
| **Public** | Marketing brochures, published rates | Any company system | Freely, no approval needed | No limit |
| **Internal** | Org charts, internal policies (this document) | Company systems only, no personal devices | Within the company only | 3 years |
| **Confidential** | Customer account data, transaction history | Encrypted storage only, access-logged | Need-to-know, manager approval | 7 years, then secure deletion |
| **Restricted** | Card numbers, credentials, cryptographic keys | Encrypted vault, hardware security module where applicable | Named individuals only, IT-Security approval per request | Minimum required by regulation, then secure deletion |

## Rules That Apply to Every Level
* Confidential and Restricted data may never be emailed to a personal address or pasted into an external tool (including AI assistants outside the company's own systems).
* Printing Confidential or Restricted data requires the secure-print workflow; documents left on a printer are treated as a reportable incident.
* Reclassifying a document to a lower level requires sign-off from the data owner, not just the person handling it.
