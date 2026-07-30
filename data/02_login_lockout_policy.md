---
title: Online Banking Login Lockout Policy
product: cybersecurity
audience: retail
effective: 2026-02-01
version: 1
---

# Login Lockout After Failed Password Attempts

To slow down automated password-guessing attacks, Libra Assist locks online banking access after repeated failed login attempts.

## Lockout Rules
* After **5 consecutive failed password attempts**, the account is locked for **exactly 30 minutes**.
* A failed biometric (fingerprint/FaceID) attempt does not count toward this limit — only password attempts do.
* During the lockout window, the correct password will still be rejected; this is intentional and is not a sign of a further compromise.
* The lockout counter resets to zero after a successful login.

If you are locked out and did not attempt to log in yourself, treat it as a possible attack and follow the compromised-account recovery procedure once the lockout expires.
