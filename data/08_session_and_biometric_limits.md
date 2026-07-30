---
title: Mobile App Session and Biometric Lockout Limits
product: cybersecurity
audience: retail
effective: 2026-02-15
version: 1
---

# Session Timeouts and Biometric Attempt Limits

## Session Auto-Lock
* The mobile app automatically locks and returns to the login screen after **3 minutes** of inactivity.
* A locked session requires biometric or PIN re-entry; it does not require the full password.

## Biometric Attempt Limits
* After **3 consecutive failed biometric attempts**, the app falls back to requiring the full account password.
* After **5 consecutive failed password attempts** at that point, the standard login lockout policy applies (30-minute lock).

The minimum session PIN length is **4 digits**; it is separate from the Internet Banking password and cannot be the same value.
