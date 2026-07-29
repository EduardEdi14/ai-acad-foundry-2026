---
title: Security Incident Response Procedure
product: cybersecurity
audience: staff
effective: 2025-06-01
version: 1
---

# Security Incident Response Procedure — Internal

This procedure applies to any suspected security incident: a compromised account, malware, a phishing report from a customer, or unusual system behavior.

## The Five Phases

1. **Detect** — Any employee who notices suspicious activity (a report from a customer, an unexpected system alert, an unrecognized login) opens a ticket in the Security queue within 15 minutes of noticing it, tagged with a preliminary severity guess.
2. **Contain** — The on-call security analyst isolates the affected account, endpoint, or service (disable the account, disconnect the endpoint from the network, revoke the affected token) before any further investigation. Containment must not wait for full diagnosis.
3. **Eradicate** — Once contained, the analyst removes the root cause: resets compromised credentials, removes malicious files, closes the exploited gap. This step is signed off by a second analyst before proceeding.
4. **Recover** — Affected systems and accounts are restored from a known-good state and monitored closely for 48 hours for any recurrence.
5. **Review** — Within 5 business days of closure, the team writes a short post-incident report: what happened, what contained it, and one concrete change to prevent recurrence.

## Escalation
* Any incident classified **Severity 1** during Detect must be escalated to the CISO according to the response time in the current incident-severity SLA document — see the SLA table for the exact deadline in force.
* Any incident involving customer financial loss, regardless of severity, is escalated to both the CISO and Legal within 1 business hour of containment.

## Customer Communication During an Incident
Front-line staff and Edi_Libra may confirm to a customer that their account has been secured and that an investigation is open, but must never disclose internal severity classifications, ticket numbers, or technical root-cause details to the customer.
